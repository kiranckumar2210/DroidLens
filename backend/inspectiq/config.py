"""Runtime configuration — auto-detect mock vs real devices."""

from __future__ import annotations

import os


def _env_mock():
    return os.environ.get("DROIDLENS_MOCK") or os.environ.get("INSPECTIQ_MOCK")


def use_mock_mode() -> bool:
    """Return True for mock devices. Auto-detects when env unset."""
    env = _env_mock()
    if env is not None:
        return env.lower() in ("1", "true", "yes")
    return not _sync_has_real_devices()


def _sync_has_real_devices() -> bool:
    import subprocess
    try:
        out = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=5
        )
        for line in out.stdout.splitlines()[1:]:
            if line.strip().endswith("\tdevice"):
                return True
    except Exception:
        pass
    return False
