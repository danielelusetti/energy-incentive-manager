#!/usr/bin/env python3
"""
EnergyIncentiveManager - Interfaccia CLI Principale

Software per il calcolo e confronto degli incentivi energetici italiani:
- Conto Termico 3.0 (DM 7/8/2025)
- Ecobonus (D.L. 63/2013, Legge di Bilancio 2025)

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import sys
import os

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.validator import valida_requisiti_ct, valida_requisiti_ecobonus
from modules.calculator_ct import calculate_heat_pump_incentive
from modules.calculator_eco import calculate_ecobonus_deduction
from modules.financial_roi import compare_incentives, genera_report_comparativo


# ============================================================================
# COSTANTI E CONFIGURAZIONE
# ============================================================================

VERSIONE = "1.0.0"

TIPOLOGIE_PDC = {
    "1": ("aria_acqua", "Aria/Acqua (standard)"),
    "2": ("aria_acqua_bt", "Aria/Acqua (bassa temperatura)"),
    "3": ("acqua_acqua", "Acqua/Acqua"),
    "4": ("geotermiche_salamoia_acqua", "Geotermica (salamoia/acqua)"),
    "5": ("split_multisplit", "Aria/Aria - Split/Multisplit (≤12 kW)"),
    "6": ("vrf_vrv", "Aria/Aria - VRF/VRV (>12 kW)"),
}

ZONE_CLIMATICHE = ["A", "B", "C", "D", "E", "F"]

TIPI_SOGGETTO = {
    "1": ("privato", "Privato cittadino"),
    "2": ("impresa", "Impresa/Società"),
    "3": ("PA", "Pubblica Amministrazione"),
}

TIPI_ABITAZIONE = {
    "1": ("abitazione_principale", "Abitazione principale (prima casa)"),
    "2": ("altra_abitazione", "Altra abitazione (seconda casa/altro)"),
}


# ============================================================================
# FUNZIONI DI UTILITÀ CLI
# ============================================================================

def clear_screen():
    """Pulisce lo schermo del terminale."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Stampa l'intestazione del programma."""
    print("\n" + "=" * 70)
    print("  ENERGY INCENTIVE MANAGER v" + VERSIONE)
    print("  Calcolo Incentivi Conto Termico 3.0 ed Ecobonus")
    print("=" * 70)


def print_menu_principale():
    """Stampa il menu principale."""
    print("\n[MENU PRINCIPALE]")
    print("-" * 40)
    print("  1. Calcolo completo (CT + Ecobonus + Confronto)")
    print("  2. Solo Conto Termico 3.0")
    print("  3. Solo Ecobonus")
    print("  4. Validazione requisiti")
    print("  5. Informazioni normative")
    print("  0. Esci")
    print("-" * 40)


def input_float(prompt: str, min_val: float = None, max_val: float = None) -> float:
    """Richiede un input numerico con validazione."""
    while True:
        try:
            valore = float(input(prompt))
            if min_val is not None and valore < min_val:
                print(f"  [!] Il valore deve essere >= {min_val}")
                continue
            if max_val is not None and valore > max_val:
                print(f"  [!] Il valore deve essere <= {max_val}")
                continue
            return valore
        except ValueError:
            print("  [!] Inserire un numero valido")


def input_int(prompt: str, min_val: int = None, max_val: int = None) -> int:
    """Richiede un input intero con validazione."""
    while True:
        try:
            valore = int(input(prompt))
            if min_val is not None and valore < min_val:
                print(f"  [!] Il valore deve essere >= {min_val}")
                continue
            if max_val is not None and valore > max_val:
                print(f"  [!] Il valore deve essere <= {max_val}")
                continue
            return valore
        except ValueError:
            print("  [!] Inserire un numero intero valido")


def input_scelta(prompt: str, opzioni_valide: list) -> str:
    """Richiede una scelta tra opzioni valide."""
    while True:
        scelta = input(prompt).strip().upper()
        if scelta in opzioni_valide:
            return scelta
        print(f"  [!] Scelta non valida. Opzioni: {', '.join(opzioni_valide)}")


def pausa():
    """Pausa prima di continuare."""
    input("\nPremi INVIO per continuare...")


# ============================================================================
# RACCOLTA DATI INTERVENTO
# ============================================================================

