"""
Modulo per la validazione dei requisiti tecnici dell'intervento II.G
Installazione di elementi infrastrutturali per la ricarica privata di veicoli elettrici

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.7
"""

from typing import Dict, List


def valida_requisiti_ricarica_veicoli(
    # REQUISITO CRITICO: abbinamento con pompa di calore
    abbinato_a_pompa_calore: bool = False,

    # Dati infrastruttura
    numero_punti_ricarica: int = 1,
    spesa_sostenuta: float = 0.0,

    # Tipologia infrastruttura
    tipo_infrastruttura: str = "standard_monofase",  # "standard_monofase", "standard_trifase", "potenza_media", "potenza_alta_100", "potenza_alta_over100"
    potenza_installata_kw: float = 7.4,

    # Requisiti tecnici dispositivi
    dispositivi_smart: bool = False,  # OBBLIGATORIO
    modalita_ricarica: str = "modo_3",  # "modo_3" o "modo_4" (CEI EN 61851)
    ha_dichiarazione_conformita: bool = False,  # OBBLIGATORIO (DM 37/2008)

    # Destinazione
    ricarica_pubblica: bool = False,
    registrata_pun: bool = False,  # OBBLIGATORIO se pubblica

    # Ubicazione
    presso_edificio: bool = True,
    presso_pertinenza: bool = False,
    presso_parcheggio_adiacente: bool = False,
    ha_visura_catastale_pertinenza: bool = None,  # OBBLIGATORIO se pertinenza/parcheggio

    # Connessione
    utenza_bassa_media_tensione: bool = False,  # OBBLIGATORIO

    # Per imprese/ETS su terziario
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    edificio_terziario: bool = False,
    riduzione_energia_primaria_pct: float = 0.0,  # ≥20% obbligatorio
    ha_ape_ante_post: bool = False,

    tipo_edificio: str = "residenziale"  # "residenziale", "terziario", "pubblico"
) -> Dict:
    """
    Valida i requisiti per l'intervento II.G - Infrastruttura Ricarica Veicoli Elettrici

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

    # 1. REQUISITO CRITICO: Abbinamento OBBLIGATORIO con Pompa di Calore
    if not abbinato_a_pompa_calore:
        errori.append(
            "REQUISITO OBBLIGATORIO: L'intervento II.G deve essere realizzato CONGIUNTAMENTE "
            "alla sostituzione di impianti di climatizzazione con pompe di calore elettriche (intervento III.A). "
            "NON è possibile installare solo l'infrastruttura di ricarica senza la pompa di calore."
        )

    # 2. Numero punti ricarica e spesa
    if numero_punti_ricarica <= 0:
        errori.append("Numero punti di ricarica deve essere ≥ 1")

    if spesa_sostenuta <= 0:
        errori.append("Spesa sostenuta deve essere > 0 €")

    # 3. Potenza minima 7.4 kW
    if potenza_installata_kw < 7.4:
        errori.append(
            f"Potenza installata {potenza_installata_kw:.1f} kW < 7.4 kW (minimo obbligatorio). "
            "Il dispositivo di ricarica deve avere potenza minima di 7.4 kW."
        )

    # 4. REQUISITO CRITICO: Dispositivi SMART obbligatori
    if not dispositivi_smart:
        errori.append(
            "OBBLIGATORIO: I dispositivi di ricarica devono essere di tipologia SMART, ovvero:\n"
            "• In grado di misurare e registrare la potenza attiva di ricarica\n"
            "• In grado di trasmettere la misura a un soggetto esterno\n"
            "• In grado di ricevere e attuare comandi (riduzione/incremento potenza)"
        )

    # 5. Modalità ricarica CEI EN 61851
    if modalita_ricarica not in ["modo_3", "modo_4"]:
        errori.append(
            f"Modalità ricarica '{modalita_ricarica}' non valida. "
            "Ammesse solo 'modo_3' o 'modo_4' secondo norma CEI EN 61851"
        )

    # 6. REQUISITO CRITICO: Dichiarazione conformità DM 37/2008
    if not ha_dichiarazione_conformita:
        errori.append(
            "OBBLIGATORIO: Dichiarazione di conformità prevista dal DM 37/2008 "
            "(decreto sulle installazioni impiantistiche)"
        )

    # 7. Ricarica pubblica: registrazione PUN obbligatoria
    if ricarica_pubblica and not registrata_pun:
        errori.append(
            "OBBLIGATORIO per ricarica con destinazione pubblica: Registrazione alla Piattaforma Unica Nazionale (PUN) "
            "di cui al Decreto del Ministro dell'ambiente 16 marzo 2023, n. 106"
        )

    # 8. REQUISITO CRITICO: Utenza bassa/media tensione
    if not utenza_bassa_media_tensione:
        errori.append(
            "OBBLIGATORIO: Il Soggetto Responsabile deve essere titolare di utenze connesse in bassa e/o media tensione"
        )

    # 9. Ubicazione e documentazione catastale
    if not (presso_edificio or presso_pertinenza or presso_parcheggio_adiacente):
        errori.append(
            "Specificare l'ubicazione dell'infrastruttura: presso edificio, pertinenza o parcheggio adiacente"
        )

    if (presso_pertinenza or presso_parcheggio_adiacente):
        if ha_visura_catastale_pertinenza is None:
            ha_visura_catastale_pertinenza = False

        if not ha_visura_catastale_pertinenza:
            errori.append(
                "OBBLIGATORIO per installazione su pertinenza/parcheggio adiacente: "
                "Visura catastale che dimostri che l'area costituisca spazio di pertinenza funzionale all'edificio"
            )

    # 10. Validazione tipologia e potenza
    limiti_potenza = {
        "standard_monofase": (7.4, 22.0, "Potenza standard monofase: 7.4 kW < P ≤ 22 kW"),
        "standard_trifase": (7.4, 22.0, "Potenza standard trifase: 7.4 kW < P ≤ 22 kW"),
        "potenza_media": (22.0, 50.0, "Potenza media: 22 kW < P ≤ 50 kW"),
        "potenza_alta_100": (50.0, 100.0, "Potenza alta: 50 kW < P ≤ 100 kW"),
        "potenza_alta_over100": (100.0, 999.0, "Potenza alta: P > 100 kW")
    }

    if tipo_infrastruttura in limiti_potenza:
        min_p, max_p, descrizione = limiti_potenza[tipo_infrastruttura]
        if not (min_p < potenza_installata_kw <= max_p):
            if tipo_infrastruttura == "potenza_alta_over100" and potenza_installata_kw > 100:
                pass  # OK
            else:
                warnings.append(
                    f"Potenza {potenza_installata_kw:.1f} kW non coerente con tipologia '{tipo_infrastruttura}'. "
                    f"{descrizione}"
                )
                punteggio -= 5

    # 11. Requisiti imprese/ETS su terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario:
        # Riduzione energia primaria ≥20% OBBLIGATORIA
        if riduzione_energia_primaria_pct < 20:
            errori.append(
                f"OBBLIGATORIO per imprese/ETS su terziario: Riduzione energia primaria ≥ 20% "
                f"(attuale: {riduzione_energia_primaria_pct:.1f}%). "
                "Questo vale per l'intervento COMBINATO (PdC + Ricarica)"
            )

        if not ha_ape_ante_post:
            errori.append(
                "OBBLIGATORIO per imprese/ETS su terziario: APE ante-operam e post-operam "
                "per verifica riduzione energia primaria"
            )

    # =========================================================================
    # SUGGERIMENTI E OTTIMIZZAZIONI
    # =========================================================================

    # Suggerimento ricarica pubblica
    if not ricarica_pubblica:
        suggerimenti.append(
            "💡 Hai considerato di aprire la ricarica al pubblico? "
            "Potrebbe aumentare l'utilità dell'infrastruttura (richiede registrazione PUN)"
        )

    # Suggerimento potenza
    if potenza_installata_kw < 11:
        suggerimenti.append(
            f"ℹ️ Potenza {potenza_installata_kw:.1f} kW è sopra il minimo (7.4 kW) ma considera che: "
            "potenze ≥11 kW riducono significativamente i tempi di ricarica"
        )

    # Suggerimento numero punti
    if numero_punti_ricarica == 1:
        suggerimenti.append(
            "💡 Con un solo punto di ricarica, valuta l'opportunità di installarne più di uno "
            "se hai più veicoli elettrici o prevedi di averli in futuro"
        )

    # Nota importante su limite incentivo
    suggerimenti.append(
        "⚠️ IMPORTANTE: L'incentivo per l'infrastruttura di ricarica (II.G) "
        "NON può superare l'incentivo riconosciuto per la pompa di calore (III.A). "
        "Calcola prima l'incentivo della pompa di calore."
    )

    # Nota ubicazione
    if presso_pertinenza or presso_parcheggio_adiacente:
        suggerimenti.append(
            "ℹ️ Installazione su pertinenza/parcheggio: verifica che l'area sia funzionale all'edificio "
            "e risulti dalla visura catastale (box, tettoie, posti auto assegnati/condominiali)"
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
    print("TEST VALIDAZIONE INFRASTRUTTURA RICARICA VEICOLI ELETTRICI")
    print("=" * 80)

    # Test 1: Intervento valido standard
    print("\n[TEST 1] Ricarica standard monofase - conforme")
    result1 = valida_requisiti_ricarica_veicoli(
        abbinato_a_pompa_calore=True,
        numero_punti_ricarica=1,
        spesa_sostenuta=2400.0,
        tipo_infrastruttura="standard_monofase",
        potenza_installata_kw=7.4,
        dispositivi_smart=True,
        modalita_ricarica="modo_3",
        ha_dichiarazione_conformita=True,
        ricarica_pubblica=False,
        presso_edificio=True,
        utenza_bassa_media_tensione=True
    )
    print(f"Ammissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    if result1['suggerimenti']:
        print("Suggerimenti:", result1['suggerimenti'][:2])

    # Test 2: Mancanza abbinamento PdC
    print("\n[TEST 2] Mancanza abbinamento con Pompa di Calore")
    result2 = valida_requisiti_ricarica_veicoli(
        abbinato_a_pompa_calore=False,  # NON conforme
        numero_punti_ricarica=1,
        spesa_sostenuta=2400.0,
        tipo_infrastruttura="standard_monofase",
        potenza_installata_kw=7.4,
        dispositivi_smart=True,
        modalita_ricarica="modo_3",
        ha_dichiarazione_conformita=True,
        presso_edificio=True,
        utenza_bassa_media_tensione=True
    )
    print(f"Ammissibile: {result2['ammissibile']}")
    print(f"Errori: {result2['errori']}")

    # Test 3: Dispositivi non smart
    print("\n[TEST 3] Dispositivi NON smart")
    result3 = valida_requisiti_ricarica_veicoli(
        abbinato_a_pompa_calore=True,
        numero_punti_ricarica=2,
        spesa_sostenuta=16800.0,
        tipo_infrastruttura="standard_trifase",
        potenza_installata_kw=22.0,
        dispositivi_smart=False,  # NON conforme
        modalita_ricarica="modo_3",
        ha_dichiarazione_conformita=True,
        presso_edificio=True,
        utenza_bassa_media_tensione=True
    )
    print(f"Ammissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    # Test 4: Ricarica pubblica senza PUN
    print("\n[TEST 4] Ricarica pubblica senza registrazione PUN")
    result4 = valida_requisiti_ricarica_veicoli(
        abbinato_a_pompa_calore=True,
        numero_punti_ricarica=1,
        spesa_sostenuta=30000.0,
        tipo_infrastruttura="potenza_media",
        potenza_installata_kw=40.0,
        dispositivi_smart=True,
        modalita_ricarica="modo_4",
        ha_dichiarazione_conformita=True,
        ricarica_pubblica=True,
        registrata_pun=False,  # NON conforme
        presso_edificio=True,
        utenza_bassa_media_tensione=True
    )
    print(f"Ammissibile: {result4['ammissibile']}")
    print(f"Errori: {result4['errori']}")

    # Test 5: Impresa su terziario - riduzione insufficiente
    print("\n[TEST 5] Impresa su terziario - riduzione energia insufficiente")
    result5 = valida_requisiti_ricarica_veicoli(
        abbinato_a_pompa_calore=True,
        numero_punti_ricarica=2,
        spesa_sostenuta=60000.0,
        tipo_infrastruttura="potenza_alta_100",
        potenza_installata_kw=80.0,
        dispositivi_smart=True,
        modalita_ricarica="modo_4",
        ha_dichiarazione_conformita=True,
        presso_edificio=True,
        utenza_bassa_media_tensione=True,
        tipo_soggetto="impresa",
        edificio_terziario=True,
        riduzione_energia_primaria_pct=15.0,  # < 20% richiesto
        ha_ape_ante_post=True
    )
    print(f"Ammissibile: {result5['ammissibile']}")
    print(f"Errori: {result5['errori']}")

    print("\n" + "=" * 80)
