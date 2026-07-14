import os

import inspectiq.bootstrap  # noqa: F401 — patch sqlite3 before app import

os.environ.setdefault("DROIDLENS_MOCK", "true")
os.environ.setdefault("INSPECTIQ_MOCK", "true")
