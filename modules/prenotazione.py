"""
Modulo per la gestione della modalità PRENOTAZIONE Conto Termico 3.0.

La prenotazione consente a PA/ETS/ESCO di:
- Ottenere certezza incentivo PRIMA di iniziare i lavori
- Ricevere acconti durante esecuzione lavori
- Rata intermedia al 50% avanzamento lavori
- Saldo a conclusione lavori

Riferimento: Art. 7 DM 7 agosto 2025 e Regole Applicative GSE
Versione: 1.0.0
"""

from typing import TypedDict, Literal
from datetime import datetime, timedelta


class FasePrenotazione(TypedDict):
    """Fase del processo di prenotazione"""
    numero: int
    nome: str
    descrizione: str
    documenti_richiesti: list[str]
    tempistica_gg: int


class CalendarioPrenotazione(TypedDict):
    """Timeline prenotazione"""
    data_presentazione: str
    data_prevista_ammissione: str
    data_limite_avvio_lavori: str
    data_limite_conclusione_lavori: str
    gg_avvio_lavori: int
    gg_conclusione_lavori: int


class RateizzazionePrenotazione(TypedDict):
    """Rateizzazione incentivo con prenotazione"""
    incentivo_totale: float
    numero_anni: int
    importo_acconto: float
    percentuale_acconto: float
    importo_rata_intermedia: float
    disponibile_rata_intermedia: bool
    importo_saldo: float
    rate_dettaglio: list[dict]


class RisultatoPrenotazione(TypedDict):
    """Risultato calcolo prenotazione"""
    ammissibile: bool
    motivo_esclusione: str
    tipo_casistica: Literal["diagnosi", "epc", "ppp", "assegnazione"] | None
    fasi: list[FasePrenotazione]
    calendario: CalendarioPrenotazione | None
    rateizzazione: RateizzazionePrenotazione | None
    massimale_preventivo: float | None


# Soggetti ammessi a prenotazione
SOGGETTI_AMMESSI_PRENOTAZIONE = [
    "PA",
    "ETS_non_economico",
    "ESCO_per_PA",
    "ESCO_per_ETS"
]


def is_prenotazione_ammissibile(
    tipo_soggetto: Literal["PA", "Privato", "Impresa", "ETS_economico", "ETS_non_economico", "ESCO"],
    conto_terzi: bool = False,
    soggetto_finale: str = None
) -> tuple[bool, str]:
    """
    Verifica se il soggetto può accedere a prenotazione.

    Args:
        tipo_soggetto: Tipologia soggetto richiedente
        conto_terzi: True se ESCO opera per conto terzi
        soggetto_finale: Tipologia soggetto finale (se conto_terzi=True)

    Returns:
        (ammissibile, motivo)
    """
    # PA e ETS non economici: sempre ammessi
    if tipo_soggetto in ["PA", "ETS_non_economico"]:
        return True, "Soggetto ammesso a prenotazione"

    # ESCO per conto PA/ETS
    if tipo_soggetto == "ESCO" and conto_terzi:
        if soggetto_finale in ["PA", "ETS_non_economico"]:
            return True, "ESCO ammessa a prenotazione per conto PA/ETS"
        else:
            return False, "ESCO può accedere a prenotazione solo per conto PA o ETS non economici"

    # Altri soggetti: NO prenotazione
    return False, f"Soggetto {tipo_soggetto} NON ammesso a prenotazione (solo PA, ETS non economici, ESCO per loro conto)"


def determina_casistica_prenotazione(
    ha_diagnosi_energetica: bool,
    ha_epc: bool,
    e_ppp: bool,
    lavori_assegnati: bool
) -> Literal["diagnosi", "epc", "ppp", "assegnazione"]:
    """
    Determina la casistica di prenotazione applicabile.

    Casistiche (Art. 7, comma 1):
    a) Diagnosi energetica (art. 8 D.lgs. 102/2014)
    b) Contratto EPC (Energy Performance Contract)
    c) Partenariato Pubblico Privato (PPP)
    d) Assegnazione lavori già avvenuta

    Args:
        ha_diagnosi_energetica: Diagnosi energetica disponibile
        ha_epc: Contratto EPC stipulato
        e_ppp: È Partenariato Pubblico Privato
        lavori_assegnati: Lavori già assegnati

    Returns:
        Codice casistica applicabile
    """
    if ha_epc:
        return "epc"
    if e_ppp:
        return "ppp"
    if lavori_assegnati:
        return "assegnazione"
    if ha_diagnosi_energetica:
        return "diagnosi"

    # Default: diagnosi (più comune per PA)
    return "diagnosi"


