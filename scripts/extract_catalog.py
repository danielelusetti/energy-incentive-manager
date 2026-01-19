"""
Script per l'estrazione del catalogo pompe di calore da PDF.
Converte il PDF in un file JSON strutturato e pulito.
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
    # Rimuove caratteri di controllo e normalizza unicode
    text = unicodedata.normalize("NFKC", text)
    # Sostituisce newline e tab con spazi
    text = re.sub(r"[\n\r\t]+", " ", text)
    # Rimuove spazi multipli
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_italian_number(value: str) -> float | None:
    """
    Converte un numero italiano (virgola come decimale) in float.
    Es: "4,52" -> 4.52, "1.234,56" -> 1234.56
    """
    if not value:
        return None

    # Rimuove spazi e unità di misura comuni
    value = re.sub(r"\s*(kW|kw|KW|W|w)?\s*$", "", str(value).strip())

    if not value:
        return None

    try:
        # Prova prima come numero normale (già float o int)
        return float(value)
    except ValueError:
        pass

    try:
        # Formato italiano: punto come separatore migliaia, virgola come decimale
        # Rimuove i punti delle migliaia e sostituisce la virgola con il punto
        cleaned = value.replace(".", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None


def create_slug(marca: str, modello: str) -> str:
    """Crea un ID univoco slug dal nome marca e modello."""
    text = f"{marca}_{modello}".lower()
    # Rimuove accenti
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Sostituisce caratteri non alfanumerici con trattini
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Rimuove trattini multipli e agli estremi
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def normalize_tipologia(tipologia: str) -> str:
    """Normalizza i nomi delle tipologie di pompa di calore."""
    if not tipologia:
        return ""

    tipologia = normalize_text(tipologia).lower()

    # Mappatura delle varianti comuni
    mappings = {
        "aria/acqua": ["aria acqua", "aria-acqua", "a/a", "air to water", "air/water"],
        "aria/aria": ["aria aria", "aria-aria", "air to air", "air/air"],
        "acqua/acqua": ["acqua acqua", "acqua-acqua", "water to water", "water/water"],
        "acqua/aria": ["acqua aria", "acqua-aria", "water to air", "water/air"],
        "geotermica": ["geotermico", "ground source", "terra", "suolo"],
    }

    for normalized, variants in mappings.items():
        if tipologia in variants or any(v in tipologia for v in variants):
            return normalized

    # Capitalizza se non trovato
    return tipologia.title()


def extract_catalog_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Estrae i dati del catalogo dal PDF.
    Restituisce una lista di dizionari con i dati delle pompe di calore.
    """
    products = []

    with pdfplumber.open(pdf_path) as pdf:
        all_rows = []
        headers = None

        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                for row_idx, row in enumerate(table):
                    if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                        continue

                    # Pulisce la riga
                    cleaned_row = [normalize_text(str(cell)) if cell else "" for cell in row]

                    # Identifica l'header (prima riga con "Marca" o simili)
                    row_lower = [c.lower() for c in cleaned_row]
                    if headers is None and any(
                        keyword in " ".join(row_lower)
                        for keyword in ["marca", "modello", "potenza", "cop"]
                    ):
                        headers = cleaned_row
                        continue

                    if headers:
                        all_rows.append(cleaned_row)

        # Se non abbiamo trovato header, usiamo quelli di default
        if headers is None:
            headers = ["Marca", "Modello", "Tipologia", "Potenza", "COP", "On/Off-Inverter"]

        # Mappa le colonne
        header_map = {}
        for idx, h in enumerate(headers):
            h_lower = h.lower()
            if "marca" in h_lower:
                header_map["marca"] = idx
            elif "modello" in h_lower:
                header_map["modello"] = idx
            elif "tipolog" in h_lower:
                header_map["tipologia"] = idx
            elif "potenza" in h_lower or "kw" in h_lower:
                header_map["potenza_kw"] = idx
            elif "cop" in h_lower or "scop" in h_lower:
                header_map["cop"] = idx
            elif "inverter" in h_lower or "on/off" in h_lower or "on-off" in h_lower:
                header_map["on_off_inverter"] = idx

        # Processa le righe
        for row in all_rows:
            try:
                marca = row[header_map.get("marca", 0)] if header_map.get("marca") is not None and len(row) > header_map.get("marca", 0) else ""
                modello = row[header_map.get("modello", 1)] if header_map.get("modello") is not None and len(row) > header_map.get("modello", 1) else ""

                # Salta righe senza marca o modello validi
                if not marca or not modello or marca.lower() in ["marca", ""]:
                    continue

                product = {
                    "id": create_slug(marca, modello),
                    "marca": marca,
                    "modello": modello,
                }

                # Tipologia
                if "tipologia" in header_map and len(row) > header_map["tipologia"]:
                    product["tipologia"] = normalize_tipologia(row[header_map["tipologia"]])

                # Potenza
                if "potenza_kw" in header_map and len(row) > header_map["potenza_kw"]:
                    potenza = parse_italian_number(row[header_map["potenza_kw"]])
                    if potenza is not None:
                        product["potenza_kw"] = potenza

                # COP
                if "cop" in header_map and len(row) > header_map["cop"]:
                    cop = parse_italian_number(row[header_map["cop"]])
                    if cop is not None:
                        product["cop"] = cop

                # On/Off o Inverter
                if "on_off_inverter" in header_map and len(row) > header_map["on_off_inverter"]:
                    value = row[header_map["on_off_inverter"]].strip()
                    if value:
                        product["on_off_inverter"] = value

                products.append(product)

            except (IndexError, KeyError) as e:
                print(f"Errore nel processare riga: {row} - {e}")
                continue

    return products


def remove_duplicates(products: list[dict]) -> list[dict]:
    """
    Rimuove i duplicati basandosi su marca, modello, tipologia, potenza e COP.
    Mantiene il primo prodotto trovato per ogni combinazione unica.
    """
    seen = set()
    unique_products = []

    for product in products:
        # Crea una chiave univoca basata sui campi principali
        key = (
            product.get("marca", "").lower(),
            product.get("modello", "").lower(),
            product.get("tipologia", "").lower(),
            product.get("potenza_kw"),
            product.get("cop"),
        )

        if key not in seen:
            seen.add(key)
            unique_products.append(product)

    return unique_products


def main():
    # Percorsi
    base_path = Path(__file__).parent.parent
    pdf_path = base_path / "docs_reference" / "2 - 2A - CATALOGO POMPE DI CALORE.pdf"
    output_path = base_path / "data" / "catalogo_pdc.json"

    print(f"Lettura PDF: {pdf_path}")

    if not pdf_path.exists():
        print(f"ERRORE: File PDF non trovato: {pdf_path}")
        return

    # Estrae i dati
    products = extract_catalog_from_pdf(pdf_path)
    print(f"Trovati {len(products)} prodotti (con duplicati)")

    # Rimuove duplicati
    products = remove_duplicates(products)
    print(f"Prodotti unici: {len(products)}")

    # Assicura che la cartella output esista
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Salva il JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"Salvato: {output_path}")

    # Mostra un esempio
    if products:
        print("\nEsempio primo prodotto:")
        print(json.dumps(products[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
