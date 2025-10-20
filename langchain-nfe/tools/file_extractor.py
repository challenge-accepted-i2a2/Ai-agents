import fitz  # PyMuPDF
import openpyxl
import docx
from pathlib import Path

def extract_text_from_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(path)
    elif ext == ".xlsx":
        return extract_xlsx_text(path)
    elif ext == ".docx":
        return extract_docx_text(path)
    else:
        raise ValueError(f"Extensão não suportada: {ext}")

def extract_pdf_text(path: Path) -> str:
    doc = fitz.open(path)
    texto = ""
    for page in doc:
        texto += page.get_text()
    return texto

def extract_xlsx_text(path: Path) -> str:
    wb = openpyxl.load_workbook(path, data_only=True)
    texto = ""
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            texto += " | ".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
    return texto

def extract_docx_text(path: Path) -> str:
    doc = docx.Document(path)
    texto = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return texto