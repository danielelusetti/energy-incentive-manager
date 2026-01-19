"""
Modulo di comparazione finanziaria tra Conto Termico 3.0 ed Ecobonus.

Questo modulo implementa:
- Calcolo NPV (Net Present Value / Valore Attuale Netto)
- Confronto tra incentivi con flussi di cassa differenti
- Analisi finanziaria per supportare la scelta dell'incentivo ottimale

Riferimenti:
- Conto Termico: DM 7/8/2025 (erogazione immediata o biennale)
- Ecobonus: D.L. 63/2013, Legge di Bilancio 2025 (detrazione 10 anni)

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import logging
from typing import Optional, Literal
from dataclasses import dataclass, field

# Import dei moduli di calcolo esistenti
# Gestisce sia esecuzione come modulo che come script
try:
    from modules.calculator_eco import calculate_ecobonus_deduction
except ImportError:
    from calculator_eco import calculate_ecobonus_deduction

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CashFlowAnalysis:
    """Analisi del flusso di cassa per un incentivo."""
    nome_incentivo: str
    totale_nominale: float
    npv: float
    flusso_cassa: list[float]
    durata_anni: int
    incasso_immediato: bool = False
    note: str = ""


@dataclass
class ComparazioneIncentivi:
    """Risultato del confronto tra Conto Termico ed Ecobonus."""
    conto_termico: CashFlowAnalysis
    ecobonus: CashFlowAnalysis
    vincitore_npv: Literal["conto_termico", "ecobonus", "parita"]
    differenza_npv: float
    differenza_percentuale: float
    tasso_sconto_applicato: float
    consiglio: str
    dettaglio_analisi: dict = field(default_factory=dict)


# ============================================================================
# FUNZIONI DI CALCOLO FINANZIARIO
# ============================================================================

def calculate_npv(
    flusso_cassa: list[float],
    tasso_sconto: float = 0.03
) -> float:
    """
    Calcola il Valore Attuale Netto (NPV / VAN) di un flusso di cassa.

    Formula: NPV = Σ (CF_i / (1 + r)^i) per i = 0, 1, 2, ..., n

    Dove:
    - CF_i = flusso di cassa all'anno i
    - r = tasso di sconto annuale
    - i = anno (0 = oggi)

    Args:
        flusso_cassa: Lista dei flussi di cassa annuali [anno_0, anno_1, ...]
        tasso_sconto: Tasso di sconto annuale (default 3%)

    Returns:
        NPV calcolato
    """
    if not flusso_cassa:
        return 0.0

    npv = 0.0
    for i, cf in enumerate(flusso_cassa):
        # Anno 0: nessuno sconto (valore presente)
        # Anno i: sconto di (1+r)^i
        fattore_sconto = (1 + tasso_sconto) ** i
        npv += cf / fattore_sconto

    return round(npv, 2)


def calculate_irr_approx(
    flusso_cassa: list[float],
    investimento_iniziale: float,
    max_iterations: int = 100,
    tolerance: float = 0.0001
) -> Optional[float]:
    """
    Calcola il Tasso Interno di Rendimento (IRR / TIR) approssimato.

    L'IRR è il tasso che rende NPV = 0.
    Usa il metodo di bisezione per approssimare.

    Args:
        flusso_cassa: Flussi di cassa positivi (benefici)
        investimento_iniziale: Esborso iniziale (valore positivo)
        max_iterations: Numero massimo iterazioni
        tolerance: Tolleranza per convergenza

    Returns:
        IRR come percentuale (es. 0.05 = 5%) o None se non converge
    """
    # Costruisci il flusso completo: [-investimento, +cf1, +cf2, ...]
    cf_completo = [-investimento_iniziale] + flusso_cassa

    # Metodo bisezione tra 0% e 100%
    r_low, r_high = 0.0, 1.0

    for _ in range(max_iterations):
        r_mid = (r_low + r_high) / 2
        npv = calculate_npv(cf_completo, r_mid)

        if abs(npv) < tolerance:
            return round(r_mid, 4)

        if npv > 0:
            r_low = r_mid
        else:
            r_high = r_mid

    return round((r_low + r_high) / 2, 4)


def calculate_payback_period(
    flusso_cassa: list[float],
    investimento_iniziale: float
) -> Optional[float]:
    """
    Calcola il Payback Period (tempo di recupero investimento).

    Args:
        flusso_cassa: Flussi di cassa annuali
        investimento_iniziale: Esborso iniziale

    Returns:
        Numero di anni per recuperare l'investimento (con decimali)
        None se non si recupera entro il periodo
    """
    cumulo = 0.0

    for i, cf in enumerate(flusso_cassa):
        cumulo += cf
        if cumulo >= investimento_iniziale:
            # Calcola frazione dell'anno
            if i == 0:
                return 0.0 if cf >= investimento_iniziale else None

            eccesso = cumulo - investimento_iniziale
            frazione = 1 - (eccesso / cf) if cf > 0 else 0
            return round(i + frazione, 2)

    return None  # Non recuperato nel periodo


# ============================================================================
# COSTRUZIONE FLUSSI DI CASSA
# ============================================================================

def build_cashflow_conto_termico(
    risultato_ct: dict,
    anni_totali: int = 10
) -> list[float]:
    """
    Costruisce il flusso di cassa del Conto Termico.

    Il CT eroga:
    - Rata unica (anno 0) se incentivo <= 15.000€
    - 2 rate (anni 0 e 1) se incentivo > 15.000€

    Args:
        risultato_ct: Dizionario output da calculator_ct.py
        anni_totali: Lunghezza array per omogeneità (default 10)

    Returns:
        Array flusso di cassa [anno_0, anno_1, ..., anno_9]
    """
    cf = [0.0] * anni_totali

    # Estrai piano erogazione dal risultato CT
    piano = risultato_ct.get("piano_erogazione", {})

    if piano.get("tipo") == "rata_unica":
        cf[0] = piano.get("importo_rata", 0.0)
    elif piano.get("tipo") == "rate_annuali":
        rate = piano.get("rate", [])
        for i, rata in enumerate(rate):
            if i < anni_totali:
                cf[i] = rata.get("importo", 0.0)
    else:
        # Fallback: usa incentivo totale anno 0
        cf[0] = risultato_ct.get("incentivo_totale", 0.0)

    return cf


def build_cashflow_ecobonus(
    risultato_eco: dict,
    anni_totali: int = 10
) -> list[float]:
    """
    Costruisce il flusso di cassa dell'Ecobonus.

    La detrazione fiscale:
    - Si recupera in dichiarazione dei redditi
    - Prima rata utilizzabile l'anno successivo alla spesa
    - 10 rate annuali di pari importo

    Nota: L'anno 0 è l'anno della spesa, la detrazione parte dall'anno 1

    Args:
        risultato_eco: Dizionario output da calculator_eco.py
        anni_totali: Lunghezza array (default 10, ma useremo 11 per offset)

    Returns:
        Array flusso di cassa [0, rata_1, rata_2, ..., rata_10]
    """
    # Ecobonus: 10 rate a partire dall'anno 1 (anno 0 = spesa)
    # Quindi array di 11 elementi: [0, r, r, r, r, r, r, r, r, r, r]
    cf = [0.0] * (anni_totali + 1)

    if risultato_eco.get("status") != "OK":
        return cf[:anni_totali]  # Ritorna zeri se non ammesso

    piano_rate = risultato_eco.get("piano_rate", [])

    # Le rate partono dall'anno 1 (anno 0 è la spesa)
    for i, rata in enumerate(piano_rate):
        if i + 1 < len(cf):
            cf[i + 1] = rata

    return cf


# ============================================================================
# FUNZIONE PRINCIPALE DI COMPARAZIONE
# ============================================================================

def compare_incentives(
    risultato_ct: dict,
    spesa_totale: float,
    tipo_intervento: str,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale",
    tasso_sconto: float = 0.03
) -> ComparazioneIncentivi:
    """
    Confronta Conto Termico ed Ecobonus dal punto di vista finanziario.

    Esegue analisi NPV per determinare quale incentivo genera più valore
    considerando il valore temporale del denaro.

    Args:
        risultato_ct: Output di calculator_ct.calculate_heat_pump_incentive()
        spesa_totale: Spesa totale intervento (IVA inclusa)
        tipo_intervento: Tipo intervento per Ecobonus (es. "pompe_di_calore")
        anno_spesa: Anno della spesa (default 2025)
        tipo_abitazione: Per Ecobonus ("abitazione_principale" o "altra_abitazione")
        tasso_sconto: Tasso annuale per attualizzazione (default 3%)

    Returns:
        ComparazioneIncentivi con analisi completa
    """
    logger.info("=" * 60)
    logger.info("AVVIO COMPARAZIONE FINANZIARIA CT vs ECOBONUS")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # STEP 1: Calcolo Ecobonus (riusa modulo esistente)
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 1] Calcolo detrazione Ecobonus")

    risultato_eco = calculate_ecobonus_deduction(
        tipo_intervento=tipo_intervento,
        spesa_sostenuta=spesa_totale,
        anno_spesa=anno_spesa,
        tipo_abitazione=tipo_abitazione
    )

    eco_ammesso = risultato_eco.get("status") == "OK"
    eco_totale = risultato_eco.get("detrazione_totale", 0.0) if eco_ammesso else 0.0

    logger.info(f"  Ecobonus ammesso: {eco_ammesso}")
    logger.info(f"  Detrazione totale: {eco_totale:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 2: Costruzione flussi di cassa
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 2] Costruzione flussi di cassa")

    # Usiamo 11 anni per allineare (anno 0 + 10 anni Ecobonus)
    anni_analisi = 11

    cf_ct = build_cashflow_conto_termico(risultato_ct, anni_analisi)
    cf_eco = build_cashflow_ecobonus(risultato_eco, 10)  # Ritorna 11 elementi

    # Allinea lunghezza
    while len(cf_eco) < anni_analisi:
        cf_eco.append(0.0)
    cf_eco = cf_eco[:anni_analisi]

    logger.info(f"  CF Conto Termico: {[round(x, 2) for x in cf_ct]}")
    logger.info(f"  CF Ecobonus:      {[round(x, 2) for x in cf_eco]}")

    # -------------------------------------------------------------------------
    # STEP 3: Calcolo NPV
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 3] Calcolo NPV (tasso sconto: {:.1%})".format(tasso_sconto))

    npv_ct = calculate_npv(cf_ct, tasso_sconto)
    npv_eco = calculate_npv(cf_eco, tasso_sconto)

    logger.info(f"  NPV Conto Termico: {npv_ct:.2f} EUR")
    logger.info(f"  NPV Ecobonus:      {npv_eco:.2f} EUR")

    # -------------------------------------------------------------------------
    # STEP 4: Analisi aggiuntive
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 4] Analisi aggiuntive")

    # Totali nominali
    ct_totale = sum(cf_ct)
    eco_totale_nominale = sum(cf_eco)

    # CT: verifica se rata unica
    ct_rata_unica = risultato_ct.get("piano_erogazione", {}).get("tipo") == "rata_unica"

    # Differenze
    differenza_npv = npv_eco - npv_ct
    diff_percentuale = (differenza_npv / npv_ct * 100) if npv_ct > 0 else 0

    # Perdita per inflazione Ecobonus
    perdita_eco = eco_totale_nominale - npv_eco
    perdita_eco_pct = (perdita_eco / eco_totale_nominale * 100) if eco_totale_nominale > 0 else 0

    logger.info(f"  Totale nominale CT: {ct_totale:.2f} EUR")
    logger.info(f"  Totale nominale ECO: {eco_totale_nominale:.2f} EUR")
    logger.info(f"  Perdita attualizzazione ECO: {perdita_eco:.2f} EUR ({perdita_eco_pct:.1f}%)")

    # -------------------------------------------------------------------------
    # STEP 5: Determinazione vincitore e consiglio
    # -------------------------------------------------------------------------
    logger.info("\n[STEP 5] Determinazione vincitore")

    if abs(npv_ct - npv_eco) < 100:  # Tolleranza 100€
        vincitore = "parita"
    elif npv_ct > npv_eco:
        vincitore = "conto_termico"
    else:
        vincitore = "ecobonus"

    # Genera consiglio personalizzato
    consiglio = _genera_consiglio(
        vincitore=vincitore,
        npv_ct=npv_ct,
        npv_eco=npv_eco,
        ct_rata_unica=ct_rata_unica,
        eco_ammesso=eco_ammesso,
        differenza_npv=differenza_npv
    )

    logger.info(f"  Vincitore NPV: {vincitore.upper()}")
    logger.info(f"  Differenza: {differenza_npv:.2f} EUR ({diff_percentuale:.1f}%)")

    # -------------------------------------------------------------------------
    # COSTRUZIONE OUTPUT
    # -------------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("COMPARAZIONE COMPLETATA")
    logger.info("=" * 60)

    analisi_ct = CashFlowAnalysis(
        nome_incentivo="Conto Termico 3.0",
        totale_nominale=round(ct_totale, 2),
        npv=npv_ct,
        flusso_cassa=[round(x, 2) for x in cf_ct],
        durata_anni=2 if not ct_rata_unica else 1,
        incasso_immediato=ct_rata_unica,
        note="Contributo diretto GSE" + (" - Rata unica" if ct_rata_unica else " - 2 rate annuali")
    )

    analisi_eco = CashFlowAnalysis(
        nome_incentivo="Ecobonus",
        totale_nominale=round(eco_totale_nominale, 2),
        npv=npv_eco,
        flusso_cassa=[round(x, 2) for x in cf_eco],
        durata_anni=10,
        incasso_immediato=False,
        note="Detrazione IRPEF/IRES in 10 anni" if eco_ammesso else "NON AMMESSO per questo intervento"
    )

    return ComparazioneIncentivi(
        conto_termico=analisi_ct,
        ecobonus=analisi_eco,
        vincitore_npv=vincitore,
        differenza_npv=round(differenza_npv, 2),
        differenza_percentuale=round(diff_percentuale, 2),
        tasso_sconto_applicato=tasso_sconto,
        consiglio=consiglio,
        dettaglio_analisi={
            "perdita_attualizzazione_ecobonus": round(perdita_eco, 2),
            "perdita_attualizzazione_ecobonus_pct": round(perdita_eco_pct, 2),
            "anni_analisi": anni_analisi,
            "ecobonus_ammesso": eco_ammesso
        }
    )


def _genera_consiglio(
    vincitore: str,
    npv_ct: float,
    npv_eco: float,
    ct_rata_unica: bool,
    eco_ammesso: bool,
    differenza_npv: float
) -> str:
    """Genera un consiglio personalizzato basato sull'analisi."""

    if not eco_ammesso:
        return ("L'Ecobonus non è disponibile per questo intervento (dal 2025 le caldaie "
                "a condensazione a combustibili fossili sono escluse). "
                "Il Conto Termico è l'unica opzione disponibile.")

    if vincitore == "parita":
        return ("I due incentivi hanno valore attuale equivalente. "
                "Il Conto Termico offre liquidità immediata, l'Ecobonus richiede "
                "capienza fiscale per 10 anni. Scegli in base alle tue esigenze di cassa.")

    if vincitore == "conto_termico":
        vantaggio = abs(differenza_npv)
        msg = f"Il Conto Termico è più vantaggioso di {vantaggio:.0f}€ in termini di valore attuale. "
        if ct_rata_unica:
            msg += "Inoltre offre l'incasso immediato in un'unica soluzione."
        else:
            msg += "L'erogazione avviene in 2 rate annuali."
        return msg

    # vincitore == "ecobonus"
    vantaggio = abs(differenza_npv)
    return (f"L'Ecobonus genera {vantaggio:.0f}€ in più di valore attuale, "
            "ma richiede capienza fiscale IRPEF/IRES per 10 anni. "
            "Se hai necessità di liquidità immediata, il Conto Termico potrebbe essere preferibile.")


