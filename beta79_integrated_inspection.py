#!/usr/bin/env python3
"""Read-only Beta79 inspection combining kernel evidence and dependency topology.

This is an advisory snapshot, NOT a write gate, privilege service or atomic proof.
The caller must not interpret `candidate` as permission to erase a device.
"""
from dataclasses import dataclass
from beta64_authorization import Denied
from beta77_live_evidence import snapshot_device
from beta78_storage_topology import inspect_topology

@dataclass(frozen=True)
class InspectionReport:
    device: str
    candidate: bool
    reasons: tuple
    dependencies: tuple
    writing_enabled: bool = False


def inspect(device, *, sys_root='/sys', proc_root='/proc', snapshot_fn=None, topology_fn=None):
    """Fail closed on unreadable topology, changing identity, or unsafe state.

    Injected collectors exist only for deterministic unit tests; real callers
    should use the default kernel-backed collectors with fixed root paths.
    """
    if not isinstance(device, str) or not device.startswith('/dev/'):
        return InspectionReport(str(device), False, ('Invalid target device',), ())
    snap = snapshot_fn or (lambda d: snapshot_device(d, sys_root=sys_root, proc_root=proc_root))
    topo = topology_fn or (lambda d: inspect_topology(d, sys_root=sys_root, proc_root=proc_root))
    try:
        first = snap(device)
        topology = topo(device)
        second = snap(device)
        if first != second:
            raise Denied('Device identity or state changed during inspection')
        if first.path != device or topology.get('device') != device:
            raise Denied('Device path mismatch')
        if topology.get('writing_enabled') is not False:
            raise Denied('Unexpected topology authorization flag')
        if any(topology.get(key) != getattr(first,key) for key in ('removable','read_only','mounted','system_disk')):
            raise Denied('Kernel snapshot and topology disagree')
        deps = topology.get('dependencies')
        if not isinstance(deps, tuple) or not deps or deps[0] != device[5:]:
            raise Denied('Incomplete storage dependency report')
        reasons = []
        if not first.whole_disk: reasons.append('Target is not a whole disk')
        if not first.removable: reasons.append('Target is not removable')
        if first.read_only: reasons.append('Target is read-only')
        if first.mounted: reasons.append('Target or partition is mounted')
        if first.system_disk: reasons.append('Target is used by the system')
        return InspectionReport(device, not reasons, tuple(reasons), deps)
    except (Denied, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return InspectionReport(device, False, (str(exc) or 'Inspection unavailable',), ())


def request_write(*args, **kwargs):
    raise Denied('Physical USB writing is disabled')
