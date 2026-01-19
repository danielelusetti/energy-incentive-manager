# 📁 Guida Rapida - Gestione Progetti Clienti

**Energy Incentive Manager - Sistema Progetti Clienti**
Versione: 1.0.0
Data: 2026-01-19

---

## 🎯 Cosa Puoi Fare

Il sistema di gestione progetti clienti ti permette di:

✅ **Salvare** analisi di fattibilità per ogni cliente
✅ **Recuperare** progetti salvati in qualsiasi momento
✅ **Modificare** dati di progetti esistenti
✅ **Cercare** progetti per nome cliente, intervento o note
✅ **Duplicare** progetti per scenari alternativi
✅ **Esportare** riepiloghi completi per cliente
✅ **Confrontare** scenari multipli per stesso cliente

---

## 🚀 Come Funziona (3 Passi)

### PASSO 1: Compila Nome Cliente

Nella **sidebar sinistra** trovi la sezione "📁 Gestione Progetto Cliente":

```
┌─────────────────────────────────────┐
│ 📁 Gestione Progetto Cliente        │
├─────────────────────────────────────┤
│ Nome Cliente/Progetto               │
│ [Mario Rossi - Via Roma 10, MI]    │ ← Scrivi qui
│                                      │
│ Note Progetto (opzionale)           │
│ [Cliente interessato a PDC + Iso..] │ ← Note facoltative
└─────────────────────────────────────┘
```

**Consiglio**: Usa un formato standard, es:
- `Mario Rossi - Via Roma 10, Milano`
- `Azienda XYZ - Sede Torino`
- `Condominio ABC - Bologna`

### PASSO 2: Calcola l'Incentivo

1. Vai su uno dei TAB calcolo (es. "🔥 Pompe di Calore")
2. Compila i dati dell'intervento
3. Clicca **"Calcola Incentivo"**
4. Il risultato viene **automaticamente salvato** con il nome cliente

✨ **Il salvataggio è automatico!** Non serve premere "Salva" da nessuna parte.

### PASSO 3: Gestisci i Progetti

Vai sul TAB **"📁 Progetti Clienti"** per:

- **Vedere tutti i progetti salvati**
- **Cercare** un cliente specifico
- **Caricare** un progetto per modificarlo
- **Duplicare** un progetto per scenari alternativi
- **Eliminare** progetti non più necessari
- **Esportare** riepilogo completo cliente

---

## 📋 Funzionalità Dettagliate

### 1. Ricerca Progetti

```
┌─────────────────────────────────────────────┐
│ 🔍 Cerca progetti                            │
├─────────────────────────────────────────────┤
│ Query: [Mario]                    [Cerca]   │
│ Campo: [tutti] ▼                             │
└─────────────────────────────────────────────┘
```

**Campi ricerca**:
- `tutti` - Cerca in tutti i campi
- `cliente` - Solo nome cliente
- `intervento` - Solo tipo intervento
- `note` - Solo note progetto

**Esempio**: Cerca "Milano" per trovare tutti i clienti di Milano

### 2. Vista Progetti

Ogni progetto mostra:

```
┌─────────────────────────────────────────────────────────────┐
│ 📄 Mario Rossi - Via Roma 10, Milano - Pompe di Calore  ▼  │
├─────────────────────────────────────────────────────────────┤
│ Tipo Intervento: Pompe di Calore                            │
│ Data Creazione: 2026-01-19 10:30:15                         │
│ Ultima Modifica: 2026-01-19 10:30:15                        │
│                                                              │
│ 💰 Incentivo Totale: EUR 45,000.00                          │
│                                                              │
│ 📝 Note: Cliente interessato anche a isolamento termico     │
│                                                              │
│ [📥 Carica] [📋 Duplica] [🗑️ Elimina]                      │
└─────────────────────────────────────────────────────────────┘
```

### 3. Azioni Disponibili

#### 📥 Carica Progetto

**Cosa fa**: Carica i dati del progetto nei campi del TAB di calcolo

**Quando usarlo**:
- Vuoi modificare un'analisi esistente
- Vuoi rivedere i dati inseriti
- Vuoi rifare il calcolo con piccole modifiche

