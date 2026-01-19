"""
Modulo per la validazione dei requisiti tecnici dell'intervento II.E
Sostituzione di sistemi per l'illuminazione d'interni e delle pertinenze esterne

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.5
"""

from typing import Dict, List


def valida_requisiti_illuminazione(
    # Tipologia intervento
    tipo_illuminazione: str = "interni",  # "interni", "esterni", "mista"

    # Dati superficie e spesa
    superficie_illuminata_mq: float = 0.0,
    spesa_sostenuta: float = 0.0,

    # Dati potenza (requisito critico)
    potenza_ante_operam_w: float = 0.0,
    potenza_post_operam_w: float = 0.0,

    # Caratteristiche tecniche lampade
    efficienza_luminosa_lm_w: float = 0.0,  # Minimo 80 lm/W
    indice_resa_cromatica: int = 0,  # >80 interni, >60 esterni
    ha_marcatura_ce: bool = False,
    ha_certificazione_laboratorio: bool = False,

    # Conformità normativa
    rispetta_criteri_illuminotecnici: bool = True,  # UNI EN 12464-1
    impianto_sottodimensionato_ante: bool = False,  # Eccezione al 50%

    # Per illuminazione esterna
    conforme_inquinamento_luminoso: bool = True,  # Se applicabile

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
    Valida i requisiti per l'intervento II.E - Illuminazione LED

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
    if superficie_illuminata_mq <= 0:
        errori.append("Superficie illuminata deve essere > 0 m²")

    if spesa_sostenuta <= 0:
        errori.append("Spesa sostenuta deve essere > 0 €")

    # 2. REQUISITO CRITICO: Potenza post ≤ 50% potenza ante
    if potenza_ante_operam_w <= 0:
        errori.append("Potenza ante-operam deve essere > 0 W")

    if potenza_post_operam_w <= 0:
        errori.append("Potenza post-operam deve essere > 0 W")

    if potenza_ante_operam_w > 0 and potenza_post_operam_w > 0:
        rapporto_potenza = (potenza_post_operam_w / potenza_ante_operam_w) * 100

        if rapporto_potenza > 50 and not impianto_sottodimensionato_ante:
            errori.append(
                f"REQUISITO OBBLIGATORIO: La potenza installata post-operam ({potenza_post_operam_w:.0f} W) "
                f"NON deve superare il 50% della potenza sostituita ({potenza_ante_operam_w:.0f} W). "
                f"Rapporto attuale: {rapporto_potenza:.1f}%"
            )
        elif rapporto_potenza > 50 and impianto_sottodimensionato_ante:
            warnings.append(
                f"⚠️ Potenza post-operam ({potenza_post_operam_w:.0f} W) supera il 50% dell'ante-operam "
                f"({potenza_ante_operam_w:.0f} W). L'incentivo sarà calcolato solo sulla quota pari al 50% "
                f"della potenza sostituita ({potenza_ante_operam_w * 0.5:.0f} W) a causa del "
                f"sottodimensionamento ante-operam dell'impianto"
            )
            punteggio -= 10
        elif rapporto_potenza > 40:
            warnings.append(
                f"Rapporto potenza post/ante = {rapporto_potenza:.1f}%. "
                f"Considera di ottimizzare ulteriormente per massimizzare il risparmio energetico"
            )
            punteggio -= 5

    # 3. Efficienza luminosa minima 80 lm/W
    if efficienza_luminosa_lm_w < 80:
        errori.append(
            f"Efficienza luminosa {efficienza_luminosa_lm_w:.1f} lm/W NON conforme. "
            f"Minimo richiesto: 80 lm/W"
        )
    elif efficienza_luminosa_lm_w < 100:
        suggerimenti.append(
            f"💡 Efficienza luminosa {efficienza_luminosa_lm_w:.1f} lm/W è sopra il minimo (80 lm/W) "
            f"ma lampade con efficienza ≥100 lm/W offrirebbero maggiore risparmio energetico"
        )

    # 4. Indice di resa cromatica (CRI)
    if tipo_illuminazione == "interni":
        if indice_resa_cromatica < 80:
            errori.append(
                f"Indice resa cromatica (CRI) {indice_resa_cromatica} NON conforme per illuminazione interni. "
                f"Minimo richiesto: 80"
            )
    elif tipo_illuminazione == "esterni":
        if indice_resa_cromatica < 60:
            errori.append(
                f"Indice resa cromatica (CRI) {indice_resa_cromatica} NON conforme per illuminazione esterni. "
                f"Minimo richiesto: 60"
            )
    elif tipo_illuminazione == "mista":
        if indice_resa_cromatica < 80:
            warnings.append(
                f"⚠️ Per illuminazione mista (interni + esterni), il CRI {indice_resa_cromatica} "
                f"potrebbe non essere sufficiente per la parte interna (minimo 80). "
                f"Verifica che le lampade interne abbiano CRI ≥ 80"
            )
            punteggio -= 5

    # 5. Marcatura CE e certificazione
    if not ha_marcatura_ce:
        errori.append(
            "OBBLIGATORIO: Le lampade devono avere marcatura CE conforme alle norme "
            "di sicurezza e compatibilità elettromagnetica"
        )

    if not ha_certificazione_laboratorio:
        errori.append(
            "OBBLIGATORIO: Le lampade devono essere certificate da laboratori accreditati "
            "per caratteristiche fotometriche (solido fotometrico, resa cromatica, flusso luminoso, efficienza)"
        )

    # 6. Conformità criteri illuminotecnici
    if not rispetta_criteri_illuminotecnici:
        errori.append(
            "OBBLIGATORIO: Gli apparecchi di illuminazione devono rispettare i criteri "
            "illuminotecnici previsti da UNI EN 12464-1 e norme CEI vigenti"
        )

    # 7. Conformità inquinamento luminoso (per esterni)
    if tipo_illuminazione in ["esterni", "mista"]:
        if not conforme_inquinamento_luminoso:
            errori.append(
                "OBBLIGATORIO per illuminazione esterna: I sistemi di illuminazione devono essere "
                "realizzati in conformità alla normativa sull'inquinamento luminoso e sulla sicurezza"
            )

    # 8. Costo specifico massimo 15 €/m²
    if superficie_illuminata_mq > 0:
        costo_specifico = spesa_sostenuta / superficie_illuminata_mq
        if costo_specifico > 15:
            warnings.append(
                f"Costo specifico {costo_specifico:.2f} €/m² supera il massimo ammissibile di 15 €/m². "
                f"L'incentivo sarà calcolato su 15 €/m²"
            )
            punteggio -= 5

    # 9. Requisiti per P ≥ 200 kW
    if potenza_impianto_kw >= 200:
        if ha_diagnosi_ante_operam is None:
            ha_diagnosi_ante_operam = False
        if ha_ape_post_operam is None:
            ha_ape_post_operam = False

        if not ha_diagnosi_ante_operam:
            # Per II.E con P ≥ 200 kW serve relazione tecnica (non diagnosi completa)
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

    # 10. Requisiti per imprese/ETS economici su edifici terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario:
        # Riduzione energia primaria richiesta
        riduzione_minima = 20 if multi_intervento else 10

        if riduzione_energia_primaria_pct < riduzione_minima:
            errori.append(
                f"OBBLIGATORIO per imprese/ETS su terziario: Riduzione energia primaria ≥ {riduzione_minima}% "
                f"(attuale: {riduzione_energia_primaria_pct:.1f}%). "
                f"Nota: 10% se solo II.E, 20% se combinato con altri interventi Titolo II"
            )

        if not ha_ape_ante_post:
            errori.append(
                "OBBLIGATORIO per imprese/ETS su terziario: APE ante-operam e post-operam "
                "per verifica riduzione energia primaria"
            )

    # =========================================================================
    # SUGGERIMENTI E OTTIMIZZAZIONI
    # =========================================================================

    # Suggerimento efficienza
    if efficienza_luminosa_lm_w >= 80 and efficienza_luminosa_lm_w < 120:
        suggerimenti.append(
            "💡 Lampade LED di ultima generazione raggiungono efficienze di 120-150 lm/W. "
            "Considera tecnologie più efficienti per massimizzare il risparmio energetico"
        )

    # Suggerimento riduzione potenza
    if potenza_ante_operam_w > 0 and potenza_post_operam_w > 0:
        riduzione_potenza = ((potenza_ante_operam_w - potenza_post_operam_w) / potenza_ante_operam_w) * 100
        if riduzione_potenza < 60:
            suggerimenti.append(
                f"ℹ️ Riduzione potenza attuale: {riduzione_potenza:.1f}%. "
                f"Ottimizzando il progetto illuminotecnico potresti raggiungere riduzioni fino al 70-80%"
            )

    # Suggerimento multi-intervento per terziario
    if tipo_soggetto in ["impresa", "ets_economico"] and edificio_terziario and not multi_intervento:
        suggerimenti.append(
            "💡 Per imprese/ETS su terziario: combinare l'intervento II.E con altri interventi "
            "del Titolo II (es. II.A isolamento, II.B serramenti, II.F building automation) "
            "per massimizzare l'efficienza complessiva"
        )

    # Verifica regolamenti EU
    suggerimenti.append(
        "ℹ️ Verifica che gli apparecchi rispettino i requisiti minimi dei regolamenti "
        "UE 2017/1369 e regolamenti emanati ai sensi della direttiva 2009/125/CE (Ecodesign)"
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
    print("TEST VALIDAZIONE ILLUMINAZIONE LED")
    print("=" * 80)

    # Test 1: Intervento valido interni
    print("\n[TEST 1] Illuminazione interni - conforme")
    result1 = valida_requisiti_illuminazione(
        tipo_illuminazione="interni",
        superficie_illuminata_mq=200.0,
        spesa_sostenuta=2500.0,  # 12.5 €/m²
        potenza_ante_operam_w=10000.0,
        potenza_post_operam_w=4000.0,  # 40% dell'ante
        efficienza_luminosa_lm_w=120.0,
        indice_resa_cromatica=85,
        ha_marcatura_ce=True,
        ha_certificazione_laboratorio=True,
        rispetta_criteri_illuminotecnici=True
    )
    print(f"Ammissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    if result1['errori']:
        print("Errori:", result1['errori'])
    if result1['warnings']:
        print("Warnings:", result1['warnings'])
    if result1['suggerimenti']:
        print("Suggerimenti:", result1['suggerimenti'])

    # Test 2: Potenza post > 50% ante
    print("\n[TEST 2] Potenza post supera 50% ante")
    result2 = valida_requisiti_illuminazione(
        tipo_illuminazione="interni",
        superficie_illuminata_mq=100.0,
        spesa_sostenuta=1200.0,
        potenza_ante_operam_w=5000.0,
        potenza_post_operam_w=3000.0,  # 60% dell'ante - NON conforme
        efficienza_luminosa_lm_w=100.0,
        indice_resa_cromatica=80,
        ha_marcatura_ce=True,
        ha_certificazione_laboratorio=True,
        rispetta_criteri_illuminotecnici=True
    )
    print(f"Ammissibile: {result2['ammissibile']}")
    print(f"Errori: {result2['errori']}")

    # Test 3: Impresa su terziario - riduzione energia insufficiente
    print("\n[TEST 3] Impresa su terziario - riduzione energia insufficiente")
    result3 = valida_requisiti_illuminazione(
        tipo_illuminazione="interni",
        superficie_illuminata_mq=500.0,
        spesa_sostenuta=7000.0,
        potenza_ante_operam_w=20000.0,
        potenza_post_operam_w=8000.0,
        efficienza_luminosa_lm_w=110.0,
        indice_resa_cromatica=82,
        ha_marcatura_ce=True,
        ha_certificazione_laboratorio=True,
        rispetta_criteri_illuminotecnici=True,
        tipo_soggetto="impresa",
        edificio_terziario=True,
        riduzione_energia_primaria_pct=8.0,  # < 10% richiesto
        ha_ape_ante_post=True
    )
    print(f"Ammissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    # Test 4: Efficienza luminosa insufficiente
    print("\n[TEST 4] Efficienza luminosa insufficiente")
    result4 = valida_requisiti_illuminazione(
        tipo_illuminazione="esterni",
        superficie_illuminata_mq=150.0,
        spesa_sostenuta=2000.0,
        potenza_ante_operam_w=8000.0,
        potenza_post_operam_w=3500.0,
        efficienza_luminosa_lm_w=75.0,  # < 80 lm/W - NON conforme
        indice_resa_cromatica=65,
        ha_marcatura_ce=True,
        ha_certificazione_laboratorio=True,
        rispetta_criteri_illuminotecnici=True,
        conforme_inquinamento_luminoso=True
    )
    print(f"Ammissibile: {result4['ammissibile']}")
    print(f"Errori: {result4['errori']}")

    print("\n" + "=" * 80)
