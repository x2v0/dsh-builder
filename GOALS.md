# Цели проекта dsh-builder

## 1. Главная цель
Запустить DSH (DeepSeek Harness) на Android **полностью из GitHub Actions**, без ручных патчей на телефоне. Артефакт воспроизводим: скачал → распаковал → запустил.

## 2. Техническая цель
Собрать в YAML **все нативные модули под Android** (`system.node` для `flock`, `require_builtin.node`, `koffi`, `node-pty`, `esbuild`), чтобы не было `ENOSYS`, `EACCES`, `Cannot find module`.

## 3. Инфраструктурная цель
YAML **чистый**: логика в `scripts/*.py`, а не в heredoc'ах. Скрипты идемпотентные, с `cd` (правило #1), без regex (правило #11), с бэкапами (правило #2).

## 4. Минимальные изменения в DSH
Следуем принципу **«DSH — everything is plugin»**. Не патчим ядро без необходимости; если можно добавить функциональность плагином — добавляем плагином.

## 5. Никаких бинарных prebuild
Всё собирается из исходников на GitHub Actions. В репозитории `dsh-builder` нет готовых `.node`/`.so`/`esbuild` — только `scripts/` и `patches/`.

## 6. Гибкость к будущим изменениям
Наша система должна переживать обновления DSH и других пакетов, которые мы собираем из `src`. Поэтому:
- патчи — **по анкорам** (а не по номерам строк);
- скрипты — **идемпотентные** (повторный запуск не ломает);
- никаких хардкодов путей, которые могут измениться (или они централизованы в одном месте).

## 7. Цель — upstream
Добавить наши изменения в основную ветку DSH (`deepseek-ai/deepseek-harness`). Не держать форк вечно. Патчи должны быть **чистыми, минимальными и объяснимыми**, чтобы их можно было предложить в upstream (PR). То же — для `dsh-node-addon-require-builtin` и других upstream-пакетов.

## Разделение: patches vs scripts

### `patches/*.patch` — то, что идёт в upstream
- `koffi-statx.patch` — Android/bionic не имеет `statx()` до API 30.
- `require-builtin-android.patch` — `platform.cc` для Android/bionic (анкоры: `__linux__ && __GLIBC__ && __aarch64__` → `__linux__ && __aarch64__`).
- `01-terminal-bash-android-shell.patch` ... `08-dsh-tool-fs-search-android-rg.patch` — Android-специфичные фиксы в DSH.
- Все патчи — в формате `git apply`, минимальные, с объяснением в комментарии.

### `scripts/*.py` — то, что локально (сборка под Android)
- `build_system_node.py` — компиляция `flock.c` через NDK.
- `build_require_builtin.py` — сборка `require_builtin.node` (с анкорами для `platform.cc` и `build.ts`).
- `install_android_build_tools.py` — `@esbuild/android-arm64`, `@rolldown/binding-android-arm64`.
- `patch_flock_ts.py` — `flock.ts`: `&& platform !== 'android'`.
- `patch_flock_c.py` — `flock.c`: `flock()` → `fcntl()` (fallback для bionic).
- `patch_fiberstate.py` — `FiberState.ACTIVE → 2` (workaround, потому что `const enum` стирается).
- `apply_patches.sh` — применяет `patches/*.patch` через `git apply`.

### Что НЕ идёт в upstream
- `FiberState.ACTIVE → 2` — это **локальный workaround** (TypeScript `const enum` стирается при компиляции; `profile-boot.ts` ожидает runtime-значение). В upstream это надо решать иначе (например, `export const FiberState = {...} as const`). Пока — в `scripts/`.


---
**Статус на 26.11.2026:** Все цели достигнуты. Артефакт `45725287927` собирается полностью в GitHub Actions, запускается на Android/Termux без ручных правок. `web` стартует, `turn` доходит до DeepSeek API.
