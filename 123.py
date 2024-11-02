import matplotlib.pyplot as plt
from docx import Document

def generate_equation_image(equation_str):
    plt.figure(figsize=(3, 1))
    plt.text(0.5, 0.5, f"${equation_str}$", fontsize=20, ha='center', va='center')
    plt.axis('off')
    plt.savefig("equation.png", bbox_inches='tight', pad_inches=0.1)
    plt.close()

def add_equation_image_to_docx(doc, equation_str):
    generate_equation_image(equation_str)
    doc.add_picture("equation.png")

# Генерация документа и формулы
doc = Document()
equation_str = r"\frac{a}{b} + \sqrt{c} = d"  # Пример LaTeX формулы
add_equation_image_to_docx(doc, equation_str)
doc.save("random_equation.docx")
