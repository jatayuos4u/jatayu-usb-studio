# Jatayu USB Studio 1.1.0 RC1 security audit

**Scope** — Live disk selection, UDisks2 access, file and filesystem staging, cancellation, readback, HTTPS downloads, the GUI response protocol and the Debian package.

| Area | Control | Review outcome |
| --- | --- | --- |
| Privilege separation | Qt and Python reject root execution. UDisks2 `Block.OpenDevice` grants a descriptor under the system's stock Polkit policy. The package adds no Polkit rule, privileged service, direct root writer or setuid executable. | Reviewed package and code. Live authorization pending. |
| Device identity | Canonical path, sysfs USB ancestry, removable flag and capacity must agree with `lsblk`. GUI selections carry the kernel disk generation. The returned FD must be a block device with the expected device number, access mode, capacity and `BLKGETDISKSEQ`. Generation is monitored during I/O. | Reviewed, with file-backed rejection and Gio argument tests. Physical replacement pending. |
| Mount, swap and holders | The backend checks all direct partition holders, mount information, block-device and file-backed active swap. UDisks2 receives `O_EXCL` and `O_NOFOLLOW` when opening the disk. | Reviewed against the UDisks2 API. Actual kernel arbitration on USB media remains a hardware test. |
| Destructive confirmation | The GUI captures the selected disk generation before the typed confirmation. After authorization and staging, the backend waits for a second affirmative confirmation before the first write. Refusal, timeout and EOF abort the write. | File-backed refusal test passed. Real Polkit and final confirmation on physical media remain pending. |
| Concurrency | One primary operation per GUI instance. Kernel exclusive claims serialize competing disk opens across copies. Clone checks source/destination identity and capacity separately. | Reviewed. Competing physical opens remain a hardware test. |
| Write completion | Exact byte counts, partial-write handling, `fsync`, best-effort cache eviction, same-descriptor SHA-256 readback, and an explicit structured result. | File-backed I/O and altered-readback rejection passed. Controller cache and media persistence require hardware validation. |
| Format and repair | Filesystem tools receive only private regular files. A repair snapshot must pass a second check. Partition extents are checked against the authorized disk and rechecked before writing. | FAT32, exFAT and ext4 format/check and ext4 partition repair passed on regular-file fixtures. Live USB filesystems remain pending. |
| HTTPS and files | Certificate verification remains enabled, redirects must stay HTTPS, scratch data is private, and publication uses a no-replace hard link. | Loopback TLS, untrusted certificate, downgrade, truncation, cancellation and existing-file tests passed. |

## Residual risks and release gates

1. Actual UDisks2 and Polkit activation was blocked by the environment's denial of Unix sockets. The local Gio test exercises argument marshalling and FD ownership with a mock reply. Run the live hardware checklist before distributing this build as production-ready.
2. Kernel disk generation and exclusive access reduce device replacement and mount races. No assurance is claimed against faulty firmware, hostile kernel components, or privileged processes that can issue raw writes outside the application. Test physical replacement, concurrent claims and devices that reset mid-transfer.
3. A filesystem repair commits a verified snapshot as raw bytes. It is not an atomic transaction across power loss or disconnect. Test interruptions only on explicitly approved disposable media.
4. A post-flush SHA-256 match checks the data the kernel returns. The device may retain controller-cached data. A disconnect/reconnect and independent read is the hardware persistence check.
5. ISO digest comparison with a user-supplied reference checks integrity. Publisher authenticity depends on how that reference or signature was obtained.

Reference API documentation

- [UDisks2 Block methods and flags](https://storaged.org/doc/udisks2-api/latest/gdbus-org.freedesktop.UDisks2.Block.html#gdbus-method-org-freedesktop-UDisks2-Block.OpenDevice)
- [Linux block ioctl implementation](https://github.com/torvalds/linux/blob/master/block/ioctl.c)
