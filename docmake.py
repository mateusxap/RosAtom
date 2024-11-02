import random
from collections import OrderedDict
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import RGBColor, Pt, Cm, Inches
from faker import Faker
from docx.oxml import OxmlElement
import os

# Инициализация Faker
locales = OrderedDict([
    ('en-US', 1),
    ('ru-RU', 2),
])
fake = Faker(locales)

# Путь к папке с изображениями
images_folder = 'natural_images'

# Создаем папку для сохранения документов
if not os.path.exists('docx'):
    os.makedirs('docx')

num_documents = 10  # Количество документов для генерации


def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr

    if tblPr is None:
        tblPr = tbl.new_tblPr()

    tblBorders = OxmlElement('w:tblBorders')

    for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)

    tblPr.append(tblBorders)


for doc_num in range(num_documents):
    document = Document()

    # Случайное количество разделов в документе
    num_sections = random.randint(1, 5)
    for section_num in range(num_sections):
        if section_num != 0:
            document.add_section(WD_SECTION.NEW_PAGE)

        # Случайное изменение ориентации страницы
        if random.randint(0, 1):
            current_section = document.sections[-1]
            new_width, new_height = current_section.page_height, current_section.page_width
            current_section.orientation = WD_ORIENT.LANDSCAPE
            current_section.page_width = new_width
            current_section.page_height = new_height

        # Случайно выбираем, использовать ли несколько колонок
        use_columns = random.choice([True, False])
        if use_columns:
            columns = random.choice([2, 3])
            sectPr = document.sections[-1]._sectPr
            cols = sectPr.xpath('./w:cols')[0]
            cols.set(qn('w:num'), str(columns))
        else:
            # Устанавливаем одну колонку
            sectPr = document.sections[-1]._sectPr
            cols = sectPr.xpath('./w:cols')[0]
            cols.set(qn('w:num'), '1')

        # Добавляем верхний колонтитул
        header = document.sections[-1].header
        header_paragraph = header.paragraphs[0]
        header_paragraph.text = fake.sentence(nb_words=random.randint(5, 10))

        # Добавляем нижний колонтитул
        footer = document.sections[-1].footer
        footer_paragraph = footer.paragraphs[0]
        footer_paragraph.text = fake.sentence(nb_words=random.randint(5, 10))

        # Добавляем заголовок
        level = random.randint(0, 4)
        heading_text = fake.sentence(nb_words=random.randint(3, 7))
        heading = document.add_heading(heading_text, level=level)
        run = heading.runs[0]
        run.font.bold = random.choice([True, False])
        run.font.italic = random.choice([True, False])
        run.font.size = Pt(random.randint(14, 24))
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER if random.choice([True, False]) else WD_ALIGN_PARAGRAPH.LEFT

        # Добавляем абзац текста
        paragraph = document.add_paragraph(fake.text(max_nb_chars=random.randint(500, 1000)))
        paragraph_format = paragraph.paragraph_format
        paragraph_format.first_line_indent = Cm(1) if random.choice([True, False]) else None
        paragraph_format.alignment = random.choice([
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.RIGHT,
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ])
        run = paragraph.runs[0]
        run.font.size = Pt(random.randint(8, 16))

        # Добавляем подпись к таблице
        caption_text = f"Таблица {random.randint(1, 100)} — {fake.sentence(nb_words=random.randint(3, 7))}"
        caption_paragraph = document.add_paragraph(caption_text)
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = caption_paragraph.runs[0]
        run.font.size = Pt(random.randint(10, 12))

        # Добавляем таблицу
        table = document.add_table(
            rows=random.randint(2, 5),
            cols=random.randint(2, 5)
        )
        table.alignment = random.choice([
            WD_TABLE_ALIGNMENT.LEFT,
            WD_TABLE_ALIGNMENT.CENTER,
            WD_TABLE_ALIGNMENT.RIGHT
        ])
        # Устанавливаем границы таблицы
        set_table_borders(table)

        # Заполняем таблицу данными
        for row in table.rows:
            for cell in row.cells:
                cell.text = fake.word()

        # Добавляем изображение с подписью
        image_files = os.listdir(images_folder)
        if image_files:
            image_path = os.path.join(images_folder, random.choice(image_files))
            document.add_picture(image_path, width=Inches(4))

            caption_text = f"Рисунок {random.randint(1, 100)} — {fake.sentence(nb_words=random.randint(3, 7))}"
            caption_paragraph = document.add_paragraph(caption_text)
            caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = caption_paragraph.runs[0]
            run.font.size = Pt(random.randint(10, 12))

        # Добавляем нумерованный список
        for _ in range(random.randint(3, 7)):
            paragraph = document.add_paragraph(fake.sentence(nb_words=random.randint(5, 15)), style='List Number')
            paragraph_format = paragraph.paragraph_format
            paragraph_format.left_indent = Cm(1)
            paragraph_format.line_spacing = random.uniform(1.0, 1.5)

        # Добавляем маркированный список
        for _ in range(random.randint(3, 7)):
            paragraph = document.add_paragraph(fake.sentence(nb_words=random.randint(5, 15)), style='List Bullet')
            paragraph_format = paragraph.paragraph_format
            paragraph_format.left_indent = Cm(1)
            paragraph_format.line_spacing = random.uniform(1.0, 1.5)

        # Добавляем дополнительный абзац
        paragraph = document.add_paragraph(fake.text(max_nb_chars=random.randint(500, 1000)))
        paragraph_format = paragraph.paragraph_format
        paragraph_format.first_line_indent = Cm(1) if random.choice([True, False]) else None
        paragraph_format.alignment = random.choice([
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.RIGHT,
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ])
        run = paragraph.runs[0]
        run.font.size = Pt(random.randint(8, 16))

    # Сохраняем документ в папку 'docx'
    document.save(f'docx/demo_{doc_num}.docx')