import os
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
import matplotlib.pyplot as plt

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

# Создаем папку для сохранения формул
if not os.path.exists('equations'):
    os.makedirs('equations')

num_documents = 10  # Количество документов для генерации

# Список LaTeX-формул
FORMULAS = [
    r"E = mc^2",
    r"\int_{a}^{b} f(x)\,dx",
    r"\frac{d}{dx}\left( e^x \right) = e^x",
    r"\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}",
    r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
    r"a^2 + b^2 = c^2",
    r"\nabla \cdot \mathbf{E} = \frac{\rho}{\varepsilon_0}",
    r"f(x) = \frac{1}{\sqrt{2\pi\sigma^2}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}",
    r"i\hbar \frac{\partial}{\partial t}\Psi = \hat{H}\Psi",
    r"e^{i\theta} = \cos \theta + i \sin \theta",
    r"\frac{\partial^2 u}{\partial t^2} = c^2 \nabla^2 u",
    r"\alpha + \beta = \gamma",
    r"\sqrt{a^2 + b^2 + c^2}",
    r"\frac{1}{1 + e^{-x}}",
    r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
    r"\mathbf{F} = m\mathbf{a}",
    r"PV = nRT",
    r"\frac{\partial u}{\partial t} + \mathbf{v} \cdot \nabla u = D \nabla^2 u",
    r"\sigma = \frac{F}{A}",
    r"\tau = r \times F"
]

