"""Guard the installed experimental writer's complete local import closure."""
import ast
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class WriterPackagingTests(unittest.TestCase):
    def test_cmake_installs_local_import_closure(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        installed = set()
        for match in re.finditer(r'install\(FILES\s+(.*?)\s+DESTINATION\s+lib/jatayu-usb-studio\)', cmake, re.S):
            installed.update(re.findall(r'\b[\w.-]+\.py\b', match.group(1)))
        pending = ['experimental_write_cli.py']
        visited = set()
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            self.assertIn(name, installed, f'Missing installed dependency: {name}')
            tree = ast.parse((ROOT / name).read_text())
            for node in ast.walk(tree):
                modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                           [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    if module and (ROOT / (module + '.py')).exists():
                        pending.append(module + '.py')

    def test_gui_uses_source_dir_for_development(self):
        main = (ROOT / 'src/main.cpp').read_text()
        self.assertIn('JATAYU_SOURCE_DIR', main)
        self.assertIn('/usr/lib/jatayu-usb-studio/experimental_write_cli.py', main)


if __name__ == '__main__':
    unittest.main()
