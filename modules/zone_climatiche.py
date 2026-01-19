"""
Mappatura Province Italiane → Zone Climatiche

Basato su DPR 412/1993 e successive modifiche (D.Lgs. 192/2005)
Fonte: Tabella A e B allegati al DPR 412/93

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

from typing import Dict, List, Tuple

# Mappatura completa: Provincia → Zona Climatica
# Formato: {"Sigla Provincia": "Zona"}
PROVINCE_ZONE_CLIMATICHE: Dict[str, str] = {
    # VALLE D'AOSTA
    "AO": "E",

    # PIEMONTE
    "AL": "E",
    "AT": "E",
    "BI": "E",
    "CN": "E",
    "NO": "E",
    "TO": "E",
    "VB": "E",
    "VC": "E",

    # LIGURIA
    "GE": "D",
    "IM": "C",
    "SP": "D",
    "SV": "D",

    # LOMBARDIA
    "BG": "E",
    "BS": "E",
    "CO": "E",
    "CR": "E",
    "LC": "E",
    "LO": "E",
    "MB": "E",
    "MI": "E",
    "MN": "E",
    "PV": "E",
    "SO": "F",
    "VA": "E",

    # TRENTINO-ALTO ADIGE
    "BZ": "F",
    "TN": "F",

    # VENETO
    "BL": "F",
    "PD": "E",
    "RO": "E",
    "TV": "E",
    "VE": "E",
    "VR": "E",
    "VI": "E",

    # FRIULI-VENEZIA GIULIA
    "GO": "E",
    "PN": "E",
    "TS": "D",
    "UD": "E",

    # EMILIA-ROMAGNA
    "BO": "E",
    "FC": "E",
    "FE": "E",
    "MO": "E",
    "PC": "E",
    "PR": "E",
    "RA": "E",
    "RE": "E",
    "RN": "E",

    # TOSCANA
    "AR": "D",
    "FI": "D",
    "GR": "C",
    "LI": "C",
    "LU": "D",
    "MS": "D",
    "PI": "D",
    "PO": "D",
    "PT": "D",
    "SI": "D",

    # UMBRIA
    "PG": "E",
    "TR": "D",

    # MARCHE
    "AN": "D",
    "AP": "D",
    "FM": "D",
    "MC": "D",
    "PU": "D",

    # LAZIO
    "FR": "D",
    "LT": "C",
    "RI": "E",
    "RM": "D",
    "VT": "D",

    # ABRUZZO
    "AQ": "E",
    "CH": "D",
    "PE": "D",
    "TE": "D",

    # MOLISE
    "CB": "D",
    "IS": "E",

    # CAMPANIA
    "AV": "D",
    "BN": "D",
    "CE": "C",
    "NA": "C",
    "SA": "C",

    # PUGLIA
    "BA": "C",
    "BT": "C",
    "BR": "C",
    "FG": "C",
    "LE": "C",
    "TA": "C",

    # BASILICATA
    "MT": "D",
    "PZ": "D",

    # CALABRIA
    "CS": "C",
    "CZ": "C",
    "KR": "C",
    "RC": "B",
    "VV": "C",

    # SICILIA
    "AG": "B",
    "CL": "B",
    "CT": "B",
    "EN": "C",
    "ME": "B",
    "PA": "B",
    "RG": "B",
    "SR": "B",
    "TP": "B",

    # SARDEGNA
    "CA": "C",
    "CI": "C",
    "NU": "C",
    "OR": "C",
    "SS": "C",
    "SU": "C",
}


# Mappatura Regione → Lista Province
REGIONI_PROVINCE: Dict[str, List[Tuple[str, str]]] = {
    "Valle d'Aosta": [
        ("AO", "Aosta")
    ],
    "Piemonte": [
        ("AL", "Alessandria"),
        ("AT", "Asti"),
        ("BI", "Biella"),
        ("CN", "Cuneo"),
        ("NO", "Novara"),
        ("TO", "Torino"),
        ("VB", "Verbano-Cusio-Ossola"),
        ("VC", "Vercelli"),
    ],
    "Liguria": [
        ("GE", "Genova"),
        ("IM", "Imperia"),
        ("SP", "La Spezia"),
        ("SV", "Savona"),
    ],
    "Lombardia": [
        ("BG", "Bergamo"),
        ("BS", "Brescia"),
        ("CO", "Como"),
        ("CR", "Cremona"),
        ("LC", "Lecco"),
        ("LO", "Lodi"),
        ("MB", "Monza e Brianza"),
        ("MI", "Milano"),
        ("MN", "Mantova"),
        ("PV", "Pavia"),
        ("SO", "Sondrio"),
        ("VA", "Varese"),
    ],
    "Trentino-Alto Adige": [
        ("BZ", "Bolzano"),
        ("TN", "Trento"),
    ],
    "Veneto": [
        ("BL", "Belluno"),
        ("PD", "Padova"),
        ("RO", "Rovigo"),
        ("TV", "Treviso"),
        ("VE", "Venezia"),
        ("VR", "Verona"),
        ("VI", "Vicenza"),
    ],
    "Friuli-Venezia Giulia": [
        ("GO", "Gorizia"),
        ("PN", "Pordenone"),
        ("TS", "Trieste"),
        ("UD", "Udine"),
    ],
    "Emilia-Romagna": [
        ("BO", "Bologna"),
        ("FC", "Forlì-Cesena"),
        ("FE", "Ferrara"),
        ("MO", "Modena"),
        ("PC", "Piacenza"),
        ("PR", "Parma"),
        ("RA", "Ravenna"),
        ("RE", "Reggio Emilia"),
        ("RN", "Rimini"),
    ],
    "Toscana": [
        ("AR", "Arezzo"),
        ("FI", "Firenze"),
        ("GR", "Grosseto"),
        ("LI", "Livorno"),
        ("LU", "Lucca"),
        ("MS", "Massa-Carrara"),
        ("PI", "Pisa"),
        ("PO", "Prato"),
        ("PT", "Pistoia"),
        ("SI", "Siena"),
    ],
    "Umbria": [
        ("PG", "Perugia"),
        ("TR", "Terni"),
    ],
    "Marche": [
        ("AN", "Ancona"),
        ("AP", "Ascoli Piceno"),
        ("FM", "Fermo"),
        ("MC", "Macerata"),
        ("PU", "Pesaro e Urbino"),
    ],
    "Lazio": [
        ("FR", "Frosinone"),
        ("LT", "Latina"),
        ("RI", "Rieti"),
        ("RM", "Roma"),
        ("VT", "Viterbo"),
    ],
    "Abruzzo": [
        ("AQ", "L'Aquila"),
        ("CH", "Chieti"),
        ("PE", "Pescara"),
        ("TE", "Teramo"),
    ],
    "Molise": [
        ("CB", "Campobasso"),
        ("IS", "Isernia"),
    ],
    "Campania": [
        ("AV", "Avellino"),
        ("BN", "Benevento"),
        ("CE", "Caserta"),
        ("NA", "Napoli"),
        ("SA", "Salerno"),
    ],
    "Puglia": [
        ("BA", "Bari"),
        ("BT", "Barletta-Andria-Trani"),
        ("BR", "Brindisi"),
        ("FG", "Foggia"),
        ("LE", "Lecce"),
        ("TA", "Taranto"),
    ],
    "Basilicata": [
        ("MT", "Matera"),
        ("PZ", "Potenza"),
    ],
    "Calabria": [
        ("CS", "Cosenza"),
        ("CZ", "Catanzaro"),
        ("KR", "Crotone"),
        ("RC", "Reggio Calabria"),
        ("VV", "Vibo Valentia"),
    ],
    "Sicilia": [
        ("AG", "Agrigento"),
        ("CL", "Caltanissetta"),
        ("CT", "Catania"),
        ("EN", "Enna"),
        ("ME", "Messina"),
        ("PA", "Palermo"),
        ("RG", "Ragusa"),
        ("SR", "Siracusa"),
        ("TP", "Trapani"),
    ],
    "Sardegna": [
        ("CA", "Cagliari"),
        ("CI", "Carbonia-Iglesias"),
        ("NU", "Nuoro"),
        ("OR", "Oristano"),
        ("SS", "Sassari"),
        ("SU", "Sud Sardegna"),
    ],
}


def get_zona_climatica(provincia_sigla: str) -> str:
    """
    Restituisce la zona climatica per una provincia.

    Args:
        provincia_sigla: Sigla della provincia (es. "MI", "RM")

    Returns:
        Zona climatica (A-F) o "E" come default
    """
    return PROVINCE_ZONE_CLIMATICHE.get(provincia_sigla.upper(), "E")


def get_province_by_regione(regione: str) -> List[Tuple[str, str]]:
    """
    Restituisce la lista delle province per una regione.

    Args:
        regione: Nome della regione

    Returns:
        Lista di tuple (sigla, nome_provincia)
    """
    return REGIONI_PROVINCE.get(regione, [])


def get_lista_regioni() -> List[str]:
    """
    Restituisce la lista ordinata di tutte le regioni italiane.

    Returns:
        Lista dei nomi delle regioni
    """
    return sorted(REGIONI_PROVINCE.keys())


def get_info_provincia(provincia_sigla: str) -> Dict[str, str]:
    """
    Restituisce informazioni complete su una provincia.

    Args:
        provincia_sigla: Sigla della provincia

    Returns:
        Dict con sigla, nome provincia, regione, zona climatica
    """
    provincia_sigla = provincia_sigla.upper()

    # Trova la regione
    regione_trovata = None
    nome_provincia = None

    for regione, province in REGIONI_PROVINCE.items():
        for sigla, nome in province:
            if sigla == provincia_sigla:
                regione_trovata = regione
                nome_provincia = nome
                break
        if regione_trovata:
            break

    zona = get_zona_climatica(provincia_sigla)

    return {
        "sigla": provincia_sigla,
        "nome": nome_provincia or "Sconosciuta",
        "regione": regione_trovata or "Sconosciuta",
        "zona_climatica": zona
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST MAPPATURA ZONE CLIMATICHE")
    print("="*70)

    # Test 1: Milano
    print("\nTest 1: Milano (MI)")
    info = get_info_provincia("MI")
    print(f"  Provincia: {info['nome']} ({info['sigla']})")
    print(f"  Regione: {info['regione']}")
    print(f"  Zona Climatica: {info['zona_climatica']}")

    # Test 2: Roma
    print("\nTest 2: Roma (RM)")
    info = get_info_provincia("RM")
    print(f"  Provincia: {info['nome']} ({info['sigla']})")
    print(f"  Regione: {info['regione']}")
    print(f"  Zona Climatica: {info['zona_climatica']}")

    # Test 3: Palermo
    print("\nTest 3: Palermo (PA)")
    info = get_info_provincia("PA")
    print(f"  Provincia: {info['nome']} ({info['sigla']})")
    print(f"  Regione: {info['regione']}")
    print(f"  Zona Climatica: {info['zona_climatica']}")

    # Test 4: Lista province Lombardia
    print("\n\nProvince Lombardia:")
    province_lombardia = get_province_by_regione("Lombardia")
    for sigla, nome in province_lombardia:
        zona = get_zona_climatica(sigla)
        print(f"  {nome} ({sigla}): Zona {zona}")

    print("\n" + "="*70)
