# Jatayu USB Studio 1.1.0

USB imaging and filesystem management for Debian 13 AMD64 and KDE Plasma 6. The Qt6 application preserves the JatayuOS dashboard, dark-blue shell, branding, and original navigation. Downloads adds HTTPS ISO retrieval and a handoff to Create Bootable USB.

## Install the Debian package

Open a terminal in the directory containing the package.

```bash
sudo apt install './jatayu-usb-studio_1.1.0-1_amd64.deb'
jatayu-usb-studio --version
```

Open **Jatayu USB Studio** from the Plasma application menu. Start it as your normal desktop user. UDisks2 uses the running Plasma Polkit agent for authorization when system policy requires it. Unmount partitions on selected USB drives before disk operations.

```bash
sudo apt remove jatayu-usb-studio
```

## Create bootable media

- **Linux** — Select a hybrid Linux ISO, select and unmount the destination, then choose **Write hybrid Linux ISO**. The app checks the written bytes against the source. You can repeat the comparison later in **Verify USB**.
- **Windows** — Select an x64 Windows installer ISO and choose **Create Windows installer (UEFI)**. The app extracts the installer, splits an oversized `sources/install.wim` into FAT32-compatible parts, and prepares a FAT32 partition with the original UEFI boot files for x64 UEFI. It checks the prepared image against the bytes read back from the USB. Use the computer's UEFI boot menu to test startup. The original ISO checksum and the prepared USB checksum describe different images.

Both options erase the selected USB. Windows preparation uses local temporary space and requires 512-byte logical sectors on the USB. This Windows mode targets x64 UEFI. Legacy BIOS and ARM64 are outside its scope.

## Build and test the source

From the extracted source directory on Debian 13 AMD64:

```bash
sudo apt install build-essential cmake qt6-base-dev python3-pytest \
    python3-gi gir1.2-glib-2.0 udisks2 dosfstools exfatprogs ntfs-3g e2fsprogs \
    qt6-qpa-plugins openssl python3-pycdlib libudfread0 mtools wimtools
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
tests/run-release-tests.sh
cpack --config build/CPackConfig.cmake -B packages
```

The package appears under `packages/`. To launch the compiled application directly from the build tree, run `./build/jatayu-usb-studio`. CMake places the required Python modules in the adjacent `backend/` directory for development runs.

The release test command retains the historical tests and deselects the exact Beta 93 source-text assertions listed in `tests/beta93-only-tests.txt`. Those assertions require superseded version strings, disabled controls, prototype installation paths, or preview-only workflows. The historical test fixtures and prototypes remain in the source. See the [changelog](CHANGELOG.md) for the release and development summary.

See `RELEASE-NOTES.md`, `HARDWARE-VALIDATION.md` and `SECURITY-AUDIT.md` before testing on disposable USB drives.

## License and credits

The original Jatayu USB Studio code and documentation are licensed under the [MIT License](LICENSE). See [Credits](CREDITS.md) and [Third-party notices](THIRD_PARTY_NOTICES.md) for attribution and dependency information. The project license covers the original code and documentation. Bundled artwork and icons are outside that grant pending confirmation of their terms.
