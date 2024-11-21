import os
import cv2
import json
from ultralytics import YOLO
import supervision as sv

def process_images(model, input_dir, output_image_dir, output_json_dir):
    # Создаём директории для выходных данных, если они не существуют
    os.makedirs(output_image_dir, exist_ok=True)
    os.makedirs(output_json_dir, exist_ok=True)
    
    # Получаем список изображений
    image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Определяем цвета для классов (опционально, если необходимо для визуализации)
    class_colors = [
        sv.Color(255, 0, 0),    # Красный для "Title"
        sv.Color(0, 255, 0),    # Зеленый для "Paragraph"
        sv.Color(0, 0, 255),    # Синий для "Table"
        sv.Color(255, 255, 0),  # Желтый для "Picture"
        sv.Color(255, 0, 255),  # Магента для "Table_signature"
        sv.Color(0, 255, 255),  # Циан для "Picture_signature"
        sv.Color(128, 0, 128),  # Фиолетовый для "Numbered_list"
        sv.Color(128, 128, 0),  # Оливковый для "Marked_list"
        sv.Color(128, 128, 128),# Серый для "Header"
        sv.Color(0, 128, 128),  # Бирюзовый для "Footer"
        sv.Color(64, 0, 0),      # Тёмно-красный для "Footnote"
        sv.Color(128, 64, 0),    # Коричневый для "Formula"
        sv.Color(128, 0, 64)     # Тёмно-фиолетовый для "Graph"
    ]
    
    # Инициализируем аннотаторы (опционально)
    box_annotator = sv.BoxAnnotator(
        color=sv.ColorPalette(class_colors),
        thickness=3
    )
    
    label_annotator = sv.LabelAnnotator(
        color=sv.ColorPalette(class_colors),
        text_color=sv.Color(255, 255, 255)
    )
    
    # Словарь для соответствия class_id ключам JSON
    class_id_to_key = {
        0: "title",
        1: "paragraph",
        2: "table",
        3: "picture",
        4: "table_signature",
        5: "picture_signature",
        6: "numbered_list",
        7: "marked_list",
        8: "header",
        9: "footer",
        10: "footnote",
        11: "formula",
        12: "graph"
    }
    
    # Обработка каждого изображения
    for image_file in image_files:
        # Полный путь к изображению
        image_path = os.path.join(input_dir, image_file)
        
        # Загружаем изображение
        image = cv2.imread(image_path)
        if image is None:
            print(f"Не удалось загрузить изображение: {image_file}")
            continue
        
        image_height, image_width = image.shape[:2]
        
        # Выполняем детекцию
        results = model(image_path, conf=0.2, iou=0.8)[0]
        
        # Конвертируем результаты в формат detections
        detections = sv.Detections.from_ultralytics(results)
        
        # (Опционально) Рисуем боксы и сохраняем аннотированное изображение
        annotated_image = box_annotator.annotate(
            scene=image.copy(),
            detections=detections
        )
        
        annotated_image = label_annotator.annotate(
            scene=annotated_image,
            detections=detections
        )
        
        # Формируем путь для сохранения аннотированного изображения
        output_image_path = os.path.join(output_image_dir, f"annotated_{image_file}")
        cv2.imwrite(output_image_path, annotated_image)
        
        print(f"Обработано изображение: {image_file}")
        
        # Инициализируем структуру для текущего изображения
        image_annotation = {
            "image_height": image_height,
            "image_width": image_width,
            "image_path": image_path,
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
            "graph": []
        }
        
        # Итерация по всем обнаруженным боксам
        for idx, box in enumerate(detections.xyxy):
            class_id = int(detections.class_id[idx])
            if class_id in class_id_to_key:
                key = class_id_to_key[class_id]
                # Преобразуем координаты в список из 4 целых чисел
                bbox = [
                    int(box[0]),  # x1
                    int(box[1]),  # y1
                    int(box[2]),  # x2
                    int(box[3])   # y2
                ]
                image_annotation[key].append(bbox)
            else:
                print(f"Неизвестный class_id {class_id} в изображении {image_file}")
        
        # Формируем имя JSON-файла (например, image1.json)
        base_name = os.path.splitext(image_file)[0]
        json_file_name = f"{base_name}.json"
        json_file_path = os.path.join(output_json_dir, json_file_name)
        
        # Сохраняем аннотацию в отдельный JSON-файл
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(image_annotation, json_file, ensure_ascii=False, indent=4)
        
        print(f"JSON-файл сохранён: {json_file_name}")
    

def main():
    # Загрузка модели
    model = YOLO('final_best.pt')
    
    # Путь к входной директории с изображениями
    input_dir = 'input/images'
    
    # Путь к выходной директории для аннотированных изображений
    output_image_dir = 'output/images_annotated'
    
    # Путь к выходной директории для JSON-файлов
    output_json_dir = 'output/json_annotations'
    
    # Обработка изображений и генерация JSON
    process_images(model, input_dir, output_image_dir, output_json_dir)

if __name__ == "__main__":
    main()

