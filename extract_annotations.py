import os
import json
import re
from collections import Counter
from pdfminer.high_level import extract_pages
from pdfminer.layout import (
    LTPage, LTTextContainer, LTTextLine, LTChar, LTAnno,
    LTImage, LTFigure, LTCurve, LTLine, LTRect
)

def extract_annotations_from_pdf():
    pdf_dir = 'pdf'
    json_dir = 'json'

    # Создаем директорию 'json', если она не существует
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)

    # Получаем список всех файлов в папке 'pdf'
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        pdf_name = os.path.splitext(pdf_file)[0]

        try:
            print(f'Извлекаем аннотации из {pdf_file}...')
            pages = list(extract_pages(pdf_path))

            for page_number, page_layout in enumerate(pages):
                page_height = page_layout.height
                page_width = page_layout.width

                annotations = {
                    "image_height": int(page_height),
                    "image_width": int(page_width),
                    "image_path": f"image/{pdf_name}_{page_number+1}.png",
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

                font_sizes = []
                text_lines = []

                # Собираем информацию о размерах шрифтов и текстовых линиях
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        for text_line in element:
                            if isinstance(text_line, LTTextLine):
                                line_text = ''
                                line_fonts = []
                                line_font_sizes = []

                                for character in text_line:
                                    if isinstance(character, LTChar):
                                        line_text += character.get_text()
                                        line_fonts.append(character.fontname)
                                        line_font_sizes.append(character.size)
                                    elif isinstance(character, LTAnno):
                                        line_text += character.get_text()

                                if line_font_sizes:
                                    avg_font_size = sum(line_font_sizes) / len(line_font_sizes)
                                    font_sizes.append(avg_font_size)
                                    text_lines.append({
                                        'text_line': text_line,
                                        'text': line_text.strip(),
                                        'font_size': avg_font_size,
                                        'fonts': line_fonts,
                                        'coords': [text_line.x0, text_line.y0, text_line.x1, text_line.y1],
                                    })

                if not font_sizes:
                    average_font_size = 0
                else:
                    # Определяем самый частый размер шрифта на странице (основной текст)
                    average_font_size = Counter(font_sizes).most_common(1)[0][0]

                # Обрабатываем собранные текстовые линии
                for item in text_lines:
                    text = item['text']
                    font_size = item['font_size']
                    coords = item['coords']
                    fonts = item['fonts']

                    is_bold = any('bold' in font.lower() or 'bd' in font.lower() for font in fonts)
                    is_italic = any('italic' in font.lower() or 'it' in font.lower() or 'oblique' in font.lower() for font in fonts)

                    # Преобразуем координаты для соответствия системе координат изображения (начало в верхнем левом углу)
                    coords_transformed = [coords[0], page_height - coords[3], coords[2], page_height - coords[1]]

                    # Проверка на колонтитулы
                    if coords[1] > page_height * 0.9:
                        # Верхний колонтитул
                        annotations['header'].append(coords_transformed)
                        continue
                    elif coords[3] < page_height * 0.1:
                        # Нижний колонтитул
                        annotations['footer'].append(coords_transformed)
                        continue

                    # Логика определения элементов
                    if font_size >= average_font_size + 2:
                        # Если размер шрифта значительно больше среднего, считаем это заголовком
                        annotations['title'].append(coords_transformed)
                    elif re.match(r'^\s*(рис\.|рисунок)\s*\d+', text.lower()):
                        annotations['picture_signature'].append(coords_transformed)
                    elif re.match(r'^\s*(табл\.|таблица)\s*\d+', text.lower()):
                        annotations['table_signature'].append(coords_transformed)
                    elif re.match(r'^\d+\.', text.strip()):
                        annotations['numbered_list'].append(coords_transformed)
                    elif re.match(r'^[•\-\*]', text.strip()):
                        annotations['marked_list'].append(coords_transformed)
                    elif is_bold or is_italic:
                        annotations['paragraph'].append(coords_transformed)
                    else:
                        annotations['paragraph'].append(coords_transformed)

                # Рекурсивная функция для поиска изображений и формул
                def parse_figure(lt_obj):
                    if isinstance(lt_obj, LTImage):
                        # Добавляем координаты изображения
                        coords = [lt_obj.x0, lt_obj.y0, lt_obj.x1, lt_obj.y1]
                        coords_transformed = [coords[0], page_height - coords[3], coords[2], page_height - coords[1]]
                        annotations['picture'].append(coords_transformed)
                    elif isinstance(lt_obj, LTFigure):
                        for obj in lt_obj:
                            parse_figure(obj)
                    elif isinstance(lt_obj, (LTCurve, LTLine, LTRect)):
                        # Возможные формулы или графики
                        coords = [lt_obj.x0, lt_obj.y0, lt_obj.x1, lt_obj.y1]
                        coords_transformed = [coords[0], page_height - coords[3], coords[2], page_height - coords[1]]
                        annotations['formula'].append(coords_transformed)
                    elif isinstance(lt_obj, LTTextContainer):
                        # Возможные формулы, представленные в виде текста
                        for text_line in lt_obj:
                            if isinstance(text_line, LTTextLine):
                                line_text = ''
                                for character in text_line:
                                    if isinstance(character, LTChar):
                                        line_text += character.get_text()
                                    elif isinstance(character, LTAnno):
                                        line_text += character.get_text()
                                if '$' in line_text or '\\(' in line_text or '\\[' in line_text:
                                    coords = [text_line.x0, text_line.y0, text_line.x1, text_line.y1]
                                    coords_transformed = [coords[0], page_height - coords[3], coords[2], page_height - coords[1]]
                                    annotations['formula'].append(coords_transformed)

                # Проходим по элементам страницы для поиска изображений и формул
                for element in page_layout:
                    if isinstance(element, (LTFigure, LTImage, LTCurve, LTLine, LTRect, LTTextContainer)):
                        parse_figure(element)

                # Сохраняем аннотации в JSON-файл
                json_name = f"{pdf_name}_{page_number+1}.json"
                json_path = os.path.join(json_dir, json_name)
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(annotations, json_file, ensure_ascii=False, indent=4)

                print(f'Аннотации для страницы {page_number+1} сохранены.')

        except Exception as e:
            print(f'Ошибка при извлечении аннотаций из {pdf_file}: {e}')

if __name__ == '__main__':
    extract_annotations_from_pdf()
