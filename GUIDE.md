# Руководство по сборке DSH на GitHub Actions

Этот документ объясняет, как устроен наш пайплайн сборки, как его запускать,
как следить за прогрессом и как проверить готовый артефакт.

## 1. Что такое GitHub Actions?

**GitHub Actions** — это встроенная в GitHub система CI/CD (Continuous Integration /
Continuous Deployment). Она позволяет запускать код на виртуальных машинах
(раннерах) прямо в облаке, без вашего участия.

Для нас это означает:
*   Мы не собираем DSH на телефоне (это долго, греет батарею и ест память).
*   Вместо этого мы отправляем код на GitHub, а он запускает сборку на мощном
    сервере (Ubuntu, 7 ГБ RAM, 2 ядра).
*   Результат (артефакт) скачивается на телефон в готовом виде.

## 2. Что такое `workflow.yaml`?

**`workflow.yaml`** (в нашем случае `.github/workflows/build-dsh.yml`) — это
инструкция для GitHub Actions. В ней описано:
*   **Когда запускаться** (`on: workflow_dispatch` — вручную, `on: push` — при коммите).
*   **Что делать** (шаги: `Checkout`, `Install`, `Build`, `Patch`, `Package`).
*   **Где взять код** (репозиторий `deepseek-ai/deepseek-harness`).
*   **Куда положить результат** (артефакт `dsh-android-arm64.tar.gz`).

## 3. Пошаговая инструкция

### 3.1. Как править YAML

Все правки — только через `python3 - << 'EOF'` (Правило #0). Никаких `sed` или
ручного редактирования через `nano`, чтобы не сломать отступы.

Пример: добавить шаг в YAML:
```bash
cd ~/dsh-builder
python3 - << 'EOF'
import os
file_path = '.github/workflows/build-dsh.yml'
with open(file_path, 'r') as f:
    content = f.read()
old = '''      - name: Install dependencies
        run: pnpm install --frozen-lockfile
'''
new = '''      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: My new step
        run: echo 'Hello'
'''
content = content.replace(old, new)
with open(file_path, 'w') as f:
    f.write(content)
print('[+] Step added.')
EOF
```

### 3.2. Как запустить сборку

```bash
cd ~/dsh-builder
git add .github/workflows/build-dsh.yml scripts/ patches/
git commit -m "feat: my changes"
git push
gh workflow run build-dsh.yml
```

### 3.3. Как следить за выполнением

```bash
cd ~/dsh-builder
gh run watch
```

Или посмотреть список последних запусков:
```bash
gh run list -L 5
```

### 3.4. Как скачать артефакт

Когда сборка завершится (зеленая галочка), выполните:
```bash
cd ~/dsh-builder
gh run download <ID>
```
Где `<ID>` — это номер запуска (виден в `gh run list`).

Артефакт появится в папке `dsh-android-arm64/dsh-android-arm64.tar.gz`.

### 3.5. Как проверить целостность

После распаковки проверьте, что все нативные модули на месте:
```bash
cd ~/dsh-artifact
find . -name '*.node' | while read f; do printf '%s\t' "$f"; file "$f" | grep -oE 'ARM aarch64|x86-64|Android [0-9]+'; done
```
Все `.node` должны быть `ARM aarch64`. Если увидите `x86-64` — значит, сборка
подтянула хост-версию, и нужно поправить скрипт.

### 3.6. Как запустить артефакт

```bash
cd ~/dsh-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-..."
node --import tsx/esm apps/cli/src/bin.ts web
```
Если сервер запустился — вы увидите ссылку `http://127.0.0.1:3080/?token=...`.
Откройте её в браузере.

## 4. Что делать, если упало

1.  Посмотрите лог ошибки:
    ```bash
    gh run view --log-failed
    ```
2.  Найдите шаг, на котором упало (`Build DSH`, `Compile system.node` и т.д.).
3.  Если ошибка в `python`-скрипте — поправьте его в `scripts/`.
4.  Если ошибка в YAML — поправьте `.github/workflows/build-dsh.yml`.
5.  Запушьте изменения и перезапустите.

## 5. Полезные ссылки

*   [GOALS.md](GOALS.md) — цели проекта.
*   [RULES.md](RULES.md) — правила правок.
*   [RESURECT.md](RESURECT.md) — как продолжить с нуля.

## 6. Примеры из реальной работы

Ниже — реальные команды, которые мы использовали при сборке DSH.
Их можно копировать и адаптировать под свои нужды.

### 6.1. Полный цикл: правка, коммит, пуш, запуск, мониторинг

```bash
cd ~/dsh-builder && \
  rm -f README.md.bak4 && \
  git add .github/workflows/build-dsh.yml scripts/patch_flock_path_android.py scripts/patch_session_persistence.py && \
  git status --short && \
  git commit -m "ci: wire patch_flock_path_android + patch_session_persistence into build-dsh.yml" && \
  git push
sleep 5
cd ~/dsh-builder && for i in 1 2 3 4 5; do
  if gh workflow run build-dsh.yml; then echo "[OK] dispatched (try $i)"; break; fi
  echo "[retry $i] HTTP 500, sleep 15"; sleep 15
done
sleep 15
cd ~/dsh-builder && gh run list --limit 1 --json databaseId,status,conclusion
```

### 6.2. Запуск собранного артефакта с ключом из файла

```bash
cd ~ && umask 077 && printf '%s' 'sk-НОВЫЙ_КЛЮЧ' > ~/.deepseek_key && chmod 600 ~/.deepseek_key
cd ~/dsh-final9/dsh-test9/dist-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="$(cat ~/.deepseek_key)"
timeout 120 node --import tsx/esm apps/cli/src/bin.ts web 2>&1 | tee ~/launch9.log
```

### 6.3. Проверка, что скрипты попали в коммит

```bash
cd ~/dsh-builder && git ls-files scripts/patch_flock_path_android.py scripts/patch_session_persistence.py
```

Если команда ничего не вывела — файлы не добавлены в git, и CI их не увидит.

