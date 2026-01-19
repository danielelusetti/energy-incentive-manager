"""
Modulo per il calcolo degli incentivi per l'intervento II.C
Installazione di sistemi di schermatura e/o ombreggiamento

Include confronto con Ecobonus (NO Bonus Ristrutturazione - non applicabile)

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.3
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import logging
import sys
import os

# Aggiungi parent directory al path per import quando eseguito come script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from modules.calculator_eco import calculate_ecobonus_deduction


# ==============================================================================
# TABELLE DI RIFERIMENTO (da Regole Applicative CT 3.0 - Par. 9.3)
# ==============================================================================

# Tabella 18 - Allegato 2 DM 7/8/2025
PARAMETRI_SCHERMATURE = {
    "schermature": {
        "percentuale_incentivo": 0.40,  # 40% (100% per PA art. 11 comma 2)
        "costo_max_mq": 250.0,  # €/m²
        "incentivo_max": 90000.0  # €
    },
    "automazione": {
        "percentuale_incentivo": 0.40,  # 40% (100% per PA art. 11 comma 2)
        "costo_max_mq": 50.0,  # €/m²
        "incentivo_max": 10000.0  # €
    },
    "pellicole_non_riflettenti": {
        "percentuale_incentivo": 0.40,  # 40% (100% per PA art. 11 comma 2)
        "costo_max_mq": 130.0,  # €/m²
        "incentivo_max": 30000.0  # €
    },
    "pellicole_riflettenti": {
        "percentuale_incentivo": 0.40,  # 40% (100% per PA art. 11 comma 2)
        "costo_max_mq": 80.0,  # €/m²
        "incentivo_max": 30000.0  # €
    }
}

# Massimale complessivo
MASSIMALE_TOTALE = 500000.0  # € (art. 6 del Decreto)

# Soglia rata unica
SOGLIA_RATA_UNICA = 15000.0  # €

# Anni rateazione
ANNI_RATEAZIONE = 5


@dataclass
class RisultatoCalcoloSchermature:
    """Risultato del calcolo per un singolo tipo di intervento"""
    tipo: str  # "schermature", "automazione", "pellicole"
    superficie_mq: float
    spesa_sostenuta: float
    costo_specifico: float  # €/m²
    costo_max_ammissibile: float  # €/m²
    spesa_ammissibile: float
    percentuale_incentivo: float
    incentivo_lordo: float
    incentivo_effettivo: float  # Dopo massimale specifico
    incentivo_max: float
    note: str


def calculate_shading_incentive(
    # Tipologie installate
    installa_schermature: bool = False,
    superficie_schermature_mq: float = 0.0,
    spesa_schermature: float = 0.0,

    installa_automazione: bool = False,
    superficie_automazione_mq: float = 0.0,
    spesa_automazione: float = 0.0,

    installa_pellicole: bool = False,
    tipo_pellicola: str = "selettiva_non_riflettente",  # o "selettiva_riflettente"
    superficie_pellicole_mq: float = 0.0,
    spesa_pellicole: float = 0.0,

    # Tipo soggetto
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    tipo_edificio: str = "residenziale",  # "residenziale", "pubblico"

    # Premialità componenti UE (+10%)
    usa_premialita_componenti_ue: bool = False

) -> Dict:
    """
    Calcola l'incentivo CT 3.0 per schermature solari (II.C)

    Formula (per ciascuna tipologia):
    I = %_spesa × C × S_int

    con:
    - C = min(C_effettivo, C_max)
    - C_effettivo = spesa / superficie
    - I_tot ≤ I_max (per tipologia)
    - I_complessivo ≤ 500,000€

    Returns:
        Dict con chiavi:
        - status: "OK" o "ERROR"
        - incentivo_totale: float
        - dettagli_schermature: RisultatoCalcoloSchermature o None
        - dettagli_automazione: RisultatoCalcoloSchermature o None
        - dettagli_pellicole: RisultatoCalcoloSchermature o None
        - incentivo_con_premialita: float
        - annualita: int
        - rata_annuale: float
        - messaggio: str
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO INCENTIVO CT 3.0 - SCHERMATURE SOLARI (II.C)")
    logger.info("=" * 60)

    risultati_parziali = []
    incentivo_totale = 0.0

    # Determina percentuale incentivo in base al tipo soggetto
    # PA su edifici pubblici: 100% (art. 11 comma 2)
    percentuale_base = 1.0 if (tipo_soggetto == "pa" and tipo_edificio == "pubblico") else 0.4

    logger.info(f"Tipo soggetto: {tipo_soggetto}")
    logger.info(f"Tipo edificio: {tipo_edificio}")
    logger.info(f"Percentuale incentivo: {percentuale_base * 100:.0f}%")
    logger.info("")

    # =========================================================================
    # 1. SCHERMATURE FISSE/MOBILI
    # =========================================================================
    if installa_schermature:
        logger.info("[CALCOLO SCHERMATURE FISSE/MOBILI]")
        logger.info(f"  Superficie: {superficie_schermature_mq:.2f} m²")
        logger.info(f"  Spesa sostenuta: {spesa_schermature:,.2f} €")

        params = PARAMETRI_SCHERMATURE["schermature"]
        costo_effettivo = spesa_schermature / superficie_schermature_mq if superficie_schermature_mq > 0 else 0
        costo_ammissibile = min(costo_effettivo, params["costo_max_mq"])

        logger.info(f"  Costo specifico: {costo_effettivo:.2f} €/m² (max: {params['costo_max_mq']:.2f} €/m²)")

        spesa_ammissibile = costo_ammissibile * superficie_schermature_mq
        incentivo_lordo = percentuale_base * spesa_ammissibile
        incentivo_effettivo = min(incentivo_lordo, params["incentivo_max"])

        logger.info(f"  Spesa ammissibile: {spesa_ammissibile:,.2f} €")
        logger.info(f"  Incentivo lordo: {incentivo_lordo:,.2f} €")
        logger.info(f"  Massimale tipologia: {params['incentivo_max']:,.2f} €")
        logger.info(f"  Incentivo effettivo: {incentivo_effettivo:,.2f} €")

        note = ""
        if costo_effettivo > params["costo_max_mq"]:
            note = f"Costo specifico limitato a {params['costo_max_mq']:.2f} €/m²"
        if incentivo_lordo > params["incentivo_max"]:
            note += f" | Incentivo limitato a massimale {params['incentivo_max']:,.2f} €"

        risultati_parziali.append(RisultatoCalcoloSchermature(
            tipo="schermature",
            superficie_mq=superficie_schermature_mq,
            spesa_sostenuta=spesa_schermature,
            costo_specifico=costo_effettivo,
            costo_max_ammissibile=params["costo_max_mq"],
            spesa_ammissibile=spesa_ammissibile,
            percentuale_incentivo=percentuale_base,
            incentivo_lordo=incentivo_lordo,
            incentivo_effettivo=incentivo_effettivo,
            incentivo_max=params["incentivo_max"],
            note=note.strip(" |")
        ))

        incentivo_totale += incentivo_effettivo
        logger.info("")

    # =========================================================================
    # 2. AUTOMAZIONE (meccanismi automatici regolazione)
    # =========================================================================
    if installa_automazione:
        logger.info("[CALCOLO AUTOMAZIONE]")
        logger.info(f"  Superficie: {superficie_automazione_mq:.2f} m²")
        logger.info(f"  Spesa sostenuta: {spesa_automazione:,.2f} €")

        params = PARAMETRI_SCHERMATURE["automazione"]
        costo_effettivo = spesa_automazione / superficie_automazione_mq if superficie_automazione_mq > 0 else 0
        costo_ammissibile = min(costo_effettivo, params["costo_max_mq"])

        logger.info(f"  Costo specifico: {costo_effettivo:.2f} €/m² (max: {params['costo_max_mq']:.2f} €/m²)")

        spesa_ammissibile = costo_ammissibile * superficie_automazione_mq
        incentivo_lordo = percentuale_base * spesa_ammissibile
        incentivo_effettivo = min(incentivo_lordo, params["incentivo_max"])

        logger.info(f"  Spesa ammissibile: {spesa_ammissibile:,.2f} €")
        logger.info(f"  Incentivo lordo: {incentivo_lordo:,.2f} €")
        logger.info(f"  Massimale tipologia: {params['incentivo_max']:,.2f} €")
        logger.info(f"  Incentivo effettivo: {incentivo_effettivo:,.2f} €")

        note = ""
        if costo_effettivo > params["costo_max_mq"]:
            note = f"Costo specifico limitato a {params['costo_max_mq']:.2f} €/m²"
        if incentivo_lordo > params["incentivo_max"]:
            note += f" | Incentivo limitato a massimale {params['incentivo_max']:,.2f} €"

        risultati_parziali.append(RisultatoCalcoloSchermature(
            tipo="automazione",
            superficie_mq=superficie_automazione_mq,
            spesa_sostenuta=spesa_automazione,
            costo_specifico=costo_effettivo,
            costo_max_ammissibile=params["costo_max_mq"],
            spesa_ammissibile=spesa_ammissibile,
            percentuale_incentivo=percentuale_base,
            incentivo_lordo=incentivo_lordo,
            incentivo_effettivo=incentivo_effettivo,
            incentivo_max=params["incentivo_max"],
            note=note.strip(" |")
        ))

        incentivo_totale += incentivo_effettivo
        logger.info("")

    # =========================================================================
    # 3. PELLICOLE SOLARI
    # =========================================================================
    if installa_pellicole:
        logger.info("[CALCOLO PELLICOLE SOLARI]")
        logger.info(f"  Tipo: {tipo_pellicola}")
        logger.info(f"  Superficie: {superficie_pellicole_mq:.2f} m²")
        logger.info(f"  Spesa sostenuta: {spesa_pellicole:,.2f} €")

        params_key = "pellicole_non_riflettenti" if tipo_pellicola == "selettiva_non_riflettente" else "pellicole_riflettenti"
        params = PARAMETRI_SCHERMATURE[params_key]

        costo_effettivo = spesa_pellicole / superficie_pellicole_mq if superficie_pellicole_mq > 0 else 0
        costo_ammissibile = min(costo_effettivo, params["costo_max_mq"])

        logger.info(f"  Costo specifico: {costo_effettivo:.2f} €/m² (max: {params['costo_max_mq']:.2f} €/m²)")

        spesa_ammissibile = costo_ammissibile * superficie_pellicole_mq
        incentivo_lordo = percentuale_base * spesa_ammissibile
        incentivo_effettivo = min(incentivo_lordo, params["incentivo_max"])

        logger.info(f"  Spesa ammissibile: {spesa_ammissibile:,.2f} €")
        logger.info(f"  Incentivo lordo: {incentivo_lordo:,.2f} €")
        logger.info(f"  Massimale tipologia: {params['incentivo_max']:,.2f} €")
        logger.info(f"  Incentivo effettivo: {incentivo_effettivo:,.2f} €")

        note = ""
        if costo_effettivo > params["costo_max_mq"]:
            note = f"Costo specifico limitato a {params['costo_max_mq']:.2f} €/m²"
        if incentivo_lordo > params["incentivo_max"]:
            note += f" | Incentivo limitato a massimale {params['incentivo_max']:,.2f} €"

        risultati_parziali.append(RisultatoCalcoloSchermature(
            tipo="pellicole",
            superficie_mq=superficie_pellicole_mq,
            spesa_sostenuta=spesa_pellicole,
            costo_specifico=costo_effettivo,
            costo_max_ammissibile=params["costo_max_mq"],
            spesa_ammissibile=spesa_ammissibile,
            percentuale_incentivo=percentuale_base,
            incentivo_lordo=incentivo_lordo,
            incentivo_effettivo=incentivo_effettivo,
            incentivo_max=params["incentivo_max"],
            note=note.strip(" |")
        ))

        incentivo_totale += incentivo_effettivo
        logger.info("")

    # =========================================================================
    # 4. APPLICAZIONE MASSIMALE COMPLESSIVO
    # =========================================================================
    logger.info("[APPLICAZIONE MASSIMALE COMPLESSIVO]")
    logger.info(f"  Incentivo totale (prima massimale): {incentivo_totale:,.2f} €")
    logger.info(f"  Massimale complessivo: {MASSIMALE_TOTALE:,.2f} €")

    incentivo_totale = min(incentivo_totale, MASSIMALE_TOTALE)
    logger.info(f"  Incentivo totale (dopo massimale): {incentivo_totale:,.2f} €")
    logger.info("")

    # =========================================================================
    # 5. PREMIALITÀ COMPONENTI UE (+10%)
    # =========================================================================
    incentivo_con_premialita = incentivo_totale
    if usa_premialita_componenti_ue:
        logger.info("[PREMIALITÀ COMPONENTI UE]")
        premialita = incentivo_totale * 0.10
        incentivo_con_premialita = incentivo_totale + premialita
        # Riapplica massimale
        incentivo_con_premialita = min(incentivo_con_premialita, MASSIMALE_TOTALE)
        logger.info(f"  Premialità +10%: {premialita:,.2f} €")
        logger.info(f"  Incentivo con premialità: {incentivo_con_premialita:,.2f} €")
        logger.info("")

    # =========================================================================
    # 6. DETERMINAZIONE RATEAZIONE
    # =========================================================================
    logger.info("[DETERMINAZIONE RATEAZIONE]")
    if incentivo_con_premialita <= SOGLIA_RATA_UNICA:
        annualita = 1
        rata_annuale = incentivo_con_premialita
        logger.info(f"  Incentivo {incentivo_con_premialita:,.2f} € ≤ {SOGLIA_RATA_UNICA:,.2f} € -> Rata unica")
    else:
        annualita = ANNI_RATEAZIONE
        rata_annuale = incentivo_con_premialita / annualita
        logger.info(f"  Incentivo {incentivo_con_premialita:,.2f} € > {SOGLIA_RATA_UNICA:,.2f} € -> {annualita} rate annuali")
        logger.info(f"  Rata annuale: {rata_annuale:,.2f} €")

    logger.info("")
    logger.info("=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"INCENTIVO TOTALE: {incentivo_con_premialita:,.2f} €")
    logger.info(f"EROGAZIONE: {annualita} {'anno' if annualita == 1 else 'anni'}")
    logger.info("=" * 60)

    return {
        "status": "OK",
        "incentivo_totale": incentivo_con_premialita,
        "incentivo_base": incentivo_totale,
        "dettagli_schermature": risultati_parziali[0] if installa_schermature else None,
        "dettagli_automazione": risultati_parziali[1] if (installa_schermature and installa_automazione) else (risultati_parziali[0] if installa_automazione else None),
        "dettagli_pellicole": risultati_parziali[-1] if installa_pellicole else None,
        "premialita_ue": incentivo_con_premialita - incentivo_totale if usa_premialita_componenti_ue else 0.0,
        "annualita": annualita,
        "rata_annuale": rata_annuale,
        "messaggio": f"Incentivo CT 3.0: {incentivo_con_premialita:,.2f} € in {annualita} {'anno' if annualita == 1 else 'anni'}"
    }


def confronta_incentivi_schermature(
    # Parametri CT 3.0
    installa_schermature: bool = False,
    superficie_schermature_mq: float = 0.0,
    spesa_schermature: float = 0.0,

    installa_automazione: bool = False,
    superficie_automazione_mq: float = 0.0,
    spesa_automazione: float = 0.0,

    installa_pellicole: bool = False,
    tipo_pellicola: str = "selettiva_non_riflettente",
    superficie_pellicole_mq: float = 0.0,
    spesa_pellicole: float = 0.0,

    tipo_soggetto: str = "privato",
    tipo_edificio: str = "residenziale",
    usa_premialita_componenti_ue: bool = False,

    # Parametri Ecobonus
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale",

    # NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Confronta CT 3.0 vs Ecobonus per schermature solari

    NOTA: Bonus Ristrutturazione NON è applicabile per schermature solari

    Returns:
        Dict con confronto CT 3.0 vs Ecobonus
    """

    # Calcola spesa totale
    spesa_totale = 0.0
    if installa_schermature:
        spesa_totale += spesa_schermature
    if installa_automazione:
        spesa_totale += spesa_automazione
    if installa_pellicole:
        spesa_totale += spesa_pellicole

    risultato = {
        "spesa_totale": spesa_totale,
        "ct_3_0": None,
        "ecobonus": None,
        "npv_ct": 0.0,
        "npv_ecobonus": 0.0,
        "miglior_incentivo": None
    }

    # -------------------------------------------------------------------------
    # 1. CONTO TERMICO 3.0
    # -------------------------------------------------------------------------
    try:
        ct_result = calculate_shading_incentive(
            installa_schermature=installa_schermature,
            superficie_schermature_mq=superficie_schermature_mq,
            spesa_schermature=spesa_schermature,
            installa_automazione=installa_automazione,
            superficie_automazione_mq=superficie_automazione_mq,
            spesa_automazione=spesa_automazione,
            installa_pellicole=installa_pellicole,
            tipo_pellicola=tipo_pellicola,
            superficie_pellicole_mq=superficie_pellicole_mq,
            spesa_pellicole=spesa_pellicole,
            tipo_soggetto=tipo_soggetto,
            tipo_edificio=tipo_edificio,
            usa_premialita_componenti_ue=usa_premialita_componenti_ue
        )

        if ct_result["status"] == "OK":
            incentivo = ct_result["incentivo_totale"]
            anni = ct_result["annualita"]
            rata = ct_result["rata_annuale"]

            # Calcolo NPV
            if anni == 1:
                npv_ct = incentivo
            else:
                npv_ct = sum(rata / ((1 + tasso_sconto) ** t) for t in range(1, anni + 1))

            risultato["ct_3_0"] = {
                "incentivo_totale": incentivo,
                "annualita": anni,
                "rata_annuale": rata,
                "percentuale_spesa": (incentivo / spesa_totale * 100) if spesa_totale > 0 else 0,
                "npv": npv_ct,
                "dettagli": ct_result
            }
            risultato["npv_ct"] = npv_ct

    except Exception as e:
        logger.error(f"Errore calcolo CT 3.0: {e}")
        risultato["ct_3_0"] = {
            "errore": str(e),
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 2. ECOBONUS
    # -------------------------------------------------------------------------
    try:
        eco_result = calculate_ecobonus_deduction(
            tipo_intervento="schermature_solari",
            spesa_sostenuta=spesa_totale,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione
        )

        if eco_result["status"] == "OK":
            detrazione = eco_result["detrazione_totale"]
            rata_annuale_eco = eco_result["calcoli"]["rata_annuale"]

            # NPV Ecobonus (10 anni)
            npv_eco = sum(rata_annuale_eco / ((1 + tasso_sconto) ** t) for t in range(1, 11))

            risultato["ecobonus"] = {
                "detrazione_totale": detrazione,
                "annualita": 10,
                "rata_annuale": rata_annuale_eco,
                "percentuale_spesa": (detrazione / spesa_totale * 100) if spesa_totale > 0 else 0,
                "npv": npv_eco,
                "dettagli": eco_result,
                "note": "Comunicazione ENEA entro 90 giorni"
            }
            risultato["npv_ecobonus"] = npv_eco

    except Exception as e:
        logger.error(f"Errore calcolo Ecobonus: {e}")
        risultato["ecobonus"] = {
            "errore": str(e),
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 3. CONFRONTO NPV
    # -------------------------------------------------------------------------
    if risultato["ct_3_0"] and risultato["ecobonus"]:
        if risultato["npv_ct"] > risultato["npv_ecobonus"]:
            risultato["miglior_incentivo"] = "CT 3.0"
        else:
            risultato["miglior_incentivo"] = "Ecobonus"

    return risultato


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST CALCOLO INCENTIVI SCHERMATURE SOLARI")
    print("=" * 80)

    # Test: Schermature + automazione
    result = calculate_shading_incentive(
        installa_schermature=True,
        superficie_schermature_mq=50.0,
        spesa_schermature=10000.0,
        installa_automazione=True,
        superficie_automazione_mq=50.0,
        spesa_automazione=2000.0,
        tipo_soggetto="privato",
        usa_premialita_componenti_ue=True
    )

    print(f"\nIncentivo totale: {result['incentivo_totale']:,.2f} €")
    print(f"Rateazione: {result['annualita']} anni")

    # Test confronto
    print("\n" + "=" * 80)
    print("TEST CONFRONTO CT 3.0 vs ECOBONUS")
    print("=" * 80)

    confronto = confronta_incentivi_schermature(
        installa_schermature=True,
        superficie_schermature_mq=50.0,
        spesa_schermature=10000.0,
        installa_automazione=True,
        superficie_automazione_mq=50.0,
        spesa_automazione=2000.0,
        tipo_soggetto="privato",
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale"
    )

    if confronto["ct_3_0"]:
        print(f"\nCT 3.0: {confronto['ct_3_0']['incentivo_totale']:,.2f} € (NPV: {confronto['npv_ct']:,.2f} €)")
    if confronto["ecobonus"]:
        print(f"Ecobonus: {confronto['ecobonus']['detrazione_totale']:,.2f} € (NPV: {confronto['npv_ecobonus']:,.2f} €)")
    print(f"\nMigliore: {confronto['miglior_incentivo']}")