**Come funziona**:
1. Clicca **"📥 Carica"** sul progetto
2. Vai sul TAB del tipo intervento (es. "🔥 Pompe di Calore")
3. Trovi tutti i campi già compilati con i dati salvati
4. Modifica quello che serve
5. Clicca "Calcola Incentivo" per aggiornare

#### 📋 Duplica Progetto

**Cosa fa**: Crea una copia del progetto con nuovo nome

**Quando usarlo**:
- Vuoi testare uno scenario alternativo
- Vuoi confrontare due soluzioni diverse
- Stesso cliente, edificio diverso

**Come funziona**:
1. Clicca **"📋 Duplica"**
2. Inserisci nuovo nome (es. "Mario Rossi - Scenario B")
3. Il progetto viene copiato con tutti i dati
4. Puoi modificarlo indipendentemente dall'originale

#### 🗑️ Elimina Progetto

**Cosa fa**: Rimuove definitivamente il progetto

**Sicurezza**: Richiede conferma con doppio click

**Come funziona**:
1. Clicca **"🗑️ Elimina"** (prima volta)
2. Il bottone diventa **"⚠️ Conferma Eliminazione"**
3. Clicca di nuovo per confermare
4. Il progetto viene eliminato permanentemente

### 4. Riepilogo Cliente

**Cosa fa**: Genera un rapporto completo di tutti i progetti di un cliente

```
┌─────────────────────────────────────────────┐
│ 📊 Riepilogo Completo Cliente                │
├─────────────────────────────────────────────┤
│ Nome Cliente: [Mario Rossi]     [Genera]   │
└─────────────────────────────────────────────┘
```

**Il riepilogo mostra**:
- **Numero totale progetti** per il cliente
- **Incentivo totale** cumulativo
- **Breakdown per tipo intervento**:
  - Pompe di Calore: 2 progetti, EUR 90,000
  - Isolamento Termico: 1 progetto, EUR 30,000
  - ecc.
- **Prima e ultima data progetto**

**Export CSV**: Puoi scaricare il riepilogo come file CSV per Excel

---

## 💡 Esempi d'Uso

### Scenario 1: Nuovo Cliente

1. Cliente chiama per preventivo PDC
2. Compili "Mario Rossi - Via Roma 10" in sidebar
3. Vai su TAB "🔥 Pompe di Calore"
4. Inserisci dati edificio e sistema
5. Calcoli incentivo
6. **Automaticamente salvato!**

### Scenario 2: Cliente Richiama

1. Cliente Mario Rossi chiama dopo 1 settimana
2. Vai su TAB "📁 Progetti Clienti"
3. Cerchi "Mario Rossi"
4. Clicchi **"📥 Carica"** sul progetto
5. Modifichi i dati necessari
6. Ricalcoli - salvataggio automatico con nuova data

### Scenario 3: Confronto Scenari

1. Cliente vuole confrontare PDC vs Caldaia a Biomassa
2. Hai già salvato scenario PDC
3. Vai su TAB "📁 Progetti Clienti"
4. Clicchi **"📋 Duplica"** sul progetto PDC
5. Rinomini "Mario Rossi - Scenario Biomassa"
6. Vai su TAB "🌲 Biomassa"
7. Calcoli con dati caldaia
8. Ora hai 2 progetti da confrontare

### Scenario 4: Report Cliente

1. Cliente ha fatto 5 analisi diverse
2. Vai su TAB "📁 Progetti Clienti"
3. Sezione "Riepilogo Cliente"
4. Inserisci "Mario Rossi"
5. Clicchi **"Genera Riepilogo"**
6. Vedi totale incentivi, breakdown interventi
7. Clicchi **"💾 Esporta CSV"** per inviare al cliente

---

## 🗂️ Organizzazione File

I progetti vengono salvati in:

```
energy tool/
└── data/
    └── progetti/
        ├── mario_rossi_-_via_roma_10_20260119_103015.json
        ├── mario_rossi_-_scenario_b_20260119_110530.json
        ├── azienda_xyz_-_sede_torino_20260119_143022.json
        └── ...
```

**Nome file**: `{cliente_sanitizzato}_{timestamp}.json`

