# dsh-builder

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

## Текущий статус

| Шаг | Статус |
|---|---|
| `system.node` (NDK r27d) | ✅ ARM aarch64 |
| `esbuild` (4 версии) | ✅ ARM aarch64 |
| `@rolldown/binding-android-arm64` (2 версии) | ✅ ARM aarch64 |
| `require_builtin.node` | ✅ ARM aarch64 (Android 30, NDK r27d), product `require-builtin` (прогон `45704335477`) |
| Патчи 02 / 05 / 10 | ✅ в артефакте |
| Патч 09 (attachment) | ⏳ anchor drift |
| `system.node` path | ✅ локальный фикс (`bin/bionic/` → `bin/`); CI-патч (§6.6) в работе |
| `rename is not defined` | ⏳ патч 02 добавил `rename()` без импорта — фикс в работе (§6.7) |
| `web` на телефоне | ✅ стартует, UI открывается, ключ валиден (модели загружаются) |

Подробно — [RESURECT.md](RESURECT.md) §5, §6.1, §11.

## Артефакт

DSH `0.2.3-alpha.2` (`@deepseek-ai/dsh-root`), платформа android-arm64
(Termux, bionic), Node.js 24 в CI, NDK r27d (target android30).

| Метрика | Значение |
|---|---|
| Размер tar.gz | 735 MB |
| Размер распакованного | 2.7 GB |
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

### Нативные `.node` модули

| Модуль | Arch | Статус |
|---|---|---|
| `system.node` | ARM aarch64 (Android 30, NDK r27d), `bionic/` path | ✅ |
| `require_builtin` | ARM aarch64 (Android 30, NDK r27d), product `require-builtin` | ✅ |
| `node-pty` | ARM aarch64 (`linux-arm64`, не android) | ⚠️ TBD |
| `koffi` | x86-64 (`linux-x64`) | ❌ нет android-сборки |
| `esbuild` | ARM aarch64 (4/4: 0.21.5, 0.25.12, 0.28.1, 0.28.2) | ✅ |
| `rolldown` | ARM aarch64 (`binding-android-arm64`, 2 версии) | ✅ |

**`require_builtin`:** прогон `45704335477` — ✅ `ARM aarch64, Android 30, NDK r27d`,
product `require-builtin` (было `internal-loader`). Фикс — `NARB_PRODUCT=require-builtin`
в `build_require_builtin.py` + fail-closed `verify_product()` (`strings | grep`).
Продукт `internal-loader` собирался по дефолту `build.ts` upstream.

**`esbuild`:** `install_android_build_tools.py` переписан (коммит `f5c149f`) —
теперь ставит `@esbuild/android-arm64@<ver>` в `node_modules` каждой
из 4 версий esbuild в `.pnpm` (0.21.5, 0.25.12, 0.28.1, 0.28.2).
До фикса `pnpm` резолвил под хост (`linux-x64`), `web` падал на старте.

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
│   └── patch_fiberstate.py           # FiberState.ACTIVE -> 2
├── GOALS.md
├── RULES.md
├── RESURECT.md
└── README.md
```

## Пайплайн `build-dsh.yml` (14 шагов)

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
| 11 | Build system.node | NDK r27d |
| 12 | Build require_builtin.node | arm64 (фикс в работе) |
| 13 | Package Artifact | `dsh-android-arm64.tar.gz` |
| 14 | Upload Artifact | `gh run download <id>` |

**Ключ:** шаг 8 (`Apply Android patches`) идёт **после** шага 7 (`Build DSH`),
иначе сборка затирает `lib/`. Патчим `lib/index.js`, не `src/*.ts`
(`tsx` грузит `exports` -> `lib/`).

## Статус патчей

| Патч | Пакет | Статус |
|---|---|---|
| 02 session-persistence | `rename(tmp, finalPath)` | ✅ в артефакте |
| 05 directory-picker-native | native Android | ✅ |
| 09 attachment-local | `link()` -> `rename()` fallback | ⚠️ в работе (anchor drift) |
| 10 fs-local | `link()` -> `rename()` fallback | ✅ в артефакте |
| 01 terminal-bash | android shell | ⏭ `[SKIP]` (устаревший анкор) |
| 03 subprocess-local | android | ⏭ `[SKIP]` |
| 04 open-in-app | opener | ⏭ `[SKIP]` (переехал) |
| 06 workspace-archive | skip session-known | ⏭ `[SKIP]` |
| 07 sandbox-local proot | **отключён** (proot запрещён) | ⏭ |
| 08 tool-fs-search | android rg | ⏭ `[SKIP]` |

Известные проблемы — [RESURECT.md](RESURECT.md) §6.

## Цели ([GOALS.md](GOALS.md))

1. **Всё в CI** — артефакт собирается в GitHub Actions, без ручных правок на телефоне.
2. **Всё нативное** — `system.node`, `require_builtin.node`, `koffi`, `node-pty`, `esbuild` — под android-arm64.
3. **YAML чистый** — логика в `scripts/*.py`, не в heredoc'ах.
4. **DSH — everything is plugin** — минимум изменений ядра, предпочитаем плагины.
5. **Никаких prebuilt в репо** — только `scripts/` и `patches/`.
6. **Гибкость** — патчи по анкорам, скрипты идемпотентные, без хардкода путей.
7. **Upstream** — патчи чистые, минимальные, пригодные для PR в upstream.

## `patches` vs `scripts`

- **`patches/*.patch`** — идут в upstream. `git apply`, минимальные, с
  объяснением. Пример: `koffi-statx.patch` (bionic без `statx()` до API 30),
  `require-builtin-android.patch` (`platform.cc` анкоры).
- **`scripts/*.py`** — локальная сборка под Android, в upstream не идут.
  Пример: `FiberState.ACTIVE -> 2` (workaround — `const enum` стирается в TS).

## Правила ([RULES.md](RULES.md))

Коротко: `cd` первой строкой (#1), без regex в патчах (#2), диагностировать
а не гадать (#3), не ломать работающее (#4), один шаг — один вывод (#5),
всё в `~/` не в `/tmp` (#555), текстовые файлы — python построчно (#12).

## Документы

- [GOALS.md](GOALS.md) — 7 целей проекта.
- [RULES.md](RULES.md) — правила правок (#0–#555).
- [RESURECT.md](RESURECT.md) — состояние, как продолжить с нуля.

## Лицензия

Патчи и скрипты — под лицензией DSH (upstream).
См. `deepseek-ai/deepseek-harness`.
