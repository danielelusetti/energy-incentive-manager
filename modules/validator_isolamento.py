"""
Modulo di validazione requisiti per Isolamento Termico CT 3.0 (II.A).

Verifica conformità secondo DM 7/8/2025 - Regole Applicative CT 3.0
Paragrafo 9.1 - Isolamento termico superfici opache

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Tabella 14 - Valori limite massimi di trasmittanza termica [W/m²K]
# Paragrafo 9.1.1 DM 7/8/2025
TRASMITTANZA_LIMITI = {
    "coperture": {
        "A": 0.27, "B": 0.27, "C": 0.27, "D": 0.22, "E": 0.20, "F": 0.19
    },
    "pavimenti": {
        "A": 0.40, "B": 0.40, "C": 0.30, "D": 0.28, "E": 0.25, "F": 0.23
    },
    "pareti": {
        "A": 0.38, "B": 0.38, "C": 0.30, "D": 0.26, "E": 0.23, "F": 0.22
    }
}


class RisultatoValidazione(NamedTuple):
    ammissibile: bool
    punteggio: float
    errori_bloccanti: list[str]
    warning: list[str]
    suggerimenti: list[str]


def valida_requisiti_isolamento(
    tipo_superficie: str,
    posizione_isolamento: str = None,
    zona_climatica: str = "E",
    trasmittanza_post_operam: float = None,
    superficie_mq: float = 0.0,
    ha_diagnosi_energetica: bool = True,
    ha_ape_post_operam: bool = None,
    edificio_ante_1993: bool = False,
    # Parametri alternativi per retrocompatibilità
    posizione: str = None,
    trasmittanza_post: float = None,
    ha_ape_post: bool = None
) -> dict:
    """
    Valida i requisiti tecnici per l'isolamento termico (II.A).

    Requisiti principali:
    - Trasmittanza entro limiti normativi
    - Diagnosi energetica obbligatoria
    - APE post-operam obbligatorio
    - Analisi ponti termici richiesta
    """

    # Gestione compatibilità nomi parametri
    pos = posizione_isolamento or posizione or "esterno"
    trasm = trasmittanza_post_operam or trasmittanza_post or 0.0
    ape = ha_ape_post_operam if ha_ape_post_operam is not None else (ha_ape_post if ha_ape_post is not None else True)

    errori = []
    warnings = []
    suggerimenti = []
    punteggio = 0.0

    # Requisiti tecnici base
    if superficie_mq <= 0:
        errori.append("Superficie deve essere > 0 m²")
    else:
        punteggio += 20

    if trasm <= 0:
        errori.append("Trasmittanza deve essere > 0 W/m²K")
    else:
        # Verifica limiti trasmittanza (Tabella 14)
        if tipo_superficie in TRASMITTANZA_LIMITI and zona_climatica in TRASMITTANZA_LIMITI.get(tipo_superficie, {}):
            limite_base = TRASMITTANZA_LIMITI[tipo_superficie][zona_climatica]
            # Incremento del 30% per isolamento interno
            if pos == "interno":
                limite = limite_base * 1.30
                tipo_limite = "interno (+30%)"
            else:
                limite = limite_base
                tipo_limite = "esterno"

            if trasm > limite:
                errori.append(f"Trasmittanza {trasm:.3f} W/m²K supera il limite {tipo_limite} di {limite:.3f} W/m²K per zona {zona_climatica}")
            else:
                punteggio += 20
        else:
            punteggio += 20  # Se tipo non riconosciuto, passa comunque

    # Documentazione obbligatoria
    if not ha_diagnosi_energetica:
        errori.append("Diagnosi energetica OBBLIGATORIA (con analisi ponti termici)")
    else:
        punteggio += 30

    if not ape:
        errori.append("APE post-operam OBBLIGATORIO")
    else:
        punteggio += 30

    # Suggerimenti
    if edificio_ante_1993:
        suggerimenti.append("Per edifici ante-1993: possibile ridurre EPgl del 50% invece di rispettare i limiti di trasmittanza")

    if pos == "interno":
        warnings.append("Isolamento interno: limiti trasmittanza incrementati del 30%")
        suggerimenti.append("Verificare rischio condensa interstiziale (UNI EN ISO 13788)")

    ammissibile = len(errori) == 0

    return {
        "ammissibile": ammissibile,
        "punteggio": punteggio if ammissibile else 0.0,
        "errori": errori,
        "warnings": warnings,
        "suggerimenti": suggerimenti
    }


# Alias per compatibilità con nomi inglesi
validate_insulation_requirements = valida_requisiti_isolamento
