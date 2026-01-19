# Energy Incentive Manager - Conto Termico 3.0

Applicazione web per calcolo incentivi Conto Termico 3.0 e Ecobonus.

**Versione**: 1.0.0 (Post-Refactoring)
**Data Aggiornamento**: 2026-01-19
**Normativa**: DM 7 agosto 2025 (Conto Termico 3.0)

---

## Caratteristiche Principali

### ✅ Conto Termico 3.0 - COMPLETO
- **Tutti gli interventi incentivabili**:
  - Pompe di Calore (III.A) - elettriche, gas, geotermiche
  - Solare Termico (III.B)
  - Biomassa (III.C) - caldaie, stufe, termocamini
  - Sistemi Ibridi
  - Scaldacqua a PDC
  - Isolamento Termico (II.E, II.F) - pareti, coperture, pavimenti
  - Serramenti (II.B)
  - Schermature Solari (II.C)
  - Building Automation (II.D)
  - Illuminazione LED (II.H)
  - Ricarica Veicoli Elettrici (II.G)
  - Fotovoltaico Combinato (II.H)

- **Vincoli Terziario CT 3.0** ✨:
  - Verifica automatica per imprese/ETS economici su edifici terziario
  - Blocco PDC a gas per imprese su terziario (Art. 25, comma 2)
  - Controllo riduzione energia primaria 10%/20% con APE

- **Modalità Prenotazione** ✨:
  - Simulazione completa per PA/ETS/ESCO
  - Acconti (50% o 40%)
  - Rata intermedia al 50% avanzamento lavori
  - Timeline con 4 date chiave
  - 7 fasi processo con documenti richiesti

- **Nuove soglie CT 3.0**:
  - Rata unica fino a 15.000€ (era 5.000€)
  - Maggiorazione +10% componenti UE
  - Maggiorazione FV registro tecnologie (+5/10/15%)

### ✅ Ecobonus 2025
- Detrazioni 50-65%
- Massimali aggiornati
- Multi-intervento

### ✅ Funzionalità Avanzate
- Multi-intervento con ottimizzazione
- Confronto scenari (CT vs Ecobonus)
- Storico calcoli persistente
- Generazione report HTML
- Analisi finanziaria (ROI, NPV, IRR, payback)

---

## Installazione

### Requisiti
- Python 3.10+
- pip

### Setup

```bash
# 1. Clona/scarica il progetto
cd "c:\Users\Utente\Desktop\energy tool"

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Avvia applicazione
streamlit run app_streamlit.py

# L'app si aprirà automaticamente nel browser
# http://localhost:8501
```

---

## Esecuzione Test

```bash
# Esegui tutti i test
pytest tests/ -v

# Test specifici
pytest tests/test_vincoli_terziario.py -v
pytest tests/test_validators.py -v

# Test con coverage report
pytest tests/ --cov=modules --cov=components --cov-report=html

# Apri report HTML (genera cartella htmlcov/)
# open htmlcov/index.html
```

**Test Coverage**:
- ✅ 64 test automatici
- ✅ 91% coverage validators
- ✅ 82% coverage vincoli_terziario

---

## Struttura Progetto

```
energy tool/
├── app_streamlit.py              # Applicazione principale Streamlit
│
├── components/                   # Componenti riutilizzabili
│   ├── validators.py             # Validazione input (superficie, potenza, date, etc.)
│   └── ui_components.py          # Componenti UI (cards, tabelle, formatting)
│
├── modules/                      # Logica business
│   ├── calculator_ct.py          # Calcolo incentivi Conto Termico
│   ├── vincoli_terziario.py      # Vincoli CT 3.0 per terziario
│   ├── prenotazione.py           # Modalità prenotazione PA/ETS
│   ├── calculator_*.py           # Calculator specifici interventi
│   ├── validator_*.py            # Validatori specifici
│   ├── report_generator.py       # Generazione report HTML
│   └── financial_roi.py          # Analisi finanziaria
│
├── tests/                        # Test automatici
│   ├── test_vincoli_terziario.py # 24 test vincoli terziario
│   ├── test_validators.py        # 33 test validatori input
│   └── test_calcoli.py           # Test calculator
│
├── backups/                      # Backup versioni precedenti
├── AGGIORNAMENTI_CT3.md         # Documentazione implementazione CT 3.0
├── REFACTORING.md                # Documentazione refactoring architetturale
├── Sintesi_CT3_Dati_Estratti.txt # Dati normativi CT 3.0
└── requirements.txt              # Dipendenze Python
```

---

## Guida Rapida

### 1. Calcolo Incentivo Pompa di Calore

1. Apri TAB "Pompe di Calore"
2. Seleziona:
   - Tipologia edificio/soggetto (es. "Residenziale - Privato")
   - Zona climatica
   - Tipo PDC (elettrica/gas/geotermica)
3. Inserisci dati tecnici:
   - SCOP/COP
   - Potenza utile (kW)
   - Temperatura design
4. Click "CALCOLA INCENTIVO"
5. Visualizza:
   - Incentivo totale
   - Rateizzazione (se > 15.000€)
   - Dettagli calcolo

**Attenzione**: Se **Terziario + Impresa**, PDC a gas **non ammessa** (Art. 25 CT 3.0)

### 2. Verifica Vincoli Terziario

1. Sidebar: Seleziona "Terziario - Impresa/ETS economico"
2. Inserisci categoria catastale (es. "C/1")
3. Se richiesto:
   - Spunta "APE ante e post disponibili"
   - Inserisci riduzione energia primaria (%)
4. Procedi con calcolo intervento
5. Sistema verifica automaticamente:
   - Ammissibilità PDC gas
   - Riduzione energia primaria sufficiente

### 3. Simulazione Prenotazione (solo PA/ETS)

