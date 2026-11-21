# UDisks2 integration status — development checkpoint

This patch adds a read-only UDisks2 system-bus availability probe and a strict
whole-disk object-path constructor. It is **not** an authorized writer.

## Production blockers

- Use UDisks2 `org.freedesktop.UDisks2.Block.OpenDevice` with a Unix FD list and
  Polkit authorization; do not call `dd`/`sudo` or accept arbitrary target paths.
- Verify the selected device's major/minor, serial, capacity, USB ancestry,
  mounted descendants, holders, and system root/swap topology at the time of
  authorization and again against the opened descriptor.
- Bind the source ISO to a verified, immutable file descriptor; do not trust
  a user-controlled path after authorization.
- Run write/cancel/flush/readback as a bounded state machine; preserve honest
  partial-write status after cancellation or failures.
- Connect the Qt GUI to the backend and perform disposable-device tests.

No physical writing is enabled by this patch. The existing experimental
standalone writer must not be run as root or with `--execute`.
