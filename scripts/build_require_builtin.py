#!/usr/bin/env python3
"""Build require_builtin.node for android-arm64 on GitHub Actions (ubuntu-latest).

Upstream (deepseek-ai/dsh-node-addon-require-builtin) уже поддерживает Android
в platform.cc (через __linux__ && __aarch64__). Нам нужно только:
  1. Добавить 'android' в whitelist платформ в scripts/build.ts.
    subprocess.run(['pnpm', 'install', '--frozen-lockfile'], cwd=dest_dir, check=False)
  2. Собрать через `pnpm build:native:napi`.
  3. Скопировать require_builtin.node в оба места (nodeabi + napi).
"""
import os
import subprocess
import sys
import shutil

# Правило #1: cd первой строкой
work = os.environ.get('RUNNER_TEMP') or os.environ.get('HOME')
os.chdir(work)
print(f'[cd] {work}')

clone = os.path.join(work, 'dsh-node-addon')
if os.path.isdir(clone):
    shutil.rmtree(clone)

# Клон upstream (HEAD, не тег)
subprocess.run([
    'git', 'clone',
    'https://github.com/deepseek-ai/dsh-node-addon-require-builtin.git',
    clone,
], check=True)

os.chdir(clone)
print(f'[cd] {clone}')


def patch_build_ts():
    """Добавляет 'android' в whitelist платформ в scripts/build.ts (идемпотентно)."""
    path = 'scripts/build.ts'
    if not os.path.exists(path):
        print('[!] scripts/build.ts не найден, пропускаем whitelist')
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "'android'" in content or '"android"' in content:
        print('[+] build.ts: android уже в whitelist')
        return

    # Ищем анкор 'linux' (в кавычках) и добавляем 'android' рядом
    for anchor in ["'linux'", '"linux"']:
        if anchor in content:
            # Заменяем первое вхождение anchor на anchor + ", 'android'"
            new_content = content.replace(anchor, anchor + ", 'android'", 1)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'[+] build.ts: добавлен android после {anchor}')
            return

    print('[!] build.ts: анкор linux не найден, whitelist не обновлён')


patch_build_ts()

# Сборка
print('[*] Запуск: pnpm build:native:napi')
r = subprocess.run(['pnpm', 'build:native:napi'])
if r.returncode != 0:
    sys.exit('[-] pnpm build:native:napi упал')

# Поиск результата
candidates = [
    'packages/require-builtin/entry/build/napi/napi-v9-android-arm64/require_builtin.node',
    'packages/internal-loader/entry/build/napi/napi-v9-android-arm64/require_builtin.node',
]
src = None
for c in candidates:
    full = os.path.join(clone, c)
    if os.path.exists(full):
        src = full
        print(f'[+] found: {full}')
        break

if not src:
    # Диагностика: показываем, что вообще собралось
    print('[-] require_builtin.node не найден. Ищем build/napi:')
    for root, dirs, files in os.walk(os.path.join(clone, 'packages')):
        if 'napi' in root and 'require_builtin.node' in files:
            print(f'    {os.path.join(root, "require_builtin.node")}')
    sys.exit('[-] require_builtin.node not found')

# Копирование в DSH
dsh = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
os.chdir(dsh)
print(f'[cd] {dsh}')

dst_dirs = [
    'node_modules/.pnpm/node-addon-require-builtin@0.1.9/node_modules/node-addon-require-builtin/build/nodeabi/node-v147-android-arm64',
    'node_modules/.pnpm/node-addon-require-builtin@0.1.9/node_modules/node-addon-require-builtin/build/napi/napi-v9-android-arm64',
]
for d in dst_dirs:
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, 'require_builtin.node')
    shutil.copyfile(src, dst)
    print(f'[+] copied -> {dst}')

print('[+] done')
