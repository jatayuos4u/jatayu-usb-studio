#!/usr/bin/env python3
"""Read-only Linux block-device inventory for hardware test preparation.

This module never opens a block device for writing. Device names and metadata
are advisory, not a security boundary; privileged writer must revalidate.
"""
import json
import os
from pathlib import Path

SYS_BLOCK = Path('/sys/class/block')

def inventory(sys_block=SYS_BLOCK):
    devices = []
    for node in sorted(Path(sys_block).iterdir()):
        try:
            if (node/'partition').exists():
                continue
            name = node.name
            if not (name.startswith('sd') or name.startswith('nvme') or name.startswith('mmcblk')):
                continue
            removable = (node/'removable').read_text().strip() == '1'
            size = int((node/'size').read_text().strip()) * 512
            ro = (node/'ro').read_text().strip() == '1'
            # Expose all candidates including nonremovable disks, but mark ineligible.
            devices.append({'path': '/dev/'+name, 'removable': removable,
                            'read_only': ro, 'size_bytes': size,
                            'eligible_for_future_hardware_test': removable and not ro and size > 0})
        except (OSError, ValueError):
            continue
    return devices

if __name__ == '__main__':
    print(json.dumps({'writing_enabled': False, 'devices': inventory()}, indent=2))
