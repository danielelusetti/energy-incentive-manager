# Aggiornamenti Conto Termico 3.0

## ✅ AGGIORNAMENTO 2026-01-19 (PARTE 2) - REFACTORING ARCHITETTURALE

**Miglioramenti Qualità Codice - COMPLETATO**:

### 1. Componenti Riutilizzabili Creati

**Directory `components/` creata** con:

#### `components/validators.py`:
- ✅ `validate_superficie()` - Valida superficie (0.1-100.000 m², warning >10.000)
- ✅ `validate_potenza()` - Valida potenza (0.5-2.000 kW, warning >500)
- ✅ `validate_percentuale()` - Valida percentuale (0-100%)
- ✅ `validate_data()` - Valida date (formato, range, warning futuro lontano)
- ✅ `validate_cop_eer()` - Valida COP/EER (1.0-7.0)
- ✅ `validate_temperatura()` - Valida temperature (-30 a +100°C)
- ✅ `validate_range_prezzi()` - Verifica coerenza prezzo×quantità=totale

#### `components/ui_components.py`:
- ✅ `format_currency()` - Formatta valuta: 50000.00 → "50.000,00 €"
- ✅ `format_percentage()` - Formatta percentuale: 0.15 → "15.0%"
- ✅ `render_risultato_incentivo()` - Card risultato uniforme
- ✅ `render_warning_vincoli()` - Alert vincoli terziario
- ✅ `render_storico_calcoli()` - Tabella storico + export CSV
- ✅ `render_card_info()` - Info card customizzabile
- ✅ `render_progress_bar()` - Progress bar con label
- ✅ `render_alert_normativa()` - Alert con riferimento articolo

### 2. Test Suite Automatica

**Directory `tests/` creata** con:

#### `tests/test_vincoli_terziario.py` - **24 test**:
- ✅ Classificazione categorie catastali (terziario vs residenziale)
- ✅ Calcolo riduzione energia primaria (10% vs 20%)
- ✅ Vincolo PDC a gas per imprese (Art. 25 comma 2)
- ✅ Vincolo APE con riduzione effettiva
- ✅ Soggetti non vincolati (PA, ETS non economico)
- ✅ Mappatura codici intervento
- ✅ Wrapper generico

#### `tests/test_validators.py` - **33 test**:
- ✅ Validazione superficie (6 test)
- ✅ Validazione potenza (5 test)
- ✅ Validazione percentuale (5 test)
- ✅ Validazione data (8 test)
- ✅ Validazione COP/EER (4 test)
- ✅ Validazione temperatura (5 test)

**Risultati**:
```
pytest tests/ -v
===== 64 test passati in 0.92s =====
```

**Coverage**:
- `components/validators.py`: **91%**
- `modules/vincoli_terziario.py`: **82%**

### 3. Backup Pre-Refactoring

**Creato backup completo**:
- Path: `backups/backup_pre_refactoring_20260119_002232/`
- Include: app_streamlit.py (639 KB), modules/, documentazione
- Versione: Funzionante pre-refactoring (CT 3.0 completo)

### 4. Documentazione

- ✅ `REFACTORING.md` - Guida completa refactoring (motivazioni, metriche, esempi)
- ✅ `README.md` - Guida utente completa con FAQ
- ✅ `requirements.txt` - Aggiunto pytest, pytest-cov

### Benefici Immediati:

✅ **Validazione robusta**: Previene errori utente comuni
✅ **Componenti riutilizzabili**: Riduce duplicazione futura
✅ **Test automatici**: Protegge da regressioni (64 test)
✅ **Backup sicurezza**: Versione funzionante sempre disponibile
✅ **Fondamenta solide**: Pronto per modularizzazione completa

---

## ✅ AGGIORNAMENTO 2026-01-19 (PARTE 1)

**Integrazione Vincoli Terziario CT 3.0 - COMPLETATA**:

### 1. Sidebar Rinnovata (linee 934-1015)
- Nuova selezione "Tipologia Edificio e Soggetto":
  * Residenziale - Privato
  * Residenziale - Condominio
  * Terziario - Impresa/ETS economico
  * PA / ETS non economico
