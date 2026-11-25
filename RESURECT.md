# RESURECT.md — возрождение dsh-builder с нуля

> Если диалог/контекст потерян — прочитай этот файл и продолжи с того места.
> Все команды в Termux (`~/`), не в `/tmp` (RULE #555).

## 0. Что строим

Артефакт DSH для Android/Termux, собираемый **полностью в GitHub Actions**, запускаемый **без ручных правок** командой:

```bash
cd <dist-artifact>
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-dummy"
node --import tsx/esm apps/cli/src/bin.ts web
```

Репозиторий: `x2v0/dsh-builder` (`~/dsh-builder`). DSH-исходники чекаутятся в CI из `deepseek-ai/deepseek-harness`.

## 1. Структура (что должно быть)

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
│   ├── build_system_node.py          # NDK r27d, arm64 Android30 (РАБОТАЕТ)
│   ├── build_require_builtin.py      # СЛОМАН: x86-64 (см. §6.1)
│   ├── install_android_build_tools.py
│   ├── patch_flock_ts.py
│   ├── patch_flock_c.py
│   └── patch_fiberstate.py
├── GOALS.md, RULES.md, RESURECT.md
```

## 2. Ключевой факт: DSH — workspace-монорепо

Пакеты: **`packages/<group>/<name>/`**, НЕ `node_modules/@deepseek-ai/dsh-*-local`.

| Пакет | Путь | main |
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
| open-in-app (opener, быв. apiproxy) | packages/host/open-in-app | lib/index.js |

**Патчить `lib/index.js`**, НЕ `src/*.ts`: `tsx` грузит `exports` -> `lib/`.

## 3. Порядок шагов в build-dsh.yml (критично)

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
8. Apply Android patches   <-- ПОСЛЕ build:*
9. Patch FiberState (patch_fiberstate.py)
10. Patch flock.c (patch_flock_c.py)
11. Build system.node (build_system_node.py) — РАБОТАЕТ
12. Build require_builtin.node (build_require_builtin.py) — x86-64 (сломан)
13. Package Artifact
14. Upload Artifact (dsh-android-arm64.tar.gz)
```

**Ключ:** `Apply Android patches` ПОСЛЕ `Build DSH` (иначе сборка затирает `lib/`).

## 4. Проверенные факты

- `build_system_node.py` -> `system.node` = arm64, Android 30, NDK r27d, NEEDED libc.so+libdl.so. Работает.
- `require_builtin` = x86-64 glibc (и до, и после наших правок). Сломан НЕ нашим коммитом.
- `koffi`, `node-pty`, `esbuild`, `rolldown` в артефакте = linux-x64.
- `--config.supportedArchitectures` + `--no-frozen-lockfile` в pnpm install — эффекта не дал.
- `apply_patches.sh` v1 искал в `node_modules/@deepseek-ai/` — неверно (workspace-layout). v2 -> `packages/`.
- Патчи 09/10 анкоры сверены grep: attachment-local (open/link строки 362,481,542,548), fs-local (linkFile строка 568).
- `install.sh` (~/dsh-termux/) — эталон ручной установки (link->rename шаги 5/6/8, flock->fcntl, node-gyp delete variables.OS).

## 5. Текущее состояние

- Коммит `702173b` — `ci: resolve android-arm64 natives via supportedArchitectures`.
- Изменены `build-dsh.yml`, `apply_patches.sh`; добавлены `patches/09`, `patches/10`.
- Прогон `45567769814` — проверка, что патчи 09/10 легли.
- Следующий шаг: дождаться, посмотреть `Apply Android patches` лог, скачать артефакт, проверить `grep -c 'termux-hardlink-fallback'`.

## 6. Известные проблемы

### 6.1 require_builtin x86-64
`build_require_builtin.py` собирает под хост. Причина: не экспортирует `NARB_TARGET_OS=android NARB_TARGET_ARCH=arm64` в `subprocess.run(env=...)`. Фикс: добавить env. Сверить с коммитами `4845404`/`e6aed72`.

### 6.2 koffi/node-pty/esbuild/rolldown linux-x64
pnpm резолвит под хост. Варианты: (A) NDK + npm install из src (CFLAGS=--target=aarch64-linux-android30, патч node-gyp delete variables.OS); (B) prebuilt @koromix/koffi-android-arm64@3.3.8 (нарушает GOAL #5). Сначала проверить, грузятся ли при `tsx apps/cli/src/bin.ts web`.

### 6.3 Патчи 04 (opener)
Анкоры под старый host-apiproxy. Сейчас opener в packages/host/open-in-app. Переписать (не блокер для web).

### 6.4 nolink.so (удалён)
Был LD_PRELOAD-затычкой для link(). Правильно — патчи 09/10 (link->rename). Не тащить в артефакт.

## 7. Как продолжить с нуля

### 7.1 Если артефакт успешен
```bash
cd ~/dsh-builder && gh run download <id> -D ~/dsh-final3
cd ~/dsh-final3 && mkdir -p dsh-test3 && tar -xzf dsh-android-arm64/dsh-android-arm64.tar.gz -C dsh-test3
cd ~/dsh-final3/dsh-test3/dist-artifact
grep -c 'termux-hardlink-fallback' packages/attachment/attachment-local/lib/index.js
grep -c 'termux-noreplace-fallback' packages/fs/fs-local/lib/index.js
```

### 7.2 Если 09/10 [SKIP]
`@@`-номера не совпали. Прислать `grep -n 'link(\|fsync\|O_RDONLY' packages/attachment/attachment-local/lib/index.js` и поправить анкоры через `python3 - << 'EOF'`.

### 7.3 Пересборка
```bash
cd ~/dsh-builder && git add -A && git commit -m "..." && git push
cd ~/dsh-builder && gh run list --limit 1 --json databaseId,status,conclusion
cd ~/dsh-builder && gh run view <id> --log | grep -E '\[OK\]|\[SKIP\]|\[WARN\]'
```

### 7.4 Диагностика .node
```bash
find . -name '*.node' | while read f; do printf '%s\t' "$f"; file "$f" | grep -oE 'ARM aarch64|x86-64|Android [0-9]+|NDK r[0-9a-z]+'; done
```

## 8. Правила (нельзя нарушать)

- #0: патчи файлов — только `python3 - << 'EOF'`.
- #1: `cd` первой строкой.
- #2: без regex; идемпотентно; бэкапы (не коммитить).
- #3: диагностировать (`ls`, `grep`, `file`, `readelf`), не гадать.
- #4: расширять, не заменять.
- #5: один шаг — один вывод.
- #12: текстовые файлы — python add line, построчно.
- #555: всё в `~/`, не `/tmp`.
- GOAL #5: никаких prebuilt в репо.
- GOAL #7: патчи чистые, анкорные, upstream.

## 9. Шпаргалка

```bash
cd ~/dsh-builder && git log --oneline -10 && git status --short
cd ~/dsh-builder && gh run list --limit 10 --json databaseId,headSha,status,conclusion
cd ~/dsh-builder && gh run view <id> --log > ~/run<id>.log 2>&1
cd ~/dsh-builder && grep -n -iE '\[OK\]|\[SKIP\]|\[WARN\]|error|failed' ~/run<id>.log | head -60
```

## 10. История ключевых решений

- `702173b` — pnpm supportedArchitectures (не дал эффекта, не сломал).
- Патчи `patches/*` были под старый layout (`node_modules/@deepseek-ai/dsh-*-local`).
- Текущий DSH — workspace-монорепо (`packages/<group>/<name>/`).
- `apply_patches.sh` v2 -> `packages/`.
- `apply_patches` ПОСЛЕ `build:*`.
- `link`->`rename` (09/10) вместо `nolink.so`.

---

**Начни с §4 (факты) и §7 (как продолжить). Не гадай, диагностируй.**

### 6.5 proot запрещён
Никакого `proot`. Всё нативно в Termux. Патч `07-sandbox-local-proot-runner.patch` **отключён** (закомментирован в `apply_patches.sh`). Если `sandbox-local` падает при `web` без proot — либо отключить sandbox на Android, либо дать нативный путь (без proot). В upstream `proot` не идёт.

