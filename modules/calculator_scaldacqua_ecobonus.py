"""
Modulo per il calcolo della detrazione Ecobonus per scaldacqua a pompa di calore

Riferimento: D.L. 63/2013 - Ecobonus
Aliquote 2025: 50% (abitazione principale), 36% (altre abitazioni)
Limite: 30.000 € di detrazione
Recupero: 10 anni
"""

from typing import Dict


def calculate_scaldacqua_ecobonus_incentive(
    spesa_sostenuta: float = 0.0,

    # Aliquota in base a prima casa o no
    abitazione_principale: bool = True,  # True = 50%, False = 36%

    # Anno intervento (per aliquote variabili)
    anno_intervento: int = 2025,

    # Spesa per comunicazione ENEA / asseverazione
    spesa_tecnici: float = 0.0,

    # Tasso sconto per NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Calcola la detrazione Ecobonus per scaldacqua a pompa di calore

    Args:
        spesa_sostenuta: Spesa totale sostenuta (€)
        abitazione_principale: Se True, aliquota 50%, altrimenti 36%
        anno_intervento: Anno di realizzazione intervento
        spesa_tecnici: Spese tecniche (asseverazione, comunicazione ENEA)

    Returns:
        Dict con:
        - detrazione_totale: Detrazione totale fiscale (€)
        - detrazione_annuale: Detrazione annuale per 10 anni (€)
        - spesa_ammissibile: Spesa effettivamente ammissibile (€)
        - aliquota_applicata: Aliquota applicata (50% o 36%)
        - anni_recupero: Anni di recupero (sempre 10)
        - npv: Net Present Value con tasso 3% (€)
        - spesa_netta: Spesa netta dopo detrazione (€)
        - dettagli: Informazioni aggiuntive
    """

    # Limite massimo di DETRAZIONE (non di spesa)
    LIMITE_DETRAZIONE_MAX = 30000.0

    # Determina aliquota in base ad abitazione principale e anno
    if anno_intervento >= 2025:
        if abitazione_principale:
            aliquota = 0.50  # 50% per abitazione principale
        else:
            aliquota = 0.36  # 36% per altre abitazioni
    else:  # 2024 e precedenti
        aliquota = 0.65  # 65% per tutti

    # Spesa totale ammissibile (spesa lavori + spese tecniche)
    spesa_totale_ammissibile = spesa_sostenuta + spesa_tecnici

    # Calcola detrazione base
    detrazione_base = aliquota * spesa_totale_ammissibile

    # Applica limite massimo di detrazione
    detrazione_totale = min(detrazione_base, LIMITE_DETRAZIONE_MAX)

    # Anni di recupero sempre 10
    anni_recupero = 10
    detrazione_annuale = detrazione_totale / anni_recupero

    # Calcola NPV (Net Present Value)
    npv = sum(
        detrazione_annuale / ((1 + tasso_sconto) ** anno)
        for anno in range(1, anni_recupero + 1)
    )

    # Spesa netta sostenuta (spesa totale - detrazione)
    spesa_netta = spesa_totale_ammissibile - detrazione_totale

    # Dettagli calcolo
    dettagli = {
        "aliquota_percentuale": f"{aliquota * 100:.0f}%",
        "abitazione_principale": abitazione_principale,
        "anno_intervento": anno_intervento,
        "spesa_lavori": spesa_sostenuta,
        "spesa_tecnici": spesa_tecnici,
        "detrazione_calcolata": detrazione_base,
        "limite_detrazione": LIMITE_DETRAZIONE_MAX,
        "applicato_limite": detrazione_base > LIMITE_DETRAZIONE_MAX,
        "modalita_recupero": f"{anni_recupero} rate annuali costanti",
        "percentuale_risparmio": (detrazione_totale / spesa_totale_ammissibile * 100) if spesa_totale_ammissibile > 0 else 0
    }

    return {
        "detrazione_totale": round(detrazione_totale, 2),
        "detrazione_annuale": round(detrazione_annuale, 2),
        "spesa_ammissibile": round(spesa_totale_ammissibile, 2),
        "aliquota_applicata": aliquota,
        "anni_recupero": anni_recupero,
        "npv": round(npv, 2),
        "spesa_netta": round(spesa_netta, 2),
        "dettagli": dettagli
    }


def confronta_ct_ecobonus(
    risultato_ct: Dict,
    risultato_ecobonus: Dict,
    spesa_sostenuta: float
) -> Dict:
    """
    Confronta i due incentivi e determina il più conveniente

    Args:
        risultato_ct: Risultato del calcolo Conto Termico
        risultato_ecobonus: Risultato del calcolo Ecobonus
        spesa_sostenuta: Spesa sostenuta per l'intervento

    Returns:
        Dict con:
        - piu_conveniente: "CT" o "Ecobonus"
        - differenza_npv: Differenza di NPV (€)
        - vantaggio_percentuale: Vantaggio percentuale (%)
        - dettagli_confronto: Dettagli del confronto
    """

    npv_ct = risultato_ct["npv"]
    npv_ecobonus = risultato_ecobonus["npv"]

    # Confronto NPV (più alto è meglio)
    if npv_ct > npv_ecobonus:
        piu_conveniente = "CT"
        differenza_npv = npv_ct - npv_ecobonus
        vantaggio_percentuale = (differenza_npv / npv_ecobonus * 100) if npv_ecobonus > 0 else 0
    else:
        piu_conveniente = "Ecobonus"
        differenza_npv = npv_ecobonus - npv_ct
        vantaggio_percentuale = (differenza_npv / npv_ct * 100) if npv_ct > 0 else 0

    # Calcola spesa netta per entrambi
    spesa_netta_ct = spesa_sostenuta - risultato_ct["incentivo_totale"]
    spesa_netta_ecobonus = risultato_ecobonus["spesa_netta"]

    dettagli_confronto = {
        "incentivo_ct": risultato_ct["incentivo_totale"],
        "incentivo_ecobonus": risultato_ecobonus["detrazione_totale"],
        "npv_ct": npv_ct,
        "npv_ecobonus": npv_ecobonus,
        "anni_erogazione_ct": risultato_ct["anni_erogazione"],
        "anni_erogazione_ecobonus": risultato_ecobonus["anni_recupero"],
        "spesa_netta_ct": spesa_netta_ct,
        "spesa_netta_ecobonus": spesa_netta_ecobonus,
        "differenza_spesa_netta": abs(spesa_netta_ct - spesa_netta_ecobonus),
        "tempo_recupero_ct": f"{risultato_ct['anni_erogazione']} anni",
        "tempo_recupero_ecobonus": f"{risultato_ecobonus['anni_recupero']} anni"
    }

    return {
        "piu_conveniente": piu_conveniente,
        "differenza_npv": round(abs(differenza_npv), 2),
        "vantaggio_percentuale": round(vantaggio_percentuale, 2),
        "dettagli_confronto": dettagli_confronto
    }


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST CALCOLO ECOBONUS - SCALDACQUA PDC")
    print("=" * 80)

    # Test 1: Abitazione principale 2025, spesa 2.500 €
    print("\n[TEST 1] Abitazione principale, spesa 2.500 €, anno 2025")
    result1 = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=2500.0,
        abitazione_principale=True,
        anno_intervento=2025
    )
    print(f"Detrazione totale: € {result1['detrazione_totale']:,.2f}")
    print(f"Aliquota: {result1['aliquota_applicata'] * 100:.0f}%")
    print(f"Detrazione annuale (10 anni): € {result1['detrazione_annuale']:,.2f}")
    print(f"NPV: € {result1['npv']:,.2f}")
    print(f"Spesa netta: € {result1['spesa_netta']:,.2f}")

    # Test 2: Altra abitazione 2025, spesa 3.500 €
    print("\n[TEST 2] Altra abitazione (36%), spesa 3.500 €, anno 2025")
    result2 = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=3500.0,
        abitazione_principale=False,
        anno_intervento=2025
    )
    print(f"Detrazione totale: € {result2['detrazione_totale']:,.2f}")
    print(f"Aliquota: {result2['aliquota_applicata'] * 100:.0f}%")
    print(f"Detrazione annuale: € {result2['detrazione_annuale']:,.2f}")
    print(f"NPV: € {result2['npv']:,.2f}")

    # Test 3: Anno 2024 (aliquota 65%)
    print("\n[TEST 3] Anno 2024 (65%), spesa 3.000 €")
    result3 = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=3000.0,
        abitazione_principale=True,
        anno_intervento=2024
    )
    print(f"Detrazione totale: € {result3['detrazione_totale']:,.2f}")
    print(f"Aliquota: {result3['aliquota_applicata'] * 100:.0f}%")
    print(f"Detrazione annuale: € {result3['detrazione_annuale']:,.2f}")

    # Test 4: Con spese tecniche
    print("\n[TEST 4] Abitazione principale, spesa 2.800 € + 200 € tecnici")
    result4 = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=2800.0,
        abitazione_principale=True,
        anno_intervento=2025,
        spesa_tecnici=200.0
    )
    print(f"Spesa ammissibile totale: € {result4['spesa_ammissibile']:,.2f}")
    print(f"Detrazione totale: € {result4['detrazione_totale']:,.2f}")
    print(f"Detrazione annuale: € {result4['detrazione_annuale']:,.2f}")

    # Test 5: Spesa molto alta (supera limite detrazione)
    print("\n[TEST 5] Spesa 100.000 € (supera limite 30.000 € detrazione)")
    result5 = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=100000.0,
        abitazione_principale=True,
        anno_intervento=2025
    )
    print(f"Detrazione calcolata (50%): € {result5['dettagli']['detrazione_calcolata']:,.2f}")
    print(f"Detrazione effettiva (limite): € {result5['detrazione_totale']:,.2f}")
    print(f"Applicato limite: {result5['dettagli']['applicato_limite']}")
    print(f"Differenza perduta: € {result5['dettagli']['detrazione_calcolata'] - result5['detrazione_totale']:,.2f}")

    # Test 6: Confronto CT vs Ecobonus
    print("\n[TEST 6] Confronto CT vs Ecobonus - Classe A, 200 litri, spesa 2.500 €")
    from calculator_scaldacqua_ct import calculate_scaldacqua_ct_incentive

    result_ct = calculate_scaldacqua_ct_incentive(
        classe_energetica="A",
        capacita_accumulo_litri=200,
        spesa_sostenuta=2500.0
    )

    result_eco = calculate_scaldacqua_ecobonus_incentive(
        spesa_sostenuta=2500.0,
        abitazione_principale=True,
        anno_intervento=2025
    )

    confronto = confronta_ct_ecobonus(result_ct, result_eco, 2500.0)

    print(f"\nCONFRONTO:")
    print(f"  CT 3.0:   Incentivo € {result_ct['incentivo_totale']:,.2f}, NPV € {result_ct['npv']:,.2f}, Erogazione {result_ct['anni_erogazione']} anni")
    print(f"  Ecobonus: Detrazione € {result_eco['detrazione_totale']:,.2f}, NPV € {result_eco['npv']:,.2f}, Recupero {result_eco['anni_recupero']} anni")
    print(f"\n  PIÙ CONVENIENTE: {confronto['piu_conveniente']}")
    print(f"  Differenza NPV: € {confronto['differenza_npv']:,.2f}")
    print(f"  Vantaggio: {confronto['vantaggio_percentuale']:.1f}%")

    print("\n" + "=" * 80)
