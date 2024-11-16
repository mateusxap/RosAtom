import torch
import torch.nn as nn
from transformers import DeformableDetrForObjectDetection, DetrImageProcessor
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
from pycocotools.coco import COCO
from tqdm import tqdm

# Определение пользовательского Dataset класса
class CustomCocoDataset(Dataset):
    def __init__(self, images_dir, annotations_file, processor):
        self.images_dir = images_dir
        self.coco = COCO(annotations_file)
        self.processor = processor
        self.image_ids = list(self.coco.imgs.keys())
        
        # Создание маппинга category_id к 0-based индексам
        self.categories = self.coco.loadCats(self.coco.getCatIds())
        self.categories.sort(key=lambda x: x['id'])  # Сортируем категории по 'id'

        self.cat_id_to_label = {cat['id']: idx for idx, cat in enumerate(self.categories)}
        self.num_classes = len(self.categories)
        
        # Проверка маппинга
        max_category_id = max(self.cat_id_to_label.values())
        print(f"Максимальный индекс категории после маппинга: {max_category_id}")
        print(f"Количество классов (num_classes): {self.num_classes}")
    
    def __len__(self):
        return len(self.image_ids)
    
    def __getitem__(self, idx):
        image_id = self.image_ids[idx]
        ann_ids = self.coco.getAnnIds(imgIds=image_id)
        annotations = self.coco.loadAnns(ann_ids)
        
        # Загрузка изображения
        img_info = self.coco.loadImgs(image_id)[0]
        img_path = os.path.join(self.images_dir, img_info['file_name'])
        image = Image.open(img_path).convert("RGB")
        
        # Извлечение аннотаций
        formatted_annotations = []
        for ann in annotations:
            bbox = ann['bbox']
            original_category_id = ann['category_id']
            category_id = self.cat_id_to_label.get(original_category_id, -1)
            if category_id == -1:
                print(f"Неизвестный category_id: {original_category_id}")
                continue  # Пропуск аннотаций с неизвестными категориями
            if category_id < 0 or category_id >= self.num_classes:
                print(f"Неверный category_id после маппинга: {category_id}")
                continue  # Пропускаем некорректные метки
            area = ann.get('area', bbox[2] * bbox[3])  # width * height

            formatted_annotation = {
                "bbox": bbox,
                "category_id": category_id,
                "area": area
            }
            formatted_annotations.append(formatted_annotation)
        
        # Подготовка аннотаций
        annotations_dict = {
            "image_id": image_id,
            "annotations": formatted_annotations
        }
        
        return {
            'image': image,
            'annotations': annotations_dict
        }


