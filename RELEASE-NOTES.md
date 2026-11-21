# Jatayu USB Studio 1.1.0 release notes

The Debian 13 AMD64 package is version `1.1.0-1`. The application, About page and `--version` report **1.1.0**. This stable package supersedes the revision 21 pre-release.

- Create Bootable USB checks and stages a local ISO 9660 image, obtains a UDisks2 descriptor and verifies the written image prefix with SHA-256.
- Windows installer mode prepares x64 UEFI FAT32 media and splits oversized install.wim files. Verification compares the prepared image with the USB. Firmware boot must be tested separately.
- Clone USB uses an independent read-only source descriptor and an exclusive destination descriptor. It checks capacities and verifies the full copied byte range.
- Format USB creates and checks FAT32, exFAT or ext4 in a private image, then writes and verifies it through the authorized UDisks2 descriptor.
- Verify USB calculates SHA-256, accepts a pasted checksum or publisher checksum file, and can compare a USB image prefix against an ISO.
- USB Repair checks an unmounted filesystem using a private snapshot. Supported automatic repairs are rechecked before the application writes the repaired byte range back.
- Device Safety reports current identity and usage findings. Downloads retrieves user-supplied HTTPS ISOs, calculates SHA-256 and passes completed files to Create Bootable USB.

## Known limitations

- Hardware validation and the live KDE/Polkit authorization flow are pending. This build is intended for disposable-media testing before ISO inclusion.
- USB workflows require the kernel and `lsblk` to identify the disk as removable USB. USB SSDs and bridges reporting fixed media are rejected. The current safety policy also rejects hardware read-only media. Mounted, active swap, or held devices must be released outside the app.
- Formatting creates a whole-device filesystem and overwrites the full disk. It currently requires 512-byte logical sectors. Some older devices expect a partition table and may reject this layout.
- ISO detection checks the ISO 9660 descriptor and declared size. It cannot establish firmware bootability. Use a publisher-provided hybrid ISO and verify the publisher's checksum separately. ISO writes compare only the written prefix. A clone to a larger disk keeps the source layout, so GPT or filesystem expansion can require a separate tool.
- ISO write and USB comparison need temporary space for the ISO. Filesystem checks and repairs need temporary space up to the full checked filesystem or partition capacity. Repair supports FAT, exFAT and ext4, subject to the checker being able to repair the snapshot safely. External ext4 journals are rejected.
- Cancellation can wait for authentication, a disk syscall, or a network read to finish. Cancelling a write after it begins can leave partial data. Software cannot repair damaged hardware.
- Downloads require an HTTPS URL ending in an ISO filename and a destination filesystem that supports hard links. Download checksums are available for manual comparison with a trusted publisher reference.
