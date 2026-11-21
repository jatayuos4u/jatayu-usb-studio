# Writer hardening checkpoint

Adds fd-bound identity checks to the experimental writer, with isolated tests.

**NOT READY FOR HARDWARE:** No Polkit-authorized privileged writer service, no GUI write integration, no protection against every device/mount race, no hardware verification. Never run the experimental writer with `--execute` or root.