def calcola_rateizzazione_prenotazione(
    incentivo_totale: float,
    numero_anni: int,
    include_acconto: bool = True,
    include_rata_intermedia: bool = False,
    percentuale_avanzamento_intermedia: float = 0.50
) -> RateizzazionePrenotazione:
    """
    Calcola rateizzazione incentivo con modalità prenotazione.

    IMPORTANTE: Con PRENOTAZIONE il pagamento è ANTICIPATO e completato a fine lavori.
    NON ci sono rate annuali successive (quelle sono solo per modalità CONSUNTIVO).

    Regole (Art. 11, comma 6):
    - Acconto: 50% se 2 anni, 40% (2/5) se 5 anni - erogato dopo ammissione
    - Rata intermedia (opzionale): al 50% avanzamento lavori
    - Saldo: a conclusione lavori
    - TOTALE = Acconto + (Rata intermedia) + Saldo = 100%

    Args:
        incentivo_totale: Incentivo totale calcolato (€)
        numero_anni: Parametro di riferimento per calcolo percentuale acconto (non rate annuali!)
        include_acconto: True per includere acconto
        include_rata_intermedia: True per includere rata intermedia
        percentuale_avanzamento_intermedia: % avanzamento per rata intermedia

    Returns:
        RateizzazionePrenotazione con dettaglio rate
    """
    # Calcola percentuale acconto
    if numero_anni == 2:
        percentuale_acconto = 0.50  # 50%
    elif numero_anni == 5:
        percentuale_acconto = 0.40  # 2/5
    else:
        percentuale_acconto = 0.50  # Default

    # Acconto
    importo_acconto = round(incentivo_totale * percentuale_acconto, 2) if include_acconto else 0.0

    # Rata intermedia (al 50% avanzamento)
    importo_rata_intermedia = 0.0
    if include_rata_intermedia:
        # La rata intermedia è una quota della rimanenza dopo acconto
        rimanenza_dopo_acconto = incentivo_totale - importo_acconto
        importo_rata_intermedia = round(rimanenza_dopo_acconto * percentuale_avanzamento_intermedia, 2)

    # Saldo finale
    importo_saldo = round(incentivo_totale - importo_acconto - importo_rata_intermedia, 2)

    # Costruisci dettaglio rate
    rate_dettaglio = []

    if include_acconto:
        rate_dettaglio.append({
            "tipo": "Acconto",
            "momento": "Ammissione a prenotazione",
            "importo": importo_acconto,
            "percentuale": percentuale_acconto * 100,
            "anno": 0
        })

    if include_rata_intermedia:
        rate_dettaglio.append({
            "tipo": "Rata intermedia",
            "momento": f"{percentuale_avanzamento_intermedia*100:.0f}% avanzamento lavori",
            "importo": importo_rata_intermedia,
            "percentuale": (importo_rata_intermedia / incentivo_totale) * 100,
            "anno": 0
        })

    rate_dettaglio.append({
        "tipo": "Saldo",
        "momento": "Conclusione lavori",
        "importo": importo_saldo,
        "percentuale": (importo_saldo / incentivo_totale) * 100,
        "anno": 1
    })

    # NOTA: Con PRENOTAZIONE il pagamento è completato a fine lavori (Acconto + Saldo = 100%)
    # Le rate annuali (2-5 anni) sono SOLO per modalità CONSUNTIVO (senza prenotazione)
    # Quindi NON aggiungiamo rate successive qui

    return RateizzazionePrenotazione(
        incentivo_totale=incentivo_totale,
        numero_anni=numero_anni,
        importo_acconto=importo_acconto,
        percentuale_acconto=percentuale_acconto,
        importo_rata_intermedia=importo_rata_intermedia,
        disponibile_rata_intermedia=include_rata_intermedia,
        importo_saldo=importo_saldo,
        rate_dettaglio=rate_dettaglio
    )


