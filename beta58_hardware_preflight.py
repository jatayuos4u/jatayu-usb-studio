#!/usr/bin/env python3
"""Read-only, fail-closed hardware-test preflight. NO destructive operations."""
import argparse
import json
import os
from pathlib import Path
from beta58_usb_inventory import inventory
from iso_write_preflight import inspect_iso

def check(iso, device, *, inventory_fn=inventory):
    result = {'ok': False, 'writing_enabled': False, 'hardware_test_ready': False,
              'device': device, 'reason': 'Not evaluated'}
    report = inspect_iso(iso)
    if not report['ok']:
        result['reason'] = report['reason']; return result
    candidates = [d for d in inventory_fn() if d['path'] == device]
    if len(candidates) != 1 or not candidates[0]['eligible_for_future_hardware_test']:
        result['reason'] = 'Device is absent or not a writable removable candidate'; return result
    if report['iso_size_bytes'] > candidates[0]['size_bytes']:
        result['reason'] = 'Image is larger than device'; return result
    result.update(ok=True, hardware_test_ready=True, iso_size_bytes=report['iso_size_bytes'],
                  iso_sha256=report['sha256'], device_size_bytes=candidates[0]['size_bytes'],
                  reason='Read-only checks passed; no physical writing capability enabled')
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='Read-only hardware preflight; NEVER writes')
    p.add_argument('--iso', required=True)
    p.add_argument('--device', required=True)
    args=p.parse_args()
    report=check(args.iso,args.device)
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['ok'] else 1)
