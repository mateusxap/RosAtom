import os
from pdf2image import convert_from_path

def extract_images_from_pdf():
    pdf_dir = 'pdf'
    image_dir = 'image'

    # Создаем директорию 'image', если она не существует
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # Получаем список всех файлов в папке 'pdf'
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        pdf_name = os.path.splitext(pdf_file)[0]

        try:
            print(f'Извлекаем изображения из {pdf_file}...')
            # Конвертируем все страницы PDF в список изображений PIL
            pages = convert_from_path(pdf_path, dpi=300)  # dpi=300 для высокого качества

            for page_number, page in enumerate(pages, start=1):
                image_name = f"{pdf_name}_{page_number}.png"
                image_path = os.path.join(image_dir, image_name)
                page.save(image_path, 'PNG')
                print(f'Изображение {image_name} сохранено.')

        except Exception as e:
            print(f'Ошибка при извлечении изображений из {pdf_file}: {e}')

if __name__ == '__main__':
    extract_images_from_pdf()
