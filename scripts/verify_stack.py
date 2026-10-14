"""Read-only HTTP smoke checks for the local deployment."""

import argparse

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, timeout=15) as client:
        for route in (
            "/",
            "/health/live",
            "/health/ready",
            "/api/overview",
            "/api/instruments",
            "/api/candles",
            "/api/signals",
            "/api/orders",
            "/api/models",
            "/api/predictions",
            "/api/risk",
            "/api/system",
        ):
            client.get(route).raise_for_status()
        overview = client.get("/api/overview").json()
        assert overview["live_execution"] == "UNSUPPORTED"
        assert client.get("/api/risk").json()["live_enabled"] is False
        candles = client.get("/api/candles").json()
        if overview["demo"]:
            assert candles["source"] == "fixture" and candles["candles"]
        print("Stack smoke checks passed")


if __name__ == "__main__":
    main()
