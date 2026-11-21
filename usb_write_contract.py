"""Beta 47/48 proposed authorization contract. Fail closed: no privileged writer installed."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ProposedWriteRequest:
    iso_sha256: str
    destination: str
    expected_serial: str
    expected_major_minor: str
    expected_size: int


def prepare_write(request, *, caller=None, polkit=None):
    """Never grant write permission, even with plausible inputs or mock authorization."""
    return {'ok': False, 'authorized': False, 'writing_enabled': False,
            'reason': 'Privileged physical USB writer is not implemented or approved'}


def execute_write(request, *, caller=None, polkit=None):
    return prepare_write(request, caller=caller, polkit=polkit)
