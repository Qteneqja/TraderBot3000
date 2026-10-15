"""Native-fault traces for isolated research CLI children; no values or local variables."""

import faulthandler
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path


@contextmanager
def research_crash_trace(run_id, root=Path('data/reports/research-crashes')):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Never put operator text, provider URLs or arbitrary path segments in a filename.
    path = root / (sha256(run_id.encode()).hexdigest() + '.log')
    previous = faulthandler.is_enabled()
    with path.open('a', encoding='utf-8') as stream:
        faulthandler.enable(file=stream, all_threads=True)
        try:
            yield
        finally:
            faulthandler.disable()
            if previous:
                faulthandler.enable()
