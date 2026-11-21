#!/usr/bin/env python3
"""Beta88 user-facing non-destructive ISO staging command. No block-device access.

This CLI intentionally cannot create bootable USB media. Its output is a regular
file in a private new directory. Do not run with sudo.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from beta87_iso_workflow import stage_iso_file


def run(argv=None):
    parser = argparse.ArgumentParser(description="Stage and verify an ISO to a NEW private regular-file directory (never USB)")
    parser.add_argument('--iso', required=True)
    parser.add_argument('--output-dir', required=True, help='A NEW directory created with permissions 0700')
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        parser.error('Do not run this command as root')
    target = Path(args.output_dir)
    if target.exists() or target.is_symlink():
        parser.error('Output directory must not already exist')
    # Avoid symlinked parent paths and protected locations; keep caller in charge
    parent = target.parent
    if not parent.is_dir() or parent.is_symlink():
        parser.error('Output parent must be a real directory')
    os.mkdir(target, 0o700)
    try:
        result = stage_iso_file(args.iso, target, progress=lambda phase, done, total:
            print(f'{phase}: {done}/{total}', file=sys.stderr))
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException:
        # Preserve the directory only if it contains unexpected files; never delete caller data
        try:
            if not any(target.iterdir()):
                target.rmdir()
        except OSError:
            pass
        raise

if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except (OSError, ValueError, PermissionError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
