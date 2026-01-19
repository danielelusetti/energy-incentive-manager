"""
EnergyIncentiveManager - Applicazione Streamlit
Interfaccia web per il calcolo degli incentivi energetici (Conto Termico 3.0 ed Ecobonus)

Funzionalità:
- Calcolo singolo intervento
- Confronto fino a 5 scenari diversi
- Storico calcoli nella sessione
- Generazione relazione tecnica (HTML/PDF)
- Supporto PdC elettriche e a gas

Autore: EnergyIncentiveManager
Versione: 2.0.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import base64
import json
from pathlib import Path

# Import moduli locali
from modules.validator import (
    valida_requisiti_ct, valida_requisiti_ecobonus,
    valida_requisiti_solare_termico, valida_requisiti_fv_combinato,
    valida_requisiti_biomassa, DOCUMENTAZIONE_BIOMASSA
)
from modules.calculator_ct import calculate_heat_pump_incentive
from modules.calculator_eco import calculate_ecobonus_deduction
from modules.calculator_solare import calculate_solar_thermal_incentive, TIPOLOGIE_SOLARE, TIPI_COLLETTORE
from modules.calculator_fv import (
    calculate_fv_combined_incentive, verifica_dimensionamento_fv,
    COSTI_MAX_FV, COSTO_MAX_ACCUMULO, MAGGIORAZIONI_REGISTRO
)
from modules.calculator_biomassa import (
    calculate_biomass_incentive, calcola_ecobonus_biomassa, confronta_incentivi_biomassa,
    TIPI_GENERATORE, COEFFICIENTI_CI, ORE_FUNZIONAMENTO, MASSIMALI_SPESA as MASSIMALI_BIOMASSA,
    LIMITI_POTENZA as LIMITI_POTENZA_BIOMASSA
)
from modules.financial_roi import calculate_npv
from modules.report_generator import (
    genera_report_html, genera_report_markdown, ScenarioCalcolo,
    genera_report_solare_termico_html, ScenarioSolareTermico,
    genera_report_building_automation_html
)
from modules.zone_climatiche import (
    get_lista_regioni, get_province_by_regione, get_zona_climatica, get_info_provincia
)
from modules.vincoli_terziario import (
    verifica_vincoli_terziario, is_terziario, calcola_riduzione_richiesta,
    CATEGORIE_CATASTALI_TERZIARIO, CATEGORIE_CATASTALI_RESIDENZIALE,
    get_interventi_soggetti_vincolo, get_descrizione_vincolo,
    verifica_vincoli_intervento_generico, get_codice_intervento
)
from modules.prenotazione import (
    simula_prenotazione, is_prenotazione_ammissibile,
    calcola_rateizzazione_prenotazione, calcola_calendario_prenotazione,
    get_fasi_prenotazione
)
from modules.gestione_progetti import get_gestore_progetti

# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Energy Incentive Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato con ottimizzazione mobile
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        color: #155724;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 5px;
        padding: 1rem;
        color: #856404;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        color: #721c24;
    }
    .info-box {
        background-color: #e7f3ff;
        border: 1px solid #b8daff;
        border-radius: 5px;
        padding: 1rem;
        color: #004085;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    .scenario-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .scenario-winner {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border: 2px solid #2E7D32;
    }
    /* Mobile optimization */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem;
        }
        .sub-header {
            font-size: 1rem;
        }
        .stButton button {
            width: 100%;
            padding: 15px;
            font-size: 16px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# COSTANTI E MAPPATURE
# ============================================================================

TIPI_INTERVENTO_ELETTRICO = {
    "Aria/Aria - Split/Multisplit": "split_multisplit",
    "Aria/Aria - Fixed Double Duct": "fixed_double_duct",
    "Aria/Aria - VRF/VRV": "vrf_vrv",
    "Aria/Aria - Rooftop": "rooftop",
    "Aria/Acqua": "aria_acqua",
    "Acqua/Aria": "acqua_aria",
    "Acqua/Acqua": "acqua_acqua",
    "Geotermica Salamoia/Aria": "geotermiche_salamoia_aria",
    "Geotermica Salamoia/Acqua": "geotermiche_salamoia_acqua",
}

TIPI_INTERVENTO_GAS = {
    "Aria/Aria (Gas)": "aria_aria_gas",
    "Acqua/Aria (Gas)": "acqua_aria_gas",
    "Salamoia/Aria (Gas)": "salamoia_aria_gas",
    "Acqua/Acqua (Gas)": "acqua_acqua_gas",
    "Salamoia/Acqua (Gas)": "salamoia_acqua_gas",
}

ZONE_CLIMATICHE = {
    "A - Clima molto caldo (es. Lampedusa)": "A",
    "B - Clima caldo (es. Palermo, Catania)": "B",
    "C - Clima temperato caldo (es. Napoli, Roma)": "C",
    "D - Clima temperato (es. Firenze, Ancona)": "D",
    "E - Clima temperato freddo (es. Milano, Torino, Bologna)": "E",
    "F - Clima freddo (es. Belluno, zone montane)": "F",
}

TIPI_SOGGETTO = {
    "Privato cittadino": "privato",
    "Impresa": "impresa",
    "Pubblica Amministrazione": "PA",
}

TIPI_ABITAZIONE = {
    "Prima casa (abitazione principale)": "abitazione_principale",
    "Seconda casa": "altra_abitazione",
    "Parti comuni condominio": "parti_comuni",
}

# Mappa eta_s_min per tipologia (valori da Tabelle 3-4-5 Allegato 1 DM 7/8/2025)
ETA_S_MIN_MAP = {
    "split_multisplit": {"GWP_gt_150": 149, "GWP_lte_150": 134},
    "fixed_double_duct": {"GWP_gt_150": 149, "GWP_lte_150": 134},
    "vrf_vrv": 137,
    "rooftop": 125,
    "aria_acqua": {"standard": 110, "bassa_temperatura": 125},
    "acqua_aria": 137,
    "acqua_acqua": {"standard": 110, "bassa_temperatura": 125},
    "geotermiche_salamoia_aria": {"lte_12kw": {"GWP_gt_150": 149, "GWP_lte_150": 134}, "gt_12kw": 137},
    "geotermiche_salamoia_acqua": {"standard": 110, "bassa_temperatura": 125},
    # PdC a gas (usano SPER invece di eta_s)
    "aria_aria_gas": 130,
    "acqua_aria_gas": 130,
    "salamoia_aria_gas": 130,
    "acqua_acqua_gas": {"standard": 110, "bassa_temperatura": 125},
    "salamoia_acqua_gas": 125,
}

# SCOP minimi per tipologia (da Tabelle 3-4-5 Allegato 1)
SCOP_MIN_MAP = {
    "split_multisplit": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42},
    "fixed_double_duct": {"GWP_gt_150": 2.60, "GWP_lte_150": 2.34},  # COP per fixed
    "vrf_vrv": 3.50,
    "rooftop": 3.20,
    "aria_acqua": {"standard": 2.825, "bassa_temperatura": 3.20},
    "acqua_aria": 3.625,
    "acqua_acqua": {"standard": 2.95, "bassa_temperatura": 3.325},
    "geotermiche_salamoia_aria": {"lte_12kw": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42}, "gt_12kw": 3.625},
    "geotermiche_salamoia_acqua": {"standard": 2.825, "bassa_temperatura": 3.20},
}

# SPER minimi per PdC a gas (Tabella 5 - Allegato 1)
SPER_MIN_MAP = {
    "aria_aria_gas": 1.33,
    "acqua_aria_gas": 1.33,
    "salamoia_aria_gas": 1.33,
    "acqua_acqua_gas": {"standard": 1.13, "bassa_temperatura": 1.28},
    "salamoia_acqua_gas": 1.28,
}


# ============================================================================
# CARICAMENTO CATALOGO GSE
# ============================================================================

@st.cache_data
def load_catalogo_gse() -> list[dict]:
    """Carica il catalogo GSE delle pompe di calore."""
    catalogo_path = Path(__file__).parent / "data" / "catalogo_pdc.json"
    if catalogo_path.exists():
        with open(catalogo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_marche_catalogo(catalogo: list[dict]) -> list[str]:
    """Restituisce la lista delle marche ordinate."""
    marche = sorted(set(p.get("marca", "") for p in catalogo if p.get("marca")))
    return marche


def get_modelli_per_marca(catalogo: list[dict], marca: str) -> list[dict]:
    """Restituisce i modelli per una marca specifica."""
    modelli = [p for p in catalogo if p.get("marca") == marca]
    # Ordina per modello
    modelli.sort(key=lambda x: x.get("modello", ""))
    return modelli


def get_prodotto_da_catalogo(catalogo: list[dict], marca: str, modello: str) -> dict | None:
    """Trova un prodotto specifico nel catalogo."""
    for p in catalogo:
        if p.get("marca") == marca and p.get("modello") == modello:
            return p
    return None


def map_tipologia_catalogo_to_intervento(tipologia: str) -> str:
    """Mappa la tipologia del catalogo al tipo intervento dell'app."""
    tipologia_lower = tipologia.lower() if tipologia else ""

    mapping = {
        "aria/acqua": "aria_acqua",
        "aria/aria": "aria_aria",  # Corretto: usa aria_aria come tipo base
        "acqua/acqua": "acqua_acqua",
        "acqua/aria": "acqua_aria",
        "geotermica": "geotermiche_salamoia_acqua",
        "salamoia/acqua": "geotermiche_salamoia_acqua",
        "acqua glicolata/acqua": "geotermiche_salamoia_acqua",
        "acqua di falda/acqua": "geotermiche_acqua_falda",
    }

    for key, value in mapping.items():
        if key in tipologia_lower:
            return value

    return "aria_acqua"  # Default


# ============================================================================
# CARICAMENTO CATALOGO GSE - SOLARE TERMICO
# ============================================================================

@st.cache_data
def load_catalogo_solare_termico() -> list[dict]:
    """Carica il catalogo GSE dei collettori solari termici."""
    # Prova prima il nuovo catalogo completo
    catalogo_path_new = Path(__file__).parent / "data" / "products_solare_termico.json"
    if catalogo_path_new.exists():
        with open(catalogo_path_new, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback al vecchio catalogo se il nuovo non esiste
    catalogo_path_old = Path(__file__).parent / "data" / "catalogo_solare_termico.json"
    if catalogo_path_old.exists():
        with open(catalogo_path_old, "r", encoding="utf-8") as f:
            return json.load(f)

    return []


def get_marche_catalogo_st(catalogo: list[dict]) -> list[str]:
    """Restituisce la lista delle marche ordinate per solare termico."""
    marche = sorted(set(p.get("marca", "") for p in catalogo if p.get("marca")))
    return marche


def get_modelli_per_marca_st(catalogo: list[dict], marca: str) -> list[dict]:
    """Restituisce i modelli per una marca specifica (solare termico)."""
    modelli = [p for p in catalogo if p.get("marca") == marca]
    modelli.sort(key=lambda x: x.get("modello", ""))
    return modelli


def get_prodotto_da_catalogo_st(catalogo: list[dict], marca: str, modello: str) -> dict | None:
    """Trova un prodotto specifico nel catalogo solare termico."""
    for p in catalogo:
        if p.get("marca") == marca and p.get("modello") == modello:
            return p
    return None


def map_tipologia_catalogo_st(tipologia: str) -> str:
    """Mappa la tipologia del catalogo solare termico ai tipi collettore dell'app."""
    tipologia_lower = tipologia.lower() if tipologia else ""

    mapping = {
        "piano": "piano",
        "piani": "piano",
        "sottovuoto": "sottovuoto",
        "concentrazione": "concentrazione",
        "factory_made": "factory_made",
        "factory made": "factory_made",
    }

    for key, value in mapping.items():
        if key in tipologia_lower:
            return value

    return "piano"  # Default


# ============================================================================
# CARICAMENTO CATALOGO GSE - BIOMASSA
# ============================================================================

@st.cache_data
def load_catalogo_biomassa() -> list[dict]:
    """Carica il catalogo GSE dei generatori a biomassa."""
    catalogo_path = Path(__file__).parent / "data" / "products_biomassa.json"
    if catalogo_path.exists():
        with open(catalogo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_marche_catalogo_biomassa(catalogo: list[dict]) -> list[str]:
    """Restituisce la lista delle marche ordinate per biomassa."""
    marche = sorted(set(p.get("marca", "") for p in catalogo if p.get("marca")))
    return marche


def get_modelli_per_marca_biomassa(catalogo: list[dict], marca: str) -> list[dict]:
    """Restituisce i modelli per una marca specifica (biomassa)."""
    modelli = [p for p in catalogo if p.get("marca") == marca]
    modelli.sort(key=lambda x: x.get("modello", ""))
    return modelli


def get_prodotto_da_catalogo_biomassa(catalogo: list[dict], marca: str, modello: str) -> dict | None:
    """Trova un prodotto specifico nel catalogo biomassa."""
    for p in catalogo:
        if p.get("marca") == marca and p.get("modello") == modello:
            return p
    return None


# ============================================================================
# CARICAMENTO CATALOGO GSE - SCALDACQUA PDC
# ============================================================================

@st.cache_data
def load_catalogo_scaldacqua() -> list[dict]:
    """Carica il catalogo GSE degli scaldacqua a pompa di calore."""
    catalogo_path = Path(__file__).parent / "data" / "products_scaldacqua.json"
    if catalogo_path.exists():
        with open(catalogo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_marche_catalogo_scaldacqua(catalogo: list[dict]) -> list[str]:
    """Restituisce la lista delle marche ordinate per scaldacqua."""
    marche = sorted(set(p.get("marca", "") for p in catalogo if p.get("marca")))
    return marche


def get_modelli_per_marca_scaldacqua(catalogo: list[dict], marca: str) -> list[dict]:
    """Restituisce i modelli per una marca specifica (scaldacqua)."""
    modelli = [p for p in catalogo if p.get("marca") == marca]
    modelli.sort(key=lambda x: x.get("modello", ""))
    return modelli


def get_prodotto_da_catalogo_scaldacqua(catalogo: list[dict], marca: str, modello: str) -> dict | None:
    """Trova un prodotto specifico nel catalogo scaldacqua."""
    for p in catalogo:
        if p.get("marca") == marca and p.get("modello") == modello:
            return p
    return None


# ============================================================================
# CARICAMENTO CATALOGO GSE - SISTEMI IBRIDI
# ============================================================================

@st.cache_data
def load_catalogo_ibridi() -> list[dict]:
    """Carica il catalogo GSE dei sistemi ibridi."""
    catalogo_path = Path(__file__).parent / "data" / "products_ibridi.json"
    if catalogo_path.exists():
        with open(catalogo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_marche_catalogo_ibridi(catalogo: list[dict]) -> list[str]:
    """Restituisce la lista delle marche ordinate per sistemi ibridi."""
    marche = sorted(set(p.get("marca", "") for p in catalogo if p.get("marca")))
    return marche


def get_modelli_per_marca_ibridi(catalogo: list[dict], marca: str) -> list[dict]:
    """Restituisce i modelli per una marca specifica (sistemi ibridi)."""
    modelli = [p for p in catalogo if p.get("marca") == marca]
    modelli.sort(key=lambda x: x.get("modello_pompa_calore", ""))
    return modelli


def get_prodotto_da_catalogo_ibridi(catalogo: list[dict], marca: str, modello_pdc: str) -> dict | None:
    """Trova un prodotto specifico nel catalogo sistemi ibridi."""
    for p in catalogo:
        if p.get("marca") == marca and p.get("modello_pompa_calore") == modello_pdc:
            return p
    return None


def map_tipologia_generatore_catalogo(tipologia_generatore: str, tipologia_alimentazione: str) -> str:
    """
    Mappa le tipologie del catalogo biomassa al tipo generatore dell'app.

    Args:
        tipologia_generatore: caldaia, stufa, termocamino
        tipologia_alimentazione: automatica, manuale

    Returns:
        Chiave del tipo generatore per l'app
    """
    tipo_gen_lower = tipologia_generatore.lower() if tipologia_generatore else ""
    tipo_alim_lower = tipologia_alimentazione.lower() if tipologia_alimentazione else ""

    # Caldaie (sempre automatiche, quindi distinguiamo per potenza successivamente)
    if "caldaia" in tipo_gen_lower:
        return "caldaia_lte_500"  # Default, verrà raffinato in base alla potenza

    # Stufe e termocamini (pellet = automatica, legna = manuale)
    if "stufa" in tipo_gen_lower:
        if "automatic" in tipo_alim_lower or "pellet" in tipo_alim_lower:
            return "stufa_pellet"
        else:
            return "stufa_legna"

    if "termocamino" in tipo_gen_lower or "camino" in tipo_gen_lower:
        if "automatic" in tipo_alim_lower or "pellet" in tipo_alim_lower:
            return "termocamino_pellet"
        else:
            return "termocamino_legna"

    return "caldaia_lte_500"  # Default


# ============================================================================
# FUNZIONI HELPER
# ============================================================================

def get_eta_s_min(tipo_intervento: str, gwp: str, bassa_temperatura: bool, potenza_kw: float) -> int:
    """Restituisce eta_s_min in base alla tipologia."""
    if tipo_intervento in ["split_multisplit", "fixed_double_duct"]:
        key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
        return ETA_S_MIN_MAP.get(tipo_intervento, {}).get(key, 149)
    elif tipo_intervento in ["vrf_vrv", "rooftop", "acqua_aria"]:
        return ETA_S_MIN_MAP.get(tipo_intervento, 137)
    elif tipo_intervento in ["aria_acqua", "acqua_acqua", "geotermiche_salamoia_acqua"]:
        key = "bassa_temperatura" if bassa_temperatura else "standard"
        return ETA_S_MIN_MAP.get(tipo_intervento, {}).get(key, 110)
    elif tipo_intervento == "geotermiche_salamoia_aria":
        if potenza_kw <= 12:
            key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
            return ETA_S_MIN_MAP["geotermiche_salamoia_aria"]["lte_12kw"].get(key, 149)
        else:
            return ETA_S_MIN_MAP["geotermiche_salamoia_aria"]["gt_12kw"]
    # PdC a gas
    elif tipo_intervento in ["aria_aria_gas", "acqua_aria_gas", "salamoia_aria_gas"]:
        return ETA_S_MIN_MAP.get(tipo_intervento, 130)
    elif tipo_intervento in ["acqua_acqua_gas", "salamoia_acqua_gas"]:
        if isinstance(ETA_S_MIN_MAP.get(tipo_intervento), dict):
            key = "bassa_temperatura" if bassa_temperatura else "standard"
            return ETA_S_MIN_MAP[tipo_intervento].get(key, 110)
        return ETA_S_MIN_MAP.get(tipo_intervento, 125)
    return 110


def get_scop_min(tipo_intervento: str, gwp: str, bassa_temperatura: bool, potenza_kw: float) -> float:
    """Restituisce SCOP/COP minimo in base alla tipologia."""
    if tipo_intervento in ["split_multisplit", "fixed_double_duct"]:
        key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
        return SCOP_MIN_MAP.get(tipo_intervento, {}).get(key, 3.0)
    elif tipo_intervento in ["vrf_vrv", "rooftop", "acqua_aria"]:
        return SCOP_MIN_MAP.get(tipo_intervento, 3.0)
    elif tipo_intervento in ["aria_acqua", "acqua_acqua", "geotermiche_salamoia_acqua"]:
        key = "bassa_temperatura" if bassa_temperatura else "standard"
        return SCOP_MIN_MAP.get(tipo_intervento, {}).get(key, 2.825)
    elif tipo_intervento == "geotermiche_salamoia_aria":
        if potenza_kw <= 12:
            key = "GWP_gt_150" if gwp == ">150" else "GWP_lte_150"
            return SCOP_MIN_MAP["geotermiche_salamoia_aria"]["lte_12kw"].get(key, 3.80)
        else:
            return SCOP_MIN_MAP["geotermiche_salamoia_aria"]["gt_12kw"]
    return 2.825


def get_sper_min(tipo_intervento: str, bassa_temperatura: bool) -> float:
    """Restituisce SPER minimo per PdC a gas."""
    if tipo_intervento not in SPER_MIN_MAP:
        return 1.13
    val = SPER_MIN_MAP[tipo_intervento]
    if isinstance(val, dict):
        key = "bassa_temperatura" if bassa_temperatura else "standard"
        return val.get(key, 1.13)
    return val


def format_currency(value: float) -> str:
    """Formatta un valore come valuta EUR."""
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def is_gas_pump(tipo_intervento: str) -> bool:
    """Verifica se è una pompa di calore a gas."""
    return tipo_intervento.endswith("_gas")


def applica_vincoli_terziario_ct3(
    tipo_intervento_app: str,
    tipo_soggetto_label: str,
    tipo_pdc: str = None
) -> tuple[bool, str | None]:
    """
    Applica vincoli terziario CT 3.0 per un intervento.

    Args:
        tipo_intervento_app: Tipo intervento (es. "serramenti", "isolamento_termico")
        tipo_soggetto_label: Label tipo soggetto from sidebar
        tipo_pdc: Tipo PDC ("gas" o "elettrica") solo per pompe di calore

    Returns:
        (ammissibile, messaggio_errore)
        - ammissibile: True se può procedere, False se bloccato
        - messaggio_errore: None se OK, stringa con errore se bloccato
    """
    # Se non c'è categoria catastale, passa (non applica vincoli)
    if not st.session_state.categoria_catastale:
        return True, None

    # Mappa tipo soggetto al formato vincoli
    tipo_soggetto_vincoli = tipo_soggetto_label
    if tipo_soggetto_label == "Privato cittadino":
        tipo_soggetto_vincoli = "Privato"
    elif tipo_soggetto_label == "Pubblica Amministrazione":
        tipo_soggetto_vincoli = "PA"

    # Verifica vincoli
    vincoli = verifica_vincoli_intervento_generico(
        tipo_intervento_app=tipo_intervento_app,
        tipo_soggetto=tipo_soggetto_vincoli,
        categoria_catastale=st.session_state.categoria_catastale,
        tipo_pdc=tipo_pdc,
        riduzione_energia_primaria_effettiva=st.session_state.riduzione_ep_effettiva / 100,
        ape_disponibili=st.session_state.ape_disponibili,
        multi_intervento=False,
        interventi_combinati=[]
    )

    # Ritorna risultato
    if not vincoli["vincolo_soddisfatto"]:
        return False, vincoli["messaggio"]
    elif vincoli["richiede_ape"] and not st.session_state.ape_disponibili:
        # Warning ma non blocca
        return True, vincoli["messaggio"]

    return True, None


def init_session_state():
    """Inizializza lo state della sessione."""
    if "storico_calcoli" not in st.session_state:
        st.session_state.storico_calcoli = []
    if "scenari" not in st.session_state:
        st.session_state.scenari = []
    if "scenari_solare" not in st.session_state:
        st.session_state.scenari_solare = []
    if "scenari_scaldacqua" not in st.session_state:
        st.session_state.scenari_scaldacqua = []
    if "scenari_ibridi" not in st.session_state:
        st.session_state.scenari_ibridi = []
    if "scenari_isolamento" not in st.session_state:
        st.session_state.scenari_isolamento = []
    if "scenari_serramenti" not in st.session_state:
        st.session_state.scenari_serramenti = []
    if "scenari_ricarica_veicoli" not in st.session_state:
        st.session_state.scenari_ricarica_veicoli = []
    if "scenari_building_automation" not in st.session_state:
        st.session_state.scenari_building_automation = []
    if "ultimo_confronto_ba" not in st.session_state:
        st.session_state.ultimo_confronto_ba = None
    if "ultimo_calcolo_solare" not in st.session_state:
        st.session_state.ultimo_calcolo_solare = None
    if "ultimo_calcolo_isolamento" not in st.session_state:
        st.session_state.ultimo_calcolo_isolamento = None
    if "ultimo_calcolo_serramenti" not in st.session_state:
        st.session_state.ultimo_calcolo_serramenti = None
    if "ultimo_calcolo_ibridi" not in st.session_state:
        st.session_state.ultimo_calcolo_ibridi = None
    if "progetto_multi" not in st.session_state:
        st.session_state.progetto_multi = {
            "nome_progetto": "",
            "tipo_soggetto": "privato",
            "tipo_edificio": "residenziale",
            "indirizzo": "",
            "interventi": [],
            "riduzione_ep_perc": None,
            "data_conclusione": None
        }
    if "progetti_multi_salvati" not in st.session_state:
        st.session_state.progetti_multi_salvati = []
    if "ultimo_calcolo" not in st.session_state:
        st.session_state.ultimo_calcolo = None
    if "ultimo_calcolo_fv" not in st.session_state:
        st.session_state.ultimo_calcolo_fv = None
    # Nuovi state per CT 3.0
    if "ultimo_incentivo" not in st.session_state:
        st.session_state.ultimo_incentivo = 0.0
    if "ultimo_numero_anni" not in st.session_state:
        st.session_state.ultimo_numero_anni = 2
    if "categoria_catastale" not in st.session_state:
        st.session_state.categoria_catastale = None
    if "tipo_soggetto_principale" not in st.session_state:
        st.session_state.tipo_soggetto_principale = "privato"
    if "ape_disponibili" not in st.session_state:
        st.session_state.ape_disponibili = False
    if "riduzione_ep_effettiva" not in st.session_state:
        st.session_state.riduzione_ep_effettiva = 0.0
    if "edificio_pubblico_art11" not in st.session_state:
        st.session_state.edificio_pubblico_art11 = False


def aggiungi_a_storico(risultato: dict):
    """Aggiunge un calcolo allo storico."""
    risultato["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.session_state.storico_calcoli.insert(0, risultato)
    # Mantieni solo gli ultimi 20 calcoli
    st.session_state.storico_calcoli = st.session_state.storico_calcoli[:20]


def create_comparison_chart(ct_value: float, eco_value: float, npv_ct: float, npv_eco: float):
    """Crea grafico di confronto tra incentivi."""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Incentivo Nominale", "Valore Attuale Netto (NPV)"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )

    fig.add_trace(
        go.Bar(name="Conto Termico", x=["Conto Termico"], y=[ct_value],
               marker_color="#2E7D32", text=[format_currency(ct_value)], textposition="auto"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name="Ecobonus", x=["Ecobonus"], y=[eco_value],
               marker_color="#1565C0", text=[format_currency(eco_value)], textposition="auto"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name="NPV CT", x=["Conto Termico"], y=[npv_ct],
               marker_color="#4CAF50", text=[format_currency(npv_ct)], textposition="auto", showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name="NPV Eco", x=["Ecobonus"], y=[npv_eco],
               marker_color="#2196F3", text=[format_currency(npv_eco)], textposition="auto", showlegend=False),
        row=1, col=2
    )

    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def create_scenarios_comparison_chart(scenari: list):
    """Crea grafico confronto tra scenari multipli."""
    if not scenari:
        return None

    nomi = [s["nome"] for s in scenari]
    ct_values = [s["ct_incentivo"] for s in scenari]
    eco_values = [s["eco_detrazione"] for s in scenari]
    npv_ct = [s["npv_ct"] for s in scenari]
    npv_eco = [s["npv_eco"] for s in scenari]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Incentivo Nominale", "NPV"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )

    fig.add_trace(
        go.Bar(name="Conto Termico", x=nomi, y=ct_values, marker_color="#2E7D32"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name="Ecobonus", x=nomi, y=eco_values, marker_color="#1565C0"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name="NPV CT", x=nomi, y=npv_ct, marker_color="#4CAF50", showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name="NPV Eco", x=nomi, y=npv_eco, marker_color="#2196F3", showlegend=False),
        row=1, col=2
    )

    fig.update_layout(
        height=400,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def calcola_scenario(
    nome: str, tipo_intervento: str, tipo_intervento_label: str,
    potenza_kw: float, scop: float, eta_s: float, eta_s_min: int, scop_min: float,
    zona_climatica: str, gwp: str, bassa_temp: bool, spesa: float,
    tipo_soggetto: str, tipo_abitazione: str, anno: int, tasso_sconto: float,
    alimentazione: str = "elettrica",
    iter_semplificato: bool = False
) -> dict:
    """Calcola un singolo scenario e restituisce i risultati."""

    # Mappa tipi app -> tipi validator
    # L'app usa tipi dettagliati (split_multisplit, vrf_vrv, ecc.)
    # Il validator usa tipi base (aria_aria, aria_acqua, ecc.)
    MAPPA_TIPI_VALIDATOR = {
        "split_multisplit": "aria_aria",
        "fixed_double_duct": "aria_aria",
        "vrf_vrv": "aria_aria",
        "rooftop": "aria_aria",
        "aria_acqua": "aria_acqua",
        "acqua_acqua": "acqua_acqua",
        "acqua_aria": "acqua_aria",
        "geotermiche_salamoia_aria": "geotermiche_salamoia_aria",
        "geotermiche_salamoia_acqua": "geotermiche_salamoia_acqua",
        "geotermiche_acqua_falda": "geotermiche_acqua_falda",
        # Tipi gas
        "aria_aria_gas": "acqua_aria",
        "salamoia_aria_gas": "geotermiche_salamoia_aria",
        "salamoia_acqua_gas": "geotermiche_salamoia_acqua",
    }

    # Mappa tipo app a tipo base per validazione
    tipo_base = MAPPA_TIPI_VALIDATOR.get(tipo_intervento, tipo_intervento)

    # Fallback per tipi gas non mappati
    if is_gas_pump(tipo_intervento) and tipo_base == tipo_intervento:
        tipo_base = tipo_intervento.replace("_gas", "")

    # Validazione CT
    validazione_ct = valida_requisiti_ct(
        tipo_intervento=tipo_base,
        zona_climatica=zona_climatica,
        potenza_nominale_kw=potenza_kw,
        scop_dichiarato=scop,
        gwp_refrigerante=gwp,
        bassa_temperatura=bassa_temp,
        alimentazione=alimentazione,
        iter_semplificato=iter_semplificato
    )

    # Calcolo CT
    risultato_ct = None
    ct_ammissibile = validazione_ct.ammissibile
    ct_incentivo = 0
    ct_rate = []
    ct_annualita = 0
    ct_kp = 0
    ct_ei = 0
    ct_ci = 0
    ct_quf = 0

    # Verifica requisiti eta_s
    # Se iter semplificato (prodotto nel catalogo GSE), il requisito è già verificato dal GSE
    eta_s_valido = iter_semplificato or (eta_s >= eta_s_min)

    # Verifica vincoli terziario CT 3.0 (Punto 3)
    vincolo_terziario_msg = None
    if st.session_state.categoria_catastale:
        # Mappa tipo soggetto al formato vincoli_terziario
        tipo_soggetto_vincoli = tipo_soggetto_label
        if tipo_soggetto_label == "Privato cittadino":
            tipo_soggetto_vincoli = "Privato"
        elif tipo_soggetto_label == "Pubblica Amministrazione":
            tipo_soggetto_vincoli = "PA"
        # Impresa rimane "Impresa"

        # Determina tipo PDC
        tipo_pdc = "gas" if is_gas_pump(tipo_intervento) else "elettrica"

        vincoli = verifica_vincoli_terziario(
            tipo_soggetto=tipo_soggetto_vincoli,
            categoria_catastale=st.session_state.categoria_catastale,
            codice_intervento="III.A",  # Pompe di calore = intervento III.A
            tipo_pdc=tipo_pdc,
            multi_intervento=False,
            interventi_combinati=[],
            riduzione_energia_primaria_effettiva=st.session_state.riduzione_ep_effettiva / 100,
            ape_disponibili=st.session_state.ape_disponibili
        )

        # Se vincolo non soddisfatto, blocca calcolo
        if not vincoli["vincolo_soddisfatto"]:
            ct_ammissibile = False
            vincolo_terziario_msg = vincoli["messaggio"]

        # Se richiede APE ma non disponibili, salva warning
        elif vincoli["richiede_ape"] and not st.session_state.ape_disponibili:
            vincolo_terziario_msg = vincoli["messaggio"]

    if ct_ammissibile and eta_s_valido:
        risultato_ct = calculate_heat_pump_incentive(
            tipo_intervento=tipo_base,
            zona_climatica=zona_climatica,
            potenza_nominale_kw=potenza_kw,
            scop_dichiarato=scop,
            spesa_totale_sostenuta=spesa,
            gwp_refrigerante=gwp,
            tipo_soggetto=tipo_soggetto,
            bassa_temperatura=bassa_temp,
            eta_s=eta_s
        )
        if risultato_ct and risultato_ct["status"] == "OK":
            ct_incentivo = risultato_ct["incentivo_totale"]
            ct_rate = risultato_ct["erogazione"]["rate"]
            ct_annualita = len(ct_rate)
            ct_kp = risultato_ct["calcoli_intermedi"]["kp"]
            ct_ei = risultato_ct["calcoli_intermedi"]["Ei"]
            ct_ci = risultato_ct["calcoli_intermedi"]["Ci"]
            ct_quf = risultato_ct["calcoli_intermedi"]["Quf"]

            # Salva in session state per Prenotazione (Punto 5)
            st.session_state.ultimo_incentivo = ct_incentivo
            st.session_state.ultimo_numero_anni = ct_annualita
    elif not eta_s_valido:
        ct_ammissibile = False

    # Validazione e calcolo Ecobonus
    validazione_eco = valida_requisiti_ecobonus(
        tipo_intervento="pompe_di_calore",
        anno_spesa=anno,
        tipo_abitazione=tipo_abitazione
    )

    risultato_eco = None
    eco_ammissibile = validazione_eco.ammissibile
    eco_detrazione = 0
    eco_aliquota = 0

    if eco_ammissibile:
        risultato_eco = calculate_ecobonus_deduction(
            tipo_intervento="pompe_di_calore",
            spesa_sostenuta=spesa,
            anno_spesa=anno,
            tipo_abitazione=tipo_abitazione
        )
        if risultato_eco and risultato_eco["status"] == "OK":
            eco_detrazione = risultato_eco["detrazione_totale"]
            eco_aliquota = risultato_eco["calcoli"]["aliquota_applicata"]

    # Calcolo NPV
    npv_ct = 0
    npv_eco = 0

    if ct_incentivo > 0:
        cf_ct = [0.0] + ct_rate
        npv_ct = calculate_npv(cf_ct, tasso_sconto)

    if eco_detrazione > 0:
        rata_eco = eco_detrazione / 10
        cf_eco = [0.0] + [rata_eco] * 10
        npv_eco = calculate_npv(cf_eco, tasso_sconto)

    return {
        "nome": nome,
        "tipo_intervento": tipo_intervento,
        "tipo_intervento_label": tipo_intervento_label,
        "potenza_kw": potenza_kw,
        "scop": scop,
        "eta_s": eta_s,
        "eta_s_min": eta_s_min,
        "scop_min": scop_min,
        "zona_climatica": zona_climatica,
        "gwp": gwp,
        "bassa_temp": bassa_temp,
        "spesa": spesa,
        "alimentazione": alimentazione,
        "ct_ammissibile": ct_ammissibile,
        "ct_incentivo": ct_incentivo,
        "ct_rate": ct_rate,
        "ct_annualita": ct_annualita,
        "ct_kp": ct_kp,
        "ct_ei": ct_ei,
        "ct_ci": ct_ci,
        "ct_quf": ct_quf,
        "eco_ammissibile": eco_ammissibile,
        "eco_detrazione": eco_detrazione,
        "eco_aliquota": eco_aliquota,
        "npv_ct": npv_ct,
        "npv_eco": npv_eco,
        "validazione_ct": validazione_ct,
        "validazione_eco": validazione_eco,
        "risultato_ct": risultato_ct,
        "risultato_eco": risultato_eco,
        "vincolo_terziario_msg": vincolo_terziario_msg,  # CT 3.0
    }


def get_download_link(content: str, filename: str, mime: str = "text/html") -> str:
    """Genera link download per contenuto."""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:{mime};base64,{b64}" download="{filename}" style="display:inline-block;padding:10px 20px;background-color:#1E88E5;color:white;text-decoration:none;border-radius:5px;margin:10px 0;">📥 Scarica {filename}</a>'


# ============================================================================
# INTERFACCIA PRINCIPALE
# ============================================================================

def main():
    init_session_state()

    # Header
    st.markdown('<p class="main-header">⚡ Energy Incentive Manager</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Calcolo e confronto incentivi Conto Termico 3.0 ed Ecobonus</p>', unsafe_allow_html=True)

    # Tabs principali
    tab_calcolo, tab_solare, tab_fv, tab_biomassa, tab_isolamento, tab_serramenti, tab_schermature, tab_illuminazione, tab_building_automation, tab_ibridi, tab_scaldacqua, tab_multi, tab_scenari, tab_storico, tab_progetti, tab_prenotazione, tab_report, tab_documenti = st.tabs([
        "🔥 PdC",
        "☀️ Solare",
        "🔆 FV",
        "🌲 Biomassa",
        "🏠 Isolamento",
        "🪟 Serramenti",
        "🌤️ Schermature",
        "💡 LED",
        "🏢 B.A.",
        "🔀 Ibridi",
        "🚿 Scaldacqua",
        "🔗 Multi",
        "📊 Scenari",
        "📜 Storico",
        "📁 Progetti",
        "🗓️ Prenotazione",
        "📄 Report",
        "📋 Documenti"
    ])

    # ===========================================================================
    # SIDEBAR - Parametri Comuni (validi per tutti gli interventi)
    # ===========================================================================
    with st.sidebar:
        st.header("⚙️ Parametri Comuni")
        st.caption("Questi parametri si applicano a tutti gli interventi")

        st.divider()

        # NOVITÀ CT 3.0 - Tipo edificio principale
        st.markdown("##### 🏢 Tipologia Edificio e Soggetto")

        tipo_edificio = st.selectbox(
            "Tipo edificio",
            options=[
                "Residenziale - Privato",
                "Residenziale - Condominio",
                "Terziario - Impresa/ETS economico",
                "PA / ETS non economico"
            ],
            index=0,
            key="sidebar_tipo_edificio",
            help="Determina percentuali incentivo e vincoli applicabili"
        )

        # Mappa tipo edificio a tipo soggetto e categoria
        if tipo_edificio == "Residenziale - Privato":
            tipo_soggetto_label = "Privato cittadino"
            edificio_pubblico_art11 = False
            suggerimento_categoria = CATEGORIE_CATASTALI_RESIDENZIALE
        elif tipo_edificio == "Residenziale - Condominio":
            tipo_soggetto_label = "Privato cittadino"
            edificio_pubblico_art11 = False
            suggerimento_categoria = CATEGORIE_CATASTALI_RESIDENZIALE
        elif tipo_edificio == "Terziario - Impresa/ETS economico":
            tipo_soggetto_label = "Impresa"
            edificio_pubblico_art11 = False
            suggerimento_categoria = CATEGORIE_CATASTALI_TERZIARIO
        else:  # PA / ETS non economico
            tipo_soggetto_label = "Pubblica Amministrazione"
            edificio_pubblico_art11 = True
            suggerimento_categoria = CATEGORIE_CATASTALI_TERZIARIO

        tipo_soggetto = TIPI_SOGGETTO.get(tipo_soggetto_label, "privato")

        # Salva in session state
        st.session_state.tipo_soggetto_principale = tipo_soggetto  # Usa tipo_soggetto mappato, non label
        st.session_state.tipo_soggetto_label = tipo_soggetto_label  # Salva anche label per display
        st.session_state.edificio_pubblico_art11 = edificio_pubblico_art11

        # Mostra info percentuale applicabile
        if edificio_pubblico_art11:
            st.success("✅ **Edificio PA**: Percentuale incentivo 100% per Titolo II")

        st.divider()

        # Categoria catastale (dettaglio)
        st.markdown("##### 📋 Dettagli Catastali")

        # Mostra solo categorie suggerite
        categorie_disponibili = ["Seleziona..."] + suggerimento_categoria
        categoria_catastale = st.selectbox(
            "Categoria catastale edificio",
            options=categorie_disponibili,
            index=0,
            key="sidebar_categoria_catastale",
            help="Categoria catastale come da visura catastale"
        )

        st.session_state.categoria_catastale = categoria_catastale if categoria_catastale != "Seleziona..." else None

        # Verifica vincoli terziario
        if categoria_catastale != "Seleziona...":
            edificio_terziario = is_terziario(categoria_catastale)

            # Se terziario + impresa -> mostra vincoli CT 3.0
            if edificio_terziario and tipo_soggetto_label == "Impresa":
                    st.warning("⚠️ **Vincoli specifici applicabili**")

                    # APE disponibili
                    ape_disp = st.checkbox(
                        "APE ante e post-operam disponibili",
                        value=st.session_state.ape_disponibili,
                        key="sidebar_ape_disp",
                        help="Obbligatori per verificare riduzione energia primaria"
                    )
                    st.session_state.ape_disponibili = ape_disp

                    if ape_disp:
                        riduzione_ep = st.number_input(
                            "Riduzione energia primaria (%)",
                            min_value=0.0,
                            max_value=100.0,
                            value=st.session_state.riduzione_ep_effettiva * 100,
                            step=0.1,
                            key="sidebar_riduzione_ep",
                            help="Da APE: (EP_ante - EP_post) / EP_ante × 100"
                        )
                        st.session_state.riduzione_ep_effettiva = riduzione_ep / 100
                    else:
                        st.session_state.riduzione_ep_effettiva = 0.0
                        st.caption("⚠️ APE necessarie per alcuni interventi")
            else:
                st.success("🏠 **Edificio RESIDENZIALE**")
                st.session_state.ape_disponibili = False
                st.session_state.riduzione_ep_effettiva = 0.0

        st.divider()

        # Selezione Regione e Provincia (determina automaticamente la zona climatica)
        st.markdown("##### 📍 Localizzazione")

        lista_regioni = get_lista_regioni()
        regione_selezionata = st.selectbox(
            "Regione",
            options=lista_regioni,
            index=lista_regioni.index("Lombardia") if "Lombardia" in lista_regioni else 0,
            key="sidebar_regione",
            help="Seleziona la regione dell'immobile"
        )

        # Province della regione selezionata
        province = get_province_by_regione(regione_selezionata)
        province_nomi = [f"{nome} ({sigla})" for sigla, nome in province]

        if province_nomi:
            provincia_display = st.selectbox(
                "Provincia",
                options=province_nomi,
                index=0,
                key="sidebar_provincia",
                help="Seleziona la provincia dell'immobile"
            )

            # Estrai la sigla dalla selezione (formato: "Nome (SIGLA)")
            provincia_sigla = provincia_display.split("(")[-1].rstrip(")")

            # Determina automaticamente la zona climatica
            zona_climatica_auto = get_zona_climatica(provincia_sigla)

            # Opzione per modifica manuale
            modifica_manuale = st.checkbox(
                "✏️ Modifica zona manualmente",
                value=False,
                key="sidebar_modifica_zona",
                help="Attiva per modificare manualmente la zona climatica (utile se il comune ha una zona diversa dalla provincia)"
            )

            if modifica_manuale:
                zona_climatica = st.selectbox(
                    "Zona climatica",
                    options=["A", "B", "C", "D", "E", "F"],
                    index=["A", "B", "C", "D", "E", "F"].index(zona_climatica_auto),
                    key="sidebar_zona_manuale",
                    help="Seleziona manualmente la zona climatica del comune"
                )
                st.warning(f"⚠️ Zona manuale: **{zona_climatica}** (automatica era: {zona_climatica_auto})")
            else:
                zona_climatica = zona_climatica_auto
                st.info(f"🌡️ **Zona Climatica: {zona_climatica}**")
        else:
            # Fallback se non ci sono province
            zona_climatica = "E"
            st.warning("⚠️ Province non trovate, uso zona E come default")

        st.divider()

        # Tipo abitazione
        tipo_abitazione_label = st.selectbox(
            "🏠 Tipo abitazione",
            options=list(TIPI_ABITAZIONE.keys()),
            index=0,
            key="sidebar_abitazione"
        )
        tipo_abitazione = TIPI_ABITAZIONE[tipo_abitazione_label]

        st.divider()

        # ===== GESTIONE PROGETTI CLIENTE =====
        st.subheader("📁 Gestione Progetto Cliente")

        # Campo nome cliente
        nome_cliente = st.text_input(
            "Nome Cliente/Progetto",
            value=st.session_state.get("nome_cliente_corrente", ""),
            placeholder="es. Mario Rossi - Via Roma 10, Milano",
            help="Identifica progetto per salvarlo e recuperarlo in seguito",
            key="input_nome_cliente"
        )

        # Salva in session state
        if nome_cliente:
            st.session_state.nome_cliente_corrente = nome_cliente

        # Note progetto
        note_progetto = st.text_area(
            "Note Progetto (opzionale)",
            value=st.session_state.get("note_progetto", ""),
            placeholder="es. Cliente interessato a PDC + Isolamento",
            height=80,
            key="input_note_progetto"
        )

        if note_progetto:
            st.session_state.note_progetto = note_progetto

        st.divider()

        # Parametri finanziari
        st.subheader("📊 Parametri NPV")
        anno = st.number_input("Anno spesa", min_value=2024, max_value=2030, value=2025, key="sidebar_anno")
        tasso_sconto = st.slider("Tasso di sconto (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.5, key="sidebar_tasso") / 100

        with st.expander("ℹ️ Come scegliere il tasso?"):
            st.markdown("""
            | Tasso | Quando usarlo |
            |-------|---------------|
            | **2-3%** | Profilo conservativo |
            | **4-5%** | Profilo medio |
            | **6-8%** | Alternative redditizie |
            """)

        st.divider()

        # Modalità calcolo
        st.subheader("⚙️ Modalità Calcolo")
        solo_ct = st.checkbox(
            "🎯 Solo Conto Termico 3.0",
            value=False,
            help="Calcola SOLO Conto Termico 3.0 senza confronto con Ecobonus (vale per tutti i TAB)",
            key="solo_conto_termico"
        )

        if solo_ct:
            st.info("✅ Modalità **Solo CT 3.0** attiva per tutti gli interventi")
        else:
            st.caption("Modalità standard: confronto CT 3.0 vs Ecobonus")

    # Estrai variabili da session_state per uso nei TAB
    solo_conto_termico = st.session_state.get("solo_conto_termico", False)
    tipo_soggetto_principale = st.session_state.get("tipo_soggetto_principale", "privato")
    edificio_pubblico_art11 = st.session_state.get("edificio_pubblico_art11", False)

    # ===========================================================================
    # TAB 1: CALCOLO SINGOLO - POMPE DI CALORE
    # ===========================================================================
    with tab_calcolo:
        st.header("🌡️ Pompa di Calore (III.B)")

        # Layout a due colonne: sinistra per input, destra per risultati
        col_input, col_spacer, col_result = st.columns([4, 0.5, 5])

        with col_input:
            st.subheader("📝 Dati Tecnici")

            # Tipo alimentazione
            alimentazione = st.radio(
                "Tipo alimentazione",
                options=["Elettrica", "Gas"],
                horizontal=True,
                help="PdC elettrica usa SCOP, PdC a gas usa SPER",
                key="pdc_alimentazione"
            )
            is_gas = alimentazione == "Gas"

            # Carica catalogo GSE
            catalogo_gse = load_catalogo_gse()

            # Checkbox per usare il catalogo
            usa_catalogo = st.checkbox(
                "🔍 Cerca nel Catalogo GSE",
                value=False,
                help="Seleziona una pompa di calore dal catalogo GSE per l'iter semplificato",
                key="pdc_usa_catalogo"
            )

            # Variabili per prodotto selezionato
            prodotto_catalogo = None
            iter_semplificato = False

            if usa_catalogo and catalogo_gse:
                # Selezione marca
                marche_disponibili = get_marche_catalogo(catalogo_gse)
                marca_selezionata = st.selectbox(
                    "Marca",
                    options=[""] + marche_disponibili,
                    index=0,
                    help="Seleziona la marca della pompa di calore",
                    key="pdc_marca"
                )

                if marca_selezionata:
                    # Ottieni modelli per marca
                    modelli_marca = get_modelli_per_marca(catalogo_gse, marca_selezionata)
                    opzioni_modelli = [""] + [
                        f"{m['modello']} ({m.get('dati_tecnici', {}).get('potenza_kw', m.get('potenza_kw', '?'))} kW, COP {m.get('dati_tecnici', {}).get('cop', m.get('cop', '?'))})"
                        for m in modelli_marca
                    ]

                    modello_idx = st.selectbox(
                        "Modello",
                        options=range(len(opzioni_modelli)),
                        format_func=lambda x: opzioni_modelli[x],
                        index=0,
                        help="Seleziona il modello",
                        key="pdc_modello"
                    )

                    if modello_idx > 0:
                        prodotto_catalogo = modelli_marca[modello_idx - 1]
                        iter_semplificato = True

                        # Mostra info prodotto selezionato
                        dati_tec = prodotto_catalogo.get('dati_tecnici', {})
                        potenza_cat = dati_tec.get('potenza_kw', prodotto_catalogo.get('potenza_kw', 'N/D'))
                        cop_cat = dati_tec.get('cop', prodotto_catalogo.get('cop', 'N/D'))
                        tipologia_cat = prodotto_catalogo.get('tipologia_scambio', prodotto_catalogo.get('tipologia', 'N/D'))
                        st.success(f"""
                        ✅ **ITER SEMPLIFICATO**

                        **{prodotto_catalogo.get('marca')} {prodotto_catalogo.get('modello')}**
                        - Tipologia: {tipologia_cat}
                        - Potenza: {potenza_cat} kW
                        - COP/SCOP: {cop_cat}
                        """)

            elif usa_catalogo and not catalogo_gse:
                st.warning("⚠️ Catalogo GSE non disponibile.")

            st.divider()

            # Selezione tipologia (manuale o da catalogo)
            if prodotto_catalogo:
                # Auto-fill da catalogo - usa tipologia_scambio se disponibile
                tipo_intervento = map_tipologia_catalogo_to_intervento(
                    prodotto_catalogo.get("tipologia_scambio", prodotto_catalogo.get("tipologia", ""))
                )
                # Trova la label corrispondente
                tipo_intervento_label = next(
                    (k for k, v in TIPI_INTERVENTO_ELETTRICO.items() if v == tipo_intervento),
                    list(TIPI_INTERVENTO_ELETTRICO.keys())[4]
                )
                st.info(f"📋 Tipologia (da catalogo): **{tipo_intervento_label}**")
            else:
                if is_gas:
                    tipo_intervento_label = st.selectbox(
                        "Tipologia pompa di calore",
                        options=list(TIPI_INTERVENTO_GAS.keys()),
                        help="Seleziona il tipo di PdC a gas",
                        key="pdc_tipologia_gas"
                    )
                    tipo_intervento = TIPI_INTERVENTO_GAS[tipo_intervento_label]
                else:
                    tipo_intervento_label = st.selectbox(
                        "Tipologia pompa di calore",
                        options=list(TIPI_INTERVENTO_ELETTRICO.keys()),
                        index=4,
                        help="Seleziona il tipo di pompa di calore",
                        key="pdc_tipologia_el"
                    )
                    tipo_intervento = TIPI_INTERVENTO_ELETTRICO[tipo_intervento_label]

            col1, col2 = st.columns(2)
            with col1:
                # Legge potenza dal nuovo formato (dati_tecnici) o vecchio formato
                potenza_da_catalogo = None
                if prodotto_catalogo:
                    dati_tec = prodotto_catalogo.get('dati_tecnici', {})
                    potenza_da_catalogo = dati_tec.get('potenza_kw', prodotto_catalogo.get('potenza_kw'))

                if potenza_da_catalogo:
                    potenza_kw = float(potenza_da_catalogo)
                    st.info(f"⚡ Potenza: **{potenza_kw} kW**")
                else:
                    potenza_kw = st.number_input("Potenza (kW)", min_value=1.0, max_value=2000.0, value=10.0, step=0.5, key="pdc_potenza")
            with col2:
                # SCOP sempre editabile dall'utente (il COP del catalogo non è lo SCOP)
                if is_gas:
                    scop = st.number_input("SPER dichiarato", min_value=0.5, max_value=3.0, value=1.4, step=0.01,
                                          help="Seasonal Primary Energy Ratio (da scheda tecnica)", key="pdc_sper")
                else:
                    scop = st.number_input("SCOP dichiarato", min_value=1.5, max_value=10.0, value=4.0, step=0.1,
                                          help="Seasonal COP (da scheda tecnica)", key="pdc_scop")

            col1, col2 = st.columns(2)
            with col1:
                gwp = st.selectbox("GWP Refrigerante", options=[">150", "<=150"], index=0, key="pdc_gwp")
            with col2:
                bassa_temp = st.checkbox("Bassa temperatura", value=False, key="pdc_bassa_temp")

            # Calcola valori minimi automaticamente
            eta_s_min = get_eta_s_min(tipo_intervento, gwp, bassa_temp, potenza_kw)
            if is_gas:
                scop_min = get_sper_min(tipo_intervento, bassa_temp)
                eff_label = "SPER"
            else:
                scop_min = get_scop_min(tipo_intervento, gwp, bassa_temp, potenza_kw)
                eff_label = "SCOP"

            # Box informativo minimi Ecodesign
            if iter_semplificato:
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; border-left: 4px solid #1976d2; margin: 10px 0;">
                    <strong>✅ Prodotto nel Catalogo GSE - Iter Semplificato</strong><br>
                    I requisiti Ecodesign sono già verificati dal GSE (Art. 14, comma 5)<br>
                    <small>Compila comunque η_s per il calcolo dell'incentivo</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #e8f4ea; padding: 10px; border-radius: 5px; border-left: 4px solid #2e7d32; margin: 10px 0;">
                    <strong>Requisiti minimi Ecodesign:</strong><br>
                    η_s min: <strong>{eta_s_min}%</strong> | {eff_label} min: <strong>{scop_min}</strong>
                </div>
                """, unsafe_allow_html=True)

            # Efficienza stagionale - sempre compilabile (serve per il calcolo incentivo)
            eta_s = st.number_input(
                "η_s dichiarata (%)", min_value=100.0, max_value=300.0, value=150.0, step=1.0,
                help=f"Efficienza energetica stagionale (da scheda tecnica). Minimo: {eta_s_min}%",
                key="pdc_eta_s"
            )

            # Warning se sotto i minimi (solo se NON iter semplificato)
            if not iter_semplificato:
                if eta_s < eta_s_min:
                    st.error(f"⛔ η_s ({eta_s}%) < minimo ({eta_s_min}%): NON AMMESSO")
                if scop < scop_min:
                    st.error(f"⛔ {eff_label} ({scop}) < minimo ({scop_min}): NON AMMESSO")

            st.divider()

            # Sezione economica - ORA NEL MAIN CONTENT
            st.subheader("💰 Spesa Intervento")
            spesa = st.number_input("Spesa totale (€)", min_value=1000.0, max_value=500000.0, value=15000.0, step=500.0, key="pdc_spesa")

            st.divider()

            # Flag Fotovoltaico Combinato
            st.subheader("🔆 Abbinamento FV Combinato")
            fv_combinato = st.checkbox(
                "Abbina impianto fotovoltaico (II.H)",
                value=st.session_state.get("pdc_fv_combinato", False),
                key="pdc_fv_combinato",
                help="Attiva per abbinare un impianto FV. I dati PdC saranno passati automaticamente al tab 'FV Combinato'"
            )

            if fv_combinato:
                st.info("""
                📋 **Fotovoltaico Combinato attivato**

                Dopo aver calcolato l'incentivo PdC:
                1. Vai al tab **🔆 FV Combinato**
                2. I dati della PdC saranno già compilati
                3. Inserisci i dati dell'impianto FV

                ⚠️ L'incentivo FV è limitato all'incentivo PdC calcolato.
                """)

            st.divider()

            # Pulsanti azione
            col1, col2 = st.columns(2)
            with col1:
                calcola = st.button("🔄 CALCOLA", type="primary", use_container_width=True, key="pdc_calcola")
            with col2:
                salva_scenario = st.button("💾 Salva Scenario", use_container_width=True, key="pdc_salva")

        with col_result:
            # Area risultati
            if calcola or salva_scenario:
                risultato = calcola_scenario(
                    nome=f"Calcolo {datetime.now().strftime('%H:%M')}",
                    tipo_intervento=tipo_intervento,
                    tipo_intervento_label=tipo_intervento_label,
                    potenza_kw=potenza_kw,
                    scop=scop,
                    eta_s=eta_s,
                    eta_s_min=eta_s_min,
                    scop_min=scop_min,
                    zona_climatica=zona_climatica,
                    gwp=gwp,
                    bassa_temp=bassa_temp,
                    spesa=spesa,
                    tipo_soggetto=tipo_soggetto,
                    tipo_abitazione=tipo_abitazione,
                    anno=anno,
                    tasso_sconto=tasso_sconto,
                    alimentazione="gas" if is_gas else "elettrica",
                    iter_semplificato=iter_semplificato
                )

                # Aggiungi info catalogo GSE al risultato
                risultato["iter_semplificato"] = iter_semplificato
                risultato["prodotto_catalogo"] = prodotto_catalogo

                st.session_state.ultimo_calcolo = risultato
                aggiungi_a_storico(risultato.copy())

                # Se FV Combinato attivato, salva i dati PdC per il tab FV
                if fv_combinato and risultato.get("ct_ammissibile"):
                    st.session_state.ultimo_calcolo_pdc = {
                        "tipo_intervento_label": tipo_intervento_label,
                        "tipo_intervento": tipo_intervento,
                        "potenza_kw": potenza_kw,
                        "scop": scop,
                        "ct_incentivo": risultato.get("ct_incentivo", 0),
                        "ct_ammissibile": risultato.get("ct_ammissibile", False),
                        "spesa": spesa,
                        "alimentazione": "gas" if is_gas else "elettrica",
                        "fv_combinato": True
                    }

                if salva_scenario and len(st.session_state.scenari) < 5:
                    nome_scenario = f"Scenario {len(st.session_state.scenari) + 1}"
                    risultato["nome"] = nome_scenario

                    # Includi dati FV se presenti e abbinamento attivo
                    if fv_combinato and st.session_state.get("ultimo_calcolo_fv"):
                        fv_data = st.session_state.ultimo_calcolo_fv
                        # Verifica che il FV sia abbinato alla stessa PdC
                        if abs(fv_data.get("pdc_abbinata", 0) - risultato.get("ct_incentivo", 0)) < 1:
                            risultato["fv_combinato"] = True  # Flag per il report
                            risultato["fv_potenza_kw"] = fv_data["potenza_fv_kw"]
                            risultato["fv_spesa"] = fv_data["spesa_fv"]
                            risultato["fv_capacita_accumulo_kwh"] = fv_data["capacita_accumulo_kwh"]
                            risultato["fv_spesa_accumulo"] = fv_data["spesa_accumulo"]
                            risultato["fv_produzione_stimata_kwh"] = fv_data["produzione_stimata_kwh"]
                            risultato["fv_incentivo_ct"] = fv_data["incentivo_ct"]
                            risultato["fv_bonus_ristrutt"] = fv_data["bonus_ristrutt"]
                            risultato["fv_registro_tecnologie"] = fv_data["registro_tecnologie"]
                            risultato["fv_npv_ct"] = fv_data["npv_ct"]
                            risultato["fv_npv_bonus"] = fv_data["npv_bonus"]
                            nome_scenario += " + FV"
                            risultato["nome"] = nome_scenario

                    st.session_state.scenari.append(risultato.copy())
                    st.success(f"✅ Scenario salvato: {nome_scenario}")
                elif salva_scenario:
                    st.warning("Hai raggiunto il massimo di 5 scenari")

                # Mostra risultati
                st.subheader("📊 Risultati")

                # Mostra eventuali vincoli terziario CT 3.0
                if risultato.get("vincolo_terziario_msg"):
                    if risultato["ct_ammissibile"]:
                        st.warning(f"⚠️ {risultato['vincolo_terziario_msg']}")
                    else:
                        st.error(f"🚫 {risultato['vincolo_terziario_msg']}")

                # Badge Iter Semplificato
                if risultato.get("iter_semplificato") and risultato.get("prodotto_catalogo"):
                    prod = risultato["prodotto_catalogo"]
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                                padding: 15px 20px; border-radius: 10px; margin-bottom: 20px;
                                color: white; text-align: center;">
                        <h4 style="margin: 0; color: white;">✅ ITER SEMPLIFICATO DISPONIBILE</h4>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em;">
                            Prodotto nel <strong>Catalogo GSE</strong>:
                            <strong>{prod.get('marca', '')} {prod.get('modello', '')}</strong>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                # Metriche principali
                if solo_conto_termico:
                    # Modalità SOLO CT 3.0
                    col1, col2 = st.columns(2)
                    with col1:
                        delta_ct = "Ammesso" if risultato["ct_ammissibile"] else "Non ammesso"
                        st.metric("Conto Termico 3.0", format_currency(risultato["ct_incentivo"]),
                                 delta=delta_ct, delta_color="normal" if risultato["ct_ammissibile"] else "inverse")
                    with col2:
                        st.metric("NPV Conto Termico", format_currency(risultato["npv_ct"]))
                else:
                    # Modalità confronto CT vs Ecobonus
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        delta_ct = "Ammesso" if risultato["ct_ammissibile"] else "Non ammesso"
                        st.metric("Conto Termico", format_currency(risultato["ct_incentivo"]),
                                 delta=delta_ct, delta_color="normal" if risultato["ct_ammissibile"] else "inverse")
                    with col2:
                        delta_eco = "Ammesso" if risultato["eco_ammissibile"] else "Non ammesso"
                        st.metric("Ecobonus", format_currency(risultato["eco_detrazione"]),
                                 delta=delta_eco, delta_color="normal" if risultato["eco_ammissibile"] else "inverse")
                    with col3:
                        st.metric("NPV Conto Termico", format_currency(risultato["npv_ct"]))
                    with col4:
                        st.metric("NPV Ecobonus", format_currency(risultato["npv_eco"]))

                # Grafico
                if not solo_conto_termico and (risultato["ct_incentivo"] > 0 or risultato["eco_detrazione"] > 0):
                    fig = create_comparison_chart(
                        risultato["ct_incentivo"], risultato["eco_detrazione"],
                        risultato["npv_ct"], risultato["npv_eco"]
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Raccomandazione COMPLETA
                st.divider()
                st.subheader("💡 Raccomandazione")

                # Calcola % sulla spesa
                ct_pct = (risultato["ct_incentivo"] / risultato["spesa"] * 100) if risultato["spesa"] > 0 else 0
                eco_pct = (risultato["eco_detrazione"] / risultato["spesa"] * 100) if risultato["spesa"] > 0 else 0
                ct_annualita = risultato.get("ct_annualita", 2)

                if solo_conto_termico:
                    # Modalità SOLO CT 3.0 - Mostra solo risultato CT
                    if risultato["ct_ammissibile"]:
                        nota_pct = f" (max 65%)" if ct_pct >= 64.9 else ""
                        st.success(f"""
                        **✅ CONTO TERMICO 3.0**

                        Incentivo: **{format_currency(risultato["ct_incentivo"])}** ({ct_pct:.1f}% della spesa{nota_pct})

                        Erogazione: **bonifico diretto GSE** in {ct_annualita} {"anno" if ct_annualita == 1 else "anni"}

                        NPV: **{format_currency(risultato["npv_ct"])}**
                        """)
                    else:
                        st.error("❌ Intervento NON ammissibile al Conto Termico 3.0")

                elif risultato["ct_ammissibile"] and risultato["eco_ammissibile"]:
                    # Entrambi ammissibili - confronto completo
                    col_rec1, col_rec2 = st.columns(2)

                    with col_rec1:
                        # Indica se applicato massimale 65%
                        nota_pct = f" (max 65%)" if ct_pct >= 64.9 else ""
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                                    padding: 20px; border-radius: 10px; color: white;">
                            <h4 style="margin: 0 0 10px 0; color: white;">🏦 Conto Termico 3.0</h4>
                            <p style="font-size: 1.5em; margin: 5px 0; font-weight: bold;">{format_currency(risultato["ct_incentivo"])}</p>
                            <p style="margin: 5px 0;">📊 <strong>{ct_pct:.1f}%</strong> della spesa{nota_pct}</p>
                            <p style="margin: 5px 0;">⏱️ Erogazione: <strong>{ct_annualita} {"anno" if ct_annualita == 1 else "anni"}</strong></p>
                            <p style="margin: 5px 0;">💰 <strong>Bonifico diretto GSE</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_rec2:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
                                    padding: 20px; border-radius: 10px; color: white;">
                            <h4 style="margin: 0 0 10px 0; color: white;">📋 Ecobonus</h4>
                            <p style="font-size: 1.5em; margin: 5px 0; font-weight: bold;">{format_currency(risultato["eco_detrazione"])}</p>
                            <p style="margin: 5px 0;">📊 <strong>{eco_pct:.1f}%</strong> della spesa</p>
                            <p style="margin: 5px 0;">⏱️ Erogazione: <strong>10 anni</strong></p>
                            <p style="margin: 5px 0;">📝 <strong>Detrazione fiscale IRPEF</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

                    # Logica raccomandazione
                    st.markdown("---")
                    if risultato["ct_incentivo"] > 0:
                        premio_liquidita = 1.15 if ct_annualita <= 2 else 1.05
                        ct_valore_reale = risultato["ct_incentivo"] * premio_liquidita

                        if ct_valore_reale >= risultato["eco_detrazione"] * 0.85:
                            st.success(f"""
                            **✅ CONSIGLIATO: CONTO TERMICO 3.0**

                            | Aspetto | Conto Termico | Ecobonus |
                            |---------|---------------|----------|
                            | **Importo** | {format_currency(risultato["ct_incentivo"])} ({ct_pct:.1f}%) | {format_currency(risultato["eco_detrazione"])} ({eco_pct:.1f}%) |
                            | **Liquidità** | Bonifico in {ct_annualita} {"anno" if ct_annualita == 1 else "anni"} | Detrazione in 10 anni |
                            | **Certezza** | Pagamento garantito GSE | Richiede capienza IRPEF |
                            | **Rischio** | Nessuno | Perdita quota se IRPEF insufficiente |

                            💡 *Con {format_currency(risultato["ct_incentivo"])} oggi puoi investire o ridurre il finanziamento.*
                            """)
                        else:
                            diff_pct = ((risultato["eco_detrazione"] - risultato["ct_incentivo"]) / risultato["ct_incentivo"] * 100) if risultato["ct_incentivo"] > 0 else 0
                            st.info(f"""
                            **📊 ECOBONUS ha valore nominale maggiore (+{diff_pct:.0f}%)**

                            | Aspetto | Conto Termico | Ecobonus |
                            |---------|---------------|----------|
                            | **Importo** | {format_currency(risultato["ct_incentivo"])} ({ct_pct:.1f}%) | {format_currency(risultato["eco_detrazione"])} ({eco_pct:.1f}%) |
                            | **Erogazione** | {ct_annualita} {"anno" if ct_annualita == 1 else "anni"} | 10 anni |
                            | **Rata annua Eco** | - | {format_currency(risultato["eco_detrazione"]/10)}/anno |

                            ⚠️ *L'Ecobonus richiede capienza IRPEF di almeno {format_currency(risultato["eco_detrazione"]/10)}/anno per 10 anni.*

                            💡 *Se non sei sicuro della tua capienza fiscale futura, il Conto Termico è più sicuro.*
                            """)

                elif risultato["ct_ammissibile"]:
                    nota_pct = f" (max 65%)" if ct_pct >= 64.9 else ""
                    st.success(f"""
                    **✅ CONTO TERMICO 3.0** è l'unica opzione disponibile.

                    Incentivo: **{format_currency(risultato["ct_incentivo"])}** ({ct_pct:.1f}% della spesa{nota_pct})

                    Erogazione: **bonifico diretto GSE** in {ct_annualita} {"anno" if ct_annualita == 1 else "anni"}
                    """)
                elif risultato["eco_ammissibile"]:
                    st.info(f"""
                    **📋 ECOBONUS** è l'unica opzione disponibile.

                    Detrazione: **{format_currency(risultato["eco_detrazione"])}** ({eco_pct:.1f}% della spesa)

                    Erogazione: **detrazione IRPEF** in 10 anni ({format_currency(risultato["eco_detrazione"]/10)}/anno)

                    ⚠️ *Verifica di avere capienza fiscale sufficiente per 10 anni.*
                    """)

                # Dettagli calcolo CT con LEGENDA
                with st.expander("📋 Dettagli Calcolo CT"):
                    if risultato["risultato_ct"] and risultato["risultato_ct"]["status"] == "OK":
                        calcoli = risultato["risultato_ct"]["calcoli_intermedi"]

                        st.markdown("**Parametri del calcolo:**")
                        st.write(f"• **Quf** = {calcoli['Quf']} h (ore equivalenti di funzionamento)")
                        st.write(f"• **Ci** = {calcoli['Ci']} €/kWht (coefficiente di valorizzazione)")
                        st.write(f"• **kp** = {calcoli['kp']:.4f} (fattore correttivo prestazionale)")
                        st.write(f"• **Ei** = {calcoli['Ei']:,.0f} kWht (energia incentivata)")
                        st.write(f"• **Ia** = {format_currency(calcoli['Ia'])} (incentivo annuo)")

                        st.markdown("---")
                        st.markdown("**Legenda:**")
                        st.caption("""
                        - **Quf**: Ore equivalenti di utilizzo dell'impianto (dipende dalla zona climatica)
                        - **Ci**: Coefficiente in €/kWht (dipende da tipologia e potenza)
                        - **kp**: Fattore che premia le prestazioni superiori ai minimi (kp = SCOP/SCOP_min × η_s/η_s_min)
                        - **Ei**: Energia termica incentivata = Potenza × Quf
                        - **Ia**: Incentivo annuo = Ci × Ei × kp (max 65% della spesa)
                        """)
                    else:
                        st.warning("CT non calcolato - requisiti non soddisfatti")
                        for err in risultato["validazione_ct"].errori_bloccanti:
                            st.error(f"• {err}")

            else:
                # Stato iniziale
                st.info("👈 Inserisci i dati tecnici e la spesa, poi clicca **CALCOLA**")

        # =======================================================================
        # SEZIONE AGGIUNTIVA: INFRASTRUTTURA RICARICA VEICOLI ELETTRICI (II.G)
        # =======================================================================
        st.markdown("---")
        st.markdown("### 🔌 Abbina Infrastruttura Ricarica Veicoli Elettrici (Intervento II.G)")

        with st.expander("ℹ️ **Cos'è l'intervento II.G?**", expanded=False):
            st.markdown("""
            L'intervento II.G consente di installare **infrastrutture di ricarica per veicoli elettrici**
            presso l'edificio, le sue pertinenze o parcheggi adiacenti, **congiuntamente**
            all'installazione della pompa di calore.

            **Caratteristiche principali:**
            - 📊 Incentivo: **30%** delle spese sostenute (100% per PA su edifici pubblici)
            - 📉 **Limite importante**: L'incentivo ricarica NON può superare l'incentivo della pompa di calore
            - ⚡ Potenza minima: **7.4 kW**
            - 🤖 Dispositivi **SMART** obbligatori
            - 🔄 Modalità ricarica: **Modo 3** o **Modo 4** (CEI EN 61851)
            - 🏢 Può essere **privata** o **aperta al pubblico** (con registrazione PUN)

            **Requisito fondamentale:** Questo intervento è ammissibile SOLO se abbinato
            all'installazione di una pompa di calore elettrica (III.A).
            """)

        aggiungi_ricarica = st.checkbox(
            "🔌 Aggiungi installazione infrastruttura ricarica veicoli elettrici",
            value=False,
            key="pdc_aggiungi_ricarica",
            help="Abbina l'intervento II.G (ricarica VE) all'installazione della pompa di calore"
        )

        if aggiungi_ricarica:
            st.info("✅ Intervento II.G abilitato - Compila i dati sotto per calcolare l'incentivo combinato")

            # Import moduli ricarica
            from modules.validator_ricarica_veicoli import valida_requisiti_ricarica_veicoli
            from modules.calculator_ricarica_veicoli import calculate_ev_charging_incentive

            st.subheader("📋 Dati Infrastruttura Ricarica")

            col_ric1, col_ric2 = st.columns(2)

            with col_ric1:
                tipo_infrastruttura_ric = st.selectbox(
                    "Tipologia infrastruttura",
                    options=[
                        "standard_monofase",
                        "standard_trifase",
                        "potenza_media",
                        "potenza_alta_100",
                        "potenza_alta_over100"
                    ],
                    format_func=lambda x: {
                        "standard_monofase": "⚡ Standard Monofase (7.4-22 kW) - Max 2.400 €/punto",
                        "standard_trifase": "⚡⚡⚡ Standard Trifase (7.4-22 kW) - Max 8.400 €/punto",
                        "potenza_media": "🔋 Potenza Media (22-50 kW) - Max 1.200 €/kW",
                        "potenza_alta_100": "🔋🔋 Potenza Alta ≤100 kW - Max 60.000 €/infr.",
                        "potenza_alta_over100": "🔋🔋🔋 Potenza Alta >100 kW - Max 110.000 €/infr."
                    }[x],
                    key="ric_tipo_infr",
                    help="Seleziona la tipologia in base alla potenza installata"
                )

                potenza_ric_kw = st.number_input(
                    "Potenza installata (kW)",
                    min_value=7.4,
                    value=7.4,
                    step=0.1,
                    key="ric_potenza",
                    help="Potenza minima obbligatoria: 7.4 kW"
                )

                if potenza_ric_kw < 7.4:
                    st.error("❌ Potenza minima: 7.4 kW")
                else:
                    st.success("✅ Potenza conforme")

            with col_ric2:
                numero_punti_ric = st.number_input(
                    "Numero punti di ricarica",
                    min_value=1,
                    value=1,
                    step=1,
                    key="ric_num_punti",
                    help="Numero di punti di ricarica da installare"
                )

                spesa_ric = st.number_input(
                    "Spesa sostenuta ricarica (€)",
                    min_value=0.0,
                    value=2400.0,
                    step=100.0,
                    key="ric_spesa",
                    help="Spesa totale per l'infrastruttura di ricarica"
                )

            st.markdown("##### ⚙️ Requisiti Tecnici")

            col_ric3, col_ric4 = st.columns(2)

            with col_ric3:
                dispositivi_smart_ric = st.checkbox(
                    "Dispositivi SMART (OBBLIGATORIO)",
                    value=True,
                    key="ric_smart",
                    help="I dispositivi devono misurare, registrare e trasmettere dati, e ricevere comandi esterni"
                )

                modalita_ric = st.selectbox(
                    "Modalità ricarica (CEI EN 61851)",
                    options=["modo_3", "modo_4"],
                    format_func=lambda x: "Modo 3" if x == "modo_3" else "Modo 4",
                    key="ric_modalita",
                    help="Modalità di ricarica secondo norma CEI EN 61851"
                )

                ha_dich_conf_ric = st.checkbox(
                    "Dichiarazione conformità DM 37/2008 (OBBLIGATORIO)",
                    value=True,
                    key="ric_dich_conf"
                )

            with col_ric4:
                ricarica_pubblica_ric = st.checkbox(
                    "Ricarica aperta al pubblico",
                    value=False,
                    key="ric_pubblica",
                    help="Infrastruttura accessibile anche a utenti esterni"
                )

                if ricarica_pubblica_ric:
                    registrata_pun_ric = st.checkbox(
                        "Registrata su PUN (OBBLIGATORIO per pubblica)",
                        value=False,
                        key="ric_pun",
                        help="Piattaforma Unica Nazionale per ricarica pubblica"
                    )
                else:
                    registrata_pun_ric = False

                utenza_bt_mt_ric = st.checkbox(
                    "Utenza bassa/media tensione (OBBLIGATORIO)",
                    value=True,
                    key="ric_utenza",
                    help="Il soggetto responsabile deve avere utenze in bassa o media tensione"
                )

            st.markdown("##### 📍 Ubicazione")

            col_ric5, col_ric6 = st.columns(2)

            with col_ric5:
                presso_edificio_ric = st.checkbox(
                    "Presso edificio",
                    value=True,
                    key="ric_presso_edificio"
                )

                presso_pertinenza_ric = st.checkbox(
                    "Presso pertinenza edificio",
                    value=False,
                    key="ric_presso_pertinenza",
                    help="Box, tettoie, posti auto assegnati/condominiali"
                )

            with col_ric6:
                presso_parcheggio_ric = st.checkbox(
                    "Presso parcheggio adiacente",
                    value=False,
                    key="ric_presso_parcheggio"
                )

                if presso_pertinenza_ric or presso_parcheggio_ric:
                    ha_visura_ric = st.checkbox(
                        "Visura catastale pertinenza (OBBLIGATORIO)",
                        value=False,
                        key="ric_visura",
                        help="Documentazione che dimostri la pertinenza funzionale all'edificio"
                    )
                else:
                    ha_visura_ric = None

            # Pulsante validazione e calcolo combinato
            if st.button("🔍 Valida e Calcola Incentivo Combinato (PdC + Ricarica)", type="primary", use_container_width=True, key="btn_calc_combinato"):

                # Prima valida la ricarica
                validazione_ric = valida_requisiti_ricarica_veicoli(
                    abbinato_a_pompa_calore=True,  # Sempre True se siamo qui
                    numero_punti_ricarica=numero_punti_ric,
                    spesa_sostenuta=spesa_ric,
                    tipo_infrastruttura=tipo_infrastruttura_ric,
                    potenza_installata_kw=potenza_ric_kw,
                    dispositivi_smart=dispositivi_smart_ric,
                    modalita_ricarica=modalita_ric,
                    ha_dichiarazione_conformita=ha_dich_conf_ric,
                    ricarica_pubblica=ricarica_pubblica_ric,
                    registrata_pun=registrata_pun_ric,
                    presso_edificio=presso_edificio_ric,
                    presso_pertinenza=presso_pertinenza_ric,
                    presso_parcheggio_adiacente=presso_parcheggio_ric,
                    ha_visura_catastale_pertinenza=ha_visura_ric,
                    utenza_bassa_media_tensione=utenza_bt_mt_ric,
                    tipo_soggetto=tipo_soggetto,
                    edificio_terziario=edificio_terziario if tipo_soggetto in ["impresa", "ets_economico"] else False,
                    riduzione_energia_primaria_pct=riduzione_energia_primaria if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario else 0.0,
                    ha_ape_ante_post=ha_ape_ante_post if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario else False,
                    tipo_edificio="residenziale"  # Default
                )

                st.subheader("✅ Validazione Infrastruttura Ricarica")

                if validazione_ric["ammissibile"]:
                    st.success(f"✅ **INTERVENTO II.G AMMISSIBILE** - Punteggio: {validazione_ric['punteggio']}/100")
                else:
                    st.error("❌ **INTERVENTO II.G NON AMMISSIBILE**")

                if validazione_ric["errori"]:
                    with st.expander("🚫 Errori Bloccanti", expanded=True):
                        for err in validazione_ric["errori"]:
                            st.error(f"• {err}")

                if validazione_ric["warnings"]:
                    with st.expander("⚠️ Attenzioni", expanded=False):
                        for warn in validazione_ric["warnings"]:
                            st.warning(f"• {warn}")

                if validazione_ric["suggerimenti"]:
                    with st.expander("💡 Suggerimenti", expanded=False):
                        for sug in validazione_ric["suggerimenti"]:
                            st.info(f"• {sug}")

                # Calcola incentivo ricarica se ammissibile E se hai già calcolato la PdC
                if validazione_ric["ammissibile"]:
                    st.markdown("---")
                    st.subheader("💰 Calcolo Incentivo Combinato")

                    # Verifica se hai già i dati della PdC calcolati
                    # Nota: in un'implementazione reale, dovresti salvare i risultati PdC in session_state
                    # Per ora usiamo placeholder - l'utente deve prima calcolare la PdC

                    st.warning(
                        "⚠️ **Per calcolare l'incentivo ricarica, devi prima calcolare l'incentivo della Pompa di Calore** "
                        "(clicca su 'CALCOLA' nella sezione sopra). L'incentivo ricarica è limitato dall'incentivo PdC."
                    )

                    st.info(
                        "💡 **Simulazione**: Inserisci l'incentivo PdC calcolato sopra per vedere l'incentivo combinato"
                    )

                    incentivo_pdc_input = st.number_input(
                        "Incentivo Pompa di Calore (€)",
                        min_value=0.0,
                        value=5000.0,
                        step=100.0,
                        key="ric_incentivo_pdc_input",
                        help="Inserisci l'incentivo totale della pompa di calore calcolato sopra"
                    )

                    potenza_pdc_input = st.number_input(
                        "Potenza Pompa di Calore (kW)",
                        min_value=0.0,
                        value=12.0,
                        step=0.1,
                        key="ric_potenza_pdc_input",
                        help="Inserisci la potenza della pompa di calore per determinare gli anni di erogazione"
                    )

                    if incentivo_pdc_input > 0:
                        # Calcola incentivo ricarica
                        risultato_ric = calculate_ev_charging_incentive(
                            tipo_infrastruttura=tipo_infrastruttura_ric,
                            numero_punti_ricarica=numero_punti_ric,
                            potenza_installata_kw=potenza_ric_kw,
                            spesa_sostenuta=spesa_ric,
                            incentivo_pompa_calore=incentivo_pdc_input,
                            potenza_pdc_kw=potenza_pdc_input,
                            tipo_soggetto=tipo_soggetto,
                            tipo_edificio="residenziale",
                            tasso_sconto=tasso_sconto
                        )

                        # Mostra risultati
                        col_res1, col_res2, col_res3 = st.columns(3)

                        with col_res1:
                            st.metric(
                                "💚 Incentivo PdC",
                                f"€ {incentivo_pdc_input:,.0f}",
                                help="Incentivo pompa di calore (III.A)"
                            )

                        with col_res2:
                            st.metric(
                                "🔌 Incentivo Ricarica",
                                f"€ {risultato_ric['incentivo_totale']:,.0f}",
                                help="Incentivo infrastruttura ricarica (II.G)"
                            )

                        with col_res3:
                            totale_combinato = incentivo_pdc_input + risultato_ric['incentivo_totale']
                            st.metric(
                                "💰 TOTALE COMBINATO",
                                f"€ {totale_combinato:,.0f}",
                                delta=f"+{risultato_ric['incentivo_totale']:,.0f} €",
                                help="Incentivo totale PdC + Ricarica"
                            )

                        st.success(
                            f"✅ **Incentivo combinato**: € {totale_combinato:,.2f} "
                            f"in {risultato_ric['anni_erogazione']} {'anno' if risultato_ric['anni_erogazione'] == 1 else 'anni'}"
                        )

                        # Dettagli ricarica
                        with st.expander("📊 Dettagli Calcolo Ricarica", expanded=False):
                            det_ric = risultato_ric['dettagli']
                            st.write(f"**Tipologia**: {det_ric['tipo_infrastruttura']}")
                            st.write(f"**Numero punti**: {det_ric['numero_punti_ricarica']}")
                            st.write(f"**Potenza installata**: {det_ric['potenza_installata_kw']:.1f} kW")
                            st.write(f"**Spesa sostenuta**: € {det_ric['spesa_sostenuta']:,.2f}")
                            st.write(f"**Spesa max ammissibile**: € {det_ric['spesa_max_ammissibile']:,.2f}")
                            st.write(f"**{det_ric['nota_costo']}**")
                            st.write(f"**{det_ric['nota_cap_spesa']}**")
                            st.write(f"**Percentuale incentivo**: {det_ric['percentuale']:.0%} ({det_ric['tipo_percentuale']})")
                            st.write(f"**Incentivo calcolato (30%)**: € {det_ric['incentivo_calcolato']:,.2f}")
                            st.warning(f"⚠️ **{det_ric['nota_limite_pdc']}**")
                            st.write(f"**{det_ric['nota_rateazione']}**")
                            if risultato_ric['anni_erogazione'] > 1:
                                st.write(f"**Rata annuale**: € {risultato_ric['rata_annuale']:,.2f}")
                                st.write(f"**NPV (3% sconto)**: € {risultato_ric['npv']:,.2f}")

    # ===========================================================================
    # TAB 2: SOLARE TERMICO (III.D)
    # ===========================================================================
    with tab_solare:
        st.header("☀️ Solare Termico (III.D)")

        # Layout a due colonne come il tab PdC
        col_input_sol, col_spacer_sol, col_result_sol = st.columns([4, 0.5, 5])

        with col_input_sol:
            st.subheader("📝 Dati Tecnici")

            # Carica catalogo GSE Solare Termico
            catalogo_st = load_catalogo_solare_termico()

            # Checkbox per usare il catalogo
            usa_catalogo_st = st.checkbox(
                "🔍 Cerca nel Catalogo GSE",
                value=False,
                help="Seleziona un collettore dal catalogo GSE per l'iter semplificato",
                key="solar_usa_catalogo"
            )

            # Variabili per prodotto selezionato
            prodotto_catalogo_st = None
            iter_semplificato_st = False

            if usa_catalogo_st and catalogo_st:
                # Selezione marca
                marche_st = get_marche_catalogo_st(catalogo_st)
                marca_st = st.selectbox(
                    "Marca",
                    options=[""] + marche_st,
                    index=0,
                    help="Seleziona la marca del collettore solare",
                    key="solar_marca"
                )

                if marca_st:
                    # Ottieni modelli per marca
                    modelli_st = get_modelli_per_marca_st(catalogo_st, marca_st)
                    opzioni_modelli_st = [""] + [
                        f"{m['modello']} ({m.get('dati_tecnici', {}).get('area_lorda_mq', m.get('superficie_lorda_mq', '?'))} m², "
                        f"Qu {m.get('dati_tecnici', {}).get('producibilita_qualificazione_kwh_mq', m.get('producibilita_kwh_mq', '?'))} kWh/m²)"
                        for m in modelli_st
                    ]

                    modello_st_idx = st.selectbox(
                        "Modello",
                        options=range(len(opzioni_modelli_st)),
                        format_func=lambda x: opzioni_modelli_st[x],
                        index=0,
                        help="Seleziona il modello",
                        key="solar_modello"
                    )

                    if modello_st_idx > 0:
                        prodotto_catalogo_st = modelli_st[modello_st_idx - 1]
                        iter_semplificato_st = True

                        # Compatibilità con entrambi i formati (vecchio e nuovo)
                        dati_tec = prodotto_catalogo_st.get('dati_tecnici', {})
                        superficie_catalogo = dati_tec.get('area_lorda_mq', prodotto_catalogo_st.get('superficie_lorda_mq', 0))
                        producibilita_catalogo = dati_tec.get('producibilita_qualificazione_kwh_mq', prodotto_catalogo_st.get('producibilita_kwh_mq', 'N/D'))

                        # Mostra info prodotto selezionato con badge iter semplificato
                        st.success(f"""
                        ✅ **ITER SEMPLIFICATO** (Prodotto a Catalogo GSE)

                        **{prodotto_catalogo_st.get('marca')} {prodotto_catalogo_st.get('modello')}**
                        - Tipologia: {prodotto_catalogo_st.get('tipologia_collettore', 'N/D')}
                        - Superficie lorda: {superficie_catalogo} m²
                        - Producibilità: {producibilita_catalogo} kWh/m²
                        - Utilizzo: {prodotto_catalogo_st.get('utilizzo', 'N/D')}
                        """)

                        # Vantaggi iter semplificato
                        if superficie_catalogo <= 50:
                            with st.expander("ℹ️ Vantaggi Iter Semplificato (sup. ≤ 50 m²)", expanded=False):
                                st.markdown("""
                                **Essendo il prodotto presente nel Catalogo GSE con superficie ≤ 50 m²:**

                                1. **Asseverazione NON obbligatoria** (par. 6.5 Regole Applicative)
                                2. **Dati tecnici pre-compilati** automaticamente dal Portaltermico
                                3. **Solar Keymark già in possesso GSE** - non serve allegarlo
                                4. **Certificazione produttore già verificata** dal GSE
                                5. **Iter più veloce** - meno documentazione da caricare

                                *Rif: D.M. 07/08/2025 - Regole Applicative CT 3.0, par. 6.5 e 9.12.4*
                                """)
                        else:
                            with st.expander("ℹ️ Info Catalogo GSE", expanded=False):
                                st.markdown("""
                                **Prodotto presente nel Catalogo GSE:**

                                - **Dati tecnici pre-compilati** automaticamente dal Portaltermico
                                - **Solar Keymark già in possesso GSE** - non serve allegarlo
                                - **Certificazione produttore già verificata** dal GSE

                                ⚠️ Con superficie > 50 m², l'asseverazione rimane obbligatoria.

                                *Rif: D.M. 07/08/2025 - Regole Applicative CT 3.0, par. 9.12.4*
                                """)

            elif usa_catalogo_st and not catalogo_st:
                st.warning("⚠️ Catalogo GSE Solare Termico non disponibile.")

            st.divider()

            # Tipologia impianto (sempre visibile per solar cooling)
            tipologia_solare_label = st.selectbox(
                "Tipologia impianto",
                options=list(TIPOLOGIE_SOLARE.values()),
                index=0,
                key="solar_tipologia",
                help="Determina il coefficiente Ci"
            )
            tipologia_solare = [k for k, v in TIPOLOGIE_SOLARE.items() if v == tipologia_solare_label][0]

            # Tipo collettore (da catalogo o manuale)
            if prodotto_catalogo_st:
                tipo_collettore = map_tipologia_catalogo_st(prodotto_catalogo_st.get("tipologia", ""))
                tipo_collettore_label = TIPI_COLLETTORE.get(tipo_collettore, "Collettori Piani")
                st.info(f"📋 Tipo collettore (da catalogo): **{tipo_collettore_label}**")
            else:
                tipo_collettore_label = st.selectbox(
                    "Tipo collettore",
                    options=list(TIPI_COLLETTORE.values()),
                    index=0,
                    key="solar_collettore",
                    help="Determina producibilità minima richiesta"
                )
                tipo_collettore = [k for k, v in TIPI_COLLETTORE.items() if v == tipo_collettore_label][0]

            st.divider()

            # Dati superficie (da catalogo o manuale)
            col1, col2 = st.columns(2)
            with col1:
                if prodotto_catalogo_st:
                    n_moduli = st.number_input(
                        "Numero moduli",
                        min_value=1, max_value=500, value=prodotto_catalogo_st.get("n_moduli", 1),
                        key="solar_n_moduli",
                        help="Numero di pannelli/collettori"
                    )
                else:
                    n_moduli = st.number_input(
                        "Numero moduli",
                        min_value=1, max_value=500, value=4,
                        key="solar_n_moduli",
                        help="Numero di pannelli/collettori"
                    )
            with col2:
                if prodotto_catalogo_st:
                    # Compatibilità con entrambi i formati
                    dati_tec_st = prodotto_catalogo_st.get('dati_tecnici', {})
                    area_modulo = dati_tec_st.get("area_lorda_mq", prodotto_catalogo_st.get("superficie_lorda_mq", 2.0))
                    st.info(f"📋 Area modulo (da catalogo): **{area_modulo} m²**")
                else:
                    area_modulo = st.number_input(
                        "Area modulo (m²)",
                        min_value=0.5, max_value=20.0, value=2.0, step=0.1,
                        key="solar_area_modulo",
                        help="Area lorda singolo modulo"
                    )

            superficie_totale = n_moduli * area_modulo
            st.info(f"**Superficie totale:** {superficie_totale:.1f} m²")

            if superficie_totale > 2500:
                st.error("⛔ Superficie max: 2500 m²")

            st.divider()

            # Producibilità (da catalogo o manuale)
            st.markdown("##### Dati Solar Keymark")

            if prodotto_catalogo_st:
                # Compatibilità con entrambi i formati
                dati_tec_st = prodotto_catalogo_st.get('dati_tecnici', {})
                qu_calcolato = dati_tec_st.get("producibilita_qualificazione_kwh_mq", prodotto_catalogo_st.get("producibilita_kwh_mq", 0))
                if qu_calcolato:
                    # Da catalogo
                    energia_modulo = qu_calcolato * area_modulo
                    st.info(f"📋 Producibilità da catalogo: **{qu_calcolato:.0f} kWh/m²** → {energia_modulo:.0f} kWht/modulo")
                    usa_stima = False
                else:
                    usa_stima = True
            else:
                qu_calcolato = 0
                usa_stima = True

            if usa_stima:
                usa_stima_checkbox = st.checkbox(
                    "Usa stima producibilità",
                    value=True,
                    key="solar_usa_stima",
                    help="Stima automatica se non hai i dati"
                )

                if usa_stima_checkbox:
                    qu_tipici = {"piano": 400, "sottovuoto": 500, "concentrazione": 650, "factory_made": 450}
                    qu_stimato = qu_tipici.get(tipo_collettore, 400)
                    energia_modulo = qu_stimato * area_modulo
                    st.info(f"Stima: {energia_modulo:.0f} kWht/anno (Qu ~ {qu_stimato} kWht/m²)")
                else:
                    energia_modulo = st.number_input(
                        "Energia modulo (kWht/anno)",
                        min_value=100.0, max_value=5000.0, value=800.0, step=50.0,
                        key="solar_energia",
                        help="Qcol da Solar Keymark"
                    )

            qu_calcolato = energia_modulo / area_modulo if area_modulo > 0 else 0
            prod_minima = {"piano": 300, "sottovuoto": 400, "concentrazione": 550, "factory_made": 400}
            min_richiesto = prod_minima.get(tipo_collettore, 300)

            if qu_calcolato > min_richiesto:
                st.success(f"✅ Qu = {qu_calcolato:.0f} kWht/m² > {min_richiesto} (min)")
            else:
                st.error(f"⛔ Qu = {qu_calcolato:.0f} < {min_richiesto} (min)")

            # Solar cooling
            potenza_frigorifera = 0.0
            if tipologia_solare == "solar_cooling":
                st.divider()
                st.markdown("##### ❄️ Solar Cooling")
                potenza_frigorifera = st.number_input(
                    "Potenza frigorifera (kW)",
                    min_value=1.0, max_value=500.0, value=10.0,
                    key="solar_frigorifera"
                )
                rapporto_sc = superficie_totale / potenza_frigorifera if potenza_frigorifera > 0 else 0
                if 2.0 < rapporto_sc <= 2.75:
                    st.success(f"✅ Rapporto m²/kWf = {rapporto_sc:.2f}")
                else:
                    st.error(f"⛔ Rapporto {rapporto_sc:.2f} fuori range 2.0-2.75")

            st.divider()

            # Spesa - nel main content
            st.subheader("💰 Spesa Intervento")
            spesa_solare = st.number_input(
                "Spesa totale (€)",
                min_value=500.0, max_value=500000.0, value=6000.0, step=500.0,
                key="solar_spesa"
            )

            st.divider()

            # Pulsante calcola
            calcola_solare = st.button("🔄 CALCOLA SOLARE", type="primary", use_container_width=True, key="btn_solare")

        with col_result_sol:
            # Area risultati solare
            if calcola_solare:
                # Validazione
                validazione_solare = valida_requisiti_solare_termico(
                    tipo_collettore=tipo_collettore,
                    superficie_lorda_m2=superficie_totale,
                    producibilita_qu=qu_calcolato,
                    con_solar_cooling=(tipologia_solare == "solar_cooling"),
                    potenza_frigorifera_kw=potenza_frigorifera
                )

                # Calcolo incentivo
                if validazione_solare.ammissibile:
                    risultato_solare = calculate_solar_thermal_incentive(
                        tipologia_impianto=tipologia_solare,
                        tipo_collettore=tipo_collettore,
                        superficie_lorda_m2=superficie_totale,
                        energia_qcol_kwh=energia_modulo,
                        area_modulo_m2=area_modulo,
                        spesa_totale=spesa_solare,
                        tipo_soggetto=tipo_soggetto
                    )

                    if risultato_solare["status"] == "OK":
                        st.subheader("📊 Risultati")

                        # Badge iter semplificato se prodotto da catalogo
                        if iter_semplificato_st and prodotto_catalogo_st:
                            st.success(f"""
                            ✅ **ITER SEMPLIFICATO** - Prodotto a Catalogo GSE

                            **{prodotto_catalogo_st.get('marca')} {prodotto_catalogo_st.get('modello')}**
                            """)
                            if superficie_totale <= 50:
                                st.info("📋 **Vantaggi**: Asseverazione non obbligatoria, dati pre-compilati, Solar Keymark già verificato")

                        # Calcola Ecobonus per confronto usando aliquote corrette
                        risultato_eco_solare = calculate_ecobonus_deduction(
                            tipo_intervento="solare_termico",
                            spesa_sostenuta=spesa_solare,
                            anno_spesa=2025,  # Anno corrente
                            tipo_abitazione=tipo_abitazione
                        )
                        eco_solare = risultato_eco_solare["detrazione_totale"]
                        eco_rata_annua = risultato_eco_solare["calcoli"]["rata_annuale"]
                        aliquota_eco_solare = risultato_eco_solare["calcoli"]["aliquota_applicata"]

                        # NPV calculation (tasso sconto 3%)
                        tasso_sconto = 0.03
                        ct_incentivo = risultato_solare["incentivo_totale"]
                        n_rate_ct = risultato_solare["erogazione"]["numero_rate"]

                        # NPV Conto Termico
                        if n_rate_ct == 1:
                            npv_ct_solare = ct_incentivo
                        else:
                            rate_ct = risultato_solare["erogazione"]["rate"]
                            npv_ct_solare = sum(rata / ((1 + tasso_sconto) ** (i+1)) for i, rata in enumerate(rate_ct))

                        # NPV Ecobonus (10 rate annue)
                        npv_eco_solare = sum(eco_rata_annua / ((1 + tasso_sconto) ** i) for i in range(1, 11))

                        # Metriche principali - condizionali in base a solo_conto_termico
                        if solo_conto_termico:
                            # Solo CT: 2 colonne
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Conto Termico 3.0",
                                    format_currency(ct_incentivo),
                                    delta="Ammesso"
                                )
                            with col2:
                                st.metric("NPV Conto Termico", format_currency(npv_ct_solare))
                        else:
                            # Modalità standard: 4 colonne
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric(
                                    "Conto Termico",
                                    format_currency(ct_incentivo),
                                    delta="Ammesso"
                                )
                            with col2:
                                st.metric(
                                    "Ecobonus",
                                    format_currency(eco_solare),
                                    delta=f"{aliquota_eco_solare*100:.0f}% (10 anni)"
                                )
                            with col3:
                                st.metric("NPV Conto Termico", format_currency(npv_ct_solare))
                            with col4:
                                st.metric("NPV Ecobonus", format_currency(npv_eco_solare))

                        # Grafico confronto (solo se NON modalità Solo CT)
                        if not solo_conto_termico and (ct_incentivo > 0 or eco_solare > 0):
                            fig = create_comparison_chart(
                                ct_incentivo, eco_solare,
                                npv_ct_solare, npv_eco_solare
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        # Raccomandazione
                        st.divider()
                        st.subheader("💡 Raccomandazione")

                        ct_pct_solare = (ct_incentivo / spesa_solare * 100) if spesa_solare > 0 else 0
                        eco_pct_solare = (eco_solare / spesa_solare * 100) if spesa_solare > 0 else 0
                        n_rate = risultato_solare["erogazione"]["numero_rate"]

                        if solo_conto_termico:
                            # Modalità Solo CT: mostra solo dettagli CT
                            st.success(f"""
                            ✅ **CONTO TERMICO 3.0**

                            **Incentivo**: {format_currency(ct_incentivo)} ({ct_pct_solare:.1f}% della spesa)
                            **Erogazione**: Bonifico diretto GSE in {n_rate} {"anno" if n_rate == 1 else "anni"}
                            **NPV**: {format_currency(npv_ct_solare)}
                            """)
                        else:
                            # Modalità standard: confronto completo
                            col_rec1, col_rec2 = st.columns(2)

                            with col_rec1:
                                nota_pct = f" (max 65%)" if ct_pct_solare >= 64.9 else ""
                                st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
                                        padding: 20px; border-radius: 10px; color: white;">
                                <h4 style="margin: 0 0 10px 0; color: white;">☀️ Conto Termico 3.0</h4>
                                <p style="font-size: 1.5em; margin: 5px 0; font-weight: bold;">{format_currency(ct_incentivo)}</p>
                                <p style="margin: 5px 0;">📊 <strong>{ct_pct_solare:.1f}%</strong> della spesa{nota_pct}</p>
                                <p style="margin: 5px 0;">⏱️ Erogazione: <strong>{n_rate} {"anno" if n_rate == 1 else "anni"}</strong></p>
                                <p style="margin: 5px 0;">💰 <strong>Bonifico diretto GSE</strong></p>
                            </div>
                            """, unsafe_allow_html=True)

                        with col_rec2:
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
                                        padding: 20px; border-radius: 10px; color: white;">
                                <h4 style="margin: 0 0 10px 0; color: white;">📋 Ecobonus</h4>
                                <p style="font-size: 1.5em; margin: 5px 0; font-weight: bold;">{format_currency(eco_solare)}</p>
                                <p style="margin: 5px 0;">📊 <strong>{eco_pct_solare:.1f}%</strong> della spesa</p>
                                <p style="margin: 5px 0;">⏱️ Erogazione: <strong>10 anni</strong></p>
                                <p style="margin: 5px 0;">📝 <strong>Detrazione fiscale IRPEF</strong></p>
                            </div>
                            """, unsafe_allow_html=True)

                        # Logica raccomandazione
                        st.markdown("---")
                        premio_liquidita = 1.15 if n_rate <= 2 else 1.05
                        ct_valore_reale = ct_incentivo * premio_liquidita

                        if ct_valore_reale >= eco_solare * 0.85:
                            st.success(f"""
                            **✅ CONSIGLIATO: CONTO TERMICO 3.0**

                            | Aspetto | Conto Termico | Ecobonus |
                            |---------|---------------|----------|
                            | **Importo** | {format_currency(ct_incentivo)} ({ct_pct_solare:.1f}%) | {format_currency(eco_solare)} ({eco_pct_solare:.1f}%) |
                            | **Liquidità** | Bonifico in {n_rate} {"anno" if n_rate == 1 else "anni"} | Detrazione in 10 anni |
                            | **Certezza** | Pagamento garantito GSE | Richiede capienza IRPEF |
                            | **Rischio** | Nessuno | Perdita quota se IRPEF insufficiente |

                            💡 *Con {format_currency(ct_incentivo)} oggi puoi investire o ridurre il finanziamento.*
                            """)
                        else:
                            diff_pct = ((eco_solare - ct_incentivo) / ct_incentivo * 100) if ct_incentivo > 0 else 0
                            st.info(f"""
                            **📊 ECOBONUS ha valore nominale maggiore (+{diff_pct:.0f}%)**

                            | Aspetto | Conto Termico | Ecobonus |
                            |---------|---------------|----------|
                            | **Importo** | {format_currency(ct_incentivo)} ({ct_pct_solare:.1f}%) | {format_currency(eco_solare)} ({eco_pct_solare:.1f}%) |
                            | **Erogazione** | {n_rate} {"anno" if n_rate == 1 else "anni"} | 10 anni |
                            | **Rata annua Eco** | - | {format_currency(eco_rata_annua)}/anno |

                            ⚠️ *L'Ecobonus richiede capienza IRPEF di almeno {format_currency(eco_rata_annua)}/anno per 10 anni.*

                            💡 *Se non sei sicuro della tua capienza fiscale futura, il Conto Termico è più sicuro.*
                            """)

                        st.divider()

                        # Box riepilogo compatto
                        calcoli = risultato_solare["calcoli_intermedi"]

                        # Salva nel session state per uso successivo
                        st.session_state.ultimo_calcolo_solare = {
                            "tipologia_solare": tipologia_solare,
                            "tipologia_solare_label": tipologia_solare_label,
                            "tipo_collettore": tipo_collettore,
                            "tipo_collettore_label": tipo_collettore_label,
                            "superficie_totale": superficie_totale,
                            "n_moduli": n_moduli,
                            "area_modulo": area_modulo,
                            "qu_calcolato": qu_calcolato,
                            "spesa_solare": spesa_solare,
                            "ct_incentivo": ct_incentivo,
                            "risultato_solare": risultato_solare,
                            "n_rate_ct": n_rate_ct,
                            "calcoli": calcoli,
                            "eco_solare": eco_solare,
                            "aliquota_eco_solare": aliquota_eco_solare,
                            "npv_ct_solare": npv_ct_solare,
                            "npv_eco_solare": npv_eco_solare,
                            "iter_semplificato_st": iter_semplificato_st,
                            "prodotto_catalogo_st": prodotto_catalogo_st,
                            "piu_conveniente": "CT" if npv_ct_solare > npv_eco_solare else "Ecobonus"
                        }

                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
                                    padding: 15px; border-radius: 10px; color: white; margin: 15px 0;">
                            <strong>Formula: Ia = Ci × Qu × Sl</strong><br>
                            Ci: {calcoli['Ci']} €/kWht | Qu: {calcoli['Qu']} kWht/m² | Sl: {calcoli['Sl']} m²<br>
                            <strong>Ia annuo: {format_currency(calcoli['Ia'])} × {calcoli['n']} anni = {format_currency(risultato_solare['incentivo_totale'])}</strong>
                        </div>
                        """, unsafe_allow_html=True)

                        # Dettagli in expander
                        with st.expander("📅 Dettaglio Erogazione"):
                            erog = risultato_solare["erogazione"]
                            if erog["modalita"] == "rata_unica":
                                st.success(f"Rata unica: {format_currency(erog['rate'][0])}")
                            else:
                                for i, rata in enumerate(erog["rate"], 1):
                                    st.write(f"Anno {i}: {format_currency(rata)}")

                        with st.expander("📋 Massimali"):
                            mass = risultato_solare["massimali_applicati"]
                            st.write(f"Spesa ammissibile: {format_currency(mass['spesa_ammissibile'])}")
                            st.write(f"Max: {mass['percentuale_applicata']*100:.0f}%")
                            if mass["taglio_applicato"]:
                                st.warning(f"Taglio: {format_currency(mass['importo_tagliato'])}")

                        # Warning
                        if validazione_solare.warning:
                            for w in validazione_solare.warning:
                                st.warning(w)

                        with st.expander("📋 Documentazione"):
                            for doc in validazione_solare.documentazione_richiesta:
                                st.write(f"• {doc}")

                    else:
                        st.error(f"Errore: {risultato_solare['messaggio']}")

                else:
                    st.error("❌ NON ammissibile")
                    for err in validazione_solare.errori_bloccanti:
                        st.error(f"• {err}")
                    if validazione_solare.suggerimenti:
                        for sug in validazione_solare.suggerimenti:
                            st.info(f"💡 {sug}")

            else:
                # Stato iniziale con info
                st.info("👈 Inserisci i dati tecnici e la spesa, poi clicca **CALCOLA SOLARE**")

                with st.expander("ℹ️ Intervento III.D - Info"):
                    st.markdown("""
                    **Collettori solari termici per:**
                    - Acqua calda sanitaria (ACS)
                    - Riscaldamento ambiente
                    - Calore di processo
                    - Solar cooling

                    **Requisiti:** Solar Keymark, Qu min, garanzia 5 anni
                    """)

                with st.expander("📊 Coefficienti Ci"):
                    st.markdown("""
                    | Tipologia | < 12 m² | 12-50 | 50-200 | 200-500 | > 500 |
                    |-----------|---------|-------|--------|---------|-------|
                    | ACS | 0.35 | 0.32 | 0.13 | 0.12 | 0.11 |
                    | ACS+Risc | 0.36 | 0.33 | 0.13 | 0.12 | 0.11 |
                    | Solar cool | 0.43 | 0.40 | 0.17 | 0.15 | 0.14 |
                    """)

        # Pulsante salva scenario solare (FUORI dal blocco calcola)
        st.divider()
        col_save_sol1, col_save_sol2 = st.columns([3, 1])
        with col_save_sol1:
            salva_scenario_solare = st.button(
                "💾 Salva Scenario Solare",
                type="secondary",
                use_container_width=True,
                key="btn_salva_solare",
                disabled=len(st.session_state.scenari_solare) >= 5
            )
        with col_save_sol2:
            st.write(f"({len(st.session_state.scenari_solare)}/5)")

        if salva_scenario_solare:
            if st.session_state.ultimo_calcolo_solare is None:
                st.warning("⚠️ Prima calcola gli incentivi con CALCOLA SOLARE")
            elif len(st.session_state.scenari_solare) >= 5:
                st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")
            else:
                dati = st.session_state.ultimo_calcolo_solare
                nuovo_scenario = {
                    "id": len(st.session_state.scenari_solare) + 1,
                    "nome": f"Scenario {len(st.session_state.scenari_solare) + 1}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "tipologia": dati["tipologia_solare_label"],
                    "tipo_collettore": dati["tipo_collettore_label"],
                    "superficie": dati["superficie_totale"],
                    "n_moduli": dati["n_moduli"],
                    "area_modulo": dati["area_modulo"],
                    "qu_calcolato": dati["qu_calcolato"],
                    "spesa": dati["spesa_solare"],
                    "ct_incentivo": dati["ct_incentivo"],
                    "ct_rate": dati["n_rate_ct"],
                    "eco_detrazione": dati["eco_solare"],
                    "aliquota_eco": dati["aliquota_eco_solare"],
                    "npv_ct": dati["npv_ct_solare"],
                    "npv_eco": dati["npv_eco_solare"],
                    "iter_semplificato": dati["iter_semplificato_st"],
                    "prodotto_catalogo": dati["prodotto_catalogo_st"],
                    "piu_conveniente": dati["piu_conveniente"]
                }
                st.session_state.scenari_solare.append(nuovo_scenario)
                st.success(f"✅ Scenario salvato! ({len(st.session_state.scenari_solare)}/5)")
                st.rerun()

    # ===========================================================================
    # TAB 3: FOTOVOLTAICO COMBINATO (II.H)
    # ===========================================================================
    with tab_fv:
        st.header("🔆 Fotovoltaico Combinato (II.H)")
        st.caption("Installazione FV abbinata a sostituzione con PdC elettrica")

        st.info("""
        **Intervento II.H** - Installazione di impianti solari fotovoltaici e sistemi di accumulo,
        realizzato **congiuntamente** alla sostituzione con pompa di calore elettrica (III.A).

        L'incentivo FV è limitato all'incentivo calcolato per la PdC abbinata.
        """)

        # Verifica se c'è un calcolo PdC salvato in sessione
        pdc_salvata = st.session_state.get("ultimo_calcolo_pdc", None)

        col_fv_input, col_fv_output = st.columns([1, 1])

        with col_fv_input:
            st.subheader("📊 Dati Pompa di Calore Abbinata")

            # Se non c'è PdC salvata, permetti input manuale
            if pdc_salvata:
                st.success(f"""
                **PdC già calcolata:**
                - Tipo: {pdc_salvata.get('tipo_intervento_label', 'N/D')}
                - Potenza: {pdc_salvata.get('potenza_kw', 0)} kW
                - Incentivo CT: {format_currency(pdc_salvata.get('ct_incentivo', 0))}
                """)
                incentivo_pdc = pdc_salvata.get('ct_incentivo', 0)
                potenza_pdc = pdc_salvata.get('potenza_kw', 0)
                usa_pdc_salvata = st.checkbox("Usa dati PdC salvata", value=True, key="usa_pdc_salvata")
            else:
                usa_pdc_salvata = False

            if not usa_pdc_salvata:
                st.warning("Inserisci manualmente i dati della PdC abbinata (o calcola prima nel tab PdC)")
                potenza_pdc = st.number_input(
                    "Potenza PdC abbinata (kW)",
                    min_value=1.0, max_value=2000.0, value=10.0,
                    key="fv_potenza_pdc",
                    help="Potenza nominale della PdC abbinata"
                )
                incentivo_pdc = st.number_input(
                    "Incentivo CT calcolato per PdC (€)",
                    min_value=0.0, max_value=500000.0, value=5000.0,
                    key="fv_incentivo_pdc",
                    help="Incentivo CT 3.0 calcolato per la PdC (limite max per FV)"
                )

            st.divider()
            st.subheader("☀️ Dati Impianto Fotovoltaico")

            potenza_fv = st.number_input(
                "Potenza FV (kW)",
                min_value=2.0, max_value=1000.0, value=6.0,
                key="fv_potenza",
                help="Potenza di picco dell'impianto FV (min 2 kW, max 1 MW)"
            )

            spesa_fv = st.number_input(
                "Spesa impianto FV (€)",
                min_value=0.0, max_value=5000000.0, value=9000.0,
                key="fv_spesa",
                help="Costo totale impianto FV (IVA inclusa se non detraibile)"
            )

            # Calcolo costo specifico FV
            costo_spec_fv = spesa_fv / potenza_fv if potenza_fv > 0 else 0
            costo_max_fv = 1500 if potenza_fv <= 20 else (1200 if potenza_fv <= 200 else (1100 if potenza_fv <= 600 else 1050))
            if costo_spec_fv > costo_max_fv:
                st.warning(f"Costo specifico {costo_spec_fv:.0f} €/kW > massimo ammissibile {costo_max_fv} €/kW")
            else:
                st.caption(f"Costo specifico: {costo_spec_fv:.0f} €/kW (max ammissibile: {costo_max_fv} €/kW)")

            st.divider()
            st.subheader("🔋 Sistema di Accumulo (opzionale)")

            con_accumulo = st.checkbox("Includi sistema di accumulo", value=False, key="fv_con_accumulo")

            if con_accumulo:
                capacita_acc = st.number_input(
                    "Capacità accumulo (kWh)",
                    min_value=0.0, max_value=500.0, value=10.0,
                    key="fv_capacita_acc"
                )
                spesa_acc = st.number_input(
                    "Spesa accumulo (€)",
                    min_value=0.0, max_value=500000.0, value=8000.0,
                    key="fv_spesa_acc"
                )
                # Calcolo costo specifico accumulo
                costo_spec_acc = spesa_acc / capacita_acc if capacita_acc > 0 else 0
                if costo_spec_acc > COSTO_MAX_ACCUMULO:
                    st.warning(f"Costo specifico {costo_spec_acc:.0f} €/kWh > massimo ammissibile {COSTO_MAX_ACCUMULO} €/kWh")
                else:
                    st.caption(f"Costo specifico: {costo_spec_acc:.0f} €/kWh (max: {COSTO_MAX_ACCUMULO} €/kWh)")
            else:
                capacita_acc = 0.0
                spesa_acc = 0.0

            st.divider()
            st.subheader("📐 Dimensionamento (verifica 105%)")

            # Fabbisogno elettrico
            fabbisogno_el = st.number_input(
                "Fabbisogno elettrico annuo (kWh)",
                min_value=0.0, max_value=10000000.0, value=4000.0,
                key="fv_fabbisogno_el",
                help="Consumo elettrico annuo dell'edificio (da bollette)"
            )

            # Fabbisogno termico con calcolatore integrato
            st.markdown("**Fabbisogno termico equivalente:**")

            # Opzione per escludere il fabbisogno termico
            includi_termico = st.checkbox(
                "Includi fabbisogno termico nel dimensionamento",
                value=True,
                key="fv_includi_termico",
                help="Deseleziona se non hai riscaldamento a gas/gasolio (es. casa già elettrica, nuova costruzione)"
            )

            if includi_termico:
                calcola_termico = st.checkbox("Calcola da consumo gas", value=True, key="fv_calcola_termico")

                if calcola_termico:
                    with st.expander("🔢 Calcolo fabbisogno termico equivalente", expanded=True):
                        st.caption("Formula: kWh_el = Consumo_termico / SCOP della PdC")

                        # Selezione tipo combustibile
                        tipo_combustibile = st.selectbox(
                            "Tipo combustibile attuale",
                            options=["Gas metano", "GPL", "Gasolio", "Pellet/Legna", "Altro"],
                            key="fv_tipo_combustibile"
                        )

                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            if tipo_combustibile == "Gas metano":
                                consumo_comb = st.number_input(
                                    "Consumo gas annuo (m³)",
                                    min_value=0.0, max_value=100000.0, value=1200.0,
                                    key="fv_consumo_gas",
                                    help="Consumo annuo di gas metano (da bollette)"
                                )
                                potere_cal = 10.69  # kWh/m³
                                st.caption(f"Potere calorifico: {potere_cal} kWh/m³")
                            elif tipo_combustibile == "GPL":
                                consumo_comb = st.number_input(
                                    "Consumo GPL annuo (litri)",
                                    min_value=0.0, max_value=50000.0, value=800.0,
                                    key="fv_consumo_gpl",
                                    help="Consumo annuo di GPL (da bollette)"
                                )
                                potere_cal = 6.82  # kWh/litro
                                st.caption(f"Potere calorifico: {potere_cal} kWh/litro")
                            elif tipo_combustibile == "Gasolio":
                                consumo_comb = st.number_input(
                                    "Consumo gasolio annuo (litri)",
                                    min_value=0.0, max_value=50000.0, value=1000.0,
                                    key="fv_consumo_gasolio",
                                    help="Consumo annuo di gasolio (da fatture)"
                                )
                                potere_cal = 10.0  # kWh/litro
                                st.caption(f"Potere calorifico: {potere_cal} kWh/litro")
                            elif tipo_combustibile == "Pellet/Legna":
                                consumo_comb = st.number_input(
                                    "Consumo pellet annuo (kg)",
                                    min_value=0.0, max_value=50000.0, value=3000.0,
                                    key="fv_consumo_pellet",
                                    help="Consumo annuo di pellet/legna (in kg)"
                                )
                                potere_cal = 4.8  # kWh/kg pellet
                                st.caption(f"Potere calorifico: {potere_cal} kWh/kg")
                            else:
                                consumo_comb = st.number_input(
                                    "Energia termica annua (kWh)",
                                    min_value=0.0, max_value=500000.0, value=12000.0,
                                    key="fv_consumo_altro",
                                    help="Energia termica annua stimata"
                                )
                                potere_cal = 1.0  # già in kWh

                        with col_t2:
                            if tipo_combustibile != "Altro":
                                rend_caldaia = st.number_input(
                                    "Rendimento generatore esistente (%)",
                                    min_value=50.0, max_value=110.0, value=90.0,
                                    key="fv_rend_caldaia",
                                    help="Rendimento stagionale (tipico 85-95% caldaie, 80-90% stufe)"
                                ) / 100
                            else:
                                rend_caldaia = 1.0

                            # Usa SCOP dalla PdC salvata o input manuale
                            if pdc_salvata and usa_pdc_salvata:
                                scop_pdc = pdc_salvata.get('scop', 4.0)
                                st.info(f"SCOP PdC: **{scop_pdc}** (da calcolo PdC)")
                            else:
                                scop_pdc = st.number_input(
                                    "SCOP della nuova PdC",
                                    min_value=2.0, max_value=8.0, value=4.0,
                                    key="fv_scop_pdc",
                                    help="SCOP della pompa di calore installata"
                                )

                        # Calcolo
                        energia_termica = consumo_comb * potere_cal * rend_caldaia  # kWh termici
                        fabbisogno_term = energia_termica / scop_pdc  # kWh elettrici equivalenti

                        st.success(f"""
                        **Risultato calcolo:**
                        - Energia termica annua: **{energia_termica:,.0f} kWh_th**
                        - Fabbisogno equivalente: **{fabbisogno_term:,.0f} kWh_el** (con SCOP {scop_pdc})
                        """)
                else:
                    fabbisogno_term = st.number_input(
                        "Fabbisogno termico equivalente (kWh el.)",
                        min_value=0.0, max_value=10000000.0, value=3000.0,
                        key="fv_fabbisogno_term",
                        help="Fabbisogno termico convertito in kWh elettrici (consumo termico / COP PdC)"
                    )
            else:
                fabbisogno_term = 0.0
                st.info("ℹ️ Fabbisogno termico non incluso. Il dimensionamento FV sarà basato solo sul fabbisogno elettrico.")

            st.divider()

            # Produzione FV con stima integrata
            st.markdown("**Produzione annua FV:**")
            calcola_produzione = st.checkbox("Stima produzione (dati medi Italia)", value=True, key="fv_calcola_prod")

            if calcola_produzione:
                with st.expander("☀️ Stima produzione FV", expanded=True):
                    st.caption("Formula: Produzione = Potenza × Irradiazione × PR")

                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        # Irradiazione media per zona Italia (kWh/m²/anno su piano orizzontale)
                        zona_italia = st.selectbox(
                            "Zona geografica",
                            options=[
                                "Nord Italia (1100-1300 kWh/m²)",
                                "Centro Italia (1300-1500 kWh/m²)",
                                "Sud Italia (1500-1800 kWh/m²)",
                                "Isole (1600-1900 kWh/m²)"
                            ],
                            index=1,
                            key="fv_zona_italia"
                        )
                        # Mappa irradiazione media
                        irr_map = {
                            "Nord Italia (1100-1300 kWh/m²)": 1200,
                            "Centro Italia (1300-1500 kWh/m²)": 1400,
                            "Sud Italia (1500-1800 kWh/m²)": 1650,
                            "Isole (1600-1900 kWh/m²)": 1750
                        }
                        irradiazione_base = irr_map.get(zona_italia, 1400)

                        orientamento = st.selectbox(
                            "Orientamento",
                            options=["Sud (ottimale)", "Sud-Est / Sud-Ovest", "Est / Ovest", "Nord (sconsigliato)"],
                            index=0,
                            key="fv_orientamento"
                        )
                        # Fattore di correzione orientamento
                        orient_factor = {"Sud (ottimale)": 1.0, "Sud-Est / Sud-Ovest": 0.95, "Est / Ovest": 0.85, "Nord (sconsigliato)": 0.60}
                        f_orient = orient_factor.get(orientamento, 1.0)

                    with col_p2:
                        inclinazione = st.slider(
                            "Inclinazione (°)",
                            min_value=0, max_value=90, value=30,
                            key="fv_inclinazione",
                            help="Inclinazione ottimale in Italia: 30-35° per Sud"
                        )
                        # Fattore inclinazione (ottimo ~30-35° per Italia)
                        if 25 <= inclinazione <= 40:
                            f_incl = 1.0
                        elif 15 <= inclinazione < 25 or 40 < inclinazione <= 50:
                            f_incl = 0.95
                        elif inclinazione < 15 or inclinazione > 50:
                            f_incl = 0.90
                        else:
                            f_incl = 0.85

                        pr = st.slider(
                            "Performance Ratio (PR)",
                            min_value=0.70, max_value=0.90, value=0.80, step=0.01,
                            key="fv_pr",
                            help="Rapporto di prestazione (tipico 0.75-0.85)"
                        )

                    # Calcolo produzione
                    # Fattore di guadagno per inclinazione ottimale sud Italia ~1.1-1.15
                    irr_effettiva = irradiazione_base * f_orient * f_incl
                    produzione_pvgis = potenza_fv * irr_effettiva * pr

                    st.success(f"""
                    **Stima produzione annua:**
                    - Irradiazione effettiva: **{irr_effettiva:,.0f} kWh/m²/anno**
                    - Produzione stimata: **{produzione_pvgis:,.0f} kWh/anno**
                    - Producibilità: **{produzione_pvgis/potenza_fv:,.0f} kWh/kWp/anno**
                    """)

                    st.warning("""
                    ⚠️ **Stima indicativa** basata su dati medi. Per il valore ufficiale da inserire
                    nella richiesta CT, usa il report **PVGIS**: [re.jrc.ec.europa.eu/pvg_tools](https://re.jrc.ec.europa.eu/pvg_tools/it/)
                    """)
            else:
                produzione_pvgis = st.number_input(
                    "Produzione annua stimata PVGIS (kWh)",
                    min_value=0.0, max_value=10000000.0, value=7200.0,
                    key="fv_produzione",
                    help="Da report PVGIS per il sito specifico"
                )

            # Verifica dimensionamento
            fabbisogno_tot = fabbisogno_el + fabbisogno_term
            limite_105 = fabbisogno_tot * 1.05
            rapporto_dim = (produzione_pvgis / fabbisogno_tot * 100) if fabbisogno_tot > 0 else 0

            if produzione_pvgis > limite_105:
                st.error(f"Produzione ({rapporto_dim:.1f}%) > 105% del fabbisogno - RIDURRE potenza FV")
            else:
                st.success(f"Dimensionamento OK: {rapporto_dim:.1f}% del fabbisogno (max 105%)")

            st.divider()
            st.subheader("🏷️ Maggiorazioni Registro Tecnologie")

            registro_fv = st.selectbox(
                "Registro tecnologie FV (art. 12 DL 181/2023)",
                options=["Nessuno", "Sezione A (+5%)", "Sezione B (+10%)", "Sezione C (+15%)"],
                index=0,
                key="fv_registro",
                help="Maggiorazione per moduli iscritti al registro delle tecnologie FV"
            )

            # Info box sul registro tecnologie
            with st.expander("ℹ️ Come verificare il Registro Tecnologie FV"):
                st.markdown("""
                ### Cos'è il Registro delle Tecnologie del Fotovoltaico?

                È un registro istituito dall'**art. 12 del DL 181/2023** per incentivare l'uso di moduli
                fotovoltaici prodotti in Europa. Prevede maggiorazioni sull'incentivo CT 3.0.

                ---

                ### Le tre sezioni e i requisiti

                | Sezione | Maggiorazione | Requisiti |
                |---------|---------------|-----------|
                | **A** | +5% | Moduli **assemblati** nell'UE |
                | **B** | +10% | Moduli con **celle** prodotte nell'UE |
                | **C** | +15% | Moduli con **celle e wafer** prodotti nell'UE (filiera completa) |

                ---

                ### Come verificare se i moduli sono nel registro

                1. **Consultare il sito GSE:**
                   - [Registro Tecnologie FV - GSE](https://www.gse.it/servizi-per-te/fotovoltaico/registro-tecnologie-fotovoltaico)

                2. **Chiedere al produttore/fornitore:**
                   - Richiedere la **dichiarazione di iscrizione** al registro
                   - Verificare la **sezione specifica** (A, B o C)

                3. **Controllare la scheda tecnica:**
                   - Verificare il luogo di produzione di: moduli, celle, wafer
                   - Controllare certificazioni di origine UE

                ---

                ### Condizioni per ottenere la maggiorazione

                **TUTTI** i moduli dell'impianto devono:
                - Essere iscritti al registro
                - Appartenere alla **stessa sezione** (non si possono mischiare A, B e C)

                **Documentazione da allegare alla richiesta CT:**
                - Dichiarazione di iscrizione al registro
                - Attestazione della sezione di appartenenza
                - Elenco numeri di serie dei moduli

                ---

                ### Esempio pratico

                Per un impianto da 6 kW con spesa ammissibile 9.000 €:

                | Scenario | % Incentivo | Incentivo |
                |----------|-------------|-----------|
                | Senza registro | 20% | 1.800 € |
                | Sezione A | 25% | 2.250 € |
                | Sezione B | 30% | 2.700 € |
                | Sezione C | 35% | 3.150 € |

                *La maggiorazione può fare la differenza nella scelta tra CT e Bonus Ristrutturazione!*
                """)

            registro_map = {
                "Nessuno": None,
                "Sezione A (+5%)": "sezione_a",
                "Sezione B (+10%)": "sezione_b",
                "Sezione C (+15%)": "sezione_c"
            }
            registro_val = registro_map.get(registro_fv)

            # Bottone calcolo
            st.divider()
            calcola_fv = st.button("⚡ CALCOLA FV COMBINATO", type="primary", use_container_width=True, key="btn_calcola_fv")

        # OUTPUT FV
        with col_fv_output:
            if calcola_fv:
                # Verifica vincoli terziario CT 3.0 (Punto 3)
                ammissibile_vincoli_fv, msg_vincoli_fv = applica_vincoli_terziario_ct3(
                    tipo_intervento_app="fotovoltaico",
                    tipo_soggetto_label=tipo_soggetto_principale
                )

                if not ammissibile_vincoli_fv:
                    st.error(f"🚫 {msg_vincoli_fv}")
                    st.stop()
                elif msg_vincoli_fv:
                    st.warning(f"⚠️ {msg_vincoli_fv}")

                st.subheader("📋 Validazione Requisiti")

                # Validazione
                validazione_fv = valida_requisiti_fv_combinato(
                    potenza_fv_kw=potenza_fv,
                    produzione_stimata_kwh=produzione_pvgis,
                    fabbisogno_elettrico_kwh=fabbisogno_el,
                    fabbisogno_termico_equiv_kwh=fabbisogno_term,
                    pdc_abbinata_ammissibile=(incentivo_pdc > 0),
                    incentivo_pdc_calcolato=incentivo_pdc,
                    edificio_esistente=True,
                    assetto_autoconsumo=True,
                    tipo_soggetto=TIPI_SOGGETTO.get(st.session_state.get("sidebar_soggetto", "Privato cittadino"), "privato")
                )

                if validazione_fv.ammissibile:
                    st.success("✅ Requisiti FV soddisfatti")

                    # Calcolo incentivo CT
                    risultato_fv = calculate_fv_combined_incentive(
                        potenza_fv_kw=potenza_fv,
                        spesa_fv=spesa_fv,
                        incentivo_pdc_abbinata=incentivo_pdc,
                        potenza_pdc_kw=potenza_pdc,
                        capacita_accumulo_kwh=capacita_acc,
                        spesa_accumulo=spesa_acc,
                        tipo_soggetto=TIPI_SOGGETTO.get(st.session_state.get("sidebar_soggetto", "Privato cittadino"), "privato"),
                        registro_tecnologie=registro_val
                    )

                    if risultato_fv["status"] == "OK":
                        incentivo_ct_fv = risultato_fv["incentivo_totale"]

                        # Calcolo Bonus Ristrutturazione per confronto
                        spesa_totale_fv = spesa_fv + spesa_acc
                        anno_spesa = st.session_state.get("sidebar_anno", 2025)
                        tipo_abit = TIPI_ABITAZIONE.get(st.session_state.get("sidebar_abitazione", "Prima casa (abitazione principale)"), "abitazione_principale")

                        # Aliquota Bonus Ristrutturazione
                        if anno_spesa <= 2024:
                            aliquota_bonus = 0.50
                        elif anno_spesa <= 2026:
                            aliquota_bonus = 0.50 if tipo_abit == "abitazione_principale" else 0.36
                        else:
                            aliquota_bonus = 0.36 if tipo_abit == "abitazione_principale" else 0.30

                        # Limite spesa 96.000€
                        spesa_ammissibile_bonus = min(spesa_totale_fv, 96000)
                        detrazione_bonus = spesa_ammissibile_bonus * aliquota_bonus
                        rata_annua_bonus = detrazione_bonus / 10

                        # NPV
                        tasso_sconto = st.session_state.get("sidebar_tasso", 3.0) / 100
                        npv_ct_fv = calculate_npv(risultato_fv["erogazione"]["rate"], tasso_sconto)
                        npv_bonus = calculate_npv([rata_annua_bonus] * 10, tasso_sconto)

                        # Display risultati
                        st.divider()
                        st.subheader("💰 Confronto Incentivi FV")

                        col_ct, col_bonus = st.columns(2)

                        with col_ct:
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%);
                                        padding: 20px; border-radius: 10px; color: white;">
                                <h3 style="margin: 0;">Conto Termico 3.0</h3>
                                <h1 style="margin: 10px 0;">{format_currency(incentivo_ct_fv)}</h1>
                                <p>NPV: {format_currency(npv_ct_fv)}</p>
                                <small>Erogazione: {risultato_fv["erogazione"]["modalita"]}</small>
                            </div>
                            """, unsafe_allow_html=True)

                        with col_bonus:
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
                                        padding: 20px; border-radius: 10px; color: white;">
                                <h3 style="margin: 0;">Bonus Ristrutturazione</h3>
                                <h1 style="margin: 10px 0;">{format_currency(detrazione_bonus)}</h1>
                                <p>NPV: {format_currency(npv_bonus)}</p>
                                <small>Aliquota: {aliquota_bonus*100:.0f}% - 10 rate da {format_currency(rata_annua_bonus)}</small>
                            </div>
                            """, unsafe_allow_html=True)

                        # Raccomandazione
                        st.divider()
                        if npv_ct_fv > npv_bonus:
                            st.success(f"""
                            **Raccomandazione: CONTO TERMICO 3.0**

                            NPV superiore di {format_currency(npv_ct_fv - npv_bonus)}
                            - Liquidità immediata (o max 5 rate)
                            - Non richiede capienza IRPEF
                            """)
                        else:
                            st.info(f"""
                            **Raccomandazione: BONUS RISTRUTTURAZIONE**

                            NPV superiore di {format_currency(npv_bonus - npv_ct_fv)}

                            ⚠️ *Richiede capienza IRPEF di almeno {format_currency(rata_annua_bonus)}/anno per 10 anni.*

                            💡 *Se non sei sicuro della tua capienza fiscale futura, il Conto Termico è più sicuro.*
                            """)

                        st.divider()

                        # Box riepilogo formula CT
                        calcoli = risultato_fv["calcoli_intermedi"]
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
                                    padding: 15px; border-radius: 10px; color: white; margin: 15px 0;">
                            <strong>Formula CT: I = %spesa × C_FTV × P_FTV + %spesa × C_ACC × C_ACCUMULO</strong><br>
                            %spesa: {calcoli['percentuale_spesa']*100:.0f}% | C_FTV: {calcoli['costo_max_fv']} €/kW | P_FTV: {potenza_fv} kW<br>
                            <strong>Incentivo lordo: {format_currency(calcoli['incentivo_totale_lordo'])} (limite PdC: {format_currency(incentivo_pdc)})</strong>
                        </div>
                        """, unsafe_allow_html=True)

                        # Dettagli in expander
                        with st.expander("📅 Dettaglio Erogazione CT"):
                            erog = risultato_fv["erogazione"]
                            if erog["modalita"] == "rata_unica":
                                st.success(f"Rata unica: {format_currency(erog['rate'][0])}")
                            else:
                                for i, rata in enumerate(erog["rate"], 1):
                                    st.write(f"Anno {i}: {format_currency(rata)}")

                        with st.expander("📋 Massimali e Costi"):
                            mass = risultato_fv["massimali_applicati"]
                            st.write(f"Spesa FV ammissibile: {format_currency(mass['spesa_fv_ammissibile'])}")
                            st.write(f"Spesa accumulo ammissibile: {format_currency(mass['spesa_acc_ammissibile'])}")
                            st.write(f"Percentuale incentivo: {mass['percentuale_applicata']*100:.0f}%")
                            if mass["taglio_applicato"]:
                                st.warning(f"Taglio per limite PdC: -{format_currency(mass['importo_tagliato'])}")

                        # Warning
                        if validazione_fv.warning:
                            for w in validazione_fv.warning:
                                st.warning(w)

                        with st.expander("📋 Documentazione Richiesta"):
                            for doc in validazione_fv.documentazione_richiesta:
                                st.write(f"• {doc}")

                        # Salva dati FV in sessione per inclusione in scenario PdC
                        st.session_state.ultimo_calcolo_fv = {
                            "potenza_fv_kw": potenza_fv,
                            "spesa_fv": spesa_fv,
                            "capacita_accumulo_kwh": capacita_acc,
                            "spesa_accumulo": spesa_acc,
                            "produzione_stimata_kwh": produzione_pvgis,
                            "incentivo_ct": incentivo_ct_fv,
                            "bonus_ristrutt": detrazione_bonus,
                            "registro_tecnologie": registro_val,
                            "npv_ct": npv_ct_fv,
                            "npv_bonus": npv_bonus,
                            "pdc_abbinata": incentivo_pdc,
                        }
                        st.info("💡 I dati FV sono stati salvati. Torna al tab PdC e clicca 'Salva Scenario' per includere il FV nel report.")

                    else:
                        st.error(f"Errore calcolo: {risultato_fv['messaggio']}")

                else:
                    st.error("❌ NON ammissibile")
                    for err in validazione_fv.errori_bloccanti:
                        st.error(f"• {err}")
                    if validazione_fv.suggerimenti:
                        for sug in validazione_fv.suggerimenti:
                            st.info(f"💡 {sug}")

            else:
                # Stato iniziale con info
                st.info("👈 Inserisci i dati dell'impianto FV, poi clicca **CALCOLA FV COMBINATO**")

                with st.expander("ℹ️ Intervento II.H - Informazioni"):
                    st.markdown("""
                    **Fotovoltaico Combinato (II.H):**

                    Installazione di impianti solari fotovoltaici e sistemi di accumulo,
                    realizzato **congiuntamente** alla sostituzione con pompa di calore elettrica.

                    **Requisiti principali:**
                    - Potenza FV: min 2 kW, max 1 MW
                    - Assetto autoconsumo (cessione parziale)
                    - Produzione <= 105% del fabbisogno energetico
                    - Moduli con marcatura CE, tolleranza positiva
                    - Garanzia prodotto >= 10 anni
                    - Rendimento inverter >= 97%

                    **Incentivo:**
                    - Base: 20% delle spese ammissibili
                    - PA: 100% delle spese ammissibili
                    - Maggiorazioni registro tecnologie: +5%/+10%/+15%
                    - **Limite massimo: incentivo calcolato per la PdC abbinata**
                    """)

                with st.expander("📊 Costi Massimi Ammissibili"):
                    st.markdown("""
                    **Impianto FV:**
                    | Potenza | Costo max |
                    |---------|-----------|
                    | ≤ 20 kW | 1.500 €/kW |
                    | 20-200 kW | 1.200 €/kW |
                    | 200-600 kW | 1.100 €/kW |
                    | 600-1000 kW | 1.050 €/kW |

                    **Accumulo:** max 1.000 €/kWh
                    """)

    # ===========================================================================
    # TAB 4: GENERATORI A BIOMASSA (III.C)
    # ===========================================================================
    with tab_biomassa:
        st.header("🔥 Generatori a Biomassa (III.C)")
        st.caption("Sostituzione impianti con caldaie, stufe e termocamini a biomassa")

        st.info("""
        **Intervento III.C** - Sostituzione di impianti di climatizzazione invernale esistenti
        con generatori di calore alimentati a biomassa (legna, pellet, cippato).

        **Requisito classe ambientale (DM 186/2017):**
        - **Classe 5 stelle obbligatoria** per sostituzione di biomassa/carbone/olio/gasolio/GPL/metano
        - **Classe 4 stelle ammessa** per sostituzione di altri combustibili fossili
        """)

        col_bio_input, col_bio_output = st.columns([1, 1])

        with col_bio_input:
            st.subheader("📊 Dati Generatore")

            # Carica catalogo GSE Biomassa
            catalogo_biomassa = load_catalogo_biomassa()

            # Checkbox per usare il catalogo
            usa_catalogo_biomassa = st.checkbox(
                "🔍 Cerca nel Catalogo GSE",
                value=False,
                help="Seleziona un generatore a biomassa dal catalogo GSE per l'iter semplificato (potenza ≤ 35 kW)",
                key="bio_usa_catalogo"
            )

            # Variabili per prodotto selezionato
            prodotto_catalogo_bio = None
            iter_semplificato_bio = False

            if usa_catalogo_biomassa and catalogo_biomassa:
                # Filtro per potenza ≤ 35 kW (requisito iter semplificato)
                catalogo_filtrato = [
                    p for p in catalogo_biomassa
                    if p.get("dati_tecnici", {}).get("potenza_kw") and
                       p.get("dati_tecnici", {}).get("potenza_kw") <= 35
                ]

                if not catalogo_filtrato:
                    st.warning("⚠️ Nessun prodotto ≤ 35 kW trovato nel catalogo.")
                else:
                    st.info(f"📋 {len(catalogo_filtrato)} prodotti disponibili (≤ 35 kW)")

                    # Selezione marca
                    marche_disponibili = get_marche_catalogo_biomassa(catalogo_filtrato)
                    marca_selezionata_bio = st.selectbox(
                        "Marca",
                        options=[""] + marche_disponibili,
                        index=0,
                        help="Seleziona la marca del generatore",
                        key="bio_marca"
                    )

                    if marca_selezionata_bio:
                        # Ottieni modelli per marca
                        modelli_marca_bio = get_modelli_per_marca_biomassa(catalogo_filtrato, marca_selezionata_bio)
                        opzioni_modelli_bio = [""] + [
                            f"{m['modello']} ({m.get('alimentazione', '?')}, {m.get('dati_tecnici', {}).get('potenza_kw', '?')} kW)"
                            for m in modelli_marca_bio
                        ]

                        modello_idx_bio = st.selectbox(
                            "Modello",
                            options=range(len(opzioni_modelli_bio)),
                            format_func=lambda x: opzioni_modelli_bio[x],
                            index=0,
                            help="Seleziona il modello",
                            key="bio_modello"
                        )

                        if modello_idx_bio > 0:
                            prodotto_catalogo_bio = modelli_marca_bio[modello_idx_bio - 1]
                            iter_semplificato_bio = True

                            # Mostra info prodotto selezionato
                            dati_tec = prodotto_catalogo_bio.get("dati_tecnici", {})
                            st.success(f"""
                            ✅ **ITER SEMPLIFICATO** (Art. 14, comma 5, DM 7/8/2025)

                            **{prodotto_catalogo_bio.get('marca')} {prodotto_catalogo_bio.get('modello')}**
                            - Tipo: {prodotto_catalogo_bio.get('tipologia_generatore', 'N/D')} - {prodotto_catalogo_bio.get('alimentazione', 'N/D')}
                            - Alimentazione: {prodotto_catalogo_bio.get('tipologia_alimentazione', 'N/D')}
                            - Potenza: {dati_tec.get('potenza_kw', 'N/D')} kW
                            - Rendimento: {dati_tec.get('rendimento_perc', 'N/D')}%
                            - Classe qualità: {prodotto_catalogo_bio.get('classe_qualita_ambientale', 'N/D')}
                            """)

                            # Vantaggi iter semplificato
                            with st.expander("ℹ️ Vantaggi Iter Semplificato (potenza ≤ 35 kW)", expanded=False):
                                st.markdown("""
                                **Essendo il prodotto presente nel Catalogo GSE con potenza ≤ 35 kW:**

                                ✅ **Documentazione semplificata:**
                                - ❌ NON serve certificazione tecnica del produttore
                                - ❌ NON serve asseverazione di fine lavori
                                - ✅ Basta autodichiarazione del Soggetto Responsabile

                                ✅ **Dati tecnici precompilati automaticamente**

                                ✅ **Iter più veloce** - i requisiti tecnici sono già verificati dal GSE

                                📋 **Riferimento normativo:** Art. 14, comma 5, DM 7 agosto 2025
                                """)

            elif usa_catalogo_biomassa and not catalogo_biomassa:
                st.warning("⚠️ Catalogo GSE Biomassa non disponibile.")

            st.divider()

            # Tipo generatore (manuale o da catalogo)
            if prodotto_catalogo_bio:
                # Auto-fill da catalogo
                tipo_gen_auto = map_tipologia_generatore_catalogo(
                    prodotto_catalogo_bio.get("tipologia_generatore", ""),
                    prodotto_catalogo_bio.get("tipologia_alimentazione", "")
                )

                # Raffina per potenza se caldaia
                potenza_prod = prodotto_catalogo_bio.get("dati_tecnici", {}).get("potenza_kw", 0)
                if tipo_gen_auto == "caldaia_lte_500" and potenza_prod > 500:
                    tipo_gen_auto = "caldaia_gt_500"

                tipo_gen_label = tipo_gen_auto
                st.info(f"📋 Tipo generatore (da catalogo): **{TIPI_GENERATORE[tipo_gen_label]}**")
            else:
                tipo_gen_label = st.selectbox(
                    "Tipo generatore",
                    options=list(TIPI_GENERATORE.keys()),
                    format_func=lambda x: TIPI_GENERATORE[x],
                    key="bio_tipo_generatore",
                    help="Seleziona il tipo di generatore a biomassa"
                )

            # Mostra limiti potenza per il tipo selezionato
            limiti = LIMITI_POTENZA_BIOMASSA.get(tipo_gen_label, {"min": 3.0, "max": 500.0})
            potenza_min = limiti["min"]
            potenza_max = limiti["max"]

            # Potenza (da catalogo o manuale)
            if prodotto_catalogo_bio:
                potenza_bio = prodotto_catalogo_bio.get("dati_tecnici", {}).get("potenza_kw", 25.0)
                st.info(f"⚡ Potenza (da catalogo): **{potenza_bio} kW**")
            else:
                potenza_bio = st.number_input(
                    f"Potenza nominale (kW) [range: {potenza_min}-{potenza_max}]",
                    min_value=potenza_min,
                    max_value=potenza_max,
                    value=min(25.0, potenza_max),
                    step=1.0,
                    key="bio_potenza",
                    help=f"Potenza nominale del generatore ({potenza_min}-{potenza_max} kW per {TIPI_GENERATORE[tipo_gen_label]})"
                )

            spesa_bio = st.number_input(
                "Spesa totale (€)",
                min_value=0.0,
                max_value=1000000.0,
                value=8000.0,
                step=100.0,
                key="bio_spesa",
                help="Spesa totale per acquisto e installazione (IVA inclusa se non detraibile)"
            )

            # Calcolo costo specifico
            massimale_unitario = MASSIMALI_BIOMASSA.get(tipo_gen_label, 350.0)
            costo_spec_bio = spesa_bio / potenza_bio if potenza_bio > 0 else 0
            spesa_max_ammiss = massimale_unitario * potenza_bio

            if costo_spec_bio > massimale_unitario:
                st.warning(f"Costo specifico {costo_spec_bio:.0f} €/kW > massimale {massimale_unitario:.0f} €/kW")
                st.caption(f"Spesa ammissibile: {spesa_max_ammiss:,.0f} € (verrà applicato il massimale)")
            else:
                st.caption(f"Costo specifico: {costo_spec_bio:.0f} €/kW (massimale: {massimale_unitario:.0f} €/kW)")

            st.divider()
            st.subheader("🔄 Tipo di Sostituzione")

            # Combustibile sostituito - determina se 5 stelle è obbligatorio
            combustibile_sostituito = st.selectbox(
                "Combustibile dell'impianto esistente da sostituire",
                options=["metano", "gpl", "gasolio", "olio", "carbone", "biomassa", "altro"],
                format_func=lambda x: {
                    "metano": "Metano / Gas naturale",
                    "gpl": "GPL",
                    "gasolio": "Gasolio",
                    "olio": "Olio combustibile",
                    "carbone": "Carbone",
                    "biomassa": "Biomassa (vecchio generatore)",
                    "altro": "Altro combustibile"
                }.get(x, x),
                index=0,
                key="bio_combustibile_sostituito",
                help="Seleziona il tipo di combustibile dell'impianto che stai sostituendo. Questo determina i requisiti di classe ambientale."
            )

            # Info sui requisiti in base al combustibile sostituito
            if combustibile_sostituito in ["biomassa", "carbone", "olio", "gasolio"]:
                st.warning("⚠️ **Classe 5 stelle OBBLIGATORIA** per sostituzione di biomassa/carbone/olio/gasolio (DM 186/2017)")
            elif combustibile_sostituito in ["gpl", "metano"]:
                if tipo_gen_label in ["caldaia_lte_500", "stufa_pellet", "termocamino_pellet", "termocamino_legna", "stufa_legna"]:
                    st.warning("⚠️ **Classe 5 stelle OBBLIGATORIA** per sostituzione GPL/metano + requisito emissioni PP ≤ 1 mg/Nm³")
                else:
                    st.info("ℹ️ Classe 4 stelle ammessa per questo tipo di sostituzione")
            else:
                st.info("ℹ️ Classe 4 stelle ammessa per questo tipo di sostituzione")

            st.divider()
            st.subheader("🌿 Caratteristiche Emissioni")

            # Classe emissioni (da catalogo o manuale)
            if prodotto_catalogo_bio:
                classe_cat = prodotto_catalogo_bio.get("classe_qualita_ambientale", "").lower()
                if "5" in classe_cat or "cinque" in classe_cat:
                    classe_emissione = "5_stelle"
                    st.success("⭐⭐⭐⭐⭐ **Classe ambientale (da catalogo): 5 stelle**")
                elif "4" in classe_cat or "quattro" in classe_cat:
                    classe_emissione = "4_stelle"
                    st.info("⭐⭐⭐⭐ **Classe ambientale (da catalogo): 4 stelle**")
                else:
                    st.warning("⚠️ Classe ambientale non riconosciuta dal catalogo, inserisci manualmente")
                    classe_emissione = st.selectbox(
                        "Classe ambientale",
                        options=["5_stelle", "4_stelle", "3_stelle", "non_classificato"],
                        format_func=lambda x: {
                            "5_stelle": "⭐⭐⭐⭐⭐ Classe 5 stelle",
                            "4_stelle": "⭐⭐⭐⭐ Classe 4 stelle",
                            "3_stelle": "⭐⭐⭐ Classe 3 stelle (NON AMMESSA)",
                            "non_classificato": "Non classificato (NON AMMESSO)"
                        }.get(x, x),
                        index=0,
                        key="bio_classe",
                        help="Classe ambientale secondo DM 186/2017. Requisito minimo varia in base al tipo di sostituzione."
                    )
            else:
                classe_emissione = st.selectbox(
                    "Classe ambientale",
                    options=["5_stelle", "4_stelle", "3_stelle", "non_classificato"],
                    format_func=lambda x: {
                        "5_stelle": "⭐⭐⭐⭐⭐ Classe 5 stelle",
                        "4_stelle": "⭐⭐⭐⭐ Classe 4 stelle",
                        "3_stelle": "⭐⭐⭐ Classe 3 stelle (NON AMMESSA)",
                        "non_classificato": "Non classificato (NON AMMESSO)"
                    }.get(x, x),
                    index=0,
                    key="bio_classe",
                    help="Classe ambientale secondo DM 186/2017. Requisito minimo varia in base al tipo di sostituzione."
                )

            # Riduzione emissioni per coefficiente Ce
            st.markdown("**Premialità emissioni (Ce):**")
            riduzione_emissioni = st.slider(
                "Riduzione emissioni vs limiti legge (%)",
                min_value=0,
                max_value=100,
                value=30,
                step=5,
                key="bio_riduzione",
                help="Riduzione delle emissioni rispetto ai limiti di legge. Determina il coefficiente Ce."
            )

            # Mostra Ce applicato
            if riduzione_emissioni <= 20:
                ce_val = 1.0
                ce_desc = "Ce = 1.0 (riduzione ≤ 20%)"
            elif riduzione_emissioni <= 50:
                ce_val = 1.2
                ce_desc = "Ce = 1.2 (riduzione 20-50%)"
            else:
                ce_val = 1.5
                ce_desc = "Ce = 1.5 (riduzione > 50%)"

            st.info(f"**{ce_desc}** - Maggiorazione incentivo: +{(ce_val-1)*100:.0f}%")

            st.divider()
            st.subheader("📋 Requisiti Tecnici")

            # Rendimento
            is_caldaia = tipo_gen_label.startswith("caldaia")
            if is_caldaia:
                import math
                if tipo_gen_label == "caldaia_lte_500":
                    rend_min = 87 + math.log10(potenza_bio)
                else:
                    rend_min = 92.0
            else:
                rend_min = 85.0

            # Rendimento (da catalogo o manuale)
            if prodotto_catalogo_bio:
                rendimento_bio = prodotto_catalogo_bio.get("dati_tecnici", {}).get("rendimento_perc")
                if rendimento_bio:
                    st.info(f"📊 Rendimento (da catalogo): **{rendimento_bio}%**")
                else:
                    st.warning("⚠️ Rendimento non disponibile nel catalogo, inserisci manualmente")
                    rendimento_bio = st.number_input(
                        f"Rendimento dichiarato (%) [minimo: {rend_min:.1f}%]",
                        min_value=50.0,
                        max_value=110.0,
                        value=max(90.0, rend_min + 1),
                        step=0.5,
                        key="bio_rendimento",
                        help=f"Rendimento stagionale del generatore (minimo {rend_min:.1f}%)"
                    )
            else:
                rendimento_bio = st.number_input(
                    f"Rendimento dichiarato (%) [minimo: {rend_min:.1f}%]",
                    min_value=50.0,
                    max_value=110.0,
                    value=max(90.0, rend_min + 1),
                    step=0.5,
                    key="bio_rendimento",
                    help=f"Rendimento stagionale del generatore (minimo {rend_min:.1f}%)"
                )

            if rendimento_bio and rendimento_bio < rend_min:
                st.error(f"⚠️ Rendimento {rendimento_bio}% < minimo richiesto {rend_min:.1f}%")

            # Accumulo per caldaie
            if is_caldaia:
                accumulo_minimo = 20 * potenza_bio  # 20 dm³/kW
                st.markdown(f"**Sistema accumulo (min {accumulo_minimo:.0f} litri = 20 dm³/kW):**")

                accumulo_installato = st.checkbox(
                    "Sistema accumulo installato",
                    value=True,
                    key="bio_accumulo_check"
                )

                if accumulo_installato:
                    capacita_accumulo = st.number_input(
                        "Capacità accumulo (litri)",
                        min_value=0.0,
                        max_value=10000.0,
                        value=max(500.0, accumulo_minimo),
                        step=50.0,
                        key="bio_accumulo_cap"
                    )
                    if capacita_accumulo < accumulo_minimo:
                        st.error(f"⚠️ Capacità {capacita_accumulo:.0f} L < minimo {accumulo_minimo:.0f} L")
                else:
                    capacita_accumulo = 0.0
                    st.error("⚠️ Sistema accumulo obbligatorio per caldaie a biomassa!")
            else:
                accumulo_installato = True  # Non richiesto per stufe/termocamini
                capacita_accumulo = None

            # Abbattimento particolato per caldaie >500 kW
            if tipo_gen_label == "caldaia_gt_500":
                abbattimento = st.checkbox(
                    "Sistema abbattimento particolato installato",
                    value=True,
                    key="bio_abbattimento",
                    help="Obbligatorio per caldaie > 500 kW"
                )
                if not abbattimento:
                    st.error("⚠️ Sistema abbattimento particolato obbligatorio per caldaie > 500 kW!")
            else:
                abbattimento = True

            # Pulsante calcolo
            st.divider()
            calcola_bio = st.button(
                "🔥 CALCOLA INCENTIVO BIOMASSA",
                type="primary",
                use_container_width=True,
                key="btn_calcola_bio"
            )

        with col_bio_output:
            st.subheader("📊 Risultati Calcolo")

            if calcola_bio:
                # Validazione requisiti
                with st.spinner("Validazione requisiti..."):
                    validazione = valida_requisiti_biomassa(
                        tipo_generatore=tipo_gen_label,
                        zona_climatica=zona_climatica,
                        potenza_nominale_kw=potenza_bio,
                        classe_emissione=classe_emissione,
                        rendimento_pct=rendimento_bio,
                        riduzione_emissioni_pct=riduzione_emissioni,
                        edificio_esistente=True,
                        impianto_esistente=True,
                        accumulo_installato=accumulo_installato,
                        capacita_accumulo_dm3=capacita_accumulo,
                        abbattimento_particolato=abbattimento,
                        tipo_soggetto=tipo_soggetto
                    )

                # Mostra risultato validazione
                if validazione.ammissibile:
                    punteggio_bio = validazione.punteggio_completezza
                    if punteggio_bio == 100:
                        st.success(f"✅ **AMMISSIBILE** - Punteggio: {punteggio_bio:.0f}%")
                    else:
                        st.success(f"✅ **AMMISSIBILE** - Punteggio: {punteggio_bio:.0f}%")
                        st.info(f"ℹ️ **Perché {punteggio_bio:.0f}% e non 100%?** Ci sono avvisi che riducono il punteggio (vedi sotto):")
                else:
                    st.error(f"❌ **NON AMMISSIBILE** - Punteggio: {validazione.punteggio_completezza:.0f}%")
                    for err in validazione.errori_bloccanti:
                        st.error(f"• {err}")
                    st.stop()

                # Warning
                if validazione.warning:
                    st.warning("**⚠️ AVVISI:**")
                    for warn in validazione.warning:
                        st.warning(f"  • {warn}")

                # Calcolo CT 3.0
                with st.spinner("Calcolo incentivo Conto Termico 3.0..."):
                    risultato_ct = calculate_biomass_incentive(
                        tipo_generatore=tipo_gen_label,
                        zona_climatica=zona_climatica,
                        potenza_nominale_kw=potenza_bio,
                        spesa_totale_sostenuta=spesa_bio,
                        riduzione_emissioni_pct=riduzione_emissioni,
                        tipo_soggetto=tipo_soggetto,
                        classe_emissione=classe_emissione,
                        rendimento_pct=rendimento_bio,
                        tipo_combustibile_sostituito=combustibile_sostituito
                    )

                # Calcolo Ecobonus
                ecobonus_bio = calcola_ecobonus_biomassa(
                    spesa_sostenuta=spesa_bio,
                    anno_spesa=2025,
                    tipo_abitazione=tipo_abitazione
                )

                if risultato_ct["status"] == "OK":
                    st.divider()
                    st.subheader("💰 Incentivi Calcolati")

                    col_ct, col_eco = st.columns(2)

                    with col_ct:
                        st.markdown("### Conto Termico 3.0")
                        incentivo_ct = risultato_ct["incentivo_totale"]
                        st.metric(
                            "Incentivo Totale",
                            f"€ {incentivo_ct:,.2f}",
                            help="Contributo diretto in conto capitale"
                        )

                        # Dettagli calcolo
                        calcoli = risultato_ct["calcoli_intermedi"]
                        with st.expander("📋 Dettagli calcolo"):
                            st.markdown(f"""
                            **Parametri:**
                            - hr (ore funzionamento): {calcoli['hr']} h
                            - Ci (coeff. valorizzazione): {calcoli['Ci']} €/kWht
                            - Ce (coeff. emissioni): {calcoli['Ce']}

                            **Calcolo:**
                            - Incentivo annuo: **€ {calcoli['I_annuo']:,.2f}**
                            - Durata: **{calcoli['n']} anni**
                            - Totale lordo: € {calcoli['I_tot_lordo']:,.2f}

                            **Massimali:**
                            - Spesa ammissibile: € {risultato_ct['massimali_applicati']['spesa_ammissibile']:,.2f}
                            - Max da percentuale ({risultato_ct['massimali_applicati']['percentuale_applicata']*100:.0f}%): € {risultato_ct['massimali_applicati']['I_max_da_massimali']:,.2f}
                            """)

                        # Erogazione
                        erog = risultato_ct["erogazione"]
                        if erog["modalita"] == "rata_unica":
                            st.info(f"💵 Erogazione: **Rata unica** € {erog['rate'][0]:,.2f}")
                        else:
                            st.info(f"💵 Erogazione: **{erog['numero_rate']} rate** da € {erog['rate'][0]:,.2f}")

                    with col_eco:
                        st.markdown("### Ecobonus")
                        st.metric(
                            "Detrazione Totale",
                            f"€ {ecobonus_bio['detrazione_effettiva']:,.2f}",
                            help="Detrazione fiscale in 10 anni"
                        )

                        with st.expander("📋 Dettagli Ecobonus"):
                            st.markdown(f"""
                            **Parametri:**
                            - Aliquota: {ecobonus_bio['aliquota']*100:.0f}%
                            - Limite detrazione: € {ecobonus_bio['limite_detrazione']:,.0f}

                            **Calcolo:**
                            - Detrazione lorda: € {ecobonus_bio['detrazione_lorda']:,.2f}
                            - Detrazione effettiva: € {ecobonus_bio['detrazione_effettiva']:,.2f}

                            **Recupero:**
                            - Anni: {ecobonus_bio['anni_recupero']}
                            - Rata annuale: € {ecobonus_bio['rata_annuale']:,.2f}
                            """)

                        st.warning("⚠️ Richiede capienza fiscale per 10 anni")

                    # Confronto
                    st.divider()
                    st.subheader("📊 Confronto CT vs Ecobonus")

                    confronto = confronta_incentivi_biomassa(
                        risultato_ct=risultato_ct,
                        spesa_sostenuta=spesa_bio,
                        anno_spesa=2025,
                        tipo_abitazione=tipo_abitazione
                    )

                    col_conf1, col_conf2 = st.columns(2)
                    with col_conf1:
                        st.metric(
                            "VAN Conto Termico",
                            f"€ {confronto['conto_termico']['van']:,.2f}",
                            help="Valore Attuale Netto (tasso 3%)"
                        )
                    with col_conf2:
                        st.metric(
                            "VAN Ecobonus",
                            f"€ {confronto['ecobonus']['van']:,.2f}",
                            help="Valore Attuale Netto (tasso 3%)"
                        )

                    # Raccomandazione
                    if confronto['confronto']['convenienza'] == "CT":
                        st.success(f"""
                        ✅ **CONTO TERMICO PIÙ CONVENIENTE**

                        Differenza VAN: +€ {confronto['confronto']['differenza_van']:,.2f}

                        Il Conto Termico è **erogazione diretta** (non richiede capienza fiscale).
                        """)
                    else:
                        st.info(f"""
                        ℹ️ **ECOBONUS PIÙ CONVENIENTE (se hai capienza fiscale)**

                        Differenza VAN: +€ {confronto['confronto']['differenza_van']:,.2f}

                        L'Ecobonus richiede capienza fiscale IRPEF/IRES per 10 anni.
                        """)

                    # Salva scenario
                    st.divider()
                    col_save, col_name = st.columns([2, 1])
                    with col_name:
                        nome_scenario_bio = st.text_input(
                            "Nome scenario",
                            value=f"Biomassa {TIPI_GENERATORE[tipo_gen_label][:20]}",
                            key="bio_nome_scenario"
                        )
                    with col_save:
                        if st.button("💾 Salva Scenario", key="btn_salva_bio", use_container_width=True):
                            if len(st.session_state.scenari) >= 5:
                                st.error("Massimo 5 scenari. Elimina uno scenario esistente.")
                            else:
                                nuovo_scenario = {
                                    "nome": nome_scenario_bio,
                                    "tipo": "biomassa",
                                    "tipo_intervento": tipo_gen_label,
                                    "tipo_intervento_label": TIPI_GENERATORE[tipo_gen_label],
                                    "potenza_kw": potenza_bio,
                                    "spesa": spesa_bio,
                                    "ct_incentivo": incentivo_ct,
                                    "eco_detrazione": ecobonus_bio['detrazione_effettiva'],
                                    "npv_ct": confronto['conto_termico']['van'],
                                    "npv_eco": confronto['ecobonus']['van'],
                                    "zona_climatica": zona_climatica,
                                    "riduzione_emissioni": riduzione_emissioni,
                                    "timestamp": datetime.now().isoformat()
                                }
                                st.session_state.scenari.append(nuovo_scenario)
                                st.success(f"✅ Scenario '{nome_scenario_bio}' salvato!")
                                st.rerun()

                else:
                    st.error(f"Errore calcolo: {risultato_ct['messaggio']}")

            else:
                # Mostra info mentre non c'è calcolo
                st.info("Compila i dati del generatore e clicca 'CALCOLA INCENTIVO BIOMASSA'")

                with st.expander("📚 Guida Generatori a Biomassa"):
                    st.markdown("""
                    ### Tipologie ammesse (III.C)

                    | Tipologia | Potenza | Ci (€/kWht) | Massimale |
                    |-----------|---------|-------------|-----------|
                    | Caldaia biomassa ≤ 500 kW | 5-500 kW | 0.020-0.060 | 350 €/kW |
                    | Caldaia biomassa > 500 kW | 500-2000 kW | 0.020 | 250 €/kW |
                    | Stufa a pellet | 3-35 kW | 0.055 | 750 €/kW |
                    | Termocamino pellet | 3-35 kW | 0.055 | 750 €/kW |
                    | Termocamino legna | 3-35 kW | 0.045 | 500 €/kW |
                    | Stufa a legna | 3-35 kW | 0.045 | 500 €/kW |

                    ### Formule di calcolo

                    **Caldaie:**
                    ```
                    I = Pn × hr × Ci × Ce
                    ```

                    **Stufe e termocamini:**
                    ```
                    I = 3.35 × ln(Pn) × hr × Ci × Ce
                    ```

                    Dove:
                    - Pn = Potenza nominale (kW)
                    - hr = Ore funzionamento (da zona climatica)
                    - Ci = Coefficiente valorizzazione (€/kWht)
                    - Ce = Coefficiente premialità emissioni

                    ### Requisiti obbligatori

                    - ✅ **Classe 5 stelle** (DM 186/2017)
                    - ✅ Certificazione **UNI EN 303-5** (caldaie) o **UNI EN 16510:2023** (stufe)
                    - ✅ Rendimento minimo: 87+log(Pn)% (caldaie) o 85% (stufe)
                    - ✅ Sistema accumulo ≥ 20 dm³/kW (solo caldaie)
                    - ✅ Sistema abbattimento particolato (caldaie > 500 kW)
                    """)

                with st.expander("📊 Ore di Funzionamento per Zona"):
                    st.markdown("""
                    | Zona | Ore (hr) |
                    |------|----------|
                    | A | 600 |
                    | B | 850 |
                    | C | 1100 |
                    | D | 1400 |
                    | E | 1700 |
                    | F | 1800 |
                    """)

                with st.expander("🌿 Coefficiente Ce (Premialità Emissioni)"):
                    st.markdown("""
                    Il coefficiente Ce premia i generatori con emissioni inferiori ai limiti di legge:

                    | Riduzione emissioni | Ce |
                    |--------------------|-----|
                    | ≤ 20% | 1.0 |
                    | 20% - 50% | 1.2 |
                    | > 50% | 1.5 |

                    La riduzione si calcola rispetto ai limiti della normativa DM 186/2017.
                    """)

    # ===========================================================================
    # TAB 5: ISOLAMENTO TERMICO
    # ===========================================================================
    with tab_isolamento:
        st.header("🏠 Isolamento Termico - Confronto Incentivi")
        st.write("Confronta Conto Termico 3.0, Ecobonus e Bonus Ristrutturazione per isolamento termico")

        st.divider()

        # Importa i moduli necessari
        from modules.calculator_isolamento import calculate_insulation_incentive, confronta_incentivi_isolamento
        from modules.validator_isolamento import validate_insulation_requirements

        # Sezione Input Dati
        st.subheader("📋 Dati Intervento")

        col1, col2 = st.columns(2)

        with col1:
            tipo_superficie_iso = st.selectbox(
                "Tipo di superficie",
                options=["coperture", "pavimenti", "pareti"],
                format_func=lambda x: {
                    "coperture": "Coperture (tetti)",
                    "pavimenti": "Pavimenti",
                    "pareti": "Pareti verticali"
                }.get(x, x),
                key="iso_tipo_superficie",
                help="Seleziona il tipo di superficie da isolare"
            )

            posizione_iso = st.selectbox(
                "Posizione isolamento",
                options=["esterno", "interno", "ventilato"],
                format_func=lambda x: {
                    "esterno": "Esterno (cappotto esterno)",
                    "interno": "Interno (cappotto interno)",
                    "ventilato": "Ventilato (con intercapedine)"
                }.get(x, x),
                key="iso_posizione",
                help="La posizione influenza il costo massimo ammissibile"
            )

            # Selezione Regione/Provincia per zona climatica
            st.markdown("**Localizzazione**")

            lista_regioni_iso = get_lista_regioni()
            regione_iso = st.selectbox(
                "Regione",
                options=lista_regioni_iso,
                index=lista_regioni_iso.index("Lombardia") if "Lombardia" in lista_regioni_iso else 0,
                key="iso_regione",
                help="Seleziona la regione dell'immobile"
            )

            province_iso = get_province_by_regione(regione_iso)
            province_nomi_iso = [f"{nome} ({sigla})" for sigla, nome in province_iso]

            if province_nomi_iso:
                provincia_display_iso = st.selectbox(
                    "Provincia",
                    options=province_nomi_iso,
                    index=0,
                    key="iso_provincia",
                    help="Seleziona la provincia - determina automaticamente la zona climatica"
                )

                # Estrai sigla e determina zona climatica
                provincia_sigla_iso = provincia_display_iso.split("(")[-1].rstrip(")")
                zona_climatica_iso_auto = get_zona_climatica(provincia_sigla_iso)

                # Opzione per modifica manuale
                modifica_manuale_iso = st.checkbox(
                    "✏️ Modifica zona manualmente",
                    value=False,
                    key="iso_modifica_zona",
                    help="Attiva per modificare manualmente la zona climatica del comune"
                )

                if modifica_manuale_iso:
                    zona_climatica_iso = st.selectbox(
                        "Zona climatica",
                        options=["A", "B", "C", "D", "E", "F"],
                        index=["A", "B", "C", "D", "E", "F"].index(zona_climatica_iso_auto),
                        key="iso_zona_manuale",
                        help="Seleziona manualmente la zona climatica"
                    )
                    st.warning(f"⚠️ Zona manuale: **{zona_climatica_iso}** (automatica era: {zona_climatica_iso_auto})")
                else:
                    zona_climatica_iso = zona_climatica_iso_auto
                    st.success(f"🌡️ Zona Climatica: **{zona_climatica_iso}**")
            else:
                zona_climatica_iso = "E"
                st.warning("⚠️ Zona E (default)")

            superficie_mq_iso = st.number_input(
                "Superficie da isolare (m²)",
                min_value=10.0,
                max_value=10000.0,
                value=150.0,
                step=10.0,
                key="iso_superficie_mq",
                help="Superficie totale da isolare"
            )

        with col2:
            spesa_totale_iso = st.number_input(
                "Spesa totale sostenuta (EUR)",
                min_value=1000.0,
                max_value=500000.0,
                value=30000.0,
                step=1000.0,
                key="iso_spesa_totale",
                help="Spesa totale IVA inclusa"
            )

            trasmittanza_post_iso = st.number_input(
                "Trasmittanza post-intervento (W/m²K)",
                min_value=0.10,
                max_value=0.50,
                value=0.22,
                step=0.01,
                format="%.2f",
                key="iso_trasmittanza",
                help="Trasmittanza termica dopo l'intervento"
            )

            anno_spesa_iso = st.selectbox(
                "Anno di spesa",
                options=[2024, 2025, 2026, 2027],
                index=1,  # Default: 2025
                key="iso_anno_spesa"
            )

            tipo_abitazione_iso = st.selectbox(
                "Tipo abitazione",
                options=["abitazione_principale", "altra_abitazione"],
                format_func=lambda x: "Abitazione principale" if x == "abitazione_principale" else "Altra abitazione",
                key="iso_tipo_abitazione"
            )

        st.divider()

        # Sezione Premialità e Opzioni
        st.subheader("🎁 Premialità e Opzioni")

        col_prem1, col_prem2, col_prem3 = st.columns(3)

        with col_prem1:
            componenti_ue_iso = st.checkbox(
                "Componenti UE (+10%)",
                value=False,
                key="iso_componenti_ue",
                help="Premialità del 10% se i componenti sono prodotti nell'Unione Europea"
            )

        with col_prem2:
            combinato_titolo_iii_iso = st.checkbox(
                "Combinato con Titolo III (+15%)",
                value=False,
                key="iso_combinato_titolo_iii",
                help="Premialità del 15% se combinato con intervento Titolo III ammesso"
            )

            if combinato_titolo_iii_iso:
                with st.expander("ℹ️ Quali interventi Titolo III sono ammessi?"):
                    st.markdown("""
                    Gli interventi **Titolo III** che danno diritto al **55%** (40% + 15%) sono:

                    - **III.A** - Pompe di Calore (elettriche/gas, aero/geo/idro)
                    - **III.B** - Sistemi Ibridi (factory made o bivalenti)
                    - **III.C** - Generatori a Biomassa (caldaie, stufe, termocamini)
                    - **III.E** - Scaldacqua a Pompa di Calore

                    ⚠️ **Nota**: Il solare termico (III.D) **NON** dà diritto al bonus 55%
                    """)

        with col_prem3:
            tipo_soggetto_iso = st.selectbox(
                "Tipo soggetto",
                options=["privato", "pa"],
                format_func=lambda x: "Privato/Condominio" if x == "privato" else "Pubblica Amministrazione",
                key="iso_tipo_soggetto"
            )

        st.divider()

        # Pulsante calcola
        calcola_iso = st.button("🔍 Calcola Incentivi", key="btn_calcola_iso", type="primary", use_container_width=True)

        if calcola_iso:

            # Verifica vincoli terziario CT 3.0 (Punto 3)
            tipo_intervento_iso_codice = "isolamento_copertura" if tipo_superficie_iso == "coperture" else ("isolamento_pavimento" if tipo_superficie_iso == "pavimenti" else "isolamento_termico")
            ammissibile_vincoli_iso, msg_vincoli_iso = applica_vincoli_terziario_ct3(
                tipo_intervento_app=tipo_intervento_iso_codice,
                tipo_soggetto_label=tipo_soggetto_principale
            )

            if not ammissibile_vincoli_iso:
                st.error(f"🚫 {msg_vincoli_iso}")
                st.stop()
            elif msg_vincoli_iso:
                st.warning(f"⚠️ {msg_vincoli_iso}")

            # Validazione requisiti tecnici
            st.subheader("✅ Validazione Requisiti Tecnici")

            validazione_result_iso = validate_insulation_requirements(
                tipo_superficie=tipo_superficie_iso,
                posizione_isolamento=posizione_iso,
                zona_climatica=zona_climatica_iso,
                trasmittanza_post_operam=trasmittanza_post_iso,
                superficie_mq=superficie_mq_iso,
                ha_diagnosi_energetica=True,  # Assumiamo presente
                ha_ape_post_operam=True       # Assumiamo presente
            )

            if validazione_result_iso["ammissibile"]:
                punteggio_iso = validazione_result_iso['punteggio']
                if punteggio_iso == 100:
                    st.success(f"✅ **Requisiti CT 3.0: AMMISSIBILE** (Punteggio: {punteggio_iso}%)")
                else:
                    st.success(f"✅ **Requisiti CT 3.0: AMMISSIBILE** (Punteggio: {punteggio_iso}%)")
                    st.info(f"ℹ️ **Perché {punteggio_iso}% e non 100%?** Ci sono avvisi o suggerimenti che riducono il punteggio (vedi sotto):")
            else:
                st.error("❌ **Requisiti CT 3.0: NON AMMISSIBILE**")
                for err in validazione_result_iso["errori"]:
                    st.error(f"- {err}")

            if validazione_result_iso["warnings"]:
                st.warning("**⚠️ AVVISI:**")
                for warn in validazione_result_iso["warnings"]:
                    st.warning(f"  • {warn}")

            st.divider()

            # Confronto tra incentivi
            st.subheader("💰 Confronto Incentivi")

            try:
                confronto_iso = confronta_incentivi_isolamento(
                    tipo_superficie=tipo_superficie_iso,
                    posizione_isolamento=posizione_iso,
                    zona_climatica=zona_climatica_iso,
                    superficie_mq=superficie_mq_iso,
                    spesa_totale_sostenuta=spesa_totale_iso,
                    trasmittanza_post_operam=trasmittanza_post_iso,
                    tipo_soggetto=tipo_soggetto_iso,
                    combinato_con_titolo_iii=combinato_titolo_iii_iso,
                    componenti_ue=componenti_ue_iso,
                    anno_spesa=anno_spesa_iso,
                    tipo_abitazione=tipo_abitazione_iso,
                    tasso_sconto=tasso_sconto
                )

                # Mostra risultati - condizionale in base a solo_conto_termico
                ct_data = confronto_iso["risultati"]["conto_termico"]
                eco_data = confronto_iso["risultati"]["ecobonus"]
                bonus_data = confronto_iso["risultati"]["bonus_ristrutturazione"]

                if solo_conto_termico:
                    # Modalità Solo CT 3.0
                    st.markdown("### 🔥 Conto Termico 3.0")
                    if ct_data["status"] == "OK":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                label="Incentivo Totale",
                                value=f"{ct_data['incentivo_totale']:,.2f} €"
                            )
                        with col2:
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{ct_data['npv']:,.2f} €"
                            )
                        st.write(f"**Rate:** {ct_data['numero_rate']} | **Rata annuale:** {ct_data['rata_annuale']:,.2f} €")
                    else:
                        st.error(f"❌ {ct_data['messaggio']}")
                else:
                    # Modalità confronto completo
                    col_ct, col_eco, col_bonus = st.columns(3)

                    # Conto Termico 3.0
                    with col_ct:
                        st.markdown("### 🔥 Conto Termico 3.0")
                        if ct_data["status"] == "OK":
                            st.metric(
                                label="Incentivo Totale",
                                value=f"{ct_data['incentivo_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{ct_data['npv']:,.2f} €"
                            )
                            st.write(f"**Rate:** {ct_data['numero_rate']}")
                            st.write(f"**Rata annuale:** {ct_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {ct_data['messaggio']}")

                    # Ecobonus
                    with col_eco:
                        st.markdown("### 💚 Ecobonus")
                        if eco_data["status"] == "OK":
                            st.metric(
                                label="Detrazione Totale",
                                value=f"{eco_data['detrazione_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{eco_data['npv']:,.2f} €"
                            )
                            st.write(f"**Aliquota:** {eco_data['aliquota']*100:.0f}%")
                            st.write(f"**Anni:** {eco_data['anni_recupero']}")
                            st.write(f"**Rata annuale:** {eco_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {eco_data['messaggio']}")

                    # Bonus Ristrutturazione
                    with col_bonus:
                        st.markdown("### 🏗️ Bonus Ristrutturazione")
                        if bonus_data["status"] == "OK":
                            st.metric(
                                label="Detrazione Totale",
                                value=f"{bonus_data['detrazione_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{bonus_data['npv']:,.2f} €"
                            )
                            st.write(f"**Aliquota:** {bonus_data['aliquota']*100:.0f}%")
                            st.write(f"**Anni:** {bonus_data['anni_recupero']}")
                            st.write(f"**Rata annuale:** {bonus_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {bonus_data['messaggio']}")

                st.divider()

                # Raccomandazione (solo se non in modalità solo CT)
                if not solo_conto_termico:
                    st.subheader("🎯 Raccomandazione")
                    st.info(confronto_iso["raccomandazione"])

                # Grafico comparativo (solo se non in modalità solo CT)
                if not solo_conto_termico and len(confronto_iso["incentivi_validi"]) > 0:
                    st.subheader("📊 Grafico Comparativo (NPV)")

                    import plotly.graph_objects as go

                    # Prepara dati per il grafico
                    incentivi_nomi = [x[0] for x in confronto_iso["incentivi_validi"]]
                    incentivi_npv = [x[1] for x in confronto_iso["incentivi_validi"]]

                    # Crea grafico a barre
                    fig_iso = go.Figure(data=[
                        go.Bar(
                            x=incentivi_nomi,
                            y=incentivi_npv,
                            text=[f"{val:,.0f} €" for val in incentivi_npv],
                            textposition='auto',
                            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'][:len(incentivi_nomi)]
                        )
                    ])

                    fig_iso.update_layout(
                        title="Confronto NPV Incentivi",
                        xaxis_title="Incentivo",
                        yaxis_title="NPV (EUR)",
                        height=400
                    )

                    st.plotly_chart(fig_iso, use_container_width=True)

                # Salva nel session state per uso successivo
                st.session_state.ultimo_calcolo_isolamento = {
                    "tipo_superficie": tipo_superficie_iso,
                    "posizione": posizione_iso,
                    "zona_climatica": zona_climatica_iso,
                    "superficie_mq": superficie_mq_iso,
                    "spesa_totale": spesa_totale_iso,
                    "trasmittanza_post": trasmittanza_post_iso,
                    "tipo_soggetto": tipo_soggetto_iso,
                    "componenti_ue": componenti_ue_iso,
                    "combinato_titolo_iii": combinato_titolo_iii_iso,
                    "anno_spesa": anno_spesa_iso,
                    "tipo_abitazione": tipo_abitazione_iso,
                    "ct_data": ct_data,
                    "eco_data": eco_data,
                    "bonus_data": bonus_data,
                    "raccomandazione": confronto_iso.get("raccomandazione", ""),
                    "migliore": confronto_iso.get("migliore", "")
                }

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # Pulsante salva scenario isolamento (FUORI dal blocco calcola)
        st.divider()
        col_save_iso1, col_save_iso2 = st.columns([3, 1])
        with col_save_iso1:
            salva_scenario_iso = st.button(
                "💾 Salva Scenario Isolamento",
                type="secondary",
                use_container_width=True,
                key="btn_salva_iso",
                disabled=len(st.session_state.scenari_isolamento) >= 5
            )
        with col_save_iso2:
            st.write(f"({len(st.session_state.scenari_isolamento)}/5)")

        if salva_scenario_iso:
            if st.session_state.ultimo_calcolo_isolamento is None:
                st.warning("⚠️ Prima calcola gli incentivi con CALCOLA INCENTIVI")
            elif len(st.session_state.scenari_isolamento) >= 5:
                st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")
            else:
                dati = st.session_state.ultimo_calcolo_isolamento
                ct_data = dati["ct_data"]
                eco_data = dati["eco_data"]
                bonus_data = dati["bonus_data"]
                nuovo_scenario = {
                    "id": len(st.session_state.scenari_isolamento) + 1,
                    "nome": f"Isolamento {len(st.session_state.scenari_isolamento) + 1}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "tipo_superficie": dati["tipo_superficie"],
                    "posizione": dati["posizione"],
                    "zona_climatica": dati["zona_climatica"],
                    "superficie_mq": dati["superficie_mq"],
                    "spesa_totale": dati["spesa_totale"],
                    "trasmittanza_post": dati["trasmittanza_post"],
                    "tipo_soggetto": dati["tipo_soggetto"],
                    "componenti_ue": dati["componenti_ue"],
                    "combinato_titolo_iii": dati["combinato_titolo_iii"],
                    "ct_incentivo": ct_data.get("incentivo_totale", 0) if ct_data["status"] == "OK" else 0,
                    "ct_npv": ct_data.get("npv", 0) if ct_data["status"] == "OK" else 0,
                    "eco_detrazione": eco_data.get("detrazione_totale", 0) if eco_data["status"] == "OK" else 0,
                    "eco_npv": eco_data.get("npv", 0) if eco_data["status"] == "OK" else 0,
                    "bonus_detrazione": bonus_data.get("detrazione_totale", 0) if bonus_data["status"] == "OK" else 0,
                    "bonus_npv": bonus_data.get("npv", 0) if bonus_data["status"] == "OK" else 0,
                    "migliore": dati["migliore"]
                }
                st.session_state.scenari_isolamento.append(nuovo_scenario)
                st.success(f"✅ Scenario salvato! ({len(st.session_state.scenari_isolamento)}/5)")
                st.rerun()

    # ===========================================================================
    # TAB SERRAMENTI: SOSTITUZIONE SERRAMENTI
    # ===========================================================================
    with tab_serramenti:
        st.header("🪟 Sostituzione Serramenti - Confronto Incentivi")
        st.write("Confronta Conto Termico 3.0, Ecobonus e Bonus Ristrutturazione per sostituzione serramenti")

        st.divider()

        # Importa i moduli necessari
        from modules.calculator_serramenti import calculate_windows_incentive, confronta_incentivi_serramenti
        from modules.validator_serramenti import valida_requisiti_serramenti

        # Sezione Input Dati
        st.subheader("📋 Dati Intervento")

        col1, col2 = st.columns(2)

        with col1:
            # Selezione Regione/Provincia per zona climatica
            st.markdown("**Localizzazione**")

            lista_regioni_serr = get_lista_regioni()
            regione_serr = st.selectbox(
                "Regione",
                options=lista_regioni_serr,
                index=lista_regioni_serr.index("Lombardia") if "Lombardia" in lista_regioni_serr else 0,
                key="serr_regione",
                help="Seleziona la regione dell'immobile"
            )

            province_serr = get_province_by_regione(regione_serr)
            province_nomi_serr = [f"{nome} ({sigla})" for sigla, nome in province_serr]

            if province_nomi_serr:
                provincia_display_serr = st.selectbox(
                    "Provincia",
                    options=province_nomi_serr,
                    index=0,
                    key="serr_provincia",
                    help="Seleziona la provincia - determina automaticamente la zona climatica"
                )

                # Estrai sigla e determina zona climatica
                provincia_sigla_serr = provincia_display_serr.split("(")[-1].rstrip(")")
                zona_climatica_serr_auto = get_zona_climatica(provincia_sigla_serr)

                # Opzione per modifica manuale
                modifica_manuale_serr = st.checkbox(
                    "✏️ Modifica zona manualmente",
                    value=False,
                    key="serr_modifica_zona",
                    help="Attiva per modificare manualmente la zona climatica del comune"
                )

                if modifica_manuale_serr:
                    zona_climatica_serr = st.selectbox(
                        "Zona climatica",
                        options=["A", "B", "C", "D", "E", "F"],
                        index=["A", "B", "C", "D", "E", "F"].index(zona_climatica_serr_auto),
                        key="serr_zona_manuale",
                        help="Seleziona manualmente la zona climatica"
                    )
                    st.warning(f"⚠️ Zona manuale: **{zona_climatica_serr}** (automatica era: {zona_climatica_serr_auto})")
                else:
                    zona_climatica_serr = zona_climatica_serr_auto
                    st.success(f"🌡️ Zona Climatica: **{zona_climatica_serr}**")
            else:
                zona_climatica_serr = "E"
                st.warning("⚠️ Zona E (default)")

            superficie_mq_serr = st.number_input(
                "Superficie serramenti (m²)",
                min_value=5.0,
                max_value=1000.0,
                value=50.0,
                step=5.0,
                key="serr_superficie_mq",
                help="Superficie totale dei serramenti da sostituire"
            )

            trasmittanza_post_serr = st.number_input(
                "Trasmittanza post-intervento (W/m²K)",
                min_value=0.80,
                max_value=3.00,
                value=1.20,
                step=0.05,
                format="%.2f",
                key="serr_trasmittanza",
                help="Trasmittanza termica dei nuovi serramenti"
            )

        with col2:
            spesa_totale_serr = st.number_input(
                "Spesa totale sostenuta (EUR)",
                min_value=1000.0,
                max_value=500000.0,
                value=25000.0,
                step=1000.0,
                key="serr_spesa_totale",
                help="Spesa totale IVA inclusa per i nuovi serramenti"
            )

            ha_termoregolazione_serr = st.checkbox(
                "Sistemi termoregolazione presenti",
                value=True,
                key="serr_termoregolazione",
                help="Sistemi di termoregolazione o valvole termostatiche OBBLIGATORI (installati o già presenti)"
            )

            anno_spesa_serr = st.selectbox(
                "Anno di spesa",
                options=[2024, 2025, 2026, 2027],
                index=1,  # Default: 2025
                key="serr_anno_spesa"
            )

            tipo_abitazione_serr = st.selectbox(
                "Tipo abitazione",
                options=["abitazione_principale", "altra_abitazione"],
                format_func=lambda x: "Abitazione principale" if x == "abitazione_principale" else "Altra abitazione",
                key="serr_tipo_abitazione"
            )

        st.divider()

        # Sezione Premialità e Opzioni
        st.subheader("🎁 Premialità e Opzioni")

        col_prem1, col_prem2, col_prem3 = st.columns(3)

        with col_prem1:
            componenti_ue_serr = st.checkbox(
                "Componenti UE (+10%)",
                value=False,
                key="serr_componenti_ue",
                help="Premialità del 10% se i componenti sono prodotti nell'Unione Europea"
            )

        with col_prem2:
            combinato_isolamento_serr = st.checkbox(
                "Combinato con II.A (Isolamento)",
                value=False,
                key="serr_combinato_isolamento",
                help="Intervento combinato con isolamento termico (II.A)"
            )

        with col_prem3:
            combinato_titolo_iii_serr = st.checkbox(
                "Combinato con Titolo III",
                value=False,
                key="serr_combinato_titolo_iii",
                help="Combinato con interventi Titolo III (PdC, biomassa, solare)"
            )

            if combinato_titolo_iii_serr:
                with st.expander("ℹ️ Quali interventi Titolo III sono ammessi?"):
                    st.markdown("""
                    Gli interventi **Titolo III** che danno diritto al **55%** (40% + 15%) per serramenti sono:

                    - **III.A** - Pompe di Calore (elettriche/gas, aero/geo/idro)
                    - **III.B** - Sistemi Ibridi (factory made o bivalenti)
                    - **III.C** - Generatori a Biomassa (caldaie, stufe, termocamini)
                    - **III.E** - Scaldacqua a Pompa di Calore

                    ⚠️ **Nota**: Il solare termico (III.D) **NON** dà diritto al bonus 55%

                    📋 **Requisito**: Deve essere combinato anche con isolamento termico (II.A)
                    """)

        # Mostra premialità 55% solo se entrambi checkbox sono attivi
        if combinato_isolamento_serr and combinato_titolo_iii_serr:
            st.success("✅ **Premialità 55%**: Intervento II.B + II.A + Titolo III")
            with st.expander("ℹ️ Come funziona la premialità 55%?"):
                st.markdown("""
                La percentuale del **55%** si ottiene quando l'intervento di sostituzione serramenti (II.B)
                è **combinato** con:

                - **II.A** - Isolamento Termico (coperture, pavimenti, pareti)
                - **Titolo III** - Interventi su impianti termici (PdC, biomassa, solare)

                ⚠️ **Nota**: Devono essere presenti **ENTRAMBI** gli interventi (II.A + Titolo III)
                oltre ai serramenti (II.B) per ottenere il 55%.
                """)

        col_sogg = st.columns(3)[0]
        with col_sogg:
            tipo_soggetto_serr = st.selectbox(
                "Tipo soggetto",
                options=["privato", "PA"],
                format_func=lambda x: "Privato/Condominio" if x == "privato" else "Pubblica Amministrazione",
                key="serr_tipo_soggetto"
            )

        st.divider()

        # Pulsante calcola
        calcola_serr = st.button("🔍 Calcola Incentivi", key="btn_calcola_serr", type="primary", use_container_width=True)

        if calcola_serr:

            # Verifica vincoli terziario CT 3.0 (Punto 3)
            ammissibile_vincoli, msg_vincoli = applica_vincoli_terziario_ct3(
                tipo_intervento_app="serramenti",
                tipo_soggetto_label=tipo_soggetto_principale
            )

            if not ammissibile_vincoli:
                st.error(f"🚫 {msg_vincoli}")
                st.stop()
            elif msg_vincoli:
                st.warning(f"⚠️ {msg_vincoli}")

            # Validazione requisiti tecnici
            st.subheader("✅ Validazione Requisiti Tecnici")

            validazione_result_serr = valida_requisiti_serramenti(
                zona_climatica=zona_climatica_serr,
                trasmittanza_post_operam=trasmittanza_post_serr,
                superficie_mq=superficie_mq_serr,
                ha_termoregolazione=ha_termoregolazione_serr,
                ha_ape_post_operam=True,  # Assumiamo presente
                potenza_impianto_kw=100.0  # Assumiamo < 200 kW
            )

            if validazione_result_serr["ammissibile"]:
                punteggio_serr = validazione_result_serr['punteggio']
                if punteggio_serr == 100:
                    st.success(f"✅ **Requisiti CT 3.0: AMMISSIBILE** (Punteggio: {punteggio_serr}%)")
                else:
                    st.success(f"✅ **Requisiti CT 3.0: AMMISSIBILE** (Punteggio: {punteggio_serr}%)")
                    st.info(f"ℹ️ **Perché {punteggio_serr}% e non 100%?** Ci sono avvisi o suggerimenti che riducono il punteggio (vedi sotto):")
            else:
                st.error("❌ **Requisiti CT 3.0: NON AMMISSIBILE**")
                for err in validazione_result_serr["errori"]:
                    st.error(f"- {err}")

            if validazione_result_serr["warnings"]:
                st.warning("**⚠️ AVVISI:**")
                for warn in validazione_result_serr["warnings"]:
                    st.warning(f"  • {warn}")

            if validazione_result_serr["suggerimenti"]:
                st.info("**💡 SUGGERIMENTI:**")
                for sugg in validazione_result_serr["suggerimenti"]:
                    st.info(f"  • {sugg}")

            st.divider()

            # Confronto tra incentivi
            st.subheader("💰 Confronto Incentivi")

            try:
                # Determina se combinato con II.A + Titolo III per il 55%
                combinato_bonus = combinato_isolamento_serr and combinato_titolo_iii_serr

                confronto_serr = confronta_incentivi_serramenti(
                    zona_climatica=zona_climatica_serr,
                    superficie_mq=superficie_mq_serr,
                    spesa_totale_sostenuta=spesa_totale_serr,
                    trasmittanza_post_operam=trasmittanza_post_serr,
                    ha_termoregolazione=ha_termoregolazione_serr,
                    tipo_soggetto=tipo_soggetto_serr,
                    combinato_con_isolamento=combinato_isolamento_serr,
                    combinato_con_titolo_iii=combinato_titolo_iii_serr,
                    componenti_ue=componenti_ue_serr,
                    anno_spesa=anno_spesa_serr,
                    tipo_abitazione=tipo_abitazione_serr,
                    tasso_sconto=tasso_sconto
                )

                # Mostra risultati - condizionale in base a solo_conto_termico
                ct_data = confronto_serr["risultati"]["conto_termico"]
                eco_data = confronto_serr["risultati"]["ecobonus"]
                bonus_data = confronto_serr["risultati"]["bonus_ristrutturazione"]

                if solo_conto_termico:
                    # Modalità Solo CT 3.0
                    st.markdown("### 🔥 Conto Termico 3.0")
                    if ct_data["status"] == "OK":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                label="Incentivo Totale",
                                value=f"{ct_data['incentivo_totale']:,.2f} €"
                            )
                        with col2:
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{ct_data['npv']:,.2f} €"
                            )
                        st.write(f"**Rate:** {ct_data['numero_rate']} | **Rata annuale:** {ct_data['rata_annuale']:,.2f} €")
                    else:
                        st.error(f"❌ {ct_data['messaggio']}")
                else:
                    # Modalità confronto completo
                    col_ct, col_eco, col_bonus = st.columns(3)

                    # Conto Termico 3.0
                    with col_ct:
                        st.markdown("### 🔥 Conto Termico 3.0")
                        if ct_data["status"] == "OK":
                            st.metric(
                                label="Incentivo Totale",
                                value=f"{ct_data['incentivo_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{ct_data['npv']:,.2f} €"
                            )
                            st.write(f"**Rate:** {ct_data['numero_rate']}")
                            st.write(f"**Rata annuale:** {ct_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {ct_data['messaggio']}")

                    # Ecobonus
                    with col_eco:
                        st.markdown("### 💚 Ecobonus")
                        if eco_data["status"] == "OK":
                            st.metric(
                                label="Detrazione Totale",
                                value=f"{eco_data['detrazione_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{eco_data['npv']:,.2f} €"
                            )
                            st.write(f"**Aliquota:** {eco_data['aliquota']*100:.0f}%")
                            st.write(f"**Anni:** {eco_data['anni_recupero']}")
                            st.write(f"**Rata annuale:** {eco_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {eco_data['messaggio']}")

                    # Bonus Ristrutturazione
                    with col_bonus:
                        st.markdown("### 🏗️ Bonus Ristrutturazione")
                        if bonus_data["status"] == "OK":
                            st.metric(
                                label="Detrazione Totale",
                                value=f"{bonus_data['detrazione_totale']:,.2f} €"
                            )
                            st.metric(
                                label="NPV (Valore Attuale)",
                                value=f"{bonus_data['npv']:,.2f} €"
                            )
                            st.write(f"**Aliquota:** {bonus_data['aliquota']*100:.0f}%")
                            st.write(f"**Anni:** {bonus_data['anni_recupero']}")
                            st.write(f"**Rata annuale:** {bonus_data['rata_annuale']:,.2f} €")
                        else:
                            st.error(f"❌ {bonus_data['messaggio']}")

                st.divider()

                # Raccomandazione (solo se non in modalità solo CT)
                if not solo_conto_termico:
                    st.subheader("🎯 Raccomandazione")
                    st.info(confronto_serr["raccomandazione"])

                # Grafico comparativo (solo se non in modalità solo CT)
                if not solo_conto_termico and len(confronto_serr["incentivi_validi"]) > 0:
                    st.subheader("📊 Grafico Comparativo (NPV)")

                    import plotly.graph_objects as go

                    # Prepara dati per il grafico
                    incentivi_nomi = [x[0] for x in confronto_serr["incentivi_validi"]]
                    incentivi_npv = [x[1] for x in confronto_serr["incentivi_validi"]]

                    # Crea grafico a barre
                    fig_serr = go.Figure(data=[
                        go.Bar(
                            x=incentivi_nomi,
                            y=incentivi_npv,
                            text=[f"{val:,.0f} €" for val in incentivi_npv],
                            textposition='auto',
                            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'][:len(incentivi_nomi)]
                        )
                    ])

                    fig_serr.update_layout(
                        title="Confronto NPV Incentivi - Serramenti",
                        xaxis_title="Incentivo",
                        yaxis_title="NPV (EUR)",
                        height=400
                    )

                    st.plotly_chart(fig_serr, use_container_width=True)

                # Salva nel session state per uso successivo
                st.session_state.ultimo_calcolo_serramenti = {
                    "zona_climatica": zona_climatica_serr,
                    "superficie_mq": superficie_mq_serr,
                    "trasmittanza_post": trasmittanza_post_serr,
                    "spesa_totale": spesa_totale_serr,
                    "tipo_soggetto": tipo_soggetto_serr,
                    "ha_termoregolazione": ha_termoregolazione_serr,
                    "componenti_ue": componenti_ue_serr,
                    "combinato_isolamento": combinato_isolamento_serr,
                    "combinato_titolo_iii": combinato_titolo_iii_serr,
                    "anno_spesa": anno_spesa_serr,
                    "tipo_abitazione": tipo_abitazione_serr,
                    "ct_data": ct_data,
                    "eco_data": eco_data,
                    "bonus_data": bonus_data,
                    "raccomandazione": confronto_serr.get("raccomandazione", ""),
                    "migliore": confronto_serr.get("migliore", "")
                }

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # Pulsante salva scenario serramenti (FUORI dal blocco calcola)
        st.divider()
        col_save_serr1, col_save_serr2 = st.columns([3, 1])
        with col_save_serr1:
            salva_scenario_serr = st.button(
                "💾 Salva Scenario Serramenti",
                type="secondary",
                use_container_width=True,
                key="btn_salva_serr",
                disabled=len(st.session_state.scenari_serramenti) >= 5
            )
        with col_save_serr2:
            st.write(f"({len(st.session_state.scenari_serramenti)}/5)")

        if salva_scenario_serr:
            if st.session_state.ultimo_calcolo_serramenti is None:
                st.warning("⚠️ Prima calcola gli incentivi con CALCOLA INCENTIVI")
            elif len(st.session_state.scenari_serramenti) >= 5:
                st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")
            else:
                dati = st.session_state.ultimo_calcolo_serramenti
                ct_data = dati["ct_data"]
                eco_data = dati["eco_data"]
                bonus_data = dati["bonus_data"]
                nuovo_scenario = {
                    "id": len(st.session_state.scenari_serramenti) + 1,
                    "nome": f"Serramenti {len(st.session_state.scenari_serramenti) + 1}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "zona_climatica": dati["zona_climatica"],
                    "superficie_mq": dati["superficie_mq"],
                    "trasmittanza_post": dati["trasmittanza_post"],
                    "spesa_totale": dati["spesa_totale"],
                    "tipo_soggetto": dati["tipo_soggetto"],
                    "ha_termoregolazione": dati["ha_termoregolazione"],
                    "componenti_ue": dati["componenti_ue"],
                    "combinato_isolamento": dati["combinato_isolamento"],
                    "combinato_titolo_iii": dati["combinato_titolo_iii"],
                    "ct_incentivo": ct_data.get("incentivo_totale", 0) if ct_data["status"] == "OK" else 0,
                    "ct_npv": ct_data.get("npv", 0) if ct_data["status"] == "OK" else 0,
                    "eco_detrazione": eco_data.get("detrazione_totale", 0) if eco_data["status"] == "OK" else 0,
                    "eco_npv": eco_data.get("npv", 0) if eco_data["status"] == "OK" else 0,
                    "bonus_detrazione": bonus_data.get("detrazione_totale", 0) if bonus_data["status"] == "OK" else 0,
                    "bonus_npv": bonus_data.get("npv", 0) if bonus_data["status"] == "OK" else 0,
                    "migliore": dati["migliore"]
                }
                st.session_state.scenari_serramenti.append(nuovo_scenario)
                st.success(f"✅ Scenario salvato! ({len(st.session_state.scenari_serramenti)}/5)")
                st.rerun()

    # ===========================================================================
    # TAB 7: SCHERMATURE SOLARI (II.C)
    # ===========================================================================
    with tab_schermature:
        st.header("🌤️ Schermature Solari - Confronto Incentivi")
        st.caption("Intervento II.C - Schermature, ombreggiamento, pellicole solari")

        st.divider()

        # Import moduli
        from modules.validator_schermature import valida_requisiti_schermature
        from modules.calculator_schermature import calculate_shading_incentive, confronta_incentivi_schermature

        # Sezione Input Dati
        st.subheader("📋 Dati Intervento")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Tipologie da Installare**")

            installa_scherm = st.checkbox(
                "Schermature fisse/mobili (tende, pergole, ecc.)",
                value=True,
                key="scherm_installa_schermature",
                help="Tende da sole, pergole, schermature esterne mobili o fisse"
            )

            installa_auto = st.checkbox(
                "Automazione (meccanismi automatici)",
                value=False,
                key="scherm_installa_automazione",
                help="Sistemi automatici di regolazione basati su radiazione solare"
            )

            installa_pell = st.checkbox(
                "Pellicole solari",
                value=False,
                key="scherm_installa_pellicole",
                help="Pellicole basso-emissive per filtrazione solare"
            )

        with col2:
            st.markdown("**Requisiti Generali**")

            esposizione_ok = st.checkbox(
                "Esposizione Est-Sud-Est → Ovest",
                value=True,
                key="scherm_esposizione",
                help="Le schermature devono essere su chiusure con esposizione da Est-Sud-Est a Ovest (passando per Sud)"
            )

            st.info("ℹ️ **REQUISITO OBBLIGATORIO CT 3.0**: Abbinamento con serramenti (II.B)")

            serramenti_conformi = st.checkbox(
                "Serramenti già conformi al DM 26/06/2015",
                value=False,
                key="scherm_serramenti_conformi",
                help="I serramenti esistenti rispettano già i requisiti di trasmittanza"
            )

            abbinato_iib = st.checkbox(
                "Abbinato a sostituzione serramenti (II.B)",
                value=False,
                key="scherm_abbinato_iib",
                help="L'intervento è abbinato alla sostituzione dei serramenti"
            )

        st.divider()

        # Dati specifici per ciascuna tipologia
        if installa_scherm:
            st.subheader("🪟 Schermature Fisse/Mobili")
            col_s1, col_s2, col_s3 = st.columns(3)

            with col_s1:
                superficie_scherm = st.number_input(
                    "Superficie (m²)",
                    min_value=0.0,
                    max_value=10000.0,
                    value=50.0,
                    step=1.0,
                    key="scherm_superficie_scherm",
                    help="Superficie totale delle chiusure trasparenti oggetto di schermatura"
                )

            with col_s2:
                spesa_scherm = st.number_input(
                    "Spesa sostenuta (€)",
                    min_value=0.0,
                    max_value=1000000.0,
                    value=10000.0,
                    step=100.0,
                    format="%.2f",
                    key="scherm_spesa_scherm",
                    help="Spesa totale per fornitura e posa schermature (IVA inclusa se costo)"
                )

            with col_s3:
                st.markdown("**Classe Prestazione Solare**")
                classe_solare = st.selectbox(
                    "Classe (UNI EN 14501)",
                    options=[3, 4],
                    index=0,
                    key="scherm_classe",
                    help="Classe minima richiesta: 3 o superiore"
                )

                with st.expander("ℹ️ Come verificare la classe?"):
                    st.markdown("""
                    La **classe di prestazione solare** si trova:

                    1. **Certificazione del produttore**: Dichiarazione conforme a UNI EN 14501
                    2. **Scheda tecnica prodotto**: Sezione prestazioni energetiche
                    3. **Certificazione Solar Keymark** (se applicabile)

                    La prestazione è valutata con **UNI EN ISO 52022-1:2018**

                    **Classe 3**: Prestazione buona (gtot ≤ 0.35)
                    **Classe 4**: Prestazione elevata (gtot ≤ 0.15)
                    """)

            # Mostra costo specifico
            if superficie_scherm > 0:
                costo_spec_scherm = spesa_scherm / superficie_scherm
                max_ammesso_scherm = 250.0
                if costo_spec_scherm > max_ammesso_scherm:
                    st.warning(f"⚠️ Costo specifico: {costo_spec_scherm:.2f} €/m² (max ammissibile CT 3.0: {max_ammesso_scherm} €/m²)")
                else:
                    st.success(f"✅ Costo specifico: {costo_spec_scherm:.2f} €/m² (entro limite {max_ammesso_scherm} €/m²)")

        if installa_auto:
            st.subheader("🤖 Automazione")
            col_a1, col_a2, col_a3 = st.columns(3)

            with col_a1:
                superficie_auto = st.number_input(
                    "Superficie (m²)",
                    min_value=0.0,
                    max_value=10000.0,
                    value=50.0,
                    step=1.0,
                    key="scherm_superficie_auto",
                    help="Superficie schermature automatizzate"
                )

            with col_a2:
                spesa_auto = st.number_input(
                    "Spesa sostenuta (€)",
                    min_value=0.0,
                    max_value=100000.0,
                    value=2000.0,
                    step=100.0,
                    format="%.2f",
                    key="scherm_spesa_auto",
                    help="Spesa per meccanismi automatici"
                )

            with col_a3:
                ha_rilevaz_rad = st.checkbox(
                    "Rilevazione radiazione solare",
                    value=True,
                    key="scherm_rilevazione",
                    help="OBBLIGATORIO: Sensori di radiazione solare (UNI EN 15232)"
                )

            # Mostra costo specifico
            if superficie_auto > 0:
                costo_spec_auto = spesa_auto / superficie_auto
                max_ammesso_auto = 50.0
                if costo_spec_auto > max_ammesso_auto:
                    st.warning(f"⚠️ Costo specifico: {costo_spec_auto:.2f} €/m² (max ammissibile CT 3.0: {max_ammesso_auto} €/m²)")
                else:
                    st.success(f"✅ Costo specifico: {costo_spec_auto:.2f} €/m² (entro limite {max_ammesso_auto} €/m²)")

        if installa_pell:
            st.subheader("🎞️ Pellicole Solari")
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)

            with col_p1:
                tipo_pell = st.selectbox(
                    "Tipo pellicola",
                    options=["selettiva_non_riflettente", "selettiva_riflettente"],
                    format_func=lambda x: "Selettiva non riflettente" if x == "selettiva_non_riflettente" else "Selettiva riflettente",
                    key="scherm_tipo_pellicola",
                    help="Tipo di pellicola solare"
                )

            with col_p2:
                superficie_pell = st.number_input(
                    "Superficie (m²)",
                    min_value=0.0,
                    max_value=10000.0,
                    value=30.0,
                    step=1.0,
                    key="scherm_superficie_pell",
                    help="Superficie vetrate con pellicole"
                )

            with col_p3:
                spesa_pell = st.number_input(
                    "Spesa sostenuta (€)",
                    min_value=0.0,
                    max_value=500000.0,
                    value=3000.0,
                    step=100.0,
                    format="%.2f",
                    key="scherm_spesa_pell",
                    help="Spesa per pellicole solari"
                )

            with col_p4:
                gtot_pell = st.number_input(
                    "Fattore solare g_tot",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.30,
                    step=0.01,
                    format="%.3f",
                    key="scherm_gtot",
                    help="Fattore solare totale (certificazione produttore)"
                )

            # Mostra costo specifico
            if superficie_pell > 0:
                costo_spec_pell = spesa_pell / superficie_pell
                max_ammesso_pell = 130.0 if tipo_pell == "selettiva_non_riflettente" else 80.0
                if costo_spec_pell > max_ammesso_pell:
                    st.warning(f"⚠️ Costo specifico: {costo_spec_pell:.2f} €/m² (max ammissibile CT 3.0: {max_ammesso_pell} €/m²)")
                else:
                    st.success(f"✅ Costo specifico: {costo_spec_pell:.2f} €/m² (entro limite {max_ammesso_pell} €/m²)")

        st.divider()

        # Parametri aggiuntivi
        st.subheader("⚙️ Parametri Aggiuntivi")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            potenza_imp = st.number_input(
                "Potenza impianto riscaldamento (kW)",
                min_value=0.0,
                max_value=10000.0,
                value=50.0,
                step=1.0,
                key="scherm_potenza",
                help="Se P ≥ 200 kW sono obbligatori APE post + Diagnosi ante"
            )

            if potenza_imp >= 200:
                st.warning("⚠️ P ≥ 200 kW: APE post + Diagnosi ante OBBLIGATORIE")
                ha_ape_post_scherm = st.checkbox("APE post-operam", value=True, key="scherm_ape_post")
                ha_diagn_ante_scherm = st.checkbox("Diagnosi ante-operam", value=True, key="scherm_diagn_ante")
            else:
                ha_ape_post_scherm = None
                ha_diagn_ante_scherm = None

        with col_p2:
            # Per imprese/ETS su terziario
            if tipo_soggetto in ["impresa", "ets_economico"]:
                edificio_terz = st.checkbox(
                    "Edificio terziario",
                    value=False,
                    key="scherm_terziario",
                    help="Se SÌ, richiesta riduzione energia primaria ≥ 10-20%"
                )

                if edificio_terz:
                    riduz_energ = st.number_input(
                        "Riduzione energia primaria (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=15.0,
                        step=1.0,
                        key="scherm_riduzione",
                        help="≥ 10% (intervento singolo) o ≥ 20% (multi-intervento)"
                    )

                    ha_ape_ante_post_scherm = st.checkbox(
                        "APE ante + post per verifica riduzione",
                        value=True,
                        key="scherm_ape_verifica"
                    )
                else:
                    riduz_energ = 0.0
                    ha_ape_ante_post_scherm = False
            else:
                edificio_terz = False
                riduz_energ = 0.0
                ha_ape_ante_post_scherm = False

            # Premialità UE
            usa_prem_ue_scherm = st.checkbox(
                "Componenti prodotti in UE (+10%)",
                value=False,
                key="scherm_ue",
                help="Premialità +10% se i componenti principali sono prodotti nell'Unione Europea"
            )

        st.divider()

        # Pulsante calcolo
        if st.button("🌤️ Calcola Confronto Schermature", type="primary", use_container_width=True, key="scherm_calcola"):
            try:
                # Verifica vincoli terziario CT 3.0 (Punto 3)
                ammissibile_vincoli_scherm, msg_vincoli_scherm = applica_vincoli_terziario_ct3(
                    tipo_intervento_app="schermature_solari",
                    tipo_soggetto_label=tipo_soggetto_principale
                )

                if not ammissibile_vincoli_scherm:
                    st.error(f"🚫 {msg_vincoli_scherm}")
                    st.stop()
                elif msg_vincoli_scherm:
                    st.warning(f"⚠️ {msg_vincoli_scherm}")

                # Validazione
                st.subheader("✅ Validazione Requisiti")

                validazione_scherm = valida_requisiti_schermature(
                    installa_schermature=installa_scherm,
                    superficie_schermature_mq=superficie_scherm if installa_scherm else 0.0,
                    spesa_schermature=spesa_scherm if installa_scherm else 0.0,
                    classe_prestazione_solare=classe_solare if installa_scherm else 3,
                    installa_automazione=installa_auto,
                    superficie_automazione_mq=superficie_auto if installa_auto else 0.0,
                    spesa_automazione=spesa_auto if installa_auto else 0.0,
                    ha_rilevazione_radiazione=ha_rilevaz_rad if installa_auto else False,
                    installa_pellicole=installa_pell,
                    tipo_pellicola=tipo_pell if installa_pell else "selettiva_non_riflettente",
                    superficie_pellicole_mq=superficie_pell if installa_pell else 0.0,
                    spesa_pellicole=spesa_pell if installa_pell else 0.0,
                    fattore_solare_gtot=gtot_pell if installa_pell else 0.0,
                    esposizione_valida=esposizione_ok,
                    serramenti_gia_conformi=serramenti_conformi,
                    abbinato_intervento_iib=abbinato_iib,
                    potenza_impianto_kw=potenza_imp,
                    ha_diagnosi_ante_operam=ha_diagn_ante_scherm,
                    ha_ape_post_operam=ha_ape_post_scherm,
                    tipo_soggetto=tipo_soggetto,
                    edificio_terziario=edificio_terz,
                    riduzione_energia_primaria_pct=riduz_energ,
                    ha_ape_ante_post=ha_ape_ante_post_scherm,
                    tipo_edificio="pubblico" if tipo_soggetto == "pa" else "residenziale"
                )

                if not validazione_scherm["ammissibile"]:
                    st.error("❌ **Intervento NON ammissibile**")
                    for err in validazione_scherm["errori"]:
                        st.error(f"• {err}")
                    if validazione_scherm["warnings"]:
                        st.warning("**Attenzioni:**")
                        for warn in validazione_scherm["warnings"]:
                            st.warning(f"• {warn}")
                else:
                    punteggio_scherm = validazione_scherm['punteggio']
                    if punteggio_scherm == 100:
                        st.success(f"✅ **Intervento ammissibile** - Punteggio: {punteggio_scherm}/100")
                    else:
                        st.success(f"✅ **Intervento ammissibile** - Punteggio: {punteggio_scherm}/100")
                        st.info(f"ℹ️ **Perché {punteggio_scherm}/100 e non 100/100?** Ci sono avvisi o suggerimenti che riducono il punteggio (vedi sotto):")

                    if validazione_scherm["warnings"]:
                        st.warning("**⚠️ AVVISI:**")
                        for warn in validazione_scherm["warnings"]:
                            st.warning(f"  • {warn}")

                    if validazione_scherm["suggerimenti"]:
                        st.info("**💡 SUGGERIMENTI:**")
                        for sug in validazione_scherm["suggerimenti"]:
                            st.info(f"  • {sug}")

                    st.divider()

                    # Confronto incentivi
                    st.subheader("💰 Confronto Incentivi")

                    confronto_scherm = confronta_incentivi_schermature(
                        installa_schermature=installa_scherm,
                        superficie_schermature_mq=superficie_scherm if installa_scherm else 0.0,
                        spesa_schermature=spesa_scherm if installa_scherm else 0.0,
                        installa_automazione=installa_auto,
                        superficie_automazione_mq=superficie_auto if installa_auto else 0.0,
                        spesa_automazione=spesa_auto if installa_auto else 0.0,
                        installa_pellicole=installa_pell,
                        tipo_pellicola=tipo_pell if installa_pell else "selettiva_non_riflettente",
                        superficie_pellicole_mq=superficie_pell if installa_pell else 0.0,
                        spesa_pellicole=spesa_pell if installa_pell else 0.0,
                        tipo_soggetto=tipo_soggetto,
                        tipo_edificio="pubblico" if tipo_soggetto == "pa" else "residenziale",
                        usa_premialita_componenti_ue=usa_prem_ue_scherm,
                        anno_spesa=anno,
                        tipo_abitazione=tipo_abitazione,
                        tasso_sconto=0.03
                    )

                    # Display risultati
                    col_ct, col_eco = st.columns(2)

                    with col_ct:
                        st.markdown("### 🏦 Conto Termico 3.0")
                        if confronto_scherm["ct_3_0"] and "errore" not in confronto_scherm["ct_3_0"]:
                            ct_data = confronto_scherm["ct_3_0"]
                            st.metric("Incentivo Totale", f"{ct_data['incentivo_totale']:,.2f} €")
                            st.write(f"📊 **{ct_data['percentuale_spesa']:.1f}%** della spesa")
                            st.write(f"⏱️ **{ct_data['annualita']}** {'anno' if ct_data['annualita'] == 1 else 'anni'}")
                            st.write(f"💰 Rata: **{ct_data['rata_annuale']:,.2f} €**")
                            st.write(f"📈 NPV (3%): **{ct_data['npv']:,.2f} €**")
                        else:
                            st.error("Errore calcolo CT 3.0")

                    with col_eco:
                        st.markdown("### 📋 Ecobonus")
                        if confronto_scherm["ecobonus"] and "errore" not in confronto_scherm["ecobonus"]:
                            eco_data = confronto_scherm["ecobonus"]
                            st.metric("Detrazione Totale", f"{eco_data['detrazione_totale']:,.2f} €")
                            st.write(f"📊 **{eco_data['percentuale_spesa']:.1f}%** della spesa")
                            st.write(f"⏱️ **10 anni**")
                            st.write(f"💰 Rata: **{eco_data['rata_annuale']:,.2f} €**")
                            st.write(f"📈 NPV (3%): **{eco_data['npv']:,.2f} €**")
                            st.info(eco_data["note"])
                        else:
                            st.error("Errore calcolo Ecobonus")

                    # Grafico NPV
                    if confronto_scherm["ct_3_0"] and confronto_scherm["ecobonus"]:
                        st.divider()
                        st.subheader("📊 Confronto NPV (Valore Attuale Netto)")

                        import plotly.graph_objects as go

                        fig = go.Figure(data=[
                            go.Bar(
                                name='CT 3.0',
                                x=['Conto Termico 3.0'],
                                y=[confronto_scherm['npv_ct']],
                                marker_color='#4CAF50',
                                text=[f"{confronto_scherm['npv_ct']:,.0f} €"],
                                textposition='outside'
                            ),
                            go.Bar(
                                name='Ecobonus',
                                x=['Ecobonus'],
                                y=[confronto_scherm['npv_ecobonus']],
                                marker_color='#2196F3',
                                text=[f"{confronto_scherm['npv_ecobonus']:,.0f} €"],
                                textposition='outside'
                            )
                        ])

                        fig.update_layout(
                            title="Valore Attuale Netto (NPV) - Tasso sconto 3%",
                            yaxis_title="NPV (€)",
                            showlegend=False,
                            height=400
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        # Raccomandazione
                        if confronto_scherm["miglior_incentivo"]:
                            if confronto_scherm["miglior_incentivo"] == "CT 3.0":
                                st.success(f"✅ **CONSIGLIATO: CONTO TERMICO 3.0** - NPV superiore di {confronto_scherm['npv_ct'] - confronto_scherm['npv_ecobonus']:,.0f} €")
                            else:
                                st.info(f"📋 **CONSIGLIATO: ECOBONUS** - NPV superiore di {confronto_scherm['npv_ecobonus'] - confronto_scherm['npv_ct']:,.0f} €")

                        st.info("ℹ️ **Nota**: Bonus Ristrutturazione NON è applicabile per le schermature solari. Sono ammessi solo CT 3.0 ed Ecobonus.")

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # ===========================================================================
    # TAB 8: ILLUMINAZIONE LED
    # ===========================================================================
    with tab_illuminazione:
        st.header("💡 Illuminazione LED - Calcolo Incentivi")
        st.caption("Intervento II.E - Sostituzione sistemi di illuminazione con LED ad alta efficienza")

        st.info(
            "ℹ️ **Nota importante**: L'illuminazione LED rientra **SOLO nel Conto Termico 3.0**. "
            "NON è ammessa per Ecobonus né per Bonus Ristrutturazione."
        )

        # Import moduli illuminazione
        from modules.validator_illuminazione import valida_requisiti_illuminazione
        from modules.calculator_illuminazione import calculate_lighting_incentive

        # --- INPUT UTENTE ---
        st.subheader("📊 Dati Intervento")

        col1, col2 = st.columns(2)

        with col1:
            tipo_illuminazione_illum = st.selectbox(
                "Tipologia illuminazione",
                options=["interni", "esterni", "mista"],
                format_func=lambda x: {
                    "interni": "🏢 Illuminazione interni (CRI ≥80)",
                    "esterni": "🌃 Illuminazione pertinenze esterne (CRI ≥60)",
                    "mista": "🏢🌃 Illuminazione mista (interni + esterni)"
                }[x],
                help="Seleziona se l'intervento riguarda illuminazione interni, esterni o entrambi"
            )

            superficie_illuminata_illum = st.number_input(
                "Superficie utile illuminata (m²)",
                min_value=0.0,
                value=200.0,
                step=10.0,
                help="Superficie utile calpestabile dell'edificio soggetta ad intervento"
            )

            spesa_illum = st.number_input(
                "Spesa sostenuta totale (€)",
                min_value=0.0,
                value=2400.0,
                step=100.0,
                help="Spesa totale per l'intervento (IVA inclusa se costituisce un costo)"
            )

        with col2:
            potenza_ante_illum = st.number_input(
                "Potenza ante-operam (W)",
                min_value=0.0,
                value=10000.0,
                step=100.0,
                help="Potenza totale impianto illuminazione PRIMA della sostituzione"
            )

            potenza_post_illum = st.number_input(
                "Potenza post-operam (W)",
                min_value=0.0,
                value=4000.0,
                step=100.0,
                help="Potenza totale impianto illuminazione DOPO la sostituzione (DEVE essere ≤ 50% ante)"
            )

            # Calcola e mostra rapporto potenza
            if potenza_ante_illum > 0 and potenza_post_illum > 0:
                rapporto_potenza_illum = (potenza_post_illum / potenza_ante_illum) * 100
                if rapporto_potenza_illum <= 50:
                    st.success(f"✅ Rapporto potenza: {rapporto_potenza_illum:.1f}% ≤ 50% - CONFORME")
                else:
                    st.error(f"❌ Rapporto potenza: {rapporto_potenza_illum:.1f}% > 50% - NON CONFORME")

        # Caratteristiche tecniche lampade
        st.subheader("🔬 Caratteristiche Tecniche Lampade")

        col3, col4 = st.columns(2)

        with col3:
            efficienza_luminosa_illum = st.number_input(
                "Efficienza luminosa (lm/W)",
                min_value=0.0,
                value=120.0,
                step=5.0,
                help="Minimo richiesto: 80 lm/W. LED di ultima generazione: 120-150 lm/W"
            )

            if efficienza_luminosa_illum < 80:
                st.error(f"❌ Efficienza {efficienza_luminosa_illum:.1f} lm/W < 80 lm/W (minimo)")
            elif efficienza_luminosa_illum < 100:
                st.warning(f"⚠️ Efficienza {efficienza_luminosa_illum:.1f} lm/W sopra minimo ma sotto standard moderno (≥100 lm/W)")
            else:
                st.success(f"✅ Efficienza {efficienza_luminosa_illum:.1f} lm/W - OTTIMA")

        with col4:
            indice_cri_illum = st.number_input(
                "Indice resa cromatica (CRI)",
                min_value=0,
                max_value=100,
                value=85,
                step=1,
                help="CRI minimo: ≥80 (interni), ≥60 (esterni)"
            )

            # Validazione CRI in base al tipo
            if tipo_illuminazione_illum == "interni" and indice_cri_illum < 80:
                st.error(f"❌ CRI {indice_cri_illum} < 80 (minimo per interni)")
            elif tipo_illuminazione_illum == "esterni" and indice_cri_illum < 60:
                st.error(f"❌ CRI {indice_cri_illum} < 60 (minimo per esterni)")
            else:
                st.success(f"✅ CRI {indice_cri_illum} - CONFORME")

        # Certificazioni
        st.subheader("📜 Certificazioni e Conformità")

        col5, col6 = st.columns(2)

        with col5:
            marcatura_ce_illum = st.checkbox(
                "✓ Lampade con marcatura CE",
                value=True,
                help="OBBLIGATORIO: Conformità a norme di sicurezza e compatibilità elettromagnetica"
            )

            certificazione_lab_illum = st.checkbox(
                "✓ Certificazione da laboratorio accreditato",
                value=True,
                help="OBBLIGATORIO: Certificazione caratteristiche fotometriche (solido fotometrico, resa cromatica, flusso luminoso, efficienza)"
            )

            criteri_illuminotecnici_illum = st.checkbox(
                "✓ Rispetto criteri illuminotecnici UNI EN 12464-1",
                value=True,
                help="OBBLIGATORIO: Gli apparecchi devono rispettare i requisiti normativi d'impianto previsti dalle norme UNI e CEI vigenti"
            )

        with col6:
            if tipo_illuminazione_illum in ["esterni", "mista"]:
                inquinamento_luminoso_illum = st.checkbox(
                    "✓ Conformità normativa inquinamento luminoso",
                    value=True,
                    help="OBBLIGATORIO per esterni: Conformità alla normativa sull'inquinamento luminoso e sulla sicurezza"
                )
            else:
                inquinamento_luminoso_illum = True

            impianto_sottodim_illum = st.checkbox(
                "Impianto ante-operam sottodimensionato rispetto a UNI EN 12464-1",
                value=False,
                help="Seleziona SOLO se l'impianto ante-operam NON rispettava i criteri illuminotecnici minimi. In questo caso l'incentivo sarà calcolato solo sul 50% della potenza sostituita."
            )

        # Parametri aggiuntivi per validazione specifica
        st.subheader("⚙️ Parametri Aggiuntivi")

        col7, col8 = st.columns(2)

        with col7:
            # Per edifici con P ≥ 200 kW
            potenza_impianto_illum = st.number_input(
                "Potenza impianto termico edificio (kW)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                help="Se ≥ 200 kW, richiesta relazione tecnica descrittiva e APE post-operam"
            )

            if potenza_impianto_illum >= 200:
                st.warning(f"⚠️ P = {potenza_impianto_illum:.0f} kW ≥ 200 kW: richiesta relazione tecnica e APE post-operam")

        with col8:
            # Per imprese/ETS su terziario
            if tipo_soggetto in ["impresa", "ets_economico"]:
                edificio_terziario_illum = st.checkbox(
                    "Edificio terziario",
                    value=False,
                    help="Per imprese/ETS su terziario richiesta riduzione energia primaria ≥ 10-20%"
                )

                if edificio_terziario_illum:
                    riduzione_energia_illum = st.number_input(
                        "Riduzione energia primaria (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.0,
                        step=1.0,
                        help="Minimo: 10% (solo II.E), 20% (multi-intervento con altri Titolo II)"
                    )

                    multi_intervento_illum = st.checkbox(
                        "Multi-intervento (II.E + altri Titolo II)",
                        value=False,
                        help="Se combinato con altri interventi Titolo II, riduzione minima = 20%"
                    )

                    ha_ape_ante_post_illum = st.checkbox(
                        "APE ante-operam e post-operam disponibili",
                        value=False,
                        help="OBBLIGATORIO per verifica riduzione energia primaria"
                    )
            else:
                edificio_terziario_illum = False
                riduzione_energia_illum = 0.0
                multi_intervento_illum = False
                ha_ape_ante_post_illum = False

        # Premialità
        premialita_ue_illum = st.checkbox(
            "🇪🇺 Componenti prodotti nell'Unione Europea (+10%)",
            value=False,
            help="Se i componenti sono prodotti in UE, l'incentivo aumenta del 10%"
        )

        # --- CALCOLO E VALIDAZIONE ---
        if st.button("🔍 Calcola Incentivo CT 3.0", key="calcola_illum", type="primary"):
            try:
                # Verifica vincoli terziario CT 3.0 (Punto 3)
                # Nota: Illuminazione (II.H) non ha vincoli terziario, ma applichiamo per coerenza
                ammissibile_vincoli_illum, msg_vincoli_illum = applica_vincoli_terziario_ct3(
                    tipo_intervento_app="illuminazione",
                    tipo_soggetto_label=tipo_soggetto_principale
                )

                if not ammissibile_vincoli_illum:
                    st.error(f"🚫 {msg_vincoli_illum}")
                    st.stop()
                elif msg_vincoli_illum:
                    st.warning(f"⚠️ {msg_vincoli_illum}")

                # Validazione requisiti
                validazione_illum = valida_requisiti_illuminazione(
                    tipo_illuminazione=tipo_illuminazione_illum,
                    superficie_illuminata_mq=superficie_illuminata_illum,
                    spesa_sostenuta=spesa_illum,
                    potenza_ante_operam_w=potenza_ante_illum,
                    potenza_post_operam_w=potenza_post_illum,
                    efficienza_luminosa_lm_w=efficienza_luminosa_illum,
                    indice_resa_cromatica=indice_cri_illum,
                    ha_marcatura_ce=marcatura_ce_illum,
                    ha_certificazione_laboratorio=certificazione_lab_illum,
                    rispetta_criteri_illuminotecnici=criteri_illuminotecnici_illum,
                    impianto_sottodimensionato_ante=impianto_sottodim_illum,
                    conforme_inquinamento_luminoso=inquinamento_luminoso_illum,
                    potenza_impianto_kw=potenza_impianto_illum,
                    ha_diagnosi_ante_operam=potenza_impianto_illum >= 200,
                    ha_ape_post_operam=potenza_impianto_illum >= 200,
                    tipo_soggetto=tipo_soggetto,
                    edificio_terziario=edificio_terziario_illum,
                    riduzione_energia_primaria_pct=riduzione_energia_illum,
                    ha_ape_ante_post=ha_ape_ante_post_illum,
                    multi_intervento=multi_intervento_illum,
                    tipo_edificio="pubblico" if tipo_soggetto == "pa" else "residenziale"
                )

                ammissibile_illum = validazione_illum["ammissibile"]
                punteggio_illum = validazione_illum["punteggio"]

                # Mostra risultato validazione
                if ammissibile_illum:
                    st.success(f"✅ **Intervento AMMISSIBILE al CT 3.0** - Punteggio: {punteggio_illum}/100")
                else:
                    st.error(f"❌ **Intervento NON AMMISSIBILE** - Punteggio: {punteggio_illum}/100")

                # Mostra errori
                if validazione_illum["errori"]:
                    st.error("**Errori bloccanti:**")
                    for err in validazione_illum["errori"]:
                        st.write(f"• {err}")

                # Mostra warnings
                if validazione_illum["warnings"]:
                    st.warning("**Avvisi:**")
                    for warn in validazione_illum["warnings"]:
                        st.write(f"• {warn}")

                # Mostra suggerimenti
                if validazione_illum["suggerimenti"]:
                    with st.expander("💡 Suggerimenti per ottimizzare l'intervento"):
                        for sug in validazione_illum["suggerimenti"]:
                            st.write(f"• {sug}")

                # Spiega punteggio se < 100
                if punteggio_illum < 100 and ammissibile_illum:
                    st.info(f"ℹ️ **Perché {punteggio_illum}/100 e non 100/100?** Ci sono avvisi o suggerimenti che riducono il punteggio (vedi sopra), ma l'intervento rimane ammissibile.")

                # Se ammissibile, calcola incentivo
                if ammissibile_illum:
                    st.markdown("---")
                    st.subheader("💰 Calcolo Incentivo Conto Termico 3.0")

                    # Calcolo CT 3.0
                    risultato_ct_illum = calculate_lighting_incentive(
                        superficie_illuminata_mq=superficie_illuminata_illum,
                        spesa_sostenuta=spesa_illum,
                        potenza_ante_operam_w=potenza_ante_illum,
                        potenza_post_operam_w=potenza_post_illum,
                        impianto_sottodimensionato_ante=impianto_sottodim_illum,
                        tipo_soggetto=tipo_soggetto,
                        tipo_edificio="pubblico" if tipo_soggetto == "pa" else "residenziale",
                        usa_premialita_componenti_ue=premialita_ue_illum
                    )

                    # Mostra risultati CT 3.0
                    st.markdown("#### 🏛️ Conto Termico 3.0")

                    col_ct1, col_ct2, col_ct3 = st.columns(3)

                    with col_ct1:
                        st.metric(
                            "Incentivo Totale",
                            f"€ {risultato_ct_illum['incentivo_totale']:,.2f}",
                            help="Incentivo totale erogato dal GSE"
                        )

                    with col_ct2:
                        st.metric(
                            "Anni Erogazione",
                            f"{risultato_ct_illum['anni_erogazione']} {'anno' if risultato_ct_illum['anni_erogazione'] == 1 else 'anni'}",
                            help="Numero di rate annuali"
                        )

                    with col_ct3:
                        st.metric(
                            "Rata Annuale",
                            f"€ {risultato_ct_illum['rata_annuale']:,.2f}",
                            help="Importo di ciascuna rata annuale"
                        )

                    # Dettagli calcolo
                    with st.expander("📋 Dettagli Calcolo CT 3.0"):
                        st.text(risultato_ct_illum['dettagli'])

                    # Calcolo NPV (solo CT 3.0, quindi valore nominale)
                    st.markdown("---")
                    st.subheader("📊 Valore Attuale Netto (NPV)")

                    # Per CT 3.0 con erogazione rateale, calcola NPV
                    if risultato_ct_illum['anni_erogazione'] > 1:
                        tasso_sconto = 0.03
                        npv_ct = sum([risultato_ct_illum['rata_annuale'] / ((1 + tasso_sconto) ** anno)
                                     for anno in range(1, risultato_ct_illum['anni_erogazione'] + 1)])
                    else:
                        npv_ct = risultato_ct_illum['incentivo_totale']

                    npv_note = "Per erogazione in rata unica, NPV = incentivo totale." if risultato_ct_illum['anni_erogazione'] == 1 else f"Per {risultato_ct_illum['anni_erogazione']} rate annuali, il valore attuale e inferiore al totale nominale."
                    st.info(
                        f"💡 **NPV Conto Termico 3.0**: € {npv_ct:,.2f}\n\n"
                        f"Il Valore Attuale Netto (NPV) attualizza i flussi di cassa futuri al valore odierno "
                        f"usando un tasso di sconto del 3%. "
                        f"{npv_note}"
                    )

                    st.success(
                        f"✅ **Intervento ammissibile al Conto Termico 3.0**\n\n"
                        f"Incentivo: € {risultato_ct_illum['incentivo_totale']:,.2f} in {risultato_ct_illum['anni_erogazione']} {'anno' if risultato_ct_illum['anni_erogazione'] == 1 else 'anni'}"
                    )

                    st.info(
                        "ℹ️ **Promemoria importante**:\n\n"
                        "• L'illuminazione LED **NON rientra** in Ecobonus né in Bonus Ristrutturazione\n"
                        "• Incentivo erogato dal GSE (Gestore Servizi Energetici)\n"
                        "• Richiesta tramite Portaltermico entro 60 giorni dalla fine lavori\n"
                        "• Conservare tutta la documentazione per 5 anni dopo l'ultima erogazione"
                    )

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # ===========================================================================
    # TAB 9: BUILDING AUTOMATION
    # ===========================================================================
    with tab_building_automation:
        st.header("🏢 Building Automation - Confronto Incentivi")
        st.caption("Intervento II.F - Tecnologie di gestione e controllo automatico (BACS/TBM)")

        st.info(
            "ℹ️ **Building Automation rientra in**: CT 3.0 (40%), Ecobonus (50%/36%), "
            "Bonus Ristrutturazione (50%/36%). Confronta le opzioni per trovare la soluzione più vantaggiosa. "
            "**NOTA**: Ecobonus ha un limite SPECIALE di 15.000€ per questo intervento."
        )

        # Import moduli
        from modules.validator_building_automation import valida_requisiti_building_automation
        from modules.calculator_building_automation import (
            calculate_building_automation_incentive,
            confronta_incentivi_building_automation
        )

        # --- INPUT UTENTE ---
        st.subheader("📊 Dati Intervento")

        col1, col2 = st.columns(2)

        with col1:
            superficie_ba = st.number_input(
                "Superficie utile calpestabile (m²)",
                min_value=0.0,
                value=300.0,
                step=10.0,
                help="Superficie utile calpestabile dell'edificio soggetta a installazione BA"
            )

            spesa_ba = st.number_input(
                "Spesa sostenuta totale (€)",
                min_value=0.0,
                value=15000.0,
                step=500.0,
                help="Spesa totale per sistema BA (IVA inclusa se costituisce un costo). Max: 60 €/m² per CT 3.0"
            )

            # Calcola costo specifico
            if superficie_ba > 0:
                costo_spec_ba = spesa_ba / superficie_ba
                if costo_spec_ba > 60:
                    st.warning(f"⚠️ Costo specifico: {costo_spec_ba:.2f} €/m² > 60 €/m² (massimo CT 3.0)")
                else:
                    st.success(f"✅ Costo specifico: {costo_spec_ba:.2f} €/m² ≤ 60 €/m²")

        with col2:
            classe_efficienza_ba = st.selectbox(
                "Classe di efficienza BACS/TBM",
                options=["A", "B", "C", "D"],
                index=1,  # Default: B
                help="Secondo UNI EN ISO 52120-1. OBBLIGATORIO: Classe B minima (A o B ammesse, C e D NON ammesse)"
            )

            if classe_efficienza_ba in ["C", "D"]:
                st.error(f"❌ Classe {classe_efficienza_ba} NON AMMESSA - Requisito minimo: Classe B")
            elif classe_efficienza_ba == "B":
                st.success("✅ Classe B - Conforme (minimo richiesto)")
            else:  # Classe A
                st.success("✅ Classe A - Prestazioni superiori")

        # Conformità normativa
        st.subheader("📋 Conformità Normativa")

        col3, col4 = st.columns(2)

        with col3:
            conforme_uni_en_ba = st.checkbox(
                "Conforme UNI EN ISO 52120-1",
                value=True,
                help="OBBLIGATORIO: Norma che specifica requisiti progettazione e criteri Classe B"
            )

            conforme_cei_ba = st.checkbox(
                "Conforme Guida CEI 205-18",
                value=True,
                help="OBBLIGATORIO: Guida per progettazione sistemi BACS"
            )

        with col4:
            ha_relazione_ba = st.checkbox(
                "Relazione tecnica progetto",
                value=True,
                help="OBBLIGATORIO: Relazione timbrata e firmata con descrizione ante/post operam"
            )

            ha_schede_ba = st.checkbox(
                "Schede controlli regolazione",
                value=True,
                help="OBBLIGATORIO: Schede dettagliate secondo CEI 205-18"
            )

        ha_schemi_ba = st.checkbox(
            "Schemi elettrici con dispositivi installati",
            value=True,
            help="OBBLIGATORIO: Schemi elettrici completi"
        )

        # Servizi controllati dal sistema BA
        st.subheader("🎛️ Servizi Controllati dal Sistema BA")
        st.caption("Seleziona almeno uno dei servizi che saranno controllati dal sistema Building Automation")

        col5, col6, col7 = st.columns(3)

        with col5:
            controlla_riscaldamento_ba = st.checkbox("🔥 Riscaldamento", value=True)
            controlla_raffrescamento_ba = st.checkbox("❄️ Raffrescamento", value=True)
            controlla_ventilazione_ba = st.checkbox("💨 Ventilazione", value=False)

        with col6:
            controlla_acs_ba = st.checkbox("🚿 ACS (Acqua Calda Sanitaria)", value=True)
            controlla_illuminazione_ba = st.checkbox("💡 Illuminazione", value=False)

        with col7:
            controlla_integrato_ba = st.checkbox("🔗 Controllo integrato", value=True, help="Controllo coordinato di più servizi")
            ha_diagnostica_ba = st.checkbox("📊 Diagnostica/Consumi", value=True, help="Monitoraggio consumi e diagnostica")

        # Conta servizi controllati
        servizi_ba = sum([
            controlla_riscaldamento_ba, controlla_raffrescamento_ba, controlla_ventilazione_ba,
            controlla_acs_ba, controlla_illuminazione_ba, controlla_integrato_ba, ha_diagnostica_ba
        ])

        if servizi_ba == 0:
            st.error("❌ Seleziona almeno UN servizio controllato dal sistema BA")
        elif servizi_ba == 1:
            st.warning(f"⚠️ Solo {servizi_ba} servizio controllato - Considera di estendere il controllo")
        elif servizi_ba >= 3:
            st.success(f"✅ {servizi_ba} servizi controllati - Ottimo per efficienza energetica")
        else:
            st.info(f"ℹ️ {servizi_ba} servizi controllati")

        # Parametri aggiuntivi
        with st.expander("⚙️ Parametri Aggiuntivi", expanded=False):
            col8, col9 = st.columns(2)

            with col8:
                potenza_impianto_ba = st.number_input(
                    "Potenza nominale impianto termico (kW)",
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    help="Se P ≥ 200 kW: obbligatoria relazione tecnica + APE post-operam"
                )

                if potenza_impianto_ba >= 200:
                    st.warning(f"⚠️ P = {potenza_impianto_ba:.1f} kW ≥ 200 kW: richiesta relazione tecnica + APE post")

                    ha_relazione_tecnica_ba = st.checkbox(
                        "Relazione tecnica descrittiva intervento",
                        value=False,
                        help="Per P ≥ 200 kW"
                    )
                    ha_ape_post_ba = st.checkbox(
                        "APE post-operam",
                        value=False,
                        help="OBBLIGATORIO per P ≥ 200 kW"
                    )
                else:
                    ha_relazione_tecnica_ba = None
                    ha_ape_post_ba = None

            with col9:
                # Parametri imprese/ETS su terziario
                if tipo_soggetto in ["impresa", "ets_economico"]:
                    edificio_terziario_ba = st.checkbox(
                        "Edificio terziario",
                        value=False,
                        help="Per imprese/ETS su terziario: richiesta riduzione energia ≥10% (o ≥20% se multi-intervento)"
                    )

                    if edificio_terziario_ba:
                        multi_intervento_ba = st.checkbox(
                            "Combinato con altri interventi Titolo II",
                            value=False,
                            help="Se combinato con II.A, II.B, II.C, II.D, II.E: riduzione minima 20% invece di 10%"
                        )

                        riduzione_energia_ba = st.number_input(
                            "Riduzione energia primaria (%)",
                            min_value=0.0,
                            max_value=100.0,
                            value=15.0,
                            step=0.5,
                            help=f"Richiesta: ≥{20 if multi_intervento_ba else 10}%"
                        )

                        ha_ape_ante_post_ba = st.checkbox(
                            "APE ante + post operam",
                            value=False,
                            help="OBBLIGATORIO per verifica riduzione energia"
                        )
                    else:
                        multi_intervento_ba = False
                        riduzione_energia_ba = 0.0
                        ha_ape_ante_post_ba = False
                else:
                    edificio_terziario_ba = False
                    multi_intervento_ba = False
                    riduzione_energia_ba = 0.0
                    ha_ape_ante_post_ba = False

        # Premialità
        usa_premialita_ue_ba = st.checkbox(
            "🇪🇺 Premialità componenti UE (+10%)",
            value=False,
            help="Se almeno il 70% dei componenti è di origine UE"
        )

        # Pulsanti azione
        col_btn1_ba, col_btn2_ba = st.columns(2)
        with col_btn1_ba:
            calcola_ba = st.button("🔍 Calcola Incentivi", type="primary", use_container_width=True, key="btn_calc_ba")
        with col_btn2_ba:
            salva_scenario_ba = st.button("💾 Salva Scenario", use_container_width=True, key="btn_salva_ba", disabled=len(st.session_state.scenari_building_automation) >= 5)

        if calcola_ba or salva_scenario_ba:
            # Verifica vincoli terziario CT 3.0 (Punto 3)
            ammissibile_vincoli_ba, msg_vincoli_ba = applica_vincoli_terziario_ct3(
                tipo_intervento_app="building_automation",
                tipo_soggetto_label=tipo_soggetto_principale
            )

            if not ammissibile_vincoli_ba:
                st.error(f"🚫 {msg_vincoli_ba}")
                st.stop()
            elif msg_vincoli_ba:
                st.warning(f"⚠️ {msg_vincoli_ba}")

            with st.spinner("Validazione requisiti in corso..."):
                risultato_validazione_ba = valida_requisiti_building_automation(
                    superficie_utile_mq=superficie_ba,
                    spesa_sostenuta=spesa_ba,
                    classe_efficienza_ba=classe_efficienza_ba,
                    conforme_uni_en_iso_52120=conforme_uni_en_ba,
                    conforme_guida_cei_205_18=conforme_cei_ba,
                    controlla_riscaldamento=controlla_riscaldamento_ba,
                    controlla_raffrescamento=controlla_raffrescamento_ba,
                    controlla_ventilazione=controlla_ventilazione_ba,
                    controlla_acs=controlla_acs_ba,
                    controlla_illuminazione=controlla_illuminazione_ba,
                    controlla_integrato=controlla_integrato_ba,
                    ha_diagnostica_consumi=ha_diagnostica_ba,
                    ha_relazione_tecnica_progetto=ha_relazione_ba,
                    ha_schede_controlli_regolazione=ha_schede_ba,
                    ha_schemi_elettrici=ha_schemi_ba,
                    potenza_impianto_kw=potenza_impianto_ba,
                    ha_diagnosi_ante_operam=ha_relazione_tecnica_ba,
                    ha_ape_post_operam=ha_ape_post_ba,
                    tipo_soggetto=tipo_soggetto,
                    edificio_terziario=edificio_terziario_ba,
                    riduzione_energia_primaria_pct=riduzione_energia_ba,
                    ha_ape_ante_post=ha_ape_ante_post_ba,
                    multi_intervento=multi_intervento_ba,
                    tipo_edificio="residenziale"  # Default, potrebbe essere gestito meglio con variabile sidebar
                )

                # Mostra risultati validazione
                if risultato_validazione_ba["ammissibile"]:
                    st.success(f"✅ **INTERVENTO AMMISSIBILE** - Punteggio: {risultato_validazione_ba['punteggio']}/100")
                else:
                    st.error("❌ **INTERVENTO NON AMMISSIBILE**")

                # Errori
                if risultato_validazione_ba["errori"]:
                    with st.expander("🚫 Errori Bloccanti", expanded=True):
                        for err in risultato_validazione_ba["errori"]:
                            st.error(f"• {err}")

                # Warnings
                if risultato_validazione_ba["warnings"]:
                    with st.expander("⚠️ Attenzioni", expanded=False):
                        for warn in risultato_validazione_ba["warnings"]:
                            st.warning(f"• {warn}")

                # Suggerimenti
                if risultato_validazione_ba["suggerimenti"]:
                    with st.expander("💡 Suggerimenti", expanded=False):
                        for sug in risultato_validazione_ba["suggerimenti"]:
                            st.info(f"• {sug}")

        # --- CALCOLO INCENTIVI ---
        st.subheader("💰 Confronto Incentivi")

        if st.button("📊 Calcola e Confronta Incentivi", use_container_width=True):
            try:
                with st.spinner("Calcolo incentivi in corso..."):
                    # Confronto 3 vie
                    confronto_ba = confronta_incentivi_building_automation(
                        superficie_utile_mq=superficie_ba,
                        spesa_sostenuta=spesa_ba,
                        tipo_soggetto_ct=tipo_soggetto,
                        tipo_edificio_ct="residenziale",  # Default
                        usa_premialita_componenti_ue=usa_premialita_ue_ba,
                        tipo_immobile_eco="principale",  # Default per residenziale
                        anno_riferimento_eco=anno,
                        tipo_immobile_br="principale",  # Default per residenziale
                        anno_riferimento_br=anno,
                        tasso_sconto=tasso_sconto
                    )

                    # Salva nel session state per uso successivo (es. salvataggio scenario)
                    st.session_state.ultimo_confronto_ba = confronto_ba

                    # Risultati confronto - condizionale in base a solo_conto_termico
                    if solo_conto_termico:
                        # Modalità Solo CT 3.0
                        st.markdown("### 🔥 Conto Termico 3.0")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "💚 Incentivo CT 3.0",
                                f"€ {confronto_ba['ct_3_0']['incentivo_totale']:,.0f}",
                                help=f"{confronto_ba['ct_3_0']['anni_erogazione']} anni"
                            )
                        with col2:
                            st.metric(
                                "NPV (Valore Attuale)",
                                f"€ {confronto_ba['ct_3_0']['npv']:,.0f}"
                            )
                        det_ct_ba = confronto_ba['ct_3_0']['dettagli']
                        st.write(f"**Percentuale incentivo**: {det_ct_ba['percentuale']:.0%} | **{det_ct_ba['nota_rateazione']}**")
                    else:
                        # Modalità confronto completo
                        st.success(f"✅ **Migliore opzione**: {confronto_ba['migliore_opzione']}")

                        # Tabella comparativa
                        col_ct, col_eco, col_br = st.columns(3)

                        with col_ct:
                            st.metric(
                                "💚 CT 3.0",
                                f"€ {confronto_ba['ct_3_0']['incentivo_totale']:,.0f}",
                                delta=f"NPV: € {confronto_ba['ct_3_0']['npv']:,.0f}",
                                help=f"{confronto_ba['ct_3_0']['anni_erogazione']} anni"
                            )

                        with col_eco:
                            st.metric(
                                "🔵 Ecobonus",
                                f"€ {confronto_ba['ecobonus']['detrazione_totale']:,.0f}",
                                delta=f"NPV: € {confronto_ba['ecobonus']['npv']:,.0f}",
                                help=f"{confronto_ba['ecobonus']['anni_erogazione']} anni - LIMITE SPECIALE: 15.000€"
                            )

                        with col_br:
                            st.metric(
                                "🟠 Bonus Ristr.",
                                f"€ {confronto_ba['bonus_ristrutturazione']['detrazione_totale']:,.0f}",
                                delta=f"NPV: € {confronto_ba['bonus_ristrutturazione']['npv']:,.0f}",
                                help=f"{confronto_ba['bonus_ristrutturazione']['anni_erogazione']} anni"
                            )

                        # Grafico comparativo NPV
                        st.subheader("📊 Confronto NPV (Valore Attuale Netto)")
                        df_confronto_ba = pd.DataFrame({
                            "Incentivo": ["CT 3.0", "Ecobonus", "Bonus Ristr."],
                            "NPV (€)": [
                                confronto_ba['ct_3_0']['npv'],
                                confronto_ba['ecobonus']['npv'],
                                confronto_ba['bonus_ristrutturazione']['npv']
                            ]
                        })
                        st.bar_chart(df_confronto_ba.set_index("Incentivo"))

                    # Dettagli CT 3.0
                    with st.expander("💚 Dettagli CT 3.0", expanded=False):
                        det_ct_ba = confronto_ba['ct_3_0']['dettagli']
                        st.write(f"**Superficie**: {det_ct_ba['superficie_mq']:.2f} m²")
                        st.write(f"**Spesa sostenuta**: € {det_ct_ba['spesa_sostenuta']:,.2f}")
                        st.write(f"**Costo specifico**: {det_ct_ba['costo_specifico']:.2f} €/m² (max: {det_ct_ba['costo_max_mq']:.2f} €/m²)")
                        st.write(f"**{det_ct_ba['nota_costo']}**")
                        st.write(f"**Percentuale incentivo**: {det_ct_ba['percentuale']:.0%} ({det_ct_ba['tipo_percentuale']})")
                        st.write(f"**Incentivo totale**: € {confronto_ba['ct_3_0']['incentivo_totale']:,.2f}")
                        st.write(f"**{det_ct_ba['nota_rateazione']}**")
                        if confronto_ba['ct_3_0']['anni_erogazione'] > 1:
                            st.write(f"**Rata annuale**: € {confronto_ba['ct_3_0']['rata_annuale']:,.2f}")

                    # Dettagli Ecobonus e Bonus Ristrutturazione (solo se non in modalità solo CT)
                    if not solo_conto_termico:
                        with st.expander("🔵 Dettagli Ecobonus", expanded=False):
                            det_eco_ba = confronto_ba['ecobonus']['dettagli']
                            st.write(f"**Aliquota**: {det_eco_ba['aliquota']:.0%}")
                            st.write(f"**Anno riferimento**: {det_eco_ba['anno_riferimento']}")
                            st.write(f"**Tipo immobile**: {det_eco_ba['tipo_immobile']}")
                            st.write(f"**Spesa ammissibile**: € {confronto_ba['ecobonus']['spesa_ammissibile']:,.2f}")
                            st.warning(f"⚠️ **{det_eco_ba['nota_speciale']}** - Limite: € {det_eco_ba['limite_max']:,.0f}")
                            st.write(f"**Detrazione totale**: € {confronto_ba['ecobonus']['detrazione_totale']:,.2f}")
                            st.write(f"**Rata annuale**: € {confronto_ba['ecobonus']['rata_annuale']:,.2f} × {confronto_ba['ecobonus']['anni_erogazione']} anni")

                        with st.expander("🟠 Dettagli Bonus Ristrutturazione", expanded=False):
                            det_br_ba = confronto_ba['bonus_ristrutturazione']['dettagli']
                            st.write(f"**Aliquota**: {det_br_ba['aliquota']:.0%}")
                            st.write(f"**Anno riferimento**: {det_br_ba['anno_riferimento']}")
                            st.write(f"**Tipo immobile**: {det_br_ba['tipo_immobile']}")
                            st.write(f"**Spesa ammissibile**: € {confronto_ba['bonus_ristrutturazione']['spesa_ammissibile']:,.2f} (limite: € {det_br_ba['limite_max']:,.0f})")
                            st.write(f"**Detrazione totale**: € {confronto_ba['bonus_ristrutturazione']['detrazione_totale']:,.2f}")
                            st.write(f"**Rata annuale**: € {confronto_ba['bonus_ristrutturazione']['rata_annuale']:,.2f} × {confronto_ba['bonus_ristrutturazione']['anni_erogazione']} anni")

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # Logica di salvataggio scenario (FUORI dal blocco calcola, usa session state)
        if salva_scenario_ba:
            if st.session_state.ultimo_confronto_ba is None:
                st.warning("⚠️ Prima calcola gli incentivi con il pulsante 'Calcola e Confronta Incentivi'")
            elif len(st.session_state.scenari_building_automation) >= 5:
                st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")
            else:
                confronto_ba = st.session_state.ultimo_confronto_ba
                nome_scenario_ba = f"Building Auto {len(st.session_state.scenari_building_automation) + 1}"
                scenario_data_ba = {
                    "nome": nome_scenario_ba,
                    "timestamp": datetime.now().isoformat(),
                    "superficie_mq": superficie_ba,
                    "spesa": spesa_ba,
                    "classe_efficienza": classe_efficienza_ba,
                    "tipo_soggetto": tipo_soggetto,
                    "ct_incentivo": confronto_ba['ct_3_0']['incentivo_totale'],
                    "ct_npv": confronto_ba['ct_3_0']['npv'],
                    "eco_detrazione": confronto_ba['ecobonus']['detrazione_totale'],
                    "eco_npv": confronto_ba['ecobonus']['npv'],
                    "bonus_detrazione": confronto_ba['bonus_ristrutturazione']['detrazione_totale'],
                    "bonus_npv": confronto_ba['bonus_ristrutturazione']['npv'],
                    "migliore": confronto_ba['migliore_opzione']
                }
                st.session_state.scenari_building_automation.append(scenario_data_ba)
                st.success(f"✅ Scenario salvato: {nome_scenario_ba}")
                st.info(f"📊 Scenari salvati: {len(st.session_state.scenari_building_automation)}/5")

    # ===========================================================================
    # TAB 10: SISTEMI IBRIDI
    # ===========================================================================
    with tab_ibridi:
        st.header("🔀 Sistemi Ibridi - Confronto Incentivi")
        st.caption("Intervento III.B - Sistemi ibridi factory made, bivalenti, pompe di calore add-on")

        # Import moduli
        from modules.validator_ibridi import valida_requisiti_ibridi
        from modules.calculator_ibridi import calculate_hybrid_incentive, confronta_incentivi_ibridi

        # ========================================================================
        # SEZIONE RICERCA DAL CATALOGO GSE
        # ========================================================================
        st.markdown("#### 🔍 Ricerca dal Catalogo GSE 2E (Sistemi Ibridi)")

        catalogo_ibridi = load_catalogo_ibridi()

        usa_catalogo_ibr = st.checkbox(
            "🔍 Cerca nel Catalogo GSE 2E (Sistemi Ibridi)",
            value=False,
            help="Seleziona un sistema ibrido dal catalogo GSE per l'iter semplificato (potenza ≤ 35 kW)",
            key="ibr_usa_catalogo"
        )

        prodotto_catalogo_ibr = None
        iter_semplificato_ibr = False

        if usa_catalogo_ibr and catalogo_ibridi:
            # Filtra solo sistemi con potenza PdC ≤ 35 kW per iter semplificato
            catalogo_filtrato_ibr = [
                p for p in catalogo_ibridi
                if p.get("dati_tecnici", {}).get("potenza_termica_pdc_kw") and
                   p.get("dati_tecnici", {}).get("potenza_termica_pdc_kw") <= 35
            ]

            if not catalogo_filtrato_ibr:
                st.warning("⚠️ Nessun sistema ibrido trovato nel catalogo con potenza ≤ 35 kW")
            else:
                st.info(f"📊 {len(catalogo_filtrato_ibr)} sistemi ibridi disponibili nel catalogo (potenza PdC ≤ 35 kW)")

                # Selezione marca
                marche_ibr = get_marche_catalogo_ibridi(catalogo_filtrato_ibr)
                marca_ibr = st.selectbox(
                    "Seleziona marca",
                    options=["-- Seleziona --"] + marche_ibr,
                    key="ibr_marca_catalogo"
                )

                if marca_ibr and marca_ibr != "-- Seleziona --":
                    # Selezione modello
                    modelli_marca_ibr = get_modelli_per_marca_ibridi(catalogo_filtrato_ibr, marca_ibr)

                    modelli_display_ibr = []
                    for m in modelli_marca_ibr:
                        dati_tec = m.get("dati_tecnici", {})
                        pot_pdc = dati_tec.get("potenza_termica_pdc_kw", "N/D")
                        pot_cald = dati_tec.get("potenza_termica_caldaia_kw", "N/D")
                        cop = dati_tec.get("cop", "N/D")
                        modello_pdc = m.get("modello_pompa_calore", "")
                        modello_caldaia = m.get("modello_caldaia_condensazione", "")

                        # Crea descrizione modello
                        desc = f"{modello_pdc}"
                        if modello_caldaia:
                            desc += f" + {modello_caldaia}"
                        desc += f" | PdC: {pot_pdc} kW, Caldaia: {pot_cald} kW, COP: {cop}"
                        modelli_display_ibr.append(desc)

                    modello_idx_ibr = st.selectbox(
                        "Seleziona modello",
                        options=range(len(modelli_display_ibr) + 1),
                        format_func=lambda i: "-- Seleziona --" if i == 0 else modelli_display_ibr[i-1],
                        key="ibr_modello_catalogo"
                    )

                    if modello_idx_ibr > 0:
                        prodotto_catalogo_ibr = modelli_marca_ibr[modello_idx_ibr - 1]
                        iter_semplificato_ibr = True

                        # Mostra dettagli prodotto selezionato
                        dati_tec_ibr = prodotto_catalogo_ibr.get("dati_tecnici", {})
                        st.success(f"""
                        ✅ **ITER SEMPLIFICATO** (Art. 14, comma 5, DM 7/8/2025)

                        **{prodotto_catalogo_ibr.get('marca')} - {prodotto_catalogo_ibr.get('modello_pompa_calore')}**
                        - Modello caldaia: {prodotto_catalogo_ibr.get('modello_caldaia_condensazione', 'N/D')}
                        - Potenza PdC: {dati_tec_ibr.get('potenza_termica_pdc_kw', 'N/D')} kW
                        - Potenza caldaia: {dati_tec_ibr.get('potenza_termica_caldaia_kw', 'N/D')} kW
                        - COP: {dati_tec_ibr.get('cop', 'N/D')}
                        - Rendimento caldaia: {dati_tec_ibr.get('rendimento_caldaia_perc', 'N/D')}%
                        - Inverter: {'Sì' if dati_tec_ibr.get('presenza_inverter') else 'No'}
                        - Tipologia: {prodotto_catalogo_ibr.get('tipologia_intervento', '2.E')}
                        """)

                        # Vantaggi iter semplificato
                        with st.expander("ℹ️ Vantaggi Iter Semplificato (potenza PdC ≤ 35 kW)", expanded=False):
                            st.markdown("""
                            **Semplificazioni documentali:**
                            - ✅ **NON richiede asseverazione tecnica** (anche se P > 35 kW per caldaia)
                            - ✅ Sufficiente **certificazione del produttore** per requisiti tecnici
                            - ✅ Prodotto già validato GSE nel Catalogo 2E

                            **Documentazione richiesta:**
                            - Dichiarazione di conformità DM 37/2008
                            - Schede tecniche componenti (PdC + caldaia)
                            - Documentazione spese (fatture, bonifici)

                            **Tempi più rapidi** per l'istruttoria della pratica.
                            """)

        st.divider()

        # Sezione input
        st.subheader("📝 Dati Tecnici")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Auto-compila tipo sistema se prodotto da catalogo (sempre factory made)
            tipo_sistema_default_ibr = "ibrido_factory_made" if iter_semplificato_ibr else "ibrido_factory_made"

            tipo_sistema_ibr = st.selectbox(
                "Tipo sistema",
                options=["ibrido_factory_made", "bivalente", "add_on"],
                format_func=lambda x: {
                    "ibrido_factory_made": "Ibrido Factory Made",
                    "bivalente": "Sistema Bivalente",
                    "add_on": "Pompa di Calore Add-On"
                }.get(x, x),
                help="Factory made: assemblato in fabbrica. Bivalente: assemblato in campo. Add-on: PdC aggiunta a caldaia esistente" + (" - AUTO-COMPILATO (catalogo GSE solo factory made)" if iter_semplificato_ibr else ""),
                key="ibr_tipo_sistema",
                disabled=iter_semplificato_ibr
            )

            # Auto-compila potenza PdC se prodotto da catalogo
            potenza_pdc_default_ibr = 12.0
            if prodotto_catalogo_ibr:
                pot_cat = prodotto_catalogo_ibr.get("dati_tecnici", {}).get("potenza_termica_pdc_kw")
                if pot_cat:
                    potenza_pdc_default_ibr = float(pot_cat)

            potenza_pdc_ibr = st.number_input(
                "Potenza Pompa di Calore (kW)",
                min_value=1.0,
                max_value=2000.0,
                value=potenza_pdc_default_ibr,
                step=0.5,
                help="Potenza nominale termica della pompa di calore" + (" - AUTO-COMPILATO da catalogo" if prodotto_catalogo_ibr else ""),
                key="ibr_potenza_pdc",
                disabled=iter_semplificato_ibr
            )

            # Auto-compila SCOP/COP se prodotto da catalogo
            scop_default_ibr = 4.0
            if prodotto_catalogo_ibr:
                cop_cat = prodotto_catalogo_ibr.get("dati_tecnici", {}).get("cop")
                if cop_cat:
                    scop_default_ibr = float(cop_cat)

            scop_pdc_ibr = st.number_input(
                "SCOP Pompa di Calore",
                min_value=1.0,
                max_value=10.0,
                value=scop_default_ibr,
                step=0.1,
                help="Coefficiente di prestazione stagionale (SCOP)" + (" - AUTO-COMPILATO da catalogo (COP)" if prodotto_catalogo_ibr else ""),
                key="ibr_scop",
                disabled=iter_semplificato_ibr
            )

        with col2:
            # Auto-compila potenza caldaia se prodotto da catalogo
            potenza_caldaia_default_ibr = 30.0
            if prodotto_catalogo_ibr:
                pot_cald_cat = prodotto_catalogo_ibr.get("dati_tecnici", {}).get("potenza_termica_caldaia_kw")
                if pot_cald_cat:
                    potenza_caldaia_default_ibr = float(pot_cald_cat)

            potenza_caldaia_ibr = st.number_input(
                "Potenza Caldaia (kW)",
                min_value=1.0,
                max_value=2000.0,
                value=potenza_caldaia_default_ibr,
                step=1.0,
                help="Potenza nominale termica della caldaia" + (" - AUTO-COMPILATO da catalogo" if prodotto_catalogo_ibr else ""),
                key="ibr_potenza_caldaia",
                disabled=iter_semplificato_ibr
            )

            # Auto-compila rendimento caldaia se prodotto da catalogo
            eta_s_caldaia_default_ibr = 93.0
            if prodotto_catalogo_ibr:
                rend_cat = prodotto_catalogo_ibr.get("dati_tecnici", {}).get("rendimento_caldaia_perc")
                if rend_cat:
                    eta_s_caldaia_default_ibr = float(rend_cat)

            eta_s_caldaia_ibr = st.number_input(
                "η_s Caldaia (%)",
                min_value=80.0,
                max_value=110.0,
                value=eta_s_caldaia_default_ibr,
                step=0.1,
                help="Rendimento stagionale caldaia (ηs > 90% se Pn ≤ 400kW, ηs > 98% se Pn > 400kW)" + (" - AUTO-COMPILATO da catalogo" if prodotto_catalogo_ibr else ""),
                key="ibr_eta_s_caldaia",
                disabled=iter_semplificato_ibr
            )

            # Auto-calcola η_s PdC da SCOP (approssimazione: ηs_pdc ≈ SCOP * 40)
            eta_s_pdc_default_ibr = 160.0
            if prodotto_catalogo_ibr and scop_default_ibr:
                eta_s_pdc_default_ibr = scop_default_ibr * 40.0

            eta_s_pdc_ibr = st.number_input(
                "η_s Pompa di Calore (%)",
                min_value=100.0,
                max_value=250.0,
                value=eta_s_pdc_default_ibr,
                step=1.0,
                help="Efficienza energetica stagionale PdC per calcolo premialità kp" + (" - AUTO-CALCOLATO da COP catalogo" if prodotto_catalogo_ibr else ""),
                key="ibr_eta_s_pdc",
                disabled=iter_semplificato_ibr
            )

        with col3:
            spesa_ibr = st.number_input(
                "Spesa Totale Sostenuta (€)",
                min_value=0.0,
                max_value=1000000.0,
                value=18000.0,
                step=100.0,
                help="Spesa totale per l'intervento (IVA inclusa se costo)",
                key="ibr_spesa"
            )

            classe_termo_ibr = st.selectbox(
                "Classe Termoregolazione",
                options=["V", "VI", "VII", "VIII"],
                index=1,
                help="Classe sistema di termoregolazione (V, VI, VII, VIII ammesse)",
                key="ibr_classe_termo"
            )

        st.divider()

        # Parametri specifici per tipo sistema
        col1, col2, col3 = st.columns(3)

        with col1:
            if tipo_sistema_ibr == "add_on":
                st.markdown("**Parametri Add-On**")
                eta_caldaia_anni_ibr = st.number_input(
                    "Età caldaia preesistente (anni)",
                    min_value=0,
                    max_value=20,
                    value=3,
                    help="Caldaia deve avere max 5 anni per add-on",
                    key="ibr_eta_caldaia"
                )

                tipo_pdc_addon_ibr = st.selectbox(
                    "Tipo Pompa di Calore",
                    options=["aria_acqua", "acqua_acqua", "aria_aria"],
                    format_func=lambda x: x.replace("_", "-").title(),
                    help="Aria-aria solo per edifici con vincoli architettonici",
                    key="ibr_tipo_pdc_addon"
                )

                if tipo_pdc_addon_ibr == "aria_aria":
                    edificio_vincoli_ibr = st.checkbox(
                        "Edificio con vincoli architettonici",
                        value=False,
                        help="PdC aria-aria ammessa solo con vincoli",
                        key="ibr_vincoli"
                    )
                else:
                    edificio_vincoli_ibr = False
            else:
                eta_caldaia_anni_ibr = 0
                tipo_pdc_addon_ibr = "aria_acqua"
                edificio_vincoli_ibr = False

            fabbricanti_diversi_ibr = st.checkbox(
                "PdC e caldaia di fabbricanti diversi",
                value=False,
                help="Richiede asseverazione compatibilità se true",
                key="ibr_fabbricanti_diversi"
            )

        with col2:
            ha_valvole_ibr = st.checkbox(
                "Valvole termostatiche installate",
                value=True,
                help="Obbligatorie su tutti i corpi scaldanti",
                key="ibr_valvole"
            )

            if fabbricanti_diversi_ibr and tipo_sistema_ibr in ["bivalente", "add_on"]:
                ha_asseverazione_ibr = st.checkbox(
                    "Asseverazione compatibilità",
                    value=False,
                    help="OBBLIGATORIA per fabbricanti diversi",
                    key="ibr_asseverazione"
                )
            else:
                ha_asseverazione_ibr = True

            # Calcola potenza totale
            potenza_totale_ibr = potenza_pdc_ibr + potenza_caldaia_ibr

            if potenza_totale_ibr > 200:
                st.warning(f"⚠️ Potenza totale: {potenza_totale_ibr:.1f} kW > 200 kW")
                ha_contabilizzazione_ibr = st.checkbox(
                    "Contabilizzazione calore installata",
                    value=False,
                    help="OBBLIGATORIA per P > 200 kW",
                    key="ibr_contabilizzazione"
                )
            else:
                ha_contabilizzazione_ibr = False

        with col3:
            if potenza_totale_ibr >= 200:
                st.warning(f"⚠️ Potenza ≥ 200 kW: APE e Diagnosi OBBLIGATORI")
                ha_ape_ibr = st.checkbox(
                    "APE post-operam",
                    value=False,
                    help="OBBLIGATORIO per P ≥ 200 kW",
                    key="ibr_ape"
                )
                ha_diagnosi_ibr = st.checkbox(
                    "Diagnosi energetica ante-operam",
                    value=False,
                    help="OBBLIGATORIA per P ≥ 200 kW",
                    key="ibr_diagnosi"
                )
            else:
                ha_ape_ibr = None
                ha_diagnosi_ibr = None

            tipo_soggetto_ibr = st.selectbox(
                "Tipo Soggetto",
                options=list(TIPI_SOGGETTO.keys()),
                help="Imprese/ETS: caldaie a gas non ammesse",
                key="ibr_tipo_soggetto"
            )

            if tipo_soggetto_ibr in ["impresa", "ets"]:
                st.warning("⚠️ Imprese/ETS: caldaie a gas NON incentivabili")

        st.divider()

        # Premialità
        st.subheader("🎁 Premialità")
        col1, col2 = st.columns(2)

        with col1:
            usa_premialita_ue_ibr = st.checkbox(
                "Componenti UE (+10%)",
                value=False,
                help="Maggiorazione 10% se tutti i componenti sono prodotti UE",
                key="ibr_premialita_ue"
            )

        with col2:
            usa_premialita_combinato_ibr = st.checkbox(
                "Combinato con Titolo III",
                value=False,
                help="Premialità per interventi combinati",
                key="ibr_premialita_combinato"
            )

            if usa_premialita_combinato_ibr:
                with st.expander("ℹ️ Quali interventi sono compatibili?"):
                    st.markdown("""
                    I **Sistemi Ibridi (III.B)** possono essere combinati con altri interventi per ottenere premialità:

                    **Interventi Titolo II compatibili:**
                    - **II.A** - Isolamento Termico (opaco verticale/orizzontale)
                    - **II.B** - Sostituzione Serramenti

                    **Altri interventi Titolo III compatibili:**
                    - **III.D** - Solare Termico
                    - **III.F** - Building Automation
                    - **III.G** - Illuminazione LED (solo edifici non residenziali)

                    💡 **Nota**: Verifica le percentuali specifiche nelle Regole Applicative per ciascuna combinazione
                    """)

        st.divider()

        # Pulsante calcola
        calcola_ibr = st.button("🔀 Calcola Confronto", type="primary", use_container_width=True, key="ibr_calcola")

        if calcola_ibr:
            try:
                # Validazione
                st.subheader("✅ Validazione Requisiti")

                validazione_ibr = valida_requisiti_ibridi(
                    tipo_sistema=tipo_sistema_ibr,
                    potenza_pdc_kw=potenza_pdc_ibr,
                    potenza_caldaia_kw=potenza_caldaia_ibr,
                    scop_pdc=scop_pdc_ibr,
                    eta_s_caldaia=eta_s_caldaia_ibr,
                    tipo_pdc=tipo_pdc_addon_ibr if tipo_sistema_ibr == "add_on" else "aria_acqua",
                    classe_termoregolazione=classe_termo_ibr,
                    ha_valvole_termostatiche=ha_valvole_ibr,
                    ha_contabilizzazione=ha_contabilizzazione_ibr,
                    eta_caldaia_preesistente_anni=eta_caldaia_anni_ibr,
                    tipo_caldaia_preesistente="condensazione_gas",
                    fabbricanti_diversi=fabbricanti_diversi_ibr,
                    ha_asseverazione_compatibilita=ha_asseverazione_ibr,
                    ha_ape_post_operam=ha_ape_ibr,
                    ha_diagnosi_ante_operam=ha_diagnosi_ibr,
                    tipo_soggetto=tipo_soggetto_ibr,
                    integra_caldaia_gas=True,  # Assumiamo caldaia a gas
                    potenza_totale_impianto_kw=potenza_totale_ibr,
                    edificio_con_vincoli=edificio_vincoli_ibr
                )

                if not validazione_ibr["ammissibile"]:
                    st.error("❌ **Intervento NON ammissibile**")
                    for err in validazione_ibr["errori"]:
                        st.error(f"• {err}")
                    if validazione_ibr["warnings"]:
                        st.warning("**Attenzioni:**")
                        for warn in validazione_ibr["warnings"]:
                            st.warning(f"• {warn}")
                else:
                    punteggio_ibr = validazione_ibr['punteggio']
                    if punteggio_ibr == 100:
                        st.success(f"✅ **Intervento ammissibile** - Punteggio: {punteggio_ibr}/100")
                    else:
                        st.success(f"✅ **Intervento ammissibile** - Punteggio: {punteggio_ibr}/100")
                        st.info(f"ℹ️ **Perché {punteggio_ibr}/100 e non 100/100?** Ci sono avvisi o suggerimenti che riducono il punteggio (vedi sotto):")

                    if validazione_ibr["warnings"]:
                        st.warning("**⚠️ AVVISI:**")
                        for warn in validazione_ibr["warnings"]:
                            st.warning(f"  • {warn}")

                    if validazione_ibr["suggerimenti"]:
                        st.info("**💡 SUGGERIMENTI:**")
                        for sug in validazione_ibr["suggerimenti"]:
                            st.info(f"  • {sug}")

                    st.divider()

                    # Confronto incentivi
                    st.subheader("💰 Confronto Incentivi")

                    # Anno spesa per calcoli Ecobonus
                    anno_spesa_ibr = st.session_state.get("sidebar_anno", 2025)

                    # Determina tipo PdC per calcolo Ci
                    tipo_pdc_ibr = tipo_pdc_addon_ibr if tipo_sistema_ibr == "add_on" else "aria_acqua"

                    confronto_ibr = confronta_incentivi_ibridi(
                        tipo_sistema=tipo_sistema_ibr,
                        potenza_pdc_kw=potenza_pdc_ibr,
                        potenza_caldaia_kw=potenza_caldaia_ibr,
                        scop_pdc=scop_pdc_ibr,
                        eta_s_pdc=eta_s_pdc_ibr,
                        zona_climatica=zona_climatica,
                        spesa_totale_sostenuta=spesa_ibr,
                        anno_spesa=anno_spesa_ibr,
                        tipo_abitazione=tipo_abitazione,
                        tipo_pdc=tipo_pdc_ibr,
                        tipo_soggetto=tipo_soggetto_ibr,
                        usa_premialita_componenti_ue=usa_premialita_ue_ibr,
                        usa_premialita_combinato_titolo_iii=usa_premialita_combinato_ibr,
                        tasso_sconto=tasso_sconto
                    )

                    # Visualizzazione risultati in 3 colonne
                    # Mostra risultati - condizionale in base a solo_conto_termico
                    if solo_conto_termico:
                        # Modalità Solo CT 3.0
                        st.markdown("### 🏛️ Conto Termico 3.0")
                        if confronto_ibr["ct"] and "errore" not in confronto_ibr["ct"]:
                            ct_data = confronto_ibr["ct"]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Incentivo Totale",
                                    format_currency(ct_data["incentivo"]),
                                    delta=None
                                )
                            with col2:
                                st.metric("NPV (3%)", format_currency(confronto_ibr["npv_ct"]))

                            if ct_data["rata_unica"]:
                                st.info("💰 **Rata unica**")
                            else:
                                st.info(f"📅 **{ct_data['anni']} rate annuali** - Rata: {format_currency(ct_data['rata_annuale'])}")

                            with st.expander("📊 Dettagli calcolo CT"):
                                dettagli_ct = ct_data["dettagli"]
                                st.write(f"**Tipo sistema:** {dettagli_ct.tipo_sistema}")
                                st.write(f"**Coefficiente k:** {dettagli_ct.coefficiente_k}")
                                st.write(f"**Coefficiente Ci:** {dettagli_ct.coefficiente_ci} €/kWh_t")
                                st.write(f"**Energia incentivata (Ei):** {dettagli_ct.energia_incentivata_ei:,.0f} kWh_t")
                        else:
                            st.error("❌ Non calcolabile")
                            if "errore" in confronto_ibr["ct"]:
                                st.write(confronto_ibr["ct"]["errore"])
                    else:
                        # Modalità confronto completo
                        col1, col2, col3 = st.columns(3)

                        # Conto Termico 3.0
                        with col1:
                            st.markdown("### 🏛️ Conto Termico 3.0")
                            if confronto_ibr["ct"] and "errore" not in confronto_ibr["ct"]:
                                ct_data = confronto_ibr["ct"]
                                st.metric(
                                    "Incentivo Totale",
                                    format_currency(ct_data["incentivo"]),
                                    delta=None
                                )

                                if ct_data["rata_unica"]:
                                    st.info("💰 **Rata unica**")
                                else:
                                    st.info(f"📅 **{ct_data['anni']} rate annuali**")
                                    st.write(f"Rata: {format_currency(ct_data['rata_annuale'])}")

                                st.metric("NPV (3%)", format_currency(confronto_ibr["npv_ct"]))

                                with st.expander("📊 Dettagli calcolo CT"):
                                    dettagli_ct = ct_data["dettagli"]
                                    st.write(f"**Tipo sistema:** {dettagli_ct.tipo_sistema}")
                                    st.write(f"**Coefficiente k:** {dettagli_ct.coefficiente_k}")
                                    st.write(f"**Coefficiente Ci:** {dettagli_ct.coefficiente_ci} €/kWh_t")
                                    st.write(f"**Energia incentivata (Ei):** {dettagli_ct.energia_incentivata_ei:,.0f} kWh_t")
                                    st.write(f"**Energia totale (Qu):** {dettagli_ct.energia_totale_qu:,.0f} kWh_t")
                                    st.write(f"**Coefficiente kp:** {dettagli_ct.coefficiente_kp:.4f}")
                            else:
                                st.error("❌ Non calcolabile")
                                if "errore" in confronto_ibr["ct"]:
                                    st.write(confronto_ibr["ct"]["errore"])

                        # Ecobonus
                        with col2:
                            st.markdown("### 🏠 Ecobonus")
                            if confronto_ibr["ecobonus"] and "errore" not in confronto_ibr["ecobonus"]:
                                eco_data = confronto_ibr["ecobonus"]
                                st.metric(
                                    "Detrazione Totale",
                                    format_currency(eco_data["detrazione"]),
                                    delta=None
                                )

                                st.info(f"📅 **{eco_data['anni']} rate annuali**")
                                st.write(f"Rata: {format_currency(eco_data['rata_annuale'])}")
                                st.write(f"Aliquota: {eco_data['aliquota']*100:.0f}%")

                                st.metric("NPV (3%)", format_currency(confronto_ibr["npv_ecobonus"]))

                                with st.expander("📊 Dettagli Ecobonus"):
                                    st.write(f"**Anno:** {anno_spesa_ibr}")
                                    st.write(f"**Tipo abitazione:** {tipo_abitazione}")
                                    st.write(f"**Limite detrazione:** 60.000 €")
                                    st.write(f"**Scadenza ENEA:** 90 giorni")
                            else:
                                st.error("❌ Non applicabile")
                                if "errore" in confronto_ibr["ecobonus"]:
                                    st.write(confronto_ibr["ecobonus"]["errore"])

                        # Bonus Ristrutturazione
                        with col3:
                            st.markdown("### 🔧 Bonus Ristrutturazione")
                            if confronto_ibr["bonus_ristrutturazione"] and "errore" not in confronto_ibr["bonus_ristrutturazione"]:
                                bonus_data = confronto_ibr["bonus_ristrutturazione"]
                                st.metric(
                                    "Detrazione Totale",
                                    format_currency(bonus_data["detrazione"]),
                                    delta=None
                                )

                                st.info(f"📅 **{bonus_data['anni']} rate annuali**")
                                st.write(f"Rata: {format_currency(bonus_data['rata_annuale'])}")
                                st.write(f"Aliquota: {bonus_data['aliquota']*100:.0f}%")

                                st.metric("NPV (3%)", format_currency(confronto_ibr["npv_bonus_ristrutturazione"]))

                                st.warning("⚠️ **NON cumulabile con Ecobonus**")

                                with st.expander("📊 Dettagli Bonus Ristrutturazione"):
                                    st.write(f"**Anno:** {anno_spesa_ibr}")
                                    st.write(f"**Tipo abitazione:** {tipo_abitazione}")
                                    st.write(f"**Limite spesa:** 96.000 €")
                                    st.write(f"**Scadenza ENEA:** 90 giorni")
                            else:
                                st.error("❌ Non applicabile")
                                if "errore" in confronto_ibr["bonus_ristrutturazione"]:
                                    st.write(confronto_ibr["bonus_ristrutturazione"]["errore"])

                        st.divider()

                        # Grafico confronto NPV
                        st.subheader("📊 Confronto NPV (Net Present Value)")

                        import plotly.graph_objects as go

                        npv_data_ibr = {
                            "Incentivo": ["Conto Termico 3.0", "Ecobonus", "Bonus Ristrutturazione"],
                            "NPV (€)": [
                                confronto_ibr["npv_ct"],
                                confronto_ibr["npv_ecobonus"],
                                confronto_ibr["npv_bonus_ristrutturazione"]
                            ],
                            "Colore": ["#1E88E5", "#43A047", "#FB8C00"]
                        }

                        fig_ibr = go.Figure(data=[
                            go.Bar(
                                x=npv_data_ibr["Incentivo"],
                                y=npv_data_ibr["NPV (€)"],
                                marker_color=npv_data_ibr["Colore"],
                                text=[format_currency(v) for v in npv_data_ibr["NPV (€)"]],
                                textposition="outside"
                            )
                        ])

                        fig_ibr.update_layout(
                            title="Confronto NPV Incentivi - Sistemi Ibridi",
                            xaxis_title="Tipo Incentivo",
                            yaxis_title="NPV (€)",
                            height=400,
                            showlegend=False
                        )

                        st.plotly_chart(fig_ibr, use_container_width=True)

                        # Migliore incentivo
                        st.success(f"🏆 **MIGLIORE INCENTIVO:** {confronto_ibr['migliore']} con NPV di {format_currency(max(confronto_ibr['npv_ct'], confronto_ibr['npv_ecobonus'], confronto_ibr['npv_bonus_ristrutturazione']))}")

                    # Salva nel session state per uso successivo
                    ct_data_ibr = confronto_ibr.get("ct", {})
                    eco_data_ibr = confronto_ibr.get("ecobonus", {})
                    bonus_data_ibr = confronto_ibr.get("bonus_ristrutturazione", {})

                    st.session_state.ultimo_calcolo_ibridi = {
                        "iter_semplificato": iter_semplificato_ibr,
                        "prodotto_catalogo": {
                            "marca": prodotto_catalogo_ibr.get("marca") if prodotto_catalogo_ibr else None,
                            "modello_pdc": prodotto_catalogo_ibr.get("modello_pompa_calore") if prodotto_catalogo_ibr else None,
                            "modello_caldaia": prodotto_catalogo_ibr.get("modello_caldaia_condensazione") if prodotto_catalogo_ibr else None
                        } if prodotto_catalogo_ibr else None,
                        "tipo_sistema": tipo_sistema_ibr,
                        "potenza_pdc_kw": potenza_pdc_ibr,
                        "potenza_caldaia_kw": potenza_caldaia_ibr,
                        "scop": scop_pdc_ibr,
                        "eta_s_pdc": eta_s_pdc_ibr,
                        "eta_s_caldaia": eta_s_caldaia_ibr,
                        "spesa": spesa_ibr,
                        "tipo_soggetto": tipo_soggetto_ibr,
                        "zona_climatica": zona_climatica,
                        "usa_premialita_ue": usa_premialita_ue_ibr,
                        "usa_premialita_combinato": usa_premialita_combinato_ibr,
                        "ct_data": ct_data_ibr,
                        "eco_data": eco_data_ibr,
                        "bonus_data": bonus_data_ibr,
                        "npv_ct": confronto_ibr.get("npv_ct", 0),
                        "npv_ecobonus": confronto_ibr.get("npv_ecobonus", 0),
                        "npv_bonus_ristrutturazione": confronto_ibr.get("npv_bonus_ristrutturazione", 0),
                        "migliore": confronto_ibr.get("migliore", "")
                    }

            except Exception as e:
                st.error(f"Errore nel calcolo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # Pulsante salva scenario ibridi (FUORI dal blocco calcola)
        st.divider()
        col_save_ibr1, col_save_ibr2 = st.columns([3, 1])
        with col_save_ibr1:
            salva_scenario_ibr = st.button(
                "💾 Salva Scenario Ibridi",
                type="secondary",
                use_container_width=True,
                key="btn_salva_ibr",
                disabled=len(st.session_state.scenari_ibridi) >= 5
            )
        with col_save_ibr2:
            st.write(f"({len(st.session_state.scenari_ibridi)}/5)")

        if salva_scenario_ibr:
            if st.session_state.ultimo_calcolo_ibridi is None:
                st.warning("⚠️ Prima calcola gli incentivi con CALCOLA CONFRONTO")
            elif len(st.session_state.scenari_ibridi) >= 5:
                st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")
            else:
                dati = st.session_state.ultimo_calcolo_ibridi
                ct_data = dati.get("ct_data", {})
                eco_data = dati.get("eco_data", {})
                bonus_data = dati.get("bonus_data", {})
                nuovo_scenario = {
                    "id": len(st.session_state.scenari_ibridi) + 1,
                    "nome": f"Ibrido {len(st.session_state.scenari_ibridi) + 1}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "iter_semplificato": dati["iter_semplificato"],
                    "prodotto_catalogo": dati["prodotto_catalogo"],
                    "tipo_sistema": dati["tipo_sistema"],
                    "potenza_pdc_kw": dati["potenza_pdc_kw"],
                    "potenza_caldaia_kw": dati["potenza_caldaia_kw"],
                    "scop": dati["scop"],
                    "eta_s_caldaia": dati["eta_s_caldaia"],
                    "spesa": dati["spesa"],
                    "tipo_soggetto": dati["tipo_soggetto"],
                    "ct_incentivo": ct_data.get("incentivo", 0) if ct_data and "errore" not in ct_data else 0,
                    "ct_npv": dati["npv_ct"],
                    "eco_detrazione": eco_data.get("detrazione", 0) if eco_data and "errore" not in eco_data else 0,
                    "eco_npv": dati["npv_ecobonus"],
                    "bonus_detrazione": bonus_data.get("detrazione", 0) if bonus_data and "errore" not in bonus_data else 0,
                    "bonus_npv": dati["npv_bonus_ristrutturazione"],
                    "migliore": dati["migliore"]
                }
                st.session_state.scenari_ibridi.append(nuovo_scenario)
                st.success(f"✅ Scenario salvato! ({len(st.session_state.scenari_ibridi)}/5)")
                st.rerun()

    # ===========================================================================
    # TAB 8: SCALDACQUA A POMPA DI CALORE (III.E)
    # ===========================================================================
    with tab_scaldacqua:
        st.header("🚿 Scaldacqua a Pompa di Calore (Intervento III.E)")
        st.caption("Sostituzione scaldacqua elettrici/a gas con scaldacqua a pompa di calore - Art. 8, comma 1, lettera e)")

        # Import moduli scaldacqua
        from modules.validator_scaldacqua_pdc import valida_requisiti_scaldacqua_pdc
        from modules.calculator_scaldacqua_ct import calculate_scaldacqua_ct_incentive
        from modules.calculator_scaldacqua_ecobonus import calculate_scaldacqua_ecobonus_incentive, confronta_ct_ecobonus

        # Nota importante
        st.info("""
        ⚠️ **REQUISITO CRITICO**: L'intervento III.E è ammissibile SOLO per **SOSTITUZIONE**
        di scaldacqua esistenti (elettrici o a gas). Non sono ammesse nuove installazioni.

        L'edificio deve essere **dotato di impianto di climatizzazione** preesistente.
        """)

        # Tabs interni: Input / Risultati / Info
        tab_input_sc, tab_risultati_sc, tab_info_sc = st.tabs(["📝 Dati Intervento", "💰 Risultati", "ℹ️ Info Normativa"])

        with tab_input_sc:
            st.subheader("Dati dell'Intervento")

            # Sezione 1: Caratteristiche scaldacqua sostituito
            st.markdown("#### 1️⃣ Scaldacqua sostituito")
            col1, col2 = st.columns(2)

            with col1:
                sostituisce_impianto = st.checkbox(
                    "✅ Sostituisce scaldacqua esistente (OBBLIGATORIO)",
                    value=True,
                    key="sc_sostituisce",
                    help="Requisito obbligatorio: deve configurarsi come sostituzione"
                )

                tipo_scaldacqua_sostituito = st.selectbox(
                    "Tipo scaldacqua sostituito",
                    options=["elettrico", "gas"],
                    format_func=lambda x: {
                        "elettrico": "⚡ Elettrico (resistenza)",
                        "gas": "🔥 A gas (metano/GPL)"
                    }[x],
                    key="sc_tipo_sostituito"
                )

            with col2:
                edificio_con_climatizzazione = st.checkbox(
                    "🏠 Edificio con impianto climatizzazione (OBBLIGATORIO)",
                    value=True,
                    key="sc_climatizzazione",
                    help="L'edificio deve essere dotato di impianto di climatizzazione"
                )

            # Sezione 2: Ricerca dal Catalogo GSE
            st.markdown("#### 2️⃣ Ricerca dal Catalogo GSE")

            # Carica catalogo scaldacqua
            catalogo_scaldacqua = load_catalogo_scaldacqua()

            # Checkbox per usare il catalogo
            usa_catalogo_sc = st.checkbox(
                "🔍 Cerca nel Catalogo GSE 2D (Scaldacqua PdC)",
                value=False,
                help="Seleziona uno scaldacqua dal catalogo GSE per l'iter semplificato (potenza ≤ 35 kW)",
                key="sc_usa_catalogo"
            )

            # Variabili per prodotto selezionato
            prodotto_catalogo_sc = None
            iter_semplificato_sc = False

            if usa_catalogo_sc and catalogo_scaldacqua:
                # Filtro per potenza ≤ 35 kW (requisito iter semplificato)
                catalogo_filtrato_sc = [
                    p for p in catalogo_scaldacqua
                    if p.get("dati_tecnici", {}).get("potenza_kw") and
                       p.get("dati_tecnici", {}).get("potenza_kw") <= 35
                ]

                if not catalogo_filtrato_sc:
                    st.warning("⚠️ Nessun prodotto ≤ 35 kW trovato nel catalogo.")
                else:
                    st.info(f"📋 {len(catalogo_filtrato_sc)} prodotti disponibili (≤ 35 kW)")

                    # Selezione marca
                    marche_disponibili_sc = get_marche_catalogo_scaldacqua(catalogo_filtrato_sc)
                    marca_selezionata_sc = st.selectbox(
                        "Marca",
                        options=[""] + marche_disponibili_sc,
                        index=0,
                        help="Seleziona la marca dello scaldacqua",
                        key="sc_marca_cat"
                    )

                    if marca_selezionata_sc:
                        # Ottieni modelli per marca
                        modelli_marca_sc = get_modelli_per_marca_scaldacqua(catalogo_filtrato_sc, marca_selezionata_sc)
                        opzioni_modelli_sc = [""] + [
                            f"{m['modello']} ({m.get('dati_tecnici', {}).get('capacita_litri', '?')} L, COP {m.get('dati_tecnici', {}).get('cop', '?')})"
                            for m in modelli_marca_sc
                        ]

                        modello_idx_sc = st.selectbox(
                            "Modello",
                            options=range(len(opzioni_modelli_sc)),
                            format_func=lambda x: opzioni_modelli_sc[x],
                            index=0,
                            help="Seleziona il modello",
                            key="sc_modello_cat"
                        )

                        if modello_idx_sc > 0:
                            prodotto_catalogo_sc = modelli_marca_sc[modello_idx_sc - 1]
                            iter_semplificato_sc = True

                            # Mostra info prodotto selezionato
                            dati_tec_sc = prodotto_catalogo_sc.get("dati_tecnici", {})
                            st.success(f"""
                            ✅ **ITER SEMPLIFICATO** (Art. 14, comma 5, DM 7/8/2025)

                            **{prodotto_catalogo_sc.get('marca')} {prodotto_catalogo_sc.get('modello')}**
                            - Capacità: {dati_tec_sc.get('capacita_litri', 'N/D')} litri
                            - Potenza: {dati_tec_sc.get('potenza_kw', 'N/D')} kW
                            - COP: {dati_tec_sc.get('cop', 'N/D')}
                            - Tipologia: {prodotto_catalogo_sc.get('tipologia_intervento', '2.D')}
                            """)

                            # Vantaggi iter semplificato
                            with st.expander("ℹ️ Vantaggi Iter Semplificato (potenza ≤ 35 kW)", expanded=False):
                                st.markdown("""
                                **Semplificazioni documentali:**
                                - ✅ **NON richiede asseverazione tecnica** (anche se P > 35 kW per scaldacqua)
                                - ✅ Sufficiente **certificazione del produttore** per requisiti tecnici
                                - ✅ Prodotto già validato GSE nel Catalogo 2D

                                **Documentazione richiesta:**
                                - Dichiarazione di conformità DM 37/2008
                                - Certificato smaltimento scaldacqua sostituito
                                - Documentazione spese (fatture, bonifici)

                                **Tempi più rapidi** per l'istruttoria della pratica.
                                """)

            st.divider()

            # Sezione 3: Caratteristiche scaldacqua installato
            st.markdown("#### 3️⃣ Scaldacqua a PdC installato")
            col1, col2, col3 = st.columns(3)

            with col1:
                classe_energetica_sc = st.selectbox(
                    "Classe energetica (Reg. UE 812/2013)",
                    options=["A", "A+", "A++", "A+++"],
                    index=0,
                    key="sc_classe",
                    help="Classe minima OBBLIGATORIA: A",
                    disabled=iter_semplificato_sc
                )

            with col2:
                # Auto-compila capacità se prodotto selezionato da catalogo
                capacita_default_sc = 200
                if prodotto_catalogo_sc:
                    capacita_cat = prodotto_catalogo_sc.get("dati_tecnici", {}).get("capacita_litri")
                    if capacita_cat:
                        capacita_default_sc = capacita_cat

                capacita_accumulo_sc = st.number_input(
                    "Capacità accumulo (litri)",
                    min_value=50,
                    max_value=1000,
                    value=capacita_default_sc,
                    step=10,
                    key="sc_capacita",
                    help="Soglia per incentivo massimo: 150 litri" + (" - AUTO-COMPILATO da catalogo" if prodotto_catalogo_sc else ""),
                    disabled=iter_semplificato_sc
                )

            with col3:
                # Auto-compila potenza se prodotto selezionato da catalogo
                potenza_default_sc = 2.5
                if prodotto_catalogo_sc:
                    potenza_cat = prodotto_catalogo_sc.get("dati_tecnici", {}).get("potenza_kw")
                    if potenza_cat:
                        potenza_default_sc = potenza_cat

                potenza_termica_sc = st.number_input(
                    "Potenza termica nominale (kW)",
                    min_value=0.5,
                    max_value=50.0,
                    value=potenza_default_sc,
                    step=0.1,
                    key="sc_potenza",
                    help="Soglia asseverazione: 35 kW" + (" - AUTO-COMPILATO da catalogo" if prodotto_catalogo_sc else ""),
                    disabled=iter_semplificato_sc
                )

            # Catalogo GSE (auto-compilato se selezionato dalla ricerca)
            a_catalogo_sc = st.checkbox(
                "📋 Presente nel Catalogo GSE 2D (Scaldacqua PdC)",
                value=iter_semplificato_sc,
                key="sc_catalogo",
                help="Semplifica documentazione, non richiede asseverazione" + (" - AUTO-COMPILATO dalla ricerca catalogo" if iter_semplificato_sc else ""),
                disabled=iter_semplificato_sc
            )

            # Sezione 3: Documentazione
            st.markdown("#### 3️⃣ Documentazione")
            col1, col2, col3 = st.columns(3)

            with col1:
                ha_dich_conformita_sc = st.checkbox(
                    "Dichiarazione conformità DM 37/2008 (OBBLIG.)",
                    value=True,
                    key="sc_dich_conf"
                )

            with col2:
                ha_cert_smaltimento_sc = st.checkbox(
                    "Certificato smaltimento scaldacqua (OBBLIG.)",
                    value=True,
                    key="sc_cert_smalt",
                    help="Attestazione consegna in centro smaltimento"
                )

            with col3:
                ha_scheda_tecnica_sc = st.checkbox(
                    "Scheda tecnica produttore (OBBLIG. se non a catalogo)",
                    value=True,
                    key="sc_scheda_tec"
                )

            # Sezione 4: Spese
            st.markdown("#### 4️⃣ Spese sostenute")
            col1, col2 = st.columns(2)

            with col1:
                spesa_lavori_sc = st.number_input(
                    "Spesa lavori scaldacqua PdC (€)",
                    min_value=0.0,
                    max_value=50000.0,
                    value=2500.0,
                    step=100.0,
                    key="sc_spesa_lavori",
                    help="Include fornitura, posa, smontaggio, opere murarie"
                )

            with col2:
                spesa_tecnici_sc = st.number_input(
                    "Spese tecniche (€)",
                    min_value=0.0,
                    max_value=5000.0,
                    value=0.0,
                    step=50.0,
                    key="sc_spesa_tecnici",
                    help="Asseverazione, comunicazione ENEA (per Ecobonus)"
                )

            # Sezione 5: Potenza edificio (per requisiti speciali)
            with st.expander("⚙️ Impostazioni avanzate (solo se potenza edificio ≥ 200 kW)"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    potenza_edificio_sc = st.number_input(
                        "Potenza complessiva edificio (kW)",
                        min_value=0.0,
                        max_value=5000.0,
                        value=0.0,
                        step=10.0,
                        key="sc_pot_edificio",
                        help="Se ≥ 200 kW: richiesti diagnosi energetica e APE"
                    )

                with col2:
                    ha_diagnosi_sc = st.checkbox(
                        "Diagnosi energetica ante-operam",
                        value=False,
                        key="sc_diagnosi"
                    )

                with col3:
                    ha_ape_post_sc = st.checkbox(
                        "APE post-operam",
                        value=False,
                        key="sc_ape_post"
                    )

            st.divider()

            # Pulsanti azione
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                calcola_sc = st.button("🔍 Calcola Incentivi", type="primary", use_container_width=True, key="btn_calc_sc")
            with col_btn2:
                salva_scenario_sc = st.button("💾 Salva Scenario", use_container_width=True, key="btn_salva_sc", disabled=len(st.session_state.scenari_scaldacqua) >= 5)

            if calcola_sc or salva_scenario_sc:
                try:
                    # Determina tipo edificio da tipo soggetto
                    tipo_edificio = "pubblico" if tipo_soggetto == "pa" else "residenziale"

                    # Determina abitazione_principale da tipo_abitazione per Ecobonus
                    abitazione_principale = (tipo_abitazione == "abitazione_principale")

                    # Validazione requisiti
                    validazione_sc = valida_requisiti_scaldacqua_pdc(
                        sostituisce_impianto_esistente=sostituisce_impianto,
                        tipo_scaldacqua_sostituito=tipo_scaldacqua_sostituito,
                        classe_energetica=classe_energetica_sc,
                        capacita_accumulo_litri=capacita_accumulo_sc,
                        potenza_termica_nominale_kw=potenza_termica_sc,
                        edificio_con_impianto_climatizzazione=edificio_con_climatizzazione,
                        ha_dichiarazione_conformita=ha_dich_conformita_sc,
                        ha_certificato_smaltimento=ha_cert_smaltimento_sc,
                        ha_scheda_tecnica_produttore=ha_scheda_tecnica_sc,
                        spesa_sostenuta=spesa_lavori_sc,
                        tipo_soggetto=tipo_soggetto,
                        tipo_edificio=tipo_edificio,
                        potenza_complessiva_edificio_kw=potenza_edificio_sc,
                        ha_diagnosi_energetica_ante=ha_diagnosi_sc,
                        ha_ape_post=ha_ape_post_sc,
                        a_catalogo_gse=a_catalogo_sc
                    )

                    # Mostra risultati validazione
                    if validazione_sc["ammissibile"]:
                        st.success(f"✅ **INTERVENTO AMMISSIBILE** - Punteggio: {validazione_sc['punteggio']}/100")
                    else:
                        st.error("❌ **INTERVENTO NON AMMISSIBILE**")
                        for errore in validazione_sc["errori"]:
                            st.error(f"• {errore}")
                        st.stop()

                    # Warnings
                    if validazione_sc["warnings"]:
                        for warning in validazione_sc["warnings"]:
                            st.warning(f"⚠️ {warning}")

                    # Suggerimenti
                    if validazione_sc["suggerimenti"]:
                        with st.expander("💡 Suggerimenti e Note", expanded=True):
                            for sugg in validazione_sc["suggerimenti"]:
                                st.info(sugg)

                    st.divider()

                    # Calcolo incentivo Conto Termico 3.0
                    st.subheader("💰 Conto Termico 3.0")
                    risultato_ct_sc = calculate_scaldacqua_ct_incentive(
                        classe_energetica=classe_energetica_sc,
                        capacita_accumulo_litri=capacita_accumulo_sc,
                        spesa_sostenuta=spesa_lavori_sc,
                        tipo_soggetto=tipo_soggetto,
                        tipo_edificio=tipo_edificio,
                        tasso_sconto=tasso_sconto
                    )

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "💚 Incentivo CT 3.0",
                            f"€ {risultato_ct_sc['incentivo_totale']:,.0f}",
                            delta=f"{risultato_ct_sc['percentuale_applicata'] * 100:.0f}% spesa"
                        )
                    with col2:
                        st.metric(
                            "🔄 Erogazione",
                            f"{risultato_ct_sc['anni_erogazione']} {'anno' if risultato_ct_sc['anni_erogazione'] == 1 else 'anni'}",
                            delta=f"€ {risultato_ct_sc['rata_annuale']:,.0f}/anno"
                        )
                    with col3:
                        st.metric(
                            f"📊 NPV ({tasso_sconto*100:.1f}%)",
                            f"€ {risultato_ct_sc['npv']:,.0f}",
                            delta="Valore attuale"
                        )
                    with col4:
                        spesa_netta_ct_sc = spesa_lavori_sc - risultato_ct_sc['incentivo_totale']
                        st.metric(
                            "💸 Spesa Netta",
                            f"€ {spesa_netta_ct_sc:,.0f}",
                            delta=f"-{(risultato_ct_sc['incentivo_totale'] / spesa_lavori_sc * 100):.1f}%"
                        )

                    with st.expander("📋 Dettagli calcolo CT 3.0", expanded=False):
                        dettagli_ct = risultato_ct_sc['dettagli']
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Classe energetica:** {dettagli_ct['classe_energetica']}")
                            st.write(f"**Capacità:** {dettagli_ct['capacita_litri']} litri ({dettagli_ct['capacita_categoria']})")
                            st.write(f"**Percentuale incentivo:** {dettagli_ct['percentuale_incentivo']}")
                            st.write(f"**Tipo soggetto:** {dettagli_ct['tipo_soggetto']}")
                        with col_b:
                            st.write(f"**Incentivo calcolato:** € {dettagli_ct['incentivo_calcolato']:,.2f}")
                            st.write(f"**Limite max tabella 38:** € {dettagli_ct['incentivo_max_tabella']:,.2f}")
                            st.write(f"**Limite applicato:** {'Sì' if dettagli_ct['applicato_limite'] else 'No'}")
                            st.write(f"**Modalità erogazione:** {dettagli_ct['modalita_erogazione']}")
                        if dettagli_ct.get('nota_pa'):
                            st.info(f"ℹ️ {dettagli_ct['nota_pa']}")

                    st.divider()

                    # Calcolo Ecobonus
                    st.subheader("🏡 Ecobonus")
                    risultato_eco_sc = calculate_scaldacqua_ecobonus_incentive(
                        spesa_sostenuta=spesa_lavori_sc,
                        abitazione_principale=abitazione_principale,
                        anno_intervento=2025,
                        spesa_tecnici=spesa_tecnici_sc,
                        tasso_sconto=tasso_sconto
                    )

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "🏠 Detrazione Ecobonus",
                            f"€ {risultato_eco_sc['detrazione_totale']:,.0f}",
                            delta=f"{risultato_eco_sc['aliquota_applicata'] * 100:.0f}% spesa"
                        )
                    with col2:
                        st.metric(
                            "📅 Recupero",
                            f"{risultato_eco_sc['anni_recupero']} anni",
                            delta=f"€ {risultato_eco_sc['detrazione_annuale']:,.0f}/anno"
                        )
                    with col3:
                        st.metric(
                            f"📊 NPV ({tasso_sconto*100:.1f}%)",
                            f"€ {risultato_eco_sc['npv']:,.0f}",
                            delta="Valore attuale"
                        )
                    with col4:
                        st.metric(
                            "💸 Spesa Netta",
                            f"€ {risultato_eco_sc['spesa_netta']:,.0f}",
                            delta=f"-{(risultato_eco_sc['detrazione_totale'] / risultato_eco_sc['spesa_ammissibile'] * 100):.1f}%"
                        )

                    with st.expander("📋 Dettagli calcolo Ecobonus", expanded=False):
                        dettagli_eco = risultato_eco_sc['dettagli']
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Aliquota:** {dettagli_eco['aliquota_percentuale']}")
                            st.write(f"**Abitazione principale:** {'Sì' if dettagli_eco['abitazione_principale'] else 'No'}")
                            st.write(f"**Anno intervento:** {dettagli_eco['anno_intervento']}")
                            st.write(f"**Spesa lavori:** € {dettagli_eco['spesa_lavori']:,.2f}")
                            st.write(f"**Spese tecniche:** € {dettagli_eco['spesa_tecnici']:,.2f}")
                        with col_b:
                            st.write(f"**Detrazione calcolata:** € {dettagli_eco['detrazione_calcolata']:,.2f}")
                            st.write(f"**Limite max:** € {dettagli_eco['limite_detrazione']:,.2f}")
                            st.write(f"**Limite applicato:** {'Sì' if dettagli_eco['applicato_limite'] else 'No'}")
                            st.write(f"**Modalità recupero:** {dettagli_eco['modalita_recupero']}")
                            st.write(f"**Risparmio effettivo:** {dettagli_eco['percentuale_risparmio']:.1f}%")

                    st.divider()

                    # Confronto CT vs Ecobonus
                    st.subheader("⚖️ Confronto CT 3.0 vs Ecobonus")
                    confronto_sc = confronta_ct_ecobonus(risultato_ct_sc, risultato_eco_sc, spesa_lavori_sc)

                    if confronto_sc['piu_conveniente'] == "CT":
                        st.success(f"🏆 **PIÙ CONVENIENTE: Conto Termico 3.0** (vantaggio NPV: € {confronto_sc['differenza_npv']:,.0f}, +{confronto_sc['vantaggio_percentuale']:.1f}%)")
                    else:
                        st.success(f"🏆 **PIÙ CONVENIENTE: Ecobonus** (vantaggio NPV: € {confronto_sc['differenza_npv']:,.0f}, +{confronto_sc['vantaggio_percentuale']:.1f}%)")

                    # Tabella comparativa
                    df_confronto_sc = pd.DataFrame({
                        "Incentivo": ["Conto Termico 3.0", "Ecobonus"],
                        "Importo Totale": [
                            f"€ {risultato_ct_sc['incentivo_totale']:,.0f}",
                            f"€ {risultato_eco_sc['detrazione_totale']:,.0f}"
                        ],
                        "Tempo Recupero": [
                            f"{risultato_ct_sc['anni_erogazione']} {'anno' if risultato_ct_sc['anni_erogazione'] == 1 else 'anni'}",
                            f"{risultato_eco_sc['anni_recupero']} anni"
                        ],
                        f"NPV ({tasso_sconto*100:.1f}%)": [
                            f"€ {risultato_ct_sc['npv']:,.0f}",
                            f"€ {risultato_eco_sc['npv']:,.0f}"
                        ],
                        "Spesa Netta": [
                            f"€ {confronto_sc['dettagli_confronto']['spesa_netta_ct']:,.0f}",
                            f"€ {confronto_sc['dettagli_confronto']['spesa_netta_ecobonus']:,.0f}"
                        ]
                    })

                    st.table(df_confronto_sc)

                    # Grafico comparativo
                    import plotly.graph_objects as go

                    fig_sc = go.Figure(data=[
                        go.Bar(name='Conto Termico 3.0', x=['Incentivo Totale', 'NPV'],
                               y=[risultato_ct_sc['incentivo_totale'], risultato_ct_sc['npv']],
                               marker_color='#2E7D32'),
                        go.Bar(name='Ecobonus', x=['Incentivo Totale', 'NPV'],
                               y=[risultato_eco_sc['detrazione_totale'], risultato_eco_sc['npv']],
                               marker_color='#1565C0')
                    ])

                    fig_sc.update_layout(
                        title="Confronto Incentivi",
                        xaxis_title="Metrica",
                        yaxis_title="Valore (€)",
                        barmode='group',
                        height=400
                    )

                    st.plotly_chart(fig_sc, use_container_width=True)

                    # Salva scenario se richiesto
                    if salva_scenario_sc and len(st.session_state.scenari_scaldacqua) < 5:
                        nome_scenario_sc = f"Scaldacqua {len(st.session_state.scenari_scaldacqua) + 1}"
                        scenario_data_sc = {
                            "nome": nome_scenario_sc,
                            "timestamp": datetime.now().isoformat(),
                            "iter_semplificato": iter_semplificato_sc,
                            "prodotto_catalogo": {
                                "marca": prodotto_catalogo_sc.get("marca"),
                                "modello": prodotto_catalogo_sc.get("modello")
                            } if prodotto_catalogo_sc else None,
                            "classe_energetica": classe_energetica_sc,
                            "capacita_litri": capacita_accumulo_sc,
                            "potenza_kw": potenza_termica_sc,
                            "spesa_lavori": spesa_lavori_sc,
                            "spesa_tecnici": spesa_tecnici_sc,
                            "tipo_soggetto": tipo_soggetto,
                            "abitazione_principale": abitazione_principale,
                            "ct_incentivo": risultato_ct_sc['incentivo_totale'],
                            "ct_npv": risultato_ct_sc['npv'],
                            "ct_anni_erogazione": risultato_ct_sc['anni_erogazione'],
                            "eco_detrazione": risultato_eco_sc['detrazione_totale'],
                            "eco_npv": risultato_eco_sc['npv'],
                            "eco_anni_recupero": risultato_eco_sc['anni_recupero'],
                            "piu_conveniente": confronto_sc['piu_conveniente'],
                            "differenza_npv": confronto_sc['differenza_npv'],
                            "vantaggio_percentuale": confronto_sc['vantaggio_percentuale']
                        }
                        st.session_state.scenari_scaldacqua.append(scenario_data_sc)
                        st.success(f"✅ Scenario salvato: {nome_scenario_sc}")
                        st.info(f"📊 Scenari salvati: {len(st.session_state.scenari_scaldacqua)}/5")
                    elif salva_scenario_sc:
                        st.warning("⚠️ Hai raggiunto il massimo di 5 scenari")

                except Exception as e:
                    st.error(f"Errore nel calcolo: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

        with tab_info_sc:
            st.subheader("ℹ️ Informazioni Normative - Intervento III.E")

            st.markdown("""
            ### Conto Termico 3.0

            **Riferimento normativo:**
            - D.M. 7 agosto 2025 - Conto Termico 3.0
            - Regole Applicative CT 3.0 - Paragrafo 9.13

            **Requisiti principali:**
            - ✅ Sostituzione di scaldacqua elettrici o a gas esistenti
            - ✅ Edificio dotato di impianto di climatizzazione
            - ✅ Classe energetica minima **A** (Reg. UE 812/2013)
            - ✅ Dichiarazione conformità DM 37/2008
            - ✅ Certificato smaltimento scaldacqua sostituito

            **Incentivo:**
            - **40%** della spesa sostenuta (100% per PA su edifici pubblici)
            - Limiti massimi da Tabella 38:
              - Classe A, ≤150 litri: **500 €**
              - Classe A, >150 litri: **1.100 €**
              - Classe A+, ≤150 litri: **700 €**
              - Classe A+, >150 litri: **1.500 €**

            **Erogazione:**
            - 2 rate annuali costanti
            - Rata unica se incentivo ≤ 15.000 €

            **Scadenza:**
            - Richiesta entro **60 giorni** dalla fine lavori

            ---

            ### Ecobonus

            **Riferimento normativo:**
            - D.L. 63/2013 - Ecobonus
            - Vademecum ENEA

            **Requisiti principali:**
            - ✅ COP > 2,6 (D.Lgs. 28/2011)
            - ✅ Valori minimi Allegato F del D.M. 6.08.2020
            - ✅ Comunicazione ENEA entro 90 giorni

            **Detrazione:**
            - **50%** per abitazione principale (2025)
            - **36%** per altre abitazioni (2025)
            - Limite: **30.000 €** di detrazione
            - Recupero in **10 anni**

            **Documentazione:**
            - Scheda descrittiva ENEA (CPID)
            - Asseverazione tecnico o dichiarazione produttore
            - Fatture e bonifici parlanti
            - Dichiarazione conformità DM 37/08

            **Scadenza:**
            - Comunicazione ENEA entro **90 giorni** dalla fine lavori

            ---

            ### Note Importanti

            ⚠️ **Non sono ammesse:**
            - Nuove installazioni senza sostituzione
            - Scaldacqua con classe energetica inferiore ad A
            - Installazioni in edifici senza impianto di climatizzazione

            💡 **Consigli:**
            - Preferisci classi energetiche superiori (A+, A++, A+++) per incentivi maggiori
            - Capacità >150 litri garantisce incentivo massimo più elevato
            - Verifica presenza nel Catalogo GSE per semplificare la documentazione
            - Per Ecobonus, considera le spese tecniche (asseverazione, ENEA) nel calcolo
            """)

    # ===========================================================================
    # TAB MULTI-INTERVENTO
    # ===========================================================================
    with tab_multi:
        st.header("🔗 Multi-Intervento")
        st.caption("Combina più interventi sullo stesso edificio per massimizzare gli incentivi")

        st.info("""
        **💡 Cos'è un Multi-Intervento?**

        Secondo il Conto Termico 3.0 (Art. 2, comma 1, lettera cc), un **multi-intervento** è la realizzazione
        contestuale su uno stesso edificio di più interventi (Titolo II e/o III), progettati e pianificati come
        unico progetto.

        **🎁 Vantaggi per le IMPRESE:**
        - Intensità incentivo aumenta dal **25% al 30%** dei costi ammissibili (+5%)
        - Possibile ulteriore **bonus +15%** con riduzione energia primaria ≥40%
        - Unica pratica GSE per tutti gli interventi
        """)

        st.divider()

        # Dati progetto
        st.subheader("📝 Dati Progetto Unico")

        col1, col2 = st.columns(2)
        with col1:
            nome_progetto = st.text_input(
                "Nome progetto",
                value=st.session_state.progetto_multi["nome_progetto"],
                placeholder="Es: Riqualificazione Edificio A",
                key="multi_nome_progetto"
            )
            # Trova la chiave corrispondente al valore salvato
            current_soggetto_value = st.session_state.progetto_multi["tipo_soggetto"]
            current_soggetto_key = None
            for k, v in TIPI_SOGGETTO.items():
                if v == current_soggetto_value:
                    current_soggetto_key = k
                    break
            if current_soggetto_key is None:
                current_soggetto_key = list(TIPI_SOGGETTO.keys())[0]

            tipo_soggetto_multi = st.selectbox(
                "Tipo soggetto",
                options=list(TIPI_SOGGETTO.keys()),
                index=list(TIPI_SOGGETTO.keys()).index(current_soggetto_key),
                key="multi_tipo_soggetto"
            )

        with col2:
            indirizzo_multi = st.text_input(
                "Indirizzo edificio",
                value=st.session_state.progetto_multi["indirizzo"],
                placeholder="Via Roma 1, Milano",
                key="multi_indirizzo"
            )
            tipo_edificio_multi = st.selectbox(
                "Tipo edificio",
                options=["residenziale", "terziario", "pubblico"],
                index=["residenziale", "terziario", "pubblico"].index(st.session_state.progetto_multi["tipo_edificio"]),
                key="multi_tipo_edificio"
            )

        # Aggiorna session state
        st.session_state.progetto_multi["nome_progetto"] = nome_progetto
        st.session_state.progetto_multi["tipo_soggetto"] = TIPI_SOGGETTO[tipo_soggetto_multi]
        st.session_state.progetto_multi["tipo_edificio"] = tipo_edificio_multi
        st.session_state.progetto_multi["indirizzo"] = indirizzo_multi

        st.divider()

        # Sezione interventi
        st.subheader("➕ Interventi del Progetto")

        # Mostra interventi già aggiunti
        if len(st.session_state.progetto_multi["interventi"]) == 0:
            st.info("Nessun intervento aggiunto. Usa il menu sottostante per aggiungere interventi al progetto.")
        else:
            st.write(f"**Interventi inclusi:** {len(st.session_state.progetto_multi['interventi'])}")

            for idx, intervento in enumerate(st.session_state.progetto_multi["interventi"]):
                with st.expander(f"**{idx+1}. {intervento['nome']}** - {intervento['tipo_label']}", expanded=False):
                    col_int1, col_int2, col_int3 = st.columns([2, 2, 1])

                    with col_int1:
                        st.write(f"**Tipo:** {intervento['tipo_label']}")
                        st.write(f"**Spesa totale:** {intervento['spesa_totale']:,.0f} €")

                    with col_int2:
                        st.write(f"**CT Incentivo:** {intervento['ct_incentivo']:,.0f} €")
                        st.write(f"**Ecobonus:** {intervento['eco_detrazione']:,.0f} €")

                    with col_int3:
                        if st.button("🗑️ Rimuovi", key=f"rimuovi_int_{idx}"):
                            st.session_state.progetto_multi["interventi"].pop(idx)
                            st.rerun()

        st.divider()

        # Aggiungi nuovo intervento
        st.subheader("➕ Aggiungi Nuovo Intervento")

        # Tab per scegliere metodo di aggiunta
        tab_import, tab_manuale = st.tabs(["📋 Import da Scenari Salvati", "✏️ Inserimento Manuale"])

        with tab_import:
            st.caption("Importa rapidamente interventi dagli scenari che hai già salvato nelle altre sezioni")

            # Verifica scenari disponibili
            scenari_disponibili = []

            # Pompe di Calore
            if len(st.session_state.scenari) > 0:
                for idx, s in enumerate(st.session_state.scenari):
                    fv_info = f" + FV {s.get('fv_potenza_kw', 0):.1f} kWp" if s.get('fv_combinato') and s.get('fv_potenza_kw', 0) > 0 else ""
                    scenari_disponibili.append({
                        "tipo": "pompe_calore",
                        "tipo_label": "Pompe di Calore (III.A)",
                        "display": f"PdC: {s['nome']} - {s['potenza_kw']} kW{fv_info}",
                        "data": s,
                        "index": idx
                    })

            # Solare Termico
            if len(st.session_state.scenari_solare) > 0:
                for idx, s in enumerate(st.session_state.scenari_solare):
                    scenari_disponibili.append({
                        "tipo": "solare_termico",
                        "tipo_label": "Solare Termico (III.B)",
                        "display": f"Solare: {s['nome']} - {s['superficie']:.1f} m²",
                        "data": s,
                        "index": idx
                    })

            # Scaldacqua PdC
            if len(st.session_state.scenari_scaldacqua) > 0:
                for idx, s in enumerate(st.session_state.scenari_scaldacqua):
                    scenari_disponibili.append({
                        "tipo": "scaldacqua_pdc",
                        "tipo_label": "Scaldacqua PdC (III.E)",
                        "display": f"Scaldacqua: {s['nome']} - Classe {s['classe_energetica']} {s['capacita_litri']}L",
                        "data": s,
                        "index": idx
                    })

            # Sistemi Ibridi
            if len(st.session_state.scenari_ibridi) > 0:
                for idx, s in enumerate(st.session_state.scenari_ibridi):
                    scenari_disponibili.append({
                        "tipo": "sistemi_ibridi",
                        "tipo_label": "Sistemi Ibridi (III.A)",
                        "display": f"Ibrido: {s['nome']} - PdC {s['potenza_pdc_kw']}kW + Caldaia {s['potenza_caldaia_kw']}kW",
                        "data": s,
                        "index": idx
                    })

            # Isolamento
            if len(st.session_state.scenari_isolamento) > 0:
                for idx, s in enumerate(st.session_state.scenari_isolamento):
                    scenari_disponibili.append({
                        "tipo": "isolamento",
                        "tipo_label": "Isolamento Termico (II.A)",
                        "display": f"Isolamento: {s['nome']} - {s['superficie_mq']:.1f} m²",
                        "data": s,
                        "index": idx
                    })

            # Serramenti
            if len(st.session_state.scenari_serramenti) > 0:
                for idx, s in enumerate(st.session_state.scenari_serramenti):
                    scenari_disponibili.append({
                        "tipo": "serramenti",
                        "tipo_label": "Serramenti (II.B)",
                        "display": f"Serramenti: {s['nome']} - {s['superficie_mq']:.1f} m²",
                        "data": s,
                        "index": idx
                    })

            # Building Automation
            if len(st.session_state.scenari_building_automation) > 0:
                for idx, s in enumerate(st.session_state.scenari_building_automation):
                    scenari_disponibili.append({
                        "tipo": "building_automation",
                        "tipo_label": "Building Automation (II.F)",
                        "display": f"Building Auto: {s['nome']} - {s['superficie_mq']:.1f} m²",
                        "data": s,
                        "index": idx
                    })

            if len(scenari_disponibili) == 0:
                st.info("ℹ️ Nessuno scenario salvato. Vai nelle varie sezioni e usa il pulsante '💾 Salva Scenario' per salvare interventi da importare qui.")
            else:
                st.write(f"**{len(scenari_disponibili)} scenari disponibili per l'import**")

                scenario_selezionato = st.selectbox(
                    "Seleziona uno scenario da importare",
                    options=["-- Seleziona --"] + [s["display"] for s in scenari_disponibili],
                    key="select_scenario_import"
                )

                if scenario_selezionato != "-- Seleziona --":
                    # Trova lo scenario selezionato
                    scenario_idx = [s["display"] for s in scenari_disponibili].index(scenario_selezionato)
                    scenario = scenari_disponibili[scenario_idx]

                    st.success(f"✅ Scenario selezionato: {scenario['tipo_label']}")

                    col_preview1, col_preview2 = st.columns(2)
                    with col_preview1:
                        st.write("**Dati scenario:**")
                        st.json({k: v for k, v in list(scenario['data'].items())[:5]}, expanded=False)

                    with col_preview2:
                        st.write("**Incentivi:**")
                        if 'ct_incentivo' in scenario['data']:
                            st.metric("CT", f"{scenario['data']['ct_incentivo']:,.0f} €")
                        if 'eco_detrazione' in scenario['data']:
                            st.metric("Eco", f"{scenario['data']['eco_detrazione']:,.0f} €")

                    if st.button("📥 Importa questo Scenario nel Multi-Intervento", type="primary", key="btn_import_scenario"):
                        # Validazione nZEB
                        tipi_esistenti = [i['tipo'] for i in st.session_state.progetto_multi["interventi"]]
                        if "nzeb" in tipi_esistenti or ("nzeb" in scenario['tipo'].lower() and len(tipi_esistenti) > 0):
                            st.error("❌ Non è possibile combinare interventi nZEB con altri interventi")
                        else:
                            # Converti scenario in InterventoMulti
                            s_data = scenario['data']

                            # Determina spesa totale e incentivi
                            spesa_totale = 0
                            ct_incentivo = 0
                            eco_detrazione = 0

                            if scenario['tipo'] == 'pompe_calore':
                                spesa_totale = s_data.get('spesa', 0)
                                if s_data.get('fv_combinato') and s_data.get('fv_spesa', 0) > 0:
                                    spesa_totale += s_data.get('fv_spesa', 0) + s_data.get('fv_spesa_accumulo', 0)
                                ct_incentivo = s_data.get('ct_incentivo', 0)
                                if s_data.get('fv_incentivo_ct', 0) > 0:
                                    ct_incentivo += s_data.get('fv_incentivo_ct', 0)
                                eco_detrazione = s_data.get('eco_detrazione', 0)
                                if s_data.get('fv_bonus_ristrutt', 0) > 0:
                                    eco_detrazione += s_data.get('fv_bonus_ristrutt', 0)
                            elif scenario['tipo'] == 'solare_termico':
                                spesa_totale = s_data.get('spesa', 0)
                                ct_incentivo = s_data.get('ct_incentivo', 0)
                                eco_detrazione = s_data.get('eco_detrazione', 0)
                            elif scenario['tipo'] == 'scaldacqua_pdc':
                                spesa_totale = s_data.get('spesa_lavori', 0) + s_data.get('spesa_tecnici', 0)
                                ct_incentivo = s_data.get('ct_incentivo', 0)
                                eco_detrazione = s_data.get('eco_detrazione', 0)
                            elif scenario['tipo'] == 'sistemi_ibridi':
                                spesa_totale = s_data.get('spesa', 0)
                                ct_incentivo = s_data.get('ct_incentivo', 0)
                                eco_detrazione = s_data.get('eco_detrazione', 0)
                            elif scenario['tipo'] in ['isolamento', 'serramenti', 'building_automation']:
                                spesa_totale = s_data.get('spesa_totale', 0) or s_data.get('spesa', 0)
                                ct_incentivo = s_data.get('ct_incentivo', 0)
                                eco_detrazione = s_data.get('eco_detrazione', 0)

                            nuovo_intervento = {
                                "tipo": scenario['tipo'].replace('_', ''),  # Es: "pompecalore"
                                "tipo_label": scenario['tipo_label'],
                                "nome": s_data.get('nome', 'Scenario importato'),
                                "spesa_totale": spesa_totale,
                                "ct_incentivo": ct_incentivo,
                                "eco_detrazione": eco_detrazione,
                                "dati": s_data  # Mantieni tutti i dati originali
                            }

                            st.session_state.progetto_multi["interventi"].append(nuovo_intervento)
                            st.success(f"✅ Scenario '{nuovo_intervento['nome']}' importato con successo!")
                            st.rerun()

        with tab_manuale:
            st.caption("Inserisci manualmente i dati di un nuovo intervento")

            tipo_intervento_nuovo = st.selectbox(
                "Seleziona tipo intervento da aggiungere",
                options=[
                    "-- Seleziona --",
                    "Pompe di Calore (III.A)",
                    "Solare Termico (III.B)",
                    "Scaldacqua PdC (III.E)",
                    "Sistemi Ibridi (III.A)",
                    "Biomassa (III.C)",
                    "Isolamento Termico (II.A)",
                    "Serramenti (II.B)",
                    "Building Automation (II.F)"
                ],
                key="tipo_int_nuovo"
            )

            if tipo_intervento_nuovo != "-- Seleziona --":
                st.info(f"📝 Configurazione: {tipo_intervento_nuovo}")

                # Form semplificato per aggiungere intervento
                with st.form("form_aggiungi_intervento"):
                    nome_int = st.text_input("Nome intervento", placeholder="Es: PdC 12 kW")

                    col_form1, col_form2 = st.columns(2)
                    with col_form1:
                        spesa_int = st.number_input("Spesa totale (€)", min_value=0.0, value=10000.0, step=100.0)
                        ct_incentivo_int = st.number_input("CT Incentivo stimato (€)", min_value=0.0, value=4000.0, step=100.0)

                    with col_form2:
                        eco_detrazione_int = st.number_input("Ecobonus stimato (€)", min_value=0.0, value=5000.0, step=100.0)

                    submit_int = st.form_submit_button("✅ Aggiungi Intervento")

                    if submit_int:
                        if not nome_int:
                            st.error("Inserisci un nome per l'intervento")
                        else:
                            # Validazione combinazioni
                            tipi_esistenti = [i['tipo'] for i in st.session_state.progetto_multi["interventi"]]

                            # Blocca nZEB + altri
                            if "nzeb" in tipi_esistenti or ("nzeb" in tipo_intervento_nuovo.lower() and len(tipi_esistenti) > 0):
                                st.error("❌ Non è possibile combinare interventi nZEB con altri interventi (nZEB comprende già tutte le categorie)")
                            else:
                                nuovo_intervento = {
                                    "tipo": tipo_intervento_nuovo.split("(")[1].strip(")").lower().replace(".", "_"),
                                    "tipo_label": tipo_intervento_nuovo,
                                    "nome": nome_int,
                                    "spesa_totale": spesa_int,
                                    "ct_incentivo": ct_incentivo_int,
                                    "eco_detrazione": eco_detrazione_int,
                                    "dati": {}  # Dati dettagliati (opzionale)
                                }

                                st.session_state.progetto_multi["interventi"].append(nuovo_intervento)
                                st.success(f"✅ Intervento '{nome_int}' aggiunto al progetto!")
                                st.rerun()

        st.divider()

        # Calcolo e riepilogo
        if len(st.session_state.progetto_multi["interventi"]) > 0:
            st.subheader("📊 Riepilogo Multi-Intervento")

            # Sezione APE e riduzione energia primaria (solo per imprese su edifici terziari)
            if TIPI_SOGGETTO[tipo_soggetto_multi] == "impresa" and tipo_edificio_multi == "terziario":
                with st.expander("⚡ Prestazione Energetica (APE) - Bonus +15%", expanded=False):
                    st.caption("Per imprese su edifici terziari con riduzione energia primaria ≥40%")

                    col_ape1, col_ape2 = st.columns(2)
                    with col_ape1:
                        ape_ante_operam = st.number_input(
                            "EPgl,nren ante-operam (kWh/m²anno)",
                            min_value=0.0,
                            value=st.session_state.progetto_multi.get("ape_ante_operam", 0.0),
                            step=1.0,
                            help="Indice di prestazione energetica globale non rinnovabile PRIMA degli interventi",
                            key="ape_ante"
                        )

                    with col_ape2:
                        ape_post_operam = st.number_input(
                            "EPgl,nren post-operam (kWh/m²anno)",
                            min_value=0.0,
                            value=st.session_state.progetto_multi.get("ape_post_operam", 0.0),
                            step=1.0,
                            help="Indice di prestazione energetica globale non rinnovabile DOPO gli interventi",
                            key="ape_post"
                        )

                    # Calcola riduzione percentuale
                    if ape_ante_operam > 0:
                        riduzione_ep_calc = ((ape_ante_operam - ape_post_operam) / ape_ante_operam) * 100
                        st.session_state.progetto_multi["riduzione_ep_perc"] = riduzione_ep_calc

                        col_rid1, col_rid2 = st.columns([2, 1])
                        with col_rid1:
                            st.metric(
                                "Riduzione Energia Primaria",
                                f"{riduzione_ep_calc:.1f}%",
                                delta="✅ Bonus +15% applicabile" if riduzione_ep_calc >= 40 else "⚠️ Soglia non raggiunta"
                            )
                        with col_rid2:
                            if riduzione_ep_calc >= 40:
                                st.success("✅ Soglia ≥40%")
                            else:
                                st.warning(f"⚠️ Serve {40 - riduzione_ep_calc:.1f}%")

                        if riduzione_ep_calc >= 40:
                            st.info("💡 **Bonus +15%** verrà applicato all'incentivo CT per interventi Titolo II (Art. 27, comma 3, lettera c)")
                    else:
                        st.session_state.progetto_multi["riduzione_ep_perc"] = None
                        st.info("Inserisci i valori di EPgl,nren ante e post-operam per calcolare la riduzione")

            # Calcola totali
            spesa_totale_multi = sum(i['spesa_totale'] for i in st.session_state.progetto_multi["interventi"])
            ct_base_multi = sum(i['ct_incentivo'] for i in st.session_state.progetto_multi["interventi"])
            eco_totale_multi = sum(i['eco_detrazione'] for i in st.session_state.progetto_multi["interventi"])

            # Bonus multi-intervento per imprese (solo Titolo II)
            bonus_multi_5 = 0  # Bonus +5% base multi-intervento
            bonus_multi_15 = 0  # Bonus +15% riduzione EP ≥40%

            if TIPI_SOGGETTO[tipo_soggetto_multi] == "impresa" and len(st.session_state.progetto_multi["interventi"]) >= 2:
                # Conta interventi Titolo II
                interventi_titolo_ii = [i for i in st.session_state.progetto_multi["interventi"] if i['tipo'].startswith("ii_")]
                if len(interventi_titolo_ii) >= 2:
                    spesa_titolo_ii = sum(i['spesa_totale'] for i in interventi_titolo_ii)

                    # Bonus +5% base multi-intervento
                    bonus_multi_5 = spesa_titolo_ii * 0.05

                    # Bonus +15% se riduzione EP ≥40%
                    riduzione_ep = st.session_state.progetto_multi.get("riduzione_ep_perc")
                    if riduzione_ep is not None and riduzione_ep >= 40:
                        bonus_multi_15 = spesa_titolo_ii * 0.15

            bonus_multi_totale = bonus_multi_5 + bonus_multi_15
            ct_totale_multi = ct_base_multi + bonus_multi_totale

            # Calcola NPV
            tasso_sconto = st.session_state.get("sidebar_tasso", 3.0) / 100
            npv_ct_multi = ct_totale_multi  # Semplificato, assumendo erogazione immediata
            npv_eco_multi = sum(
                (eco_totale_multi / 10) / ((1 + tasso_sconto) ** anno)
                for anno in range(1, 11)
            )

            # Mostra risultati
            col_ris1, col_ris2, col_ris3 = st.columns(3)

            with col_ris1:
                st.metric("Spesa Totale Progetto", f"{spesa_totale_multi:,.0f} €")
                st.metric("Numero Interventi", len(st.session_state.progetto_multi["interventi"]))

            with col_ris2:
                st.metric("CT Incentivo Base", f"{ct_base_multi:,.0f} €")
                if bonus_multi_5 > 0:
                    st.metric("✨ Bonus Multi (+5%)", f"{bonus_multi_5:,.0f} €", delta="Multi-intervento")

            with col_ris3:
                if bonus_multi_15 > 0:
                    st.metric("🌟 Bonus EP (+15%)", f"{bonus_multi_15:,.0f} €", delta="Riduzione ≥40%")
                    st.caption(f"Tot. bonus: {bonus_multi_totale:,.0f} €")

            st.divider()

            # Confronto CT vs Ecobonus
            col_conf1, col_conf2 = st.columns(2)

            with col_conf1:
                st.markdown("### 💰 Conto Termico 3.0")
                st.metric("Incentivo Totale CT", f"{ct_totale_multi:,.0f} €")
                st.metric("NPV (att. {:.1%})".format(tasso_sconto), f"{npv_ct_multi:,.0f} €")
                st.caption("Erogazione: 1-2 rate annuali")

            with col_conf2:
                st.markdown("### 💳 Ecobonus")
                st.metric("Detrazione Totale", f"{eco_totale_multi:,.0f} €")
                st.metric("NPV (att. {:.1%})".format(tasso_sconto), f"{npv_eco_multi:,.0f} €")
                st.caption("Recupero: 10 anni")

            # Convenienza
            if npv_ct_multi > npv_eco_multi:
                st.success(f"✅ **Conto Termico più conveniente** di {npv_ct_multi - npv_eco_multi:,.0f} € (NPV)")
            else:
                st.info(f"ℹ️ **Ecobonus più conveniente** di {npv_eco_multi - npv_ct_multi:,.0f} € (NPV)")

            st.divider()

            # Pulsanti azione
            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                salva_disabled = len(st.session_state.progetti_multi_salvati) >= 5 or not nome_progetto
                if st.button("💾 Salva Progetto Multi-Intervento", type="primary", use_container_width=True, disabled=salva_disabled):
                    # Crea snapshot del progetto corrente
                    progetto_salvato = {
                        "nome_progetto": nome_progetto,
                        "tipo_soggetto": TIPI_SOGGETTO[tipo_soggetto_multi],
                        "tipo_edificio": tipo_edificio_multi,
                        "indirizzo": indirizzo_multi,
                        "interventi": st.session_state.progetto_multi["interventi"].copy(),
                        "riduzione_ep_perc": st.session_state.progetto_multi.get("riduzione_ep_perc"),
                        "ape_ante_operam": st.session_state.progetto_multi.get("ape_ante_operam"),
                        "ape_post_operam": st.session_state.progetto_multi.get("ape_post_operam"),
                        "data_salvataggio": datetime.now().isoformat(),
                        # Dati calcolati
                        "spesa_totale": spesa_totale_multi,
                        "ct_incentivo_base": ct_base_multi,
                        "ct_bonus_multi_5": bonus_multi_5,
                        "ct_bonus_multi_15": bonus_multi_15,
                        "ct_incentivo_totale": ct_totale_multi,
                        "ct_npv": npv_ct_multi,
                        "eco_detrazione_totale": eco_totale_multi,
                        "eco_npv": npv_eco_multi,
                        "piu_conveniente": "CT" if npv_ct_multi > npv_eco_multi else "ECO",
                        "differenza_npv": abs(npv_ct_multi - npv_eco_multi)
                    }

                    st.session_state.progetti_multi_salvati.append(progetto_salvato)
                    st.success(f"✅ Progetto '{nome_progetto}' salvato! ({len(st.session_state.progetti_multi_salvati)}/5)")

                if salva_disabled and not nome_progetto:
                    st.caption("⚠️ Inserisci un nome progetto per salvare")
                elif salva_disabled:
                    st.caption("⚠️ Massimo 5 progetti salvati")

            with col_btn2:
                if st.button("🔄 Reset Progetto", use_container_width=True):
                    st.session_state.progetto_multi = {
                        "nome_progetto": "",
                        "tipo_soggetto": "privato",
                        "tipo_edificio": "residenziale",
                        "indirizzo": "",
                        "interventi": [],
                        "riduzione_ep_perc": None,
                        "data_conclusione": None
                    }
                    st.rerun()

        else:
            st.info("Aggiungi almeno 2 interventi per visualizzare il riepilogo del multi-intervento")

    # ===========================================================================
    # TAB 9: CONFRONTO SCENARI
    # ===========================================================================
    with tab_scenari:
        st.header("📊 Confronto Scenari Multipli")
        st.write("Confronta fino a 5 scenari per tipologia di intervento")

        # Selezione tipo intervento
        tipo_scenari = st.selectbox(
            "Tipo di intervento:",
            options=[
                "🌡️ Pompe di Calore",
                "☀️ Solare Termico",
                "🏠 Isolamento Termico",
                "🪟 Serramenti",
                "🏢 Building Automation",
                "🔀 Sistemi Ibridi"
            ],
            key="scenari_tipo_intervento"
        )

        if tipo_scenari == "🌡️ Pompe di Calore":
            if len(st.session_state.scenari) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'PdC' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari)}/5")

                # Grafico confronto
                fig = create_scenarios_comparison_chart(st.session_state.scenari)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari:
                    migliore = "CT" if s["npv_ct"] > s["npv_eco"] else "Eco"
                    df_data.append({
                        "Scenario": s["nome"],
                        "Tipologia": s["tipo_intervento_label"],
                        "Potenza": f"{s['potenza_kw']} kW",
                        "Spesa": format_currency(s["spesa"]),
                        "CT 3.0": format_currency(s.get("ct_incentivo", 0)),
                        "CT (NPV)": format_currency(s["npv_ct"]),
                        "Ecobonus": format_currency(s.get("eco_detrazione", 0)),
                        "Eco (NPV)": format_currency(s["npv_eco"]),
                        "Migliore": migliore
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Migliore assoluto
                miglior = max(st.session_state.scenari, key=lambda x: max(x["npv_ct"], x["npv_eco"]))
                miglior_incentivo = "CT" if miglior["npv_ct"] > miglior["npv_eco"] else "Ecobonus"
                miglior_npv = max(miglior["npv_ct"], miglior["npv_eco"])

                st.success(f"""
                **Miglior scenario:** {miglior["nome"]} con {miglior_incentivo}

                **NPV:** {format_currency(miglior_npv)}
                """)

                # Gestione scenari
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Cancella tutti gli scenari PdC", type="secondary", key="del_scenari_pdc"):
                        st.session_state.scenari = []
                        st.rerun()
                with col2:
                    if len(st.session_state.scenari) >= 5:
                        st.warning("Hai raggiunto il massimo di 5 scenari")

        elif tipo_scenari == "☀️ Solare Termico":
            if len(st.session_state.scenari_solare) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'Solare' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari_solare)}/5")

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari_solare:
                    df_data.append({
                        "Scenario": s["nome"],
                        "Tipologia": s.get("tipologia", s.get("tipologia_label", "N/D")),
                        "Superficie": f"{s.get('superficie', s.get('superficie_m2', 0)):.1f} m²",
                        "Spesa": format_currency(s.get("spesa_solare", s.get("spesa", 0))),
                        "CT 3.0": format_currency(s.get("ct_incentivo", 0)),
                        "CT (NPV)": format_currency(s.get("npv_ct_solare", s.get("ct_npv", 0))),
                        "Ecobonus": format_currency(s.get("eco_solare", s.get("eco_detrazione", 0))),
                        "Eco (NPV)": format_currency(s.get("npv_eco_solare", s.get("eco_npv", 0))),
                        "Migliore": s.get("piu_conveniente", "N/D")
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Migliore assoluto
                if len(st.session_state.scenari_solare) > 0:
                    miglior = max(st.session_state.scenari_solare, key=lambda x: max(x.get("ct_npv", 0), x.get("eco_npv", 0)))
                    miglior_npv = max(miglior.get("ct_npv", 0), miglior.get("eco_npv", 0))
                    st.success(f"**Miglior scenario:** {miglior['nome']} - NPV: {format_currency(miglior_npv)}")

                st.divider()
                if st.button("🗑️ Cancella tutti gli scenari Solare", type="secondary", key="del_scenari_solare"):
                    st.session_state.scenari_solare = []
                    st.rerun()

        elif tipo_scenari == "🏠 Isolamento Termico":
            if len(st.session_state.scenari_isolamento) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'Isolamento' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari_isolamento)}/5")

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari_isolamento:
                    df_data.append({
                        "Scenario": s["nome"],
                        "Superficie": f"{s['superficie_mq']:.1f} m²",
                        "Zona": s.get("zona_climatica", "N/D"),
                        "U post": f"{s.get('trasmittanza_post', 0):.3f} W/m²K",
                        "Spesa": format_currency(s.get("spesa_totale", 0)),
                        "CT 3.0": format_currency(s.get("ct_incentivo", 0)),
                        "CT (NPV)": format_currency(s.get("ct_npv", 0)),
                        "Ecobonus": format_currency(s.get("eco_detrazione", 0)),
                        "Eco (NPV)": format_currency(s.get("eco_npv", 0)),
                        "Migliore": s.get("migliore", "N/D")
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                if st.button("🗑️ Cancella tutti gli scenari Isolamento", type="secondary", key="del_scenari_iso"):
                    st.session_state.scenari_isolamento = []
                    st.rerun()

        elif tipo_scenari == "🪟 Serramenti":
            if len(st.session_state.scenari_serramenti) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'Serramenti' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari_serramenti)}/5")

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari_serramenti:
                    df_data.append({
                        "Scenario": s["nome"],
                        "Superficie": f"{s['superficie_mq']:.1f} m²",
                        "Zona": s.get("zona_climatica", "N/D"),
                        "U post": f"{s.get('trasmittanza_post', 0):.2f} W/m²K",
                        "Spesa": format_currency(s.get("spesa_totale", 0)),
                        "CT 3.0": format_currency(s.get("ct_incentivo", 0)),
                        "CT (NPV)": format_currency(s.get("ct_npv", 0)),
                        "Ecobonus": format_currency(s.get("eco_detrazione", 0)),
                        "Eco (NPV)": format_currency(s.get("eco_npv", 0)),
                        "Migliore": s.get("migliore", "N/D")
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                if st.button("🗑️ Cancella tutti gli scenari Serramenti", type="secondary", key="del_scenari_serr"):
                    st.session_state.scenari_serramenti = []
                    st.rerun()

        elif tipo_scenari == "🏢 Building Automation":
            if len(st.session_state.scenari_building_automation) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'B.A.' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari_building_automation)}/5")

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari_building_automation:
                    df_data.append({
                        "Scenario": s["nome"],
                        "Superficie": f"{s['superficie_mq']:.0f} m²",
                        "Classe": s.get("classe_efficienza", "N/D"),
                        "Spesa": format_currency(s.get("spesa", 0)),
                        "CT": format_currency(s.get("ct_incentivo", 0)),
                        "CT NPV": format_currency(s.get("ct_npv", 0)),
                        "Eco": format_currency(s.get("eco_detrazione", 0)),
                        "Eco NPV": format_currency(s.get("eco_npv", 0)),
                        "Migliore": s.get("migliore", "N/D")
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Migliore assoluto
                if len(st.session_state.scenari_building_automation) > 0:
                    miglior = max(st.session_state.scenari_building_automation, key=lambda x: max(x.get("ct_npv", 0), x.get("eco_npv", 0)))
                    miglior_npv = max(miglior.get("ct_npv", 0), miglior.get("eco_npv", 0))
                    st.success(f"**Miglior scenario:** {miglior['nome']} ({miglior.get('migliore', 'N/D')}) - NPV: {format_currency(miglior_npv)}")

                st.divider()
                if st.button("🗑️ Cancella tutti gli scenari B.A.", type="secondary", key="del_scenari_ba"):
                    st.session_state.scenari_building_automation = []
                    st.rerun()

        elif tipo_scenari == "🔀 Sistemi Ibridi":
            if len(st.session_state.scenari_ibridi) == 0:
                st.info("Nessuno scenario salvato. Vai alla tab 'Ibridi' e clicca 'Salva Scenario' per aggiungere scenari.")
            else:
                st.write(f"**Scenari salvati:** {len(st.session_state.scenari_ibridi)}/5")

                # Tabella confronto
                st.subheader("Tabella Comparativa")
                df_data = []
                for s in st.session_state.scenari_ibridi:
                    df_data.append({
                        "Scenario": s.get("nome", "N/D"),
                        "Tipo": s.get("tipo_sistema", "N/D"),
                        "Potenza PdC": f"{s.get('potenza_pdc_kw', s.get('potenza_nominale_kw', 0)):.1f} kW",
                        "Spesa": format_currency(s.get("spesa", s.get("spesa_totale", 0))),
                        "CT 3.0": format_currency(s.get("ct_incentivo", 0)),
                        "CT (NPV)": format_currency(s.get("ct_npv", 0)),
                        "Ecobonus": format_currency(s.get("eco_detrazione", 0)),
                        "Eco (NPV)": format_currency(s.get("eco_npv", 0)),
                        "Migliore": s.get("migliore", "N/D")
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                if st.button("🗑️ Cancella tutti gli scenari Ibridi", type="secondary", key="del_scenari_ibridi"):
                    st.session_state.scenari_ibridi = []
                    st.rerun()

    # ===========================================================================
    # TAB 3: STORICO CALCOLI
    # ===========================================================================
    with tab_storico:
        st.header("📜 Storico Calcoli")

        if len(st.session_state.storico_calcoli) == 0:
            st.info("Nessun calcolo effettuato in questa sessione")
        else:
            st.write(f"**Ultimi {len(st.session_state.storico_calcoli)} calcoli:**")

            for i, calcolo in enumerate(st.session_state.storico_calcoli):
                with st.expander(f"📌 {calcolo.get('timestamp', '')} - {calcolo['tipo_intervento_label']} {calcolo['potenza_kw']} kW"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("**Dati tecnici:**")
                        st.write(f"• Tipologia: {calcolo['tipo_intervento_label']}")
                        st.write(f"• Potenza: {calcolo['potenza_kw']} kW")
                        st.write(f"• SCOP: {calcolo['scop']}")
                        st.write(f"• η_s: {calcolo['eta_s']}%")
                    with col2:
                        st.write("**Risultati:**")
                        st.write(f"• CT: {format_currency(calcolo['ct_incentivo'])}")
                        st.write(f"• Ecobonus: {format_currency(calcolo['eco_detrazione'])}")
                    with col3:
                        st.write("**NPV:**")
                        st.write(f"• CT: {format_currency(calcolo['npv_ct'])}")
                        st.write(f"• Eco: {format_currency(calcolo['npv_eco'])}")

            if st.button("🗑️ Cancella storico"):
                st.session_state.storico_calcoli = []
                st.rerun()

    # ===========================================================================
    # TAB PROGETTI CLIENTI - Gestione progetti salvati
    # ===========================================================================
    with tab_progetti:
        st.header("📁 Gestione Progetti Clienti")

        st.info("""
        **Sistema Gestione Progetti** ti permette di:
        - 💾 **Salvare** analisi di fattibilità per singoli clienti
        - 🔍 **Cercare** e **recuperare** progetti facilmente
        - ✏️ **Modificare** progetti esistenti
        - 📋 **Duplicare** progetti per scenari alternativi
        - 📊 **Esportare** riepilogo completo cliente
        """)

        gestore = get_gestore_progetti()

        # ===== RICERCA PROGETTI =====
        st.divider()
        st.subheader("🔍 Ricerca Progetti")

        col1, col2 = st.columns([3, 1])

        with col1:
            query_ricerca = st.text_input(
                "Cerca per nome cliente, intervento o note",
                placeholder="es. Mario Rossi, Pompe, Milano...",
                key="query_ricerca_progetti"
            )

        with col2:
            campo_ricerca = st.selectbox(
                "Campo",
                options=["tutti", "cliente", "intervento", "note"],
                index=0,
                key="campo_ricerca_progetti"
            )

        # Esegui ricerca
        if query_ricerca:
            progetti_trovati = gestore.cerca_progetti(query_ricerca, campo_ricerca)
        else:
            progetti_trovati = gestore.lista_progetti()

        # ===== RISULTATI =====
        st.divider()

        if progetti_trovati:
            st.success(f"✅ Trovati **{len(progetti_trovati)}** progetti")

            for idx, progetto in enumerate(progetti_trovati):
                with st.expander(
                    f"📄 **{progetto['nome_cliente']}** - {progetto['tipo_intervento']} "
                    f"({progetto['data_creazione'][:10]})",
                    expanded=(idx == 0)  # Primo espanso
                ):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**Cliente**: {progetto['nome_cliente']}")
                        st.write(f"**Intervento**: {progetto['tipo_intervento']}")
                        st.metric("Incentivo", f"{progetto['incentivo_totale']:,.2f} €")

                    with col2:
                        st.write(f"**Creato**: {progetto['data_creazione'][:16].replace('T', ' ')}")
                        st.write(f"**Modificato**: {progetto['data_ultima_modifica'][:16].replace('T', ' ')}")
                        if progetto['note']:
                            st.caption(f"📝 {progetto['note'][:100]}...")

                    with col3:
                        # Bottoni azione
                        if st.button("🔄 Carica", key=f"load_prog_{idx}", use_container_width=True):
                            # Carica progetto
                            filepath = Path(progetto['filepath'])
                            successo, dati, msg = gestore.carica_progetto(filepath)

                            if successo:
                                st.success("✅ Progetto caricato!")

                                # Ripopola session state
                                st.session_state.nome_cliente_corrente = dati['nome_cliente']
                                st.session_state.note_progetto = dati.get('note', '')

                                # Mostra info caricamento
                                st.info(f"📋 Caricato: **{dati['nome_cliente']}**\n\nRicorda di andare al TAB **{dati['tipo_intervento']}** per vedere i dati caricati.")

                            else:
                                st.error(f"❌ {msg}")

                        if st.button("📋 Duplica", key=f"dup_prog_{idx}", use_container_width=True):
                            filepath = Path(progetto['filepath'])
                            successo, msg, _ = gestore.duplica_progetto(filepath)
                            if successo:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")

                        if st.button("🗑️", key=f"del_prog_{idx}", use_container_width=True, help="Elimina progetto"):
                            filepath = Path(progetto['filepath'])

                            # Conferma eliminazione
                            if st.session_state.get(f"confirm_delete_{idx}"):
                                successo, msg = gestore.elimina_progetto(filepath)
                                if successo:
                                    st.success(f"✅ {msg}")
                                    st.session_state[f"confirm_delete_{idx}"] = False
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                            else:
                                st.session_state[f"confirm_delete_{idx}"] = True
                                st.warning("⚠️ Click di nuovo per confermare eliminazione")

        else:
            st.info("🔍 Nessun progetto trovato. Calcola un incentivo e salvalo usando il campo 'Nome Cliente' in sidebar!")

        # ===== RIEPILOGO CLIENTE =====
        st.divider()
        st.subheader("📊 Riepilogo Cliente")

        col1, col2 = st.columns([3, 1])

        with col1:
            cliente_riepilogo = st.text_input(
                "Nome cliente per riepilogo completo",
                placeholder="es. Mario Rossi",
                key="cliente_riepilogo"
            )

        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            genera_riepilogo = st.button("📊 Genera Riepilogo", key="btn_riepilogo", use_container_width=True)

        if genera_riepilogo and cliente_riepilogo:
            riepilogo = gestore.esporta_riepilogo_cliente(cliente_riepilogo)

            if riepilogo['numero_progetti'] > 0:
                st.success(f"✅ **{riepilogo['nome_cliente']}**: {riepilogo['numero_progetti']} progetti trovati")

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("💰 Incentivo Totale", f"{riepilogo['incentivo_totale']:,.2f} €")
                    st.metric("📋 Numero Progetti", riepilogo['numero_progetti'])

                with col2:
                    st.write("**Interventi per tipo:**")
                    for tipo, dati in riepilogo['interventi_per_tipo'].items():
                        st.write(f"- **{tipo}**: {dati['count']} progetti ({dati['incentivo_totale']:,.2f} €)")

                # Tabella progetti
                st.write("**Dettaglio progetti:**")
                df_riepilogo = pd.DataFrame(riepilogo['progetti'])
                df_riepilogo_display = df_riepilogo[[
                    'nome_file', 'tipo_intervento', 'incentivo_totale', 'data_creazione'
                ]].copy()
                df_riepilogo_display.columns = ['File', 'Intervento', 'Incentivo (€)', 'Data Creazione']
                st.dataframe(df_riepilogo_display, use_container_width=True, hide_index=True)

                # Esporta CSV
                csv = df_riepilogo.to_csv(index=False)
                st.download_button(
                    "📥 Esporta Riepilogo CSV",
                    data=csv,
                    file_name=f"riepilogo_{cliente_riepilogo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning(f"⚠️ Nessun progetto trovato per '{cliente_riepilogo}'")

    # ===========================================================================
    # TAB PRENOTAZIONE - CT 3.0
    # ===========================================================================
    with tab_prenotazione:
        st.header("🗓️ Modalità Prenotazione - Conto Termico 3.0")

        st.info("""
        **Modalità Prenotazione** consente a PA, ETS non economici e ESCO (per loro conto) di:
        - ✅ Ottenere certezza incentivo **PRIMA** di iniziare i lavori
        - 💰 Ricevere **acconti** durante l'esecuzione
        - 📅 Rate intermedie al 50% avanzamento lavori
        - 🎯 Massimale preventivo vincolante
        """)

        # Verifica ammissibilità
        st.subheader("1️⃣ Verifica Ammissibilità")

        ammissibile_pren, motivo_pren = is_prenotazione_ammissibile(
            tipo_soggetto=st.session_state.get("tipo_soggetto_principale", "privato"),
            conto_terzi=False
        )

        if not ammissibile_pren:
            st.error(f"❌ {motivo_pren}")
            st.info("💡 La prenotazione è riservata a PA, ETS non economici e ESCO per loro conto.")
        else:
            st.success(f"✅ {motivo_pren}")

            st.divider()

            # Verifica se c'è un incentivo calcolato
            if st.session_state.ultimo_incentivo > 0:
                st.success(f"""
                **Ultimo incentivo calcolato**: {format_currency(st.session_state.ultimo_incentivo)}
                **Durata erogazione**: {st.session_state.ultimo_numero_anni} {'anno' if st.session_state.ultimo_numero_anni == 1 else 'anni'}
                """)
                incentivo_pren = st.session_state.ultimo_incentivo
                anni_pren = st.session_state.ultimo_numero_anni
            else:
                st.warning("⚠️ Nessun incentivo calcolato. Inserisci manualmente i dati o calcola prima un intervento.")
                col_inc1, col_inc2 = st.columns(2)
                with col_inc1:
                    incentivo_pren = st.number_input(
                        "Incentivo totale (€)",
                        min_value=0.0,
                        max_value=500000.0,
                        value=50000.0,
                        step=1000.0,
                        key="pren_incentivo_manuale"
                    )
                with col_inc2:
                    anni_pren = st.selectbox(
                        "Anni erogazione",
                        options=[2, 5],
                        index=1,
                        key="pren_anni_manuale"
                    )

            # Casistica prenotazione
            st.subheader("2️⃣ Casistica Prenotazione")

            st.caption("Seleziona la casistica applicabile (Art. 7, comma 1):")

            col_cas1, col_cas2 = st.columns(2)

            with col_cas1:
                ha_diagnosi_pren = st.checkbox(
                    "a) Diagnosi energetica",
                    value=True,
                    key="pren_diagnosi",
                    help="Diagnosi energetica ex art. 8 D.lgs. 102/2014"
                )
                ha_epc_pren = st.checkbox(
                    "b) Contratto EPC",
                    value=False,
                    key="pren_epc",
                    help="Energy Performance Contract stipulato"
                )

            with col_cas2:
                e_ppp_pren = st.checkbox(
                    "c) Partenariato Pubblico Privato",
                    value=False,
                    key="pren_ppp",
                    help="Intervento in PPP"
                )
                lavori_assegnati_pren = st.checkbox(
                    "d) Lavori già assegnati",
                    value=False,
                    key="pren_assegnati",
                    help="Assegnazione lavori già avvenuta"
                )

            # Opzioni erogazione
            st.subheader("3️⃣ Opzioni Erogazione")

            col_opt1, col_opt2 = st.columns(2)

            with col_opt1:
                include_acconto_pren = st.checkbox(
                    "📤 Richiedi acconto all'ammissione",
                    value=True,
                    key="pren_acconto",
                    help=f"Acconto: 50% se 2 anni, 40% se 5 anni"
                )

                if include_acconto_pren:
                    perc_acconto = 0.50 if anni_pren == 2 else 0.40
                    importo_acconto_stim = incentivo_pren * perc_acconto
                    st.caption(f"💰 Acconto stimato: {format_currency(importo_acconto_stim)} ({perc_acconto*100:.0f}%)")

            with col_opt2:
                include_rata_int_pren = st.checkbox(
                    "📊 Richiedi rata intermedia",
                    value=False,
                    key="pren_rata_int",
                    help="Rata intermedia al 50% avanzamento lavori"
                )

                if include_rata_int_pren:
                    st.caption("📅 Erogata al raggiungimento 50% avanzamento lavori")

            # Timeline
            st.subheader("4️⃣ Timeline Indicativa")

            data_oggi = datetime.now()

            col_time1, col_time2 = st.columns(2)
            with col_time1:
                data_presentazione_pren = st.date_input(
                    "Data presentazione istanza",
                    value=data_oggi,
                    key="pren_data_pres"
                )
            with col_time2:
                gg_istruttoria_pren = st.number_input(
                    "Giorni stimati istruttoria GSE",
                    min_value=30,
                    max_value=180,
                    value=90,
                    step=10,
                    key="pren_gg_istr",
                    help="Tempo stimato per ammissione (default: 90 gg)"
                )

            st.divider()

            # Pulsante simulazione
            if st.button("🔍 SIMULA PRENOTAZIONE", type="primary", use_container_width=True, key="btn_simula_pren"):

                # Converti data
                data_pres_dt = datetime.combine(data_presentazione_pren, datetime.min.time())

                # Simula prenotazione
                risultato_pren = simula_prenotazione(
                    tipo_soggetto=st.session_state.get("tipo_soggetto_principale", "privato"),
                    incentivo_totale=incentivo_pren,
                    numero_anni=anni_pren,
                    ha_diagnosi_energetica=ha_diagnosi_pren,
                    ha_epc=ha_epc_pren,
                    e_ppp=e_ppp_pren,
                    lavori_assegnati=lavori_assegnati_pren,
                    include_acconto=include_acconto_pren,
                    include_rata_intermedia=include_rata_int_pren,
                    data_presentazione=data_pres_dt
                )

                if not risultato_pren["ammissibile"]:
                    st.error(f"❌ {risultato_pren['motivo_esclusione']}")
                else:
                    st.success("✅ Simulazione completata con successo!")

                    # RATEIZZAZIONE
                    st.subheader("💰 Rateizzazione Incentivo")

                    rateizz = risultato_pren["rateizzazione"]

                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.metric("Incentivo Totale", format_currency(rateizz["incentivo_totale"]))
                    with col_r2:
                        if rateizz["disponibile_rata_intermedia"]:
                            st.metric("Rata Intermedia", format_currency(rateizz["importo_rata_intermedia"]))
                        else:
                            st.metric("Acconto", format_currency(rateizz["importo_acconto"]))
                    with col_r3:
                        st.metric("Saldo", format_currency(rateizz["importo_saldo"]))

                    # Tabella dettaglio rate
                    st.markdown("**Dettaglio Rate:**")


                    df_rate = pd.DataFrame(rateizz["rate_dettaglio"])

                    # Formatta per visualizzazione
                    df_display = df_rate.copy()
                    df_display["importo"] = df_display["importo"].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_display["percentuale"] = df_display["percentuale"].apply(lambda x: f"{x:.1f}%")
                    df_display.columns = ["Tipo Rata", "Momento Erogazione", "Importo", "% Incentivo", "Anno"]

                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                    st.divider()

                    # TIMELINE
                    st.subheader("📅 Timeline Prenotazione")

                    calendario = risultato_pren["calendario"]

                    timeline_data = {
                        "Fase": [
                            "📝 Presentazione istanza",
                            "✅ Ammissione prevista",
                            "🚧 Limite avvio lavori",
                            "🏁 Limite conclusione"
                        ],
                        "Data": [
                            calendario["data_presentazione"],
                            calendario["data_prevista_ammissione"],
                            calendario["data_limite_avvio_lavori"],
                            calendario["data_limite_conclusione_lavori"]
                        ],
                        "Note": [
                            "Invio istanza a GSE",
                            f"Dopo {gg_istruttoria_pren} gg istruttoria",
                            f"Entro {calendario['gg_avvio_lavori']} gg da ammissione",
                            f"Entro {calendario['gg_conclusione_lavori']} gg ({calendario['gg_conclusione_lavori']//30} mesi)"
                        ]
                    }

                    df_timeline = pd.DataFrame(timeline_data)
                    st.table(df_timeline)

                    st.divider()

                    # FASI PROCESSO
                    st.subheader("📋 Fasi del Processo")

                    fasi = risultato_pren["fasi"]

                    for fase in fasi:
                        with st.expander(f"**Fase {fase['numero']}: {fase['nome']}**", expanded=(fase['numero'] <= 2)):
                            st.write(fase["descrizione"])

                            if fase["documenti_richiesti"]:
                                st.markdown("**📄 Documenti richiesti:**")
                                for doc in fase["documenti_richiesti"]:
                                    st.write(f"- {doc}")

                            if fase["tempistica_gg"] > 0:
                                st.caption(f"⏱️ Tempistica: {fase['tempistica_gg']} giorni")

                    st.divider()

                    # MASSIMALE
                    st.info(f"""
                    **Massimale preventivo vincolante**: {format_currency(risultato_pren['massimale_preventivo'])}

                    Questo è l'importo massimo erogabile, calcolato in fase di ammissione e vincolante per tutta la durata dell'intervento.
                    """)

    # ===========================================================================
    # TAB 4: GENERA REPORT
    # ===========================================================================
    with tab_report:
        st.header("📄 Genera Relazione Tecnica")

        # Selezione tipo report
        tipo_report = st.selectbox(
            "Tipo di intervento:",
            options=[
                "🌡️ Pompe di Calore",
                "☀️ Solare Termico",
                "🚿 Scaldacqua PdC",
                "🔀 Sistemi Ibridi",
                "🏠 Isolamento Termico",
                "🪟 Serramenti",
                "🏢 Building Automation",
                "🔗 Multi-Intervento"
            ],
            key="report_tipo_intervento"
        )

        if tipo_report == "🌡️ Pompe di Calore":
            # Report PdC (esistente)
            if len(st.session_state.scenari) == 0:
                st.info("Salva almeno uno scenario PdC per generare la relazione tecnica")
            else:
                st.write(f"**Scenari PdC da includere:** {len(st.session_state.scenari)}")

                # Mostra scenari salvati con possibilità di rimuovere
                for i, s in enumerate(st.session_state.scenari):
                    fv_info = ""
                    if s.get("fv_combinato") and s.get("fv_potenza_kw", 0) > 0:
                        fv_info = f" + FV {s['fv_potenza_kw']:.1f} kWp"
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        st.write(f"• **{s['nome']}**: {s['tipo_intervento_label']} {s['potenza_kw']} kW{fv_info}")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_pdc_{i}"):
                            st.session_state.scenari.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto")
                    tipo_abitazione_report = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione")
                with col2:
                    anno_report = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno")
                    tasso_report = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso") / 100

                st.divider()

                if st.button("📄 Genera Report PdC", type="primary", use_container_width=True):
                    # Converti scenari in ScenarioCalcolo
                    scenari_obj = []
                    for s in st.session_state.scenari:
                        # Verifica se ha FV abbinato
                        fv_abbinato = s.get("fv_combinato", False) and s.get("fv_potenza_kw", 0) > 0

                        sc = ScenarioCalcolo(
                            nome=s["nome"],
                            tipo_intervento=s["tipo_intervento"],
                            tipo_intervento_label=s["tipo_intervento_label"],
                            potenza_kw=s["potenza_kw"],
                            scop=s["scop"],
                            eta_s=s["eta_s"],
                            eta_s_min=s["eta_s_min"],
                            zona_climatica=s["zona_climatica"],
                            gwp=s["gwp"],
                            bassa_temperatura=s["bassa_temp"],
                            spesa=s["spesa"],
                            ct_ammissibile=s["ct_ammissibile"],
                            ct_incentivo=s["ct_incentivo"],
                            ct_rate=s["ct_rate"],
                            ct_annualita=s["ct_annualita"],
                            ct_kp=s["ct_kp"],
                            ct_ei=s["ct_ei"],
                            ct_ci=s["ct_ci"],
                            ct_quf=s["ct_quf"],
                            eco_ammissibile=s["eco_ammissibile"],
                            eco_detrazione=s["eco_detrazione"],
                            eco_aliquota=s["eco_aliquota"],
                            npv_ct=s["npv_ct"],
                            npv_eco=s["npv_eco"],
                            # Dati FV se abbinato
                            fv_abbinato=fv_abbinato,
                            fv_potenza_kw=s.get("fv_potenza_kw", 0.0),
                            fv_spesa=s.get("fv_spesa", 0.0),
                            fv_capacita_accumulo_kwh=s.get("fv_capacita_accumulo_kwh", 0.0),
                            fv_spesa_accumulo=s.get("fv_spesa_accumulo", 0.0),
                            fv_produzione_stimata_kwh=s.get("fv_produzione_stimata_kwh", 0.0),
                            fv_incentivo_ct=s.get("fv_incentivo_ct", 0.0),
                            fv_bonus_ristrutt=s.get("fv_bonus_ristrutt", 0.0),
                            fv_registro_tecnologie=s.get("fv_registro_tecnologie", ""),
                            fv_npv_ct=s.get("fv_npv_ct", 0.0),
                            fv_npv_bonus=s.get("fv_npv_bonus", 0.0),
                        )
                        scenari_obj.append(sc)

                    # Genera HTML
                    html_content = genera_report_html(
                        scenari=scenari_obj,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report],
                        anno=anno_report,
                        tasso_sconto=tasso_report,
                        solo_ct=solo_conto_termico
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content, f"relazione_tecnica_pdc_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content, height=800, scrolling=True)

                    st.success("✅ Report generato! Clicca sul link sopra per scaricare.")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

        elif tipo_report == "☀️ Solare Termico":
            if len(st.session_state.scenari_solare) == 0:
                st.info("Salva almeno uno scenario Solare Termico per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Solare da includere:** {len(st.session_state.scenari_solare)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_solare):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        st.write(f"• **{s['nome']}**: {s['tipologia']} - {s['superficie']:.1f} m²")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_sol_{i}"):
                            st.session_state.scenari_solare.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report solare
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_sol = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_sol")
                    tipo_abitazione_report_sol = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_sol")
                with col2:
                    anno_report_sol = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_sol")
                    tasso_report_sol = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_sol") / 100

                st.divider()

                if st.button("📄 Genera Report Solare Termico", type="primary", use_container_width=True):
                    # Converti scenari in ScenarioSolareTermico
                    scenari_sol_obj = []
                    for s in st.session_state.scenari_solare:
                        # Mappa le chiavi del dizionario salvato ai campi del dataclass
                        sc = ScenarioSolareTermico(
                            nome=s["nome"],
                            tipologia_impianto=s.get("tipologia", "acs_solo"),
                            tipologia_label=s.get("tipologia", "ACS"),
                            tipo_collettore=s.get("tipo_collettore", "piano"),
                            tipo_collettore_label=s.get("tipo_collettore", "Piano"),
                            superficie_m2=s.get("superficie", 0),
                            n_moduli=s.get("n_moduli", 1),
                            area_modulo_m2=s.get("area_modulo", 2.0),
                            producibilita_qu=s.get("qu_calcolato", 0) / max(s.get("superficie", 1), 1),  # kWht/m²
                            spesa=s.get("spesa", 0),
                            ct_ammissibile=s.get("ct_incentivo", 0) > 0,
                            ct_incentivo=s.get("ct_incentivo", 0),
                            ct_rate=[s.get("ct_incentivo", 0) / max(s.get("ct_rate", 1), 1)] * s.get("ct_rate", 2) if s.get("ct_rate", 1) > 0 else [0],
                            ct_annualita=s.get("ct_rate", 2),
                            ct_ci=0.15,  # Valore standard per solare termico
                            ct_ia=s.get("ct_incentivo", 0) / max(s.get("ct_rate", 1), 1),
                            eco_ammissibile=s.get("eco_detrazione", 0) > 0,
                            eco_detrazione=s.get("eco_detrazione", 0),
                            eco_aliquota=s.get("aliquota_eco", 0.5),
                            npv_ct=s.get("npv_ct", 0),
                            npv_eco=s.get("npv_eco", 0),
                        )
                        scenari_sol_obj.append(sc)

                    # Genera HTML Solare
                    html_content = genera_report_solare_termico_html(
                        scenari=scenari_sol_obj,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report_sol],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report_sol],
                        anno=anno_report_sol,
                        tasso_sconto=tasso_report_sol
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content, f"relazione_tecnica_solare_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content, height=800, scrolling=True)

                    st.success("✅ Report Solare Termico generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

        elif tipo_report == "🚿 Scaldacqua PdC":
            if len(st.session_state.scenari_scaldacqua) == 0:
                st.info("Salva almeno uno scenario Scaldacqua per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Scaldacqua da includere:** {len(st.session_state.scenari_scaldacqua)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_scaldacqua):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        iter_info = " (Iter Semplificato)" if s.get('iter_semplificato') else ""
                        st.write(f"• **{s['nome']}**: Classe {s['classe_energetica']} - {s['capacita_litri']} litri{iter_info}")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_sc_{i}"):
                            st.session_state.scenari_scaldacqua.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_sc = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_sc")
                    tipo_abitazione_report_sc = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_sc")
                with col2:
                    anno_report_sc = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_sc")
                    tasso_report_sc = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_sc") / 100

                st.divider()

                if st.button("📄 Genera Report Scaldacqua", type="primary", use_container_width=True):
                    from modules.report_generator import ScenarioScaldacqua, genera_report_scaldacqua_html

                    # Converti scenari in ScenarioScaldacqua
                    scenari_sc_obj = []
                    for s in st.session_state.scenari_scaldacqua:
                        prodotto_cat = s.get('prodotto_catalogo', {}) or {}
                        sc = ScenarioScaldacqua(
                            nome=s['nome'],
                            classe_energetica=s['classe_energetica'],
                            capacita_litri=s['capacita_litri'],
                            potenza_kw=s['potenza_kw'],
                            spesa_lavori=s['spesa_lavori'],
                            spesa_tecnici=s['spesa_tecnici'],
                            tipo_soggetto=s['tipo_soggetto'],
                            abitazione_principale=s['abitazione_principale'],
                            iter_semplificato=s.get('iter_semplificato', False),
                            prodotto_marca=prodotto_cat.get('marca', ''),
                            prodotto_modello=prodotto_cat.get('modello', ''),
                            ct_incentivo=s['ct_incentivo'],
                            ct_npv=s['ct_npv'],
                            ct_anni_erogazione=s['ct_anni_erogazione'],
                            eco_detrazione=s['eco_detrazione'],
                            eco_npv=s['eco_npv'],
                            eco_anni_recupero=s['eco_anni_recupero'],
                            piu_conveniente=s['piu_conveniente'],
                            differenza_npv=s['differenza_npv']
                        )
                        scenari_sc_obj.append(sc)

                    # Genera HTML
                    html_content = genera_report_scaldacqua_html(
                        scenari=scenari_sc_obj,
                        tipo_soggetto=tipo_soggetto_report_sc,
                        tipo_abitazione=tipo_abitazione_report_sc,
                        anno=anno_report_sc,
                        tasso_sconto=tasso_report_sc
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content, f"relazione_tecnica_scaldacqua_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content, height=800, scrolling=True)

                    st.success("✅ Report Scaldacqua generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

        elif tipo_report == "🔀 Sistemi Ibridi":
            if len(st.session_state.scenari_ibridi) == 0:
                st.info("Salva almeno uno scenario Sistemi Ibridi per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Ibridi da includere:** {len(st.session_state.scenari_ibridi)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_ibridi):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        iter_info = " (Iter Semplificato)" if s.get('iter_semplificato') else ""
                        st.write(f"• **{s['nome']}**: PdC {s['potenza_pdc_kw']} kW + Caldaia {s['potenza_caldaia_kw']} kW{iter_info}")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_ibr_{i}"):
                            st.session_state.scenari_ibridi.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report Ibridi
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_ibr = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_ibr")
                    tipo_abitazione_report_ibr = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_ibr")
                with col2:
                    anno_report_ibr = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_ibr")
                    tasso_report_ibr = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_ibr") / 100

                st.divider()

                if st.button("📄 Genera Report Sistemi Ibridi", type="primary", use_container_width=True):
                    from modules.report_generator import genera_report_ibridi_html

                    # Genera HTML
                    html_content_ibr = genera_report_ibridi_html(
                        scenari=st.session_state.scenari_ibridi,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report_ibr],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report_ibr],
                        anno=anno_report_ibr,
                        tasso_sconto=tasso_report_ibr,
                        solo_ct=solo_conto_termico
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content_ibr, f"relazione_tecnica_ibridi_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content_ibr, height=800, scrolling=True)

                    st.success("✅ Report Sistemi Ibridi generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

                # Tabella comparativa scenari
                if len(st.session_state.scenari_ibridi) > 1:
                    st.subheader("📊 Confronto Scenari")
                    df_data = []
                    for s in st.session_state.scenari_ibridi:
                        df_data.append({
                            "Scenario": s['nome'],
                            "Tipo": s['tipo_sistema'],
                            "PdC (kW)": s['potenza_pdc_kw'],
                            "Caldaia (kW)": s['potenza_caldaia_kw'],
                            "Spesa (€)": f"€ {s['spesa']:,.0f}",
                            "CT NPV": f"€ {s['ct_npv']:,.0f}",
                            "Migliore": s['migliore']
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True)

        elif tipo_report == "🏠 Isolamento Termico":
            if len(st.session_state.scenari_isolamento) == 0:
                st.info("Salva almeno uno scenario Isolamento Termico per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Isolamento da includere:** {len(st.session_state.scenari_isolamento)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_isolamento):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        st.write(f"• **{s['nome']}**: {s['tipo_superficie']} - {s['superficie_mq']} m² - Zona {s['zona_climatica']}")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_iso_{i}"):
                            st.session_state.scenari_isolamento.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report Isolamento
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_iso = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_iso")
                    tipo_abitazione_report_iso = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_iso")
                with col2:
                    anno_report_iso = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_iso")
                    tasso_report_iso = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_iso") / 100

                st.divider()

                if st.button("📄 Genera Report Isolamento Termico", type="primary", use_container_width=True):
                    from modules.report_generator import genera_report_isolamento_html

                    # Genera HTML
                    html_content_iso = genera_report_isolamento_html(
                        scenari=st.session_state.scenari_isolamento,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report_iso],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report_iso],
                        anno=anno_report_iso,
                        tasso_sconto=tasso_report_iso,
                        solo_ct=solo_conto_termico
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content_iso, f"relazione_tecnica_isolamento_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content_iso, height=800, scrolling=True)

                    st.success("✅ Report Isolamento Termico generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

                # Tabella comparativa scenari
                if len(st.session_state.scenari_isolamento) > 1:
                    st.subheader("📊 Confronto Scenari")
                    df_data = []
                    for s in st.session_state.scenari_isolamento:
                        df_data.append({
                            "Scenario": s['nome'],
                            "Superficie": s['tipo_superficie'],
                            "m²": s['superficie_mq'],
                            "Zona": s['zona_climatica'],
                            "Spesa (€)": f"€ {s['spesa_totale']:,.0f}",
                            "Migliore": s['migliore']
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True)

        elif tipo_report == "🪟 Serramenti":
            if len(st.session_state.scenari_serramenti) == 0:
                st.info("Salva almeno uno scenario Serramenti per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Serramenti da includere:** {len(st.session_state.scenari_serramenti)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_serramenti):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        st.write(f"• **{s['nome']}**: {s['superficie_mq']} m² - Zona {s['zona_climatica']} - U={s['trasmittanza_post']} W/m²K")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_serr_{i}"):
                            st.session_state.scenari_serramenti.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report Serramenti
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_serr = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_serr")
                    tipo_abitazione_report_serr = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_serr")
                with col2:
                    anno_report_serr = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_serr")
                    tasso_report_serr = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_serr") / 100

                st.divider()

                if st.button("📄 Genera Report Serramenti", type="primary", use_container_width=True):
                    from modules.report_generator import genera_report_serramenti_html

                    # Genera HTML
                    html_content_serr = genera_report_serramenti_html(
                        scenari=st.session_state.scenari_serramenti,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report_serr],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report_serr],
                        anno=anno_report_serr,
                        tasso_sconto=tasso_report_serr,
                        solo_ct=solo_conto_termico
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content_serr, f"relazione_tecnica_serramenti_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content_serr, height=800, scrolling=True)

                    st.success("✅ Report Serramenti generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

                # Tabella comparativa scenari
                if len(st.session_state.scenari_serramenti) > 1:
                    st.subheader("📊 Confronto Scenari")
                    df_data = []
                    for s in st.session_state.scenari_serramenti:
                        df_data.append({
                            "Scenario": s['nome'],
                            "m²": s['superficie_mq'],
                            "Zona": s['zona_climatica'],
                            "U (W/m²K)": s['trasmittanza_post'],
                            "Spesa (€)": f"€ {s['spesa_totale']:,.0f}",
                            "Migliore": s['migliore']
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True)

        elif tipo_report == "🏢 Building Automation":
            if len(st.session_state.scenari_building_automation) == 0:
                st.info("Salva almeno uno scenario Building Automation per generare la relazione tecnica")
            else:
                st.write(f"**Scenari Building Automation da includere:** {len(st.session_state.scenari_building_automation)}")

                # Mostra scenari salvati
                for i, s in enumerate(st.session_state.scenari_building_automation):
                    col_sc1, col_sc2 = st.columns([5, 1])
                    with col_sc1:
                        st.write(f"• **{s['nome']}**: {s['superficie_mq']} m² - Classe {s['classe_efficienza']}")
                    with col_sc2:
                        if st.button("🗑️", key=f"del_ba_{i}"):
                            st.session_state.scenari_building_automation.pop(i)
                            st.rerun()

                st.divider()

                # Parametri report BA
                col1, col2 = st.columns(2)
                with col1:
                    tipo_soggetto_report_ba = st.selectbox("Tipo soggetto", list(TIPI_SOGGETTO.keys()), key="report_soggetto_ba")
                    tipo_abitazione_report_ba = st.selectbox("Tipo abitazione", list(TIPI_ABITAZIONE.keys()), key="report_abitazione_ba")
                with col2:
                    anno_report_ba = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_ba")
                    tasso_report_ba = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_ba") / 100

                st.divider()

                if st.button("📄 Genera Report Building Automation", type="primary", use_container_width=True):
                    # Genera HTML
                    html_content_ba = genera_report_building_automation_html(
                        scenari=st.session_state.scenari_building_automation,
                        tipo_soggetto=TIPI_SOGGETTO[tipo_soggetto_report_ba],
                        tipo_abitazione=TIPI_ABITAZIONE[tipo_abitazione_report_ba],
                        anno=anno_report_ba,
                        tasso_sconto=tasso_report_ba,
                        solo_ct=solo_conto_termico
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content_ba, f"relazione_tecnica_ba_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content_ba, height=800, scrolling=True)

                    st.success("✅ Report generato! Clicca sul link sopra per scaricare.")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

                # Tabella comparativa scenari
                if len(st.session_state.scenari_building_automation) > 1:
                    st.subheader("📊 Confronto Scenari")
                    df_data = []
                    for s in st.session_state.scenari_building_automation:
                        df_data.append({
                            "Scenario": s['nome'],
                            "m²": s['superficie_mq'],
                            "Classe": s['classe_efficienza'],
                            "Spesa (€)": f"€ {s['spesa']:,.0f}",
                            "CT NPV": f"€ {s['ct_npv']:,.0f}",
                            "Migliore": s['migliore']
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True)

        elif tipo_report == "🔗 Multi-Intervento":
            if len(st.session_state.progetti_multi_salvati) == 0:
                st.info("Nessun progetto Multi-Intervento salvato. Vai al tab 'Multi-Intervento', configura un progetto e salvalo per generare il report.")
            else:
                st.write(f"**Progetti Multi-Intervento salvati:** {len(st.session_state.progetti_multi_salvati)}")

                # Selezione progetto
                progetti_nomi = [p["nome_progetto"] for p in st.session_state.progetti_multi_salvati]
                progetto_selezionato_idx = st.selectbox(
                    "Seleziona progetto da includere nel report",
                    options=list(range(len(progetti_nomi))),
                    format_func=lambda x: progetti_nomi[x],
                    key="select_progetto_multi_report"
                )

                progetto_sel = st.session_state.progetti_multi_salvati[progetto_selezionato_idx]

                # Mostra anteprima progetto
                with st.expander("📋 Anteprima Progetto", expanded=True):
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.write(f"**Nome:** {progetto_sel['nome_progetto']}")
                        st.write(f"**Indirizzo:** {progetto_sel['indirizzo']}")
                        st.write(f"**Tipo soggetto:** {progetto_sel['tipo_soggetto'].upper()}")
                    with col_p2:
                        st.write(f"**Tipo edificio:** {progetto_sel['tipo_edificio'].capitalize()}")
                        st.write(f"**N° interventi:** {len(progetto_sel['interventi'])}")
                        st.write(f"**Spesa totale:** {progetto_sel['spesa_totale']:,.0f} €")

                    st.write("**Interventi inclusi:**")
                    for idx, intervento in enumerate(progetto_sel['interventi'], 1):
                        st.caption(f"{idx}. {intervento['tipo_label']}: {intervento['nome']} - {intervento['spesa_totale']:,.0f} €")

                st.divider()

                # Parametri report
                col1, col2 = st.columns(2)
                with col1:
                    anno_report_multi = st.number_input("Anno", min_value=2024, max_value=2030, value=2025, key="report_anno_multi")
                with col2:
                    tasso_report_multi = st.slider("Tasso sconto (%)", 0.0, 10.0, 3.0, key="report_tasso_multi") / 100

                st.divider()

                if st.button("📄 Genera Report Multi-Intervento", type="primary", use_container_width=True):
                    from modules.report_generator import ScenarioMultiIntervento, InterventoMulti, genera_report_multi_intervento_html

                    # Converti progetto in ScenarioMultiIntervento
                    interventi_obj = [
                        InterventoMulti(
                            tipo=i['tipo'],
                            tipo_label=i['tipo_label'],
                            nome=i['nome'],
                            spesa_totale=i['spesa_totale'],
                            ct_incentivo=i['ct_incentivo'],
                            eco_detrazione=i['eco_detrazione'],
                            dati=i.get('dati', {})
                        )
                        for i in progetto_sel['interventi']
                    ]

                    scenario_multi_obj = ScenarioMultiIntervento(
                        nome_progetto=progetto_sel['nome_progetto'],
                        tipo_soggetto=progetto_sel['tipo_soggetto'],
                        tipo_edificio=progetto_sel['tipo_edificio'],
                        indirizzo=progetto_sel['indirizzo'],
                        interventi=interventi_obj,
                        spesa_totale=progetto_sel['spesa_totale'],
                        ct_incentivo_base=progetto_sel['ct_incentivo_base'],
                        ct_bonus_multi_5=progetto_sel.get('ct_bonus_multi_5', 0),
                        ct_bonus_multi_15=progetto_sel.get('ct_bonus_multi_15', 0),
                        ct_incentivo_totale=progetto_sel['ct_incentivo_totale'],
                        ct_npv=progetto_sel['ct_npv'],
                        eco_detrazione_totale=progetto_sel['eco_detrazione_totale'],
                        eco_npv=progetto_sel['eco_npv'],
                        riduzione_ep_perc=progetto_sel.get('riduzione_ep_perc'),
                        ape_ante_operam=progetto_sel.get('ape_ante_operam'),
                        ape_post_operam=progetto_sel.get('ape_post_operam'),
                        piu_conveniente=progetto_sel['piu_conveniente'],
                        differenza_npv=progetto_sel['differenza_npv']
                    )

                    # Genera HTML
                    html_content = genera_report_multi_intervento_html(
                        scenario=scenario_multi_obj,
                        anno=anno_report_multi,
                        tasso_sconto=tasso_report_multi
                    )

                    # Download
                    st.markdown(
                        get_download_link(html_content, f"relazione_multi_intervento_{progetto_sel['nome_progetto'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"),
                        unsafe_allow_html=True
                    )

                    # Preview
                    with st.expander("👁️ Anteprima Report"):
                        st.components.v1.html(html_content, height=800, scrolling=True)

                    st.success("✅ Report Multi-Intervento generato!")
                    st.info("💡 Per salvare come PDF, apri il file HTML nel browser e usa Stampa > Salva come PDF")

    # ===========================================================================
    # TAB 5: DOCUMENTI
    # ===========================================================================
    with tab_documenti:
        st.header("📋 Checklist Documentazione")

        # Selezione tipo intervento
        tipo_intervento_doc = st.radio(
            "Tipo intervento:",
            options=["🌡️ Pompe di Calore", "☀️ Solare Termico", "🔆 FV Combinato", "🔥 Biomassa", "🏠 Isolamento Termico", "🪟 Serramenti", "🌤️ Schermature Solari", "💡 Illuminazione LED", "🏢 Building Automation", "🔀 Sistemi Ibridi", "🔌 Ricarica Veicoli Elettrici", "🚿 Scaldacqua PdC"],
            horizontal=True,
            key="doc_tipo_intervento"
        )

        if tipo_intervento_doc == "🌡️ Pompe di Calore":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.9.4**")

            # Selezione tipo incentivo
            incentivo_doc = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus"],
                horizontal=True,
                key="doc_incentivo_pdc"
            )

            st.divider()

            if incentivo_doc == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - Pompe di Calore (Int. III.A)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.9.4")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2, col3 = st.columns(3)
                with col1:
                    potenza_doc = st.number_input(
                        "Potenza nominale (kW)",
                        min_value=1.0, max_value=2000.0, value=10.0,
                        key="doc_potenza",
                        help="Determina i documenti obbligatori"
                    )
                with col2:
                    a_catalogo = st.checkbox(
                        "Generatore a Catalogo GSE",
                        value=False,
                        key="doc_catalogo",
                        help="Se presente nel Catalogo Apparecchi Domestici GSE"
                    )
                with col3:
                    incentivo_stimato = st.number_input(
                        "Incentivo stimato (€)",
                        min_value=0.0, max_value=100000.0, value=5000.0,
                        key="doc_incentivo",
                        help="Per verificare soglia 3.500€"
                    )

                col1, col2 = st.columns(2)
                with col1:
                    uso_acs_processo = st.checkbox(
                        "Anche per ACS/calore processo",
                        value=False,
                        key="doc_acs",
                        help="Se PdC usata anche per acqua calda sanitaria o processo"
                    )
                with col2:
                    is_geotermica = st.checkbox(
                        "Pompa di calore geotermica",
                        value=False,
                        key="doc_geo",
                        help="Richiede schema posizionamento sonde"
                    )

                st.divider()

                # Inizializza stato checklist CT pompe di calore
                if "checklist_ct_pdc" not in st.session_state:
                    st.session_state.checklist_ct_pdc = {}

                # ==========================================
                # SEZIONE A: DOCUMENTI DA ALLEGARE ALLA RICHIESTA
                # ==========================================
                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune a tutti gli interventi")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5 e Allegato 2")

                with st.expander("ℹ️ Cosa include la documentazione comune", expanded=False):
                    st.markdown("""
                    La **documentazione comune** comprende tutti i dati e documenti da inserire/caricare sul **PortalTermico GSE**:

                    **Dati anagrafici e identificativi:**
                    - Dati del Soggetto Responsabile (nome, cognome, codice fiscale, P.IVA se applicabile)
                    - Documento d'identità in corso di validità del Soggetto Responsabile
                    - Coordinate bancarie (IBAN) per l'accredito dell'incentivo
                    - Indirizzo PEC e/o email per le comunicazioni

                    **Dati dell'immobile:**
                    - Visura catastale (Foglio, Particella, Subalterno)
                    - Categoria catastale dell'immobile
                    - Indirizzo completo dell'edificio/unità immobiliare
                    - Superficie utile riscaldata (m²)

                    **Dati dell'impianto esistente:**
                    - Tipologia impianto sostituito (caldaia, altro generatore)
                    - Potenza e combustibile dell'impianto sostituito
                    - Anno di installazione (se noto)

                    **Dichiarazioni:**
                    - Dichiarazione sostitutiva atto notorietà (DSAN) ex DPR 445/2000
                    - Dichiarazione di non cumulo con altri incentivi non cumulabili
                    - Accettazione condizioni contrattuali (Scheda-Contratto)

                    **Se applicabile:**
                    - Delega a soggetto terzo + documento identità delegante/delegato
                    - Contratto EPC/Servizio Energia (se tramite ESCO)
                    - Delibera assembleare (se condominio)
                    """)

                docs_comuni = [
                    ("scheda_domanda", "📋 Scheda-domanda compilata e sottoscritta", True),
                    ("doc_identita", "🪪 Documento d'identità del Soggetto Responsabile (in corso di validità)", True),
                    ("visura_catastale", "🏠 Visura catastale dell'immobile", True),
                    ("dsan", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                    ("iban", "🏦 Coordinate bancarie (IBAN) per accredito incentivo", True),
                ]

                for key, label, obbligatorio in docs_comuni:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                # Documenti aggiuntivi condizionali
                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                docs_comuni_cond = [
                    ("delega", "📄 Delega + documento identità delegante (se si opera tramite delegato)", False),
                    ("contratto_esco", "📄 Contratto EPC/Servizio Energia (se tramite ESCO)", False),
                    ("delibera_cond", "📄 Delibera assembleare condominiale (se intervento condominiale)", False),
                ]

                for key, label, obbligatorio in docs_comuni_cond:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(se applicabile)*" if not obbligatorio else ""),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                # 2. Asseverazione / Certificazione produttore
                st.markdown("#### 2️⃣ Asseverazione e Certificazione")

                # Logica documenti in base a potenza e catalogo
                if a_catalogo:
                    st.success("✅ Generatore a Catalogo: asseverazione NON obbligatoria")
                    assev_note = "Non richiesta (a Catalogo)"
                elif potenza_doc <= 35:
                    if incentivo_stimato > 3500:
                        assev_note = "Certificazione produttore obbligatoria (P ≤ 35 kW, incentivo > 3.500€)"
                        st.info("ℹ️ P ≤ 35 kW non a Catalogo: asseverazione non obbligatoria, ma serve certificazione produttore per incentivo > 3.500€")
                    else:
                        assev_note = "Certificazione produttore consigliata"
                        st.info("ℹ️ P ≤ 35 kW, incentivo ≤ 3.500€: asseverazione e certificazione non obbligatorie")
                elif potenza_doc > 35:
                    assev_note = "Asseverazione tecnico + certificazione produttore OBBLIGATORIE"
                    st.warning("⚠️ P > 35 kW: asseverazione tecnico abilitato + certificazione produttore obbligatorie")

                docs_assev = []
                if potenza_doc > 35 or (potenza_doc <= 35 and incentivo_stimato > 3500 and not a_catalogo):
                    docs_assev.append(("cert_produttore", "📄 Certificazione produttore (requisiti minimi DM 7/8/2025)", True))
                if potenza_doc > 35 and not a_catalogo:
                    docs_assev.append(("asseverazione", "📄 Asseverazione tecnico abilitato (par. 12.5 Regole)", True))

                for key, label, obbligatorio in docs_assev:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                # 3. Relazione tecnica (se P >= 100 kW o uso ACS/processo)
                st.markdown("#### 3️⃣ Relazione tecnica di progetto")

                if potenza_doc >= 100:
                    st.warning("⚠️ P ≥ 100 kW: relazione tecnica progetto con schemi funzionali OBBLIGATORIA")
                    if "relazione_tecnica" not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc["relazione_tecnica"] = False
                    st.session_state.checklist_ct_pdc["relazione_tecnica"] = st.checkbox(
                        "📄 Relazione tecnica di progetto con schemi funzionali *(obbligatoria)*",
                        value=st.session_state.checklist_ct_pdc["relazione_tecnica"],
                        key="ct_pdc_relazione_tecnica"
                    )

                if uso_acs_processo:
                    st.warning("⚠️ Uso anche per ACS/processo: relazione tecnica con carichi termici OBBLIGATORIA")
                    if "relazione_carichi" not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc["relazione_carichi"] = False
                    st.session_state.checklist_ct_pdc["relazione_carichi"] = st.checkbox(
                        "📄 Relazione tecnica carichi termici (risc. prevalente > 51%) *(obbligatoria)*",
                        value=st.session_state.checklist_ct_pdc["relazione_carichi"],
                        key="ct_pdc_relazione_carichi"
                    )

                if potenza_doc < 100 and not uso_acs_processo:
                    st.success("✅ Relazione tecnica non obbligatoria per questa configurazione")

                # 4. Documentazione fotografica
                st.markdown("#### 4️⃣ Documentazione fotografica")
                st.caption("Raccolta in documento PDF unico - Rif. par. 9.9.4 Regole Applicative")

                docs_foto = [
                    ("foto_targhe_sostituiti", "📷 Foto targhe generatori SOSTITUITI", True),
                    ("foto_targhe_installati", "📷 Foto targhe generatori INSTALLATI (tutte le unità)", True),
                    ("foto_generatori_sostituiti", "📷 Foto generatori sostituiti", True),
                    ("foto_generatori_installati", "📷 Foto generatori installati", True),
                    ("foto_valvole", "📷 Foto valvole termostatiche / sistema regolazione", True),
                ]

                for key, label, obbligatorio in docs_foto:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                # Foto centrale termica (solo se presente)
                st.markdown("---")
                ha_centrale_termica = st.checkbox(
                    "🏠 L'impianto è installato in una centrale termica/locale tecnico dedicato?",
                    value=False,
                    key="ct_pdc_ha_centrale"
                )

                if ha_centrale_termica:
                    docs_foto_centrale = [
                        ("foto_centrale_ante", "📷 Foto centrale termica/locale ANTE-operam", True),
                        ("foto_centrale_post", "📷 Foto centrale termica/locale POST-operam", True),
                    ]
                    for key, label, obbligatorio in docs_foto_centrale:
                        if key not in st.session_state.checklist_ct_pdc:
                            st.session_state.checklist_ct_pdc[key] = False
                        st.session_state.checklist_ct_pdc[key] = st.checkbox(
                            label + " *(obbligatorio)*",
                            value=st.session_state.checklist_ct_pdc[key],
                            key=f"ct_pdc_{key}"
                        )
                else:
                    st.info("ℹ️ Le foto della centrale termica non sono richieste se il generatore non è installato in un locale tecnico dedicato.")

                st.divider()

                # ==========================================
                # SEZIONE B: DOCUMENTI DA CONSERVARE
                # ==========================================
                st.markdown("### 📁 Documenti da conservare")
                st.caption("Da esibire in caso di controllo GSE")

                docs_conservare = [
                    ("scheda_tecnica", "📄 Scheda tecnica produttore (SCOP, η_s, GWP, P_rated)", True),
                    ("cert_smaltimento", "📄 Certificato smaltimento generatore sostituito", True),
                    ("dm_37_08", "📄 Dichiarazione conformità DM 37/08", True),
                    ("titolo_abilitativo", "📄 Titolo autorizzativo/abilitativo (se previsto)", False),
                    ("catasto_regionale", "📄 Iscrizione catasto regionale impianti (se presente)", False),
                ]

                # Libretto impianto obbligatorio solo se P > 10 kW termici (DPR 74/2013)
                if potenza_doc > 10:
                    docs_conservare.insert(3, ("libretto", "📄 Libretto impianto aggiornato (P > 10 kW)", True))
                else:
                    st.info("ℹ️ Libretto impianto non obbligatorio per P ≤ 10 kW (DPR 74/2013)")

                # Aggiungi documenti condizionali
                if potenza_doc >= 35 and potenza_doc < 100:
                    docs_conservare.insert(4, ("relazione_35_100", "📄 Relazione tecnica progetto (P 35-100 kW)", True))

                if is_geotermica and potenza_doc < 35:
                    docs_conservare.insert(4, ("schema_sonde", "📄 Schema posizionamento sonde geotermiche", True))

                if potenza_doc >= 200:
                    docs_conservare.insert(4, ("ape_post", "📄 APE post-operam", True))
                    docs_conservare.insert(4, ("diagnosi_ante", "📄 Diagnosi energetica ante-operam", True))
                    st.error("⚠️ P ≥ 200 kW: Diagnosi ante-operam e APE post-operam OBBLIGATORI (pena decadenza)")

                for key, label, obbligatorio in docs_conservare:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                st.divider()

                # ==========================================
                # SEZIONE C: FATTURE E BONIFICI
                # ==========================================
                st.markdown("### 💰 Fatture e Bonifici")
                st.caption("Rif. Paragrafo 12.2 Regole Applicative")

                docs_pagamento = [
                    ("fatture", "🧾 Fatture intestate al Soggetto Responsabile", True),
                    ("bonifici", "💳 Ricevute bonifici con riferimento DM 7/8/2025", True),
                ]

                for key, label, obbligatorio in docs_pagamento:
                    if key not in st.session_state.checklist_ct_pdc:
                        st.session_state.checklist_ct_pdc[key] = False
                    st.session_state.checklist_ct_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_pdc[key],
                        key=f"ct_pdc_{key}"
                    )

                with st.expander("📝 Esempio causale bonifico"):
                    st.markdown("""
                    **Formato causale bonifico:**

                    ```
                    D.M. 7 agosto 2025 FATTURA N. xx/202x SR XXXYYY99Z991Z999Y P.iva 12345678910 BENEFICIARIO XXXYYY99Z991Z999Y P.iva 12345678910
                    ```

                    **Struttura:**
                    - `D.M. 7 agosto 2025` - Riferimento al Decreto
                    - `FATTURA N. xx/202x` - Numero e anno fattura
                    - `SR XXXYYY99Z991Z999Y` - Codice Fiscale del Soggetto Responsabile
                    - `P.iva 12345678910` - Partita IVA del Soggetto Responsabile
                    - `BENEFICIARIO XXXYYY99Z991Z999Y` - CF/P.IVA del beneficiario (fornitore)
                    - `P.iva 12345678910` - Partita IVA del beneficiario

                    ⚠️ *L'opzione "Identificativo fiscale" è riservata agli operatori esteri privi di Partita IVA o Codice Fiscale.*
                    """)

                st.info("""
                **Requisiti fatture:**
                - Intestate al Soggetto Responsabile
                - Riferimento al D.M. 7 agosto 2025
                - Descrizione chiara tipologia intervento
                - P.IVA emittente e CF/P.IVA Soggetto Responsabile

                **Requisiti bonifici:**
                - Causale con riferimento DM 7/8/2025 e n. fattura
                - ⚠️ NON usare bonifici per detrazioni fiscali (65%-50%)
                """)

                # Calcolo progresso CT
                ct_completati = sum(st.session_state.checklist_ct_pdc.values())
                ct_totali = len(st.session_state.checklist_ct_pdc)
                ct_progresso = ct_completati / ct_totali if ct_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {ct_completati}/{ct_totali} documenti")
                st.progress(ct_progresso)

                # Link utili CT
                st.divider()
                st.subheader("🔗 Link Utili - Conto Termico")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Area Clienti GSE**](https://areaclienti.gse.it/)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    - [**Catalogo Apparecchi**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/catalogo-apparecchi-domestici)
                    - [**Normativa**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/normativa)
                    """)

                st.info("""
                💡 **Scadenza:** La domanda va presentata entro **60 giorni** dalla data di conclusione dell'intervento
                (data collaudo o dichiarazione di conformità DM 37/08).
                """)

            else:  # Ecobonus
                st.subheader("📁 Documenti per Ecobonus - Pompe di Calore")
                st.caption("Rif. D.L. 63/2013 e Vademecum ENEA")

                # Inizializza checklist Ecobonus
                if "checklist_eco_pdc" not in st.session_state:
                    st.session_state.checklist_eco_pdc = {}

                # Parametri
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    potenza_eco = st.number_input(
                        "Potenza nominale (kW)",
                        min_value=1.0, max_value=500.0, value=10.0,
                        key="eco_potenza",
                        help="P > 100 kW richiede asseverazione"
                    )
                with col2:
                    is_condominio = st.checkbox(
                        "Intervento condominiale",
                        value=False,
                        key="eco_condominio",
                        help="Richiede delibera assembleare"
                    )

                st.divider()

                # Comunicazione ENEA
                st.markdown("### 📤 Comunicazione ENEA")

                docs_enea = [
                    ("cpid_enea", "📄 Scheda descrittiva con codice CPID (entro 90 giorni)", True),
                ]

                for key, label, obbligatorio in docs_enea:
                    if key not in st.session_state.checklist_eco_pdc:
                        st.session_state.checklist_eco_pdc[key] = False
                    st.session_state.checklist_eco_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_eco_pdc[key],
                        key=f"eco_pdc_{key}"
                    )

                # Documentazione tecnica
                st.markdown("### 📋 Documentazione Tecnica")

                docs_tecnica = [
                    ("schede_tecniche", "📄 Schede tecniche prodotti (PdC, valvole termostatiche)", True),
                    ("dm_37_08", "📄 Dichiarazione conformità DM 37/08", True),
                ]

                # Libretto impianto obbligatorio solo se P > 10 kW termici (DPR 74/2013)
                if potenza_eco > 10:
                    docs_tecnica.append(("libretto", "📄 Libretto impianto aggiornato (P > 10 kW)", True))
                else:
                    st.info("ℹ️ Libretto impianto non obbligatorio per P ≤ 10 kW (DPR 74/2013)")

                if potenza_eco > 100:
                    docs_tecnica.insert(0, ("asseverazione", "📄 Asseverazione tecnico abilitato", True))
                    st.warning("⚠️ P > 100 kW: asseverazione obbligatoria")
                else:
                    docs_tecnica.insert(0, ("dichiarazione_fornitore", "📄 Dichiarazione fornitore (alternativa ad asseverazione)", False))

                for key, label, obbligatorio in docs_tecnica:
                    if key not in st.session_state.checklist_eco_pdc:
                        st.session_state.checklist_eco_pdc[key] = False
                    st.session_state.checklist_eco_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_eco_pdc[key],
                        key=f"eco_pdc_{key}"
                    )

                st.info("ℹ️ **APE non richiesto**: L'APE (Attestato Prestazione Energetica) NON è richiesto tra i documenti obbligatori per pompe di calore Ecobonus secondo il vademecum ENEA.")

                # Documentazione amministrativa
                st.markdown("### 💰 Documentazione Amministrativa")

                docs_admin = [
                    ("fatture", "🧾 Fatture con dettaglio spese", True),
                    ("bonifici", "💳 Bonifici parlanti (causale art. 16-bis DPR 917/86)", True),
                ]

                if is_condominio:
                    docs_admin.append(("delibera", "📄 Delibera assembleare", True))

                docs_admin.append(("consenso", "📄 Consenso proprietario (se detentore)", False))

                for key, label, obbligatorio in docs_admin:
                    if key not in st.session_state.checklist_eco_pdc:
                        st.session_state.checklist_eco_pdc[key] = False
                    st.session_state.checklist_eco_pdc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_eco_pdc[key],
                        key=f"eco_pdc_{key}"
                    )

                st.info("""
                **Requisiti bonifico parlante:**
                - Causale: "Riqualificazione energetica art. 1 c. 344-347 L. 296/2006"
                - Codice fiscale beneficiario detrazione
                - Partita IVA/CF destinatario pagamento
                """)

                # Calcolo progresso Ecobonus
                eco_completati = sum(st.session_state.checklist_eco_pdc.values())
                eco_totali = len(st.session_state.checklist_eco_pdc)
                eco_progresso = eco_completati / eco_totali if eco_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {eco_completati}/{eco_totali} documenti")
                st.progress(eco_progresso)

                # Link utili Ecobonus
                st.divider()
                st.subheader("🔗 Link Utili - Ecobonus")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA**](https://detrazionifiscali.enea.it/)
                    - [**Portale 2025**](https://bonusfiscali.enea.it/)
                    - [**Vademecum ENEA**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali.html)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Ecobonus**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/faq-ecobonus.html)
                    - [**Guida Agenzia Entrate**](https://www.agenziaentrate.gov.it/portale/web/guest/aree-tematiche/casa/agevolazioni)
                    - [**Requisiti PdC**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/vademecum/pompe-di-calore.html)
                    """)

                st.info("""
                ℹ️ **Requisiti Ecobonus - Pompe di Calore**:
                - Aliquota: **65%**
                - Limite spesa: **30.000€** per unità immobiliare
                - Detrazione in 10 rate annuali
                - Interventi ammessi: pompe di calore, sistemi geotermici, scaldacqua a pompa di calore
                - APE **NON richiesto** (non menzionato nei documenti obbligatori ENEA)

                **Comunicazione ENEA**:
                - Obbligatoria entro **90 giorni** dalla fine lavori
                - Tramite portale https://detrazionifiscali.enea.it/
                """)

                st.warning("""
                ⚠️ **Dal 2025:** Caldaie a condensazione solo fossili ESCLUSE. Ammessi sistemi ibridi factory-made.
                """)

        elif tipo_intervento_doc == "☀️ Solare Termico":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.12.4**")

            # Selezione tipo incentivo
            incentivo_doc_solare = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus"],
                horizontal=True,
                key="doc_incentivo_solare"
            )

            st.divider()

            if incentivo_doc_solare == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - Solare Termico (Int. III.D)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.12.4")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    superficie_doc = st.number_input(
                        "Superficie lorda (m²)",
                        min_value=1.0, max_value=2500.0, value=10.0,
                        key="doc_superficie_solare",
                        help="Determina i documenti obbligatori"
                    )
                with col2:
                    tipo_collettore_doc = st.selectbox(
                        "Tipo collettore",
                        options=["Piano", "Sottovuoto", "Concentrazione", "Factory-made"],
                        key="doc_tipo_collettore"
                    )
    
                st.divider()
    
                # Inizializza stato checklist CT solare termico
                if "checklist_ct_solare" not in st.session_state:
                    st.session_state.checklist_ct_solare = {}
    
                # ==========================================
                # SEZIONE A: DOCUMENTI DA ALLEGARE
                # ==========================================
                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")
    
                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune a tutti gli interventi")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5 e Allegato 2")
    
                with st.expander("ℹ️ Cosa include la documentazione comune", expanded=False):
                    st.markdown("""
                    La **documentazione comune** comprende tutti i dati e documenti da inserire/caricare sul **PortalTermico GSE**:
    
                    **Dati anagrafici e identificativi:**
                    - Dati del Soggetto Responsabile (nome, cognome, codice fiscale, P.IVA se applicabile)
                    - Documento d'identità in corso di validità del Soggetto Responsabile
                    - Coordinate bancarie (IBAN) per l'accredito dell'incentivo
                    - Indirizzo PEC e/o email per le comunicazioni
    
                    **Dati dell'immobile:**
                    - Visura catastale (Foglio, Particella, Subalterno)
                    - Categoria catastale dell'immobile
                    - Indirizzo completo dell'edificio/unità immobiliare
                    - Superficie utile riscaldata (m²)
    
                    **Dati dell'impianto esistente:**
                    - Tipologia impianto termico esistente
                    - Combustibile utilizzato
    
                    **Dichiarazioni:**
                    - Dichiarazione sostitutiva atto notorietà (DSAN) ex DPR 445/2000
                    - Dichiarazione di non cumulo con altri incentivi non cumulabili
                    - Accettazione condizioni contrattuali (Scheda-Contratto)
    
                    **Se applicabile:**
                    - Delega a soggetto terzo + documento identità delegante/delegato
                    - Contratto EPC/Servizio Energia (se tramite ESCO)
                    - Delibera assembleare (se condominio)
                    """)
    
                docs_comuni_sol = [
                    ("scheda_domanda", "📋 Scheda-domanda compilata e sottoscritta", True),
                    ("doc_identita", "🪪 Documento d'identità del Soggetto Responsabile (in corso di validità)", True),
                    ("visura_catastale", "🏠 Visura catastale dell'immobile", True),
                    ("dsan", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                    ("iban", "🏦 Coordinate bancarie (IBAN) per accredito incentivo", True),
                ]
    
                for key, label, obbligatorio in docs_comuni_sol:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                # Documenti aggiuntivi condizionali
                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                docs_comuni_sol_cond = [
                    ("delega", "📄 Delega + documento identità delegante (se si opera tramite delegato)", False),
                    ("contratto_esco", "📄 Contratto EPC/Servizio Energia (se tramite ESCO)", False),
                    ("delibera_cond", "📄 Delibera assembleare condominiale (se intervento condominiale)", False),
                ]
    
                for key, label, obbligatorio in docs_comuni_sol_cond:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(se applicabile)*" if not obbligatorio else ""),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                # 2. Certificazione Solar Keymark
                st.markdown("#### 2️⃣ Certificazione Solar Keymark")
    
                docs_cert_sol = [
                    ("solar_keymark", "📄 Certificazione Solar Keymark in corso di validità", True),
                    ("test_report", "📄 Test report Solar Keymark con producibilità (kWht/m² anno)", True),
                ]
    
                if tipo_collettore_doc == "Concentrazione":
                    docs_cert_sol.append(("approv_enea", "📄 Approvazione ENEA (alternativa al Solar Keymark)", False))
    
                for key, label, obbligatorio in docs_cert_sol:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                # 3. Asseverazione (se superficie > 50 m²)
                if superficie_doc > 50:
                    st.markdown("#### 3️⃣ Asseverazione tecnico (Sl > 50 m²)")
                    if "asseverazione" not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare["asseverazione"] = False
                    st.session_state.checklist_ct_solare["asseverazione"] = st.checkbox(
                        "📄 Asseverazione tecnico abilitato *(obbligatoria per Sl > 50 m²)*",
                        value=st.session_state.checklist_ct_solare["asseverazione"],
                        key="ct_sol_asseverazione"
                    )
    
                    if "relazione_tecnica" not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare["relazione_tecnica"] = False
                    st.session_state.checklist_ct_solare["relazione_tecnica"] = st.checkbox(
                        "📄 Relazione tecnica di progetto firmata *(obbligatoria per Sl > 50 m²)*",
                        value=st.session_state.checklist_ct_solare["relazione_tecnica"],
                        key="ct_sol_relazione_tecnica"
                    )
    
                    if "schemi_funzionali" not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare["schemi_funzionali"] = False
                    st.session_state.checklist_ct_solare["schemi_funzionali"] = st.checkbox(
                        "📄 Schemi funzionali impianto *(obbligatorio per Sl > 50 m²)*",
                        value=st.session_state.checklist_ct_solare["schemi_funzionali"],
                        key="ct_sol_schemi_funzionali"
                    )
    
                # 4. Documentazione fotografica
                st.markdown("#### 4️⃣ Documentazione fotografica")
                st.caption("Raccolta in documento PDF unico - minimo 6 foto")
    
                docs_foto_sol = [
                    ("foto_collettori_inst", "📷 Foto collettori installati (vista generale)", True),
                    ("foto_targhe", "📷 Foto targhe identificative collettori", True),
                    ("foto_bollitore", "📷 Foto bollitore/accumulo installato", True),
                    ("foto_targa_bollitore", "📷 Foto targa bollitore", True),
                    ("foto_impianto_ante", "📷 Foto impianto ante-operam (se sostituzione)", False),
                    ("foto_impianto_post", "📷 Foto impianto post-operam", True),
                ]
    
                for key, label, obbligatorio in docs_foto_sol:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                st.divider()
    
                # ==========================================
                # SEZIONE B: DOCUMENTI DA CONSERVARE
                # ==========================================
                st.markdown("### 📁 Documenti da conservare")
                st.caption("Da esibire in caso di controllo GSE")
    
                docs_conservare_sol = [
                    ("cert_produttore", "📄 Certificazione produttore requisiti minimi", True),
                    ("dm_37_08", "📄 Dichiarazione conformità DM 37/08", True),
                    ("libretto", "📄 Libretto impianto", True),
                    ("garanzia_collettori", "📄 Garanzia collettori (min 5 anni)", True),
                    ("garanzia_bollitori", "📄 Garanzia bollitori (min 5 anni)", True),
                    ("garanzia_accessori", "📄 Garanzia accessori (min 2 anni)", True),
                ]
    
                # Contabilizzazione calore obbligatoria per superficie > 100 m²
                if superficie_doc > 100:
                    docs_conservare_sol.insert(2, ("contabilizzazione", "📄 Sistema contabilizzazione calore (Sl > 100 m²)", True))
                    st.warning("⚠️ Superficie > 100 m²: obbligatoria contabilizzazione calore e comunicazione GSE annuale")
    
                for key, label, obbligatorio in docs_conservare_sol:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                st.divider()
    
                # ==========================================
                # SEZIONE C: FATTURE E BONIFICI
                # ==========================================
                st.markdown("### 💰 Fatture e Bonifici")
                st.caption("Rif. Paragrafo 12.2 Regole Applicative")
    
                docs_pagamento_sol = [
                    ("fatture", "🧾 Fatture intestate al Soggetto Responsabile", True),
                    ("bonifici", "💳 Ricevute bonifici con riferimento DM 7/8/2025", True),
                ]
    
                for key, label, obbligatorio in docs_pagamento_sol:
                    if key not in st.session_state.checklist_ct_solare:
                        st.session_state.checklist_ct_solare[key] = False
                    st.session_state.checklist_ct_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_solare[key],
                        key=f"ct_sol_{key}"
                    )
    
                # Calcolo progresso
                sol_completati = sum(st.session_state.checklist_ct_solare.values())
                sol_totali = len(st.session_state.checklist_ct_solare)
                sol_progresso = sol_completati / sol_totali if sol_totali > 0 else 0
    
                st.divider()
                st.markdown(f"**Progresso:** {sol_completati}/{sol_totali} documenti")
                st.progress(sol_progresso)
    
                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Solare Termico")
    
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Area Clienti GSE**](https://areaclienti.gse.it/)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**Database Solar Keymark**](https://www.solarkeymark.org/database/)
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    - [**Normativa**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/normativa)
                    """)
    
                st.info("""
                💡 **Scadenza:** La domanda va presentata entro **60 giorni** dalla data di conclusione dell'intervento.
                """)

            else:  # Ecobonus
                st.subheader("📁 Documenti per Ecobonus - Collettori Solari Termici")
                st.caption("Rif. Legge 296/2006 (comma 346, art. 1) - Vademecum ENEA")

                # Inizializza stato checklist Ecobonus solare termico
                if "checklist_eco_solare" not in st.session_state:
                    st.session_state.checklist_eco_solare = {}

                st.info("""
                ℹ️ **Ecobonus 65%** - Detrazione IRPEF/IRES
                - Aliquota: **65%** delle spese totali sostenute
                - Limite massimo: **60.000 € per unità immobiliare**
                - Durata detrazione: **10 anni**
                - Installazione collettori solari termici per produzione ACS per usi domestici/industriali
                """)

                st.markdown("### 📋 Documentazione da trasmettere all'ENEA")
                st.caption("Entro 90 giorni dalla fine lavori")

                docs_trasmettere = [
                    ("scheda_enea", "📄 Scheda descrittiva intervento su portale ENEA (con codice CPID)", True),
                ]

                for key, label, obbligatorio in docs_trasmettere:
                    if key not in st.session_state.checklist_eco_solare:
                        st.session_state.checklist_eco_solare[key] = False
                    st.session_state.checklist_eco_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_eco_solare[key],
                        key=f"eco_sol_{key}"
                    )

                st.divider()

                st.markdown("### 📁 Documentazione da conservare")
                st.caption("Da esibire in caso di controllo Agenzia delle Entrate")

                # Parametro per superficie collettori
                st.markdown("##### ⚙️ Parametri intervento")
                superficie_collettori = st.number_input(
                    "Superficie collettori solari (m²)",
                    min_value=1.0, max_value=500.0, value=10.0,
                    key="doc_superficie_eco_solare",
                    help="Determina se serve asseverazione (≥ 20 m²) o dichiarazione produttore (< 20 m²)"
                )

                st.divider()

                # 1. Documentazione tecnica
                st.markdown("#### 1️⃣ Documentazione tecnica")

                docs_tecnici = [
                    ("scheda_desc_cpid", "📄 Stampa scheda descrittiva ENEA con codice CPID firmata", True),
                ]

                # Asseverazione o dichiarazione produttore
                if superficie_collettori < 20:
                    st.success(f"✅ Superficie < 20 m²: può bastare dichiarazione produttore (in alternativa ad asseverazione)")
                    docs_tecnici.append(("dichiarazione_produttore", "📄 Dichiarazione produttore rispetto requisiti tecnici (alternativa ad asseverazione)", False))
                    docs_tecnici.append(("asseverazione_tecnico", "📄 Asseverazione tecnico abilitato (requisiti tecnici + congruità spese) + computo metrico", False))
                else:
                    st.warning(f"⚠️ Superficie ≥ 20 m²: obbligatoria asseverazione tecnico abilitato")
                    docs_tecnici.append(("asseverazione_tecnico", "📄 Asseverazione tecnico abilitato (requisiti tecnici + congruità spese) + computo metrico", True))

                docs_tecnici.extend([
                    ("schede_tecniche", "📄 Schede tecniche collettori installati", True),
                    ("dm_37_08", "📄 Dichiarazione conformità DM 37/08", True),
                    ("libretto_impianto", "📄 Libretto impianto termico (quando previsto)", False),
                ])

                for key, label, obbligatorio in docs_tecnici:
                    if key not in st.session_state.checklist_eco_solare:
                        st.session_state.checklist_eco_solare[key] = False
                    st.session_state.checklist_eco_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_eco_solare[key],
                        key=f"eco_sol_{key}"
                    )

                # 2. Documentazione amministrativa
                st.markdown("#### 2️⃣ Documentazione amministrativa")

                docs_amm = [
                    ("fatture", "🧾 Fatture relative alle spese sostenute", True),
                    ("bonifici", "💳 Bonifici bancari/postali 'parlanti' (causale Legge 296/2006, CF beneficiario, n./data fattura, P.IVA destinatario)", True),
                    ("email_cpid", "📧 Stampa email ENEA con codice CPID", True),
                ]

                for key, label, obbligatorio in docs_amm:
                    if key not in st.session_state.checklist_eco_solare:
                        st.session_state.checklist_eco_solare[key] = False
                    st.session_state.checklist_eco_solare[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_eco_solare[key],
                        key=f"eco_sol_{key}"
                    )

                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                docs_amm_cond = [
                    ("delibera_cond", "📄 Delibera assembleare + tabella millesimale (per interventi condominiali)", False),
                    ("consenso_proprietario", "📄 Dichiarazione consenso proprietario (se intervento da detentore immobile)", False),
                ]

                for key, label, obbligatorio in docs_amm_cond:
                    if key not in st.session_state.checklist_eco_solare:
                        st.session_state.checklist_eco_solare[key] = False
                    st.session_state.checklist_eco_solare[key] = st.checkbox(
                        label,
                        value=st.session_state.checklist_eco_solare[key],
                        key=f"eco_sol_{key}"
                    )

                # Calcolo progresso
                eco_sol_completati = sum(st.session_state.checklist_eco_solare.values())
                eco_sol_totali = len(st.session_state.checklist_eco_solare)
                eco_sol_progresso = eco_sol_completati / eco_sol_totali if eco_sol_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {eco_sol_completati}/{eco_sol_totali} documenti")
                st.progress(eco_sol_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Ecobonus Collettori Solari")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA Ecobonus**](https://detrazionifiscali.enea.it/)
                    - [**Guida Agenzia Entrate**](https://www.agenziaentrate.gov.it/portale/schede/agevolazioni/detrazione-riqualificazione-energetica-55-2016)
                    - [**Database Solar Keymark**](https://www.solarkeymark.org/database/)
                    """)
                with col2:
                    st.markdown("""
                    - [**Vademecum ENEA Collettori Solari**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus.html)
                    - [**FAQ Ecobonus ENEA**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/faq-ecobonus.html)
                    - [**Normativa**](https://www.gazzettaufficiale.it/)
                    """)

                st.warning("""
                ⚠️ **Scadenza:** Comunicazione ENEA entro **90 giorni** dalla fine lavori tramite portale https://detrazionifiscali.enea.it/
                """)

                with st.expander("ℹ️ Requisiti tecnici principali", expanded=False):
                    st.markdown("""
                    **Requisiti obbligatori:**
                    - Certificazione **Solar Keymark** (UNI EN 12975/12976)
                    - Garanzia collettori e bollitori: **minimo 5 anni**
                    - Garanzia accessori elettrici/elettronici: **minimo 2 anni**
                    - Producibilità specifica minima:
                      - Collettori piani: **≥ 300 kWht/m²anno** (Würzburg)
                      - Collettori sottovuoto: **≥ 400 kWht/m²anno** (Würzburg)
                      - Collettori concentrazione: **≥ 550 kWht/m²anno** (Atene)

                    **Edifici ammessi:**
                    - Edifici **esistenti** (accatastati o con richiesta in corso)
                    - In regola con pagamento tributi
                    """)


        elif tipo_intervento_doc == "🔆 FV Combinato":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.8.4**")

            # Selezione tipo incentivo
            incentivo_doc_fv = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Bonus Ristrutturazione"],
                horizontal=True,
                key="doc_incentivo_fv"
            )

            st.divider()

            if incentivo_doc_fv == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - FV Combinato (Int. II.H)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.8.4")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2, col3 = st.columns(3)
                with col1:
                    potenza_fv_doc = st.number_input(
                        "Potenza FV (kWp)",
                        min_value=2.0, max_value=1000.0, value=6.0,
                        key="doc_potenza_fv",
                        help="Min 2 kW, max 1 MW"
                    )
                with col2:
                    ha_accumulo_doc = st.checkbox(
                        "Con sistema di accumulo",
                        value=True,
                        key="doc_ha_accumulo",
                        help="Se presente sistema di accumulo elettrico"
                    )
                with col3:
                    registro_fv_doc = st.selectbox(
                        "Registro tecnologie FV",
                        options=["Nessuno", "Sezione A (+5%)", "Sezione B (+10%)", "Sezione C (+15%)"],
                        key="doc_registro_fv",
                        help="Maggiorazione per moduli prodotti in UE"
                    )

                st.divider()

                # Inizializza stato checklist CT FV
                if "checklist_ct_fv" not in st.session_state:
                    st.session_state.checklist_ct_fv = {}

                # ==========================================
                # SEZIONE A: DOCUMENTI DA ALLEGARE ALLA RICHIESTA
                # ==========================================
                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune a tutti gli interventi")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5 e Allegato 2")

                with st.expander("ℹ️ Cosa include la documentazione comune", expanded=False):
                    st.markdown("""
                    La **documentazione comune** comprende tutti i dati e documenti da inserire/caricare sul **PortalTermico GSE**:

                    **Dati anagrafici e identificativi:**
                    - Dati del Soggetto Responsabile (nome, cognome, codice fiscale, P.IVA se applicabile)
                    - Documento d'identità in corso di validità del Soggetto Responsabile
                    - Coordinate bancarie (IBAN) per l'accredito dell'incentivo
                    - Indirizzo PEC e/o email per le comunicazioni

                    **Dati dell'immobile:**
                    - Visura catastale (Foglio, Particella, Subalterno)
                    - Categoria catastale dell'immobile
                    - Indirizzo completo dell'edificio/unità immobiliare
                    - Superficie utile riscaldata (m²)

                    **Dichiarazioni:**
                    - Dichiarazione sostitutiva atto notorietà (DSAN) ex DPR 445/2000
                    - Dichiarazione di non cumulo con altri incentivi non cumulabili
                    - Accettazione condizioni contrattuali (Scheda-Contratto)

                    **Se applicabile:**
                    - Delega a soggetto terzo + documento identità delegante/delegato
                    - Contratto EPC/Servizio Energia (se tramite ESCO)
                    - Delibera assembleare (se condominio)
                    """)

                docs_comuni_fv = [
                    ("scheda_domanda", "📋 Scheda-domanda compilata e sottoscritta", True),
                    ("doc_identita", "🪪 Documento d'identità del Soggetto Responsabile (in corso di validità)", True),
                    ("visura_catastale", "🏠 Visura catastale dell'immobile", True),
                    ("dsan", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                    ("iban", "🏦 Coordinate bancarie (IBAN) per accredito incentivo", True),
                ]

                for key, label, obbligatorio in docs_comuni_fv:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                # Documenti aggiuntivi condizionali
                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                docs_comuni_fv_cond = [
                    ("delega", "📄 Delega + documento identità delegante (se si opera tramite delegato)", False),
                    ("contratto_esco", "📄 Contratto EPC/Servizio Energia (se tramite ESCO)", False),
                    ("delibera_cond", "📄 Delibera assembleare condominiale (se intervento condominiale)", False),
                ]

                for key, label, obbligatorio in docs_comuni_fv_cond:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(se applicabile)*" if not obbligatorio else ""),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                # 2. Documentazione specifica FV (par. 9.8.4)
                st.markdown("#### 2️⃣ Documentazione specifica impianto FV")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.8.4")

                docs_specifici_fv = [
                    ("asseverazione_fv", "📄 Asseverazione tecnico abilitato (requisiti tecnici)", True),
                    ("cert_produttore_fv", "📄 Certificazione produttore dei requisiti minimi", True),
                    ("modello_unico", "📄 Copia modello unico connessione (o preventivo accettato)", True),
                    ("relazione_fabbisogno", "📄 Relazione calcolo fabbisogno elettrico ed equivalente termico", True),
                    ("report_pvgis", "📄 Report PVGIS (https://re.jrc.ec.europa.eu/pvg_tools/it/)", True),
                    ("bollette_elettriche", "📄 Bollette elettriche rappresentative consumi annuali", True),
                    ("fatture_combustibili", "📄 Fatture acquisto combustibili (per fabbisogno termico)", True),
                    ("elenco_seriali", "📄 Elenco numeri di serie moduli e inverter", True),
                    ("schede_tecniche_moduli", "📄 Schede tecniche moduli fotovoltaici", True),
                ]

                for key, label, obbligatorio in docs_specifici_fv:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                # Info PVGIS
                with st.expander("ℹ️ Come usare PVGIS per il report producibilità"):
                    st.markdown("""
                    **PVGIS** (Photovoltaic Geographical Information System) è lo strumento ufficiale della Commissione Europea per stimare la produzione FV.

                    **Passaggi:**
                    1. Vai su [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/it/)
                    2. Seleziona "Prestazione impianto fotovoltaico connesso alla rete"
                    3. Inserisci l'indirizzo o le coordinate dell'edificio
                    4. Configura l'impianto:
                       - Potenza di picco installata (kWp)
                       - Perdite di sistema (default 14%)
                       - Tipo di montaggio (integrato, rack, ecc.)
                       - Inclinazione e orientamento
                    5. Genera il report PDF
                    6. Il report include la **produzione annua stimata (kWh/anno)**

                    ⚠️ La produzione stimata NON deve superare il **105%** del fabbisogno energetico totale (elettrico + termico equivalente).
                    """)

                # Documenti aggiuntivi per P > 20 kW
                if potenza_fv_doc > 20:
                    st.markdown("#### 2️⃣bis Documenti aggiuntivi (P > 20 kW)")
                    st.warning("⚠️ Potenza > 20 kW: richiesta documentazione aggiuntiva")

                    docs_fv_gt20 = [
                        ("relazione_tecnica_fv", "📄 Relazione tecnica di progetto firmata", True),
                        ("schema_unifilare", "📄 Schema elettrico unifilare as-built", True),
                    ]

                    for key, label, obbligatorio in docs_fv_gt20:
                        if key not in st.session_state.checklist_ct_fv:
                            st.session_state.checklist_ct_fv[key] = False
                        st.session_state.checklist_ct_fv[key] = st.checkbox(
                            label + (" *(obbligatorio per P > 20 kW)*" if obbligatorio else ""),
                            value=st.session_state.checklist_ct_fv[key],
                            key=f"ct_fv_{key}"
                        )

                # Documenti Registro Tecnologie FV
                if registro_fv_doc != "Nessuno":
                    st.markdown("#### 2️⃣ter Documentazione Registro Tecnologie FV")
                    st.info(f"📋 Maggiorazione {registro_fv_doc} applicabile")

                    if "dichiarazione_registro" not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv["dichiarazione_registro"] = False
                    st.session_state.checklist_ct_fv["dichiarazione_registro"] = st.checkbox(
                        "📄 Dichiarazione iscrizione al Registro Tecnologie FV *(obbligatoria per maggiorazione)*",
                        value=st.session_state.checklist_ct_fv["dichiarazione_registro"],
                        key="ct_fv_dichiarazione_registro"
                    )

                    with st.expander("ℹ️ Come verificare l'iscrizione al Registro"):
                        st.markdown("""
                        **Verifica iscrizione moduli FV:**

                        1. **Consultare il sito GSE:**
                           [https://www.gse.it/servizi-per-te/fotovoltaico/registro-tecnologie-fotovoltaico](https://www.gse.it/servizi-per-te/fotovoltaico/registro-tecnologie-fotovoltaico)

                        2. **Richiedere al produttore/fornitore:**
                           - Dichiarazione di iscrizione al registro
                           - Indicazione della sezione specifica (A, B o C)

                        **Requisiti delle sezioni:**

                        | Sezione | Maggiorazione | Requisito |
                        |---------|---------------|-----------|
                        | A | +5% | Moduli **assemblati** in UE |
                        | B | +10% | Moduli con **celle** prodotte in UE |
                        | C | +15% | Moduli con **celle e wafer** prodotti in UE |

                        ⚠️ **TUTTI** i moduli dell'impianto devono essere iscritti alla **stessa** sezione.
                        """)

                # 3. Documentazione fotografica
                st.markdown("#### 3️⃣ Documentazione fotografica")
                st.caption("Raccolta in documento PDF unico - Minimo 6 foto (par. 9.8.4)")

                docs_foto_fv = [
                    ("foto_moduli_installati", "📷 Foto moduli FV installati (vista generale)", True),
                    ("foto_targhe_moduli", "📷 Foto targhe identificative moduli", True),
                    ("foto_inverter", "📷 Foto inverter installato con targa", True),
                    ("foto_quadro_elettrico", "📷 Foto quadro elettrico con protezioni", True),
                    ("foto_contatore", "📷 Foto contatore bidirezionale", True),
                    ("foto_copertura_post", "📷 Foto copertura post-operam (vista generale)", True),
                ]

                for key, label, obbligatorio in docs_foto_fv:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                # Foto accumulo (se presente)
                if ha_accumulo_doc:
                    st.markdown("---")
                    st.markdown("**Foto sistema di accumulo:**")

                    docs_foto_accumulo = [
                        ("foto_accumulo", "📷 Foto sistema di accumulo installato", True),
                        ("foto_targa_accumulo", "📷 Foto targa identificativa accumulo", True),
                    ]

                    for key, label, obbligatorio in docs_foto_accumulo:
                        if key not in st.session_state.checklist_ct_fv:
                            st.session_state.checklist_ct_fv[key] = False
                        st.session_state.checklist_ct_fv[key] = st.checkbox(
                            label + (" *(obbligatorio)*" if obbligatorio else ""),
                            value=st.session_state.checklist_ct_fv[key],
                            key=f"ct_fv_{key}"
                        )

                st.divider()

                # ==========================================
                # SEZIONE B: DOCUMENTI DA CONSERVARE
                # ==========================================
                st.markdown("### 📁 Documenti da conservare")
                st.caption("Da esibire in caso di controllo GSE")

                docs_conservare_fv = [
                    ("scheda_tecnica_moduli", "📄 Schede tecniche moduli FV (specifiche complete)", True),
                    ("scheda_tecnica_inverter", "📄 Scheda tecnica inverter", True),
                    ("dm_37_08_fv", "📄 Dichiarazione conformità DM 37/08", True),
                    ("garanzia_moduli", "📄 Garanzia moduli (min 10 anni prodotto, 90% rendimento)", True),
                    ("garanzia_inverter", "📄 Garanzia inverter", True),
                    ("connessione_rete", "📄 Regolamento di esercizio / Contratto connessione", True),
                ]

                if ha_accumulo_doc:
                    docs_conservare_fv.insert(2, ("scheda_tecnica_accumulo", "📄 Scheda tecnica sistema di accumulo", True))
                    docs_conservare_fv.insert(-1, ("garanzia_accumulo", "📄 Garanzia sistema di accumulo", True))

                for key, label, obbligatorio in docs_conservare_fv:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(se applicabile)*"),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                st.divider()

                # ==========================================
                # SEZIONE C: FATTURE E BONIFICI
                # ==========================================
                st.markdown("### 💰 Fatture e Bonifici")
                st.caption("Rif. Paragrafo 12.2 Regole Applicative")

                docs_pagamento_fv = [
                    ("fatture_fv", "🧾 Fatture intestate al Soggetto Responsabile", True),
                    ("bonifici_fv", "💳 Ricevute bonifici con riferimento DM 7/8/2025", True),
                ]

                for key, label, obbligatorio in docs_pagamento_fv:
                    if key not in st.session_state.checklist_ct_fv:
                        st.session_state.checklist_ct_fv[key] = False
                    st.session_state.checklist_ct_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_fv[key],
                        key=f"ct_fv_{key}"
                    )

                with st.expander("📝 Esempio causale bonifico"):
                    st.markdown("""
                    **Formato causale bonifico:**

                    ```
                    D.M. 7 agosto 2025 FATTURA N. xx/202x SR XXXYYY99Z991Z999Y P.iva 12345678910 BENEFICIARIO XXXYYY99Z991Z999Y P.iva 12345678910
                    ```

                    ⚠️ *NON usare bonifici per detrazioni fiscali (65%-50%) - causale diversa!*
                    """)

                # ==========================================
                # SEZIONE D: DOCUMENTAZIONE PDC ABBINATA
                # ==========================================
                st.markdown("### 🌡️ Documentazione PdC abbinata (III.A)")
                st.caption("L'intervento II.H richiede SEMPRE una PdC abbinata ammissibile")

                st.warning("""
                ⚠️ **IMPORTANTE:** L'intervento FV Combinato (II.H) può essere richiesto **SOLO**
                congiuntamente alla sostituzione di un impianto di climatizzazione con pompa di calore (III.A).

                La documentazione della PdC deve essere completa e conforme al paragrafo 9.9.4.
                """)

                if "doc_pdc_completa" not in st.session_state.checklist_ct_fv:
                    st.session_state.checklist_ct_fv["doc_pdc_completa"] = False
                st.session_state.checklist_ct_fv["doc_pdc_completa"] = st.checkbox(
                    "✅ Documentazione PdC abbinata (III.A) completa *(obbligatorio)*",
                    value=st.session_state.checklist_ct_fv["doc_pdc_completa"],
                    key="ct_fv_doc_pdc_completa",
                    help="Vedi tab 'Pompe di Calore' per la checklist completa"
                )

                # Calcolo progresso CT FV
                fv_completati = sum(st.session_state.checklist_ct_fv.values())
                fv_totali = len(st.session_state.checklist_ct_fv)
                fv_progresso = fv_completati / fv_totali if fv_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {fv_completati}/{fv_totali} documenti")
                st.progress(fv_progresso)

                # Link utili CT FV
                st.divider()
                st.subheader("🔗 Link Utili - FV Combinato CT 3.0")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Area Clienti GSE**](https://areaclienti.gse.it/)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**PVGIS - Calcolo producibilità**](https://re.jrc.ec.europa.eu/pvg_tools/it/)
                    - [**Registro Tecnologie FV**](https://www.gse.it/servizi-per-te/fotovoltaico/registro-tecnologie-fotovoltaico)
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    """)

                st.info("""
                💡 **Scadenza:** La domanda va presentata entro **60 giorni** dalla data di conclusione dell'intervento
                (data collaudo o dichiarazione di conformità DM 37/08).
                """)

            else:  # Bonus Ristrutturazione per FV
                st.subheader("📁 Documenti per Bonus Ristrutturazione - Fotovoltaico")
                st.caption("Rif. Art. 16-bis DPR 917/86 - Detrazione 50%")

                # Inizializza checklist Bonus Ristrutturazione FV
                if "checklist_bonus_fv" not in st.session_state:
                    st.session_state.checklist_bonus_fv = {}

                # Parametri
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    potenza_bonus_fv = st.number_input(
                        "Potenza FV (kWp)",
                        min_value=1.0, max_value=200.0, value=6.0,
                        key="bonus_potenza_fv"
                    )
                with col2:
                    ha_accumulo_bonus = st.checkbox(
                        "Con sistema di accumulo",
                        value=True,
                        key="bonus_ha_accumulo"
                    )

                st.divider()

                # Comunicazione ENEA
                st.markdown("### 📤 Comunicazione ENEA")
                st.caption("Obbligatoria per impianti FV che producono energia")

                if "cpid_enea_fv" not in st.session_state.checklist_bonus_fv:
                    st.session_state.checklist_bonus_fv["cpid_enea_fv"] = False
                st.session_state.checklist_bonus_fv["cpid_enea_fv"] = st.checkbox(
                    "📄 Comunicazione ENEA con codice CPID (entro 90 giorni) *(obbligatoria)*",
                    value=st.session_state.checklist_bonus_fv["cpid_enea_fv"],
                    key="bonus_fv_cpid_enea"
                )

                st.info("""
                ⚠️ **ENEA:** Per il fotovoltaico, la comunicazione ENEA è richiesta
                in quanto intervento che comporta risparmio energetico.
                Portale: [bonusfiscali.enea.it](https://bonusfiscali.enea.it/)
                """)

                # Documentazione tecnica
                st.markdown("### 📋 Documentazione Tecnica")

                docs_tecnica_bonus_fv = [
                    ("schede_tecniche_fv", "📄 Schede tecniche moduli e inverter", True),
                    ("dm_37_08_bonus", "📄 Dichiarazione conformità DM 37/08", True),
                    ("regolamento_esercizio", "📄 Regolamento di esercizio / Contratto GSE", True),
                    ("preventivo_accettato", "📄 Preventivo Enel accettato / Modello unico", True),
                ]

                if ha_accumulo_bonus:
                    docs_tecnica_bonus_fv.insert(1, ("scheda_accumulo_bonus", "📄 Scheda tecnica sistema di accumulo", True))

                for key, label, obbligatorio in docs_tecnica_bonus_fv:
                    if key not in st.session_state.checklist_bonus_fv:
                        st.session_state.checklist_bonus_fv[key] = False
                    st.session_state.checklist_bonus_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_bonus_fv[key],
                        key=f"bonus_fv_{key}"
                    )

                # Documentazione amministrativa
                st.markdown("### 💰 Documentazione Amministrativa")

                docs_admin_bonus_fv = [
                    ("fatture_bonus_fv", "🧾 Fatture con dettaglio spese e descrizione lavori", True),
                    ("bonifici_bonus_fv", "💳 Bonifici parlanti (causale art. 16-bis DPR 917/86)", True),
                ]

                for key, label, obbligatorio in docs_admin_bonus_fv:
                    if key not in st.session_state.checklist_bonus_fv:
                        st.session_state.checklist_bonus_fv[key] = False
                    st.session_state.checklist_bonus_fv[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_bonus_fv[key],
                        key=f"bonus_fv_{key}"
                    )

                st.info("""
                **Requisiti bonifico parlante:**
                - Causale: "Lavori di ristrutturazione edilizia art. 16-bis DPR 917/86"
                - Codice fiscale beneficiario detrazione
                - Partita IVA/CF destinatario pagamento

                **Limite spesa:** 96.000€ per unità immobiliare
                **Detrazione:** 50% in 10 rate annuali
                """)

                # Titolo abilitativo
                st.markdown("### 📄 Titolo Abilitativo")

                if "titolo_abilitativo_fv" not in st.session_state.checklist_bonus_fv:
                    st.session_state.checklist_bonus_fv["titolo_abilitativo_fv"] = False
                st.session_state.checklist_bonus_fv["titolo_abilitativo_fv"] = st.checkbox(
                    "📄 CILA / SCIA / Permesso di costruire (se richiesto) *(se applicabile)*",
                    value=st.session_state.checklist_bonus_fv["titolo_abilitativo_fv"],
                    key="bonus_fv_titolo"
                )

                st.caption("""
                Per impianti FV fino a 200 kW su edifici esistenti, generalmente è sufficiente
                una comunicazione di inizio lavori o attività libera (verifica con il Comune).
                """)

                # Calcolo progresso Bonus FV
                bonus_fv_completati = sum(st.session_state.checklist_bonus_fv.values())
                bonus_fv_totali = len(st.session_state.checklist_bonus_fv)
                bonus_fv_progresso = bonus_fv_completati / bonus_fv_totali if bonus_fv_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {bonus_fv_completati}/{bonus_fv_totali} documenti")
                st.progress(bonus_fv_progresso)

                # Link utili Bonus Ristrutturazione
                st.divider()
                st.subheader("🔗 Link Utili - Bonus Ristrutturazione FV")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA 2025**](https://bonusfiscali.enea.it/)
                    - [**Guida Agenzia Entrate**](https://www.agenziaentrate.gov.it/portale/web/guest/aree-tematiche/casa/agevolazioni)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Bonus Casa**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/bonus-casa.html)
                    - [**GSE - Scambio sul Posto**](https://www.gse.it/servizi-per-te/fotovoltaico/scambio-sul-posto)
                    """)

                st.info("""
                💡 **Scadenza ENEA:** Comunicazione entro **90 giorni** dalla fine lavori.
                """)

                st.warning("""
                ⚠️ **Aliquote dal 2025:**
                - Abitazione principale: 50% (2025-2026), poi 36% (2027), poi 30% (2028+)
                - Altre abitazioni: 36% (2025-2027), poi 30% (2028+)
                """)

        elif tipo_intervento_doc == "🔥 Biomassa":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.9.5**")

            st.info("""
            ℹ️ **NOTA**: I generatori a biomassa sono ammessi **SOLO al Conto Termico 3.0**.
            NON sono disponibili vademecum ENEA ufficiali per Ecobonus biomassa.
            """)

            st.divider()

            if True:  # Solo Conto Termico disponibile
                st.subheader("📁 Documenti per Conto Termico 3.0 - Biomassa (Int. III.C)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.9.5")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2, col3 = st.columns(3)
                with col1:
                    tipo_gen_doc = st.selectbox(
                        "Tipo generatore",
                        options=["caldaia", "stufa_pellet", "stufa_legna", "termocamino"],
                        format_func=lambda x: {
                            "caldaia": "Caldaia a biomassa",
                            "stufa_pellet": "Stufa a pellet",
                            "stufa_legna": "Stufa a legna",
                            "termocamino": "Termocamino"
                        }.get(x, x),
                        key="doc_tipo_gen_bio"
                    )
                with col2:
                    potenza_bio_doc = st.number_input(
                        "Potenza nominale (kW)",
                        min_value=1.0, max_value=2000.0, value=25.0,
                        key="doc_potenza_bio"
                    )
                with col3:
                    incentivo_bio_stimato = st.number_input(
                        "Incentivo stimato (€)",
                        min_value=0.0, max_value=100000.0, value=3000.0,
                        key="doc_incentivo_bio_stimato"
                    )

                st.divider()

                # Inizializza stato checklist CT biomassa
                if "checklist_ct_bio" not in st.session_state:
                    st.session_state.checklist_ct_bio = {}

                # ==========================================
                # SEZIONE A: DOCUMENTI DA ALLEGARE ALLA RICHIESTA
                # ==========================================
                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5")

                docs_comuni_bio = [
                    ("scheda_domanda_bio", "📋 Scheda-domanda compilata e sottoscritta", True),
                    ("doc_identita_bio", "🪪 Documento d'identità del Soggetto Responsabile", True),
                    ("visura_catastale_bio", "🏠 Visura catastale dell'immobile", True),
                    ("dsan_bio", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                    ("iban_bio", "🏦 Coordinate bancarie (IBAN)", True),
                ]

                for key, label, obbligatorio in docs_comuni_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                # 2. Certificazione ambientale
                st.markdown("#### 2️⃣ Certificazione Ambientale (OBBLIGATORIA)")

                docs_cert_bio = [
                    ("cert_4_5stelle", "⭐ Certificazione classe 4 o 5 stelle (DM 186/2017)", True),
                ]

                if tipo_gen_doc == "caldaia":
                    docs_cert_bio.append(("cert_uni_303_5", "📄 Certificazione UNI EN 303-5 classe 4 o 5", True))
                else:
                    docs_cert_bio.append(("cert_uni_16510", "📄 Certificazione UNI EN 16510:2023", True))

                for key, label, obbligatorio in docs_cert_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                st.info("ℹ️ **CLASSI AMMESSE:** Generatori classe 4 stelle (per sostituzione combustibili fossili) o classe 5 stelle (DM 186/2017)")

                # 3. Asseverazione (se P > 35 kW)
                st.markdown("#### 3️⃣ Asseverazione e Certificazione")

                if potenza_bio_doc > 35:
                    st.warning("⚠️ P > 35 kW: asseverazione tecnico e certificazione produttore OBBLIGATORIE")
                    docs_assev_bio = [
                        ("asseverazione_bio", "📄 Asseverazione tecnico abilitato", True),
                        ("cert_produttore_bio", "📄 Certificazione produttore requisiti minimi", True),
                    ]
                elif incentivo_bio_stimato > 3500:
                    st.info("ℹ️ Incentivo > 3.500€: certificazione produttore consigliata")
                    docs_assev_bio = [
                        ("cert_produttore_bio", "📄 Certificazione produttore requisiti minimi", False),
                    ]
                else:
                    st.success("✅ P ≤ 35 kW e incentivo ≤ 3.500€: asseverazione non obbligatoria")
                    docs_assev_bio = []

                for key, label, obbligatorio in docs_assev_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else " *(consigliato)*"),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                # 4. Documentazione tecnica specifica biomassa
                st.markdown("#### 4️⃣ Documentazione Tecnica Specifica")

                docs_tecnica_bio = [
                    ("scheda_tecnica_gen", "📄 Scheda tecnica generatore (rendimento, emissioni)", True),
                    ("dm_37_08_bio", "📄 Dichiarazione conformità DM 37/08", True),
                    ("libretto_impianto", "📄 Libretto impianto aggiornato", True),
                ]

                # Caldaie: documenti specifici
                if tipo_gen_doc == "caldaia":
                    docs_tecnica_bio.append(("cert_accumulo", "📄 Certificazione sistema accumulo (≥20 dm³/kW)", True))
                    if potenza_bio_doc > 500:
                        docs_tecnica_bio.append(("cert_abbattimento", "📄 Certificazione sistema abbattimento particolato", True))

                for key, label, obbligatorio in docs_tecnica_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                # 5. Documentazione fotografica
                st.markdown("#### 5️⃣ Documentazione Fotografica")

                docs_foto_bio = [
                    ("foto_generatore", "📷 Foto generatore installato", True),
                    ("foto_targa", "📷 Foto targa dati generatore", True),
                    ("foto_canna_fumaria", "📷 Foto canna fumaria/scarico fumi", True),
                    ("foto_ante_operam", "📷 Foto impianto ante-operam (prima dell'intervento)", True),
                    ("foto_post_operam", "📷 Foto impianto post-operam (dopo l'intervento)", True),
                ]

                if tipo_gen_doc == "caldaia":
                    docs_foto_bio.append(("foto_accumulo_bio", "📷 Foto sistema di accumulo", True))
                    if potenza_bio_doc > 500:
                        docs_foto_bio.append(("foto_abbattimento", "📷 Foto sistema abbattimento particolato", True))

                for key, label, obbligatorio in docs_foto_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                # 6. Fatture e bonifici
                st.markdown("#### 6️⃣ Fatture e Bonifici")

                docs_fatture_bio = [
                    ("fatture_bio", "💰 Fatture intestate al Soggetto Responsabile", True),
                    ("bonifici_bio", "💳 Bonifici con riferimento DM 7/8/2025", True),
                ]

                for key, label, obbligatorio in docs_fatture_bio:
                    if key not in st.session_state.checklist_ct_bio:
                        st.session_state.checklist_ct_bio[key] = False
                    st.session_state.checklist_ct_bio[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_bio[key],
                        key=f"ct_bio_{key}"
                    )

                # Progresso
                bio_completati = sum(st.session_state.checklist_ct_bio.values())
                bio_totali = len(st.session_state.checklist_ct_bio)
                bio_progresso = bio_completati / bio_totali if bio_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {bio_completati}/{bio_totali} documenti")
                st.progress(bio_progresso)

                # Link utili CT Biomassa
                st.divider()
                st.subheader("🔗 Link Utili - Biomassa CT 3.0")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative.pdf)
                    - [**DM 186/2017 (Classe 5 stelle)**](https://www.gazzettaufficiale.it/eli/id/2017/11/16/17G00193/sg)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    - [**Norma UNI EN 303-5**](https://store.uni.com/uni-en-303-5-2012)
                    - [**Norma UNI EN 16510**](https://store.uni.com/ricerca?q=UNI+EN+16510)
                    """)

                st.info("""
                💡 **Scadenza:** La domanda va presentata entro **60 giorni** dalla data di conclusione dell'intervento.
                """)


        elif tipo_intervento_doc == "🏠 Isolamento Termico":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Intervento II.A**")

            # Selezione tipo incentivo
            incentivo_doc_iso = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus", "Bonus Ristrutturazione"],
                horizontal=True,
                key="doc_incentivo_iso"
            )

            st.divider()

            if incentivo_doc_iso == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - Isolamento Termico (Int. II.A)")
                st.caption("Rif. Regole Applicative CT 3.0 - Intervento II.A - Isolamento superfici opache")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    tipo_superficie_doc = st.selectbox(
                        "Tipo superficie",
                        options=["coperture", "pavimenti", "pareti"],
                        format_func=lambda x: {"coperture": "Coperture (tetti)", "pavimenti": "Pavimenti", "pareti": "Pareti"}.get(x, x),
                        key="doc_iso_superficie"
                    )
                with col2:
                    incentivo_stimato_iso = st.number_input(
                        "Incentivo stimato (€)",
                        min_value=0.0, max_value=500000.0, value=10000.0,
                        key="doc_iso_incentivo",
                        help="Per verificare soglia 15.000€ (rata unica)"
                    )

                st.divider()

                # Inizializza stato checklist CT isolamento
                if "checklist_ct_iso" not in st.session_state:
                    st.session_state.checklist_ct_iso = {}

                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5")

                doc_iso_ct_comune = {
                    "scheda_domanda_iso": st.checkbox("Scheda-domanda compilata e sottoscritta", key="doc_iso_scheda"),
                    "doc_identita_iso": st.checkbox("Documento d'identità del Soggetto Responsabile", key="doc_iso_identita"),
                    "visura_catastale_iso": st.checkbox("Visura catastale dell'immobile", key="doc_iso_visura"),
                    "dsan_iso": st.checkbox("Dichiarazione sostitutiva di atto di notorietà (DSAN)", key="doc_iso_dsan"),
                    "iban_iso": st.checkbox("Coordinate bancarie (IBAN)", key="doc_iso_iban")
                }
                st.session_state.checklist_ct_iso.update(doc_iso_ct_comune)

                # 2. Documentazione tecnica specifica
                st.markdown("#### 2️⃣ Documentazione tecnica - Isolamento Termico")
                st.caption("Rif. Regole Applicative CT 3.0 - Intervento II.A")

                st.info("""
                **Documenti tecnici obbligatori per isolamento termico:**
                - Diagnosi energetica o APE ante-operam
                - APE post-intervento
                - Asseverazione tecnico abilitato (trasmittanza, superficie, conformità)
                - Certificazioni materiali isolanti
                - Relazione tecnica intervento
                """)

                doc_iso_ct_tecnici = {
                    "diagnosi_ape_ante_iso": st.checkbox("Diagnosi energetica o APE ante-operam", key="doc_iso_ape_ante"),
                    "ape_post_iso": st.checkbox("APE post-intervento (obbligatorio)", key="doc_iso_ape_post"),
                    "asseverazione_iso": st.checkbox("Asseverazione tecnico abilitato (trasmittanza, superficie)", key="doc_iso_asseverazione"),
                    "cert_materiali_iso": st.checkbox("Certificazioni materiali isolanti (conducibilità termica λ)", key="doc_iso_cert_materiali"),
                    "relazione_tecnica_iso": st.checkbox("Relazione tecnica dell'intervento", key="doc_iso_relazione")
                }
                st.session_state.checklist_ct_iso.update(doc_iso_ct_tecnici)

                # 3. Documentazione economica
                st.markdown("#### 3️⃣ Documentazione economica")
                doc_iso_ct_economici = {
                    "computo_metrico_iso": st.checkbox("Computo metrico estimativo", key="doc_iso_computo"),
                    "fatture_iso": st.checkbox("Fatture quietanzate dei lavori", key="doc_iso_fatture"),
                    "bonifici_iso": st.checkbox("Bonifici/ricevute pagamento", key="doc_iso_bonifici")
                }
                st.session_state.checklist_ct_iso.update(doc_iso_ct_economici)

                # Progresso
                iso_ct_completati = sum(1 for v in st.session_state.checklist_ct_iso.values() if v)
                iso_ct_totali = len(st.session_state.checklist_ct_iso)
                iso_ct_progresso = iso_ct_completati / iso_ct_totali if iso_ct_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {iso_ct_completati}/{iso_ct_totali} documenti")
                st.progress(iso_ct_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Conto Termico Isolamento")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole_applicative_CT3.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**Catalogo Interventi GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/cataloghi)
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    """)

            elif incentivo_doc_iso == "Ecobonus":
                st.subheader("📁 Documenti per Ecobonus - Coibentazione Involucro")
                st.caption("Rif. D.L. 63/2013 - Vademecum ENEA Coibentazione")

                # Inizializza stato checklist Eco isolamento
                if "checklist_eco_iso" not in st.session_state:
                    st.session_state.checklist_eco_iso = {}

                st.warning("""
                ⚠️ **Asseverazione sempre obbligatoria**:
                Per la coibentazione, l'asseverazione tecnico abilitato è **sempre obbligatoria** e **non può essere sostituita**
                con dichiarazione del produttore/installatore (a differenza di altri interventi Ecobonus).
                """)

                st.markdown("### 📤 Documentazione da preparare")

                # 1. Comunicazione ENEA
                st.markdown("#### 📤 Comunicazione ENEA")
                st.caption("Da inviare entro 90 giorni dalla fine lavori")

                doc_iso_eco_enea = {
                    "scheda_descrittiva_iso": st.checkbox("📋 Scheda descrittiva intervento con CPID (portale ENEA) *(obbligatorio)*", key="doc_iso_eco_scheda")
                }
                st.session_state.checklist_eco_iso.update(doc_iso_eco_enea)

                # 2. Documentazione tecnica
                st.markdown("#### 📋 Documentazione Tecnica")

                doc_iso_eco_tecnici = {
                    "asseverazione_eco_iso": st.checkbox("📄 Asseverazione tecnico abilitato (sempre obbligatoria) *(obbligatorio)*", key="doc_iso_eco_assev"),
                    "ape_post_eco_iso": st.checkbox("📄 APE (Attestato Prestazione Energetica) di ogni singola unità immobiliare *(obbligatorio)*", key="doc_iso_eco_ape"),
                    "relazione_tecnica_iso": st.checkbox("📄 Relazione tecnica L.192/2005 *(obbligatorio)*", key="doc_iso_eco_relaz_192"),
                    "computo_metrico_iso": st.checkbox("📄 Computo metrico (dal 6 ottobre 2020) *(obbligatorio)*", key="doc_iso_eco_computo"),
                    "cert_materiali_eco_iso": st.checkbox("📄 Certificazioni materiali isolanti (λ, spessore, CAM) *(obbligatorio)*", key="doc_iso_eco_cert")
                }
                st.session_state.checklist_eco_iso.update(doc_iso_eco_tecnici)

                # 3. Documentazione economica
                st.markdown("#### 💰 Documentazione Amministrativa")
                doc_iso_eco_economici = {
                    "fatture_eco_iso": st.checkbox("🧾 Fatture dei lavori *(obbligatorio)*", key="doc_iso_eco_fatture"),
                    "bonifici_parlanti_iso": st.checkbox("💳 Bonifici parlanti (causale specifica Ecobonus) *(obbligatorio)*", key="doc_iso_eco_bonif"),
                    "ricevute_bonifici_iso": st.checkbox("📄 Ricevute bonifici *(obbligatorio)*", key="doc_iso_eco_ric")
                }
                st.session_state.checklist_eco_iso.update(doc_iso_eco_economici)

                # Progresso
                iso_eco_completati = sum(1 for v in st.session_state.checklist_eco_iso.values() if v)
                iso_eco_totali = len(st.session_state.checklist_eco_iso)
                iso_eco_progresso = iso_eco_completati / iso_eco_totali if iso_eco_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {iso_eco_completati}/{iso_eco_totali} documenti")
                st.progress(iso_eco_progresso)

                st.info("""
                ℹ️ **Requisiti tecnici**:
                - Aliquota: **65%**
                - Limite spesa: **60.000€** per unità immobiliare
                - Detrazione in 10 rate annuali
                - Superfici disperdenti opache verticali, orizzontali, inclinate
                - Rispetto valori trasmittanza U secondo zona climatica (DM 26/6/2015 - Allegato E)

                **Comunicazione ENEA**:
                - Obbligatoria entro 90 giorni dalla fine lavori
                - Tramite portale https://detrazionifiscali.enea.it/
                """)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Ecobonus Coibentazione")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA Detrazioni Fiscali**](https://detrazionifiscali.enea.it/)
                    - [**Vademecum Coibentazione**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus.html)
                    """)
                with col2:
                    st.markdown("""
                    - [**Agenzia Entrate - Ecobonus**](https://www.agenziaentrate.gov.it/portale/web/guest/schede/agevolazioni/detrazione-riqualificazione-energetica-702)
                    - [**DM 26/6/2015 - Requisiti Tecnici**](https://www.gazzettaufficiale.it/eli/id/2015/07/15/15A05198/sg)
                    """)

            else:  # Bonus Ristrutturazione
                st.subheader("📁 Documenti per Bonus Ristrutturazione - Isolamento Termico")
                st.caption("Rif. Art. 16-bis TUIR - Legge di Bilancio 2025")

                # Inizializza stato checklist Bonus Ristrutt isolamento
                if "checklist_bonus_iso" not in st.session_state:
                    st.session_state.checklist_bonus_iso = {}

                st.info("""
                **IMPORTANTE:** Il Bonus Ristrutturazione NON è cumulabile con l'Ecobonus.
                Per interventi di risparmio energetico è richiesta la comunicazione ENEA entro 90 giorni.
                """)

                st.markdown("### 📤 Documentazione da preparare")

                # 1. Documentazione amministrativa
                st.markdown("#### 1️⃣ Documentazione amministrativa")
                doc_iso_bonus_amm = {
                    "titolo_edilizio_iso": st.checkbox("Titolo edilizio (CILA, SCIA, permesso di costruire)", key="doc_iso_bonus_titolo"),
                    "comunicazione_asl_iso": st.checkbox("Comunicazione preventiva ASL (se richiesta)", key="doc_iso_bonus_asl"),
                    "visura_catastale_bonus_iso": st.checkbox("Visura catastale aggiornata", key="doc_iso_bonus_visura")
                }
                st.session_state.checklist_bonus_iso.update(doc_iso_bonus_amm)

                # 2. Documentazione tecnica
                st.markdown("#### 2️⃣ Documentazione tecnica")
                doc_iso_bonus_tecnici = {
                    "scheda_enea_bonus_iso": st.checkbox("Scheda descrittiva ENEA (richiesta per risparmio energetico)", key="doc_iso_bonus_enea"),
                    "relazione_tecnica_bonus_iso": st.checkbox("Relazione tecnica intervento", key="doc_iso_bonus_relaz"),
                    "ape_bonus_iso": st.checkbox("APE post-intervento", key="doc_iso_bonus_ape")
                }
                st.session_state.checklist_bonus_iso.update(doc_iso_bonus_tecnici)

                # 3. Documentazione economica
                st.markdown("#### 3️⃣ Documentazione economica")
                doc_iso_bonus_economici = {
                    "fatture_bonus_iso": st.checkbox("Fatture lavori edili", key="doc_iso_bonus_fatture"),
                    "bonifici_parlanti_bonus_iso": st.checkbox("Bonifici parlanti (causale: Art. 16-bis TUIR)", key="doc_iso_bonus_bonif"),
                    "dichiarazione_redditi_iso": st.checkbox("Dichiarazione dei redditi (per detrazioni)", key="doc_iso_bonus_730")
                }
                st.session_state.checklist_bonus_iso.update(doc_iso_bonus_economici)

                # Progresso
                iso_bonus_completati = sum(1 for v in st.session_state.checklist_bonus_iso.values() if v)
                iso_bonus_totali = len(st.session_state.checklist_bonus_iso)
                iso_bonus_progresso = iso_bonus_completati / iso_bonus_totali if iso_bonus_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {iso_bonus_completati}/{iso_bonus_totali} documenti")
                st.progress(iso_bonus_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Bonus Ristrutturazione")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA (per risparmio energetico)**](https://bonusfiscali.enea.it/)
                    - [**Agenzia Entrate - Guida Ristrutturazioni**](https://www.agenziaentrate.gov.it/portale/web/guest/schede/agevolazioni/detrazione-riqualificazione-energetica-55-65)
                    """)
                with col2:
                    st.markdown("""
                    - [**Bonus Casa 2025**](https://www.agenziaentrate.gov.it/portale/web/guest/bonus-casa)
                    - [**FAQ Bonus Ristrutturazione**](https://www.agenziaentrate.gov.it/portale/web/guest/faq)
                    """)

                st.warning("""
                ⚠️ **Aliquote Bonus Ristrutturazione:**
                - 2025-2026: 50% abitazione principale, 36% altre abitazioni
                - 2027+: 36% abitazione principale, 30% altre abitazioni
                - Limite spesa: 96.000€ per unità immobiliare
                - Recupero: 10 rate annuali di pari importo
                - Scadenza comunicazione ENEA: 90 giorni dalla fine lavori (solo per risparmio energetico)
                """)

        elif tipo_intervento_doc == "🪟 Serramenti":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.2**")

            # Selezione tipo incentivo
            incentivo_doc_serr = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus", "Bonus Ristrutturazione"],
                horizontal=True,
                key="doc_incentivo_serr"
            )

            st.divider()

            if incentivo_doc_serr == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - Serramenti (Int. II.B)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.2.4")

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    superficie_serr_doc = st.number_input(
                        "Superficie serramenti (m²)",
                        min_value=1.0, max_value=1000.0, value=50.0,
                        key="doc_serr_superficie",
                        help="Superficie totale serramenti sostituiti"
                    )
                with col2:
                    incentivo_stimato_serr = st.number_input(
                        "Incentivo stimato (€)",
                        min_value=0.0, max_value=500000.0, value=10000.0,
                        key="doc_serr_incentivo",
                        help="Per verificare soglia 15.000€ (rata unica)"
                    )

                potenza_impianto_serr = st.number_input(
                    "Potenza nominale impianto (kW)",
                    min_value=1.0, max_value=10000.0, value=50.0,
                    key="doc_serr_potenza",
                    help="Per verificare soglia 200 kW (APE obbligatorio)"
                )

                st.divider()

                # Inizializza stato checklist CT serramenti
                if "checklist_ct_serr" not in st.session_state:
                    st.session_state.checklist_ct_serr = {}

                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5")

                doc_serr_ct_comune = {
                    "scheda_domanda_serr": st.checkbox("📋 Scheda-domanda compilata e sottoscritta *(obbligatorio)*", key="doc_serr_scheda"),
                    "doc_identita_serr": st.checkbox("🪪 Documento d'identità del Soggetto Responsabile *(obbligatorio)*", key="doc_serr_identita"),
                    "visura_catastale_serr": st.checkbox("🏠 Visura catastale dell'immobile *(obbligatorio)*", key="doc_serr_visura"),
                    "dsan_serr": st.checkbox("📝 Dichiarazione sostitutiva di atto di notorietà (DSAN) *(obbligatorio)*", key="doc_serr_dsan"),
                    "iban_serr": st.checkbox("🏦 Coordinate bancarie (IBAN) *(obbligatorio)*", key="doc_serr_iban")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_ct_comune)

                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                doc_serr_ct_comune_cond = {
                    "delega_serr": st.checkbox("📄 Delega + documento identità delegante (se tramite delegato)", key="doc_serr_delega"),
                    "contratto_esco_serr": st.checkbox("📄 Contratto EPC/Servizio Energia (se tramite ESCO)", key="doc_serr_esco"),
                    "delibera_cond_serr": st.checkbox("📄 Delibera assembleare condominiale (se condominio)", key="doc_serr_delibera")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_ct_comune_cond)

                # 2. Asseverazione tecnica
                st.markdown("#### 2️⃣ Asseverazione tecnica")
                st.caption("Rif. Paragrafo 12.5 Regole Applicative")

                st.info("""
                **Asseverazione tecnico abilitato obbligatoria** con:
                - Verifica rispetto trasmittanza termica Uw (Tabella 16)
                - Calcolo superfici serramenti sostituiti
                - Attestazione sostituzione integrale chiusura trasparente + infisso
                - Verifica obbligatorietà termoregolazione (installata o già presente)
                """)

                doc_serr_assev = {
                    "asseverazione_serr": st.checkbox("📄 Asseverazione tecnico abilitato (par. 12.5) *(obbligatorio)*", key="doc_serr_assev")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_assev)

                # 3. Documentazione fotografica
                st.markdown("#### 3️⃣ Documentazione fotografica")
                st.caption("Raccolta in documento PDF unico - Rif. par. 9.2.4")

                st.warning("""
                ⚠️ **OBBLIGATORIO: Foto termoregolazione**

                I sistemi di termoregolazione o valvole termostatiche devono essere:
                - Installati congiuntamente ai serramenti, OPPURE
                - Già presenti al momento dell'intervento

                È **OBBLIGATORIO** fornire documentazione fotografica dei sistemi.
                """)

                doc_serr_foto = {
                    "foto_serr_ante": st.checkbox("📷 Foto serramenti ANTE-operam (da esterno/interno) *(obbligatorio)*", key="doc_serr_foto_ante"),
                    "foto_serr_post": st.checkbox("📷 Foto serramenti POST-operam (da esterno/interno) *(obbligatorio)*", key="doc_serr_foto_post"),
                    "foto_serr_lavori": st.checkbox("📷 Foto durante i lavori (rimozione vecchi, installazione nuovi) *(obbligatorio)*", key="doc_serr_foto_lavori"),
                    "foto_termoregolazione": st.checkbox("📷 Foto sistemi termoregolazione/valvole termostatiche *(OBBLIGATORIO)*", key="doc_serr_foto_termo")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_foto)

                # 4. Relazione tecnica
                st.markdown("#### 4️⃣ Relazione tecnica")
                st.caption("Rif. par. 9.2.4")

                st.info("""
                **Relazione tecnica obbligatoria** contenente:
                - Trasmittanza termica ante-operam
                - Trasmittanza termica post-operam (con verifica rispetto Tabella 16)
                - Superfici serramenti sostituiti (distinte per tipologia)
                - Computo metrico con costi unitari
                """)

                doc_serr_relazione = {
                    "relazione_tecnica_serr": st.checkbox("📄 Relazione tecnica con trasmittanze e superfici *(obbligatorio)*", key="doc_serr_relazione")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_relazione)

                # 5. Documentazione APE (se P >= 200 kW)
                if potenza_impianto_serr >= 200:
                    st.markdown("#### 5️⃣ Documentazione energetica (P ≥ 200 kW)")
                    st.error("⚠️ P ≥ 200 kW: APE post-operam + Diagnosi energetica ante-operam OBBLIGATORI")

                    doc_serr_ape = {
                        "diagnosi_ante_serr": st.checkbox("📄 Diagnosi energetica ante-operam *(obbligatorio)*", key="doc_serr_diagnosi"),
                        "ape_post_serr": st.checkbox("📄 APE post-operam *(obbligatorio)*", key="doc_serr_ape")
                    }
                    st.session_state.checklist_ct_serr.update(doc_serr_ape)
                else:
                    st.success("✅ APE e Diagnosi non obbligatori per P < 200 kW")

                st.divider()

                # SEZIONE B: DOCUMENTI DA CONSERVARE
                st.markdown("### 📁 Documenti da conservare")
                st.caption("Da esibire in caso di controllo GSE")

                doc_serr_conservare = {
                    "schede_tecniche_serr": st.checkbox("📄 Schede tecniche serramenti (trasmittanza Uw certificata) *(obbligatorio)*", key="doc_serr_schede"),
                    "schede_termo_serr": st.checkbox("📄 Schede tecniche termoregolazione/valvole (se installate) *(se applicabile)*", key="doc_serr_schede_termo"),
                    "dm_37_08_serr": st.checkbox("📄 Dichiarazione conformità DM 37/08 (se previsto) *(se applicabile)*", key="doc_serr_dm37"),
                    "titolo_abilitativo_serr": st.checkbox("📄 Titolo autorizzativo/abilitativo (se previsto) *(se applicabile)*", key="doc_serr_titolo")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_conservare)

                st.divider()

                # SEZIONE C: FATTURE E BONIFICI
                st.markdown("### 💰 Fatture e Bonifici")
                st.caption("Rif. Paragrafo 12.2 Regole Applicative")

                doc_serr_pagamento = {
                    "fatture_serr": st.checkbox("🧾 Fatture intestate al Soggetto Responsabile *(obbligatorio)*", key="doc_serr_fatture"),
                    "bonifici_serr": st.checkbox("💳 Ricevute bonifici con riferimento DM 7/8/2025 *(obbligatorio)*", key="doc_serr_bonifici")
                }
                st.session_state.checklist_ct_serr.update(doc_serr_pagamento)

                with st.expander("📝 Esempio causale bonifico"):
                    st.markdown("""
                    **Formato causale bonifico:**

                    ```
                    D.M. 7 agosto 2025 FATTURA N. xx/202x SR XXXYYY99Z991Z999Y P.iva 12345678910 BENEFICIARIO XXXYYY99Z991Z999Y P.iva 12345678910
                    ```

                    **Struttura:**
                    - `D.M. 7 agosto 2025` - Riferimento al Decreto
                    - `FATTURA N. xx/202x` - Numero e anno fattura
                    - `SR XXXYYY99Z991Z999Y` - Codice Fiscale del Soggetto Responsabile
                    - `BENEFICIARIO XXXYYY99Z991Z999Y` - CF/P.IVA del beneficiario (fornitore)
                    """)

                # Calcolo progresso CT serramenti
                serr_ct_completati = sum(1 for v in st.session_state.checklist_ct_serr.values() if v)
                serr_ct_totali = len(st.session_state.checklist_ct_serr)
                serr_ct_progresso = serr_ct_completati / serr_ct_totali if serr_ct_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {serr_ct_completati}/{serr_ct_totali} documenti")
                st.progress(serr_ct_progresso)

                # Link utili CT
                st.divider()
                st.subheader("🔗 Link Utili - Conto Termico Serramenti")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole_applicative_CT3.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    - [**Normativa**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/normativa)
                    """)

                st.info("""
                💡 **Scadenza:** La domanda va presentata entro **60 giorni** dalla data di conclusione dell'intervento
                (data collaudo o dichiarazione di fine lavori).
                """)

            elif incentivo_doc_serr == "Ecobonus":
                st.subheader("📁 Documenti per Ecobonus - Serramenti")
                st.caption("Rif. D.L. 63/2013 - Vademecum ENEA Serramenti")

                # Inizializza stato checklist Eco serramenti
                if "checklist_eco_serr" not in st.session_state:
                    st.session_state.checklist_eco_serr = {}

                st.warning("""
                ⚠️ **IMPORTANTE - Aliquota SPECIALE per Serramenti**:
                - Ecobonus per serramenti ha aliquota **50%** (NON 65% come altri interventi)
                - Limite spesa: **60.000€** per unità immobiliare
                - Detrazione in 10 rate annuali
                """)

                # Parametro tipo intervento
                st.markdown("##### ⚙️ Tipo intervento")
                tipo_unita_serr = st.radio(
                    "Tipo unità immobiliare",
                    options=["Singola unità immobiliare", "Condominio/parti comuni"],
                    key="doc_serr_tipo_unita",
                    help="Determina se servono APE e asseverazione o se bastano dichiarazioni fornitore/installatore"
                )

                is_singola_unita = (tipo_unita_serr == "Singola unità immobiliare")

                st.divider()

                st.markdown("### 📤 Documentazione da preparare")

                # 1. Comunicazione ENEA
                st.markdown("#### 📤 Comunicazione ENEA")
                st.caption("Da inviare entro 90 giorni dalla fine lavori")
                doc_serr_eco_enea = {
                    "scheda_descrittiva_serr": st.checkbox("📋 Scheda descrittiva intervento con CPID (portale ENEA) *(obbligatorio)*", key="doc_serr_eco_scheda")
                }
                st.session_state.checklist_eco_serr.update(doc_serr_eco_enea)

                # 2. Documentazione tecnica
                st.markdown("#### 📋 Documentazione Tecnica")

                st.info("""
                **Requisiti tecnici Ecobonus serramenti:**
                - Sostituzione finestre comprensive di infissi delimitanti verso esterno o vani non riscaldati
                - Rispetto trasmittanza termica Uw secondo zona climatica (DM 26/6/2015 - Allegato E)
                - Possono essere inclusi cassonetti (roller shutter boxes)
                - Possono essere incluse chiusure oscuranti se simultanee
                """)

                doc_serr_eco_tecnici = {}

                if is_singola_unita:
                    st.success("✅ Singola unità: APE e asseverazione **NON richiesti**. Basta dichiarazione fornitore/installatore.")
                    doc_serr_eco_tecnici["dichiarazione_fornitore_serr"] = st.checkbox(
                        "📄 Dichiarazione fornitore/installatore (con requisiti tecnici) *(obbligatorio)*",
                        key="doc_serr_eco_dich_forn"
                    )
                else:
                    st.warning("⚠️ Condominio/parti comuni: servono APE e asseverazione")
                    doc_serr_eco_tecnici["asseverazione_eco_serr"] = st.checkbox(
                        "📄 Asseverazione tecnico abilitato *(obbligatorio)*",
                        key="doc_serr_eco_assev"
                    )
                    doc_serr_eco_tecnici["ape_serr"] = st.checkbox(
                        "📄 APE (Attestato Prestazione Energetica) *(obbligatorio)*",
                        key="doc_serr_eco_ape"
                    )

                doc_serr_eco_tecnici["computo_metrico_serr"] = st.checkbox(
                    "📄 Computo metrico (dal 6 ottobre 2020) *(obbligatorio)*",
                    key="doc_serr_eco_computo"
                )
                doc_serr_eco_tecnici["schede_tecniche_eco_serr"] = st.checkbox(
                    "📄 Schede tecniche serramenti (Uw certificata) *(obbligatorio)*",
                    key="doc_serr_eco_schede"
                )

                st.session_state.checklist_eco_serr.update(doc_serr_eco_tecnici)

                # 3. Documentazione economica
                st.markdown("#### 💰 Documentazione Amministrativa")

                doc_serr_eco_economici = {
                    "fatture_eco_serr": st.checkbox("🧾 Fatture dei lavori *(obbligatorio)*", key="doc_serr_eco_fatture"),
                    "bonifici_parlanti_serr": st.checkbox("💳 Bonifici parlanti (causale specifica Ecobonus) *(obbligatorio)*", key="doc_serr_eco_bonif"),
                    "ricevute_bonifici_serr": st.checkbox("📄 Ricevute bonifici *(obbligatorio)*", key="doc_serr_eco_ric")
                }
                st.session_state.checklist_eco_serr.update(doc_serr_eco_economici)

                with st.expander("📝 Esempio causale bonifico Ecobonus"):
                    st.markdown("""
                    **Formato causale bonifico parlante Ecobonus:**

                    ```
                    Bonifico per detrazione fiscale art. 1, comma 345-347, L. 296/2006
                    Fattura n. XX/2025 del GG/MM/AAAA
                    CF/P.IVA beneficiario: XXXYYY99Z991Z999Y
                    CF ordinante: XXXYYY99Z991Z999Y
                    ```

                    ⚠️ **Attenzione:** Il bonifico deve essere di tipo "parlante" con causale specifica per Ecobonus.
                    """)

                # Progresso
                serr_eco_completati = sum(1 for v in st.session_state.checklist_eco_serr.values() if v)
                serr_eco_totali = len(st.session_state.checklist_eco_serr)
                serr_eco_progresso = serr_eco_completati / serr_eco_totali if serr_eco_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {serr_eco_completati}/{serr_eco_totali} documenti")
                st.progress(serr_eco_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Ecobonus Serramenti")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA Detrazioni Fiscali**](https://detrazionifiscali.enea.it/)
                    - [**Vademecum Serramenti ENEA**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus.html)
                    """)
                with col2:
                    st.markdown("""
                    - [**Agenzia Entrate - Ecobonus**](https://www.agenziaentrate.gov.it/portale/web/guest/schede/agevolazioni/detrazione-riqualificazione-energetica-702)
                    - [**Asseverazione Serramenti**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/asseverazioni.html)
                    """)

                st.info("""
                ℹ️ **Riepilogo Ecobonus Serramenti:**
                - Aliquota: **50%** (NOTA: inferiore al 65% di altri interventi Ecobonus)
                - Limite spesa: **60.000€** per unità immobiliare
                - Detrazione: 10 rate annuali di pari importo
                - **Singola unità**: APE e asseverazione NON richiesti (basta dichiarazione fornitore/installatore)
                - **Condominio/parti comuni**: servono APE e asseverazione
                - **Scadenza comunicazione ENEA: 90 giorni dalla fine lavori**

                **Comunicazione ENEA**:
                - Obbligatoria entro 90 giorni dalla fine lavori
                - Tramite portale https://detrazionifiscali.enea.it/
                """)

            else:  # Bonus Ristrutturazione
                st.subheader("📁 Documenti per Bonus Ristrutturazione - Serramenti")
                st.caption("Rif. Art. 16-bis TUIR - Legge di Bilancio 2025")

                # Inizializza stato checklist Bonus Ristrutt serramenti
                if "checklist_bonus_serr" not in st.session_state:
                    st.session_state.checklist_bonus_serr = {}

                st.info("""
                **IMPORTANTE:** Il Bonus Ristrutturazione NON è cumulabile con l'Ecobonus.
                Per interventi di sostituzione serramenti è richiesta la comunicazione ENEA entro 90 giorni.
                """)

                st.markdown("### 📤 Documentazione da preparare")

                # 1. Documentazione amministrativa
                st.markdown("#### 1️⃣ Documentazione amministrativa")
                doc_serr_bonus_amm = {
                    "titolo_edilizio_serr": st.checkbox("📄 Titolo edilizio (CILA, SCIA, se richiesto) *(se applicabile)*", key="doc_serr_bonus_titolo"),
                    "comunicazione_asl_serr": st.checkbox("📄 Comunicazione preventiva ASL (se richiesta) *(se applicabile)*", key="doc_serr_bonus_asl"),
                    "visura_catastale_bonus_serr": st.checkbox("🏠 Visura catastale aggiornata *(obbligatorio)*", key="doc_serr_bonus_visura")
                }
                st.session_state.checklist_bonus_serr.update(doc_serr_bonus_amm)

                # 2. Documentazione tecnica
                st.markdown("#### 2️⃣ Documentazione tecnica")
                st.caption("Comunicazione ENEA obbligatoria per risparmio energetico")

                doc_serr_bonus_tecnici = {
                    "scheda_enea_bonus_serr": st.checkbox("📋 Scheda descrittiva ENEA (obbligatoria per risparmio energetico) *(obbligatorio)*", key="doc_serr_bonus_enea"),
                    "relazione_tecnica_bonus_serr": st.checkbox("📄 Relazione tecnica con trasmittanze ante/post *(obbligatorio)*", key="doc_serr_bonus_relaz"),
                    "schede_tecniche_bonus_serr": st.checkbox("📄 Schede tecniche serramenti con Uw certificata *(obbligatorio)*", key="doc_serr_bonus_schede")
                }
                st.session_state.checklist_bonus_serr.update(doc_serr_bonus_tecnici)

                # 3. Documentazione economica
                st.markdown("#### 3️⃣ Documentazione economica")
                doc_serr_bonus_economici = {
                    "fatture_bonus_serr": st.checkbox("🧾 Fatture lavori edili *(obbligatorio)*", key="doc_serr_bonus_fatture"),
                    "bonifici_parlanti_bonus_serr": st.checkbox("💳 Bonifici parlanti (causale: Art. 16-bis TUIR) *(obbligatorio)*", key="doc_serr_bonus_bonif"),
                    "dichiarazione_redditi_serr": st.checkbox("📄 Dichiarazione dei redditi (per detrazioni) *(obbligatorio)*", key="doc_serr_bonus_730")
                }
                st.session_state.checklist_bonus_serr.update(doc_serr_bonus_economici)

                with st.expander("📝 Esempio causale bonifico Bonus Ristrutturazione"):
                    st.markdown("""
                    **Formato causale bonifico parlante Bonus Ristrutturazione:**

                    ```
                    Bonifico per detrazione fiscale art. 16-bis TUIR
                    Fattura n. XX/2025 del GG/MM/AAAA
                    CF/P.IVA beneficiario: XXXYYY99Z991Z999Y
                    CF ordinante: XXXYYY99Z991Z999Y
                    ```

                    ⚠️ **Attenzione:** Il bonifico deve riportare il riferimento all'art. 16-bis del TUIR.
                    """)

                # Progresso
                serr_bonus_completati = sum(1 for v in st.session_state.checklist_bonus_serr.values() if v)
                serr_bonus_totali = len(st.session_state.checklist_bonus_serr)
                serr_bonus_progresso = serr_bonus_completati / serr_bonus_totali if serr_bonus_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {serr_bonus_completati}/{serr_bonus_totali} documenti")
                st.progress(serr_bonus_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Bonus Ristrutturazione")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**Portale ENEA (per risparmio energetico)**](https://bonusfiscali.enea.it/)
                    - [**Agenzia Entrate - Guida Ristrutturazioni**](https://www.agenziaentrate.gov.it/portale/web/guest/schede/agevolazioni/detrazione-riqualificazione-energetica-55-65)
                    """)
                with col2:
                    st.markdown("""
                    - [**Bonus Casa 2025**](https://www.agenziaentrate.gov.it/portale/web/guest/bonus-casa)
                    - [**FAQ Bonus Ristrutturazione**](https://www.agenziaentrate.gov.it/portale/web/guest/faq)
                    """)

                st.warning("""
                ⚠️ **Aliquote Bonus Ristrutturazione:**
                - 2025-2026: 50% abitazione principale, 36% altre abitazioni
                - 2027+: 36% abitazione principale, 30% altre abitazioni
                - Limite spesa: 96.000€ per unità immobiliare
                - Detrazione massima: 48.000€ (se 50%) o 34.560€ (se 36%)
                - Recupero: 10 rate annuali di pari importo
                - **NON cumulabile con Ecobonus**
                - **Scadenza comunicazione ENEA: 90 giorni dalla fine lavori**
                """)

        elif tipo_intervento_doc == "🌤️ Schermature Solari":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.3**")

            st.info("""
            ℹ️ **NOTA**: Le schermature solari sono ammesse **SOLO al Conto Termico 3.0**.
            NON sono disponibili vademecum ENEA ufficiali per Ecobonus schermature solari.
            """)

            st.divider()

            if True:  # Solo Conto Termico disponibile
                st.subheader("📁 Documenti per Conto Termico 3.0 - Schermature Solari (Int. II.C)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.3.4")

                st.markdown("""
                ##### 📄 Documentazione Comune

                - 📝 Scheda-domanda compilata e firmata
                - 🪪 Documento identità valido del Soggetto Responsabile
                - 🏠 Visura catastale edificio
                - 📋 DSAN (Dichiarazione Sostitutiva Atto Notorietà)
                - 💳 Coordinate bancarie (IBAN)

                ##### 📝 Asseverazione Tecnica

                - ✅ **Asseverazione tecnico abilitato** (obbligatoria - Par. 12.5)
                - 📄 **Relazione tecnica di progetto** con:
                  - Descrizione dettagliata intervento
                  - Caratterizzazione ante-operam chiusure trasparenti
                  - Prestazioni post-operam componenti installati
                  - Elaborati grafici edificio (superfici oggetto intervento)
                  - Tabella riepilogativa sistemi installati per facciata con orientamento
                  - Classe prestazione solare per ciascun elemento

                ##### 📸 Documentazione Fotografica

                **Minimo 6 foto** (formato PDF):
                - 📷 Facciate oggetto intervento ANTE-operam
                - 📷 Facciate oggetto intervento POST-operam
                - 📷 Facciate in fase di lavorazione
                - 📷 Vista dettaglio schermature/pellicole installate
                - 📷 Meccanismi automatici (se installati)
                - 📷 3 foto aggiuntive intervento serramenti abbinato (II.B)

                ##### 🔬 Certificazioni Tecniche

                - 📜 **Certificazione produttore schermature**:
                  - Prestazione solare classe ≥ 3 (UNI EN 14501)
                  - Valutazione con UNI EN ISO 52022-1:2018
                - 📜 **Certificazione pellicole** (se applicabile):
                  - Fattore solare g_tot classe 3 o 4
                  - Trasmittanza vetro riferimento

                ##### 📋 APE e Diagnosi (se P ≥ 200 kW)

                - 🏠 APE post-operam (se P ≥ 200 kW)
                - 📊 Diagnosi energetica ante-operam (se P ≥ 200 kW)

                ##### 📋 APE ante+post (imprese/ETS su terziario)

                - 🏠 APE ante-operam (verifica riduzione energia ≥ 10-20%)
                - 🏠 APE post-operam (verifica riduzione energia ≥ 10-20%)

                ##### 💰 Documenti Economici

                - 🧾 Fatture intervento con dettaglio spese ammissibili
                - 💳 Bonifici/ricevute pagamento
                - 📋 Prospetto ripartizione spese (se ESCo/PPP)

                ##### 📁 Documenti da Conservare (5 anni)

                - 📄 Titolo autorizzativo/abilitativo (se richiesto)
                - 📋 Schede tecniche schermature/pellicole/automazione
                - 📜 Certificazioni produttori
                - 🏠 APE post-operam (tutti i casi)
                - 📊 Diagnosi ante-operam (se P ≥ 200 kW)

                ---

                **🔗 Link Utili:**
                - [Portaltermico GSE](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                - [Regole Applicative CT 3.0 - Par. 9.3](https://www.gse.it)

                ⚠️ **REQUISITO CRITICO**: L'intervento II.C deve essere abbinato a:
                - Sostituzione serramenti (II.B), OPPURE
                - Serramenti esistenti già conformi al DM 26/06/2015
                """)


        elif tipo_intervento_doc == "💡 Illuminazione LED":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.5.4**")

            st.info(
                "ℹ️ **Nota importante**: L'illuminazione LED rientra **SOLO nel Conto Termico 3.0**. "
                "NON è ammessa per Ecobonus né per Bonus Ristrutturazione."
            )

            st.subheader("📋 Documentazione Conto Termico 3.0")

            st.markdown("### 📄 Documentazione Comune")

            doc_comune_illum = [
                ("📝 Richiesta di concessione degli incentivi firmata digitalmente", "richiesta"),
                ("🪪 Copia documento identità del Soggetto Responsabile", "doc_id"),
                ("💳 Fatture e ricevute pagamenti (bonifici/mandati di pagamento)", "fatture"),
                ("🏠 Visura catastale edificio", "visura"),
            ]

            for label, key in doc_comune_illum:
                st.checkbox(label, key=f"doc_comune_illum_{key}")

            st.markdown("### 🔧 Documentazione Tecnica Specifica")

            st.markdown("**📌 Relazione tecnica descrittiva dell'intervento**")
            st.caption("Contenente:")

            doc_relazione_illum = [
                ("📄 Descrizione dell'intervento realizzato", "descrizione"),
                ("📐 Superficie utile illuminata (m²)", "superficie"),
                ("💡 Tipologia illuminazione (interni/esterni/mista)", "tipologia"),
                ("⚡ Potenza ante-operam e post-operam (W) con dimostrazione rispetto limite 50%", "potenza"),
                ("🔬 Caratteristiche tecniche lampade installate (efficienza lm/W, CRI)", "caratteristiche"),
                ("📊 Dimostrazione rispetto criteri illuminotecnici UNI EN 12464-1", "criteri"),
                ("💰 Calcolo spesa ammissibile con dettaglio costi unitari (€/m²)", "calcolo_spesa")
            ]

            for label, key in doc_relazione_illum:
                st.checkbox(label, key=f"doc_rel_illum_{key}")

            st.markdown("**📸 Documentazione Fotografica**")

            doc_foto_illum = [
                ("📷 Minimo 6 fotografie dell'edificio/unità immobiliare", "foto_edificio"),
                ("📷 Fotografie impianto illuminazione ante-operam", "foto_ante"),
                ("📷 Fotografie impianto illuminazione post-operam (lampade installate)", "foto_post"),
                ("🏷️ Fotografie targhe identificative apparecchi (marca, modello, dati tecnici)", "foto_targhe"),
                ("⚡ Fotografie quadri elettrici/sistemi di alimentazione", "foto_quadri"),
                ("🏢 Fotografie ambienti illuminati (per verifica criteri illuminotecnici)", "foto_ambienti")
            ]

            for label, key in doc_foto_illum:
                st.checkbox(label, key=f"doc_foto_illum_{key}")

            st.markdown("**🏭 Certificazioni Produttore/Laboratorio**")

            doc_cert_illum = [
                ("🇪🇺 Certificazione marcatura CE lampade (conformità direttive europee)", "cert_ce"),
                ("🔬 Certificazione da laboratorio accreditato per caratteristiche fotometriche", "cert_lab"),
                ("💡 Dichiarazione solido fotometrico lampade installate", "solido_fotom"),
                ("🎨 Certificazione indice resa cromatica (CRI ≥80 interni, ≥60 esterni)", "cert_cri"),
                ("⚡ Certificazione efficienza luminosa (≥80 lm/W)", "cert_efficienza"),
                ("📜 Conformità regolamenti UE 2017/1369 e direttiva 2009/125/CE (Ecodesign)", "conf_ecodesign"),
                ("📋 Schede tecniche dettagliate prodotti installati", "schede_tecniche")
            ]

            for label, key in doc_cert_illum:
                st.checkbox(label, key=f"doc_cert_illum_{key}")

            st.markdown("**📐 Documentazione Progettuale**")

            doc_prog_illum = [
                ("📐 Progetto illuminotecnico conforme a UNI EN 12464-1", "progetto_illum"),
                ("📊 Calcoli illuminotecnici (livelli illuminamento, uniformità, abbagliamento)", "calcoli_illum"),
                ("⚡ Schemi elettrici impianto illuminazione post-operam", "schemi_elettrici"),
                ("✅ Dichiarazione conformità impianto elettrico (se modificato)", "dich_conformita"),
                ("📋 Verifica conformità norme CEI vigenti", "conf_cei")
            ]

            for label, key in doc_prog_illum:
                st.checkbox(label, key=f"doc_prog_illum_{key}")

            st.markdown("**🌃 Per illuminazione esterna/pertinenze**")

            doc_esterni_illum = [
                ("🌙 Dichiarazione conformità normativa inquinamento luminoso", "conf_inquin_lum"),
                ("🏢 Dimostrazione che ambiente esterno è pertinenza dell'edificio", "pertinenza"),
                ("📐 Verifica superficie pertinenza ≤ 2× superficie edificio", "verifica_sup")
            ]

            for label, key in doc_esterni_illum:
                st.checkbox(label, key=f"doc_ext_illum_{key}")

            st.markdown("**⚙️ Per edifici con P ≥ 200 kW**")

            doc_200kw_illum = [
                ("📄 Relazione tecnica descrittiva dell'intervento (al posto di diagnosi energetica completa)", "relazione_200"),
                ("🏠 APE (Attestato Prestazione Energetica) post-operam", "ape_post_200"),
                ("📋 Documentazione stato legittimità urbanistico-edilizia edificio", "legittimita")
            ]

            for label, key in doc_200kw_illum:
                st.checkbox(label, key=f"doc_200_illum_{key}")

            st.markdown("**🏢 Per imprese/ETS economici su edifici terziario**")

            doc_terziario_illum = [
                ("🏠 APE ante-operam", "ape_ante_terz"),
                ("🏠 APE post-operam", "ape_post_terz"),
                ("📊 Dimostrazione riduzione energia primaria ≥10% (solo II.E) o ≥20% (multi-intervento)", "riduzione_energia")
            ]

            for label, key in doc_terziario_illum:
                st.checkbox(label, key=f"doc_terz_illum_{key}")

            st.markdown("**💰 Documentazione Economica**")

            doc_econ_illum = [
                ("🧾 Fatture elettroniche con dettaglio spese ammissibili", "fatture_econ"),
                ("💳 Ricevute pagamenti con evidenza beneficiario e ordinante", "ricevute"),
                ("📋 Prospetto riepilogativo spese per tipologia (fornitura, posa, adeguamenti elettrici)", "prospetto_spese"),
                ("📄 Dichiarazione IVA se costituisce un costo", "dich_iva")
            ]

            for label, key in doc_econ_illum:
                st.checkbox(label, key=f"doc_econ_illum_{key}")

            st.markdown("---")

            st.success("""
            ✅ **Timeline e scadenze**:
            - Richiesta CT 3.0: entro **60 giorni** dalla fine lavori
            - Erogazione: rata unica se ≤15.000€, altrimenti 5 rate annuali
            - Conservazione documenti: 5 anni dopo ultima erogazione
            """)

            st.warning("""
            ⚠️ **Importante**:
            - L'illuminazione LED **NON rientra** in Ecobonus né Bonus Ristrutturazione
            - Incentivo riservato a edifici esistenti con impianto climatizzazione
            - Potenza post-operam DEVE essere ≤ 50% potenza ante-operam
            - Efficienza minima 80 lm/W, CRI ≥80 (interni) o ≥60 (esterni)
            """)

        elif tipo_intervento_doc == "🏢 Building Automation":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.6.4**")

            # Selezione tipo incentivo
            incentivo_doc_ba = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus", "Bonus Ristrutturazione"],
                horizontal=True,
                key="doc_incentivo_ba"
            )

            st.divider()

            if incentivo_doc_ba == "Conto Termico 3.0":
                st.subheader("📋 Documentazione Conto Termico 3.0 - Building Automation (Int. II.F)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.6.4")

                st.markdown("### 📄 Documentazione Comune")

                doc_comune_ba = {
                    "Richiesta di concessione degli incentivi firmata digitalmente": False,
                    "Copia documento identità del Soggetto Responsabile": False,
                    "Fatture e ricevute pagamenti (bonifici/mandati di pagamento)": False,
                    "Visura catastale edificio": False,
                }

                for doc, _ in doc_comune_ba.items():
                    st.checkbox(f"☐ {doc}", key=f"doc_comune_ba_{doc}")

                st.markdown("### 🔧 Documentazione Tecnica Specifica")

                st.markdown("**📌 Relazione tecnica di progetto (OBBLIGATORIO)**")
                st.caption("Timbrata e firmata dal progettista, contenente:")

                doc_relazione_ba = [
                    "Descrizione situazione ante-operam (sistemi esistenti)",
                    "Descrizione situazione post-operam (sistema BA installato)",
                    "Superficie utile calpestabile edificio (m²)",
                    "Elenco servizi controllati dal sistema BA (riscaldamento, raffrescamento, ventilazione, ACS, illuminazione, controllo integrato)",
                    "Dimostrazione conseguimento Classe B (o superiore) secondo UNI EN ISO 52120-1",
                    "Calcolo spesa ammissibile con dettaglio costi unitari (€/m²)",
                    "Conformità a Guida CEI 205-18 per progettazione sistemi BACS"
                ]

                for doc in doc_relazione_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_rel_ba_{doc}")

                st.markdown("**📋 Schede dettagliate dei controlli di regolazione (OBBLIGATORIO)**")
                st.caption("Secondo linee guida CEI 205-18, contenenti:")

                doc_schede_ba = [
                    "Tipologia di controllo per ogni servizio (on/off, modulante, adattivo)",
                    "Funzioni implementate (termoregolazione, programmazione oraria, rilevazione presenza)",
                    "Elenco componenti installati (sensori, attuatori, controllori, interfacce)",
                    "Schema funzionale sistema di controllo",
                    "Logiche di funzionamento e interazione tra servizi (se controllo integrato)"
                ]

                for doc in doc_schede_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_schede_ba_{doc}")

                st.markdown("**⚡ Schemi elettrici (OBBLIGATORIO)**")

                doc_schemi_ba = [
                    "Schemi elettrici completi con indicazione dispositivi installati",
                    "Layout posizionamento sensori e attuatori",
                    "Schema architettura rete di comunicazione (se presente)",
                    "Dichiarazione conformità impianto elettrico (Decreto n. 37/2008)"
                ]

                for doc in doc_schemi_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_schemi_ba_{doc}")

                st.markdown("**📸 Documentazione Fotografica**")

                doc_foto_ba = [
                    "Minimo 6 fotografie dell'edificio/unità immobiliare",
                    "Fotografie quadro elettrico/centrale controllo sistema BA",
                    "Fotografie sensori installati (temperatura, radiazione, presenza)",
                    "Fotografie attuatori (valvole termostatiche, servocomandi)",
                    "Fotografie interfacce utente (display, pannelli di controllo)",
                    "Fotografie targhette identificative componenti (marca, modello)"
                ]

                for doc in doc_foto_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_foto_ba_{doc}")

                st.markdown("**🏭 Certificazioni e Conformità Normativa (OBBLIGATORIO)**")

                doc_cert_ba = [
                    "Certificazione conformità sistema BA a UNI EN ISO 52120-1 (Classe B minima)",
                    "Dichiarazione progettazione conforme a Guida CEI 205-18",
                    "Certificazioni marcatura CE componenti elettronici",
                    "Schede tecniche dettagliate tutti i componenti installati",
                    "Dichiarazione installazione da personale qualificato (Decreto n. 37/2008)",
                    "Manuale d'uso e manutenzione sistema BA"
                ]

                for doc in doc_cert_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_cert_ba_{doc}")

                st.markdown("**⚙️ Per edifici con P ≥ 200 kW**")

                doc_200kw_ba = [
                    "Relazione tecnica descrittiva dell'intervento (non diagnosi energetica completa)",
                    "APE (Attestato Prestazione Energetica) post-operam",
                    "Documentazione stato legittimità urbanistico-edilizia edificio"
                ]

                for doc in doc_200kw_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_200_ba_{doc}")

                st.markdown("**🏢 Per imprese/ETS economici su edifici terziario**")

                doc_terziario_ba = [
                    "APE ante-operam",
                    "APE post-operam",
                    "Dimostrazione riduzione energia primaria ≥10% (solo II.F) o ≥20% (multi-intervento con II.A/II.B/II.C/II.D/II.E)"
                ]

                for doc in doc_terziario_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_terz_ba_{doc}")

                st.markdown("**💰 Documentazione Economica**")

                doc_econ_ba = [
                    "Fatture elettroniche con dettaglio spese ammissibili",
                    "Ricevute pagamenti con evidenza beneficiario e ordinante",
                    "Prospetto riepilogativo spese per tipologia (fornitura componenti, progettazione, installazione, configurazione)",
                    "Dichiarazione IVA se costituisce un costo",
                    "Dimostrazione costo specifico ≤ 60 €/m²"
                ]

                for doc in doc_econ_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_econ_ba_{doc}")

                st.markdown("---")

                st.success("""
                ✅ **Timeline e scadenze**:
                - Richiesta CT 3.0: entro **60 giorni** dalla fine lavori
                - Erogazione: rata unica se ≤15.000€, altrimenti 5 rate annuali
                - Conservazione documenti: 5 anni dopo ultima erogazione
                """)

                st.warning("""
                ⚠️ **Requisiti critici**:
                - Classe efficienza BA: minimo **Classe B** (UNI EN ISO 52120-1) - Classe C e D NON ammesse
                - Conformità **OBBLIGATORIA** a UNI EN ISO 52120-1 e Guida CEI 205-18
                - Almeno UN servizio deve essere controllato dal sistema BA
                - Documentazione tecnica (relazione, schede controlli, schemi elettrici) TUTTI obbligatori
                - Costo specifico massimo: 60 €/m²
                - Incentivo massimo: 100.000€
                """)

            elif incentivo_doc_ba == "Ecobonus":
                st.subheader("📋 Documentazione Ecobonus - Building Automation")
                st.caption("Rif. Vademecum ENEA Building Automation")

                st.warning("""
                ⚠️ **ATTENZIONE - Limite SPECIALE per Building Automation**:
                - Ecobonus per Building Automation ha un limite di spesa di **15.000€ per unità immobiliare** (dal 6 ottobre 2020)
                - Questo è INFERIORE rispetto ad altri interventi Ecobonus (generalmente 60.000€)
                - Aliquota: **65%**
                - Solo edifici **residenziali** ("Solo per unità abitative")
                - Detrazione ripartita in 10 anni
                """)

                # Parametro potenza per asseverazione
                st.markdown("##### ⚙️ Parametri intervento")
                potenza_ba = st.number_input(
                    "Potenza termica utile nominale impianto (kW)",
                    min_value=1.0, max_value=500.0, value=20.0,
                    key="doc_ba_potenza",
                    help="P < 100 kW: può bastare dichiarazione produttore/installatore invece di asseverazione"
                )

                st.divider()

                st.markdown("### 📄 Documentazione Richiesta")

                # Comunicazione ENEA
                st.markdown("#### 📤 Comunicazione ENEA")
                st.checkbox("📋 Scheda descrittiva intervento con CPID (entro 90 giorni) *(obbligatorio)*", key="doc_eco_ba_cpid")

                # Documentazione tecnica
                st.markdown("#### 📋 Documentazione Tecnica")

                if potenza_ba < 100:
                    st.success(f"✅ P < 100 kW: può bastare dichiarazione produttore/installatore invece di asseverazione")
                    st.checkbox("📄 Dichiarazione produttore/installatore (alternativa ad asseverazione)", key="doc_eco_ba_dich_prod")
                    st.checkbox("📄 Asseverazione tecnico abilitato (se non si usa dichiarazione produttore)", key="doc_eco_ba_assev_opt")
                else:
                    st.warning(f"⚠️ P ≥ 100 kW: asseverazione obbligatoria")
                    st.checkbox("📄 Asseverazione tecnico abilitato *(obbligatorio)*", key="doc_eco_ba_assev")

                st.checkbox("📄 Relazione tecnica L.192/2005 *(obbligatorio)*", key="doc_eco_ba_relaz")
                st.checkbox("📄 Computo metrico (dal 6 ottobre 2020) *(obbligatorio)*", key="doc_eco_ba_computo")
                st.checkbox("📄 Schede tecniche sistema BACS installato *(obbligatorio)*", key="doc_eco_ba_schede")
                st.checkbox("📄 Certificazione Classe B EN 15232 (dal 6 ottobre 2020) *(obbligatorio)*", key="doc_eco_ba_classeb")

                # Documentazione amministrativa
                st.markdown("#### 💰 Documentazione Amministrativa")
                st.checkbox("🧾 Fatture dei lavori *(obbligatorio)*", key="doc_eco_ba_fatture")
                st.checkbox("💳 Bonifici parlanti con causale Ecobonus *(obbligatorio)*", key="doc_eco_ba_bonif")
                st.checkbox("📄 Ricevute bonifici *(obbligatorio)*", key="doc_eco_ba_ric_bonif")

                st.info("""
                ℹ️ **Requisiti tecnici**:
                - Solo unità abitative (edifici residenziali)
                - Dal 6 ottobre 2020: Classe B secondo EN 15232
                - Prima del 6 ottobre 2020: nessun limite di spesa
                - Dal 6 ottobre 2020: limite 15.000€/unità immobiliare

                **Comunicazione ENEA**:
                - Obbligatoria entro 90 giorni dalla fine lavori
                - Tramite portale https://detrazionifiscali.enea.it/
                """)

            elif incentivo_doc_ba == "Bonus Ristrutturazione":
                st.subheader("📋 Documentazione Bonus Ristrutturazione - Building Automation")

                st.info("""
                ℹ️ **Bonus Ristrutturazione per Building Automation**:
                - Aliquote: 50% (abitazione principale), 36% (altra abitazione) per 2025
                - Limite spesa: 96.000€ per unità immobiliare
                - Detrazione ripartita in 10 anni
                - Può essere cumulato con altri interventi di ristrutturazione
                """)

                st.markdown("### 📄 Documentazione Richiesta")

                doc_br_ba = [
                    "Fatture e ricevute pagamenti tracciabili (bonifico parlante con causale Bonus Ristrutturazione)",
                    "Comunicazione inizio lavori (se richiesta dal Comune)",
                    "CILA o altro titolo abilitativo edilizio (se necessario)",
                    "Schede tecniche sistema Building Automation installato",
                    "Certificazione conformità UNI EN ISO 52120-1 (Classe B minima)",
                    "Dichiarazione progettazione conforme Guida CEI 205-18",
                    "Comunicazione ENEA entro 90 giorni (intervento a efficienza energetica)"
                ]

                for doc in doc_br_ba:
                    st.checkbox(f"☐ {doc}", key=f"doc_br_ba_{doc}")

                st.warning("""
                ⚠️ **Bonifico parlante**:
                - Causale: "Bonifico per detrazione Bonus Ristrutturazione art. 16-bis DPR 917/1986"
                - Indicare: codice fiscale beneficiario, partita IVA/CF beneficiario del pagamento, riferimento fattura
                - Ritenuta d'acconto 8% trattenuta dalla banca
                """)

        elif tipo_intervento_doc == "🔀 Sistemi Ibridi":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.10**")

            st.info("""
            ℹ️ **NOTA**: I sistemi ibridi sono ammessi **SOLO al Conto Termico 3.0**.
            NON sono disponibili vademecum ENEA ufficiali per Ecobonus o Bonus Ristrutturazione sistemi ibridi.
            """)

            st.divider()

            if True:  # Solo Conto Termico disponibile
                st.subheader("📁 Documenti per Conto Termico 3.0 - Sistemi Ibridi (Int. III.B)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.10.4")

                # Parametri
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2 = st.columns(2)
                with col1:
                    tipo_sistema_doc_ibr = st.selectbox(
                        "Tipo sistema",
                        options=["Ibrido Factory Made", "Sistema Bivalente", "Add-On"],
                        key="doc_ibr_tipo"
                    )
                    potenza_pdc_doc_ibr = st.number_input(
                        "Potenza PdC (kW)",
                        min_value=1.0,
                        value=12.0,
                        key="doc_ibr_potenza_pdc"
                    )
                with col2:
                    potenza_caldaia_doc_ibr = st.number_input(
                        "Potenza caldaia (kW)",
                        min_value=1.0,
                        value=30.0,
                        key="doc_ibr_potenza_caldaia"
                    )
                    a_catalogo_ibr = st.checkbox(
                        "Sistema a Catalogo GSE",
                        value=iter_semplificato_ibr,
                        key="doc_ibr_catalogo",
                        help="Auto-compilato se prodotto selezionato dalla ricerca catalogo" if iter_semplificato_ibr else "",
                        disabled=iter_semplificato_ibr
                    )

                st.divider()

                # Inizializza checklist
                if "checklist_ct_ibr" not in st.session_state:
                    st.session_state.checklist_ct_ibr = {}

                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune")
                doc_ibr_ct_comune = {
                    "scheda_domanda_ibr": st.checkbox("📋 Scheda-domanda compilata *(obbligatorio)*", key="doc_ibr_scheda"),
                    "doc_identita_ibr": st.checkbox("🪪 Documento identità SR *(obbligatorio)*", key="doc_ibr_identita"),
                    "visura_catastale_ibr": st.checkbox("🏠 Visura catastale *(obbligatorio)*", key="doc_ibr_visura"),
                    "dsan_ibr": st.checkbox("📝 DSAN *(obbligatorio)*", key="doc_ibr_dsan"),
                    "iban_ibr": st.checkbox("🏦 IBAN *(obbligatorio)*", key="doc_ibr_iban")
                }
                st.session_state.checklist_ct_ibr.update(doc_ibr_ct_comune)

                # 2. Asseverazione/Certificazione
                st.markdown("#### 2️⃣ Asseverazione e Certificazione")

                if tipo_sistema_doc_ibr == "Ibrido Factory Made":
                    if potenza_caldaia_doc_ibr <= 35 and not a_catalogo_ibr:
                        st.info("ℹ️ P ≤ 35 kW non a Catalogo: certificazione produttore obbligatoria")
                        doc_ibr_ct_assev = {
                            "cert_produttore_ibr": st.checkbox("📄 Certificazione produttore requisiti minimi *(obbligatorio)*", key="doc_ibr_cert_prod")
                        }
                    elif potenza_caldaia_doc_ibr > 35:
                        st.warning("⚠️ P > 35 kW: asseverazione + certificazione OBBLIGATORIE")
                        doc_ibr_ct_assev = {
                            "asseverazione_ibr": st.checkbox("📄 Asseverazione tecnico abilitato *(obbligatorio)*", key="doc_ibr_assev"),
                            "cert_produttore_ibr": st.checkbox("📄 Certificazione produttore *(obbligatorio)*", key="doc_ibr_cert_prod2")
                        }
                    else:
                        st.success("✅ Sistema a Catalogo: asseverazione non obbligatoria")
                        doc_ibr_ct_assev = {}
                else:  # Bivalente o Add-On
                    st.warning("⚠️ Asseverazione tecnico OBBLIGATORIA per bivalente/add-on")
                    doc_ibr_ct_assev = {
                        "asseverazione_ibr": st.checkbox("📄 Asseverazione tecnico abilitato *(obbligatorio)*", key="doc_ibr_assev_biv"),
                        "cert_produttore_ibr": st.checkbox("📄 Certificazione produttore (se non a catalogo) *(se applicabile)*", key="doc_ibr_cert_prod_biv")
                    }

                st.session_state.checklist_ct_ibr.update(doc_ibr_ct_assev)

                # 3. Relazione tecnica
                st.markdown("#### 3️⃣ Relazione tecnica")
                potenza_tot_ibr = potenza_pdc_doc_ibr + potenza_caldaia_doc_ibr

                if potenza_tot_ibr >= 100:
                    st.warning(f"⚠️ P ≥ 100 kW: relazione tecnica OBBLIGATORIA")
                    doc_ibr_relazione = {
                        "relazione_tecnica_ibr": st.checkbox("📄 Relazione tecnica progetto con schemi funzionali *(obbligatorio)*", key="doc_ibr_relazione")
                    }
                    st.session_state.checklist_ct_ibr.update(doc_ibr_relazione)
                else:
                    st.success("✅ Relazione tecnica non obbligatoria per P < 100 kW")

                # 4. Documentazione fotografica
                st.markdown("#### 4️⃣ Documentazione fotografica")
                st.caption("Minimo 7 foto in PDF unico")

                st.warning("""
                ⚠️ **OBBLIGATORIO per sistemi ibridi:**
                - Foto targhe generatori sostituiti E installati (PdC + caldaia)
                - Foto generatori sostituiti E installati
                - Foto centrale termica ante E post-operam
                - Foto dispositivi controllo/regolazione tra PdC e caldaia
                - Foto valvole termostatiche
                """)

                doc_ibr_foto = {
                    "foto_targhe_sost_ibr": st.checkbox("📷 Targhe generatori sostituiti *(obbligatorio)*", key="doc_ibr_foto_targ_sost"),
                    "foto_targhe_inst_ibr": st.checkbox("📷 Targhe generatori installati (PdC + caldaia) *(obbligatorio)*", key="doc_ibr_foto_targ_inst"),
                    "foto_gen_sost_ibr": st.checkbox("📷 Generatori sostituiti *(obbligatorio)*", key="doc_ibr_foto_gen_sost"),
                    "foto_gen_inst_ibr": st.checkbox("📷 Generatori installati (PdC + caldaia) *(obbligatorio)*", key="doc_ibr_foto_gen_inst"),
                    "foto_centrale_ante_ibr": st.checkbox("📷 Centrale termica ANTE-operam *(obbligatorio)*", key="doc_ibr_foto_ante"),
                    "foto_centrale_post_ibr": st.checkbox("📷 Centrale termica POST-operam *(obbligatorio)*", key="doc_ibr_foto_post"),
                    "foto_controllo_ibr": st.checkbox("📷 Dispositivi controllo/regolazione PdC-caldaia *(obbligatorio)*", key="doc_ibr_foto_ctrl"),
                    "foto_valvole_ibr": st.checkbox("📷 Valvole termostatiche *(obbligatorio)*", key="doc_ibr_foto_valv")
                }
                st.session_state.checklist_ct_ibr.update(doc_ibr_foto)

                st.divider()

                # SEZIONE B: DOCUMENTI DA CONSERVARE
                st.markdown("### 📁 Documenti da conservare")
                st.caption("Da esibire in caso di controllo GSE")

                doc_ibr_conservare = {
                    "schede_tecniche_ibr": st.checkbox("📄 Schede tecniche PdC e caldaia *(obbligatorio)*", key="doc_ibr_schede"),
                    "cert_smaltimento_ibr": st.checkbox("📄 Certificato smaltimento generatore sostituito *(obbligatorio)*", key="doc_ibr_smaltimento"),
                    "dm_37_08_ibr": st.checkbox("📄 Dichiarazione conformità DM 37/08 *(obbligatorio)*", key="doc_ibr_dm37"),
                    "libretto_ibr": st.checkbox("📄 Libretto impianto aggiornato *(obbligatorio)*", key="doc_ibr_libretto"),
                    "titolo_abilitativo_ibr": st.checkbox("📄 Titolo autorizzativo (se previsto) *(se applicabile)*", key="doc_ibr_titolo")
                }

                if potenza_tot_ibr >= 200:
                    st.error("⚠️ P ≥ 200 kW: APE post + Diagnosi ante OBBLIGATORI")
                    doc_ibr_conservare_200 = {
                        "ape_post_ibr": st.checkbox("📄 APE post-operam *(obbligatorio)*", key="doc_ibr_ape"),
                        "diagnosi_ante_ibr": st.checkbox("📄 Diagnosi energetica ante-operam *(obbligatorio)*", key="doc_ibr_diagnosi")
                    }
                    doc_ibr_conservare.update(doc_ibr_conservare_200)

                if tipo_sistema_doc_ibr == "Add-On":
                    doc_ibr_conservare["doc_messa_servizio_ibr"] = st.checkbox(
                        "📄 Documentazione messa in esercizio con data installazione *(obbligatorio per add-on)*",
                        key="doc_ibr_messa_serv"
                    )

                st.session_state.checklist_ct_ibr.update(doc_ibr_conservare)

                st.divider()

                # SEZIONE C: FATTURE
                st.markdown("### 💰 Fatture e Bonifici")
                doc_ibr_pagamento = {
                    "fatture_ibr": st.checkbox("🧾 Fatture intestate al SR *(obbligatorio)*", key="doc_ibr_fatture"),
                    "bonifici_ibr": st.checkbox("💳 Bonifici con rif. DM 7/8/2025 *(obbligatorio)*", key="doc_ibr_bonifici")
                }
                st.session_state.checklist_ct_ibr.update(doc_ibr_pagamento)

                # Progresso
                ibr_ct_completati = sum(1 for v in st.session_state.checklist_ct_ibr.values() if v)
                ibr_ct_totali = len(st.session_state.checklist_ct_ibr)
                ibr_ct_progresso = ibr_ct_completati / ibr_ct_totali if ibr_ct_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {ibr_ct_completati}/{ibr_ct_totali} documenti")
                st.progress(ibr_ct_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Conto Termico Sistemi Ibridi")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                    - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole_applicative_CT3.pdf)
                    """)
                with col2:
                    st.markdown("""
                    - [**FAQ Conto Termico**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/faq)
                    - [**Catalogo Apparecchi**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/catalogo-apparecchi-domestici)
                    """)

                st.info("""
                💡 **Note importanti:**
                - Scadenza domanda: 60 giorni dalla fine lavori
                - P > 200 kW: contabilizzazione calore OBBLIGATORIA
                - Imprese/ETS: caldaie a gas NON incentivabili
                """)

        elif tipo_intervento_doc == "🔌 Ricarica Veicoli Elettrici":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.7**")

            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.7**")

            st.subheader("📁 Documenti per Conto Termico 3.0 - Infrastruttura Ricarica VE (Int. II.G)")
            st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.7.4")

            st.info("""
            ⚠️ **REQUISITO FONDAMENTALE**: L'intervento II.G è ammissibile SOLO se realizzato
            **congiuntamente** alla sostituzione di impianti di climatizzazione con pompe di calore
            elettriche (intervento III.A).

            **Incentivo**: min(30% × Spesa; Incentivo Pompa di Calore)
            - L'incentivo per la ricarica NON può mai superare l'incentivo della pompa di calore
            - 100% per PA su edifici pubblici
            """)

            # Parametri per determinare documenti necessari
            st.markdown("##### ⚙️ Parametri intervento")
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_infr_doc_ric = st.selectbox(
                    "Tipo infrastruttura",
                    options=["standard_monofase", "standard_trifase", "potenza_media", "potenza_alta_100", "potenza_alta_over100"],
                    format_func=lambda x: {
                        "standard_monofase": "Standard Monofase (7.4-22 kW)",
                        "standard_trifase": "Standard Trifase (7.4-22 kW)",
                        "potenza_media": "Potenza Media (22-50 kW)",
                        "potenza_alta_100": "Potenza Alta ≤100 kW",
                        "potenza_alta_over100": "Potenza Alta >100 kW"
                    }[x],
                    key="doc_ric_tipo_infr"
                )

                potenza_ric_doc = st.number_input(
                    "Potenza totale (kW)",
                    min_value=7.4, max_value=500.0, value=7.4,
                    key="doc_ric_potenza",
                    help="Potenza minima obbligatoria: 7.4 kW"
                )

            with col2:
                num_punti_doc_ric = st.number_input(
                    "Numero punti ricarica",
                    min_value=1, max_value=100, value=1,
                    key="doc_ric_num_punti"
                )

                ricarica_pubblica_doc = st.checkbox(
                    "Ricarica aperta al pubblico",
                    value=False,
                    key="doc_ric_pubblica",
                    help="Richiede registrazione PUN"
                )

            with col3:
                presso_pertinenza_doc = st.checkbox(
                    "Su pertinenza/parcheggio",
                    value=False,
                    key="doc_ric_pertinenza",
                    help="Richiede visura catastale"
                )

                tipo_sogg_doc_ric = st.selectbox(
                    "Tipo soggetto",
                    options=["privato", "pa", "impresa", "ets_economico"],
                    format_func=lambda x: {
                        "privato": "Privato",
                        "pa": "PA",
                        "impresa": "Impresa",
                        "ets_economico": "ETS economico"
                    }[x],
                    key="doc_ric_tipo_sogg"
                )

            st.divider()

            # Inizializza stato checklist CT ricarica VE
            if "checklist_ct_ric" not in st.session_state:
                st.session_state.checklist_ct_ric = {}

            # ==========================================
            # SEZIONE A: DOCUMENTI DA ALLEGARE ALLA RICHIESTA
            # ==========================================
            st.markdown("### 📤 Documenti da allegare alla richiesta")
            st.caption("Da caricare sul PortalTermico GSE")

            # 1. Documentazione comune
            st.markdown("#### 1️⃣ Documentazione comune a tutti gli interventi")
            st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5 e Allegato 2")

            docs_comuni_ric = [
                ("scheda_domanda_ric", "📋 Scheda-domanda compilata e sottoscritta", True),
                ("doc_identita_ric", "🪪 Documento d'identità del Soggetto Responsabile (in corso di validità)", True),
                ("visura_catastale_ric", "🏠 Visura catastale dell'immobile", True),
                ("dsan_ric", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                ("iban_ric", "🏦 Coordinate bancarie (IBAN) per accredito incentivo", True),
            ]

            for key, label, obbligatorio in docs_comuni_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label + (" *(obbligatorio)*" if obbligatorio else ""),
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # Documenti aggiuntivi condizionali
            st.markdown("**Documenti aggiuntivi (se applicabili):**")
            docs_comuni_cond_ric = [
                ("delega_ric", "📄 Delega + documento identità delegante (se si opera tramite delegato)", False),
                ("contratto_esco_ric", "📄 Contratto EPC/Servizio Energia (se tramite ESCO)", False),
                ("delibera_cond_ric", "📄 Delibera assembleare condominiale (se intervento condominiale)", False),
            ]

            for key, label, obbligatorio in docs_comuni_cond_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label + (" *(se applicabile)*" if not obbligatorio else ""),
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # 2. Documentazione tecnica specifica II.G
            st.markdown("#### 2️⃣ Documentazione tecnica infrastruttura ricarica")
            st.caption("Requisiti specifici per intervento II.G")

            docs_tecnici_ric = [
                ("dich_conformita_ric", "📄 Dichiarazione conformità DM 37/2008 (impianti elettrici) *(obbligatorio)*", True),
                ("cert_smart_ric", "📄 Certificazione dispositivi SMART (misura/trasmissione/comando) *(obbligatorio)*", True),
                ("cert_cei_61851_ric", "📄 Certificazione conformità CEI EN 61851 (Modo 3 o Modo 4) *(obbligatorio)*", True),
                ("schede_tecniche_ric", "📄 Schede tecniche dispositivi di ricarica *(obbligatorio)*", True),
                ("utenza_bt_mt_ric", "📄 Documentazione utenza bassa/media tensione (contratto/POD) *(obbligatorio)*", True),
            ]

            for key, label, obbligatorio in docs_tecnici_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label,
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # 3. Documenti condizionali (ubicazione e destinazione)
            st.markdown("#### 3️⃣ Documenti condizionali")

            if presso_pertinenza_doc:
                st.warning("⚠️ Installazione su pertinenza/parcheggio: visura catastale OBBLIGATORIA")
                if "visura_pertinenza_ric" not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric["visura_pertinenza_ric"] = False
                st.session_state.checklist_ct_ric["visura_pertinenza_ric"] = st.checkbox(
                    "🏠 Visura catastale pertinenza/parcheggio (dimostra funzionalità all'edificio) *(obbligatorio)*",
                    value=st.session_state.checklist_ct_ric["visura_pertinenza_ric"],
                    key="ct_ric_visura_pertinenza"
                )

            if ricarica_pubblica_doc:
                st.warning("⚠️ Ricarica pubblica: registrazione PUN OBBLIGATORIA")
                if "registrazione_pun_ric" not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric["registrazione_pun_ric"] = False
                st.session_state.checklist_ct_ric["registrazione_pun_ric"] = st.checkbox(
                    "📋 Attestazione registrazione Piattaforma Unica Nazionale (PUN) - DM 106/2023 *(obbligatorio)*",
                    value=st.session_state.checklist_ct_ric["registrazione_pun_ric"],
                    key="ct_ric_pun"
                )

            if tipo_sogg_doc_ric in ["impresa", "ets_economico"]:
                st.warning("⚠️ Imprese/ETS su edifici terziari: riduzione energia ≥20% OBBLIGATORIA")
                docs_impresa_ric = [
                    ("ape_ante_ric", "📄 APE ante-operam (pre-intervento combinato PdC+Ricarica) *(obbligatorio)*", True),
                    ("ape_post_ric", "📄 APE post-operam (post-intervento combinato PdC+Ricarica) *(obbligatorio)*", True),
                    ("relazione_riduzione_ric", "📄 Relazione tecnica riduzione energia primaria ≥20% *(obbligatorio)*", True),
                ]

                for key, label, obbligatorio in docs_impresa_ric:
                    if key not in st.session_state.checklist_ct_ric:
                        st.session_state.checklist_ct_ric[key] = False
                    st.session_state.checklist_ct_ric[key] = st.checkbox(
                        label,
                        value=st.session_state.checklist_ct_ric[key],
                        key=f"ct_ric_{key}"
                    )

            # 4. Documentazione combinata con Pompa di Calore
            st.markdown("#### 4️⃣ Documentazione abbinamento con Pompa di Calore (III.A)")
            st.caption("REQUISITO CRITICO: II.G realizzato congiuntamente a III.A")

            st.info("""
            ℹ️ **Installazione combinata obbligatoria**:
            - L'infrastruttura ricarica deve essere installata congiuntamente alla pompa di calore
            - La documentazione deve dimostrare il collegamento temporale e funzionale tra i due interventi
            - L'incentivo ricarica è LIMITATO all'incentivo della pompa di calore
            """)

            docs_abbinamento_ric = [
                ("doc_pdc_completa_ric", "📁 Documentazione completa Pompa di Calore (intervento III.A) *(obbligatorio)*", True),
                ("relazione_abbinamento_ric", "📄 Relazione tecnica abbinamento PdC + Ricarica VE *(consigliato)*", False),
                ("cronoprogramma_ric", "📅 Cronoprogramma lavori (dimostra contestualità interventi) *(consigliato)*", False),
            ]

            for key, label, obbligatorio in docs_abbinamento_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label,
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # ==========================================
            # SEZIONE B: DOCUMENTAZIONE FOTOGRAFICA
            # ==========================================
            st.markdown("### 📷 Documentazione fotografica")
            st.caption("Da allegare alla richiesta - Paragrafo 5.1.3 Regole Applicative")

            st.info("""
            ℹ️ **Requisiti foto**:
            - Data e ora visibili (metadata EXIF)
            - Alta risoluzione, nitide e ben illuminate
            - Inquadrature che mostrino chiaramente l'infrastruttura installata
            - Targhe dati leggibili
            """)

            docs_foto_ric = [
                ("foto_infr_installata_ric", "📸 Foto infrastruttura ricarica installata (vista generale) *(obbligatorio)*", True),
                ("foto_dispositivo_ricarica_ric", "📸 Foto dispositivo/colonnina con targa dati leggibile *(obbligatorio)*", True),
                ("foto_quadro_elettrico_ric", "📸 Foto quadro elettrico con protezioni dedicate *(obbligatorio)*", True),
                ("foto_contatore_ric", "📸 Foto contatore/POD utenza bassa/media tensione *(obbligatorio)*", True),
                ("foto_ubicazione_ric", "📸 Foto ubicazione (presso edificio/pertinenza/parcheggio) *(obbligatorio)*", True),
                ("foto_sistema_smart_ric", "📸 Foto sistema SMART (display/app di controllo) *(consigliato)*", False),
            ]

            for key, label, obbligatorio in docs_foto_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label,
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # ==========================================
            # SEZIONE C: DOCUMENTI DA CONSERVARE
            # ==========================================
            st.markdown("### 📁 Documenti da conservare per 10 anni")
            st.caption("Non allegare alla domanda - Conservare per controlli GSE")

            st.warning("""
            ⚠️ **IMPORTANTE**: Questi documenti NON vanno allegati alla richiesta, ma devono essere
            conservati per 10 anni e forniti al GSE in caso di controllo.
            """)

            docs_conservare_ric = [
                ("fatture_ric", "🧾 Fatture lavori infrastruttura ricarica (intestate al SR)", True),
                ("bonifici_ric", "💳 Bonifici con riferimento DM 7/8/2025", True),
                ("contratto_installatore_ric", "📄 Contratto con installatore/fornitore", True),
                ("garanzie_ric", "📄 Certificati garanzia dispositivi ricarica", True),
                ("manuali_ric", "📖 Manuali d'uso e manutenzione dispositivi", True),
                ("cert_ce_ric", "📄 Certificati CE dispositivi", True),
                ("libretto_impianto_ric", "📋 Libretto impianto elettrico aggiornato", True),
                ("dich_rispondenza_ric", "📄 Dichiarazione rispondenza (se richiesta)", False),
            ]

            for key, label, obbligatorio in docs_conservare_ric:
                if key not in st.session_state.checklist_ct_ric:
                    st.session_state.checklist_ct_ric[key] = False
                st.session_state.checklist_ct_ric[key] = st.checkbox(
                    label + (" *(obbligatorio conservare)*" if obbligatorio else " *(consigliato)*"),
                    value=st.session_state.checklist_ct_ric[key],
                    key=f"ct_ric_{key}"
                )

            # ==========================================
            # PROGRESSO E RIEPILOGO
            # ==========================================
            st.divider()

            ric_completati = sum(1 for v in st.session_state.checklist_ct_ric.values() if v)
            ric_totali = len(st.session_state.checklist_ct_ric)
            ric_progresso = ric_completati / ric_totali if ric_totali > 0 else 0

            st.markdown(f"**Progresso:** {ric_completati}/{ric_totali} documenti")
            st.progress(ric_progresso)

            # Calcola obbligatori mancanti
            obbligatori_keys = [
                "scheda_domanda_ric", "doc_identita_ric", "visura_catastale_ric", "dsan_ric", "iban_ric",
                "dich_conformita_ric", "cert_smart_ric", "cert_cei_61851_ric", "schede_tecniche_ric", "utenza_bt_mt_ric",
                "doc_pdc_completa_ric",
                "foto_infr_installata_ric", "foto_dispositivo_ricarica_ric", "foto_quadro_elettrico_ric",
                "foto_contatore_ric", "foto_ubicazione_ric"
            ]

            if presso_pertinenza_doc:
                obbligatori_keys.append("visura_pertinenza_ric")
            if ricarica_pubblica_doc:
                obbligatori_keys.append("registrazione_pun_ric")
            if tipo_sogg_doc_ric in ["impresa", "ets_economico"]:
                obbligatori_keys.extend(["ape_ante_ric", "ape_post_ric", "relazione_riduzione_ric"])

            obbligatori_mancanti = [k for k in obbligatori_keys if not st.session_state.checklist_ct_ric.get(k, False)]

            if obbligatori_mancanti:
                st.error(f"⚠️ Mancano {len(obbligatori_mancanti)} documenti OBBLIGATORI")
            else:
                st.success("✅ Tutti i documenti obbligatori sono stati spuntati!")

            # Link utili
            st.divider()
            st.subheader("🔗 Link Utili - Conto Termico 3.0 Ricarica VE")
            st.markdown("""
            - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
            - [**Catalogo Apparecchi GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/catalogo)
            - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative%20Conto%20Termico%203.0.pdf)
            - [**Piattaforma Unica Nazionale (PUN)**](https://www.piattaformaunicanazionale.it/) - per ricarica pubblica
            - [**Norma CEI EN 61851**](https://www.ceinorme.it) - Standard ricarica veicoli elettrici
            """)

            st.info("""
            ℹ️ **Tempistiche importanti**:
            - Richiesta incentivo: entro **60 giorni** dalla data di fine lavori
            - Conservazione documenti: **10 anni** dalla data di fine erogazione incentivo
            - Termine per controlli GSE: entro **8 anni** dalla data di fine erogazione
            """)

            st.warning("""
            ⚠️ **Limiti incentivo Ricarica VE (Tabella 22)**:
            - Standard monofase (7.4-22 kW): max **2.400 €/punto**
            - Standard trifase (7.4-22 kW): max **8.400 €/punto**
            - Potenza media (22-50 kW): max **1.200 €/kW**
            - Potenza alta ≤100 kW: max **60.000 €/infrastruttura**
            - Potenza alta >100 kW: max **110.000 €/infrastruttura**

            **LIMITE CRITICO**: I_ricarica ≤ I_pompa_calore (incentivo ricarica non può superare incentivo PdC)
            """)

        elif tipo_intervento_doc == "🚿 Scaldacqua PdC":
            st.write("Documentazione secondo **Regole Applicative CT 3.0 - Paragrafo 9.13**")

            # Selezione tipo incentivo
            incentivo_doc_sc = st.radio(
                "Seleziona l'incentivo:",
                options=["Conto Termico 3.0", "Ecobonus"],
                horizontal=True,
                key="doc_incentivo_sc"
            )

            st.divider()

            if incentivo_doc_sc == "Conto Termico 3.0":
                st.subheader("📁 Documenti per Conto Termico 3.0 - Scaldacqua PdC (Int. III.E)")
                st.caption("Rif. Regole Applicative CT 3.0 - Paragrafo 9.13.4")

                st.info("""
                ⚠️ **REQUISITO CRITICO**: L'intervento deve essere SOSTITUZIONE di scaldacqua esistente
                (elettrico o a gas). Non sono ammesse nuove installazioni.

                **Incentivo**: 40% della spesa sostenuta (100% per PA su edifici pubblici)
                - Limiti max da Tabella 38 in base a classe energetica e capacità accumulo
                """)

                # Parametri per determinare documenti necessari
                st.markdown("##### ⚙️ Parametri intervento")
                col1, col2, col3 = st.columns(3)
                with col1:
                    classe_doc_sc = st.selectbox(
                        "Classe energetica",
                        options=["A", "A+", "A++", "A+++"],
                        key="doc_sc_classe"
                    )
                    potenza_doc_sc = st.number_input(
                        "Potenza termica (kW)",
                        min_value=0.5, max_value=50.0, value=2.5,
                        key="doc_sc_potenza",
                        help="Soglia asseverazione: 35 kW"
                    )

                with col2:
                    capacita_doc_sc = st.number_input(
                        "Capacità accumulo (litri)",
                        min_value=50, max_value=1000, value=200,
                        key="doc_sc_capacita",
                        help="Soglia incentivo massimo: 150 litri"
                    )
                    a_catalogo_doc_sc = st.checkbox(
                        "A Catalogo GSE 2D",
                        value=False,
                        key="doc_sc_catalogo"
                    )

                with col3:
                    incentivo_stimato_sc = st.number_input(
                        "Incentivo stimato (€)",
                        min_value=0.0, max_value=5000.0, value=1000.0,
                        key="doc_sc_incentivo_stim",
                        help="Per verificare soglia 3.500€"
                    )

                st.divider()

                # Inizializza stato checklist CT scaldacqua
                if "checklist_ct_sc" not in st.session_state:
                    st.session_state.checklist_ct_sc = {}

                # ==========================================
                # SEZIONE A: DOCUMENTI DA ALLEGARE ALLA RICHIESTA
                # ==========================================
                st.markdown("### 📤 Documenti da allegare alla richiesta")
                st.caption("Da caricare sul PortalTermico GSE")

                # 1. Documentazione comune
                st.markdown("#### 1️⃣ Documentazione comune a tutti gli interventi")
                st.caption("Rif. Regole Applicative CT 3.0 - Cap. 5 e Allegato 2")

                docs_comuni_sc = [
                    ("scheda_domanda_sc", "📋 Scheda-domanda compilata e sottoscritta", True),
                    ("doc_identita_sc", "🪪 Documento d'identità del Soggetto Responsabile", True),
                    ("visura_catastale_sc", "🏠 Visura catastale dell'immobile", True),
                    ("dsan_sc", "📝 Dichiarazione sostitutiva atto notorietà (DSAN)", True),
                    ("iban_sc", "🏦 Coordinate bancarie (IBAN) per accredito incentivo", True),
                ]

                for key, label, obbligatorio in docs_comuni_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # Documenti aggiuntivi condizionali
                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                docs_comuni_cond_sc = [
                    ("delega_sc", "📄 Delega + documento identità delegante", False),
                    ("contratto_esco_sc", "📄 Contratto EPC/Servizio Energia (se tramite ESCO)", False),
                    ("delibera_cond_sc", "📄 Delibera assembleare condominiale", False),
                ]

                for key, label, obbligatorio in docs_comuni_cond_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label + (" *(se applicabile)*" if not obbligatorio else ""),
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # 2. Asseverazione / Certificazione produttore
                st.markdown("#### 2️⃣ Asseverazione e Certificazione")

                if a_catalogo_doc_sc:
                    st.success("✅ Scaldacqua a Catalogo GSE: asseverazione NON obbligatoria")
                    assev_note_sc = "Non richiesta (a Catalogo)"
                elif potenza_doc_sc <= 35:
                    if incentivo_stimato_sc > 3500:
                        assev_note_sc = "Certificazione produttore obbligatoria (P ≤ 35 kW, incentivo > 3.500€)"
                        st.info("ℹ️ P ≤ 35 kW non a Catalogo: asseverazione non obbligatoria, ma serve certificazione produttore per incentivo > 3.500€")
                    else:
                        assev_note_sc = "Certificazione produttore consigliata"
                        st.info("ℹ️ P ≤ 35 kW, incentivo ≤ 3.500€: asseverazione e certificazione non obbligatorie")
                elif potenza_doc_sc > 35:
                    assev_note_sc = "Asseverazione tecnico + certificazione produttore OBBLIGATORIE"
                    st.warning("⚠️ P > 35 kW: asseverazione tecnico abilitato + certificazione produttore obbligatorie")

                docs_assev_sc = []
                if potenza_doc_sc > 35 or (potenza_doc_sc <= 35 and incentivo_stimato_sc > 3500 and not a_catalogo_doc_sc):
                    docs_assev_sc.append(("cert_produttore_sc", "📄 Certificazione produttore (classe energetica, requisiti Reg. UE 812/2013)", True))
                if potenza_doc_sc > 35 and not a_catalogo_doc_sc:
                    docs_assev_sc.append(("asseverazione_sc", "📄 Asseverazione tecnico abilitato (par. 12.5 Regole)", True))

                for key, label, obbligatorio in docs_assev_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label + (" *(obbligatorio)*" if obbligatorio else ""),
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # 3. Documentazione fotografica
                st.markdown("#### 3️⃣ Documentazione fotografica")
                st.caption("Rif. Paragrafo 5.1.3 Regole Applicative")

                st.info("""
                ℹ️ **Requisiti foto**:
                - Data e ora visibili (metadata EXIF)
                - Alta risoluzione, nitide e ben illuminate
                - Vista dettaglio e vista d'insieme
                - Targhe dati leggibili
                """)

                docs_foto_sc = [
                    ("foto_scaldacqua_vecchio_det", "📸 Foto dettaglio scaldacqua sostituito (targa dati) *(obbligatorio)*", True),
                    ("foto_scaldacqua_vecchio_ins", "📸 Foto d'insieme scaldacqua sostituito *(obbligatorio)*", True),
                    ("foto_scaldacqua_nuovo_det", "📸 Foto dettaglio scaldacqua PdC installato (targa dati) *(obbligatorio)*", True),
                    ("foto_scaldacqua_nuovo_ins", "📸 Foto d'insieme scaldacqua PdC installato *(obbligatorio)*", True),
                ]

                for key, label, obbligatorio in docs_foto_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label,
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # ==========================================
                # SEZIONE B: DOCUMENTI DA CONSERVARE
                # ==========================================
                st.markdown("### 📁 Documenti da conservare per 10 anni")
                st.caption("Non allegare alla domanda - Conservare per controlli GSE")

                st.warning("""
                ⚠️ **IMPORTANTE**: Questi documenti NON vanno allegati alla richiesta, ma devono essere
                conservati per 10 anni e forniti al GSE in caso di controllo.
                """)

                docs_conservare_sc = [
                    ("scheda_tecnica_sc", "📄 Scheda tecnica produttore scaldacqua PdC *(obbligatorio)*", True),
                    ("cert_smaltimento_sc", "♻️ Certificato smaltimento scaldacqua sostituito *(obbligatorio)*", True),
                    ("dich_conformita_sc", "📄 Dichiarazione conformità DM 37/08 *(obbligatorio)*", True),
                    ("libretto_impianto_sc", "📋 Libretto d'impianto *(obbligatorio)*", True),
                    ("schema_funzionale_sc", "📐 Schema funzionale d'impianto *(obbligatorio)*", True),
                    ("titolo_abilitativo_sc", "📄 Titolo autorizzativo/abilitativo (se previsto) *(se applicabile)*", False),
                ]

                for key, label, obbligatorio in docs_conservare_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label,
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # Documenti speciali per potenza edificio ≥ 200 kW
                st.markdown("**Documenti per potenza edificio ≥ 200 kW (se applicabile):**")
                docs_potenza_sc = [
                    ("diagnosi_ante_sc", "📊 Diagnosi energetica ante-operam (se P ≥ 200 kW) *(se applicabile)*", False),
                    ("ape_post_sc", "📄 APE post-operam (se P ≥ 200 kW) *(se applicabile)*", False),
                ]

                for key, label, obbligatorio in docs_potenza_sc:
                    if key not in st.session_state.checklist_ct_sc:
                        st.session_state.checklist_ct_sc[key] = False
                    st.session_state.checklist_ct_sc[key] = st.checkbox(
                        label,
                        value=st.session_state.checklist_ct_sc[key],
                        key=f"ct_sc_{key}"
                    )

                # ==========================================
                # PROGRESSO E RIEPILOGO
                # ==========================================
                st.divider()

                sc_completati = sum(1 for v in st.session_state.checklist_ct_sc.values() if v)
                sc_totali = len(st.session_state.checklist_ct_sc)
                sc_progresso = sc_completati / sc_totali if sc_totali > 0 else 0

                st.markdown(f"**Progresso:** {sc_completati}/{sc_totali} documenti")
                st.progress(sc_progresso)

                # Calcola obbligatori mancanti
                obbligatori_keys_sc = [
                    "scheda_domanda_sc", "doc_identita_sc", "visura_catastale_sc", "dsan_sc", "iban_sc",
                    "foto_scaldacqua_vecchio_det", "foto_scaldacqua_vecchio_ins",
                    "foto_scaldacqua_nuovo_det", "foto_scaldacqua_nuovo_ins",
                    "scheda_tecnica_sc", "cert_smaltimento_sc", "dich_conformita_sc",
                    "libretto_impianto_sc", "schema_funzionale_sc"
                ]

                if potenza_doc_sc > 35 or (potenza_doc_sc <= 35 and incentivo_stimato_sc > 3500 and not a_catalogo_doc_sc):
                    obbligatori_keys_sc.append("cert_produttore_sc")
                if potenza_doc_sc > 35 and not a_catalogo_doc_sc:
                    obbligatori_keys_sc.append("asseverazione_sc")

                obbligatori_mancanti_sc = [k for k in obbligatori_keys_sc if not st.session_state.checklist_ct_sc.get(k, False)]

                if obbligatori_mancanti_sc:
                    st.error(f"⚠️ Mancano {len(obbligatori_mancanti_sc)} documenti OBBLIGATORI")
                else:
                    st.success("✅ Tutti i documenti obbligatori sono stati spuntati!")

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Conto Termico 3.0 Scaldacqua PdC")
                st.markdown("""
                - [**PortalTermico GSE**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico)
                - [**Catalogo 2D - Scaldacqua PdC**](https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico/catalogo)
                - [**Regole Applicative CT 3.0**](https://www.gse.it/documenti_site/Documenti%20GSE/Servizi%20per%20te/CONTO%20TERMICO/Regole%20applicative%20Conto%20Termico%203.0.pdf)
                - [**Regolamento UE 812/2013**](https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32013R0812) - Etichettatura energetica
                """)

                st.info("""
                ℹ️ **Tempistiche importanti**:
                - Richiesta incentivo: entro **60 giorni** dalla data di fine lavori
                - Conservazione documenti: **10 anni** dalla data di fine erogazione incentivo
                - Termine per controlli GSE: entro **8 anni** dalla data di fine erogazione
                """)

                st.warning("""
                ⚠️ **Limiti incentivo Scaldacqua PdC (Tabella 38)**:
                - Classe A, ≤150 litri: max **500 €**
                - Classe A, >150 litri: max **1.100 €**
                - Classe A+, ≤150 litri: max **700 €**
                - Classe A+, >150 litri: max **1.500 €**

                **Percentuale**: 40% della spesa (100% per PA su edifici pubblici)
                **Erogazione**: 2 rate annuali (rata unica se ≤ 15.000€)
                """)

            elif incentivo_doc_sc == "Ecobonus":
                st.subheader("📁 Documenti per Ecobonus - Scaldacqua PdC")
                st.caption("Rif. D.L. 63/2013 - Ecobonus")

                if "checklist_eco_sc" not in st.session_state:
                    st.session_state.checklist_eco_sc = {}

                st.info("""
                **Aliquote 2025:**
                - 50% per abitazione principale
                - 36% per altre abitazioni
                - Limite: 30.000€ di detrazione
                - Recupero: 10 anni
                """)

                st.markdown("### 📤 Documentazione da preparare")

                # 1. Comunicazione ENEA
                st.markdown("#### 1️⃣ Comunicazione ENEA (OBBLIGATORIA)")
                doc_eco_sc_enea = {
                    "cpid_enea_sc": st.checkbox("📋 Scheda CPID ENEA (entro 90 gg dalla fine lavori) *(obbligatorio)*", key="doc_eco_sc_cpid")
                }
                st.session_state.checklist_eco_sc.update(doc_eco_sc_enea)

                st.warning("""
                ⚠️ **Scadenza ENEA**: Entro **90 giorni** dalla fine lavori
                - Portale: https://detrazionifiscali.enea.it/
                """)

                # 2. Documentazione tecnica
                st.markdown("#### 2️⃣ Documentazione tecnica")
                doc_eco_sc_tecnici = {
                    "schede_tecniche_eco_sc": st.checkbox("📄 Schede tecniche scaldacqua PdC (COP, classe energetica) *(obbligatorio)*", key="doc_eco_sc_schede"),
                    "assev_dich_eco_sc": st.checkbox("📄 Asseverazione tecnico O dichiarazione produttore (P ≤ 100 kW) *(obbligatorio)*", key="doc_eco_sc_assev"),
                    "dich_conf_eco_sc": st.checkbox("📄 Dichiarazione conformità DM 37/08 *(obbligatorio)*", key="doc_eco_sc_conf"),
                    "libretto_eco_sc": st.checkbox("📋 Libretto impianto *(obbligatorio)*", key="doc_eco_sc_libretto")
                }
                st.session_state.checklist_eco_sc.update(doc_eco_sc_tecnici)

                st.info("""
                ℹ️ **Requisiti tecnici**:
                - COP > 2,6 secondo D.Lgs. 28/2011
                - Valori minimi Allegato F del D.M. 6.08.2020
                - Classe energetica minima A (Reg. UE 812/2013)
                """)

                # 3. Documentazione amministrativa
                st.markdown("#### 3️⃣ Documentazione amministrativa")
                doc_eco_sc_amm = {
                    "fatture_eco_sc": st.checkbox("🧾 Fatture lavori (dettagliate) *(obbligatorio)*", key="doc_eco_sc_fatture"),
                    "bonifici_eco_sc": st.checkbox("💳 Bonifici parlanti (causale detrazione fiscale) *(obbligatorio)*", key="doc_eco_sc_bonifici"),
                    "visura_eco_sc": st.checkbox("🏠 Visura catastale *(obbligatorio)*", key="doc_eco_sc_visura")
                }
                st.session_state.checklist_eco_sc.update(doc_eco_sc_amm)

                st.markdown("**Documenti aggiuntivi (se applicabili):**")
                doc_eco_sc_cond = {
                    "delibera_eco_sc": st.checkbox("📄 Delibera assembleare (se condominio) *(se applicabile)*", key="doc_eco_sc_delib"),
                    "consenso_eco_sc": st.checkbox("📄 Consenso proprietario (se detentore) *(se applicabile)*", key="doc_eco_sc_consenso")
                }
                st.session_state.checklist_eco_sc.update(doc_eco_sc_cond)

                st.warning("""
                ⚠️ **Bonifico parlante**:
                - Causale: "Detrazione fiscale Ecobonus art. X DL 63/2013"
                - Indicare: codice fiscale beneficiario, P.IVA destinatario, estremi fattura
                - Ritenuta d'acconto 8% trattenuta dalla banca
                """)

                # Progresso
                eco_sc_completati = sum(1 for v in st.session_state.checklist_eco_sc.values() if v)
                eco_sc_totali = len(st.session_state.checklist_eco_sc)
                eco_sc_progresso = eco_sc_completati / eco_sc_totali if eco_sc_totali > 0 else 0

                st.divider()
                st.markdown(f"**Progresso:** {eco_sc_completati}/{eco_sc_totali} documenti")
                st.progress(eco_sc_progresso)

                # Link utili
                st.divider()
                st.subheader("🔗 Link Utili - Ecobonus Scaldacqua PdC")
                st.markdown("""
                - [**Portale ENEA**](https://detrazionifiscali.enea.it/)
                - [**Vademecum ENEA Pompe di Calore**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/vademecum.html)
                - [**FAQ Ecobonus**](https://www.efficienzaenergetica.enea.it/detrazioni-fiscali/ecobonus/faq.html)
                """)

                st.info("""
                ℹ️ **Note importanti**:
                - Detrazione spalmata in 10 rate annuali di pari importo
                - Possibilità di cessione del credito o sconto in fattura (verificare normativa vigente)
                - Conservare tutta la documentazione per 10 anni
                """)

        # Sezione esportazione checklist
        st.divider()
        st.subheader("📥 Esporta Checklist")

        if st.button("📄 Genera Checklist PDF-ready", use_container_width=True):
            # Genera HTML checklist basata sulla struttura attuale
            if tipo_intervento_doc == "🔆 FV Combinato":
                # Checklist per FV Combinato
                if incentivo_doc_fv == "Conto Termico 3.0":
                    checklist = st.session_state.get("checklist_ct_fv", {})
                    titolo = "Conto Termico 3.0 - FV Combinato (par. 9.8.4)"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                    docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda"))
                    docs.append(("Documento d'identità del SR", "doc_identita"))
                    docs.append(("Visura catastale dell'immobile", "visura_catastale"))
                    docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan"))
                    docs.append(("Coordinate bancarie (IBAN)", "iban"))
                    if "delega" in checklist:
                        docs.append(("Delega + doc. identità delegante", "delega"))
                    if "contratto_esco" in checklist:
                        docs.append(("Contratto EPC/Servizio Energia", "contratto_esco"))
                    if "delibera_cond" in checklist:
                        docs.append(("Delibera assembleare condominiale", "delibera_cond"))

                    docs.append(("📤 DOCUMENTAZIONE SPECIFICA FV", None))
                    docs.append(("Asseverazione tecnico abilitato", "asseverazione_fv"))
                    docs.append(("Certificazione produttore requisiti minimi", "cert_produttore_fv"))
                    docs.append(("Modello unico connessione", "modello_unico"))
                    docs.append(("Relazione calcolo fabbisogno", "relazione_fabbisogno"))
                    docs.append(("Report PVGIS producibilità", "report_pvgis"))
                    docs.append(("Bollette elettriche annuali", "bollette_elettriche"))
                    docs.append(("Fatture combustibili", "fatture_combustibili"))
                    docs.append(("Elenco numeri serie moduli/inverter", "elenco_seriali"))
                    docs.append(("Schede tecniche moduli FV", "schede_tecniche_moduli"))
                    if "relazione_tecnica_fv" in checklist:
                        docs.append(("Relazione tecnica progetto (P > 20 kW)", "relazione_tecnica_fv"))
                    if "schema_unifilare" in checklist:
                        docs.append(("Schema unifilare as-built (P > 20 kW)", "schema_unifilare"))
                    if "dichiarazione_registro" in checklist:
                        docs.append(("Dichiarazione Registro Tecnologie FV", "dichiarazione_registro"))

                    docs.append(("📷 DOCUMENTAZIONE FOTOGRAFICA", None))
                    docs.append(("Foto moduli FV installati", "foto_moduli_installati"))
                    docs.append(("Foto targhe moduli", "foto_targhe_moduli"))
                    docs.append(("Foto inverter con targa", "foto_inverter"))
                    docs.append(("Foto quadro elettrico", "foto_quadro_elettrico"))
                    docs.append(("Foto contatore bidirezionale", "foto_contatore"))
                    docs.append(("Foto copertura post-operam", "foto_copertura_post"))
                    if "foto_accumulo" in checklist:
                        docs.append(("Foto sistema di accumulo", "foto_accumulo"))
                    if "foto_targa_accumulo" in checklist:
                        docs.append(("Foto targa accumulo", "foto_targa_accumulo"))

                    docs.append(("📁 DOCUMENTI DA CONSERVARE", None))
                    docs.append(("Schede tecniche moduli FV", "scheda_tecnica_moduli"))
                    docs.append(("Scheda tecnica inverter", "scheda_tecnica_inverter"))
                    if "scheda_tecnica_accumulo" in checklist:
                        docs.append(("Scheda tecnica accumulo", "scheda_tecnica_accumulo"))
                    docs.append(("Dichiarazione conformità DM 37/08", "dm_37_08_fv"))
                    docs.append(("Garanzia moduli (10 anni/90%)", "garanzia_moduli"))
                    docs.append(("Garanzia inverter", "garanzia_inverter"))
                    if "garanzia_accumulo" in checklist:
                        docs.append(("Garanzia accumulo", "garanzia_accumulo"))
                    docs.append(("Contratto connessione rete", "connessione_rete"))

                    docs.append(("💰 FATTURE E BONIFICI", None))
                    docs.append(("Fatture intestate al SR", "fatture_fv"))
                    docs.append(("Bonifici con rif. DM 7/8/2025", "bonifici_fv"))

                    docs.append(("🌡️ PDC ABBINATA (III.A)", None))
                    docs.append(("Documentazione PdC completa", "doc_pdc_completa"))

                else:  # Bonus Ristrutturazione FV
                    checklist = st.session_state.get("checklist_bonus_fv", {})
                    titolo = "Bonus Ristrutturazione - Fotovoltaico"

                    docs = []
                    docs.append(("📤 COMUNICAZIONE ENEA", None))
                    docs.append(("Comunicazione ENEA con CPID", "cpid_enea_fv"))

                    docs.append(("📋 DOCUMENTAZIONE TECNICA", None))
                    docs.append(("Schede tecniche moduli e inverter", "schede_tecniche_fv"))
                    if "scheda_accumulo_bonus" in checklist:
                        docs.append(("Scheda tecnica accumulo", "scheda_accumulo_bonus"))
                    docs.append(("Dichiarazione conformità DM 37/08", "dm_37_08_bonus"))
                    docs.append(("Regolamento esercizio / Contratto GSE", "regolamento_esercizio"))
                    docs.append(("Preventivo Enel / Modello unico", "preventivo_accettato"))

                    docs.append(("💰 DOCUMENTAZIONE AMMINISTRATIVA", None))
                    docs.append(("Fatture con dettaglio spese", "fatture_bonus_fv"))
                    docs.append(("Bonifici parlanti art. 16-bis", "bonifici_bonus_fv"))
                    if "titolo_abilitativo_fv" in checklist:
                        docs.append(("Titolo abilitativo (CILA/SCIA)", "titolo_abilitativo_fv"))

            elif tipo_intervento_doc == "☀️ Solare Termico":
                # Checklist per Solare Termico CT
                checklist = st.session_state.get("checklist_ct_solare", {})
                titolo = "Conto Termico 3.0 - Solare Termico (par. 9.12.4)"

                docs = []
                docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda"))
                docs.append(("Documento d'identità del SR", "doc_identita"))
                docs.append(("Visura catastale dell'immobile", "visura_catastale"))
                docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan"))
                docs.append(("Coordinate bancarie (IBAN)", "iban"))
                if "delega" in checklist:
                    docs.append(("Delega + doc. identità delegante", "delega"))
                if "contratto_esco" in checklist:
                    docs.append(("Contratto EPC/Servizio Energia", "contratto_esco"))
                if "delibera_cond" in checklist:
                    docs.append(("Delibera assembleare condominiale", "delibera_cond"))

                docs.append(("📤 CERTIFICAZIONI", None))
                docs.append(("Certificazione Solar Keymark", "solar_keymark"))
                docs.append(("Test report Solar Keymark", "test_report"))
                if "approv_enea" in checklist:
                    docs.append(("Approvazione ENEA (concentrazione)", "approv_enea"))
                if "asseverazione" in checklist:
                    docs.append(("Asseverazione tecnico (Sl > 50 m²)", "asseverazione"))
                if "relazione_tecnica" in checklist:
                    docs.append(("Relazione tecnica progetto", "relazione_tecnica"))
                if "schemi_funzionali" in checklist:
                    docs.append(("Schemi funzionali impianto", "schemi_funzionali"))

                docs.append(("📷 DOCUMENTAZIONE FOTOGRAFICA", None))
                docs.append(("Foto targhe collettori installati", "foto_targhe_collettori"))
                docs.append(("Foto collettori installati", "foto_collettori"))
                docs.append(("Foto accumulo con targhetta", "foto_accumulo"))
                docs.append(("Foto centralina/regolazione", "foto_centralina"))
                docs.append(("Foto copertura ante-operam", "foto_copertura_ante"))
                docs.append(("Foto copertura post-operam", "foto_copertura_post"))

                docs.append(("📁 DOCUMENTI DA CONSERVARE", None))
                docs.append(("Scheda tecnica collettori", "scheda_tecnica"))
                docs.append(("Dichiarazione conformità DM 37/08", "dm_37_08"))
                docs.append(("Certificato smaltimento (se sostituzione)", "cert_smaltimento"))

                docs.append(("💰 FATTURE E BONIFICI", None))
                docs.append(("Fatture intestate al SR", "fatture"))
                docs.append(("Bonifici con rif. DM 7/8/2025", "bonifici"))

            elif tipo_intervento_doc == "🌡️ Pompe di Calore":
                if incentivo_doc == "Conto Termico 3.0":
                    checklist = st.session_state.get("checklist_ct_pdc", {})
                    titolo = "Conto Termico 3.0 - Pompe di Calore (par. 9.9.4)"

                    # Costruisci lista documenti dinamicamente
                    docs = []

                    # Documentazione comune dettagliata
                    docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                    docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda"))
                    docs.append(("Documento d'identità del SR", "doc_identita"))
                    docs.append(("Visura catastale dell'immobile", "visura_catastale"))
                    docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan"))
                    docs.append(("Coordinate bancarie (IBAN)", "iban"))
                    if "delega" in checklist:
                        docs.append(("Delega + doc. identità delegante", "delega"))
                    if "contratto_esco" in checklist:
                        docs.append(("Contratto EPC/Servizio Energia", "contratto_esco"))
                    if "delibera_cond" in checklist:
                        docs.append(("Delibera assembleare condominiale", "delibera_cond"))
    
                    # Certificazioni/Asseverazioni
                    docs.append(("📤 CERTIFICAZIONI E ASSEVERAZIONI", None))
                    if "cert_produttore" in checklist:
                        docs.append(("Certificazione produttore", "cert_produttore"))
                    if "asseverazione" in checklist:
                        docs.append(("Asseverazione tecnico abilitato", "asseverazione"))
                    if "relazione_tecnica" in checklist:
                        docs.append(("Relazione tecnica progetto (P ≥ 100 kW)", "relazione_tecnica"))
                    if "relazione_carichi" in checklist:
                        docs.append(("Relazione carichi termici (ACS/processo)", "relazione_carichi"))
    
                    # Foto
                    docs.append(("📷 DOCUMENTAZIONE FOTOGRAFICA", None))
                    docs.append(("Foto targhe generatori sostituiti", "foto_targhe_sostituiti"))
                    docs.append(("Foto targhe generatori installati", "foto_targhe_installati"))
                    docs.append(("Foto generatori sostituiti", "foto_generatori_sostituiti"))
                    docs.append(("Foto generatori installati", "foto_generatori_installati"))
                    docs.append(("Foto centrale termica ante-operam", "foto_centrale_ante"))
                    docs.append(("Foto centrale termica post-operam", "foto_centrale_post"))
                    docs.append(("Foto valvole termostatiche", "foto_valvole"))
    
                    # Documenti da conservare
                    docs.append(("📁 DOCUMENTI DA CONSERVARE", None))
                    docs.append(("Scheda tecnica produttore", "scheda_tecnica"))
                    docs.append(("Certificato smaltimento generatore", "cert_smaltimento"))
                    docs.append(("Dichiarazione conformità DM 37/08", "dm_37_08"))
                    if "libretto" in checklist:
                        docs.append(("Libretto impianto (P > 10 kW)", "libretto"))
                    if "diagnosi_ante" in checklist:
                        docs.append(("Diagnosi energetica ante-operam (P ≥ 200 kW)", "diagnosi_ante"))
                    if "ape_post" in checklist:
                        docs.append(("APE post-operam (P ≥ 200 kW)", "ape_post"))
                    if "relazione_35_100" in checklist:
                        docs.append(("Relazione tecnica (P 35-100 kW)", "relazione_35_100"))
                    if "schema_sonde" in checklist:
                        docs.append(("Schema sonde geotermiche", "schema_sonde"))
                    docs.append(("Titolo autorizzativo/abilitativo", "titolo_abilitativo"))
                    docs.append(("Iscrizione catasto regionale", "catasto_regionale"))
    
                    # Fatture e bonifici
                    docs.append(("💰 FATTURE E BONIFICI", None))
                    docs.append(("Fatture intestate al SR", "fatture"))
                    docs.append(("Bonifici con rif. DM 7/8/2025", "bonifici"))

                elif incentivo_doc == "Ecobonus":
                    checklist = st.session_state.get("checklist_eco_pdc", {})
                    titolo = "Ecobonus - Pompe di Calore"
                    docs = [
                        ("📤 COMUNICAZIONE ENEA", None),
                        ("Scheda CPID ENEA (entro 90 gg)", "cpid_enea"),
                        ("📋 DOCUMENTAZIONE TECNICA", None),
                        ("Schede tecniche prodotti", "schede_tecniche"),
                        ("Dichiarazione conformità DM 37/08", "dm_37_08"),
                    ]
                    if "libretto" in checklist:
                        docs.append(("Libretto impianto (P > 10 kW)", "libretto"))
                    docs.append(("APE post-intervento", "ape"))
                    docs.append(("💰 DOCUMENTAZIONE AMMINISTRATIVA", None))
                    docs.append(("Fatture dettagliate", "fatture"))
                    docs.append(("Bonifici parlanti", "bonifici"))
                    if "asseverazione" in checklist:
                        docs.insert(3, ("Asseverazione tecnico (P > 100 kW)", "asseverazione"))
                    if "delibera" in checklist:
                        docs.append(("Delibera assembleare", "delibera"))
                    if "consenso" in checklist:
                        docs.append(("Consenso proprietario", "consenso"))

            elif tipo_intervento_doc == "🪟 Serramenti":
                if incentivo_doc_serr == "Conto Termico 3.0":
                    checklist = st.session_state.get("checklist_ct_serr", {})
                    titolo = "Conto Termico 3.0 - Serramenti (Int. II.B)"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                    docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda_serr"))
                    docs.append(("Documento d'identità del SR", "doc_identita_serr"))
                    docs.append(("Visura catastale dell'immobile", "visura_catastale_serr"))
                    docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan_serr"))
                    docs.append(("Coordinate bancarie (IBAN)", "iban_serr"))
                    if "delega_serr" in checklist:
                        docs.append(("Delega + doc. identità delegante", "delega_serr"))
                    if "contratto_esco_serr" in checklist:
                        docs.append(("Contratto EPC/Servizio Energia", "contratto_esco_serr"))
                    if "delibera_cond_serr" in checklist:
                        docs.append(("Delibera assembleare", "delibera_cond_serr"))

                    docs.append(("📤 ASSEVERAZIONE TECNICA", None))
                    docs.append(("Asseverazione tecnico abilitato (par. 12.5)", "asseverazione_serr"))

                    docs.append(("📷 DOCUMENTAZIONE FOTOGRAFICA", None))
                    docs.append(("Foto serramenti ANTE-operam", "foto_serr_ante"))
                    docs.append(("Foto serramenti POST-operam", "foto_serr_post"))
                    docs.append(("Foto durante lavori", "foto_serr_lavori"))
                    docs.append(("Foto sistemi termoregolazione (OBBLIG.)", "foto_termoregolazione"))

                    docs.append(("📤 RELAZIONE TECNICA", None))
                    docs.append(("Relazione tecnica trasmittanze/superfici", "relazione_tecnica_serr"))

                    if "diagnosi_ante_serr" in checklist or "ape_post_serr" in checklist:
                        docs.append(("📤 DOCUMENTAZIONE ENERGETICA (P≥200kW)", None))
                        if "diagnosi_ante_serr" in checklist:
                            docs.append(("Diagnosi energetica ante-operam", "diagnosi_ante_serr"))
                        if "ape_post_serr" in checklist:
                            docs.append(("APE post-operam", "ape_post_serr"))

                    docs.append(("📁 DOCUMENTI DA CONSERVARE", None))
                    docs.append(("Schede tecniche serramenti (Uw)", "schede_tecniche_serr"))
                    if "schede_termo_serr" in checklist:
                        docs.append(("Schede tecniche termoregolazione", "schede_termo_serr"))
                    if "dm_37_08_serr" in checklist:
                        docs.append(("Dichiarazione conformità DM 37/08", "dm_37_08_serr"))
                    if "titolo_abilitativo_serr" in checklist:
                        docs.append(("Titolo autorizzativo", "titolo_abilitativo_serr"))

                    docs.append(("💰 FATTURE E BONIFICI", None))
                    docs.append(("Fatture intestate al SR", "fatture_serr"))
                    docs.append(("Bonifici con rif. DM 7/8/2025", "bonifici_serr"))

                elif incentivo_doc_serr == "Ecobonus":
                    checklist = st.session_state.get("checklist_eco_serr", {})
                    titolo = "Ecobonus - Serramenti"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE TECNICA", None))
                    docs.append(("Scheda descrittiva ENEA (entro 90gg)", "scheda_descrittiva_serr"))
                    docs.append(("Asseverazione tecnico (Legge 10/91)", "asseverazione_eco_serr"))
                    docs.append(("Relazione tecnica trasmittanze ante/post", "relazione_trasmittanza_serr"))
                    docs.append(("Schede tecniche serramenti (Uw)", "schede_tecniche_eco_serr"))

                    docs.append(("💰 DOCUMENTAZIONE ECONOMICA", None))
                    docs.append(("Fatture dei lavori", "fatture_eco_serr"))
                    docs.append(("Bonifici parlanti (causale Ecobonus)", "bonifici_parlanti_serr"))
                    docs.append(("Ricevute bonifici", "ricevute_bonifici_serr"))

                else:  # Bonus Ristrutturazione
                    checklist = st.session_state.get("checklist_bonus_serr", {})
                    titolo = "Bonus Ristrutturazione - Serramenti"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE AMMINISTRATIVA", None))
                    docs.append(("Titolo edilizio (CILA/SCIA)", "titolo_edilizio_serr"))
                    docs.append(("Comunicazione preventiva ASL", "comunicazione_asl_serr"))
                    docs.append(("Visura catastale aggiornata", "visura_catastale_bonus_serr"))

                    docs.append(("📤 DOCUMENTAZIONE TECNICA", None))
                    docs.append(("Scheda ENEA risparmio energetico", "scheda_enea_bonus_serr"))
                    docs.append(("Relazione tecnica trasmittanze", "relazione_tecnica_bonus_serr"))
                    docs.append(("Schede tecniche serramenti (Uw)", "schede_tecniche_bonus_serr"))

                    docs.append(("💰 DOCUMENTAZIONE ECONOMICA", None))
                    docs.append(("Fatture lavori edili", "fatture_bonus_serr"))
                    docs.append(("Bonifici parlanti (Art. 16-bis)", "bonifici_parlanti_bonus_serr"))
                    docs.append(("Dichiarazione redditi", "dichiarazione_redditi_serr"))

            elif tipo_intervento_doc == "🏠 Isolamento Termico":
                if incentivo_doc_iso == "Conto Termico 3.0":
                    checklist = st.session_state.get("checklist_ct_iso", {})
                    titolo = "Conto Termico 3.0 - Isolamento Termico (Int. II.A)"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                    docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda_iso"))
                    docs.append(("Documento d'identità del SR", "doc_identita_iso"))
                    docs.append(("Visura catastale dell'immobile", "visura_catastale_iso"))
                    docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan_iso"))
                    docs.append(("Coordinate bancarie (IBAN)", "iban_iso"))

                    docs.append(("📤 DOCUMENTAZIONE TECNICA - ISOLAMENTO", None))
                    docs.append(("Diagnosi energetica o APE ante-operam", "diagnosi_ape_ante_iso"))
                    docs.append(("APE post-intervento (obbligatorio)", "ape_post_iso"))
                    docs.append(("Asseverazione tecnico abilitato", "asseverazione_iso"))
                    docs.append(("Certificazioni materiali isolanti (λ)", "cert_materiali_iso"))
                    docs.append(("Relazione tecnica intervento", "relazione_tecnica_iso"))

                    docs.append(("💰 DOCUMENTAZIONE ECONOMICA", None))
                    docs.append(("Computo metrico estimativo", "computo_metrico_iso"))
                    docs.append(("Fatture quietanzate lavori", "fatture_iso"))
                    docs.append(("Bonifici/ricevute pagamento", "bonifici_iso"))

                elif incentivo_doc_iso == "Ecobonus":
                    checklist = st.session_state.get("checklist_eco_iso", {})
                    titolo = "Ecobonus - Coibentazione Involucro"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE TECNICA", None))
                    docs.append(("Scheda descrittiva intervento ENEA", "scheda_descrittiva_iso"))
                    docs.append(("Asseverazione tecnico (Legge 10/91)", "asseverazione_eco_iso"))
                    docs.append(("APE post-intervento", "ape_post_eco_iso"))
                    docs.append(("Relazione tecnica trasmittanza", "relazione_trasmittanza_iso"))
                    docs.append(("Certificazioni materiali isolanti", "cert_materiali_eco_iso"))

                    docs.append(("💰 DOCUMENTAZIONE ECONOMICA", None))
                    docs.append(("Fatture dei lavori", "fatture_eco_iso"))
                    docs.append(("Bonifici parlanti (Ecobonus)", "bonifici_parlanti_iso"))
                    docs.append(("Ricevute bonifici", "ricevute_bonifici_iso"))

                else:  # Bonus Ristrutturazione
                    checklist = st.session_state.get("checklist_bonus_iso", {})
                    titolo = "Bonus Ristrutturazione - Isolamento Termico"

                    docs = []
                    docs.append(("📤 DOCUMENTAZIONE AMMINISTRATIVA", None))
                    docs.append(("Titolo edilizio (CILA/SCIA)", "titolo_edilizio_iso"))
                    docs.append(("Comunicazione preventiva ASL", "comunicazione_asl_iso"))
                    docs.append(("Visura catastale aggiornata", "visura_catastale_bonus_iso"))

                    docs.append(("📤 DOCUMENTAZIONE TECNICA", None))
                    docs.append(("Scheda descrittiva ENEA", "scheda_enea_bonus_iso"))
                    docs.append(("Relazione tecnica intervento", "relazione_tecnica_bonus_iso"))
                    docs.append(("APE post-intervento", "ape_bonus_iso"))

                    docs.append(("💰 DOCUMENTAZIONE ECONOMICA", None))
                    docs.append(("Fatture lavori edili", "fatture_bonus_iso"))
                    docs.append(("Bonifici parlanti (Art. 16-bis)", "bonifici_parlanti_bonus_iso"))
                    docs.append(("Dichiarazione redditi", "dichiarazione_redditi_iso"))

            elif tipo_intervento_doc == "🔌 Ricarica Veicoli Elettrici":
                checklist = st.session_state.get("checklist_ct_ric", {})
                titolo = "Conto Termico 3.0 - Ricarica Veicoli Elettrici (Int. II.G)"

                docs = []
                docs.append(("📤 DOCUMENTAZIONE COMUNE", None))
                docs.append(("Scheda-domanda compilata e sottoscritta", "scheda_domanda_ric"))
                docs.append(("Documento d'identità del SR", "doc_identita_ric"))
                docs.append(("Visura catastale dell'immobile", "visura_catastale_ric"))
                docs.append(("Dichiarazione sostitutiva (DSAN)", "dsan_ric"))
                docs.append(("Coordinate bancarie (IBAN)", "iban_ric"))
                if "delega_ric" in checklist:
                    docs.append(("Delega + doc. identità delegante", "delega_ric"))
                if "contratto_esco_ric" in checklist:
                    docs.append(("Contratto EPC/Servizio Energia", "contratto_esco_ric"))
                if "delibera_cond_ric" in checklist:
                    docs.append(("Delibera assembleare condominiale", "delibera_cond_ric"))

                docs.append(("📤 DOCUMENTAZIONE TECNICA RICARICA VE", None))
                docs.append(("Dichiarazione conformità DM 37/2008", "dich_conformita_ric"))
                docs.append(("Certificazione dispositivi SMART", "cert_smart_ric"))
                docs.append(("Certificazione CEI EN 61851", "cert_cei_61851_ric"))
                docs.append(("Schede tecniche dispositivi ricarica", "schede_tecniche_ric"))
                docs.append(("Documentazione utenza BT/MT", "utenza_bt_mt_ric"))
                if "visura_pertinenza_ric" in checklist:
                    docs.append(("Visura catastale pertinenza/parcheggio", "visura_pertinenza_ric"))
                if "registrazione_pun_ric" in checklist:
                    docs.append(("Attestazione registrazione PUN", "registrazione_pun_ric"))
                if "ape_ante_ric" in checklist:
                    docs.append(("APE ante-operam (imprese/ETS)", "ape_ante_ric"))
                if "ape_post_ric" in checklist:
                    docs.append(("APE post-operam (imprese/ETS)", "ape_post_ric"))
                if "relazione_riduzione_ric" in checklist:
                    docs.append(("Relazione riduzione energia ≥20%", "relazione_riduzione_ric"))

                docs.append(("📤 ABBINAMENTO POMPA DI CALORE", None))
                docs.append(("Documentazione completa PdC (III.A)", "doc_pdc_completa_ric"))
                if "relazione_abbinamento_ric" in checklist:
                    docs.append(("Relazione tecnica abbinamento PdC+Ricarica", "relazione_abbinamento_ric"))
                if "cronoprogramma_ric" in checklist:
                    docs.append(("Cronoprogramma lavori", "cronoprogramma_ric"))

                docs.append(("📷 DOCUMENTAZIONE FOTOGRAFICA", None))
                docs.append(("Foto infrastruttura installata", "foto_infr_installata_ric"))
                docs.append(("Foto dispositivo con targa dati", "foto_dispositivo_ricarica_ric"))
                docs.append(("Foto quadro elettrico", "foto_quadro_elettrico_ric"))
                docs.append(("Foto contatore/POD", "foto_contatore_ric"))
                docs.append(("Foto ubicazione", "foto_ubicazione_ric"))
                if "foto_sistema_smart_ric" in checklist:
                    docs.append(("Foto sistema SMART", "foto_sistema_smart_ric"))

                docs.append(("📁 DOCUMENTI DA CONSERVARE", None))
                docs.append(("Fatture lavori ricarica VE", "fatture_ric"))
                docs.append(("Bonifici con rif. DM 7/8/2025", "bonifici_ric"))
                docs.append(("Contratto installatore/fornitore", "contratto_installatore_ric"))
                docs.append(("Garanzie dispositivi ricarica", "garanzie_ric"))
                docs.append(("Manuali d'uso e manutenzione", "manuali_ric"))
                docs.append(("Certificati CE dispositivi", "cert_ce_ric"))
                docs.append(("Libretto impianto elettrico", "libretto_impianto_ric"))
                if "dich_rispondenza_ric" in checklist:
                    docs.append(("Dichiarazione rispondenza", "dich_rispondenza_ric"))

            # Genera HTML
            html_checklist = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Checklist Documenti - {titolo}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; max-width: 900px; margin: 0 auto; }}
        h1 {{ color: #1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 10px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .date {{ color: #666; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #1E88E5; color: white; }}
        .section {{ background-color: #e3f2fd; font-weight: bold; }}
        .check {{ font-size: 1.3em; text-align: center; width: 60px; }}
        .ok {{ color: #2E7D32; }}
        .pending {{ color: #F57C00; }}
        .note {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; }}
        .footer {{ text-align: center; color: #666; font-size: 0.8em; margin-top: 40px; }}
        @media print {{ body {{ padding: 20px; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Checklist Documenti</h1>
        <h2>{titolo}</h2>
        <p class="date">Generato il {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    </div>

    <table>
        <tr>
            <th style="width: 65%;">Documento</th>
            <th class="check">Stato</th>
            <th style="width: 20%;">Note</th>
        </tr>
"""
            count_ok = 0
            count_tot = 0

            for doc_nome, doc_key in docs:
                if doc_key is None:
                    # Riga sezione
                    html_checklist += f"""
        <tr class="section">
            <td colspan="3">{doc_nome}</td>
        </tr>
"""
                else:
                    count_tot += 1
                    is_ok = checklist.get(doc_key, False)
                    if is_ok:
                        count_ok += 1
                    stato = "✅" if is_ok else "⬜"
                    stato_class = "ok" if is_ok else "pending"
                    html_checklist += f"""
        <tr>
            <td>{doc_nome}</td>
            <td class="check {stato_class}">{stato}</td>
            <td></td>
        </tr>
"""

            pct = (count_ok / count_tot * 100) if count_tot > 0 else 0
            html_checklist += f"""
    </table>

    <p><strong>Progresso:</strong> {count_ok}/{count_tot} documenti completati ({pct:.0f}%)</p>

    <div class="note">
        <strong>📌 Riferimenti normativi:</strong><br>
"""
            # Riferimenti normativi in base al tipo intervento
            if tipo_intervento_doc == "🔆 FV Combinato":
                if incentivo_doc_fv == "Conto Termico 3.0":
                    html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.8.4 (FV Combinato II.H)<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a><br>
        • PVGIS: <a href="https://re.jrc.ec.europa.eu/pvg_tools/it/">re.jrc.ec.europa.eu/pvg_tools</a>
"""
                else:
                    html_checklist += """
        • Art. 16-bis DPR 917/86 - Bonus Ristrutturazione<br>
        • Limite spesa: 96.000€ per unità immobiliare<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori<br>
        • Portale: <a href="https://bonusfiscali.enea.it/">bonusfiscali.enea.it</a>
"""
            elif tipo_intervento_doc == "☀️ Solare Termico":
                html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.12.4 (Solare Termico III.D)<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a><br>
        • Solar Keymark: <a href="https://www.solarkeymark.org/database/">solarkeymark.org/database</a>
"""
            elif tipo_intervento_doc == "🌡️ Pompe di Calore" and incentivo_doc == "Conto Termico 3.0":
                html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.9.4 (Pompe di Calore III.A)<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a>
"""
            elif tipo_intervento_doc == "🌡️ Pompe di Calore" and incentivo_doc == "Ecobonus":
                html_checklist += """
        • D.L. 63/2013 - Ecobonus<br>
        • Vademecum ENEA<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori<br>
        • Portale: <a href="https://detrazionifiscali.enea.it/">detrazionifiscali.enea.it</a>
"""
            elif tipo_intervento_doc == "🪟 Serramenti":
                if incentivo_doc_serr == "Conto Termico 3.0":
                    html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.2.4 (Serramenti II.B)<br>
        • <strong>OBBLIGATORIO:</strong> Termoregolazione installata o già presente<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a>
"""
                elif incentivo_doc_serr == "Ecobonus":
                    html_checklist += """
        • D.L. 63/2013 - Ecobonus - Serramenti<br>
        • Vademecum ENEA Serramenti<br>
        • Rispetto trasmittanza Uw secondo zona climatica<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori<br>
        • Portale: <a href="https://detrazionifiscali.enea.it/">detrazionifiscali.enea.it</a>
"""
                else:  # Bonus Ristrutturazione
                    html_checklist += """
        • Art. 16-bis DPR 917/86 - Bonus Ristrutturazione - Serramenti<br>
        • NON cumulabile con Ecobonus<br>
        • Limite spesa: 96.000€ per unità immobiliare<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori<br>
        • Portale ENEA: <a href="https://bonusfiscali.enea.it/">bonusfiscali.enea.it</a>
"""
            elif tipo_intervento_doc == "🏠 Isolamento Termico":
                if incentivo_doc_iso == "Conto Termico 3.0":
                    html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.1 (Isolamento Termico II.A)<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a>
"""
                elif incentivo_doc_iso == "Ecobonus":
                    html_checklist += """
        • D.L. 63/2013 - Ecobonus - Coibentazione Involucro<br>
        • Vademecum ENEA Coibentazione<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori<br>
        • Portale: <a href="https://detrazionifiscali.enea.it/">detrazionifiscali.enea.it</a>
"""
                else:  # Bonus Ristrutturazione
                    html_checklist += """
        • Art. 16-bis DPR 917/86 - Bonus Ristrutturazione<br>
        • Limite spesa: 96.000€ per unità immobiliare<br>
        • Scadenza ENEA: 90 giorni dalla fine lavori (per risparmio energetico)<br>
        • Portale ENEA: <a href="https://bonusfiscali.enea.it/">bonusfiscali.enea.it</a>
"""
            elif tipo_intervento_doc == "🔌 Ricarica Veicoli Elettrici":
                html_checklist += """
        • D.M. 7 agosto 2025 - Conto Termico 3.0<br>
        • Regole Applicative CT 3.0 - Paragrafo 9.7 (Ricarica VE II.G)<br>
        • <strong>OBBLIGATORIO:</strong> Abbinamento con Pompa di Calore (III.A)<br>
        • <strong>LIMITE:</strong> Incentivo ricarica ≤ Incentivo pompa di calore<br>
        • Scadenza: 60 giorni dalla fine lavori<br>
        • Portale: <a href="https://www.gse.it/servizi-per-te/efficienza-energetica/conto-termico">gse.it/conto-termico</a><br>
        • PUN: <a href="https://www.piattaformaunicanazionale.it/">piattaformaunicanazionale.it</a> (per ricarica pubblica)<br>
        • CEI EN 61851: Standard ricarica veicoli elettrici
"""
            html_checklist += """
    </div>

    <div class="footer">
        <p>Energy Incentive Manager - Checklist Documenti</p>
        <p>Stampare con Ctrl+P o Cmd+P per salvare come PDF</p>
    </div>
</body>
</html>
"""
            # Download link
            st.markdown(
                get_download_link(html_checklist, f"checklist_{titolo.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')}_{datetime.now().strftime('%Y%m%d')}.html"),
                unsafe_allow_html=True
            )
            st.success("✅ Checklist generata! Apri il file HTML e stampa come PDF.")

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        Energy Incentive Manager v2.0 | Conto Termico 3.0 (DM 7/8/2025) ed Ecobonus
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
