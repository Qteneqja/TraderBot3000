import subprocess
import sys
from hashlib import sha256


def test_isolated_native_abort_leaves_trace_without_local_values(tmp_path):
    # A disposable child tests fatal diagnostics; it has no providers or application settings.
    program = """
import os
from pathlib import Path
from app.machine_learning.diagnostics import research_crash_trace
if os.name == 'posix':
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
unrelated_value = 'NEVER_LOG_THIS_SYNTHETIC_VALUE'
with research_crash_trace('../fixture-only', Path(os.environ['CRASH_TEST_ROOT'])):
    os.abort()
"""
    import os

    env = dict(os.environ, CRASH_TEST_ROOT=str(tmp_path))
    result = subprocess.run([sys.executable, '-c', program], env=env, capture_output=True, timeout=20)
    assert result.returncode != 0
    path = tmp_path / (sha256(b'../fixture-only').hexdigest() + '.log')
    trace = path.read_text()
    assert 'Fatal Python error' in trace
    assert 'NEVER_LOG_THIS_SYNTHETIC_VALUE' not in trace
    assert len(list(tmp_path.iterdir())) == 1