def main():
    # Параметры
    model_name = "Aryn/deformable-detr-DocLayNet"
    data_dir = 'dataset'  # Путь к папке с датасетом
    train_images_dir = os.path.join(data_dir, 'images', 'train')
    train_annotations_file = os.path.join(data_dir, 'annotations', 'instances_train.json')
    output_model_dir = 'trained_model'

    # Проверка наличия файлов
    if not os.path.exists(train_annotations_file):
        raise FileNotFoundError(f"Файл аннотаций {train_annotations_file} не найден.")
    if not os.path.isdir(train_images_dir):
        raise NotADirectoryError(f"Папка с изображениями {train_images_dir} не найдена.")

    # Загрузка модели и процессора
    processor = DetrImageProcessor.from_pretrained(model_name)
    model = DeformableDetrForObjectDetection.from_pretrained(model_name)

    # Распечатка структуры модели для определения правильных атрибутов
    print("Структура модели:")
    print(model)

    # Создание пользовательского датасета
    dataset = CustomCocoDataset(train_images_dir, train_annotations_file, processor)
    num_classes = dataset.num_classes
    num_labels = num_classes + 1  # Добавляем 1 для класса "no object"

    # Обновление количества меток в конфигурации модели
    model.config.num_labels = num_labels

    # Переинициализация слоёв class_embed внутри model.decoder и model
    def reinitialize_class_embed(module):
        if hasattr(module, 'class_embed'):
            if isinstance(module.class_embed, nn.Linear):
                in_features = module.class_embed.in_features
                module.class_embed = nn.Linear(in_features, num_labels)
                nn.init.xavier_uniform_(module.class_embed.weight)
                nn.init.zeros_(module.class_embed.bias)
            elif isinstance(module.class_embed, nn.ModuleList):
                new_class_embed = nn.ModuleList([
                    nn.Linear(layer.in_features, num_labels)
                    for layer in module.class_embed
                ])
                for new_layer in new_class_embed:
                    nn.init.xavier_uniform_(new_layer.weight)
                    nn.init.zeros_(new_layer.bias)
                module.class_embed = new_class_embed

    reinitialize_class_embed(model)
    reinitialize_class_embed(model.model.decoder)

    # Переинициализация слоёв bbox_embed внутри model.decoder и model
    def reinitialize_bbox_embed(module):
        if hasattr(module, 'bbox_embed'):
            if isinstance(module.bbox_embed, nn.Linear):
                in_features = module.bbox_embed.in_features
                module.bbox_embed = nn.Linear(in_features, 4)
                nn.init.xavier_uniform_(module.bbox_embed.weight)
                nn.init.zeros_(module.bbox_embed.bias)
            elif isinstance(module.bbox_embed, nn.ModuleList):
                for bbox_head in module.bbox_embed:
                    if hasattr(bbox_head, 'layers'):
                        in_features = bbox_head.layers[2].in_features
                        bbox_head.layers[2] = nn.Linear(in_features, 4)
                        nn.init.xavier_uniform_(bbox_head.layers[2].weight)
                        nn.init.zeros_(bbox_head.layers[2].bias)

    reinitialize_bbox_embed(model)
    reinitialize_bbox_embed(model.model.decoder)

    # Замораживание всех параметров
    for param in model.parameters():
        param.requires_grad = False

    # Разморозка слоёв class_embed и bbox_embed
    for name, param in model.named_parameters():
        if "class_embed" in name or "bbox_embed" in name:
            param.requires_grad = True

    # Определение custom_collate_fn внутри main()
    def custom_collate_fn(batch):
        images = [item['image'] for item in batch]
        annotations = [item['annotations'] for item in batch]
        encoding = processor(images=images, annotations=annotations, return_tensors="pt")
        return encoding

    # Создание DataLoader с кастомной функцией collate_fn
    train_dataloader = DataLoader(
        dataset, 
        batch_size=4, 
        shuffle=True, 
        num_workers=0,  # Установите на 0 или 1, если работаете на Windows
        pin_memory=True if torch.cuda.is_available() else False,
        collate_fn=custom_collate_fn
    )

    # Определение оптимизатора
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=5e-6)

    # Перемещение модели на устройство
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.train()

    # Обучение
    num_epochs = 1  # Уменьшено для примера
    for epoch in range(num_epochs):
        print(f"\nЭпоха {epoch+1}/{num_epochs}")
        total_loss = 0.0
        for batch in tqdm(train_dataloader, desc="Обучение"):
            pixel_values = batch['pixel_values'].to(device)
            pixel_mask = batch['pixel_mask'].to(device)
            labels = [{k: v.to(device) for k, v in t.items()} for t in batch['labels']]

            outputs = model(pixel_values=pixel_values, pixel_mask=pixel_mask, labels=labels)

            # Проверка размера выходных логитов
            pred_logits = outputs.logits  # [batch_size, num_queries, num_labels]
            print(f"Размер pred_logits: {pred_logits.shape}")

            loss = outputs.loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
        
        avg_loss = total_loss / len(train_dataloader)
        print(f"Средний Loss после эпохи {epoch+1}: {avg_loss:.4f}")

    print("Обучение завершено.")

    # Сохранение модели с использованием safe_serialization=False
    os.makedirs(output_model_dir, exist_ok=True)
    try:
        model.save_pretrained(output_model_dir)
        processor.save_pretrained(output_model_dir)
        print(f"Модель успешно сохранена в {output_model_dir}.")
    except RuntimeError as e:
        print(f"Ошибка при сохранении модели: {e}")
        print("Попробуйте сохранить модель с параметром `safe_serialization=False`.")
        model.save_pretrained(output_model_dir, safe_serialization=False)
        processor.save_pretrained(output_model_dir)
        print(f"Модель успешно сохранена в {output_model_dir} с `safe_serialization=False`.")

if __name__ == "__main__":
    main()
