"""Run sender-bound private-bus integration probe with strict resource warnings."""
import json, os, subprocess, sys
from pathlib import Path

def audit():
    env = dict(os.environ, PYTHONWARNINGS="error::ResourceWarning")
    result = subprocess.run([sys.executable, "-X", "dev", "beta57_bus_probe.py"],
                            cwd=Path(__file__).parent, env=env, text=True,
                            capture_output=True, timeout=25)
    if result.returncode or "ResourceWarning" in result.stderr:
        raise RuntimeError(result.stderr.strip() or "Beta 57 integration probe failed")
    data = json.loads(result.stdout)
    if (data.get("ok") is not True or data.get("private_bus") is not True
            or data.get("calls") != 4 or data.get("authorized") is not False
            or data.get("writing_enabled") is not False):
        raise RuntimeError("Unexpected sender-bound integration result")
    return {"ok": True, "private_bus": True, "calls": 4,
            "resource_warnings": 0, "writing_enabled": False}

if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
