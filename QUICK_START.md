# Quick Start - Energy Incentive Manager CT 3.0

## Avvio Rapido (5 minuti)

### 1. Installazione

```bash
cd "c:\Users\Utente\Desktop\energy tool"
pip install -r requirements.txt
```

### 2. Verifica Funzionamento

```bash
# Esegui test automatici
pytest tests/ -v

# Risultato atteso:
# ===== 64 passed in ~1s =====
```

### 3. Avvia Applicazione

```bash
streamlit run app_streamlit.py

# Si aprirà automaticamente il browser su:
# http://localhost:8501
```

---

## Primo Calcolo Incentivo (3 minuti)

### Esempio: Pompa di Calore Elettrica

1. **Sidebar Sinistra**:
   - Tipologia: "Residenziale - Privato"
   - Zona climatica: "E"
   - Categoria catastale: "A/3" (se richiesta)

2. **TAB "Pompe di Calore"**:
   - Tipo PDC: "Elettrica"
   - Configurazione: "Solo riscaldamento"
   - SCOP: 4.5
   - Potenza utile: 25 kW
   - Temperatura design: 45°C

3. **Click "CALCOLA INCENTIVO"**

4. **Risultato**:
   ```
   ✅ Incentivo Totale: 12.500,00 €

   Spesa ammissibile: 25.000,00 €
   Erogazione: Rata unica (< 15.000€)
   ```

---

## Test Vincoli Terziario (2 minuti)

### Scenario: Impresa su Edificio Terziario

1. **Sidebar**:
   - Tipologia: "Terziario - Impresa/ETS economico"
   - Categoria catastale: "C/1" (negozio)

2. **TAB "Pompe di Calore"**:
   - Tipo PDC: **"Gas"**
   - Configurazione: "Solo riscaldamento"
   - Potenza: 35 kW

3. **Click "CALCOLA INCENTIVO"**

4. **Risultato Atteso**:
   ```
   🚫 IMPRESE/ETS economici su edifici terziario:
   pompe di calore a GAS NON ammesse (Art. 25, comma 2)
   ```

5. **Cambia in PDC Elettrica** → Calcolo funziona

---

## Simulazione Prenotazione (3 minuti)

### Solo per PA/ETS Non Economici

1. **Prima calcola un incentivo** (qualsiasi TAB)

2. **VAI AL TAB "Prenotazione"**

3. **Se hai selezionato PA**:
   ```
   ✅ Soggetto ammesso a prenotazione
   ```

4. **Seleziona casistiche**:
   - ☑ Diagnosi energetica disponibile
   - ☑ Richiedi acconto
   - ☑ Richiedi rata intermedia

5. **Click "SIMULA PRENOTAZIONE"**

6. **Risultato**:
   - Rateizzazione dettagliata (acconto 50%, rata intermedia, saldo)
   - Timeline (presentazione → conclusione)
   - 7 fasi processo + documenti

---

## Test Validazione Input (1 minuto)

### Prova Input Errati

1. **TAB qualsiasi con input numerico**

2. **Inserisci superficie = 0**:
   ```
   ❌ Superficie deve essere maggiore di zero
   ```

3. **Inserisci superficie = 999999**:
   ```
   ⚠️ Superficie eccessiva (massimo: 100.000 m²). Verificare valore.
   ```

4. **Inserisci potenza = 0.1 kW**:
   ```
   ⚠️ Potenza troppo bassa (minimo: 0.5 kW)
   ```

---

## Comandi Utili

```bash
# Test tutto
pytest tests/ -v

# Test solo vincoli terziario
pytest tests/test_vincoli_terziario.py -v

# Test con coverage HTML report
pytest tests/ --cov=modules --cov=components --cov-report=html
# Apri htmlcov/index.html

# Ripristina backup (se necessario)
cp -r backups/backup_pre_refactoring_20260119_002232/* .

# Verifica struttura progetto
ls -R components/ tests/
```

---

## Scenari di Test Completi

### Scenario 1: Privato Residenziale PDC Elettrica ✅

