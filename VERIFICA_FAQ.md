# 📋 Verifica Coerenza FAQ vs Applicazione

**Data Verifica**: 2026-01-19
**File Verificato**: `docs_reference/FAQ.txt`
**Applicazione**: Energy Incentive Manager CT 3.0

---

## ✅ PUNTI VERIFICATI E CONFORMI

### 1. Requisiti Edificio (FAQ Linee 1-3)

**FAQ dice**:
> "Tutti gli interventi sono ammissibili solo se realizzati su edifici esistenti, iscritti al catasto edilizio urbano, ad esclusione degli edifici in costruzione (categoria F), dotati di impianto di climatizzazione invernale funzionante."

**Applicazione**:
- ✅ **CONFORME**: Linea 2 `app_streamlit.py` mostra avviso categoria F
- ✅ **CONFORME**: Sidebar richiede categoria catastale (esclusa F)
- ✅ **CONFORME**: Validazione edificio esistente implementata

**Evidenza**: L'applicazione esclude correttamente categoria F.

---

### 2. Impianto Climatizzazione Esistente (FAQ Linee 5-8)

**FAQ dice**:
> "Impianto di climatizzazione invernale esistente e funzionante alla data di entrata in vigore del Decreto (25 dicembre 2025)."

**Applicazione**:
- ✅ **CONFORME**: Validazione impianto esistente presente
- ⚠️ **PARZIALE**: Data 25/12/2025 non verificata esplicitamente

**Raccomandazione**: Aggiungere check data riferimento 25/12/2025.

---

### 3. Incentivo 100% PA Comuni ≤15k (FAQ Linee 12-15)

**FAQ dice**:
> "L'incentivo è determinato al 100% delle spese ammissibili per interventi realizzati su edifici di proprietà di Comuni con popolazione fino a 15.000 abitanti."

**Applicazione**:
- ✅ **CONFORME**: `edificio_pubblico_art11 = True` attiva incentivo 100%
- ✅ **CONFORME**: Sidebar mostra "✅ **Edificio PA**: Percentuale incentivo 100%"
- ✅ **CONFORME**: Calcoli applicano correttamente percentuale 100%

**Evidenza**: Linea 1033 `app_streamlit.py` - messaggio PA 100%.

---

### 4. Fotovoltaico + Accumulo (FAQ Linee 16-21)

**FAQ dice**:
> "Installazione FV e accumulo incentivabile solo se realizzato:
> - Congiuntamente a PDC elettriche (III.A)
> - In assetto autoconsumo (energia prodotta ≤ 105% somma consumi)"

**Applicazione - Verifico modulo FV**:
