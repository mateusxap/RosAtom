import convert_to_pdf
import extract_images
import extract_annotations

if __name__ == '__main__':
    # Шаг 1: Конвертация DOCX в PDF
    convert_to_pdf.convert_docx_to_pdf()

    # Шаг 2: Извлечение Изображений из PDF
    extract_images.extract_images_from_pdf()

    # Шаг 3: Извлечение Координат Элементов из PDF
    extract_annotations.extract_annotations_from_pdf()
