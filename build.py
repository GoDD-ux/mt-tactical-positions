# -*- coding: utf-8 -*-
"""Сборка мода в .mtmod.

    python build.py                            # собрать пакет в dist/
    python build.py --install C:/Games/Tanki   # собрать и положить в папку модов

Клиент игры работает на Python 2.7, поэтому .pyc должны быть скомпилированы именно им.
Если сам build.py запущен под Python 3, для компиляции вызывается интерпретатор
из переменной окружения PY27 (или `py -2.7`).
"""
from __future__ import print_function

import argparse
import io
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MOD_SRC = os.path.join(ROOT, 'mod')
DIST = os.path.join(ROOT, 'dist')


def read_meta():
    with io.open(os.path.join(ROOT, 'meta.xml'), encoding='utf-8') as f:
        meta = f.read()
    mod_id = re.search(r'<id>(.+?)</id>', meta).group(1)
    version = re.search(r'<version>(.+?)</version>', meta).group(1)
    return mod_id, version


def compile_sources(out_dir):
    """Кладёт в out_dir скомпилированные .pyc с путями как в клиенте (scripts/client/...)."""
    src_root = os.path.join(MOD_SRC, 'scripts')
    if sys.version_info[:2] != (2, 7):
        py27 = os.environ.get('PY27')
        cmd = [py27] if py27 else ['py', '-2.7']
        subprocess.check_call(cmd + [os.path.abspath(__file__), '--compile-only', out_dir])
        return
    for dirpath, _, filenames in os.walk(src_root):
        for name in filenames:
            if not name.endswith('.py'):
                continue
            source = os.path.join(dirpath, name)
            relative = os.path.relpath(source, MOD_SRC).replace(os.sep, '/')
            target = os.path.join(out_dir, relative + 'c')
            if not os.path.isdir(os.path.dirname(target)):
                os.makedirs(os.path.dirname(target))
            # dfile попадает в трейсбеки, пусть там будет путь как у файлов клиента
            py_compile.compile(source, target, dfile=relative, doraise=True)


def collect_files(pyc_dir):
    """Возвращает список (путь в архиве, путь на диске)."""
    files = []
    for base, prefix in ((pyc_dir, 'res/'),):
        for dirpath, _, filenames in os.walk(base):
            for name in filenames:
                if name.endswith('.py'):
                    continue
                path = os.path.join(dirpath, name)
                arcname = prefix + os.path.relpath(path, base).replace(os.sep, '/')
                files.append((arcname, path))
    files.append(('meta.xml', os.path.join(ROOT, 'meta.xml')))
    return sorted(files)


def write_package(target, files):
    # клиент читает .mtmod как zip без сжатия, каталоги должны быть отдельными записями
    dirs = set()
    for arcname, _ in files:
        parts = arcname.split('/')[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add('/'.join(parts[:i]) + '/')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_STORED) as z:
        for d in sorted(dirs):
            z.writestr(zipfile.ZipInfo(d), b'')
        for arcname, path in files:
            z.write(path, arcname)


def game_version(game_dir):
    with io.open(os.path.join(game_dir, 'version.xml'), encoding='utf-8') as f:
        match = re.search(r'<version>\s*v\.([\d.]+)', f.read())
    if not match:
        raise SystemExit('cannot read game version from version.xml')
    return match.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', metavar='GAME_DIR')
    parser.add_argument('--compile-only', metavar='OUT_DIR', help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.compile_only:
        compile_sources(args.compile_only)
        return

    mod_id, version = read_meta()
    tmp = tempfile.mkdtemp()
    try:
        compile_sources(tmp)
        if not os.path.isdir(DIST):
            os.makedirs(DIST)
        target = os.path.join(DIST, '%s_%s.mtmod' % (mod_id, version))
        write_package(target, collect_files(tmp))
    finally:
        shutil.rmtree(tmp)
    print('built', os.path.relpath(target, ROOT))

    if args.install:
        mods_dir = os.path.join(args.install, 'mods', game_version(args.install))
        shutil.copy(target, mods_dir)
        print('installed to', mods_dir)


if __name__ == '__main__':
    main()
