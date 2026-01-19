"""
Modulo di calcolo incentivi Conto Termico 3.0 per Pompe di Calore.

Riferimento normativo: DM 7 agosto 2025 e Regole Applicative GSE.
Questo modulo implementa il calcolo dell'incentivo secondo la formula:
    I_tot = Ei × Ci × n (con applicazione massimali)

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Optional, TypedDict, Literal, Union

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class InputRiepilogo(TypedDict):
    tipo_intervento: str
    zona_climatica: str
    potenza_kw: float
    scop_dichiarato: float
    spesa_sostenuta: float
    tipo_soggetto: str


class CalcoliIntermedi(TypedDict):
    Quf: float
    Qu: float
    kp: float
    Ei: float
    Ci: float
    Ia: float
    n: int
    I_tot_lordo: float


class MassimaliApplicati(TypedDict):
    spesa_ammissibile: float
    massimale_unitario_applicato: float
    percentuale_applicata: float
    I_max_da_massimali: float
    taglio_applicato: bool
    importo_tagliato: float


class Erogazione(TypedDict):
    modalita: Literal["rata_unica", "rate_annuali"]
    rate: list[float]
    numero_rate: int


class RisultatoCalcolo(TypedDict):
    status: Literal["OK", "ERROR"]
    messaggio: str
    input_riepilogo: InputRiepilogo
    calcoli_intermedi: Optional[CalcoliIntermedi]
    massimali_applicati: Optional[MassimaliApplicati]
    incentivo_totale: Optional[float]
    erogazione: Optional[Erogazione]


# ============================================================================
# COSTANTI E FALLBACK
# ============================================================================

# Coefficienti Quf per zona climatica (Tabella 8 - Allegato 2 DM 7/8/2025)
QUF_FALLBACK: dict[str, int] = {
    "A": 600,
    "B": 850,
    "C": 1100,
    "D": 1400,
    "E": 1700,
    "F": 1800
}

# Massimali di spesa unitaria per tecnologia (Allegato 2 DM 7/8/2025)
MASSIMALI_SPESA: dict[str, float] = {
    "aria_aria": 1600.0,           # €/kW
    "split_multisplit": 1600.0,
    "fixed_double_duct": 1600.0,
    "vrf_vrv": 1600.0,
    "rooftop": 1600.0,
    "aria_acqua": 2000.0,          # €/kW
    "acqua_aria": 2500.0,          # €/kW
    "acqua_acqua": 2500.0,         # €/kW
    "geotermiche_salamoia_aria": 2500.0,   # €/kW
    "geotermiche_salamoia_acqua": 2500.0,  # €/kW
}

# SCOP/COP minimi di fallback (Tabelle 3-4 Allegato 1 DM 7/8/2025)
SCOP_MINIMI_FALLBACK: dict[str, dict] = {
    "aria_aria": {
        "split_multisplit": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42},
        "fixed_double_duct": {"GWP_gt_150": 2.60, "GWP_lte_150": 2.34},  # COP, non SCOP
        "vrf_vrv": {"standard": 3.50},
        "rooftop": {"standard": 3.20},
    },
    "aria_acqua": {"standard": 2.825, "bassa_temperatura": 3.20},
    "acqua_aria": {"standard": 3.625},
    "acqua_acqua": {"standard": 2.95, "bassa_temperatura": 3.325},
    "geotermiche_salamoia_aria": {
        "lte_12kw": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42},
        "gt_12kw": {"standard": 3.625}
    },
    "geotermiche_salamoia_acqua": {"standard": 2.825, "bassa_temperatura": 3.20},
}

# Percentuali massime incentivo (Art. 11 DM 7/8/2025)
PERCENTUALI_MASSIME: dict[str, float] = {
    "privato": 0.65,   # 65%
    "impresa": 0.65,   # 65%
    "PA": 1.00,        # 100% per edifici pubblici (Art. 11, comma 2)
}

# Soglia erogazione rata unica (Art. 11, comma 4 DM 7/8/2025)
SOGLIA_RATA_UNICA: float = 15000.0


# ============================================================================
# FUNZIONI DI SUPPORTO
# ============================================================================

def load_json_data(file_path: str) -> dict:
    """
    Carica i dati dal file JSON.

    Args:
        file_path: Percorso al file JSON

    Returns:
        Dizionario con i dati caricati

    Raises:
        FileNotFoundError: Se il file non esiste
        json.JSONDecodeError: Se il JSON non è valido
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File JSON non trovato: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_quf(zona_climatica: str, json_data: Optional[dict] = None) -> int:
    """
    Recupera il coefficiente Quf (ore equivalenti) per la zona climatica.

    Riferimento: Tabella 8 - Allegato 2 DM 7/8/2025

    Args:
        zona_climatica: Lettera della zona (A-F)
        json_data: Dati dal file JSON (opzionale)

    Returns:
        Valore Quf in ore equivalenti
    """
    zona = zona_climatica.upper()

    # Prova a recuperare dal JSON
    if json_data and "zone_climatiche_Quf" in json_data:
        quf = json_data["zone_climatiche_Quf"].get(zona)
        if quf is not None:
            return int(quf)

    # Fallback ai valori di default
    if zona in QUF_FALLBACK:
        return QUF_FALLBACK[zona]

    raise ValueError(f"Zona climatica non valida: {zona_climatica}")


