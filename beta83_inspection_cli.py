#!/usr/bin/env python3
"""Beta83 unprivileged two-pass read-only inspection, never a write gate.

Each pass collects two kernel snapshots and a topology walk. A clean report is
advisory only; device removal or a changed report rejects the result.
"""
import argparse
import json
from beta80_inspection_cli import VALID
from beta79_integrated_inspection import inspect


def report(device, inspector=inspect):
    blocked = lambda reason: {"device": str(device), "candidate": False,
                              "reasons": [reason], "dependencies": [],
                              "writing_enabled": False, "status": "BLOCKED"}
    if not isinstance(device, str) or not VALID.fullmatch(device):
        return blocked('Invalid device path')
    try:
        first = inspector(device)
        second = inspector(device)
        for result in (first, second):
            if (result.device != device or type(result.candidate) is not bool or
                    result.writing_enabled is not False or
                    not isinstance(result.reasons, tuple) or
                    not isinstance(result.dependencies, tuple)):
                return blocked('Invalid inspection evidence')
        if first != second:
            return blocked('Device identity, topology, or safety status changed between inspections')
        if not first.candidate:
            return {"device": device, "candidate": False,
                    "reasons": list(first.reasons) or ['Inspection rejected without explanation'],
                    "dependencies": list(first.dependencies),
                    "writing_enabled": False, "status": "BLOCKED"}
        if first.reasons or not first.dependencies or first.dependencies[0] != device[5:]:
            return blocked('Incomplete or contradictory inspection evidence')
        return {"device": device, "candidate": True, "reasons": [],
                "dependencies": list(first.dependencies), "writing_enabled": False,
                "status": "ADVISORY_ONLY"}
    except Exception:
        return blocked('Inspection unavailable')


def request_write(*args, **kwargs):
    raise PermissionError('Physical USB writing remains disabled')


def main():
    parser = argparse.ArgumentParser(description='Double-pass read-only USB inspection')
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.target), sort_keys=True))

if __name__ == '__main__':
    main()
