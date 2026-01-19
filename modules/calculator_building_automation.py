"""
Modulo per il calcolo dell'incentivo CT 3.0 per l'intervento II.F
Installazione di tecnologie di gestione e controllo automatico (Building Automation)

Include anche il confronto con Ecobonus e Bonus Ristrutturazione
"""

from typing import Dict, Literal


# ==============================================================================
# PARAMETRI CT 3.0 - BUILDING AUTOMATION
# ==============================================================================

PARAMETRI_BUILDING_AUTOMATION = {
    "percentuale_base": 0.40,  # 40% per privati, imprese, ETS
    "percentuale_pa_edifici_pubblici": 1.00,  # 100% per PA su edifici pubblici
    "costo_max_mq": 60.0,  # €/m²
    "incentivo_max": 100000.0,  # €
    "soglia_rata_unica": 15000.0,  # €
    "anni_rateazione": 5,
    "maggiorazione_componenti_ue": 0.10  # +10% se ≥70% componenti UE
}


# ==============================================================================
# CALCOLO INCENTIVO CT 3.0
# ==============================================================================

def calculate_building_automation_incentive(
    # Dati base
    superficie_utile_mq: float = 0.0,
    spesa_sostenuta: float = 0.0,

    # Tipo soggetto
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    tipo_edificio: str = "residenziale",  # "residenziale", "terziario", "pubblico"

    # Premialità
    usa_premialita_componenti_ue: bool = False,

    # Tasso sconto per NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Calcola l'incentivo CT 3.0 per l'intervento II.F - Building Automation

    Formula: I = P% × C × S

    Returns:
        Dict con chiavi:
        - incentivo_totale: float
        - spesa_ammissibile: float
        - anni_erogazione: int
        - rata_annuale: float
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

    if superficie_utile_mq <= 0 or spesa_sostenuta <= 0:
        risultato["dettagli"]["errore"] = "Superficie e spesa devono essere > 0"
        return risultato

    # 1. Determina la percentuale di incentivo
    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        percentuale = PARAMETRI_BUILDING_AUTOMATION["percentuale_pa_edifici_pubblici"]
        tipo_percentuale = "PA edifici pubblici"
    else:
        percentuale = PARAMETRI_BUILDING_AUTOMATION["percentuale_base"]
        tipo_percentuale = "Base (privati, imprese, ETS)"

    # 2. Applica premialità componenti UE
    if usa_premialita_componenti_ue:
        percentuale += PARAMETRI_BUILDING_AUTOMATION["maggiorazione_componenti_ue"]
        tipo_percentuale += " + Premialità UE"

    # 3. Calcola costo specifico
    costo_specifico = spesa_sostenuta / superficie_utile_mq
    costo_max = PARAMETRI_BUILDING_AUTOMATION["costo_max_mq"]

    # 4. Spesa ammissibile (cap al costo specifico massimo)
    if costo_specifico > costo_max:
        spesa_ammissibile = costo_max * superficie_utile_mq
        nota_costo = f"Costo specifico {costo_specifico:.2f} €/m² > {costo_max} €/m² (massimo ammissibile)"
    else:
        spesa_ammissibile = spesa_sostenuta
        nota_costo = f"Costo specifico {costo_specifico:.2f} €/m² entro il limite"

    # 5. Calcola incentivo totale
    incentivo_calcolato = percentuale * spesa_ammissibile

    # 6. Applica cap massimo
    incentivo_max = PARAMETRI_BUILDING_AUTOMATION["incentivo_max"]
    if incentivo_calcolato > incentivo_max:
        incentivo_totale = incentivo_max
        nota_cap = f"Incentivo calcolato {incentivo_calcolato:.2f} € limitato a {incentivo_max:.2f} €"
    else:
        incentivo_totale = incentivo_calcolato
        nota_cap = "Entro il limite massimo"

    # 7. Determina anni di erogazione
    soglia_rata_unica = PARAMETRI_BUILDING_AUTOMATION["soglia_rata_unica"]
    if incentivo_totale <= soglia_rata_unica:
        anni_erogazione = 1
        nota_rateazione = f"Rata unica (≤ {soglia_rata_unica:.0f} €)"
    else:
        anni_erogazione = PARAMETRI_BUILDING_AUTOMATION["anni_rateazione"]
        nota_rateazione = f"Rateizzato in {anni_erogazione} anni"

    rata_annuale = incentivo_totale / anni_erogazione

    # 8. Calcola NPV
    if anni_erogazione == 1:
        npv = incentivo_totale
    else:
        npv = sum(rata_annuale / ((1 + tasso_sconto) ** anno) for anno in range(1, anni_erogazione + 1))

    # 9. Compila risultato
    risultato.update({
        "incentivo_totale": round(incentivo_totale, 2),
        "spesa_ammissibile": round(spesa_ammissibile, 2),
        "anni_erogazione": anni_erogazione,
        "rata_annuale": round(rata_annuale, 2),
        "npv": round(npv, 2),
        "dettagli": {
            "superficie_mq": superficie_utile_mq,
            "spesa_sostenuta": spesa_sostenuta,
            "costo_specifico": round(costo_specifico, 2),
            "costo_max_mq": costo_max,
            "nota_costo": nota_costo,
            "percentuale": percentuale,
            "tipo_percentuale": tipo_percentuale,
            "incentivo_calcolato": round(incentivo_calcolato, 2),
            "incentivo_max": incentivo_max,
            "nota_cap": nota_cap,
            "nota_rateazione": nota_rateazione,
            "tasso_sconto_npv": tasso_sconto
        }
    })

    return risultato


# ==============================================================================
# CONFRONTO CON ECOBONUS E BONUS RISTRUTTURAZIONE
# ==============================================================================

def confronta_incentivi_building_automation(
    # Dati base
    superficie_utile_mq: float = 0.0,
    spesa_sostenuta: float = 0.0,

    # CT 3.0
    tipo_soggetto_ct: str = "privato",
    tipo_edificio_ct: str = "residenziale",
    usa_premialita_componenti_ue: bool = False,

    # Ecobonus
    tipo_immobile_eco: Literal["principale", "altro"] = "principale",
    anno_riferimento_eco: int = 2025,

    # Bonus Ristrutturazione
    tipo_immobile_br: Literal["principale", "altro"] = "principale",
    anno_riferimento_br: int = 2025,

    # Tasso sconto per NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Confronta l'incentivo CT 3.0 con Ecobonus e Bonus Ristrutturazione

    NOTA IMPORTANTE: Per Building Automation, Ecobonus ha un limite SPECIALE di 15.000€
    (diverso dal limite standard di 60.000€)

    Returns:
        Dict con chiavi:
        - ct_3_0: Dict (risultato calcolo CT 3.0)
        - ecobonus: Dict (risultato calcolo Ecobonus)
        - bonus_ristrutturazione: Dict (risultato calcolo Bonus Ristrutturazione)
        - migliore_opzione: str
        - differenza_rispetto_migliore: Dict
    """

    # 1. Calcola CT 3.0
    ct_result = calculate_building_automation_incentive(
        superficie_utile_mq=superficie_utile_mq,
        spesa_sostenuta=spesa_sostenuta,
        tipo_soggetto=tipo_soggetto_ct,
        tipo_edificio=tipo_edificio_ct,
        usa_premialita_componenti_ue=usa_premialita_componenti_ue,
        tasso_sconto=tasso_sconto
    )

    # 2. Calcola Ecobonus
    # ATTENZIONE: Limite SPECIALE di 15.000€ per Building Automation
    aliquote_eco = {
        2024: {"principale": 0.50, "altro": 0.36},
        2025: {"principale": 0.50, "altro": 0.36},
        2026: {"principale": 0.36, "altro": 0.30},
        2027: {"principale": 0.36, "altro": 0.30}
    }

    aliquota_eco = aliquote_eco.get(anno_riferimento_eco, {}).get(tipo_immobile_eco, 0.36)
    limite_eco = 15000.0  # LIMITE SPECIALE per Building Automation (non 60.000€!)
    anni_eco = 10

    spesa_ammissibile_eco = min(spesa_sostenuta, limite_eco)
    detrazione_totale_eco = aliquota_eco * spesa_ammissibile_eco
    rata_annuale_eco = detrazione_totale_eco / anni_eco

    # NPV Ecobonus
    npv_eco = sum(rata_annuale_eco / ((1 + tasso_sconto) ** anno) for anno in range(1, anni_eco + 1))

    eco_result = {
        "detrazione_totale": round(detrazione_totale_eco, 2),
        "spesa_ammissibile": round(spesa_ammissibile_eco, 2),
        "anni_erogazione": anni_eco,
        "rata_annuale": round(rata_annuale_eco, 2),
        "npv": round(npv_eco, 2),
        "dettagli": {
            "aliquota": aliquota_eco,
            "tipo_immobile": tipo_immobile_eco,
            "anno_riferimento": anno_riferimento_eco,
            "limite_max": limite_eco,
            "nota_speciale": "Limite SPECIALE di 15.000€ per Building Automation",
            "tasso_sconto_npv": tasso_sconto
        }
    }

    # 3. Calcola Bonus Ristrutturazione
    aliquote_br = {
        2024: {"principale": 0.50, "altro": 0.36},
        2025: {"principale": 0.50, "altro": 0.36},
        2026: {"principale": 0.36, "altro": 0.30},
        2027: {"principale": 0.36, "altro": 0.30}
    }

    aliquota_br = aliquote_br.get(anno_riferimento_br, {}).get(tipo_immobile_br, 0.36)
    limite_br = 96000.0  # Limite standard
    anni_br = 10

    spesa_ammissibile_br = min(spesa_sostenuta, limite_br)
    detrazione_totale_br = aliquota_br * spesa_ammissibile_br
    rata_annuale_br = detrazione_totale_br / anni_br

    # NPV Bonus Ristrutturazione
    npv_br = sum(rata_annuale_br / ((1 + tasso_sconto) ** anno) for anno in range(1, anni_br + 1))

    br_result = {
        "detrazione_totale": round(detrazione_totale_br, 2),
        "spesa_ammissibile": round(spesa_ammissibile_br, 2),
        "anni_erogazione": anni_br,
        "rata_annuale": round(rata_annuale_br, 2),
        "npv": round(npv_br, 2),
        "dettagli": {
            "aliquota": aliquota_br,
            "tipo_immobile": tipo_immobile_br,
            "anno_riferimento": anno_riferimento_br,
            "limite_max": limite_br,
            "tasso_sconto_npv": tasso_sconto
        }
    }

    # 4. Determina la migliore opzione (basata su NPV)
    opzioni = {
        "CT 3.0": ct_result["npv"],
        "Ecobonus": eco_result["npv"],
        "Bonus Ristrutturazione": br_result["npv"]
    }

    migliore_opzione = max(opzioni, key=opzioni.get)
    npv_migliore = opzioni[migliore_opzione]

    # 5. Calcola differenze
    differenze = {
        nome: round(npv_migliore - npv, 2)
        for nome, npv in opzioni.items()
    }

    return {
        "ct_3_0": ct_result,
        "ecobonus": eco_result,
        "bonus_ristrutturazione": br_result,
        "migliore_opzione": migliore_opzione,
        "differenza_rispetto_migliore": differenze,
        "confronto_npv": {
            nome: round(npv, 2)
            for nome, npv in opzioni.items()
        }
    }


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST CALCOLO INCENTIVO BUILDING AUTOMATION")
    print("=" * 80)

    # Test 1: CT 3.0 base - privato
    print("\n[TEST 1] CT 3.0 - Privato, sistema Classe B")
    result1 = calculate_building_automation_incentive(
        superficie_utile_mq=300.0,
        spesa_sostenuta=15000.0,  # 50 €/m²
        tipo_soggetto="privato",
        tipo_edificio="residenziale",
        usa_premialita_componenti_ue=False
    )
    print(f"Incentivo totale: {result1['incentivo_totale']:.2f} €")
    print(f"NPV: {result1['npv']:.2f} €")
    print(f"Erogazione: {result1['anni_erogazione']} anni × {result1['rata_annuale']:.2f} €/anno")
    print(f"Percentuale: {result1['dettagli']['percentuale']:.0%}")

    # Test 2: CT 3.0 - PA edifici pubblici
    print("\n[TEST 2] CT 3.0 - PA edifici pubblici, sistema Classe A")
    result2 = calculate_building_automation_incentive(
        superficie_utile_mq=500.0,
        spesa_sostenuta=28000.0,  # 56 €/m²
        tipo_soggetto="pa",
        tipo_edificio="pubblico",
        usa_premialita_componenti_ue=True
    )
    print(f"Incentivo totale: {result2['incentivo_totale']:.2f} €")
    print(f"NPV: {result2['npv']:.2f} €")
    print(f"Erogazione: {result2['anni_erogazione']} anni × {result2['rata_annuale']:.2f} €/anno")
    print(f"Percentuale: {result2['dettagli']['percentuale']:.0%}")

    # Test 3: Confronto 3 vie
    print("\n[TEST 3] Confronto CT 3.0 vs Ecobonus vs Bonus Ristrutturazione")
    result3 = confronta_incentivi_building_automation(
        superficie_utile_mq=200.0,
        spesa_sostenuta=10000.0,  # 50 €/m²
        tipo_soggetto_ct="privato",
        tipo_edificio_ct="residenziale",
        usa_premialita_componenti_ue=False,
        tipo_immobile_eco="principale",
        anno_riferimento_eco=2025,
        tipo_immobile_br="principale",
        anno_riferimento_br=2025
    )

    print(f"\nCT 3.0:")
    print(f"  Incentivo: {result3['ct_3_0']['incentivo_totale']:.2f} €")
    print(f"  NPV: {result3['ct_3_0']['npv']:.2f} €")
    print(f"  Anni: {result3['ct_3_0']['anni_erogazione']}")

    print(f"\nEcobonus:")
    print(f"  Detrazione: {result3['ecobonus']['detrazione_totale']:.2f} €")
    print(f"  NPV: {result3['ecobonus']['npv']:.2f} €")
    print(f"  Anni: {result3['ecobonus']['anni_erogazione']}")
    print(f"  Limite: {result3['ecobonus']['dettagli']['limite_max']:.0f} € (SPECIALE per BA)")

    print(f"\nBonus Ristrutturazione:")
    print(f"  Detrazione: {result3['bonus_ristrutturazione']['detrazione_totale']:.2f} €")
    print(f"  NPV: {result3['bonus_ristrutturazione']['npv']:.2f} €")
    print(f"  Anni: {result3['bonus_ristrutturazione']['anni_erogazione']}")

    print(f"\nMIGLIORE OPZIONE: {result3['migliore_opzione']}")
    print(f"NPV: {result3['confronto_npv'][result3['migliore_opzione']]:.2f} €")

    # Test 4: Spesa elevata - verifica limiti
    print("\n[TEST 4] Spesa elevata - verifica limiti speciali Ecobonus")
    result4 = confronta_incentivi_building_automation(
        superficie_utile_mq=500.0,
        spesa_sostenuta=30000.0,  # Spesa alta
        tipo_soggetto_ct="privato",
        tipo_edificio_ct="residenziale",
        usa_premialita_componenti_ue=False,
        tipo_immobile_eco="principale",
        anno_riferimento_eco=2025,
        tipo_immobile_br="principale",
        anno_riferimento_br=2025
    )

    print(f"\nCT 3.0:")
    print(f"  Spesa ammissibile: {result4['ct_3_0']['spesa_ammissibile']:.2f} €")
    print(f"  Incentivo: {result4['ct_3_0']['incentivo_totale']:.2f} €")
    print(f"  NPV: {result4['ct_3_0']['npv']:.2f} €")

    print(f"\nEcobonus:")
    print(f"  Spesa ammissibile: {result4['ecobonus']['spesa_ammissibile']:.2f} € (limite {result4['ecobonus']['dettagli']['limite_max']:.0f} €)")
    print(f"  Detrazione: {result4['ecobonus']['detrazione_totale']:.2f} €")
    print(f"  NPV: {result4['ecobonus']['npv']:.2f} €")

    print(f"\nBonus Ristrutturazione:")
    print(f"  Spesa ammissibile: {result4['bonus_ristrutturazione']['spesa_ammissibile']:.2f} €")
    print(f"  Detrazione: {result4['bonus_ristrutturazione']['detrazione_totale']:.2f} €")
    print(f"  NPV: {result4['bonus_ristrutturazione']['npv']:.2f} €")

    print(f"\nMIGLIORE OPZIONE: {result4['migliore_opzione']}")

    print("\n" + "=" * 80)
