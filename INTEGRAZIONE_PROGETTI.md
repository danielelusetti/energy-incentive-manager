# Integrazione Sistema Gestione Progetti Clienti

**Creato**: 2026-01-19
**Versione**: 1.0.0

---

## Panoramica

Il sistema gestione progetti permette di **salvare analisi di fattibilità per singoli clienti** e **recuperarle facilmente** per modifiche future.

### Funzionalità:
- ✅ Salvataggio progetti su **file JSON persistenti**
- ✅ **Ricerca** progetti per cliente/intervento/note
- ✅ **Modifica** progetti esistenti
- ✅ **Duplicazione** progetti (scenari alternativi)
- ✅ **Riepilogo** tutti i progetti di un cliente
- ✅ **Storico modifiche** con timestamp

---

## File Creati

```
modules/gestione_progetti.py    # Logica salvataggio/caricamento
data/
├── .gitignore                  # Protegge dati clienti
└── progetti/                   # Directory progetti (*.json)
    ├── mario_rossi_via_roma_20260119_143022.json
    ├── hotel_bella_vista_20260119_150315.json
    └── condominio_verde_20260119_161204.json
```

---

## Integrazione in app_streamlit.py

### 1. Import Modulo (Aggiungi in testa al file)

```python
# Dopo gli altri import
from modules.gestione_progetti import get_gestore_progetti
```

### 2. Sidebar - Campo Nome Cliente

**Aggiungi in sidebar dopo selezione edificio**:

```python
# ====== GESTIONE PROGETTI CLIENTE ======
st.sidebar.divider()
st.sidebar.subheader("📋 Gestione Progetto Cliente")

# Campo nome cliente
nome_cliente = st.sidebar.text_input(
    "Nome Cliente/Progetto",
    value=st.session_state.get("nome_cliente_corrente", ""),
    placeholder="es. Mario Rossi - Via Roma 10, Milano",
    help="Identifica progetto per salvarlo e recuperarlo in seguito",
    key="input_nome_cliente"
)

# Salva in session state
if nome_cliente:
    st.session_state.nome_cliente_corrente = nome_cliente

# Note progetto
note_progetto = st.sidebar.text_area(
    "Note Progetto (opzionale)",
    value=st.session_state.get("note_progetto", ""),
    placeholder="es. Cliente interessato a PDC + Isolamento",
    height=80,
    key="input_note_progetto"
)

if note_progetto:
    st.session_state.note_progetto = note_progetto
```

### 3. Salvataggio Progetto (Dopo Calcolo Incentivo)

**In ogni TAB, dopo il calcolo, aggiungi**:

```python
# Esempio nel TAB Pompe di Calore
if st.button("🧮 CALCOLA INCENTIVO", type="primary", key="btn_calcola_pdc"):

    # ... validazioni ...

    # Calcolo incentivo
    risultato = calcola_incentivo_pdc(
        tipo_pdc=tipo_pdc,
        scop=scop,
        potenza_utile=potenza_utile,
        # ... altri parametri ...
    )

    # Mostra risultato
    render_risultato_incentivo(risultato, "Pompa di Calore")

    # ===== SALVATAGGIO PROGETTO =====
    st.divider()
    st.subheader("💾 Salva Progetto Cliente")

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.session_state.get("nome_cliente_corrente"):
            st.info(f"Cliente: **{st.session_state.nome_cliente_corrente}**")
        else:
            st.warning("⚠️ Inserisci nome cliente in sidebar per salvare")

    with col2:
        if st.button("💾 SALVA", type="primary", disabled=not st.session_state.get("nome_cliente_corrente")):

            # Prepara dati input
            dati_input = {
                "tipo_pdc": tipo_pdc,
                "configurazione": configurazione,
                "scop": scop,
                "potenza_utile": potenza_utile,
                "temperatura_design": temperatura_design,
                "zona_climatica": zona_climatica,
                "tipo_soggetto": tipo_soggetto_principale,
                "categoria_catastale": st.session_state.get("categoria_catastale", ""),
                # ... altri input rilevanti ...
            }

            # Salva progetto
            gestore = get_gestore_progetti()
            successo, messaggio, progetto_id = gestore.salva_progetto(
                nome_cliente=st.session_state.nome_cliente_corrente,
                tipo_intervento="Pompa di Calore",
                risultato_calcolo=risultato,
                dati_input=dati_input,
                note=st.session_state.get("note_progetto", "")
            )

            if successo:
                st.success(f"✅ {messaggio}")
                st.session_state.ultimo_progetto_id = progetto_id
            else:
                st.error(f"❌ {messaggio}")
```

