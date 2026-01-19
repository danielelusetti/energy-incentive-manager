"""
Modulo per la validazione dei requisiti tecnici dell'intervento II.F
Installazione di tecnologie di gestione e controllo automatico (Building Automation)

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.6
"""

from typing import Dict, List


def valida_requisiti_building_automation(
    # Dati superficie e spesa
    superficie_utile_mq: float = 0.0,
    spesa_sostenuta: float = 0.0,

    # Classe di efficienza BA (OBBLIGATORIA: minimo Classe B)
    classe_efficienza_ba: str = "B",  # "A", "B", "C", "D"

    # Conformità normativa
    conforme_uni_en_iso_52120: bool = False,  # OBBLIGATORIO
    conforme_guida_cei_205_18: bool = False,  # OBBLIGATORIO per progettazione

    # Servizi controllati dal sistema BA (almeno uno obbligatorio)
    controlla_riscaldamento: bool = False,
    controlla_raffrescamento: bool = False,
    controlla_ventilazione: bool = False,
    controlla_acs: bool = False,
    controlla_illuminazione: bool = False,
    controlla_integrato: bool = False,
    ha_diagnostica_consumi: bool = False,

    # Documentazione tecnica
    ha_relazione_tecnica_progetto: bool = False,
    ha_schede_controlli_regolazione: bool = False,
    ha_schemi_elettrici: bool = False,

    # Per edifici con P ≥ 200 kW
    potenza_impianto_kw: float = 0.0,
    ha_diagnosi_ante_operam: bool = None,
    ha_ape_post_operam: bool = None,

    # Per imprese/ETS economici su terziario
    tipo_soggetto: str = "privato",  # "privato", "impresa", "pa", "ets_economico"
    edificio_terziario: bool = False,
    riduzione_energia_primaria_pct: float = 0.0,  # % riduzione richiesta
    ha_ape_ante_post: bool = False,  # Per verifica riduzione energia
    multi_intervento: bool = False,  # Combinato con altri Titolo II

    tipo_edificio: str = "residenziale"  # "residenziale", "terziario", "pubblico"
) -> Dict:
    """
    Valida i requisiti per l'intervento II.F - Building Automation

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

    # 1. Superficie e spesa
    if superficie_utile_mq <= 0:
        errori.append("Superficie utile deve essere > 0 m²")

    if spesa_sostenuta <= 0:
        errori.append("Spesa sostenuta deve essere > 0 €")

    # 2. REQUISITO CRITICO: Classe di efficienza minima B
    classi_valide = ["A", "B", "C", "D"]
    if classe_efficienza_ba not in classi_valide:
        errori.append(f"Classe efficienza '{classe_efficienza_ba}' non valida. Ammesse: A, B, C, D")
    elif classe_efficienza_ba in ["C", "D"]:
        errori.append(
            f"REQUISITO OBBLIGATORIO: Classe di efficienza {classe_efficienza_ba} NON ammessa. "
            f"Il sistema BACS/TBM deve raggiungere almeno la Classe B secondo UNI EN ISO 52120-1"
        )
    elif classe_efficienza_ba == "B":
        suggerimenti.append(
            "💡 Classe B è il minimo richiesto. Valuta sistemi di Classe A per prestazioni superiori "
            "e maggiore efficienza energetica"
        )

    # 3. REQUISITO CRITICO: Conformità UNI EN ISO 52120-1
    if not conforme_uni_en_iso_52120:
        errori.append(
            "OBBLIGATORIO: Il sistema deve essere conforme alla norma UNI EN ISO 52120-1 "
            "che specifica i requisiti di progettazione e i criteri per l'identificazione della classe B di efficienza"
        )

    # 4. REQUISITO CRITICO: Conformità Guida CEI 205-18
    if not conforme_guida_cei_205_18:
        errori.append(
            "OBBLIGATORIO: La progettazione del sistema deve seguire la Guida CEI 205-18 "
            "per i requisiti di progettazione dei sistemi BACS"
        )

    # 5. REQUISITO CRITICO: Almeno un servizio deve essere controllato
    servizi_controllati = [
        controlla_riscaldamento,
        controlla_raffrescamento,
        controlla_ventilazione,
        controlla_acs,
        controlla_illuminazione,
        controlla_integrato,
        ha_diagnostica_consumi
    ]

    numero_servizi = sum(servizi_controllati)

    if numero_servizi == 0:
        errori.append(
            "OBBLIGATORIO: Il sistema Building Automation deve controllare almeno uno dei seguenti servizi: "
            "riscaldamento, raffrescamento, ventilazione, ACS, illuminazione, controllo integrato, diagnostica/consumi"
        )
    elif numero_servizi == 1:
        warnings.append(
            f"⚠️ Sistema controlla solo 1 servizio. Per massimizzare l'efficienza energetica, "
            f"considera di estendere il controllo ad altri servizi (riscaldamento, raffrescamento, ventilazione, ecc.)"
        )
        punteggio -= 10
    elif numero_servizi < 3:
        suggerimenti.append(
            f"ℹ️ Sistema controlla {numero_servizi} servizi. Per ottimizzare l'efficienza, "
            f"valuta di includere il controllo integrato di più funzioni"
        )

    # 6. Diagnostica e rilevamento consumi
    if not ha_diagnostica_consumi:
        warnings.append(
            "⚠️ Sistema senza diagnostica e rilevamento consumi. "
            "La funzione diagnostica è fondamentale per monitorare l'efficienza nel tempo"
        )
        punteggio -= 5

    # 7. Controllo integrato
    if numero_servizi >= 2 and not controlla_integrato:
        suggerimenti.append(
            "💡 Con controllo di più servizi, considera di implementare il controllo integrato "
            "per ottimizzare le interazioni tra i diversi sistemi"
        )

    # 8. Documentazione tecnica obbligatoria
    if not ha_relazione_tecnica_progetto:
        errori.append(
            "OBBLIGATORIO: Relazione tecnica di progetto timbrata e firmata dal progettista "
            "contenente descrizione ante/post operam, servizi implementati, conseguimento Classe B"
        )

    if not ha_schede_controlli_regolazione:
        errori.append(
            "OBBLIGATORIO: Schede dettagliate dei controlli di regolazione "
            "come da linee guida CEI 205-18 (tipologia controllo, funzioni, componenti)"
        )

    if not ha_schemi_elettrici:
        errori.append(
            "OBBLIGATORIO: Schemi elettrici con indicazione dei dispositivi installati"
        )

    # 9. Costo specifico massimo 60 €/m²
    if superficie_utile_mq > 0:
        costo_specifico = spesa_sostenuta / superficie_utile_mq
        if costo_specifico > 60:
            warnings.append(
                f"Costo specifico {costo_specifico:.2f} €/m² supera il massimo ammissibile di 60 €/m². "
                f"L'incentivo sarà calcolato su 60 €/m²"
            )
            punteggio -= 5

    # 10. Requisiti per P ≥ 200 kW
    if potenza_impianto_kw >= 200:
        if ha_diagnosi_ante_operam is None:
            ha_diagnosi_ante_operam = False
        if ha_ape_post_operam is None:
            ha_ape_post_operam = False

        if not ha_diagnosi_ante_operam:
            # Per II.F con P ≥ 200 kW serve relazione tecnica (non diagnosi completa)
            warnings.append(
                f"Per P ≥ 200 kW ({potenza_impianto_kw:.1f} kW): "
                f"Richiesta relazione tecnica descrittiva dell'intervento (non diagnosi energetica completa)"
            )
            punteggio -= 5

        if not ha_ape_post_operam:
            errori.append(
                f"OBBLIGATORIO per P ≥ 200 kW ({potenza_impianto_kw:.1f} kW): "
                f"APE post-operam"
            )

    # 11. Requisiti per imprese/ETS economici su edifici terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario:
        # Riduzione energia primaria richiesta
        riduzione_minima = 20 if multi_intervento else 10

        if riduzione_energia_primaria_pct < riduzione_minima:
            errori.append(
                f"OBBLIGATORIO per imprese/ETS su terziario: Riduzione energia primaria ≥ {riduzione_minima}% "
                f"(attuale: {riduzione_energia_primaria_pct:.1f}%). "
                f"Nota: 10% se solo II.F, 20% se combinato con altri interventi Titolo II"
            )

        if not ha_ape_ante_post:
            errori.append(
                "OBBLIGATORIO per imprese/ETS su terziario: APE ante-operam e post-operam "
                "per verifica riduzione energia primaria"
            )

    # =========================================================================
    # SUGGERIMENTI E OTTIMIZZAZIONI
    # =========================================================================

    # Suggerimento servizi mancanti
    servizi_mancanti = []
    if not controlla_riscaldamento:
        servizi_mancanti.append("riscaldamento")
    if not controlla_raffrescamento:
        servizi_mancanti.append("raffrescamento")
    if not controlla_ventilazione:
        servizi_mancanti.append("ventilazione")
    if not controlla_acs:
        servizi_mancanti.append("ACS")
    if not controlla_illuminazione:
        servizi_mancanti.append("illuminazione")

    if len(servizi_mancanti) > 0 and len(servizi_mancanti) < 5:
        suggerimenti.append(
            f"💡 Servizi non controllati: {', '.join(servizi_mancanti)}. "
            f"Estendere il controllo BA aumenterebbe l'efficienza energetica complessiva"
        )

    # Suggerimento Classe A
    if classe_efficienza_ba == "B":
        suggerimenti.append(
            "💡 I sistemi di Classe A offrono funzionalità avanzate di ottimizzazione energetica "
            "e maggiore flessibilità nel controllo. Valuta l'upgrade per massimizzare i benefici"
        )

    # Suggerimento multi-intervento per terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario and not multi_intervento:
        suggerimenti.append(
            "💡 Per imprese/ETS su terziario: combinare l'intervento II.F con altri interventi "
            "del Titolo II (es. II.A isolamento, II.B serramenti, II.E illuminazione) "
            "per massimizzare l'efficienza complessiva"
        )

    # Nota importante conformità
    suggerimenti.append(
        "ℹ️ Verifica che il sistema BACS/TBM sia installato da personale qualificato secondo "
        "Decreto n. 37 del 22 Gennaio 2008 (disposizioni in materia di installazione impianti)"
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
    print("TEST VALIDAZIONE BUILDING AUTOMATION")
    print("=" * 80)

    # Test 1: Intervento valido Classe B con più servizi
    print("\n[TEST 1] Building Automation Classe B - conforme")
    result1 = valida_requisiti_building_automation(
        superficie_utile_mq=300.0,
        spesa_sostenuta=15000.0,  # 50 €/m²
        classe_efficienza_ba="B",
        conforme_uni_en_iso_52120=True,
        conforme_guida_cei_205_18=True,
        controlla_riscaldamento=True,
        controlla_raffrescamento=True,
        controlla_ventilazione=True,
        controlla_acs=True,
        ha_diagnostica_consumi=True,
        controlla_integrato=True,
        ha_relazione_tecnica_progetto=True,
        ha_schede_controlli_regolazione=True,
        ha_schemi_elettrici=True
    )
    print(f"Ammissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    if result1['suggerimenti']:
        print("Suggerimenti:", result1['suggerimenti'][:2])

    # Test 2: Classe C - NON ammessa
    print("\n[TEST 2] Classe C - NON ammessa")
    result2 = valida_requisiti_building_automation(
        superficie_utile_mq=200.0,
        spesa_sostenuta=10000.0,
        classe_efficienza_ba="C",  # NON ammessa
        conforme_uni_en_iso_52120=True,
        conforme_guida_cei_205_18=True,
        controlla_riscaldamento=True,
        ha_diagnostica_consumi=True,
        ha_relazione_tecnica_progetto=True,
        ha_schede_controlli_regolazione=True,
        ha_schemi_elettrici=True
    )
    print(f"Ammissibile: {result2['ammissibile']}")
    print(f"Errori: {result2['errori']}")

    # Test 3: Nessun servizio controllato
    print("\n[TEST 3] Nessun servizio controllato")
    result3 = valida_requisiti_building_automation(
        superficie_utile_mq=150.0,
        spesa_sostenuta=8000.0,
        classe_efficienza_ba="B",
        conforme_uni_en_iso_52120=True,
        conforme_guida_cei_205_18=True,
        # Nessun servizio controllato
        ha_relazione_tecnica_progetto=True,
        ha_schede_controlli_regolazione=True,
        ha_schemi_elettrici=True
    )
    print(f"Ammissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    # Test 4: Impresa su terziario - riduzione energia insufficiente
    print("\n[TEST 4] Impresa su terziario - riduzione energia insufficiente")
    result4 = valida_requisiti_building_automation(
        superficie_utile_mq=500.0,
        spesa_sostenuta=25000.0,
        classe_efficienza_ba="A",
        conforme_uni_en_iso_52120=True,
        conforme_guida_cei_205_18=True,
        controlla_riscaldamento=True,
        controlla_raffrescamento=True,
        ha_diagnostica_consumi=True,
        controlla_integrato=True,
        ha_relazione_tecnica_progetto=True,
        ha_schede_controlli_regolazione=True,
        ha_schemi_elettrici=True,
        tipo_soggetto="impresa",
        edificio_terziario=True,
        riduzione_energia_primaria_pct=8.0,  # < 10% richiesto
        ha_ape_ante_post=True
    )
    print(f"Ammissibile: {result4['ammissibile']}")
    print(f"Errori: {result4['errori']}")

    # Test 5: Mancanza documentazione obbligatoria
    print("\n[TEST 5] Mancanza documentazione obbligatoria")
    result5 = valida_requisiti_building_automation(
        superficie_utile_mq=200.0,
        spesa_sostenuta=10000.0,
        classe_efficienza_ba="B",
        conforme_uni_en_iso_52120=True,
        conforme_guida_cei_205_18=True,
        controlla_riscaldamento=True,
        controlla_raffrescamento=True,
        ha_diagnostica_consumi=True,
        # Manca documentazione
        ha_relazione_tecnica_progetto=False,
        ha_schede_controlli_regolazione=False,
        ha_schemi_elettrici=False
    )
    print(f"Ammissibile: {result5['ammissibile']}")
    print(f"Errori: {result5['errori']}")

    print("\n" + "=" * 80)
