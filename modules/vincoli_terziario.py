"""
Modulo per la gestione dei vincoli specifici per edifici del settore terziario
secondo CT 3.0 - Art. 25, comma 2 e Art. 4, comma 3.

Vincoli per IMPRESE e ETS ECONOMICI su edifici terziario:
- NO pompe di calore a gas
- Riduzione domanda energia primaria OBBLIGATORIA:
  * 10% per: II.B, II.E, II.F (singoli)
  * 20% per: II.B+altro Tit.II, II.E+altro Tit.II, II.F+altro Tit.II
  * 20% per: II.G, II.H, II.D (nZEB)

Riferimento: DM 7 agosto 2025 e Regole Applicative GSE
Versione: 1.0.0
"""

from typing import TypedDict, Literal


class VincoliTerziario(TypedDict):
    """Vincoli applicabili per edifici terziario"""
    riduzione_energia_primaria_richiesta: float  # Percentuale minima richiesta
    riduzione_energia_primaria_effettiva: float  # Percentuale effettiva (da APE)
    vincolo_soddisfatto: bool
    pdc_gas_ammessa: bool
    richiede_ape: bool
    messaggio: str


# Categorie catastali terziario (Tabella 1 Allegato 1 DM)
CATEGORIE_CATASTALI_TERZIARIO = [
    # Gruppo B - Edifici per uso collettivo
    "B/1", "B/2", "B/3", "B/4", "B/5", "B/6", "B/7", "B/8",
    # Gruppo C - Edifici commerciali e vari
    "C/1", "C/2", "C/3", "C/4", "C/5", "C/6", "C/7",
    # Gruppo D - Edifici a destinazione speciale
    "D/1", "D/2", "D/3", "D/4", "D/5", "D/6", "D/7", "D/8", "D/9", "D/10",
    # Gruppo E - Edifici a destinazione particolare
    "E/1", "E/2", "E/3", "E/4", "E/5", "E/6", "E/7", "E/8", "E/9"
]

# Categorie catastali residenziale
CATEGORIE_CATASTALI_RESIDENZIALE = [
    "A/1", "A/2", "A/3", "A/4", "A/5", "A/6", "A/7", "A/8", "A/9", "A/11"
    # Escluso A/10 (uffici e studi privati)
]

# Interventi con riduzione 10% se singoli
INTERVENTI_RIDUZIONE_10_PCT = ["II.B", "II.E", "II.F"]

# Interventi con riduzione 20% sempre
INTERVENTI_RIDUZIONE_20_PCT = ["II.G", "II.H", "II.D"]


def is_terziario(categoria_catastale: str) -> bool:
    """
    Verifica se la categoria catastale appartiene al settore terziario.

    Args:
        categoria_catastale: Categoria catastale (es. "C/1", "D/3")

    Returns:
        True se terziario, False se residenziale
    """
    return categoria_catastale in CATEGORIE_CATASTALI_TERZIARIO


def calcola_riduzione_richiesta(
    codice_intervento: str,
    multi_intervento: bool = False,
    interventi_combinati: list[str] = None
) -> float:
    """
    Calcola la riduzione di energia primaria richiesta per l'intervento.

    Args:
        codice_intervento: Codice intervento principale (es. "II.B", "II.H")
        multi_intervento: True se multi-intervento
        interventi_combinati: Lista interventi combinati

    Returns:
        Percentuale riduzione richiesta (0.10 = 10%, 0.20 = 20%)
    """
    if interventi_combinati is None:
        interventi_combinati = []

    # Interventi con riduzione 20% sempre
    if codice_intervento in INTERVENTI_RIDUZIONE_20_PCT:
        return 0.20

    # Interventi con riduzione variabile
    if codice_intervento in INTERVENTI_RIDUZIONE_10_PCT:
        if multi_intervento:
            # Verifica se combinato con altro Titolo II
            titoli_ii = [i for i in interventi_combinati if i.startswith("II.")]
            if len(titoli_ii) > 1:  # Più di un intervento Titolo II
                return 0.20
        return 0.10

    # Per altri interventi (Titolo III): NO riduzione obbligatoria
    return 0.0


