import os
import json
import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import (LAParams, LTTextBoxHorizontal, LTTextLineHorizontal,
                             LTChar)
from collections import defaultdict
import fitz  # PyMuPDF
import pdfplumber

# Масштабный коэффициент для преобразования координат
SCALING_FACTOR = 4.1667  # Пример для dpi=300 (300 / 72)
IMAGE_DIR = 'image'  # Папка, где сохраняются изображения страницы


def extract_annotations_from_pdf(pdf_path, output_dir='json'):
    """
    Извлекает координаты элементов из PDF-файла и сохраняет их в JSON-файлы.
    Теперь с поддержкой аннотирования таблиц с использованием pdfplumber, включая таблицы без границ.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    laparams = LAParams()

    # Открываем PDF-файл с помощью pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page_layout in enumerate(extract_pages(pdf_path, laparams=laparams)):
            annotations = defaultdict(list)
            font_sizes = []
            elements = []
            header_elements = []
            footer_elements = []
            page = pdf.pages[page_number]

            # Получаем размеры страницы
            page_width = page_layout.bbox[2] * SCALING_FACTOR
            page_height = page_layout.bbox[3] * SCALING_FACTOR

            is_landscape = page_width > page_height

            # Настройка порогов для хедера и футера в зависимости от ориентации
            if is_landscape:
                header_y_threshold = page_height * 0.10
                footer_y_threshold = page_height * 0.90
            else:
                header_y_threshold = page_height * 0.05
                footer_y_threshold = page_height * 0.95

            # Извлекаем таблицы с помощью pdfplumber с использованием режима 'stream' для обнаружения таблиц без границ
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_tolerance": 5,
            }
            tables = page.extract_tables(table_settings=table_settings)
            table_bboxes = []

            # Получаем координаты таблиц
            for table in page.find_tables(table_settings=table_settings):
                x0, top, x1, bottom = table.bbox  # bbox = (x0, top, x1, bottom)
                x0_scaled = x0 * SCALING_FACTOR
                x1_scaled = x1 * SCALING_FACTOR
                y0_scaled = top * SCALING_FACTOR
                y1_scaled = bottom * SCALING_FACTOR
                # Координаты преобразуются в формат [x0, y0, x1, y1]
                coords_transformed = [x0_scaled, y0_scaled, x1_scaled, y1_scaled]
                table_bboxes.append(coords_transformed)
            # Добавляем координаты таблиц в аннотации
            annotations['table'].extend(table_bboxes)

            # Флаги для управления состоянием
            in_numbered_list = False
            in_bulleted_list = False

            x_list_pred = y_list_pred0 = 0

            # Сбор информации о шрифтах и элементах
            for element in page_layout:
                if isinstance(element, LTTextBoxHorizontal):
                    for text_line in element:
                        if isinstance(text_line, LTTextLineHorizontal):
                            # Получаем координаты текстовой строки
                            x0, y0, x1, y1 = text_line.bbox
                            x0_scaled = x0 * SCALING_FACTOR
                            x1_scaled = x1 * SCALING_FACTOR
                            y0_scaled = y0 * SCALING_FACTOR
                            y1_scaled = y1 * SCALING_FACTOR

                            # Преобразуем координаты в систему с началом в верхнем левом углу
                            text_y0 = page_height - y1_scaled  # Верхняя граница
                            text_y1 = page_height - y0_scaled  # Нижняя граница

                            coords_transformed = [x0_scaled, text_y0, x1_scaled, text_y1]

                            # Проверяем, находится ли текстовая строка внутри таблицы
                            if is_in_table(coords_transformed, table_bboxes):
                                continue  # Пропускаем обработку этой строки, так как она внутри таблицы

                            line_text = text_line.get_text().strip()
                            if not line_text:
                                continue
                            sizes = []
                            is_bold = False
                            is_italic = False
                            text_chars = []
                            font_colors = set()
                            for char in text_line:
                                if isinstance(char, LTChar):
                                    sizes.append(char.size)
                                    font_name = char.fontname.lower()
                                    if 'bold' in font_name:
                                        is_bold = True
                                    if 'italic' in font_name or 'oblique' in font_name:
                                        is_italic = True
                                    text_chars.append(char.get_text())
                                    # Получение информации о цвете шрифта
                                    try:
                                        font_color = char.graphicstate.ncolor
                                        font_colors.add(font_color)
                                    except AttributeError:
                                        pass
                                else:
                                    text_chars.append(char.get_text())

                            if sizes:
                                font_size = sum(sizes) / len(sizes)
                                font_sizes.append(font_size)
                                elements.append({
                                    'text_line': text_line,
                                    'text': ''.join(text_chars).strip(),
                                    'font_size': font_size,
                                    'is_bold': is_bold,
                                    'is_italic': is_italic,
                                    'font_colors': font_colors,
                                    'coords': coords_transformed
                                })

            average_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

            idx = 0
            current_paragraph = None
            bullet_chars = '•◦●○▪–—*-·•‣⁃▪■❖➤►▶‣⁌⁍'
            while idx < len(elements):
                elem = elements[idx]
                text_line = elem['text_line']
                text = elem['text']
                font_size = elem['font_size']
                is_bold = elem['is_bold']
                is_italic = elem['is_italic']
                font_colors = elem['font_colors']
                coords_transformed = elem['coords']

                x0_scaled, y0_scaled, x1_scaled, y1_scaled = coords_transformed

                # Определение хедера и футера
                if y0_scaled < header_y_threshold:
                    header_elements.append(coords_transformed)
                    idx += 1
                    continue
                elif y1_scaled > footer_y_threshold:
                    footer_elements.append(coords_transformed)
                    idx += 1
                    continue

                # Обработка сносок в тексте
                footnote_matches = re.finditer(r'\$\$\d+\$\$', text)
                for match in footnote_matches:
                    start, end = match.span()
                    annotations['footnote'].append(coords_transformed)
                    break

                # Функция для получения координат первого символа
                def get_first_char_coords(text_line):
                    for char in text_line:
                        if isinstance(char, LTChar):
                            x0_char = char.bbox[0] * SCALING_FACTOR
                            y0_char = page_height - char.bbox[3] * SCALING_FACTOR
                            y1_char = page_height - char.bbox[1] * SCALING_FACTOR
                            return [x0_char, y0_char, y1_char]
                    return None

                # Обработка нумерованных списков
                numbered_match = re.match(r'^\s*\d+[\.\)]\s+', text)
                if numbered_match:
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    annotations['numbered_list'].append(coords_transformed)
                    in_numbered_list = True
                    in_bulleted_list = False
                    idx += 1
                    first_char_coords = get_first_char_coords(text_line)
                    if first_char_coords:
                        x_list_pred, y_list_pred0, _ = first_char_coords
                    continue

                # Обработка маркированных списков
                bulleted_match = re.match(r'^\s*[' + re.escape(bullet_chars) + r']\s+', text)
                if bulleted_match:
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    annotations['marked_list'].append(coords_transformed)
                    in_bulleted_list = True
                    in_numbered_list = False
                    idx += 1
                    first_char_coords = get_first_char_coords(text_line)
                    if first_char_coords:
                        x_list_pred, y_list_pred0, _ = first_char_coords
                    continue

                # Продолжение нумерованного списка
                if in_numbered_list:
                    first_char_coords = get_first_char_coords(text_line)
                    if first_char_coords:
                        x_list, y_list0, y_list1 = first_char_coords
                        if (x_list - x_list_pred > 8) and (y_list_pred0 - y_list1 <= 12):
                            annotations['numbered_list'].append(coords_transformed)
                            idx += 1
                            y_list_pred0 = y_list0
                            continue
                        else:
                            in_numbered_list = False

                # Продолжение маркированного списка
                if in_bulleted_list:
                    first_char_coords = get_first_char_coords(text_line)
                    if first_char_coords:
                        x_list, y_list0, y_list1 = first_char_coords
                        if (x_list - x_list_pred > 10) and (y_list_pred0 - y_list1 <= 12):
                            annotations['marked_list'].append(coords_transformed)
                            idx += 1
                            y_list_pred0 = y_list0
                            continue
                        else:
                            in_bulleted_list = False

                # Обработка подписей к рисункам
                figure_signature_match = re.match(r'^\s*(рис\.?|рисунок)\s*\d+', text.lower())
                if figure_signature_match:
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    annotations['picture_signature'].append(coords_transformed)
                    idx += 1
                    continue

                # Обработка подписей к таблицам
                table_signature_match = re.match(r'^\s*(табл\.?|таблица)\s*\d+', text.lower())
                if table_signature_match:
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    annotations['table_signature'].append(coords_transformed)
                    idx += 1
                    continue

                # Обработка формул
                formula_match = re.match(r'^\s*формула', text.lower())
                if formula_match or (any(color == 1.0 for color in font_colors) and is_centered_text(text_line, page_width)):
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    # Формулы будут обработаны PyMuPDF, поэтому здесь пропускаем
                    idx += 1
                    continue

                # Обработка параграфов
                if font_size >= average_font_size + 2 and (is_bold or is_italic):
                    if current_paragraph is not None:
                        annotations['paragraph'].append(current_paragraph)
                        current_paragraph = None
                    annotations['title'].append(coords_transformed)
                elif not in_numbered_list and not in_bulleted_list:
                    if current_paragraph is None:
                        current_paragraph = coords_transformed.copy()
                    else:
                        current_paragraph[0] = min(current_paragraph[0], coords_transformed[0])
                        current_paragraph[1] = min(current_paragraph[1], coords_transformed[1])
                        current_paragraph[2] = max(current_paragraph[2], coords_transformed[2])
                        current_paragraph[3] = max(current_paragraph[3], coords_transformed[3])

                idx += 1

            # После обработки всех элементов, добавляем текущий параграф, если он есть
            if current_paragraph is not None:
                annotations['paragraph'].append(current_paragraph)

            # Объединение боксов хедера и футера
            if header_elements:
                min_x = min(box[0] for box in header_elements)
                min_y = min(box[1] for box in header_elements)
                max_x = max(box[2] for box in header_elements)
                max_y = max(box[3] for box in header_elements)
                annotations['header'].append([min_x, min_y, max_x, max_y])
            if footer_elements:
                min_x = min(box[0] for box in footer_elements)
                min_y = min(box[1] for box in footer_elements)
                max_x = max(box[2] for box in footer_elements)
                max_y = max(box[3] for box in footer_elements)
                annotations['footer'].append([min_x, min_y, max_x, max_y])

            # Формирование пути к изображению
            image_path = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.png"

            # Структура JSON
            json_data = {
                "image_height": int(page_height),
                "image_width": int(page_width),
                "image_path": os.path.join(IMAGE_DIR, image_path),
                "title": annotations["title"],
                "paragraph": annotations["paragraph"],
                "table": annotations["table"],
                "picture": annotations["picture"],  # Пустой список, так как pdfminer не помечает картинки
                "table_signature": annotations["table_signature"],
                "picture_signature": annotations["picture_signature"],
                "numbered_list": annotations["numbered_list"],
                "marked_list": annotations["marked_list"],
                "header": annotations["header"],
                "footer": annotations["footer"],
                "footnote": annotations["footnote"],
                "formula": annotations["formula"]
            }

            # Сохранение аннотаций
            json_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.json"
            json_path = os.path.join(output_dir, json_name)
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=4)
            print(f"Аннотации для страницы {page_number + 1} сохранены в {json_path}.")


def is_in_table(bbox, table_bboxes):
    """
    Проверяет, находится ли данный bbox внутри какого-либо из боксов таблиц.
    :param bbox: Координаты бокса [x0, y0, x1, y1].
    :param table_bboxes: Список координат боксов таблиц.
    :return: True, если bbox находится внутри таблицы, иначе False.
    """
    for table_bbox in table_bboxes:
        if bboxes_overlap(bbox, table_bbox):
            return True
    return False


def bboxes_overlap(bbox1, bbox2):
    """
    Проверяет, пересекаются ли два бокса.
    :param bbox1: Первый бокс [x0, y0, x1, y1].
    :param bbox2: Второй бокс [x0, y0, x1, y1].
    :return: True, если боксы пересекаются, иначе False.
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2

    if x1_1 <= x0_2 or x0_1 >= x1_2:
        return False  # Нет горизонтального пересечения
    if y1_1 <= y0_2 or y0_1 >= y1_2:
        return False  # Нет вертикального пересечения
    return True  # Есть пересечение