```
Soggetto: Privato cittadino
Edificio: Residenziale A/3
Zona: E
PDC: Elettrica 25 kW, SCOP 4.5

Risultato: Incentivo ~12.500€, rata unica
```

### Scenario 2: Impresa Terziario PDC Gas ❌

```
Soggetto: Impresa/ETS economico
Edificio: Terziario C/1
PDC: Gas 35 kW

Risultato: BLOCCATO (Art. 25, comma 2)
```

### Scenario 3: Impresa Terziario PDC Elettrica + APE ✅

```
Soggetto: Impresa/ETS economico
Edificio: Terziario C/1
PDC: Elettrica 35 kW
APE: Sì, riduzione 15%

Risultato: Incentivo OK (riduzione >= 10% richiesto)
```

### Scenario 4: PA Prenotazione ✅

```
Soggetto: Pubblica Amministrazione
Intervento: Serramenti 150 m²
Incentivo: 30.000€

Prenotazione:
- Acconto: 15.000€ (50%)
- Rata intermedia: 7.500€ (25% totale)
- Saldo: 7.500€ (25% totale)
- Rate annue: 0 (già tutto erogato in 3 fasi)
```

---

## Troubleshooting

### Problema: Test non passano

**Soluzione**:
```bash
# Verifica dipendenze
pip install -r requirements.txt --upgrade

# Riesegui test
pytest tests/ -v
```

### Problema: Streamlit non si avvia

**Soluzione**:
```bash
# Reinstalla streamlit
pip install streamlit --upgrade

# Verifica versione
streamlit --version

# Deve essere >= 1.28.0
```

### Problema: Import error components

**Soluzione**:
```bash
# Verifica file __init__.py esistano
ls components/__init__.py tests/__init__.py

# Se mancano, Python non riconosce come pacchetti
```

### Problema: Vuoi tornare a versione pre-refactoring

**Soluzione**:
```bash
# Ripristina backup
cd "c:\Users\Utente\Desktop\energy tool"
cp -r backups/backup_pre_refactoring_20260119_002232/* .

# Conferma ripristino
ls -lh app_streamlit.py
# Deve mostrare 639 KB
```

---

## Link Rapidi Documentazione

| Documento | Per Chi | Contenuto |
|-----------|---------|-----------|
| [README.md](README.md) | **Tutti** | Guida completa utente |
| [QUICK_START.md](QUICK_START.md) | **Principianti** | Questo file - inizio rapido |
| [REFACTORING.md](REFACTORING.md) | **Sviluppatori** | Dettagli tecnici architettura |
| [AGGIORNAMENTI_CT3.md](AGGIORNAMENTI_CT3.md) | **Tutti** | Storia implementazione CT 3.0 |
| [RIEPILOGO_REFACTORING.md](RIEPILOGO_REFACTORING.md) | **Tutti** | Sommario lavoro sessione |

---

## FAQ Rapide

**Q: L'app è pronta per l'uso?**
A: ✅ Sì, completamente funzionale e testata (64 test passati)

**Q: Posso usare PDC a gas su terziario con impresa?**
A: ❌ No, bloccato dal CT 3.0 Art. 25 comma 2. Usa PDC elettrica.

**Q: Serve APE per privato su residenziale?**
A: ⚠️ Opzionale per singolo intervento. Obbligatoria per multi-intervento e terziario.

**Q: Qual è la soglia rata unica?**
A: 💰 15.000€ (era 5.000€ nel CT 2.0)

**Q: Chi può fare prenotazione?**
A: 🏛️ Solo PA, ETS non economici, ESCO per loro conto. Privati NO.

**Q: Come esporto risultati?**
A: 📄 TAB "Genera Report" → Download HTML. Stampa come PDF dal browser.

---

## Supporto

**Bug o problemi?**
1. Controlla [README.md](README.md) FAQ
2. Verifica test: `pytest tests/ -v`
3. Consulta backup: `backups/backup_pre_refactoring_*/README_BACKUP.md`

**Estensioni future?**
Vedi [REFACTORING.md](REFACTORING.md) sezione "Prossimi Passi"

---

**Buon lavoro!** 🚀

*Ultima revisione: 2026-01-19*