def raccogli_dati_pdc() -> dict:
    """Raccoglie i dati per il calcolo pompa di calore."""
    print("\n[DATI POMPA DI CALORE]")
    print("-" * 40)

    # Tipologia
    print("\nTipologia pompa di calore:")
    for key, (_, desc) in TIPOLOGIE_PDC.items():
        print(f"  {key}. {desc}")

    scelta_tipo = input_scelta("\nScelta [1-6]: ", list(TIPOLOGIE_PDC.keys()))
    tipo_intervento, tipo_desc = TIPOLOGIE_PDC[scelta_tipo]

    # Bassa temperatura (solo per aria_acqua)
    bassa_temperatura = False
    if tipo_intervento == "aria_acqua_bt":
        tipo_intervento = "aria_acqua"
        bassa_temperatura = True

    # Zona climatica
    print("\nZona climatica dell'edificio:")
    print("  A = Sud Italia costiero (es. Lampedusa)")
    print("  B = Sud Italia (es. Palermo, Reggio Calabria)")
    print("  C = Centro-Sud (es. Napoli, Roma)")
    print("  D = Centro Italia (es. Firenze, Ancona)")
    print("  E = Nord Italia (es. Milano, Torino, Bologna)")
    print("  F = Zone alpine/appenniniche (es. Cuneo, Belluno)")

    zona = input_scelta("\nZona [A-F]: ", ZONE_CLIMATICHE)

    # Dati tecnici
    print("\nDati tecnici:")
    potenza = input_float("  Potenza nominale [kW]: ", min_val=0.1, max_val=2000)
    scop = input_float("  SCOP dichiarato: ", min_val=1.1, max_val=10)

    # GWP refrigerante
    print("\nGWP del refrigerante:")
    print("  1. GWP > 150 (es. R410A, R32)")
    print("  2. GWP ≤ 150 (es. R290 propano, R1234yf)")
    scelta_gwp = input_scelta("\nScelta [1-2]: ", ["1", "2"])
    gwp = ">150" if scelta_gwp == "1" else "<=150"

    # Spesa
    print("\nDati economici:")
    spesa = input_float("  Spesa totale IVA inclusa [EUR]: ", min_val=100)

    # Tipo soggetto
    print("\nTipo di soggetto beneficiario:")
    for key, (_, desc) in TIPI_SOGGETTO.items():
        print(f"  {key}. {desc}")

    scelta_soggetto = input_scelta("\nScelta [1-3]: ", list(TIPI_SOGGETTO.keys()))
    tipo_soggetto, _ = TIPI_SOGGETTO[scelta_soggetto]

    # Tipo abitazione (per Ecobonus)
    print("\nTipo di abitazione (per calcolo Ecobonus):")
    for key, (_, desc) in TIPI_ABITAZIONE.items():
        print(f"  {key}. {desc}")

    scelta_abit = input_scelta("\nScelta [1-2]: ", list(TIPI_ABITAZIONE.keys()))
    tipo_abitazione, _ = TIPI_ABITAZIONE[scelta_abit]

    # Anno spesa
    anno = input_int("\nAnno della spesa [2024-2028]: ", min_val=2024, max_val=2028)

    return {
        "tipo_intervento": tipo_intervento,
        "tipo_desc": tipo_desc,
        "zona_climatica": zona,
        "potenza_kw": potenza,
        "scop": scop,
        "gwp": gwp,
        "bassa_temperatura": bassa_temperatura,
        "spesa": spesa,
        "tipo_soggetto": tipo_soggetto,
        "tipo_abitazione": tipo_abitazione,
        "anno": anno
    }


def stampa_riepilogo_dati(dati: dict):
    """Stampa il riepilogo dei dati inseriti."""
    print("\n" + "=" * 50)
    print("RIEPILOGO DATI INSERITI")
    print("=" * 50)
    print(f"  Tipologia:        {dati['tipo_desc']}")
    print(f"  Zona climatica:   {dati['zona_climatica']}")
    print(f"  Potenza:          {dati['potenza_kw']} kW")
    print(f"  SCOP:             {dati['scop']}")
    print(f"  GWP refrigerante: {dati['gwp']}")
    print(f"  Spesa totale:     {dati['spesa']:,.2f} EUR")
    print(f"  Tipo soggetto:    {dati['tipo_soggetto']}")
    print(f"  Tipo abitazione:  {dati['tipo_abitazione']}")
    print(f"  Anno spesa:       {dati['anno']}")
    if dati.get('bassa_temperatura'):
        print(f"  Bassa temperatura: Sì")
    print("=" * 50)


