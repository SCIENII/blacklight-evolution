#!/usr/bin/env python3
"""Unit tests for tools/check_doc_links.py."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('check_doc_links', Path(__file__).resolve().parents[1] / 'check_doc_links.py')
links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(links)


class DocLinkCheckTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, rel, text='x'):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_existing_relative_link_passes(self):
        self.write('docs/target.md')
        self.write('README.md', '[a](docs/target.md)\n')
        self.assertEqual(links.check(self.root), [])

    def test_missing_relative_link_is_reported(self):
        self.write('README.md', '[a](docs/missing.md)\n')
        problems = links.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][0], 'README.md')
        self.assertEqual(problems[0][1], 1)
        self.assertIn('missing', problems[0][3])

    def test_parent_relative_link_resolves(self):
        self.write('docs/spec/target.md')
        self.write('docs/spec/README.md', '[a](../other/target.md)\n')
        self.write('docs/other/target.md')
        self.assertEqual(links.check(self.root), [])

    def test_external_urls_and_fragments_are_ignored(self):
        self.write('README.md', '[h](https://example.invalid/x)\n[m](mailto:a@b)\n[f](#section)\n[r][ref]\n\n[ref]: https://example.invalid/y\n')
        self.assertEqual(links.check(self.root), [])

    def test_directory_link_passes(self):
        self.write('docs/inside.md')
        self.write('README.md', '[d](docs)\n')
        self.assertEqual(links.check(self.root), [])

    def test_anchor_and_query_are_stripped(self):
        self.write('docs/target.md')
        self.write('README.md', '[a](docs/target.md#section)\n[b](docs/target.md?raw=1)\n')
        self.assertEqual(links.check(self.root), [])

    def test_case_mismatch_is_reported(self):
        self.write('docs/Target.md')
        self.write('README.md', '[a](docs/target.md)\n')
        problems = links.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn('case mismatch', problems[0][3])

    def test_escaping_root_is_reported(self):
        self.write('README.md', '[a](../../etc/passwd)\n')
        problems = links.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn('escapes', problems[0][3])

    def test_percent_encoded_and_chinese_paths(self):
        self.write('docs/\u5236\u4f5c\u8d44\u6599/\u8bf4\u660e.md')
        self.write('README.md', '[a](docs/\u5236\u4f5c\u8d44\u6599/\u8bf4\u660e.md)\n'
                                '[b](docs/%E5%88%B6%E4%BD%9C%E8%B5%84%E6%96%99/%E8%AF%B4%E6%98%8E.md)\n')
        self.assertEqual(links.check(self.root), [])

    def test_image_link_pointing_at_file_passes(self):
        self.write('docs/img.png')
        self.write('docs/a.md', '![i](img.png)\n')
        self.assertEqual(links.check(self.root), [])

    def test_build_and_run_dirs_are_skipped(self):
        self.write('build/tmp.md', '[a](missing.md)\n')
        self.write('run/tmp.md', '[a](missing.md)\n')
        self.assertEqual(links.check(self.root), [])

    def test_exit_code_reflects_findings(self):
        self.write('README.md', '[a](missing.md)\n')
        self.assertEqual(links.main(['--root', str(self.root), '--summary']), 1)
        self.write('missing.md')
        self.assertEqual(links.main(['--root', str(self.root), '--summary']), 0)


if __name__ == '__main__':
    unittest.main()
