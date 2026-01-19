"""
Modulo per la validazione dei requisiti tecnici dell'intervento II.C
Installazione di sistemi di schermatura e/o ombreggiamento

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.3
"""

from typing import Dict, List


def valida_requisiti_schermature(
    # Tipologie installate (almeno una deve essere True)
    installa_schermature: bool = False,
    installa_automazione: bool = False,
    installa_pellicole: bool = False,

    # Dati schermature fisse/mobili
    superficie_schermature_mq: float = 0.0,
    spesa_schermature: float = 0.0,
    classe_prestazione_solare: int = 3,  # 3 o 4 (superiore)

    # Dati automazione
    superficie_automazione_mq: float = 0.0,
    spesa_automazione: float = 0.0,
    ha_rilevazione_radiazione: bool = False,

    # Dati pellicole solari
    tipo_pellicola: str = "selettiva_non_riflettente",  # "selettiva_non_riflettente" o "selettiva_riflettente"
    superficie_pellicole_mq: float = 0.0,
    spesa_pellicole: float = 0.0,
    fattore_solare_gtot: float = 0.0,  # Per pellicole

    # Requisiti generali
    esposizione_valida: bool = True,  # Est-Sud-Est → Ovest

    # REQUISITO CRITICO: Abbinamento serramenti
    serramenti_gia_conformi: bool = False,  # Serramenti già rispettano DM 26/06/2015
    abbinato_intervento_iib: bool = False,  # Abbinato a sostituzione serramenti II.B

    # Per edifici con P ≥ 200 kW
    potenza_impianto_kw: float = 0.0,
    ha_diagnosi_ante_operam: bool = None,
    ha_ape_post_operam: bool = None,

    # Per imprese/ETS economici su terziario
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    edificio_terziario: bool = False,
    riduzione_energia_primaria_pct: float = 0.0,  # % riduzione richiesta
    ha_ape_ante_post: bool = False,  # Per verifica riduzione energia

    tipo_edificio: str = "residenziale"  # "residenziale", "terziario", "pubblico"
) -> Dict:
    """
    Valida i requisiti per l'intervento II.C - Schermature Solari

    Returns:
        Dict con chiavi:
        - ammissibile: bool
        - punteggio: int (0-100)
        - errori: List[str]
        - warnings: List[str]
        - suggerimenti: List[str]
    """

    errori = []
    warnings = []
    suggerimenti = []
    punteggio = 100

    # =========================================================================
    # VALIDAZIONI CRITICHE (errori bloccanti)
    # =========================================================================

    # 1. Almeno una tipologia deve essere installata
    if not (installa_schermature or installa_automazione or installa_pellicole):
        errori.append("Selezionare almeno una tipologia di intervento (schermature, automazione, o pellicole)")

    # 2. REQUISITO CRITICO: Abbinamento con serramenti (II.B)
    if not serramenti_gia_conformi and not abbinato_intervento_iib:
        errori.append(
            "REQUISITO OBBLIGATORIO: L'intervento II.C deve essere abbinato alla sostituzione "
            "di serramenti (II.B) OPPURE i serramenti esistenti devono già rispettare i requisiti "
            "del DM 26/06/2015 (trasmittanza limite per zona climatica)"
        )

    # 3. Esposizione valida (Est-Sud-Est → Ovest)
    if not esposizione_valida:
        errori.append(
            "Le schermature devono essere installate su chiusure trasparenti con esposizione "
            "da Est-Sud-Est a Ovest (passando per Sud). Non ammesse esposizioni Nord, Nord-Est, Nord-Ovest"
        )

    # 4. Validazione schermature fisse/mobili
    if installa_schermature:
        if superficie_schermature_mq <= 0:
            errori.append("Superficie schermature deve essere > 0 m²")

        if spesa_schermature <= 0:
            errori.append("Spesa per schermature deve essere > 0 €")

        # Classe prestazione solare
        if classe_prestazione_solare < 3:
            errori.append(
                f"Classe prestazione solare {classe_prestazione_solare} NON ammessa. "
                "Richiesta classe 3 o superiore (UNI EN 14501)"
            )

        # Costo specifico massimo 250 €/m²
        if superficie_schermature_mq > 0:
            costo_spec_scherm = spesa_schermature / superficie_schermature_mq
            if costo_spec_scherm > 250:
                warnings.append(
                    f"Costo specifico schermature {costo_spec_scherm:.2f} €/m² supera il massimo "
                    f"ammissibile di 250 €/m². L'incentivo sarà calcolato su 250 €/m²"
                )
                punteggio -= 5

    # 5. Validazione automazione
    if installa_automazione:
        if superficie_automazione_mq <= 0:
            errori.append("Superficie automazione deve essere > 0 m²")

        if spesa_automazione <= 0:
            errori.append("Spesa per automazione deve essere > 0 €")

        # OBBLIGATORIO: Rilevazione radiazione solare
        if not ha_rilevazione_radiazione:
            errori.append(
                "OBBLIGATORIO: I meccanismi automatici di regolazione devono essere basati "
                "sulla rilevazione della radiazione solare incidente (UNI EN 15232)"
            )

        # Costo specifico massimo 50 €/m²
        if superficie_automazione_mq > 0:
            costo_spec_auto = spesa_automazione / superficie_automazione_mq
            if costo_spec_auto > 50:
                warnings.append(
                    f"Costo specifico automazione {costo_spec_auto:.2f} €/m² supera il massimo "
                    f"ammissibile di 50 €/m². L'incentivo sarà calcolato su 50 €/m²"
                )
                punteggio -= 5

    # 6. Validazione pellicole solari
    if installa_pellicole:
        if superficie_pellicole_mq <= 0:
            errori.append("Superficie pellicole deve essere > 0 m²")

        if spesa_pellicole <= 0:
            errori.append("Spesa per pellicole deve essere > 0 €")

        # Fattore solare g_tot (classe 3 o 4 UNI 14501)
        if fattore_solare_gtot <= 0:
            errori.append("Fattore solare g_tot deve essere > 0")
        elif fattore_solare_gtot > 0.5:
            warnings.append(
                f"Fattore solare g_tot = {fattore_solare_gtot:.3f} potrebbe non rientrare "
                "in classe 3 o 4. Verificare certificazione produttore"
            )
            punteggio -= 5

        # Costo specifico massimo
        costo_max_pellicole = 130 if tipo_pellicola == "selettiva_non_riflettente" else 80
        if superficie_pellicole_mq > 0:
            costo_spec_pell = spesa_pellicole / superficie_pellicole_mq
            if costo_spec_pell > costo_max_pellicole:
                warnings.append(
                    f"Costo specifico pellicole {costo_spec_pell:.2f} €/m² supera il massimo "
                    f"ammissibile di {costo_max_pellicole} €/m². L'incentivo sarà calcolato su {costo_max_pellicole} €/m²"
                )
                punteggio -= 5

    # 7. Verifica combinazioni ammesse
    if installa_pellicole and installa_automazione:
        # Automazione con pellicole richiede schermature preesistenti
        if not installa_schermature and not serramenti_gia_conformi:
            warnings.append(
                "ATTENZIONE: L'installazione di pellicole + automazione richiede che l'edificio "
                "sia già dotato di schermature conformi alla Tabella 2 - Allegato 1 DM 7/8/2025"
            )
            punteggio -= 10

    # 8. Requisiti per P ≥ 200 kW
    if potenza_impianto_kw >= 200:
        if ha_diagnosi_ante_operam is None:
            ha_diagnosi_ante_operam = False
        if ha_ape_post_operam is None:
            ha_ape_post_operam = False

        if not ha_diagnosi_ante_operam:
            errori.append(
                f"OBBLIGATORIO per P ≥ 200 kW ({potenza_impianto_kw:.1f} kW): "
                "Diagnosi energetica ante-operam"
            )

        if not ha_ape_post_operam:
            errori.append(
                f"OBBLIGATORIO per P ≥ 200 kW ({potenza_impianto_kw:.1f} kW): "
                "APE post-operam"
            )

    # 9. Requisiti per imprese/ETS economici su edifici terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario:
        # Riduzione energia primaria richiesta
        riduzione_minima = 10 if (serramenti_gia_conformi or not abbinato_intervento_iib) else 20

        if riduzione_energia_primaria_pct < riduzione_minima:
            errori.append(
                f"OBBLIGATORIO per imprese/ETS su terziario: Riduzione energia primaria ≥ {riduzione_minima}% "
                f"(attuale: {riduzione_energia_primaria_pct:.1f}%)"
            )

        if not ha_ape_ante_post:
            errori.append(
                "OBBLIGATORIO per imprese/ETS su terziario: APE ante-operam e post-operam "
                "per verifica riduzione energia primaria"
            )

    # =========================================================================
    # SUGGERIMENTI E OTTIMIZZAZIONI
    # =========================================================================

    # Suggerimento classe superiore
    if installa_schermature and classe_prestazione_solare == 3:
        suggerimenti.append(
            "💡 Classe prestazione solare 3 è il minimo. Valuta classe 4 per prestazioni superiori"
        )

    # Suggerimento automazione
    if installa_schermature and not installa_automazione:
        suggerimenti.append(
            "💡 Considera l'installazione di meccanismi automatici di regolazione basati su radiazione solare "
            "per massimizzare l'efficienza e accedere a ulteriore incentivo"
        )

    # Abbinamento serramenti
    if serramenti_gia_conformi:
        suggerimenti.append(
            "ℹ️ Hai dichiarato che i serramenti sono già conformi al DM 26/06/2015. "
            "Conserva la documentazione tecnica per eventuali controlli"
        )

    if abbinato_intervento_iib:
        suggerimenti.append(
            "ℹ️ Intervento abbinato a sostituzione serramenti (II.B). "
            "Ricorda che per imprese/ETS su terziario serve riduzione energia ≥ 20%"
        )

    # =========================================================================
    # CALCOLO FINALE
    # =========================================================================

    ammissibile = len(errori) == 0

    if not ammissibile:
        punteggio = 0

    return {
        "ammissibile": ammissibile,
        "punteggio": max(0, min(100, punteggio)),
        "errori": errori,
        "warnings": warnings,
        "suggerimenti": suggerimenti
    }


