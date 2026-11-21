# UDisks2 topology checkpoint (not a new beta release)

Added `inspect_usb` in `udisks2_backend.py` and ten tests. The check uses
`lsblk --json` to reject non-USB, non-removable, read-only, mounted,
partition, ambiguous, and incomplete target topology. It is strictly
read-only and returns `authorized: false`, `writing_enabled: false`.

## Critical limitations

- This is a read-only user-session advisory check, NOT a privileged authorization.
- It is subject to time-of-check/time-of-use races; do not use its result
  alone to permit a write.
- No UDisks2 writable FD acquisition, Polkit authorization, or Qt GUI integration
  has been implemented in this checkpoint.
- Do not run `beta91_experimental_writer.py --execute` or run it as root.
- Hardware safety and actual bootable USB creation remain unverified.

## Checks performed

`python3 -m unittest discover -s tests -q`: 660 tests, 30 skipped, OK.
`python3 backend_security_review.py`: PASS (non-writing checks only).
`python3 packaging_audit.py`: PASS (non-writing checks only).
Qt6 compilation was not performed for this checkpoint.