def calcola_calendario_prenotazione(
    data_presentazione: datetime = None,
    tipo_soggetto: Literal["PA", "ETS_non_economico", "ESCO"] = "PA",
    gg_istruttoria: int = 90
) -> CalendarioPrenotazione:
    """
    Calcola timeline prenotazione.

    Tempistiche:
    - Comunicazione avvio lavori: entro 90 gg da ammissione
    - Conclusione lavori: 24 mesi (36 per PA)

    Args:
        data_presentazione: Data presentazione richiesta
        tipo_soggetto: Tipologia soggetto
        gg_istruttoria: Giorni stimati per istruttoria GSE

    Returns:
        CalendarioPrenotazione con date chiave
    """
    if data_presentazione is None:
        data_presentazione = datetime.now()

    # Data prevista ammissione (dopo istruttoria)
    data_ammissione = data_presentazione + timedelta(days=gg_istruttoria)

    # Limite avvio lavori: 90 gg da ammissione
    gg_avvio = 90
    data_limite_avvio = data_ammissione + timedelta(days=gg_avvio)

    # Limite conclusione lavori: 24 mesi (36 per PA)
    gg_conclusione = 1080 if tipo_soggetto == "PA" else 720  # 36 o 24 mesi
    data_limite_conclusione = data_ammissione + timedelta(days=gg_conclusione)

    return CalendarioPrenotazione(
        data_presentazione=data_presentazione.strftime("%d/%m/%Y"),
        data_prevista_ammissione=data_ammissione.strftime("%d/%m/%Y"),
        data_limite_avvio_lavori=data_limite_avvio.strftime("%d/%m/%Y"),
        data_limite_conclusione_lavori=data_limite_conclusione.strftime("%d/%m/%Y"),
        gg_avvio_lavori=gg_avvio,
        gg_conclusione_lavori=gg_conclusione
    )


def get_fasi_prenotazione(
    casistica: Literal["diagnosi", "epc", "ppp", "assegnazione"]
) -> list[FasePrenotazione]:
    """
    Restituisce le fasi del processo di prenotazione per la casistica.

    Args:
        casistica: Tipo casistica prenotazione

    Returns:
        Lista fasi
    """
    fasi_comuni = [
        FasePrenotazione(
            numero=1,
            nome="Caricamento dati e documentazione",
            descrizione="Inserimento dati intervento e upload documenti",
            documenti_richiesti=[
                "Scheda-domanda prenotazione firmata digitalmente",
                "Visura catastale edificio",
                "Diagnosi energetica o APE ante-operam",
                "Progetto preliminare intervento",
                "Preventivi dettagliati spese"
            ],
            tempistica_gg=0
        ),
        FasePrenotazione(
            numero=2,
            nome="Invio istanza a prenotazione",
            descrizione="Invio formale richiesta a GSE",
            documenti_richiesti=[],
            tempistica_gg=1
        ),
        FasePrenotazione(
            numero=3,
            nome="Istruttoria e ammissione",
            descrizione="Valutazione GSE e perfezionamento contratto",
            documenti_richiesti=[],
            tempistica_gg=90
        ),
        FasePrenotazione(
            numero=4,
            nome="Avvio lavori",
            descrizione="Comunicazione avvio lavori (entro 90 gg)",
            documenti_richiesti=[
                "Comunicazione inizio lavori",
                "Ordini/contratti fornitori"
            ],
            tempistica_gg=90
        ),
        FasePrenotazione(
            numero=5,
            nome="Esecuzione lavori",
            descrizione="Realizzazione intervento",
            documenti_richiesti=[
                "Eventuali SAL (Stati Avanzamento Lavori)",
                "Richiesta rata intermedia (se prevista)"
            ],
            tempistica_gg=720  # 24 mesi standard
        ),
        FasePrenotazione(
            numero=6,
            nome="Conclusione e richiesta saldo",
            descrizione="Fine lavori e richiesta erogazione saldo",
            documenti_richiesti=[
                "Tutti i documenti accesso diretto",
                "Fatture quietanzate",
                "Certificato collaudo/dichiarazione fine lavori",
                "APE post-operam",
                "Documentazione fotografica"
            ],
            tempistica_gg=60
        ),
        FasePrenotazione(
            numero=7,
            nome="Erogazione rate successive",
            descrizione="Erogazione rate annuali (se previste)",
            documenti_richiesti=[],
            tempistica_gg=365  # Annuale
        )
    ]

    # Documenti specifici per casistica
    if casistica == "epc":
        fasi_comuni[0]["documenti_richiesti"].append("Contratto EPC stipulato")
    elif casistica == "ppp":
        fasi_comuni[0]["documenti_richiesti"].append("Convenzione PPP")
    elif casistica == "assegnazione":
        fasi_comuni[0]["documenti_richiesti"].append("Atto assegnazione lavori")

    return fasi_comuni