# ============================================================================
# CALCOLO E VISUALIZZAZIONE RISULTATI
# ============================================================================

def calcolo_completo():
    """Esegue il calcolo completo con confronto CT vs Ecobonus."""
    clear_screen()
    print_header()
    print("\n[CALCOLO COMPLETO - CT + ECOBONUS + CONFRONTO]")

    # Raccolta dati
    dati = raccogli_dati_pdc()
    stampa_riepilogo_dati(dati)

    print("\n" + "=" * 70)
    print("ELABORAZIONE IN CORSO...")
    print("=" * 70)

    # 1. Validazione CT
    print("\n[1/4] Validazione requisiti Conto Termico 3.0...")
    validazione_ct = valida_requisiti_ct(
        tipo_intervento=dati["tipo_intervento"],
        zona_climatica=dati["zona_climatica"],
        potenza_nominale_kw=dati["potenza_kw"],
        scop_dichiarato=dati["scop"],
        gwp_refrigerante=dati["gwp"],
        bassa_temperatura=dati["bassa_temperatura"]
    )

    ct_ammesso = validazione_ct.ammissibile
    print(f"      {'OK - Ammesso' if ct_ammesso else 'ESCLUSO'}")
    if not ct_ammesso and validazione_ct.errori_bloccanti:
        print(f"      Motivo: {validazione_ct.errori_bloccanti[0]}")

    # 2. Calcolo CT
    risultato_ct = None
    if ct_ammesso:
        print("\n[2/4] Calcolo incentivo Conto Termico 3.0...")
        risultato_ct = calculate_heat_pump_incentive(
            tipo_intervento=dati["tipo_intervento"],
            zona_climatica=dati["zona_climatica"],
            potenza_nominale_kw=dati["potenza_kw"],
            scop_dichiarato=dati["scop"],
            spesa_totale_sostenuta=dati["spesa"],
            gwp_refrigerante=dati["gwp"],
            tipo_soggetto=dati["tipo_soggetto"],
            bassa_temperatura=dati["bassa_temperatura"]
        )

        if risultato_ct["status"] == "OK":
            print(f"      Incentivo calcolato: {risultato_ct['incentivo_totale']:,.2f} EUR")
        else:
            print(f"      ERRORE: {risultato_ct['messaggio']}")
    else:
        print("\n[2/4] Calcolo CT saltato (requisiti non soddisfatti)")

    # 3. Validazione e Calcolo Ecobonus
    print("\n[3/4] Validazione e calcolo Ecobonus...")
    # Mapping tipo CT -> tipo Ecobonus
    tipo_eco = "pompe_di_calore"  # Le PdC sono tutte incentivabili come "pompe_di_calore" in Ecobonus
    validazione_eco = valida_requisiti_ecobonus(
        tipo_intervento=tipo_eco,
        anno_spesa=dati["anno"],
        tipo_abitazione=dati["tipo_abitazione"]
    )

    eco_ammesso = validazione_eco.ammissibile
    print(f"      {'OK - Ammesso' if eco_ammesso else 'ESCLUSO'}")

    risultato_eco = None
    if eco_ammesso:
        risultato_eco = calculate_ecobonus_deduction(
            tipo_intervento="pompe_di_calore",
            spesa_sostenuta=dati["spesa"],
            anno_spesa=dati["anno"],
            tipo_abitazione=dati["tipo_abitazione"]
        )

        if risultato_eco["status"] == "OK":
            aliquota = risultato_eco["calcoli"]["aliquota_applicata"]
            print(f"      Aliquota: {aliquota*100:.0f}%")
            print(f"      Detrazione calcolata: {risultato_eco['detrazione_totale']:,.2f} EUR")
        else:
            print(f"      ERRORE: {risultato_eco['messaggio']}")
    else:
        if validazione_eco.warning:
            for w in validazione_eco.warning:
                print(f"      [!] {w}")

    # 4. Confronto finanziario
    print("\n[4/4] Confronto finanziario NPV...")

    if risultato_ct and risultato_ct["status"] == "OK":
        # Prepara struttura per financial_roi
        ct_per_confronto = {
            "status": "OK",
            "incentivo_totale": risultato_ct["incentivo_totale"],
            "piano_erogazione": {
                "tipo": risultato_ct["erogazione"]["modalita"],
                "importo_rata": risultato_ct["erogazione"]["rate"][0] if risultato_ct["erogazione"]["rate"] else 0,
                "rate": [{"importo": r} for r in risultato_ct["erogazione"]["rate"]]
            }
        }

        confronto = compare_incentives(
            risultato_ct=ct_per_confronto,
            spesa_totale=dati["spesa"],
            tipo_intervento="pompe_di_calore",
            anno_spesa=dati["anno"],
            tipo_abitazione=dati["tipo_abitazione"],
            tasso_sconto=0.03
        )

        print("      Confronto completato")

        # Stampa report
        print("\n")
        print(genera_report_comparativo(confronto))
    else:
        print("      Confronto non disponibile (CT non calcolabile)")

    # Riepilogo finale
    print("\n" + "=" * 70)
    print("RIEPILOGO INCENTIVI DISPONIBILI")
    print("=" * 70)

    if risultato_ct and risultato_ct["status"] == "OK":
        ct_val = risultato_ct["incentivo_totale"]
        ct_mod = risultato_ct["erogazione"]["modalita"]
        print(f"\n  CONTO TERMICO 3.0")
        print(f"    Incentivo totale:  {ct_val:>12,.2f} EUR")
        print(f"    Erogazione:        {'Rata unica' if ct_mod == 'rata_unica' else 'Rate annuali'}")
    else:
        print(f"\n  CONTO TERMICO 3.0: Non disponibile")

    if risultato_eco and risultato_eco["status"] == "OK":
        eco_val = risultato_eco["detrazione_totale"]
        eco_rata = risultato_eco["calcoli"]["rata_annuale"]
        print(f"\n  ECOBONUS")
        print(f"    Detrazione totale: {eco_val:>12,.2f} EUR")
        print(f"    Rata annuale:      {eco_rata:>12,.2f} EUR x 10 anni")
    else:
        print(f"\n  ECOBONUS: Non disponibile")

    print("\n" + "=" * 70)

    pausa()