- Mostra automaticamente se applicabile percentuale 100% per PA (art. 11 comma 2)
- Categoria catastale con suggerimenti basati su tipo edificio
- Input APE e riduzione energia primaria per terziario+impresa

### 2. Modulo vincoli_terziario.py esteso
- Aggiunta mappatura `MAPPA_CODICI_INTERVENTO` (linea 248-271)
- Nuova funzione `get_codice_intervento()` per conversione automatica
- Nuova funzione `verifica_vincoli_intervento_generico()` wrapper semplificato (linea 287-324)

### 3. Funzione helper centralizzata
- `applica_vincoli_terziario_ct3()` in app_streamlit.py (linea 575-623)
- Gestisce automaticamente mappatura tipo soggetto
- Applica vincoli per qualsiasi tipo intervento
- Ritorna (ammissibile, messaggio) per gestione uniforme

### 4. Applicazione vincoli per intervento - ✅ COMPLETATA
- ✅ **Pompe di Calore (III.A)**: Linee 756-788 + visualizzazione 1367-1372
- ✅ **Serramenti (II.B)**: Linee 4345-4355
- ✅ **Isolamento Termico (II.E, II.F)**: Linee 3958-3969
- ✅ **Schermature Solari (II.C)**: Linee 4868-4878
- ✅ **Illuminazione LED (II.H)**: Linee 5254-5265
- ✅ **Building Automation (II.D)**: Linee 5629-5639
- ✅ **FV Combinato (II.H)**: Linee 2902-2912

**Copertura completa**: Tutti gli interventi CT 3.0 implementano ora i vincoli terziario!

### 5. TAB Prenotazione - ✅ COMPLETATA (linee 7712-7974)

**Funzionalità implementate**:
- ✅ Verifica ammissibilità soggetto (PA, ETS non economico, ESCO)
- ✅ Utilizzo automatico ultimo incentivo calcolato da session_state
- ✅ Input manuale incentivo se non presente calcolo precedente
- ✅ 4 casistiche prenotazione (diagnosi, EPC, PPP, assegnazione)
- ✅ Opzioni erogazione: acconto (50% o 40%) e rata intermedia opzionale
- ✅ Preview percentuale acconto basata su anni erogazione
- ✅ Input data presentazione personalizzabile
- ✅ Simulazione completa con button
- ✅ Visualizzazione rateizzazione con tabella formattata
- ✅ Timeline con 4 date chiave (presentazione, ammissione, avvio, conclusione)
- ✅ 7 fasi processo in expander con documenti richiesti per fase
- ✅ Massimale preventivo vincolante

**Integrazione con moduli**:
- Utilizza `prenotazione.py`: `simula_prenotazione()`, `is_prenotazione_ammissibile()`
- Session state: `ultimo_incentivo`, `ultimo_numero_anni`
- Gestione errori e validazione completa

**Prossimi passi**:
1. ~~Implementare TAB "Prenotazione" nell'interfaccia~~ ✅ COMPLETATO
2. Aggiungere funzione `genera_report_prenotazione_html()` in report_generator (opzionale)
3. Test completo con scenari diversi (residenziale/terziario/PA)
4. Verifica percentuali 100% per PA su interventi Titolo II

## Stato Implementazione

### ✅ PUNTO 2 - Dati CT 3.0 Verificati

**Soglia 15.000€ già corretta** in `modules/calculator_ct.py`:
- Linea 125: `SOGLIA_RATA_UNICA: float = 15000.0`
- Linee 721-734: Logica erogazione corretta

**Nessuna azione richiesta** - Il codice usa già la soglia corretta del CT 3.0.

---

### ✅ PUNTO 3 - Vincoli Terziario/Imprese

**Nuovo modulo creato**: `modules/vincoli_terziario.py`

#### Funzionalità Implementate:

1. **Verifica categoria catastale** (residenziale vs terziario)
   - Categorie terziario: B, C, D, E
   - Categorie residenziale: A (escluso A/10)

2. **Esclusione PDC a gas per imprese su terziario**
   - Art. 25, comma 2: imprese/ETS economici NON possono installare PDC a gas

