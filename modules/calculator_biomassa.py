"""
Modulo di calcolo incentivi Conto Termico 3.0 per Generatori a Biomassa (III.C).

Riferimento normativo: D.M. 7 agosto 2025 - Regole Applicative CT 3.0
Paragrafo 9.9.5 - Sostituzione di impianti di climatizzazione invernale esistenti
con generatori di calore alimentati a biomassa.

Tipologie di intervento:
    - Caldaie a biomassa ≤ 500 kW
    - Caldaie a biomassa > 500 kW e ≤ 2.000 kW
    - Stufe e termocamini a pellet
    - Termocamini a legna
    - Stufe a legna

Formule di calcolo:
    - Caldaie: I = Pn × hr × Ci × Ce
    - Stufe/Termocamini: I = 3.35 × ln(Pn) × hr × Ci × Ce

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import math
import logging
from typing import Optional, TypedDict, Literal

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class InputRiepilogoBiomassa(TypedDict):
    tipo_generatore: str
    zona_climatica: str
    potenza_kw: float
    spesa_sostenuta: float
    tipo_soggetto: str
    classe_emissione: str
    riduzione_emissioni_pct: float
    tipo_combustibile_sostituito: str  # biomassa, carbone, olio, gasolio, gpl, metano, altro


class CalcoliIntermediBiomassa(TypedDict):
    hr: int
    Ci: float
    Ce: float
    I_annuo: float
    n: int
    I_tot_lordo: float


class MassimaliApplicatiBiomassa(TypedDict):
    spesa_ammissibile: float
    massimale_unitario_applicato: float
    percentuale_applicata: float
    I_max_da_massimali: float
    taglio_applicato: bool
    importo_tagliato: float


class ErogazioneBiomassa(TypedDict):
    modalita: Literal["rata_unica", "rate_annuali"]
    rate: list[float]
    numero_rate: int


class RisultatoCalcoloBiomassa(TypedDict):
    status: Literal["OK", "ERROR"]
    messaggio: str
    input_riepilogo: InputRiepilogoBiomassa
    calcoli_intermedi: Optional[CalcoliIntermediBiomassa]
    massimali_applicati: Optional[MassimaliApplicatiBiomassa]
    incentivo_totale: Optional[float]
    erogazione: Optional[ErogazioneBiomassa]


# ============================================================================
# COSTANTI E DATI (da Regole Applicative CT 3.0 - DM 7/8/2025)
# ============================================================================

# Tipologie di generatori a biomassa
TIPI_GENERATORE = {
    "caldaia_lte_500": "Caldaia a biomassa ≤ 500 kW",
    "caldaia_gt_500": "Caldaia a biomassa > 500 kW e ≤ 2.000 kW",
    "stufa_pellet": "Stufa a pellet",
    "termocamino_pellet": "Termocamino a pellet",
    "termocamino_legna": "Termocamino a legna",
    "stufa_legna": "Stufa a legna"
}

# Coefficienti Ci (€/kWht) - Tabella 9 Allegato 2 DM 7/8/2025
# Riferimento: Regole Applicative par. 9.9.5
COEFFICIENTI_CI = {
    "caldaia_lte_500": {
        "fasce": [
            {"potenza_min_kw": 0, "potenza_max_kw": 35, "Ci": 0.060},
            {"potenza_min_kw": 35, "potenza_max_kw": 150, "Ci": 0.025},
            {"potenza_min_kw": 150, "potenza_max_kw": 500, "Ci": 0.020},
        ]
    },
    "caldaia_gt_500": {
        "Ci": 0.020  # Per caldaie > 500 kW
    },
    "stufa_pellet": {"Ci": 0.055},
    "termocamino_pellet": {"Ci": 0.055},
    "termocamino_legna": {"Ci": 0.045},
    "stufa_legna": {"Ci": 0.045}
}

# Ore di funzionamento (hr) per zona climatica - Tabella 8 Allegato 2
# Riferimento: stesso valore usato per pompe di calore
ORE_FUNZIONAMENTO = {
    "A": 600,
    "B": 850,
    "C": 1100,
    "D": 1400,
    "E": 1700,
    "F": 1800
}

# Coefficiente Ce (premiante emissioni) - Regole Applicative par. 9.9.5
# Il Ce premia generatori con basse emissioni rispetto ai limiti di legge
COEFFICIENTI_CE = {
    "riduzione_lte_20": 1.0,    # Riduzione emissioni ≤ 20%
    "riduzione_20_50": 1.2,     # Riduzione emissioni 20-50%
    "riduzione_gt_50": 1.5      # Riduzione emissioni > 50%
}

# Massimali di spesa unitaria (€/kW) - Allegato 2 DM 7/8/2025
MASSIMALI_SPESA = {
    "caldaia_lte_500": 350.0,       # €/kW per caldaie ≤ 500 kW
    "caldaia_gt_500": 250.0,        # €/kW per caldaie > 500 kW
    "stufa_pellet": 750.0,          # €/kW per stufe a pellet
    "termocamino_pellet": 750.0,    # €/kW per termocamini a pellet
    "termocamino_legna": 500.0,     # €/kW per termocamini a legna
    "stufa_legna": 500.0            # €/kW per stufe a legna
}

# Percentuali massime incentivo (Art. 11 DM 7/8/2025)
PERCENTUALI_MASSIME = {
    "privato": 0.65,   # 65%
    "impresa": 0.65,   # 65%
    "PA": 1.00,        # 100% per edifici pubblici
}

# Soglia erogazione rata unica (Art. 11, comma 4)
SOGLIA_RATA_UNICA = 15000.0

# Limiti potenza per tipologia
LIMITI_POTENZA = {
    "caldaia_lte_500": {"min": 5.0, "max": 500.0},
    "caldaia_gt_500": {"min": 500.0, "max": 2000.0},
    "stufa_pellet": {"min": 3.0, "max": 35.0},
    "termocamino_pellet": {"min": 3.0, "max": 35.0},
    "termocamino_legna": {"min": 3.0, "max": 35.0},
    "stufa_legna": {"min": 3.0, "max": 35.0}
}


# ============================================================================
# FUNZIONI DI SUPPORTO
# ============================================================================

def get_ore_funzionamento(zona_climatica: str) -> int:
    """
    Recupera le ore di funzionamento (hr) per la zona climatica.

    Riferimento: Tabella 8 - Allegato 2 DM 7/8/2025

    Args:
        zona_climatica: Lettera della zona (A-F)

    Returns:
        Valore hr in ore equivalenti
    """
    zona = zona_climatica.upper()
    if zona in ORE_FUNZIONAMENTO:
        return ORE_FUNZIONAMENTO[zona]
    raise ValueError(f"Zona climatica non valida: {zona_climatica}")


def get_ci(tipo_generatore: str, potenza_kw: float) -> float:
    """
    Recupera il coefficiente Ci per il tipo di generatore e potenza.

    Riferimento: Tabella 9 - Allegato 2 DM 7/8/2025

    Args:
        tipo_generatore: Tipologia di generatore biomassa
        potenza_kw: Potenza nominale in kW

    Returns:
        Valore Ci in €/kWht
    """
    if tipo_generatore not in COEFFICIENTI_CI:
        raise ValueError(f"Tipo generatore non valido: {tipo_generatore}")

    ci_data = COEFFICIENTI_CI[tipo_generatore]

    # Se ha fasce di potenza (caldaie ≤ 500 kW)
    if "fasce" in ci_data:
        for fascia in ci_data["fasce"]:
            p_min = fascia["potenza_min_kw"]
            p_max = fascia["potenza_max_kw"]
            if p_min <= potenza_kw <= p_max:
                return fascia["Ci"]
        # Se supera l'ultima fascia, usa l'ultimo valore
        return ci_data["fasce"][-1]["Ci"]

    # Se ha valore singolo
    return ci_data["Ci"]


def get_ce(riduzione_emissioni_pct: float) -> float:
    """
    Calcola il coefficiente Ce (premialità emissioni) in base alla
    riduzione percentuale delle emissioni rispetto ai limiti di legge.

    Riferimento: Regole Applicative CT 3.0, par. 9.9.5

    Args:
        riduzione_emissioni_pct: Percentuale di riduzione emissioni (0-100)

    Returns:
        Valore Ce (1.0, 1.2 o 1.5)
    """
    if riduzione_emissioni_pct <= 20:
        return COEFFICIENTI_CE["riduzione_lte_20"]
    elif riduzione_emissioni_pct <= 50:
        return COEFFICIENTI_CE["riduzione_20_50"]
    else:
        return COEFFICIENTI_CE["riduzione_gt_50"]


def get_massimale_spesa(tipo_generatore: str) -> float:
    """
    Recupera il massimale di spesa unitaria (€/kW) per la tipologia.

    Riferimento: Allegato 2 DM 7/8/2025

    Args:
        tipo_generatore: Tipologia di generatore biomassa

    Returns:
        Massimale in €/kW
    """
    return MASSIMALI_SPESA.get(tipo_generatore, 350.0)


def is_caldaia(tipo_generatore: str) -> bool:
    """
    Verifica se il generatore è una caldaia (usa formula lineare).

    Args:
        tipo_generatore: Tipologia di generatore

    Returns:
        True se caldaia, False se stufa/termocamino
    """
    return tipo_generatore.startswith("caldaia")


def is_stufa_termocamino(tipo_generatore: str) -> bool:
    """
    Verifica se il generatore è stufa o termocamino (usa formula logaritmica).

    Args:
        tipo_generatore: Tipologia di generatore

    Returns:
        True se stufa/termocamino, False altrimenti
    """
    return tipo_generatore in ["stufa_pellet", "termocamino_pellet",
                                "termocamino_legna", "stufa_legna"]


def valida_potenza(tipo_generatore: str, potenza_kw: float) -> tuple[bool, str]:
    """
    Valida la potenza del generatore rispetto ai limiti della tipologia.

    Args:
        tipo_generatore: Tipologia di generatore
        potenza_kw: Potenza nominale in kW

    Returns:
        Tupla (valido, messaggio)
    """
    if tipo_generatore not in LIMITI_POTENZA:
        return False, f"Tipo generatore non riconosciuto: {tipo_generatore}"

    limiti = LIMITI_POTENZA[tipo_generatore]
    p_min = limiti["min"]
    p_max = limiti["max"]

    if potenza_kw < p_min:
        return False, f"Potenza {potenza_kw} kW inferiore al minimo ammesso ({p_min} kW) per {TIPI_GENERATORE[tipo_generatore]}"
    if potenza_kw > p_max:
        return False, f"Potenza {potenza_kw} kW superiore al massimo ammesso ({p_max} kW) per {TIPI_GENERATORE[tipo_generatore]}"

    return True, "OK"


# ============================================================================
# FUNZIONE PRINCIPALE DI CALCOLO
# ============================================================================

def calculate_biomass_incentive(
    tipo_generatore: str,
    zona_climatica: str,
    potenza_nominale_kw: float,
    spesa_totale_sostenuta: float,
    riduzione_emissioni_pct: float = 0.0,
    tipo_soggetto: str = "privato",
    classe_emissione: str = "5_stelle",
    rendimento_pct: Optional[float] = None,
    tipo_combustibile_sostituito: str = "metano"  # biomassa, carbone, olio, gasolio, gpl, metano, altro
) -> RisultatoCalcoloBiomassa:
    """
    Calcola l'incentivo Conto Termico 3.0 per un generatore a biomassa (III.C).

    Implementa la pipeline completa di calcolo secondo il DM 7/8/2025:
    1. Validazione tecnica (classe emissioni, rendimento)
    2. Calcolo incentivo lordo con formula appropriata
    3. Applicazione massimali (spesa specifica + percentuale)
    4. Determinazione rateazione

    Formule:
        - Caldaie: I = Pn × hr × Ci × Ce
        - Stufe/Termocamini: I = 3.35 × ln(Pn) × hr × Ci × Ce

    Args:
        tipo_generatore: Tipologia ('caldaia_lte_500', 'caldaia_gt_500',
                         'stufa_pellet', 'termocamino_pellet',
                         'termocamino_legna', 'stufa_legna')
        zona_climatica: Zona climatica (A-F)
        potenza_nominale_kw: Potenza nominale Pn in kW
        spesa_totale_sostenuta: Spesa totale IVA inclusa in euro
        riduzione_emissioni_pct: Riduzione % emissioni vs limiti legge (0-100)
        tipo_soggetto: Tipo di soggetto ("privato", "impresa", "PA")
        classe_emissione: Classe ambientale ("5_stelle", "4_stelle", etc.)
        rendimento_pct: Rendimento del generatore in % (opzionale, per verifica)
        tipo_combustibile_sostituito: Tipo combustibile rimosso ("biomassa", "carbone",
                                      "olio", "gasolio", "gpl", "metano", "altro")

    Returns:
        RisultatoCalcoloBiomassa con tutti i dettagli del calcolo
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO INCENTIVO CT 3.0 - BIOMASSA (III.C)")
    logger.info("=" * 60)

    # Preparazione output di errore
    input_riepilogo: InputRiepilogoBiomassa = {
        "tipo_generatore": tipo_generatore,
        "zona_climatica": zona_climatica,
        "potenza_kw": potenza_nominale_kw,
        "spesa_sostenuta": spesa_totale_sostenuta,
        "tipo_soggetto": tipo_soggetto,
        "classe_emissione": classe_emissione,
        "riduzione_emissioni_pct": riduzione_emissioni_pct,
        "tipo_combustibile_sostituito": tipo_combustibile_sostituito
    }

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")

    # Verifica tipo generatore
    if tipo_generatore not in TIPI_GENERATORE:
        return {
            "status": "ERROR",
            "messaggio": f"Tipo generatore non valido: {tipo_generatore}. "
                        f"Valori ammessi: {list(TIPI_GENERATORE.keys())}",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    # Verifica zona climatica
    zona = zona_climatica.upper()
    if zona not in ["A", "B", "C", "D", "E", "F"]:
        return {
            "status": "ERROR",
            "messaggio": f"Zona climatica non valida: {zona_climatica}. "
                        "Valori ammessi: A, B, C, D, E, F",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    # Verifica potenza
    valido, msg = valida_potenza(tipo_generatore, potenza_nominale_kw)
    if not valido:
        return {
            "status": "ERROR",
            "messaggio": msg,
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    # Verifica classe emissione (DM 186/2017 + Regole Operative CT 3.0)
    # La classe 5 stelle è OBBLIGATORIA solo in questi casi:
    # 1. Sostituzione di biomassa/carbone/olio/gasolio
    # 2. Sostituzione di GPL o metano (solo per caldaie ≤500kW e stufe/termocamini)
    # 3. Nuova installazione per aziende agricole/forestali (non gestito qui)

    richiede_5_stelle = False
    motivo_5_stelle = ""

    # Caso 1: Sostituzione di biomassa, carbone, olio combustibile, gasolio
    if tipo_combustibile_sostituito.lower() in ["biomassa", "carbone", "olio", "gasolio"]:
        richiede_5_stelle = True
        motivo_5_stelle = f"sostituzione di impianto a {tipo_combustibile_sostituito}"

    # Caso 2: Sostituzione GPL/metano (solo caldaie e stufe, con requisiti emissioni aggiuntivi)
    # Secondo Regole Operative linee 4783-4793: solo caldaie ≤500kW e stufe/termocamini
    elif tipo_combustibile_sostituito.lower() in ["gpl", "metano"]:
        if tipo_generatore in ["caldaia_lte_500", "stufa_pellet", "termocamino_pellet",
                               "termocamino_legna", "stufa_legna"]:
            richiede_5_stelle = True
            motivo_5_stelle = f"sostituzione di GPL/metano (richiede anche emissioni PP ≤ 1 mg/Nm³)"

    # Verifica effettiva
    if richiede_5_stelle and classe_emissione != "5_stelle":
        return {
            "status": "ERROR",
            "messaggio": f"Classe emissione '{classe_emissione}' non ammessa per {motivo_5_stelle}. "
                        f"Requisito obbligatorio: classe 5 stelle (DM 186/2017, art. 29 D.Lgs 199/2021)",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    # Accetta anche classe 4 stelle per sostituzioni standard (altri combustibili fossili)
    if classe_emissione not in ["4_stelle", "5_stelle"]:
        return {
            "status": "ERROR",
            "messaggio": f"Classe emissione '{classe_emissione}' non valida. "
                        f"Valori ammessi: '4_stelle' o '5_stelle' (DM 186/2017)",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    logger.info(f"  Tipo generatore: {TIPI_GENERATORE[tipo_generatore]}")
    logger.info(f"  Zona climatica: {zona}")
    logger.info(f"  Potenza nominale: {potenza_nominale_kw} kW")
    logger.info(f"  Spesa sostenuta: {spesa_totale_sostenuta} EUR")
    logger.info(f"  Combustibile sostituito: {tipo_combustibile_sostituito}")
    logger.info(f"  Classe emissione: {classe_emissione}")
    if richiede_5_stelle:
        logger.info(f"  ⚠ Classe 5 stelle obbligatoria per {motivo_5_stelle}")
    else:
        logger.info(f"  ✓ Classe {classe_emissione} ammessa per questo tipo di sostituzione")
    logger.info(f"  Riduzione emissioni: {riduzione_emissioni_pct}%")
    logger.info(f"  Tipo soggetto: {tipo_soggetto}")

    # -------------------------------------------------------------------------
    # STEP 2: Verifica requisiti tecnici
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Verifica requisiti tecnici")

    # Verifica rendimento minimo (se fornito)
    if rendimento_pct is not None:
        if is_caldaia(tipo_generatore):
            # Caldaie: rendimento ≥ 87 + log(Pn)%
            rendimento_min = 87 + math.log10(potenza_nominale_kw)
            if rendimento_pct < rendimento_min:
                return {
                    "status": "ERROR",
                    "messaggio": f"Rendimento {rendimento_pct}% inferiore al minimo "
                                f"richiesto ({rendimento_min:.1f}%) per caldaie a biomassa",
                    "input_riepilogo": input_riepilogo,
                    "calcoli_intermedi": None,
                    "massimali_applicati": None,
                    "incentivo_totale": None,
                    "erogazione": None
                }
            logger.info(f"  Rendimento minimo caldaia: {rendimento_min:.1f}%")
            logger.info(f"  Rendimento dichiarato: {rendimento_pct}%")
            logger.info("  OK: Requisito rendimento soddisfatto")
        else:
            # Stufe/Termocamini: rendimento ≥ 85%
            rendimento_min = 85.0
            if rendimento_pct < rendimento_min:
                return {
                    "status": "ERROR",
                    "messaggio": f"Rendimento {rendimento_pct}% inferiore al minimo "
                                f"richiesto ({rendimento_min}%) per stufe/termocamini",
                    "input_riepilogo": input_riepilogo,
                    "calcoli_intermedi": None,
                    "massimali_applicati": None,
                    "incentivo_totale": None,
                    "erogazione": None
                }
            logger.info(f"  Rendimento minimo stufa/termocamino: {rendimento_min}%")
            logger.info(f"  Rendimento dichiarato: {rendimento_pct}%")
            logger.info("  OK: Requisito rendimento soddisfatto")
    else:
        logger.info("  Rendimento non fornito, si assume conforme ai requisiti")

    logger.info("  OK: Requisiti tecnici validati")

    # -------------------------------------------------------------------------
    # STEP 3: Recupero coefficienti
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Recupero coefficienti")

    hr = get_ore_funzionamento(zona)
    ci = get_ci(tipo_generatore, potenza_nominale_kw)
    ce = get_ce(riduzione_emissioni_pct)

    logger.info(f"  hr (zona {zona}): {hr} ore equivalenti")
    logger.info(f"  Ci (coefficiente valorizzazione): {ci} EUR/kWht")
    logger.info(f"  Ce (premialità emissioni): {ce}")

    # -------------------------------------------------------------------------
    # STEP 4: Calcolo incentivo annuo
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Calcolo incentivo annuo (Ia)")

    if is_caldaia(tipo_generatore):
        # Formula caldaie: I = Pn × hr × Ci × Ce
        i_annuo = potenza_nominale_kw * hr * ci * ce
        formula = f"Ia = {potenza_nominale_kw} kW × {hr} h × {ci} €/kWht × {ce}"
        logger.info(f"  Formula (caldaia): Ia = Pn × hr × Ci × Ce")
    else:
        # Formula stufe/termocamini: I = 3.35 × ln(Pn) × hr × Ci × Ce
        ln_pn = math.log(potenza_nominale_kw)
        i_annuo = 3.35 * ln_pn * hr * ci * ce
        formula = f"Ia = 3.35 × ln({potenza_nominale_kw}) × {hr} h × {ci} €/kWht × {ce}"
        logger.info(f"  Formula (stufa/termocamino): Ia = 3.35 × ln(Pn) × hr × Ci × Ce")
        logger.info(f"  ln({potenza_nominale_kw}) = {ln_pn:.4f}")

    logger.info(f"  {formula}")
    logger.info(f"  Ia = {i_annuo:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 5: Determinazione durata (n)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Determinazione durata incentivo (n)")

    # Art. 11, comma 3: 2 annualità per P ≤ 35 kW, 5 annualità per P > 35 kW
    n = 2 if potenza_nominale_kw <= 35 else 5
    logger.info(f"  Potenza {potenza_nominale_kw} kW {'<=' if potenza_nominale_kw <= 35 else '>'} 35 kW")
    logger.info(f"  n = {n} annualità")

    # -------------------------------------------------------------------------
    # STEP 6: Calcolo incentivo totale lordo
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 6] Calcolo incentivo totale lordo")

    i_tot_lordo = i_annuo * n
    logger.info(f"  I_tot_lordo = {i_annuo:.2f} EUR × {n} = {i_tot_lordo:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 7: Applicazione massimali
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 7] Applicazione massimali")

    # CAP A: Spesa specifica ammissibile (massimale €/kW)
    massimale_unitario = get_massimale_spesa(tipo_generatore)
    spesa_max_ammissibile = massimale_unitario * potenza_nominale_kw
    spesa_ammissibile = min(spesa_totale_sostenuta, spesa_max_ammissibile)

    logger.info(f"  [CAP A] Massimale spesa unitaria: {massimale_unitario} EUR/kW")
    logger.info(f"  Spesa max ammissibile: {massimale_unitario} × {potenza_nominale_kw} = {spesa_max_ammissibile:.2f} EUR")
    logger.info(f"  Spesa sostenuta: {spesa_totale_sostenuta:.2f} EUR")
    logger.info(f"  Spesa ammissibile: min({spesa_totale_sostenuta:.2f}, {spesa_max_ammissibile:.2f}) = {spesa_ammissibile:.2f} EUR")

    # CAP B: Percentuale massima
    percentuale = PERCENTUALI_MASSIME.get(tipo_soggetto, 0.65)
    i_max_percentuale = spesa_ammissibile * percentuale

    logger.info(f"  [CAP B] Percentuale massima ({tipo_soggetto}): {percentuale*100:.0f}%")
    logger.info(f"  I_max da percentuale: {spesa_ammissibile:.2f} × {percentuale} = {i_max_percentuale:.2f} EUR")

    # Incentivo finale: minimo tra lordo e massimale
    i_tot = min(i_tot_lordo, i_max_percentuale)
    taglio_applicato = i_tot < i_tot_lordo
    importo_tagliato = i_tot_lordo - i_tot if taglio_applicato else 0.0

    logger.info(f"  Incentivo lordo: {i_tot_lordo:.2f} EUR")
    logger.info(f"  Incentivo max da massimali: {i_max_percentuale:.2f} EUR")
    logger.info(f"  INCENTIVO FINALE: min({i_tot_lordo:.2f}, {i_max_percentuale:.2f}) = {i_tot:.2f} EUR")

    if taglio_applicato:
        logger.warning(f"  ATTENZIONE: Applicato taglio massimale di {importo_tagliato:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 8: Determinazione rateazione
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 8] Determinazione rateazione")

    if i_tot <= SOGLIA_RATA_UNICA or tipo_soggetto == "PA":
        modalita = "rata_unica"
        rate = [round(i_tot, 2)]
        numero_rate = 1
        if tipo_soggetto == "PA":
            logger.info("  PA: erogazione in rata unica (indipendentemente dall'importo)")
        else:
            logger.info(f"  Incentivo {i_tot:.2f} EUR <= {SOGLIA_RATA_UNICA} EUR -> Rata unica")
    else:
        modalita = "rate_annuali"
        rata_annua = i_tot / n
        rate = [round(rata_annua, 2)] * n
        numero_rate = n
        logger.info(f"  Incentivo {i_tot:.2f} EUR > {SOGLIA_RATA_UNICA} EUR -> {n} rate annuali")
        logger.info(f"  Rata annua: {i_tot:.2f} / {n} = {rata_annua:.2f} EUR")

    logger.info(f"  Modalità: {modalita}")
    logger.info(f"  Rate: {rate}")

    # -------------------------------------------------------------------------
    # OUTPUT FINALE
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"INCENTIVO TOTALE: {i_tot:.2f} EUR")
    logger.info("=" * 60)

    calcoli_intermedi: CalcoliIntermediBiomassa = {
        "hr": hr,
        "Ci": ci,
        "Ce": ce,
        "I_annuo": round(i_annuo, 2),
        "n": n,
        "I_tot_lordo": round(i_tot_lordo, 2)
    }

    massimali_applicati: MassimaliApplicatiBiomassa = {
        "spesa_ammissibile": round(spesa_ammissibile, 2),
        "massimale_unitario_applicato": massimale_unitario,
        "percentuale_applicata": percentuale,
        "I_max_da_massimali": round(i_max_percentuale, 2),
        "taglio_applicato": taglio_applicato,
        "importo_tagliato": round(importo_tagliato, 2)
    }

    erogazione: ErogazioneBiomassa = {
        "modalita": modalita,
        "rate": rate,
        "numero_rate": numero_rate
    }

    return {
        "status": "OK",
        "messaggio": "Calcolo completato con successo",
        "input_riepilogo": input_riepilogo,
        "calcoli_intermedi": calcoli_intermedi,
        "massimali_applicati": massimali_applicati,
        "incentivo_totale": round(i_tot, 2),
        "erogazione": erogazione
    }


# ============================================================================
# FUNZIONI AUSILIARIE PER CONFRONTO INCENTIVI
# ============================================================================

def calcola_ecobonus_biomassa(
    spesa_sostenuta: float,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale"
) -> dict:
    """
    Calcola la detrazione Ecobonus per generatori a biomassa.

    L'Ecobonus per biomassa prevede una detrazione del 50% (o 36% dal 2026
    per abitazioni non principali) con limite di 30.000€.

    Args:
        spesa_sostenuta: Spesa totale in euro
        anno_spesa: Anno di sostenimento spesa
        tipo_abitazione: "abitazione_principale" o "altre_abitazioni"

    Returns:
        Dizionario con dettagli detrazione
    """
    # Aliquote Ecobonus biomassa
    if anno_spesa <= 2025:
        aliquota = 0.50  # 50%
    else:
        if tipo_abitazione == "abitazione_principale":
            aliquota = 0.50  # 50%
        else:
            aliquota = 0.36  # 36%

    limite_detrazione = 30000.0
    detrazione_lorda = spesa_sostenuta * aliquota
    detrazione_effettiva = min(detrazione_lorda, limite_detrazione)
    anni_recupero = 10
    rata_annuale = detrazione_effettiva / anni_recupero

    return {
        "aliquota": aliquota,
        "limite_detrazione": limite_detrazione,
        "detrazione_lorda": round(detrazione_lorda, 2),
        "detrazione_effettiva": round(detrazione_effettiva, 2),
        "anni_recupero": anni_recupero,
        "rata_annuale": round(rata_annuale, 2),
        "spesa_sostenuta": spesa_sostenuta
    }


def confronta_incentivi_biomassa(
    risultato_ct: RisultatoCalcoloBiomassa,
    spesa_sostenuta: float,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale",
    tasso_sconto: float = 0.03
) -> dict:
    """
    Confronta Conto Termico vs Ecobonus per generatori a biomassa.

    Args:
        risultato_ct: Risultato del calcolo CT 3.0
        spesa_sostenuta: Spesa sostenuta
        anno_spesa: Anno spesa
        tipo_abitazione: Tipo abitazione per Ecobonus
        tasso_sconto: Tasso per calcolo VAN

    Returns:
        Confronto dettagliato tra i due incentivi
    """
    # Calcolo Ecobonus
    ecobonus = calcola_ecobonus_biomassa(spesa_sostenuta, anno_spesa, tipo_abitazione)

    # Dati CT
    ct_totale = risultato_ct.get("incentivo_totale", 0) or 0
    ct_rate = risultato_ct.get("erogazione", {}).get("rate", []) if risultato_ct.get("erogazione") else []

    # Calcolo VAN Conto Termico
    van_ct = 0.0
    for i, rata in enumerate(ct_rate):
        van_ct += rata / ((1 + tasso_sconto) ** i)

    # Calcolo VAN Ecobonus
    van_eco = 0.0
    for i in range(ecobonus["anni_recupero"]):
        van_eco += ecobonus["rata_annuale"] / ((1 + tasso_sconto) ** i)

    # Confronto
    convenienza = "CT" if van_ct > van_eco else "ECOBONUS"
    differenza = abs(van_ct - van_eco)

    return {
        "conto_termico": {
            "incentivo_totale": ct_totale,
            "numero_rate": len(ct_rate),
            "van": round(van_ct, 2)
        },
        "ecobonus": {
            "detrazione_totale": ecobonus["detrazione_effettiva"],
            "aliquota": f"{ecobonus['aliquota']*100:.0f}%",
            "rata_annuale": ecobonus["rata_annuale"],
            "anni_recupero": ecobonus["anni_recupero"],
            "van": round(van_eco, 2)
        },
        "confronto": {
            "convenienza": convenienza,
            "differenza_van": round(differenza, 2),
            "nota": "Il Conto Termico è erogazione diretta, "
                   "l'Ecobonus richiede capienza fiscale"
        }
    }


# ============================================================================
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    import json

    print("\n" + "=" * 70)
    print("ESEMPIO 1: Caldaia a biomassa 25 kW - Zona E")
    print("=" * 70)

    risultato1 = calculate_biomass_incentive(
        tipo_generatore="caldaia_lte_500",
        zona_climatica="E",
        potenza_nominale_kw=25.0,
        spesa_totale_sostenuta=8000.0,
        riduzione_emissioni_pct=30.0,  # Ce = 1.2
        tipo_soggetto="privato",
        classe_emissione="5_stelle",
        rendimento_pct=92.0
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato1, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("ESEMPIO 2: Stufa a pellet 8 kW - Zona D")
    print("=" * 70)

    risultato2 = calculate_biomass_incentive(
        tipo_generatore="stufa_pellet",
        zona_climatica="D",
        potenza_nominale_kw=8.0,
        spesa_totale_sostenuta=3500.0,
        riduzione_emissioni_pct=55.0,  # Ce = 1.5
        tipo_soggetto="privato",
        classe_emissione="5_stelle",
        rendimento_pct=90.0
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato2, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("CONFRONTO CT vs ECOBONUS")
    print("=" * 70)

    confronto = confronta_incentivi_biomassa(
        risultato_ct=risultato2,
        spesa_sostenuta=3500.0,
        anno_spesa=2025
    )

    print("\nCONFRONTO:")
    print(json.dumps(confronto, indent=2, ensure_ascii=False))
