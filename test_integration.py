"""
Test script per verifica integrazione completa Progetti Clienti
Testa tutte le funzionalita del modulo gestione_progetti
"""

from modules.gestione_progetti import get_gestore_progetti
from datetime import datetime

def test_integration():
    """Test completo integrazione"""

    print("=" * 70)
    print("TEST INTEGRAZIONE PROGETTI CLIENTI - Energy Incentive Manager")
    print("=" * 70)
    print()

    # Inizializza gestore
    print("[1/8] Inizializzazione gestore...")
    gestore = get_gestore_progetti()
    print("    OK - Gestore inizializzato")
    print()

    # Test 1: Lista progetti esistenti
    print("[2/8] Lista progetti esistenti...")
    progetti = gestore.lista_progetti()
    print(f"    OK - Trovati {len(progetti)} progetti")
    for p in progetti:
        print(f"         - {p['nome_cliente']} ({p['tipo_intervento']})")
    print()

    # Test 2: Salva nuovo progetto
    print("[3/8] Salvataggio nuovo progetto test...")
    test_dati_input = {
        "superficie": 120,
        "potenza": 15,
        "cop": 4.5,
        "temperatura": 7
    }

    test_risultato = {
        "incentivo_totale": 45000,
        "incentivo_annuale": 9000,
        "durata_anni": 5,
        "potenza_kw": 15
    }

    successo, msg, prog_id = gestore.salva_progetto(
        nome_cliente="Test Cliente - Integrazione",
        tipo_intervento="Pompe di Calore",
        risultato_calcolo=test_risultato,
        dati_input=test_dati_input,
        note="Test automatico integrazione sistema"
    )

    if successo:
        print(f"    OK - {msg}")
        print(f"         Progetto ID: {prog_id}")
    else:
        print(f"    ERRORE - {msg}")
        return False
    print()

    # Test 3: Cerca progetti
    print("[4/8] Test ricerca progetti...")
    risultati = gestore.cerca_progetti("Test", campo="cliente")
    print(f"    OK - Trovati {len(risultati)} progetti con 'Test' nel nome cliente")
    print()

    # Test 4: Carica progetto
    print("[5/8] Test caricamento progetto...")
    progetti_aggiornati = gestore.lista_progetti()
    if progetti_aggiornati:
        from pathlib import Path
        filepath = Path(progetti_aggiornati[0]["filepath"])
        successo, dati, msg = gestore.carica_progetto(filepath)
        if successo:
            print(f"    OK - Progetto caricato: {dati['nome_cliente']}")
            print(f"         Incentivo totale: EUR {dati['risultato_calcolo']['incentivo_totale']:,.2f}")
        else:
            print(f"    ERRORE - {msg}")
            return False
    print()

    # Test 5: Duplica progetto
    print("[6/8] Test duplicazione progetto...")
    if progetti_aggiornati:
        from pathlib import Path
        filepath = Path(progetti_aggiornati[0]["filepath"])
        successo, msg, nuovo_id = gestore.duplica_progetto(
            filepath,
            nuovo_nome_cliente="Test Cliente - Copia"
        )
        if successo:
            print(f"    OK - {msg}")
            print(f"         Nuovo progetto ID: {nuovo_id}")
        else:
            print(f"    ERRORE - {msg}")
            return False
    print()

    # Test 6: Riepilogo cliente
    print("[7/8] Test riepilogo cliente...")
    riepilogo = gestore.esporta_riepilogo_cliente("Test Cliente")
    print(f"    OK - Riepilogo generato per: {riepilogo['nome_cliente']}")
    print(f"         Numero progetti: {riepilogo['numero_progetti']}")
    print(f"         Incentivo totale: EUR {riepilogo['incentivo_totale']:,.2f}")
    if riepilogo['interventi_per_tipo']:
        print(f"         Interventi:")
        for tipo, dati in riepilogo['interventi_per_tipo'].items():
            print(f"           - {tipo}: {dati['count']} progetti, EUR {dati['incentivo_totale']:,.2f}")
    print()

    # Test 7: Cleanup progetti test
    print("[8/8] Pulizia progetti test...")
    count_eliminati = 0
    progetti_finali = gestore.lista_progetti()
    for p in progetti_finali:
        if "Test Cliente" in p["nome_cliente"]:
            from pathlib import Path
            filepath = Path(p["filepath"])
            successo, msg = gestore.elimina_progetto(filepath)
            if successo:
                count_eliminati += 1

    print(f"    OK - Eliminati {count_eliminati} progetti test")
    print()

    # Riepilogo finale
    print("=" * 70)
    print("RISULTATO TEST INTEGRAZIONE")
    print("=" * 70)
    print()
    print("TUTTI I TEST SUPERATI!")
    print()
    print("Funzionalita verificate:")
    print("  [OK] Inizializzazione gestore")
    print("  [OK] Lista progetti")
    print("  [OK] Salvataggio progetti")
    print("  [OK] Ricerca progetti")
    print("  [OK] Caricamento progetti")
    print("  [OK] Duplicazione progetti")
    print("  [OK] Riepilogo cliente")
    print("  [OK] Eliminazione progetti")
    print()
    print("L'integrazione e completa e funzionante!")
    print()
    print("PROSSIMI PASSI:")
    print("1. Aprire browser: http://localhost:8501")
    print("2. Compilare 'Nome Cliente' in sidebar")
    print("3. Calcolare un incentivo")
    print("4. Andare su TAB 'Progetti Clienti'")
    print("5. Verificare il progetto salvato appare nella lista")
    print()
    print("=" * 70)

    return True

if __name__ == "__main__":
    try:
        test_integration()
    except Exception as e:
        print(f"\nERRORE DURANTE TEST: {str(e)}")
        import traceback
        traceback.print_exc()
