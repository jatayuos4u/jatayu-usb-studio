# Verified write transaction — integration status

This source adds `verified_write_transaction.py`, a descriptor-bound, progress-aware write/readback core with SHA-256 verification and cancellation. It is exercised on disposable regular files only.

**NOT a functional USB-writing release candidate.** It is not connected to the Qt GUI, UDisks2 authorized writable FD acquisition, live privileged topology attestation, or hardware tests. The caller must provide independently authorized, validated FDs; the function never opens or authorizes a block device. Never use it on physical media without implementing and auditing those missing boundaries.

Tests: 679 run, 30 skipped, no failures (local environment). No physical writes performed.
