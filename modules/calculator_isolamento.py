"""
Modulo di calcolo incentivi Conto Termico 3.0 per Isolamento Termico (II.A).

Riferimento normativo: D.M. 7 agosto 2025 - Regole Applicative CT 3.0
Paragrafo 9.1 - Isolamento termico di superfici opache delimitanti il volume climatizzato

Tipologie di intervento:
    - Isolamento coperture (esterno, interno, ventilato)
    - Isolamento pavimenti (esterno, interno)
    - Isolamento pareti perimetrali (esterno, interno, ventilato)

Formula di calcolo:
    I_tot = %_spesa × C × S_int
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

class InputRiepilogoIsolamento(TypedDict):
    tipo_superficie: str
    posizione_isolamento: str
    zona_climatica: str
    superficie_mq: float
    spesa_sostenuta: float
    tipo_soggetto: str
    trasmittanza_post_operam: float
    combinato_con_titolo_iii: bool
    componenti_ue: bool


class CalcoliIntermedIsolamento(TypedDict):
    C_max: float  # Costo massimo unitario [€/m²]
    spesa_ammissibile: float
    percentuale_base: float
    percentuale_applicata: float
    C_effettivo: float  # Costo specifico effettivo
    I_lordo: float


class RisultatoCalcoloIsolamento(TypedDict):
    status: Literal["OK", "ERROR"]
    messaggio: str
    input_riepilogo: InputRiepilogoIsolamento
    calcoli: Optional[CalcoliIntermedIsolamento]
    incentivo_totale: Optional[float]
    numero_rate: int
    rata_annuale: Optional[float]
    I_max: float


# ============================================================================
# COSTANTI E DATI (da Regole Applicative CT 3.0 - DM 7/8/2025)
# ============================================================================

# Tabella 14 - Valori limite massimi di trasmittanza termica [W/m²K]
# Paragrafo 9.1.1
TRASMITTANZA_LIMITI = {
    "coperture": {
        "A": 0.27, "B": 0.27, "C": 0.27, "D": 0.22, "E": 0.20, "F": 0.19
    },
    "pavimenti": {
        "A": 0.40, "B": 0.40, "C": 0.30, "D": 0.28, "E": 0.25, "F": 0.23
    },
    "pareti": {
        "A": 0.38, "B": 0.38, "C": 0.30, "D": 0.26, "E": 0.23, "F": 0.22
    }
}

# Tabella 15 - Costi massimi unitari e percentuali incentivate
# Paragrafo 9.1.3
COSTI_MASSIMI = {
    "coperture": {
        "esterno": 300.0,
        "interno": 150.0,
        "ventilato": 350.0
    },
    "pavimenti": {
        "esterno": 170.0,
        "interno": 150.0
    },
    "pareti": {
        "esterno": 200.0,
        "interno": 100.0,
        "ventilato": 250.0
    }
}

# Percentuali base di incentivazione
PERCENTUALE_BASE = 0.40  # 40%
PERCENTUALE_ZONE_EF = 0.50  # 50% per zone E e F
PERCENTUALE_TITOLO_III = 0.55  # 55% se combinato con interventi Titolo III
PERCENTUALE_PA = 1.00  # 100% per edifici pubblici

# Massimale incentivo totale (somma coperture + pavimenti + pareti)
I_MAX_TOTALE = 1_000_000.0  # €

# Maggiorazione componenti UE
MAGGIORAZIONE_UE = 0.10  # +10%

# Numero di rate
NUMERO_RATE = 5
SOGLIA_RATA_UNICA = 15000.0  # € - sotto questa soglia, rata unica


# ============================================================================
# FUNZIONI DI VALIDAZIONE
# ============================================================================

def valida_trasmittanza(
    tipo_superficie: str,
    zona_climatica: str,
    trasmittanza: float,
    posizione: str
) -> tuple[bool, str]:
    """
    Valida che la trasmittanza post-operam rispetti i limiti normativi.

    Per isolamento dall'interno o intercapedine, i limiti sono incrementati del 30%.
    """
    if tipo_superficie not in TRASMITTANZA_LIMITI:
        return False, f"Tipo superficie '{tipo_superficie}' non valido"

    if zona_climatica not in TRASMITTANZA_LIMITI[tipo_superficie]:
        return False, f"Zona climatica '{zona_climatica}' non valida"

    limite_base = TRASMITTANZA_LIMITI[tipo_superficie][zona_climatica]

    # Incremento del 30% per isolamento interno/intercapedine
    if posizione == "interno":
        limite = limite_base * 1.30
        tipo_limite = "interno (+30%)"
    else:
        limite = limite_base
        tipo_limite = "esterno"

    if trasmittanza > limite:
        return False, f"Trasmittanza {trasmittanza:.3f} W/m²K supera il limite {tipo_limite} di {limite:.3f} W/m²K per zona {zona_climatica}"

    return True, f"OK: Trasmittanza {trasmittanza:.3f} W/m²K rispetta il limite di {limite:.3f} W/m²K"


# ============================================================================
# FUNZIONE PRINCIPALE DI CALCOLO
# ============================================================================

def calculate_insulation_incentive(
    tipo_superficie: Literal["coperture", "pavimenti", "pareti"],
    posizione_isolamento: Literal["esterno", "interno", "ventilato"],
    zona_climatica: Literal["A", "B", "C", "D", "E", "F"],
    superficie_mq: float,
    spesa_totale_sostenuta: float,
    trasmittanza_post_operam: float,
    tipo_soggetto: str = "privato",
    combinato_con_titolo_iii: bool = False,
    componenti_ue: bool = False,
    tasso_sconto: float = 0.03
) -> RisultatoCalcoloIsolamento:
    """
    Calcola l'incentivo Conto Termico 3.0 per isolamento termico (II.A).

    Implementa la pipeline completa di calcolo secondo il DM 7/8/2025:
    1. Validazione trasmittanza
    2. Determinazione costo massimo unitario
    3. Calcolo percentuale incentivata
    4. Applicazione massimali
    5. Maggiorazioni (zone E/F, Titolo III, componenti UE, PA)
    6. Determinazione rateazione

    Formula:
        I_tot = %_spesa × C × S_int
        con I_tot ≤ I_max

    Args:
        tipo_superficie: Tipo superficie ("coperture", "pavimenti", "pareti")
        posizione_isolamento: Posizione ("esterno", "interno", "ventilato")
        zona_climatica: Zona climatica (A-F)
        superficie_mq: Superficie isolata in m²
        spesa_totale_sostenuta: Spesa totale IVA inclusa in euro
        trasmittanza_post_operam: Trasmittanza U post-operam [W/m²K]
        tipo_soggetto: Tipo di soggetto ("privato", "impresa", "PA")
        combinato_con_titolo_iii: Se combinato con interventi Titolo III (PdC, biomassa, solare)
        componenti_ue: Se i componenti principali sono prodotti in UE

    Returns:
        RisultatoCalcoloIsolamento con tutti i dettagli del calcolo
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO INCENTIVO CT 3.0 - ISOLAMENTO TERMICO (II.A)")
    logger.info("=" * 60)

    # Preparazione output
    input_riepilogo: InputRiepilogoIsolamento = {
        "tipo_superficie": tipo_superficie,
        "posizione_isolamento": posizione_isolamento,
        "zona_climatica": zona_climatica,
        "superficie_mq": superficie_mq,
        "spesa_sostenuta": spesa_totale_sostenuta,
        "tipo_soggetto": tipo_soggetto,
        "trasmittanza_post_operam": trasmittanza_post_operam,
        "combinato_con_titolo_iii": combinato_con_titolo_iii,
        "componenti_ue": componenti_ue
    }

    # -------------------------------------------------------------------------
    # STEP 1: Validazione input
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Validazione input")
    logger.info(f"  Tipo superficie: {tipo_superficie}")
    logger.info(f"  Posizione isolamento: {posizione_isolamento}")
    logger.info(f"  Zona climatica: {zona_climatica}")
    logger.info(f"  Superficie: {superficie_mq} m²")
    logger.info(f"  Spesa sostenuta: {spesa_totale_sostenuta:,.2f} EUR")
    logger.info(f"  Trasmittanza post-operam: {trasmittanza_post_operam:.3f} W/m²K")
    logger.info(f"  Tipo soggetto: {tipo_soggetto}")

    # Validazione trasmittanza
    valido, msg = valida_trasmittanza(tipo_superficie, zona_climatica, trasmittanza_post_operam, posizione_isolamento)
    if not valido:
        return {
            "status": "ERROR",
            "messaggio": msg,
            "input_riepilogo": input_riepilogo,
            "calcoli": None,
            "incentivo_totale": None,
            "numero_rate": 0,
            "rata_annuale": None,
            "I_max": I_MAX_TOTALE
        }

    logger.info(f"  {msg}")

    # -------------------------------------------------------------------------
    # STEP 2: Determinazione costo massimo unitario (C_max)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Determinazione costo massimo unitario")

    if posizione_isolamento not in COSTI_MASSIMI.get(tipo_superficie, {}):
        return {
            "status": "ERROR",
            "messaggio": f"Posizione '{posizione_isolamento}' non valida per {tipo_superficie}",
            "input_riepilogo": input_riepilogo,
            "calcoli": None,
            "incentivo_totale": None,
            "numero_rate": 0,
            "rata_annuale": None,
            "I_max": I_MAX_TOTALE
        }

    C_max = COSTI_MASSIMI[tipo_superficie][posizione_isolamento]
    logger.info(f"  C_max = {C_max} EUR/m²")

    # Costo specifico effettivo
    C_effettivo = spesa_totale_sostenuta / superficie_mq if superficie_mq > 0 else 0
    logger.info(f"  C_effettivo = {spesa_totale_sostenuta:,.2f} / {superficie_mq} = {C_effettivo:.2f} EUR/m²")

    # Spesa ammissibile
    C_applicato = min(C_effettivo, C_max)
    spesa_ammissibile = C_applicato * superficie_mq

    if C_effettivo > C_max:
        logger.warning(f"  ⚠ Costo specifico {C_effettivo:.2f} EUR/m² supera C_max {C_max} EUR/m²")
        logger.info(f"  Applicato C_max: spesa ammissibile = {C_max} × {superficie_mq} = {spesa_ammissibile:,.2f} EUR")
    else:
        logger.info(f"  Spesa ammissibile = {spesa_ammissibile:,.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 3: Determinazione percentuale incentivata
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Determinazione percentuale incentivata")

    # Percentuale base
    percentuale_base = PERCENTUALE_BASE
    logger.info(f"  Percentuale base: {percentuale_base*100:.0f}%")

    # PA: 100%
    if tipo_soggetto == "PA":
        percentuale_applicata = PERCENTUALE_PA
        logger.info(f"  ✓ Edificio pubblico: percentuale = {percentuale_applicata*100:.0f}%")
    # Combinato con Titolo III: 55%
    elif combinato_con_titolo_iii:
        percentuale_applicata = PERCENTUALE_TITOLO_III
        logger.info(f"  ✓ Combinato con Titolo III: percentuale = {percentuale_applicata*100:.0f}%")
    # Zone E/F: 50%
    elif zona_climatica in ["E", "F"]:
        percentuale_applicata = PERCENTUALE_ZONE_EF
        logger.info(f"  ✓ Zona climatica {zona_climatica}: percentuale = {percentuale_applicata*100:.0f}%")
    else:
        percentuale_applicata = percentuale_base
        logger.info(f"  Percentuale applicata: {percentuale_applicata*100:.0f}%")

    # -------------------------------------------------------------------------
    # STEP 4: Calcolo incentivo lordo
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Calcolo incentivo lordo")

    I_lordo = percentuale_applicata * spesa_ammissibile
    logger.info(f"  I_lordo = {percentuale_applicata*100:.0f}% × {spesa_ammissibile:,.2f} = {I_lordo:,.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 5: Maggiorazione componenti UE (+10%)
    # -------------------------------------------------------------------------
    if componenti_ue:
        logger.info("\n[STEP 5] Maggiorazione componenti UE")
        maggiorazione = I_lordo * MAGGIORAZIONE_UE
        I_lordo_con_ue = I_lordo + maggiorazione
        logger.info(f"  Maggiorazione +10%: {maggiorazione:,.2f} EUR")
        logger.info(f"  I_totale con UE: {I_lordo_con_ue:,.2f} EUR")
        I_finale = I_lordo_con_ue
    else:
        I_finale = I_lordo

    # -------------------------------------------------------------------------
    # STEP 6: Applicazione massimale I_max
    # -------------------------------------------------------------------------
    logger.info(f"\n[STEP 6] Applicazione massimale")
    logger.info(f"  I_max = {I_MAX_TOTALE:,.2f} EUR (sommato per tutti gli interventi)")

    if I_finale > I_MAX_TOTALE:
        logger.warning(f"  ⚠ Incentivo {I_finale:,.2f} EUR supera I_max {I_MAX_TOTALE:,.2f} EUR")
        I_finale = I_MAX_TOTALE
        logger.info(f"  Incentivo finale: {I_finale:,.2f} EUR (limitato a I_max)")
    else:
        logger.info(f"  Incentivo finale: {I_finale:,.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 7: Determinazione rateazione
    # -------------------------------------------------------------------------
    logger.info(f"\n[STEP 7] Determinazione rateazione")

    if I_finale <= SOGLIA_RATA_UNICA:
        numero_rate = 1
        rata = I_finale
        logger.info(f"  Incentivo {I_finale:,.2f} EUR <= {SOGLIA_RATA_UNICA:,.2f} EUR -> Rata unica")
    else:
        numero_rate = NUMERO_RATE
        rata = I_finale / numero_rate
        logger.info(f"  Incentivo {I_finale:,.2f} EUR > {SOGLIA_RATA_UNICA:,.2f} EUR -> {numero_rate} rate annuali")
        logger.info(f"  Rata annuale: {I_finale:,.2f} / {numero_rate} = {rata:,.2f} EUR")

    # -------------------------------------------------------------------------
    # Output finale
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"INCENTIVO TOTALE: {I_finale:,.2f} EUR")
    if numero_rate > 1:
        logger.info(f"RATEAZIONE: {rata:,.2f} EUR × {numero_rate} anni")
    else:
        logger.info("EROGAZIONE: Rata unica")
    logger.info("=" * 60)

    calcoli: CalcoliIntermedIsolamento = {
        "C_max": C_max,
        "spesa_ammissibile": spesa_ammissibile,
        "percentuale_base": percentuale_base,
        "percentuale_applicata": percentuale_applicata,
        "C_effettivo": C_effettivo,
        "I_lordo": I_lordo
    }

    return {
        "status": "OK",
        "messaggio": "Calcolo completato con successo",
        "input_riepilogo": input_riepilogo,
        "calcoli": calcoli,
        "incentivo_totale": round(I_finale, 2),
        "numero_rate": numero_rate,
        "rata_annuale": round(rata, 2) if numero_rate > 1 else round(I_finale, 2),
        "I_max": I_MAX_TOTALE
    }


# ============================================================================
# CONFRONTO TRA INCENTIVI
# ============================================================================

def confronta_incentivi_isolamento(
    tipo_superficie: Literal["coperture", "pavimenti", "pareti"],
    posizione_isolamento: Literal["esterno", "interno", "ventilato"],
    zona_climatica: Literal["A", "B", "C", "D", "E", "F"],
    superficie_mq: float,
    spesa_totale_sostenuta: float,
    trasmittanza_post_operam: float,
    tipo_soggetto: str = "privato",
    combinato_con_titolo_iii: bool = False,
    componenti_ue: bool = False,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale",
    tasso_sconto: float = 0.03
) -> dict:
    """
    Confronta i tre incentivi disponibili per l'isolamento termico:
    1. Conto Termico 3.0
    2. Ecobonus
    3. Bonus Ristrutturazione

    Calcola il NPV (Net Present Value) per ogni incentivo per un confronto equo.

    IMPORTANTE: Ecobonus e Bonus Ristrutturazione NON sono cumulabili tra loro.
    Possono essere cumulabili con il Conto Termico solo se i vincoli normativi lo permettono.

    Args:
        (stessi parametri di calculate_insulation_incentive)
        anno_spesa: Anno della spesa (default 2025)
        tipo_abitazione: "abitazione_principale" o "altra_abitazione"

    Returns:
        dict con confronto tra incentivi e raccomandazione
    """
    from modules.calculator_eco import calculate_ecobonus_deduction, calculate_bonus_ristrutturazione

    risultati = {}

    # -------------------------------------------------------------------------
    # 1. CONTO TERMICO 3.0
    # -------------------------------------------------------------------------
    try:
        ct_result = calculate_insulation_incentive(
            tipo_superficie=tipo_superficie,
            posizione_isolamento=posizione_isolamento,
            zona_climatica=zona_climatica,
            superficie_mq=superficie_mq,
            spesa_totale_sostenuta=spesa_totale_sostenuta,
            trasmittanza_post_operam=trasmittanza_post_operam,
            tipo_soggetto=tipo_soggetto,
            combinato_con_titolo_iii=combinato_con_titolo_iii,
            componenti_ue=componenti_ue
        )

        if ct_result["status"] == "OK":
            numero_rate = ct_result["numero_rate"]
            rata_annuale = ct_result["rata_annuale"]

            # Calcolo NPV (tasso sconto 3%)
            if numero_rate == 1:
                npv_ct = rata_annuale  # Rata unica
            else:
                # NPV = Σ (Rata / (1 + r)^t) per t da 1 a n
                npv_ct = sum(rata_annuale / ((1 + tasso_sconto) ** t) for t in range(1, numero_rate + 1))

            risultati["conto_termico"] = {
                "incentivo_totale": ct_result["incentivo_totale"],
                "numero_rate": numero_rate,
                "rata_annuale": rata_annuale,
                "npv": round(npv_ct, 2),
                "status": "OK",
                "messaggio": ct_result["messaggio"],
                "dettagli": ct_result
            }
        else:
            risultati["conto_termico"] = {
                "incentivo_totale": 0,
                "numero_rate": 0,
                "rata_annuale": 0,
                "npv": 0,
                "status": "ERROR",
                "messaggio": ct_result["messaggio"],
                "dettagli": ct_result
            }
    except Exception as e:
        risultati["conto_termico"] = {
            "incentivo_totale": 0,
            "npv": 0,
            "status": "ERROR",
            "messaggio": f"Errore calcolo CT: {str(e)}",
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 2. ECOBONUS
    # -------------------------------------------------------------------------
    try:
        eco_result = calculate_ecobonus_deduction(
            tipo_intervento="coibentazione_involucro",
            spesa_sostenuta=spesa_totale_sostenuta,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione
        )

        if eco_result["status"] == "OK":
            detrazione = eco_result["detrazione_totale"]
            rata_annuale_eco = eco_result["calcoli"]["rata_annuale"]
            anni = eco_result["calcoli"]["anni_recupero"]

            # Calcolo NPV (tasso sconto 3%)
            npv_eco = sum(rata_annuale_eco / ((1 + tasso_sconto) ** t) for t in range(1, anni + 1))

            risultati["ecobonus"] = {
                "detrazione_totale": detrazione,
                "anni_recupero": anni,
                "rata_annuale": rata_annuale_eco,
                "npv": round(npv_eco, 2),
                "aliquota": eco_result["calcoli"]["aliquota_applicata"],
                "status": "OK",
                "messaggio": eco_result["messaggio"],
                "dettagli": eco_result
            }
        else:
            risultati["ecobonus"] = {
                "detrazione_totale": 0,
                "npv": 0,
                "status": "ERROR",
                "messaggio": eco_result["messaggio"],
                "dettagli": eco_result
            }
    except Exception as e:
        risultati["ecobonus"] = {
            "detrazione_totale": 0,
            "npv": 0,
            "status": "ERROR",
            "messaggio": f"Errore calcolo Ecobonus: {str(e)}",
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # 3. BONUS RISTRUTTURAZIONE
    # -------------------------------------------------------------------------
    try:
        bonus_result = calculate_bonus_ristrutturazione(
            tipo_intervento="coibentazione_involucro",
            spesa_sostenuta=spesa_totale_sostenuta,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione
        )

        if bonus_result["status"] == "OK":
            detrazione = bonus_result["detrazione_totale"]
            rata_annuale_bonus = bonus_result["calcoli"]["rata_annuale"]
            anni = bonus_result["calcoli"]["anni_recupero"]

            # Calcolo NPV (tasso sconto 3%)
            npv_bonus = sum(rata_annuale_bonus / ((1 + tasso_sconto) ** t) for t in range(1, anni + 1))

            risultati["bonus_ristrutturazione"] = {
                "detrazione_totale": detrazione,
                "anni_recupero": anni,
                "rata_annuale": rata_annuale_bonus,
                "npv": round(npv_bonus, 2),
                "aliquota": bonus_result["calcoli"]["aliquota_applicata"],
                "status": "OK",
                "messaggio": bonus_result["messaggio"],
                "dettagli": bonus_result
            }
        else:
            risultati["bonus_ristrutturazione"] = {
                "detrazione_totale": 0,
                "npv": 0,
                "status": "ERROR",
                "messaggio": bonus_result["messaggio"],
                "dettagli": bonus_result
            }
    except Exception as e:
        risultati["bonus_ristrutturazione"] = {
            "detrazione_totale": 0,
            "npv": 0,
            "status": "ERROR",
            "messaggio": f"Errore calcolo Bonus Ristrutturazione: {str(e)}",
            "dettagli": None
        }

    # -------------------------------------------------------------------------
    # RACCOMANDAZIONE
    # -------------------------------------------------------------------------
    incentivi_validi = []

    if risultati["conto_termico"]["status"] == "OK":
        incentivi_validi.append(("Conto Termico 3.0", risultati["conto_termico"]["npv"]))

    if risultati["ecobonus"]["status"] == "OK":
        incentivi_validi.append(("Ecobonus", risultati["ecobonus"]["npv"]))

    if risultati["bonus_ristrutturazione"]["status"] == "OK":
        incentivi_validi.append(("Bonus Ristrutturazione", risultati["bonus_ristrutturazione"]["npv"]))

    # Ordina per NPV decrescente
    incentivi_validi.sort(key=lambda x: x[1], reverse=True)

    raccomandazione = ""
    if incentivi_validi:
        migliore = incentivi_validi[0]
        raccomandazione = f"{migliore[0]} (NPV: {migliore[1]:.2f} EUR)"

        # Nota sulla non cumulabilità Ecobonus/Bonus Ristrutturazione
        if len(incentivi_validi) >= 2:
            raccomandazione += "\n\nNOTA: Ecobonus e Bonus Ristrutturazione NON sono cumulabili tra loro."
    else:
        raccomandazione = "Nessun incentivo disponibile con i parametri forniti."

    return {
        "risultati": risultati,
        "incentivi_validi": incentivi_validi,
        "raccomandazione": raccomandazione
    }


# ============================================================================
# ESEMPI E TEST
# ============================================================================

if __name__ == "__main__":
    import json

    # Test 1: Cappotto esterno su pareti, zona E
    print("\n" + "="*80)
    print("TEST 1: Cappotto esterno pareti - Zona E - Privato")
    print("="*80)

    risultato1 = calculate_insulation_incentive(
        tipo_superficie="pareti",
        posizione_isolamento="esterno",
        zona_climatica="E",
        superficie_mq=150.0,
        spesa_totale_sostenuta=30000.0,
        trasmittanza_post_operam=0.22,
        tipo_soggetto="privato",
        combinato_con_titolo_iii=False,
        componenti_ue=True
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato1, indent=2, ensure_ascii=False))

    # Test 2: Isolamento copertura, combinato con PdC
    print("\n" + "="*80)
    print("TEST 2: Copertura ventilata - Zona D - Combinato con Titolo III")
    print("="*80)

    risultato2 = calculate_insulation_incentive(
        tipo_superficie="coperture",
        posizione_isolamento="ventilato",
        zona_climatica="D",
        superficie_mq=100.0,
        spesa_totale_sostenuta=35000.0,
        trasmittanza_post_operam=0.20,
        tipo_soggetto="privato",
        combinato_con_titolo_iii=True,
        componenti_ue=False
    )

    print("\nRISULTATO:")
    print(json.dumps(risultato2, indent=2, ensure_ascii=False))