def get_scop_minimo(
    tipo_intervento: str,
    gwp: str = ">150",
    bassa_temperatura: bool = False,
    potenza_kw: float = 10.0,
    json_data: Optional[dict] = None
) -> float:
    """
    Recupera il valore SCOP/COP minimo Ecodesign per il tipo di intervento.

    Riferimento: Tabelle 3-4-5 Allegato 1 DM 7/8/2025

    Args:
        tipo_intervento: Tipologia di pompa di calore
        gwp: GWP del refrigerante (">150" o "<=150")
        bassa_temperatura: True se pompa di calore a bassa temperatura
        potenza_kw: Potenza nominale in kW
        json_data: Dati dal file JSON (opzionale)

    Returns:
        Valore SCOP/COP minimo
    """
    # Prova a recuperare dal JSON
    if json_data and "requisiti_minimi_ecodesign" in json_data:
        req = json_data["requisiti_minimi_ecodesign"].get("pompe_calore_elettriche", {})

        # Gestione tipologie aria/aria
        if tipo_intervento.startswith("aria_aria") or tipo_intervento in ["split_multisplit", "fixed_double_duct", "vrf_vrv", "rooftop"]:
            aria_aria = req.get("aria_aria", {})

            if tipo_intervento in ["split_multisplit", "aria_aria_split"]:
                sub = aria_aria.get("split_multisplit", {})
                key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
                if key in sub:
                    return sub[key].get("SCOP_min", 3.80)

            elif tipo_intervento == "fixed_double_duct":
                sub = aria_aria.get("fixed_double_duct", {})
                key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
                if key in sub:
                    return sub[key].get("COP_min", 2.60)

            elif tipo_intervento == "vrf_vrv":
                sub = aria_aria.get("vrf_vrv", {})
                return sub.get("SCOP_min", 3.50)

            elif tipo_intervento == "rooftop":
                sub = aria_aria.get("rooftop", {})
                return sub.get("SCOP_min", 3.20)

        # Gestione aria/acqua
        elif tipo_intervento == "aria_acqua":
            sub = req.get("aria_acqua", {})
            if bassa_temperatura and "bassa_temperatura" in sub:
                return sub["bassa_temperatura"].get("SCOP_min", 3.20)
            elif "standard" in sub:
                return sub["standard"].get("SCOP_min", 2.825)

        # Gestione acqua/aria
        elif tipo_intervento == "acqua_aria":
            sub = req.get("acqua_aria", {})
            return sub.get("SCOP_min", 3.625)

        # Gestione acqua/acqua
        elif tipo_intervento == "acqua_acqua":
            sub = req.get("acqua_acqua", {})
            if bassa_temperatura and "bassa_temperatura" in sub:
                return sub["bassa_temperatura"].get("SCOP_min", 3.325)
            elif "standard" in sub:
                return sub["standard"].get("SCOP_min", 2.95)

        # Gestione geotermiche
        elif tipo_intervento == "geotermiche_salamoia_aria":
            sub = req.get("geotermiche_salamoia_aria", {})
            if potenza_kw <= 12:
                sub_potenza = sub.get("lte_12kw", {})
                key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
                if key in sub_potenza:
                    return sub_potenza[key].get("SCOP_min", 3.80)
            else:
                sub_potenza = sub.get("gt_12kw", {})
                return sub_potenza.get("SCOP_min", 3.625)

        elif tipo_intervento == "geotermiche_salamoia_acqua":
            sub = req.get("geotermiche_salamoia_acqua", {})
            if bassa_temperatura and "bassa_temperatura" in sub:
                return sub["bassa_temperatura"].get("SCOP_min", 3.20)
            elif "standard" in sub:
                return sub["standard"].get("SCOP_min", 2.825)

    # Fallback ai valori di default
    logger.warning(f"SCOP minimo non trovato nel JSON per {tipo_intervento}, uso fallback")

    if tipo_intervento in ["aria_acqua"]:
        return 3.20 if bassa_temperatura else 2.825
    elif tipo_intervento in ["acqua_acqua"]:
        return 3.325 if bassa_temperatura else 2.95
    elif tipo_intervento in ["split_multisplit", "aria_aria_split"]:
        return 3.80 if gwp == ">150" else 3.42
    elif tipo_intervento == "fixed_double_duct":
        return 2.60 if gwp == ">150" else 2.34
    elif tipo_intervento == "vrf_vrv":
        return 3.50
    elif tipo_intervento == "rooftop":
        return 3.20
    elif tipo_intervento == "acqua_aria":
        return 3.625
    elif tipo_intervento.startswith("geotermiche"):
        return 3.625 if potenza_kw > 12 else 3.80

    return 3.80  # Default conservativo


