# Experimental GUI-to-UDisks2 transaction integration

The Create Bootable USB screen now contains an opt-in experimental write button when launched with `JATAYU_USB_EXPERIMENTAL_WRITE=1`. It requires the exact `ERASE /dev/...` confirmation and invokes `experimental_write_cli.py`, which delegates to `udisks2_authorized_transaction.py` and reports JSON progress for writing and readback verification. The entire application must **not** be run as root.

**Not a release candidate.** Physical writing was not tested. Cancellation is not yet wired into this GUI workflow; closing the application during a write may leave the USB unusable. The Python helper is not included in the existing Debian packaging. The GUI compilation could not be checked in this environment because Qt6 development dependencies are unavailable. No user should activate the experimental mode on a drive holding valuable data. Default GUI operation remains read-only.