1. Calcola prima un incentivo (qualsiasi intervento)
2. Vai al TAB "Prenotazione"
3. Sistema usa automaticamente ultimo incentivo calcolato
4. Seleziona casistica:
   - Diagnosi energetica
   - Contratto EPC
   - PPP
   - Lavori assegnati
5. Opzioni:
   - Richiedi acconto (50% o 40%)
   - Richiedi rata intermedia (50% avanzamento)
6. Click "SIMULA PRENOTAZIONE"
7. Visualizza:
   - Rateizzazione dettagliata
   - Timeline (presentazione → conclusione)
   - 7 fasi processo + documenti

### 4. Multi-Intervento

1. TAB "Multi-Intervento"
2. Aggiungi interventi combinabili:
   - PDC + Solare Termico
   - PDC + Isolamento
   - PDC + Serramenti
3. Sistema verifica:
   - Compatibilità
   - Abbinamenti obbligatori (es. FV richiede PDC)
4. Calcola incentivo totale ottimizzato

---

## Novità CT 3.0 (Rispetto CT 2.0)

| Aspetto | CT 2.0 | CT 3.0 |
|---------|--------|--------|
| **Soglia rata unica** | 5.000€ | **15.000€** |
| **Nuovi interventi** | - | **Colonnine VE (II.G)**, **FV combinato (II.H)** |
| **Biomassa classe 5 stelle** | Sempre obbligatoria | Solo se sostituisci biomassa/carbone/olio/gasolio |
| **Maggiorazioni** | Limitate | **+10% componenti UE**, **+5/10/15% FV registro** |
| **Vincoli terziario** | Generici | **Specifici per imprese** (no PDC gas, riduzione EP) |
| **Prenotazione** | Solo PA | **PA, ETS non economico, ESCO** |
| **PA edifici pubblici** | Massimali variabili | **100% spese** (art. 11 comma 2) |

---

## Riferimenti Normativi

### Principali:
- **DM 7 agosto 2025** - Conto Termico 3.0
- **Regole Applicative GSE** - Aggiornamento CT 3.0
- **DM 186/2017** - Classe ambientale 5 stelle biomassa
- **D.lgs 102/2014** - Diagnosi energetica

### Articoli Chiave CT 3.0:
- **Art. 4**: Requisiti ammissibilità
- **Art. 7**: Modalità prenotazione
- **Art. 11**: Erogazione incentivi (soglia 15.000€, PA 100%)
- **Art. 25, comma 2**: Vincoli terziario imprese (no PDC gas)

---

## FAQ

### Q: Posso usare PDC a gas su edificio terziario per un'impresa?
**A**: **NO**. Il CT 3.0 (Art. 25, comma 2) vieta PDC a gas per imprese/ETS economici su edifici terziario (cat. B, C, D, E). PDC elettriche sono ammesse.

### Q: Quando serve APE ante e post-operam?
**A**:
- **Sempre** per edifici terziario con imprese (riduzione energia primaria obbligatoria)
- **Opzionale** per privati su residenziale (tranne multi-intervento)
- **Obbligatoria** per prenotazione

### Q: Qual è la soglia per rata unica?
**A**: **15.000€** (CT 3.0). Sopra questa soglia: 2 o 5 anni.

### Q: Chi può accedere a prenotazione?
**A**: Solo PA, ETS non economici, ESCO per loro conto. **Privati e imprese NO**.

### Q: La classe 5 stelle biomassa è sempre obbligatoria?
**A**: **NO**. Obbligatoria solo se sostituisci impianto a biomassa/carbone/olio/gasolio esistente. Se sostituisci caldaia a gas/GPL, classe 5 stelle NON obbligatoria (ma consigliata).

---

## Supporto e Contributi

### Segnalazione Bug:
1. Verifica backup disponibile: `backups/backup_pre_refactoring_*/`
2. Esegui test: `pytest tests/ -v`
3. Documenta bug con:
   - Input inseriti
   - Output atteso vs effettivo
   - Screenshot se applicabile

### Estensioni Future:
- [ ] Modularizzare TAB in `pages/`
- [ ] CI/CD con GitHub Actions
- [ ] Export PDF piano prenotazione
- [ ] Integrazione API GSE (quando disponibile)
- [ ] Supporto multi-lingua

---

## Licenza

Uso interno - Consulta documentazione normativa GSE per uso commerciale.

---

## Credits

**Sviluppo**: Claude Code (Anthropic)
**Normativa**: DM 7 agosto 2025, GSE Regole Applicative CT 3.0
**Data Ultimo Aggiornamento**: 2026-01-19

---

## Changelog

### v1.0.0 (2026-01-19) - Post-Refactoring
- ✅ Refactoring architetturale completo
- ✅ Componenti riutilizzabili (`components/validators.py`, `components/ui_components.py`)
- ✅ Test automatici (64 test, 82-91% coverage moduli critici)
- ✅ Backup pre-refactoring
- ✅ Documentazione completa (REFACTORING.md)

### v0.9.0 (2026-01-19) - CT 3.0 Implementazione Completa
- ✅ Vincoli terziario applicati a TUTTI gli interventi
- ✅ TAB Prenotazione completa
- ✅ Sidebar unificata edificio/soggetto
- ✅ Helper centralizzata `applica_vincoli_terziario_ct3()`

### v0.8.0 - CT 3.0 Base
- Implementazione coefficienti CT 3.0
- Soglia 15.000€
- Nuovi interventi (II.G, II.H)

---

**Per dettagli implementazione CT 3.0**: vedi [AGGIORNAMENTI_CT3.md](AGGIORNAMENTI_CT3.md)
**Per dettagli refactoring**: vedi [REFACTORING.md](REFACTORING.md)
