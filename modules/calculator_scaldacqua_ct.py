"""
Modulo per il calcolo dell'incentivo Conto Termico 3.0 per l'intervento III.E
Sostituzione di scaldacqua elettrici e a gas con scaldacqua a pompa di calore

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.13.3
Formula: I = 40% × C (con limite massimo da Tabella 38)
"""

from typing import Dict


# Tabella 38 - Scaldacqua a pompa di calore: incentivo massimo
# Reg. UE 812/2013
INCENTIVI_MASSIMI_SCALDACQUA = {
    "A": {
        "<=150": 500.0,    # V ≤ 150 litri
        ">150": 1100.0     # V > 150 litri
    },
    "A+": {
        "<=150": 700.0,    # V ≤ 150 litri
        ">150": 1500.0     # V > 150 litri
    },
    # Classi superiori (non in tabella ufficiale, uso stesso limite di A+)
    "A++": {
        "<=150": 700.0,
        ">150": 1500.0
    },
    "A+++": {
        "<=150": 700.0,
        ">150": 1500.0
    }
}


def calculate_scaldacqua_ct_incentive(
    classe_energetica: str = "A",  # "A", "A+", "A++", "A+++"
    capacita_accumulo_litri: int = 200,
    spesa_sostenuta: float = 0.0,

    # Tipologia soggetto (per PA su edifici pubblici)
    tipo_soggetto: str = "privato",  # "privato", "pa", "impresa", "ets_economico"
    tipo_edificio: str = "residenziale",  # "residenziale", "pubblico", "terziario"

    # Tasso sconto per NPV
    tasso_sconto: float = 0.03
) -> Dict:
    """
    Calcola l'incentivo Conto Termico 3.0 per scaldacqua a pompa di calore

    Args:
        classe_energetica: Classe energetica secondo Reg. UE 812/2013
        capacita_accumulo_litri: Capacità accumulo in litri
        spesa_sostenuta: Spesa totale sostenuta (€)
        tipo_soggetto: Tipologia soggetto richiedente
        tipo_edificio: Tipologia edificio

    Returns:
        Dict con:
        - incentivo_totale: Incentivo totale CT 3.0 (€)
        - spesa_ammissibile: Spesa effettivamente ammissibile (€)
        - incentivo_max_tabella: Limite massimo da Tabella 38 (€)
        - percentuale_applicata: Percentuale applicata (40% o 100%)
        - anni_erogazione: Anni di erogazione (1 o 2)
        - rata_annuale: Importo rata annuale (€)
        - npv: Net Present Value con tasso 3% (€)
        - dettagli: Informazioni aggiuntive
    """

    # Determina percentuale in base a soggetto e tipo edificio
    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        percentuale = 1.00  # 100% per PA su edifici pubblici
    else:
        percentuale = 0.40  # 40% per tutti gli altri

    # Determina incentivo massimo da Tabella 38
    classe_valida = classe_energetica if classe_energetica in INCENTIVI_MASSIMI_SCALDACQUA else "A"
    capacita_key = "<=150" if capacita_accumulo_litri <= 150 else ">150"
    incentivo_max = INCENTIVI_MASSIMI_SCALDACQUA[classe_valida][capacita_key]

    # Calcola incentivo base (percentuale × spesa)
    incentivo_base = percentuale * spesa_sostenuta

    # Applica limite massimo
    incentivo_totale = min(incentivo_base, incentivo_max)

    # Determina anni erogazione
    # Sempre 2 rate annuali, oppure unica soluzione se ≤ 15.000 €
    if incentivo_totale <= 15000.0:
        anni_erogazione = 1
        rata_annuale = incentivo_totale
    else:
        anni_erogazione = 2
        rata_annuale = incentivo_totale / 2

    # Calcola NPV (Net Present Value)
    if anni_erogazione == 1:
        npv = incentivo_totale
    else:
        npv = sum(
            rata_annuale / ((1 + tasso_sconto) ** anno)
            for anno in range(1, anni_erogazione + 1)
        )

    # Dettagli calcolo
    dettagli = {
        "classe_energetica": classe_energetica,
        "capacita_litri": capacita_accumulo_litri,
        "capacita_categoria": f"{'≤' if capacita_accumulo_litri <= 150 else '>'} 150 litri",
        "percentuale_incentivo": f"{percentuale * 100:.0f}%",
        "incentivo_calcolato": incentivo_base,
        "incentivo_max_tabella": incentivo_max,
        "applicato_limite": incentivo_base > incentivo_max,
        "modalita_erogazione": "Rata unica" if anni_erogazione == 1 else f"{anni_erogazione} rate annuali",
        "tipo_soggetto": tipo_soggetto,
        "nota_pa": "Incentivo al 100%" if tipo_soggetto == "pa" and tipo_edificio == "pubblico" else None
    }

    return {
        "incentivo_totale": round(incentivo_totale, 2),
        "spesa_ammissibile": round(spesa_sostenuta, 2),
        "incentivo_max_tabella": incentivo_max,
        "percentuale_applicata": percentuale,
        "anni_erogazione": anni_erogazione,
        "rata_annuale": round(rata_annuale, 2),
        "npv": round(npv, 2),
        "dettagli": dettagli
    }


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST CALCOLO INCENTIVO CONTO TERMICO 3.0 - SCALDACQUA PDC")
    print("=" * 80)

    # Test 1: Classe A, accumulo piccolo (≤ 150 litri)
    print("\n[TEST 1] Classe A, 120 litri, spesa 2.000 €")
    result1 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A",
        capacita_accumulo_litri=120,
        spesa_sostenuta=2000.0
    )
    print(f"Incentivo totale: € {result1['incentivo_totale']:,.2f}")
    print(f"Incentivo max tabella: € {result1['incentivo_max_tabella']:,.0f}")
    print(f"Percentuale: {result1['percentuale_applicata'] * 100:.0f}%")
    print(f"Anni erogazione: {result1['anni_erogazione']}")
    print(f"NPV: € {result1['npv']:,.2f}")
    print(f"Applicato limite: {result1['dettagli']['applicato_limite']}")

    # Test 2: Classe A, accumulo grande (> 150 litri)
    print("\n[TEST 2] Classe A, 250 litri, spesa 3.500 €")
    result2 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A",
        capacita_accumulo_litri=250,
        spesa_sostenuta=3500.0
    )
    print(f"Incentivo totale: € {result2['incentivo_totale']:,.2f}")
    print(f"Incentivo max tabella: € {result2['incentivo_max_tabella']:,.0f}")
    print(f"Incentivo calcolato (40%): € {result2['dettagli']['incentivo_calcolato']:,.2f}")
    print(f"Applicato limite: {result2['dettagli']['applicato_limite']}")
    print(f"Rata annuale: € {result2['rata_annuale']:,.2f}")

    # Test 3: Classe A+, accumulo piccolo
    print("\n[TEST 3] Classe A+, 140 litri, spesa 2.800 €")
    result3 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A+",
        capacita_accumulo_litri=140,
        spesa_sostenuta=2800.0
    )
    print(f"Incentivo totale: € {result3['incentivo_totale']:,.2f}")
    print(f"Incentivo max tabella: € {result3['incentivo_max_tabella']:,.0f}")
    print(f"Incentivo calcolato (40%): € {result3['dettagli']['incentivo_calcolato']:,.2f}")
    print(f"Applicato limite: {result3['dettagli']['applicato_limite']}")

    # Test 4: Classe A+, accumulo grande
    print("\n[TEST 4] Classe A+, 300 litri, spesa 4.500 €")
    result4 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A+",
        capacita_accumulo_litri=300,
        spesa_sostenuta=4500.0
    )
    print(f"Incentivo totale: € {result4['incentivo_totale']:,.2f}")
    print(f"Incentivo max tabella: € {result4['incentivo_max_tabella']:,.0f}")
    print(f"Incentivo calcolato (40%): € {result4['dettagli']['incentivo_calcolato']:,.2f}")
    print(f"Applicato limite: {result4['dettagli']['applicato_limite']}")

    # Test 5: PA su edificio pubblico (100%)
    print("\n[TEST 5] PA su edificio pubblico, Classe A, 200 litri, spesa 2.500 €")
    result5 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A",
        capacita_accumulo_litri=200,
        spesa_sostenuta=2500.0,
        tipo_soggetto="pa",
        tipo_edificio="pubblico"
    )
    print(f"Incentivo totale: € {result5['incentivo_totale']:,.2f}")
    print(f"Percentuale: {result5['percentuale_applicata'] * 100:.0f}%")
    print(f"Incentivo calcolato (100%): € {result5['dettagli']['incentivo_calcolato']:,.2f}")
    print(f"Incentivo max tabella: € {result5['incentivo_max_tabella']:,.0f}")
    print(f"Applicato limite: {result5['dettagli']['applicato_limite']}")
    print(f"Nota: {result5['dettagli']['nota_pa']}")

    # Test 6: Spesa molto alta che supera limite
    print("\n[TEST 6] Classe A+, 250 litri, spesa 8.000 € (supera limite)")
    result6 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A+",
        capacita_accumulo_litri=250,
        spesa_sostenuta=8000.0
    )
    print(f"Incentivo totale: € {result6['incentivo_totale']:,.2f}")
    print(f"Incentivo calcolato (40%): € {result6['dettagli']['incentivo_calcolato']:,.2f}")
    print(f"Incentivo max tabella: € {result6['incentivo_max_tabella']:,.0f}")
    print(f"Applicato limite: {result6['dettagli']['applicato_limite']}")
    print(f"Differenza perduta: € {result6['dettagli']['incentivo_calcolato'] - result6['incentivo_totale']:,.2f}")

    # Test 7: Classe A++
    print("\n[TEST 7] Classe A++, 200 litri, spesa 5.000 €")
    result7 = calculate_scaldacqua_ct_incentive(
        classe_energetica="A++",
        capacita_accumulo_litri=200,
        spesa_sostenuta=5000.0
    )
    print(f"Incentivo totale: € {result7['incentivo_totale']:,.2f}")
    print(f"Incentivo max tabella: € {result7['incentivo_max_tabella']:,.0f}")

    print("\n" + "=" * 80)
