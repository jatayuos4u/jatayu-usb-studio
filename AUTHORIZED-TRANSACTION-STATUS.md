# Experimental authorized transaction integration

Added `udisks2_authorized_transaction.py` to combine source staging, USB inspection, UDisks2 Polkit-mediated writable descriptor acquisition, live identity/topology revalidation, chunked write, and SHA-256 readback. It is deliberately **not invoked from the Qt GUI**, not installed as a service, and not approved for hardware use.

The existing GUI remains read-only. Before deployment, the integration requires a real Polkit authorization flow test, a security review of UDisks2 FD ownership and device mount races, complete GUI progress/cancellation/error handling, and disposable USB testing. Automated tests use mocks and do not validate physical safety.

Do not run experimental writer functions against production drives. In particular, never target the OS disk.