def simula_prenotazione(
    tipo_soggetto: Literal["PA", "Privato", "Impresa", "ETS_economico", "ETS_non_economico", "ESCO"],
    incentivo_totale: float,
    numero_anni: int,
    ha_diagnosi_energetica: bool = False,
    ha_epc: bool = False,
    e_ppp: bool = False,
    lavori_assegnati: bool = False,
    include_acconto: bool = True,
    include_rata_intermedia: bool = False,
    conto_terzi: bool = False,
    soggetto_finale: str = None,
    data_presentazione: datetime = None
) -> RisultatoPrenotazione:
    """
    Simula processo di prenotazione completo.

    Args:
        tipo_soggetto: Tipologia soggetto richiedente
        incentivo_totale: Incentivo totale calcolato
        numero_anni: Numero anni erogazione (2 o 5)
        ha_diagnosi_energetica: Diagnosi disponibile
        ha_epc: Contratto EPC
        e_ppp: È PPP
        lavori_assegnati: Lavori assegnati
        include_acconto: Includi acconto
        include_rata_intermedia: Includi rata intermedia
        conto_terzi: ESCO opera per conto terzi
        soggetto_finale: Soggetto finale (se conto_terzi)
        data_presentazione: Data presentazione

    Returns:
        RisultatoPrenotazione completo
    """
    # Verifica ammissibilità
    ammissibile, motivo = is_prenotazione_ammissibile(tipo_soggetto, conto_terzi, soggetto_finale)

    if not ammissibile:
        return RisultatoPrenotazione(
            ammissibile=False,
            motivo_esclusione=motivo,
            tipo_casistica=None,
            fasi=[],
            calendario=None,
            rateizzazione=None,
            massimale_preventivo=None
        )

    # Determina casistica
    casistica = determina_casistica_prenotazione(
        ha_diagnosi_energetica,
        ha_epc,
        e_ppp,
        lavori_assegnati
    )

    # Calcola rateizzazione
    rateizzazione = calcola_rateizzazione_prenotazione(
        incentivo_totale,
        numero_anni,
        include_acconto,
        include_rata_intermedia
    )

    # Calcola calendario
    calendario = calcola_calendario_prenotazione(
        data_presentazione,
        tipo_soggetto if tipo_soggetto in ["PA", "ETS_non_economico"] else soggetto_finale
    )

    # Ottieni fasi
    fasi = get_fasi_prenotazione(casistica)

    # Massimale preventivo = incentivo calcolato (vincolante)
    massimale_preventivo = incentivo_totale

    return RisultatoPrenotazione(
        ammissibile=True,
        motivo_esclusione="",
        tipo_casistica=casistica,
        fasi=fasi,
        calendario=calendario,
        rateizzazione=rateizzazione,
        massimale_preventivo=massimale_preventivo
    )
