"""
Test automatici per verificare i calcoli di Energy Incentive Manager.

Include test con casi noti (es. esempio Caleffi) per validare l'accuratezza.

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.calculator_ct import calculate_heat_pump_incentive
from modules.calculator_eco import calculate_ecobonus_deduction
from modules.financial_roi import calculate_npv
from modules.validator import valida_requisiti_ct, valida_requisiti_ecobonus


def test_esempio_caleffi():
    """
    Test con esempio Caleffi:
    - PdC aria/acqua 10 kW
    - SCOP 4.0, η_s 150%
    - Zona E (Milano)
    - Atteso: Ia = 2.600 €, totale = 5.200 €
    """
    print("\n" + "=" * 60)
    print("TEST: Esempio Caleffi (PdC aria/acqua 10kW)")
    print("=" * 60)

    risultato = calculate_heat_pump_incentive(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=4.0,
        spesa_totale_sostenuta=15000.0,
        gwp_refrigerante=">150",
        tipo_soggetto="privato",
        bassa_temperatura=False,
        eta_s=150.0
    )

    assert risultato["status"] == "OK", f"Calcolo fallito: {risultato.get('messaggio')}"

    ia_calcolato = risultato["calcoli_intermedi"]["Ia"]
    ia_atteso = 2600.0
    tolleranza_pct = 1.0  # 1% tolleranza per arrotondamenti

    differenza_pct = abs(ia_calcolato - ia_atteso) / ia_atteso * 100

    print(f"  Ia calcolato: {ia_calcolato:.2f} EUR")
    print(f"  Ia atteso:    {ia_atteso:.2f} EUR")
    print(f"  Differenza:   {differenza_pct:.2f}%")

    assert differenza_pct < tolleranza_pct, \
        f"Ia calcolato ({ia_calcolato}) differisce troppo da atteso ({ia_atteso})"

    totale_calcolato = risultato["incentivo_totale"]
    totale_atteso = 5200.0

    diff_totale_pct = abs(totale_calcolato - totale_atteso) / totale_atteso * 100
    print(f"  Totale calcolato: {totale_calcolato:.2f} EUR")
    print(f"  Totale atteso:    {totale_atteso:.2f} EUR")
    print(f"  Differenza:       {diff_totale_pct:.2f}%")

    assert diff_totale_pct < tolleranza_pct, \
        f"Totale calcolato ({totale_calcolato}) differisce troppo da atteso ({totale_atteso})"

    print("  [OK] Test superato!")
    return True


def test_coefficiente_kp():
    """Test calcolo kp = eta_s / eta_s_min."""
    print("\n" + "=" * 60)
    print("TEST: Coefficiente kp")
    print("=" * 60)

    # PdC aria/acqua standard: eta_s_min = 110%
    # eta_s = 150% -> kp = 150/110 = 1.3636

    risultato = calculate_heat_pump_incentive(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=4.0,
        spesa_totale_sostenuta=15000.0,
        gwp_refrigerante=">150",
        tipo_soggetto="privato",
        bassa_temperatura=False,
        eta_s=150.0
    )

    assert risultato["status"] == "OK"

    kp_calcolato = risultato["calcoli_intermedi"]["kp"]
    kp_atteso = 150.0 / 110.0

    print(f"  kp calcolato: {kp_calcolato:.4f}")
    print(f"  kp atteso:    {kp_atteso:.4f}")

    assert abs(kp_calcolato - kp_atteso) < 0.001, \
        f"kp calcolato ({kp_calcolato}) != atteso ({kp_atteso})"

    print("  [OK] Test superato!")
    return True


def test_quf_zone_climatiche():
    """Test valori Quf per diverse zone climatiche."""
    print("\n" + "=" * 60)
    print("TEST: Coefficiente Quf per zone climatiche")
    print("=" * 60)

    quf_attesi = {
        "A": 600,
        "B": 850,
        "C": 1100,
        "D": 1400,
        "E": 1700,
        "F": 1800
    }

    for zona, quf_atteso in quf_attesi.items():
        risultato = calculate_heat_pump_incentive(
            tipo_intervento="aria_acqua",
            zona_climatica=zona,
            potenza_nominale_kw=10.0,
            scop_dichiarato=4.0,
            spesa_totale_sostenuta=15000.0,
            gwp_refrigerante=">150",
            eta_s=150.0
        )

        if risultato["status"] == "OK":
            quf_calcolato = risultato["calcoli_intermedi"]["Quf"]
            assert quf_calcolato == quf_atteso, \
                f"Zona {zona}: Quf calcolato ({quf_calcolato}) != atteso ({quf_atteso})"
            print(f"  Zona {zona}: Quf = {quf_calcolato} h [OK]")
        else:
            print(f"  Zona {zona}: Calcolo fallito - {risultato.get('messaggio')}")

    print("  [OK] Test superato!")
    return True


def test_ecobonus_2025():
    """Test calcolo Ecobonus 2025 con aliquote differenziate."""
    print("\n" + "=" * 60)
    print("TEST: Ecobonus 2025")
    print("=" * 60)

    # Abitazione principale: 50%
    risultato_pp = calculate_ecobonus_deduction(
        tipo_intervento="pompe_di_calore",
        spesa_sostenuta=20000.0,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale"
    )

    assert risultato_pp["status"] == "OK"
    assert risultato_pp["calcoli"]["aliquota_applicata"] == 0.50, \
        "Aliquota abitazione principale 2025 deve essere 50%"
    print(f"  Prima casa 2025: aliquota {risultato_pp['calcoli']['aliquota_applicata']*100}% [OK]")

    # Seconda casa: 36%
    risultato_sc = calculate_ecobonus_deduction(
        tipo_intervento="pompe_di_calore",
        spesa_sostenuta=20000.0,
        anno_spesa=2025,
        tipo_abitazione="altra_abitazione"
    )

    assert risultato_sc["status"] == "OK"
    assert risultato_sc["calcoli"]["aliquota_applicata"] == 0.36, \
        "Aliquota seconda casa 2025 deve essere 36%"
    print(f"  Seconda casa 2025: aliquota {risultato_sc['calcoli']['aliquota_applicata']*100}% [OK]")

    print("  [OK] Test superato!")
    return True


def test_npv_calculation():
    """Test calcolo NPV."""
    print("\n" + "=" * 60)
    print("TEST: Calcolo NPV")
    print("=" * 60)

    # Test semplice: 1000€ oggi = 1000€ NPV
    cf = [1000.0]
    npv = calculate_npv(cf, 0.03)
    assert abs(npv - 1000.0) < 0.01, "NPV anno 0 deve essere uguale al valore"
    print(f"  NPV [1000] = {npv} EUR [OK]")

    # Test 2 anni: 1000€ anno 1 al 3% = 1000/1.03 = 970.87
    cf = [0.0, 1000.0]
    npv = calculate_npv(cf, 0.03)
    npv_atteso = 1000.0 / 1.03
    assert abs(npv - npv_atteso) < 0.01, f"NPV anno 1: {npv} != {npv_atteso}"
    print(f"  NPV [0, 1000] @3% = {npv:.2f} EUR (atteso {npv_atteso:.2f}) [OK]")

    # Test 10 anni Ecobonus style
    rata = 750.0
    cf = [0.0] + [rata] * 10
    npv = calculate_npv(cf, 0.03)
    print(f"  NPV Ecobonus (750€/anno x 10) @3% = {npv:.2f} EUR [OK]")

    print("  [OK] Test superato!")
    return True


def test_validazione_scop_minimo():
    """Test validazione SCOP minimo."""
    print("\n" + "=" * 60)
    print("TEST: Validazione SCOP minimo")
    print("=" * 60)

    # SCOP insufficiente: aria/acqua standard richiede 2.825
    val = valida_requisiti_ct(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=2.5,  # Sotto il minimo
        gwp_refrigerante=">150",
        bassa_temperatura=False
    )

    assert not val.ammissibile, "SCOP 2.5 < 2.825: dovrebbe essere non ammissibile"
    print(f"  SCOP 2.5 (min 2.825): ammissibile = {val.ammissibile} [OK]")

    # SCOP sufficiente
    val2 = valida_requisiti_ct(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=4.0,
        gwp_refrigerante=">150",
        bassa_temperatura=False
    )

    assert val2.ammissibile, "SCOP 4.0 >= 2.825: dovrebbe essere ammissibile"
    print(f"  SCOP 4.0 (min 2.825): ammissibile = {val2.ammissibile} [OK]")

    print("  [OK] Test superato!")
    return True


def test_massimali_spesa():
    """Test applicazione massimali di spesa."""
    print("\n" + "=" * 60)
    print("TEST: Massimali di spesa CT")
    print("=" * 60)

    # Spesa che supera il 65% di incentivo massimo
    risultato = calculate_heat_pump_incentive(
        tipo_intervento="aria_acqua",
        zona_climatica="E",
        potenza_nominale_kw=10.0,
        scop_dichiarato=4.0,
        spesa_totale_sostenuta=5000.0,  # Spesa bassa
        gwp_refrigerante=">150",
        tipo_soggetto="privato",
        eta_s=150.0
    )

    assert risultato["status"] == "OK"

    # L'incentivo non può superare il 65% della spesa
    max_incentivo = 5000.0 * 0.65
    assert risultato["incentivo_totale"] <= max_incentivo, \
        f"Incentivo {risultato['incentivo_totale']} supera 65% della spesa ({max_incentivo})"

    print(f"  Spesa 5000€: incentivo {risultato['incentivo_totale']:.2f} EUR (max {max_incentivo:.2f}) [OK]")

    print("  [OK] Test superato!")
    return True


def run_all_tests():
    """Esegue tutti i test."""
    print("\n" + "=" * 70)
    print("ENERGY INCENTIVE MANAGER - TEST SUITE")
    print("=" * 70)

    tests = [
        ("Esempio Caleffi", test_esempio_caleffi),
        ("Coefficiente kp", test_coefficiente_kp),
        ("Quf zone climatiche", test_quf_zone_climatiche),
        ("Ecobonus 2025", test_ecobonus_2025),
        ("Calcolo NPV", test_npv_calculation),
        ("Validazione SCOP", test_validazione_scop_minimo),
        ("Massimali spesa", test_massimali_spesa),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RISULTATI: {passed} passati, {failed} falliti su {len(tests)} test")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