**Formato timestamp**: `AAAAMMGG_HHMMSS`

**Esempio**:
- Cliente: "Mario Rossi - Via Roma 10"
- Data: 19/01/2026 10:30:15
- File: `mario_rossi_-_via_roma_10_20260119_103015.json`

### Contenuto File Progetto

Ogni file JSON contiene:

```json
{
  "versione": "1.0.0",
  "nome_cliente": "Mario Rossi - Via Roma 10, Milano",
  "progetto_id": "20260119_103015",
  "data_creazione": "2026-01-19T10:30:15.123456",
  "data_ultima_modifica": "2026-01-19T10:30:15.123456",
  "tipo_intervento": "Pompe di Calore",
  "risultato_calcolo": {
    "incentivo_totale": 45000,
    "incentivo_annuale": 9000,
    "durata_anni": 5,
    ...
  },
  "dati_input": {
    "superficie": 120,
    "potenza": 15,
    "cop": 4.5,
    ...
  },
  "note": "Cliente interessato a PDC + Isolamento",
  "storico_modifiche": [
    {
      "data": "2026-01-19T10:30:15",
      "azione": "creazione",
      "utente": "Utente"
    }
  ]
}
```

---

## 🔒 Sicurezza Dati

### Protezione Privacy

I file progetti **NON vengono inviati a Git** (se usi version control).

Il file `.gitignore` nella directory `data/` contiene:

```gitignore
# Ignora tutti i file progetti (dati clienti sensibili)
progetti/*.json

# Mantieni directory
!.gitignore
```

Questo assicura che i dati sensibili dei clienti rimangano solo sul tuo computer.

### Backup Consigliati

**Best Practice**:
1. **Backup giornaliero**: Copia directory `data/progetti/` su drive esterno
2. **Backup settimanale**: Upload su cloud personale (Google Drive, OneDrive)
3. **Backup pre-modifica**: Prima di eliminazioni massive

**Script Backup Rapido**:

```bash
# Windows
xcopy "data\progetti" "D:\backup\progetti_%date:~-4,4%%date:~-10,2%%date:~-7,2%" /E /I

# Linux/Mac
cp -r data/progetti ~/backup/progetti_$(date +%Y%m%d)
```

---

## ❓ FAQ

### Q: Cosa succede se non compilo "Nome Cliente"?

**R**: Il progetto viene salvato comunque, ma con nome generico tipo "progetto_20260119_103015". Consigliato sempre compilare il nome per ritrovare facilmente i progetti.

### Q: Posso modificare un progetto salvato?

**R**: Sì! Clicca "📥 Carica" sul progetto nel TAB "Progetti Clienti", vai sul TAB di calcolo, modifica i dati e ricalcola. Viene salvato automaticamente con nuova data modifica.

### Q: Come faccio a confrontare 2 scenari?

**R**: Usa la funzione "📋 Duplica" per creare una copia del progetto con nome diverso (es. "Cliente X - Scenario A" e "Cliente X - Scenario B"). Poi puoi visualizzarli entrambi nel TAB Progetti.

### Q: Cosa succede se elimino per sbaglio?

**R**: L'eliminazione è **permanente**. Per sicurezza, il sistema richiede doppio click. Se hai fatto backup regolari, puoi recuperare da lì.

### Q: Posso esportare i dati?

**R**: Sì! Usa la funzione "Riepilogo Cliente" e clicca "💾 Esporta CSV" per ottenere un file Excel con tutti i progetti del cliente.

### Q: I progetti sono salvati nel cloud?

**R**: No, sono salvati **localmente** sul tuo computer nella directory `data/progetti/`. Questo garantisce privacy dei dati clienti. Se vuoi backup cloud, devi farlo manualmente.

### Q: Cosa contiene il file JSON del progetto?

**R**: Tutti i dati inseriti (superficie, potenza, COP, ecc.), i risultati del calcolo (incentivo totale, annuale, ecc.), le note, e lo storico modifiche.

### Q: Posso cercare progetti per data?

**R**: Attualmente la ricerca è per nome cliente, tipo intervento e note. I progetti sono comunque ordinati per data (più recenti prima).

### Q: Posso usare lo stesso nome cliente per progetti diversi?

