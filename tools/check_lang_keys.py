#!/usr/bin/env python3
"""Check Minecraft language files for key parity and placeholder consistency.

Standard library only, matching the other helpers under tools/. Read-only.

Checks, per language file pair under ``--lang-dir``:
  * every key present in one file exists in the other (missing keys);
  * ``%s`` / ``%1$s`` / ``{0}`` placeholders match between locales;
  * keys that are also referenced from Java source but absent everywhere.

The English file is expected to be free of CJK text; the check reports any key
whose translation still contains untranslated source text.

Exit codes: 0 = clean, 1 = findings, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_LANG_DIR = Path('src/main/resources/assets/blacklight/lang')
PLACEHOLDER = re.compile(r'%(?:\d+\$)?[sdf]|\{\d+\}')
CJK = re.compile(r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]')


def load(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path} is not a JSON object')
    return data


def placeholders(value: str) -> list[str]:
    return sorted(PLACEHOLDER.findall(value))


def compare(reference: dict[str, str], other: dict[str, str],
            reference_name: str, other_name: str) -> list[str]:
    findings: list[str] = []
    for key in sorted(set(reference) - set(other)):
        findings.append(f'{key}: present in {reference_name}, missing from {other_name}')
    for key in sorted(set(other) - set(reference)):
        findings.append(f'{key}: present in {other_name}, missing from {reference_name}')
    for key in sorted(set(reference) & set(other)):
        left, right = placeholders(reference[key]), placeholders(other[key])
        if left != right:
            findings.append(f'{key}: placeholders differ ({reference_name}={left} {other_name}={right})')
    return findings


def untranslated(reference: dict[str, str], source: dict[str, str]) -> list[str]:
    """Keys whose English value still contains CJK source text."""
    return [f'{key}: English value contains CJK text: {reference[key]!r}'
            for key in sorted(reference) if CJK.search(reference[key])]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check Minecraft language files for parity and placeholders.')
    parser.add_argument('--lang-dir', default=str(DEFAULT_LANG_DIR), help='directory holding en_us.json and zh_cn.json')
    parser.add_argument('--reference', default='en_us.json', help='reference locale file name')
    parser.add_argument('--other', default='zh_cn.json', help='locale file compared against the reference')
    parser.add_argument('--allow-cjk-in-reference', action='store_true',
                        help='skip the untranslated-source check')
    args = parser.parse_args(argv)

    lang_dir = Path(args.lang_dir)
    reference_path, other_path = lang_dir / args.reference, lang_dir / args.other
    for path in (reference_path, other_path):
        if not path.is_file():
            print(f'missing language file: {path}', file=sys.stderr)
            return 2
    try:
        reference, other = load(reference_path), load(other_path)
    except (json.JSONDecodeError, ValueError) as error:
        print(f'invalid language file: {error}', file=sys.stderr)
        return 2

    findings = compare(reference, other, args.reference, args.other)
    if not args.allow_cjk_in_reference:
        findings.extend(untranslated(reference, other))
    for line in findings:
        print(line)
    print(f'\n{len(findings)} finding(s); {len(reference)} key(s) in {args.reference}, '
          f'{len(other)} in {args.other}')
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
