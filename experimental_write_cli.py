"""Opt-in experimental UDisks2 ISO writer. Not for production deployment."""
import argparse
import json
import os
import sys
from pathlib import Path
from udisks2_authorized_transaction import authorized_transaction


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--confirm', required=True)
    parser.add_argument('--cancel-file', help='Private GUI cancellation marker')
    args = parser.parse_args(argv)
    if os.environ.get('JATAYU_USB_EXPERIMENTAL_WRITE') != '1':
        parser.error('Experimental writing is disabled by default')
    if os.geteuid() == 0:
        parser.error('Do not run the GUI writer as root; UDisks2 handles authorization')
    if args.confirm != 'ERASE ' + args.device:
        parser.error('Exact device-specific confirmation required')
    def cancelled():
        return bool(args.cancel_file and Path(args.cancel_file).is_file())
    def progress(phase, done, total):
        print(json.dumps({'event':'progress','phase':phase,'bytes':done,'total':total}), flush=True)
    try:
        result = authorized_transaction(args.iso, args.device, confirm=args.confirm, progress=progress, cancelled=cancelled)
        print(json.dumps({'event':'result', **result}), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({'event':'error','message':str(exc)}), flush=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
