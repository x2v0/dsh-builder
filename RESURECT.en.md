# RESURECT.en.md — reviving dsh-builder from scratch

**[🇷🇺 Русский](RESURECT.md) | [🇬🇧 English](RESURECT.en.md) | [🇨🇳 中文](RESURECT.zh.md)**


> If the dialog/context is lost — read this file and continue from where you left off.
> All commands in Termux (`~/`), not in `/tmp` (RULE #555).

## 0. What we are building

The DSH artifact for Android/Termux, built **fully in GitHub Actions**, run **without manual edits** with the command:

```bash
cd <dist-artifact>
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-dummy"
node --import tsx/esm apps/cli/src/bin.ts web
```

Repository: `x2v0/dsh-builder` (`~/dsh-builder`). DSH sources are checked out in CI from `deepseek-ai/deepseek-harness`.

## 1. Structure (what should be)

```
~/dsh-builder/
├── .github/workflows/build-dsh.yml
├── patches/
│   ├── 01-terminal-bash-android-shell.patch
│   ├── 02-session-persistence-link-rename.patch
│   ├── 03-subprocess-local-android.patch
│   ├── 04-host-apiproxy-termux-open-{index,opener}.patch
│   ├── 05-host-directory-picker-native-android.patch
│   ├── 06-workspace-archive-skip-session-known-check.patch
│   ├── 07-sandbox-local-proot-runner.patch
│   ├── 08-dsh-tool-fs-search-android-rg.patch
│   ├── 09-attachment-local-link-rename.patch
│   ├── 10-fs-local-link-rename.patch
│   ├── koffi-statx.patch
│   └── require-builtin-android.patch
├── scripts/
│   ├── apply_patches.sh              # v2: packages/<group>/<name>/
│   ├── build_system_node.py          # NDK r27d, arm64 Android30 (WORKS)
│   ├── build_require_builtin.py      # BROKEN: x86-64 (see §6.1)
│   ├── install_android_build_tools.py
│   ├── patch_flock_ts.py
│   ├── patch_flock_c.py
│   └── patch_fiberstate.py
├── GOALS.md, RULES.md, RESURECT.md
```

## 2. Key fact: DSH is a workspace monorepo

Packages: **`packages/<group>/<name>/`**, NOT `node_modules/@deepseek-ai/dsh-*-local`.

| Package | Path | main |
|---|---|---|
| terminal-bash | packages/terminal/terminal-bash | lib/index.js |
| session-persistence-jsonl | packages/session/session-persistence-jsonl | lib/index.js |
| subprocess-local | packages/subprocess/subprocess-local | lib/index.js |
| directory-picker-native | packages/host/directory-picker-native | lib/index.js |
| workspace | packages/workspace/workspace | lib/index.js |
| sandbox-local | packages/sandbox/sandbox-local | lib/index.js |
| tool-fs-search | packages/fs/tool-fs-search | lib/index.js |
| attachment-local | packages/attachment/attachment-local | lib/index.js |
| fs-local | packages/fs/fs-local | lib/index.js |
| open-in-app (opener, former apiproxy) | packages/host/open-in-app | lib/index.js |

**Patch `lib/index.js`**, NOT `src/*.ts`: `tsx` loads `exports` -> `lib/`.

## 3. Step order in build-dsh.yml (critical)

```
1. Checkout DSH Source (deepseek-ai/deepseek-harness)
2. Checkout dsh-builder -> path: builder
3. Setup Node.js (24)
4. Patch flock for Android (patch_flock_ts.py)
5. Install Dependencies:
     npm install -g pnpm
     pnpm install --no-frozen-lockfile --config.supportedArchitectures='{"os":["android"],"cpu":["arm64"]}'
6. Install Android-native build tools (install_android_build_tools.py)
7. Build DSH: build:lib:host, build:lib:client, build:web, build:native-system
8. Apply Android patches   <-- AFTER build:*
9. Patch FiberState (patch_fiberstate.py)
10. Patch flock.c (patch_flock_c.py)
11. Build system.node (build_system_node.py) — WORKS
12. Build require_builtin.node (build_require_builtin.py) — x86-64 (broken)
13. Package Artifact
14. Upload Artifact (dsh-android-arm64.tar.gz)
```

**Key:** `Apply Android patches` AFTER `Build DSH` (otherwise the build overwrites `lib/`).

## 4. Verified facts

- `build_system_node.py` -> `system.node` = arm64, Android 30, NDK r27d, NEEDED libc.so+libdl.so. Works.
- `require_builtin` = x86-64 glibc (both before and after our edits). Broken NOT by our commit.
- `koffi`, `node-pty`, `esbuild`, `rolldown` in artifact = linux-x64.
- `--config.supportedArchitectures` + `--no-frozen-lockfile` in pnpm install — no effect.
- `apply_patches.sh` v1 searched in `node_modules/@deepseek-ai/` — wrong (workspace-layout). v2 -> `packages/`.
- Patches 09/10 anchors verified by grep: attachment-local (open/link lines 362,481,542,548), fs-local (linkFile line 568).
- `install.sh` (~/dsh-termux/) — reference manual install (link->rename steps 5/6/8, flock->fcntl, node-gyp delete variables.OS).

## 5. Current state

**DSH is fully functional on Android/Termux.** Artifact `45725287927` is self-contained:
download -> unpack -> run -> works. All native modules and path-fixes are built in CI.

### What firmly works (artifact 45725287927)

- `system.node` — ARM aarch64, Android 30, NDK r27d, `flock.js` looks into `bin/bionic/` ✅
- `esbuild` — 4/4 android-arm64 (0.21.5, 0.25.12, 0.28.1, 0.28.2) ✅
- `@rolldown/binding-android-arm64` — 2 nodes (1.1.1, 1.2.7) ✅
- `require_builtin.node` — ARM aarch64, Android 30, product `require-builtin` ✅
- Patches 02, 05, 10 — in artifact ✅
- `session-persistence-jsonl` — `rename` added to import (`patch_session_persistence.py`) ✅
- `flock.js` — path to `system.node` fixed for Android (`patch_flock_path_android.py`) ✅
- **`web`** — starts, UI opens (127.0.0.1), key valid (2 models loaded) ✅
- **`turn`** — reaches DeepSeek API (response or `QUOTA` without balance) ✅
