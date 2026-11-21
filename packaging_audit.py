"""Static safety audit for Beta 21 deployment templates; no installation."""
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parent

def audit_templates(root=ROOT):
    root = Path(root)
    policy = root / 'packaging/polkit/in.jatayuos.usbstudio.inspect.policy'
    unit = root / 'packaging/systemd/jatayu-usb-inspection.service'
    busconf = root / 'packaging/system-bus/in.jatayuos.USBStudio.Inspection.conf'
    errors = []
    try:
        tree = ET.parse(policy)
        actions = tree.findall('./action')
        if len(actions) != 1 or actions[0].attrib.get('id') != 'in.jatayuos.usbstudio.inspect':
            errors.append('Unexpected Polkit action')
        for key in ('allow_any', 'allow_inactive', 'allow_active'):
            if actions[0].findtext('./defaults/' + key) != 'no':
                errors.append('Polkit default is not deny: ' + key)
    except (OSError, ET.ParseError, IndexError) as exc:
        errors.append('Invalid Polkit policy: ' + str(exc))
    try:
        text = unit.read_text()
        for value in ('User=jatayu-usb-preview', 'NoNewPrivileges=yes', 'PrivateDevices=yes',
                      'ProtectSystem=strict', 'ProtectHome=yes', 'CapabilityBoundingSet=',
                      'AmbientCapabilities=', 'Restart=no'):
            if value not in text: errors.append('Missing service restriction: ' + value)
        if 'WantedBy=' in text and not any(line.lstrip().startswith('#') and 'WantedBy=' in line for line in text.splitlines()):
            errors.append('Automatic systemd enablement prohibited')
        if 'ExecStart=/usr/bin/python3 -I /usr/lib/jatayu-usb-studio/system_service.py' not in text:
            errors.append('Unexpected executable')
    except OSError as exc: errors.append('Invalid service unit: ' + str(exc))
    try:
        tree = ET.parse(busconf)
        owns = [e.attrib.get('own') for e in tree.findall('.//allow') if 'own' in e.attrib]
        if owns != ['in.jatayuos.USBStudio.Inspection']:
            errors.append('Unexpected D-Bus name ownership')
        for p in tree.findall('./policy'):
            if p.attrib.get('user') == 'root': errors.append('Root ownership prohibited')
    except (OSError, ET.ParseError) as exc: errors.append('Invalid D-Bus policy: ' + str(exc))
    return errors

if __name__ == '__main__':
    import sys
    failures = audit_templates()
    for failure in failures: print('FAIL:', failure)
    if not failures: print('PASS: non-writing deployment templates pass static checks')
    sys.exit(bool(failures))
