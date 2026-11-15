#!/usr/bin/env python3
"""Unit tests for tools/check_lang_keys.py."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('check_lang_keys', Path(__file__).resolve().parents[1] / 'check_lang_keys.py')
lang = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lang)


class LangKeyCheckTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def write(self, name, data):
        path = self.dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def test_parity_passes(self):
        self.write('en_us.json', {'a': 'Target', 'b': 'Hello %s'})
        self.write('zh_cn.json', {'a': '\u76ee\u6807', 'b': '\u4f60\u597d %s'})
        self.assertEqual(lang.main(['--lang-dir', str(self.dir)]), 0)

    def test_missing_key_is_reported(self):
        self.write('en_us.json', {'a': 'A', 'b': 'B'})
        self.write('zh_cn.json', {'a': 'A'})
        self.assertEqual(lang.main(['--lang-dir', str(self.dir)]), 1)

    def test_placeholder_mismatch_is_reported(self):
        self.write('en_us.json', {'a': 'Hello %s'})
        self.write('zh_cn.json', {'a': '\u4f60\u597d %d'})
        findings = lang.compare({'a': 'Hello %s'}, {'a': '\u4f60\u597d %d'}, 'en_us.json', 'zh_cn.json')
        self.assertTrue(any('placeholders differ' in f for f in findings))

    def test_positional_placeholders_must_match_exactly(self):
        self.write('en_us.json', {'a': '%1$s \u2192 %2$s'})
        self.write('zh_cn.json', {'a': '%2$s \u2192 %1$s'})
        findings = lang.compare({'a': '%1$s \u2192 %2$s'}, {'a': '%2$s \u2192 %1$s'}, 'en_us.json', 'zh_cn.json')
        self.assertEqual(findings, [])

    def test_brace_placeholders_are_compared(self):
        findings = lang.compare({'a': '{0} of {1}'}, {'a': '{0}'}, 'en_us.json', 'zh_cn.json')
        self.assertTrue(any('placeholders differ' in f for f in findings))

    def test_untranslated_source_text_is_reported(self):
        findings = lang.untranslated({'a': '\u81f3\u5c0a\u730e\u6740\u8005 Supreme Hunter'}, {})
        self.assertEqual(len(findings), 1)

    def test_translated_reference_passes(self):
        findings = lang.untranslated({'a': 'Supreme Hunter'}, {})
        self.assertEqual(findings, [])

    def test_missing_file_is_usage_error(self):
        self.write('en_us.json', {'a': 'A'})
        self.assertEqual(lang.main(['--lang-dir', str(self.dir)]), 2)

    def test_invalid_json_is_usage_error(self):
        (self.dir / 'en_us.json').write_text('{', encoding='utf-8')
        self.write('zh_cn.json', {'a': 'A'})
        self.assertEqual(lang.main(['--lang-dir', str(self.dir)]), 2)

    def test_non_object_json_is_usage_error(self):
        (self.dir / 'en_us.json').write_text('[]', encoding='utf-8')
        self.write('zh_cn.json', {})
        self.assertEqual(lang.main(['--lang-dir', str(self.dir)]), 2)


if __name__ == '__main__':
    unittest.main()
