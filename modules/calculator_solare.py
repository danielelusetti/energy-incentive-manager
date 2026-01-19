"""
Modulo di calcolo incentivi Conto Termico 3.0 per Solare Termico (III.D).

Riferimento normativo: DM 7 agosto 2025 e Regole Applicative GSE (par. 9.12).
Formula principale:
    Ia_tot = Ci × Qu × Sl

dove:
- Ci = coefficiente di valorizzazione energia termica (€/kWht)
- Qu = energia termica prodotta per unità superficie (kWht/m²)
- Sl = superficie solare lorda installata (m²)

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import logging
from typing import Optional, TypedDict, Literal

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class InputSolareRiepilogo(TypedDict):
    tipologia_impianto: str
    tipo_collettore: str
    superficie_lorda_m2: float
    energia_qcol_kwh: float
    area_modulo_m2: float
    spesa_sostenuta: float
    tipo_soggetto: str


class CalcoliIntermedSolare(TypedDict):
    Qu: float  # kWht/m²
    Ci: float  # €/kWht
    Sl: float  # m²
    Ia: float  # incentivo annuo
    n: int     # numero annualità
    I_tot_lordo: float


class MassimaliSolare(TypedDict):
    spesa_ammissibile: float
    percentuale_applicata: float
    I_max_da_massimali: float
    taglio_applicato: bool
    importo_tagliato: float


class ErogazioneSolare(TypedDict):
    modalita: Literal["rata_unica", "rate_annuali"]
    rate: list[float]
    numero_rate: int


class RisultatoSolare(TypedDict):
    status: Literal["OK", "ERROR"]
    messaggio: str
    input_riepilogo: Optional[InputSolareRiepilogo]
    calcoli_intermedi: Optional[CalcoliIntermedSolare]
    massimali_applicati: Optional[MassimaliSolare]
    incentivo_totale: Optional[float]
    erogazione: Optional[ErogazioneSolare]


# ============================================================================
# COSTANTI E COEFFICIENTI
# ============================================================================

# Tipologie di impianto solare termico
TIPOLOGIE_SOLARE = {
    "acs": "Produzione acqua calda sanitaria",
    "acs_riscaldamento": "ACS + riscaldamento ambiente / calore processo bassa T",
    "concentrazione": "Collettori a concentrazione / calore processo",
    "solar_cooling": "Solar cooling",
}

# Tipi di collettore
TIPI_COLLETTORE = {
    "piano": "Collettore piano",
    "sottovuoto": "Collettore sottovuoto / tubi evacuati",
    "concentrazione": "Collettore a concentrazione",
    "factory_made": "Sistema factory made (EN 12976)",
}

# Coefficienti Ci per tipologia e fascia superficie (Tabella 16 - Allegato 2 DM 7/8/2025)
# Formato: {tipologia: {fascia_sl: Ci}}
# Fasce: <12, 12-50, 50-200, 200-500, >500 m²
CI_COEFFICIENTI = {
    "acs": {
        "lt_12": 0.35,
        "12_50": 0.32,
        "50_200": 0.13,
        "200_500": 0.12,
        "gt_500": 0.11,
    },
    "acs_riscaldamento": {
        "lt_12": 0.36,
        "12_50": 0.33,
        "50_200": 0.13,
        "200_500": 0.12,
        "gt_500": 0.11,
    },
    "concentrazione": {
        "lt_12": 0.38,
        "12_50": 0.35,
        "50_200": 0.13,
        "200_500": 0.12,
        "gt_500": 0.11,
    },
    "solar_cooling": {
        "lt_12": 0.43,
        "12_50": 0.40,
        "50_200": 0.17,
        "200_500": 0.15,
        "gt_500": 0.14,
    },
}

# Temperature medie di funzionamento per applicazione (Tabella 17 - Allegato 2)
TEMPERATURE_FUNZIONAMENTO = {
    "acs": 50,  # °C
    "acs_riscaldamento": 50,  # °C (combinato)
    "processo_bassa_t": 75,  # °C
    "solar_cooling_bassa_t": 75,  # °C
    "processo_media_t": 150,  # °C
    "solar_cooling_media_t": 150,  # °C
}

# Producibilità minima richiesta (kWht/m² anno) - par. 9.12.1
PRODUCIBILITA_MINIMA = {
    "piano": 300,       # Würzburg
    "sottovuoto": 400,  # Würzburg
    "concentrazione": 550,  # Atene
    "factory_made": 400,  # Würzburg
}

# Percentuali massime incentivo
PERCENTUALI_MASSIME = {
    "privato": 0.65,
    "impresa": 0.65,
    "PA": 1.00,
}

# Soglia per erogazione in unica soluzione
SOGLIA_RATA_UNICA = 15000.0

# Superficie massima incentivabile
SUPERFICIE_MASSIMA_M2 = 2500.0


# ============================================================================
# FUNZIONI DI CALCOLO
# ============================================================================

def get_fascia_superficie(sl: float) -> str:
    """Determina la fascia di superficie per il coefficiente Ci."""
    if sl < 12:
        return "lt_12"
    elif sl <= 50:
        return "12_50"
    elif sl <= 200:
        return "50_200"
    elif sl <= 500:
        return "200_500"
    else:
        return "gt_500"


def get_ci_coefficiente(tipologia: str, sl: float) -> float:
    """
    Restituisce il coefficiente Ci in base alla tipologia e superficie.

    Args:
        tipologia: Tipo impianto (acs, acs_riscaldamento, concentrazione, solar_cooling)
        sl: Superficie lorda m²

    Returns:
        Coefficiente Ci in €/kWht
    """
    if tipologia not in CI_COEFFICIENTI:
        tipologia = "acs"  # default

    fascia = get_fascia_superficie(sl)
    return CI_COEFFICIENTI[tipologia].get(fascia, 0.13)


def get_numero_annualita(sl: float) -> int:
    """
    Determina il numero di annualità per l'erogazione.

    Da Regole: 2 annualità per Sl <= 50m², 5 annualità per Sl > 50m²
    """
    return 2 if sl <= 50 else 5


def calcola_qu(
    tipo_collettore: str,
    qcol_kwh: float,
    area_modulo_m2: float,
    ql_mj: float = 0.0
) -> float:
    """
    Calcola Qu (energia termica per unità di superficie).

    Formule da par. 9.12.3:
    - Collettori piani/sottovuoto: Qu = Qcol / Ag
    - Factory made (EN 12976): Qu = QL / (3.6 × Ag)
    - Concentrazione: Qu = Qsol / Ag

    Args:
        tipo_collettore: Tipo di collettore
        qcol_kwh: Energia termica annua per modulo (kWht) da Solar Keymark
        area_modulo_m2: Area lorda singolo modulo (m²)
        ql_mj: Per factory made, energia in MJ

    Returns:
        Qu in kWht/m²
    """
    if area_modulo_m2 <= 0:
        return 0.0

    if tipo_collettore == "factory_made" and ql_mj > 0:
        # Conversione MJ -> kWh e divisione per area
        return (ql_mj / 3.6) / area_modulo_m2
    else:
        return qcol_kwh / area_modulo_m2


def verifica_producibilita_minima(
    tipo_collettore: str,
    qu: float
) -> tuple[bool, float]:
    """
    Verifica se la producibilità rispetta i requisiti minimi.

    Returns:
        Tuple (è_valido, producibilità_minima_richiesta)
    """
    minimo = PRODUCIBILITA_MINIMA.get(tipo_collettore, 300)
    return qu > minimo, minimo


def calculate_solar_thermal_incentive(
    tipologia_impianto: str,
    tipo_collettore: str,
    superficie_lorda_m2: float,
    energia_qcol_kwh: float,
    area_modulo_m2: float,
    spesa_totale: float,
    tipo_soggetto: str = "privato",
    energia_ql_mj: float = 0.0,
) -> RisultatoSolare:
    """
    Calcola l'incentivo Conto Termico per impianti solari termici.

    Formula: Ia_tot = Ci × Qu × Sl

    Args:
        tipologia_impianto: acs, acs_riscaldamento, concentrazione, solar_cooling
        tipo_collettore: piano, sottovuoto, concentrazione, factory_made
        superficie_lorda_m2: Superficie solare lorda totale (m²)
        energia_qcol_kwh: Energia termica annua per modulo (kWht da Solar Keymark)
        area_modulo_m2: Area lorda singolo modulo (m²)
        spesa_totale: Spesa totale sostenuta (€)
        tipo_soggetto: privato, impresa, PA
        energia_ql_mj: Solo per factory made - energia in MJ

    Returns:
        Dizionario con risultato completo del calcolo
    """

    # Validazioni iniziali
    if superficie_lorda_m2 <= 0:
        return {
            "status": "ERROR",
            "messaggio": "La superficie solare deve essere > 0",
            "input_riepilogo": None,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None,
        }

    if superficie_lorda_m2 > SUPERFICIE_MASSIMA_M2:
        return {
            "status": "ERROR",
            "messaggio": f"Superficie massima incentivabile: {SUPERFICIE_MASSIMA_M2} m²",
            "input_riepilogo": None,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None,
        }

    if area_modulo_m2 <= 0:
        return {
            "status": "ERROR",
            "messaggio": "L'area del modulo deve essere > 0",
            "input_riepilogo": None,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None,
        }

    # Calcolo Qu
    qu = calcola_qu(tipo_collettore, energia_qcol_kwh, area_modulo_m2, energia_ql_mj)

    # Verifica producibilità minima
    prod_valida, prod_minima = verifica_producibilita_minima(tipo_collettore, qu)
    if not prod_valida:
        return {
            "status": "ERROR",
            "messaggio": f"Producibilità insufficiente: {qu:.1f} kWht/m² < {prod_minima} kWht/m² minimo richiesto",
            "input_riepilogo": None,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None,
        }

    # Ottieni coefficiente Ci
    ci = get_ci_coefficiente(tipologia_impianto, superficie_lorda_m2)

    # Calcolo incentivo annuo: Ia = Ci × Qu × Sl
    ia = ci * qu * superficie_lorda_m2

    # Numero annualità
    n = get_numero_annualita(superficie_lorda_m2)

    # Incentivo totale lordo
    i_tot_lordo = ia * n

    # Applica massimale percentuale
    percentuale_max = PERCENTUALI_MASSIME.get(tipo_soggetto, 0.65)
    spesa_ammissibile = spesa_totale  # Le spese accessorie sono già incluse nei Ci
    i_max_percentuale = spesa_ammissibile * percentuale_max

    # Applica taglio se necessario
    if i_tot_lordo > i_max_percentuale:
        incentivo_finale = i_max_percentuale
        taglio_applicato = True
        importo_tagliato = i_tot_lordo - i_max_percentuale
    else:
        incentivo_finale = i_tot_lordo
        taglio_applicato = False
        importo_tagliato = 0.0

    # Calcolo erogazione
    if incentivo_finale <= SOGLIA_RATA_UNICA:
        modalita = "rata_unica"
        rate = [incentivo_finale]
        numero_rate = 1
    else:
        modalita = "rate_annuali"
        rata_annua = incentivo_finale / n
        rate = [rata_annua] * n
        numero_rate = n

    # Costruisci risultato
    return {
        "status": "OK",
        "messaggio": "Calcolo completato con successo",
        "input_riepilogo": {
            "tipologia_impianto": TIPOLOGIE_SOLARE.get(tipologia_impianto, tipologia_impianto),
            "tipo_collettore": TIPI_COLLETTORE.get(tipo_collettore, tipo_collettore),
            "superficie_lorda_m2": superficie_lorda_m2,
            "energia_qcol_kwh": energia_qcol_kwh,
            "area_modulo_m2": area_modulo_m2,
            "spesa_sostenuta": spesa_totale,
            "tipo_soggetto": tipo_soggetto,
        },
        "calcoli_intermedi": {
            "Qu": round(qu, 2),
            "Ci": ci,
            "Sl": superficie_lorda_m2,
            "Ia": round(ia, 2),
            "n": n,
            "I_tot_lordo": round(i_tot_lordo, 2),
        },
        "massimali_applicati": {
            "spesa_ammissibile": spesa_ammissibile,
            "percentuale_applicata": percentuale_max,
            "I_max_da_massimali": round(i_max_percentuale, 2),
            "taglio_applicato": taglio_applicato,
            "importo_tagliato": round(importo_tagliato, 2),
        },
        "incentivo_totale": round(incentivo_finale, 2),
        "erogazione": {
            "modalita": modalita,
            "rate": [round(r, 2) for r in rate],
            "numero_rate": numero_rate,
        },
    }


def stima_energia_da_superficie(
    tipo_collettore: str,
    superficie_m2: float,
    area_modulo_m2: float = 2.0
) -> float:
    """
    Stima approssimativa dell'energia producibile data la superficie.
    Utile quando non si hanno i dati Solar Keymark.

    Usa valori medi tipici:
    - Collettori piani: ~350-450 kWht/m² anno (Würzburg)
    - Sottovuoto: ~450-550 kWht/m² anno
    - Concentrazione: ~600-800 kWht/m² anno (Atene)

    Returns:
        Energia stimata per singolo modulo (kWht)
    """
    qu_tipici = {
        "piano": 400,
        "sottovuoto": 500,
        "concentrazione": 650,
        "factory_made": 450,
    }

    qu = qu_tipici.get(tipo_collettore, 400)
    return qu * area_modulo_m2


# ============================================================================
# FUNZIONE DI TEST
# ============================================================================

if __name__ == "__main__":
    # Test con valori di esempio
    risultato = calculate_solar_thermal_incentive(
        tipologia_impianto="acs",
        tipo_collettore="piano",
        superficie_lorda_m2=8.0,  # 4 pannelli da 2m²
        energia_qcol_kwh=800,     # kWht/anno per modulo (da Solar Keymark)
        area_modulo_m2=2.0,
        spesa_totale=5000.0,
        tipo_soggetto="privato",
    )

    print("\n=== TEST SOLARE TERMICO ===")
    print(f"Status: {risultato['status']}")

    if risultato['status'] == 'OK':
        print(f"\nCalcoli:")
        print(f"  Qu = {risultato['calcoli_intermedi']['Qu']} kWht/m²")
        print(f"  Ci = {risultato['calcoli_intermedi']['Ci']} €/kWht")
        print(f"  Sl = {risultato['calcoli_intermedi']['Sl']} m²")
        print(f"  Ia = {risultato['calcoli_intermedi']['Ia']} €/anno")
        print(f"  n = {risultato['calcoli_intermedi']['n']} annualità")
        print(f"\nIncentivo totale: € {risultato['incentivo_totale']}")
        print(f"Erogazione: {risultato['erogazione']['modalita']}")
        print(f"Rate: {risultato['erogazione']['rate']}")
