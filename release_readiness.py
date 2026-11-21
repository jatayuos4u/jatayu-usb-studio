#!/usr/bin/env python3
"""Beta 46 release gate: conservative static evidence, never opens a block device.

Reports prerequisites and gaps. A PASS means only that the non-writing
source-tree checks ran successfully; it does NOT approve a full USB writer.
"""
import json
from pathlib import Path
from backend_security_review import review
from packaging_audit import audit_templates

ROOT = Path(__file__).resolve().parent

def assess(root=ROOT):
    root = Path(root)
    required = ['CMakeLists.txt', 'src/main.cpp', 'assets.qrc',
                'jatayu-usb-studio.desktop', 'packaging_audit.py',
                'backend_security_review.py', 'device_topology_guard.py',
                'device_identity_guard.py', 'live_inspection_cli.py',
                'file_backed_writer.py', 'tests']
    missing = [p for p in required if not (root / p).exists()]
    checks = {
        'source_tree_complete': not missing,
        'nonwriting_service_static_review': False,
        'nonwriting_deployment_template_review': False,
        'debian_source_package_present': (root/'debian'/'control').is_file() and (root/'debian'/'rules').is_file(),
        'privileged_block_writer_approved': False,
        'hardware_destructive_tests_verified': False,
        'release_candidate_approved': False,
    }
    issues = []
    if missing: issues.append('Missing source files: ' + ', '.join(missing))
    try:
        security_issues = review(root)
        checks['nonwriting_service_static_review'] = not security_issues
        issues += ['Security static review: ' + x for x in security_issues]
    except Exception as exc:
        issues.append('Security static review could not complete: ' + str(exc))
    try:
        template_issues = audit_templates(root)
        checks['nonwriting_deployment_template_review'] = not template_issues
        issues += ['Deployment template: ' + x for x in template_issues]
    except Exception as exc:
        issues.append('Template review could not complete: ' + str(exc))
    blockers = [
        'No independently reviewed privileged block-device writer with bounded authorization and atomic device revalidation',
        'No verified disposable-hardware tests for ISO writing, cloning, formatting and recovery',
        'Debian source package is not present' if not checks['debian_source_package_present'] else 'Debian package install/upgrade/removal tests not independently verified',
        'No signed release artifact or final supply-chain review',
    ]
    return {'version': '1.1.0-beta48', 'scope': 'Read-only prototype release-readiness assessment',
            'checks': checks, 'static_findings': issues,
            'blockers_to_full_featured_stable': blockers,
            'full_featured_release_ready': False,
            'physical_usb_writes_authorized': False}

if __name__ == '__main__':
    report = assess()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['checks']['source_tree_complete'] and report['checks']['nonwriting_service_static_review'] and report['checks']['nonwriting_deployment_template_review'] else 1)
