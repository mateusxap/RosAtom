import os
import json
import yaml
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DetrForObjectDetection, DetrFeatureExtractor, DetrConfig
from torch.optim import AdamW
from tqdm import tqdm
from pycocotools.coco import COCO

class COCODataset(Dataset):
    def __init__(self, img_dir, ann_file, feature_extractor, transform=None):
        self.img_dir = img_dir
        self.coco = COCO(ann_file)
        self.image_ids = list(self.coco.imgs.keys())
        self.feature_extractor = feature_extractor
        self.transform = transform

    def __len__(self):
        return len(self.image_ids)

    def __getitem__(self, idx):
        image_id = self.image_ids[idx]
        ann_ids = self.coco.getAnnIds(imgIds=image_id)
        anns = self.coco.loadAnns(ann_ids)
        img_info = self.coco.loadImgs(image_id)[0]
        img_path = os.path.join(self.img_dir, img_info['file_name'])
        image = Image.open(img_path).convert("RGB")

        # Извлечение bbox и меток
        boxes = []
        labels = []
        for ann in anns:
            bbox = ann['bbox']  # [x_min, y_min, width, height]
            if len(bbox) == 4:
                boxes.append(bbox)
                labels.append(ann['category_id'] - 1)  # Сдвиг на 1 вниз

        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)

        target = {}
        target["boxes"] = boxes
        target["class_labels"] = labels  # Используем 'class_labels'

        if self.transform:
            image = self.transform(image)

        # Преобразование изображений с помощью feature_extractor
        encoding = self.feature_extractor(images=image, return_tensors="pt")
        pixel_values = encoding["pixel_values"].squeeze(0)  # Удаление лишнего измерения

        return pixel_values, target

def collate_fn(batch):
    pixel_values = [item[0] for item in batch]
    targets = [item[1] for item in batch]
    pixel_values = torch.stack(pixel_values)
    return {"pixel_values": pixel_values, "labels": targets}

def main():
    # Пути к данным
    base_dir = "dataset"
    train_img_dir = os.path.join(base_dir, "train", "images")
    train_ann_file = os.path.join(base_dir, "train", "train.json")
    test_img_dir = os.path.join(base_dir, "test", "images")
    test_ann_file = os.path.join(base_dir, "test", "test.json")

    # Загрузка Feature Extractor
    feature_extractor = DetrFeatureExtractor.from_pretrained("cmarkea/detr-layout-detection")

    # Чтение конфигурации из YAML файла
    yaml_path = os.path.join(base_dir, 'config.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)

    class_names = config.get('names', [])
    num_classes = config.get('nc', len(class_names))
    print(f"Количество классов: {num_classes}")

    # Проверка соответствия количества классов
    if num_classes != len(class_names):
        print("Предупреждение: 'nc' не соответствует количеству классов в 'names'. Используем длину 'names'.")
        num_classes = len(class_names)

    # Определение DetrConfig с обновленным num_labels
    config_detr = DetrConfig.from_pretrained("cmarkea/detr-layout-detection", num_labels=num_classes)

    # Инициализация модели с обновленным конфигурационным файлом
    model = DetrForObjectDetection.from_pretrained("cmarkea/detr-layout-detection", config=config_detr)

    # Проверка num_labels
    print(f"Model config num_labels: {model.config.num_labels}")  # Должно быть 13

    # Создание датасетов
    train_dataset = COCODataset(train_img_dir, train_ann_file, feature_extractor, transform=None)
    test_dataset = COCODataset(test_img_dir, test_ann_file, feature_extractor, transform=None)

    # Создание DataLoader'ов
    train_dataloader = DataLoader(train_dataset, batch_size=8, shuffle=True, collate_fn=collate_fn)
    test_dataloader = DataLoader(test_dataset, batch_size=8, shuffle=False, collate_fn=collate_fn)

    # Заморозка всех параметров модели
    for param in model.parameters():
        param.requires_grad = False

    # Разморозка только классификационного слоя и слоя предсказания bbox
    for name, param in model.named_parameters():
        if 'class_labels_classifier' in name or 'bbox_predictor' in name:
            param.requires_grad = True

    # Выводим названия параметров, подлежащих обучению
    print("Параметры, подлежащие обучению после заморозки:")
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(name)

    # Перенос модели на устройство
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model.to(device)
    print(f"Используемое устройство: {device}")

    # Настройка оптимизатора
    optimizer = AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)

    # Цикл обучения модели
    num_epochs = 1
    best_loss = float('inf')

    for epoch in range(num_epochs):
        # Тренировочная фаза
        model.train()
        epoch_loss = 0
        progress_bar = tqdm(train_dataloader, desc=f"Epoch {epoch+1}/{num_epochs}")

        for batch in progress_bar:
            pixel_values = batch['pixel_values'].to(device)
            targets = batch['labels']

            # Преобразование целевых значений для модели
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            optimizer.zero_grad()

            outputs = model(pixel_values=pixel_values, labels=targets)
            loss = outputs.loss
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            progress_bar.set_postfix({'Loss': loss.item()})

        avg_epoch_loss = epoch_loss / len(train_dataloader)
        print(f"Эпоха {epoch+1} завершена. Средняя потеря: {avg_epoch_loss:.4f}")

        # Валидационная фаза
        model.eval()
        test_loss = 0
        with torch.no_grad():
            for batch in tqdm(test_dataloader, desc="Валидация"):
                pixel_values = batch['pixel_values'].to(device)
                targets = batch['labels']
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

                outputs = model(pixel_values=pixel_values, labels=targets)
                loss = outputs.loss
                test_loss += loss.item()

        avg_test_loss = test_loss / len(test_dataloader)
        print(f"Валидация завершена. Средняя потеря: {avg_test_loss:.4f}")

        # Сохранение лучшей модели
        if avg_test_loss < best_loss:
            best_loss = avg_test_loss
            save_directory = "trained_detr_layout_detection"
            os.makedirs(save_directory, exist_ok=True)
            model.save_pretrained(save_directory)
            feature_extractor.save_pretrained(save_directory)
            print(f"Лучшая модель сохранена с потерей: {best_loss:.4f}")

    print("Обучение завершено.")

if __name__ == "__main__":
    main()
