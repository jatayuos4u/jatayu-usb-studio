# Hardware validation checklist

**Status** — Pending on a Debian 13 AMD64 desktop with KDE Plasma 6. No physical USB device was modified during development.

Use two clearly labelled spare drives with expendable contents and a trusted Linux hybrid ISO. Confirm which device is disposable by manufacturer, model, capacity and the displayed path. Record the package version, kernel, UDisks2 version, USB models and the result of each check.

## Read-only and authorization

- [ ] Install the package and start it from the Plasma application menu as a normal user. Verify the About page and `jatayu-usb-studio --version` both show 1.1.0 RC1.
- [ ] Check that the internal system disk never appears in a write selector. Confirm that Device Safety gives a rejection reason for mounted, read-only or busy removable devices when present.
- [ ] With a disposable target, decline the initial confirmation, deny the Polkit request, and decline the final confirmation in separate runs. Verify that each run leaves the drive unchanged.
- [ ] Check that the system Polkit agent appears when no previous authorization is cached. Verify that an inactive session or a denied policy receives a readable error.
- [ ] Replace a selected spare drive before approving a write. Verify that the replacement is rejected, even if it receives the same `/dev` path.
- [ ] Where you already have an approved disposable swap fixture, confirm Device Safety rejects active USB swap. Leave host swap and system storage untouched.

## Destructive tests on approved disposable drives

- [ ] Write the Linux ISO, observe progress and let SHA-256 readback finish. Safely disconnect and reconnect the drive, run Verify USB, and test firmware boot in the intended UEFI or BIOS mode.
- [ ] Clone from the first spare drive to the second. Check insufficient capacity and same-device rejection. Independently compare the copied source byte range.
- [ ] Format each of FAT32, exFAT and ext4. Reconnect the drive, confirm the filesystem type, mount it and verify an ordinary file can be created and read.
- [ ] Use a known recoverable filesystem fixture with a backup. Check reports damage without writing, then validate the supported repair and run a fresh check.
- [ ] Open the same spare disk from a second instance. Verify competing access fails while the first instance holds the device. Verify mounted targets stay blocked.
- [ ] Cancel during an approved write and verify the partial-write message. Separately disconnect a spare drive during an approved test and verify I/O failure without a success message.
- [ ] Download a Linux ISO from a trusted publisher HTTPS URL, compare the digest, and send the result to Create Bootable USB. Verify TLS, error and existing-file handling.
- [ ] Remove the package and confirm the launcher and installed program disappear.
