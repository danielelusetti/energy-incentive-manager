"""
Script per l'estrazione delle tabelle dalle Regole Applicative CT 3.0.
Estrae spese ammissibili, checklist documenti e definizioni.
"""

import json
import re
import unicodedata
from pathlib import Path

import pdfplumber


def normalize_text(text: str) -> str:
    """Rimuove spazi extra, newline e normalizza il testo."""
    if not text:
        return ""
    # Rimuove caratteri speciali e bullet points
    text = text.replace("\uf0b7", "•").replace("\uf0a7", "-")
    text = unicodedata.normalize("NFKC", text)
    # Sostituisce newline e tab con spazi
    text = re.sub(r"[\n\r\t]+", " ", text)
    # Rimuove spazi multipli
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_cell(cell) -> str:
    """Pulisce il contenuto di una cella."""
    if cell is None:
        return ""
    return normalize_text(str(cell))


def is_valid_table(table: list, min_rows: int = 3) -> bool:
    """Verifica se una tabella è valida (non troppo piccola)."""
    if not table or len(table) < min_rows:
        return False
    # Verifica che abbia almeno 2 colonne
    if not table[0] or len(table[0]) < 2:
        return False
    return True


def get_table_context(page, table_bbox) -> str:
    """Estrae il testo prima della tabella per identificare l'argomento."""
    try:
        # Prendi il testo sopra la tabella
        top_area = (0, max(0, table_bbox[1] - 100), page.width, table_bbox[1])
        text_above = page.within_bbox(top_area).extract_text() or ""
        return normalize_text(text_above[-500:] if len(text_above) > 500 else text_above)
    except Exception:
        return ""


def identify_table_type(context: str, headers: list) -> str:
    """Identifica il tipo di tabella in base al contesto e agli header."""
    context_lower = context.lower()
    headers_lower = " ".join([h.lower() for h in headers if h])

    # Spese ammissibili
    if any(kw in context_lower or kw in headers_lower for kw in [
        "spese ammissibili", "spesa ammissibile", "voci di spesa",
        "costi ammissibili", "fornitura", "smontaggio"
    ]):
        return "spese_ammissibili"

    # Checklist documenti
    if any(kw in context_lower or kw in headers_lower for kw in [
        "documentazione", "documenti", "allegare", "checklist",
        "da conservare", "da allegare", "bonifico", "fattura"
    ]):
        return "checklist_documenti"

    # Requisiti tecnici
    if any(kw in context_lower or kw in headers_lower for kw in [
        "requisiti", "requisito", "minimo", "scop", "cop", "eta_s", "η"
    ]):
        return "requisiti_tecnici"

    # Soggetti ammessi
    if any(kw in context_lower or kw in headers_lower for kw in [
        "soggetti ammessi", "soggetto responsabile", "beneficiari"
    ]):
        return "soggetti_ammessi"

    # Interventi
    if any(kw in context_lower or kw in headers_lower for kw in [
        "intervento", "tipologia", "iii.a", "iii.b", "ii."
    ]):
        return "interventi"

    return "altro"


def extract_spese_ammissibili(table: list, context: str) -> list:
    """Estrae le spese ammissibili da una tabella."""
    spese = []
    headers = [clean_cell(h) for h in table[0]] if table else []

    for row in table[1:]:
        cleaned_row = [clean_cell(c) for c in row]
        if not any(cleaned_row):
            continue

        spesa = {
            "voce": cleaned_row[0] if len(cleaned_row) > 0 else "",
        }

        # Cerca colonne note/riferimento
        if len(cleaned_row) > 1:
            spesa["riferimento_intervento"] = cleaned_row[1]
        if len(cleaned_row) > 2:
            spesa["note"] = cleaned_row[2]

        if spesa["voce"]:
            spese.append(spesa)

    return spese


def extract_checklist_documenti(table: list, context: str) -> list:
    """Estrae la checklist documenti da una tabella."""
    documenti = []
    headers = [clean_cell(h).lower() for h in table[0]] if table else []

    # Determina la fase dal contesto
    fase = "Richiesta incentivo"
    if "conservare" in context.lower():
        fase = "Da conservare"
    elif "allegare" in context.lower():
        fase = "Da allegare"

    for row in table[1:]:
        cleaned_row = [clean_cell(c) for c in row]
        if not any(cleaned_row):
            continue

        doc = {
            "documento": cleaned_row[0] if len(cleaned_row) > 0 else "",
            "fase": fase,
            "obbligatorio": True  # Default obbligatorio
        }

        # Cerca indicazioni di obbligatorietà
        row_text = " ".join(cleaned_row).lower()
        if any(kw in row_text for kw in ["facoltativ", "se applicabile", "ove previsto", "se present"]):
            doc["obbligatorio"] = False

        # Note aggiuntive
        if len(cleaned_row) > 1 and cleaned_row[1]:
            doc["note"] = cleaned_row[1]

        if doc["documento"]:
            documenti.append(doc)

    return documenti