def calcolo_solo_ct():
    """Esegue solo il calcolo Conto Termico."""
    clear_screen()
    print_header()
    print("\n[CALCOLO CONTO TERMICO 3.0]")

    dati = raccogli_dati_pdc()
    stampa_riepilogo_dati(dati)

    print("\n" + "=" * 70)
    print("CALCOLO CONTO TERMICO 3.0")
    print("=" * 70)

    risultato = calculate_heat_pump_incentive(
        tipo_intervento=dati["tipo_intervento"],
        zona_climatica=dati["zona_climatica"],
        potenza_nominale_kw=dati["potenza_kw"],
        scop_dichiarato=dati["scop"],
        spesa_totale_sostenuta=dati["spesa"],
        gwp_refrigerante=dati["gwp"],
        tipo_soggetto=dati["tipo_soggetto"],
        bassa_temperatura=dati["bassa_temperatura"]
    )

    if risultato["status"] == "OK":
        print(f"\n  RISULTATO: AMMESSO")
        print(f"\n  [Calcoli intermedi]")
        calc = risultato["calcoli_intermedi"]
        print(f"    Quf (ore equiv.):     {calc['Quf']} h")
        print(f"    Qu (calore prod.):    {calc['Qu']:,.2f} kWht")
        print(f"    kp (premialità):      {calc['kp']:.4f}")
        print(f"    Ei (energia incent.): {calc['Ei']:,.2f} kWht")
        print(f"    Ci (coeff. valor.):   {calc['Ci']} EUR/kWht")
        print(f"    Ia (incentivo annuo): {calc['Ia']:,.2f} EUR")
        print(f"    n (annualità):        {calc['n']}")

        print(f"\n  [Massimali]")
        mass = risultato["massimali_applicati"]
        print(f"    Spesa ammissibile:    {mass['spesa_ammissibile']:,.2f} EUR")
        print(f"    Massimale unitario:   {mass['massimale_unitario_applicato']} EUR/kW")
        print(f"    Percentuale max:      {mass['percentuale_applicata']*100:.0f}%")
        if mass["taglio_applicato"]:
            print(f"    [!] Taglio applicato: {mass['importo_tagliato']:,.2f} EUR")

        print(f"\n  [INCENTIVO FINALE]")
        print(f"    Totale:               {risultato['incentivo_totale']:,.2f} EUR")
        erog = risultato["erogazione"]
        if erog["modalita"] == "rata_unica":
            print(f"    Erogazione:           Rata unica")
        else:
            print(f"    Erogazione:           {erog['numero_rate']} rate annuali")
            print(f"    Importo rata:         {erog['rate'][0]:,.2f} EUR")
    else:
        print(f"\n  RISULTATO: NON AMMESSO")
        print(f"  Motivo: {risultato['messaggio']}")

    print("\n" + "=" * 70)
    pausa()


