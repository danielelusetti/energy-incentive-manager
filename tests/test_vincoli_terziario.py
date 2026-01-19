"""
Test per modulo vincoli_terziario.py

Testa tutti i vincoli CT 3.0 per edifici terziario con imprese/ETS economici.
"""

import sys
from pathlib import Path

# Aggiungi parent directory al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules.vincoli_terziario import (
    is_terziario,
    calcola_riduzione_richiesta,
    verifica_vincoli_terziario,
    get_codice_intervento,
    verifica_vincoli_intervento_generico,
    CATEGORIE_CATASTALI_TERZIARIO,
    CATEGORIE_CATASTALI_RESIDENZIALE
)


class TestCategorieEdifici:
    """Test classificazione categorie catastali."""

    def test_categoria_terziario_valide(self):
        """Verifica categorie terziario riconosciute."""
        assert is_terziario("C/1") is True
        assert is_terziario("D/3") is True
        assert is_terziario("B/5") is True
        assert is_terziario("E/1") is True

    def test_categoria_residenziale(self):
        """Verifica categorie residenziali non siano terziario."""
        assert is_terziario("A/1") is False
        assert is_terziario("A/3") is False
        assert is_terziario("A/7") is False

    def test_categoria_non_valida(self):
        """Verifica categorie inesistenti."""
        assert is_terziario("Z/99") is False
        assert is_terziario("") is False


class TestRiduzioneEnergiaPrimaria:
    """Test calcolo riduzione energia primaria richiesta."""

    def test_riduzione_10pct_singolo(self):
        """Interventi II.B, II.E, II.F singoli: 10%."""
        assert calcola_riduzione_richiesta("II.B", False) == 0.10
        assert calcola_riduzione_richiesta("II.E", False) == 0.10
        assert calcola_riduzione_richiesta("II.F", False) == 0.10

    def test_riduzione_20pct_multi(self):
        """Interventi II.B+altro, II.E+altro, II.F+altro: 20%."""
        assert calcola_riduzione_richiesta("II.B", True, ["II.B", "II.D"]) == 0.20
        assert calcola_riduzione_richiesta("II.E", True, ["II.E", "II.H"]) == 0.20

    def test_riduzione_20pct_sempre(self):
        """Interventi II.D, II.G, II.H: sempre 20%."""
        assert calcola_riduzione_richiesta("II.D", False) == 0.20
        assert calcola_riduzione_richiesta("II.G", False) == 0.20
        assert calcola_riduzione_richiesta("II.H", False) == 0.20

    def test_riduzione_nulla_titolo_iii(self):
        """Interventi Titolo III: no riduzione obbligatoria."""
        assert calcola_riduzione_richiesta("III.A", False) == 0.0
        assert calcola_riduzione_richiesta("III.C", False) == 0.0


class TestVincoliPdCGas:
    """Test vincolo PDC a gas per imprese su terziario."""

    def test_pdc_gas_bloccata_impresa_terziario(self):
        """Impresa su terziario: PDC gas NON ammessa."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            codice_intervento="III.A",
            tipo_pdc="gas",
            ape_disponibili=False
        )

        assert risultato["vincolo_soddisfatto"] is False
        assert risultato["pdc_gas_ammessa"] is False
        assert "Art. 25, comma 2" in risultato["messaggio"]

    def test_pdc_gas_bloccata_ets_economico_terziario(self):
        """ETS economico su terziario: PDC gas NON ammessa."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="ETS_economico",
            categoria_catastale="D/3",
            codice_intervento="III.A",
            tipo_pdc="gas"
        )

        assert risultato["vincolo_soddisfatto"] is False
        assert risultato["pdc_gas_ammessa"] is False

    def test_pdc_elettrica_ok_impresa_terziario(self):
        """Impresa su terziario: PDC elettrica OK."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            codice_intervento="III.A",
            tipo_pdc="elettrica"
        )

        assert risultato["vincolo_soddisfatto"] is True
        assert risultato["pdc_gas_ammessa"] is True

    def test_pdc_gas_ok_privato_residenziale(self):
        """Privato su residenziale: PDC gas OK."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Privato",
            categoria_catastale="A/3",
            codice_intervento="III.A",
            tipo_pdc="gas"
        )

        assert risultato["vincolo_soddisfatto"] is True
        assert risultato["pdc_gas_ammessa"] is True


