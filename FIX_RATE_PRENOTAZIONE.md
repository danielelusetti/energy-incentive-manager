# 🔧 Fix Calcolo Rate Prenotazione

**Data Fix**: 2026-01-19 01:05
**Problema**: Somma rate prenotazione non corrisponde all'incentivo totale
**Stato**: ✅ RISOLTO

---

## 🐛 Problema Identificato

### Sintomo Riportato dall'Utente

Con incentivo totale di **€50,000**:

| Tipo Rate | Importo | % |
|-----------|---------|---|
| Acconto | €20,000 | 40% |
| Saldo | €30,000 | 60% |
| Rata annua 2/5 | €6,000 | 12% |
| Rata annua 3/5 | €6,000 | 12% |
| Rata annua 4/5 | €6,000 | 12% |
| Rata annua 5/5 | €6,000 | 12% |
| **TOTALE** | **€74,000** | **148%** ❌

**Problema**: La somma è €74,000 invece di €50,000!

### Causa Root

Il codice in `modules/prenotazione.py` (linee 213-224) aggiungeva **erroneamente** rate annuali successive dopo acconto e saldo:

```python
# CODICE ERRATO
if numero_anni > 1:
    rata_annua_successiva = round(importo_saldo / numero_anni, 2)
    for anno in range(2, numero_anni + 1):
        rate_dettaglio.append({
            "tipo": f"Rata annua {anno}/{numero_anni}",
            "momento": f"Anno {anno}",
            "importo": rata_annua_successiva,
            "percentuale": (rata_annua_successiva / incentivo_totale) * 100,
            "anno": anno
        })
```

Questo creava:
- **Acconto**: €20,000 (40%)
- **Saldo**: €30,000 (60%)
- **Rate 2-5**: €6,000 × 4 = €24,000 (48% extra!)
- **Totale**: €74,000 (148%) ❌

---

## 💡 Comprensione Normativa

### Modalità PRENOTAZIONE vs CONSUNTIVO

Esistono **DUE modalità diverse** di accesso al Conto Termico:

#### 1️⃣ Modalità CONSUNTIVO (Standard)
**Chi**: Tutti i soggetti
**Quando**: Dopo la fine dei lavori
**Pagamento**:
- Rate annuali distribuite in 2 o 5 anni
- Esempio 5 anni: 5 rate da 20% ciascuna = 100%

#### 2️⃣ Modalità PRENOTAZIONE (Solo PA/ETS/ESCO)
**Chi**: Solo PA, ETS non economici, ESCO per loro conto
**Quando**: Prima di iniziare i lavori
**Pagamento ANTICIPATO**:
- **Acconto** (40-50%): Subito dopo ammissione GSE
- **Rata intermedia** (opzionale): Al 50% avanzamento lavori
- **Saldo** (50-60%): A conclusione lavori
- **TOTALE = 100%** (pagamento completo a fine lavori!)

### Errore Concettuale nel Codice

Il codice originale confondeva:
- **Numero anni erogazione** (parametro per calcolare % acconto)
- **Rate annuali** (che NON esistono in prenotazione!)

Il parametro `numero_anni` (2 o 5) serve SOLO per determinare:
- Se 2 anni → Acconto 50%
- Se 5 anni → Acconto 40% (2/5)

**NON** significa che ci sono rate da distribuire negli anni successivi!

---

## ✅ Soluzione Applicata

### File Modificato: `modules/prenotazione.py`

#### 1. Rimosso Codice Errato (Linee 213-224)

**Prima**:
```python
# Rate annue successive (se previste)
if numero_anni > 1:
    rata_annua_successiva = round(importo_saldo / numero_anni, 2)
    # Prima rata annua è già nel saldo
    for anno in range(2, numero_anni + 1):
        rate_dettaglio.append({
            "tipo": f"Rata annua {anno}/{numero_anni}",
            "momento": f"Anno {anno}",
            "importo": rata_annua_successiva,
            "percentuale": (rata_annua_successiva / incentivo_totale) * 100,
            "anno": anno
        })
```

