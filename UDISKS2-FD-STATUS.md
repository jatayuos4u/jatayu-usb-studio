# UDisks2 FD integration — developer-only checkpoint

Implemented: Gio system-bus `Block.OpenDevice("r", {})` with Unix FD list handling, read-only topology check before/after acquisition, opened-fd major/minor matching, deterministic close, and tests.

**Not implemented:** authorized writable descriptor, Polkit write flow, fd-bound mount/holder race resistance, GUI writing, boot validation. This module cannot write USB drives. Do not deploy or promote to RC.

Run `python3 -m unittest discover -s tests -q` from the project root. Existing Qt6 GUI remains unchanged.
