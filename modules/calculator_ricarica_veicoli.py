"""
Modulo per il calcolo dell'incentivo CT 3.0 per l'intervento II.G
Installazione di elementi infrastrutturali per la ricarica privata di veicoli elettrici

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.7.3
"""

from typing import Dict


# ==============================================================================
# PARAMETRI CT 3.0 - INFRASTRUTTURA RICARICA VEICOLI ELETTRICI
# ==============================================================================

# Tabella 22 - Costo massimo ammissibile per tecnologia
COSTI_MASSIMI_RICARICA = {
    "standard_monofase": 2400.0,  # €/punto (7.4 kW < P ≤ 22 kW, monofase)
    "standard_trifase": 8400.0,   # €/punto (7.4 kW < P ≤ 22 kW, trifase)
    "potenza_media": 1200.0,      # €/kW (22 kW < P ≤ 50 kW)
    "potenza_alta_100": 60000.0,  # €/infrastruttura (50 kW < P ≤ 100 kW)
    "potenza_alta_over100": 110000.0  # €/infrastruttura (P > 100 kW)
}

PARAMETRI_RICARICA = {
    "percentuale_base": 0.30,  # 30% spese sostenute
    "percentuale_pa_edifici_pubblici": 1.00,  # 100% per PA su edifici pubblici
    # Anni erogazione dipendono dalla PdC combinata:
    # P_pdc ≤ 35 kW → 2 rate
    # P_pdc > 35 kW → 5 rate
    # oppure rata unica se ≤ 15.000€
}


# ==============================================================================
# CALCOLO INCENTIVO II.G
# ==============================================================================

