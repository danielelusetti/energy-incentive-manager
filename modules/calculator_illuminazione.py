"""
Modulo per il calcolo degli incentivi per l'intervento II.E
Sostituzione di sistemi per l'illuminazione d'interni e delle pertinenze esterne

Include SOLO calcolo Conto Termico 3.0 (NO Ecobonus, NO Bonus Ristrutturazione)

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.5
"""

from typing import Dict
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==============================================================================
# PARAMETRI DI RIFERIMENTO (da Regole Applicative CT 3.0 - Par. 9.5, Tabella 7)
# ==============================================================================

# Tabella 20 - Allegato 2 - Parametri II.E (D.M. 7 agosto 2025)
# NOTA: Esistono DUE tipologie con parametri diversi
PARAMETRI_ILLUMINAZIONE = {
    "alta_efficienza": {  # Lampade ad alta efficienza
        "percentuale_base": 0.40,
        "percentuale_pa_edifici_pubblici": 1.00,
        "costo_max_mq": 15.0,  # €/m²
        "incentivo_max": 50000.0,  # €
    },
    "led": {  # Lampade a LED
        "percentuale_base": 0.40,
        "percentuale_pa_edifici_pubblici": 1.00,
        "costo_max_mq": 35.0,  # €/m²
        "incentivo_max": 140000.0,  # €
    },
    "soglia_rata_unica": 15000.0,  # € - sotto questa soglia, erogazione in unica soluzione
    "anni_rateazione": 5  # anni
}

MASSIMALE_COMPLESSIVO = 500000.0  # € - massimale totale interventi Titolo II