# ============================================================================
# FUNZIONI DI UTILITÀ
# ============================================================================

def analisi_sensibilita_tasso(
    risultato_ct: dict,
    spesa_totale: float,
    tipo_intervento: str,
    tassi: list[float] = None
) -> dict:
    """
    Analisi di sensibilità al variare del tasso di sconto.

    Mostra come cambia il vincitore al variare del tasso.

    Args:
        risultato_ct: Output calculator_ct
        spesa_totale: Spesa totale
        tipo_intervento: Tipo intervento
        tassi: Lista tassi da testare (default [0.01, 0.03, 0.05, 0.07, 0.10])

    Returns:
        Dizionario con risultati per ogni tasso
    """
    if tassi is None:
        tassi = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]

    risultati = {}

    for tasso in tassi:
        comp = compare_incentives(
            risultato_ct=risultato_ct,
            spesa_totale=spesa_totale,
            tipo_intervento=tipo_intervento,
            tasso_sconto=tasso
        )

        risultati[f"{tasso*100:.0f}%"] = {
            "npv_ct": comp.conto_termico.npv,
            "npv_eco": comp.ecobonus.npv,
            "vincitore": comp.vincitore_npv,
            "differenza": comp.differenza_npv
        }

    return risultati


def calcola_tasso_indifferenza(
    risultato_ct: dict,
    spesa_totale: float,
    tipo_intervento: str,
    anno_spesa: int = 2025,
    tipo_abitazione: str = "abitazione_principale"
) -> Optional[float]:
    """
    Calcola il tasso di sconto che rende equivalenti CT ed Ecobonus.

    Utile per capire: "A quale tasso di sconto i due incentivi si equivalgono?"

    Returns:
        Tasso di indifferenza o None se non trovato
    """
    # Usa bisezione tra 0% e 50%
    r_low, r_high = 0.0, 0.50
    tolerance = 0.0001

    for _ in range(100):
        r_mid = (r_low + r_high) / 2

        comp = compare_incentives(
            risultato_ct=risultato_ct,
            spesa_totale=spesa_totale,
            tipo_intervento=tipo_intervento,
            anno_spesa=anno_spesa,
            tipo_abitazione=tipo_abitazione,
            tasso_sconto=r_mid
        )

        diff = comp.differenza_npv

        if abs(diff) < 10:  # Tolleranza 10€
            return round(r_mid, 4)

        # Se Ecobonus vince (diff > 0), aumenta tasso per penalizzarlo
        if diff > 0:
            r_low = r_mid
        else:
            r_high = r_mid

    return None


