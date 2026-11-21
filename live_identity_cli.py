#!/usr/bin/env python3
"""Beta 36 live read-only identity inspection. No privileged operations."""
import argparse
import json
import subprocess
from device_identity_guard import COLUMNS, capture_identity, compare_identity
from device_topology_guard import MAX_BYTES


def snapshot_live(runner=subprocess.run):
    result = runner(['lsblk', '--json', '--bytes', '--output', COLUMNS],
                    capture_output=True, check=False, timeout=8)
    if result.returncode != 0 or not isinstance(result.stdout, bytes) or len(result.stdout) > MAX_BYTES:
        raise ValueError('lsblk failed or produced invalid snapshot')
    return result.stdout


def inspect(target, baseline=None, runner=subprocess.run):
    try:
        snapshot = snapshot_live(runner)
        return capture_identity(snapshot, target) if baseline is None else compare_identity(baseline, snapshot, target)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'authorized': False, 'writing_enabled': False, 'read_only': True,
                'reason': 'Live identity unavailable: ' + str(exc)}


def main():
    p = argparse.ArgumentParser(description='Read-only USB identity inspection (not authorization)')
    p.add_argument('--target', required=True)
    p.add_argument('--baseline-file', help='Compare against an existing baseline JSON file')
    p.add_argument('--save-baseline', help='Create a NEW baseline file; never overwrite')
    args = p.parse_args()
    if args.baseline_file and args.save_baseline:
        p.error('Choose baseline comparison OR capture')
    try:
        baseline = None
        if args.baseline_file:
            with open(args.baseline_file, 'rb') as f:
                raw = f.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Oversized baseline')
            baseline = json.loads(raw)
        result = inspect(args.target, baseline)
        if args.save_baseline and result['ok']:
            with open(args.save_baseline, 'x', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
    except (OSError, ValueError, TypeError) as exc:
        result = {'ok': False, 'authorized': False, 'writing_enabled': False, 'read_only': True,
                  'reason': 'Baseline error: ' + str(exc)}
    print(json.dumps(result))

if __name__ == '__main__':
    main()
