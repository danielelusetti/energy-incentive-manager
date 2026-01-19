"""
Script per estrarre i dati del catalogo pompe di calore dal PDF GSE
Genera il file JSON con l'elenco delle PDC ammissibili al Conto Termico

Colonne del PDF:
- Tipologia (2.A, 2.B, etc.)
- Tipologia funzionamento (Elettrica, Gas)
- Tipologia scambio (Aria/Acqua, Acqua/Acqua, etc.)
- Denominazione Commerciale
- Marca
- Modello
- Identificativo modello unità esterna
- Identificativo modello unità interna
- Potenza termica [kW]
- Presenza inverter
- COP
- GUE
- Emissioni NO2
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

def clean_text(text: str) -> str:
    """Rimuove spazi extra e caratteri di a capo"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text).strip())

def parse_number(value: str) -> Optional[float]:
    """Converte una stringa numerica (con virgola italiana) in float"""
    if not value or str(value).strip() in ["-", "—", "–", "", "N/A", "n/a", "NO", "SI"]:
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

def normalize_tipologia_scambio(value: str) -> str:
    """Normalizza la tipologia di scambio"""
    if not value:
        return ""
    value = clean_text(value).lower()

    mappings = {
        "aria/acqua": ["aria acqua", "aria-acqua", "aria / acqua", "air/water", "air to water"],
        "aria/aria": ["aria aria", "aria-aria", "aria / aria", "air/air", "air to air"],
        "acqua/acqua": ["acqua acqua", "acqua-acqua", "acqua / acqua", "water/water"],
        "acqua glicolata/acqua": ["acqua glicolata acqua", "acqua glicolata/acqua", "glicolata"],
        "salamoia/acqua": ["salamoia acqua", "salamoia/acqua", "brine"],
        "acqua di falda/acqua": ["acqua di falda", "falda/acqua", "groundwater"],
    }

    for normalized, variants in mappings.items():
        if value in variants or any(v in value for v in variants):
            return normalized

    # Ritorna il valore capitalizzato se non mappato
    return value.title()

def is_header_row(row: List) -> bool:
    """Identifica se una riga è un'intestazione"""
    if not row:
        return False

    row_text = ' '.join([str(cell).lower() if cell else '' for cell in row])

    # Parole chiave delle intestazioni per PDC
    header_keywords = ['marca', 'modello', 'potenza', 'cop', 'gue', 'tipologia',
                       'funzionamento', 'scambio', 'identificativo', 'unità', 'unita',
                       'inverter', 'emissioni', 'denominazione']

    keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
    return keyword_count >= 2