# ============================================================================
# REPORT TESTUALE
# ============================================================================

def genera_report_comparativo(comparazione: ComparazioneIncentivi) -> str:
    """
    Genera un report testuale della comparazione.

    Args:
        comparazione: Risultato di compare_incentives()

    Returns:
        Stringa con report formattato
    """
    ct = comparazione.conto_termico
    eco = comparazione.ecobonus

    report = []
    report.append("=" * 70)
    report.append("REPORT COMPARATIVO: CONTO TERMICO vs ECOBONUS")
    report.append("=" * 70)
    report.append("")

    # Sezione Conto Termico
    report.append("[CT] CONTO TERMICO 3.0")
    report.append("-" * 35)
    report.append(f"  Totale nominale:    {ct.totale_nominale:>10,.2f} EUR")
    report.append(f"  Valore attuale NPV: {ct.npv:>10,.2f} EUR")
    report.append(f"  Modalita':          {'Rata unica' if ct.incasso_immediato else '2 rate annuali'}")
    report.append(f"  Note: {ct.note}")
    report.append("")

    # Sezione Ecobonus
    report.append("[ECO] ECOBONUS")
    report.append("-" * 35)
    report.append(f"  Totale nominale:    {eco.totale_nominale:>10,.2f} EUR")
    report.append(f"  Valore attuale NPV: {eco.npv:>10,.2f} EUR")
    report.append(f"  Durata recupero:    {eco.durata_anni} anni")
    perdita = eco.totale_nominale - eco.npv
    report.append(f"  Perdita inflazione: {perdita:>10,.2f} EUR ({comparazione.dettaglio_analisi.get('perdita_attualizzazione_ecobonus_pct', 0):.1f}%)")
    report.append(f"  Note: {eco.note}")
    report.append("")

    # Sezione Confronto
    report.append("[VS] CONFRONTO")
    report.append("-" * 35)
    report.append(f"  Tasso sconto applicato: {comparazione.tasso_sconto_applicato*100:.1f}%")
    report.append(f"  Differenza NPV:         {comparazione.differenza_npv:>+10,.2f} EUR")
    report.append(f"  Variazione percentuale: {comparazione.differenza_percentuale:>+10.1f}%")
    report.append("")

    # Vincitore
    vincitore_label = {
        "conto_termico": ">>> CONTO TERMICO",
        "ecobonus": ">>> ECOBONUS",
        "parita": "=== PARITA'"
    }
    report.append(f"  VINCITORE NPV: {vincitore_label.get(comparazione.vincitore_npv, comparazione.vincitore_npv)}")
    report.append("")

    # Consiglio
    report.append("[!] CONSIGLIO")
    report.append("-" * 35)
    # Word wrap del consiglio
    import textwrap
    consiglio_wrapped = textwrap.fill(comparazione.consiglio, width=65)
    for line in consiglio_wrapped.split('\n'):
        report.append(f"  {line}")
    report.append("")
    report.append("=" * 70)

    return "\n".join(report)


