#!/usr/bin/env python3
"""Beta84: read-only system-bus health check plus independent LOCAL inspection.

The installed D-Bus service does NOT perform device inspection. Never represent
local evidence as service-certified or as permission to write.
"""
import argparse
import asyncio
import json
from beta83_inspection_cli import report as local_report
from beta68_real_bus_audit import audit


def combine(device, local, service):
    result = {'device': device, 'candidate': False, 'reasons': [],
              'dependencies': [], 'writing_enabled': False,
              'status': 'UNAVAILABLE', 'inspection_source': 'local_unprivileged',
              'service_status': 'UNAVAILABLE', 'service_verified': False,
              'trusted_device_inspection': False}
    if type(service) is dict:
        result['service_status'] = str(service.get('status', 'UNAVAILABLE'))[:80]
        result['service_verified'] = (service.get('ok') is True and
            service.get('real_system_bus') is True and
            service.get('status') == 'INSPECTION_ONLY' and
            service.get('writing_enabled') is False)
    if type(local) is not dict or local.get('device') != device or local.get('writing_enabled') is not False:
        result['reasons'] = ['Local inspection evidence unavailable or invalid']
        return result
    if (type(local.get('candidate')) is not bool or
        type(local.get('reasons')) is not list or
        not all(type(x) is str for x in local['reasons']) or
        type(local.get('dependencies')) is not list or
        not all(type(x) is str for x in local['dependencies']) or
        local.get('status') not in ('BLOCKED','ADVISORY_ONLY')):
        result['reasons'] = ['Malformed local inspection evidence']
        return result
    result['dependencies'] = local['dependencies']
    if local['status'] == 'BLOCKED' or local['candidate'] is False:
        result['status'] = 'BLOCKED'
        result['reasons'] = local['reasons'] or ['Local inspection blocked']
    elif local['status'] == 'ADVISORY_ONLY' and local['candidate'] is True and not local['reasons']:
        result['status'] = 'ADVISORY_ONLY'
        result['candidate'] = True
    else:
        result['reasons'] = ['Contradictory local inspection evidence']
    return result


def main():
    parser=argparse.ArgumentParser(description='Read-only D-Bus health + local safety evidence')
    parser.add_argument('--target', required=True)
    args=parser.parse_args()
    try:
        local=local_report(args.target)
    except Exception:
        local=None
    try:
        service=asyncio.run(asyncio.wait_for(audit(),timeout=6))
    except Exception:
        service={'ok':False,'status':'SYSTEM_BUS_UNAVAILABLE','writing_enabled':False}
    print(json.dumps(combine(args.target,local,service),sort_keys=True))

if __name__=='__main__':
    main()
