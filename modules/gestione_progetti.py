"""
Modulo per gestione progetti clienti - Analisi di fattibilità Conto Termico.

Permette di:
- Salvare analisi per cliente su file JSON persistenti
- Caricare progetti esistenti
- Modificare progetti salvati
- Confrontare scenari multipli per stesso cliente
- Esportare analisi complete

Versione: 1.0.0
Data: 2026-01-19
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re


class GestioneProgetti:
    """Gestisce salvataggio e caricamento progetti clienti."""

    def __init__(self, base_dir: str = "data/progetti"):
        """
        Inizializza gestore progetti.

        Args:
            base_dir: Directory base per salvataggio progetti
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, nome: str) -> str:
        """
        Sanitizza nome per uso come filename.

        Args:
            nome: Nome cliente/progetto

        Returns:
            Nome sanitizzato safe per filesystem
        """
        # Rimuovi caratteri non validi
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', nome)
        # Rimuovi spazi multipli
        safe_name = re.sub(r'\s+', '_', safe_name)
        # Limita lunghezza
        safe_name = safe_name[:100]
        return safe_name.lower()

    def _get_project_path(self, nome_cliente: str, progetto_id: Optional[str] = None) -> Path:
        """
        Ottiene path file progetto.

        Args:
            nome_cliente: Nome cliente
            progetto_id: ID progetto (timestamp se None)

        Returns:
            Path file progetto
        """
        safe_cliente = self._sanitize_filename(nome_cliente)

        if progetto_id is None:
            progetto_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{safe_cliente}_{progetto_id}.json"
        return self.base_dir / filename

    def salva_progetto(
        self,
        nome_cliente: str,
        tipo_intervento: str,
        risultato_calcolo: Dict[str, Any],
        dati_input: Dict[str, Any],
        note: str = "",
        progetto_id: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Salva progetto su file.

        Args:
            nome_cliente: Nome cliente/progetto
            tipo_intervento: Tipo intervento (es. "Pompe di Calore")
            risultato_calcolo: Risultato calcolo incentivo
            dati_input: Dati input usati per calcolo
            note: Note aggiuntive
            progetto_id: ID progetto (se None, crea nuovo)

        Returns:
            (successo, messaggio, progetto_id)
        """
        try:
            if not nome_cliente or not nome_cliente.strip():
                return False, "Nome cliente obbligatorio", ""

            # Genera progetto_id se nuovo
            if progetto_id is None:
                progetto_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Prepara dati progetto
            progetto = {
                "versione": "1.0.0",
                "nome_cliente": nome_cliente.strip(),
                "progetto_id": progetto_id,
                "data_creazione": datetime.now().isoformat(),
                "data_ultima_modifica": datetime.now().isoformat(),
                "tipo_intervento": tipo_intervento,
                "risultato_calcolo": risultato_calcolo,
                "dati_input": dati_input,
                "note": note,
                "storico_modifiche": [
                    {
                        "data": datetime.now().isoformat(),
                        "azione": "creazione" if progetto_id == datetime.now().strftime("%Y%m%d_%H%M%S") else "modifica",
                        "utente": os.getlogin() if hasattr(os, 'getlogin') else "unknown"
                    }
                ]
            }

            # Salva su file
            filepath = self._get_project_path(nome_cliente, progetto_id)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(progetto, f, indent=2, ensure_ascii=False)

            return True, f"Progetto salvato: {filepath.name}", progetto_id

        except Exception as e:
            return False, f"Errore salvataggio: {str(e)}", ""

    def carica_progetto(self, filepath: Path) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Carica progetto da file.

        Args:
            filepath: Path file progetto

        Returns:
            (successo, dati_progetto, messaggio)
        """
        try:
            if not filepath.exists():
                return False, None, f"File non trovato: {filepath}"

            with open(filepath, 'r', encoding='utf-8') as f:
                progetto = json.load(f)

            return True, progetto, "Progetto caricato con successo"

        except json.JSONDecodeError as e:
            return False, None, f"Errore formato JSON: {str(e)}"
        except Exception as e:
            return False, None, f"Errore caricamento: {str(e)}"

    def lista_progetti(self, nome_cliente: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista progetti salvati.

        Args:
            nome_cliente: Filtra per nome cliente (opzionale)

        Returns:
            Lista progetti con metadati
        """
        progetti = []

        try:
            # Cerca tutti i file JSON
            pattern = "*.json"
            if nome_cliente:
                safe_cliente = self._sanitize_filename(nome_cliente)
                pattern = f"{safe_cliente}_*.json"

            for filepath in self.base_dir.glob(pattern):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        progetto = json.load(f)

                    # Estrai metadati
                    progetti.append({
                        "filepath": str(filepath),
                        "nome_file": filepath.name,
                        "nome_cliente": progetto.get("nome_cliente", "N/A"),
                        "progetto_id": progetto.get("progetto_id", ""),
                        "tipo_intervento": progetto.get("tipo_intervento", "N/A"),
                        "data_creazione": progetto.get("data_creazione", "N/A"),
                        "data_ultima_modifica": progetto.get("data_ultima_modifica", "N/A"),
                        "incentivo_totale": progetto.get("risultato_calcolo", {}).get("incentivo_totale", 0),
                        "note": progetto.get("note", "")[:100]  # Prime 100 char
                    })

                except Exception:
                    # Skip file corrotti
                    continue

            # Ordina per data modifica (più recenti prima)
            progetti.sort(key=lambda x: x["data_ultima_modifica"], reverse=True)

        except Exception:
            pass

        return progetti

    def cerca_progetti(
        self,
        query: str,
        campo: str = "tutti"  # "tutti", "cliente", "intervento", "note"
    ) -> List[Dict[str, Any]]:
        """
        Cerca progetti per query.

        Args:
            query: Testo da cercare
            campo: Campo in cui cercare

        Returns:
            Lista progetti che matchano
        """
        tutti_progetti = self.lista_progetti()
        query_lower = query.lower()

        risultati = []

        for progetto in tutti_progetti:
            match = False

            if campo == "tutti" or campo == "cliente":
                if query_lower in progetto["nome_cliente"].lower():
                    match = True

            if campo == "tutti" or campo == "intervento":
                if query_lower in progetto["tipo_intervento"].lower():
                    match = True

            if campo == "tutti" or campo == "note":
                if query_lower in progetto["note"].lower():
                    match = True

            if match:
                risultati.append(progetto)

        return risultati

    def elimina_progetto(self, filepath: Path) -> Tuple[bool, str]:
        """
        Elimina progetto.

        Args:
            filepath: Path file progetto

        Returns:
            (successo, messaggio)
        """
        try:
            if not filepath.exists():
                return False, "File non trovato"

            filepath.unlink()
            return True, "Progetto eliminato"

        except Exception as e:
            return False, f"Errore eliminazione: {str(e)}"

    def duplica_progetto(
        self,
        filepath: Path,
        nuovo_nome_cliente: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Duplica progetto esistente.

        Args:
            filepath: Path progetto da duplicare
            nuovo_nome_cliente: Nuovo nome cliente (opzionale)

        Returns:
            (successo, messaggio, nuovo_progetto_id)
        """
        try:
            # Carica progetto originale
            successo, progetto, msg = self.carica_progetto(filepath)
            if not successo:
                return False, msg, ""

            # Modifica metadati
            nome_cliente = nuovo_nome_cliente or f"{progetto['nome_cliente']} (Copia)"

            # Salva come nuovo progetto
            return self.salva_progetto(
                nome_cliente=nome_cliente,
                tipo_intervento=progetto["tipo_intervento"],
                risultato_calcolo=progetto["risultato_calcolo"],
                dati_input=progetto["dati_input"],
                note=f"Duplicato da: {progetto['nome_cliente']} - {progetto.get('note', '')}",
                progetto_id=None  # Nuovo ID
            )

        except Exception as e:
            return False, f"Errore duplicazione: {str(e)}", ""

    def esporta_riepilogo_cliente(self, nome_cliente: str) -> Dict[str, Any]:
        """
        Esporta riepilogo tutti progetti di un cliente.

        Args:
            nome_cliente: Nome cliente

        Returns:
            Dizionario con riepilogo progetti cliente
        """
        progetti_cliente = self.lista_progetti(nome_cliente)

        if not progetti_cliente:
            return {
                "nome_cliente": nome_cliente,
                "numero_progetti": 0,
                "progetti": []
            }

        # Calcola totali
        incentivo_totale = sum(p["incentivo_totale"] for p in progetti_cliente)

        interventi_per_tipo = {}
        for p in progetti_cliente:
            tipo = p["tipo_intervento"]
            if tipo not in interventi_per_tipo:
                interventi_per_tipo[tipo] = {
                    "count": 0,
                    "incentivo_totale": 0
                }
            interventi_per_tipo[tipo]["count"] += 1
            interventi_per_tipo[tipo]["incentivo_totale"] += p["incentivo_totale"]

        return {
            "nome_cliente": nome_cliente,
            "numero_progetti": len(progetti_cliente),
            "incentivo_totale": incentivo_totale,
            "interventi_per_tipo": interventi_per_tipo,
            "progetti": progetti_cliente,
            "data_primo_progetto": min(p["data_creazione"] for p in progetti_cliente),
            "data_ultimo_progetto": max(p["data_ultima_modifica"] for p in progetti_cliente)
        }


# Funzioni helper standalone
def get_gestore_progetti() -> GestioneProgetti:
    """
    Ottiene istanza singleton gestore progetti.

    Returns:
        Istanza GestioneProgetti
    """
    return GestioneProgetti()