class TestVincoliRiduzioneAPE:
    """Test vincoli riduzione energia primaria con APE."""

    def test_serramenti_10pct_senza_ape(self):
        """Serramenti singoli su terziario impresa: richiede APE."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            codice_intervento="II.B",
            ape_disponibili=False
        )

        assert risultato["vincolo_soddisfatto"] is False
        assert risultato["richiede_ape"] is True
        assert "10%" in risultato["messaggio"]

    def test_serramenti_10pct_con_ape_sufficiente(self):
        """Serramenti: APE con riduzione 12% >= 10% richiesto."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            codice_intervento="II.B",
            riduzione_energia_primaria_effettiva=0.12,
            ape_disponibili=True
        )

        assert risultato["vincolo_soddisfatto"] is True
        assert risultato["riduzione_energia_primaria_richiesta"] == 0.10

    def test_serramenti_10pct_con_ape_insufficiente(self):
        """Serramenti: APE con riduzione 8% < 10% richiesto."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            codice_intervento="II.B",
            riduzione_energia_primaria_effettiva=0.08,
            ape_disponibili=True
        )

        assert risultato["vincolo_soddisfatto"] is False
        assert "8.0% < 10%" in risultato["messaggio"]

    def test_building_automation_20pct(self):
        """Building automation: sempre 20%."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Impresa",
            categoria_catastale="D/5",
            codice_intervento="II.D",
            riduzione_energia_primaria_effettiva=0.22,
            ape_disponibili=True
        )

        assert risultato["vincolo_soddisfatto"] is True
        assert risultato["riduzione_energia_primaria_richiesta"] == 0.20


class TestSoggettiNonVincolati:
    """Test che soggetti non vincolati passino sempre."""

    def test_pa_non_vincolato(self):
        """PA: no vincoli terziario."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="PA",
            categoria_catastale="D/3",
            codice_intervento="II.B"
        )

        assert risultato["vincolo_soddisfatto"] is True
        assert "Nessun vincolo" in risultato["messaggio"]

    def test_ets_non_economico_non_vincolato(self):
        """ETS non economico: no vincoli."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="ETS_non_economico",
            categoria_catastale="C/1",
            codice_intervento="II.B"
        )

        assert risultato["vincolo_soddisfatto"] is True

    def test_privato_residenziale_non_vincolato(self):
        """Privato su residenziale: no vincoli."""
        risultato = verifica_vincoli_terziario(
            tipo_soggetto="Privato",
            categoria_catastale="A/3",
            codice_intervento="II.B"
        )

        assert risultato["vincolo_soddisfatto"] is True


class TestMappaturaCodiciIntervento:
    """Test mappatura nomi interventi -> codici CT."""

    def test_codici_pdc(self):
        """Verifica mappatura PDC."""
        assert get_codice_intervento("pompe_di_calore") == "III.A"
        assert get_codice_intervento("pdc") == "III.A"

    def test_codici_serramenti(self):
        """Verifica mappatura serramenti."""
        assert get_codice_intervento("serramenti") == "II.B"
        assert get_codice_intervento("finestre") == "II.B"

    def test_codici_isolamento(self):
        """Verifica mappatura isolamento."""
        assert get_codice_intervento("isolamento_termico") == "II.E"
        assert get_codice_intervento("isolamento_copertura") == "II.F"
        assert get_codice_intervento("isolamento_pavimento") == "II.F"

    def test_codice_sconosciuto(self):
        """Verifica gestione codici non mappati."""
        assert get_codice_intervento("xyz_non_esiste") == "SCONOSCIUTO"


class TestWrapperGenerico:
    """Test wrapper verifica_vincoli_intervento_generico."""

    def test_wrapper_serramenti(self):
        """Wrapper con nome app 'serramenti'."""
        risultato = verifica_vincoli_intervento_generico(
            tipo_intervento_app="serramenti",
            tipo_soggetto="Impresa",
            categoria_catastale="C/1",
            riduzione_energia_primaria_effettiva=0.15,
            ape_disponibili=True
        )

        assert risultato["vincolo_soddisfatto"] is True

    def test_wrapper_pdc_gas(self):
        """Wrapper PDC gas bloccato."""
        risultato = verifica_vincoli_intervento_generico(
            tipo_intervento_app="pompe_di_calore",
            tipo_soggetto="Impresa",
            categoria_catastale="D/1",
            tipo_pdc="gas"
        )

        assert risultato["vincolo_soddisfatto"] is False


# ===== Esecuzione Test =====
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
