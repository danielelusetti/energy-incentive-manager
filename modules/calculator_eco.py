"""
Modulo di calcolo detrazioni Ecobonus per interventi di efficienza energetica.

Riferimento normativo: D.L. 63/2013, Legge di Bilancio 2025, Vademecum ENEA.
Questo modulo implementa il calcolo della detrazione fiscale IRPEF/IRES secondo la formula:
    Detrazione = min(Spesa × Aliquota, Limite_Detrazione_Massima)

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Optional, TypedDict, Literal
from datetime import date

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

TipoIntervento = Literal[
    "pompe_di_calore",
    "caldaie_condensazione_classe_A",
    "caldaie_condensazione_classe_A_evoluta",
    "sistemi_ibridi",
    "solare_termico",
    "coibentazione_involucro",
    "serramenti_infissi",
    "schermature_solari",      # Tende da sole, schermature solari, pellicole
    "riqualificazione_globale",
    "microcogeneratori",
    "generatori_biomassa",
    "building_automation",
    "fotovoltaico",           # Bonus Ristrutturazione (non Ecobonus)
    "fotovoltaico_accumulo"   # FV + sistema di accumulo
]

TipoAbitazione = Literal["abitazione_principale", "altra_abitazione"]


class InputRiepilogo(TypedDict):
    tipo_intervento: str
    anno_spesa: int
    tipo_abitazione: str
    spesa_sostenuta: float


class CalcoliIntermedi(TypedDict):
    aliquota_applicata: float
    limite_detrazione: float
    detrazione_lorda: float
    detrazione_effettiva: float
    rata_annuale: float
    anni_recupero: int


class RisultatoCalcoloEco(TypedDict):
    status: Literal["OK", "ERROR", "WARNING"]
    messaggio: str
    input_riepilogo: InputRiepilogo
    calcoli: Optional[CalcoliIntermedi]
    detrazione_totale: Optional[float]
    piano_rate: Optional[list[float]]


# ============================================================================
# COSTANTI E DATI
# ============================================================================

# Aliquote per anno e tipo abitazione (Legge di Bilancio 2025)
ALIQUOTE: dict = {
    2024: {
        "pompe_di_calore": {"standard": 0.65},
        "caldaie_condensazione_classe_A": {"standard": 0.50},
        "caldaie_condensazione_classe_A_evoluta": {"standard": 0.65},
        "sistemi_ibridi": {"standard": 0.65},
        "solare_termico": {"standard": 0.65},
        "coibentazione_involucro": {"standard": 0.65},
        "serramenti_infissi": {"standard": 0.50},
        "schermature_solari": {"standard": 0.50},  # Ecobonus schermature
        "riqualificazione_globale": {"standard": 0.65},
        "microcogeneratori": {"standard": 0.65},
        "generatori_biomassa": {"standard": 0.50},
        "building_automation": {"standard": 0.65},
        # Fotovoltaico: Bonus Ristrutturazione (50% nel 2024)
        "fotovoltaico": {"standard": 0.50},
        "fotovoltaico_accumulo": {"standard": 0.50},
    },
    2025: {
        "abitazione_principale": 0.50,
        "altra_abitazione": 0.36,
    },
    2026: {
        "abitazione_principale": 0.50,
        "altra_abitazione": 0.36,
    },
    2027: {
        "abitazione_principale": 0.36,
        "altra_abitazione": 0.30,
    },
    2028: {
        "abitazione_principale": 0.36,
        "altra_abitazione": 0.30,
    },
}

# Limiti di detrazione massima per tipo intervento (invariati)
# Per il fotovoltaico: limite di spesa 96.000€ (Bonus Ristrutturazione)
LIMITI_DETRAZIONE: dict[str, float] = {
    "pompe_di_calore": 30000.0,
    "caldaie_condensazione_classe_A": 30000.0,
    "caldaie_condensazione_classe_A_evoluta": 30000.0,
    "sistemi_ibridi": 30000.0,
    "solare_termico": 60000.0,
    "coibentazione_involucro": 60000.0,
    "serramenti_infissi": 60000.0,
    "schermature_solari": 60000.0,  # Stesso limite serramenti
    "riqualificazione_globale": 100000.0,
    "microcogeneratori": 100000.0,
    "generatori_biomassa": 30000.0,
    "building_automation": 15000.0,
    # Fotovoltaico: limite spesa 96.000€ -> detrazione max 48.000€ al 50%
    "fotovoltaico": 48000.0,
    "fotovoltaico_accumulo": 48000.0,  # Stesso limite, accumulo incluso
}

# Interventi esclusi dal 2025 (Legge di Bilancio 2025)
INTERVENTI_ESCLUSI_2025: list[str] = [
    "caldaie_condensazione_classe_A",
    "caldaie_condensazione_classe_A_evoluta",
]

# Anni di recupero (sempre 10)
ANNI_RECUPERO: int = 10


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
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File JSON non trovato: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_intervento_escluso(tipo_intervento: str, anno: int) -> bool:
    """
    Verifica se l'intervento è escluso dall'Ecobonus per l'anno indicato.

    Riferimento: Legge di Bilancio 2025 - Esclusione caldaie a combustibili fossili

    Args:
        tipo_intervento: Tipo di intervento
        anno: Anno della spesa

    Returns:
        True se l'intervento è escluso
    """
    if anno >= 2025 and tipo_intervento in INTERVENTI_ESCLUSI_2025:
        return True
    return False


def get_aliquota(
    tipo_intervento: str,
    anno: int,
    tipo_abitazione: str = "abitazione_principale"
) -> float:
    """
    Recupera l'aliquota di detrazione applicabile.

    Riferimento: Legge di Bilancio 2025 - Nuove aliquote differenziate

    Args:
        tipo_intervento: Tipo di intervento
        anno: Anno della spesa
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"

    Returns:
        Aliquota di detrazione (es. 0.50 per 50%)
    """
    # Anno 2024: regime precedente con aliquote specifiche per intervento
    if anno <= 2024:
        if anno in ALIQUOTE and tipo_intervento in ALIQUOTE[anno]:
            return ALIQUOTE[anno][tipo_intervento].get("standard", 0.50)
        return 0.50  # Default

    # Anni 2025-2028: aliquote dipendenti dal tipo di abitazione
    if anno in ALIQUOTE:
        return ALIQUOTE[anno].get(tipo_abitazione, 0.36)

    # Anni successivi: assumiamo le aliquote 2028
    return ALIQUOTE[2028].get(tipo_abitazione, 0.30)


def get_limite_detrazione(tipo_intervento: str) -> float:
    """
    Recupera il limite massimo di detrazione per il tipo di intervento.

    Args:
        tipo_intervento: Tipo di intervento

    Returns:
        Limite di detrazione in euro
    """
    return LIMITI_DETRAZIONE.get(tipo_intervento, 30000.0)


# ============================================================================
# BONUS RISTRUTTURAZIONE - ALIQUOTE E LIMITI
# ============================================================================

# Aliquote Bonus Ristrutturazione per anno e tipo abitazione
ALIQUOTE_BONUS_RISTRUTT: dict = {
    2024: {
        "abitazione_principale": 0.50,
        "altra_abitazione": 0.50,
    },
    2025: {
        "abitazione_principale": 0.50,
        "altra_abitazione": 0.36,
    },
    2026: {
        "abitazione_principale": 0.50,
        "altra_abitazione": 0.36,
    },
    2027: {
        "abitazione_principale": 0.36,
        "altra_abitazione": 0.30,
    },
}

# Limite di spesa per Bonus Ristrutturazione: 96.000€ per unità immobiliare
LIMITE_SPESA_BONUS_RISTRUTT: float = 96000.0

# Anni di recupero Bonus Ristrutturazione: sempre 10
ANNI_RECUPERO_BONUS_RISTRUTT: int = 10

# Interventi ammessi al Bonus Ristrutturazione che riguardano risparmio energetico
# (richiedono comunicazione ENEA)
INTERVENTI_BONUS_RISTRUTT_ENEA: list[str] = [
    "coibentazione_involucro",  # Isolamento termico
    "serramenti_infissi",
    "caldaie_condensazione_classe_A",
    "pompe_di_calore",
    "sistemi_ibridi",
    "solare_termico",
    "fotovoltaico",
    "fotovoltaico_accumulo",
    "generatori_biomassa",
]


# ============================================================================
# FUNZIONE PRINCIPALE DI CALCOLO
# ============================================================================

def calculate_ecobonus_deduction(
    tipo_intervento: str,
    spesa_sostenuta: float,
    anno_spesa: int = None,
    tipo_abitazione: str = "abitazione_principale",
    json_path: Optional[str] = None
) -> RisultatoCalcoloEco:
    """
    Calcola la detrazione Ecobonus per un intervento di efficienza energetica.

    Implementa la formula:
        Detrazione = min(Spesa × Aliquota, Limite_Detrazione_Massima)

    La detrazione è ripartita in 10 rate annuali di pari importo.

    Args:
        tipo_intervento: Tipo di intervento (es. "pompe_di_calore", "sistemi_ibridi")
        spesa_sostenuta: Spesa totale sostenuta in euro (IVA inclusa)
        anno_spesa: Anno in cui è sostenuta la spesa (default: anno corrente)
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"
        json_path: Percorso al file JSON con le regole (opzionale)

    Returns:
        RisultatoCalcoloEco con tutti i dettagli del calcolo
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO DETRAZIONE ECOBONUS")
    logger.info("=" * 60)

    # Default anno corrente
    if anno_spesa is None:
        anno_spesa = date.today().year

    # Preparazione input
    input_riepilogo: InputRiepilogo = {
        "tipo_intervento": tipo_intervento,
        "anno_spesa": anno_spesa,
        "tipo_abitazione": tipo_abitazione,
        "spesa_sostenuta": spesa_sostenuta
    }

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")

    if spesa_sostenuta <= 0:
        return {
            "status": "ERROR",
            "messaggio": "La spesa sostenuta deve essere > 0",
            "input_riepilogo": input_riepilogo,
            "calcoli": None,
            "detrazione_totale": None,
            "piano_rate": None
        }

    if tipo_abitazione not in ["abitazione_principale", "altra_abitazione"]:
        tipo_abitazione = "abitazione_principale"
        logger.warning(f"Tipo abitazione non valido, uso default: {tipo_abitazione}")

    logger.info(f"  Tipo intervento: {tipo_intervento}")
    logger.info(f"  Anno spesa: {anno_spesa}")
    logger.info(f"  Tipo abitazione: {tipo_abitazione}")
    logger.info(f"  Spesa sostenuta: {spesa_sostenuta:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 2: Verifica esclusione intervento (dal 2025)
    # Riferimento: Legge di Bilancio 2025
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Verifica ammissibilita' intervento")

    if is_intervento_escluso(tipo_intervento, anno_spesa):
        msg = (f"Intervento NON ammesso: dal 2025 le caldaie a condensazione "
               f"alimentate solo a combustibili fossili sono escluse dall'Ecobonus. "
               f"Considerare sistemi ibridi o pompe di calore.")
        logger.error(f"  ESCLUSO: {msg}")
        return {
            "status": "ERROR",
            "messaggio": msg,
            "input_riepilogo": input_riepilogo,
            "calcoli": None,
            "detrazione_totale": None,
            "piano_rate": None
        }

    logger.info("  OK: Intervento ammesso")

    # -------------------------------------------------------------------------
    # STEP 3: Determinazione aliquota
    # Riferimento: Legge di Bilancio 2025 - Art. 1
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Determinazione aliquota")

    aliquota = get_aliquota(tipo_intervento, anno_spesa, tipo_abitazione)

    logger.info(f"  Anno: {anno_spesa}")
    logger.info(f"  Tipo abitazione: {tipo_abitazione}")
    logger.info(f"  Aliquota applicata: {aliquota * 100:.0f}%")

    # -------------------------------------------------------------------------
    # STEP 4: Determinazione limite detrazione
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Determinazione limite detrazione")

    limite_detrazione = get_limite_detrazione(tipo_intervento)
    logger.info(f"  Limite detrazione massima: {limite_detrazione:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 5: Calcolo detrazione
    # Formula: Detrazione = min(Spesa × Aliquota, Limite)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Calcolo detrazione")

    detrazione_lorda = spesa_sostenuta * aliquota
    detrazione_effettiva = min(detrazione_lorda, limite_detrazione)

    logger.info(f"  Detrazione lorda: {spesa_sostenuta:.2f} x {aliquota} = {detrazione_lorda:.2f} EUR")
    logger.info(f"  Limite applicato: {limite_detrazione:.2f} EUR")
    logger.info(f"  DETRAZIONE EFFETTIVA: min({detrazione_lorda:.2f}, {limite_detrazione:.2f}) = {detrazione_effettiva:.2f} EUR")

    if detrazione_lorda > limite_detrazione:
        logger.warning(f"  ATTENZIONE: Detrazione ridotta per superamento limite massimo")

    # -------------------------------------------------------------------------
    # STEP 6: Calcolo piano rate (10 anni)
    # Riferimento: Art. 14 D.L. 63/2013
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 6] Calcolo piano rate")

    rata_annuale = detrazione_effettiva / ANNI_RECUPERO
    piano_rate = [round(rata_annuale, 2)] * ANNI_RECUPERO

    logger.info(f"  Anni di recupero: {ANNI_RECUPERO}")
    logger.info(f"  Rata annuale: {detrazione_effettiva:.2f} / {ANNI_RECUPERO} = {rata_annuale:.2f} EUR")

    # -------------------------------------------------------------------------
    # OUTPUT FINALE
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"DETRAZIONE TOTALE: {detrazione_effettiva:.2f} EUR")
    logger.info(f"RATA ANNUALE: {rata_annuale:.2f} EUR x {ANNI_RECUPERO} anni")
    logger.info("=" * 60)

    calcoli: CalcoliIntermedi = {
        "aliquota_applicata": aliquota,
        "limite_detrazione": limite_detrazione,
        "detrazione_lorda": round(detrazione_lorda, 2),
        "detrazione_effettiva": round(detrazione_effettiva, 2),
        "rata_annuale": round(rata_annuale, 2),
        "anni_recupero": ANNI_RECUPERO
    }

    return {
        "status": "OK",
        "messaggio": "Calcolo completato con successo",
        "input_riepilogo": input_riepilogo,
        "calcoli": calcoli,
        "detrazione_totale": round(detrazione_effettiva, 2),
        "piano_rate": piano_rate
    }