**Dopo**:
```python
# NOTA: Con PRENOTAZIONE il pagamento è completato a fine lavori (Acconto + Saldo = 100%)
# Le rate annuali (2-5 anni) sono SOLO per modalità CONSUNTIVO (senza prenotazione)
# Quindi NON aggiungiamo rate successive qui
```

#### 2. Aggiornato Docstring (Linee 144-165)

**Prima**:
```python
"""
Calcola rateizzazione incentivo con modalità prenotazione.

Regole (Art. 11, comma 6):
- Acconto: 50% se 2 anni, 40% (2/5) se 5 anni
- Rata intermedia: possibile al 50% avanzamento lavori
- Saldo: a conclusione lavori
- Rate annue: le restanti dopo saldo  ← ERRATO!
```

**Dopo**:
```python
"""
Calcola rateizzazione incentivo con modalità prenotazione.

IMPORTANTE: Con PRENOTAZIONE il pagamento è ANTICIPATO e completato a fine lavori.
NON ci sono rate annuali successive (quelle sono solo per modalità CONSUNTIVO).

Regole (Art. 11, comma 6):
- Acconto: 50% se 2 anni, 40% (2/5) se 5 anni - erogato dopo ammissione
- Rata intermedia (opzionale): al 50% avanzamento lavori
- Saldo: a conclusione lavori
- TOTALE = Acconto + (Rata intermedia) + Saldo = 100%

Args:
    numero_anni: Parametro di riferimento per calcolo percentuale acconto (non rate annuali!)
```

---

## 📊 Risultato Corretto

### Dopo il Fix

Con incentivo totale di **€50,000** e 5 anni:

| Tipo Rate | Momento Erogazione | Importo | % |
|-----------|-------------------|---------|---|
| **Acconto** | Ammissione a prenotazione | €20,000 | 40% |
| **Saldo** | Conclusione lavori | €30,000 | 60% |
| **TOTALE** | | **€50,000** | **100%** ✅

### Variante con Rata Intermedia (Opzionale)

Se attivata rata intermedia al 50% avanzamento:

| Tipo Rate | Momento Erogazione | Importo | % |
|-----------|-------------------|---------|---|
| **Acconto** | Ammissione | €20,000 | 40% |
| **Rata intermedia** | 50% avanzamento lavori | €15,000 | 30% |
| **Saldo** | Conclusione lavori | €15,000 | 30% |
| **TOTALE** | | **€50,000** | **100%** ✅

---

## 🧪 Test Verifica

### Test Case 1: Incentivo €50,000 - 5 anni
**Input**:
- Incentivo: €50,000
- Numero anni: 5
- Acconto: Sì
- Rata intermedia: No

**Output Atteso**:
```
Acconto (40%): €20,000
Saldo (60%): €30,000
TOTALE: €50,000 ✅
```

**Risultato**: ✅ PASS

### Test Case 2: Incentivo €50,000 - 2 anni
**Input**:
- Incentivo: €50,000
- Numero anni: 2
- Acconto: Sì
- Rata intermedia: No

**Output Atteso**:
```
Acconto (50%): €25,000
Saldo (50%): €25,000
TOTALE: €50,000 ✅
```

**Risultato**: ✅ PASS

### Test Case 3: Con Rata Intermedia
**Input**:
- Incentivo: €50,000
- Numero anni: 5
- Acconto: Sì
- Rata intermedia: Sì (50% avanzamento)

**Output Atteso**:
```
Acconto (40%): €20,000
Rata intermedia (30%): €15,000
Saldo (30%): €15,000
TOTALE: €50,000 ✅
```

**Risultato**: ✅ PASS

---

## 📝 Dettagli Matematici

### Formula Corretta

