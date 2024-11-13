import os
import json
import shutil
from pathlib import Path
import random
import yaml  # Нужно установить библиотеку PyYAML: pip install pyyaml

def create_detr_dataset(source_image_dir, source_json_dir):
    # Создание основной папки
    base_dir = "dataset"
    train_image_dir = os.path.join(base_dir, "train", "image")
    test_image_dir = os.path.join(base_dir, "test", "image")
    train_json_dir = os.path.join(base_dir, "train", "json")
    test_json_dir = os.path.join(base_dir, "test", "json")
    
    os.makedirs(train_image_dir, exist_ok=True)
    os.makedirs(test_image_dir, exist_ok=True)
    os.makedirs(train_json_dir, exist_ok=True)
    os.makedirs(test_json_dir, exist_ok=True)
    
    categories_set = set()  # для сбора уникальных категорий
    
    # Сбор списка изображений
    image_files = [f for f in os.listdir(source_image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    random.shuffle(image_files)  # Перемешиваем для случайного распределения
    
    # Разделение на 80/20
    split_index = int(0.8 * len(image_files))
    train_files = image_files[:split_index]
    test_files = image_files[split_index:]
    
    # Обработка изображений и JSON файлов
    for image_file in image_files:
        src_image_path = os.path.join(source_image_dir, image_file)
        filename = Path(image_file).stem
        
        # Определяем папку назначения
        if image_file in train_files:
            dst_image_path = os.path.join(train_image_dir, image_file)
            dst_json_dir = train_json_dir
        else:
            dst_image_path = os.path.join(test_image_dir, image_file)
            dst_json_dir = test_json_dir
        
        shutil.copy(src_image_path, dst_image_path)
        
        # Поиск и обработка связанного JSON файла
        src_json_path = os.path.join(source_json_dir, f"{filename}.json")
        if os.path.exists(src_json_path):
            with open(src_json_path, 'r') as f:
                entry = json.load(f)
            
            # Преобразование структуры в требуемый формат для DETR
            annotations = []
            for category, boxes in entry.items():
                if category in ["image_height", "image_width", "image_path"]:
                    continue
                for box in boxes:
                    annotations.append({
                        "category": category,
                        "box": box  # оставляем в формате [x1, y1, x2, y2]
                    })
                    categories_set.add(category)  # сбор уникальных категорий
            
            # Создание нового JSON для DETR
            detr_json = {
                "image_path": os.path.join("image", image_file),  # Путь к изображению относительно папки train/test
                "annotations": annotations
            }
            
            # Сохранение преобразованного JSON
            json_output_path = os.path.join(dst_json_dir, f"{filename}.json")
            with open(json_output_path, 'w') as json_file:
                json.dump(detr_json, json_file, indent=4)
    
    # Создание yaml файла с относительными путями
    yaml_content = {
        'train': 'dataset/train/image',  # относительный путь к тренировочным данным
        'test': 'dataset/test/image',    # относительный путь к тестовым данным
        'nc': len(categories_set),
        'names': list(categories_set)
    }
    
    yaml_path = os.path.join(base_dir, 'config.yaml')
    with open(yaml_path, 'w') as yaml_file:
        yaml.dump(yaml_content, yaml_file, default_flow_style=False)

    print("Данные преобразованы, yaml файл создан, и сохранены для обучения DETR.")

# Указание путей к исходным папкам
source_image_dir = "image"
source_json_dir = "json"

# Выполнение функции
create_detr_dataset(source_image_dir, source_json_dir)
