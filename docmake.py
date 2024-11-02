import random
from collections import OrderedDict
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import RGBColor, Pt, Cm, Inches
from docx.oxml import OxmlElement
from faker import Faker
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

# Список цветов в формате HEX
COLORS = """000000 000080 00008B 0000CD 0000FF 006400 008000 008080 008B8B 00BFFF 00CED1 
00FA9A 00FF00 00FF7F 00FFFF 00FFFF 191970 1E90FF 20B2AA 228B22 2E8B57 2F4F4F 32CD32 3CB371 
40E0D0 4169E1 4682B4 483D8B 48D1CC 4B0082 556B2F 5F9EA0 6495ED 66CDAA 696969 6A5ACD 6B8E23 
708090 778899 7B68EE 7CFC00 7FFF00 7FFFD4 800000 800080 808000 808080 87CEEB 87CEFA 8A2BE2 
8B0000 8B008B 8B4513 8FBC8F 90EE90 9370D8 9400D3 98FB98 9932CC 9ACD32 A0522D A52A2A A9A9A9 
ADD8E6 ADFF2F AFEEEE B0C4DE B0E0E6 B22222 B8860B BA55D3 BC8F8F BDB76B C0C0C0 C71585 CD5C5C 
CD853F D2691E D2B48C D3D3D3 D87093 D8BFD8 DA70D6 DAA520 DC143C DCDCDC DDA0DD DEB887 E0FFFF 
E6E6FA E9967A EE82EE EEE8AA F08080 F0E68C F0F8FF F0FFF0 F0FFFF F4A460 F5DEB3 F5F5DC F5F5F5 
F5FFFA F8F8FF FA8072 FAEBD7 FAF0E6 FAFAD2 FDF5E6 FF0000 FF00FF FF00FF FF1493 FF4500 FF6347 
FF69B4 FF7F50 FF8C00 FFA07A FFA500 FFB6C1 FFC0CB FFD700 FFDAB9 FFDEAD FFE4B5 FFE4C4 FFE4E1 
FFEBCD FFEFD5 FFF0F5 FFF5EE FFF8DC FFFACD FFFAF0 FFFAFA FFFF00 FFFFE0 FFFFF0 FFFFFF"""

colors_list = COLORS.split()

def set_table_borders(table, include_borders=True):
    tbl = table._tbl
    tblPr = tbl.tblPr

    if tblPr is None:
        tblPr = tbl.new_tblPr()

    if include_borders:
        tblBorders = OxmlElement('w:tblBorders')

        for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '4')
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), '000000')
            tblBorders.append(border)

        tblPr.append(tblBorders)
    else:
        # Удаляем границы, если они есть
        for element in tblPr.xpath('w:tblBorders'):
            tblPr.remove(element)

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

        # Решаем, делать ли таблицу цветной
        make_colorful = random.choice([True, False])

        # Решаем, будут ли границы таблицы
        include_borders = random.choice([True, False])
        set_table_borders(table, include_borders=include_borders)

        if make_colorful:
            # Выбираем случайные цвета для строк
            color_row_1 = random.choice(colors_list)
            color_row_2 = random.choice(colors_list)

            # Выбираем цвет текста: белый или черный
            font_color = RGBColor(255, 255, 255) if random.choice([True, False]) else RGBColor(0, 0, 0)

            for idx_row, row in enumerate(table.rows):
                # Выбираем цвет для текущей строки
                color = color_row_1 if idx_row % 2 == 0 else color_row_2

                for cell in row.cells:
                    # Заполняем ячейку текстом
                    cell.text = fake.word()

                    # Устанавливаем цвет заливки ячейки
                    shading_elm = OxmlElement('w:shd')
                    shading_elm.set(qn('w:fill'), color)
                    cell._tc.get_or_add_tcPr().append(shading_elm)

                    # Устанавливаем цвет и размер шрифта
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = font_color
                            run.font.size = Pt(random.randint(8, 14))

                    # Устанавливаем выравнивание содержимого ячейки
                    alignment = random.choice([
                        WD_ALIGN_PARAGRAPH.LEFT,
                        WD_ALIGN_PARAGRAPH.CENTER,
                        WD_ALIGN_PARAGRAPH.RIGHT,
                        WD_ALIGN_PARAGRAPH.JUSTIFY
                    ])
                    cell.paragraphs[0].alignment = alignment
        else:
            # Если таблица не цветная, заполняем ячейки стандартно
            for row in table.rows:
                for cell in row.cells:
                    cell.text = fake.word()

                    # Устанавливаем размер шрифта
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(random.randint(8, 14))

                    # Устанавливаем выравнивание содержимого ячейки
                    alignment = random.choice([
                        WD_ALIGN_PARAGRAPH.LEFT,
                        WD_ALIGN_PARAGRAPH.CENTER,
                        WD_ALIGN_PARAGRAPH.RIGHT,
                        WD_ALIGN_PARAGRAPH.JUSTIFY
                    ])
                    cell.paragraphs[0].alignment = alignment

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