### 4. TAB "Progetti Clienti" (Nuovo TAB)

**Aggiungi nuovo TAB nell'elenco**:

```python
# Modifica definizione tabs
tab_calcolo, tab_solare, ..., tab_progetti, tab_report, tab_documenti = st.tabs([
    "🧮 Pompe di Calore",
    # ... altri TAB ...
    "📁 Progetti Clienti",  # ← NUOVO
    "📄 Genera Report",
    "📋 Documenti"
])

# Contenuto TAB Progetti
with tab_progetti:
    st.header("📁 Gestione Progetti Clienti")

    gestore = get_gestore_progetti()

    # ===== RICERCA PROGETTI =====
    st.subheader("🔍 Cerca Progetti")

    col1, col2 = st.columns([3, 1])

    with col1:
        query_ricerca = st.text_input(
            "Cerca per nome cliente, intervento o note",
            placeholder="es. Mario Rossi, Pompe, Milano...",
            key="query_ricerca_progetti"
        )

    with col2:
        campo_ricerca = st.selectbox(
            "Campo",
            options=["tutti", "cliente", "intervento", "note"],
            key="campo_ricerca_progetti"
        )

    # Esegui ricerca
    if query_ricerca:
        progetti_trovati = gestore.cerca_progetti(query_ricerca, campo_ricerca)
    else:
        progetti_trovati = gestore.lista_progetti()

    # ===== RISULTATI =====
    if progetti_trovati:
        st.success(f"Trovati {len(progetti_trovati)} progetti")

        for idx, progetto in enumerate(progetti_trovati):
            with st.expander(
                f"📄 {progetto['nome_cliente']} - {progetto['tipo_intervento']} "
                f"({progetto['data_creazione'][:10]})"
            ):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.write(f"**Cliente**: {progetto['nome_cliente']}")
                    st.write(f"**Intervento**: {progetto['tipo_intervento']}")
                    st.write(f"**Incentivo**: {progetto['incentivo_totale']:,.2f} €")

                with col2:
                    st.write(f"**Creato**: {progetto['data_creazione'][:16]}")
                    st.write(f"**Modificato**: {progetto['data_ultima_modifica'][:16]}")
                    if progetto['note']:
                        st.write(f"**Note**: {progetto['note'][:100]}...")

                with col3:
                    # Bottoni azione
                    if st.button("🔄 Carica", key=f"load_{idx}"):
                        # Carica progetto
                        filepath = Path(progetto['filepath'])
                        successo, dati, msg = gestore.carica_progetto(filepath)

                        if successo:
                            st.success("✅ Progetto caricato!")

                            # Ripopola session state con dati progetto
                            st.session_state.nome_cliente_corrente = dati['nome_cliente']
                            st.session_state.note_progetto = dati.get('note', '')

                            # Ripopola input (da implementare per ogni TAB)
                            for key, value in dati['dati_input'].items():
                                st.session_state[key] = value

                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

                    if st.button("📋 Duplica", key=f"dup_{idx}"):
                        filepath = Path(progetto['filepath'])
                        successo, msg, _ = gestore.duplica_progetto(filepath)
                        if successo:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

                    if st.button("🗑️ Elimina", key=f"del_{idx}"):
                        filepath = Path(progetto['filepath'])
                        successo, msg = gestore.elimina_progetto(filepath)
                        if successo:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

    else:
        st.info("Nessun progetto trovato. Calcola un incentivo e salvalo!")

    # ===== RIEPILOGO CLIENTE =====
    st.divider()
    st.subheader("📊 Riepilogo Cliente")

    cliente_riepilogo = st.text_input(
        "Nome cliente per riepilogo",
        key="cliente_riepilogo"
    )

    if cliente_riepilogo and st.button("📊 Genera Riepilogo"):
        riepilogo = gestore.esporta_riepilogo_cliente(cliente_riepilogo)

        if riepilogo['numero_progetti'] > 0:
            st.success(f"**{riepilogo['nome_cliente']}**: {riepilogo['numero_progetti']} progetti")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Incentivo Totale", f"{riepilogo['incentivo_totale']:,.2f} €")
                st.metric("Numero Progetti", riepilogo['numero_progetti'])

            with col2:
                st.write("**Interventi per tipo**:")
                for tipo, dati in riepilogo['interventi_per_tipo'].items():
                    st.write(f"- {tipo}: {dati['count']} ({dati['incentivo_totale']:,.2f} €)")

            # Esporta riepilogo
            if st.button("📥 Esporta Riepilogo CSV"):
                import pandas as pd
                df = pd.DataFrame(riepilogo['progetti'])
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    data=csv,
                    file_name=f"riepilogo_{cliente_riepilogo}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.warning(f"Nessun progetto trovato per '{cliente_riepilogo}'")
```