# ============================================================================
# TEST / ESEMPIO
# ============================================================================

if __name__ == "__main__":
    import json

    print("\n" + "=" * 70)
    print("TEST MODULO FINANCIAL_ROI")
    print("=" * 70)

    # Simula un risultato CT (normalmente viene da calculator_ct.py)
    risultato_ct_simulato = {
        "status": "OK",
        "incentivo_totale": 6318.58,
        "piano_erogazione": {
            "tipo": "rata_unica",
            "importo_rata": 6318.58,
            "note": "Incentivo <= 15000 EUR: erogazione in rata unica"
        }
    }

    spesa = 15000.0
    tipo = "pompe_di_calore"

    print(f"\nScenario: Pompa di calore, spesa {spesa:.0f} EUR")
    print(f"Incentivo CT simulato: {risultato_ct_simulato['incentivo_totale']:.2f} EUR")

    # Test 1: Comparazione base
    print("\n" + "-" * 50)
    print("TEST 1: Comparazione con tasso 3%")
    print("-" * 50)

    comp = compare_incentives(
        risultato_ct=risultato_ct_simulato,
        spesa_totale=spesa,
        tipo_intervento=tipo,
        anno_spesa=2025,
        tipo_abitazione="abitazione_principale",
        tasso_sconto=0.03
    )

    print(genera_report_comparativo(comp))

    # Test 2: Analisi sensibilità
    print("\n" + "-" * 50)
    print("TEST 2: Analisi sensibilita' al tasso di sconto")
    print("-" * 50)

    sensibilita = analisi_sensibilita_tasso(
        risultato_ct=risultato_ct_simulato,
        spesa_totale=spesa,
        tipo_intervento=tipo
    )

    print("\nTasso   | NPV CT     | NPV ECO    | Vincitore      | Diff")
    print("-" * 65)
    for tasso, dati in sensibilita.items():
        print(f"{tasso:>5}   | {dati['npv_ct']:>9,.2f} | {dati['npv_eco']:>9,.2f} | {dati['vincitore']:<14} | {dati['differenza']:>+8,.2f}")

    # Test 3: Tasso di indifferenza
    print("\n" + "-" * 50)
    print("TEST 3: Calcolo tasso di indifferenza")
    print("-" * 50)

    tasso_indiff = calcola_tasso_indifferenza(
        risultato_ct=risultato_ct_simulato,
        spesa_totale=spesa,
        tipo_intervento=tipo
    )

    if tasso_indiff:
        print(f"\nTasso di indifferenza: {tasso_indiff*100:.2f}%")
        print("(A questo tasso, CT ed Ecobonus hanno lo stesso valore attuale)")
    else:
        print("\nTasso di indifferenza non trovato nel range 0-50%")
