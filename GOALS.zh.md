# 项目目标

**[🇷🇺 Русский](GOALS.md) | [🇬🇧 English](GOALS.en.md) | [🇨🇳 中文](GOALS.zh.md)**


## 1. 主要目标
在 Android 上**完全从 GitHub Actions** 运行 DSH (DeepSeek Harness)，无需在手机上
手动打补丁。构建产物可复现：下载 -> 解包 -> 运行。

## 2. 技术目标
在 YAML 中构建**所有 Android 原生模块**（`flock` 的 `system.node`、`require_builtin.node`、
`koffi`、`node-pty`、`esbuild`），以避免 `ENOSYS`、`EACCES`、`Cannot find module`。

## 3. 基础设施目标
YAML **干净**：逻辑在 `scripts/*.py` 中，而不是 heredoc。脚本幂等，带 `cd`（规则 #1），
无正则（规则 #11），带备份（规则 #2）。

## 4. 对 DSH 的最小改动
遵循原则 **"DSH — everything is plugin"**。不要不必要地修改核心；
如果可以通过插件添加功能 — 通过插件添加。

## 5. 无二进制预构建
一切都在 GitHub Actions 上从源代码构建。`dsh-builder` 仓库中没有现成的
`.node`/`.so`/`esbuild` — 只有 `scripts/` 和 `patches/`。

## 6. 对未来变化的灵活性
我们的系统必须能在 DSH 和其他我们从 `src` 构建的包更新后继续工作。因此：
- 补丁 — **按锚点**（不是按行号）；
- 脚本 — **幂等**（重复运行不会破坏）；
- 没有可能改变的硬编码路径（或它们集中在一个地方）。

## 7. 上游目标
将我们的更改添加到 DSH 主分支（`deepseek-ai/deepseek-harness`）。不要永远保留分支。
补丁必须**干净、最小且可解释**，以便可以提供到上游（PR）。
对于 `dsh-node-addon-require-builtin` 和其他上游包也是如此。

## 分离：patches 与 scripts

### `patches/*.patch` — 进入上游的内容
- `koffi-statx.patch` — Android/bionic 在 API 30 之前没有 `statx()`。
- `require-builtin-android.patch` — Android/bionic 的 `platform.cc`（锚点：`__linux__ && __GLIBC__ && __aarch64__` -> `__linux__ && __aarch64__`）。
- `01-terminal-bash-android-shell.patch` ... `08-dsh-tool-fs-search-android-rg.patch` — DSH 中的 Android 特定修复。
- 所有补丁 — `git apply` 格式，最小化，在注释中带解释。

### `scripts/*.py` — 本地内容（为 Android 构建）
- `build_system_node.py` — 通过 NDK 编译 `flock.c`。
- `build_require_builtin.py` — 构建 `require_builtin.node`（带 `platform.cc` 和 `build.ts` 的锚点）。
- `install_android_build_tools.py` — `@esbuild/android-arm64`、`@rolldown/binding-android-arm64`。
- `patch_flock_ts.py` — `flock.ts`：`&& platform !== 'android'`。
- `patch_flock_c.py` — `flock.c`：`flock()` -> `fcntl()`（bionic 的 fallback）。
- `patch_fiberstate.py` — `FiberState.ACTIVE -> 2`（workaround，因为 `const enum` 被擦除）。
- `apply_patches.sh` — 通过 `git apply` 应用 `patches/*.patch`。

### 不进入上游的内容
- `FiberState.ACTIVE -> 2` — 这是一个**本地 workaround**（TypeScript `const enum` 在编译时被擦除；
  `profile-boot.ts` 期望运行时值）。在上游应该以不同方式解决
  （例如，`export const FiberState = {...} as const`）。目前 — 在 `scripts/` 中。
