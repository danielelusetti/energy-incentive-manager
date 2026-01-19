import pdfplumber

pdf_path = "docs_reference/Regole_Applicative_CT_3_0.pdf"
output_path = "Regole_Extracted.txt"

print(f"Sto estraendo il testo da {pdf_path}...")

with pdfplumber.open(pdf_path) as pdf:
    with open(output_path, "w", encoding="utf-8") as f:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                f.write(f"--- PAGINA {i+1} ---\n")
                f.write(text)
                f.write("\n\n")

print("Fatto! Ora puoi dare il file .txt a Claude.")