# Project Goals

**[🇷🇺 Русский](GOALS.md) | [🇬🇧 English](GOALS.en.md) | [🇨🇳 中文](GOALS.zh.md)**


## 1. Main Goal
Run DSH (DeepSeek Harness) on Android **fully from GitHub Actions**, without manual patches
on the phone. The artifact is reproducible: download -> unpack -> run.

## 2. Technical Goal
Build in YAML **all native modules for Android** (`system.node` for `flock`, `require_builtin.node`,
`koffi`, `node-pty`, `esbuild`), to avoid `ENOSYS`, `EACCES`, `Cannot find module`.

## 3. Infrastructure Goal
YAML **clean**: logic in `scripts/*.py`, not in heredocs. Scripts are idempotent, with `cd` (rule #1),
no regex (rule #11), with backups (rule #2).

## 4. Minimal Changes to DSH
Follow the principle **"DSH — everything is plugin"**. Do not patch the core without necessity;
if functionality can be added via a plugin — add via plugin.

## 5. No Binary Prebuilds
Everything is built from source on GitHub Actions. There are no ready-made `.node`/`.so`/`esbuild`
in the `dsh-builder` repository — only `scripts/` and `patches/`.

## 6. Flexibility for Future Changes
Our system must survive updates of DSH and other packages we build from `src`. Therefore:
- patches — **by anchors** (not by line numbers);
- scripts — **idempotent** (repeated runs do not break);
- no hardcoded paths that may change (or they are centralized in one place).

## 7. Upstream Goal
Add our changes to the main DSH branch (`deepseek-ai/deepseek-harness`). Do not keep a fork forever.
Patches must be **clean, minimal, and explainable** so they can be offered upstream (PR).
Same — for `dsh-node-addon-require-builtin` and other upstream packages.

## Separation: patches vs scripts

### `patches/*.patch` — what goes upstream
- `koffi-statx.patch` — Android/bionic has no `statx()` before API 30.
- `require-builtin-android.patch` — `platform.cc` for Android/bionic (anchors: `__linux__ && __GLIBC__ && __aarch64__` -> `__linux__ && __aarch64__`).
- `01-terminal-bash-android-shell.patch` ... `08-dsh-tool-fs-search-android-rg.patch` — Android-specific fixes in DSH.
- All patches — in `git apply` format, minimal, with explanation in comments.

### `scripts/*.py` — what is local (build for Android)
- `build_system_node.py` — compile `flock.c` via NDK.
- `build_require_builtin.py` — build `require_builtin.node` (with anchors for `platform.cc` and `build.ts`).
- `install_android_build_tools.py` — `@esbuild/android-arm64`, `@rolldown/binding-android-arm64`.
- `patch_flock_ts.py` — `flock.ts`: `&& platform !== 'android'`.
- `patch_flock_c.py` — `flock.c`: `flock()` -> `fcntl()` (fallback for bionic).
- `patch_fiberstate.py` — `FiberState.ACTIVE -> 2` (workaround because `const enum` is erased).
- `apply_patches.sh` — applies `patches/*.patch` via `git apply`.

### What does NOT go upstream
- `FiberState.ACTIVE -> 2` — this is a **local workaround** (TypeScript `const enum` is erased on compile;
  `profile-boot.ts` expects a runtime value). In upstream this should be solved differently
  (e.g., `export const FiberState = {...} as const`). For now — in `scripts/`.
