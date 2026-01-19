"""
Script per estrarre i dati del catalogo scaldacqua a pompa di calore dal PDF GSE
Genera il file JSON con l'elenco degli scaldacqua ammissibili

Schema JSON output:
{
  "id_slug": "marca-modello",
  "search_text": "marca modello 200 litri",
  "marca": "Ariston",
  "modello": "Nuos Evo 200",
  "tipologia_intervento": "III.E",
  "identificativo_unita_esterna": "...",
  "identificativo_unita_interna": "...",
  "dati_tecnici": {
    "capacita_litri": 200,
    "potenza_kw": 2.5,
    "cop": 3.2
  }
}
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """Rimuove spazi extra e caratteri di a capo"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text).strip())

def parse_number(value: str) -> float:
    """Converte una stringa numerica (con virgola italiana) in float"""
    if not value or value in ["-", "—", "–", "", "N/A", "n/a"]:
        return None
    try:
        # Rimuovi spazi e sostituisci virgola con punto
        cleaned = str(value).strip().replace(" ", "").replace(",", ".")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None

def parse_capacita(value: str) -> int:
    """Estrae la capacità in litri da una stringa"""
    if not value:
        return None
    try:
        # Rimuovi unità di misura e spazi
        cleaned = str(value).strip().lower()
        cleaned = cleaned.replace("litri", "").replace("lt", "").replace("l", "").strip()
        cleaned = cleaned.replace(",", ".").replace(" ", "")
        return int(float(cleaned))
    except (ValueError, AttributeError):
        return None

def create_slug(marca: str, modello: str) -> str:
    """Crea uno slug univoco dalla marca e modello"""
    text = f"{marca} {modello}".lower()
    # Rimuovi caratteri speciali e sostituisci spazi con trattino
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def is_header_row(row: List) -> bool:
    """Identifica se una riga è un'intestazione"""
    if not row:
        return False

    # Converti la riga in testo per il controllo
    row_text = ' '.join([str(cell).lower() if cell else '' for cell in row])

    # Parole chiave tipiche delle intestazioni per scaldacqua
    header_keywords = ['marca', 'modello', 'potenza', 'cop', 'capacità', 'capacita',
                       'litri', 'volume', 'costruttore', 'tipologia', 'intervento',
                       'identificativo', 'unità', 'unita']

    # Se contiene almeno 2 parole chiave, è probabilmente un'intestazione
    keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
    return keyword_count >= 2

