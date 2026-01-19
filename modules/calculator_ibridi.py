"""
Calcolatore incentivi per intervento III.B - Sistemi Ibridi (CT 3.0)
Include confronto con Ecobonus e Bonus Ristrutturazione

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.10
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import logging
import sys
import os

# Aggiungi parent directory al path per import quando eseguito come script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurazione logging (PRIMA degli import che potrebbero usarlo)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from modules.calculator_eco import calculate_ecobonus_deduction

# Import opzionale per Bonus Ristrutturazione (potrebbe non esistere ancora)
try:
    from modules.calculator_bonus_ristrutturazione import calculate_bonus_ristrutturazione
    HAS_BONUS_RISTRUTTURAZIONE = True
except ImportError:
    HAS_BONUS_RISTRUTTURAZIONE = False
    logger.warning("Modulo calculator_bonus_ristrutturazione non trovato - confronto limitato a CT ed Ecobonus")


# ==============================================================================
# TABELLE DI RIFERIMENTO (da Regole Applicative CT 3.0 - Par. 9.10)
# ==============================================================================

# Coefficiente k (Tabella 18 - Allegato 2)
COEFFICIENTI_K = {
    "ibrido_factory_made": {"fino_35kw": 1.25, "oltre_35kw": 1.25},
    "bivalente": {"fino_35kw": 1.00, "oltre_35kw": 1.10},
    "add_on": {"fino_35kw": 1.00, "oltre_35kw": 1.10}
}

# Coefficienti Ci per zona climatica e potenza (Tabella 9 - €/kWht)
COEFFICIENTI_CI = {
    "A": {"fino_35kw": 0.044, "oltre_35kw": 0.022},
    "B": {"fino_35kw": 0.048, "oltre_35kw": 0.024},
    "C": {"fino_35kw": 0.062, "oltre_35kw": 0.031},
    "D": {"fino_35kw": 0.070, "oltre_35kw": 0.035},
    "E": {"fino_35kw": 0.078, "oltre_35kw": 0.039},
    "F": {"fino_35kw": 0.083, "oltre_35kw": 0.041}
}

# Coefficiente Quf per zona climatica (Tabella 8)
COEFFICIENTI_QUF = {
    "A": 400,
    "B": 500,
    "C": 650,
    "D": 900,
    "E": 1150,
    "F": 1350
}

# Rateazione (Tabella 1 Art. 11)
ANNI_RATEAZIONE = {
    "fino_35kw": 2,
    "oltre_35kw": 5
}

# Soglia rata unica
SOGLIA_RATA_UNICA = 15000.0  # €

# Massimale incentivo
I_MAX_TOTALE = 500_000.0  # €

# SCOP/η_s minimo Ecodesign (valore indicativo)
ETA_S_MIN_ECODESIGN = 0.86  # 86%


@dataclass
class RisultatoCalcoloIbridi:
    """Risultato del calcolo incentivo CT 3.0 per sistemi ibridi"""
    incentivo_totale: float
    incentivo_annuo: float
    anni_rateazione: int
    rata_unica: bool
    energia_incentivata_ei: float
    energia_totale_qu: float
    coefficiente_k: float
    coefficiente_ci: float
    coefficiente_quf: float
    coefficiente_kp: float
    scop_pdc: float
    potenza_pdc_kw: float
    potenza_caldaia_kw: float
    tipo_sistema: str
    zona_climatica: str
    dettagli: Dict


def calculate_hybrid_incentive(
    tipo_sistema: str,  # "ibrido_factory_made", "bivalente", "add_on"
    potenza_pdc_kw: float,
    potenza_caldaia_kw: float,
    scop_pdc: float,
    eta_s_pdc: float,
    zona_climatica: str,
    tipo_soggetto: str = "privato",
    eta_s_min_ecodesign: float = ETA_S_MIN_ECODESIGN,
    usa_premialita_componenti_ue: bool = False,
    usa_premialita_combinato_titolo_iii: bool = False
) -> RisultatoCalcoloIbridi:
    """
    Calcola l'incentivo CT 3.0 per sistemi ibridi (III.B)

    Formula: I_a = k × Ei × Ci
    dove:
    - k: coefficiente utilizzo PdC (1,25 factory made, 1/1,1 bivalente/add-on)
    - Ei: energia termica incentivata = Qu × [1 - 1/SCOP] × kp
    - Ci: coefficiente valorizzazione (€/kWht)

    Args:
        tipo_sistema: Tipo sistema ("ibrido_factory_made", "bivalente", "add_on")
        potenza_pdc_kw: Potenza nominale PdC [kW]
        potenza_caldaia_kw: Potenza nominale caldaia [kW]
        scop_pdc: Coefficiente prestazione stagionale PdC
        eta_s_pdc: Efficienza energetica stagionale PdC [%]
        zona_climatica: Zona climatica (A-F)
        tipo_soggetto: Tipo soggetto ("privato", "pa")
        eta_s_min_ecodesign: η_s minimo Ecodesign per calcolo kp
        usa_premialita_componenti_ue: Premialità +10% componenti UE
        usa_premialita_combinato_titolo_iii: Premialità combinazione Titolo III

    Returns:
        RisultatoCalcoloIbridi con tutti i dettagli del calcolo
    """

    logger.info("============================================================")
    logger.info("AVVIO CALCOLO INCENTIVO CT 3.0 - SISTEMI IBRIDI (III.B)")
    logger.info("============================================================")
    logger.info("")
    logger.info(f"Tipo sistema: {tipo_sistema}")
    logger.info(f"Potenza PdC: {potenza_pdc_kw} kW")
    logger.info(f"Potenza caldaia: {potenza_caldaia_kw} kW")
    logger.info(f"SCOP PdC: {scop_pdc}")
    logger.info(f"η_s PdC: {eta_s_pdc}%")
    logger.info(f"Zona climatica: {zona_climatica}")
    logger.info(f"Tipo soggetto: {tipo_soggetto}")

    # -------------------------------------------------------------------------
    # 1. DETERMINA COEFFICIENTE k
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 1] Calcolo coefficiente k")

    # Determina fascia potenza (basata su potenza CALDAIA per k)
    if potenza_caldaia_kw <= 35:
        fascia_k = "fino_35kw"
    else:
        fascia_k = "oltre_35kw"

    k = COEFFICIENTI_K[tipo_sistema][fascia_k]
    logger.info(f"  Tipo sistema: {tipo_sistema}")
    logger.info(f"  Potenza caldaia: {potenza_caldaia_kw} kW → Fascia: {fascia_k}")
    logger.info(f"  Coefficiente k = {k}")

    # -------------------------------------------------------------------------
    # 2. CALCOLA COEFFICIENTE kp (PREMIALITÀ)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 2] Calcolo coefficiente kp (premialità efficienza)")

    # kp = η_s / η_s_min_ECODESIGN
    eta_s_pdc_decimale = eta_s_pdc / 100.0
    kp = eta_s_pdc_decimale / eta_s_min_ecodesign

    logger.info(f"  η_s PdC: {eta_s_pdc}% = {eta_s_pdc_decimale:.4f}")
    logger.info(f"  η_s_min ECODESIGN: {eta_s_min_ecodesign:.4f}")
    logger.info(f"  kp = {eta_s_pdc_decimale:.4f} / {eta_s_min_ecodesign:.4f} = {kp:.4f}")

    # -------------------------------------------------------------------------
    # 3. CALCOLA Qu (energia termica totale prodotta)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 3] Calcolo Qu (energia termica totale)")

    # Qu = P_rated × Q_uf
    # P_rated = potenza PdC alle condizioni standard
    p_rated = potenza_pdc_kw
    q_uf = COEFFICIENTI_QUF[zona_climatica]

    qu = p_rated * q_uf

    logger.info(f"  P_rated (PdC): {p_rated} kW")
    logger.info(f"  Q_uf (zona {zona_climatica}): {q_uf} h")
    logger.info(f"  Qu = {p_rated} × {q_uf} = {qu:,.0f} kWh_t")

    # -------------------------------------------------------------------------
    # 4. CALCOLA Ei (energia termica incentivata)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 4] Calcolo Ei (energia termica incentivata)")

    # Ei = Qu × [1 - 1/SCOP] × kp
    fattore_scop = 1.0 - (1.0 / scop_pdc)
    ei = qu * fattore_scop * kp

    logger.info(f"  Fattore SCOP: [1 - 1/{scop_pdc}] = {fattore_scop:.4f}")
    logger.info(f"  Ei = {qu:,.0f} × {fattore_scop:.4f} × {kp:.4f}")
    logger.info(f"  Ei = {ei:,.2f} kWh_t")

    # -------------------------------------------------------------------------
    # 5. DETERMINA COEFFICIENTE Ci
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 5] Determinazione coefficiente Ci")

    # Fascia potenza per Ci (basata su potenza PdC)
    if potenza_pdc_kw <= 35:
        fascia_ci = "fino_35kw"
    else:
        fascia_ci = "oltre_35kw"

    ci = COEFFICIENTI_CI[zona_climatica][fascia_ci]

    logger.info(f"  Zona climatica: {zona_climatica}")
    logger.info(f"  Potenza PdC: {potenza_pdc_kw} kW → Fascia: {fascia_ci}")
    logger.info(f"  Ci = {ci} €/kWh_t")

    # -------------------------------------------------------------------------
    # 6. CALCOLA INCENTIVO ANNUO
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 6] Calcolo incentivo annuo")

    # I_a = k × Ei × Ci
    incentivo_annuo = k * ei * ci

    logger.info(f"  I_a = k × Ei × Ci")
    logger.info(f"  I_a = {k} × {ei:,.2f} × {ci}")
    logger.info(f"  I_a = {incentivo_annuo:,.2f} €")

    # -------------------------------------------------------------------------
    # 7. APPLICA PREMIALITÀ AGGIUNTIVE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 7] Applicazione premialità aggiuntive")

    premialita_applicate = []

    # Premialità componenti UE (+10%)
    if usa_premialita_componenti_ue:
        incentivo_annuo *= 1.10
        premialita_applicate.append("Componenti UE (+10%)")
        logger.info(f"  ✓ Premialità componenti UE: +10%")

    # Premialità combinato Titolo III (già inclusa in tipologie specifiche)
    if usa_premialita_combinato_titolo_iii:
        premialita_applicate.append("Combinato Titolo III")
        logger.info(f"  ✓ Premialità combinato Titolo III")

    if premialita_applicate:
        logger.info(f"  Incentivo annuo dopo premialità: {incentivo_annuo:,.2f} €")
    else:
        logger.info(f"  Nessuna premialità aggiuntiva applicata")

    # -------------------------------------------------------------------------
    # 8. PERCENTUALE INCENTIVATA PA (100%)
    # -------------------------------------------------------------------------
    if tipo_soggetto == "pa":
        logger.info("")
        logger.info("[STEP 8] Applicazione percentuale PA (100%)")
        logger.info("  Nota: Per PA incentivo calcolato su spesa ammissibile (100%)")

    # -------------------------------------------------------------------------
    # 9. DETERMINA RATEAZIONE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 9] Determinazione rateazione")

    # Rateazione basata su potenza PdC
    if potenza_pdc_kw <= 35:
        anni_rateazione = ANNI_RATEAZIONE["fino_35kw"]
    else:
        anni_rateazione = ANNI_RATEAZIONE["oltre_35kw"]

    logger.info(f"  Potenza PdC: {potenza_pdc_kw} kW")
    logger.info(f"  Anni rateazione: {anni_rateazione} anni")

    # -------------------------------------------------------------------------
    # 10. CALCOLA INCENTIVO TOTALE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 10] Calcolo incentivo totale")

    incentivo_totale = incentivo_annuo * anni_rateazione

    logger.info(f"  Incentivo totale = {incentivo_annuo:,.2f} × {anni_rateazione}")
    logger.info(f"  Incentivo totale = {incentivo_totale:,.2f} €")

    # Verifica massimale
    if incentivo_totale > I_MAX_TOTALE:
        logger.warning(f"  ATTENZIONE: Incentivo {incentivo_totale:,.2f} € supera il massimale di {I_MAX_TOTALE:,.2f} €")
        logger.warning(f"  Incentivo limitato a {I_MAX_TOTALE:,.2f} €")
        incentivo_totale = I_MAX_TOTALE
        incentivo_annuo = incentivo_totale / anni_rateazione

    # -------------------------------------------------------------------------
    # 11. VERIFICA RATA UNICA
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 11] Verifica rata unica")

    rata_unica = incentivo_totale <= SOGLIA_RATA_UNICA

    if rata_unica:
        logger.info(f"  ✓ Incentivo {incentivo_totale:,.2f} € ≤ {SOGLIA_RATA_UNICA:,.2f} €")
        logger.info(f"  Erogazione in RATA UNICA")
    else:
        logger.info(f"  Incentivo {incentivo_totale:,.2f} € > {SOGLIA_RATA_UNICA:,.2f} €")
        logger.info(f"  Erogazione in {anni_rateazione} rate annuali di {incentivo_annuo:,.2f} €")

    # -------------------------------------------------------------------------
    # ESITO FINALE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("============================================================")
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"INCENTIVO TOTALE: {incentivo_totale:,.2f} €")
    if rata_unica:
        logger.info(f"MODALITÀ: Rata unica")
    else:
        logger.info(f"RATA ANNUALE: {incentivo_annuo:,.2f} € x {anni_rateazione} anni")
    logger.info("============================================================")

    return RisultatoCalcoloIbridi(
        incentivo_totale=incentivo_totale,
        incentivo_annuo=incentivo_annuo,
        anni_rateazione=anni_rateazione,
        rata_unica=rata_unica,
        energia_incentivata_ei=ei,
        energia_totale_qu=qu,
        coefficiente_k=k,
        coefficiente_ci=ci,
        coefficiente_quf=q_uf,
        coefficiente_kp=kp,
        scop_pdc=scop_pdc,
        potenza_pdc_kw=potenza_pdc_kw,
        potenza_caldaia_kw=potenza_caldaia_kw,
        tipo_sistema=tipo_sistema,
        zona_climatica=zona_climatica,
        dettagli={
            "p_rated": p_rated,
            "fattore_scop": fattore_scop,
            "fascia_k": fascia_k,
            "fascia_ci": fascia_ci,
            "premialita_applicate": premialita_applicate
        }
    )


def confronta_incentivi_ibridi(
    tipo_sistema: str,
    potenza_pdc_kw: float,
    potenza_caldaia_kw: float,
    scop_pdc: float,
    eta_s_pdc: float,
    zona_climatica: str,
    spesa_totale_sostenuta: float,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale",
    tipo_soggetto: str = "privato",
    eta_s_min_ecodesign: float = ETA_S_MIN_ECODESIGN,
    usa_premialita_componenti_ue: bool = False,
    usa_premialita_combinato_titolo_iii: bool = False,
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Confronta i 3 incentivi disponibili per sistemi ibridi:
    - Conto Termico 3.0 (CT)
    - Ecobonus
    - Bonus Ristrutturazione

    Include calcolo NPV per confronto equo tra incentivi con diverse durate

    Args:
        [come calculate_hybrid_incentive] +
        spesa_totale_sostenuta: Spesa totale per l'intervento [€]
        anno_spesa: Anno della spesa
        tipo_abitazione: Tipo abitazione per Ecobonus/Bonus Ristrutturazione
        tasso_sconto: Tasso di sconto per NPV (default 3%)

    Returns:
        Dict con risultati CT, Ecobonus, Bonus Ristrutturazione e NPV
    """

    logger.info("============================================================")
    logger.info("CONFRONTO INCENTIVI SISTEMI IBRIDI (CT 3.0 vs ECO vs BONUS)")
    logger.info("============================================================")

    risultati = {
        "ct": None,
        "ecobonus": None,
        "bonus_ristrutturazione": None,
        "npv_ct": 0.0,
        "npv_ecobonus": 0.0,
        "npv_bonus_ristrutturazione": 0.0,
        "migliore": None
    }

    # -------------------------------------------------------------------------
    # 1. CONTO TERMICO 3.0
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[1/3] Calcolo Conto Termico 3.0")

    try:
        ct_result = calculate_hybrid_incentive(
            tipo_sistema=tipo_sistema,
            potenza_pdc_kw=potenza_pdc_kw,
            potenza_caldaia_kw=potenza_caldaia_kw,
            scop_pdc=scop_pdc,
            eta_s_pdc=eta_s_pdc,
            zona_climatica=zona_climatica,
            tipo_soggetto=tipo_soggetto,
            eta_s_min_ecodesign=eta_s_min_ecodesign,
            usa_premialita_componenti_ue=usa_premialita_componenti_ue,
            usa_premialita_combinato_titolo_iii=usa_premialita_combinato_titolo_iii
        )

        incentivo = ct_result.incentivo_totale
        anni = 1 if ct_result.rata_unica else ct_result.anni_rateazione

        # Calcola NPV
        if ct_result.rata_unica:
            npv_ct = incentivo
        else:
            rata = ct_result.incentivo_annuo
            npv_ct = sum(rata / ((1 + tasso_sconto) ** t) for t in range(1, anni + 1))

        risultati["ct"] = {
            "incentivo": incentivo,
            "rata_annuale": ct_result.incentivo_annuo if not ct_result.rata_unica else incentivo,
            "anni": anni,
            "rata_unica": ct_result.rata_unica,
            "dettagli": ct_result
        }
        risultati["npv_ct"] = npv_ct

        logger.info(f"  ✓ CT 3.0: {incentivo:,.2f} € (NPV: {npv_ct:,.2f} €)")

    except Exception as e:
        logger.error(f"  ✗ Errore calcolo CT 3.0: {e}")
        risultati["ct"] = {
            "errore": str(e),
            "incentivo": 0.0,
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 2. ECOBONUS
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[2/3] Calcolo Ecobonus")

    try:
        eco_result = calculate_ecobonus_deduction(
            tipo_intervento="pompe_calore",  # Usa categoria pompe_calore
            spesa_sostenuta=spesa_totale_sostenuta,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione
        )

        if eco_result["status"] == "OK":
            detrazione = eco_result["detrazione_totale"]
            rata_annuale_eco = eco_result["calcoli"]["rata_annuale"]
            anni_eco = eco_result["calcoli"]["anni_recupero"]

            # NPV Ecobonus (10 rate annuali)
            npv_eco = sum(rata_annuale_eco / ((1 + tasso_sconto) ** t) for t in range(1, anni_eco + 1))

            risultati["ecobonus"] = {
                "detrazione": detrazione,
                "rata_annuale": rata_annuale_eco,
                "anni": anni_eco,
                "aliquota": eco_result["aliquota_applicata"],
                "dettagli": eco_result
            }
            risultati["npv_ecobonus"] = npv_eco

            logger.info(f"  ✓ Ecobonus: {detrazione:,.2f} € (NPV: {npv_eco:,.2f} €)")
        else:
            logger.warning(f"  ⚠ Ecobonus non applicabile: {eco_result.get('message', 'N/A')}")
            risultati["ecobonus"] = {
                "errore": eco_result.get("message", "Non applicabile"),
                "detrazione": 0.0,
                "dettagli": None
            }

    except Exception as e:
        logger.error(f"  ✗ Errore calcolo Ecobonus: {e}")
        risultati["ecobonus"] = {
            "errore": str(e),
            "detrazione": 0.0,
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 3. BONUS RISTRUTTURAZIONE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[3/3] Calcolo Bonus Ristrutturazione")

    try:
        bonus_result = calculate_bonus_ristrutturazione(
            tipo_intervento="pompe_calore",  # Usa categoria generica per sistemi ibridi
            spesa_sostenuta=spesa_totale_sostenuta,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione
        )

        if bonus_result["status"] == "OK":
            detrazione = bonus_result["detrazione_totale"]
            rata_annuale_bonus = bonus_result["calcoli"]["rata_annuale"]
            anni_bonus = bonus_result["calcoli"]["anni_recupero"]

            # NPV Bonus Ristrutturazione (10 rate annuali)
            npv_bonus = sum(rata_annuale_bonus / ((1 + tasso_sconto) ** t) for t in range(1, anni_bonus + 1))

            risultati["bonus_ristrutturazione"] = {
                "detrazione": detrazione,
                "rata_annuale": rata_annuale_bonus,
                "anni": anni_bonus,
                "aliquota": bonus_result["aliquota_applicata"],
                "dettagli": bonus_result
            }
            risultati["npv_bonus_ristrutturazione"] = npv_bonus

            logger.info(f"  ✓ Bonus Ristrutturazione: {detrazione:,.2f} € (NPV: {npv_bonus:,.2f} €)")
        else:
            logger.warning(f"  ⚠ Bonus Ristrutturazione non applicabile: {bonus_result.get('message', 'N/A')}")
            risultati["bonus_ristrutturazione"] = {
                "errore": bonus_result.get("message", "Non applicabile"),
                "detrazione": 0.0,
                "dettagli": None
            }

    except Exception as e:
        logger.error(f"  ✗ Errore calcolo Bonus Ristrutturazione: {e}")
        risultati["bonus_ristrutturazione"] = {
            "errore": str(e),
            "detrazione": 0.0,
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # CONFRONTO FINALE (basato su NPV)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("============================================================")
    logger.info("CONFRONTO NPV (Net Present Value)")
    logger.info("============================================================")

    npvs = {
        "Conto Termico 3.0": risultati["npv_ct"],
        "Ecobonus": risultati["npv_ecobonus"],
        "Bonus Ristrutturazione": risultati["npv_bonus_ristrutturazione"]
    }

    for nome, npv in npvs.items():
        logger.info(f"  {nome}: {npv:,.2f} €")

    # Determina il migliore
    migliore_nome = max(npvs, key=npvs.get)
    migliore_npv = npvs[migliore_nome]

    risultati["migliore"] = migliore_nome

    logger.info("")
    logger.info(f"🏆 MIGLIORE: {migliore_nome} con NPV di {migliore_npv:,.2f} €")
    logger.info("============================================================")

    return risultati


# ==============================================================================
# TEST
# ==============================================================================
if __name__ == "__main__":
    # Test 1: Ibrido factory made piccolo (P ≤ 35 kW)
    print("\n" + "="*80)
    print("TEST 1: Ibrido Factory Made - P ≤ 35 kW")
    print("="*80)

    result1 = calculate_hybrid_incentive(
        tipo_sistema="ibrido_factory_made",
        potenza_pdc_kw=8.0,
        potenza_caldaia_kw=20.0,
        scop_pdc=4.2,
        eta_s_pdc=170.0,  # 170%
        zona_climatica="E",
        tipo_soggetto="privato"
    )

    print(f"\nIncentivo totale: {result1.incentivo_totale:,.2f} €")
    print(f"Anni rateazione: {result1.anni_rateazione}")
    print(f"Rata unica: {result1.rata_unica}")
    if not result1.rata_unica:
        print(f"Rata annuale: {result1.incentivo_annuo:,.2f} €")

    # Test 2: Sistema bivalente grande (P > 35 kW)
    print("\n" + "="*80)
    print("TEST 2: Bivalente - P > 35 kW")
    print("="*80)

    result2 = calculate_hybrid_incentive(
        tipo_sistema="bivalente",
        potenza_pdc_kw=50.0,
        potenza_caldaia_kw=120.0,
        scop_pdc=3.8,
        eta_s_pdc=150.0,
        zona_climatica="D",
        tipo_soggetto="privato"
    )

    print(f"\nIncentivo totale: {result2.incentivo_totale:,.2f} €")
    print(f"Anni rateazione: {result2.anni_rateazione}")
    print(f"Rata annuale: {result2.incentivo_annuo:,.2f} €")

    # Test 3: Confronto 3 incentivi
    print("\n" + "="*80)
    print("TEST 3: Confronto CT 3.0 vs Ecobonus vs Bonus Ristrutturazione")
    print("="*80)

    confronto = confronta_incentivi_ibridi(
        tipo_sistema="ibrido_factory_made",
        potenza_pdc_kw=12.0,
        potenza_caldaia_kw=30.0,
        scop_pdc=4.0,
        eta_s_pdc=160.0,
        zona_climatica="E",
        spesa_totale_sostenuta=15000.0,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale",
        tipo_soggetto="privato"
    )

    print("\n--- RISULTATI ---")
    if confronto["ct"]:
        print(f"CT 3.0: {confronto['ct']['incentivo']:,.2f} € (NPV: {confronto['npv_ct']:,.2f} €)")
    if confronto["ecobonus"]:
        print(f"Ecobonus: {confronto['ecobonus'].get('detrazione', 0):,.2f} € (NPV: {confronto['npv_ecobonus']:,.2f} €)")
    if confronto["bonus_ristrutturazione"]:
        print(f"Bonus Ristrutturazione: {confronto['bonus_ristrutturazione'].get('detrazione', 0):,.2f} € (NPV: {confronto['npv_bonus_ristrutturazione']:,.2f} €)")

    print(f"\n🏆 MIGLIORE: {confronto['migliore']}")
