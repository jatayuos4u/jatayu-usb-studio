# Jatayu USB Studio RC1 · package revision 2

Install the updated Debian 13 AMD64 build from the download directory.

```bash
sudo apt install './jatayu-usb-studio_1.1.0~rc1-2_amd64.deb'
dpkg-query -W jatayu-usb-studio
/usr/bin/jatayu-usb-studio
```

The title bar identifies package revision 2. Launching the explicit package path also avoids an older manually installed binary in `/usr/local/bin`.

- Format USB adds NTFS through Debian's `ntfs-3g` tools. It creates and checks an NTFS image before asking for the final write confirmation. The app still formats the whole selected device.
- USB Repair displays the filesystem and size of each individual partition. NTFS supports a limited read-only consistency check. Automatic NTFS repair is unavailable.
- The dashboard identifies its device inspection as read-only. The footer reports UDisks2 reachability. Physical operations use their own progress dialog, and failures show the most recent stage when available.

The updated Qt navigation test verified the NTFS option, and the file-backed NTFS test exercised both formatting and checking. The Python release suite recorded 668 passes, 6 skips and 39 deselected Beta 93 assertions. Earlier reports in the source archive describe package revision 1. Physical USB testing and live Polkit authorization remain pending.
