"""
Script per estrarre i dati del catalogo solare termico dal PDF GSE
Genera il file JSON con l'elenco dei collettori solari ammissibili

Schema JSON output:
{
  "id_slug": "marca-modello",
  "search_text": "marca modello piano",
  "marca": "Viessmann",
  "modello": "Vitosol 100",
  "tipologia": "piano|sottovuoto|concentrazione|factory_made",
  "tipologia_collettore": "Piani",
  "area_lorda_mq": 2.52,
  "area_apertura_mq": 2.35,
  "energia_qcol_50": 1552,
  "energia_qcol_75": 893,
  "producibilita_qualificazione": 517.33
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
    if not value or value in ["-", "—", "–", "", "N.D.", "n.d."]:
        return None
    try:
        # Rimuovi spazi, unità di misura e sostituisci virgola con punto
        cleaned = str(value).strip()
        cleaned = re.sub(r'\s*(m2|mq|m²|kWh)\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace(" ", "").replace(",", ".")
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
    header_keywords = ['marca', 'modello', 'tipologia', 'collettore', 'area', 'lorda',
                       'apertura', 'superficie', 'energia', 'qcol', 'producibilità']

    # Se contiene almeno 2 parole chiave, è probabilmente un'intestazione
    keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
    return keyword_count >= 2

def normalize_tipologia(tipologia: str) -> str:
    """Normalizza la tipologia del collettore"""
    if not tipologia:
        return ""

    tip_lower = tipologia.lower()

    if 'piano' in tip_lower or 'piani' in tip_lower:
        return "piano"
    elif 'sottovuoto' in tip_lower or 'vuoto' in tip_lower or 'tubi' in tip_lower:
        return "sottovuoto"
    elif 'concentraz' in tip_lower:
        return "concentrazione"
    elif 'factory' in tip_lower or 'made' in tip_lower or 'integrat' in tip_lower:
        return "factory_made"

    return tip_lower

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
                    elif 'tipologia' in header and 'collettore' in header:
                        col_map['tipologia_collettore'] = idx
                    elif 'tipologia' in header and 'intervento' not in header:
                        col_map['tipologia'] = idx
                    elif 'utilizzo' in header:
                        col_map['utilizzo'] = idx
                    # Area lorda (AG) - la più importante!
                    elif ('area' in header and 'ag' in header) or (('area' in header or 'superficie' in header) and ('lorda' in header or 'lorde' in header)):
                        col_map['area_lorda'] = idx
                    # Area apertura (Aa)
                    elif ('area' in header and 'aa' in header) or (('area' in header or 'superficie' in header) and ('apertura' in header or 'aperta' in header)):
                        col_map['area_apertura'] = idx
                    # Energia Qcol a 50°C
                    elif 'energia' in header and ('qcol' in header or 'q col' in header) and '50' in header:
                        col_map['energia_50'] = idx
                    # Energia Qcol a 75°C
                    elif 'energia' in header and ('qcol' in header or 'q col' in header) and '75' in header:
                        col_map['energia_75'] = idx
                    # Producibilità specifica requisiti d'accesso
                    elif ('producibilità' in header or 'producibilita' in header) and ('specific' in header or 'requisit' in header or 'accesso' in header):
                        col_map['producibilita'] = idx

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
                    area_lorda = parse_number(row[col_map['area_lorda']] if 'area_lorda' in col_map and len(row) > col_map['area_lorda'] else None)
                    area_apertura = parse_number(row[col_map['area_apertura']] if 'area_apertura' in col_map and len(row) > col_map['area_apertura'] else None)
                    energia_50 = parse_number(row[col_map['energia_50']] if 'energia_50' in col_map and len(row) > col_map['energia_50'] else None)
                    energia_75 = parse_number(row[col_map['energia_75']] if 'energia_75' in col_map and len(row) > col_map['energia_75'] else None)
                    producibilita = parse_number(row[col_map['producibilita']] if 'producibilita' in col_map and len(row) > col_map['producibilita'] else None)

                    # Tipologia collettore
                    tipologia_collettore = ''
                    if 'tipologia_collettore' in col_map and len(row) > col_map['tipologia_collettore']:
                        tipologia_collettore = clean_text(row[col_map['tipologia_collettore']])
                    elif 'tipologia' in col_map and len(row) > col_map['tipologia']:
                        tipologia_collettore = clean_text(row[col_map['tipologia']])

                    # Normalizza tipologia
                    tipologia = normalize_tipologia(tipologia_collettore)

                    # Utilizzo (solo_acs, acs_riscaldamento)
                    utilizzo = ''
                    if 'utilizzo' in col_map and len(row) > col_map['utilizzo']:
                        utilizzo_raw = clean_text(row[col_map['utilizzo']]).lower()
                        if 'acs' in utilizzo_raw and 'riscaldamento' in utilizzo_raw:
                            utilizzo = 'acs_riscaldamento'
                        elif 'acs' in utilizzo_raw:
                            utilizzo = 'solo_acs'
                        else:
                            utilizzo = utilizzo_raw

                    # Crea il prodotto
                    product = {
                        "id_slug": create_slug(marca, modello),
                        "search_text": f"{marca} {modello} {tipologia}".lower().strip(),
                        "marca": marca,
                        "modello": modello,
                        "tipologia": tipologia,
                        "tipologia_collettore": tipologia_collettore,
                        "utilizzo": utilizzo,
                        "dati_tecnici": {
                            "area_lorda_mq": area_lorda,
                            "area_apertura_mq": area_apertura,
                            "energia_qcol_50": energia_50,
                            "energia_qcol_75": energia_75,
                            "producibilita_qualificazione_kwh_mq": producibilita
                        }
                    }

                    products.append(product)

    return products

def main():
    """Funzione principale"""
    # Percorsi
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs_reference" / "4 - 2C - CATALOGO SOLARE TERMICO.pdf"
    output_path = base_dir / "data" / "products_solare_termico.json"

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

    # Statistiche
    marche = set(p['marca'] for p in products_list)
    print(f"Marche uniche: {len(marche)}")

    tipologie = {}
    for p in products_list:
        tip = p['tipologia']
        tipologie[tip] = tipologie.get(tip, 0) + 1

    print(f"\nTipologie estratte:")
    for tip, count in sorted(tipologie.items()):
        print(f"  - {tip}: {count} prodotti")

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
            print(f"  Tipologia: {product['tipologia']} ({product['tipologia_collettore']})")
            dati = product['dati_tecnici']
            print(f"  Area lorda: {dati['area_lorda_mq']} m²")
            print(f"  Area apertura: {dati['area_apertura_mq']} m²")
            print(f"  Producibilità: {dati['producibilita_qualificazione_kwh_mq']} kWh/m²")

if __name__ == "__main__":
    main()