def generate_equation_image(equation_str, output_dir='equations'):
    """
    Генерирует изображение формулы из LaTeX-строки и сохраняет его.
    
    :param equation_str: Строка LaTeX-формулы.
    :param output_dir: Директория для сохранения изображений формул.
    :return: Путь к сохранённому изображению формулы.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Генерируем уникальное имя файла
    filename = f"equation_{random.randint(1000, 9999)}.png"
    filepath = os.path.join(output_dir, filename)
    
    # Создаём изображение формулы
    plt.figure(figsize=(3, 1))
    plt.text(0.5, 0.5, f"${equation_str}$", fontsize=20, ha='center', va='center')
    plt.axis('off')
    plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
    return filepath

def add_equation_to_docx(doc, equation_str, caption=True):
    """
    Генерирует изображение формулы и добавляет его в документ.
    
    :param doc: Объект документа Document.
    :param equation_str: Строка LaTeX-формулы.
    :param caption: Добавлять ли подпись к формуле.
    """
    equation_image_path = generate_equation_image(equation_str)
    try:
        doc.add_picture(equation_image_path, width=Inches(4))
        if caption:
            caption_text = f"Формула {random.randint(1, 100)} — {fake.sentence(nb_words=random.randint(3, 7))}"
            caption_paragraph = doc.add_paragraph(caption_text)
            caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = caption_paragraph.runs[0]
            run.font.size = Pt(random.randint(10, 12))
    except Exception as e:
        print(f"Ошибка при добавлении формулы: {e}")

def add_footnote(paragraph, footnote_text, footnote_num, footnotes):
    """
    Добавляет сноску в абзац и сохраняет её текст.
    
    :param paragraph: Объект абзаца.
    :param footnote_text: Текст сноски.
    :param footnote_num: Номер сноски.
    :param footnotes: Список сносок.
    """
    footnote_mark = paragraph.add_run(f'[{footnote_num}]')
    footnote_mark.font.superscript = True
    footnotes.append((footnote_num, footnote_text))

def add_footnotes_section(document, footnotes):
    """
    Добавляет раздел с примечаниями (сносками) в конец документа.
    
    :param document: Объект документа Document.
    :param footnotes: Список сносок.
    """
    if footnotes:
        document.add_page_break()
        footnote_heading = document.add_paragraph('Примечания')
        footnote_heading.style = 'Heading 1'
        for num, text in footnotes:
            footnote_paragraph = document.add_paragraph()
            footnote_run = footnote_paragraph.add_run(f'[{num}] {text}')
            footnote_run.font.size = Pt(8)

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

for doc_num in range(1, num_documents + 1):
    document = Document()

    # Инициализация списка сносок
    footnotes = []
    footnote_num = 1  # Начальный номер сноски

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

        # Добавляем абзац текста с возможными сносками
        paragraph = document.add_paragraph(fake.text(max_nb_chars=random.randint(500, 1000)))
        paragraph_format = paragraph.paragraph_format
        paragraph_format.first_line_indent = Cm(1) if random.choice([True, False]) else None
        paragraph_format.alignment = random.choice([
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.RIGHT,
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ])

        # Разбиваем текст на предложения
        sentences = paragraph.text.split('. ')
        paragraph.text = ''  # Очищаем текст абзаца для повторного заполнения
        for sentence in sentences:
            if sentence.strip() == '':
                continue
            run = paragraph.add_run(sentence + '. ')
            run.font.size = Pt(random.randint(8, 16))
            run.font.name = 'Times New Roman'
            
            # Случайно добавляем сноску
            if random.choice([True, False, False]):  # Увеличиваем вероятность добавления сносок
                footnote_text = fake.sentence(nb_words=5)
                add_footnote(paragraph, footnote_text, footnote_num, footnotes)
                footnote_num += 1

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
        image_files = os.listdir(images_folder) if os.path.exists(images_folder) else []
        if image_files:
            image_path = os.path.join(images_folder, random.choice(image_files))
            try:
                document.add_picture(image_path, width=Inches(4))
            except Exception as e:
                print(f"Ошибка при добавлении изображения: {e}")

            caption_text = f"Рисунок {random.randint(1, 100)} — {fake.sentence(nb_words=random.randint(3, 7))}"
            caption_paragraph = document.add_paragraph(caption_text)
            caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = caption_paragraph.runs[0]
            run.font.size = Pt(random.randint(10, 12))

        # Добавляем нумерованный список
        for _ in range(random.randint(3, 7)):
            list_item = fake.sentence(nb_words=random.randint(5, 15))
            paragraph = document.add_paragraph(list_item, style='List Number')
            paragraph_format = paragraph.paragraph_format
            paragraph_format.left_indent = Cm(1)
            paragraph_format.line_spacing = random.uniform(1.0, 1.5)
            run = paragraph.runs[0]
            run.font.size = Pt(random.randint(8, 16))
            run.font.name = 'Times New Roman'

        # Добавляем маркированный список
        for _ in range(random.randint(3, 7)):
            list_item = fake.sentence(nb_words=random.randint(5, 15))
            paragraph = document.add_paragraph(list_item, style='List Bullet')
            paragraph_format = paragraph.paragraph_format
            paragraph_format.left_indent = Cm(1)
            paragraph_format.line_spacing = random.uniform(1.0, 1.5)
            run = paragraph.runs[0]
            run.font.size = Pt(random.randint(8, 16))
            run.font.name = 'Times New Roman'

        # Добавляем дополнительный абзац с возможными сносками
        paragraph = document.add_paragraph(fake.text(max_nb_chars=random.randint(500, 1000)))
        paragraph_format = paragraph.paragraph_format
        paragraph_format.first_line_indent = Cm(1) if random.choice([True, False]) else None
        paragraph_format.alignment = random.choice([
            WD_ALIGN_PARAGRAPH.LEFT,
            WD_ALIGN_PARAGRAPH.CENTER,
            WD_ALIGN_PARAGRAPH.RIGHT,
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ])
        sentences = paragraph.text.split('. ')
        paragraph.text = ''
        for sentence in sentences:
            if sentence.strip() == '':
                continue
            run = paragraph.add_run(sentence + '. ')
            run.font.size = Pt(random.randint(8, 16))
            run.font.name = 'Times New Roman'
            
            # Случайно добавляем сноску
            if random.choice([True, False, False]):  # Увеличиваем вероятность добавления сносок
                footnote_text = fake.sentence(nb_words=5)
                add_footnote(paragraph, footnote_text, footnote_num, footnotes)
                footnote_num += 1

        # Добавляем формулу с возможной подписью
        if random.choice([True, False]):
            equation_str = random.choice(FORMULAS)
            add_equation_to_docx(document, equation_str, caption=True)

    # Добавляем сноски в конец документа
    add_footnotes_section(document, footnotes)

    # Сохраняем документ в папку 'docx'
    document.save(f'docx/document_{doc_num}.docx')
    print(f"Документ {doc_num} успешно сгенерирован.")
