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
    Параграфы не обрабатываются здесь и будут обрабатываться PyMuPDF.
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

            # Сбор информации о шрифтах и элементах, за исключением параграфов
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
                            contains_special_symbol = False  # Флаг наличия специальных символов
                            for char in text_line:
                                if isinstance(char, LTChar):
                                    sizes.append(char.size)
                                    font_name = char.fontname.lower()
                                    if 'bold' in font_name:
                                        is_bold = True
                                    if 'italic' in font_name or 'oblique' in font_name:
                                        is_italic = True
                                    char_text = char.get_text()
                                    text_chars.append(char_text)
                                    # Проверяем наличие специальных символов
                                    if char_text in ['~', '&', '$']:
                                        contains_special_symbol = True
                                    # Получение информации о цвете шрифта
                                    try:
                                        font_color = char.graphicstate.ncolor
                                        font_colors.add(font_color)
                                    except AttributeError:
                                        pass
                                else:
                                    text_chars.append(char.get_text())

                            # Если строка содержит только специальные символы, пропускаем ее
                            if contains_special_symbol and not any(c.isalnum() for c in ''.join(text_chars)):
                                continue

                            if sizes:
                                font_size = sum(sizes) / len(sizes)
                                font_sizes.append(font_size)
                                elements.append({
                                    'text_line': text_line,
                                    'text': ''.join(text_chars).strip(),
                                    'char_count': len(text_chars),  # Изменено: добавлено количество символов
                                    'font_size': font_size,
                                    'is_bold': is_bold,
                                    'is_italic': is_italic,
                                    'font_colors': font_colors,
                                    'coords': coords_transformed,
                                    'contains_special_symbol': contains_special_symbol
                                })

            # Убираем обработку параграфов в pdfminer
            # Все параграфы будут обрабатываться в PyMuPDF

            # Обработка заголовков
            idx = 0
            current_title = None
            while idx < len(elements):
                elem = elements[idx]
                text_line = elem['text_line']
                text = elem['text']
                font_size = elem['font_size']
                is_bold = elem['is_bold']
                is_italic = elem['is_italic']
                font_colors = elem['font_colors']
                coords_transformed = elem['coords']
                contains_special_symbol = elem['contains_special_symbol']

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
                footnote_matches = re.finditer(r'\[\d+\]', text)
                x0_br = y0_br = x1_br = y1_br = 0
                for match in footnote_matches:
                    start, end = match.span()
                    for idxx, char in enumerate(text_line):
                        if start <= idxx < end:
                            if isinstance(char, LTChar):
                                char_text = char.get_text()
                                if char_text == '[':
                                    x0_br = char.bbox[0] * SCALING_FACTOR
                                    y0_br = page_height - char.bbox[3] * SCALING_FACTOR
                                if char_text == ']':
                                    x1_br = char.bbox[2] * SCALING_FACTOR
                                    y1_br = page_height - char.bbox[1] * SCALING_FACTOR
                                    annotations['footnote'].append([x0_br, y0_br, x1_br, y1_br])
                                    break            

                # Обработка подписей к рисункам
                figure_signature_match = re.match(r'^\s*(рис\.?|рисунок)\s*\d+', text.lower())
                if figure_signature_match:
                    if current_title is not None:
                        annotations['title'].append(current_title)
                        current_title = None
                    # Инициализируем объединенный бокс
                    combined_coords = coords_transformed.copy()
                    # Сохраняем размер шрифта и нижнюю координату Y текущего элемента
                    current_font_size = font_size
                    current_bottom_y = combined_coords[3]
                    # Инициализируем индекс для просмотра следующих элементов
                    idx_next = idx + 1
                    while idx_next < len(elements):
                        next_elem = elements[idx_next]
                        next_font_size = next_elem['font_size']
                        next_coords = next_elem['coords']
                        # Проверяем, похож ли размер шрифта
                        if abs(next_font_size - current_font_size) < 0.1:
                            # Проверяем, близко ли расположены элементы по Y
                            vertical_gap = next_coords[1] - current_bottom_y
                            if 0 <= vertical_gap <= 20:
                                # Обновляем объединенный бокс
                                combined_coords[0] = min(combined_coords[0], next_coords[0])
                                combined_coords[1] = min(combined_coords[1], next_coords[1])
                                combined_coords[2] = max(combined_coords[2], next_coords[2])
                                combined_coords[3] = max(combined_coords[3], next_coords[3])
                                current_bottom_y = combined_coords[3]
                                idx_next += 1
                                continue
                        break
                    # Добавляем объединенный бокс в аннотации
                    annotations['picture_signature'].append(combined_coords)
                    idx = idx_next
                    continue

                # Обработка подписей к таблицам
                table_signature_match = re.match(r'^\s*(табл\.?|таблица)\s*\d+', text.lower())
                if table_signature_match:
                    if current_title is not None:
                        annotations['title'].append(current_title)
                        current_title = None
                    # Инициализируем объединенный бокс
                    combined_coords = coords_transformed.copy()
                    # Сохраняем размер шрифта и нижнюю координату Y текущего элемента
                    current_font_size = font_size
                    current_bottom_y = combined_coords[3]
                    # Инициализируем индекс для просмотра следующих элементов
                    idx_next = idx + 1
                    while idx_next < len(elements):
                        next_elem = elements[idx_next]
                        next_font_size = next_elem['font_size']
                        next_coords = next_elem['coords']
                        # Проверяем, похож ли размер шрифта
                        if abs(next_font_size - current_font_size) < 0.1:
                            # Проверяем, близко ли расположены элементы по Y
                            vertical_gap = next_coords[1] - current_bottom_y
                            if 0 <= vertical_gap <= 20:
                                # Обновляем объединенный бокс
                                combined_coords[0] = min(combined_coords[0], next_coords[0])
                                combined_coords[1] = min(combined_coords[1], next_coords[1])
                                combined_coords[2] = max(combined_coords[2], next_coords[2])
                                combined_coords[3] = max(combined_coords[3], next_coords[3])
                                current_bottom_y = combined_coords[3]
                                idx_next += 1
                                continue
                        break
                    # Добавляем объединенный бокс в аннотации
                    annotations['table_signature'].append(combined_coords)
                    idx = idx_next
                    continue

                # Обработка формул
                formula_match = re.match(r'^\s*формула', text.lower())
                if formula_match or (is_centered_text(text_line, page_width) and not any(c.isalnum() for c in text)):
                    if current_title is not None:
                        annotations['title'].append(current_title)
                        current_title = None
                    # Формулы будут обработаны PyMuPDF, поэтому здесь пропускаем
                    idx += 1
                    continue

                # Обработка заголовков
                if is_bold or is_italic:
                    if current_title is None:
                        current_title = coords_transformed.copy()
                    else:
                        current_title[0] = min(current_title[0], coords_transformed[0])
                        current_title[1] = min(current_title[1], coords_transformed[1])
                        current_title[2] = max(current_title[2], coords_transformed[2])
                        current_title[3] = max(current_title[3], coords_transformed[3])
                else:
                    # Если мы были в заголовке, завершаем его
                    if current_title is not None:
                        annotations['title'].append(current_title)
                        current_title = None
                    # Параграфы будут обработаны в блоке PyMuPDF, поэтому здесь пропускаем

                idx += 1

            # После цикла добавляем незавершенные элементы
            if current_title is not None:
                annotations['title'].append(current_title)

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
                "paragraph": [],  # Параграфы будут заполнены в PyMuPDF
                "table": annotations["table"],
                "picture": annotations["picture"],  # Пустой список, так как pdfminer не помечает картинки
                "table_signature": annotations["table_signature"],
                "picture_signature": annotations["picture_signature"],
                "numbered_list": annotations["numbered_list"],
                "marked_list": annotations["marked_list"],
                "header": annotations["header"],
                "footer": annotations["footer"],
                "footnote": annotations["footnote"],
                "formula": annotations["formula"],
                "graph": annotations["graph"]  # Добавлено поле для графиков
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
    Извлекает координаты элементов из PDF-файла с помощью PyMuPDF и добавляет аннотации формул, графиков и изображений.
    Также обрабатывает параграфы, учитывая многоколоночные документы.
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
        pictures_type = []  # Список для хранения типов аннотаций ("formula", "image", "graph")

        for block in blocks:
            if block['type'] == 0:  # Текстовый блок
                for line in block['lines']:
                    for span in line['spans']:
                        text = span['text']
                        bbox = span['bbox']  # [x0, y0, x1, y1]
                        font_size = span['size']
                        x0, y0, x1, y1 = bbox
                        # Преобразуем координаты в нужный формат
                        x0_scaled = x0 * SCALING_FACTOR
                        y0_scaled = y0 * SCALING_FACTOR
                        x1_scaled = x1 * SCALING_FACTOR
                        y1_scaled = y1 * SCALING_FACTOR
                        coords_transformed = [x0_scaled, y0_scaled, x1_scaled, y1_scaled]
                        char_count = len(text)
                        elements.append({
                            'type': 'text',
                            'text': text,
                            'bbox': coords_transformed,
                            'char_count': char_count,  # Добавлено: количество символов
                            'font_size': font_size # Добавлено: размер шрифта
                        })
                        # Проверяем на наличие символов "~", "&" и "$"
                        if '~' in text:
                            pictures_type.append('formula')
                        elif '&' in text:
                            pictures_type.append('image')
                        elif '$' in text:
                            pictures_type.append('graph')
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
            if idx < len(pictures_type):
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
                "image_path": os.path.join(IMAGE_DIR,
                                           f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number + 1}.png"),
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
                "formula": [],
                "graph": []  # Добавляем ключ 'graph'
            }

        # Добавляем аннотации из PyMuPDF к существующим аннотациям
        for element in elements:
            if 'annotations' in element:
                if element['annotations'] == 'formula':
                    json_data['formula'].append(element['bbox'])
                elif element['annotations'] == 'image':
                    json_data['picture'].append(element['bbox'])
                elif element['annotations'] == 'graph':
                    json_data['graph'].append(element['bbox'])

        # Флаги для управления состоянием
        in_numbered_list = False
        in_bulleted_list = False
        
        idx = 0
        indent = -1
        x_list_pred = y_list_pred = char_size_pred = 0
        x_list_begin = y_list_begin = -1
        x_list_end = y_list_end = -1       
        bullet_chars = '•◦●○▪–—*-·•‣⁃▪■❖➤►▶‣⁌⁍'

        text_elements = [elem for elem in elements if elem['type'] == 'text']

        # Цикл по текстовым элементам страницы     
        while idx < len(text_elements):                
            text = text_elements[idx]['text']            
            if text == ' ':
                idx += 1
                if idx == len(text_elements):
                    if in_numbered_list:
                        json_data['numbered_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                    if in_bulleted_list:
                        json_data['marked_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                continue
            coords_transformed = text_elements[idx]['bbox']

            # Обработка нумерованных списков 
            numbered_match = re.match(r'^\s*\d+[\.\)]\s*', text)
            if numbered_match and not in_numbered_list:
                in_numbered_list = True
                if in_bulleted_list:
                    json_data['marked_list'].append([x_list_begin, y_list_begin, x_list_end, y_list_end])
                    in_bulleted_list = False
                idx += 2
                x_list_begin, y_list_begin, _, y_list_end = coords_transformed
                x_list_end = text_elements[idx]['bbox'][2]
                x_list_pred = coords_transformed[0]
                y_list_pred = coords_transformed[3]
                char_size_pred = round(text_elements[idx]['font_size'])
                idx += 1
                continue

            # Продолжение нумерованного списка
            if in_numbered_list:
                x_list, y_list0, _, y_list1 = coords_transformed                
                is_num = re.match(r'^\s*\d+[\.\)]\s*', text) is not None
                is_let = text[0].isalpha()
                char_size = -1

                if is_num:                    
                    idx += 2
                    char_size = round(text_elements[idx]['font_size'])
                    coords_transformed = text_elements[idx]['bbox']
                    text = text_elements[idx]['text']
                else:
                    char_size = round(text_elements[idx]['font_size'])                
                if indent == -1 and is_let:
                    indent = x_list - x_list_pred
                x_dif = x_list - x_list_pred

                if ((is_num and abs(x_list - x_list_pred) < 0.001) or (is_let and (abs(x_dif - 75) < 0.001 or x_dif > 500))) and (
                         y_list0 - y_list_pred <= 65) and (char_size == char_size_pred):
                    if y_list_begin > y_list0:
                        json_data['numbered_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                        x_list_begin = coords_transformed[0]
                        if not is_num:
                            x_list_begin -= indent
                        x_list_pred = x_list_begin
                        y_list_begin = coords_transformed[1]

                    if coords_transformed[2] > x_list_end: 
                         x_list_end = coords_transformed[2]
                    y_list_end = coords_transformed[3]

                    idx += 1
                    if idx == len(text_elements):
                        json_data['numbered_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                    y_list_pred = y_list1
                    continue
                else:
                    if is_num:
                        idx -= 2
                    json_data['numbered_list'].append(
                        [x_list_begin, y_list_begin, x_list_end, y_list_end])
                    in_numbered_list = False
                    indent = -1
                    continue
            
            # Обработка маркированных списков 
            bulleted_match = re.match(r'^\s*[' + re.escape(bullet_chars) + r']\s*', text)
            if bulleted_match and not in_bulleted_list:
                in_bulleted_list = True
                in_numbered_list = False
                idx += 2
                x_list_begin, y_list_begin, _, y_list_end = coords_transformed
                x_list_end = text_elements[idx]['bbox'][2]
                x_list_pred = coords_transformed[0]
                y_list_pred = coords_transformed[3]
                char_size_pred = round(text_elements[idx]['font_size'])
                idx += 1
                continue
            
            # Продолжение маркированного списка
            if in_bulleted_list:
                x_list, y_list0, _, y_list1 = coords_transformed                
                is_bullet = text[0] in bullet_chars
                is_let = text[0].isalpha()
                char_size = -1

                if is_bullet:                    
                    idx += 2
                    char_size = round(text_elements[idx]['font_size'])
                    coords_transformed = text_elements[idx]['bbox']
                    text = text_elements[idx]['text']
                else:
                    char_size = round(text_elements[idx]['font_size'])
                if indent == -1 and is_let:
                    indent = x_list - x_list_pred
                x_dif = x_list - x_list_pred

                if ((is_bullet and abs(x_list - x_list_pred) < 0.001) or (is_let and (abs(x_dif - 75) < 0.001 or x_dif > 500))) and (
                         y_list0 - y_list_pred <= 65) and (char_size == char_size_pred):
                    if y_list_begin > y_list0:
                        json_data['marked_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                        x_list_begin = coords_transformed[0]
                        if not is_bullet:
                            x_list_begin -= indent
                        x_list_pred = x_list_begin
                        y_list_begin = coords_transformed[1]

                    if coords_transformed[2] > x_list_end: 
                         x_list_end = coords_transformed[2]
                    y_list_end = coords_transformed[3]

                    idx += 1
                    if idx == len(text_elements):
                        json_data['marked_list'].append(
                            [x_list_begin, y_list_begin, x_list_end, y_list_end])
                    y_list_pred = y_list1
                    continue
                else:
                    if is_bullet:
                        idx -= 2
                    json_data['marked_list'].append(
                        [x_list_begin, y_list_begin, x_list_end, y_list_end])
                    in_bulleted_list = False
                    indent = -1
                    continue

            idx += 1

        # Обработка параграфов
        # Собираем все существующие боксы, чтобы избежать пересечений
        existing_boxes = []
        for key in ['title', 'table', 'picture', 'table_signature', 'picture_signature', 'numbered_list', 'marked_list',
                    'header', 'footer', 'formula', 'graph']:
            existing_boxes.extend(json_data.get(key, []))

        # Фильтруем текстовые элементы, не пересекающиеся с существующими боксами
        filtered_text_elements = []
        for elem in text_elements:
            overlaps = False
            for bbox in existing_boxes:
                if bboxes_overlap(elem['bbox'], bbox):
                    overlaps = True
                    break
            if not overlaps:
                filtered_text_elements.append(elem)

        # Исключаем элементы, содержащие только символы " ", "~", "&", "$" из аннотирования как параграф
        paragraph_elements = []
        for elem in filtered_text_elements:
            text_content = elem['text'].strip()
            if text_content not in ["", "~", "&", "$"]:
                paragraph_elements.append(elem)

        # Группируем элементы в столбцы на основе координаты x0
        threshold = 200
        # Собираем элементы с их x0 и y0 координатами
        sorted_elements = paragraph_elements
        columns = []
        current_column = []
        prev_y0 = None

        for elem in sorted_elements:
            y0 = elem['bbox'][1]
            if prev_y0 is None:
                current_column.append(elem)
            elif abs(y0 - prev_y0) <= threshold:
                current_column.append(elem)
            else:
                columns.append(current_column)
                current_column = [elem]
            prev_y0 = y0

        # Добавляем последний столбец
        if current_column:
            columns.append(current_column)

        # Объединяем боксы в каждом столбце
        for column in columns:
            x0s = [elem['bbox'][0] for elem in column]
            y0s = [elem['bbox'][1] for elem in column]
            x1s = [elem['bbox'][2] for elem in column]
            y1s = [elem['bbox'][3] for elem in column]
            merged_bbox = [min(x0s), min(y0s), max(x1s), max(y1s)]
            # Добавляем объединенный бокс в поле 'paragraph' в json_data
            json_data['paragraph'].append(merged_bbox)

        # Сохраняем обновленные данные в JSON-файл
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)

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


if __name__ == "__main__":
    pdf_folder = "pdf"
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Обработка файла: {pdf_file}")
        extract_annotations_from_pdf(pdf_path, output_dir='json')
        extract_annotations_with_pymupdf(pdf_path, output_dir='json')
