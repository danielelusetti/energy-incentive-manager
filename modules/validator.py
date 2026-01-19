"""
Modulo Gatekeeper per la validazione dell'ammissibilità agli incentivi.

Questo modulo verifica i requisiti di ammissibilità per:
- Conto Termico 3.0 (DM 7/8/2025)
- Ecobonus (D.L. 63/2013, Legge di Bilancio 2025)

Esegue controlli preliminari PRIMA del calcolo per:
- Verificare requisiti tecnici minimi
- Identificare esclusioni normative
- Segnalare documentazione mancante
- Suggerire alternative in caso di non ammissibilità

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field
from datetime import date

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RequisitoValidazione:
    """Singolo requisito di validazione."""
    codice: str
    descrizione: str
    superato: bool
    obbligatorio: bool = True
    dettaglio: str = ""
    riferimento_normativo: str = ""


@dataclass
class RisultatoValidazione:
    """Risultato completo della validazione."""
    ammissibile: bool
    incentivo: Literal["conto_termico", "ecobonus", "entrambi"]
    requisiti: list[RequisitoValidazione]
    errori_bloccanti: list[str]
    warning: list[str]
    suggerimenti: list[str]
    punteggio_completezza: float  # 0-100%
    documentazione_richiesta: list[str]


# ============================================================================
# COSTANTI E REGOLE
# ============================================================================

# Requisiti minimi SCOP/COP per Conto Termico 3.0 (da pompe_calore_ci.json)
SCOP_MINIMI_CT = {
    "aria_aria": {
        "split_multisplit": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42},
        "vrf_vrv": 3.50,
        "rooftop": 3.20,
    },
    "aria_acqua": {
        "standard": 2.825,
        "bassa_temperatura": 3.20,
    },
    "acqua_acqua": {
        "standard": 2.95,
        "bassa_temperatura": 3.325,
    },
    "acqua_aria": 3.625,
    "geotermiche_salamoia_aria": {
        "lte_12kw": {"GWP_gt_150": 3.80, "GWP_lte_150": 3.42},
        "gt_12kw": 3.625,
    },
    "geotermiche_salamoia_acqua": {
        "standard": 2.825,
        "bassa_temperatura": 3.20,
    },
}

# Zone climatiche italiane valide
ZONE_CLIMATICHE_VALIDE = ["A", "B", "C", "D", "E", "F"]

# Categorie catastali ammissibili CT 3.0 (Tabella 1 - Allegato 1)
CATEGORIE_CATASTALI_CT = {
    "ammesse": {
        "A": ["A/1", "A/2", "A/3", "A/4", "A/5", "A/6", "A/7", "A/8", "A/9", "A/11"],
        "B": ["B/1", "B/2", "B/3", "B/4", "B/5", "B/6", "B/7", "B/8"],
        "C": ["C/1", "C/2", "C/3", "C/4", "C/5", "C/6", "C/7"],
        "D": ["D/1", "D/2", "D/3", "D/4", "D/5", "D/6", "D/7", "D/8", "D/9", "D/10"],
        "E": ["E/1", "E/2", "E/3", "E/4", "E/5", "E/6", "E/7", "E/8", "E/9"],
    },
    "escluse": {
        "A/10": "Uffici e studi privati",
        "F": "Entita' urbane (tutte le categorie F)",
    },
    "note": "Le categorie A/10 e gruppo F sono escluse dal Conto Termico 3.0"
}

# Requisiti minimi SPER per pompe di calore a GAS (Tabella 5 - Allegato 1)
SPER_MINIMI_CT = {
    "aria_aria": 1.33,  # Reg. 2281/2016
    "acqua_aria": 1.33,  # Reg. 2281/2016
    "salamoia_aria": 1.33,  # Reg. 2281/2016
    "acqua_acqua": {
        "standard": 1.13,  # Reg. 813/2013
        "bassa_temperatura": 1.28,  # Reg. 813/2013
    },
    "salamoia_acqua": 1.28,  # Reg. 813/2013
}

# Tipi di intervento Ecobonus ammessi dal 2025
INTERVENTI_ECOBONUS_2025 = [
    "pompe_di_calore",
    "sistemi_ibridi",
    "solare_termico",
    "coibentazione_involucro",
    "serramenti_infissi",
    "schermature_solari",
    "riqualificazione_globale",
    "microcogeneratori",
    "generatori_biomassa",
    "building_automation",
    "scaldacqua_pdc",
    "collettori_solari",
    "fotovoltaico",           # Bonus Ristrutturazione (non Ecobonus puro)
    "fotovoltaico_accumulo",  # FV + sistema di accumulo
]

# Interventi ESCLUSI dall'Ecobonus dal 2025
INTERVENTI_ESCLUSI_ECOBONUS_2025 = [
    "caldaie_condensazione",
    "caldaie_condensazione_classe_A",
    "caldaie_condensazione_classe_A_evoluta",
    "caldaie_uniche_combustibili_fossili",
]

# Aliquote Ecobonus per anno e tipo abitazione (Legge di Bilancio 2025/2026)
# Fonte: ecobonus.pdf - Tabella riassuntiva pag. 6
ALIQUOTE_ECOBONUS = {
    2024: {
        "abitazione_principale": {
            "default": 0.50,  # Serramenti, infissi, schermature, caldaie biomassa
            "riqualificazione_globale": 0.65,
            "pompe_di_calore": 0.65,
            "sistemi_ibridi": 0.65,
            "coibentazione_involucro": 0.65,
            "collettori_solari": 0.65,
            "microcogeneratori": 0.65,
            "building_automation": 0.65,
            "scaldacqua_pdc": 0.65,
        },
        "altra_abitazione": {
            "default": 0.50,
            "riqualificazione_globale": 0.65,
            "pompe_di_calore": 0.65,
            "sistemi_ibridi": 0.65,
            "coibentazione_involucro": 0.65,
            "collettori_solari": 0.65,
            "microcogeneratori": 0.65,
            "building_automation": 0.65,
            "scaldacqua_pdc": 0.65,
        },
    },
    2025: {
        "abitazione_principale": {"default": 0.50},  # 50% per prima casa
        "altra_abitazione": {"default": 0.36},       # 36% per altre
    },
    2026: {
        "abitazione_principale": {"default": 0.50},  # 50% per prima casa
        "altra_abitazione": {"default": 0.36},       # 36% per altre
    },
    2027: {
        "abitazione_principale": {"default": 0.36},  # Riduzione ulteriore
        "altra_abitazione": {"default": 0.30},       # 30% per altre
    },
    2028: {
        "abitazione_principale": {"default": 0.36},
        "altra_abitazione": {"default": 0.30},
    },
}

# Limiti di detrazione/spesa Ecobonus per tipo intervento
# Fonte: ecobonus.pdf - Tabella riassuntiva pag. 6-7
# ATTENZIONE: limite_tipo indica se il valore e' la DETRAZIONE massima o la SPESA massima
LIMITI_ECOBONUS = {
    "schermature_solari": {
        "limite_euro": 60000,
        "limite_tipo": "detrazione_massima",
        "nota": "Acquisto e posa schermature solari",
    },
    "serramenti_infissi": {
        "limite_euro": 60000,
        "limite_tipo": "detrazione_massima",
        "nota": "Acquisto e posa finestre comprensive di infissi",
    },
    "pompe_di_calore": {
        "limite_euro": 30000,
        "limite_tipo": "detrazione_massima",
        "nota": "Sostituzione impianti con PdC ad alta efficienza o geotermiche",
    },
    "scaldacqua_pdc": {
        "limite_euro": 30000,
        "limite_tipo": "detrazione_massima",
        "nota": "Sostituzione scaldacqua tradizionali con scaldacqua a PdC",
    },
    "generatori_biomassa": {
        "limite_euro": 30000,
        "limite_tipo": "detrazione_massima",
        "nota": "Generatori di calore alimentati da biomasse combustibili",
    },
    "coibentazione_involucro": {
        "limite_euro": 60000,
        "limite_tipo": "detrazione_massima",
        "nota": "Strutture opache verticali/orizzontali (pareti, coperture, pavimenti)",
    },
    "collettori_solari": {
        "limite_euro": 60000,
        "limite_tipo": "detrazione_massima",
        "nota": "Pannelli solari per produzione acqua calda",
    },
    "riqualificazione_globale": {
        "limite_euro": 100000,
        "limite_tipo": "detrazione_massima",
        "nota": "Interventi di riqualificazione energetica globale",
    },
    "microcogeneratori": {
        "limite_euro": 100000,
        "limite_tipo": "detrazione_massima",
        "nota": "Acquisto e posa micro-cogeneratori in sostituzione impianti",
    },
    "building_automation": {
        "limite_euro": 15000,
        "limite_tipo": "detrazione_massima",
        "nota": "Dispositivi multimediali per controllo remoto impianti",
    },
    "sistemi_ibridi": {
        "limite_euro": 30000,
        "limite_tipo": "detrazione_massima",
        "nota": "PdC integrata con caldaia condensazione (factory-made DM 6/08/2020)",
    },
    # Interventi condominiali
    "condominio_involucro_25pct": {
        "limite_euro": 40000,
        "limite_tipo": "spesa_massima",
        "moltiplicatore": "unita_immobiliari",
        "nota": "Coibentazione involucro >25% sup. disperdente - per unita' immobiliare",
    },
    "condominio_involucro_qualita": {
        "limite_euro": 40000,
        "limite_tipo": "spesa_massima",
        "moltiplicatore": "unita_immobiliari",
        "nota": "Coibentazione >25% + qualita' media involucro - per unita' immobiliare",
    },
    "condominio_sismabonus": {
        "limite_euro": 136000,
        "limite_tipo": "spesa_massima",
        "moltiplicatore": "unita_immobiliari",
        "nota": "Interventi congiunti riduzione rischio sismico + riqualificazione energetica",
    },
}

# Documentazione richiesta per tipo incentivo
DOCUMENTAZIONE_CT = [
    "Scheda tecnica generatore",
    "Dichiarazione di conformità DM 37/08",
    "Fatture e bonifici",
    "Libretto impianto aggiornato",
    "Documentazione fotografica ante/post",
    "Comunicazione ASL (se prevista)",
    "Asseverazione tecnico (se P > 100 kW)",
]

DOCUMENTAZIONE_ECOBONUS = [
    "Scheda descrittiva ENEA (entro 90 gg)",
    "Asseverazione tecnico abilitato",
    "APE post-intervento",
    "Fatture con indicazione spese",
    "Bonifici parlanti",
    "Dichiarazione di conformità DM 37/08",
    "Delibera assembleare (se condominio)",
]

# Documentazione richiesta per Solare Termico (par. 9.12.4)
DOCUMENTAZIONE_SOLARE_TERMICO = [
    "Certificazione Solar Keymark (o approvazione ENEA per concentrazione)",
    "Test report Solar Keymark con producibilità",
    "Fatture e bonifici",
    "Documentazione fotografica (6 foto minimo)",
    "Certificazione produttore requisiti minimi",
    "Dichiarazione conformità DM 37/08",
    "Libretto impianto",
    "Garanzia collettori (min 5 anni) e bollitori (min 5 anni)",
    "Garanzia accessori (min 2 anni)",
]

DOCUMENTAZIONE_SOLARE_TERMICO_GT_50M2 = [
    "Asseverazione tecnico abilitato",
    "Relazione tecnica di progetto firmata",
    "Schemi funzionali impianto",
]

# Documentazione richiesta per Fotovoltaico Combinato II.H (par. 9.8.4)
DOCUMENTAZIONE_FV_COMBINATO = [
    "Documentazione comune a tutte le tipologie di interventi",
    "Asseverazione tecnico abilitato (requisiti tecnici)",
    "Certificazione produttore dei requisiti minimi",
    "Copia modello unico connessione (o preventivo accettato)",
    "Relazione calcolo fabbisogno elettrico ed equivalente",
    "Report PVGIS (https://re.jrc.ec.europa.eu/pvg_tools/it/)",
    "Bollette elettriche rappresentative consumi annuali",
    "Fatture acquisto combustibili (per fabbisogno termico)",
    "Elenco numeri serie moduli e inverter",
    "Dichiarazione conformità impianto (DM 37/08)",
    "Documentazione fotografica (6 foto minimo)",
    "Schede tecniche moduli fotovoltaici",
]

DOCUMENTAZIONE_FV_GT_20KW = [
    "Relazione tecnica di progetto firmata",
    "Schema elettrico unifilare as-built",
]

# Documentazione richiesta per Generatori a Biomassa (III.C) - par. 9.9.5
DOCUMENTAZIONE_BIOMASSA = [
    "Certificazione classe ambientale 5 stelle (DM 186/2017)",
    "Certificazione UNI EN 303-5 classe 5 (per caldaie)",
    "Certificazione UNI EN 16510:2023 (per stufe/termocamini)",
    "Scheda tecnica generatore con rendimento e emissioni",
    "Dichiarazione conformità DM 37/08",
    "Fatture e bonifici",
    "Documentazione fotografica ante/post (6 foto minimo)",
    "Libretto impianto aggiornato",
    "Certificato installazione sistema accumulo (≥20 dm³/kW per caldaie)",
]

DOCUMENTAZIONE_BIOMASSA_GT_35KW = [
    "Asseverazione tecnico abilitato",
    "Relazione tecnica di progetto firmata",
    "Schema funzionale impianto",
]

DOCUMENTAZIONE_BIOMASSA_GT_500KW = [
    "Documentazione sistema abbattimento particolato",
    "Certificazione rendimento ≥ 92%",
]

# Requisiti tecnici biomassa (par. 9.9.5 e Allegato 1)
REQUISITI_BIOMASSA = {
    "caldaia_lte_500": {
        "norma": "UNI EN 303-5",
        "classe_minima": "classe 5",
        "rendimento_formula": "87 + log(Pn)",  # Rendimento minimo %
        "accumulo_minimo_dm3_kw": 20,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 5.0,
        "potenza_max_kw": 500.0,
    },
    "caldaia_gt_500": {
        "norma": "UNI EN 303-5",
        "classe_minima": "classe 5",
        "rendimento_minimo": 92,  # Rendimento fisso 92%
        "abbattimento_particolato": True,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 500.0,
        "potenza_max_kw": 2000.0,
    },
    "stufa_pellet": {
        "norma": "UNI EN 16510:2023",
        "rendimento_minimo": 85,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 3.0,
        "potenza_max_kw": 35.0,
    },
    "termocamino_pellet": {
        "norma": "UNI EN 16510:2023",
        "rendimento_minimo": 85,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 3.0,
        "potenza_max_kw": 35.0,
    },
    "termocamino_legna": {
        "norma": "UNI EN 16510:2023",
        "rendimento_minimo": 85,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 3.0,
        "potenza_max_kw": 35.0,
    },
    "stufa_legna": {
        "norma": "UNI EN 16510:2023",
        "rendimento_minimo": 85,
        "classe_emissioni": "5_stelle",
        "potenza_min_kw": 3.0,
        "potenza_max_kw": 35.0,
    },
}

# Requisiti tecnici FV combinato (par. 9.8.1)
REQUISITI_FV_COMBINATO = {
    "potenza_min_kw": 2.0,
    "potenza_max_kw": 1000.0,
    "carico_minimo_pa": 5400,
    "coeff_perdita_temp_min": -0.37,  # %/°C (valore negativo migliore)
    "garanzia_prodotto_anni": 10,
    "garanzia_rendimento_10_anni": 0.90,  # 90%
    "rendimento_inverter_min": 0.97,  # 97%
    "tolleranza": "positiva",  # Solo tolleranza positiva
    "produzione_max_fabbisogno": 1.05,  # 105% del fabbisogno
}

# Costi massimi specifici FV (€/kW) - par. 9.8.3
COSTI_MAX_FV = {
    "0-20": 1500.0,
    "20-200": 1200.0,
    "200-600": 1100.0,
    "600-1000": 1050.0,
}

# Costo massimo accumulo (€/kWh)
COSTO_MAX_ACCUMULO = 1000.0

# Requisiti producibilità minima solare termico (par. 9.12.1)
PRODUCIBILITA_MINIMA_SOLARE = {
    "piano": {"valore": 300, "localita": "Würzburg"},
    "sottovuoto": {"valore": 400, "localita": "Würzburg"},
    "concentrazione": {"valore": 550, "localita": "Atene"},
    "factory_made": {"valore": 400, "localita": "Würzburg"},
}


# ============================================================================
# FUNZIONI DI VALIDAZIONE - CONTO TERMICO
# ============================================================================

def valida_requisiti_ct(
    tipo_intervento: str,
    zona_climatica: str,
    potenza_nominale_kw: float,
    scop_dichiarato: float,
    gwp_refrigerante: str = ">150",
    bassa_temperatura: bool = False,
    edificio_esistente: bool = True,
    impianto_esistente: bool = True,
    categoria_catastale: str = None,
    alimentazione: str = "elettrica",
    iter_semplificato: bool = False,
) -> RisultatoValidazione:
    """
    Valida i requisiti per l'ammissibilita' al Conto Termico 3.0.

    Args:
        tipo_intervento: Tipo di pompa di calore
        zona_climatica: Zona climatica (A-F)
        potenza_nominale_kw: Potenza termica nominale in kW
        scop_dichiarato: SCOP/COP/SPER dichiarato dal costruttore
        gwp_refrigerante: ">150" o "<=150" (GWP del refrigerante)
        bassa_temperatura: True se sistema a bassa temperatura
        edificio_esistente: True se edificio esistente
        impianto_esistente: True se sostituisce impianto esistente
        categoria_catastale: Categoria catastale edificio (es. "A/2", "D/1")
        alimentazione: "elettrica" o "gas" per determinare SCOP vs SPER
        iter_semplificato: True se prodotto nel catalogo GSE (bypassa controllo SCOP)

    Returns:
        RisultatoValidazione con esito e dettagli
    """
    requisiti = []
    errori = []
    warning = []
    suggerimenti = []

    logger.info("=" * 60)
    logger.info("VALIDAZIONE REQUISITI CONTO TERMICO 3.0")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # REQ-CT-01: Edificio esistente
    # -------------------------------------------------------------------------
    req_edificio = RequisitoValidazione(
        codice="REQ-CT-01",
        descrizione="Edificio esistente e accatastato",
        superato=edificio_esistente,
        obbligatorio=True,
        dettaglio="OK" if edificio_esistente else "Il CT richiede edifici esistenti",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_edificio)
    if not edificio_esistente:
        errori.append("CT non ammesso per nuove costruzioni")

    # -------------------------------------------------------------------------
    # REQ-CT-02: Sostituzione impianto esistente
    # -------------------------------------------------------------------------
    req_impianto = RequisitoValidazione(
        codice="REQ-CT-02",
        descrizione="Sostituzione impianto di climatizzazione esistente",
        superato=impianto_esistente,
        obbligatorio=True,
        dettaglio="OK" if impianto_esistente else "Richiesta sostituzione impianto esistente",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_impianto)
    if not impianto_esistente:
        errori.append("CT richiede sostituzione di impianto esistente")

    # -------------------------------------------------------------------------
    # REQ-CT-03: Categoria catastale ammessa
    # -------------------------------------------------------------------------
    if categoria_catastale:
        cat_ammessa = _verifica_categoria_catastale(categoria_catastale)
        req_catastale = RequisitoValidazione(
            codice="REQ-CT-03",
            descrizione="Categoria catastale ammessa",
            superato=cat_ammessa,
            obbligatorio=True,
            dettaglio=f"Categoria {categoria_catastale}" if cat_ammessa else f"Categoria {categoria_catastale} ESCLUSA",
            riferimento_normativo="Allegato 1 - Tabella 1"
        )
        requisiti.append(req_catastale)
        if not cat_ammessa:
            errori.append(f"Categoria catastale {categoria_catastale} esclusa dal CT 3.0")
            suggerimenti.append("Categorie escluse: A/10 (uffici privati) e gruppo F")

    # -------------------------------------------------------------------------
    # REQ-CT-04: Zona climatica valida
    # -------------------------------------------------------------------------
    zona_valida = zona_climatica.upper() in ZONE_CLIMATICHE_VALIDE
    req_zona = RequisitoValidazione(
        codice="REQ-CT-04",
        descrizione="Zona climatica valida (A-F)",
        superato=zona_valida,
        obbligatorio=True,
        dettaglio=f"Zona {zona_climatica}" if zona_valida else f"Zona '{zona_climatica}' non riconosciuta",
        riferimento_normativo="Allegato 2 - Tabella 8"
    )
    requisiti.append(req_zona)
    if not zona_valida:
        errori.append(f"Zona climatica '{zona_climatica}' non valida")

    # -------------------------------------------------------------------------
    # REQ-CT-05: Tipo intervento riconosciuto
    # -------------------------------------------------------------------------
    tipi_validi = list(SCOP_MINIMI_CT.keys())
    tipo_valido = tipo_intervento.lower() in tipi_validi
    req_tipo = RequisitoValidazione(
        codice="REQ-CT-05",
        descrizione="Tipologia pompa di calore ammessa",
        superato=tipo_valido,
        obbligatorio=True,
        dettaglio=f"Tipo '{tipo_intervento}'" if tipo_valido else f"Tipo '{tipo_intervento}' non riconosciuto",
        riferimento_normativo="Allegato 1 - Tabelle 3-4-5"
    )
    requisiti.append(req_tipo)
    if not tipo_valido:
        errori.append(f"Tipo intervento '{tipo_intervento}' non riconosciuto")
        suggerimenti.append(f"Tipi ammessi: {', '.join(tipi_validi)}")

    # -------------------------------------------------------------------------
    # REQ-CT-06: Potenza nominale > 0
    # -------------------------------------------------------------------------
    potenza_valida = potenza_nominale_kw > 0
    req_potenza = RequisitoValidazione(
        codice="REQ-CT-06",
        descrizione="Potenza termica nominale valida",
        superato=potenza_valida,
        obbligatorio=True,
        dettaglio=f"{potenza_nominale_kw} kW" if potenza_valida else "Potenza deve essere > 0",
        riferimento_normativo="Allegato 2"
    )
    requisiti.append(req_potenza)
    if not potenza_valida:
        errori.append("Potenza nominale deve essere > 0 kW")

    # -------------------------------------------------------------------------
    # REQ-CT-07: SCOP/COP/SPER minimo Ecodesign
    # Se iter_semplificato=True (prodotto nel catalogo GSE), il requisito è
    # automaticamente superato perché il GSE ha già verificato l'ammissibilità
    # -------------------------------------------------------------------------
    if alimentazione.lower() == "gas":
        scop_min = _get_sper_minimo_ct(tipo_intervento, bassa_temperatura)
        etichetta_eff = "SPER"
    else:
        scop_min = _get_scop_minimo_ct(tipo_intervento, gwp_refrigerante, bassa_temperatura, potenza_nominale_kw)
        etichetta_eff = "SCOP/COP"

    # Se iter semplificato, il requisito è automaticamente superato
    if iter_semplificato:
        scop_sufficiente = True
        dettaglio_scop = f"Prodotto nel Catalogo GSE - requisiti già verificati ({etichetta_eff} {scop_dichiarato})"
    else:
        scop_sufficiente = scop_dichiarato >= scop_min if scop_min else False
        dettaglio_scop = f"{etichetta_eff} {scop_dichiarato} >= {scop_min}" if scop_sufficiente else f"{etichetta_eff} {scop_dichiarato} < {scop_min} (minimo)"

    req_scop = RequisitoValidazione(
        codice="REQ-CT-07",
        descrizione=f"{etichetta_eff} >= minimo Ecodesign ({scop_min})" + (" [Catalogo GSE]" if iter_semplificato else ""),
        superato=scop_sufficiente,
        obbligatorio=True,
        dettaglio=dettaglio_scop,
        riferimento_normativo="Allegato 1 - Requisiti Ecodesign" + (" / Art. 14 comma 5" if iter_semplificato else "")
    )
    requisiti.append(req_scop)
    if not scop_sufficiente:
        errori.append(f"{etichetta_eff} {scop_dichiarato} insufficiente (minimo {scop_min})")
        suggerimenti.append(f"Verificare scheda tecnica o considerare modello con {etichetta_eff} superiore")

    # -------------------------------------------------------------------------
    # WARNING: Potenza massima (se > 2000 kW)
    # -------------------------------------------------------------------------
    if potenza_nominale_kw > 2000:
        warning.append(f"Potenza {potenza_nominale_kw} kW molto elevata - verificare massimali")

    # -------------------------------------------------------------------------
    # CALCOLO PUNTEGGIO COMPLETEZZA
    # -------------------------------------------------------------------------
    requisiti_obbligatori = [r for r in requisiti if r.obbligatorio]
    superati = sum(1 for r in requisiti_obbligatori if r.superato)
    punteggio = (superati / len(requisiti_obbligatori) * 100) if requisiti_obbligatori else 0

    ammissibile = len(errori) == 0

    logger.info(f"\nRisultato: {'AMMISSIBILE' if ammissibile else 'NON AMMISSIBILE'}")
    logger.info(f"Punteggio: {punteggio:.0f}%")

    return RisultatoValidazione(
        ammissibile=ammissibile,
        incentivo="conto_termico",
        requisiti=requisiti,
        errori_bloccanti=errori,
        warning=warning,
        suggerimenti=suggerimenti,
        punteggio_completezza=punteggio,
        documentazione_richiesta=DOCUMENTAZIONE_CT if ammissibile else []
    )


def _get_scop_minimo_ct(
    tipo_intervento: str,
    gwp: str,
    bassa_temperatura: bool,
    potenza_kw: float
) -> Optional[float]:
    """Recupera il SCOP minimo per il tipo di intervento."""
    tipo = tipo_intervento.lower()

    if tipo not in SCOP_MINIMI_CT:
        return None

    config = SCOP_MINIMI_CT[tipo]

    # Caso semplice: valore diretto
    if isinstance(config, (int, float)):
        return float(config)

    # Caso con sotto-tipologie
    if isinstance(config, dict):
        # Gestione bassa temperatura
        if bassa_temperatura and "bassa_temperatura" in config:
            return config["bassa_temperatura"]
        if "standard" in config:
            return config["standard"]

        # Gestione GWP
        gwp_key = "GWP_lte_150" if gwp == "<=150" else "GWP_gt_150"
        if gwp_key in config:
            return config[gwp_key]

        # Gestione potenza per geotermiche
        if "lte_12kw" in config and potenza_kw <= 12:
            sub = config["lte_12kw"]
            if isinstance(sub, dict):
                return sub.get(gwp_key, sub.get("GWP_gt_150"))
            return sub
        if "gt_12kw" in config and potenza_kw > 12:
            return config["gt_12kw"]

        # Gestione split/vrf
        for key in ["split_multisplit", "vrf_vrv", "rooftop"]:
            if key in config:
                sub = config[key]
                if isinstance(sub, dict):
                    return sub.get(gwp_key, sub.get("GWP_gt_150", 3.0))
                return sub

    return 3.0  # Default fallback


def _get_sper_minimo_ct(tipo_intervento: str, bassa_temperatura: bool = False) -> Optional[float]:
    """Recupera il SPER minimo per pompe di calore a GAS (Tabella 5 - Allegato 1)."""
    tipo = tipo_intervento.lower()

    if tipo not in SPER_MINIMI_CT:
        return None

    config = SPER_MINIMI_CT[tipo]

    # Caso semplice: valore diretto
    if isinstance(config, (int, float)):
        return float(config)

    # Caso con bassa temperatura
    if isinstance(config, dict):
        if bassa_temperatura and "bassa_temperatura" in config:
            return config["bassa_temperatura"]
        if "standard" in config:
            return config["standard"]

    return 1.13  # Default fallback


def _verifica_categoria_catastale(categoria: str) -> bool:
    """
    Verifica se la categoria catastale e' ammessa al CT 3.0.

    Args:
        categoria: Categoria catastale (es. "A/2", "D/1", "A/10")

    Returns:
        True se ammessa, False se esclusa
    """
    if not categoria:
        return True  # Se non specificata, assumiamo ammessa

    cat_upper = categoria.upper().strip()

    # Verifica esclusioni specifiche
    if cat_upper == "A/10":
        return False  # Uffici e studi privati - ESCLUSI

    # Verifica gruppo F (entita' urbane) - ESCLUSE
    if cat_upper.startswith("F"):
        return False

    # Estrai gruppo dalla categoria (es. "A" da "A/2")
    gruppo = cat_upper.split("/")[0] if "/" in cat_upper else cat_upper[0]

    # Verifica se il gruppo e' tra quelli ammessi
    if gruppo in CATEGORIE_CATASTALI_CT["ammesse"]:
        # Verifica se la categoria specifica e' nella lista
        categorie_gruppo = CATEGORIE_CATASTALI_CT["ammesse"][gruppo]
        return cat_upper in categorie_gruppo

    return False  # Gruppo non riconosciuto


def _get_aliquota_ecobonus(anno: int, tipo_abitazione: str, tipo_intervento: str) -> float:
    """
    Recupera l'aliquota Ecobonus applicabile.

    Args:
        anno: Anno della spesa
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"
        tipo_intervento: Tipo di intervento (es. "pompe_di_calore")

    Returns:
        Aliquota come decimale (es. 0.50 per 50%)
    """
    # Normalizza tipo abitazione
    tipo_abit = tipo_abitazione.lower()
    if tipo_abit not in ["abitazione_principale", "altra_abitazione"]:
        tipo_abit = "altra_abitazione"

    # Anno non presente -> usa l'ultimo disponibile o default
    if anno not in ALIQUOTE_ECOBONUS:
        if anno < 2024:
            anno = 2024
        elif anno > 2028:
            anno = 2028

    aliquote_anno = ALIQUOTE_ECOBONUS.get(anno, {})
    aliquote_tipo = aliquote_anno.get(tipo_abit, {})

    # Cerca aliquota specifica per tipo intervento
    tipo_lower = tipo_intervento.lower()
    if tipo_lower in aliquote_tipo:
        return aliquote_tipo[tipo_lower]

    # Altrimenti usa default
    return aliquote_tipo.get("default", 0.36)


# ============================================================================
# FUNZIONI DI VALIDAZIONE - SOLARE TERMICO (III.D)
# ============================================================================

def valida_requisiti_solare_termico(
    tipo_collettore: str,
    superficie_lorda_m2: float,
    producibilita_qu: float,
    edificio_esistente: bool = True,
    impianto_climatizzazione: bool = True,
    solar_keymark: bool = True,
    garanzia_collettori_anni: int = 5,
    garanzia_bollitori_anni: int = 5,
    con_solar_cooling: bool = False,
    potenza_frigorifera_kw: float = 0.0,
    categoria_catastale: str = None,
) -> RisultatoValidazione:
    """
    Valida i requisiti per l'ammissibilita' al Conto Termico 3.0 - Solare Termico (III.D).

    Args:
        tipo_collettore: piano, sottovuoto, concentrazione, factory_made
        superficie_lorda_m2: Superficie solare lorda totale (m²)
        producibilita_qu: Producibilità specifica (kWht/m² anno)
        edificio_esistente: True se edificio esistente
        impianto_climatizzazione: True se dotato di impianto climatizzazione
        solar_keymark: True se collettori hanno certificazione Solar Keymark
        garanzia_collettori_anni: Anni garanzia collettori (min 5)
        garanzia_bollitori_anni: Anni garanzia bollitori (min 5)
        con_solar_cooling: True se abbinato a solar cooling
        potenza_frigorifera_kw: Potenza frigorifera per solar cooling (kW)
        categoria_catastale: Categoria catastale edificio

    Returns:
        RisultatoValidazione con esito e dettagli
    """
    requisiti = []
    errori = []
    warning = []
    suggerimenti = []

    logger.info("=" * 60)
    logger.info("VALIDAZIONE REQUISITI SOLARE TERMICO (III.D)")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # REQ-ST-01: Edificio esistente
    # -------------------------------------------------------------------------
    req_edificio = RequisitoValidazione(
        codice="REQ-ST-01",
        descrizione="Edificio esistente e accatastato",
        superato=edificio_esistente,
        obbligatorio=True,
        dettaglio="OK" if edificio_esistente else "Il CT richiede edifici esistenti",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_edificio)
    if not edificio_esistente:
        errori.append("CT non ammesso per nuove costruzioni")

    # -------------------------------------------------------------------------
    # REQ-ST-02: Impianto climatizzazione esistente
    # -------------------------------------------------------------------------
    req_impianto = RequisitoValidazione(
        codice="REQ-ST-02",
        descrizione="Edificio dotato di impianto di climatizzazione invernale",
        superato=impianto_climatizzazione,
        obbligatorio=True,
        dettaglio="OK" if impianto_climatizzazione else "Richiesto impianto esistente",
        riferimento_normativo="Par. 9.12 Regole Applicative"
    )
    requisiti.append(req_impianto)
    if not impianto_climatizzazione:
        errori.append("Edificio deve essere dotato di impianto climatizzazione")

    # -------------------------------------------------------------------------
    # REQ-ST-03: Categoria catastale ammessa
    # -------------------------------------------------------------------------
    if categoria_catastale:
        cat_ammessa = _verifica_categoria_catastale(categoria_catastale)
        req_catastale = RequisitoValidazione(
            codice="REQ-ST-03",
            descrizione="Categoria catastale ammessa",
            superato=cat_ammessa,
            obbligatorio=True,
            dettaglio=f"Categoria {categoria_catastale}" if cat_ammessa else f"Categoria {categoria_catastale} ESCLUSA",
            riferimento_normativo="Allegato 1 - Tabella 1"
        )
        requisiti.append(req_catastale)
        if not cat_ammessa:
            errori.append(f"Categoria catastale {categoria_catastale} esclusa dal CT 3.0")

    # -------------------------------------------------------------------------
    # REQ-ST-04: Superficie massima
    # -------------------------------------------------------------------------
    superficie_valida = 0 < superficie_lorda_m2 <= 2500
    req_superficie = RequisitoValidazione(
        codice="REQ-ST-04",
        descrizione="Superficie solare lorda <= 2500 m²",
        superato=superficie_valida,
        obbligatorio=True,
        dettaglio=f"{superficie_lorda_m2} m²" if superficie_valida else f"{superficie_lorda_m2} m² supera limite 2500 m²",
        riferimento_normativo="Par. 9.12 Regole Applicative"
    )
    requisiti.append(req_superficie)
    if not superficie_valida:
        if superficie_lorda_m2 > 2500:
            errori.append("Superficie solare supera il massimo di 2500 m²")
        else:
            errori.append("Superficie solare deve essere > 0")

    # -------------------------------------------------------------------------
    # REQ-ST-05: Certificazione Solar Keymark
    # -------------------------------------------------------------------------
    # Per concentrazione può essere sostituita da approvazione ENEA
    if tipo_collettore == "concentrazione":
        dettaglio_cert = "Solar Keymark o approvazione ENEA richiesta"
    else:
        dettaglio_cert = "OK" if solar_keymark else "Certificazione Solar Keymark obbligatoria"

    req_cert = RequisitoValidazione(
        codice="REQ-ST-05",
        descrizione="Certificazione Solar Keymark",
        superato=solar_keymark,
        obbligatorio=True,
        dettaglio=dettaglio_cert,
        riferimento_normativo="Par. 9.12.1 punto i"
    )
    requisiti.append(req_cert)
    if not solar_keymark and tipo_collettore != "concentrazione":
        errori.append("Certificazione Solar Keymark obbligatoria")
    elif not solar_keymark and tipo_collettore == "concentrazione":
        warning.append("Per collettori a concentrazione: richiedere approvazione ENEA")

    # -------------------------------------------------------------------------
    # REQ-ST-06: Producibilità minima
    # -------------------------------------------------------------------------
    req_prod = PRODUCIBILITA_MINIMA_SOLARE.get(tipo_collettore, {"valore": 300, "localita": "Würzburg"})
    prod_minima = req_prod["valore"]
    localita = req_prod["localita"]
    prod_valida = producibilita_qu > prod_minima

    req_producibilita = RequisitoValidazione(
        codice="REQ-ST-06",
        descrizione=f"Producibilità > {prod_minima} kWht/m² anno ({localita})",
        superato=prod_valida,
        obbligatorio=True,
        dettaglio=f"{producibilita_qu:.0f} kWht/m²" if prod_valida else f"{producibilita_qu:.0f} < {prod_minima} kWht/m²",
        riferimento_normativo="Par. 9.12.1 punto iii"
    )
    requisiti.append(req_producibilita)
    if not prod_valida:
        errori.append(f"Producibilità {producibilita_qu:.0f} kWht/m² < minimo {prod_minima} kWht/m²")
        suggerimenti.append(f"Selezionare collettori con producibilità > {prod_minima} kWht/m² ({localita})")

    # -------------------------------------------------------------------------
    # REQ-ST-07: Garanzia collettori e bollitori (min 5 anni)
    # -------------------------------------------------------------------------
    garanzia_valida = garanzia_collettori_anni >= 5 and garanzia_bollitori_anni >= 5
    req_garanzia = RequisitoValidazione(
        codice="REQ-ST-07",
        descrizione="Garanzia collettori e bollitori >= 5 anni",
        superato=garanzia_valida,
        obbligatorio=True,
        dettaglio=f"Collettori: {garanzia_collettori_anni}a, Bollitori: {garanzia_bollitori_anni}a",
        riferimento_normativo="Par. 9.12.1 punto vi"
    )
    requisiti.append(req_garanzia)
    if not garanzia_valida:
        errori.append("Garanzia collettori e bollitori deve essere >= 5 anni")

    # -------------------------------------------------------------------------
    # REQ-ST-08: Solar cooling - rapporto superficie/potenza (se applicabile)
    # -------------------------------------------------------------------------
    if con_solar_cooling and potenza_frigorifera_kw > 0:
        rapporto = superficie_lorda_m2 / potenza_frigorifera_kw
        rapporto_valido = 2.0 < rapporto <= 2.75
        req_solar_cooling = RequisitoValidazione(
            codice="REQ-ST-08",
            descrizione="Rapporto m²/kWf tra 2 e 2.75 (solar cooling)",
            superato=rapporto_valido,
            obbligatorio=True,
            dettaglio=f"Rapporto: {rapporto:.2f}" if rapporto_valido else f"Rapporto {rapporto:.2f} fuori range 2-2.75",
            riferimento_normativo="Par. 9.12.1 punto xi"
        )
        requisiti.append(req_solar_cooling)
        if not rapporto_valido:
            errori.append(f"Rapporto superficie/potenza frigorifera ({rapporto:.2f}) deve essere tra 2 e 2.75")

    # -------------------------------------------------------------------------
    # WARNING: Superficie > 100 m² richiede contabilizzazione calore
    # -------------------------------------------------------------------------
    if superficie_lorda_m2 > 100:
        warning.append("Superficie > 100 m²: obbligatoria contabilizzazione calore e comunicazione GSE annuale")

    # -------------------------------------------------------------------------
    # WARNING: Superficie > 50 m² richiede asseverazione
    # -------------------------------------------------------------------------
    if superficie_lorda_m2 > 50:
        warning.append("Superficie > 50 m²: richiesta asseverazione tecnico abilitato")

    # -------------------------------------------------------------------------
    # CALCOLO PUNTEGGIO COMPLETEZZA
    # -------------------------------------------------------------------------
    requisiti_obbligatori = [r for r in requisiti if r.obbligatorio]
    superati = sum(1 for r in requisiti_obbligatori if r.superato)
    punteggio = (superati / len(requisiti_obbligatori) * 100) if requisiti_obbligatori else 0

    ammissibile = len(errori) == 0

    # Documentazione
    docs = DOCUMENTAZIONE_SOLARE_TERMICO.copy()
    if superficie_lorda_m2 > 50:
        docs.extend(DOCUMENTAZIONE_SOLARE_TERMICO_GT_50M2)

    logger.info(f"\nRisultato: {'AMMISSIBILE' if ammissibile else 'NON AMMISSIBILE'}")
    logger.info(f"Punteggio: {punteggio:.0f}%")

    return RisultatoValidazione(
        ammissibile=ammissibile,
        incentivo="conto_termico",
        requisiti=requisiti,
        errori_bloccanti=errori,
        warning=warning,
        suggerimenti=suggerimenti,
        punteggio_completezza=punteggio,
        documentazione_richiesta=docs if ammissibile else []
    )


# ============================================================================
# FUNZIONI DI VALIDAZIONE - FOTOVOLTAICO COMBINATO (II.H)
# ============================================================================

def valida_requisiti_fv_combinato(
    potenza_fv_kw: float,
    produzione_stimata_kwh: float,
    fabbisogno_elettrico_kwh: float,
    fabbisogno_termico_equiv_kwh: float = 0.0,
    pdc_abbinata_ammissibile: bool = True,
    incentivo_pdc_calcolato: float = 0.0,
    edificio_esistente: bool = True,
    assetto_autoconsumo: bool = True,
    marcatura_ce: bool = True,
    tolleranza_positiva: bool = True,
    carico_moduli_pa: float = 5400.0,
    coeff_perdita_temp: float = -0.37,
    garanzia_prodotto_anni: int = 10,
    garanzia_rendimento_10anni: float = 0.90,
    rendimento_inverter: float = 0.97,
    registro_tecnologie: str = None,
    tipo_soggetto: str = "privato",
    categoria_catastale: str = None,
) -> RisultatoValidazione:
    """
    Valida i requisiti per l'ammissibilità al CT 3.0 - FV Combinato (II.H).

    Rif. Regole Applicative CT 3.0 - Paragrafo 9.8

    L'intervento II.H consiste nella installazione di impianti solari fotovoltaici
    e relativi sistemi di accumulo, realizzato CONGIUNTAMENTE alla sostituzione
    di impianti di climatizzazione invernale con pompe di calore elettriche (III.A).

    Args:
        potenza_fv_kw: Potenza di picco FV (kW)
        produzione_stimata_kwh: Produzione annua stimata (da PVGIS)
        fabbisogno_elettrico_kwh: Fabbisogno elettrico annuo edificio
        fabbisogno_termico_equiv_kwh: Fabbisogno termico equivalente in kWh el.
        pdc_abbinata_ammissibile: True se la PdC abbinata è ammessa al CT
        incentivo_pdc_calcolato: Incentivo CT calcolato per la PdC (limite FV)
        edificio_esistente: True se edificio esistente
        assetto_autoconsumo: True se in regime cessione parziale
        marcatura_ce: True se moduli hanno marcatura CE
        tolleranza_positiva: True se moduli hanno tolleranza solo positiva
        carico_moduli_pa: Resistenza al carico minima moduli (Pa)
        coeff_perdita_temp: Coefficiente perdita potenza temperatura (%/°C)
        garanzia_prodotto_anni: Anni di garanzia prodotto
        garanzia_rendimento_10anni: Garanzia rendimento dopo 10 anni (es. 0.90)
        rendimento_inverter: Rendimento europeo inverter (es. 0.97)
        registro_tecnologie: "sezione_a", "sezione_b", "sezione_c" o None
        tipo_soggetto: "privato", "impresa", "PA"
        categoria_catastale: Categoria catastale edificio

    Returns:
        RisultatoValidazione con esito e dettagli
    """
    requisiti = []
    errori = []
    warning = []
    suggerimenti = []

    logger.info("=" * 60)
    logger.info("VALIDAZIONE REQUISITI FV COMBINATO (II.H)")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # REQ-FV-01: PdC abbinata ammissibile al CT
    # -------------------------------------------------------------------------
    req_pdc = RequisitoValidazione(
        codice="REQ-FV-01",
        descrizione="Pompa di calore abbinata ammissibile al CT (III.A)",
        superato=pdc_abbinata_ammissibile,
        obbligatorio=True,
        dettaglio="OK" if pdc_abbinata_ammissibile else "PdC abbinata NON ammissibile",
        riferimento_normativo="Par. 9.8 - Requisito congiuntività"
    )
    requisiti.append(req_pdc)
    if not pdc_abbinata_ammissibile:
        errori.append("L'intervento II.H richiede una PdC abbinata ammissibile al CT (III.A)")

    # -------------------------------------------------------------------------
    # REQ-FV-02: Incentivo PdC calcolato (limite massimo FV)
    # -------------------------------------------------------------------------
    incentivo_valido = incentivo_pdc_calcolato > 0
    req_incentivo_pdc = RequisitoValidazione(
        codice="REQ-FV-02",
        descrizione="Incentivo PdC abbinata calcolato (limite incentivo FV)",
        superato=incentivo_valido,
        obbligatorio=True,
        dettaglio=f"€ {incentivo_pdc_calcolato:,.2f}" if incentivo_valido else "Incentivo PdC = 0",
        riferimento_normativo="Par. 9.8.3 - Limite I_tot_pdc"
    )
    requisiti.append(req_incentivo_pdc)
    if not incentivo_valido:
        errori.append("Calcolare prima l'incentivo della PdC abbinata (limite massimo FV)")

    # -------------------------------------------------------------------------
    # REQ-FV-03: Edificio esistente
    # -------------------------------------------------------------------------
    req_edificio = RequisitoValidazione(
        codice="REQ-FV-03",
        descrizione="Edificio esistente e accatastato",
        superato=edificio_esistente,
        obbligatorio=True,
        dettaglio="OK" if edificio_esistente else "Richiesto edificio esistente",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_edificio)
    if not edificio_esistente:
        errori.append("CT non ammesso per nuove costruzioni")

    # -------------------------------------------------------------------------
    # REQ-FV-04: Categoria catastale ammessa
    # -------------------------------------------------------------------------
    if categoria_catastale:
        cat_ammessa = _verifica_categoria_catastale(categoria_catastale)
        req_catastale = RequisitoValidazione(
            codice="REQ-FV-04",
            descrizione="Categoria catastale ammessa",
            superato=cat_ammessa,
            obbligatorio=True,
            dettaglio=f"Categoria {categoria_catastale}" if cat_ammessa else f"Categoria {categoria_catastale} ESCLUSA",
            riferimento_normativo="Allegato 1 - Tabella 1"
        )
        requisiti.append(req_catastale)
        if not cat_ammessa:
            errori.append(f"Categoria catastale {categoria_catastale} esclusa dal CT 3.0")

    # -------------------------------------------------------------------------
    # REQ-FV-05: Potenza FV nei limiti (2 kW - 1 MW)
    # -------------------------------------------------------------------------
    potenza_min = REQUISITI_FV_COMBINATO["potenza_min_kw"]
    potenza_max = REQUISITI_FV_COMBINATO["potenza_max_kw"]
    potenza_valida = potenza_min <= potenza_fv_kw <= potenza_max

    req_potenza = RequisitoValidazione(
        codice="REQ-FV-05",
        descrizione=f"Potenza FV tra {potenza_min} kW e {potenza_max} kW",
        superato=potenza_valida,
        obbligatorio=True,
        dettaglio=f"{potenza_fv_kw} kW" if potenza_valida else f"{potenza_fv_kw} kW fuori range",
        riferimento_normativo="Par. 9.8.1 - Requisiti tecnici"
    )
    requisiti.append(req_potenza)
    if not potenza_valida:
        if potenza_fv_kw < potenza_min:
            errori.append(f"Potenza FV ({potenza_fv_kw} kW) < minimo ({potenza_min} kW)")
        else:
            errori.append(f"Potenza FV ({potenza_fv_kw} kW) > massimo ({potenza_max} kW)")

    # -------------------------------------------------------------------------
    # REQ-FV-06: Assetto autoconsumo (cessione parziale)
    # -------------------------------------------------------------------------
    req_autoconsumo = RequisitoValidazione(
        codice="REQ-FV-06",
        descrizione="Impianto in assetto autoconsumo (cessione parziale)",
        superato=assetto_autoconsumo,
        obbligatorio=True,
        dettaglio="OK" if assetto_autoconsumo else "Richiesto assetto autoconsumo",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_autoconsumo)
    if not assetto_autoconsumo:
        errori.append("L'impianto FV deve essere in assetto autoconsumo (cessione parziale)")

    # -------------------------------------------------------------------------
    # REQ-FV-07: Dimensionamento corretto (produzione <= 105% fabbisogno)
    # -------------------------------------------------------------------------
    fabbisogno_totale = fabbisogno_elettrico_kwh + fabbisogno_termico_equiv_kwh
    limite_produzione = fabbisogno_totale * REQUISITI_FV_COMBINATO["produzione_max_fabbisogno"]
    dimensionamento_ok = produzione_stimata_kwh <= limite_produzione if fabbisogno_totale > 0 else True
    rapporto_pct = (produzione_stimata_kwh / fabbisogno_totale * 100) if fabbisogno_totale > 0 else 0

    req_dimensionamento = RequisitoValidazione(
        codice="REQ-FV-07",
        descrizione="Produzione <= 105% del fabbisogno energetico",
        superato=dimensionamento_ok,
        obbligatorio=True,
        dettaglio=f"{rapporto_pct:.1f}% del fabbisogno" if dimensionamento_ok else f"Produzione {rapporto_pct:.1f}% > 105%",
        riferimento_normativo="Par. 9.8.1 - Dimensionamento"
    )
    requisiti.append(req_dimensionamento)
    if not dimensionamento_ok:
        errori.append(f"Produzione stimata ({produzione_stimata_kwh:.0f} kWh) supera il 105% del fabbisogno ({limite_produzione:.0f} kWh)")
        suggerimenti.append("Ridurre la potenza dell'impianto o verificare il calcolo del fabbisogno")

    # -------------------------------------------------------------------------
    # REQ-FV-08: Marcatura CE e conformità
    # -------------------------------------------------------------------------
    req_ce = RequisitoValidazione(
        codice="REQ-FV-08",
        descrizione="Moduli con marcatura CE (Direttiva 2014/35/UE)",
        superato=marcatura_ce,
        obbligatorio=True,
        dettaglio="OK" if marcatura_ce else "Marcatura CE obbligatoria",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_ce)
    if not marcatura_ce:
        errori.append("Moduli FV devono avere marcatura CE")

    # -------------------------------------------------------------------------
    # REQ-FV-09: Tolleranza positiva
    # -------------------------------------------------------------------------
    req_tolleranza = RequisitoValidazione(
        codice="REQ-FV-09",
        descrizione="Moduli con tolleranza solo positiva",
        superato=tolleranza_positiva,
        obbligatorio=True,
        dettaglio="OK" if tolleranza_positiva else "Tolleranza deve essere solo positiva",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_tolleranza)
    if not tolleranza_positiva:
        errori.append("Moduli FV devono avere tolleranza solo positiva")

    # -------------------------------------------------------------------------
    # REQ-FV-10: Resistenza al carico >= 5400 Pa
    # -------------------------------------------------------------------------
    carico_min = REQUISITI_FV_COMBINATO["carico_minimo_pa"]
    carico_valido = carico_moduli_pa >= carico_min

    req_carico = RequisitoValidazione(
        codice="REQ-FV-10",
        descrizione=f"Resistenza al carico >= {carico_min} Pa",
        superato=carico_valido,
        obbligatorio=True,
        dettaglio=f"{carico_moduli_pa} Pa" if carico_valido else f"{carico_moduli_pa} Pa < {carico_min} Pa",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_carico)
    if not carico_valido:
        errori.append(f"Resistenza al carico ({carico_moduli_pa} Pa) < minimo ({carico_min} Pa)")

    # -------------------------------------------------------------------------
    # REQ-FV-11: Coefficiente perdita temperatura >= -0.37%/°C
    # -------------------------------------------------------------------------
    coeff_min = REQUISITI_FV_COMBINATO["coeff_perdita_temp_min"]
    coeff_valido = coeff_perdita_temp >= coeff_min  # Più negativo = peggiore

    req_coeff = RequisitoValidazione(
        codice="REQ-FV-11",
        descrizione=f"Coeff. perdita temperatura >= {coeff_min}%/°C",
        superato=coeff_valido,
        obbligatorio=True,
        dettaglio=f"{coeff_perdita_temp}%/°C" if coeff_valido else f"{coeff_perdita_temp}%/°C < {coeff_min}%/°C",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_coeff)
    if not coeff_valido:
        errori.append(f"Coeff. perdita temperatura ({coeff_perdita_temp}%/°C) peggiore del minimo ({coeff_min}%/°C)")

    # -------------------------------------------------------------------------
    # REQ-FV-12: Garanzia prodotto >= 10 anni
    # -------------------------------------------------------------------------
    garanzia_min = REQUISITI_FV_COMBINATO["garanzia_prodotto_anni"]
    garanzia_valida = garanzia_prodotto_anni >= garanzia_min

    req_garanzia_prod = RequisitoValidazione(
        codice="REQ-FV-12",
        descrizione=f"Garanzia prodotto >= {garanzia_min} anni",
        superato=garanzia_valida,
        obbligatorio=True,
        dettaglio=f"{garanzia_prodotto_anni} anni" if garanzia_valida else f"{garanzia_prodotto_anni} anni < {garanzia_min} anni",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_garanzia_prod)
    if not garanzia_valida:
        errori.append(f"Garanzia prodotto ({garanzia_prodotto_anni} anni) < minimo ({garanzia_min} anni)")

    # -------------------------------------------------------------------------
    # REQ-FV-13: Garanzia rendimento >= 90% dopo 10 anni
    # -------------------------------------------------------------------------
    rend_min = REQUISITI_FV_COMBINATO["garanzia_rendimento_10_anni"]
    rend_valido = garanzia_rendimento_10anni >= rend_min

    req_garanzia_rend = RequisitoValidazione(
        codice="REQ-FV-13",
        descrizione=f"Garanzia rendimento >= {rend_min*100:.0f}% dopo 10 anni",
        superato=rend_valido,
        obbligatorio=True,
        dettaglio=f"{garanzia_rendimento_10anni*100:.0f}%" if rend_valido else f"{garanzia_rendimento_10anni*100:.0f}% < {rend_min*100:.0f}%",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_garanzia_rend)
    if not rend_valido:
        errori.append(f"Garanzia rendimento ({garanzia_rendimento_10anni*100:.0f}%) < minimo ({rend_min*100:.0f}%)")

    # -------------------------------------------------------------------------
    # REQ-FV-14: Rendimento inverter >= 97%
    # -------------------------------------------------------------------------
    inv_min = REQUISITI_FV_COMBINATO["rendimento_inverter_min"]
    inv_valido = rendimento_inverter >= inv_min

    req_inverter = RequisitoValidazione(
        codice="REQ-FV-14",
        descrizione=f"Rendimento europeo inverter >= {inv_min*100:.0f}%",
        superato=inv_valido,
        obbligatorio=True,
        dettaglio=f"{rendimento_inverter*100:.0f}%" if inv_valido else f"{rendimento_inverter*100:.0f}% < {inv_min*100:.0f}%",
        riferimento_normativo="Par. 9.8.1"
    )
    requisiti.append(req_inverter)
    if not inv_valido:
        errori.append(f"Rendimento inverter ({rendimento_inverter*100:.0f}%) < minimo ({inv_min*100:.0f}%)")

    # -------------------------------------------------------------------------
    # WARNING: Potenza > 20 kW richiede documentazione aggiuntiva
    # -------------------------------------------------------------------------
    if potenza_fv_kw > 20:
        warning.append("Potenza > 20 kW: richiesta relazione tecnica di progetto e schema unifilare as-built")

    # -------------------------------------------------------------------------
    # INFO: Registro tecnologie FV (maggiorazione)
    # -------------------------------------------------------------------------
    if registro_tecnologie:
        maggiorazioni = {"sezione_a": "+5%", "sezione_b": "+10%", "sezione_c": "+15%"}
        magg = maggiorazioni.get(registro_tecnologie, "")
        if magg:
            suggerimenti.append(f"Registro tecnologie FV ({registro_tecnologie}): maggiorazione {magg} applicabile")

    # -------------------------------------------------------------------------
    # INFO: Imprese su edifici terziario
    # -------------------------------------------------------------------------
    if tipo_soggetto == "impresa":
        warning.append("Imprese su edifici terziario: richiesta riduzione domanda energia primaria >= 20%")
        warning.append("Intensità massima incentivi imprese: 30% dei costi ammissibili")

    # -------------------------------------------------------------------------
    # CALCOLO PUNTEGGIO COMPLETEZZA
    # -------------------------------------------------------------------------
    requisiti_obbligatori = [r for r in requisiti if r.obbligatorio]
    superati = sum(1 for r in requisiti_obbligatori if r.superato)
    punteggio = (superati / len(requisiti_obbligatori) * 100) if requisiti_obbligatori else 0

    ammissibile = len(errori) == 0

    # Documentazione
    docs = DOCUMENTAZIONE_FV_COMBINATO.copy()
    if potenza_fv_kw > 20:
        docs.extend(DOCUMENTAZIONE_FV_GT_20KW)

    logger.info(f"\nRisultato: {'AMMISSIBILE' if ammissibile else 'NON AMMISSIBILE'}")
    logger.info(f"Punteggio: {punteggio:.0f}%")

    return RisultatoValidazione(
        ammissibile=ammissibile,
        incentivo="conto_termico",
        requisiti=requisiti,
        errori_bloccanti=errori,
        warning=warning,
        suggerimenti=suggerimenti,
        punteggio_completezza=punteggio,
        documentazione_richiesta=docs if ammissibile else []
    )


# ============================================================================
# FUNZIONI DI VALIDAZIONE - BIOMASSA (III.C)
# ============================================================================

def valida_requisiti_biomassa(
    tipo_generatore: str,
    zona_climatica: str,
    potenza_nominale_kw: float,
    classe_emissione: str = "5_stelle",
    rendimento_pct: float = None,
    riduzione_emissioni_pct: float = 0.0,
    edificio_esistente: bool = True,
    impianto_esistente: bool = True,
    accumulo_installato: bool = True,
    capacita_accumulo_dm3: float = None,
    abbattimento_particolato: bool = True,
    categoria_catastale: str = None,
    tipo_soggetto: str = "privato",
) -> RisultatoValidazione:
    """
    Valida i requisiti per l'ammissibilità al CT 3.0 - Generatori a Biomassa (III.C).

    Rif. Regole Applicative CT 3.0 - Paragrafo 9.9.5

    L'intervento III.C consiste nella sostituzione di impianti di climatizzazione
    invernale esistenti con generatori di calore alimentati a biomassa.

    Args:
        tipo_generatore: Tipologia generatore ('caldaia_lte_500', 'caldaia_gt_500',
                         'stufa_pellet', 'termocamino_pellet', 'termocamino_legna',
                         'stufa_legna')
        zona_climatica: Zona climatica (A-F)
        potenza_nominale_kw: Potenza nominale in kW
        classe_emissione: Classe ambientale ('5_stelle' obbligatoria)
        rendimento_pct: Rendimento del generatore in %
        riduzione_emissioni_pct: Riduzione emissioni vs limiti legge (0-100)
        edificio_esistente: True se edificio esistente
        impianto_esistente: True se sostituisce impianto esistente
        accumulo_installato: True se sistema accumulo installato (per caldaie)
        capacita_accumulo_dm3: Capacità accumulo in dm³ (litri)
        abbattimento_particolato: True se sistema abbattimento installato (>500kW)
        categoria_catastale: Categoria catastale edificio
        tipo_soggetto: "privato", "impresa", "PA"

    Returns:
        RisultatoValidazione con esito e dettagli
    """
    import math

    requisiti = []
    errori = []
    warning = []
    suggerimenti = []

    logger.info("=" * 60)
    logger.info("VALIDAZIONE REQUISITI BIOMASSA (III.C)")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # REQ-BIO-01: Tipo generatore valido
    # -------------------------------------------------------------------------
    tipi_validi = list(REQUISITI_BIOMASSA.keys())
    tipo_valido = tipo_generatore in tipi_validi

    req_tipo = RequisitoValidazione(
        codice="REQ-BIO-01",
        descrizione="Tipologia generatore ammessa",
        superato=tipo_valido,
        obbligatorio=True,
        dettaglio=f"Tipo '{tipo_generatore}'" if tipo_valido else f"Tipo '{tipo_generatore}' non riconosciuto",
        riferimento_normativo="Par. 9.9.5 Regole Applicative"
    )
    requisiti.append(req_tipo)
    if not tipo_valido:
        errori.append(f"Tipo generatore '{tipo_generatore}' non riconosciuto")
        suggerimenti.append(f"Tipi ammessi: {', '.join(tipi_validi)}")
        # Se tipo non valido, non possiamo continuare
        return RisultatoValidazione(
            ammissibile=False,
            incentivo="conto_termico",
            requisiti=requisiti,
            errori_bloccanti=errori,
            warning=warning,
            suggerimenti=suggerimenti,
            punteggio_completezza=0,
            documentazione_richiesta=[]
        )

    req_biomassa = REQUISITI_BIOMASSA[tipo_generatore]

    # -------------------------------------------------------------------------
    # REQ-BIO-02: Edificio esistente
    # -------------------------------------------------------------------------
    req_edificio = RequisitoValidazione(
        codice="REQ-BIO-02",
        descrizione="Edificio esistente e accatastato",
        superato=edificio_esistente,
        obbligatorio=True,
        dettaglio="OK" if edificio_esistente else "Il CT richiede edifici esistenti",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_edificio)
    if not edificio_esistente:
        errori.append("CT non ammesso per nuove costruzioni")

    # -------------------------------------------------------------------------
    # REQ-BIO-03: Sostituzione impianto esistente
    # -------------------------------------------------------------------------
    req_impianto = RequisitoValidazione(
        codice="REQ-BIO-03",
        descrizione="Sostituzione impianto di climatizzazione esistente",
        superato=impianto_esistente,
        obbligatorio=True,
        dettaglio="OK" if impianto_esistente else "Richiesta sostituzione impianto esistente",
        riferimento_normativo="Art. 4 DM 7/8/2025"
    )
    requisiti.append(req_impianto)
    if not impianto_esistente:
        errori.append("CT richiede sostituzione di impianto esistente")

    # -------------------------------------------------------------------------
    # REQ-BIO-04: Categoria catastale ammessa
    # -------------------------------------------------------------------------
    if categoria_catastale:
        cat_ammessa = _verifica_categoria_catastale(categoria_catastale)
        req_catastale = RequisitoValidazione(
            codice="REQ-BIO-04",
            descrizione="Categoria catastale ammessa",
            superato=cat_ammessa,
            obbligatorio=True,
            dettaglio=f"Categoria {categoria_catastale}" if cat_ammessa else f"Categoria {categoria_catastale} ESCLUSA",
            riferimento_normativo="Allegato 1 - Tabella 1"
        )
        requisiti.append(req_catastale)
        if not cat_ammessa:
            errori.append(f"Categoria catastale {categoria_catastale} esclusa dal CT 3.0")

    # -------------------------------------------------------------------------
    # REQ-BIO-05: Zona climatica valida
    # -------------------------------------------------------------------------
    zona_valida = zona_climatica.upper() in ZONE_CLIMATICHE_VALIDE
    req_zona = RequisitoValidazione(
        codice="REQ-BIO-05",
        descrizione="Zona climatica valida (A-F)",
        superato=zona_valida,
        obbligatorio=True,
        dettaglio=f"Zona {zona_climatica}" if zona_valida else f"Zona '{zona_climatica}' non riconosciuta",
        riferimento_normativo="Allegato 2 - Tabella 8"
    )
    requisiti.append(req_zona)
    if not zona_valida:
        errori.append(f"Zona climatica '{zona_climatica}' non valida")

    # -------------------------------------------------------------------------
    # REQ-BIO-06: Potenza nei limiti per tipologia
    # -------------------------------------------------------------------------
    p_min = req_biomassa["potenza_min_kw"]
    p_max = req_biomassa["potenza_max_kw"]
    potenza_valida = p_min <= potenza_nominale_kw <= p_max

    req_potenza = RequisitoValidazione(
        codice="REQ-BIO-06",
        descrizione=f"Potenza nominale tra {p_min} kW e {p_max} kW",
        superato=potenza_valida,
        obbligatorio=True,
        dettaglio=f"{potenza_nominale_kw} kW" if potenza_valida else f"{potenza_nominale_kw} kW fuori range",
        riferimento_normativo="Par. 9.9.5 Regole Applicative"
    )
    requisiti.append(req_potenza)
    if not potenza_valida:
        if potenza_nominale_kw < p_min:
            errori.append(f"Potenza {potenza_nominale_kw} kW < minimo {p_min} kW per {tipo_generatore}")
        else:
            errori.append(f"Potenza {potenza_nominale_kw} kW > massimo {p_max} kW per {tipo_generatore}")

    # -------------------------------------------------------------------------
    # REQ-BIO-07: Classe emissioni 5 stelle (obbligatoria)
    # -------------------------------------------------------------------------
    classe_valida = classe_emissione == "5_stelle"
    req_classe = RequisitoValidazione(
        codice="REQ-BIO-07",
        descrizione="Certificazione classe ambientale 5 stelle (DM 186/2017)",
        superato=classe_valida,
        obbligatorio=True,
        dettaglio="OK" if classe_valida else f"Classe '{classe_emissione}' non ammessa",
        riferimento_normativo="DM 186/2017 e Par. 9.9.5"
    )
    requisiti.append(req_classe)
    if not classe_valida:
        errori.append("Requisito obbligatorio: classe ambientale 5 stelle (DM 186/2017)")

    # -------------------------------------------------------------------------
    # REQ-BIO-08: Rendimento minimo
    # -------------------------------------------------------------------------
    if rendimento_pct is not None:
        is_caldaia = tipo_generatore.startswith("caldaia")

        if is_caldaia and tipo_generatore == "caldaia_lte_500":
            # Caldaie ≤500kW: rendimento ≥ 87 + log(Pn)
            rendimento_min = 87 + math.log10(potenza_nominale_kw)
        elif is_caldaia and tipo_generatore == "caldaia_gt_500":
            # Caldaie >500kW: rendimento ≥ 92%
            rendimento_min = 92.0
        else:
            # Stufe/Termocamini: rendimento ≥ 85%
            rendimento_min = req_biomassa.get("rendimento_minimo", 85)

        rendimento_valido = rendimento_pct >= rendimento_min

        req_rendimento = RequisitoValidazione(
            codice="REQ-BIO-08",
            descrizione=f"Rendimento >= {rendimento_min:.1f}%",
            superato=rendimento_valido,
            obbligatorio=True,
            dettaglio=f"{rendimento_pct}%" if rendimento_valido else f"{rendimento_pct}% < {rendimento_min:.1f}%",
            riferimento_normativo="Allegato 1 - Requisiti minimi"
        )
        requisiti.append(req_rendimento)
        if not rendimento_valido:
            errori.append(f"Rendimento {rendimento_pct}% < minimo {rendimento_min:.1f}%")
    else:
        warning.append("Rendimento non specificato - verificare conformità ai requisiti minimi")

    # -------------------------------------------------------------------------
    # REQ-BIO-09: Sistema accumulo per caldaie (≥20 dm³/kW)
    # -------------------------------------------------------------------------
    if tipo_generatore.startswith("caldaia"):
        if accumulo_installato:
            if capacita_accumulo_dm3 is not None:
                accumulo_minimo = req_biomassa.get("accumulo_minimo_dm3_kw", 20) * potenza_nominale_kw
                accumulo_valido = capacita_accumulo_dm3 >= accumulo_minimo

                req_accumulo = RequisitoValidazione(
                    codice="REQ-BIO-09",
                    descrizione=f"Sistema accumulo >= {accumulo_minimo:.0f} dm³ (20 dm³/kW)",
                    superato=accumulo_valido,
                    obbligatorio=True,
                    dettaglio=f"{capacita_accumulo_dm3} dm³" if accumulo_valido else f"{capacita_accumulo_dm3} dm³ < {accumulo_minimo:.0f} dm³",
                    riferimento_normativo="Par. 9.9.5 - Requisiti caldaie"
                )
                requisiti.append(req_accumulo)
                if not accumulo_valido:
                    errori.append(f"Accumulo {capacita_accumulo_dm3} dm³ < minimo {accumulo_minimo:.0f} dm³")
            else:
                warning.append(f"Verificare capacità accumulo (minimo 20 dm³/kW = {20 * potenza_nominale_kw:.0f} dm³)")
        else:
            req_accumulo = RequisitoValidazione(
                codice="REQ-BIO-09",
                descrizione="Sistema accumulo installato (obbligatorio per caldaie)",
                superato=False,
                obbligatorio=True,
                dettaglio="Sistema accumulo NON installato",
                riferimento_normativo="Par. 9.9.5 - Requisiti caldaie"
            )
            requisiti.append(req_accumulo)
            errori.append("Sistema accumulo obbligatorio per caldaie a biomassa (≥20 dm³/kW)")

    # -------------------------------------------------------------------------
    # REQ-BIO-10: Sistema abbattimento particolato (>500 kW)
    # -------------------------------------------------------------------------
    if tipo_generatore == "caldaia_gt_500":
        req_abbattimento = RequisitoValidazione(
            codice="REQ-BIO-10",
            descrizione="Sistema abbattimento particolato installato (>500 kW)",
            superato=abbattimento_particolato,
            obbligatorio=True,
            dettaglio="OK" if abbattimento_particolato else "Sistema abbattimento NON installato",
            riferimento_normativo="Par. 9.9.5 - Requisiti caldaie >500 kW"
        )
        requisiti.append(req_abbattimento)
        if not abbattimento_particolato:
            errori.append("Sistema abbattimento particolato obbligatorio per caldaie > 500 kW")

    # -------------------------------------------------------------------------
    # INFO: Coefficiente Ce (premialità emissioni)
    # -------------------------------------------------------------------------
    if riduzione_emissioni_pct > 0:
        if riduzione_emissioni_pct <= 20:
            ce_info = "Ce = 1.0 (riduzione ≤ 20%)"
        elif riduzione_emissioni_pct <= 50:
            ce_info = "Ce = 1.2 (riduzione 20-50%)"
        else:
            ce_info = "Ce = 1.5 (riduzione > 50%)"
        suggerimenti.append(f"Premialità emissioni: {ce_info}")
    else:
        suggerimenti.append("Fornire riduzione emissioni per maggiorazione Ce")

    # -------------------------------------------------------------------------
    # WARNING: Potenza > 35 kW richiede documentazione aggiuntiva
    # -------------------------------------------------------------------------
    if potenza_nominale_kw > 35:
        warning.append("Potenza > 35 kW: richiesta asseverazione tecnico e relazione progetto")

    # -------------------------------------------------------------------------
    # CALCOLO PUNTEGGIO COMPLETEZZA
    # -------------------------------------------------------------------------
    requisiti_obbligatori = [r for r in requisiti if r.obbligatorio]
    superati = sum(1 for r in requisiti_obbligatori if r.superato)
    punteggio = (superati / len(requisiti_obbligatori) * 100) if requisiti_obbligatori else 0

    ammissibile = len(errori) == 0

    # Documentazione
    docs = DOCUMENTAZIONE_BIOMASSA.copy()
    if potenza_nominale_kw > 35:
        docs.extend(DOCUMENTAZIONE_BIOMASSA_GT_35KW)
    if potenza_nominale_kw > 500:
        docs.extend(DOCUMENTAZIONE_BIOMASSA_GT_500KW)

    logger.info(f"\nRisultato: {'AMMISSIBILE' if ammissibile else 'NON AMMISSIBILE'}")
    logger.info(f"Punteggio: {punteggio:.0f}%")

    return RisultatoValidazione(
        ammissibile=ammissibile,
        incentivo="conto_termico",
        requisiti=requisiti,
        errori_bloccanti=errori,
        warning=warning,
        suggerimenti=suggerimenti,
        punteggio_completezza=punteggio,
        documentazione_richiesta=docs if ammissibile else []
    )


# ============================================================================
# FUNZIONI DI VALIDAZIONE - ECOBONUS
# ============================================================================

def valida_requisiti_ecobonus(
    tipo_intervento: str,
    anno_spesa: int = None,
    tipo_abitazione: str = "abitazione_principale",
    edificio_esistente: bool = True,
    impianto_riscaldamento: bool = True,
    capienza_fiscale: bool = True,
) -> RisultatoValidazione:
    """
    Valida i requisiti per l'ammissibilità all'Ecobonus.

    Args:
        tipo_intervento: Tipo di intervento
        anno_spesa: Anno della spesa (default: anno corrente)
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"
        edificio_esistente: True se edificio esistente
        impianto_riscaldamento: True se dotato di impianto riscaldamento
        capienza_fiscale: True se il contribuente ha capienza IRPEF/IRES

    Returns:
        RisultatoValidazione con esito e dettagli
    """
    if anno_spesa is None:
        anno_spesa = date.today().year

    requisiti = []
    errori = []
    warning = []
    suggerimenti = []

    logger.info("=" * 60)
    logger.info("VALIDAZIONE REQUISITI ECOBONUS")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # REQ-ECO-01: Edificio esistente
    # -------------------------------------------------------------------------
    req_edificio = RequisitoValidazione(
        codice="REQ-ECO-01",
        descrizione="Edificio esistente e accatastato",
        superato=edificio_esistente,
        obbligatorio=True,
        dettaglio="OK" if edificio_esistente else "Ecobonus richiede edifici esistenti",
        riferimento_normativo="Art. 14 D.L. 63/2013"
    )
    requisiti.append(req_edificio)
    if not edificio_esistente:
        errori.append("Ecobonus non ammesso per nuove costruzioni")

    # -------------------------------------------------------------------------
    # REQ-ECO-02: Impianto di riscaldamento esistente
    # -------------------------------------------------------------------------
    req_impianto = RequisitoValidazione(
        codice="REQ-ECO-02",
        descrizione="Edificio dotato di impianto di riscaldamento",
        superato=impianto_riscaldamento,
        obbligatorio=True,
        dettaglio="OK" if impianto_riscaldamento else "Richiesto impianto riscaldamento preesistente",
        riferimento_normativo="Vademecum ENEA"
    )
    requisiti.append(req_impianto)
    if not impianto_riscaldamento:
        errori.append("Edificio deve essere dotato di impianto di riscaldamento")

    # -------------------------------------------------------------------------
    # REQ-ECO-03: Tipo intervento ammesso
    # -------------------------------------------------------------------------
    tipo_lower = tipo_intervento.lower()

    # Verifica esclusione dal 2025
    escluso_2025 = any(excl in tipo_lower for excl in ["caldaia", "condensazione"]) and anno_spesa >= 2025

    tipo_ammesso = tipo_lower in [t.lower() for t in INTERVENTI_ECOBONUS_2025] and not escluso_2025

    if escluso_2025:
        dettaglio = f"ESCLUSO dal 2025: caldaie a combustibili fossili"
        suggerimenti.append("Dal 2025 considerare: pompe di calore, sistemi ibridi factory-made, biomassa")
    else:
        dettaglio = f"Tipo '{tipo_intervento}'" if tipo_ammesso else f"Tipo '{tipo_intervento}' non riconosciuto"

    req_tipo = RequisitoValidazione(
        codice="REQ-ECO-03",
        descrizione="Tipologia intervento ammessa",
        superato=tipo_ammesso,
        obbligatorio=True,
        dettaglio=dettaglio,
        riferimento_normativo="Legge di Bilancio 2025" if escluso_2025 else "Art. 14 D.L. 63/2013"
    )
    requisiti.append(req_tipo)
    if not tipo_ammesso:
        if escluso_2025:
            errori.append("Caldaie a condensazione ESCLUSE dall'Ecobonus dal 2025")
        else:
            errori.append(f"Tipo intervento '{tipo_intervento}' non ammesso")

    # -------------------------------------------------------------------------
    # REQ-ECO-04: Capienza fiscale
    # -------------------------------------------------------------------------
    req_capienza = RequisitoValidazione(
        codice="REQ-ECO-04",
        descrizione="Capienza fiscale IRPEF/IRES sufficiente",
        superato=capienza_fiscale,
        obbligatorio=False,  # Non bloccante ma importante
        dettaglio="OK" if capienza_fiscale else "Verificare capienza fiscale per 10 anni",
        riferimento_normativo="Art. 14 D.L. 63/2013"
    )
    requisiti.append(req_capienza)
    if not capienza_fiscale:
        warning.append("Attenzione: senza capienza fiscale la detrazione non è utilizzabile")
        suggerimenti.append("Considerare il Conto Termico come alternativa (contributo diretto)")

    # -------------------------------------------------------------------------
    # REQ-ECO-05: Tipo abitazione valido
    # -------------------------------------------------------------------------
    tipi_abitazione_validi = ["abitazione_principale", "altra_abitazione"]
    tipo_abit_valido = tipo_abitazione.lower() in tipi_abitazione_validi

    req_abitazione = RequisitoValidazione(
        codice="REQ-ECO-05",
        descrizione="Tipo abitazione valido",
        superato=tipo_abit_valido,
        obbligatorio=True,
        dettaglio=f"{tipo_abitazione}" if tipo_abit_valido else "Specificare tipo abitazione",
        riferimento_normativo="Legge di Bilancio 2025"
    )
    requisiti.append(req_abitazione)

    # -------------------------------------------------------------------------
    # INFO: Aliquote e limiti applicabili
    # -------------------------------------------------------------------------
    aliquota = _get_aliquota_ecobonus(anno_spesa, tipo_abitazione, tipo_lower)
    limite_info = LIMITI_ECOBONUS.get(tipo_lower, {})

    if anno_spesa >= 2025:
        if tipo_abitazione == "abitazione_principale":
            warning.append(f"Anno {anno_spesa}: aliquota {aliquota*100:.0f}% (era 65% nel 2024 per molti interventi)")
        else:
            warning.append(f"Anno {anno_spesa}: aliquota {aliquota*100:.0f}% per seconde case")

    if anno_spesa >= 2027:
        warning.append(f"Anno {anno_spesa}: ulteriore riduzione aliquote (36%/30%)")

    # Info su limite detrazione
    if limite_info:
        limite_euro = limite_info.get("limite_euro", 0)
        limite_tipo = limite_info.get("limite_tipo", "detrazione_massima")
        if limite_tipo == "detrazione_massima":
            spesa_max = limite_euro / aliquota if aliquota > 0 else 0
            suggerimenti.append(f"Detrazione max: {limite_euro:,.0f} EUR (spesa max ammissibile: {spesa_max:,.0f} EUR)")
        else:
            suggerimenti.append(f"Spesa max ammissibile: {limite_euro:,.0f} EUR")

    # -------------------------------------------------------------------------
    # CALCOLO PUNTEGGIO COMPLETEZZA
    # -------------------------------------------------------------------------
    requisiti_obbligatori = [r for r in requisiti if r.obbligatorio]
    superati = sum(1 for r in requisiti_obbligatori if r.superato)
    punteggio = (superati / len(requisiti_obbligatori) * 100) if requisiti_obbligatori else 0

    ammissibile = len(errori) == 0

    logger.info(f"\nRisultato: {'AMMISSIBILE' if ammissibile else 'NON AMMISSIBILE'}")
    logger.info(f"Punteggio: {punteggio:.0f}%")

    return RisultatoValidazione(
        ammissibile=ammissibile,
        incentivo="ecobonus",
        requisiti=requisiti,
        errori_bloccanti=errori,
        warning=warning,
        suggerimenti=suggerimenti,
        punteggio_completezza=punteggio,
        documentazione_richiesta=DOCUMENTAZIONE_ECOBONUS if ammissibile else []
    )


# ============================================================================
# VALIDAZIONE COMBINATA (GATEKEEPER PRINCIPALE)
# ============================================================================

def valida_ammissibilita(
    # Dati intervento
    tipo_intervento: str,
    potenza_nominale_kw: float = None,
    scop_dichiarato: float = None,
    zona_climatica: str = None,
    spesa_prevista: float = None,
    # Dati edificio
    edificio_esistente: bool = True,
    impianto_esistente: bool = True,
    categoria_catastale: str = None,
    # Dati Ecobonus
    anno_spesa: int = None,
    tipo_abitazione: str = "abitazione_principale",
    capienza_fiscale: bool = True,
    # Opzioni
    gwp_refrigerante: str = ">150",
    bassa_temperatura: bool = False,
    alimentazione: str = "elettrica",
) -> dict:
    """
    Funzione principale del Gatekeeper.

    Valida l'ammissibilita' a ENTRAMBI gli incentivi e fornisce un riepilogo
    completo con raccomandazioni.

    Args:
        tipo_intervento: Tipo di intervento/pompa di calore
        potenza_nominale_kw: Potenza termica (richiesta per CT)
        scop_dichiarato: SCOP/COP/SPER dichiarato (richiesto per CT)
        zona_climatica: Zona A-F (richiesta per CT)
        spesa_prevista: Spesa prevista in euro
        edificio_esistente: True se edificio esistente
        impianto_esistente: True se sostituisce impianto esistente
        categoria_catastale: Categoria catastale (es. "A/2", "D/1")
        anno_spesa: Anno spesa (default: corrente)
        tipo_abitazione: Per Ecobonus
        capienza_fiscale: Per Ecobonus
        gwp_refrigerante: ">150" o "<=150"
        bassa_temperatura: Sistema bassa temperatura
        alimentazione: "elettrica" o "gas" per determinare SCOP vs SPER

    Returns:
        Dizionario con validazioni CT, Ecobonus e raccomandazione finale
    """
    if anno_spesa is None:
        anno_spesa = date.today().year

    logger.info("\n" + "=" * 70)
    logger.info("GATEKEEPER - VALIDAZIONE AMMISSIBILITA' INCENTIVI")
    logger.info("=" * 70)

    risultati = {
        "timestamp": date.today().isoformat(),
        "input": {
            "tipo_intervento": tipo_intervento,
            "potenza_kw": potenza_nominale_kw,
            "scop": scop_dichiarato,
            "zona_climatica": zona_climatica,
            "spesa_prevista": spesa_prevista,
            "anno_spesa": anno_spesa,
            "categoria_catastale": categoria_catastale,
            "alimentazione": alimentazione,
        },
        "conto_termico": None,
        "ecobonus": None,
        "raccomandazione": None,
        "incentivi_disponibili": [],
    }

    # -------------------------------------------------------------------------
    # VALIDAZIONE CONTO TERMICO
    # -------------------------------------------------------------------------
    ct_validabile = all([potenza_nominale_kw, scop_dichiarato, zona_climatica])

    if ct_validabile:
        logger.info("\n--- Validazione Conto Termico 3.0 ---")
        val_ct = valida_requisiti_ct(
            tipo_intervento=tipo_intervento,
            zona_climatica=zona_climatica,
            potenza_nominale_kw=potenza_nominale_kw,
            scop_dichiarato=scop_dichiarato,
            gwp_refrigerante=gwp_refrigerante,
            bassa_temperatura=bassa_temperatura,
            edificio_esistente=edificio_esistente,
            impianto_esistente=impianto_esistente,
            categoria_catastale=categoria_catastale,
            alimentazione=alimentazione,
        )
        risultati["conto_termico"] = {
            "ammissibile": val_ct.ammissibile,
            "punteggio": val_ct.punteggio_completezza,
            "errori": val_ct.errori_bloccanti,
            "warning": val_ct.warning,
            "suggerimenti": val_ct.suggerimenti,
            "documentazione": val_ct.documentazione_richiesta,
        }
        if val_ct.ammissibile:
            risultati["incentivi_disponibili"].append("conto_termico")
    else:
        risultati["conto_termico"] = {
            "ammissibile": False,
            "errori": ["Dati insufficienti per validazione CT (richiesti: potenza, SCOP, zona)"],
            "warning": [],
            "suggerimenti": ["Fornire potenza_nominale_kw, scop_dichiarato, zona_climatica"],
        }

    # -------------------------------------------------------------------------
    # VALIDAZIONE ECOBONUS
    # -------------------------------------------------------------------------
    logger.info("\n--- Validazione Ecobonus ---")

    # Mappa tipo intervento CT -> Ecobonus
    tipo_eco = _mappa_tipo_intervento_eco(tipo_intervento)

    val_eco = valida_requisiti_ecobonus(
        tipo_intervento=tipo_eco,
        anno_spesa=anno_spesa,
        tipo_abitazione=tipo_abitazione,
        edificio_esistente=edificio_esistente,
        impianto_riscaldamento=impianto_esistente,
        capienza_fiscale=capienza_fiscale,
    )
    risultati["ecobonus"] = {
        "ammissibile": val_eco.ammissibile,
        "punteggio": val_eco.punteggio_completezza,
        "errori": val_eco.errori_bloccanti,
        "warning": val_eco.warning,
        "suggerimenti": val_eco.suggerimenti,
        "documentazione": val_eco.documentazione_richiesta,
    }
    if val_eco.ammissibile:
        risultati["incentivi_disponibili"].append("ecobonus")

    # -------------------------------------------------------------------------
    # RACCOMANDAZIONE FINALE
    # -------------------------------------------------------------------------
    risultati["raccomandazione"] = _genera_raccomandazione(
        ct_ammissibile=risultati["conto_termico"]["ammissibile"],
        eco_ammissibile=val_eco.ammissibile,
        capienza_fiscale=capienza_fiscale,
        spesa_prevista=spesa_prevista,
    )

    logger.info("\n" + "=" * 70)
    logger.info(f"INCENTIVI DISPONIBILI: {risultati['incentivi_disponibili'] or 'NESSUNO'}")
    logger.info("=" * 70)

    return risultati


def _mappa_tipo_intervento_eco(tipo_ct: str) -> str:
    """Mappa il tipo intervento CT al corrispondente Ecobonus."""
    tipo = tipo_ct.lower()

    # Pompe di calore
    if any(x in tipo for x in ["aria", "acqua", "geotermic", "salamoia"]):
        return "pompe_di_calore"

    # Caldaie
    if "caldaia" in tipo or "condensazione" in tipo:
        return "caldaie_condensazione"

    # Ibridi
    if "ibrid" in tipo:
        return "sistemi_ibridi"

    # Solare
    if "solare" in tipo or "solar" in tipo:
        return "solare_termico"

    # Biomassa
    if "biomassa" in tipo or "pellet" in tipo or "legna" in tipo:
        return "generatori_biomassa"

    return tipo_ct


def _genera_raccomandazione(
    ct_ammissibile: bool,
    eco_ammissibile: bool,
    capienza_fiscale: bool,
    spesa_prevista: float = None,
) -> dict:
    """Genera raccomandazione finale basata sulle validazioni."""

    if ct_ammissibile and eco_ammissibile:
        return {
            "status": "ENTRAMBI_DISPONIBILI",
            "messaggio": (
                "Entrambi gli incentivi sono disponibili. "
                "Eseguire il confronto finanziario con financial_roi.compare_incentives() "
                "per determinare l'opzione più vantaggiosa."
            ),
            "azione_consigliata": "Procedere con calcolo comparativo CT vs Ecobonus",
        }

    elif ct_ammissibile and not eco_ammissibile:
        return {
            "status": "SOLO_CT",
            "messaggio": (
                "Solo il Conto Termico è disponibile. "
                "L'Ecobonus non è ammissibile per questo intervento."
            ),
            "azione_consigliata": "Procedere con calcolo Conto Termico",
        }

    elif eco_ammissibile and not ct_ammissibile:
        msg = "Solo l'Ecobonus è disponibile."
        if not capienza_fiscale:
            msg += " ATTENZIONE: verificare capienza fiscale per 10 anni."
        return {
            "status": "SOLO_ECOBONUS",
            "messaggio": msg,
            "azione_consigliata": "Procedere con calcolo Ecobonus",
        }

    else:
        return {
            "status": "NESSUNO_DISPONIBILE",
            "messaggio": (
                "Nessun incentivo è attualmente ammissibile. "
                "Verificare i requisiti non soddisfatti e valutare modifiche all'intervento."
            ),
            "azione_consigliata": "Rivedere progetto o requisiti",
        }


# ============================================================================
# REPORT TESTUALE
# ============================================================================

def genera_report_validazione(risultato: dict) -> str:
    """Genera un report testuale della validazione."""
    lines = []
    lines.append("=" * 70)
    lines.append("REPORT VALIDAZIONE AMMISSIBILITA' INCENTIVI")
    lines.append("=" * 70)
    lines.append("")

    # Input
    lines.append("[INPUT]")
    lines.append("-" * 35)
    inp = risultato.get("input", {})
    lines.append(f"  Tipo intervento: {inp.get('tipo_intervento', 'N/A')}")
    lines.append(f"  Potenza: {inp.get('potenza_kw', 'N/A')} kW")
    alim = inp.get('alimentazione', 'elettrica')
    eff_label = "SPER" if alim == "gas" else "SCOP"
    lines.append(f"  {eff_label}: {inp.get('scop', 'N/A')}")
    lines.append(f"  Zona climatica: {inp.get('zona_climatica', 'N/A')}")
    if inp.get('categoria_catastale'):
        lines.append(f"  Categoria catastale: {inp.get('categoria_catastale')}")
    lines.append(f"  Alimentazione: {alim}")
    lines.append(f"  Spesa prevista: {inp.get('spesa_prevista', 'N/A')} EUR")
    lines.append(f"  Anno spesa: {inp.get('anno_spesa', 'N/A')}")
    lines.append("")

    # Conto Termico
    ct = risultato.get("conto_termico", {})
    lines.append("[CONTO TERMICO 3.0]")
    lines.append("-" * 35)
    lines.append(f"  Ammissibile: {'SI' if ct.get('ammissibile') else 'NO'}")
    if ct.get("errori"):
        lines.append("  Errori:")
        for e in ct["errori"]:
            lines.append(f"    - {e}")
    if ct.get("warning"):
        lines.append("  Warning:")
        for w in ct["warning"]:
            lines.append(f"    - {w}")
    lines.append("")

    # Ecobonus
    eco = risultato.get("ecobonus", {})
    lines.append("[ECOBONUS]")
    lines.append("-" * 35)
    lines.append(f"  Ammissibile: {'SI' if eco.get('ammissibile') else 'NO'}")
    if eco.get("errori"):
        lines.append("  Errori:")
        for e in eco["errori"]:
            lines.append(f"    - {e}")
    if eco.get("warning"):
        lines.append("  Warning:")
        for w in eco["warning"]:
            lines.append(f"    - {w}")
    lines.append("")

    # Raccomandazione
    racc = risultato.get("raccomandazione", {})
    lines.append("[RACCOMANDAZIONE]")
    lines.append("-" * 35)
    lines.append(f"  Status: {racc.get('status', 'N/A')}")

    import textwrap
    msg = racc.get("messaggio", "")
    for line in textwrap.wrap(msg, width=60):
        lines.append(f"  {line}")
    lines.append("")
    lines.append(f"  Azione: {racc.get('azione_consigliata', 'N/A')}")
    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================================
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEST MODULO VALIDATOR (GATEKEEPER)")
    print("=" * 70)

    # Test 1: Pompa di calore ammissibile a entrambi
    print("\n--- TEST 1: PdC aria/acqua (ammissibile a entrambi) ---")
    result1 = valida_ammissibilita(
        tipo_intervento="aria_acqua",
        potenza_nominale_kw=10,
        scop_dichiarato=4.5,
        zona_climatica="E",
        spesa_prevista=15000,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale",
    )
    print(genera_report_validazione(result1))

    # Test 2: Caldaia a condensazione (esclusa da Ecobonus 2025)
    print("\n--- TEST 2: Caldaia condensazione (esclusa Ecobonus 2025) ---")
    result2 = valida_ammissibilita(
        tipo_intervento="caldaia_condensazione",
        potenza_nominale_kw=24,
        scop_dichiarato=None,  # Non applicabile
        zona_climatica="E",
        spesa_prevista=8000,
        anno_spesa=2025,
    )
    print(genera_report_validazione(result2))

    # Test 3: PdC con SCOP insufficiente
    print("\n--- TEST 3: PdC con SCOP insufficiente ---")
    result3 = valida_ammissibilita(
        tipo_intervento="aria_acqua",
        potenza_nominale_kw=10,
        scop_dichiarato=2.5,  # Sotto il minimo 2.825
        zona_climatica="E",
        spesa_prevista=12000,
        anno_spesa=2025,
    )
    print(genera_report_validazione(result3))

    # Test 4: Categoria catastale A/10 (esclusa)
    print("\n--- TEST 4: Categoria catastale A/10 (ESCLUSA) ---")
    result4 = valida_ammissibilita(
        tipo_intervento="aria_acqua",
        potenza_nominale_kw=10,
        scop_dichiarato=4.5,
        zona_climatica="E",
        spesa_prevista=15000,
        anno_spesa=2025,
        categoria_catastale="A/10",  # Uffici privati - ESCLUSI
    )
    print(genera_report_validazione(result4))

    # Test 5: PdC a gas con SPER
    print("\n--- TEST 5: PdC a GAS (verifica SPER) ---")
    result5 = valida_ammissibilita(
        tipo_intervento="acqua_acqua",
        potenza_nominale_kw=50,
        scop_dichiarato=1.20,  # SPER per gas
        zona_climatica="E",
        spesa_prevista=25000,
        anno_spesa=2025,
        alimentazione="gas",
    )
    print(genera_report_validazione(result5))

    # Test 6: Ecobonus per seconda casa (aliquota 36%)
    print("\n--- TEST 6: PdC per SECONDA CASA (aliquota 36%) ---")
    result6 = valida_ammissibilita(
        tipo_intervento="aria_acqua",  # Tipo tecnico per CT
        potenza_nominale_kw=8,
        scop_dichiarato=4.2,
        zona_climatica="D",
        spesa_prevista=10000,
        anno_spesa=2025,
        tipo_abitazione="altra_abitazione",  # Seconda casa -> aliquota 36%
    )
    print(genera_report_validazione(result6))

    # Test 7: Anno 2027 con aliquote ulteriormente ridotte
    print("\n--- TEST 7: Anno 2027 (aliquote ridotte 36%/30%) ---")
    result7 = valida_ammissibilita(
        tipo_intervento="aria_acqua",
        potenza_nominale_kw=10,
        scop_dichiarato=4.5,
        zona_climatica="E",
        spesa_prevista=15000,
        anno_spesa=2027,  # Aliquote ridotte al 36%/30%
        tipo_abitazione="abitazione_principale",
    )
    print(genera_report_validazione(result7))
