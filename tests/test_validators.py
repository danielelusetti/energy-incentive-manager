"""
Test per modulo validators.py

Testa validazione input utente.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import date, datetime, timedelta
from components.validators import (
    validate_superficie,
    validate_potenza,
    validate_percentuale,
    validate_data,
    validate_cop_eer,
    validate_temperatura,
    ValidationError
)


class TestValidazioneSuperficie:
    """Test validazione superficie."""

    def test_superficie_valida(self):
        """Superficie normale valida."""
        valido, msg = validate_superficie(100.0)
        assert valido is True
        assert msg is None

    def test_superficie_zero(self):
        """Superficie zero non valida."""
        valido, msg = validate_superficie(0.0)
        assert valido is False
        assert "maggiore di zero" in msg

    def test_superficie_negativa(self):
        """Superficie negativa non valida."""
        valido, msg = validate_superficie(-10.0)
        assert valido is False

    def test_superficie_troppo_piccola(self):
        """Superficie sotto minimo."""
        valido, msg = validate_superficie(0.05, min_value=0.1)
        assert valido is False
        assert "troppo piccola" in msg

    def test_superficie_troppo_grande(self):
        """Superficie sopra massimo."""
        valido, msg = validate_superficie(150000, max_value=100000)
        assert valido is False
        assert "eccessiva" in msg

    def test_superficie_warning_grande(self):
        """Superficie molto grande genera warning."""
        valido, msg = validate_superficie(15000)
        assert valido is True
        assert msg is not None
        assert "ATTENZIONE" in msg


class TestValidazionePotenza:
    """Test validazione potenza."""

    def test_potenza_valida(self):
        """Potenza normale valida."""
        valido, msg = validate_potenza(25.0)
        assert valido is True
        assert msg is None

    def test_potenza_zero(self):
        """Potenza zero non valida."""
        valido, msg = validate_potenza(0.0)
        assert valido is False

    def test_potenza_sotto_minimo(self):
        """Potenza sotto minimo."""
        valido, msg = validate_potenza(0.3, min_value=0.5)
        assert valido is False
        assert "troppo bassa" in msg

    def test_potenza_sopra_massimo(self):
        """Potenza sopra massimo."""
        valido, msg = validate_potenza(2500, max_value=2000)
        assert valido is False
        assert "eccessiva" in msg

    def test_potenza_elevata_warning(self):
        """Potenza elevata genera warning."""
        valido, msg = validate_potenza(600, max_value=2000)
        assert valido is True
        assert "ATTENZIONE" in msg


class TestValidazionePercentuale:
    """Test validazione percentuale."""

    def test_percentuale_valida(self):
        """Percentuale valida."""
        valido, msg = validate_percentuale(50.0)
        assert valido is True
        assert msg is None

    def test_percentuale_0(self):
        """0% valido."""
        valido, msg = validate_percentuale(0.0)
        assert valido is True

    def test_percentuale_100(self):
        """100% valido."""
        valido, msg = validate_percentuale(100.0)
        assert valido is True

    def test_percentuale_negativa(self):
        """Percentuale negativa non valida."""
        valido, msg = validate_percentuale(-5.0)
        assert valido is False

    def test_percentuale_sopra_100(self):
        """Percentuale > 100% non valida."""
        valido, msg = validate_percentuale(105.0)
        assert valido is False


class TestValidazioneData:
    """Test validazione data."""

    def test_data_valida(self):
        """Data valida."""
        oggi = date.today()
        valido, msg = validate_data(oggi)
        assert valido is True
        assert msg is None

    def test_data_stringa_valida(self):
        """Data formato stringa valida."""
        valido, msg = validate_data("2025-06-15")
        assert valido is True

    def test_data_stringa_formato_errato(self):
        """Data formato stringa errato."""
        valido, msg = validate_data("15/06/2025")
        assert valido is False
        assert "Formato richiesto" in msg

    def test_data_minima(self):
        """Data rispetta minimo."""
        data_min = date(2025, 1, 1)
        data_test = date(2025, 6, 1)

        valido, msg = validate_data(data_test, data_minima=data_min)
        assert valido is True

    def test_data_sotto_minimo(self):
        """Data sotto minimo."""
        data_min = date(2025, 1, 1)
        data_test = date(2024, 12, 31)

        valido, msg = validate_data(data_test, data_minima=data_min)
        assert valido is False
        assert "non può essere anteriore" in msg

    def test_data_massima(self):
        """Data rispetta massimo."""
        data_max = date(2026, 12, 31)
        data_test = date(2026, 6, 1)

        valido, msg = validate_data(data_test, data_massima=data_max)
        assert valido is True

    def test_data_oltre_massimo(self):
        """Data oltre massimo."""
        data_max = date(2026, 12, 31)
        data_test = date(2027, 1, 1)

        valido, msg = validate_data(data_test, data_massima=data_max)
        assert valido is False

    def test_data_futuro_lontano_warning(self):
        """Data molto futura genera warning."""
        oggi = date.today()
        data_futura = oggi + timedelta(days=1000)

        valido, msg = validate_data(data_futura)
        assert valido is True
        assert msg is not None
        assert "ATTENZIONE" in msg


class TestValidazioneCOPEER:
    """Test validazione COP/EER."""

    def test_cop_valido(self):
        """COP valido."""
        valido, msg = validate_cop_eer(4.5, tipo="COP")
        assert valido is True
        assert msg is None

    def test_cop_troppo_basso(self):
        """COP troppo basso."""
        valido, msg = validate_cop_eer(0.8, tipo="COP", min_value=1.0)
        assert valido is False

    def test_cop_troppo_alto_warning(self):
        """COP molto alto genera warning."""
        valido, msg = validate_cop_eer(8.5, tipo="COP", max_value=7.0)
        assert valido is False
        assert "molto elevato" in msg

    def test_eer_valido(self):
        """EER valido."""
        valido, msg = validate_cop_eer(3.2, tipo="EER")
        assert valido is True


class TestValidazioneTemperatura:
    """Test validazione temperatura."""

    def test_temperatura_valida(self):
        """Temperatura normale."""
        valido, msg = validate_temperatura(20.0)
        assert valido is True

    def test_temperatura_troppo_bassa(self):
        """Temperatura sotto minimo."""
        valido, msg = validate_temperatura(-50.0, min_value=-30.0)
        assert valido is False

    def test_temperatura_troppo_alta(self):
        """Temperatura sopra massimo."""
        valido, msg = validate_temperatura(150.0, max_value=100.0)
        assert valido is False

    def test_temperatura_limite_inferiore(self):
        """Temperatura = minimo OK."""
        valido, msg = validate_temperatura(-30.0, min_value=-30.0)
        assert valido is True

    def test_temperatura_limite_superiore(self):
        """Temperatura = massimo OK."""
        valido, msg = validate_temperatura(100.0, max_value=100.0)
        assert valido is True


# ===== Esecuzione Test =====
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
