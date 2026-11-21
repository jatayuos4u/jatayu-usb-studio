# Experimental writer packaging integration

This checkpoint fixes the CMake install rules to include the experimental CLI and all its locally imported Python modules. It also fixes the Qt6 development-tree CLI lookup to use `JATAYU_SOURCE_DIR` before falling back to `/usr/lib/jatayu-usb-studio/experimental_write_cli.py`.

The writer remains explicitly gated by `JATAYU_USB_EXPERIMENTAL_WRITE=1`. **Do not enable on important drives.** No physical hardware test, Qt6 build, or installed-package runtime validation was possible in this environment. CMake configuration requires Qt6 development files.

Test: `python3 -m unittest discover -s tests -q`.
