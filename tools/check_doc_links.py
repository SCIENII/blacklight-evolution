#!/usr/bin/env python3
"""Check that relative links in Markdown files resolve inside the repository.

Standard library only, matching the other helpers under tools/. Read-only: it
never edits files, moves content, or contacts the network. External URLs,
mail anchors and pure fragments are ignored; a link to a directory counts as
resolved because GitHub renders directory listings.

Exit codes: 0 = every checked link resolves, 1 = at least one link is broken,
2 = usage error.
"""
from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
import urllib.parse
from pathlib import Path

SKIP_DIRS = {'.git', 'build', '.gradle', 'node_modules', 'run', 'run-wall-gametest'}
LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
REF_DEF = re.compile(r'^\s{0,3}\[[^\]]+\]:\s*(\S+)', re.M)
HTML_SRC = re.compile(r'<(?:img|a)\b[^>]*?\b(?:src|href)\s*=\s*"([^"]+)"', re.I)
EXTERNAL = re.compile(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)')


def iter_targets(text: str):
    """Yield raw link targets with their 1-based line numbers."""
    for regex in (LINK, REF_DEF, HTML_SRC):
        for match in regex.finditer(text):
            target = match.group(1).strip()
            if target:
                yield text.count('\n', 0, match.start()) + 1, target


def resolve(doc: Path, root: Path, target: str) -> str | None:
    """Return a repo-relative path, or None when the target is not local."""
    if not target or EXTERNAL.match(target) or target.startswith('#'):
        return None
    cleaned = urllib.parse.unquote(target.split('#')[0].split('?')[0]).strip()
    if not cleaned:
        return None
    if cleaned.startswith('/'):
        joined = cleaned.lstrip('/')
    else:
        joined = posixpath.normpath(posixpath.join(doc.parent.relative_to(root).as_posix(), cleaned))
    if joined == '..' or joined.startswith('../'):
        return ''
    return joined


def existing_paths(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    dirs: set[str] = {'', '.'}
    for base, names, filenames in os.walk(root):
        names[:] = [n for n in names if n not in SKIP_DIRS]
        rel_base = Path(base).relative_to(root).as_posix()
        if rel_base != '.':
            dirs.add(rel_base)
        for name in filenames:
            files.add(posixpath.join(rel_base, name) if rel_base != '.' else name)
    return files, dirs


def markdown_files(root: Path) -> list[Path]:
    found = []
    for base, names, filenames in os.walk(root):
        names[:] = sorted(n for n in names if n not in SKIP_DIRS)
        for name in filenames:
            if name.lower().endswith('.md'):
                found.append(Path(base) / name)
    return sorted(found)


def check(root: Path) -> list[tuple[str, int, str, str]]:
    files, dirs = existing_paths(root)
    casefold = {f.casefold(): f for f in files} | {d.casefold(): d for d in dirs}
    problems = []
    for doc in markdown_files(root):
        try:
            text = doc.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            text = doc.read_text(encoding='utf-8', errors='replace')
        rel_doc = doc.relative_to(root).as_posix()
        for line, target in iter_targets(text):
            resolved = resolve(doc, root, target)
            if resolved is None:
                continue
            if resolved == '':
                problems.append((rel_doc, line, target, 'escapes repository root'))
                continue
            if resolved in files or resolved in dirs:
                continue
            if resolved.casefold() in casefold:
                problems.append((rel_doc, line, target, 'case mismatch: ' + casefold[resolved.casefold()]))
                continue
            problems.append((rel_doc, line, target, 'missing: ' + resolved))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check relative Markdown links inside the repository.')
    parser.add_argument('--root', default='.', help='repository root (default: current directory)')
    parser.add_argument('--json', action='store_true', help='emit machine-readable output')
    parser.add_argument('--summary', action='store_true', help='print only the count')
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f'not a directory: {root}', file=sys.stderr)
        return 2
    problems = check(root)
    if args.json:
        import json
        print(json.dumps([{'file': f, 'line': l, 'target': t, 'reason': r} for f, l, t, r in problems],
                         ensure_ascii=False, indent=1))
    elif args.summary:
        print(f'{len(problems)} broken relative link(s)')
    else:
        for rel_doc, line, target, reason in problems:
            print(f'{rel_doc}:{line}: {target} -> {reason}')
        print(f'\n{len(problems)} broken relative link(s) in {len(markdown_files(root))} Markdown file(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