def is_centered_text(text_line, page_width, tolerance=20):
    """
    Проверяет, выровнен ли текст по центру страницы для выявления надписи "Формула" под рисунком.
    :param text_line: Объект LTTextLineHorizontal.
    :param page_width: Ширина страницы.
    :param tolerance: Допустимое отклонение в пикселях.
    :return: True, если текст выровнен по центру, иначе False.
    """
    x0, _, x1, _ = text_line.bbox
    text_center = (x0 + x1) / 2 * SCALING_FACTOR
    page_center = page_width / 2
    return abs(page_center - text_center) <= tolerance


def extract_annotations_with_pymupdf(pdf_path, output_dir='json'):
    """
    Извлекает координаты элементов из PDF-файла с помощью PyMuPDF и добавляет аннотации формул и изображений.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)

    for page_number in range(len(doc)):
        page = doc[page_number]
        page_width, page_height = page.rect.width, page.rect.height

        # Получаем текстовые блоки в виде словаря
        page_dict = page.get_text("dict")
        blocks = page_dict["blocks"]

        elements = []  # Список для хранения элементов страницы
        pictures_type = []  # Список для хранения типов аннотаций ("formula", "image")

        for block in blocks:
            if block['type'] == 0:  # Текстовый блок
                for line in block['lines']:
                    for span in line['spans']:
                        text = span['text']
                        bbox = span['bbox']  # [x0, y0, x1, y1]
                        x0, y0, x1, y1 = bbox
                        # Преобразуем координаты в нужный формат
                        x0_scaled = x0 * SCALING_FACTOR
                        y0_scaled = y0 * SCALING_FACTOR
                        x1_scaled = x1 * SCALING_FACTOR
                        y1_scaled = y1 * SCALING_FACTOR
                        coords_transformed = [x0_scaled, y0_scaled, x1_scaled, y1_scaled]
                        elements.append({
                            'type': 'text',
                            'text': text,
                            'bbox': coords_transformed
                        })
                        # Проверяем на наличие символов "~" и "&"
                        if '~' in text:
                            pictures_type.append('formula')
                        if '&' in text:
                            pictures_type.append('image')
            elif block['type'] == 1:  # Изображение
                bbox = block['bbox']
                x0, y0, x1, y1 = bbox
                x0_scaled = x0 * SCALING_FACTOR
                y0_scaled = y0 * SCALING_FACTOR
                x1_scaled = x1 * SCALING_FACTOR
                y1_scaled = y1 * SCALING_FACTOR
                coords_transformed = [x0_scaled, y0_scaled, x1_scaled, y1_scaled]
                elements.append({
                    'type': 'image',
                    'bbox': coords_transformed
                })

        # Проходим по последним элементам в количестве len(pictures_type) и присваиваем аннотации
        image_elements = [elem for elem in elements if elem['type'] == 'image']

        # Теперь присваиваем аннотации
        for idx, image_elem in enumerate(image_elements[-len(pictures_type):]):
            image_elem['annotations'] = pictures_type[idx]

        # Загрузка существующих аннотаций из pdfminer
        json_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.json"
        json_path = os.path.join(output_dir, json_name)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as json_file:
                json_data = json.load(json_file)
        else:
            json_data = {
                "image_height": int(page_height * SCALING_FACTOR),
                "image_width": int(page_width * SCALING_FACTOR),
                "image_path": os.path.join(IMAGE_DIR, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.png"),
                "title": [],
                "paragraph": [],
                "table": [],
                "picture": [],
                "table_signature": [],
                "picture_signature": [],
                "numbered_list": [],
                "marked_list": [],
                "header": [],
                "footer": [],
                "footnote": [],
                "formula": []
            }

        # Добавляем аннотации из PyMuPDF к существующим аннотациям
        for element in elements:
            if 'annotations' in element:
                if 'formula' in element['annotations']:
                    json_data['formula'].append(element['bbox'])
                if 'image' in element['annotations']:
                    json_data['picture'].append(element['bbox'])

        # Сохраняем обновленные аннотации
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
        print(f"Обновленные аннотации для страницы {page_number + 1} сохранены в {json_path}.")

    doc.close()


if __name__ == "__main__":
    pdf_folder = "pdf"
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Обработка файла: {pdf_file}")
        extract_annotations_from_pdf(pdf_path)
        extract_annotations_with_pymupdf(pdf_path)