def calcolo_solo_ecobonus():
    """Esegue solo il calcolo Ecobonus."""
    clear_screen()
    print_header()
    print("\n[CALCOLO ECOBONUS]")

    print("\nDati intervento:")

    # Tipo intervento semplificato
    print("\nTipo di intervento:")
    print("  1. Pompe di calore")
    print("  2. Sistemi ibridi")
    print("  3. Solare termico")
    print("  4. Coibentazione involucro")
    print("  5. Serramenti/infissi")

    tipi_eco = {
        "1": "pompe_di_calore",
        "2": "sistemi_ibridi",
        "3": "solare_termico",
        "4": "coibentazione_involucro",
        "5": "serramenti_infissi"
    }

    scelta = input_scelta("\nScelta [1-5]: ", list(tipi_eco.keys()))
    tipo_intervento = tipi_eco[scelta]

    # Altri dati
    spesa = input_float("\nSpesa totale IVA inclusa [EUR]: ", min_val=100)
    anno = input_int("Anno della spesa [2024-2028]: ", min_val=2024, max_val=2028)

    print("\nTipo di abitazione:")
    for key, (_, desc) in TIPI_ABITAZIONE.items():
        print(f"  {key}. {desc}")

    scelta_abit = input_scelta("\nScelta [1-2]: ", list(TIPI_ABITAZIONE.keys()))
    tipo_abitazione, _ = TIPI_ABITAZIONE[scelta_abit]

    print("\n" + "=" * 70)
    print("CALCOLO ECOBONUS")
    print("=" * 70)

    risultato = calculate_ecobonus_deduction(
        tipo_intervento=tipo_intervento,
        spesa_sostenuta=spesa,
        anno_spesa=anno,
        tipo_abitazione=tipo_abitazione
    )

    if risultato["status"] == "OK":
        print(f"\n  RISULTATO: AMMESSO")
        calc = risultato["calcoli"]

        print(f"\n  [Calcolo]")
        print(f"    Aliquota applicata:   {calc['aliquota_applicata']*100:.0f}%")
        print(f"    Limite detrazione:    {calc['limite_detrazione']:,.2f} EUR")
        print(f"    Detrazione lorda:     {calc['detrazione_lorda']:,.2f} EUR")

        print(f"\n  [DETRAZIONE FINALE]")
        print(f"    Totale:               {risultato['detrazione_totale']:,.2f} EUR")
        print(f"    Rata annuale:         {calc['rata_annuale']:,.2f} EUR")
        print(f"    Anni di recupero:     {calc['anni_recupero']}")

        if calc['detrazione_lorda'] > calc['limite_detrazione']:
            print(f"\n  [!] Attenzione: detrazione ridotta per superamento limite massimo")
    else:
        print(f"\n  RISULTATO: NON AMMESSO")
        print(f"  Motivo: {risultato['messaggio']}")

    print("\n" + "=" * 70)
    pausa()


