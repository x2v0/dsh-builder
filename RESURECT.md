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

Артефакт собирается. Прогон **45682861933** (commit `1bb2448`) — первый, где install в клоне
`dsh-node-addon-require-builtin` проходит (`--ignore-scripts`), впервые дошли до
`pnpm build:native:napi`.

### Что твёрдо работает (артефакт 45650323936, проверено `file`)

- `system.node` — ARM aarch64, Android 30, NDK r27d ✅
- `esbuild` — **4/4** android-arm64 (0.21.5, 0.25.12, 0.28.1, 0.28.2), `ARM aarch64` ✅
- `@rolldown/binding-android-arm64` — 2 ноды (1.1.1, 1.2.7) ✅
- патчи 02 (`session-persistence`), 05, 10 (`fs-local`) — в артефакте ✅
- `web` больше не падает на esbuild / rolldown

### Что осталось (единственный блокер `web`)

- `require_builtin.node` — собран **x86-64**, лежит в `...-android-arm64/`, лоадер не грузит.
  Плюс дрейф версии: файлы в `0.1.9`, `pnpm` поставил `0.1.10` → `Cannot find module`.
  См. §6.1.

### Ожидание от прогона 45682861933

```
[*] pnpm install --no-frozen-lockfile --ignore-scripts
[*] pnpm build:native:napi (NDK cross-compile)
[arch] ... ARM aarch64
[+] done — version 0.1.10, aarch64
```

Если `[+] done` — скачать артефакт, `file` оба `.node`, **запустить `web`**.

## 6. Известные проблемы

### 6.1 require_builtin x86-64 + version drift

**Симптом:** `dsh: host preparation failed: No usable native binding found for
node-addon-require-builtin-android-arm64 (auto)`. В артефакте `.node` лежит в
`node-addon-require-builtin@0.1.9/build/{nodeabi,napi}/...-android-arm64/`, но `file`
показывает `x86-64`, а лоадер ищет в `0.1.10` → `Cannot find module`.

**Два бага в `build_require_builtin.py`:**
1. `CXX` не переопределён → `build.ts` берёт хост-`c++` → x86-64 в папке `android-arm64/`.
2. Версия захардкожена `0.1.9` → `pnpm install` поставил `0.1.10` → файлы не там, где ищет лоадер.

**Что сделано (commit `1bb2448`):**
- `find_installed_version()` — `glob .pnpm/node-addon-require-builtin@*` → старшая semver.
- `CC`/`CXX`/`AR` → NDK `aarch64-linux-android30-clang(++)` (как в `build_system_node.py`).
- `LDFLAGS`/`CFLAGS`/`CXXFLAGS` = `--target=aarch64-linux-android30 -fPIC`.
- `NARB_TARGET_OS=android`, `NARB_TARGET_ARCH=arm64` — для имени пути в `build.ts`.
- `npm_githead()` — точный коммит из реестра npm; fallback на master.
- `patch_pm_allow_builds()` — `package.json#pnpm.strictDepBuilds=false` + `.npmrc strict-dep-builds=false`.
- `pnpm install --no-frozen-lockfile --ignore-scripts` — обходит `ERR_PNPM_IGNORED_BUILDS` на pnpm<10.3.
- `verify_arch()` — `file | grep aarch64`; **падает**, если не arm64 (раньше копировал молча x86-64).
- Копирует в оба пути (`napi/napi-v9-android-arm64/`, `nodeabi/node-v147-android-arm64/`) **для определённой версии**.

**Остаточные риски:**
- `gitHead` для `0.1.10` = `(none)` → клонируется `master`, а не тег. Если API разойдётся — пин на коммит.
- `build.ts` может иметь `case 'android': throw` — если `pnpm build:native:napi failed`, пришли 20 строк лога.
- NDK env может не дойти до `c++` в spawn — если `[arch] ... x86-64`, жёстко прописать путь в `build.ts`.

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


### 6.6 system.node path mismatch (`bin/bionic/` vs `bin/`)

**Симптом (после require_builtin):** при первом turn — `Cannot find module
'.../node_modules/@deepseek-ai/node-addon-system-android-arm64/bin/system.node'`.