def verifica_vincoli_terziario(
    tipo_soggetto: Literal["PA", "Privato", "Impresa", "ETS_economico", "ETS_non_economico"],
    categoria_catastale: str,
    codice_intervento: str,
    tipo_pdc: str = None,  # "elettrica" o "gas"
    multi_intervento: bool = False,
    interventi_combinati: list[str] = None,
    riduzione_energia_primaria_effettiva: float = 0.0,  # Da APE (0.15 = 15%)
    ape_disponibili: bool = False
) -> VincoliTerziario:
    """
    Verifica i vincoli specifici per interventi su edifici terziario.

    Args:
        tipo_soggetto: Tipologia soggetto
        categoria_catastale: Categoria catastale edificio
        codice_intervento: Codice intervento (es. "II.B", "III.A")
        tipo_pdc: "elettrica" o "gas" (solo per pompe di calore)
        multi_intervento: True se multi-intervento
        interventi_combinati: Lista codici interventi combinati
        riduzione_energia_primaria_effettiva: Riduzione effettiva da APE
        ape_disponibili: True se APE ante e post disponibili

    Returns:
        VincoliTerziario con risultati verifica
    """
    if interventi_combinati is None:
        interventi_combinati = []

    # Verifica se è terziario
    edificio_terziario = is_terziario(categoria_catastale)

    # Verifica se soggetto è impresa/ETS economico
    soggetto_impresa = tipo_soggetto in ["Impresa", "ETS_economico"]

    # Se NON è terziario O NON è impresa -> nessun vincolo
    if not edificio_terziario or not soggetto_impresa:
        return VincoliTerziario(
            riduzione_energia_primaria_richiesta=0.0,
            riduzione_energia_primaria_effettiva=riduzione_energia_primaria_effettiva,
            vincolo_soddisfatto=True,
            pdc_gas_ammessa=True,
            richiede_ape=False,
            messaggio="Nessun vincolo specifico applicabile"
        )

    # VINCOLO 1: NO pompe di calore a gas per imprese su terziario
    pdc_gas_ammessa = True
    if codice_intervento == "III.A" and tipo_pdc == "gas":
        pdc_gas_ammessa = False
        return VincoliTerziario(
            riduzione_energia_primaria_richiesta=0.0,
            riduzione_energia_primaria_effettiva=0.0,
            vincolo_soddisfatto=False,
            pdc_gas_ammessa=False,
            richiede_ape=False,
            messaggio="❌ IMPRESE/ETS economici su edifici terziario: pompe di calore a GAS NON ammesse (Art. 25, comma 2)"
        )

    # VINCOLO 2: Riduzione energia primaria per interventi specifici
    riduzione_richiesta = calcola_riduzione_richiesta(
        codice_intervento,
        multi_intervento,
        interventi_combinati
    )

    # Se non richiede riduzione -> OK
    if riduzione_richiesta == 0.0:
        return VincoliTerziario(
            riduzione_energia_primaria_richiesta=0.0,
            riduzione_energia_primaria_effettiva=riduzione_energia_primaria_effettiva,
            vincolo_soddisfatto=True,
            pdc_gas_ammessa=True,
            richiede_ape=False,
            messaggio="✅ Intervento ammesso - No riduzione energia primaria richiesta"
        )

    # Richiede riduzione -> verifica APE
    if not ape_disponibili:
        return VincoliTerziario(
            riduzione_energia_primaria_richiesta=riduzione_richiesta,
            riduzione_energia_primaria_effettiva=0.0,
            vincolo_soddisfatto=False,
            pdc_gas_ammessa=True,
            richiede_ape=True,
            messaggio=f"⚠️ OBBLIGATORIO APE ante e post-operam per verificare riduzione energia primaria >= {riduzione_richiesta*100:.0f}%"
        )

    # Verifica se riduzione effettiva soddisfa vincolo
    vincolo_soddisfatto = riduzione_energia_primaria_effettiva >= riduzione_richiesta

    if vincolo_soddisfatto:
        messaggio = f"✅ Riduzione energia primaria {riduzione_energia_primaria_effettiva*100:.1f}% >= {riduzione_richiesta*100:.0f}% richiesto"
    else:
        messaggio = f"❌ Riduzione energia primaria {riduzione_energia_primaria_effettiva*100:.1f}% < {riduzione_richiesta*100:.0f}% richiesto - Intervento NON ammissibile"

    return VincoliTerziario(
        riduzione_energia_primaria_richiesta=riduzione_richiesta,
        riduzione_energia_primaria_effettiva=riduzione_energia_primaria_effettiva,
        vincolo_soddisfatto=vincolo_soddisfatto,
        pdc_gas_ammessa=True,
        richiede_ape=True,
        messaggio=messaggio
    )


