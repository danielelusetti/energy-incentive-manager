# 🔧 Fix Prenotazione - Mapping Tipo Soggetto

**Data Fix**: 2026-01-19 01:00
**Problema**: PA non riconosciuto come ammissibile a prenotazione
**Stato**: ✅ RISOLTO

---

## 🐛 Problema Identificato

### Sintomo
Quando l'utente selezionava "PA / ETS non economico" nella sidebar, il TAB Prenotazione mostrava:

```
❌ Soggetto Pubblica Amministrazione NON ammesso a prenotazione
```

Invece di riconoscere la PA come ammissibile.

### Causa Root
**Linea 1028** - Mapping errato tipo soggetto:

```python
# PRIMA (ERRATO)
st.session_state.tipo_soggetto_principale = tipo_soggetto_label  # "Pubblica Amministrazione"
```

Il problema era che veniva salvato il **label** ("Pubblica Amministrazione") invece del **codice** ("PA").

La funzione `is_prenotazione_ammissibile()` in `modules/prenotazione.py` si aspetta i codici:
- `"PA"` ✅
- `"privato"` ✅
- `"impresa"` ✅
- `"ETS_non_economico"` ✅
- `"ESCO"` ✅

Ma riceveva:
- `"Pubblica Amministrazione"` ❌
- `"Privato cittadino"` ❌
- `"Impresa"` (questo funzionava per caso) ⚠️

---

## ✅ Soluzione Applicata

### 1. Fix Mapping Session State (Linea 1028-1030)

**Prima**:
```python
tipo_soggetto = TIPI_SOGGETTO.get(tipo_soggetto_label, "privato")

# Salva in session state
st.session_state.tipo_soggetto_principale = tipo_soggetto_label  # ERRATO
st.session_state.edificio_pubblico_art11 = edificio_pubblico_art11
```

**Dopo**:
```python
tipo_soggetto = TIPI_SOGGETTO.get(tipo_soggetto_label, "privato")

# Salva in session state
st.session_state.tipo_soggetto_principale = tipo_soggetto  # CORRETTO - usa codice
st.session_state.tipo_soggetto_label = tipo_soggetto_label  # Salva anche label per display
st.session_state.edificio_pubblico_art11 = edificio_pubblico_art11
```

### 2. Fix Default Values

**Linea 671** - Init session state:
```python
# PRIMA
st.session_state.tipo_soggetto_principale = "Privato"  # ERRATO - label

# DOPO
st.session_state.tipo_soggetto_principale = "privato"  # CORRETTO - codice
```

**Linea 1205** - Estrazione variabili:
```python
# PRIMA
tipo_soggetto_principale = st.session_state.get("tipo_soggetto_principale", "Privato")

# DOPO
tipo_soggetto_principale = st.session_state.get("tipo_soggetto_principale", "privato")
```

**Linee 7940, 8079** - TAB Prenotazione:
```python
# PRIMA
tipo_soggetto=st.session_state.get("tipo_soggetto_principale", "Privato")

# DOPO
tipo_soggetto=st.session_state.get("tipo_soggetto_principale", "privato")
```

---

## 📊 Mapping Tipo Soggetto

Il dizionario `TIPI_SOGGETTO` (linea 194) definisce la mappatura corretta:

```python
TIPI_SOGGETTO = {
    "Privato cittadino": "privato",        # Label → Codice
    "Impresa": "impresa",                   # Label → Codice
    "Pubblica Amministrazione": "PA",       # Label → Codice
}
```

### Flusso Corretto

1. **Sidebar**: Utente seleziona "PA / ETS non economico"
2. **Mapping**: `tipo_soggetto_label = "Pubblica Amministrazione"`
3. **Dizionario**: `tipo_soggetto = TIPI_SOGGETTO["Pubblica Amministrazione"]` → `"PA"`
4. **Session State**: Salva `"PA"` (non "Pubblica Amministrazione")
5. **TAB Prenotazione**: Legge `"PA"` da session_state
6. **Verifica**: `is_prenotazione_ammissibile(tipo_soggetto="PA")` → ✅ Ammesso

---

## 🧪 Test Verifica

### Test Case 1: PA Ammessa
**Input**: Seleziona "PA / ETS non economico" in sidebar
**Expected**:
```
✅ Soggetto ammesso a prenotazione
```
**Actual**: ✅ PASS

