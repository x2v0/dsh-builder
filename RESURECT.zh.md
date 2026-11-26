# RESURECT.zh.md — 从头恢复 dsh-builder

> 如果对话/上下文丢失 — 阅读此文件并从您离开的地方继续。
> 所有命令在 Termux (`~/`) 中，不在 `/tmp` 中（规则 #555）。

## 0. 我们在构建什么

用于 Android/Termux 的 DSH 构建产物，**完全在 GitHub Actions 中构建**，使用以下命令
**无需手动编辑**即可运行：

```bash
cd <dist-artifact>
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-dummy"
node --import tsx/esm apps/cli/src/bin.ts web
```

仓库：`x2v0/dsh-builder` (`~/dsh-builder`)。DSH 源代码在 CI 中从 `deepseek-ai/deepseek-harness` 检出。

## 1. 结构（应该是什么）

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
│   ├── build_system_node.py          # NDK r27d, arm64 Android30 (工作)
│   ├── build_require_builtin.py      # 损坏：x86-64（见 §6.1）
│   ├── install_android_build_tools.py
│   ├── patch_flock_ts.py
│   ├── patch_flock_c.py
│   └── patch_fiberstate.py
├── GOALS.md, RULES.md, RESURECT.md
```

## 2. 关键事实：DSH 是 workspace 单仓库

包：**`packages/<group>/<name>/`**，不是 `node_modules/@deepseek-ai/dsh-*-local`。

| 包 | 路径 | main |
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
| open-in-app（opener，原 apiproxy） | packages/host/open-in-app | lib/index.js |

**补丁 `lib/index.js`**，不是 `src/*.ts`：`tsx` 加载 `exports` -> `lib/`。

## 3. build-dsh.yml 中的步骤顺序（关键）

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
8. Apply Android patches   <-- 在 build:* 之后
9. Patch FiberState (patch_fiberstate.py)
10. Patch flock.c (patch_flock_c.py)
11. Build system.node (build_system_node.py) — 工作
12. Build require_builtin.node (build_require_builtin.py) — x86-64（损坏）
13. Package Artifact
14. Upload Artifact (dsh-android-arm64.tar.gz)
```

**关键：** `Apply Android patches` 在 `Build DSH` **之后**（否则构建会覆盖 `lib/`）。

## 4. 已验证的事实

- `build_system_node.py` -> `system.node` = arm64, Android 30, NDK r27d, NEEDED libc.so+libdl.so。工作。
- `require_builtin` = x86-64 glibc（我们的编辑前后都是）。不是我们的提交导致的损坏。
- `koffi`、`node-pty`、`esbuild`、`rolldown` 在构建产物中 = linux-x64。
- `--config.supportedArchitectures` + `--no-frozen-lockfile` 在 pnpm install 中 — 无效果。
- `apply_patches.sh` v1 在 `node_modules/@deepseek-ai/` 中搜索 — 错误（workspace-layout）。v2 -> `packages/`。
- 补丁 09/10 锚点通过 grep 验证：attachment-local（open/link 行 362,481,542,548），fs-local（linkFile 行 568）。
- `install.sh` (~/dsh-termux/) — 参考手动安装（link->rename 步骤 5/6/8，flock->fcntl，node-gyp delete variables.OS）。

## 5. 当前状态

**DSH 在 Android/Termux 上完全可用。** 构建产物 `45725287927` 是自包含的：
下载 -> 解包 -> 运行 -> 工作。所有原生模块和路径修复都在 CI 中构建。

### 稳定工作的部分（构建产物 45725287927）

- `system.node` — ARM aarch64, Android 30, NDK r27d, `flock.js` 查找 `bin/bionic/` ✅
- `esbuild` — 4/4 android-arm64 (0.21.5, 0.25.12, 0.28.1, 0.28.2) ✅
- `@rolldown/binding-android-arm64` — 2 个节点 (1.1.1, 1.2.7) ✅
- `require_builtin.node` — ARM aarch64, Android 30, product `require-builtin` ✅
- 补丁 02、05、10 — 在构建产物中 ✅
- `session-persistence-jsonl` — `rename` 添加到导入（`patch_session_persistence.py`）✅
- `flock.js` — 为 Android 修复了 `system.node` 的路径（`patch_flock_path_android.py`）✅
- **`web`** — 启动，UI 打开 (127.0.0.1)，密钥有效（加载了 2 个模型）✅
- **`turn`** — 到达 DeepSeek API（响应或 `QUOTA` 无余额）✅