def get_interventi_soggetti_vincolo() -> list[str]:
    """
    Restituisce lista codici interventi soggetti a vincolo riduzione energia primaria.

    Returns:
        Lista codici interventi
    """
    return INTERVENTI_RIDUZIONE_10_PCT + INTERVENTI_RIDUZIONE_20_PCT


def get_descrizione_vincolo(codice_intervento: str, multi_intervento: bool = False) -> str:
    """
    Restituisce descrizione vincolo per l'intervento.

    Args:
        codice_intervento: Codice intervento
        multi_intervento: True se multi-intervento

    Returns:
        Descrizione vincolo
    """
    riduzione = calcola_riduzione_richiesta(codice_intervento, multi_intervento)

    if riduzione == 0.0:
        return "Nessun vincolo riduzione energia primaria"

    if codice_intervento in INTERVENTI_RIDUZIONE_20_PCT:
        return f"Riduzione energia primaria >= 20% (sempre richiesta)"

    if codice_intervento in INTERVENTI_RIDUZIONE_10_PCT:
        if multi_intervento:
            return f"Riduzione energia primaria >= 20% (multi-intervento con altro Titolo II)"
        else:
            return f"Riduzione energia primaria >= 10% (singolo intervento)"

    return "Vincolo non definito"


# Mappatura tipo intervento streamlit -> codice intervento CT
MAPPA_CODICI_INTERVENTO = {
    # Titolo III - Pompe di calore
    "pompe_di_calore": "III.A",
    "pdc": "III.A",

    # Titolo II - Efficienza energetica involucro
    "serramenti": "II.B",
    "finestre": "II.B",
    "isolamento_termico": "II.E",  # Pareti verticali
    "isolamento_copertura": "II.F",  # Coperture
    "isolamento_pavimento": "II.F",  # Pavimenti
    "schermature_solari": "II.C",

    # Building automation e illuminazione
    "building_automation": "II.D",  # NZEB
    "illuminazione": "II.H",  # LED (no vincoli terziario)

    # VE e FV
    "ricarica_ve": "II.G",
    "fotovoltaico": "II.H",

    # Biomassa
    "biomassa": "III.C"
}


def get_codice_intervento(tipo_intervento_app: str) -> str:
    """
    Ottiene il codice intervento CT da tipo intervento applicazione.

    Args:
        tipo_intervento_app: Nome tipo intervento nell'applicazione

    Returns:
        Codice intervento CT (es. "II.B", "III.A")
    """
    return MAPPA_CODICI_INTERVENTO.get(tipo_intervento_app.lower(), "SCONOSCIUTO")


def verifica_vincoli_intervento_generico(
    tipo_intervento_app: str,
    tipo_soggetto: str,
    categoria_catastale: str,
    tipo_pdc: str = None,
    riduzione_energia_primaria_effettiva: float = 0.0,
    ape_disponibili: bool = False,
    multi_intervento: bool = False,
    interventi_combinati: list[str] = None
) -> VincoliTerziario:
    """
    Wrapper semplificato per verificare vincoli terziario per qualsiasi intervento.

    Args:
        tipo_intervento_app: Nome tipo intervento nell'app (es. "serramenti", "isolamento_termico")
        tipo_soggetto: Tipologia soggetto
        categoria_catastale: Categoria catastale edificio
        tipo_pdc: Tipo PDC solo per pompe di calore
        riduzione_energia_primaria_effettiva: Riduzione da APE
        ape_disponibili: APE ante/post disponibili
        multi_intervento: Se multi-intervento
        interventi_combinati: Lista interventi combinati

    Returns:
        VincoliTerziario con risultati verifica
    """
    codice_intervento = get_codice_intervento(tipo_intervento_app)

    return verifica_vincoli_terziario(
        tipo_soggetto=tipo_soggetto,
        categoria_catastale=categoria_catastale,
        codice_intervento=codice_intervento,
        tipo_pdc=tipo_pdc,
        multi_intervento=multi_intervento,
        interventi_combinati=interventi_combinati,
        riduzione_energia_primaria_effettiva=riduzione_energia_primaria_effettiva,
        ape_disponibili=ape_disponibili
    )
