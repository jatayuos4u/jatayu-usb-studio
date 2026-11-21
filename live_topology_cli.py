#!/usr/bin/env python3
"""Beta 35: unprivileged live topology advisory. NEVER authorizes writes.

This snapshot can become stale immediately; not a privileged write guard.
"""
import argparse
import json
import subprocess
from device_topology_guard import inspect_topology, MAX_BYTES

LSBLK_COLUMNS = 'NAME,PATH,TYPE,TRAN,RM,RO,SIZE,MOUNTPOINTS,PKNAME'

def inspect_live(target, *, runner=subprocess.run):
    if not isinstance(target, str) or not target.startswith('/dev/') or '/' in target[5:]:
        return {'ok': False, 'authorized': False, 'writing_enabled': False, 'reason': 'Invalid target path'}
    try:
        result = runner(['lsblk', '--json', '--bytes', '--output', LSBLK_COLUMNS],
                        capture_output=True, timeout=8, check=False)
        if result.returncode != 0:
            raise ValueError('lsblk returned an error')
        if not isinstance(result.stdout, bytes) or len(result.stdout) > MAX_BYTES:
            raise ValueError('Missing or oversized lsblk snapshot')
        assessment = inspect_topology(result.stdout, target)
        assessment['read_only'] = True
        assessment['snapshot_source'] = 'lsblk'
        return assessment
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'authorized': False, 'writing_enabled': False,
                'read_only': True, 'reason': 'Live topology unavailable: ' + str(exc)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_live(args.target)))

if __name__ == '__main__':
    main()
