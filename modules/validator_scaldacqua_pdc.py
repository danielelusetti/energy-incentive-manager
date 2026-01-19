"""
Modulo per la validazione dei requisiti tecnici dell'intervento III.E
Sostituzione di scaldacqua elettrici e a gas con scaldacqua a pompa di calore

Riferimento: Regole Applicative CT 3.0 - Paragrafo 9.13
"""

from typing import Dict, List


def valida_requisiti_scaldacqua_pdc(
    # REQUISITO CRITICO: sostituzione (non nuova installazione)
    sostituisce_impianto_esistente: bool = False,
    tipo_scaldacqua_sostituito: str = "elettrico",  # "elettrico", "gas", "altro"

    # Caratteristiche scaldacqua installato
    classe_energetica: str = "A",  # "A", "A+", "A++", "A+++"
    capacita_accumulo_litri: int = 200,

    # Requisito potenza (solo per asseverazione)
    potenza_termica_nominale_kw: float = 3.0,

    # Presenza impianto climatizzazione
    edificio_con_impianto_climatizzazione: bool = False,  # OBBLIGATORIO

    # Documentazione
    ha_dichiarazione_conformita: bool = False,  # OBBLIGATORIO (DM 37/2008)
    ha_certificato_smaltimento: bool = False,  # OBBLIGATORIO
    ha_scheda_tecnica_produttore: bool = False,  # OBBLIGATORIO

    # Spesa sostenuta
    spesa_sostenuta: float = 0.0,

    # Per PA su edifici pubblici
    tipo_soggetto: str = "privato",  # "privato", "pa", "impresa", "ets_economico"
    tipo_edificio: str = "residenziale",  # "residenziale", "pubblico", "terziario"

    # Per potenza >= 200 kW (raro per scaldacqua)
    potenza_complessiva_edificio_kw: float = 0.0,
    ha_diagnosi_energetica_ante: bool = False,
    ha_ape_post: bool = False,

    # A catalogo GSE?
    a_catalogo_gse: bool = False
) -> Dict:
    """
    Valida i requisiti per l'intervento III.E - Scaldacqua a Pompa di Calore

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

    # 1. REQUISITO CRITICO: Deve essere SOSTITUZIONE di impianto esistente
    if not sostituisce_impianto_esistente:
        errori.append(
            "REQUISITO OBBLIGATORIO: L'intervento deve configurarsi come SOSTITUZIONE "
            "di scaldacqua esistenti. Non sono ammesse nuove installazioni senza sostituzione."
        )

    # 2. Tipo scaldacqua sostituito deve essere elettrico o gas
    if tipo_scaldacqua_sostituito not in ["elettrico", "gas"]:
        errori.append(
            f"Tipo scaldacqua sostituito '{tipo_scaldacqua_sostituito}' non ammesso. "
            "Ammessi solo 'elettrico' o 'gas'."
        )

    # 3. REQUISITO CRITICO: Classe energetica minima A (Regolamento UE 812/2013)
    classi_ammesse = ["A", "A+", "A++", "A+++"]
    if classe_energetica not in classi_ammesse:
        errori.append(
            f"OBBLIGATORIO: Classe energetica minima 'A' secondo Regolamento Europeo 812/2013. "
            f"Classe '{classe_energetica}' non ammessa."
        )

    # 4. Capacità accumulo valida
    if capacita_accumulo_litri <= 0:
        errori.append("Capacità accumulo deve essere > 0 litri")

    if capacita_accumulo_litri < 80:
        warnings.append(
            f"Capacità accumulo {capacita_accumulo_litri} litri è molto bassa. "
            "Verifica che sia sufficiente per il fabbisogno di acqua calda sanitaria."
        )
        punteggio -= 5

    # 5. REQUISITO CRITICO: Edificio deve avere impianto di climatizzazione
    if not edificio_con_impianto_climatizzazione:
        errori.append(
            "OBBLIGATORIO: L'edificio deve essere dotato di un impianto di climatizzazione. "
            "Gli scaldacqua PdC possono essere installati solo in edifici con impianto di climatizzazione."
        )

    # 6. REQUISITO CRITICO: Dichiarazione conformità DM 37/2008
    if not ha_dichiarazione_conformita:
        errori.append(
            "OBBLIGATORIO: Dichiarazione di conformità prevista dal DM 37/2008 "
            "(redatta da installatore qualificato)"
        )

    # 7. REQUISITO CRITICO: Certificato smaltimento scaldacqua sostituito
    if not ha_certificato_smaltimento:
        errori.append(
            "OBBLIGATORIO: Certificato del corretto smaltimento dello scaldacqua sostituito "
            "o documento attestante consegna in centro smaltimento"
        )

    # 8. Scheda tecnica produttore
    if not ha_scheda_tecnica_produttore and not a_catalogo_gse:
        errori.append(
            "OBBLIGATORIO (se non a Catalogo GSE): Scheda tecnica del produttore "
            "attestante requisiti minimi (classe energetica, capacità)"
        )

    # 9. Spesa sostenuta
    if spesa_sostenuta <= 0:
        errori.append("Spesa sostenuta deve essere > 0 €")

    # 10. Potenza termica nominale
    if potenza_termica_nominale_kw <= 0:
        warnings.append("Potenza termica nominale non specificata o non valida")
        punteggio -= 3

    # 11. Asseverazione per potenza > 35 kW
    if potenza_termica_nominale_kw > 35 and not a_catalogo_gse:
        suggerimenti.append(
            f"⚠️ Potenza {potenza_termica_nominale_kw:.1f} kW > 35 kW: "
            "Asseverazione tecnico abilitato OBBLIGATORIA + certificazione produttore"
        )
    elif potenza_termica_nominale_kw <= 35 and not a_catalogo_gse:
        suggerimenti.append(
            f"ℹ️ Potenza {potenza_termica_nominale_kw:.1f} kW ≤ 35 kW: "
            "Asseverazione tecnico NON obbligatoria, sufficiente certificazione produttore "
            "per incentivi > 3.500 €"
        )

    # 12. Requisiti per potenza complessiva edificio ≥ 200 kW
    if potenza_complessiva_edificio_kw >= 200:
        if not ha_diagnosi_energetica_ante:
            errori.append(
                f"OBBLIGATORIO per edifici con potenza ≥ 200 kW: "
                "Diagnosi energetica ante-operam"
            )

        if not ha_ape_post:
            errori.append(
                f"OBBLIGATORIO per edifici con potenza ≥ 200 kW: "
                "APE post-operam"
            )

    # =========================================================================
    # SUGGERIMENTI E OTTIMIZZAZIONI
    # =========================================================================

    # Suggerimento classe energetica superiore
    if classe_energetica == "A":
        suggerimenti.append(
            "💡 Classe energetica 'A': considera classi superiori (A+, A++, A+++) "
            "per incentivo maggiore e migliori prestazioni"
        )

    # Suggerimento capacità accumulo
    if capacita_accumulo_litri <= 150:
        suggerimenti.append(
            f"ℹ️ Capacità {capacita_accumulo_litri} litri ≤ 150 litri: "
            "Incentivo massimo ridotto (500 € classe A, 700 € classe A+)"
        )
    else:
        suggerimenti.append(
            f"✅ Capacità {capacita_accumulo_litri} litri > 150 litri: "
            "Incentivo massimo maggiorato (1.100 € classe A, 1.500 € classe A+)"
        )

    # Suggerimento catalogo GSE
    if not a_catalogo_gse:
        suggerimenti.append(
            "💡 Verifica se lo scaldacqua è presente nel Catalogo GSE (Catalogo 2D): "
            "semplifica la documentazione e non richiede asseverazione"
        )

    # Nota importante su tipo sostituzione
    if tipo_scaldacqua_sostituito == "gas":
        suggerimenti.append(
            "ℹ️ Sostituzione scaldacqua a gas con PdC: ottimo intervento per efficienza energetica "
            "e riduzione emissioni. Considera anche i risparmi in bolletta."
        )
    elif tipo_scaldacqua_sostituito == "elettrico":
        suggerimenti.append(
            "ℹ️ Sostituzione scaldacqua elettrico con PdC: riduzione significativa dei consumi elettrici "
            "(COP tipico 2.5-4.0 significa 60-75% di risparmio energetico)"
        )

    # Nota PA su edifici pubblici
    if tipo_soggetto == "pa" and tipo_edificio == "pubblico":
        suggerimenti.append(
            "ℹ️ PA su edificio pubblico: Percentuale incentivata 100% della spesa ammissibile "
            "(invece del 40% per privati)"
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
    print("TEST VALIDAZIONE SCALDACQUA A POMPA DI CALORE (III.E)")
    print("=" * 80)

    # Test 1: Intervento valido classe A, accumulo piccolo
    print("\n[TEST 1] Scaldacqua PdC classe A, 120 litri - conforme")
    result1 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=True,
        tipo_scaldacqua_sostituito="elettrico",
        classe_energetica="A",
        capacita_accumulo_litri=120,
        potenza_termica_nominale_kw=2.5,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=True,
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=2000.0
    )
    print(f"Ammissibile: {result1['ammissibile']}")
    print(f"Punteggio: {result1['punteggio']}/100")
    if result1['suggerimenti']:
        print(f"Suggerimenti: {result1['suggerimenti'][:2]}")

    # Test 2: Intervento valido classe A+, accumulo grande
    print("\n[TEST 2] Scaldacqua PdC classe A+, 250 litri - conforme")
    result2 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=True,
        tipo_scaldacqua_sostituito="gas",
        classe_energetica="A+",
        capacita_accumulo_litri=250,
        potenza_termica_nominale_kw=3.5,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=True,
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=3500.0,
        a_catalogo_gse=True
    )
    print(f"Ammissibile: {result2['ammissibile']}")
    print(f"Punteggio: {result2['punteggio']}/100")

    # Test 3: NON conforme - nuova installazione senza sostituzione
    print("\n[TEST 3] Nuova installazione senza sostituzione - NON conforme")
    result3 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=False,  # NON conforme
        tipo_scaldacqua_sostituito="elettrico",
        classe_energetica="A",
        capacita_accumulo_litri=200,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=True,
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=2500.0
    )
    print(f"Ammissibile: {result3['ammissibile']}")
    print(f"Errori: {result3['errori']}")

    # Test 4: NON conforme - classe energetica insufficiente
    print("\n[TEST 4] Classe energetica B - NON conforme")
    result4 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=True,
        tipo_scaldacqua_sostituito="elettrico",
        classe_energetica="B",  # NON conforme
        capacita_accumulo_litri=200,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=True,
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=2000.0
    )
    print(f"Ammissibile: {result4['ammissibile']}")
    print(f"Errori: {result4['errori']}")

    # Test 5: NON conforme - mancanza certificato smaltimento
    print("\n[TEST 5] Mancanza certificato smaltimento - NON conforme")
    result5 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=True,
        tipo_scaldacqua_sostituito="gas",
        classe_energetica="A",
        capacita_accumulo_litri=180,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=False,  # NON conforme
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=2800.0
    )
    print(f"Ammissibile: {result5['ammissibile']}")
    print(f"Errori: {result5['errori']}")

    # Test 6: PA su edificio pubblico
    print("\n[TEST 6] PA su edificio pubblico - incentivo 100%")
    result6 = valida_requisiti_scaldacqua_pdc(
        sostituisce_impianto_esistente=True,
        tipo_scaldacqua_sostituito="elettrico",
        classe_energetica="A++",
        capacita_accumulo_litri=300,
        potenza_termica_nominale_kw=4.0,
        edificio_con_impianto_climatizzazione=True,
        ha_dichiarazione_conformita=True,
        ha_certificato_smaltimento=True,
        ha_scheda_tecnica_produttore=True,
        spesa_sostenuta=4500.0,
        tipo_soggetto="pa",
        tipo_edificio="pubblico",
        a_catalogo_gse=True
    )
    print(f"Ammissibile: {result6['ammissibile']}")
    print(f"Punteggio: {result6['punteggio']}/100")
    if result6['suggerimenti']:
        print(f"Suggerimenti PA: {[s for s in result6['suggerimenti'] if 'PA' in s]}")

    print("\n" + "=" * 80)
