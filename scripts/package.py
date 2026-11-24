import os
import json
import glob
import shutil
import re

base = os.getcwd()

# 1. Пакет system.node
pkg_dir = 'node_modules/@deepseek-ai/node-addon-system-android-arm64'
os.makedirs(os.path.join(pkg_dir, 'bin'), exist_ok=True)
with open(os.path.join(pkg_dir, 'package.json'), 'w') as f:
    json.dump({"name": "@deepseek-ai/node-addon-system-android-arm64", "version": "0.1.2", "main": "bin/system.node"}, f, indent=2)

# 2. Пакет @esbuild/android-arm64
esbuild_bin = '../prebuilt/esbuild-android-arm64'
esbuild_dirs = glob.glob('node_modules/.pnpm/esbuild@*/node_modules/esbuild')
for es_dir in esbuild_dirs:
    with open(os.path.join(es_dir, 'package.json')) as f:
        ver = json.load(f)['version']
    scope_dir = os.path.join(os.path.dirname(es_dir), '@esbuild', 'android-arm64')
    os.makedirs(os.path.join(scope_dir, 'bin'), exist_ok=True)
    with open(os.path.join(scope_dir, 'package.json'), 'w') as f:
        json.dump({"name": "@esbuild/android-arm64", "version": ver, "os": ["android"], "cpu": ["arm64"]}, f, indent=2)
    shutil.copy2(esbuild_bin, os.path.join(scope_dir, 'bin', 'esbuild'))
    os.chmod(os.path.join(scope_dir, 'bin', 'esbuild'), 0o755)

# 3. Нативные модули
req_dirs = glob.glob('node_modules/.pnpm/node-addon-require-builtin@*/node_modules/node-addon-require-builtin')
for req_dir in req_dirs:
    for p in [os.path.join(req_dir, 'build', 'nodeabi', 'node-v147-android-arm64'), os.path.join(req_dir, 'build', 'napi', 'napi-v9-android-arm64')]:
        os.makedirs(p, exist_ok=True)
        shutil.copy2('../prebuilt/require_builtin.node', os.path.join(p, 'require_builtin.node'))

koffi_dirs = glob.glob('node_modules/.pnpm/koffi@*/node_modules/koffi')
for k_dir in koffi_dirs:
    for p in [os.path.join(k_dir, 'build', 'koffi', 'android_arm64'), k_dir]:
        os.makedirs(p, exist_ok=True)
        shutil.copy2('../prebuilt/koffi.node', os.path.join(p, 'koffi.node'))

pty_dirs = glob.glob('node_modules/.pnpm/node-pty@*/node_modules/node-pty')
for p_dir in pty_dirs:
    for p in [os.path.join(p_dir, 'build', 'Release'), os.path.join(p_dir, 'prebuilds', 'android-arm64')]:
        os.makedirs(p, exist_ok=True)
        shutil.copy2('../prebuilt/node-pty.node', os.path.join(p, 'pty.node'))
        shutil.copy2('../prebuilt/node-pty.node', os.path.join(p, 'node-pty.node'))

# 4. Симлинки для vendor
vendor_dir = 'vendor'
if os.path.isdir(vendor_dir):
    for vpkg in os.listdir(vendor_dir):
        vjson = os.path.join(vendor_dir, vpkg, 'package.json')
        if os.path.exists(vjson):
            with open(vjson) as f:
                name = json.load(f).get('name')
            if name:
                if name.startswith('@'):
                    scope, pname = name.split('/', 1)
                    ldir = os.path.join('node_modules', scope)
                else:
                    ldir = 'node_modules'
                    pname = name
                os.makedirs(ldir, exist_ok=True)
                lpath = os.path.join(ldir, pname)
                if not os.path.exists(lpath):
                    rel = os.path.relpath(os.path.join(vendor_dir, vpkg), ldir)
                    os.symlink(rel, lpath)

# 5. Патч FiberState
fiber_ts = os.path.join(vendor_dir, 'cordis', 'src', 'fiber.ts')
profile_boot = 'apps/cli/src/profile-boot.ts'
if os.path.exists(fiber_ts) and os.path.exists(profile_boot):
    with open(fiber_ts) as f:
        fiber_content = f.read()
    match = re.search(r'export const enum FiberState \{(.*?)\}', fiber_content, re.DOTALL)
    if match:
        enum_body = match.group(1)
        enum_items = {}
        current_val = 0
        for line in enum_body.splitlines():
            line = line.strip()
            if not line or line.startswith('//'): continue
            if '=' in line:
                n, v = line.split('=')
                n, v = n.strip().rstrip(','), v.strip().rstrip(',')
                current_val = int(v, 0) if '0x' in v else int(v) if v.isdigit() else current_val
                enum_items[n] = current_val
            else:
                enum_items[line.rstrip(',')] = current_val
            current_val += 1
            
        js_obj = "const FiberState = {\n" + "".join([f"  {k}: {v},\n" for k, v in enum_items.items()]) + "};\n"
        
        with open(profile_boot) as f:
            pb_content = f.read()
        old_imp = "import type { FiberState, Context } from '@deepseek-ai/cordis'"
        new_imp = "import type { Context } from '@deepseek-ai/cordis'\n\n" + js_obj
        if old_imp in pb_content:
            pb_content = pb_content.replace(old_imp, new_imp)
        else:
            old_imp2 = "import { FiberState, type Context } from '@deepseek-ai/cordis'"
            if old_imp2 in pb_content:
                pb_content = pb_content.replace(old_imp2, new_imp)
        with open(profile_boot, 'w') as f:
            f.write(pb_content)

# 6. 500 000 симлинков
pnpm_dir = os.path.join(base, 'node_modules', '.pnpm')
pkg_map = {}
for entry in os.listdir(pnpm_dir):
    if not os.path.isdir(os.path.join(pnpm_dir, entry)): continue
    inner_nm = os.path.join(pnpm_dir, entry, 'node_modules')
    if not os.path.isdir(inner_nm): continue
    for name in os.listdir(inner_nm):
        if name.startswith('@'):
            scope_dir = os.path.join(inner_nm, name)
            if os.path.isdir(scope_dir):
                for sub in os.listdir(scope_dir):
                    pkg_map[f"{name}/{sub}"] = os.path.join(scope_dir, sub)
        else:
            pkg_map[name] = os.path.join(inner_nm, name)

def create_symlinks(target_nm):
    os.makedirs(target_nm, exist_ok=True)
    created = 0
    for full_name, real_path in pkg_map.items():
        if full_name.startswith('@'):
            scope, name = full_name.split('/', 1)
            link_dir = os.path.join(target_nm, scope)
            os.makedirs(link_dir, exist_ok=True)
            link = os.path.join(link_dir, name)
        else:
            link = os.path.join(target_nm, full_name)
        if not os.path.exists(link):
            rel = os.path.relpath(real_path, os.path.dirname(link))
            os.symlink(rel, link)
            created += 1
    return created

total = 0
for sub in ['packages', 'apps']:
    subdir = os.path.join(base, sub)
    if not os.path.isdir(subdir): continue
    for root, dirs, files in os.walk(subdir):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if 'package.json' in files:
            total += create_symlinks(os.path.join(root, 'node_modules'))
total += create_symlinks(os.path.join(base, 'node_modules'))
print(f"[+] Total symlinks: {total}")
