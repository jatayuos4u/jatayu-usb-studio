# Jatayu USB Studio — Active-swap protection review

## Finding and change

The experimental physical writer validated mounts and holders, but `/proc/self/mountinfo` does not include active swap. A removable USB partition can be used as swap without being mounted. This update adds a fail-closed check against `/proc/swaps` and compares active swap block-device major/minor numbers with the selected disk and its partitions. Four isolated regression tests cover active, unrelated, unreadable, and malformed swap information.

## Limitations and release blockers

- This is an incremental safety fix, **not** a security certification of the writer.
- No actual UDisks2/Polkit authorization, physical writing, cancellation or readback was tested on hardware in this environment.
- USB topology can change between checks; additional race-condition review is required.
- The GUI experimental writer remains disabled unless explicitly opted in. Do not enable it on a drive containing important data.
- The Qt6 application was not compiled in this environment; user previously confirmed the preceding build compiles on Debian 13.