---

## Formato File Progetto (.json)

```json
{
  "versione": "1.0.0",
  "nome_cliente": "Mario Rossi - Via Roma 10, Milano",
  "progetto_id": "20260119_143022",
  "data_creazione": "2026-01-19T14:30:22.123456",
  "data_ultima_modifica": "2026-01-19T14:30:22.123456",
  "tipo_intervento": "Pompa di Calore",
  "risultato_calcolo": {
    "incentivo_totale": 12500.0,
    "costo_ammissibile": 25000.0,
    "erogazione": {
      "numero_rate": 1,
      "prima_rata": 12500.0
    },
    ...
  },
  "dati_input": {
    "tipo_pdc": "elettrica",
    "scop": 4.5,
    "potenza_utile": 25,
    "zona_climatica": "E",
    ...
  },
  "note": "Cliente interessato anche a isolamento termico",
  "storico_modifiche": [
    {
      "data": "2026-01-19T14:30:22.123456",
      "azione": "creazione",
      "utente": "Utente"
    }
  ]
}
```

---

## Workflow Tipico

### Scenario: Analisi PDC per Cliente

1. **Apri app** → Inserisci in sidebar:
   - Nome cliente: "Mario Rossi - Via Roma 10"
   - Note: "Interessato a sostituire caldaia gas"

2. **TAB Pompe di Calore**:
   - Inserisci dati tecnici
   - Click "CALCOLA INCENTIVO"
   - Visualizzi risultato
   - Click "💾 SALVA"

3. **File salvato**:
   ```
   data/progetti/mario_rossi_via_roma_10_20260119_143022.json
   ```

4. **Settimana dopo - Modifica progetto**:
   - TAB "Progetti Clienti"
   - Cerca "Mario Rossi"
   - Click "🔄 Carica"
   - Modifica parametri
   - Ricalcola
   - Click "💾 SALVA" (sovrascrive)

5. **Confronto scenari**:
   - Carica progetto
   - TAB "Progetti Clienti" → Click "📋 Duplica"
   - Modifica duplicato con scenario alternativo
   - Hai 2 scenari salvati per confronto

---

## Best Practices

### Naming Convention Clienti:
- ✅ `Mario Rossi - Via Roma 10, Milano`
- ✅ `Hotel Bella Vista - Progetto 2026`
- ✅ `Condominio Verde - Ristrutturazione`
- ❌ `progetto1` (poco descrittivo)
- ❌ `cliente` (troppo generico)

### Note Utili:
- Contesto richiesta cliente
- Vincoli particolari
- Alternative valutate
- Follow-up necessari

### Backup:
- I file sono in `data/progetti/`
- Fai backup periodico di questa directory
- I file sono JSON text (leggibili, versionabili)

---

## Esempio Pratico Completo

Vedi file: `esempi/esempio_workflow_cliente.py` (da creare)

---

## FAQ

**Q: Dove sono salvati i progetti?**
A: `data/progetti/*.json` - file JSON persistenti

**Q: Posso esportare i progetti?**
A: Sì, puoi copiare i file JSON o usare export CSV riepilogo

**Q: Perdo i progetti chiudendo l'app?**
A: NO! Sono salvati su file, non in session_state

**Q: Posso condividere progetti con colleghi?**
A: Sì, condividi il file `.json` del progetto

**Q: Come faccio backup?**
A: Copia directory `data/progetti/` periodicamente

**Q: Posso versioning progetti (Git)?**
A: NO, `.gitignore` protegge dati clienti. Usa backup manuale.

---

## Testing

```bash
# Test modulo gestione_progetti
cd "c:\Users\Utente\Desktop\energy tool"

python -c "
from modules.gestione_progetti import get_gestore_progetti

gestore = get_gestore_progetti()

# Salva test
successo, msg, pid = gestore.salva_progetto(
    nome_cliente='Test Cliente',
    tipo_intervento='PDC Test',
    risultato_calcolo={'incentivo_totale': 10000},
    dati_input={'test': 'value'},
    note='Progetto di test'
)

print(f'Salvataggio: {successo} - {msg}')

# Lista progetti
progetti = gestore.lista_progetti()
print(f'Progetti totali: {len(progetti)}')
"
```

---

**Prossimo Step**: Integra codice in `app_streamlit.py` seguendo questa guida!
