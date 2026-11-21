# Jatayu USB Studio: writable-FD boundary checkpoint

This checkpoint adds `udisks2_write_boundary.py`, a testable UDisks2 `Block.OpenDevice("rw")` permission/descriptor probe. It performs two topology inspections, verifies the returned descriptor is a block device with read-write flags, matches the selected device major/minor, and closes it unconditionally. It does not expose the descriptor to the GUI or write any bytes. A Polkit prompt may occur if the probe is explicitly called on a real device; it is not called automatically.

**Do not use this code to write USB hardware.** Security gaps: fd-bound mount/swap/holder revalidation, stable identity under device replug, explicit erase confirmation tied to authorization, reliable cancel and readback, hardware test and review. Existing static audits only cover the non-writing inspection prototype.

Run tests with `python3 -m unittest discover -s tests -q`.
