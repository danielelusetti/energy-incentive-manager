"""
Componenti UI riutilizzabili per l'applicazione Conto Termico.

Questo modulo contiene componenti Streamlit riutilizzabili per ridurre
duplicazione di codice e migliorare manutenibilità.
"""

from .ui_components import (
    render_risultato_incentivo,
    render_warning_vincoli,
    render_storico_calcoli,
    format_currency,
    format_percentage,
    render_card_info,
    render_progress_bar,
    render_alert_normativa
)

from .validators import (
    validate_superficie,
    validate_potenza,
    validate_percentuale,
    validate_data,
    validate_cop_eer,
    validate_temperatura,
    validate_range_prezzi,
    ValidationError
)

__all__ = [
    # UI Components
    'render_risultato_incentivo',
    'render_warning_vincoli',
    'render_storico_calcoli',
    'format_currency',
    'format_percentage',
    'render_card_info',
    'render_progress_bar',
    'render_alert_normativa',

    # Validators
    'validate_superficie',
    'validate_potenza',
    'validate_percentuale',
    'validate_data',
    'validate_cop_eer',
    'validate_temperatura',
    'validate_range_prezzi',
    'ValidationError'
]