def get_ci(
    tipo_intervento: str,
    potenza_kw: float,
    json_data: Optional[dict] = None
) -> float:
    """
    Recupera il coefficiente Ci (valorizzazione energia termica) per la tecnologia.

    Riferimento: Tabella 9 - Allegato 2 DM 7/8/2025

    Args:
        tipo_intervento: Tipologia di pompa di calore
        potenza_kw: Potenza nominale in kW
        json_data: Dati dal file JSON (opzionale)

    Returns:
        Valore Ci in €/kWht
    """
    # Prova a recuperare dal JSON
    if json_data and "coefficienti_Ci" in json_data:
        ci_data = json_data["coefficienti_Ci"]

        # Mapping tipo intervento -> chiave JSON
        mapping = {
            "split_multisplit": ("aria_aria", "split_multisplit"),
            "aria_aria_split": ("aria_aria", "split_multisplit"),
            "fixed_double_duct": ("aria_aria", "fixed_double_duct"),
            "vrf_vrv": ("aria_aria", "vrf_vrv"),
            "rooftop": ("aria_aria", "rooftop"),
            "aria_acqua": ("aria_acqua", None),
            "acqua_aria": ("acqua_aria", None),
            "acqua_acqua": ("acqua_acqua", None),
            "geotermiche_salamoia_aria": ("geotermiche_salamoia_aria", None),
            "geotermiche_salamoia_acqua": ("geotermiche_salamoia_acqua", None),
        }

        if tipo_intervento in mapping:
            key1, key2 = mapping[tipo_intervento]

            if key2:  # Sottocategoria (aria/aria)
                sub = ci_data.get(key1, {}).get(key2, {})
            else:
                sub = ci_data.get(key1, {})

            # Se ha fasce di potenza
            if "fasce" in sub:
                for fascia in sub["fasce"]:
                    p_min = fascia.get("potenza_min_kw", 0)
                    p_max = fascia.get("potenza_max_kw", float('inf'))
                    if p_max is None:
                        p_max = float('inf')

                    if p_min <= potenza_kw <= p_max or (p_min < potenza_kw and p_max == float('inf')):
                        return fascia["Ci"]

            # Se ha valore singolo
            elif "Ci" in sub:
                return sub["Ci"]

    # Fallback basato su tipo e potenza
    logger.warning(f"Ci non trovato nel JSON per {tipo_intervento}, uso fallback")

    # Valori di fallback (Tabella 9 - Allegato 2)
    if tipo_intervento in ["split_multisplit", "aria_aria_split"]:
        return 0.070
    elif tipo_intervento == "fixed_double_duct":
        return 0.200
    elif tipo_intervento in ["vrf_vrv", "rooftop"]:
        return 0.15 if potenza_kw <= 35 else 0.055
    elif tipo_intervento == "aria_acqua":
        return 0.15 if potenza_kw <= 35 else 0.06
    elif tipo_intervento in ["acqua_aria", "acqua_acqua", "geotermiche_salamoia_aria", "geotermiche_salamoia_acqua"]:
        return 0.160 if potenza_kw <= 35 else 0.06

    return 0.15  # Default


