"""
Validatore per intervento III.B - Sistemi Ibridi (CT 3.0)
Sostituzione di impianti di climatizzazione invernale con sistemi ibridi
factory made, bivalenti, o pompe di calore "add on"

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.10
"""

from typing import Dict, List, Tuple
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# TABELLE DI RIFERIMENTO (da Regole Applicative CT 3.0 - Par. 9.10)
# ==============================================================================

# Requisiti caldaia condensazione (Tabella 6 - Allegato 1)
REQUISITI_CALDAIA_CONDENSAZIONE = {
    "eta_s_min_fino_400kw": 90.0,  # η_s > 90% per Pn ≤ 400 kW
    "eta_s_min_oltre_400kw": 98.0  # η_s > 98% per Pn > 400 kW
}

# Requisiti pompa di calore (stessi di III.A - par. 9.9.1)
REQUISITI_POMPA_CALORE = {
    "scop_min": 2.5,  # Valore indicativo minimo
    "cop_min": 2.5    # Valore indicativo minimo
}

# Rapporto potenze per ibridi factory made
RAPPORTO_POTENZE_MAX = 0.5  # Pn_PdC / Pn_caldaia ≤ 0,5

# Classi termoregolazione ammesse
CLASSI_TERMOREGOLAZIONE = ["V", "VI", "VII", "VIII"]

# Età massima caldaia per add-on
ETA_MAX_CALDAIA_ADD_ON = 5  # anni


