#!/usr/bin/env python3
"""Unprivileged, read-only kernel identity and usage inspection; never authorizes writing."""
import argparse
import json
from device_revalidation import inspect_device
from live_safety import inspect_usage

def inspect(target):
    try:
        fingerprint = inspect_device(target)
        usage = inspect_usage(fingerprint)
        return {'ok': bool(usage['safe_snapshot']), 'read_only': True,
                'writing_authorized': False, 'target': target,
                'major': fingerprint.major, 'minor': fingerprint.minor,
                'capacity_bytes': fingerprint.size_bytes,
                'kernel_identity_checked': True, 'usage_checked': True,
                'reason': 'Kernel identity and mount/swap/holder snapshot passed; NOT write authorization'}
    except (OSError, ValueError, TypeError) as exc:
        return {'ok': False, 'read_only': True, 'writing_authorized': False,
                'target': target, 'reason': str(exc)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.target)))

if __name__ == '__main__':
    main()