# ==============================================================================
# TEST DEL MODULO
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST VALIDAZIONE SCHERMATURE SOLARI")
    print("=" * 80)

    # Test 1: Schermature + automazione con serramenti conformi
    print("\n[TEST 1] Schermature + automazione, serramenti conformi")
    result1 = valida_requisiti_schermature(
        installa_schermature=True,
        superficie_schermature_mq=50.0,
        spesa_schermature=10000.0,
        classe_prestazione_solare=4,
        installa_automazione=True,
        superficie_automazione_mq=50.0,
        spesa_automazione=2000.0,
        ha_rilevazione_radiazione=True,
        serramenti_gia_conformi=True,
        esposizione_valida=True
    )
    print(f"Ammissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    if result1['errori']:
        print("Errori:", result1['errori'])
    if result1['warnings']:
        print("Warnings:", result1['warnings'])
    if result1['suggerimenti']:
        print("Suggerimenti:", result1['suggerimenti'])

    # Test 2: Mancanza abbinamento serramenti
    print("\n[TEST 2] Mancanza requisito abbinamento serramenti")
    result2 = valida_requisiti_schermature(
        installa_schermature=True,
        superficie_schermature_mq=50.0,
        spesa_schermature=10000.0,
        classe_prestazione_solare=3,
        serramenti_gia_conformi=False,
        abbinato_intervento_iib=False,
        esposizione_valida=True
    )
    print(f"Ammissibile: {result2['ammissibile']}")
    print(f"Errori: {result2['errori']}")

    # Test 3: Impresa su terziario con riduzione insufficiente
    print("\n[TEST 3] Impresa su terziario - riduzione energia insufficiente")
    result3 = valida_requisiti_schermature(
        installa_schermature=True,
        superficie_schermature_mq=100.0,
        spesa_schermature=20000.0,
        classe_prestazione_solare=3,
        serramenti_gia_conformi=True,
        esposizione_valida=True,
        tipo_soggetto="impresa",
        edificio_terziario=True,
        riduzione_energia_primaria_pct=8.0,  # < 10% richiesto
        ha_ape_ante_post=True
    )
    print(f"Ammissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    print("\n" + "=" * 80)