**Причина:** `native/system/packages/entry/lib/flock.js` собирает путь так:
`bin/<libc>/system.node` для linux, `bin/system.node` для остальных. Android в списке
платформ есть (`platform !== 'android'`), но **`bionic` в выборе libc не учтён** — лоадер
ищет `bin/system.node`, а `build_system_node.py` кладёт в `bin/bionic/system.node`.

**Локальный workaround (телефон):** `cp bin/bionic/system.node bin/system.node`.
После этого `flock` грузится, turn идёт дальше.

**CI-фикс:** `patch_flock_path_android.py` — `if (platform === 'android') { filename = join('bionic', filename); }`
перед `if (platform === 'linux')` в `flock.js`, маркер `/* termux-bionic-system-node */`.
Вызов после `Apply Android patches` (как `patch_flock_c.py`).

### 6.7 `rename is not defined` (патч 02 без импорта)

**Симптом:** turn падает с `ReferenceError: rename is not defined`.

**Причина:** `patches/02-session-persistence-link-rename.patch` вставил `await rename(...)`
в `session-persistence-jsonl/lib/index.js` (строки ~2056, ~3349), но `rename` **не импортирован**
из `node:fs/promises` (строка 4 импорта: `link, lstat, mkdir, mkdtemp, open, readFile, readdir, realpath, rm, stat, truncate`).

**Локальный фикс:** `readFile, readdir, realpath, rename,` в импорте `node:fs/promises`.

**CI-фикс:** `patch_session_persistence.py` — добавление `rename` в импорт + вставка fallback
`link → rename` по anchor, маркер `/* termux-link-fallback */`. После `Apply Android patches`.

## 11. Следующий шаг

### 11.1 Если прогон 45682861933 дал `[+] done — version 0.1.10, aarch64`

```bash
cd ~/dsh-builder && gh run download 45682861933 -D ~/dsh-final7
cd ~/dsh-final7 && mkdir -p dsh-test7 && tar -xzf dsh-android-arm64/dsh-android-arm64.tar.gz -C dsh-test7
cd ~/dsh-final7/dsh-test7/dist-artifact
find . -name 'require_builtin.node' | while read f; do printf '%s\t' "$f"; file "$f" | grep -oE 'ARM aarch64|x86-64|Android [0-9]+'; done
```

Ожидаем **оба `ARM aarch64`**. Тогда — запуск:

```bash
cd ~/dsh-final7/dsh-test7/dist-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-dummy"
timeout 120 node --import tsx/esm apps/cli/src/bin.ts web 2>&1 | tee ~/launch5.log
echo "=== exit: $? ==="
grep -n -iE 'ENOSYS|EACCES|Cannot find module|invalid ELF|undefined symbol|koffi|node-pty|require_builtin|sandbox|proot|listening|http://' ~/launch5.log | head -30
tail -40 ~/launch5.log
```

`exit: 124` = сервер живой, ждёт — **цель достигнута**.

### 11.2 Если прогон упал дальше по цепочке

| Симптом в логе | Что делать |
|---|---|
| `pnpm install` OK, `pnpm build:native:napi failed` | 20 строк контекста → патч `build.ts` под `case 'android'` |
| `pnpm install` OK, `[arch] ... x86-64` | NDK env не дошёл → жёстко прописать путь `CXX` в `build.ts` |
| `require_builtin.node not produced` | find-вывод → расширить `candidates` |
| `ERR_PNPM_*` новый | текст в лог → точечный фикс |

### 11.3 После успешного `web` — PR-стратегия

1. PR-1: `fs` hardlink fallback (патч 10).
2. PR-2: `attachment` fallback + durability guard (патч 09, доделать).
3. PR-3: `session-persistence` fallback (патч 02).
4. PR-4: `koffi` `statx` bionic (`koffi-statx.patch`).
5. PR-5: `require_builtin` Android (`require-builtin-android.patch`).

### 11.4 Открытые вопросы (не блокеры `web`)

- `koffi`/`node-pty` — linux-x64/linux-arm64 prebuilt. Проверить при загрузке; если падают — NDK из src или отключить.
- Патч 09 (`attachment`) — anchor drift; писать как `patch_attachment_link.py` (по образцу `patch_flock_c.py`).
- `sandbox-local` без proot — отключить для Android или нативный путь (proot запрещён, §6.5).

