# Third-party notices

Jatayu USB Studio uses Qt 6 for its interface, Python and PyGObject for backend operations, and UDisks2, D-Bus, and polkit for system integration and storage authorization.

The Windows installer workflow uses pycdlib, libudfread, mtools, and wimtools. Filesystem operations use system utilities provided by util-linux, dosfstools, exfatprogs, ntfs-3g, and e2fsprogs. See the [Debian package dependency list](CMakeLists.txt) for the full list.

These dependencies are installed separately through Debian packages. Their copyright notices and license terms are available in each installed package’s `/usr/share/doc/<package>/copyright` file.

This notice covers runtime dependencies. Asset attribution should be added once the provenance and terms of the bundled icons and artwork are confirmed.
