import os
from docx2pdf import convert

def convert_docx_to_pdf():
    docx_dir = 'docx'
    pdf_dir = 'pdf'

    # Создаем директорию 'pdf', если она не существует
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    # Получаем список всех файлов в папке 'docx'
    docx_files = [f for f in os.listdir(docx_dir) if f.endswith('.docx')]

    for docx_file in docx_files:
        docx_path = os.path.join(docx_dir, docx_file)
        pdf_file = os.path.splitext(docx_file)[0] + '.pdf'
        pdf_path = os.path.join(pdf_dir, pdf_file)
        try:
            print(f'Конвертируем {docx_file} в PDF...')
            convert(docx_path, pdf_path)
            print(f'Файл {pdf_file} успешно создан.')
        except Exception as e:
            print(f'Ошибка при конвертации {docx_file}: {e}')

if __name__ == '__main__':
    convert_docx_to_pdf()
