import os
import pypdfium2

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
            # Открываем PDF файл
            pdf = pypdfium2.PdfDocument(pdf_path)

            for page_number in range(len(pdf)):
                page = pdf.get_page(page_number)
                image = page.render(scale=300/72).to_pil() 
                image_name = f"{pdf_name}_{page_number}.png"
                image_path = os.path.join(image_dir, image_name)
                image.save(image_path)
                print(f'Изображение {image_name} сохранено.')

        except Exception as e:
            print(f'Ошибка при извлечении изображений из {pdf_file}: {e}')

if __name__ == '__main__':
    extract_images_from_pdf()