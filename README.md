# Deck Card Numbers

[![License: AGPL v3](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)

Приложение для Nextcloud Deck: каждая новая карточка сразу получает в заголовке номер `#<id>` —
тот же, что в адресе карточки `/apps/deck/board/<boardId>/card/<id>`.

```
Купить хлеб   →   #123 Купить хлеб
```

**English:** a Nextcloud Deck app that prefixes new card titles with `#<card id>` (the id from
`/apps/deck/board/<boardId>/card/<id>`). It listens to `OCA\Deck\Event\CardCreatedEvent`, so the card
is already numbered in the very response that creates it — web UI, mobile apps and the REST API
alike. Requires Nextcloud 28–36 and Deck ≥ 1.5. Not affiliated with Nextcloud GmbH.

## Зачем это нужно

Номер карточки в Deck существует, но виден только в адресной строке (и бейджем в самой карточке
с Deck 1.9). Если на карточки ссылаются в чатах, коммитах, заметках и тикетах, удобнее, когда номер
стоит в заголовке: он виден на доске, приходит в уведомлениях, поиске и мобильном приложении.

Встроенного шаблона заголовка в Deck нет, а `id` присваивает БД при INSERT. Поэтому «номер при
создании» — это правка заголовка в том же запросе, который создаёт карточку.

## Как это работает

Приложение подписывается на `OCA\Deck\Event\CardCreatedEvent`. Deck диспатчит это событие из
`CardService::create()` **с тем же объектом `Card`, который затем возвращает клиенту**, поэтому
слушатель меняет заголовок на `#<id> <прежний заголовок>` и сохраняет карточку через
`CardMapper::update()`: ответ API уже содержит номер, без второго запроса и без окна, в котором
карточка живёт без номера.

- Работает для всех клиентов: веб-интерфейс, мобильные приложения, REST API, импорт досок.
- Идемпотентно: заголовок, который уже начинается с `#<свой id>`, не трогается.
- Копия карточки (Deck копирует заголовок вместе со старым номером) перенумеровывается:
  `#999 Старое имя` у карточки 124 станет `#124 Старое имя`.
- Заголовок, начинающийся с `#` без цифр (`#тег …`), получает номер как обычный текст.
- Отдельной записи в activity-ленте на переименование нет — карточка создаётся уже с номером.

## Совместимость

| Компонент | Требование |
|---|---|
| Nextcloud | 28 – 36 (`max-version` в `appinfo/info.xml`) |
| Deck | ≥ 1.5 (событие `CardCreatedEvent`; проверено на 1.19.1) |
| PHP | 8.1+ |

Проверено в бою: Nextcloud 35.0.2, Deck 1.19.1, PHP 8.5, контейнер `nextcloud:latest`.

## Установка

Каталог приложения должен называться `deckcardnumber` (это его app id), а не `deck-card-number`.

### Вариант 1: из git

```bash
cd /var/www/html/custom_apps
git clone https://github.com/krutogorets/deck-card-number.git deckcardnumber
chown -R www-data:www-data deckcardnumber
sudo -u www-data php /var/www/html/occ app:enable deckcardnumber
```

### Вариант 2: из архива

```bash
cd /var/www/html/custom_apps
curl -L https://github.com/krutogorets/deck-card-number/archive/refs/heads/main.tar.gz \
  | tar xz --strip-components=1 --one-top-level=deckcardnumber
chown -R www-data:www-data deckcardnumber
sudo -u www-data php /var/www/html/occ app:enable deckcardnumber
```

### Вариант 3: Docker

```bash
docker cp deck-card-number nextcloud:/var/www/html/custom_apps/deckcardnumber
docker exec -u root nextcloud chown -R www-data:www-data /var/www/html/custom_apps/deckcardnumber
docker exec -u www-data nextcloud php occ app:enable deckcardnumber
```

Если `/var/www/html` — bind-mount (как в типовом compose-стеке), приложение переживёт
пересоздание контейнера и обновление образа. Если это анонимный volume — тоже, но при пересоздании
стека с нуля приложение придётся положить заново.

### Проверка

```bash
sudo -u www-data php /var/www/html/occ app:list --enabled | grep deckcardnumber
#   - deckcardnumber: 1.0.0
```

Создайте карточку — в заголовке должен появиться `#<id>`, совпадающий с числом в адресе карточки.

## Обновление

```bash
cd /var/www/html/custom_apps/deckcardnumber && git pull
sudo -u www-data php /var/www/html/occ upgrade
```

## Удаление

```bash
sudo -u www-data php /var/www/html/occ app:disable deckcardnumber
rm -rf /var/www/html/custom_apps/deckcardnumber
```

Уже проставленные номера в заголовках остаются — приложение только пишет их при создании.

## Нумерация существующих карточек

Приложение намеренно не трогает карточки, созданные до установки. Если нужно пронумеровать их,
в репозитории есть отдельный скрипт, работающий через Deck REST API:

```bash
export NC_URL=https://cloud.example.com NC_USER=user NC_APP_PASSWORD='app-password'
python3 tools/backfill.py --once            # dry run: показать, что изменится
python3 tools/backfill.py --once --apply    # переименовать
python3 tools/backfill.py --loop --apply --interval 60   # следить за новыми карточками
```

`--boards 2,4` ограничивает набор досок, `--backfill` не нужен: скрипт по умолчанию обрабатывает
все карточки без своего номера. App password выдаётся в Nextcloud: Настройки → Безопасность →
Пароли приложений.

## Ограничения

- `max-version="36"`: при обновлении Nextcloud до 37 приложение будет отключено, пока в
  `appinfo/info.xml` не поднят `max-version` (и не проверена совместимость).
- Номер ставится один раз при создании. Если потом вручную стереть `#123` из заголовка, приложение
  не вернёт его (это работа для `tools/backfill.py`).
- Заголовки нумеруются как есть: `#123` + пробел + прежний текст, без переформатирования
  существующих префиксов вроде `[Feature]`.
- Приложение не аффилировано с Nextcloud GmbH; Deck не даёт официального API для такой подмены,
  используется публичное событие `CardCreatedEvent`.

## Диагностика и поддержка

| Симптом | Что проверить |
|---|---|
| Новая карточка без номера | `occ app:list --enabled \| grep deckcardnumber`; включён ли Deck; не отключило ли приложение обновление NC (`occ app:list` покажет disabled) |
| Номер не тот | `id` в Deck глобальный для инстанса, а не по доске — сверяйте с `/apps/deck/board/<boardId>/card/<id>` |
| Ошибка 500 при создании карточки | `grep deckcardnumber /var/www/html/data/nextcloud.log`, затем `php -l` на файлах приложения |
| После обновления Nextcloud ничего не работает | проверьте `max-version` в `appinfo/info.xml` и статус приложения |

Логи приложения пишутся с тегом `deckcardnumber` (только предупреждения, если переименование не
удалось — например, карточка уже удалена параллельно).

Сообщения об ошибках и предложения — в [Issues](https://github.com/krutogorets/deck-card-number/issues).
К репорту приложите версии Nextcloud и Deck (`occ status`, `occ app:list | grep deck`), текст ошибки
из `nextcloud.log` и шаги, после которых карточка осталась без номера.

## Лицензия

AGPL-3.0-or-later, см. [LICENSE](LICENSE).
