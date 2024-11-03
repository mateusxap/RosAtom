import os
import json
import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextBoxHorizontal, LTTextLineHorizontal, LTChar, LTFigure, LTImage
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
    
    # Настройки для парсинга
    laparams = LAParams()
    
    # Парсинг страниц PDF
    for page_number, page_layout in enumerate(extract_pages(pdf_path, laparams=laparams)):
        annotations = defaultdict(list)
        font_sizes = []
        elements = []
        images = []
        page_width = page_layout.bbox[2] * SCALING_FACTOR
        page_height = page_layout.bbox[3] * SCALING_FACTOR
        
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
                        for char in text_line:
                            if isinstance(char, LTChar):
                                sizes.append(char.size)
                                font_name = char.fontname.lower()
                                if 'bold' in font_name:
                                    is_bold = True
                                if 'italic' in font_name or 'oblique' in font_name:
                                    is_italic = True
                        if sizes:
                            font_size = sum(sizes) / len(sizes)
                            font_sizes.append(font_size)
                            elements.append({
                                'text_line': text_line,
                                'text': line_text,
                                'font_size': font_size,
                                'is_bold': is_bold,
                                'is_italic': is_italic
                            })
            elif isinstance(element, (LTFigure, LTImage)):
                # Собираем информацию об изображениях
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
        
        # Определяем средний размер шрифта
        if font_sizes:
            average_font_size = sum(font_sizes) / len(font_sizes)
        else:
            average_font_size = 0
        
        # Обработка текстовых элементов
        for idx, elem in enumerate(elements):
            text_line = elem['text_line']
            text = elem['text']
            font_size = elem['font_size']
            is_bold = elem['is_bold']
            is_italic = elem['is_italic']
            
            # Координаты
            x0, y0, x1, y1 = text_line.bbox
            x0_scaled = x0 * SCALING_FACTOR
            y0_scaled = y0 * SCALING_FACTOR
            x1_scaled = x1 * SCALING_FACTOR
            y1_scaled = y1 * SCALING_FACTOR
            coords_transformed = [x0_scaled, page_height - y1_scaled, x1_scaled, page_height - y0_scaled]
            
            # Проверка на колонтитулы
            if y1_scaled > page_height * 0.95:
                annotations['header'].append(coords_transformed)
                continue
            elif y0_scaled < page_height * 0.05:
                annotations['footer'].append(coords_transformed)
                continue
            
            # Логика определения элементов
            if font_size >= average_font_size + 2:
                annotations['title'].append(coords_transformed)
            elif re.match(r'^\s*(рис\.?|рисунок)\s*\d+', text.lower()):
                annotations['picture_signature'].append(coords_transformed)
            elif re.match(r'^\s*(табл\.?|таблица)\s*\d+', text.lower()):
                annotations['table_signature'].append(coords_transformed)
            elif re.match(r'^\d+\.', text.strip()):
                annotations['numbered_list'].append(coords_transformed)
            elif re.match(r'^[•\-\*]', text.strip()):
                annotations['marked_list'].append(coords_transformed)
            elif re.search(r'\[\d+\]', text):
                annotations['footnote'].append(coords_transformed)
            elif text.lower() == 'формула':
                formula_image = None
                min_distance = None
                for img in images:
                    img_y0 = img['y0']
                    img_y1 = img['y1']
                    if img_y1 < y0 and (min_distance is None or (y0 - img_y1) < min_distance):
                        min_distance = y0 - img_y1
                        formula_image = img
                if formula_image:
                    annotations['formula'].append(formula_image['bbox'])
                annotations['formula_caption'].append(coords_transformed)
            elif is_bold or is_italic:
                annotations['paragraph'].append(coords_transformed)
            else:
                annotations['paragraph'].append(coords_transformed)
        
        # Обработка оставшихся изображений (которые не формулы)
        for img in images:
            img_bbox = img['bbox']
            if img_bbox not in annotations.get('formula', []):
                annotations['picture'].append(img_bbox)
        
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
        json_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_number+1}.json"
        json_path = os.path.join(output_dir, json_name)
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
        print(f"Аннотации для страницы {page_number+1} сохранены в {json_path}.")

if __name__ == "__main__":
    pdf_folder = "pdf"
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Обработка файла: {pdf_file}")
        extract_annotations_from_pdf(pdf_path)
