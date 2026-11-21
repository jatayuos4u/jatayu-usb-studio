# Jatayu USB Studio 1.1.0 RC1 automated test report

**Environment** — Debian 13 AMD64, GCC 14.2, Qt 6.8.2, CMake 3.31.6 and Python 3.13. The isolated runtime used Debian package payloads and independent package metadata, with no host block devices exposed.

| Check | Result |
| --- | --- |
| Release Qt6 build | Passed. Executable and navigation test linked successfully. |
| Qt offscreen navigation | Passed, 1 of 1. All ten pages opened. Primary action controls were visible and enabled, and the title showed RC1. |
| Release Python suite | 667 passed, 6 skipped, 39 deselected. Includes 22 RC1-specific cases. |
| Original ZIP baseline | 684 passed and 6 skipped before editing. |
| Virtual disk workflows | Passed on regular files. ISO write, prefix comparison, checksum mismatch, clone, same-device rejection, FAT32/exFAT/ext4 formatting and checking, and ext4 partition repair with neighboring bytes preserved. |
| Replacement, cancellation and safety | Passed for test fixtures, including generation mismatch, a non-block descriptor, active swap and a declined final write confirmation. |
| Gio UDisks2 request | Passed a mocked daemon reply using a real Gio Unix FD list. Verified the OpenDevice argument types, flags, descriptor handling and close. |
| HTTPS downloads | Passed real TLS on loopback with an explicit test trust anchor. The default trust store rejected the same untrusted certificate. Error cases covered non-HTTPS redirects, incomplete or invalid ISO data, cancellation and existing destination files. |
| Package lifecycle | Passed `dpkg --install`, `dpkg -V`, installed backend imports, desktop-file validation, offscreen launch as a normal user, shared-library resolution, and `dpkg --purge`. Purge removed the program, launcher and runtime backend directory. |
| Versions | Installed binary reported `Jatayu USB Studio 1.1.0 RC1`. Package reported `1.1.0~rc1-1`, architecture `amd64`. |
| Live authorization and actual hardware | Pending. The environment rejected Unix socket creation, preventing a live UDisks2/Polkit test. No hardware writes were performed. |

The six skips are carried forward from the input suite's integration environments. The deselections are exact Beta 93 tests that assert obsolete version strings, read-only-only controls, removed prototype build paths or other superseded UI details. They are listed in `tests/beta93-only-tests.txt`; the historical tests remain in the source ZIP. The isolated package fixture staged dependencies from Debian archives, so the package lifecycle test did not boot a clean Plasma desktop or run the dependency packages' maintainer scripts.

## Repeat the release checks

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
tests/run-release-tests.sh
```

## Tested package digest

```text
7be8f4c20743c5cdff06bd02dbd8ee6246657c621c9c1324f841e1da56755728  jatayu-usb-studio_1.1.0~rc1-1_amd64.deb
```