**R**: Sì! Ogni progetto ha un timestamp unico nel nome file. Puoi avere "Mario Rossi" con 10 progetti diversi. Usa il campo "Note" per distinguerli (es. "PDC residenza principale", "PDC casa vacanze").

### Q: Il riepilogo cliente somma tutti i progetti?

**R**: Sì, il riepilogo mostra:
- Numero totale progetti
- Somma incentivi totali
- Breakdown per tipo intervento
Utile per vedere il "potenziale totale" di un cliente con edifici multipli.

---

## 🎓 Best Practices

### Naming Convention Clienti

**Consigliato**:
- `Nome Cognome - Indirizzo, Città` (es. "Mario Rossi - Via Roma 10, Milano")
- `Azienda - Sede` (es. "XYZ Srl - Stabilimento Torino")
- `Condominio - Indirizzo` (es. "Condominio Giardini - Via Verdi 5, Bologna")

**Evita**:
- Nomi troppo generici ("Cliente 1", "Test", ecc.)
- Caratteri speciali eccessivi (`<>:"/\|?*`)
- Nomi troppo lunghi (max 100 caratteri)

### Uso delle Note

Le note sono preziose per:
- **Preferenze cliente**: "Preferisce PDC aria-acqua"
- **Vincoli edificio**: "Edificio sottoposto a vincolo paesaggistico"
- **Scenari**: "Scenario con incentivo massimo"
- **Stato lavorazione**: "In attesa documenti APE"
- **Follow-up**: "Richiamare tra 2 settimane"

### Workflow Consigliato

1. **Prima visita cliente**:
   - Crea progetto con dati rilevati
   - Note: "Prima analisi - dati da verificare"

2. **Dopo sopralluogo**:
   - Carica progetto
   - Aggiorna con dati corretti
   - Note: "Dati aggiornati post-sopralluogo"

3. **Scenario alternativo**:
   - Duplica progetto originale
   - Rinomina con "- Scenario B"
   - Modifica parametri

4. **Presentazione cliente**:
   - Genera riepilogo cliente
   - Esporta CSV
   - Allega a preventivo

---

## 🔧 Troubleshooting

### Problema: Non vedo i miei progetti nel TAB Progetti

**Soluzione**:
1. Verifica di aver compilato "Nome Cliente" prima di calcolare
2. Controlla directory `data/progetti/` - devono esserci file `.json`
3. Prova ricerca con campo "tutti" e query vuota per vedere tutti i progetti

### Problema: Errore "File non trovato" quando carico progetto

**Soluzione**:
1. Possibile file cancellato manualmente
2. Ricarica la pagina Streamlit (F5)
3. Verifica integrità file JSON (aprilo con editor testo)

### Problema: Ricerca non trova progetti esistenti

**Soluzione**:
1. La ricerca è case-insensitive ma deve trovare match parziale
2. Prova con query più breve (es. "Mario" invece di "Mario Rossi - Via...")
3. Prova campo "tutti" invece di campo specifico

### Problema: Duplicazione crea nome identico

**Soluzione**:
1. Modifica il nome nel campo che appare
2. Ogni file ha timestamp unico, non ci sono conflitti anche con stesso nome

---

## 📞 Supporto

Per problemi tecnici o domande:

1. Controlla questa guida
2. Leggi `QUICK_START.md` per tutorial rapidi
3. Leggi `INTEGRAZIONE_PROGETTI.md` per dettagli tecnici
4. Verifica file `test_integration.py` per test funzionalità

---

## 🎉 Conclusione

Il sistema Gestione Progetti Clienti ti permette di:

✅ Organizzare tutte le analisi per cliente
✅ Ritrovare rapidamente progetti passati
✅ Confrontare scenari multipli
✅ Generare report professionali
✅ Proteggere dati sensibili

**Inizia subito**:
1. Apri [http://localhost:8501](http://localhost:8501)
2. Compila "Nome Cliente" in sidebar
3. Calcola un incentivo
4. Vai su TAB "📁 Progetti Clienti"

**Buon lavoro!** 🚀

---

*Guida creata: 2026-01-19*
*Energy Incentive Manager - CT 3.0*
*Versione: 1.0.0*