def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Estrae tutte le tabelle dal PDF e le converte in lista di prodotti"""
    products = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Totale pagine: {len(pdf.pages)}")

        for page_num, page in enumerate(pdf.pages, 1):
            if page_num % 50 == 0:
                print(f"Elaborazione pagina {page_num}...")

            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Identifica la riga di intestazione
                header_idx = None
                for idx, row in enumerate(table[:5]):
                    if is_header_row(row):
                        header_idx = idx
                        break

                if header_idx is None:
                    header_idx = 0

                headers = [clean_text(h).lower() if h else '' for h in table[header_idx]]

                # Mappa le colonne in base all'header
                col_map = {}
                for idx, header in enumerate(headers):
                    h = header.lower()
                    if 'tipologia' in h and ('intervento' in h or len(h) < 15):
                        if 'tipologia' not in col_map:  # Prima tipologia = tipo intervento
                            col_map['tipologia'] = idx
                    elif 'funzionamento' in h or ('tipologia' in h and 'funzionamento' in h):
                        col_map['funzionamento'] = idx
                    elif 'scambio' in h or ('tipologia' in h and 'scambio' in h):
                        col_map['scambio'] = idx
                    elif 'denominazione' in h or 'commerciale' in h:
                        col_map['denominazione'] = idx
                    elif 'marca' in h or 'costruttore' in h:
                        col_map['marca'] = idx
                    elif 'modello' in h and 'identificativo' not in h:
                        col_map['modello'] = idx
                    elif 'identificativo' in h and 'esterna' in h:
                        col_map['id_esterna'] = idx
                    elif 'identificativo' in h and 'interna' in h:
                        col_map['id_interna'] = idx
                    elif 'potenza' in h and ('termica' in h or 'kw' in h):
                        col_map['potenza'] = idx
                    elif 'inverter' in h or 'presenza' in h:
                        col_map['inverter'] = idx
                    elif h == 'cop' or ('cop' in h and 'scop' not in h):
                        col_map['cop'] = idx
                    elif 'gue' in h:
                        col_map['gue'] = idx
                    elif 'emissioni' in h or 'no2' in h or 'nox' in h:
                        col_map['emissioni_no2'] = idx

                # Elabora le righe di dati
                for row in table[header_idx + 1:]:
                    if not row or is_header_row(row):
                        continue

                    # Estrai marca - obbligatoria
                    marca = ""
                    if 'marca' in col_map and len(row) > col_map['marca']:
                        marca = clean_text(row[col_map['marca']])

                    # Estrai modello - obbligatorio
                    modello = ""
                    if 'modello' in col_map and len(row) > col_map['modello']:
                        modello = clean_text(row[col_map['modello']])

                    # Salta righe senza marca o modello
                    if not marca or not modello or len(marca) < 2:
                        continue

                    # Salta righe che sembrano intestazioni
                    if marca.lower() in ['marca', 'costruttore']:
                        continue

                    # Estrai tutti gli altri campi
                    tipologia = ""
                    if 'tipologia' in col_map and len(row) > col_map['tipologia']:
                        tipologia = clean_text(row[col_map['tipologia']])

                    funzionamento = ""
                    if 'funzionamento' in col_map and len(row) > col_map['funzionamento']:
                        funzionamento = clean_text(row[col_map['funzionamento']])

                    scambio = ""
                    if 'scambio' in col_map and len(row) > col_map['scambio']:
                        scambio = normalize_tipologia_scambio(row[col_map['scambio']])

                    denominazione = ""
                    if 'denominazione' in col_map and len(row) > col_map['denominazione']:
                        denominazione = clean_text(row[col_map['denominazione']])

                    id_esterna = ""
                    if 'id_esterna' in col_map and len(row) > col_map['id_esterna']:
                        id_esterna = clean_text(row[col_map['id_esterna']])

                    id_interna = ""
                    if 'id_interna' in col_map and len(row) > col_map['id_interna']:
                        id_interna = clean_text(row[col_map['id_interna']])

                    potenza = None
                    if 'potenza' in col_map and len(row) > col_map['potenza']:
                        potenza = parse_number(row[col_map['potenza']])

                    inverter = ""
                    if 'inverter' in col_map and len(row) > col_map['inverter']:
                        inv_val = clean_text(row[col_map['inverter']]).upper()
                        if inv_val in ['SI', 'SÌ', 'YES', 'S']:
                            inverter = "SI"
                        elif inv_val in ['NO', 'N']:
                            inverter = "NO"
                        else:
                            inverter = inv_val

                    cop = None
                    if 'cop' in col_map and len(row) > col_map['cop']:
                        cop = parse_number(row[col_map['cop']])

                    gue = None
                    if 'gue' in col_map and len(row) > col_map['gue']:
                        gue = parse_number(row[col_map['gue']])

                    emissioni_no2 = None
                    if 'emissioni_no2' in col_map and len(row) > col_map['emissioni_no2']:
                        emissioni_no2 = parse_number(row[col_map['emissioni_no2']])

                    # Crea il prodotto con struttura completa
                    product = {
                        "id_slug": create_slug(marca, modello),
                        "search_text": f"{marca} {modello} {denominazione} {scambio}".lower().strip(),
                        "marca": marca,
                        "modello": modello,
                        "denominazione_commerciale": denominazione,
                        "tipologia_intervento": tipologia,
                        "tipologia_funzionamento": funzionamento,
                        "tipologia_scambio": scambio,
                        "identificativo_unita_esterna": id_esterna,
                        "identificativo_unita_interna": id_interna,
                        "dati_tecnici": {
                            "potenza_kw": potenza,
                            "cop": cop,
                            "gue": gue,
                            "presenza_inverter": inverter,
                            "emissioni_no2": emissioni_no2
                        }
                    }

                    products.append(product)

    return products

def main():
    """Funzione principale"""
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "docs_reference" / "2 - 2A - CATALOGO POMPE DI CALORE.pdf"
    output_path = base_dir / "data" / "catalogo_pdc.json"

    if not pdf_path.exists():
        print(f"ERRORE: File PDF non trovato: {pdf_path}")
        return

    print(f"Inizio estrazione da: {pdf_path}")
    print("Questo potrebbe richiedere alcuni minuti per PDF grandi...")

    # Estrai i dati
    products = extract_tables_from_pdf(str(pdf_path))

    print(f"\nTotale prodotti estratti: {len(products)}")

    # Rimuovi duplicati basandosi su marca + modello + potenza + cop
    unique_products = {}
    for product in products:
        # Chiave univoca
        key = (
            product['marca'].lower(),
            product['modello'].lower(),
            product['dati_tecnici']['potenza_kw'],
            product['dati_tecnici']['cop']
        )
        if key not in unique_products:
            unique_products[key] = product

    products_list = list(unique_products.values())
    print(f"Prodotti unici dopo deduplicazione: {len(products_list)}")

    # Ordina per marca e modello
    products_list.sort(key=lambda x: (x['marca'].lower(), x['modello'].lower()))

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
            print(f"  Denominazione: {product['denominazione_commerciale']}")
            print(f"  Tipologia: {product['tipologia_intervento']} - {product['tipologia_funzionamento']}")
            print(f"  Scambio: {product['tipologia_scambio']}")
            print(f"  Potenza: {product['dati_tecnici']['potenza_kw']} kW")
            print(f"  COP: {product['dati_tecnici']['cop']}")
            print(f"  GUE: {product['dati_tecnici']['gue']}")
            print(f"  Inverter: {product['dati_tecnici']['presenza_inverter']}")
            if product['identificativo_unita_esterna']:
                print(f"  Unità esterna: {product['identificativo_unita_esterna']}")
            if product['identificativo_unita_interna']:
                print(f"  Unità interna: {product['identificativo_unita_interna']}")

if __name__ == "__main__":
    main()
