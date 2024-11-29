import os
import shutil
import json
import yaml
import random
from tqdm import tqdm

# Пути к исходным данным
images_src_folder = 'image'  # Замените на ваш путь к папке с изображениями
annotations_src_folder = 'json'  # Замените на ваш путь к папке с JSON файлами

# Пути к новому датасету
dataset_folder = 'dataset'
images_dst_folder = os.path.join(dataset_folder, 'images')
annotations_dst_folder = os.path.join(dataset_folder, 'annotations')

# Создание необходимых папок
os.makedirs(os.path.join(images_dst_folder, 'train'), exist_ok=True)
os.makedirs(os.path.join(images_dst_folder, 'val'), exist_ok=True)
os.makedirs(annotations_dst_folder, exist_ok=True)

# Получение списка файлов изображений
image_files = [f for f in os.listdir(images_src_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# Перемешивание и разделение на train/val (80%/20%)
random.shuffle(image_files)
split_index = int(0.8 * len(image_files))
train_images = image_files[:split_index]
val_images = image_files[split_index:]

# Копирование изображений
for img_name in tqdm(train_images, desc="Копирование обучающих изображений"):
    shutil.copy(os.path.join(images_src_folder, img_name), os.path.join(images_dst_folder, 'train', img_name))

for img_name in tqdm(val_images, desc="Копирование валидационных изображений"):
    shutil.copy(os.path.join(images_src_folder, img_name), os.path.join(images_dst_folder, 'val', img_name))

# Определение категорий
categories_list = [
    'title', 'paragraph', 'table', 'picture', 'table_signature',
    'picture_signature', 'numbered_list', 'marked_list', 'header',
    'footer', 'footnote', 'formula', 'graph'
]

# Создание словаря категорий с идентификаторами, начиная с 0
category_id_map = {category: idx for idx, category in enumerate(categories_list)}

def convert_annotations(image_list, images_folder, annotations_src_folder, output_json_path):
    coco_dataset = {
        "images": [],
        "annotations": [],
        "categories": []
    }
    annotation_id = 1

    # Добавление категорий
    for category_name, category_id in category_id_map.items():
        category = {
            "id": category_id,
            "name": category_name
        }
        coco_dataset["categories"].append(category)

    for idx, img_name in enumerate(tqdm(image_list, desc="Обработка аннотаций")):
        json_filename = os.path.splitext(img_name)[0] + '.json'
        json_path = os.path.join(annotations_src_folder, json_filename)
        if not os.path.exists(json_path):
            print(f"JSON файл для изображения {img_name} не найден. Пропуск.")
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        width = data.get('image_width')
        height = data.get('image_height')

        image_info = {
            "id": idx + 1,
            "file_name": img_name,
            "width": width,
            "height": height
        }
        coco_dataset["images"].append(image_info)

        for category_name in categories_list:
            if category_name in data and data[category_name]:
                bboxes = data[category_name]
                for bbox in bboxes:
                    x_min, y_min, x_max, y_max = bbox
                    # Проверка на корректность координат
                    x_min = max(0, x_min)
                    y_min = max(0, y_min)
                    x_max = min(width, x_max)
                    y_max = min(height, y_max)
                    bbox_width = x_max - x_min
                    bbox_height = y_max - y_min

                    if bbox_width <= 0 or bbox_height <= 0:
                        print(f"Некорректные координаты для bbox в {json_filename}. Пропуск.")
                        continue

                    area = bbox_width * bbox_height
                    coco_annotation = {
                        "id": annotation_id,
                        "image_id": idx + 1,
                        "category_id": category_id_map[category_name],
                        "bbox": [x_min, y_min, bbox_width, bbox_height],
                        "area": area,
                        "iscrowd": 0
                    }
                    coco_dataset["annotations"].append(coco_annotation)
                    annotation_id += 1

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(coco_dataset, f, ensure_ascii=False, indent=4)

# Преобразование аннотаций
convert_annotations(train_images, os.path.join(images_dst_folder, 'train'), annotations_src_folder, os.path.join(annotations_dst_folder, 'instances_train.json'))
convert_annotations(val_images, os.path.join(images_dst_folder, 'val'), annotations_src_folder, os.path.join(annotations_dst_folder, 'instances_val.json'))

# Создание файла data.yaml
data_yaml = {
    'train': os.path.abspath(os.path.join(images_dst_folder, 'train')),
    'val': os.path.abspath(os.path.join(images_dst_folder, 'val')),
    'nc': len(categories_list),
    'names': categories_list
}

with open(os.path.join(dataset_folder, 'data.yaml'), 'w', encoding='utf-8') as f:
    yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True)

print("Датасет успешно подготовлен.")