def calculate_ev_charging_incentive(
    # Dati infrastruttura
    tipo_infrastruttura: str = "standard_monofase",
    numero_punti_ricarica: int = 1,
    potenza_installata_kw: float = 7.4,
    spesa_sostenuta: float = 0.0,

    # Dati pompa di calore COMBINATA (obbligatoria)
    incentivo_pompa_calore: float = 0.0,  # I_tot PdC (limite massimo)
    potenza_pdc_kw: float = 0.0,  # Per determinare anni erogazione

    # Tipo soggetto
    tipo_soggetto: str = "privato",
    tipo_edificio: str = "residenziale",

    # Tasso sconto per NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Calcola l'incentivo CT 3.0 per l'intervento II.G - Infrastruttura Ricarica Veicoli Elettrici

    Formula: I = min(30% × C_tot; I_pompa_calore)

    IMPORTANTE: L'incentivo per la ricarica NON può superare l'incentivo della pompa di calore combinata

    Returns:
        Dict con chiavi:
        - incentivo_totale: float
        - spesa_ammissibile: float
        - anni_erogazione: int
        - rata_annuale: float
        - npv: float
        - dettagli: Dict
    """

    risultato = {
        "incentivo_totale": 0.0,
        "spesa_ammissibile": 0.0,
        "anni_erogazione": 0,
        "rata_annuale": 0.0,
        "npv": 0.0,
        "dettagli": {}
    }

    if spesa_sostenuta <= 0:
        risultato["dettagli"]["errore"] = "Spesa sostenuta deve essere > 0"
        return risultato

    if incentivo_pompa_calore <= 0:
        risultato["dettagli"]["errore"] = "Incentivo pompa di calore deve essere > 0 (calcola prima la PdC)"
        return risultato

    # 1. Determina costo massimo ammissibile in base alla tipologia
    if tipo_infrastruttura == "standard_monofase":
        costo_max_per_unita = COSTI_MASSIMI_RICARICA["standard_monofase"]
        spesa_max_ammissibile = costo_max_per_unita * numero_punti_ricarica
        nota_costo = f"{costo_max_per_unita:.0f} €/punto × {numero_punti_ricarica} punti"

    elif tipo_infrastruttura == "standard_trifase":
        costo_max_per_unita = COSTI_MASSIMI_RICARICA["standard_trifase"]
        spesa_max_ammissibile = costo_max_per_unita * numero_punti_ricarica
        nota_costo = f"{costo_max_per_unita:.0f} €/punto × {numero_punti_ricarica} punti"

    elif tipo_infrastruttura == "potenza_media":
        # 22 kW < P ≤ 50 kW: 1.200 €/kW
        costo_max_per_kw = COSTI_MASSIMI_RICARICA["potenza_media"]
        spesa_max_ammissibile = costo_max_per_kw * potenza_installata_kw
        nota_costo = f"{costo_max_per_kw:.0f} €/kW × {potenza_installata_kw:.1f} kW"

    elif tipo_infrastruttura == "potenza_alta_100":
        # 50 kW < P ≤ 100 kW: 60.000 €/infrastruttura
        spesa_max_ammissibile = COSTI_MASSIMI_RICARICA["potenza_alta_100"]
        nota_costo = f"{spesa_max_ammissibile:.0f} €/infrastruttura"

    elif tipo_infrastruttura == "potenza_alta_over100":
        # P > 100 kW: 110.000 €/infrastruttura
        spesa_max_ammissibile = COSTI_MASSIMI_RICARICA["potenza_alta_over100"]
        nota_costo = f"{spesa_max_ammissibile:.0f} €/infrastruttura"

    else:
        risultato["dettagli"]["errore"] = f"Tipologia infrastruttura '{tipo_infrastruttura}' non valida"
        return risultato

    # 2. Spesa ammissibile (cap al massimo)
    spesa_ammissibile = min(spesa_sostenuta, spesa_max_ammissibile)

    if spesa_sostenuta > spesa_max_ammissibile:
        nota_cap_spesa = f"Spesa {spesa_sostenuta:.2f} € > {spesa_max_ammissibile:.2f} € (massimo ammissibile)"
    else:
        nota_cap_spesa = f"Spesa entro il limite ammissibile"

    # 3. Determina percentuale incentivo
    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        percentuale = PARAMETRI_RICARICA["percentuale_pa_edifici_pubblici"]
        tipo_percentuale = "PA edifici pubblici (100%)"
    else:
        percentuale = PARAMETRI_RICARICA["percentuale_base"]
        tipo_percentuale = "Base (30%)"

    # 4. Calcola incentivo prima del cap con pompa di calore
    incentivo_calcolato = percentuale * spesa_ammissibile

    # 5. REQUISITO CRITICO: Cap all'incentivo pompa di calore
    if incentivo_calcolato > incentivo_pompa_calore:
        incentivo_totale = incentivo_pompa_calore
        nota_limite_pdc = (
            f"Incentivo calcolato {incentivo_calcolato:.2f} € > Incentivo PdC {incentivo_pompa_calore:.2f} €. "
            f"Applicato limite (I_ricarica ≤ I_pompa_calore)"
        )
    else:
        incentivo_totale = incentivo_calcolato
        nota_limite_pdc = f"Incentivo entro il limite della pompa di calore ({incentivo_pompa_calore:.2f} €)"

    # 6. Determina anni di erogazione (dipende dalla PdC)
    soglia_rata_unica = 15000.0

    if incentivo_totale <= soglia_rata_unica:
        anni_erogazione = 1
        nota_rateazione = f"Rata unica (≤ {soglia_rata_unica:.0f} €)"
    else:
        # Dipende dalla potenza della PdC combinata
        if potenza_pdc_kw <= 35:
            anni_erogazione = 2
            nota_rateazione = f"2 rate annuali (P_PdC ≤ 35 kW)"
        else:
            anni_erogazione = 5
            nota_rateazione = f"5 rate annuali (P_PdC > 35 kW)"

    rata_annuale = incentivo_totale / anni_erogazione

    # 7. Calcola NPV
    if anni_erogazione == 1:
        npv = incentivo_totale
    else:
        npv = sum(rata_annuale / ((1 + tasso_sconto) ** anno) for anno in range(1, anni_erogazione + 1))

    # 8. Compila risultato
    risultato.update({
        "incentivo_totale": round(incentivo_totale, 2),
        "spesa_ammissibile": round(spesa_ammissibile, 2),
        "anni_erogazione": anni_erogazione,
        "rata_annuale": round(rata_annuale, 2),
        "npv": round(npv, 2),
        "dettagli": {
            "tipo_infrastruttura": tipo_infrastruttura,
            "numero_punti_ricarica": numero_punti_ricarica,
            "potenza_installata_kw": potenza_installata_kw,
            "spesa_sostenuta": spesa_sostenuta,
            "spesa_max_ammissibile": spesa_max_ammissibile,
            "nota_costo": nota_costo,
            "nota_cap_spesa": nota_cap_spesa,
            "percentuale": percentuale,
            "tipo_percentuale": tipo_percentuale,
            "incentivo_calcolato": round(incentivo_calcolato, 2),
            "incentivo_pdc_limite": incentivo_pompa_calore,
            "nota_limite_pdc": nota_limite_pdc,
            "potenza_pdc_kw": potenza_pdc_kw,
            "nota_rateazione": nota_rateazione,
            "tasso_sconto_npv": tasso_sconto
        }
    })

    return risultato


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST CALCOLO INCENTIVO INFRASTRUTTURA RICARICA VEICOLI ELETTRICI")
    print("=" * 80)

    # Test 1: Standard monofase - 1 punto
    print("\n[TEST 1] Standard monofase - 1 punto ricarica")
    result1 = calculate_ev_charging_incentive(
        tipo_infrastruttura="standard_monofase",
        numero_punti_ricarica=1,
        potenza_installata_kw=7.4,
        spesa_sostenuta=2400.0,
        incentivo_pompa_calore=5000.0,  # Incentivo PdC
        potenza_pdc_kw=12.0,
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"Spesa: {result1['spesa_ammissibile']:.2f} €")
    print(f"Incentivo: {result1['incentivo_totale']:.2f} € ({result1['dettagli']['tipo_percentuale']})")
    print(f"NPV: {result1['npv']:.2f} €")
    print(f"Erogazione: {result1['anni_erogazione']} anni")
    print(f"Nota: {result1['dettagli']['nota_limite_pdc']}")

    # Test 2: Standard trifase - 2 punti
    print("\n[TEST 2] Standard trifase - 2 punti ricarica")
    result2 = calculate_ev_charging_incentive(
        tipo_infrastruttura="standard_trifase",
        numero_punti_ricarica=2,
        potenza_installata_kw=22.0,
        spesa_sostenuta=16800.0,  # 8400 × 2
        incentivo_pompa_calore=12000.0,
        potenza_pdc_kw=40.0,  # > 35 kW → 5 rate
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"Spesa: {result2['spesa_ammissibile']:.2f} €")
    print(f"Incentivo: {result2['incentivo_totale']:.2f} € ({result2['dettagli']['tipo_percentuale']})")
    print(f"NPV: {result2['npv']:.2f} €")
    print(f"Erogazione: {result2['anni_erogazione']} anni × {result2['rata_annuale']:.2f} €/anno")
    print(f"Nota: {result2['dettagli']['nota_limite_pdc']}")

    # Test 3: Potenza media - con limite PdC
    print("\n[TEST 3] Potenza media 40 kW - incentivo limitato da PdC")
    result3 = calculate_ev_charging_incentive(
        tipo_infrastruttura="potenza_media",
        numero_punti_ricarica=1,
        potenza_installata_kw=40.0,
        spesa_sostenuta=48000.0,  # 1200 × 40
        incentivo_pompa_calore=10000.0,  # Limite più basso
        potenza_pdc_kw=25.0,
        tipo_soggetto="privato",
        tipo_edificio="residenziale"
    )
    print(f"Spesa: {result3['spesa_ammissibile']:.2f} €")
    print(f"Incentivo calcolato: {result3['dettagli']['incentivo_calcolato']:.2f} €")
    print(f"Incentivo effettivo: {result3['incentivo_totale']:.2f} € (limitato da PdC)")
    print(f"NPV: {result3['npv']:.2f} €")
    print(f"Nota: {result3['dettagli']['nota_limite_pdc']}")

    # Test 4: PA edifici pubblici (100%)
    print("\n[TEST 4] PA edifici pubblici - 100%")
    result4 = calculate_ev_charging_incentive(
        tipo_infrastruttura="potenza_alta_100",
        numero_punti_ricarica=1,
        potenza_installata_kw=75.0,
        spesa_sostenuta=60000.0,
        incentivo_pompa_calore=80000.0,
        potenza_pdc_kw=50.0,
        tipo_soggetto="pa",
        tipo_edificio="pubblico"
    )
    print(f"Spesa: {result4['spesa_ammissibile']:.2f} €")
    print(f"Incentivo: {result4['incentivo_totale']:.2f} € ({result4['dettagli']['tipo_percentuale']})")
    print(f"NPV: {result4['npv']:.2f} €")
    print(f"Erogazione: {result4['anni_erogazione']} anni × {result4['rata_annuale']:.2f} €/anno")

    # Test 5: Potenza alta over 100 kW
    print("\n[TEST 5] Potenza alta > 100 kW")
    result5 = calculate_ev_charging_incentive(
        tipo_infrastruttura="potenza_alta_over100",
        numero_punti_ricarica=1,
        potenza_installata_kw=150.0,
        spesa_sostenuta=110000.0,
        incentivo_pompa_calore=50000.0,
        potenza_pdc_kw=60.0,
        tipo_soggetto="privato",
        tipo_edificio="terziario"
    )
    print(f"Spesa: {result5['spesa_ammissibile']:.2f} €")
    print(f"Incentivo calcolato (30%): {result5['dettagli']['incentivo_calcolato']:.2f} €")
    print(f"Incentivo effettivo: {result5['incentivo_totale']:.2f} € (limitato da PdC)")
    print(f"NPV: {result5['npv']:.2f} €")

    print("\n" + "=" * 80)
