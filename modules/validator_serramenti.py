"""
Modulo di validazione requisiti per Sostituzione Serramenti CT 3.0 (II.B).

Verifica conformità secondo DM 7/8/2025 - Regole Applicative CT 3.0
Paragrafo 9.2 - Sostituzione chiusure trasparenti comprensive di infissi

Autore: EnergyIncentiveManager
Versione: 1.0.0
"""

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class RisultatoValidazione(NamedTuple):
    ammissibile: bool
    punteggio: float
    errori_bloccanti: list[str]
    warning: list[str]
    suggerimenti: list[str]


def valida_requisiti_serramenti(
    zona_climatica: str = "E",
    trasmittanza_post_operam: float = None,
    superficie_mq: float = 0.0,
    ha_termoregolazione: bool = True,
    ha_ape_post_operam: bool = None,
    potenza_impianto_kw: float = 0.0,
    # Parametri alternativi per retrocompatibilità
    trasmittanza_post: float = None,
    ha_ape_post: bool = None,
    ha_valvole_termostatiche: bool = None
) -> dict:
    """
    Valida i requisiti tecnici per la sostituzione serramenti (II.B).

    Requisiti principali (Par. 9.2.1):
    - Trasmittanza entro limiti normativi (Tabella 16)
    - Sistemi termoregolazione o valvole termostatiche (obbligatori)
    - APE post-operam obbligatorio per edifici ≥200 kW
    - Diagnosi energetica per edifici ≥200 kW

    Args:
        zona_climatica: Zona climatica A-F
        trasmittanza_post_operam: Trasmittanza post-intervento (W/m²K)
        superficie_mq: Superficie serramenti (m²)
        ha_termoregolazione: Presenza sistemi termoregolazione/valvole
        ha_ape_post_operam: APE post-operam disponibile
        potenza_impianto_kw: Potenza impianto riscaldamento

    Returns:
        dict con ammissibilità, punteggio, errori, warning e suggerimenti
    """

    # Gestione compatibilità nomi parametri
    trasm = trasmittanza_post_operam or trasmittanza_post or 0.0
    termoreg = ha_termoregolazione or ha_valvole_termostatiche or False
    ape = ha_ape_post_operam if ha_ape_post_operam is not None else (
        ha_ape_post if ha_ape_post is not None else (potenza_impianto_kw >= 200)
    )

    errori = []
    warnings = []
    suggerimenti = []
    punteggio = 0.0

    # Limiti trasmittanza (Tabella 16 - DM 7/8/2025)
    LIMITI_TRASMITTANZA = {
        "A": 2.60,
        "B": 2.60,
        "C": 1.75,
        "D": 1.67,
        "E": 1.30,
        "F": 1.00
    }

    # Requisiti tecnici base
    if superficie_mq <= 0:
        errori.append("Superficie deve essere > 0 m²")
    else:
        punteggio += 20

    if trasm <= 0:
        errori.append("Trasmittanza deve essere > 0 W/m²K")
    else:
        punteggio += 20

    # Verifica trasmittanza rispetto ai limiti
    limite = LIMITI_TRASMITTANZA.get(zona_climatica, 1.30)
    if trasm > 0 and trasm > limite:
        errori.append(
            f"Trasmittanza {trasm:.2f} W/m²K supera il limite {limite:.2f} W/m²K per zona {zona_climatica}"
        )
    elif trasm > 0:
        punteggio += 30

    # Requisiti obbligatori - Termoregolazione
    if not termoreg:
        errori.append(
            "Sistemi termoregolazione o valvole termostatiche OBBLIGATORI "
            "(devono essere installati o già presenti)"
        )
    else:
        punteggio += 20

    # APE post-operam obbligatorio per impianti ≥200 kW
    if potenza_impianto_kw >= 200 and not ape:
        errori.append(
            f"APE post-operam OBBLIGATORIO per impianti ≥200 kW (potenza: {potenza_impianto_kw:.0f} kW)"
        )
    elif potenza_impianto_kw >= 200 and ape:
        punteggio += 10

    # Suggerimenti
    if potenza_impianto_kw >= 200:
        suggerimenti.append(
            "Edifici ≥200 kW richiedono anche diagnosi energetica ante-operam"
        )

    if zona_climatica in ["E", "F"]:
        suggerimenti.append(
            f"Zone {zona_climatica}: limiti trasmittanza più stringenti (≤{limite:.2f} W/m²K)"
        )

    if trasm > 0 and trasm <= limite * 0.8:
        suggerimenti.append(
            f"Ottimo! Trasmittanza {trasm:.2f} W/m²K è ben al di sotto del limite ({limite:.2f} W/m²K)"
        )

    ammissibile = len(errori) == 0

    return {
        "ammissibile": ammissibile,
        "punteggio": punteggio if ammissibile else 0.0,
        "errori": errori,
        "warnings": warnings,
        "suggerimenti": suggerimenti
    }


# Alias per compatibilità con nomi inglesi
validate_windows_requirements = valida_requisiti_serramenti


if __name__ == "__main__":
    # Test validazione
    print("\n" + "="*70)
    print("TEST VALIDAZIONE SERRAMENTI")
    print("="*70)

    # Test 1: Caso valido zona E
    print("\nTest 1: Zona E, trasmittanza 1.20 W/m²K")
    result = valida_requisiti_serramenti(
        zona_climatica="E",
        trasmittanza_post_operam=1.20,
        superficie_mq=50.0,
        ha_termoregolazione=True,
        potenza_impianto_kw=150
    )
    print(f"  Ammissibile: {result['ammissibile']}")
    print(f"  Punteggio: {result['punteggio']}")
    print(f"  Errori: {result['errori']}")
    print(f"  Suggerimenti: {result['suggerimenti']}")

    # Test 2: Trasmittanza troppo alta
    print("\nTest 2: Zona E, trasmittanza 1.50 W/m²K (troppo alta)")
    result = valida_requisiti_serramenti(
        zona_climatica="E",
        trasmittanza_post_operam=1.50,
        superficie_mq=50.0,
        ha_termoregolazione=True
    )
    print(f"  Ammissibile: {result['ammissibile']}")
    print(f"  Errori: {result['errori']}")

    # Test 3: Mancano valvole termostatiche
    print("\nTest 3: Senza termoregolazione")
    result = valida_requisiti_serramenti(
        zona_climatica="E",
        trasmittanza_post_operam=1.20,
        superficie_mq=50.0,
        ha_termoregolazione=False
    )
    print(f"  Ammissibile: {result['ammissibile']}")
    print(f"  Errori: {result['errori']}")

    print("\n" + "="*70)