def extract_requisiti_tecnici(table: list, context: str) -> list:
    """Estrae i requisiti tecnici da una tabella."""
    requisiti = []
    headers = [clean_cell(h) for h in table[0]] if table else []

    for row in table[1:]:
        cleaned_row = [clean_cell(c) for c in row]
        if not any(cleaned_row):
            continue

        req = {"headers": headers, "values": cleaned_row}

        # Cerca di strutturare meglio
        if len(cleaned_row) >= 2:
            req = {
                "tipologia": cleaned_row[0],
                "valore": cleaned_row[1] if len(cleaned_row) > 1 else "",
                "unita": cleaned_row[2] if len(cleaned_row) > 2 else "",
                "note": cleaned_row[3] if len(cleaned_row) > 3 else "",
            }

        requisiti.append(req)

    return requisiti


def extract_bullet_lists_from_text(text: str) -> list:
    """Estrae gli elenchi puntati dal testo."""
    items = []

    # Pattern per elenchi puntati (numeri, lettere, bullet)
    patterns = [
        r'(?:^|\n)\s*(\d+)[\.)\]]\s*([^\n]+)',  # 1. item, 1) item
        r'(?:^|\n)\s*([a-z])[\.)\]]\s*([^\n]+)',  # a. item, a) item
        r'(?:^|\n)\s*[-•●◦▪]\s*([^\n]+)',  # - item, • item
        r'(?:^|\n)\s*[ivxIVX]+[\.)\]]\s*([^\n]+)',  # i. item, ii) item
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                item_text = match[-1].strip()
            else:
                item_text = match.strip()
            if item_text and len(item_text) > 5:
                items.append(normalize_text(item_text))

    return items


def extract_documentation_sections(text: str) -> dict:
    """Estrae le sezioni di documentazione dal testo."""
    sections = {
        "documenti_allegare": [],
        "documenti_conservare": [],
        "spese_ammissibili_testo": []
    }

    text_lower = text.lower()

    # Cerca sezioni "Documentazione da allegare"
    allegare_pattern = r'[Dd]ocumentazione\s+da\s+allegare[^:]*:?\s*([\s\S]*?)(?=[Dd]ocumentazione\s+da\s+conservare|$|\n\n\n)'
    allegare_matches = re.findall(allegare_pattern, text)
    for match in allegare_matches:
        items = extract_bullet_lists_from_text(match)
        sections["documenti_allegare"].extend(items)

    # Cerca sezioni "Documentazione da conservare"
    conservare_pattern = r'[Dd]ocumentazione\s+da\s+conservare[^:]*:?\s*([\s\S]*?)(?=\n\n\n|\d+\.\d+\s|$)'
    conservare_matches = re.findall(conservare_pattern, text)
    for match in conservare_matches:
        items = extract_bullet_lists_from_text(match)
        sections["documenti_conservare"].extend(items)

    # Cerca sezioni "Spese ammissibili"
    spese_pattern = r'[Ss]pese\s+ammissibili[^:]*:?\s*([\s\S]*?)(?=\n\n\n|\d+\.\d+\s|$)'
    spese_matches = re.findall(spese_pattern, text)
    for match in spese_matches:
        items = extract_bullet_lists_from_text(match)
        sections["spese_ammissibili_testo"].extend(items)

    return sections


def extract_tables_from_pdf(pdf_path: Path) -> dict:
    """Estrae tutte le tabelle e gli elenchi puntati dal PDF."""
    result = {
        "spese_ammissibili": [],
        "checklist_documenti": [],
        "documenti_allegare": [],
        "documenti_conservare": [],
        "requisiti_tecnici": [],
        "soggetti_ammessi": [],
        "interventi": [],
        "altre_tabelle": []
    }

    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Estrai testo completo per elenchi puntati
            page_text = page.extract_text() or ""
            full_text += f"\n--- PAGINA {page_num + 1} ---\n{page_text}"

            # Estrai tabelle
            tables = page.extract_tables()

            for table in tables:
                if not is_valid_table(table, min_rows=2):
                    continue

                # Ottieni contesto
                try:
                    table_settings = page.find_tables()
                    if table_settings:
                        bbox = table_settings[0].bbox
                        context = get_table_context(page, bbox)
                    else:
                        context = ""
                except Exception:
                    context = ""

                # Pulisci headers
                headers = [clean_cell(h) for h in table[0]] if table else []

                # Identifica tipo tabella
                table_type = identify_table_type(context, headers)

                print(f"Pagina {page_num + 1}: Trovata tabella tipo '{table_type}' ({len(table)} righe)")

                # Estrai in base al tipo
                if table_type == "spese_ammissibili":
                    spese = extract_spese_ammissibili(table, context)
                    result["spese_ammissibili"].extend(spese)

                elif table_type == "checklist_documenti":
                    docs = extract_checklist_documenti(table, context)
                    result["checklist_documenti"].extend(docs)

                elif table_type == "requisiti_tecnici":
                    reqs = extract_requisiti_tecnici(table, context)
                    result["requisiti_tecnici"].extend(reqs)

                else:
                    # Salva comunque per analisi manuale
                    result["altre_tabelle"].append({
                        "pagina": page_num + 1,
                        "tipo_identificato": table_type,
                        "contesto": context[:200] if context else "",
                        "headers": headers,
                        "righe": len(table)
                    })

    # Estrai elenchi puntati dal testo completo
    print("\nEstrazione elenchi puntati dal testo...")
    doc_sections = extract_documentation_sections(full_text)

    # Converti in formato strutturato
    for item in doc_sections["documenti_allegare"]:
        result["documenti_allegare"].append({
            "documento": item,
            "fase": "Da allegare alla richiesta",
            "obbligatorio": True
        })

    for item in doc_sections["documenti_conservare"]:
        result["documenti_conservare"].append({
            "documento": item,
            "fase": "Da conservare",
            "obbligatorio": True
        })

    for item in doc_sections["spese_ammissibili_testo"]:
        if item not in [s["voce"] for s in result["spese_ammissibili"]]:
            result["spese_ammissibili"].append({
                "voce": item,
                "riferimento_intervento": "",
                "note": "Estratto da testo"
            })

    return result


def remove_duplicates_from_list(items: list, key_field: str) -> list:
    """Rimuove duplicati da una lista di dizionari."""
    seen = set()
    unique = []
    for item in items:
        key = item.get(key_field, "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def main():
    # Percorsi
    base_path = Path(__file__).parent.parent
    pdf_path = base_path / "docs_reference" / "Regole_Applicative_CT_3_0.pdf"
    output_path = base_path / "data" / "compliance_tables.json"

    print(f"Lettura PDF: {pdf_path}")

    if not pdf_path.exists():
        print(f"ERRORE: File PDF non trovato: {pdf_path}")
        return

    # Estrae i dati
    result = extract_tables_from_pdf(pdf_path)

    # Rimuove duplicati
    result["spese_ammissibili"] = remove_duplicates_from_list(
        result["spese_ammissibili"], "voce"
    )
    result["checklist_documenti"] = remove_duplicates_from_list(
        result["checklist_documenti"], "documento"
    )
    result["documenti_allegare"] = remove_duplicates_from_list(
        result["documenti_allegare"], "documento"
    )
    result["documenti_conservare"] = remove_duplicates_from_list(
        result["documenti_conservare"], "documento"
    )

    # Statistiche
    print(f"\n=== RISULTATI ESTRAZIONE ===")
    print(f"Spese ammissibili: {len(result['spese_ammissibili'])}")
    print(f"Checklist documenti (tabelle): {len(result['checklist_documenti'])}")
    print(f"Documenti da allegare (testo): {len(result['documenti_allegare'])}")
    print(f"Documenti da conservare (testo): {len(result['documenti_conservare'])}")
    print(f"Requisiti tecnici: {len(result['requisiti_tecnici'])}")
    print(f"Altre tabelle: {len(result['altre_tabelle'])}")

    # Assicura che la cartella output esista
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Salva il JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSalvato: {output_path}")

    # Mostra esempi
    if result["spese_ammissibili"]:
        print("\n--- Esempio spesa ammissibile ---")
        print(json.dumps(result["spese_ammissibili"][0], ensure_ascii=False, indent=2))

    if result["documenti_allegare"]:
        print("\n--- Esempi documenti da allegare ---")
        for doc in result["documenti_allegare"][:5]:
            print(f"  - {doc['documento'][:80]}...")

    if result["documenti_conservare"]:
        print("\n--- Esempi documenti da conservare ---")
        for doc in result["documenti_conservare"][:5]:
            print(f"  - {doc['documento'][:80]}...")


if __name__ == "__main__":
    main()
