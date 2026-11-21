"""Beta 55: verify D-Bus transport cleanup without hiding ResourceWarning.

Runs existing private-bus probes as child processes. No system-bus or USB access.
"""
import json
import os
import subprocess
import sys

PROBES = (("beta53_bus_probe.py", "calls", 3), ("beta54_security_probe.py", "negative_cases", 6))

def audit(timeout=20):
    results = []
    for script, field, expected in PROBES:
        env = dict(os.environ)
        env["PYTHONWARNINGS"] = "error::ResourceWarning"
        completed = subprocess.run([sys.executable, "-X", "dev", script],
                                   cwd=os.path.dirname(os.path.abspath(__file__)),
                                   env=env, capture_output=True, text=True, timeout=timeout)
        if completed.returncode != 0 or "ResourceWarning" in completed.stderr:
            raise RuntimeError(f"{script}: cleanup audit failed: {completed.stderr.strip()}")
        try:
            data = json.loads(completed.stdout.strip())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"{script}: invalid JSON response") from exc
        if (data.get("ok") is not True or data.get("private_bus") is not True
                or data.get(field) != expected or data.get("writing_enabled") is not False
                or data.get("authorized") is True):
            raise RuntimeError(f"{script}: unexpected security result")
        results.append(script)
    return {"ok": True, "resource_warnings": 0, "private_bus_probes": len(results), "writing_enabled": False}

if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
