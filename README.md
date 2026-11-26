# dsh-builder

Сборка [DSH (DeepSeek Harness)](https://github.com/deepseek-ai/deepseek-harness)
под **Android / Termux**, полностью в **GitHub Actions**, без ручных патчей
на телефоне. Артефакт воспроизводим: скачал -> распаковал -> запустил.

> Это **не форк DSH**. Репозиторий содержит только патчи (`patches/`) и
> скрипты сборки (`scripts/`). Исходники DSH чекаутятся в CI из
> `deepseek-ai/deepseek-harness`.

## 📖 Подробная инструкция

Если вы впервые видите этот проект или хотите понять, как устроен пайплайн
(что такое GitHub Actions, как править YAML, как запускать и проверять сборку),
читайте **[GUIDE.md](GUIDE.md)**.

Краткая шпаргалка:
*   `gh workflow run build-dsh.yml` — запустить сборку.
*   `gh run watch` — следить за прогрессом.
*   `gh run download <ID>` — скачать готовый артефакт.

---

Сборка [DSH (DeepSeek Harness)](https://github.com/deepseek-ai/deepseek-harness)
под **Android / Termux**, полностью в **GitHub Actions**, без ручных патчей
на телефоне. Артефакт воспроизводим: скачал -> распаковал -> запустил.

> Это **не форк DSH**. Репозиторий содержит только патчи (`patches/`) и
> скрипты сборки (`scripts/`). Исходники DSH чекаутятся в CI из
> `deepseek-ai/deepseek-harness`.

## Быстрый старт

```bash
cd ~/dsh-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-..."
node --import tsx/esm apps/cli/src/bin.ts web
```

### Что такое `workflow.yaml`?

Это файл `.github/workflows/build-dsh.yml`. Он говорит GitHub Actions:
*   **Когда** запускаться (`workflow_dispatch` — вручную, `push` — при коммите).
*   **Что делать** (шаги: Checkout, Install, Build, Patch, Package).
*   **Куда** положить результат (артефакт `dsh-android-arm64.tar.gz`).

### Что такое `git push`?

`git push` отправляет ваши локальные коммиты на GitHub. После этого
GitHub Actions может автоматически запустить сборку (если в YAML есть `on: push`).
Если автоматического запуска нет — используйте `gh workflow run build-dsh.yml`.

## Текущий статус

**Артефакт `45725287927` — полностью самодостаточен.** Скачал → распаковал → запустил → работает.
Никаких ручных `cp`/`patch` не требуется.

| Шаг | Статус |
|---|---|
| `system.node` (NDK r27d, `bin/bionic/`) | ✅ ARM aarch64, Android 30 |
| `esbuild` (4 версии) | ✅ ARM aarch64 |
| `@rolldown/binding-android-arm64` (2 версии) | ✅ ARM aarch64 |
| `require_builtin.node` | ✅ ARM aarch64, product `require-builtin` |
| Патчи 02 / 05 / 10 | ✅ в артефакте |
| Патч 09 (attachment) | ⚠️ anchor drift (не блокер для `web`) |
| `flock.js` bionic path | ✅ `patch_flock_path_android.py` |
| `session-persistence` rename | ✅ `patch_session_persistence.py` |
| **`web`** | ✅ стартует, UI открывается, ключ валиден (2 модели) |
| **`turn` (LLM)** | ✅ доходит до API (`QUOTA` — только без баланса) |

Подробно — [RESURECT.md](RESURECT.md) §5, §6.1, §6.6, §6.7, §11.

## Артефакт

DSH `0.2.3-alpha.2` (`@deepseek-ai/dsh-root`), платформа android-arm64
(Termux, bionic), Node.js 24 в CI, NDK r27d (target android30).

| Метрика | Значение |
|---|---|
| Размер tar.gz | 735 MB |
| Размер распакованного | 4.3 GB |
| из них `node_modules` | 2.3 GB |
| `packages/` | 354 MB |
| `apps/` | 47 MB |
| Всего файлов | 116 506 |
| без `node_modules` | 31 012 |
| `.ts` файлов | 9 990 |
| `.js` файлов | 4 388 |
| `.json` файлов | 3 680 |
| `.node` модулей | 49 |
| TS LOC | 1 582 225 |
| JS LOC | 1 553 256 |
| Workspace-пакетов | 397 в 57 группах |
| Apps | `cli`, `desktop`, `desktop-host`, `desktop-publisher`, `plugin-market-generator`, `web` |


## Структура репозитория

```
dsh-builder/
├── .github/workflows/build-dsh.yml
├── patches/             # Android-фиксы для upstream (git apply)
│   ├── 01..10-*.patch
│   ├── koffi-statx.patch
│   └── require-builtin-android.patch
├── scripts/             # локальная сборка под Android
│   ├── apply_patches.sh              # v2: packages/<group>/<name>/
│   ├── build_system_node.py          # NDK r27d -> system.node (arm64)
│   ├── build_require_builtin.py      # NARB_TARGET_OS/ARCH (фикс в работе)
│   ├── install_android_build_tools.py # @esbuild/@rolldown android-arm64
│   ├── patch_flock_ts.py             # flock.ts: platform !== 'android'
│   ├── patch_flock_c.py              # flock() -> fcntl()
│   ├── patch_flock_path_android.py   # flock.js: android -> bin/bionic/system.node
│   ├── patch_session_persistence.py  # rename в импорт node:fs/promises
│   └── patch_fiberstate.py           # FiberState.ACTIVE -> 2
├── GOALS.md
├── RULES.md
├── RESURECT.md
└── README.md
```

## Пайплайн `build-dsh.yml` (16 шагов)

| # | Шаг | Что делает |
|---|---|---|
| 1 | Checkout DSH Source | `deepseek-ai/deepseek-harness` |
| 2 | Checkout dsh-builder | `scripts/` + `patches/` -> `builder/` |
| 3 | Setup Node.js | 24 |
| 4 | Patch flock for Android | `patch_flock_ts.py` |
| 5 | Install Dependencies | `pnpm install --no-frozen-lockfile` |
| 6 | Install Android-native build tools | `install_android_build_tools.py` |
| 7 | Build DSH | `build:lib:host`, `build:lib:client`, `build:web`, `build:native-system` |
| 8 | Apply Android patches | `apply_patches.sh` — **после** `build:*` |
| 9 | Patch FiberState | `patch_fiberstate.py` |
| 10 | Patch flock.c | `patch_flock_c.py` (`flock` -> `fcntl`) |
| 11 | Patch flock.js path | `patch_flock_path_android.py` (android -> `bin/bionic/`) |
| 12 | Patch session-persistence | `patch_session_persistence.py` (`rename` в импорт) |
| 13 | Build system.node | NDK r27d -> ARM aarch64 |
| 14 | Build require_builtin.node | NDK cross-compile, `NARB_PRODUCT=require-builtin` |
| 15 | Package Artifact | `dsh-android-arm64.tar.gz` |
| 16 | Upload Artifact | `gh run download <id>` |

## Документы

- [GOALS.md](GOALS.md) — 7 целей проекта.
- [RULES.md](RULES.md) — правила правок (#0–#555).
- [RESURECT.md](RESURECT.md) — состояние, как продолжить с нуля.
