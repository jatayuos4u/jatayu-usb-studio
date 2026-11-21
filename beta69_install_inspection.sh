#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then echo "Run with sudo: sudo sh beta69_install_inspection.sh" >&2; exit 1; fi
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v systemctl >/dev/null || { echo "systemd required" >&2; exit 1; }
/usr/bin/python3 -c 'import dbus_next' || { echo "Install python3-dbus-next first" >&2; exit 1; }
if ! getent group jatayu-usb-preview >/dev/null; then groupadd --system jatayu-usb-preview; fi
if ! id jatayu-usb-preview >/dev/null 2>&1; then useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --gid jatayu-usb-preview jatayu-usb-preview; fi
install -d -o root -g root -m 0755 /usr/lib/jatayu-usb-studio
for name in beta52_system_bus beta551_dbus_cleanup beta56_secure_dispatch beta63_service beta65_polkit beta66_inspection_service beta67_system_bus polkit_inspection sender_identity; do
    install -o root -g root -m 0644 "$BASE/$name.py" "/usr/lib/jatayu-usb-studio/$name.py"
done
install -o root -g root -m 0644 "$BASE/packaging/system-bus/in.jatayuos.USBStudio.Inspection.conf" /etc/dbus-1/system.d/in.jatayuos.USBStudio.Inspection.conf
install -o root -g root -m 0644 "$BASE/packaging/polkit/in.jatayuos.usbstudio.inspect.policy" /usr/share/polkit-1/actions/in.jatayuos.usbstudio.inspect.policy
install -o root -g root -m 0644 "$BASE/packaging/systemd/jatayu-usb-inspection-beta69.service" /etc/systemd/system/jatayu-usb-inspection.service
systemctl daemon-reload
# Reload D-Bus policy without restarting the system bus (disruptive).
if command -v busctl >/dev/null; then busctl --system call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null; fi
echo 'Installed inspection service files; not started or enabled.'
echo 'Next: sudo systemctl start jatayu-usb-inspection.service'