def confronta_ecobonus_anni(
    tipo_intervento: str,
    spesa_sostenuta: float,
    tipo_abitazione: str = "abitazione_principale"
) -> dict:
    """
    Confronta la detrazione Ecobonus tra diversi anni.

    Utile per mostrare l'impatto delle nuove aliquote.

    Args:
        tipo_intervento: Tipo di intervento
        spesa_sostenuta: Spesa sostenuta
        tipo_abitazione: Tipo di abitazione

    Returns:
        Dizionario con confronto tra anni
    """
    risultati = {}

    for anno in [2024, 2025, 2026, 2027]:
        risultato = calculate_ecobonus_deduction(
            tipo_intervento=tipo_intervento,
            spesa_sostenuta=spesa_sostenuta,
            anno_spesa=anno,
            tipo_abitazione=tipo_abitazione
        )

        if risultato["status"] == "OK":
            risultati[anno] = {
                "aliquota": risultato["calcoli"]["aliquota_applicata"],
                "detrazione": risultato["detrazione_totale"],
                "rata_annuale": risultato["calcoli"]["rata_annuale"]
            }
        else:
            risultati[anno] = {
                "aliquota": None,
                "detrazione": None,
                "rata_annuale": None,
                "escluso": True,
                "motivo": risultato["messaggio"]
            }

    return risultati