**Senza rata intermedia**:
```
Acconto = Incentivo × 40% (se 5 anni) o 50% (se 2 anni)
Saldo = Incentivo - Acconto
TOTALE = Acconto + Saldo = Incentivo (100%)
```

**Con rata intermedia**:
```
Acconto = Incentivo × 40%
Rimanenza = Incentivo - Acconto
Rata_Intermedia = Rimanenza × 50%
Saldo = Rimanenza - Rata_Intermedia
TOTALE = Acconto + Rata_Intermedia + Saldo = Incentivo (100%)
```

### Esempio Numerico

**Incentivo**: €50,000 | **Anni**: 5

**Senza rata intermedia**:
```
Acconto = €50,000 × 0.40 = €20,000
Saldo = €50,000 - €20,000 = €30,000
TOTALE = €20,000 + €30,000 = €50,000 ✅
```

**Con rata intermedia**:
```
Acconto = €50,000 × 0.40 = €20,000
Rimanenza = €50,000 - €20,000 = €30,000
Rata_Intermedia = €30,000 × 0.50 = €15,000
Saldo = €30,000 - €15,000 = €15,000
TOTALE = €20,000 + €15,000 + €15,000 = €50,000 ✅
```

---

## 🎓 Lesson Learned

### Confusione Terminologica

Il parametro `numero_anni` creava confusione perché:
- In **modalità CONSUNTIVO**: significa "anni di erogazione rate"
- In **modalità PRENOTAZIONE**: significa "parametro per calcolo % acconto"

### Soluzione per il Futuro

Sarebbe meglio rinominare il parametro in:
```python
def calcola_rateizzazione_prenotazione(
    incentivo_totale: float,
    riferimento_anni: int = 5,  # Più chiaro: "riferimento" non "numero anni erogazione"
    ...
)
```

O aggiungere enum:
```python
class TipoPercentualeAcconto(Enum):
    DUE_ANNI = 0.50  # 50%
    CINQUE_ANNI = 0.40  # 40% (2/5)
```

---

## 📋 Checklist Fix

- [x] Codice errato rimosso (linee 213-224)
- [x] Docstring aggiornata con chiarimenti
- [x] Commenti esplicativi aggiunti
- [x] Applicazione riavviata
- [x] Test matematici verificati
- [x] Nessun breaking change
- [x] Documentazione creata

---

## 🔍 Impatto

### Funzionalità Corrette
✅ **TAB Prenotazione** ora mostra totali corretti
✅ **Calcolo matematico** accurato (100% incentivo)
✅ **Dettaglio rate** coerente con normativa CT 3.0
✅ **Simulazione prenotazione** affidabile per utenti PA

### Nessun Effetto su
✅ **Calcoli incentivo** (non modificati)
✅ **Modalità CONSUNTIVO** (separata, non interessata)
✅ **Altri TAB** (nessuna dipendenza)
✅ **Progetti salvati** (non influenzati)

---

## 🚀 Stato Finale

```
┌────────────────────────────────────────────┐
│  ✅ FIX CALCOLO RATE COMPLETATO            │
├────────────────────────────────────────────┤
│  Problema: Totale rate ≠ incentivo         │
│  Causa: Rate annuali erroneamente aggiunte │
│  Fix: Rimosso codice rate successive       │
│  Formula: Acconto + Saldo = 100%           │
│  Test: ✅ TUTTI SUPERATI                   │
│  Matematica: ✅ CORRETTA                   │
└────────────────────────────────────────────┘
```

**Ora il calcolo rate prenotazione è matematicamente corretto!** ✅

---

## 📚 Riferimenti Normativi

- **DM 7 agosto 2025** - Conto Termico 3.0
- **Art. 11, comma 6** - Modalità prenotazione
- **Regole Applicative GSE** - Erogazione incentivi

---

*Fix applicato: 2026-01-19 01:05*
*Energy Incentive Manager - CT 3.0*
*Rate Prenotazione v1.1*
