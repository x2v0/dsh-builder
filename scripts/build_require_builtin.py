#!/usr/bin/env python3
"""Build require_builtin.node for android-arm64 on GitHub Actions (ubuntu-latest)."""
import os, subprocess, sys, shutil

# Правило #1: cd первой строкой
work = os.environ.get('RUNNER_TEMP') or os.environ.get('HOME')
os.chdir(work)
print(f'[cd] {work}')

clone = os.path.join(work, 'dsh-node-addon')
if os.path.isdir(clone):
    shutil.rmtree(clone)

# Клон upstream (HEAD, не тег)
subprocess.run(['git', 'clone',
    'https://github.com/deepseek-ai/dsh-node-addon-require-builtin.git', clone], check=True)

os.chdir(clone)
print(f'[cd] {clone}')

# Применяем патч
patch_file = os.environ.get('REQUIRE_BUILTIN_PATCH', 'patches/require-builtin-android.patch')
# Патч лежит в репе dsh-builder, но мы в клоне — ищем по абсолютному пути
repo = os.environ.get('GITHUB_WORKSPACE', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
patch_abs = os.path.join(repo, patch_file)
if not os.path.exists(patch_abs):
    sys.exit(f'[-] patch not found: {patch_abs}')

r = subprocess.run(['git', 'apply', '--verbose', patch_abs], capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print(r.stderr)
    sys.exit('[-] git apply failed')

# Сборка
env = os.environ.copy()
r = subprocess.run(['pnpm', 'build:native:napi'], env=env)
if r.returncode != 0:
    sys.exit('[-] build failed')

# Поиск产物
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
    sys.exit('[-] require_builtin.node not found')

# Копирование в DSH
dsh = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
os.chdir(dsh)
print(f'[cd] {dsh}')
for d in [
    'node_modules/.pnpm/node-addon-require-builtin@0.1.9/node_modules/node-addon-require-builtin/build/nodeabi/node-v147-android-arm64',
    'node_modules/.pnpm/node-addon-require-builtin@0.1.9/node_modules/node-addon-require-builtin/build/napi/napi-v9-android-arm64',
]:
    os.makedirs(d, exist_ok=True)
    shutil.copyfile(src, os.path.join(d, 'require_builtin.node'))
    print(f'[+] copied -> {d}/require_builtin.node')

print('[+] done')
