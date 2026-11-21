#!/usr/bin/env python3
"""Unprivileged, read-only GUI adapter; NEVER a USB write authorization."""
import argparse
import json
import re
from beta79_integrated_inspection import inspect

VALID = re.compile(r"/dev/[A-Za-z0-9_.-]{1,64}\Z")

def report(device, inspector=inspect):
    if not isinstance(device, str) or not VALID.fullmatch(device):
        return {"device": str(device), "candidate": False, "reasons": ["Invalid device path"],
                "dependencies": [], "writing_enabled": False, "status": "BLOCKED"}
    try:
        result = inspector(device)
        reasons = list(result.reasons)
        if result.writing_enabled is not False:
            raise ValueError("Unexpected write authorization")
        if result.device != device or type(result.candidate) is not bool:
            raise ValueError("Inspection result mismatch")
        if not result.candidate and not reasons:
            reasons = ["Inspection rejected without explanation"]
        return {"device": device, "candidate": bool(result.candidate and not reasons),
                "reasons": reasons, "dependencies": list(result.dependencies),
                "writing_enabled": False, "status": "ADVISORY_ONLY" if result.candidate and not reasons else "BLOCKED"}
    except Exception:
        return {"device": device, "candidate": False, "reasons": ["Inspection unavailable"],
                "dependencies": [], "writing_enabled": False, "status": "BLOCKED"}

def main():
    parser = argparse.ArgumentParser(description="Read-only integrated USB inspection")
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.target), sort_keys=True))

if __name__ == '__main__':
    main()
