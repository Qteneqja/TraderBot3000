"""Isolated Docker regression: replace a backend IP without restarting its Nginx proxy.

Build the frontend image first. No application database, credentials or workers are used.
"""

import argparse
import json
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

SERVER = """
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'generation': os.environ['GENERATION'], 'path': self.path}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
"""


def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check
    )
    return result.stdout.strip()


def wait_response(base, generation):
    paths = ("/health/ready", "/api/candles?symbol=EUR_USD&timeframe=300&limit=2")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            results = []
            for path in paths:
                with urlopen(base + path, timeout=3) as response:
                    results.append(
                        json.load(response) == {"generation": generation, "path": path}
                    )
            if all(results):
                return
        except (URLError, ValueError, TimeoutError):
            pass
        time.sleep(1)
    raise AssertionError(
        f"Proxy did not serve {generation} backend with original paths/query strings"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-image", default="aegistrade-frontend")
    parser.add_argument("--backend-image", default="python:3.13-slim")
    args = parser.parse_args()
    prefix = "aegis-proxy-test-" + uuid4().hex[:12]
    network, first, second, proxy = (
        prefix + suffix for suffix in ("-net", "-first", "-second", "-proxy")
    )
    docker("network", "create", network)
    try:
        docker(
            "run",
            "-d",
            "--name",
            first,
            "--network",
            network,
            "--network-alias",
            "backend",
            "-e",
            "GENERATION=first",
            args.backend_image,
            "python",
            "-u",
            "-c",
            SERVER,
        )
        docker(
            "run",
            "-d",
            "--name",
            proxy,
            "--network",
            network,
            "-p",
            "127.0.0.1::8080",
            args.frontend_image,
        )
        inspection = json.loads(docker("inspect", proxy))[0]
        port = inspection["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
        base = f"http://127.0.0.1:{port}"
        docker("exec", proxy, "nginx", "-t")
        wait_response(base, "first")
        first_ip = json.loads(docker("inspect", first))[0]["NetworkSettings"][
            "Networks"
        ][network]["IPAddress"]
        # Allocate the replacement while the old IP is occupied, guaranteeing an actual IP change.
        docker(
            "run",
            "-d",
            "--name",
            second,
            "--network",
            network,
            "--network-alias",
            "backend",
            "-e",
            "GENERATION=second",
            args.backend_image,
            "python",
            "-u",
            "-c",
            SERVER,
        )
        second_ip = json.loads(docker("inspect", second))[0]["NetworkSettings"][
            "Networks"
        ][network]["IPAddress"]
        assert first_ip != second_ip
        docker("rm", "-f", first)
        wait_response(base, "second")
        current = json.loads(docker("inspect", proxy))[0]
        assert current["Id"] == inspection["Id"]
        assert current["State"]["StartedAt"] == inspection["State"]["StartedAt"]
        print(
            "Proxy recovery passed: changed backend IP, same proxy, health/API paths and queries preserved"
        )
    finally:
        # Only resources created under this invocation's unique prefix are removed.
        for name in (proxy, first, second):
            docker("rm", "-f", name, check=False)
        docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
