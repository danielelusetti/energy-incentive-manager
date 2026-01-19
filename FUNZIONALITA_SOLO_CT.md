# 🎯 Funzionalità "Solo Conto Termico 3.0"

**Data Implementazione**: 2026-01-19
**Versione**: 2.1.0
**Stato**: ✅ Implementata (TAB PdC) - ⏳ In corso (altri TAB)

---

## 📋 Descrizione

Nuova funzionalità che permette di calcolare e visualizzare **SOLO** gli incentivi del Conto Termico 3.0, senza il confronto con Ecobonus.

### Motivazione

Richiesta utente:
> "Vorrei che per ogni singolo intervento ci fosse la possibilità di generare il calcolo dell'incentivo solamente per il conto termico 3.0 senza paragonarlo ad altri incentivi perché magari il cliente mi chiede direttamente di usare questo incentivo."

---

## 🔧 Implementazione

### 1. Checkbox Globale in Sidebar

**Posizione**: Sidebar → Sezione "⚙️ Modalità Calcolo"

**Codice** ([app_streamlit.py:1206-1218](app_streamlit.py#L1206-L1218)):
```python
st.subheader("⚙️ Modalità Calcolo")
solo_ct = st.checkbox(
    "🎯 Solo Conto Termico 3.0",
    value=False,
    help="Attiva per calcolare SOLO Conto Termico 3.0 senza confronto con Ecobonus",
    key="solo_conto_termico"
)

if solo_ct:
    st.info("✅ Modalità **Solo CT 3.0** attiva")
else:
    st.caption("Modalità standard: confronto CT 3.0 vs Ecobonus")
```

### 2. Visualizzazione Condizionale Risultati

**Metriche** ([app_streamlit.py:1531-1554](app_streamlit.py#L1531-L1554)):

**Se `solo_ct = True`**:
- Mostra solo 2 metriche: "Conto Termico 3.0" e "NPV"
- Nasconde metriche Ecobonus

**Se `solo_ct = False`** (default):
- Mostra 4 metriche: CT, Ecobonus, NPV CT, NPV Eco
- Comportamento originale

### 3. Grafico Comparativo

**Logica** ([app_streamlit.py:1557](app_streamlit.py#L1557)):
```python
if not solo_conto_termico and (risultato["ct_incentivo"] > 0 or risultato["eco_detrazione"] > 0):
    # Mostra grafico confronto
```

Il grafico viene **nascosto** se modalità Solo CT attiva.

### 4. Raccomandazione

**Se `solo_ct = True`** ([app_streamlit.py:1573-1587](app_streamlit.py#L1573-L1587)):
```python
if solo_conto_termico:
    if risultato["ct_ammissibile"]:
        st.success("""
        ✅ CONTO TERMICO 3.0

        Incentivo: €XX,XXX (XX% della spesa)
        Erogazione: bonifico diretto GSE in N anni
        NPV: €XX,XXX
        """)
    else:
        st.error("❌ Intervento NON ammissibile")
```

**Se `solo_ct = False`**:
- Logica completa di confronto CT vs Ecobonus
- Raccomandazione automatica basata su NPV

---

## 📊 Confronto Modalità

| Aspetto | Solo CT 3.0 | Confronto (Default) |
|---------|-------------|---------------------|
| **Metriche** | 2 (CT + NPV) | 4 (CT + Eco + NPV CT + NPV Eco) |
| **Grafico** | Nascosto | Visibile |
| **Raccomandazione** | Solo CT | Confronto completo |
| **Dettagli** | Solo CT | CT + Ecobonus |
| **Report** | Solo CT (TODO) | CT + Ecobonus |

---

## ✅ TAB Implementati

| TAB | Stato | Note |
|-----|-------|------|
| 🔥 Pompe di Calore | ✅ COMPLETO | Implementazione completa |
| ☀️ Solare Termico | ⏳ TODO | Da implementare |
| 🔆 FV Combinato | ⏳ TODO | Da implementare |
| 🌲 Biomassa | ⏳ TODO | Da implementare |
| 🏠 Isolamento | ⏳ TODO | Da implementare |
| 🪟 Serramenti | ⏳ TODO | Da implementare |
| 🌤️ Schermature | ⏳ TODO | Da implementare |
| 💡 LED | ⏳ TODO | Da implementare |
| 🏢 B.A. | ⏳ TODO | Da implementare |
| 🔀 Ibridi | ⏳ TODO | Da implementare |
| 🚿 Scaldacqua | ⏳ TODO | Da implementare |
| 🔗 Multi | ⏳ TODO | Da implementare |

---

## 🎯 Prossimi Passi

### Alta Priorità

1. **✅ Test Funzionale TAB PdC**
   - Verificare checkbox funzionante
   - Test con calcolo reale
   - Verificare visualizzazione corretta

2. **Report Generator**
   - Modificare `report_generator.py`
   - Se `solo_ct = True` → report solo CT
   - Rimuovere sezioni Ecobonus condizionalmente

3. **Replica Altri TAB**
   - Biomassa
   - Isolamento
   - Serramenti
   - (Altri TAB principali)

### Media Priorità

4. **Template Riutilizzabile**
   - Creare funzione helper per rendering condizionale
   - Ridurre codice duplicato

5. **Documentazione Utente**
   - Aggiornare README
   - Guida uso modalità Solo CT

---

## 💡 Esempi Uso

### Scenario 1: Cliente Chiede Solo CT

**Utente**:
1. Spunta checkbox "🎯 Solo Conto Termico 3.0" in sidebar
2. Va su TAB "🔥 PdC"
3. Compila dati intervento
4. Calcola incentivo

**Risultato**:
- Vede SOLO incentivo CT 3.0
- NESSUN riferimento a Ecobonus
- Report (futuro) contiene solo CT

### Scenario 2: Confronto Standard

**Utente**:
1. Lascia checkbox "Solo CT 3.0" **NON** spuntato
2. Calcola intervento

**Risultato**:
- Vede confronto completo CT vs Ecobonus
- Raccomandazione automatica
- Report con entrambi incentivi

---

## 🔧 Note Tecniche

### Variabile Globale

```python
# Estrazione da session_state (linea 1221)
solo_conto_termico = st.session_state.get("solo_conto_termico", False)
```

Disponibile in TUTTI i TAB dopo questa linea.

### Pattern Implementazione

**Per ogni TAB**:

1. **Metriche**:
```python
if solo_conto_termico:
    # 2 colonne: CT + NPV
else:
    # 4 colonne: CT + Eco + NPV CT + NPV Eco
```

2. **Grafico**:
```python
if not solo_conto_termico and (ct > 0 or eco > 0):
    # Mostra grafico confronto
```

3. **Raccomandazione**:
```python
if solo_conto_termico:
    # Risultato solo CT
elif ct_ammissibile and eco_ammissibile:
    # Confronto completo
elif ct_ammissibile:
    # Solo CT (non ammissibile Eco)
elif eco_ammissibile:
    # Solo Eco (non ammissibile CT)
```

---

## 📝 Modifiche File

| File | Righe Modificate | Tipo Modifica |
|------|------------------|---------------|
| `app_streamlit.py` | 1206-1218 | Checkbox sidebar |
| `app_streamlit.py` | 1221 | Variabile globale |
| `app_streamlit.py` | 1531-1554 | Metriche condizionali |
| `app_streamlit.py` | 1557 | Grafico condizionale |
| `app_streamlit.py` | 1573-1587 | Raccomandazione Solo CT |
| `report_generator.py` | TODO | Report condizionale |

---

## ✅ Checklist Completamento

**TAB Pompe di Calore**:
- [x] Checkbox sidebar implementato
- [x] Variabile globale estratta
- [x] Metriche condizionali
- [x] Grafico condizionale
- [x] Raccomandazione Solo CT
- [ ] Test funzionale completo

**Altri TAB**:
- [ ] Solare Termico
- [ ] FV Combinato
- [ ] Biomassa
- [ ] Isolamento
- [ ] Serramenti
- [ ] Schermature
- [ ] LED
- [ ] Building Automation
- [ ] Ibridi
- [ ] Scaldacqua
- [ ] Multi-Intervento

**Report**:
- [ ] Modificare `report_generator.py`
- [ ] Test report Solo CT
- [ ] Verificare PDF generato

---

## 🚀 Stato Attuale

```
┌────────────────────────────────────────────┐
│ FUNZIONALITÀ SOLO CT 3.0                   │
├────────────────────────────────────────────┤
│ Checkbox Sidebar: ✅ IMPLEMENTATO          │
│ TAB PdC: ✅ COMPLETO                       │
│ Altri TAB: ⏳ IN CORSO                     │
│ Report: ⏳ TODO                            │
│ Test: ⏳ IN CORSO                          │
├────────────────────────────────────────────┤
│ Pronto per: TEST UTENTE (TAB PdC)          │
└────────────────────────────────────────────┘
```

**L'utente può testare la funzionalità sul TAB Pompe di Calore!** ✅

---

*Documento creato: 2026-01-19 01:25*
*Energy Incentive Manager - Feature "Solo CT 3.0"*
*Versione: 2.1.0*
