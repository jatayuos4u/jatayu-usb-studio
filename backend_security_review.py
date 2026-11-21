#!/usr/bin/env python3
"""Beta 45 static review of the NONPRIVILEGED system-bus inspection prototype.

This is a conservative, source-based gate, NOT a security certification.
Never starts the service, installs policy, or accesses block devices.
"""
from pathlib import Path
import ast
import re
from packaging_audit import audit_templates

ROOT = Path(__file__).resolve().parent
REVIEW_FILES = ('system_service.py', 'sender_dispatch.py', 'sender_identity.py',
                'polkit_inspection.py', 'service_security.py', 'privileged_service.py')
FORBIDDEN_CALLS = {'os.system', 'os.popen', 'subprocess.Popen', 'subprocess.run',
                   'subprocess.call', 'subprocess.check_call', 'subprocess.check_output',
                   'os.open', 'os.write', 'builtins.open'}
FORBIDDEN_IMPORTS = {'ctypes', 'fcntl', 'subprocess'}


def _name(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return (base + '.' if base else '') + node.attr
    return ''


def review(root=ROOT):
    root = Path(root)
    findings = []
    for issue in audit_templates(root):
        findings.append('deployment: ' + issue)
    for filename in REVIEW_FILES:
        path = root / filename
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=filename)
        except (OSError, UnicodeError, SyntaxError) as exc:
            findings.append(f'{filename}: cannot inspect source: {exc}')
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in FORBIDDEN_IMPORTS:
                        findings.append(f'{filename}: disallowed import {alias.name}')
            elif isinstance(node, ast.ImportFrom):
                if (node.module or '').split('.')[0] in FORBIDDEN_IMPORTS:
                    findings.append(f'{filename}: disallowed import from {node.module}')
            elif isinstance(node, ast.Call):
                name = _name(node.func)
                if name in FORBIDDEN_CALLS:
                    findings.append(f'{filename}: disallowed call {name}')
                if name in ('eval', 'exec', 'compile', '__import__'):
                    findings.append(f'{filename}: dynamic execution {name}')
    service = (root/'system_service.py').read_text(encoding='utf-8') if (root/'system_service.py').exists() else ''
    # Exact method allowlist is a deliberate protocol restriction.
    if "msg.member not in ('Capabilities', 'Prepare')" not in service:
        findings.append('system_service.py: method allowlist changed')
    if 'msg.sender' not in service:
        findings.append('system_service.py: sender envelope binding missing')
    if 'MessageType.METHOD_CALL' not in service:
        findings.append('system_service.py: method-call filtering missing')
    if 'authorized": False' not in (root/'sender_dispatch.py').read_text(encoding='utf-8'):
        findings.append('sender_dispatch.py: explicit authorization denial missing')
    if 'writing_enabled": False' not in (root/'sender_dispatch.py').read_text(encoding='utf-8'):
        findings.append('sender_dispatch.py: explicit writing denial missing')
    polkit = (root/'polkit_inspection.py').read_text(encoding='utf-8')
    if "ACTION_ID, {}, 0, ''" not in polkit:
        findings.append('polkit_inspection.py: noninteractive authorization flag changed')
    if "'system-bus-name'" not in polkit:
        findings.append('polkit_inspection.py: sender-bound subject missing')
    return findings


if __name__ == '__main__':
    issues = review()
    if issues:
        for issue in issues: print('FAIL:', issue)
        raise SystemExit(1)
    print('PASS: static non-writing inspection prototype checks (NOT a privileged backend approval)')
