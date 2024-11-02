import os
import json
from PIL import Image, ImageDraw, ImageFont

# Папки с данными
IMAGE_DIR = 'image'
JSON_DIR = 'json'
ANNOTATED_IMAGE_DIR = 'annotated_images'

# Создаём папку для аннотированных изображений, если она не существует
os.makedirs(ANNOTATED_IMAGE_DIR, exist_ok=True)

# Цвета для разных типов элементов (RGB)
COLORS = {
    "title": (255, 0, 0),             # Красный
    "paragraph": (0, 255, 0),         # Зелёный
    "table": (0, 0, 255),             # Синий
    "picture": (255, 165, 0),         # Оранжевый
    "table_signature": (128, 0, 128), # Фиолетовый
    "picture_signature": (0, 128, 128), # Тёмно-голубой
    "numbered_list": (255, 192, 203), # Розовый
    "marked_list": (165, 42, 42),     # Коричневый
    "header": (255, 215, 0),          # Золотой
    "footer": (0, 255, 255),          # Голубой
    "footnote": (173, 255, 47),       # Зелёно-жёлтый
    "formula": (255, 105, 180)        # Горячий розовый
}

# Функция для получения размера текста
def get_text_size(draw, text, font):
    try:
        # Используем textbbox для получения размера текста
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return (width, height)
    except AttributeError:
        # Для более старых версий Pillow используем getsize
        return font.getsize(text)

# Функция для преобразования координат
def transform_coords(coords, page_width, page_height, image_width, image_height):
    x0, y0, x1, y1 = coords
    scale_x = image_width / page_width
    scale_y = image_height / page_height

    # Масштабируем координаты
    x0 = x0 * scale_x
    x1 = x1 * scale_x
    y0 = y0 * scale_y
    y1 = y1 * scale_y

    # Инвертируем координаты по оси Y
    y0 = image_height - y0
    y1 = image_height - y1

    # Убедимся, что y0 < y1 после инвертирования
    y0, y1 = min(y0, y1), max(y0, y1)

    return [x0, y0, x1, y1]

# Функция для рисования боксов и меток
def draw_boxes(image_path, annotations, output_path):
    try:
        with Image.open(image_path).convert("RGBA") as img:
            image_width, image_height = img.size

            overlay = Image.new('RGBA', img.size, (255,255,255,0))
            draw = ImageDraw.Draw(overlay)
            # Попробуем загрузить стандартный шрифт
            try:
                font = ImageFont.truetype("arial.ttf", size=15)
            except IOError:
                # Если шрифт не найден, используем стандартный
                font = ImageFont.load_default()
            
            # Получаем размеры страницы из аннотаций
            page_width = annotations.get("image_width")
            page_height = annotations.get("image_height")

            if not page_width or not page_height:
                print(f"В аннотациях отсутствуют размеры страницы. Пропускаем {image_path}.")
                return

            for element_type, boxes in annotations.items():
                if element_type not in COLORS:
                    continue  # Игнорируем неизвестные типы
                color = COLORS[element_type]
                
                for box in boxes:
                    if not isinstance(box, (list, tuple)):
                        print(f"Предупреждение: Ожидался список или кортеж для '{element_type}', но получен {type(box)}. Пропускаем.")
                        continue
                    if len(box) != 4:
                        print(f"Предупреждение: Ожидалось 4 элемента в коробке для '{element_type}', но получено {len(box)}. Пропускаем.")
                        continue
                    if not all(isinstance(coord, (int, float)) for coord in box):
                        print(f"Предупреждение: Координаты должны быть числами для '{element_type}', но получены {box}. Пропускаем.")
                        continue

                    # Преобразуем координаты
                    x1, y1, x2, y2 = transform_coords(box, page_width, page_height, image_width, image_height)

                    # Рисуем полупрозрачный прямоугольник
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                    # Добавляем текст метки
                    text = element_type
                    text_size = get_text_size(draw, text, font)
                    # Позиционирование текста: верхний левый угол прямоугольника
                    text_x = x1
                    text_y = y1 - text_size[1] if y1 - text_size[1] > 0 else y1
                    # Рисуем фон для текста
                    draw.rectangle([text_x, text_y, text_x + text_size[0], text_y + text_size[1]], fill=color)
                    # Рисуем текст
                    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
            
            # Объединяем оригинальное изображение с наложенным
            annotated_img = Image.alpha_composite(img, overlay)
            
            # Сохраняем аннотированное изображение
            annotated_img.convert("RGB").save(output_path)
            print(f'Аннотированное изображение сохранено: {output_path}')
    except Exception as e:
        print(f'Ошибка при обработке изображения {image_path}: {e}')

# Основная функция
def annotate_images():
    # Получаем список всех JSON-файлов
    json_files = [f for f in os.listdir(JSON_DIR) if f.lower().endswith('.json')]
    
    if not json_files:
        print("Папка 'json' пуста. Нет файлов для обработки.")
        return
    
    for json_file in json_files:
        json_path = os.path.join(JSON_DIR, json_file)
        
        # Загружаем аннотации из JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
        except Exception as e:
            print(f'Ошибка при чтении JSON-файла {json_file}: {e}')
            continue
        
        # Получаем путь к соответствующему изображению
        image_path = annotations.get("image_path")
        if not image_path:
            print(f'В JSON-файле {json_file} отсутствует поле "image_path". Пропускаем.')
            continue
        
        # Полный путь к изображению
        image_full_path = os.path.join('.', image_path)
        if not os.path.exists(image_full_path):
            print(f'Изображение {image_full_path} не найдено. Пропускаем.')
            continue
        
        # Путь для сохранения аннотированного изображения
        annotated_image_name = os.path.splitext(json_file)[0] + '_annotated.png'
        annotated_image_path = os.path.join(ANNOTATED_IMAGE_DIR, annotated_image_name)
        
        # Рисуем боксы и сохраняем изображение
        draw_boxes(image_full_path, annotations, annotated_image_path)

if __name__ == '__main__':
    annotate_images()