def validazione_requisiti():
    """Esegue solo la validazione dei requisiti."""
    clear_screen()
    print_header()
    print("\n[VALIDAZIONE REQUISITI]")

    dati = raccogli_dati_pdc()

    print("\n" + "=" * 70)
    print("VALIDAZIONE REQUISITI")
    print("=" * 70)

    # Validazione CT
    print("\n[CONTO TERMICO 3.0]")
    print("-" * 40)

    val_ct = valida_requisiti_ct(
        tipo_intervento=dati["tipo_intervento"],
        zona_climatica=dati["zona_climatica"],
        potenza_nominale_kw=dati["potenza_kw"],
        scop_dichiarato=dati["scop"],
        gwp_refrigerante=dati["gwp"],
        bassa_temperatura=dati["bassa_temperatura"]
    )

    if val_ct.ammissibile:
        print("  Stato: AMMESSO")
        print(f"  SCOP dichiarato: {dati['scop']}")
        print(f"  Punteggio:       {val_ct.punteggio_completezza:.0f}%")
    else:
        print("  Stato: ESCLUSO")
        if val_ct.errori_bloccanti:
            print(f"  Motivo: {val_ct.errori_bloccanti[0]}")

    if val_ct.warning:
        print("\n  Avvisi:")
        for w in val_ct.warning:
            print(f"    [!] {w}")

    # Validazione Ecobonus
    print("\n[ECOBONUS]")
    print("-" * 40)

    # Mapping tipo CT -> tipo Ecobonus
    tipo_eco = "pompe_di_calore"  # Le PdC sono tutte incentivabili come "pompe_di_calore" in Ecobonus
    val_eco = valida_requisiti_ecobonus(
        tipo_intervento=tipo_eco,
        anno_spesa=dati["anno"],
        tipo_abitazione=dati["tipo_abitazione"]
    )

    if val_eco.ammissibile:
        print("  Stato: AMMESSO")
        print(f"  Punteggio: {val_eco.punteggio_completezza:.0f}%")
    else:
        print("  Stato: ESCLUSO")
        if val_eco.errori_bloccanti:
            print(f"  Motivo: {val_eco.errori_bloccanti[0]}")

    if val_eco.warning:
        print("\n  Avvisi:")
        for w in val_eco.warning:
            print(f"    [!] {w}")

    print("\n" + "=" * 70)
    pausa()


def info_normative():
    """Mostra informazioni sulle normative."""
    clear_screen()
    print_header()
    print("\n[INFORMAZIONI NORMATIVE]")
    print("=" * 70)

    print("""
CONTO TERMICO 3.0
-----------------
Riferimento: DM 7 agosto 2025 e Regole Applicative GSE

Il Conto Termico incentiva interventi per l'incremento dell'efficienza
energetica e la produzione di energia termica da fonti rinnovabili.

Caratteristiche principali:
- Incentivo erogato direttamente dal GSE (non detrazione fiscale)
- Erogazione: rata unica se ≤15.000€, altrimenti in 2-5 rate annuali
- Massimale: 65% della spesa ammissibile (100% per PA)
- Requisiti tecnici: rispetto minimi Ecodesign (SCOP/COP)

Interventi incentivabili (pompe di calore):
- Sostituzione di impianti esistenti
- Aria/Aria, Aria/Acqua, Acqua/Acqua, Geotermiche


ECOBONUS
--------
Riferimento: D.L. 63/2013, Art. 14 - Legge di Bilancio 2025

L'Ecobonus è una detrazione fiscale IRPEF/IRES per interventi di
riqualificazione energetica degli edifici.

Aliquote dal 2025 (Legge di Bilancio 2025):
- Abitazione principale: 50% (2025-2026), 36% (dal 2027)
- Altre abitazioni:      36% (2025-2026), 30% (dal 2027)

Caratteristiche principali:
- Detrazione ripartita in 10 rate annuali
- Limite detrazione massima: varia per tipo intervento
- Richiede capienza fiscale per usufruire della detrazione
- Dal 2025: ESCLUSE caldaie a combustibili fossili


CONFRONTO CT vs ECOBONUS
------------------------
Il software calcola il Valore Attuale Netto (NPV) per confrontare:
- CT: incasso immediato o in poche rate
- Ecobonus: detrazione diluita su 10 anni

Considerazioni:
- Il CT è preferibile per chi ha bisogno di liquidità
- L'Ecobonus può dare importi nominali maggiori
- Il valore temporale del denaro favorisce il CT
- L'Ecobonus richiede capienza fiscale

""")

    print("=" * 70)
    pausa()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funzione principale del programma."""
    while True:
        clear_screen()
        print_header()
        print_menu_principale()

        scelta = input("\nScelta: ").strip()

        if scelta == "1":
            calcolo_completo()
        elif scelta == "2":
            calcolo_solo_ct()
        elif scelta == "3":
            calcolo_solo_ecobonus()
        elif scelta == "4":
            validazione_requisiti()
        elif scelta == "5":
            info_normative()
        elif scelta == "0":
            print("\nArrivederci!")
            break
        else:
            print("\n[!] Scelta non valida")
            pausa()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgramma interrotto dall'utente.")
        sys.exit(0)
