"""
Script per estrarre i dati del catalogo sistemi ibridi dal PDF GSE
Genera il file JSON con l'elenco dei sistemi ibridi ammissibili

Schema JSON output:
{
  "id_slug": "marca-modello-pdc-modello-caldaia",
  "search_text": "marca modello pompa calore caldaia",
  "marca": "APEN GROUP",
  "modello_pompa_calore": "AquaPump Hybrid",
  "modello_caldaia_condensazione": "...",
  "tipologia_intervento": "2.E",
  "identificativo_unita_esterna": "HY434fT",
  "identificativo_unita_interna": "",
  "dati_tecnici": {
    "potenza_termica_pdc_kw": 12.28,
    "presenza_inverter": true,
    "cop": 4.1,
    "potenza_termica_caldaia_kw": 34.8,
    "rendimento_caldaia_perc": 98.3
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

def parse_inverter(value: str) -> bool:
    """Determina se è presente l'inverter"""
    if not value:
        return False
    value_lower = str(value).lower().strip()
    return value_lower in ["si", "sì", "yes", "s", "y", "true", "1"]

def create_slug(marca: str, modello_pdc: str, modello_caldaia: str = "") -> str:
    """Crea uno slug univoco dalla marca e modelli"""
    text = f"{marca} {modello_pdc} {modello_caldaia}".lower()
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

    # Parole chiave tipiche delle intestazioni per sistemi ibridi
    header_keywords = ['marca', 'modello', 'pompa', 'calore', 'caldaia', 'condensazione',
                       'potenza', 'termica', 'inverter', 'cop', 'rendimento',
                       'identificativo', 'unità', 'unita', 'esterna', 'interna', 'tipologia']

    # Se contiene almeno 3 parole chiave, è probabilmente un'intestazione
    keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
    return keyword_count >= 3

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
                    elif 'marca' in header:
                        col_map['marca'] = idx
                    elif 'modello' in header and 'pompa' in header and 'calore' in header:
                        col_map['modello_pdc'] = idx
                    elif 'modello' in header and 'caldaia' in header and 'condensazione' in header:
                        col_map['modello_caldaia'] = idx
                    elif 'identificativo' in header and ('modello' in header) and ('esterna' in header or 'estern' in header):
                        col_map['id_esterna'] = idx
                    elif 'identificativo' in header and ('modello' in header) and ('interna' in header or 'intern' in header):
                        col_map['id_interna'] = idx
                    elif 'potenza' in header and 'termica' in header and ('pompa' in header or 'pdc' in header or 'calore' in header):
                        col_map['potenza_pdc'] = idx
                    elif 'presenza' in header and 'inverter' in header:
                        col_map['inverter'] = idx
                    elif 'cop' in header:
                        col_map['cop'] = idx
                    elif 'potenza' in header and 'termica' in header and 'caldaia' in header:
                        col_map['potenza_caldaia'] = idx
                    elif 'rendimento' in header and ('utile' in header or 'caldaia' in header):
                        col_map['rendimento'] = idx

                # Elabora le righe di dati (salta l'intestazione)
                for row in table[header_idx + 1:]:
                    if not row or is_header_row(row):
                        continue

                    # Verifica che ci siano almeno marca e modello PdC
                    if 'marca' not in col_map or 'modello_pdc' not in col_map:
                        continue

                    marca = clean_text(row[col_map['marca']] if len(row) > col_map['marca'] else '')
                    modello_pdc = clean_text(row[col_map['modello_pdc']] if len(row) > col_map['modello_pdc'] else '')

                    # Salta righe vuote o incomplete
                    if not marca or not modello_pdc or len(marca) < 2:
                        continue

                    # Estrai gli altri dati
                    tipologia = clean_text(row[col_map['tipologia']] if 'tipologia' in col_map and len(row) > col_map['tipologia'] else '2.E')
                    modello_caldaia = clean_text(row[col_map['modello_caldaia']] if 'modello_caldaia' in col_map and len(row) > col_map['modello_caldaia'] else '')
                    id_esterna = clean_text(row[col_map['id_esterna']] if 'id_esterna' in col_map and len(row) > col_map['id_esterna'] else '')
                    id_interna = clean_text(row[col_map['id_interna']] if 'id_interna' in col_map and len(row) > col_map['id_interna'] else '')

                    potenza_pdc = parse_number(row[col_map['potenza_pdc']] if 'potenza_pdc' in col_map and len(row) > col_map['potenza_pdc'] else None)
                    potenza_caldaia = parse_number(row[col_map['potenza_caldaia']] if 'potenza_caldaia' in col_map and len(row) > col_map['potenza_caldaia'] else None)
                    cop = parse_number(row[col_map['cop']] if 'cop' in col_map and len(row) > col_map['cop'] else None)
                    rendimento = parse_number(row[col_map['rendimento']] if 'rendimento' in col_map and len(row) > col_map['rendimento'] else None)

                    # Presenza inverter
                    inverter = False
                    if 'inverter' in col_map and len(row) > col_map['inverter']:
                        inverter = parse_inverter(row[col_map['inverter']])

                    # Crea il prodotto
                    product = {
                        "id_slug": create_slug(marca, modello_pdc, modello_caldaia),
                        "search_text": f"{marca} {modello_pdc} {modello_caldaia}".lower().strip(),
                        "marca": marca,
                        "modello_pompa_calore": modello_pdc,
                        "modello_caldaia_condensazione": modello_caldaia,
                        "tipologia_intervento": tipologia,
                        "identificativo_unita_esterna": id_esterna,
                        "identificativo_unita_interna": id_interna,
                        "dati_tecnici": {
                            "potenza_termica_pdc_kw": potenza_pdc,
                            "presenza_inverter": inverter,
                            "cop": cop,
                            "potenza_termica_caldaia_kw": potenza_caldaia,
                            "rendimento_caldaia_perc": rendimento
                        }
                    }

                    products.append(product)

    return products

def main():
    """Funzione principale"""
    # Percorsi
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs_reference" / "6 - 2E - CATALOGO SISTEMI IBRIDI.pdf"
    output_path = base_dir / "data" / "products_ibridi.json"

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
        for product in products_list[:3]:
            print(f"\n- {product['marca']} - {product['modello_pompa_calore']}")
            print(f"  Modello caldaia: {product['modello_caldaia_condensazione']}")
            print(f"  Tipologia: {product['tipologia_intervento']}")
            print(f"  Potenza PdC: {product['dati_tecnici']['potenza_termica_pdc_kw']} kW")
            print(f"  Inverter: {'Sì' if product['dati_tecnici']['presenza_inverter'] else 'No'}")
            print(f"  COP: {product['dati_tecnici']['cop']}")
            print(f"  Potenza caldaia: {product['dati_tecnici']['potenza_termica_caldaia_kw']} kW")
            print(f"  Rendimento caldaia: {product['dati_tecnici']['rendimento_caldaia_perc']}%")
            if product['identificativo_unita_esterna']:
                print(f"  Unità esterna: {product['identificativo_unita_esterna']}")

if __name__ == "__main__":
    main()