3. **Calcolo riduzione energia primaria richiesta**:
   - 10% per: II.B, II.E, II.F (singoli)
   - 20% per: II.B+altro Tit.II, II.E+altro Tit.II, II.F+altro Tit.II
   - 20% per: II.G, II.H, II.D (sempre)

4. **Verifica vincoli con APE**
   - Controllo riduzione effettiva vs richiesta
   - Obbligatorietà APE ante/post per terziario

#### Funzioni Principali:

```python
from modules.vincoli_terziario import (
    verifica_vincoli_terziario,
    is_terziario,
    calcola_riduzione_richiesta,
    get_interventi_soggetti_vincolo
)

# Esempio uso
risultato = verifica_vincoli_terziario(
    tipo_soggetto="Impresa",
    categoria_catastale="C/1",
    codice_intervento="II.B",
    multi_intervento=False,
    riduzione_energia_primaria_effettiva=0.12,  # 12%
    ape_disponibili=True
)

# risultato.vincolo_soddisfatto -> True/False
# risultato.messaggio -> Descrizione esito
```

#### Dove Integrare:

1. **app_streamlit.py** - Sezione input edificio:
   - Aggiungere campo "Categoria catastale"
   - Aggiungere toggle "APE disponibili"
   - Se APE disponibili: input "Riduzione energia primaria (%)"

2. **Tutti i calculator** (serramenti, isolamento, illuminazione, building automation, ricarica VE, FV):
   - Chiamare `verifica_vincoli_terziario()` prima del calcolo
   - Bloccare calcolo se `vincolo_soddisfatto=False`
   - Mostrare warning se `richiede_ape=True`

3. **calculator_ct.py** - Pompe di calore:
   - Verificare `pdc_gas_ammessa` prima di calcolare incentivo PDC gas

---

### ✅ PUNTO 5 - Procedura Prenotazione

**Nuovo modulo creato**: `modules/prenotazione.py`

#### Funzionalità Implementate:

1. **Verifica ammissibilità prenotazione**
   - Solo PA, ETS non economici, ESCO per loro conto
   - Privati e imprese: NO prenotazione

2. **Casistiche prenotazione** (Art. 7):
   - a) Diagnosi energetica
   - b) Contratto EPC
   - c) Partenariato Pubblico Privato (PPP)
   - d) Assegnazione lavori già avvenuta

3. **Calcolo acconti e rate**:
   - Acconto: 50% se 2 anni, 40% se 5 anni
   - Rata intermedia: al 50% avanzamento lavori (opzionale)
   - Saldo: a conclusione lavori
   - Rate annue: distribuzione successiva

4. **Timeline prenotazione**:
   - Avvio lavori: entro 90 gg da ammissione
   - Conclusione: 24 mesi (36 per PA)
   - Fasi complete del processo

5. **Massimale preventivo vincolante**

#### Funzioni Principali:

```python
from modules.prenotazione import (
    simula_prenotazione,
    calcola_rateizzazione_prenotazione,
    calcola_calendario_prenotazione,
    is_prenotazione_ammissibile
)

# Esempio simulazione completa
risultato = simula_prenotazione(
    tipo_soggetto="PA",
    incentivo_totale=50000.0,
    numero_anni=5,
    ha_diagnosi_energetica=True,
    include_acconto=True,
    include_rata_intermedia=True
)

# risultato.ammissibile -> True/False
# risultato.rateizzazione -> Dettaglio rate
# risultato.calendario -> Timeline
# risultato.fasi -> 7 fasi processo
```

#### Dove Integrare:

1. **app_streamlit.py** - Nuova TAB "Prenotazione":
   - Sezione "Verifica ammissibilità"
   - Input casistica (diagnosi/EPC/PPP/assegnazione)
   - Checkbox "Include acconto" e "Include rata intermedia"
   - Visualizzazione timeline con Gantt chart
   - Tabella rateizzazione dettagliata
   - Download piano prenotazione (PDF/Excel)

2. **report_generator.py**:
   - Nuova funzione `genera_report_prenotazione_html()`
   - Include timeline, fasi, rateizzazione, documenti richiesti

