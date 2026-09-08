#!/usr/bin/env python3
"""Verify packaged resources after copying or extracting; no network needed."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'package-manifest.json').read_text(encoding='utf-8'))
    failures = []
    for relative, expected in manifest['files'].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            failures.append(relative + ': unsafe path'); continue
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(relative)
    print(json.dumps({'version': manifest['version'], 'checked': len(manifest['files']), 'failures': failures,
                      'meaning': '文件完整性，不证明命题质量或来源真实性'}, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
