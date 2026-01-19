"""
Modulo di calcolo incentivi Conto Termico 3.0 per impianti fotovoltaici combinati (II.H).

Riferimento normativo: D.M. 7 agosto 2025 - Regole Applicative CT 3.0
Paragrafo 9.8 - Installazione di impianti solari fotovoltaici abbinati a pompa di calore elettrica

L'intervento II.H consiste nella installazione di impianti solari fotovoltaici e relativi sistemi
di accumulo, realizzato congiuntamente alla sostituzione di impianti di climatizzazione invernale
esistenti con pompe di calore elettriche (intervento III.A).

Formula di calcolo:
    I_tot = min(%_spesa × C_FTV × P_FTV + %_spesa × C_ACC × C_ACCUMULO, I_tot_pdc)
    con I_tot ≤ I_max

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import logging
from typing import Optional, TypedDict, Literal

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class InputRiepilogoFV(TypedDict):
    potenza_fv_kw: float
    capacita_accumulo_kwh: float
    spesa_fv: float
    spesa_accumulo: float
    tipo_soggetto: str
    registro_tecnologie: Optional[str]
    incentivo_pdc_abbinata: float


class CalcoliIntermediFV(TypedDict):
    costo_specifico_fv: float
    costo_max_fv: float
    costo_specifico_acc: float
    costo_max_acc: float
    percentuale_spesa: float
    incentivo_fv_lordo: float
    incentivo_acc_lordo: float
    incentivo_totale_lordo: float
    limite_pdc: float
    maggiorazione_registro: float


class ErogazioneFV(TypedDict):
    numero_rate: int
    rate: list[float]
    modalita: str


class RisultatoCalcoloFV(TypedDict):
    status: Literal["OK", "ERROR", "WARNING"]
    messaggio: str
    input_riepilogo: InputRiepilogoFV
    calcoli_intermedi: Optional[CalcoliIntermediFV]
    incentivo_totale: Optional[float]
    erogazione: Optional[ErogazioneFV]
    massimali_applicati: Optional[dict]


# ============================================================================
# COSTANTI E DATI (da Regole Applicative CT 3.0 - Paragrafo 9.8.3)
# ============================================================================

# Costi massimi specifici FV (€/kW) per fascia di potenza
COSTI_MAX_FV: dict[str, float] = {
    "0-20": 1500.0,      # fino a 20 kW
    "20-200": 1200.0,    # oltre 20 kW e fino a 200 kW
    "200-600": 1100.0,   # oltre 200 kW e fino a 600 kW
    "600-1000": 1050.0,  # oltre 600 kW e fino a 1.000 kW
}

# Costo massimo accumulo (€/kWh)
COSTO_MAX_ACCUMULO: float = 1000.0

# Percentuale incentivata base
PERCENTUALE_SPESA_BASE: float = 0.20  # 20%

# Percentuale per PA
PERCENTUALE_SPESA_PA: float = 1.00  # 100%

# Maggiorazioni per registro tecnologie fotovoltaico (art. 12 DL 181/2023)
# Rif. Regole Applicative CT 3.0 - Par. 9.8.3
#
# Il "Registro delle tecnologie del fotovoltaico" incentiva l'uso di moduli prodotti in UE.
# Le tre sezioni hanno requisiti crescenti di "europeità" della filiera produttiva:
#
#   Sezione A (+5%):  Moduli ASSEMBLATI nell'Unione Europea
#   Sezione B (+10%): Moduli con CELLE prodotte nell'Unione Europea
#   Sezione C (+15%): Moduli con CELLE e WAFER prodotti nell'UE (filiera completa)
#
# CONDIZIONI per ottenere la maggiorazione:
#   - TUTTI i moduli dell'impianto devono essere iscritti al registro
#   - Tutti i moduli devono appartenere alla STESSA sezione (non mischiabili)
#   - L'iscrizione va dichiarata nella richiesta con documentazione allegata
#
# COME VERIFICARE se i moduli sono nel registro:
#   1. Consultare: https://www.gse.it/servizi-per-te/fotovoltaico/registro-tecnologie-fotovoltaico
#   2. Richiedere al produttore/fornitore la dichiarazione di iscrizione
#   3. Verificare la sezione specifica (A, B o C) nella documentazione
#
MAGGIORAZIONI_REGISTRO: dict[str, float] = {
    "sezione_a": 0.05,  # +5% per lettera a) - Moduli assemblati in UE
    "sezione_b": 0.10,  # +10% per lettera b) - Celle prodotte in UE
    "sezione_c": 0.15,  # +15% per lettera c) - Celle e wafer prodotti in UE
    "nessuno": 0.00,    # nessuna maggiorazione
}

# Limiti potenza FV (kW)
POTENZA_MIN_FV: float = 2.0
POTENZA_MAX_FV: float = 1000.0

# Soglia per rata unica (€)
SOGLIA_RATA_UNICA: float = 15000.0


# ============================================================================
# FUNZIONI DI SUPPORTO
# ============================================================================

def get_costo_max_fv(potenza_kw: float) -> float:
    """
    Restituisce il costo massimo specifico FV in base alla potenza.

    Rif. Regole Applicative CT 3.0 - Par. 9.8.3

    Args:
        potenza_kw: Potenza di picco dell'impianto FV in kW

    Returns:
        Costo massimo specifico in €/kW
    """
    if potenza_kw <= 20:
        return COSTI_MAX_FV["0-20"]
    elif potenza_kw <= 200:
        return COSTI_MAX_FV["20-200"]
    elif potenza_kw <= 600:
        return COSTI_MAX_FV["200-600"]
    else:
        return COSTI_MAX_FV["600-1000"]


def get_percentuale_spesa(tipo_soggetto: str) -> float:
    """
    Restituisce la percentuale incentivata in base al tipo soggetto.

    Args:
        tipo_soggetto: "privato", "impresa", "PA"

    Returns:
        Percentuale incentivata (es. 0.20 per 20%)
    """
    if tipo_soggetto == "PA":
        return PERCENTUALE_SPESA_PA
    return PERCENTUALE_SPESA_BASE


def get_maggiorazione_registro(registro_tecnologie: Optional[str]) -> float:
    """
    Restituisce la maggiorazione per iscrizione al registro tecnologie FV.

    Rif. art. 12 DL 181/2023 e Par. 9.8.3 Regole Applicative

    Args:
        registro_tecnologie: "sezione_a", "sezione_b", "sezione_c" o None

    Returns:
        Maggiorazione percentuale (es. 0.05 per +5%)
    """
    if registro_tecnologie and registro_tecnologie in MAGGIORAZIONI_REGISTRO:
        return MAGGIORAZIONI_REGISTRO[registro_tecnologie]
    return 0.0


def calcola_erogazione_fv(
    incentivo_totale: float,
    potenza_pdc_kw: float
) -> ErogazioneFV:
    """
    Calcola le modalità di erogazione dell'incentivo FV.

    L'erogazione segue le stesse regole dell'intervento PdC abbinato:
    - 2 rate se P_rated ≤ 35 kW
    - 5 rate se P_rated > 35 kW
    - Rata unica se incentivo ≤ 15.000€

    Args:
        incentivo_totale: Incentivo totale calcolato
        potenza_pdc_kw: Potenza della PdC abbinata

    Returns:
        Dizionario con modalità e rate
    """
    # Rata unica se incentivo <= 15.000€
    if incentivo_totale <= SOGLIA_RATA_UNICA:
        return {
            "numero_rate": 1,
            "rate": [round(incentivo_totale, 2)],
            "modalita": "rata_unica"
        }

    # Numero rate basato sulla potenza PdC
    if potenza_pdc_kw <= 35:
        n_rate = 2
    else:
        n_rate = 5

    rata = incentivo_totale / n_rate

    return {
        "numero_rate": n_rate,
        "rate": [round(rata, 2)] * n_rate,
        "modalita": f"{n_rate}_rate_annuali"
    }


# ============================================================================
# FUNZIONE PRINCIPALE DI CALCOLO
# ============================================================================

def calculate_fv_combined_incentive(
    potenza_fv_kw: float,
    spesa_fv: float,
    incentivo_pdc_abbinata: float,
    potenza_pdc_kw: float,
    capacita_accumulo_kwh: float = 0.0,
    spesa_accumulo: float = 0.0,
    tipo_soggetto: str = "privato",
    registro_tecnologie: Optional[str] = None
) -> RisultatoCalcoloFV:
    """
    Calcola l'incentivo Conto Termico 3.0 per impianto FV combinato (II.H).

    Formula (Par. 9.8.3 Regole Applicative):
        I_tot = min(%_spesa × C_FTV × P_FTV + %_spesa × C_ACC × C_ACCUMULO, I_tot_pdc)
        con I_tot ≤ I_max

    Dove:
        - %_spesa = 20% (base) o 100% (PA), con eventuali maggiorazioni registro
        - C_FTV = min(costo_specifico_effettivo, costo_max_per_fascia)
        - P_FTV = potenza di picco FV (kW)
        - C_ACC = min(costo_specifico_accumulo, 1000 €/kWh)
        - C_ACCUMULO = capacità accumulo (kWh)
        - I_tot_pdc = incentivo calcolato per la PdC abbinata (limite massimo)

    Args:
        potenza_fv_kw: Potenza di picco impianto FV (kW)
        spesa_fv: Spesa sostenuta per impianto FV (€)
        incentivo_pdc_abbinata: Incentivo calcolato per la PdC abbinata (€)
        potenza_pdc_kw: Potenza della PdC abbinata (kW)
        capacita_accumulo_kwh: Capacità sistema accumulo (kWh), default 0
        spesa_accumulo: Spesa per sistema accumulo (€), default 0
        tipo_soggetto: "privato", "impresa", "PA"
        registro_tecnologie: "sezione_a", "sezione_b", "sezione_c" o None

    Returns:
        RisultatoCalcoloFV con tutti i dettagli del calcolo
    """

    logger.info("=" * 60)
    logger.info("CALCOLO INCENTIVO CT 3.0 - FOTOVOLTAICO COMBINATO (II.H)")
    logger.info("=" * 60)

    # Input riepilogo
    input_riepilogo: InputRiepilogoFV = {
        "potenza_fv_kw": potenza_fv_kw,
        "capacita_accumulo_kwh": capacita_accumulo_kwh,
        "spesa_fv": spesa_fv,
        "spesa_accumulo": spesa_accumulo,
        "tipo_soggetto": tipo_soggetto,
        "registro_tecnologie": registro_tecnologie,
        "incentivo_pdc_abbinata": incentivo_pdc_abbinata
    }

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")

    if potenza_fv_kw < POTENZA_MIN_FV:
        return {
            "status": "ERROR",
            "messaggio": f"Potenza FV ({potenza_fv_kw} kW) inferiore al minimo ammesso ({POTENZA_MIN_FV} kW)",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "incentivo_totale": None,
            "erogazione": None,
            "massimali_applicati": None
        }

    if potenza_fv_kw > POTENZA_MAX_FV:
        return {
            "status": "ERROR",
            "messaggio": f"Potenza FV ({potenza_fv_kw} kW) superiore al massimo ammesso ({POTENZA_MAX_FV} kW)",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "incentivo_totale": None,
            "erogazione": None,
            "massimali_applicati": None
        }

    if spesa_fv <= 0:
        return {
            "status": "ERROR",
            "messaggio": "La spesa per l'impianto FV deve essere > 0",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "incentivo_totale": None,
            "erogazione": None,
            "massimali_applicati": None
        }

    if incentivo_pdc_abbinata <= 0:
        return {
            "status": "ERROR",
            "messaggio": "L'intervento II.H richiede una PdC abbinata con incentivo > 0 (intervento III.A)",
            "input_riepilogo": input_riepilogo,
            "calcoli_intermedi": None,
            "incentivo_totale": None,
            "erogazione": None,
            "massimali_applicati": None
        }

    logger.info(f"  Potenza FV: {potenza_fv_kw} kW")
    logger.info(f"  Spesa FV: {spesa_fv:.2f} €")
    logger.info(f"  Capacità accumulo: {capacita_accumulo_kwh} kWh")
    logger.info(f"  Spesa accumulo: {spesa_accumulo:.2f} €")
    logger.info(f"  Incentivo PdC abbinata (limite): {incentivo_pdc_abbinata:.2f} €")

    # -------------------------------------------------------------------------
    # STEP 2: Calcolo costo specifico FV
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Calcolo costo specifico FV")

    costo_specifico_fv = spesa_fv / potenza_fv_kw
    costo_max_fv = get_costo_max_fv(potenza_fv_kw)
    costo_fv_applicato = min(costo_specifico_fv, costo_max_fv)

    logger.info(f"  Costo specifico effettivo: {costo_specifico_fv:.2f} €/kW")
    logger.info(f"  Costo massimo ammissibile: {costo_max_fv:.2f} €/kW")
    logger.info(f"  Costo applicato: {costo_fv_applicato:.2f} €/kW")

    # -------------------------------------------------------------------------
    # STEP 3: Calcolo costo specifico accumulo (se presente)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Calcolo costo specifico accumulo")

    costo_specifico_acc = 0.0
    costo_acc_applicato = 0.0

    if capacita_accumulo_kwh > 0 and spesa_accumulo > 0:
        costo_specifico_acc = spesa_accumulo / capacita_accumulo_kwh
        costo_acc_applicato = min(costo_specifico_acc, COSTO_MAX_ACCUMULO)
        logger.info(f"  Costo specifico effettivo: {costo_specifico_acc:.2f} €/kWh")
        logger.info(f"  Costo massimo ammissibile: {COSTO_MAX_ACCUMULO:.2f} €/kWh")
        logger.info(f"  Costo applicato: {costo_acc_applicato:.2f} €/kWh")
    else:
        logger.info("  Nessun sistema di accumulo")

    # -------------------------------------------------------------------------
    # STEP 4: Calcolo percentuale e maggiorazioni
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Calcolo percentuale e maggiorazioni")

    percentuale_base = get_percentuale_spesa(tipo_soggetto)
    maggiorazione = get_maggiorazione_registro(registro_tecnologie)
    percentuale_totale = percentuale_base + maggiorazione

    logger.info(f"  Percentuale base ({tipo_soggetto}): {percentuale_base * 100:.0f}%")
    logger.info(f"  Maggiorazione registro: +{maggiorazione * 100:.0f}%")
    logger.info(f"  Percentuale totale: {percentuale_totale * 100:.0f}%")

    # -------------------------------------------------------------------------
    # STEP 5: Calcolo incentivo lordo
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Calcolo incentivo lordo")

    # Incentivo FV = %_spesa × C_FTV × P_FTV
    incentivo_fv_lordo = percentuale_totale * costo_fv_applicato * potenza_fv_kw

    # Incentivo accumulo = %_spesa × C_ACC × C_ACCUMULO
    incentivo_acc_lordo = percentuale_totale * costo_acc_applicato * capacita_accumulo_kwh

    # Incentivo totale lordo
    incentivo_totale_lordo = incentivo_fv_lordo + incentivo_acc_lordo

    logger.info(f"  Incentivo FV: {percentuale_totale} × {costo_fv_applicato:.2f} × {potenza_fv_kw} = {incentivo_fv_lordo:.2f} €")
    logger.info(f"  Incentivo accumulo: {percentuale_totale} × {costo_acc_applicato:.2f} × {capacita_accumulo_kwh} = {incentivo_acc_lordo:.2f} €")
    logger.info(f"  Incentivo totale lordo: {incentivo_totale_lordo:.2f} €")

    # -------------------------------------------------------------------------
    # STEP 6: Applicazione limite PdC abbinata
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 6] Applicazione limite PdC abbinata")

    # L'incentivo FV non può superare l'incentivo della PdC abbinata
    incentivo_totale = min(incentivo_totale_lordo, incentivo_pdc_abbinata)

    taglio_applicato = incentivo_totale_lordo > incentivo_pdc_abbinata
    importo_tagliato = incentivo_totale_lordo - incentivo_totale if taglio_applicato else 0

    logger.info(f"  Limite PdC abbinata: {incentivo_pdc_abbinata:.2f} €")
    logger.info(f"  Incentivo finale: min({incentivo_totale_lordo:.2f}, {incentivo_pdc_abbinata:.2f}) = {incentivo_totale:.2f} €")

    if taglio_applicato:
        logger.warning(f"  TAGLIO APPLICATO: -{importo_tagliato:.2f} € per limite PdC")

    # -------------------------------------------------------------------------
    # STEP 7: Calcolo erogazione
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 7] Calcolo erogazione")

    erogazione = calcola_erogazione_fv(incentivo_totale, potenza_pdc_kw)

    logger.info(f"  Modalità: {erogazione['modalita']}")
    logger.info(f"  Numero rate: {erogazione['numero_rate']}")
    logger.info(f"  Importo rata: {erogazione['rate'][0]:.2f} €")

    # -------------------------------------------------------------------------
    # OUTPUT FINALE
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("CALCOLO COMPLETATO")
    logger.info(f"INCENTIVO TOTALE FV COMBINATO: {incentivo_totale:.2f} €")
    logger.info("=" * 60)

    calcoli_intermedi: CalcoliIntermediFV = {
        "costo_specifico_fv": round(costo_specifico_fv, 2),
        "costo_max_fv": costo_max_fv,
        "costo_specifico_acc": round(costo_specifico_acc, 2),
        "costo_max_acc": COSTO_MAX_ACCUMULO,
        "percentuale_spesa": percentuale_totale,
        "incentivo_fv_lordo": round(incentivo_fv_lordo, 2),
        "incentivo_acc_lordo": round(incentivo_acc_lordo, 2),
        "incentivo_totale_lordo": round(incentivo_totale_lordo, 2),
        "limite_pdc": incentivo_pdc_abbinata,
        "maggiorazione_registro": maggiorazione
    }

    massimali = {
        "spesa_fv_ammissibile": round(costo_fv_applicato * potenza_fv_kw, 2),
        "spesa_acc_ammissibile": round(costo_acc_applicato * capacita_accumulo_kwh, 2),
        "percentuale_applicata": percentuale_totale,
        "taglio_applicato": taglio_applicato,
        "importo_tagliato": round(importo_tagliato, 2)
    }

    return {
        "status": "OK",
        "messaggio": "Calcolo completato con successo",
        "input_riepilogo": input_riepilogo,
        "calcoli_intermedi": calcoli_intermedi,
        "incentivo_totale": round(incentivo_totale, 2),
        "erogazione": erogazione,
        "massimali_applicati": massimali
    }


# ============================================================================
# FUNZIONI AUSILIARIE
# ============================================================================

def verifica_dimensionamento_fv(
    potenza_fv_kw: float,
    produzione_annua_kwh: float,
    fabbisogno_elettrico_kwh: float,
    fabbisogno_termico_equiv_kwh: float = 0.0
) -> dict:
    """
    Verifica il corretto dimensionamento dell'impianto FV in assetto autoconsumo.

    Rif. Par. 9.8.1: L'energia prodotta non deve superare il 105% del fabbisogno.

    Args:
        potenza_fv_kw: Potenza FV installata
        produzione_annua_kwh: Produzione annua stimata (da PVGIS)
        fabbisogno_elettrico_kwh: Fabbisogno elettrico annuo dell'edificio
        fabbisogno_termico_equiv_kwh: Fabbisogno termico convertito in kWh elettrici

    Returns:
        Dizionario con esito verifica e dettagli
    """
    fabbisogno_totale = fabbisogno_elettrico_kwh + fabbisogno_termico_equiv_kwh
    limite_produzione = fabbisogno_totale * 1.05  # 105%

    rapporto = (produzione_annua_kwh / fabbisogno_totale * 100) if fabbisogno_totale > 0 else 0

    ammissibile = produzione_annua_kwh <= limite_produzione

    return {
        "ammissibile": ammissibile,
        "fabbisogno_totale_kwh": round(fabbisogno_totale, 2),
        "limite_produzione_kwh": round(limite_produzione, 2),
        "produzione_stimata_kwh": round(produzione_annua_kwh, 2),
        "rapporto_percentuale": round(rapporto, 1),
        "messaggio": "OK - Dimensionamento corretto" if ammissibile
                     else f"ERRORE - Produzione ({rapporto:.1f}%) supera il 105% del fabbisogno"
    }


def calcola_fabbisogno_equivalente(
    consumo_combustibile_kg: float = 0.0,
    tipo_combustibile: str = "metano"
) -> float:
    """
    Converte il fabbisogno termico in kWh elettrici equivalenti.

    Args:
        consumo_combustibile_kg: Consumo annuo combustibile in kg (o Sm³ per metano)
        tipo_combustibile: "metano", "gpl", "gasolio", "pellet"

    Returns:
        kWh elettrici equivalenti
    """
    # PCI tipici (kWh/unità)
    pci = {
        "metano": 9.97,    # kWh/Sm³
        "gpl": 12.8,       # kWh/kg
        "gasolio": 11.9,   # kWh/kg
        "pellet": 4.7      # kWh/kg
    }

    # Rendimento medio caldaia tradizionale
    rendimento_caldaia = 0.85

    # COP medio pompa di calore
    cop_pdc = 3.5

    if tipo_combustibile not in pci:
        return 0.0

    # Energia termica prodotta dalla caldaia
    energia_termica = consumo_combustibile_kg * pci[tipo_combustibile] * rendimento_caldaia

    # Energia elettrica equivalente con PdC
    energia_elettrica_equiv = energia_termica / cop_pdc

    return round(energia_elettrica_equiv, 2)


# ============================================================================
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    import json

    print("\n" + "=" * 70)
    print("ESEMPIO: Impianto FV 6 kW + Accumulo 10 kWh abbinato a PdC")
    print("=" * 70)

    risultato = calculate_fv_combined_incentive(
        potenza_fv_kw=6.0,
        spesa_fv=9000.0,           # 1500 €/kW
        capacita_accumulo_kwh=10.0,
        spesa_accumulo=8000.0,     # 800 €/kWh
        incentivo_pdc_abbinata=5000.0,  # Limite dalla PdC
        potenza_pdc_kw=10.0,
        tipo_soggetto="privato",
        registro_tecnologie="sezione_a"  # +5%
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("ESEMPIO: Verifica dimensionamento")
    print("=" * 70)

    verifica = verifica_dimensionamento_fv(
        potenza_fv_kw=6.0,
        produzione_annua_kwh=7200.0,  # ~1200 kWh/kW
        fabbisogno_elettrico_kwh=4000.0,
        fabbisogno_termico_equiv_kwh=3000.0
    )

    print("\nVERIFICA DIMENSIONAMENTO:")
    print(json.dumps(verifica, indent=2, ensure_ascii=False))
