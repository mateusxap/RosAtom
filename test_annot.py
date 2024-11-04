import os
import json
import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import (LAParams, LTTextBoxHorizontal, LTTextLineHorizontal,
                             LTChar, LTFigure, LTImage)
from collections import defaultdict

# Масштабный коэффициент для преобразования координат
SCALING_FACTOR = 4.1667  # Пример для dpi=300 (300 / 72)
IMAGE_DIR = 'image'  # Папка, где сохраняются изображения страницы

def extract_annotations_from_pdf(pdf_path, output_dir='json'):
    """
    Извлекает координаты элементов из PDF-файла и сохраняет их в JSON-файлы.

    :param pdf_path: Путь к PDF-файлу.
    :param output_dir: Директория для сохранения JSON-файлов.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    laparams = LAParams()

    for page_number, page_layout in enumerate(extract_pages(pdf_path, laparams=laparams)):
        annotations = defaultdict(list)
        font_sizes = []
        elements = []
        images = []
        header_elements = []
        footer_elements = []
        page_width = page_layout.bbox[2] * SCALING_FACTOR
        page_height = page_layout.bbox[3] * SCALING_FACTOR
        is_landscape = page_width > page_height

        # Настройка порогов для хедера и футера в зависимости от ориентации
        if is_landscape:
            header_y_threshold = page_height * 0.90
            footer_y_threshold = page_height * 0.10
        else:
            header_y_threshold = page_height * 0.95
            footer_y_threshold = page_height * 0.05

        # Флаги для управления состоянием
        in_numbered_list = False
        in_bulleted_list = False
        in_table = False
        in_footnote_section = False

        x_list_pred = y_list_pred0 = y_list_pred1 = 0

        # Сбор информации о шрифтах и элементах
        for element in page_layout:
            if isinstance(element, LTTextBoxHorizontal):
                for text_line in element:
                    if isinstance(text_line, LTTextLineHorizontal):
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
                                'font_colors': font_colors
                            })
            elif isinstance(element, (LTFigure, LTImage)):
                def parse_figure(fig):
                    for obj in fig:
                        if isinstance(obj, LTImage):
                            x0, y0, x1, y1 = obj.bbox
                            x0_scaled = x0 * SCALING_FACTOR
                            y0_scaled = y0 * SCALING_FACTOR
                            x1_scaled = x1 * SCALING_FACTOR
                            y1_scaled = y1 * SCALING_FACTOR
                            coords_transformed = [x0_scaled, page_height - y1_scaled, x1_scaled, page_height - y0_scaled]
                            images.append({
                                'bbox': coords_transformed,
                                'y0': y0_scaled,
                                'y1': y1_scaled
                            })
                        elif isinstance(obj, LTFigure):
                            parse_figure(obj)
                parse_figure(element)

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

            x0, y0, x1, y1 = text_line.bbox
            x0_scaled = x0 * SCALING_FACTOR
            y0_scaled = y0 * SCALING_FACTOR
            x1_scaled = x1 * SCALING_FACTOR
            y1_scaled = y1 * SCALING_FACTOR
            coords_transformed = [x0_scaled, page_height - y1_scaled, x1_scaled, page_height - y0_scaled]

            # Определение хедера и футера
            if y1_scaled > header_y_threshold:
                header_elements.append(coords_transformed)
                idx += 1
                continue
            elif y0_scaled < footer_y_threshold:
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

            
            def get_first_char_coords(text_line):
                for char in text_line:
                    if isinstance(char, LTChar):
                        return [char.bbox[0], char.bbox[1], char.bbox[3]]
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
                x_list_pred, y_list_pred0, _ = get_first_char_coords(text_line)
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
                x_list_pred, y_list_pred0, _ = get_first_char_coords(text_line)
                continue

            # Продолжение нумерованного списка
            if in_numbered_list:
                x_list, y_list0, y_list1 = get_first_char_coords(text_line)
                if (x_list - x_list_pred > 8) and (y_list_pred0 - y_list1 <= 12):
                    annotations['numbered_list'].append(coords_transformed)
                    idx += 1
                    y_list_pred0 = y_list0
                    continue
                else:
                    in_numbered_list = False

            # Продолжение маркированного списка
            if in_bulleted_list:
                x_list, y_list0, y_list1 = get_first_char_coords(text_line)
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

                # Объединение последующих строк в подписи к рисунку
                figure_signature_boxes = [coords_transformed]
                idx += 1
                while idx < len(elements):
                    next_elem = elements[idx]
                    next_text_line = next_elem['text_line']
                    next_text = next_elem['text']
                    next_x0, next_y0, next_x1, next_y1 = next_text_line.bbox
                    next_x0_scaled = next_x0 * SCALING_FACTOR
                    next_y0_scaled = next_y0 * SCALING_FACTOR
                    next_x1_scaled = next_x1 * SCALING_FACTOR
                    next_y1_scaled = next_y1 * SCALING_FACTOR
                    next_coords_transformed = [next_x0_scaled, page_height - next_y1_scaled, next_x1_scaled, page_height - next_y0_scaled]

                    # Проверяем вертикальный промежуток
                    vertical_gap = y0_scaled - next_y1_scaled
                    if vertical_gap > average_font_size * 2:
                        break

                    # Добавляем строку в подпись
                    figure_signature_boxes.append(next_coords_transformed)
                    y0_scaled = next_y0_scaled
                    idx += 1

                # Определяем общий бокс подписи к рисунку
                min_x = min(box[0] for box in figure_signature_boxes)
                min_y = min(box[1] for box in figure_signature_boxes)
                max_x = max(box[2] for box in figure_signature_boxes)
                max_y = max(box[3] for box in figure_signature_boxes)
                annotations['picture_signature'].append([min_x, min_y, max_x, max_y])
                continue

            # Обработка таблиц
            table_signature_match = re.match(r'^\s*(табл\.?|таблица)\s*\d+', text.lower())
            if table_signature_match:
                if current_paragraph is not None:
                    annotations['paragraph'].append(current_paragraph)
                    current_paragraph = None

                # Объединение последующих строк в заголовке таблицы
                table_signature_boxes = [coords_transformed]
                idx += 1
                while idx < len(elements):
                    next_elem = elements[idx]
                    next_text_line = next_elem['text_line']
                    next_text = next_elem['text']
                    next_x0, next_y0, next_x1, next_y1 = next_text_line.bbox
                    next_x0_scaled = next_x0 * SCALING_FACTOR
                    next_y0_scaled = next_y0 * SCALING_FACTOR
                    next_x1_scaled = next_x1 * SCALING_FACTOR
                    next_y1_scaled = next_y1 * SCALING_FACTOR
                    next_coords_transformed = [next_x0_scaled, page_height - next_y1_scaled, next_x1_scaled, page_height - next_y0_scaled]

                    # Проверяем вертикальный промежуток
                    vertical_gap = y0_scaled - next_y1_scaled
                    if vertical_gap > average_font_size * 2:
                        break

                    # Добавляем строку в заголовок таблицы
                    table_signature_boxes.append(next_coords_transformed)
                    y0_scaled = next_y0_scaled
                    idx += 1

                # Определяем общий бокс заголовка таблицы
                min_x = min(box[0] for box in table_signature_boxes)
                min_y = min(box[1] for box in table_signature_boxes)
                max_x = max(box[2] for box in table_signature_boxes)
                max_y = max(box[3] for box in table_signature_boxes)
                annotations['table_signature'].append([min_x, min_y, max_x, max_y])

                # Теперь берем следующий параграф и считаем его таблицей
                if idx < len(elements):
                    next_elem = elements[idx]
                    next_text_line = next_elem['text_line']
                    next_text = next_elem['text']
                    next_font_size = next_elem['font_size']
                    next_is_bold = next_elem['is_bold']
                    next_is_italic = next_elem['is_italic']
                    next_x0, next_y0, next_x1, next_y1 = next_text_line.bbox
                    next_x0_scaled = next_x0 * SCALING_FACTOR
                    next_y0_scaled = next_y0 * SCALING_FACTOR
                    next_x1_scaled = next_x1 * SCALING_FACTOR
                    next_y1_scaled = next_y1 * SCALING_FACTOR
                    next_coords_transformed = [next_x0_scaled, page_height - next_y1_scaled, next_x1_scaled, page_height - next_y0_scaled]

                    # Собираем строки, пока они образуют параграф (то есть таблицу)
                    table_boxes = [next_coords_transformed]
                    idx += 1
                    y0_scaled = next_y0_scaled
                    while idx < len(elements):
                        next_elem = elements[idx]
                        next_text_line = next_elem['text_line']
                        next_text = next_elem['text']
                        next_x0, next_y0, next_x1, next_y1 = next_text_line.bbox
                        next_x0_scaled = next_x0 * SCALING_FACTOR
                        next_y0_scaled = next_y0 * SCALING_FACTOR
                        next_x1_scaled = next_x1 * SCALING_FACTOR
                        next_y1_scaled = next_y1 * SCALING_FACTOR
                        next_coords_transformed = [next_x0_scaled, page_height - next_y1_scaled, next_x1_scaled, page_height - next_y0_scaled]

                        # Проверяем вертикальный промежуток
                        vertical_gap = y0_scaled - next_y1_scaled
                        if vertical_gap > average_font_size * 2:
                            break

                        # Останавливаемся, если встречаем новый заголовок таблицы или другой заголовок
                        if re.match(r'^\s*(табл\.?|таблица)\s*\d+', next_text.lower()) or \
                           re.match(r'^\s*(рис\.?|рисунок)\s*\d+', next_text.lower()):
                            break
                        # Добавляем элемент таблицы
                        table_boxes.append(next_coords_transformed)
                        y0_scaled = next_y0_scaled
                        idx += 1

                    if table_boxes:
                        # Определяем общий бокс таблицы
                        min_x = min(box[0] for box in table_boxes)
                        min_y = min(box[1] for box in table_boxes)
                        max_x = max(box[2] for box in table_boxes)
                        max_y = max(box[3] for box in table_boxes)
                        annotations['table'].append([min_x, min_y, max_x, max_y])
                continue

            # Обработка формул
            formula_match = re.match(r'^\s*формула', text.lower())
            if formula_match or (any(color == 1.0 for color in font_colors) and is_centered_text(text_line, page_width)):
                if current_paragraph is not None:
                    annotations['paragraph'].append(current_paragraph)
                    current_paragraph = None
                # Ищем изображение над текущей строкой
                formula_image = None
                min_distance = None
                for img in images:
                    img_y0 = img['y0']
                    img_y1 = img['y1']
                    if img_y1 < y1_scaled and (min_distance is None or (y1_scaled - img_y1) < min_distance):
                        min_distance = y1_scaled - img_y1
                        formula_image = img
                if formula_image:
                    annotations['formula'].append(tuple(formula_image['bbox']))
                    # Удаляем изображение из списка рисунков, чтобы оно не попало в "picture"
                    images.remove(formula_image)
                idx += 1
                continue

            # Обработка параграфов
            if font_size >= average_font_size + 2 and (is_bold or is_italic):
                if current_paragraph is not None:
                    annotations['paragraph'].append(current_paragraph)
                    current_paragraph = None
                annotations['title'].append(coords_transformed)
            elif not in_numbered_list and not in_bulleted_list:
                # Проверяем, что текущая строка не является названием таблицы, рисунка или частью футера/хедера
                if not re.match(r'^\s*(табл\.?|таблица|рис\.?|рисунок|формула)\s*\d*', text.lower()):
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

        # Обработка оставшихся изображений (которые не формулы)
        for img in images:
            img_bbox = tuple(img['bbox'])
            if img_bbox not in annotations.get('formula', []):
                annotations['picture'].append(img['bbox'])

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
            "picture": annotations["picture"],
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
        print(f"Аннотации для страницы {page_number+1} сохранены в {json_path}.")

def is_centered_text(text_line, page_width, tolerance=20):
    """
    Проверяет, выровнен ли текст по центру страницы для выявления надписи "Формула" под рисунком.

    :param text_line: Объект LTTextLineHorizontal.
    :param page_width: Ширина страницы.
    :param tolerance: Допустимое отклонение в пикселях.
    :return: True, если текст выровнен по центру, иначе False.
    """
    x0, _, x1, _ = text_line.bbox
    text_width = x1 - x0
    page_center = page_width / 2
    text_center = (x0 + x1) / 2 * SCALING_FACTOR
    return abs(page_center - text_center) <= tolerance

if __name__ == "__main__":
    pdf_folder = "pdf"
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Обработка файла: {pdf_file}")
        extract_annotations_from_pdf(pdf_path)
