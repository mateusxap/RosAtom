import os
import json
import shutil
from pathlib import Path
import random
import yaml  # Убедитесь, что библиотека установлена: pip install pyyaml
from PIL import Image

def create_coco_dataset(source_image_dir, source_json_dir):
    # Создание основной папки
    base_dir = "dataset"
    train_image_dir = os.path.join(base_dir, "train", "images")
    test_image_dir = os.path.join(base_dir, "test", "images")
    train_json_dir = os.path.join(base_dir, "train")
    test_json_dir = os.path.join(base_dir, "test")
    
    os.makedirs(train_image_dir, exist_ok=True)
    os.makedirs(test_image_dir, exist_ok=True)
    
    # Сбор списка изображений
    image_files = [f for f in os.listdir(source_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    random.shuffle(image_files)  # Перемешиваем для случайного распределения
    
    # Разделение на 80/20
    split_index = int(0.8 * len(image_files))
    train_files = image_files[:split_index]
    test_files = image_files[split_index:]
    
    # Загрузка конфигурации из YAML файла для категорий
    yaml_path = os.path.join(base_dir, 'config.yaml')
    if not os.path.exists(yaml_path):
        print(f"YAML файл не найден по пути: {yaml_path}")
        return
    
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)
    
    class_names = config.get('names', [])
    if not class_names:
        print("Список классов пуст. Проверьте YAML файл.")
        return
    
    # Создание маппинга классов в индексы
    class_to_idx = {cls_name: idx for idx, cls_name in enumerate(class_names, start=1)}  # start=1, так как 0 обычно зарезервирован для фона
    
    # Инициализация структур данных для COCO
    coco_train = {
        "images": [],
        "annotations": [],
        "categories": []
    }
    coco_test = {
        "images": [],
        "annotations": [],
        "categories": []
    }
    
    # Заполнение списка категорий
    categories = []
    for cls_name, cls_id in class_to_idx.items():
        categories.append({
            "id": cls_id,
            "name": cls_name,
            "supercategory": "none"
        })
    coco_train["categories"] = categories
    coco_test["categories"] = categories  # Одинаковые категории для train и test
    
    annotation_id = 1  # Уникальный ID для аннотаций
    image_id = 1        # Уникальный ID для изображений
    
    # Функция для обработки выборки
    def process_files(files, split, coco):
        nonlocal annotation_id, image_id
        for image_file in files:
            src_image_path = os.path.join(source_image_dir, image_file)
            filename = Path(image_file).stem
            
            # Определяем папку назначения
            if split == "train":
                dst_image_path = os.path.join(train_image_dir, image_file)
            else:
                dst_image_path = os.path.join(test_image_dir, image_file)
            
            shutil.copy(src_image_path, dst_image_path)
            
            # Получение размеров изображения
            try:
                with Image.open(src_image_path) as img:
                    width, height = img.size
            except Exception as e:
                print(f"Ошибка при открытии изображения {src_image_path}: {e}")
                continue
            
            # Создание записи об изображении
            image_info = {
                "id": image_id,
                "file_name": image_file,
                "width": width,
                "height": height
            }
            coco["images"].append(image_info)
            
            # Поиск и обработка связанного JSON файла
            src_json_path = os.path.join(source_json_dir, f"{filename}.json")
            if os.path.exists(src_json_path):
                try:
                    with open(src_json_path, 'r') as f:
                        entry = json.load(f)
                except Exception as e:
                    print(f"Ошибка при чтении JSON файла {src_json_path}: {e}")
                    image_id += 1
                    continue
                
                # Перебор всех категорий в JSON
                for category_name, boxes in entry.items():
                    if category_name in ["image_height", "image_width", "image_path"]:
                        continue  # Пропускаем служебные поля
                    if category_name not in class_to_idx:
                        print(f"Категория '{category_name}' не найдена в YAML файле. Пропускаем.")
                        continue
                    category_id = class_to_idx[category_name]
                    
                    for box in boxes:
                        if len(box) != 4:
                            print(f"Некорректный bbox для изображения {image_file}: {box}")
                            continue
                        x_min, y_min, x_max, y_max = box
                        bbox_width = max(0, x_max - x_min)
                        bbox_height = max(0, y_max - y_min)
                        area = bbox_width * bbox_height
                        
                        # Проверка корректности bbox
                        if bbox_width <= 0 or bbox_height <= 0:
                            print(f"Некорректные размеры bbox для изображения {image_file}: {box}")
                            continue
                        
                        annotation = {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": category_id,
                            "bbox": [x_min, y_min, bbox_width, bbox_height],
                            "area": area,
                            "iscrowd": 0
                        }
                        coco["annotations"].append(annotation)
                        annotation_id += 1
            else:
                print(f"JSON файл не найден для изображения: {image_file}")
            
            image_id += 1
    
    # Обработка тренировочных и тестовых файлов
    print("Обработка тренировочных файлов...")
    process_files(train_files, "train", coco_train)
    
    print("Обработка тестовых файлов...")
    process_files(test_files, "test", coco_test)
    
    # Проверка наличия аннотаций
    if not coco_train["annotations"]:
        print("Предупреждение: В тренировочном наборе отсутствуют аннотации.")
    if not coco_test["annotations"]:
        print("Предупреждение: В тестовом наборе отсутствуют аннотации.")
    
    # Сохранение COCO JSON файлов
    train_coco_path = os.path.join(train_json_dir, 'train.json')
    test_coco_path = os.path.join(test_json_dir, 'test.json')
    
    try:
        with open(train_coco_path, 'w') as f:
            json.dump(coco_train, f, indent=4)
        print(f"Тренировочные данные сохранены в {train_coco_path}")
    except Exception as e:
        print(f"Ошибка при сохранении тренировочного JSON файла: {e}")
    
    try:
        with open(test_coco_path, 'w') as f:
            json.dump(coco_test, f, indent=4)
        print(f"Тестовые данные сохранены в {test_coco_path}")
    except Exception as e:
        print(f"Ошибка при сохранении тестового JSON файла: {e}")
    
    # Создание YAML файла с относительными путями и категориями
    categories_set = set(cls['name'] for cls in categories)
    yaml_content = {
        'train': 'train/train.json',  # относительный путь к тренировочным данным
        'test': 'test/test.json',    # относительный путь к тестовым данным
        'nc': len(categories_set),
        'names': list(categories_set)
    }
    
    yaml_output_path = os.path.join(base_dir, 'config.yaml')
    try:
        with open(yaml_output_path, 'w') as yaml_file:
            yaml.dump(yaml_content, yaml_file, default_flow_style=False)
        print(f"YAML файл с конфигурацией сохранен в {yaml_output_path}")
    except Exception as e:
        print(f"Ошибка при сохранении YAML файла: {e}")
    
    print("Данные успешно преобразованы и сохранены в формате COCO Detection.")

# Указание путей к исходным папкам
source_image_dir = "image"  # Путь к папке с изображениями
source_json_dir = "json"    # Путь к папке с JSON аннотациями

# Выполнение функции
create_coco_dataset(source_image_dir, source_json_dir)