### Test Case 2: Privato NON Ammesso
**Input**: Seleziona "Residenziale - Privato" in sidebar
**Expected**:
```
❌ Soggetto privato NON ammesso a prenotazione (solo PA, ETS non economici, ESCO per loro conto)
```
**Actual**: ✅ PASS

### Test Case 3: Impresa NON Ammessa
**Input**: Seleziona "Terziario - Impresa/ETS economico" in sidebar
**Expected**:
```
❌ Soggetto impresa NON ammesso a prenotazione (solo PA, ETS non economici, ESCO per loro conto)
```
**Actual**: ✅ PASS

---

## 📝 Files Modificati

| File | Linee Modificate | Tipo Modifica |
|------|------------------|---------------|
| `app_streamlit.py` | 671 | Default init session state |
| `app_streamlit.py` | 1028-1030 | Mapping session_state salvataggio |
| `app_streamlit.py` | 1205 | Default get session_state |
| `app_streamlit.py` | 7940 | Default TAB Prenotazione |
| `app_streamlit.py` | 8079 | Default TAB Prenotazione |

**Totale Modifiche**: 5 linee in 1 file

---

## 🎯 Impatto Fix

### Funzionalità Riparate
✅ **TAB Prenotazione** ora riconosce correttamente:
- PA come ammessa
- Privati come NON ammessi
- Imprese come NON ammesse
- ETS non economici come ammessi (quando implementato)
- ESCO per conto PA/ETS come ammesse (quando implementato)

### Funzionalità Invariate
✅ **TAB Calcolo** continuano a funzionare correttamente
✅ **Percentuali incentivo** PA (100%) ancora applicata correttamente
✅ **Validazioni vincoli** terziario ancora funzionanti
✅ **Sistema Progetti Clienti** non influenzato

### Nessun Breaking Change
✅ Modifica retrocompatibile
✅ Nessun progetto salvato influenzato
✅ Nessuna API pubblica modificata

---

## 🔍 Dettagli Tecnici

### Perché il Bug Non Era Evidente Prima

Il bug non era visibile nei TAB di calcolo perché:

1. **Nei TAB di calcolo** si usa `tipo_soggetto_label` come parametro:
   ```python
   calcola_incentivo_pdc(
       tipo_soggetto_label=tipo_soggetto_principale,  # Riceve label o codice, entrambi OK
       ...
   )
   ```
   La funzione accettava entrambi i formati.

2. **Nel TAB Prenotazione** si usa `tipo_soggetto` (codice):
   ```python
   is_prenotazione_ammissibile(
       tipo_soggetto=tipo_soggetto_principale,  # DEVE essere codice
       ...
   )
   ```
   La funzione usa `Literal` type hint e match exact su codici.

### Type Safety Lesson

Questo bug evidenzia l'importanza di:
- ✅ Usare type hints `Literal` per valori enum
- ✅ Distinguere chiaramente "label" vs "codice"
- ✅ Naming convention coerente (`_label` suffix per label)
- ✅ Validazione input funzioni con type checking

---

## ✅ Checklist Verifica Fix

- [x] Codice modificato e testato
- [x] Applicazione riavviata senza errori
- [x] Test PA ammessa: PASS
- [x] Test Privato non ammesso: PASS
- [x] Test Impresa non ammessa: PASS
- [x] Nessun breaking change introdotto
- [x] Documentazione aggiornata (questo file)
- [x] Pronto per produzione

---

## 🚀 Stato Finale

```
┌────────────────────────────────────────────┐
│  ✅ FIX COMPLETATO E VERIFICATO            │
├────────────────────────────────────────────┤
│  Problema: PA non riconosciuta             │
│  Causa: Mapping label invece di codice     │
│  Fix: Salva codice in session_state        │
│  Test: ✅ TUTTI SUPERATI                   │
│  Pronto: PRODUZIONE                        │
└────────────────────────────────────────────┘
```

**L'applicazione ora riconosce correttamente PA come ammessa a prenotazione!** ✅

---

*Fix applicato: 2026-01-19 01:00*
*Energy Incentive Manager - CT 3.0*
*Tipo Soggetto Mapping v1.1*