def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Estrae tutte le tabelle dal PDF e le converte in lista di prodotti"""
    products = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Totale pagine: {len(pdf.pages)}")

        for page_num, page in enumerate(pdf.pages, 1):
            print(f"Elaborazione pagina {page_num}...")

            # Estrai tutte le tabelle dalla pagina
            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Identifica la riga di intestazione
                header_idx = None
                for idx, row in enumerate(table[:5]):  # Controlla le prime 5 righe
                    if is_header_row(row):
                        header_idx = idx
                        break

                if header_idx is None:
                    # Se non troviamo l'intestazione, proviamo con la prima riga
                    header_idx = 0

                headers = [clean_text(h).lower() if h else '' for h in table[header_idx]]

                # Mappa le colonne in base all'header
                col_map = {}
                for idx, header in enumerate(headers):
                    if 'tipologia' in header and 'intervento' in header:
                        col_map['tipologia'] = idx
                    elif 'marca' in header or 'costruttore' in header:
                        col_map['marca'] = idx
                    elif 'modello' in header and 'identificativo' not in header:
                        col_map['modello'] = idx
                    elif 'identificativo' in header and 'esterna' in header:
                        col_map['id_esterna'] = idx
                    elif 'identificativo' in header and 'interna' in header:
                        col_map['id_interna'] = idx
                    elif 'potenza' in header and 'termica' in header:
                        col_map['potenza'] = idx
                    elif 'cop' in header:
                        col_map['cop'] = idx
                    elif 'capacità' in header or 'capacita' in header or ('volume' in header or 'litri' in header):
                        col_map['capacita'] = idx

                # Elabora le righe di dati (salta l'intestazione)
                for row in table[header_idx + 1:]:
                    if not row or is_header_row(row):
                        continue

                    # Verifica che ci siano almeno marca e modello
                    if 'marca' not in col_map or 'modello' not in col_map:
                        continue

                    marca = clean_text(row[col_map['marca']] if len(row) > col_map['marca'] else '')
                    modello = clean_text(row[col_map['modello']] if len(row) > col_map['modello'] else '')

                    # Salta righe vuote o incomplete
                    if not marca or not modello or len(marca) < 2:
                        continue

                    # Estrai gli altri dati
                    tipologia = clean_text(row[col_map['tipologia']] if 'tipologia' in col_map and len(row) > col_map['tipologia'] else 'III.E')
                    id_esterna = clean_text(row[col_map['id_esterna']] if 'id_esterna' in col_map and len(row) > col_map['id_esterna'] else '')
                    id_interna = clean_text(row[col_map['id_interna']] if 'id_interna' in col_map and len(row) > col_map['id_interna'] else '')

                    potenza = parse_number(row[col_map['potenza']] if 'potenza' in col_map and len(row) > col_map['potenza'] else None)
                    cop = parse_number(row[col_map['cop']] if 'cop' in col_map and len(row) > col_map['cop'] else None)
                    capacita = parse_capacita(row[col_map['capacita']] if 'capacita' in col_map and len(row) > col_map['capacita'] else None)

                    # Verifica dati essenziali (capacità è fondamentale per gli scaldacqua)
                    if not capacita or capacita <= 0:
                        # Prova a estrarre capacità dal modello (es. "Nuos 200" -> 200 litri)
                        match = re.search(r'(\d{2,4})', modello)
                        if match:
                            capacita = int(match.group(1))

                    # Crea il prodotto
                    product = {
                        "id_slug": create_slug(marca, modello),
                        "search_text": f"{marca} {modello} {capacita if capacita else ''}".lower().strip(),
                        "marca": marca,
                        "modello": modello,
                        "tipologia_intervento": tipologia,
                        "identificativo_unita_esterna": id_esterna,
                        "identificativo_unita_interna": id_interna,
                        "dati_tecnici": {
                            "capacita_litri": capacita,
                            "potenza_kw": potenza,
                            "cop": cop
                        }
                    }

                    products.append(product)

    return products

def main():
    """Funzione principale"""
    # Percorsi
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs_reference" / "5 - 2D - CATALOGO SCALDACQUA PDC.pdf"
    output_path = base_dir / "data" / "products_scaldacqua.json"

    # Verifica esistenza PDF
    if not pdf_path.exists():
        print(f"ERRORE: File PDF non trovato: {pdf_path}")
        return

    print(f"Inizio estrazione da: {pdf_path}")

    # Estrai i dati
    products = extract_tables_from_pdf(str(pdf_path))

    print(f"\nTotale prodotti estratti: {len(products)}")

    # Rimuovi duplicati basandosi su id_slug
    unique_products = {}
    for product in products:
        slug = product['id_slug']
        if slug not in unique_products:
            unique_products[slug] = product

    products_list = list(unique_products.values())
    print(f"Prodotti unici dopo deduplicazione: {len(products_list)}")

    # Crea la directory data se non esiste
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Salva il JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products_list, f, ensure_ascii=False, indent=2)

    print(f"\nFile JSON salvato in: {output_path}")

    # Mostra alcuni esempi
    if products_list:
        print("\n=== ESEMPI DI PRODOTTI ESTRATTI ===")
        for product in products_list[:5]:
            print(f"\n- {product['marca']} {product['modello']}")
            print(f"  Tipologia: {product['tipologia_intervento']}")
            print(f"  Capacità: {product['dati_tecnici']['capacita_litri']} litri")
            print(f"  Potenza: {product['dati_tecnici']['potenza_kw']} kW")
            print(f"  COP: {product['dati_tecnici']['cop']}")
            if product['identificativo_unita_esterna']:
                print(f"  Unità esterna: {product['identificativo_unita_esterna']}")

if __name__ == "__main__":
    main()
