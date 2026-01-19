"""Script per analizzare la struttura del PDF solare termico"""
import pdfplumber
from pathlib import Path

pdf_path = Path(__file__).parent.parent / "docs_reference" / "4 - 2C - CATALOGO SOLARE TERMICO.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Totale pagine: {len(pdf.pages)}")

    # Analizza la prima pagina con contenuto
    page = pdf.pages[1]  # Seconda pagina (spesso la prima ha solo intro)

    print("\n=== ANALISI PAGINA 2 ===")
    tables = page.extract_tables()

    if tables:
        print(f"\nTabelle trovate: {len(tables)}")

        for i, table in enumerate(tables[:1]):  # Solo prima tabella
            print(f"\n--- TABELLA {i+1} ---")
            print(f"Righe: {len(table)}")

            # Mostra le prime 5 righe
            for j, row in enumerate(table[:5]):
                print(f"\nRiga {j}: {len(row)} colonne")
                for k, cell in enumerate(row):
                    if cell:
                        print(f"  Col {k}: {repr(cell[:100] if len(str(cell)) > 100 else cell)}")