def calculate_bonus_ristrutturazione(
    tipo_intervento: str,
    spesa_sostenuta: float,
    anno_spesa: int = None,
    tipo_abitazione: str = "abitazione_principale"
) -> RisultatoCalcoloEco:
    """
    Calcola la detrazione Bonus Ristrutturazione per interventi di ristrutturazione edilizia.

    Riferimento normativo: Art. 16-bis TUIR, Legge di Bilancio 2025.

    IMPORTANTE: Il Bonus Ristrutturazione NON è cumulabile con l'Ecobonus.
    Il contribuente deve scegliere quale detrazione applicare.

    Implementa la formula:
        Detrazione = min(Spesa_Sostenuta, 96.000€) × Aliquota

    La detrazione è ripartita in 10 rate annuali di pari importo.

    Aliquote:
    - 2024: 50% (prima casa e altre abitazioni)
    - 2025-2026: 50% prima casa, 36% altre abitazioni
    - 2027 in poi: 36% prima casa, 30% altre abitazioni

    Args:
        tipo_intervento: Tipo di intervento (es. "coibentazione_involucro", "fotovoltaico")
        spesa_sostenuta: Spesa totale sostenuta in euro (IVA inclusa)
        anno_spesa: Anno in cui è sostenuta la spesa (default: anno corrente)
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"

    Returns:
        RisultatoCalcoloEco con tutti i dettagli del calcolo
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO DETRAZIONE BONUS RISTRUTTURAZIONE")
    logger.info("=" * 60)

    # Default anno corrente
    if anno_spesa is None:
        anno_spesa = date.today().year

    # Preparazione input
    input_riepilogo: InputRiepilogo = {
        "tipo_intervento": tipo_intervento,
        "anno_spesa": anno_spesa,
        "tipo_abitazione": tipo_abitazione,
        "spesa_sostenuta": spesa_sostenuta
    }

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")

    if spesa_sostenuta <= 0:
        return {
            "status": "ERROR",
            "messaggio": "La spesa sostenuta deve essere > 0",
            "input_riepilogo": input_riepilogo,
            "calcoli": None,
            "detrazione_totale": None,
            "piano_rate": None
        }

    if tipo_abitazione not in ["abitazione_principale", "altra_abitazione"]:
        tipo_abitazione = "abitazione_principale"
        logger.warning(f"Tipo abitazione non valido, uso default: {tipo_abitazione}")

    logger.info(f"  Tipo intervento: {tipo_intervento}")
    logger.info(f"  Anno spesa: {anno_spesa}")
    logger.info(f"  Tipo abitazione: {tipo_abitazione}")
    logger.info(f"  Spesa sostenuta: {spesa_sostenuta:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 2: Verifica comunicazione ENEA (se intervento energetico)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Verifica requisiti comunicazione ENEA")

    richiede_enea = tipo_intervento in INTERVENTI_BONUS_RISTRUTT_ENEA

    if richiede_enea:
        logger.info(f"  ATTENZIONE: Intervento '{tipo_intervento}' richiede comunicazione ENEA entro 90 giorni")
    else:
        logger.info(f"  OK: Intervento non richiede comunicazione ENEA")

    # -------------------------------------------------------------------------
    # STEP 3: Determinazione aliquota
    # Riferimento: Legge di Bilancio 2025 - Art. 1
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Determinazione aliquota")

    # Recupera aliquota per anno e tipo abitazione
    if anno_spesa in ALIQUOTE_BONUS_RISTRUTT:
        aliquota = ALIQUOTE_BONUS_RISTRUTT[anno_spesa].get(tipo_abitazione, 0.36)
    else:
        # Anni successivi al 2027: usa le aliquote 2027
        aliquota = ALIQUOTE_BONUS_RISTRUTT[2027].get(tipo_abitazione, 0.30)

    logger.info(f"  Anno: {anno_spesa}")
    logger.info(f"  Tipo abitazione: {tipo_abitazione}")
    logger.info(f"  Aliquota applicata: {aliquota * 100:.0f}%")

    # -------------------------------------------------------------------------
    # STEP 4: Applicazione limite di spesa
    # Riferimento: Limite 96.000€ per unità immobiliare
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Applicazione limite di spesa")

    spesa_ammissibile = min(spesa_sostenuta, LIMITE_SPESA_BONUS_RISTRUTT)

    logger.info(f"  Limite spesa massima: {LIMITE_SPESA_BONUS_RISTRUTT:.2f} EUR")
    logger.info(f"  Spesa sostenuta: {spesa_sostenuta:.2f} EUR")
    logger.info(f"  Spesa ammissibile: {spesa_ammissibile:.2f} EUR")

    if spesa_sostenuta > LIMITE_SPESA_BONUS_RISTRUTT:
        logger.warning(f"  ATTENZIONE: Spesa ridotta per superamento limite massimo")

    # -------------------------------------------------------------------------
    # STEP 5: Calcolo detrazione
    # Formula: Detrazione = Spesa_Ammissibile × Aliquota
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Calcolo detrazione")

    detrazione_totale = spesa_ammissibile * aliquota
    limite_detrazione_max = LIMITE_SPESA_BONUS_RISTRUTT * aliquota

    logger.info(f"  Detrazione: {spesa_ammissibile:.2f} × {aliquota} = {detrazione_totale:.2f} EUR")
    logger.info(f"  Detrazione massima teorica: {limite_detrazione_max:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 6: Calcolo piano rate (10 anni)
    # Riferimento: Art. 16-bis TUIR
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 6] Calcolo piano rate")

    rata_annuale = detrazione_totale / ANNI_RECUPERO_BONUS_RISTRUTT
    piano_rate = [round(rata_annuale, 2)] * ANNI_RECUPERO_BONUS_RISTRUTT

    logger.info(f"  Anni di recupero: {ANNI_RECUPERO_BONUS_RISTRUTT}")
    logger.info(f"  Rata annuale: {detrazione_totale:.2f} / {ANNI_RECUPERO_BONUS_RISTRUTT} = {rata_annuale:.2f} EUR")

    # -------------------------------------------------------------------------
    # OUTPUT FINALE
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"DETRAZIONE TOTALE: {detrazione_totale:.2f} EUR")
    logger.info(f"RATA ANNUALE: {rata_annuale:.2f} EUR x {ANNI_RECUPERO_BONUS_RISTRUTT} anni")
    logger.info("ATTENZIONE: NON cumulabile con Ecobonus")
    if richiede_enea:
        logger.info("PROMEMORIA: Comunicazione ENEA entro 90 giorni dalla fine lavori")
    logger.info("=" * 60)

    calcoli: CalcoliIntermedi = {
        "aliquota_applicata": aliquota,
        "limite_detrazione": limite_detrazione_max,
        "detrazione_lorda": round(detrazione_totale, 2),
        "detrazione_effettiva": round(detrazione_totale, 2),
        "rata_annuale": round(rata_annuale, 2),
        "anni_recupero": ANNI_RECUPERO_BONUS_RISTRUTT
    }

    messaggio = "Calcolo completato con successo"
    if richiede_enea:
        messaggio += " - RICHIEDE comunicazione ENEA entro 90 giorni"

    return {
        "status": "OK",
        "messaggio": messaggio,
        "input_riepilogo": input_riepilogo,
        "calcoli": calcoli,
        "detrazione_totale": round(detrazione_totale, 2),
        "piano_rate": piano_rate
    }


# ============================================================================
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ESEMPIO 1: Pompa di calore - Abitazione principale 2025")
    print("=" * 70)

    risultato1 = calculate_ecobonus_deduction(
        tipo_intervento="pompe_di_calore",
        spesa_sostenuta=20000.0,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale"
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato1, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("ESEMPIO 2: Caldaia a condensazione - Anno 2025 (ESCLUSA)")
    print("=" * 70)

    risultato2 = calculate_ecobonus_deduction(
        tipo_intervento="caldaie_condensazione_classe_A",
        spesa_sostenuta=8000.0,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale"
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato2, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("ESEMPIO 3: Confronto anni per Sistema Ibrido")
    print("=" * 70)

    confronto = confronta_ecobonus_anni(
        tipo_intervento="sistemi_ibridi",
        spesa_sostenuta=15000.0,
        tipo_abitazione="abitazione_principale"
    )

    print("\nCONFRONTO ANNI:")
    for anno, dati in confronto.items():
        if dati.get("escluso"):
            print(f"  {anno}: ESCLUSO - {dati['motivo']}")
        else:
            print(f"  {anno}: Aliquota {dati['aliquota']*100:.0f}% -> Detrazione {dati['detrazione']:.2f} EUR ({dati['rata_annuale']:.2f} EUR/anno)")
