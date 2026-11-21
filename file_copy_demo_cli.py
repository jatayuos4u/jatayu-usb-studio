"""Unprivileged regular-file copy bridge. Never opens block devices."""
import argparse
import json
import os
import sys
from file_backed_writer import copy_image_to_new_file, CopyCancelled

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--destination',required=True)
    p.add_argument('--cancel-file',required=True)
    args=p.parse_args(argv)
    if not os.path.isabs(args.cancel_file):
        p.error('Absolute cancellation path required')
    def cancelled(): return os.path.exists(args.cancel_file)
    def status(event):
        print(json.dumps({'type':'progress',**event}),flush=True)
    try:
        result=copy_image_to_new_file(args.source,args.destination,status=status,cancelled=cancelled)
        print(json.dumps({'type':'result','ok':True,**result}),flush=True)
        return 0
    except (Exception,) as exc:
        print(json.dumps({'type':'result','ok':False,'error':str(exc),'cancelled':isinstance(exc,CopyCancelled)}),flush=True)
        return 1
if __name__=='__main__': sys.exit(main())