def get_massimale_spesa(tipo_intervento: str) -> float:
    """
    Recupera il massimale di spesa unitaria (€/kW) per la tecnologia.

    Riferimento: Allegato 2 DM 7/8/2025

    Args:
        tipo_intervento: Tipologia di pompa di calore

    Returns:
        Massimale in €/kW
    """
    # Normalizza tipo intervento
    tipo_lower = tipo_intervento.lower()

    # Aria/Aria -> 1600 €/kW
    if "aria_aria" in tipo_lower or tipo_lower in ["split_multisplit", "fixed_double_duct", "vrf_vrv", "rooftop"]:
        return 1600.0

    # Aria/Acqua -> 2000 €/kW
    if tipo_lower == "aria_acqua":
        return 2000.0

    # Altre (Geotermia, Acqua/Acqua, Acqua/Aria) -> 2500 €/kW
    return 2500.0


# ============================================================================
# FUNZIONE PRINCIPALE DI CALCOLO
# ============================================================================

def calculate_heat_pump_incentive(
    tipo_intervento: str,
    zona_climatica: str,
    potenza_nominale_kw: float,
    scop_dichiarato: float,
    spesa_totale_sostenuta: float,
    gwp_refrigerante: str = ">150",
    tipo_soggetto: str = "privato",
    bassa_temperatura: bool = False,
    eta_s: Optional[float] = None,
    json_path: Optional[str] = None
) -> RisultatoCalcolo:
    """
    Calcola l'incentivo Conto Termico 3.0 per una pompa di calore.

    Implementa la pipeline completa di calcolo secondo il DM 7/8/2025:
    1. Validazione tecnica (SCOP minimo Ecodesign)
    2. Calcolo energia termica incentivata (Ei)
    3. Calcolo incentivo lordo
    4. Applicazione massimali (spesa specifica + percentuale)
    5. Determinazione rateazione

    Args:
        tipo_intervento: Tipologia PdC ('aria_acqua', 'split_multisplit', 'geotermiche_salamoia_acqua', ecc.)
        zona_climatica: Zona climatica (A-F)
        potenza_nominale_kw: Potenza nominale P_rated in kW
        scop_dichiarato: SCOP dichiarato dal costruttore (o COP per fixed_double_duct)
        spesa_totale_sostenuta: Spesa totale IVA inclusa in euro
        gwp_refrigerante: GWP del refrigerante (">150" o "<=150")
        tipo_soggetto: Tipo di soggetto ("privato", "impresa", "PA")
        bassa_temperatura: True se PdC a bassa temperatura
        eta_s: Efficienza stagionale in % (es. 150 per 150%). Se fornito, viene usato
               per il calcolo di kp al posto dello SCOP. RACCOMANDATO per maggiore precisione.
        json_path: Percorso al file JSON con i coefficienti (opzionale)

    Returns:
        RisultatoCalcolo con tutti i dettagli del calcolo

    Note:
        Il coefficiente di premialità kp viene calcolato come:
        - kp = eta_s / eta_s_min_ecodesign (se eta_s è fornito)
        - kp = SCOP / SCOP_min_ecodesign (altrimenti, meno preciso)

        Per risultati più accurati, fornire eta_s dalla scheda tecnica del prodotto.
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO INCENTIVO CONTO TERMICO 3.0")
    logger.info("=" * 60)

    # Preparazione output di errore
    input_riepilogo: InputRiepilogo = {
        "tipo_intervento": tipo_intervento,
        "zona_climatica": zona_climatica,
        "potenza_kw": potenza_nominale_kw,
        "scop_dichiarato": scop_dichiarato,
        "spesa_sostenuta": spesa_totale_sostenuta,
        "tipo_soggetto": tipo_soggetto
    }

    # -------------------------------------------------------------------------
    # STEP 0: Caricamento dati JSON
    # -------------------------------------------------------------------------
    json_data: Optional[dict] = None
    if json_path:
        try:
            json_data = load_json_data(json_path)
            logger.info(f"Dati JSON caricati da: {json_path}")
        except FileNotFoundError:
            logger.warning(f"File JSON non trovato: {json_path}, uso valori di fallback")
        except json.JSONDecodeError as e:
            logger.warning(f"Errore parsing JSON: {e}, uso valori di fallback")
    else:
        # Prova percorso di default
        default_path = Path(__file__).parent.parent / "data" / "pompe_calore_ci.json"
        if default_path.exists():
            try:
                json_data = load_json_data(str(default_path))
                logger.info(f"Dati JSON caricati da percorso default: {default_path}")
            except Exception as e:
                logger.warning(f"Errore caricamento JSON default: {e}")

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")

    zona = zona_climatica.upper()
    if zona not in ["A", "B", "C", "D", "E", "F"]:
        return {
            "status": "ERROR",
            "messaggio": f"Zona climatica non valida: {zona_climatica}. Valori ammessi: A, B, C, D, E, F",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    if potenza_nominale_kw <= 0:
        return {
            "status": "ERROR",
            "messaggio": "Potenza nominale deve essere > 0",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    if scop_dichiarato <= 1:
        return {
            "status": "ERROR",
            "messaggio": "SCOP/COP deve essere > 1",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    logger.info(f"  Tipo intervento: {tipo_intervento}")
    logger.info(f"  Zona climatica: {zona}")
    logger.info(f"  Potenza nominale: {potenza_nominale_kw} kW")
    logger.info(f"  SCOP dichiarato: {scop_dichiarato}")
    logger.info(f"  Spesa sostenuta: {spesa_totale_sostenuta} EUR")
    logger.info(f"  GWP refrigerante: {gwp_refrigerante}")
    logger.info(f"  Tipo soggetto: {tipo_soggetto}")

    # -------------------------------------------------------------------------
    # STEP 2: Validazione tecnica - Verifica SCOP minimo Ecodesign
    # Riferimento: Tabelle 3-4-5 Allegato 1 DM 7/8/2025
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Validazione tecnica (requisiti Ecodesign)")

    scop_minimo = get_scop_minimo(
        tipo_intervento=tipo_intervento,
        gwp=gwp_refrigerante,
        bassa_temperatura=bassa_temperatura,
        potenza_kw=potenza_nominale_kw,
        json_data=json_data
    )

    logger.info(f"  SCOP/COP minimo Ecodesign: {scop_minimo}")
    logger.info(f"  SCOP/COP dichiarato: {scop_dichiarato}")

    if scop_dichiarato < scop_minimo:
        msg = (f"Intervento non incentivabile: SCOP/COP inferiore ai minimi Ecodesign "
               f"(richiesto: {scop_minimo}, dichiarato: {scop_dichiarato})")
        logger.error(f"  FAIL: {msg}")
        return {
            "status": "ERROR",
            "messaggio": msg,
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "massimali_applicati": None,
            "incentivo_totale": None,
            "erogazione": None
        }

    logger.info("  OK: Requisiti Ecodesign soddisfatti")

    # -------------------------------------------------------------------------
    # STEP 3: Calcolo coefficiente di premialità (kp)
    # Riferimento: Regole Applicative CT 3.0, par. 9.9.3
    # Formula CORRETTA: kp = eta_s / eta_s_min_ecodesign
    # Nota: La normativa richiede l'uso dell'efficienza stagionale (eta_s),
    #       non dello SCOP direttamente.
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Calcolo coefficiente di premialità (kp)")

    # Mappa eta_s_min per tipologia (valori da Tabelle 3-4-5 Allegato 1)
    ETA_S_MIN = {
        "split_multisplit": {"GWP_gt_150": 149, "GWP_lte_150": 134},
        "fixed_double_duct": {"GWP_gt_150": 149, "GWP_lte_150": 134},  # Usa eta_s anche per questi
        "vrf_vrv": 137,
        "rooftop": 125,
        "aria_acqua": {"standard": 110, "bassa_temperatura": 125},
        "acqua_aria": 137,
        "acqua_acqua": {"standard": 110, "bassa_temperatura": 125},
        "geotermiche_salamoia_aria": {"lte_12kw": {"GWP_gt_150": 149, "GWP_lte_150": 134}, "gt_12kw": 137},
        "geotermiche_salamoia_acqua": {"standard": 110, "bassa_temperatura": 125},
    }

    # Determina eta_s_min in base alla tipologia
    eta_s_min = 110  # Default
    if tipo_intervento in ["split_multisplit", "fixed_double_duct"]:
        key = "GWP_gt_150" if gwp_refrigerante == ">150" else "GWP_lte_150"
        eta_s_min = ETA_S_MIN.get(tipo_intervento, {}).get(key, 149)
    elif tipo_intervento in ["vrf_vrv", "rooftop", "acqua_aria"]:
        eta_s_min = ETA_S_MIN.get(tipo_intervento, 137)
    elif tipo_intervento in ["aria_acqua", "acqua_acqua", "geotermiche_salamoia_acqua"]:
        key = "bassa_temperatura" if bassa_temperatura else "standard"
        eta_s_min = ETA_S_MIN.get(tipo_intervento, {}).get(key, 110)
    elif tipo_intervento == "geotermiche_salamoia_aria":
        if potenza_nominale_kw <= 12:
            key = "GWP_gt_150" if gwp_refrigerante == ">150" else "GWP_lte_150"
            eta_s_min = ETA_S_MIN["geotermiche_salamoia_aria"]["lte_12kw"].get(key, 149)
        else:
            eta_s_min = ETA_S_MIN["geotermiche_salamoia_aria"]["gt_12kw"]

    # Calcolo kp
    if eta_s is not None:
        # Usa eta_s fornito dall'utente (metodo CORRETTO secondo normativa)
        kp = eta_s / eta_s_min
        logger.info(f"  Metodo: eta_s / eta_s_min (CORRETTO secondo normativa)")
        logger.info(f"  eta_s dichiarato: {eta_s}%")
        logger.info(f"  eta_s_min Ecodesign: {eta_s_min}%")
        logger.info(f"  kp = {eta_s} / {eta_s_min} = {kp:.4f}")
    else:
        # Fallback: usa SCOP (meno preciso, per retrocompatibilità)
        kp = scop_dichiarato / scop_minimo
        logger.info(f"  Metodo: SCOP / SCOP_min (fallback - meno preciso)")
        logger.info(f"  NOTA: Per maggiore precisione, fornire eta_s dalla scheda tecnica")
        logger.info(f"  kp = {scop_dichiarato} / {scop_minimo} = {kp:.4f}")

    # -------------------------------------------------------------------------
    # STEP 4: Calcolo calore totale prodotto (Qu)
    # Riferimento: Tabella 8 Allegato 2 DM 7/8/2025
    # Formula: Qu = P_rated × Quf
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Calcolo calore totale prodotto (Qu)")

    quf = get_quf(zona, json_data)
    qu = potenza_nominale_kw * quf

    logger.info(f"  Quf (zona {zona}): {quf} ore equivalenti")
    logger.info(f"  Qu = {potenza_nominale_kw} kW × {quf} h = {qu:.2f} kWht")

    # -------------------------------------------------------------------------
    # STEP 5: Calcolo energia termica incentivata (Ei)
    # Riferimento: Regole Applicative CT 3.0, par. 9.9.3
    # Formula: Ei = Qu × (1 - 1/SCOP) × kp
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Calcolo energia termica incentivata (Ei)")

    ei = qu * (1 - 1/scop_dichiarato) * kp
    logger.info(f"  Ei = {qu:.2f} × (1 - 1/{scop_dichiarato}) × {kp:.4f}")
    logger.info(f"  Ei = {qu:.2f} × {(1 - 1/scop_dichiarato):.4f} × {kp:.4f}")
    logger.info(f"  Ei = {ei:.2f} kWht")

    # -------------------------------------------------------------------------
    # STEP 6: Calcolo incentivo annuo (Ia)
    # Riferimento: Tabella 9 Allegato 2 DM 7/8/2025
    # Formula: Ia = Ei × Ci
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 6] Calcolo incentivo annuo (Ia)")

    ci = get_ci(tipo_intervento, potenza_nominale_kw, json_data)
    ia = ei * ci

    logger.info(f"  Ci (coefficiente valorizzazione): {ci} EUR/kWht")
    logger.info(f"  Ia = {ei:.2f} kWht × {ci} EUR/kWht = {ia:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 7: Determinazione durata (n)
    # Riferimento: Art. 11, comma 3 DM 7/8/2025
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 7] Determinazione durata incentivo (n)")

    # Art. 11, comma 3: 2 annualità per P ≤ 35 kW, 5 annualità per P > 35 kW
    n = 2 if potenza_nominale_kw <= 35 else 5
    logger.info(f"  Potenza {potenza_nominale_kw} kW {'<=' if potenza_nominale_kw <= 35 else '>'} 35 kW")
    logger.info(f"  n = {n} annualità")

    # -------------------------------------------------------------------------
    # STEP 8: Calcolo incentivo totale lordo
    # Formula: I_tot_lordo = Ia × n
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 8] Calcolo incentivo totale lordo")

    i_tot_lordo = ia * n
    logger.info(f"  I_tot_lordo = {ia:.2f} EUR × {n} = {i_tot_lordo:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 9: Applicazione massimali
    # Riferimento: Art. 11 DM 7/8/2025 e Allegato 2
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 9] Applicazione massimali")

    # CAP A: Spesa specifica ammissibile (massimale €/kW)
    massimale_unitario = get_massimale_spesa(tipo_intervento)
    spesa_max_ammissibile = massimale_unitario * potenza_nominale_kw
    spesa_ammissibile = min(spesa_totale_sostenuta, spesa_max_ammissibile)

    logger.info(f"  [CAP A] Massimale spesa unitaria: {massimale_unitario} EUR/kW")
    logger.info(f"  Spesa max ammissibile: {massimale_unitario} × {potenza_nominale_kw} = {spesa_max_ammissibile:.2f} EUR")
    logger.info(f"  Spesa sostenuta: {spesa_totale_sostenuta:.2f} EUR")
    logger.info(f"  Spesa ammissibile: min({spesa_totale_sostenuta:.2f}, {spesa_max_ammissibile:.2f}) = {spesa_ammissibile:.2f} EUR")

    # CAP B: Percentuale massima
    # Art. 11, comma 2: PA su edifici pubblici -> 100%
    # Altri soggetti -> 65%
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
    # STEP 10: Determinazione rateazione
    # Riferimento: Art. 11, comma 4 DM 7/8/2025
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 10] Determinazione rateazione")

    # Art. 11, comma 4: Rata unica se I_tot ≤ 15.000 EUR o per PA/aventi diritto
    if i_tot <= SOGLIA_RATA_UNICA or tipo_soggetto == "PA":
        modalita = "rata_unica"
        rate = [round(i_tot, 2)]
        numero_rate = 1
        if tipo_soggetto == "PA":
            logger.info(f"  PA: erogazione in rata unica (indipendentemente dall'importo)")
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

    calcoli_intermedi: CalcoliIntermedi = {
        "Quf": quf,
        "Qu": round(qu, 2),
        "kp": round(kp, 4),
        "Ei": round(ei, 2),
        "Ci": ci,
        "Ia": round(ia, 2),
        "n": n,
        "I_tot_lordo": round(i_tot_lordo, 2)
    }

    massimali_applicati: MassimaliApplicati = {
        "spesa_ammissibile": round(spesa_ammissibile, 2),
        "massimale_unitario_applicato": massimale_unitario,
        "percentuale_applicata": percentuale,
        "I_max_da_massimali": round(i_max_percentuale, 2),
        "taglio_applicato": taglio_applicato,
        "importo_tagliato": round(importo_tagliato, 2)
    }

    erogazione: Erogazione = {
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
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    # Esempio di calcolo: PdC aria/acqua 10 kW, SCOP 4.5, zona E, spesa 15.000 EUR
    print("\n" + "=" * 70)
    print("ESEMPIO DI CALCOLO - Pompa di calore Aria/Acqua")
    print("=" * 70)

    risultato = calculate_heat_pump_incentive(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=4.5,
        spesa_totale_sostenuta=15000.0,
        gwp_refrigerante=">150",
        tipo_soggetto="privato",
        bassa_temperatura=False
    )

    print("\n" + "=" * 70)
    print("RISULTATO FINALE")
    print("=" * 70)
    print(json.dumps(risultato, indent=2, ensure_ascii=False))