def valida_requisiti_ibridi(
    tipo_sistema: str = "ibrido_factory_made",  # "ibrido_factory_made", "bivalente", "add_on"
    potenza_pdc_kw: float = 0.0,
    potenza_caldaia_kw: float = 0.0,
    scop_pdc: float = 0.0,
    eta_s_caldaia: float = 0.0,
    tipo_pdc: str = "aria_acqua",  # Per add-on: "aria_acqua", "acqua_acqua", "aria_aria"
    classe_termoregolazione: str = "V",
    ha_valvole_termostatiche: bool = True,
    ha_contabilizzazione: bool = False,  # Obbligatorio se P > 200 kW
    eta_caldaia_preesistente_anni: int = 0,  # Solo per add-on
    tipo_caldaia_preesistente: str = "condensazione_gas",  # Solo per add-on
    fabbricanti_diversi: bool = False,  # Se PdC e caldaia di fabbricanti diversi
    ha_asseverazione_compatibilita: bool = False,  # Obbligatoria se fabbricanti diversi
    ha_ape_post_operam: bool = None,
    ha_diagnosi_ante_operam: bool = None,
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa"
    integra_caldaia_gas: bool = False,  # Per controllo esclusione imprese
    potenza_totale_impianto_kw: float = None,
    edificio_con_vincoli: bool = False  # Per add-on aria-aria
) -> Dict:
    """
    Valida i requisiti tecnici per sistemi ibridi secondo CT 3.0 Par. 9.10

    Args:
        tipo_sistema: Tipo sistema ("ibrido_factory_made", "bivalente", "add_on")
        potenza_pdc_kw: Potenza nominale pompa di calore [kW]
        potenza_caldaia_kw: Potenza nominale caldaia [kW]
        scop_pdc: Coefficiente prestazione stagionale PdC
        eta_s_caldaia: Rendimento stagionale caldaia [%]
        tipo_pdc: Tipologia PdC (per add-on)
        classe_termoregolazione: Classe termoregolazione (V, VI, VII, VIII)
        ha_valvole_termostatiche: Presenza valvole termostatiche
        ha_contabilizzazione: Contabilizzazione calore installata
        eta_caldaia_preesistente_anni: Età caldaia preesistente (solo add-on) [anni]
        tipo_caldaia_preesistente: Tipo caldaia preesistente (solo add-on)
        fabbricanti_diversi: Se PdC e caldaia sono di fabbricanti diversi
        ha_asseverazione_compatibilita: Asseverazione compatibilità presente
        ha_ape_post_operam: APE post-operam disponibile
        ha_diagnosi_ante_operam: Diagnosi energetica ante disponibile
        tipo_soggetto: Tipo soggetto ("privato", "impresa", "pa")
        integra_caldaia_gas: Se il sistema integra caldaia a gas
        potenza_totale_impianto_kw: Potenza totale impianto post-operam
        edificio_con_vincoli: Se edificio ha vincoli architettonici

    Returns:
        Dict con:
            - ammissibile (bool)
            - punteggio (int): 0-100
            - errori (List[str])
            - warnings (List[str])
            - suggerimenti (List[str])
    """

    logger.info("============================================================")
    logger.info("AVVIO VALIDAZIONE SISTEMA IBRIDO CT 3.0 (III.B)")
    logger.info("============================================================")
    logger.info("")
    logger.info("[STEP 1] Validazione input")

    errori = []
    warnings = []
    suggerimenti = []
    punteggio = 100

    # Se potenza_totale_impianto_kw non specificata, usa potenza PdC + caldaia
    if potenza_totale_impianto_kw is None:
        potenza_totale_impianto_kw = potenza_pdc_kw + potenza_caldaia_kw

    logger.info(f"  Tipo sistema: {tipo_sistema}")
    logger.info(f"  Potenza PdC: {potenza_pdc_kw} kW")
    logger.info(f"  Potenza caldaia: {potenza_caldaia_kw} kW")
    logger.info(f"  Potenza totale impianto: {potenza_totale_impianto_kw} kW")
    logger.info(f"  SCOP PdC: {scop_pdc}")
    logger.info(f"  η_s caldaia: {eta_s_caldaia}%")
    logger.info(f"  Tipo soggetto: {tipo_soggetto}")

    # -------------------------------------------------------------------------
    # 1. VALIDAZIONE POTENZA MASSIMA (≤ 2.000 kW)
    # -------------------------------------------------------------------------
    if potenza_totale_impianto_kw > 2000:
        errori.append(
            f"Potenza totale impianto {potenza_totale_impianto_kw} kW supera il limite di 2.000 kW"
        )
        logger.error(f"  ERRORE: Potenza {potenza_totale_impianto_kw} kW > 2.000 kW (limite CT 3.0)")
        punteggio -= 100
    else:
        logger.info(f"  OK: Potenza {potenza_totale_impianto_kw} kW ≤ 2.000 kW")

    # -------------------------------------------------------------------------
    # 2. ESCLUSIONE CALDAIE A GAS PER IMPRESE/ETS (Art. 25, comma 2)
    # -------------------------------------------------------------------------
    if tipo_soggetto in ["impresa", "ets"] and integra_caldaia_gas:
        errori.append(
            "Per imprese/ETS non sono incentivabili sistemi ibridi che integrano caldaie a gas"
        )
        logger.error("  ERRORE: Sistemi ibridi con caldaia a gas non ammessi per imprese/ETS")
        punteggio -= 100
    else:
        if tipo_soggetto in ["impresa", "ets"]:
            logger.info("  OK: Sistema non integra caldaia a gas (requisito imprese/ETS)")

    # -------------------------------------------------------------------------
    # 3. VALIDAZIONE SPECIFICA PER TIPO SISTEMA
    # -------------------------------------------------------------------------
    if tipo_sistema == "ibrido_factory_made":
        logger.info("")
        logger.info("[STEP 2] Validazione Ibrido Factory Made")

        # 3.1 Rapporto potenze ≤ 0,5
        if potenza_caldaia_kw > 0:
            rapporto = potenza_pdc_kw / potenza_caldaia_kw
            logger.info(f"  Rapporto Pn_PdC/Pn_caldaia: {rapporto:.2f}")

            if rapporto > RAPPORTO_POTENZE_MAX:
                errori.append(
                    f"Rapporto potenze {rapporto:.2f} supera il limite di {RAPPORTO_POTENZE_MAX} "
                    f"(Pn_PdC/Pn_caldaia ≤ 0,5)"
                )
                logger.error(f"  ERRORE: Rapporto {rapporto:.2f} > {RAPPORTO_POTENZE_MAX}")
                punteggio -= 30
            else:
                logger.info(f"  OK: Rapporto {rapporto:.2f} ≤ {RAPPORTO_POTENZE_MAX}")
        else:
            errori.append("Potenza caldaia non specificata o zero")
            punteggio -= 20

        # 3.2 Sistema assemblato in fabbrica
        suggerimenti.append(
            "Verificare che il sistema sia assemblato in fabbrica (factory made) "
            "con certificazione del produttore"
        )

    elif tipo_sistema == "bivalente":
        logger.info("")
        logger.info("[STEP 2] Validazione Sistema Bivalente")

        # 3.3 Dichiarazione compatibilità fabbricante
        suggerimenti.append(
            "Il fabbricante della PdC deve fornire dichiarazione di compatibilità "
            "con il generatore secondario"
        )

        # 3.4 Asseverazione se fabbricanti diversi
        if fabbricanti_diversi and not ha_asseverazione_compatibilita:
            errori.append(
                "Per sistemi con PdC e caldaia di fabbricanti diversi è obbligatoria "
                "l'asseverazione di compatibilità da tecnico abilitato"
            )
            logger.error("  ERRORE: Manca asseverazione compatibilità (fabbricanti diversi)")
            punteggio -= 40
        elif fabbricanti_diversi:
            logger.info("  OK: Asseverazione compatibilità presente (fabbricanti diversi)")

    elif tipo_sistema == "add_on":
        logger.info("")
        logger.info("[STEP 2] Validazione Pompa di Calore Add-On")

        # 3.5 Età caldaia preesistente ≤ 5 anni
        logger.info(f"  Età caldaia preesistente: {eta_caldaia_preesistente_anni} anni")

        if eta_caldaia_preesistente_anni > ETA_MAX_CALDAIA_ADD_ON:
            errori.append(
                f"Caldaia preesistente ha {eta_caldaia_preesistente_anni} anni, "
                f"ma deve avere max {ETA_MAX_CALDAIA_ADD_ON} anni per add-on"
            )
            logger.error(f"  ERRORE: Età caldaia {eta_caldaia_preesistente_anni} anni > {ETA_MAX_CALDAIA_ADD_ON} anni")
            punteggio -= 50
        else:
            logger.info(f"  OK: Età caldaia {eta_caldaia_preesistente_anni} anni ≤ {ETA_MAX_CALDAIA_ADD_ON} anni")

        # 3.6 Caldaia preesistente deve essere a condensazione a gas
        if tipo_caldaia_preesistente != "condensazione_gas":
            errori.append(
                "Per add-on la caldaia preesistente deve essere a condensazione alimentata a gas"
            )
            logger.error("  ERRORE: Caldaia preesistente non è a condensazione a gas")
            punteggio -= 40
        else:
            logger.info("  OK: Caldaia preesistente a condensazione a gas")

        # 3.7 Tipologia PdC (aria-acqua, acqua-acqua, aria-aria solo con vincoli)
        logger.info(f"  Tipo PdC: {tipo_pdc}")

        if tipo_pdc == "aria_aria" and not edificio_con_vincoli:
            errori.append(
                "PdC aria-aria ammessa solo per edifici con vincoli architettonici"
            )
            logger.error("  ERRORE: PdC aria-aria richiede vincoli architettonici")
            punteggio -= 30
        elif tipo_pdc == "aria_aria":
            logger.info("  OK: PdC aria-aria ammessa (edificio con vincoli)")
        elif tipo_pdc in ["aria_acqua", "acqua_acqua"]:
            logger.info(f"  OK: Tipo PdC {tipo_pdc} ammesso")
        else:
            warnings.append(f"Tipo PdC '{tipo_pdc}' non standard per add-on")

        # 3.8 Asseverazione se fabbricanti diversi
        if fabbricanti_diversi and not ha_asseverazione_compatibilita:
            errori.append(
                "Per add-on con PdC e caldaia di fabbricanti diversi è obbligatoria "
                "l'asseverazione di compatibilità"
            )
            logger.error("  ERRORE: Manca asseverazione compatibilità")
            punteggio -= 40

    else:
        errori.append(f"Tipo sistema '{tipo_sistema}' non valido")
        punteggio -= 100

    # -------------------------------------------------------------------------
    # 4. VALIDAZIONE POMPA DI CALORE (requisiti par. 9.9.1)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 3] Validazione requisiti Pompa di Calore")

    if scop_pdc <= 0:
        errori.append("SCOP della pompa di calore non specificato")
        logger.error("  ERRORE: SCOP non specificato")
        punteggio -= 20
    elif scop_pdc < REQUISITI_POMPA_CALORE["scop_min"]:
        errori.append(
            f"SCOP {scop_pdc} inferiore al minimo {REQUISITI_POMPA_CALORE['scop_min']}"
        )
        logger.error(f"  ERRORE: SCOP {scop_pdc} < {REQUISITI_POMPA_CALORE['scop_min']}")
        punteggio -= 25
    else:
        logger.info(f"  OK: SCOP {scop_pdc} ≥ {REQUISITI_POMPA_CALORE['scop_min']}")

    suggerimenti.append(
        "Verificare che la PdC rispetti tutti i requisiti del par. 9.9.1 "
        "(SCOP, GWP refrigerante, efficienza minima)"
    )

    # -------------------------------------------------------------------------
    # 5. VALIDAZIONE CALDAIA A CONDENSAZIONE (Tabella 6)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 4] Validazione requisiti Caldaia")

    if potenza_caldaia_kw <= 0:
        errori.append("Potenza caldaia non specificata")
        logger.error("  ERRORE: Potenza caldaia non specificata")
        punteggio -= 20
    else:
        # Determina η_s minimo in base alla potenza
        if potenza_caldaia_kw <= 400:
            eta_s_min = REQUISITI_CALDAIA_CONDENSAZIONE["eta_s_min_fino_400kw"]
            logger.info(f"  Pn caldaia {potenza_caldaia_kw} kW ≤ 400 kW: η_s_min = {eta_s_min}%")
        else:
            eta_s_min = REQUISITI_CALDAIA_CONDENSAZIONE["eta_s_min_oltre_400kw"]
            logger.info(f"  Pn caldaia {potenza_caldaia_kw} kW > 400 kW: η_s_min = {eta_s_min}%")

        if eta_s_caldaia <= 0:
            errori.append("Rendimento stagionale caldaia (η_s) non specificato")
            logger.error("  ERRORE: η_s non specificato")
            punteggio -= 20
        elif eta_s_caldaia < eta_s_min:
            errori.append(
                f"Rendimento caldaia η_s = {eta_s_caldaia}% inferiore al minimo {eta_s_min}%"
            )
            logger.error(f"  ERRORE: η_s {eta_s_caldaia}% < {eta_s_min}%")
            punteggio -= 25
        else:
            logger.info(f"  OK: η_s {eta_s_caldaia}% ≥ {eta_s_min}%")

    # -------------------------------------------------------------------------
    # 6. VALIDAZIONE TERMOREGOLAZIONE (Classi V-VIII)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 5] Validazione Termoregolazione")
    logger.info(f"  Classe termoregolazione: {classe_termoregolazione}")

    if classe_termoregolazione not in CLASSI_TERMOREGOLAZIONE:
        errori.append(
            f"Classe termoregolazione '{classe_termoregolazione}' non ammessa. "
            f"Richieste classi: {', '.join(CLASSI_TERMOREGOLAZIONE)}"
        )
        logger.error(f"  ERRORE: Classe {classe_termoregolazione} non ammessa")
        punteggio -= 30
    else:
        logger.info(f"  OK: Classe {classe_termoregolazione} ammessa")

    # -------------------------------------------------------------------------
    # 7. VALIDAZIONE VALVOLE TERMOSTATICHE
    # -------------------------------------------------------------------------
    logger.info(f"  Valvole termostatiche: {'Sì' if ha_valvole_termostatiche else 'No'}")

    if not ha_valvole_termostatiche:
        warnings.append(
            "Valvole termostatiche obbligatorie su tutti i corpi scaldanti "
            "(salvo eccezioni previste)"
        )
        logger.warning("  ATTENZIONE: Valvole termostatiche non presenti")
    else:
        logger.info("  OK: Valvole termostatiche presenti")

    # -------------------------------------------------------------------------
    # 8. VALIDAZIONE CONTABILIZZAZIONE CALORE (se P > 200 kW)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 6] Validazione Contabilizzazione Calore")

    if potenza_totale_impianto_kw > 200:
        logger.info(f"  Potenza {potenza_totale_impianto_kw} kW > 200 kW")

        if not ha_contabilizzazione:
            errori.append(
                f"Per impianti con P > 200 kW è OBBLIGATORIA l'installazione di sistemi "
                f"di contabilizzazione del calore (potenza: {potenza_totale_impianto_kw} kW)"
            )
            logger.error("  ERRORE: Contabilizzazione calore OBBLIGATORIA ma non presente")
            punteggio -= 50
        else:
            logger.info("  OK: Contabilizzazione calore presente (obbligatoria)")
    else:
        logger.info(f"  Potenza {potenza_totale_impianto_kw} kW ≤ 200 kW: contabilizzazione non obbligatoria")
        if ha_contabilizzazione:
            logger.info("  INFO: Contabilizzazione presente (facoltativa)")

    # -------------------------------------------------------------------------
    # 9. VALIDAZIONE APE E DIAGNOSI (se P ≥ 200 kW)
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("[STEP 7] Validazione APE e Diagnosi Energetica")

    if potenza_totale_impianto_kw >= 200:
        logger.info(f"  Potenza {potenza_totale_impianto_kw} kW ≥ 200 kW")

        # Gestione valori None
        ape_disponibile = ha_ape_post_operam if ha_ape_post_operam is not None else False
        diagnosi_disponibile = ha_diagnosi_ante_operam if ha_diagnosi_ante_operam is not None else False

        if not ape_disponibile:
            errori.append(
                "Per impianti con P ≥ 200 kW è OBBLIGATORIO l'APE post-operam (pena decadenza)"
            )
            logger.error("  ERRORE: APE post-operam OBBLIGATORIO ma non disponibile")
            punteggio -= 50
        else:
            logger.info("  OK: APE post-operam presente (obbligatorio)")

        if not diagnosi_disponibile:
            errori.append(
                "Per impianti con P ≥ 200 kW è OBBLIGATORIA la diagnosi energetica ante-operam (pena decadenza)"
            )
            logger.error("  ERRORE: Diagnosi energetica ante-operam OBBLIGATORIA ma non disponibile")
            punteggio -= 50
        else:
            logger.info("  OK: Diagnosi energetica ante-operam presente (obbligatoria)")
    else:
        logger.info(f"  Potenza {potenza_totale_impianto_kw} kW < 200 kW: APE/Diagnosi non obbligatori")

    # -------------------------------------------------------------------------
    # 10. SUGGERIMENTI FINALI
    # -------------------------------------------------------------------------
    suggerimenti.append(
        "Verificare la messa a punto e l'equilibratura del sistema di distribuzione"
    )

    suggerimenti.append(
        "Sistema di controllo e regolazione deve ottimizzare il funzionamento "
        "preferenziale della PdC rispetto alla caldaia"
    )

    if tipo_sistema == "add_on":
        suggerimenti.append(
            "Per add-on conservare documentazione di messa in esercizio con data installazione"
        )

    # -------------------------------------------------------------------------
    # ESITO FINALE
    # -------------------------------------------------------------------------
    logger.info("")
    logger.info("============================================================")

    ammissibile = len(errori) == 0 and punteggio > 0

    if ammissibile:
        logger.info("ESITO: INTERVENTO AMMISSIBILE ✓")
        logger.info(f"Punteggio: {punteggio}/100")
    else:
        logger.error("ESITO: INTERVENTO NON AMMISSIBILE ✗")
        logger.error(f"Errori critici rilevati: {len(errori)}")
        for err in errori:
            logger.error(f"  - {err}")

    logger.info("============================================================")

    return {
        "ammissibile": ammissibile,
        "punteggio": max(0, punteggio),
        "errori": errori,
        "warnings": warnings,
        "suggerimenti": suggerimenti
    }


