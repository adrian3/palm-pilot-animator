"""Exercise setup modes without downloading or executing third-party tools."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        shutil.copyfile(Path(__file__).with_name('setup-local.sh'), self.root / 'tools/setup-local.sh')
        compiler = self.root / '.local/toolchain/bin/m68k-palmos-gcc'
        compiler.parent.mkdir(parents=True)
        compiler.touch()
        (self.root / '.local/sdk-3.5').mkdir()
        (self.root / '.local/palm-sync').mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name in ('node', 'npm'):
            tool = self.bin / name
            tool.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$SETUP_TEST_LOG"\n')
            tool.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{self.bin}:/usr/bin:/bin', SETUP_TEST_LOG=str(self.root / 'calls'))

    def run_setup(self, *args):
        return subprocess.run(['/bin/sh', str(self.root / 'tools/setup-local.sh'), *args], env=self.env, capture_output=True, text=True)

    def test_export_skips_receiver(self):
        result = self.run_setup('--export-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'calls').exists())
        self.assertIn('skipped', result.stdout)

    def test_default_restores_receiver(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.root / 'calls').read_text()
        self.assertIn('npm ci --prefix', calls)
        self.assertIn('npm run build:tsc --prefix', calls)

    def test_unknown_or_extra_arguments_fail(self):
        self.assertEqual(self.run_setup('--unknown').returncode, 2)
        self.assertEqual(self.run_setup('--export-only', 'extra').returncode, 2)
        self.assertFalse((self.root / 'calls').exists())


if __name__ == '__main__':
    unittest.main()
