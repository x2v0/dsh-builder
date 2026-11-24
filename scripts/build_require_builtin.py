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

# Применяем изменения по анкорам (без git apply — устойчиво к сдвигу строк)
def patch_file(path, old, new, label):
    if not os.path.exists(path):
        sys.exit(f'[-] {label}: file not found: {path}')
    content = open(path).read()
    if old not in content:
        sys.exit(f'[-] {label}: anchor not found in {path}')
    open(path, 'w').write(content.replace(old, new, 1))
    print(f'[+] patched {label}: {path}')

patch_file(
    'packages/native/src/runtime_context/platform.cc',
    '#elif defined(__linux__) && defined(__GLIBC__) && defined(__aarch64__)\n'
    '  return ReadLinuxGlibcArm64CurrentV8Context(isolate, symbols);',
    '#elif defined(__linux__) && defined(__GLIBC__) && defined(__aarch64__)\n'
    '  return ReadLinuxGlibcArm64CurrentV8Context(isolate, symbols);\n'
    '#elif defined(__linux__) && defined(__aarch64__)\n'
    '  // Android/bionic (Termux): the arm64 reader only calls resolved symbols,\n'
    '  // so bionic can use the same path.\n'
    '  return ReadLinuxGlibcArm64CurrentV8Context(isolate, symbols);',
    'runtime_context/platform.cc',
)

patch_file(
    'packages/native/src/runtime_probe/platform.cc',
    '#elif defined(__linux__) && defined(__GLIBC__) && defined(__aarch64__)\n'
    '  return ParseLinuxGlibcArm64BuiltinModuleRequireGetterOffset(getter);',
    '#elif defined(__linux__) && defined(__GLIBC__) && defined(__aarch64__)\n'
    '  return ParseLinuxGlibcArm64BuiltinModuleRequireGetterOffset(getter);\n'
    '#elif defined(__linux__) && defined(__aarch64__)\n'
    '  // Android/bionic: reuse the AAPCS64 getter matcher.\n'
    '  return ParseLinuxGlibcArm64BuiltinModuleRequireGetterOffset(getter);',
    'runtime_probe/platform.cc',
)

# build.ts: добавляем android в whitelist, если его нет
bt = 'scripts/build.ts'
if os.path.exists(bt):
    content = open(bt).read()
    if "'android'" not in content and '"android"' not in content:
        for anchor in ["'linux'", '"linux"']:
            if anchor in content:
                open(bt, 'w').write(content.replace(anchor, anchor + ", 'android'", 1))
                print(f'[+] patched build.ts: whitelist + android')
                break
        else:
            print('[!] build.ts: linux anchor not found, whitelist not updated')
    else:
        print('[+] build.ts: android already in whitelist')
else:
    print('[!] build.ts not found, skipping whitelist patch')

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