# ==============================================================================
# TEST
# ==============================================================================
if __name__ == "__main__":
    # Test 1: Ibrido factory made valido
    print("\n" + "="*80)
    print("TEST 1: Ibrido Factory Made - Caso valido")
    print("="*80)
    result1 = valida_requisiti_ibridi(
        tipo_sistema="ibrido_factory_made",
        potenza_pdc_kw=8.0,
        potenza_caldaia_kw=20.0,
        scop_pdc=4.2,
        eta_s_caldaia=92.0,
        classe_termoregolazione="VI",
        ha_valvole_termostatiche=True,
        ha_contabilizzazione=False,
        tipo_soggetto="privato",
        integra_caldaia_gas=True
    )
    print(f"\nAmmissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    print(f"Errori: {len(result1['errori'])}")
    print(f"Warnings: {len(result1['warnings'])}")

    # Test 2: Sistema bivalente con fabbricanti diversi senza asseverazione
    print("\n" + "="*80)
    print("TEST 2: Bivalente - Fabbricanti diversi senza asseverazione (ERRORE)")
    print("="*80)
    result2 = valida_requisiti_ibridi(
        tipo_sistema="bivalente",
        potenza_pdc_kw=12.0,
        potenza_caldaia_kw=25.0,
        scop_pdc=3.8,
        eta_s_caldaia=95.0,
        classe_termoregolazione="VII",
        ha_valvole_termostatiche=True,
        fabbricanti_diversi=True,
        ha_asseverazione_compatibilita=False,
        tipo_soggetto="privato"
    )
    print(f"\nAmmissibile: {result2['ammissibile']}")
    print(f"Errori: {result2['errori']}")

    # Test 3: Add-on con caldaia troppo vecchia
    print("\n" + "="*80)
    print("TEST 3: Add-On - Caldaia > 5 anni (ERRORE)")
    print("="*80)
    result3 = valida_requisiti_ibridi(
        tipo_sistema="add_on",
        potenza_pdc_kw=10.0,
        potenza_caldaia_kw=30.0,
        scop_pdc=3.5,
        eta_s_caldaia=93.0,
        tipo_pdc="aria_acqua",
        classe_termoregolazione="V",
        ha_valvole_termostatiche=True,
        eta_caldaia_preesistente_anni=7,
        tipo_caldaia_preesistente="condensazione_gas",
        tipo_soggetto="privato"
    )
    print(f"\nAmmissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    # Test 4: Sistema con P > 200 kW senza contabilizzazione
    print("\n" + "="*80)
    print("TEST 4: P > 200 kW senza contabilizzazione (ERRORE)")
    print("="*80)
    result4 = valida_requisiti_ibridi(
        tipo_sistema="ibrido_factory_made",
        potenza_pdc_kw=80.0,
        potenza_caldaia_kw=180.0,
        scop_pdc=3.9,
        eta_s_caldaia=94.0,
        classe_termoregolazione="VIII",
        ha_valvole_termostatiche=True,
        ha_contabilizzazione=False,
        ha_ape_post_operam=True,
        ha_diagnosi_ante_operam=True,
        potenza_totale_impianto_kw=260.0,
        tipo_soggetto="privato"
    )
    print(f"\nAmmissibile: {result4['ammissibile']}")
    print(f"Errori: {result4['errori']}")

    # Test 5: Impresa con caldaia a gas (ERRORE)
    print("\n" + "="*80)
    print("TEST 5: Impresa con caldaia a gas (ERRORE)")
    print("="*80)
    result5 = valida_requisiti_ibridi(
        tipo_sistema="ibrido_factory_made",
        potenza_pdc_kw=15.0,
        potenza_caldaia_kw=30.0,
        scop_pdc=4.0,
        eta_s_caldaia=93.0,
        classe_termoregolazione="VI",
        ha_valvole_termostatiche=True,
        tipo_soggetto="impresa",
        integra_caldaia_gas=True
    )
    print(f"\nAmmissibile: {result5['ammissibile']}")
    print(f"Errori: {result5['errori']}")
