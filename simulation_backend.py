#!/usr/bin/env python3
"""Fail-closed, read-only USB write workflow simulation. Never opens a device."""
import argparse
import json
import os
from pathlib import Path
from writer_guard import guard
import subprocess


def simulate(snapshot, target, iso):
    report = guard(snapshot, target, iso)
    reasons = report['reasons']
    ok = report['candidate_checks_passed']
    return {'simulation_complete': ok, 'read_only': True, 'allowed_to_write': False,
            'target': target, 'reasons': reasons,
            'steps': ['ISO metadata inspected', 'USB safety guard checked',
                      'Simulated completion only'] if ok else [],
            'message': 'Guard checks passed. Simulation complete; no disk written.' if ok
                       else 'Simulation blocked. No disk written.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True)
    parser.add_argument('--iso', required=True)
    parser.add_argument('--snapshot', help='JSON test fixture instead of live lsblk')
    args = parser.parse_args()
    if args.snapshot:
        with open(args.snapshot, encoding='utf-8') as file:
            snapshot = json.load(file)
    else:
        cp = subprocess.run(['lsblk', '--json', '--bytes', '--paths', '-o',
                             'NAME,PATH,TYPE,TRAN,SIZE,MOUNTPOINTS,FSTYPE'],
                            check=True, capture_output=True, text=True, timeout=10)
        snapshot = json.loads(cp.stdout)
    print(json.dumps(simulate(snapshot, args.target, args.iso), indent=2))

if __name__ == '__main__':
    main()