---

## Esempio Integrazione in Streamlit

### 1. Vincoli Terziario (Sezione Input):

```python
# In app_streamlit.py, sezione dati edificio

st.subheader("📋 Dati Edificio")

categoria_catastale = st.selectbox(
    "Categoria catastale",
    options=["Seleziona..."] + CATEGORIE_CATASTALI_RESIDENZIALE + CATEGORIE_CATASTALI_TERZIARIO,
    key="cat_catastale"
)

tipo_soggetto = st.selectbox(
    "Tipologia soggetto",
    options=["Privato", "Impresa", "PA", "ETS_economico", "ETS_non_economico"],
    key="tipo_soggetto"
)

# Solo se terziario + impresa
if is_terziario(categoria_catastale) and tipo_soggetto in ["Impresa", "ETS_economico"]:
    st.warning("⚠️ Edificio terziario + Impresa: vincoli specifici applicabili")

    # Input APE
    ape_disponibili = st.checkbox("APE ante e post-operam disponibili", key="ape_disp")

    if ape_disponibili:
        riduzione_ep = st.number_input(
            "Riduzione energia primaria effettiva (%)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.1,
            key="riduzione_ep",
            help="Da APE: (EP_ante - EP_post) / EP_ante × 100"
        )
    else:
        riduzione_ep = 0.0
        st.info("APE obbligatorie per verificare vincolo riduzione energia primaria")

# Prima del calcolo
if st.button("Calcola Incentivo"):
    # Verifica vincoli
    vincoli = verifica_vincoli_terziario(
        tipo_soggetto=tipo_soggetto,
        categoria_catastale=categoria_catastale,
        codice_intervento="II.B",  # Esempio
        tipo_pdc="elettrica",  # Se PDC
        riduzione_energia_primaria_effettiva=riduzione_ep/100,
        ape_disponibili=ape_disponibili
    )

    if not vincoli["vincolo_soddisfatto"]:
        st.error(vincoli["messaggio"])
        st.stop()

    # Procedi con calcolo...
```

### 2. Prenotazione (Nuova TAB):

```python
# In app_streamlit.py, nuova tab

tab_prenotazione = st.tabs(["...", "Prenotazione"])

with tab_prenotazione:
    st.header("🗓️ Simulazione Prenotazione")

    # Verifica ammissibilità
    ammissibile, motivo = is_prenotazione_ammissibile(tipo_soggetto)

    if not ammissibile:
        st.error(f"❌ {motivo}")
    else:
        st.success("✅ Soggetto ammesso a prenotazione")

        # Input casistica
        st.subheader("Tipo casistica")
        col1, col2 = st.columns(2)
        with col1:
            ha_diagnosi = st.checkbox("Diagnosi energetica disponibile")
            ha_epc = st.checkbox("Contratto EPC")
        with col2:
            e_ppp = st.checkbox("Partenariato Pubblico Privato")
            lavori_assegnati = st.checkbox("Lavori già assegnati")

        # Opzioni rateizzazione
        st.subheader("Opzioni erogazione")
        include_acconto = st.checkbox("Richiedi acconto", value=True)
        include_rata_int = st.checkbox("Richiedi rata intermedia al 50%", value=False)

        if st.button("Simula Prenotazione"):
            # Usa incentivo calcolato precedentemente
            incentivo = st.session_state.get("ultimo_incentivo", 50000)

            risultato = simula_prenotazione(
                tipo_soggetto=tipo_soggetto,
                incentivo_totale=incentivo,
                numero_anni=5,  # Da calcolo precedente
                ha_diagnosi_energetica=ha_diagnosi,
                ha_epc=ha_epc,
                e_ppp=e_ppp,
                lavori_assegnati=lavori_assegnati,
                include_acconto=include_acconto,
                include_rata_intermedia=include_rata_int
            )

            # Visualizza risultati
            st.subheader("📊 Rateizzazione")

            # Tabella rate
            df_rate = pd.DataFrame(risultato["rateizzazione"]["rate_dettaglio"])
            st.dataframe(df_rate)

            # Grafico waterfall
            fig = create_waterfall_chart(df_rate)
            st.plotly_chart(fig)

            # Timeline
            st.subheader("📅 Timeline Prenotazione")
            cal = risultato["calendario"]

            timeline_data = {
                "Fase": ["Presentazione", "Ammissione", "Avvio lavori", "Conclusione"],
                "Data": [cal["data_presentazione"], cal["data_prevista_ammissione"],
                        cal["data_limite_avvio_lavori"], cal["data_limite_conclusione_lavori"]]
            }
            st.table(timeline_data)

            # Fasi dettagliate
            st.subheader("📋 Fasi Processo")
            for fase in risultato["fasi"]:
                with st.expander(f"Fase {fase['numero']}: {fase['nome']}"):
                    st.write(fase["descrizione"])
                    st.write("**Documenti richiesti:**")
                    for doc in fase["documenti_richiesti"]:
                        st.write(f"- {doc}")
```

