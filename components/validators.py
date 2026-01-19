"""
Modulo per validazione input utente.

Previene errori comuni e fornisce messaggi di errore chiari.
"""

from typing import Tuple, Optional
from datetime import datetime, date


class ValidationError(Exception):
    """Eccezione per errori di validazione input."""
    pass


def validate_superficie(
    superficie: float,
    min_value: float = 0.1,
    max_value: float = 100000.0,
    campo: str = "Superficie"
) -> Tuple[bool, Optional[str]]:
    """
    Valida input superficie.

    Args:
        superficie: Valore superficie da validare (m²)
        min_value: Valore minimo accettabile
        max_value: Valore massimo accettabile
        campo: Nome campo per messaggio errore

    Returns:
        (valido, messaggio_errore)
    """
    if superficie <= 0:
        return False, f"❌ {campo} deve essere maggiore di zero"

    if superficie < min_value:
        return False, f"⚠️ {campo} troppo piccola (minimo: {min_value} m²)"

    if superficie > max_value:
        return False, f"⚠️ {campo} eccessiva (massimo: {max_value} m²). Verificare valore."

    # Warning per valori sospetti
    if superficie > 10000:
        return True, f"⚠️ ATTENZIONE: {campo} molto grande ({superficie:,.0f} m²). Confermare il valore."

    return True, None


def validate_potenza(
    potenza: float,
    min_value: float = 0.5,
    max_value: float = 2000.0,
    campo: str = "Potenza",
    unita: str = "kW"
) -> Tuple[bool, Optional[str]]:
    """
    Valida input potenza.

    Args:
        potenza: Valore potenza da validare
        min_value: Valore minimo accettabile
        max_value: Valore massimo accettabile
        campo: Nome campo per messaggio errore
        unita: Unità di misura

    Returns:
        (valido, messaggio_errore)
    """
    if potenza <= 0:
        return False, f"❌ {campo} deve essere maggiore di zero"

    if potenza < min_value:
        return False, f"⚠️ {campo} troppo bassa (minimo: {min_value} {unita})"

    if potenza > max_value:
        return False, f"⚠️ {campo} eccessiva (massimo: {max_value} {unita}). Verificare valore."

    # Warning specifici per range
    if potenza > 500 and max_value > 500:
        return True, f"⚠️ ATTENZIONE: {campo} elevata ({potenza} {unita}). Verificare categoria generatore."

    return True, None


def validate_percentuale(
    valore: float,
    min_value: float = 0.0,
    max_value: float = 100.0,
    campo: str = "Percentuale"
) -> Tuple[bool, Optional[str]]:
    """
    Valida input percentuale.

    Args:
        valore: Valore percentuale da validare
        min_value: Valore minimo accettabile
        max_value: Valore massimo accettabile
        campo: Nome campo per messaggio errore

    Returns:
        (valido, messaggio_errore)
    """
    if valore < min_value:
        return False, f"❌ {campo} non può essere inferiore a {min_value}%"

    if valore > max_value:
        return False, f"❌ {campo} non può essere superiore a {max_value}%"

    return True, None


def validate_data(
    data_input: date | datetime | str,
    data_minima: Optional[date] = None,
    data_massima: Optional[date] = None,
    campo: str = "Data"
) -> Tuple[bool, Optional[str]]:
    """
    Valida input data.

    Args:
        data_input: Data da validare
        data_minima: Data minima accettabile (opzionale)
        data_massima: Data massima accettabile (opzionale)
        campo: Nome campo per messaggio errore

    Returns:
        (valido, messaggio_errore)
    """
    # Converti a date se datetime
    if isinstance(data_input, datetime):
        data = data_input.date()
    elif isinstance(data_input, str):
        try:
            data = datetime.strptime(data_input, "%Y-%m-%d").date()
        except ValueError:
            return False, f"❌ {campo} non valida. Formato richiesto: YYYY-MM-DD"
    else:
        data = data_input

    # Verifica range
    if data_minima and data < data_minima:
        return False, f"❌ {campo} non può essere anteriore a {data_minima.strftime('%d/%m/%Y')}"

    if data_massima and data > data_massima:
        return False, f"❌ {campo} non può essere posteriore a {data_massima.strftime('%d/%m/%Y')}"

    # Warning per date future lontane
    oggi = date.today()
    if data > oggi:
        giorni_futuro = (data - oggi).days
        if giorni_futuro > 730:  # > 2 anni
            return True, f"⚠️ ATTENZIONE: {campo} oltre 2 anni nel futuro. Verificare."

    return True, None


def validate_range_prezzi(
    prezzo_unitario: float,
    quantita: float,
    prezzo_totale: float,
    tolleranza: float = 0.01
) -> Tuple[bool, Optional[str]]:
    """
    Valida coerenza tra prezzo unitario, quantità e prezzo totale.

    Args:
        prezzo_unitario: Prezzo per unità (€)
        quantita: Quantità
        prezzo_totale: Prezzo totale dichiarato (€)
        tolleranza: Tolleranza percentuale per arrotondamenti

    Returns:
        (valido, messaggio_errore)
    """
    calcolato = prezzo_unitario * quantita
    differenza_pct = abs(calcolato - prezzo_totale) / calcolato if calcolato > 0 else 0

    if differenza_pct > tolleranza:
        return False, f"❌ INCOERENZA: Prezzo unitario × quantità = {calcolato:,.2f} € ≠ Totale dichiarato {prezzo_totale:,.2f} €"

    return True, None


def validate_cop_eer(
    valore: float,
    tipo: str = "COP",  # "COP" o "EER"
    min_value: float = 1.0,
    max_value: float = 7.0
) -> Tuple[bool, Optional[str]]:
    """
    Valida coefficiente COP o EER.

    Args:
        valore: Valore COP/EER
        tipo: "COP" o "EER"
        min_value: Valore minimo accettabile
        max_value: Valore massimo accettabile

    Returns:
        (valido, messaggio_errore)
    """
    if valore < min_value:
        return False, f"❌ {tipo} troppo basso (minimo: {min_value})"

    if valore > max_value:
        return False, f"⚠️ {tipo} molto elevato ({valore}). Valori tipici: {min_value}-{max_value}. Verificare scheda tecnica."

    return True, None


def validate_temperatura(
    temperatura: float,
    min_value: float = -30.0,
    max_value: float = 100.0,
    campo: str = "Temperatura"
) -> Tuple[bool, Optional[str]]:
    """
    Valida temperatura.

    Args:
        temperatura: Valore temperatura (°C)
        min_value: Temperatura minima
        max_value: Temperatura massima
        campo: Nome campo

    Returns:
        (valido, messaggio_errore)
    """
    if temperatura < min_value:
        return False, f"❌ {campo} troppo bassa (minimo: {min_value}°C)"

    if temperatura > max_value:
        return False, f"❌ {campo} troppo alta (massimo: {max_value}°C)"

    return True, None
