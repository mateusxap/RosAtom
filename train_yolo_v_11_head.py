import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
from ultralytics import YOLO
import torchvision.transforms as transforms

# Определение пользовательского Dataset класса
class CustomYoloDataset(Dataset):
    def __init__(self, images_dir, annotations_dir, processor=None):
        self.images_dir = images_dir
        self.annotations_dir = annotations_dir
        self.processor = processor
        self.image_ids = [f.split('.')[0] for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png'))]
        
        self.classes = ['title', 'paragraph', 'table', 'picture', 'table_signature',
                        'picture_signature', 'numbered_list', 'marked_list', 'header',
                        'footer', 'footnote', 'formula', 'graph']
        self.class_to_id = {cls: i for i, cls in enumerate(self.classes)}
        self.num_classes = len(self.classes)
    
    def __len__(self):
        return len(self.image_ids)
    
    def __getitem__(self, idx):
        image_id = self.image_ids[idx]
        img_path = os.path.join(self.images_dir, f"{image_id}.png")
        image = Image.open(img_path).convert("RGB")
        image = transforms.ToTensor()(image)
        
        ann_path = os.path.join(self.annotations_dir, f"{image_id}.txt")
        annots = []
        
        with open(ann_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                label = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:])
                annots.append([label, x_center, y_center, width, height])
        
        if self.processor:
            image = self.processor(image)

        return {
            'image': image,
            'annotations': torch.tensor(annots, dtype=torch.float32)  
        }


def main():
    # Параметры
    data_dir = 'dataset'  # Путь к папке с датасетом
    train_images_dir = os.path.join(data_dir, 'train', 'images')
    train_labels_dir = os.path.join(data_dir, 'train', 'labels')
    output_model_dir = 'trained_model'

    # Проверка наличия файлов
    if not os.path.isdir(train_labels_dir):
        raise NotADirectoryError(f"Папка с аннотациями {train_labels_dir} не найдена.")
    if not os.path.isdir(train_images_dir):
        raise NotADirectoryError(f"Папка с изображениями {train_images_dir} не найдена.")

    # Загрузка модели
    model = YOLO('yolov11x_best.pt')
    model.info()

    # Создание пользовательского датасета
    dataset = CustomYoloDataset(train_images_dir, train_labels_dir)

    # Заморозка всех параметров
    for param in model.parameters():
        param.requires_grad = False
    
    # Разморозка параметров головы
    for _, param in model.model.model[-1].named_parameters():       
        param.requires_grad = True

    print("\nПараметры для обучения:")
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(name)

    '''
    for name, layer in model.model.model[-1].named_modules():
        if isinstance(layer, torch.nn.Conv2d):
            nn.init.xavier_uniform_(layer.weight)
            if layer.bias:
                nn.init.zeros_(layer.bias)
    '''

    # Создание DataLoader
    train_dataloader = DataLoader(
        dataset, 
        batch_size=4, 
        shuffle=True, 
        num_workers=0,
        pin_memory=True if torch.cuda.is_available() else False
    )

    # Перемещение модели на устройство
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.train(data='dataset/dataset.yaml', freeze=23) #epochs=1)
    #dataset=CustomYoloDataset)

if __name__ == "__main__":
    main()
