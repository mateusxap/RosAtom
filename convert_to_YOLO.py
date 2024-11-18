import json
import os
import glob
import shutil
import yaml
from pathlib import Path

# Функция для нормализации координат для YOLO
def convert_to_yolo_format(box, img_width, img_height):
    x_min, y_min, x_max, y_max = box
    x_center = ((x_min + x_max) / 2) / img_width
    y_center = ((y_min + y_max) / 2) / img_height
    width = (x_max - x_min) / img_width
    height = (y_max - y_min) / img_height
    return x_center, y_center, width, height

# Основная функция для преобразования JSON в YOLO формат
def json_to_yolo(json_data, output_path, image_name):
    img_width = json_data["image_width"]
    img_height = json_data["image_height"]
    
    class_map = {
        "title": 0,
        "paragraph": 1,
        "table": 2,
        "picture": 3,
        "table_signature": 4,
        "picture_signature": 5,
        "numbered_list": 6,
        "marked_list": 7,
        "header": 8,
        "footer": 9,
        "footnote": 10,
        "formula": 11,
        "graph": 12
    }

    yolo_annotations = []
    for label, boxes in json_data.items():
        if label in class_map:
            class_id = class_map[label]
            for box in boxes:
                x_center, y_center, width, height = convert_to_yolo_format(box, img_width, img_height)
                yolo_annotations.append(f"{class_id} {x_center} {y_center} {width} {height}")

    # Запись аннотаций в файл
    yolo_path = os.path.join(output_path, "labels", f"{image_name}.txt")
    with open(yolo_path, "w") as f:
        f.write("\n".join(yolo_annotations))

# Создание YAML файла
def create_yaml_file(output_directory, classes):
    yaml_data = {
        'train': os.path.join(output_directory, 'train/images'),
        'val': os.path.join(output_directory, 'val/images'),
        'nc': len(classes),
        'names': classes
    }
    
    yaml_path = os.path.join(output_directory, 'dataset.yaml')
    with open(yaml_path, 'w') as yaml_file:
        yaml.dump(yaml_data, yaml_file, default_flow_style=False)

# Создание структуры папок
def create_directory_structure(base_path):
    os.makedirs(os.path.join(base_path, "train/images"), exist_ok=True)
    os.makedirs(os.path.join(base_path, "train/labels"), exist_ok=True)
    os.makedirs(os.path.join(base_path, "val/images"), exist_ok=True)
    os.makedirs(os.path.join(base_path, "val/labels"), exist_ok=True)

# Основная обработка JSON файлов и копирование изображений
def process_json_files(input_directory, output_directory, image_directory):
    create_directory_structure(output_directory)

    json_files = glob.glob(os.path.join(input_directory, "*.json"))
    classes = [
        "title", "paragraph", "table", "picture", "table_signature", 
        "picture_signature", "numbered_list", "marked_list", "header", 
        "footer", "footnote", "formula", "graph"
    ]

    # Разделение данных на обучающие и валидационные (80% / 20%)
    split_index = int(0.8 * len(json_files))
    train_files = json_files[:split_index]
    val_files = json_files[split_index:]

    for json_file in train_files:
        with open(json_file, "r") as file:
            json_data = json.load(file)
            image_name = Path(json_data["image_path"]).stem
            json_to_yolo(json_data, os.path.join(output_directory, "train"), image_name)
            image_src = os.path.join(image_directory, f"{image_name}.png")  # Измените расширение, если нужно
            image_dst = os.path.join(output_directory, "train/images", f"{image_name}.png")
            shutil.copy(image_src, image_dst)

    for json_file in val_files:
        with open(json_file, "r") as file:
            json_data = json.load(file)
            image_name = Path(json_data["image_path"]).stem
            json_to_yolo(json_data, os.path.join(output_directory, "val"), image_name)
            image_src = os.path.join(image_directory, f"{image_name}.png")  # Измените расширение, если нужно
            image_dst = os.path.join(output_directory, "val/images", f"{image_name}.png")
            shutil.copy(image_src, image_dst)

    # Создание YAML файла
    create_yaml_file(output_directory, classes)

# Параметры путей
input_directory = "json"
output_directory = "dataset"
image_directory = "image"

# Запуск обработки
process_json_files(input_directory, output_directory, image_directory)
