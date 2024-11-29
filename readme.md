# Проект для обработки документов и создания датасета

Этот проект включает несколько Python скриптов, которые работают в определенной последовательности для создания датасета, его обработки с использованием модели, и получения аннотированных изображений и соответствующих JSON файлов.

## Скрипты

1. **`docmake_v0.1.py`** — Скрипт для создания базового датасета.
2. **`convert_to_pdf.py`** — Преобразует изображения в формат PDF.
3. **`extract_images_pdf2image.py`** — Извлекает изображения из PDF документов.
4. **`test_annot_v0.2.py`** — Аннотирует извлеченные изображения.

После того, как датасет будет подготовлен, необходимо запустить скрипт **`final_detect.py`** для обработки датасета с помощью модели и получения аннотированных изображений и JSON файлов.

## Требования

Перед запуском убедитесь, что у вас установлены все необходимые зависимости. Для этого выполните команду:

```bash
pip install -r requirements.txt
```

MiKTeX — Для обработки LaTeX и PDF. Вы можете скачать MiKTeX [с официального сайта](https://miktex.org/download). После установки, убедитесь, что путь к папке с исполняемыми файлами MiKTeX добавлен в переменную окружения PATH.

Poppler — Для работы с PDF файлами. Скачайте Poppler для Windows [с официального репозитория](https://github.com/oschwartz10612/poppler-windows/releases/). После установки добавьте путь к папке с бинарными файлами Poppler в переменную окружения PATH.

### Описание полей
1. Общая информация
image_height: Высота изображения в пикселях.
image_width: Ширина изображения в пикселях.
image_path: Путь к исходному изображению.

2. Элементы разметки
Каждый элемент разметки представлен в виде списка прямоугольников. Прямоугольник описывается массивом из четырех чисел [x1, y1, x2, y2], где:

(x1, y1) — координаты верхнего левого угла прямоугольника.
(x2, y2) — координаты нижнего правого угла прямоугольника.
Координаты измеряются в пикселях относительно верхнего левого угла изображения.

3. Список элементов разметки:
title: Заголовок документа.
paragraph: Абзацы текста.
table: Таблицы.
picture: Изображения.
table_signature: Подписи к таблицам.
picture_signature: Подписи к изображениям.
numbered_list: Нумерованные списки.
marked_list: Маркированные списки.
header: Колонтитулы (верхние).
footer: Нижние колонтитулы.
footnote: Сноски.
formula: Формулы.
graph: Графики.

Примечание: Если список для определённого элемента пустой ([]), это означает отсутствие данного элемента на странице.

### Docker-образ
[Ссылка на образ](https://disk.yandex.ru/d/ROETDdQazkIcHw)
### Docker-compose
[Ссылка на файлы Docker](https://disk.yandex.ru/d/X08WqHaCfortfw)