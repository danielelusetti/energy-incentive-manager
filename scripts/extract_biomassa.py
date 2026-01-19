"""
Script per estrarre i dati del catalogo caldaie a biomassa dal PDF GSE
Genera il file JSON con l'elenco delle caldaie ammissibili

Schema JSON output:
{
  "id_slug": "marca-modello",
  "search_text": "marca modello pellet automatica",
  "marca": "ADLER",
  "modello": "BOILER16AD",
  "alimentazione": "pellet|legna|cippato",
  "tipologia_alimentazione": "automatica|manuale",
  "tipologia_generatore": "caldaia|stufa",
  "classe_qualita_ambientale": "4 stelle|5 stelle|etc",
  "dati_tecnici": {
    "potenza_kw": 13.8,
    "rendimento_perc": 91.2,
    "emissioni_pp_mg_nm3": 13.0,
    "emissioni_co_g_nm3": 0.056
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
    if not value or value in ["-", "—", "–", ""]:
        return None
    try:
        # Rimuovi spazi e sostituisci virgola con punto
        cleaned = str(value).strip().replace(" ", "").replace(",", ".")
        return float(cleaned)
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

    # Parole chiave tipiche delle intestazioni
    header_keywords = ['marca', 'modello', 'potenza', 'rendimento', 'emissioni',
                       'costruttore', 'coefficiente', 'particolato', 'tipologia']

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

                # Mappa le colonne (cerca pattern flessibili)
                # IMPORTANTE: l'ordine dei check è importante per evitare false positive
                col_map = {}
                for idx, header in enumerate(headers):
                    if 'marca' in header or 'costruttore' in header:
                        col_map['marca'] = idx
                    elif 'modello' in header:
                        col_map['modello'] = idx
                    elif 'potenza' in header and 'termica' in header:
                        col_map['potenza'] = idx
                    # Prima controlla "Tipologia Alimentazione" (Automatica/Manuale)
                    elif 'tipologia' in header and 'alimentazione' in header:
                        col_map['tipologia_alimentazione'] = idx
                    # Poi controlla "Alimentazione" semplice (Pellet/Legna/Cippato)
                    elif 'alimentazione' in header or 'combustibile' in header:
                        col_map['alimentazione'] = idx
                    elif 'rendimento' in header:
                        col_map['rendimento'] = idx
                    elif ('emissioni' in header and 'pp' in header) or 'particolato' in header or ('polveri' in header and 'sottili' in header):
                        col_map['emissioni_pp'] = idx
                    elif 'emissioni' in header and 'co' in header:
                        col_map['emissioni_co'] = idx
                    elif 'classe' in header and ('qualità' in header or 'qualita' in header or 'ambientale' in header or 'stelle' in header):
                        col_map['classe_qualita'] = idx
                    elif 'tipologia' in header and 'generatore' in header:
                        col_map['tipologia_generatore'] = idx

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
                    potenza = parse_number(row[col_map['potenza']] if 'potenza' in col_map and len(row) > col_map['potenza'] else None)
                    rendimento = parse_number(row[col_map['rendimento']] if 'rendimento' in col_map and len(row) > col_map['rendimento'] else None)
                    emissioni_pp = parse_number(row[col_map['emissioni_pp']] if 'emissioni_pp' in col_map and len(row) > col_map['emissioni_pp'] else None)
                    emissioni_co = parse_number(row[col_map['emissioni_co']] if 'emissioni_co' in col_map and len(row) > col_map['emissioni_co'] else None)

                    # Alimentazione (Pellet, Legna, Cippato, etc.)
                    alimentazione = ''
                    if 'alimentazione' in col_map and len(row) > col_map['alimentazione']:
                        alimentazione = clean_text(row[col_map['alimentazione']]).lower()

                    # Tipologia alimentazione (Automatica/Manuale)
                    tipologia_alimentazione = ''
                    if 'tipologia_alimentazione' in col_map and len(row) > col_map['tipologia_alimentazione']:
                        tipologia_alimentazione = clean_text(row[col_map['tipologia_alimentazione']]).lower()

                    # Tipologia generatore (Caldaia, Stufa, etc.)
                    tipologia_generatore = ''
                    if 'tipologia_generatore' in col_map and len(row) > col_map['tipologia_generatore']:
                        tipologia_generatore = clean_text(row[col_map['tipologia_generatore']]).lower()

                    # Classe di qualità ambientale
                    classe_qualita = ''
                    if 'classe_qualita' in col_map and len(row) > col_map['classe_qualita']:
                        classe_qualita = clean_text(row[col_map['classe_qualita']]).lower()

                    # Inferisci alimentazione dal modello se non presente
                    if not alimentazione:
                        modello_lower = modello.lower()
                        if 'pellet' in modello_lower:
                            alimentazione = 'pellet'
                        elif 'legna' in modello_lower or 'legno' in modello_lower:
                            alimentazione = 'legna'
                        elif 'cippato' in modello_lower:
                            alimentazione = 'cippato'

                    # Crea il prodotto
                    product = {
                        "id_slug": create_slug(marca, modello),
                        "search_text": f"{marca} {modello} {alimentazione} {tipologia_alimentazione}".lower().strip(),
                        "marca": marca,
                        "modello": modello,
                        "alimentazione": alimentazione,
                        "tipologia_alimentazione": tipologia_alimentazione,
                        "tipologia_generatore": tipologia_generatore,
                        "classe_qualita_ambientale": classe_qualita,
                        "dati_tecnici": {
                            "potenza_kw": potenza,
                            "rendimento_perc": rendimento,
                            "emissioni_pp_mg_nm3": emissioni_pp,
                            "emissioni_co_g_nm3": emissioni_co
                        }
                    }

                    products.append(product)

    return products

def main():
    """Funzione principale"""
    # Percorsi
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs_reference" / "2B - CATALOGO CALDAIE A BIOMASSA.pdf"
    output_path = base_dir / "data" / "products_biomassa.json"

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
            print(f"\n- {product['marca']} {product['modello']}")
            print(f"  Alimentazione: {product['alimentazione']}")
            print(f"  Tipologia: {product['tipologia_alimentazione']} - {product['tipologia_generatore']}")
            print(f"  Classe qualità: {product['classe_qualita_ambientale']}")
            print(f"  Potenza: {product['dati_tecnici']['potenza_kw']} kW")
            print(f"  Emissioni PP: {product['dati_tecnici']['emissioni_pp_mg_nm3']} mg/Nm³")
            print(f"  Emissioni CO: {product['dati_tecnici']['emissioni_co_g_nm3']} g/Nm³")

if __name__ == "__main__":
    main()