---

## Checklist Integrazione

### Vincoli Terziario:
- [x] Aggiungere campo categoria catastale in input edificio
- [x] Aggiungere selezione tipo soggetto
- [x] Aggiungere checkbox APE disponibili
- [x] Aggiungere input riduzione energia primaria
- [x] Importare `vincoli_terziario` in app_streamlit.py
- [x] Chiamare verifica prima di calcolo incentivo PDC (linee 756-788)
- [x] Mostrare warning/error se vincoli non soddisfatti (linee 1367-1372)
- [x] Bloccare PDC gas per imprese su terziario (implementato in vincoli)
- [x] Salvare incentivo in session_state per Prenotazione (linee 811-813)
- [x] Applicare stessa verifica agli altri calculator (serramenti, isolamento, illuminazione, building_automation, ricarica_veicoli, FV)

### Prenotazione:
- [x] Creare nuova TAB "Prenotazione" in app (linee 7712-7974)
- [x] Implementare verifica ammissibilità
- [x] Input casistiche (4 checkbox)
- [x] Input opzioni rateizzazione (acconto + rata intermedia)
- [x] Visualizzazione tabella rate con formatting
- [x] Timeline con date chiave (4 date principali)
- [x] Accordion fasi processo (7 fasi con documenti)
- [x] Visualizzazione massimale preventivo
- [ ] Aggiungere `genera_report_prenotazione_html()` in report_generator
- [ ] Download piano prenotazione PDF

### Test:
- [ ] Test vincoli terziario con vari scenari
- [ ] Test prenotazione PA vs privati
- [ ] Test calcolo acconti (2 anni vs 5 anni)
- [ ] Test timeline con varie date
- [ ] Verifica integrazione end-to-end

---

## Note Implementazione

1. **Import necessari** all'inizio di `app_streamlit.py`:
```python
from modules.vincoli_terziario import (
    verifica_vincoli_terziario,
    is_terziario,
    CATEGORIE_CATASTALI_TERZIARIO,
    CATEGORIE_CATASTALI_RESIDENZIALE
)
from modules.prenotazione import (
    simula_prenotazione,
    is_prenotazione_ammissibile
)
```

2. **Session state** da aggiungere:
```python
if 'ultimo_incentivo' not in st.session_state:
    st.session_state.ultimo_incentivo = 0.0
if 'ultimo_numero_anni' not in st.session_state:
    st.session_state.ultimo_numero_anni = 2
```

3. **Salvare risultati** dopo ogni calcolo per usarli in prenotazione:
```python
st.session_state.ultimo_incentivo = risultato["incentivo_totale"]
st.session_state.ultimo_numero_anni = risultato["erogazione"]["numero_rate"]
```

4. **Validazione APE**: Se possibile, aggiungere anche parser PDF APE per estrarre automaticamente i valori EP ante/post.

---

## Documentazione Aggiuntiva

- Vedi `Sintesi_CT3_Dati_Estratti.txt` per dettagli normativi completi
- Vedi `Regole_Extracted.txt` (linee 4866-4874) per classe 5 stelle biomassa
- Vedi presentazione `Presentazione_Conto_Termico_3.0.pdf` per overview CT 3.0