def calculate_lighting_incentive(
    # Dati superficie e spesa
    superficie_illuminata_mq: float = 0.0,
    spesa_sostenuta: float = 0.0,

    # Tipo lampada (IMPORTANTE: determinare i massimali corretti)
    tipo_lampada: str = "led",  # "led" o "alta_efficienza"

    # Dati potenza (per calcolo spesa ammissibile se impianto sottodimensionato)
    potenza_ante_operam_w: float = 0.0,
    potenza_post_operam_w: float = 0.0,
    impianto_sottodimensionato_ante: bool = False,

    # Soggetto e tipo edificio
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    tipo_edificio: str = "residenziale",  # "residenziale", "terziario", "pubblico"

    # Premialità componenti UE (opzionale)
    usa_premialita_componenti_ue: bool = False
) -> Dict:
    """
    Calcola l'incentivo CT 3.0 per l'intervento II.E - Illuminazione LED

    Formula: I_tot = %_spesa × C × S_ed
    con I_tot ≤ I_max

    Args:
        superficie_illuminata_mq: Superficie utile calpestabile illuminata (m²)
        spesa_sostenuta: Spesa totale sostenuta (€)
        potenza_ante_operam_w: Potenza impianto ante-operam (W)
        potenza_post_operam_w: Potenza impianto post-operam (W)
        impianto_sottodimensionato_ante: Se True, impianto ante era sottodimensionato
        tipo_soggetto: Tipologia soggetto beneficiario
        tipo_edificio: Tipologia edificio
        usa_premialita_componenti_ue: Se True, applica +10% per componenti UE

    Returns:
        Dict con dettagli incentivo CT 3.0
    """

    logger.info("=" * 60)
    logger.info("AVVIO CALCOLO INCENTIVO CT 3.0 - ILLUMINAZIONE (II.E)")
    logger.info("=" * 60)
    logger.info(f"Tipo lampada: {tipo_lampada}")
    logger.info(f"Tipo soggetto: {tipo_soggetto}")
    logger.info(f"Tipo edificio: {tipo_edificio}")

    # Recupera parametri in base al tipo di lampada
    if tipo_lampada not in PARAMETRI_ILLUMINAZIONE:
        tipo_lampada = "led"  # Default a LED
    params = PARAMETRI_ILLUMINAZIONE[tipo_lampada]
    costo_max_mq = params["costo_max_mq"]
    incentivo_max = params["incentivo_max"]

    logger.info(f"Parametri Tabella 20: C_max = {costo_max_mq} €/m², I_max = {incentivo_max:,.0f} €")

    # =========================================================================
    # STEP 1: Determinazione percentuale incentivata
    # =========================================================================

    # PA su edifici pubblici: 100%, altri: 40%
    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        percentuale_incentivo = params["percentuale_pa_edifici_pubblici"]
        logger.info(f"Percentuale incentivo: 100% (PA su edificio pubblico)")
    else:
        percentuale_incentivo = params["percentuale_base"]
        logger.info(f"Percentuale incentivo: 40%")

    # =========================================================================
    # STEP 2: Calcolo costo specifico e spesa ammissibile
    # =========================================================================

    logger.info("")
    logger.info("[STEP 2] Calcolo spesa ammissibile")
    logger.info(f"  Superficie illuminata: {superficie_illuminata_mq:.2f} m²")
    logger.info(f"  Spesa sostenuta: {spesa_sostenuta:,.2f} €")

    if superficie_illuminata_mq <= 0:
        logger.error("  ERRORE: Superficie deve essere > 0")
        return {
            "incentivo_totale": 0.0,
            "spesa_ammissibile": 0.0,
            "anni_erogazione": 0,
            "dettagli": "Errore: superficie non valida"
        }

    # Costo specifico effettivo
    costo_specifico = spesa_sostenuta / superficie_illuminata_mq
    logger.info(f"  Costo specifico: {costo_specifico:.2f} €/m²")
    logger.info(f"  Costo massimo ammissibile: {costo_max_mq:.2f} €/m²")

    # Applica il minimo tra costo effettivo e massimo ammissibile
    costo_ammissibile = min(costo_specifico, costo_max_mq)
    logger.info(f"  Costo ammissibile: {costo_ammissibile:.2f} €/m²")

    # Spesa ammissibile base
    spesa_ammissibile_base = costo_ammissibile * superficie_illuminata_mq
    logger.info(f"  Spesa ammissibile base: {spesa_ammissibile_base:,.2f} €")

    # =========================================================================
    # STEP 3: Riduzione spesa se impianto sottodimensionato ante-operam
    # =========================================================================

    logger.info("")
    logger.info("[STEP 3] Verifica sottodimensionamento impianto ante-operam")

    spesa_ammissibile = spesa_ammissibile_base
    riduzione_applicata = False

    if impianto_sottodimensionato_ante and potenza_ante_operam_w > 0 and potenza_post_operam_w > 0:
        rapporto_potenza = (potenza_post_operam_w / potenza_ante_operam_w) * 100

        if rapporto_potenza > 50:
            # L'incentivo è ammissibile solo per la quota potenza pari al 50% della potenza sostituita
            fattore_riduzione = 0.50  # Solo 50% della spesa è incentivabile
            spesa_ammissibile = spesa_ammissibile_base * fattore_riduzione
            riduzione_applicata = True

            logger.info(f"  Impianto ante-operam SOTTODIMENSIONATO rispetto a UNI EN 12464-1")
            logger.info(f"  Potenza ante: {potenza_ante_operam_w:.0f} W")
            logger.info(f"  Potenza post: {potenza_post_operam_w:.0f} W")
            logger.info(f"  Rapporto potenza: {rapporto_potenza:.1f}% (> 50%)")
            logger.info(f"  Fattore riduzione spesa: {fattore_riduzione:.2f}")
            logger.info(f"  Spesa ammissibile ridotta: {spesa_ammissibile:,.2f} €")
    else:
        logger.info(f"  Nessuna riduzione per sottodimensionamento")
        if potenza_ante_operam_w > 0 and potenza_post_operam_w > 0:
            rapporto_potenza = (potenza_post_operam_w / potenza_ante_operam_w) * 100
            logger.info(f"  Rapporto potenza post/ante: {rapporto_potenza:.1f}%")
            logger.info(f"  ✓ Requisito potenza post ≤ 50% ante rispettato")

    # =========================================================================
    # STEP 4: Calcolo incentivo lordo
    # =========================================================================

    logger.info("")
    logger.info("[STEP 4] Calcolo incentivo lordo")

    incentivo_lordo = percentuale_incentivo * spesa_ammissibile
    logger.info(f"  I_lordo = {percentuale_incentivo:.0%} × {spesa_ammissibile:,.2f} = {incentivo_lordo:,.2f} €")

    # =========================================================================
    # STEP 5: Applicazione premialità componenti UE (+10%)
    # =========================================================================

    logger.info("")
    logger.info("[STEP 5] Premialità componenti UE")

    incentivo_con_premialita = incentivo_lordo

    if usa_premialita_componenti_ue:
        premialita_ue = incentivo_lordo * 0.10
        incentivo_con_premialita = incentivo_lordo + premialita_ue
        logger.info(f"  Premialità UE (+10%): {premialita_ue:,.2f} €")
        logger.info(f"  Incentivo con premialità: {incentivo_con_premialita:,.2f} €")
    else:
        logger.info(f"  Premialità UE non applicata")

    # =========================================================================
    # STEP 6: Applicazione massimale incentivo
    # =========================================================================

    logger.info("")
    logger.info("[STEP 6] Applicazione massimale")
    logger.info(f"  Incentivo (prima massimale): {incentivo_con_premialita:,.2f} €")
    logger.info(f"  Massimale intervento II.E ({tipo_lampada}): {incentivo_max:,.2f} €")
    logger.info(f"  Massimale complessivo Titolo II: {MASSIMALE_COMPLESSIVO:,.2f} €")

    incentivo_finale = min(incentivo_con_premialita, incentivo_max)

    if incentivo_finale < incentivo_con_premialita:
        logger.info(f"  ⚠️ Incentivo limitato dal massimale di {incentivo_max:,.2f} €")

    logger.info(f"  Incentivo finale: {incentivo_finale:,.2f} €")

    # =========================================================================
    # STEP 7: Determinazione modalità erogazione
    # =========================================================================

    logger.info("")
    logger.info("[STEP 7] Determinazione rateazione")

    # PA/ETS su edifici pubblici: sempre rata unica
    # Altri: rata unica se ≤ 15.000€, altrimenti 5 anni
    soglia_rata_unica = PARAMETRI_ILLUMINAZIONE["soglia_rata_unica"]
    anni_rateazione = PARAMETRI_ILLUMINAZIONE["anni_rateazione"]

    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        anni_erogazione = 1
        logger.info(f"  PA su edificio pubblico → Erogazione in RATA UNICA")
    elif incentivo_finale <= soglia_rata_unica:
        anni_erogazione = 1
        logger.info(f"  Incentivo {incentivo_finale:,.2f} € ≤ {soglia_rata_unica:,.2f} € → Rata unica")
    else:
        anni_erogazione = anni_rateazione
        rata_annuale = incentivo_finale / anni_erogazione
        logger.info(f"  Incentivo {incentivo_finale:,.2f} € > {soglia_rata_unica:,.2f} €")
        logger.info(f"  Erogazione in {anni_erogazione} rate annuali di {rata_annuale:,.2f} €")

    # =========================================================================
    # RISULTATO FINALE
    # =========================================================================

    logger.info("")
    logger.info("=" * 60)
    logger.info("CALCOLO COMPLETATO CON SUCCESSO")
    logger.info(f"INCENTIVO TOTALE: {incentivo_finale:,.2f} €")
    logger.info(f"EROGAZIONE: {anni_erogazione} anni")
    logger.info("=" * 60)

    # Costruisci messaggio dettagliato
    dettagli = []
    dettagli.append(f"Superficie illuminata: {superficie_illuminata_mq:.2f} m²")
    dettagli.append(f"Spesa sostenuta: {spesa_sostenuta:,.2f} €")
    dettagli.append(f"Costo specifico: {costo_specifico:.2f} €/m² (max: {costo_max_mq:.2f} €/m²)")
    dettagli.append(f"Spesa ammissibile: {spesa_ammissibile:,.2f} €")

    if riduzione_applicata:
        dettagli.append(f"⚠️ Riduzione per sottodimensionamento ante-operam applicata")

    dettagli.append(f"Percentuale incentivo: {percentuale_incentivo:.0%}")

    if usa_premialita_componenti_ue:
        dettagli.append(f"Premialità UE: +10%")

    dettagli.append(f"Incentivo finale: {incentivo_finale:,.2f} €")
    dettagli.append(f"Erogazione: {anni_erogazione} {'anno' if anni_erogazione == 1 else 'anni'}")

    return {
        "incentivo_totale": round(incentivo_finale, 2),
        "spesa_ammissibile": round(spesa_ammissibile, 2),
        "spesa_sostenuta": round(spesa_sostenuta, 2),
        "superficie_mq": round(superficie_illuminata_mq, 2),
        "costo_specifico": round(costo_specifico, 2),
        "costo_specifico_ammissibile": round(costo_ammissibile, 2),
        "percentuale_incentivo": percentuale_incentivo,
        "incentivo_lordo": round(incentivo_lordo, 2),
        "premialita_ue": round(incentivo_con_premialita - incentivo_lordo, 2) if usa_premialita_componenti_ue else 0.0,
        "riduzione_sottodimensionamento": riduzione_applicata,
        "anni_erogazione": anni_erogazione,
        "rata_annuale": round(incentivo_finale / anni_erogazione, 2),
        "dettagli": "\n".join(dettagli),
        "tipo_soggetto": tipo_soggetto,
        "tipo_edificio": tipo_edificio
    }


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST CALCOLO INCENTIVI ILLUMINAZIONE LED")
    print("=" * 80)

    # Test 1: Soggetto privato, edificio residenziale
    print("\n[TEST 1] Privato - Edificio residenziale")
    result1 = calculate_lighting_incentive(
        superficie_illuminata_mq=200.0,
        spesa_sostenuta=2400.0,  # 12 €/m²
        potenza_ante_operam_w=10000.0,
        potenza_post_operam_w=4000.0,  # 40% dell'ante
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"\nIncentivo totale: {result1['incentivo_totale']:,.2f} €")
    print(f"Anni erogazione: {result1['anni_erogazione']}")
    print(f"Rata annuale: {result1['rata_annuale']:,.2f} €")

    # Test 2: PA su edificio pubblico (100%)
    print("\n[TEST 2] PA - Edificio pubblico (100%)")
    result2 = calculate_lighting_incentive(
        superficie_illuminata_mq=500.0,
        spesa_sostenuta=7000.0,  # 14 €/m²
        potenza_ante_operam_w=25000.0,
        potenza_post_operam_w=10000.0,  # 40% dell'ante
        tipo_soggetto="pa",
        tipo_edificio="pubblico"
    )
    print(f"\nIncentivo totale: {result2['incentivo_totale']:,.2f} €")
    print(f"Anni erogazione: {result2['anni_erogazione']}")

    # Test 3: Impianto sottodimensionato ante-operam
    print("\n[TEST 3] Impianto sottodimensionato ante-operam")
    result3 = calculate_lighting_incentive(
        superficie_illuminata_mq=150.0,
        spesa_sostenuta=2000.0,
        potenza_ante_operam_w=5000.0,
        potenza_post_operam_w=3500.0,  # 70% dell'ante - > 50%
        impianto_sottodimensionato_ante=True,
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"\nIncentivo totale: {result3['incentivo_totale']:,.2f} €")
    print(f"Riduzione sottodimensionamento: {result3['riduzione_sottodimensionamento']}")

    # Test 4: Con premialità UE
    print("\n[TEST 4] Con premialità componenti UE (+10%)")
    result4 = calculate_lighting_incentive(
        superficie_illuminata_mq=300.0,
        spesa_sostenuta=4200.0,  # 14 €/m²
        potenza_ante_operam_w=15000.0,
        potenza_post_operam_w=6000.0,  # 40% dell'ante
        tipo_soggetto="impresa",
        tipo_edificio="terziario",
        usa_premialita_componenti_ue=True
    )
    print(f"\nIncentivo totale: {result4['incentivo_totale']:,.2f} €")
    print(f"Premialità UE: {result4['premialita_ue']:,.2f} €")

    # Test 5: Costo specifico supera il massimale
    print("\n[TEST 5] Costo specifico > 15 €/m²")
    result5 = calculate_lighting_incentive(
        superficie_illuminata_mq=100.0,
        spesa_sostenuta=2000.0,  # 20 €/m² > 15 €/m² max
        potenza_ante_operam_w=5000.0,
        potenza_post_operam_w=2000.0,
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"\nCosto specifico: {result5['costo_specifico']:.2f} €/m²")
    print(f"Costo ammissibile: {result5['costo_specifico_ammissibile']:.2f} €/m²")
    print(f"Incentivo totale: {result5['incentivo_totale']:,.2f} €")

    print("\n" + "=" * 80)
