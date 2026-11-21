#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then echo "Run with sudo" >&2; exit 1; fi
systemctl stop jatayu-usb-inspection.service 2>/dev/null || true
systemctl disable jatayu-usb-inspection.service 2>/dev/null || true
rm -f /etc/systemd/system/jatayu-usb-inspection.service /etc/dbus-1/system.d/in.jatayuos.USBStudio.Inspection.conf /usr/share/polkit-1/actions/in.jatayuos.usbstudio.inspect.policy
rm -rf /usr/lib/jatayu-usb-studio
systemctl daemon-reload
busctl --system call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null || true
echo 'Inspection service files removed. Dedicated service account retained.'
