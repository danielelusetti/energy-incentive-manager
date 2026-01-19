"""
Modulo per la generazione di relazioni tecniche PDF.

Genera report professionali per il confronto tra incentivi CT ed Ecobonus,
inclusi scenari multipli di pompe di calore, solare termico e FV combinato.

Riferimento normativo: DM 7/8/2025, D.L. 63/2013
Autore: EnergyIncentiveManager
Versione: 2.0.0
"""

import io
from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass, field


@dataclass
class ScenarioCalcolo:
    """Rappresenta uno scenario di calcolo per una pompa di calore."""
    nome: str
    tipo_intervento: str
    tipo_intervento_label: str
    potenza_kw: float
    scop: float
    eta_s: float
    eta_s_min: int
    zona_climatica: str
    gwp: str
    bassa_temperatura: bool
    spesa: float

    # Risultati CT
    ct_ammissibile: bool
    ct_incentivo: float
    ct_rate: list
    ct_annualita: int
    ct_kp: float
    ct_ei: float
    ct_ci: float
    ct_quf: int

    # Risultati Ecobonus
    eco_ammissibile: bool
    eco_detrazione: float
    eco_aliquota: float

    # NPV
    npv_ct: float
    npv_eco: float

    # Dati FV combinato (opzionali, presenti se abbinato a FV)
    fv_abbinato: bool = False
    fv_potenza_kw: float = 0.0
    fv_spesa: float = 0.0
    fv_capacita_accumulo_kwh: float = 0.0
    fv_spesa_accumulo: float = 0.0
    fv_produzione_stimata_kwh: float = 0.0
    fv_incentivo_ct: float = 0.0
    fv_bonus_ristrutt: float = 0.0
    fv_registro_tecnologie: str = ""
    fv_npv_ct: float = 0.0
    fv_npv_bonus: float = 0.0


@dataclass
class ScenarioSolareTermico:
    """Rappresenta uno scenario di calcolo per solare termico (III.D)."""
    nome: str
    tipologia_impianto: str  # acs_solo, acs_riscaldamento, solar_cooling, processo
    tipologia_label: str
    tipo_collettore: str  # piano, sottovuoto, concentrazione, factory_made
    tipo_collettore_label: str
    superficie_m2: float
    n_moduli: int
    area_modulo_m2: float
    producibilita_qu: float  # kWht/m²
    spesa: float

    # Risultati CT
    ct_ammissibile: bool
    ct_incentivo: float
    ct_rate: list
    ct_annualita: int
    ct_ci: float  # Coefficiente valorizzazione
    ct_ia: float  # Incentivo annuo

    # Risultati Ecobonus
    eco_ammissibile: bool
    eco_detrazione: float
    eco_aliquota: float

    # NPV
    npv_ct: float
    npv_eco: float


@dataclass
class ScenarioFVCombinato:
    """Rappresenta uno scenario di calcolo per FV combinato (II.H) standalone."""
    nome: str
    potenza_fv_kw: float
    spesa_fv: float
    capacita_accumulo_kwh: float
    spesa_accumulo: float
    produzione_stimata_kwh: float
    fabbisogno_elettrico_kwh: float
    fabbisogno_termico_equiv_kwh: float
    registro_tecnologie: str

    # Dati PdC abbinata (obbligatoria)
    pdc_tipo_intervento: str
    pdc_tipo_label: str
    pdc_potenza_kw: float
    pdc_incentivo_ct: float

    # Risultati CT FV
    ct_ammissibile: bool
    ct_incentivo: float
    ct_rate: list
    ct_annualita: int
    ct_percentuale: float

    # Risultati Bonus Ristrutturazione FV
    bonus_ammissibile: bool
    bonus_detrazione: float
    bonus_aliquota: float

    # NPV
    npv_ct: float
    npv_bonus: float
    spesa_totale: float = 0.0

    def __post_init__(self):
        self.spesa_totale = self.spesa_fv + self.spesa_accumulo


@dataclass
class ScenarioScaldacqua:
    """Rappresenta uno scenario di calcolo per scaldacqua a pompa di calore (III.E)."""
    nome: str
    classe_energetica: str
    capacita_litri: int
    potenza_kw: float
    spesa_lavori: float
    spesa_tecnici: float
    tipo_soggetto: str
    abitazione_principale: bool
    iter_semplificato: bool = False
    prodotto_marca: str = ""
    prodotto_modello: str = ""

    # Risultati CT
    ct_incentivo: float = 0.0
    ct_npv: float = 0.0
    ct_anni_erogazione: int = 2

    # Risultati Ecobonus
    eco_detrazione: float = 0.0
    eco_npv: float = 0.0
    eco_anni_recupero: int = 10

    # Confronto
    piu_conveniente: str = "CT"
    differenza_npv: float = 0.0


@dataclass
class ScenarioIbridi:
    """Rappresenta uno scenario di calcolo per sistemi ibridi (III.B)."""
    nome: str
    tipo_sistema: str  # ibrido_factory_made, bivalente, add_on
    potenza_pdc_kw: float
    potenza_caldaia_kw: float
    scop: float
    eta_s_caldaia: float
    spesa: float
    tipo_soggetto: str
    iter_semplificato: bool = False
    prodotto_marca: str = ""
    prodotto_modello_pdc: str = ""
    prodotto_modello_caldaia: str = ""

    # Risultati CT
    ct_incentivo: float = 0.0
    ct_npv: float = 0.0

    # Risultati Ecobonus
    eco_detrazione: float = 0.0
    eco_npv: float = 0.0

    # Risultati Bonus Ristrutturazione
    bonus_detrazione: float = 0.0
    bonus_npv: float = 0.0

    # Confronto
    migliore: str = "CT"


@dataclass
class ScenarioIsolamento:
    """Rappresenta uno scenario di calcolo per isolamento termico (II.A)."""
    nome: str
    tipo_superficie: str  # coperture, pavimenti, pareti
    posizione: str  # esterno, interno, ventilato
    zona_climatica: str
    superficie_mq: float
    spesa_totale: float
    trasmittanza_post: float
    tipo_soggetto: str

    # Risultati CT
    ct_incentivo: float = 0.0
    ct_npv: float = 0.0

    # Risultati Ecobonus
    eco_detrazione: float = 0.0
    eco_npv: float = 0.0

    # Risultati Bonus Ristrutturazione
    bonus_detrazione: float = 0.0
    bonus_npv: float = 0.0

    # Confronto
    migliore: str = "CT"


@dataclass
class ScenarioSerramenti:
    """Rappresenta uno scenario di calcolo per sostituzione serramenti."""
    nome: str
    zona_climatica: str
    superficie_mq: float
    trasmittanza_post: float
    spesa_totale: float
    tipo_soggetto: str

    # Risultati (dipende da quali sono ammissibili)
    ct_incentivo: float = 0.0
    ct_npv: float = 0.0
    eco_detrazione: float = 0.0
    eco_npv: float = 0.0
    bonus_detrazione: float = 0.0
    bonus_npv: float = 0.0

    # Confronto
    migliore: str = ""


@dataclass
class ScenarioBuildingAutomation:
    """Rappresenta uno scenario di calcolo per building automation (II.F)."""
    nome: str
    superficie_mq: float
    classe_efficienza: str
    spesa: float
    tipo_soggetto: str

    # Risultati CT
    ct_incentivo: float = 0.0
    ct_npv: float = 0.0

    # Risultati Ecobonus
    eco_detrazione: float = 0.0
    eco_npv: float = 0.0

    # Risultati Bonus Ristrutturazione
    bonus_detrazione: float = 0.0
    bonus_npv: float = 0.0

    # Confronto
    migliore: str = "CT"


@dataclass
class InterventoMulti:
    """Rappresenta un singolo intervento all'interno di un multi-intervento."""
    tipo: str  # Es: "ii_a", "iii_a"
    tipo_label: str  # Es: "Isolamento Termico (II.A)"
    nome: str  # Nome personalizzato
    spesa_totale: float
    ct_incentivo: float
    eco_detrazione: float
    dati: dict  # Dati tecnici dettagliati (opzionale)


@dataclass
class ScenarioMultiIntervento:
    """Rappresenta un progetto multi-intervento (più interventi sullo stesso edificio)."""
    # Dati progetto
    nome_progetto: str
    tipo_soggetto: str  # "privato", "impresa", "pa", "ets_economico"
    tipo_edificio: str  # "residenziale", "terziario", "pubblico"
    indirizzo: str

    # Lista interventi
    interventi: list[InterventoMulti]

    # Dati aggregati
    spesa_totale: float
    ct_incentivo_base: float
    ct_bonus_multi_5: float = 0.0  # Bonus +5% per imprese su Titolo II multi-intervento
    ct_bonus_multi_15: float = 0.0  # Bonus +15% per riduzione EP ≥40%
    ct_incentivo_totale: float = 0.0
    ct_npv: float = 0.0

    eco_detrazione_totale: float = 0.0
    eco_npv: float = 0.0

    # Opzionali per Fase 2
    riduzione_ep_perc: float = None  # Riduzione energia primaria (per bonus +15%)
    ape_ante_operam: float = None
    ape_post_operam: float = None
    data_conclusione: str = None  # Data conclusione ultimo intervento

    # Confronto
    piu_conveniente: str = "CT"
    differenza_npv: float = 0.0


def genera_report_html(
    scenari: list[ScenarioCalcolo],
    tipo_soggetto: str,
    tipo_abitazione: str,
    anno: int,
    tasso_sconto: float,
    include_grafici: bool = True,
    solo_ct: bool = False
) -> str:
    """
    Genera un report HTML professionale con confronto scenari.

    Args:
        scenari: Lista di scenari calcolati
        tipo_soggetto: Tipo di soggetto richiedente
        tipo_abitazione: Tipo di abitazione
        anno: Anno della spesa
        tasso_sconto: Tasso di sconto per NPV
        include_grafici: Se includere grafici nel report
        solo_ct: Se True, genera report solo con Conto Termico (senza Ecobonus)

    Returns:
        Stringa HTML del report
    """
    data_report = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relazione Tecnica - Incentivi Energetici</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: white;
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #1E88E5;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #1E88E5;
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .meta-info {{
            display: flex;
            justify-content: space-between;
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 25px;
            font-size: 12px;
        }}
        h2 {{
            color: #1E88E5;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
            margin: 25px 0 15px 0;
            font-size: 18px;
        }}
        h3 {{
            color: #333;
            margin: 20px 0 10px 0;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 12px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background-color: #1E88E5;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .highlight {{
            background-color: #e8f5e9 !important;
            font-weight: bold;
        }}
        .scenario-box {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            background: #fafafa;
        }}
        .scenario-title {{
            font-weight: bold;
            color: #1E88E5;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }}
        .metric-label {{
            color: #666;
        }}
        .metric-value {{
            font-weight: bold;
        }}
        .positive {{
            color: #2E7D32;
        }}
        .negative {{
            color: #C62828;
        }}
        .recommendation {{
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border-left: 4px solid #2E7D32;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .recommendation h3 {{
            color: #2E7D32;
            margin-bottom: 10px;
        }}
        .formula-box {{
            background: #fff3e0;
            border: 1px solid #ffcc80;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        .note {{
            background: #e3f2fd;
            border-left: 4px solid #1E88E5;
            padding: 10px 15px;
            margin: 15px 0;
            font-size: 11px;
            color: #0D47A1;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 10px;
            color: #999;
            text-align: center;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}
        .comparison-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .comparison-card.ct {{
            border-color: #2E7D32;
            background: linear-gradient(to bottom, #e8f5e9, white);
        }}
        .comparison-card.eco {{
            border-color: #1565C0;
            background: linear-gradient(to bottom, #e3f2fd, white);
        }}
        .comparison-card h4 {{
            margin-bottom: 10px;
        }}
        .comparison-card.ct h4 {{
            color: #2E7D32;
        }}
        .comparison-card.eco h4 {{
            color: #1565C0;
        }}
        .big-number {{
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .ct .big-number {{
            color: #2E7D32;
        }}
        .eco .big-number {{
            color: #1565C0;
        }}
        @media print {{
            body {{
                padding: 10mm;
            }}
            .page-break {{
                page-break-before: always;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>RELAZIONE TECNICA</h1>
        <div class="subtitle">{"Analisi Incentivo Energetico" if solo_ct else "Analisi Comparativa Incentivi Energetici"}</div>
        <div class="subtitle">{"Conto Termico 3.0 (DM 7/8/2025)" if solo_ct else "Conto Termico 3.0 (DM 7/8/2025) vs Ecobonus"}</div>
    </div>

    <div class="meta-info">
        <div><strong>Data:</strong> {data_report}</div>
        <div><strong>Soggetto:</strong> {tipo_soggetto.replace('_', ' ').title()}</div>
        <div><strong>Abitazione:</strong> {tipo_abitazione.replace('_', ' ').title()}</div>
        <div><strong>Anno spesa:</strong> {anno}</div>
    </div>

    <h2>1. Premessa</h2>
    <p>
        {"La presente relazione tecnica analizza l'incentivazione disponibile per l'installazione di pompe di calore tramite il <strong>Conto Termico 3.0</strong> (DM 7 agosto 2025)." if solo_ct else "La presente relazione tecnica analizza le opzioni di incentivazione disponibili per l'installazione di pompe di calore, confrontando il <strong>Conto Termico 3.0</strong> (DM 7 agosto 2025) con l'<strong>Ecobonus</strong> (D.L. 63/2013 e s.m.i.)."}
    </p>
    {"" if solo_ct else f'''<p style="margin-top: 10px;">
        L'analisi include il calcolo del <strong>Valore Attuale Netto (NPV)</strong> con un tasso
        di sconto del {tasso_sconto*100:.1f}% per una corretta valutazione finanziaria delle
        diverse opzioni temporali di erogazione.
    </p>'''}
"""

    # Sezione 2: Scenari analizzati
    html += """
    <h2>2. Scenari Analizzati</h2>
    <p>Sono stati analizzati i seguenti {n} scenari di installazione:</p>
""".format(n=len(scenari))

    for i, scenario in enumerate(scenari, 1):
        # Sezione PdC
        html += f"""
    <div class="scenario-box">
        <div class="scenario-title">Scenario {i}: {scenario.nome}</div>
        <table>
            <tr>
                <th colspan="4">🌡️ Pompa di Calore (III.A)</th>
            </tr>
            <tr>
                <td><strong>Tipologia:</strong></td>
                <td>{scenario.tipo_intervento_label}</td>
                <td><strong>Spesa PdC:</strong></td>
                <td>{scenario.spesa:,.2f} EUR</td>
            </tr>
            <tr>
                <td><strong>Potenza nominale:</strong></td>
                <td>{scenario.potenza_kw} kW</td>
                <td><strong>Zona climatica:</strong></td>
                <td>{scenario.zona_climatica}</td>
            </tr>
            <tr>
                <td><strong>SCOP dichiarato:</strong></td>
                <td>{scenario.scop}</td>
                <td><strong>GWP refrigerante:</strong></td>
                <td>{scenario.gwp}</td>
            </tr>
            <tr>
                <td><strong>η_s dichiarata:</strong></td>
                <td>{scenario.eta_s}%</td>
                <td><strong>η_s min Ecodesign:</strong></td>
                <td>{scenario.eta_s_min}%</td>
            </tr>
        </table>"""

        # Sezione FV se abbinato
        if getattr(scenario, 'fv_abbinato', False) and scenario.fv_potenza_kw > 0:
            registro_label = {
                "sezione_a": "Sez. A (+5%)",
                "sezione_b": "Sez. B (+10%)",
                "sezione_c": "Sez. C (+15%)",
                "nessuno": "Nessuno",
                "": "Nessuno"
            }.get(scenario.fv_registro_tecnologie, "Nessuno")

            html += f"""
        <table style="margin-top: 15px;">
            <tr>
                <th colspan="4">🔆 Fotovoltaico Combinato (II.H)</th>
            </tr>
            <tr>
                <td><strong>Potenza FV:</strong></td>
                <td>{scenario.fv_potenza_kw:.1f} kWp</td>
                <td><strong>Spesa FV:</strong></td>
                <td>{scenario.fv_spesa:,.2f} EUR</td>
            </tr>
            <tr>
                <td><strong>Accumulo:</strong></td>
                <td>{scenario.fv_capacita_accumulo_kwh:.1f} kWh</td>
                <td><strong>Spesa accumulo:</strong></td>
                <td>{scenario.fv_spesa_accumulo:,.2f} EUR</td>
            </tr>
            <tr>
                <td><strong>Produzione stimata:</strong></td>
                <td>{scenario.fv_produzione_stimata_kwh:,.0f} kWh/anno</td>
                <td><strong>Registro tecnologie:</strong></td>
                <td>{registro_label}</td>
            </tr>
            <tr>
                <td><strong>Spesa totale intervento:</strong></td>
                <td colspan="3"><strong>{scenario.spesa + scenario.fv_spesa + scenario.fv_spesa_accumulo:,.2f} EUR</strong></td>
            </tr>
        </table>"""

        html += """
    </div>
"""

    # Sezione 3: Metodologia di calcolo
    html += """
    <h2>3. Metodologia di Calcolo</h2>

    <h3>3.1 Conto Termico 3.0</h3>
    <p>Il calcolo dell'incentivo segue le formule previste dall'Allegato 2 del DM 7/8/2025:</p>

    <div class="formula-box">
        <strong>Formula incentivo annuo:</strong> I<sub>a</sub> = E<sub>i</sub> × C<sub>i</sub><br><br>
        <strong>Energia termica incentivata:</strong> E<sub>i</sub> = Q<sub>u</sub> × (1 - 1/SCOP) × k<sub>p</sub><br><br>
        <strong>Calore totale prodotto:</strong> Q<sub>u</sub> = P<sub>rated</sub> × Q<sub>uf</sub><br><br>
        <strong>Coefficiente premialità:</strong> k<sub>p</sub> = η<sub>s</sub> / η<sub>s,min</sub>
    </div>

    <div class="note">
        <strong>Nota:</strong> Il coefficiente k<sub>p</sub> viene calcolato utilizzando l'efficienza
        stagionale (η_s) come previsto dalla normativa, garantendo maggiore precisione rispetto
        al metodo basato su SCOP/SCOP_min.
    </div>
"""

    if not solo_ct:
        html += """
    <h3>3.2 Ecobonus</h3>
    <p>La detrazione fiscale è calcolata secondo il D.L. 63/2013 e Legge di Bilancio 2025:</p>

    <div class="formula-box">
        <strong>Detrazione:</strong> D = min(Spesa × Aliquota, Limite<sub>max</sub>)<br><br>
        <strong>Fruizione:</strong> 10 rate annuali di pari importo
    </div>

    <h3>3.3 Valore Attuale Netto (NPV)</h3>
    <p>Per confrontare incentivi con tempistiche diverse, si calcola il NPV:</p>

    <div class="formula-box">
        NPV = Σ (CF<sub>i</sub> / (1 + r)<sup>i</sup>) per i = 0, 1, 2, ..., n<br><br>
        dove r = {tasso}% (tasso di sconto)
    </div>
""".format(tasso=tasso_sconto*100)

    # Sezione 4: Risultati dettagliati
    html += """
    <div class="page-break"></div>
    <h2>4. Risultati Dettagliati</h2>
"""

    for i, scenario in enumerate(scenari, 1):
        html += f"""
    <h3>4.{i} Scenario: {scenario.nome}</h3>
"""

        if solo_ct:
            # Solo Conto Termico - visualizzazione singola
            html += f"""
    <div style="border: 2px solid #2E7D32; border-radius: 8px; padding: 20px; background: linear-gradient(to bottom, #e8f5e9, white);">
        <h4 style="color: #2E7D32; margin-bottom: 15px;">Conto Termico 3.0</h4>
        <div style="font-size: 32px; font-weight: bold; color: #2E7D32; margin: 15px 0;">{scenario.ct_incentivo:,.2f} EUR</div>
        <div style="margin: 10px 0;">
            <strong>Ammissibilità:</strong>
            <span class="{'positive' if scenario.ct_ammissibile else 'negative'}">
                {'✅ Ammesso' if scenario.ct_ammissibile else '❌ Non ammesso'}
            </span>
        </div>
        <div><strong>Durata erogazione:</strong> {scenario.ct_annualita} anni</div>
        <div><strong>Modalità:</strong> Bonifico diretto GSE</div>
        <div><strong>% sulla spesa:</strong> {scenario.ct_incentivo/scenario.spesa*100:.1f}%</div>
    </div>

    <div class="note">
        <strong>Calcoli intermedi CT PdC:</strong> Q<sub>uf</sub>={scenario.ct_quf} h,
        k<sub>p</sub>={scenario.ct_kp:.4f}, E<sub>i</sub>={scenario.ct_ei:,.0f} kWht,
        C<sub>i</sub>={scenario.ct_ci} EUR/kWht
    </div>
"""
        else:
            # Modalità confronto - visualizzazione comparativa
            vincitore_npv = "Conto Termico" if scenario.npv_ct > scenario.npv_eco else "Ecobonus"
            vantaggio = abs(scenario.npv_ct - scenario.npv_eco)

            html += f"""
    <div class="comparison-grid">
        <div class="comparison-card ct">
            <h4>Conto Termico 3.0</h4>
            <div class="big-number">{scenario.ct_incentivo:,.2f} EUR</div>
            <div>NPV: {scenario.npv_ct:,.2f} EUR</div>
            <div>Erogazione: {scenario.ct_annualita} anni</div>
        </div>
        <div class="comparison-card eco">
            <h4>Ecobonus</h4>
            <div class="big-number">{scenario.eco_detrazione:,.2f} EUR</div>
            <div>NPV: {scenario.npv_eco:,.2f} EUR</div>
            <div>Erogazione: 10 anni</div>
        </div>
    </div>

    <table>
        <tr>
            <th>Parametro</th>
            <th>Conto Termico 3.0</th>
            <th>Ecobonus</th>
        </tr>
        <tr>
            <td>Ammissibilità</td>
            <td class="{'positive' if scenario.ct_ammissibile else 'negative'}">
                {'Ammesso' if scenario.ct_ammissibile else 'Non ammesso'}
            </td>
            <td class="{'positive' if scenario.eco_ammissibile else 'negative'}">
                {'Ammesso' if scenario.eco_ammissibile else 'Non ammesso'}
            </td>
        </tr>
        <tr>
            <td>Incentivo nominale</td>
            <td>{scenario.ct_incentivo:,.2f} EUR</td>
            <td>{scenario.eco_detrazione:,.2f} EUR</td>
        </tr>
        <tr>
            <td>Valore attuale (NPV)</td>
            <td class="{'highlight' if scenario.npv_ct > scenario.npv_eco else ''}">{scenario.npv_ct:,.2f} EUR</td>
            <td class="{'highlight' if scenario.npv_eco > scenario.npv_ct else ''}">{scenario.npv_eco:,.2f} EUR</td>
        </tr>
        <tr>
            <td>% sulla spesa</td>
            <td>{scenario.ct_incentivo/scenario.spesa*100:.1f}%</td>
            <td>{scenario.eco_detrazione/scenario.spesa*100:.1f}%</td>
        </tr>
        <tr>
            <td>Durata erogazione</td>
            <td>{scenario.ct_annualita} anni</td>
            <td>10 anni</td>
        </tr>
        <tr>
            <td>Modalità</td>
            <td>Bonifico diretto GSE</td>
            <td>Detrazione fiscale IRPEF</td>
        </tr>
    </table>

    <div class="note">
        <strong>Calcoli intermedi CT PdC:</strong> Q<sub>uf</sub>={scenario.ct_quf} h,
        k<sub>p</sub>={scenario.ct_kp:.4f}, E<sub>i</sub>={scenario.ct_ei:,.0f} kWht,
        C<sub>i</sub>={scenario.ct_ci} EUR/kWht
    </div>
"""

        # Sezione FV se abbinato
        if getattr(scenario, 'fv_abbinato', False) and scenario.fv_potenza_kw > 0:
            spesa_totale_fv = scenario.fv_spesa + scenario.fv_spesa_accumulo
            incentivo_totale_ct = scenario.ct_incentivo + scenario.fv_incentivo_ct

            if solo_ct:
                # Solo CT - mostra solo FV con CT
                html += f"""
    <h4 style="margin-top: 20px;">🔆 Impianto Fotovoltaico Combinato (II.H)</h4>

    <div style="border: 2px solid #2E7D32; border-radius: 8px; padding: 20px; background: linear-gradient(to bottom, #e8f5e9, white); margin-top: 15px;">
        <h4 style="color: #2E7D32; margin-bottom: 15px;">Conto Termico FV</h4>
        <div style="font-size: 24px; font-weight: bold; color: #2E7D32; margin: 15px 0;">{scenario.fv_incentivo_ct:,.2f} EUR</div>
        <div><strong>% spesa FV:</strong> {scenario.fv_incentivo_ct/spesa_totale_fv*100:.1f}%</div>
        <div><strong>Limite:</strong> pari all'incentivo PdC</div>
    </div>

    <div class="recommendation" style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-left-color: #FF9800;">
        <h3 style="color: #E65100;">📊 Riepilogo Totale Intervento PdC + FV</h3>
        <table>
            <tr>
                <th>Voce</th>
                <th>Importo</th>
            </tr>
            <tr>
                <td>Spesa totale (PdC + FV)</td>
                <td><strong>{scenario.spesa + spesa_totale_fv:,.2f} EUR</strong></td>
            </tr>
            <tr>
                <td>Incentivo PdC</td>
                <td>{scenario.ct_incentivo:,.2f} EUR</td>
            </tr>
            <tr>
                <td>Incentivo FV</td>
                <td>{scenario.fv_incentivo_ct:,.2f} EUR</td>
            </tr>
            <tr class="highlight">
                <td><strong>TOTALE INCENTIVI</strong></td>
                <td><strong>{incentivo_totale_ct:,.2f} EUR</strong></td>
            </tr>
        </table>
    </div>
"""
            else:
                # Confronto - mostra CT vs Bonus Ristrutturazione
                incentivo_totale_eco = scenario.eco_detrazione + scenario.fv_bonus_ristrutt
                npv_totale_ct = scenario.npv_ct + scenario.fv_npv_ct
                npv_totale_eco = scenario.npv_eco + scenario.fv_npv_bonus

                html += f"""
    <h4 style="margin-top: 20px;">🔆 Impianto Fotovoltaico Combinato (II.H)</h4>

    <div class="comparison-grid">
        <div class="comparison-card ct">
            <h4>Conto Termico FV</h4>
            <div class="big-number">{scenario.fv_incentivo_ct:,.2f} EUR</div>
            <div>NPV: {scenario.fv_npv_ct:,.2f} EUR</div>
            <div>Limite: incentivo PdC</div>
        </div>
        <div class="comparison-card eco">
            <h4>Bonus Ristrutturazione</h4>
            <div class="big-number">{scenario.fv_bonus_ristrutt:,.2f} EUR</div>
            <div>NPV: {scenario.fv_npv_bonus:,.2f} EUR</div>
            <div>Erogazione: 10 anni</div>
        </div>
    </div>

    <table>
        <tr>
            <th>Parametro FV</th>
            <th>Conto Termico 3.0</th>
            <th>Bonus Ristrutturazione</th>
        </tr>
        <tr>
            <td>Incentivo FV</td>
            <td>{scenario.fv_incentivo_ct:,.2f} EUR</td>
            <td>{scenario.fv_bonus_ristrutt:,.2f} EUR</td>
        </tr>
        <tr>
            <td>% spesa FV</td>
            <td>{scenario.fv_incentivo_ct/spesa_totale_fv*100:.1f}%</td>
            <td>{scenario.fv_bonus_ristrutt/spesa_totale_fv*100:.1f}%</td>
        </tr>
    </table>

    <div class="recommendation" style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-left-color: #FF9800;">
        <h3 style="color: #E65100;">📊 Riepilogo Totale Intervento PdC + FV</h3>
        <table>
            <tr>
                <th>Voce</th>
                <th>Conto Termico Totale</th>
                <th>Ecobonus + Bonus Ristrutt.</th>
            </tr>
            <tr>
                <td>Spesa totale</td>
                <td colspan="2" style="text-align: center;"><strong>{scenario.spesa + spesa_totale_fv:,.2f} EUR</strong></td>
            </tr>
            <tr>
                <td>Incentivo PdC</td>
                <td>{scenario.ct_incentivo:,.2f} EUR</td>
                <td>{scenario.eco_detrazione:,.2f} EUR</td>
            </tr>
            <tr>
                <td>Incentivo FV</td>
                <td>{scenario.fv_incentivo_ct:,.2f} EUR</td>
                <td>{scenario.fv_bonus_ristrutt:,.2f} EUR</td>
            </tr>
            <tr class="highlight">
                <td><strong>TOTALE INCENTIVI</strong></td>
                <td><strong>{incentivo_totale_ct:,.2f} EUR</strong></td>
                <td><strong>{incentivo_totale_eco:,.2f} EUR</strong></td>
            </tr>
            <tr>
                <td><strong>NPV TOTALE</strong></td>
                <td class="{'highlight' if npv_totale_ct > npv_totale_eco else ''}">{npv_totale_ct:,.2f} EUR</td>
                <td class="{'highlight' if npv_totale_eco > npv_totale_ct else ''}">{npv_totale_eco:,.2f} EUR</td>
            </tr>
        </table>
    </div>
"""

    # Sezione 5: Confronto scenari
    if len(scenari) > 1:
        html += """
    <div class="page-break"></div>
    <h2>5. Confronto tra Scenari</h2>
"""
        if solo_ct:
            # Solo CT - tabella semplificata
            html += """
    <table>
        <tr>
            <th>Scenario</th>
            <th>Tipologia</th>
            <th>Potenza</th>
            <th>Spesa</th>
            <th>CT Incentivo</th>
        </tr>
"""
            for scenario in scenari:
                html += f"""
        <tr>
            <td>{scenario.nome}</td>
            <td>{scenario.tipo_intervento_label}</td>
            <td>{scenario.potenza_kw} kW</td>
            <td>{scenario.spesa:,.0f} EUR</td>
            <td class="highlight">{scenario.ct_incentivo:,.0f} EUR</td>
        </tr>
"""
        else:
            # Confronto - tabella completa
            html += """
    <table>
        <tr>
            <th>Scenario</th>
            <th>Tipologia</th>
            <th>Potenza</th>
            <th>Spesa</th>
            <th>CT (NPV)</th>
            <th>Ecobonus (NPV)</th>
            <th>Migliore</th>
        </tr>
"""
            for scenario in scenari:
                migliore = "CT" if scenario.npv_ct > scenario.npv_eco else "Eco"
                html += f"""
        <tr>
            <td>{scenario.nome}</td>
            <td>{scenario.tipo_intervento_label}</td>
            <td>{scenario.potenza_kw} kW</td>
            <td>{scenario.spesa:,.0f} EUR</td>
            <td>{scenario.npv_ct:,.0f} EUR</td>
            <td>{scenario.npv_eco:,.0f} EUR</td>
            <td class="{'positive' if migliore == 'CT' else ''}">{migliore}</td>
        </tr>
"""
        html += """
    </table>
"""

    # Sezione 6: Raccomandazione (solo se ci sono più scenari O se è modalità confronto)
    if len(scenari) > 1 or not solo_ct:
        html += f"""
    <h2>{'6' if len(scenari) > 1 else '5'}. Raccomandazione</h2>
"""

        if solo_ct:
            # Solo CT con più scenari - raccomandazione semplificata
            miglior_scenario = max(scenari, key=lambda s: s.ct_incentivo)
            html += f"""
    <div class="recommendation">
        <h3>Scenario Consigliato</h3>
        <p>
            Sulla base dell'analisi effettuata, lo scenario con il miglior incentivo
            Conto Termico 3.0 è <strong>"{miglior_scenario.nome}"</strong>.
        </p>
        <p style="margin-top: 10px;">
            <strong>Incentivo Conto Termico 3.0:</strong> {miglior_scenario.ct_incentivo:,.2f} EUR<br>
            <strong>Durata erogazione:</strong> {miglior_scenario.ct_annualita} anni<br>
            <strong>Modalità:</strong> Bonifico diretto GSE
        </p>
    </div>

    <div class="note">
        <strong>Nota importante:</strong> Vantaggi del Conto Termico 3.0:
        <ul style="margin-top: 5px; margin-left: 20px;">
            <li>Erogazione diretta tramite bonifico GSE (liquidità immediata)</li>
            <li>Non richiede capienza fiscale</li>
            <li>Tempi di erogazione rapidi (2-5 anni a seconda della potenza)</li>
            <li>Importo certo e garantito</li>
        </ul>
    </div>
"""
        else:
            # Confronto - raccomandazione comparativa
            miglior_scenario = max(scenari, key=lambda s: max(s.npv_ct, s.npv_eco))
            miglior_incentivo = "Conto Termico 3.0" if miglior_scenario.npv_ct > miglior_scenario.npv_eco else "Ecobonus"
            miglior_npv = max(miglior_scenario.npv_ct, miglior_scenario.npv_eco)

            html += f"""
    <div class="recommendation">
        <h3>Opzione Consigliata</h3>
        <p>
            Sulla base dell'analisi NPV effettuata, si consiglia di optare per
            <strong>{miglior_incentivo}</strong> per lo scenario <strong>"{miglior_scenario.nome}"</strong>.
        </p>
        <p style="margin-top: 10px;">
            <strong>Valore attuale netto:</strong> {miglior_npv:,.2f} EUR<br>
            <strong>Vantaggio rispetto all'alternativa:</strong> {abs(miglior_scenario.npv_ct - miglior_scenario.npv_eco):,.2f} EUR
        </p>
    </div>

    <div class="note">
        <strong>Nota importante:</strong> La scelta finale deve considerare anche:
        <ul style="margin-top: 5px; margin-left: 20px;">
            <li>Capienza fiscale del contribuente (per Ecobonus)</li>
            <li>Necessità di liquidità immediata</li>
            <li>Complessità amministrativa della pratica</li>
            <li>Eventuali variazioni normative future</li>
        </ul>
    </div>
"""

    # Riferimenti normativi
    html += """
    <h2>Riferimenti Normativi</h2>
    <ul>
        <li>DM 7 agosto 2025 - Conto Termico 3.0</li>
        <li>Regole Applicative GSE - Conto Termico 3.0</li>
"""
    if not solo_ct:
        html += """        <li>D.L. 63/2013 convertito in L. 90/2013 - Ecobonus</li>
        <li>Legge di Bilancio 2025 - Nuove aliquote Ecobonus</li>
"""
    html += """        <li>Regolamenti UE 206/2012, 813/2013, 2281/2016 - Requisiti Ecodesign</li>
    </ul>

    <div class="footer">
        <p>
            Documento generato automaticamente da Energy Incentive Manager<br>
            I calcoli sono indicativi e non sostituiscono la consulenza di un professionista abilitato.
        </p>
    </div>
</body>
</html>
"""

    return html


def genera_report_markdown(
    scenari: list[ScenarioCalcolo],
    tipo_soggetto: str,
    tipo_abitazione: str,
    anno: int,
    tasso_sconto: float
) -> str:
    """
    Genera un report in formato Markdown.

    Args:
        scenari: Lista di scenari calcolati
        tipo_soggetto: Tipo di soggetto richiedente
        tipo_abitazione: Tipo di abitazione
        anno: Anno della spesa
        tasso_sconto: Tasso di sconto per NPV

    Returns:
        Stringa Markdown del report
    """
    data_report = datetime.now().strftime("%d/%m/%Y %H:%M")

    md = f"""# RELAZIONE TECNICA
## Analisi Comparativa Incentivi Energetici

**Data:** {data_report}
**Soggetto:** {tipo_soggetto.replace('_', ' ').title()}
**Abitazione:** {tipo_abitazione.replace('_', ' ').title()}
**Anno spesa:** {anno}
**Tasso sconto NPV:** {tasso_sconto*100:.1f}%

---

## 1. Premessa

La presente relazione analizza le opzioni di incentivazione per l'installazione di pompe di calore:
- **Conto Termico 3.0** (DM 7 agosto 2025)
- **Ecobonus** (D.L. 63/2013)

---

## 2. Scenari Analizzati

"""

    for i, s in enumerate(scenari, 1):
        md += f"""### Scenario {i}: {s.nome}

| Parametro | Valore |
|-----------|--------|
| Tipologia | {s.tipo_intervento_label} |
| Potenza | {s.potenza_kw} kW |
| SCOP | {s.scop} |
| η_s | {s.eta_s}% (min: {s.eta_s_min}%) |
| Zona climatica | {s.zona_climatica} |
| Spesa | {s.spesa:,.2f} EUR |

"""

    md += """---

## 3. Risultati

| Scenario | CT Incentivo | CT NPV | Ecobonus | Eco NPV | Migliore |
|----------|-------------|--------|----------|---------|----------|
"""

    for s in scenari:
        migliore = "CT" if s.npv_ct > s.npv_eco else "Ecobonus"
        md += f"| {s.nome} | {s.ct_incentivo:,.0f} EUR | {s.npv_ct:,.0f} EUR | {s.eco_detrazione:,.0f} EUR | {s.npv_eco:,.0f} EUR | **{migliore}** |\n"

    # Raccomandazione
    miglior_scenario = max(scenari, key=lambda s: max(s.npv_ct, s.npv_eco))
    miglior_incentivo = "Conto Termico 3.0" if miglior_scenario.npv_ct > miglior_scenario.npv_eco else "Ecobonus"

    md += f"""

---

## 4. Raccomandazione

**Opzione consigliata:** {miglior_incentivo} per scenario "{miglior_scenario.nome}"

Vantaggio NPV: {abs(miglior_scenario.npv_ct - miglior_scenario.npv_eco):,.2f} EUR

---

*Documento generato da Energy Incentive Manager*
"""

    return md


def genera_report_solare_termico_html(
    scenari: list[ScenarioSolareTermico],
    tipo_soggetto: str,
    tipo_abitazione: str,
    anno: int,
    tasso_sconto: float,
) -> str:
    """
    Genera un report HTML per scenari di solare termico.

    Args:
        scenari: Lista di scenari solare termico
        tipo_soggetto: Tipo di soggetto richiedente
        tipo_abitazione: Tipo di abitazione
        anno: Anno della spesa
        tasso_sconto: Tasso di sconto per NPV

    Returns:
        Stringa HTML del report
    """
    data_report = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relazione Tecnica - Solare Termico</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6; color: #333;
            max-width: 210mm; margin: 0 auto; padding: 20mm; background: white;
        }}
        .header {{
            text-align: center; border-bottom: 3px solid #FF9800;
            padding-bottom: 20px; margin-bottom: 30px;
        }}
        .header h1 {{ color: #FF9800; font-size: 24px; margin-bottom: 10px; }}
        .header .subtitle {{ color: #666; font-size: 14px; }}
        .meta-info {{
            display: flex; justify-content: space-between; background: #f5f5f5;
            padding: 15px; border-radius: 5px; margin-bottom: 25px; font-size: 12px;
        }}
        h2 {{
            color: #FF9800; border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px; margin: 25px 0 15px 0; font-size: 18px;
        }}
        h3 {{ color: #333; margin: 20px 0 10px 0; font-size: 14px; }}
        table {{
            width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px;
        }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #FF9800; color: white; font-weight: 600; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .highlight {{ background-color: #fff3e0 !important; font-weight: bold; }}
        .scenario-box {{
            border: 1px solid #ddd; border-radius: 8px;
            padding: 15px; margin: 15px 0; background: #fafafa;
        }}
        .scenario-title {{
            font-weight: bold; color: #FF9800; font-size: 14px; margin-bottom: 10px;
        }}
        .positive {{ color: #2E7D32; }}
        .negative {{ color: #C62828; }}
        .recommendation {{
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-left: 4px solid #FF9800;
            padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;
        }}
        .recommendation h3 {{ color: #E65100; margin-bottom: 10px; }}
        .formula-box {{
            background: #e3f2fd; border: 1px solid #90caf9;
            padding: 15px; margin: 15px 0; border-radius: 5px;
            font-family: 'Courier New', monospace; font-size: 12px;
        }}
        .note {{
            background: #fff3e0; border-left: 4px solid #FF9800;
            padding: 10px 15px; margin: 15px 0; font-size: 11px; color: #E65100;
        }}
        .footer {{
            margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;
            font-size: 10px; color: #999; text-align: center;
        }}
        .comparison-grid {{
            display: grid; grid-template-columns: repeat(2, 1fr);
            gap: 15px; margin: 15px 0;
        }}
        .comparison-card {{
            border: 1px solid #ddd; border-radius: 8px; padding: 15px; text-align: center;
        }}
        .comparison-card.ct {{
            border-color: #FF9800; background: linear-gradient(to bottom, #fff3e0, white);
        }}
        .comparison-card.eco {{
            border-color: #1565C0; background: linear-gradient(to bottom, #e3f2fd, white);
        }}
        .comparison-card h4 {{ margin-bottom: 10px; }}
        .comparison-card.ct h4 {{ color: #E65100; }}
        .comparison-card.eco h4 {{ color: #1565C0; }}
        .big-number {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        .ct .big-number {{ color: #E65100; }}
        .eco .big-number {{ color: #1565C0; }}
        @media print {{ body {{ padding: 10mm; }} .page-break {{ page-break-before: always; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>☀️ RELAZIONE TECNICA - SOLARE TERMICO</h1>
        <div class="subtitle">Analisi Comparativa Incentivi Energetici</div>
        <div class="subtitle">Conto Termico 3.0 (DM 7/8/2025) vs Ecobonus</div>
    </div>

    <div class="meta-info">
        <div><strong>Data:</strong> {data_report}</div>
        <div><strong>Soggetto:</strong> {tipo_soggetto.replace('_', ' ').title()}</div>
        <div><strong>Abitazione:</strong> {tipo_abitazione.replace('_', ' ').title()}</div>
        <div><strong>Anno spesa:</strong> {anno}</div>
    </div>

    <h2>1. Premessa</h2>
    <p>
        La presente relazione tecnica analizza le opzioni di incentivazione disponibili per
        l'installazione di impianti solari termici (intervento III.D), confrontando il
        <strong>Conto Termico 3.0</strong> (DM 7 agosto 2025) con l'<strong>Ecobonus</strong>
        (D.L. 63/2013 e s.m.i.).
    </p>
    <p style="margin-top: 10px;">
        L'analisi include il calcolo del <strong>Valore Attuale Netto (NPV)</strong> con un tasso
        di sconto del {tasso_sconto*100:.1f}% per una corretta valutazione finanziaria.
    </p>

    <h2>2. Scenari Analizzati</h2>
    <p>Sono stati analizzati i seguenti {n} scenari di installazione:</p>
""".format(n=len(scenari))

    for i, scenario in enumerate(scenari, 1):
        html += f"""
    <div class="scenario-box">
        <div class="scenario-title">Scenario {i}: {scenario.nome}</div>
        <table>
            <tr>
                <th colspan="2">Dati Tecnici</th>
                <th colspan="2">Parametri Economici</th>
            </tr>
            <tr>
                <td><strong>Tipologia impianto:</strong></td>
                <td>{scenario.tipologia_label}</td>
                <td><strong>Spesa totale:</strong></td>
                <td>{scenario.spesa:,.2f} EUR</td>
            </tr>
            <tr>
                <td><strong>Tipo collettore:</strong></td>
                <td>{scenario.tipo_collettore_label}</td>
                <td><strong>Superficie totale:</strong></td>
                <td>{scenario.superficie_m2:.1f} m²</td>
            </tr>
            <tr>
                <td><strong>N° moduli:</strong></td>
                <td>{scenario.n_moduli}</td>
                <td><strong>Area singolo modulo:</strong></td>
                <td>{scenario.area_modulo_m2:.2f} m²</td>
            </tr>
            <tr>
                <td><strong>Producibilità Qu:</strong></td>
                <td>{scenario.producibilita_qu:.0f} kWht/m²</td>
                <td><strong>Coeff. Ci:</strong></td>
                <td>{scenario.ct_ci:.2f} €/kWht</td>
            </tr>
        </table>
    </div>
"""

    # Sezione 3: Metodologia
    html += f"""
    <h2>3. Metodologia di Calcolo</h2>

    <h3>3.1 Conto Termico 3.0 - Solare Termico (III.D)</h3>
    <p>Il calcolo dell'incentivo segue le formule previste dall'Allegato 2 del DM 7/8/2025:</p>

    <div class="formula-box">
        <strong>Formula incentivo annuo:</strong> I<sub>a</sub> = C<sub>i</sub> × Q<sub>u</sub> × S<sub>l</sub><br><br>
        <strong>dove:</strong><br>
        C<sub>i</sub> = coefficiente di valorizzazione (€/kWht) - dipende da tipologia e superficie<br>
        Q<sub>u</sub> = producibilità specifica collettore (kWht/m²) - da Solar Keymark<br>
        S<sub>l</sub> = superficie lorda totale (m²)
    </div>

    <div class="note">
        <strong>Nota:</strong> La producibilità Q<sub>u</sub> deve essere certificata Solar Keymark
        e rispettare i valori minimi per tipo di collettore (piano: 300, sottovuoto: 400,
        concentrazione: 550 kWht/m²).
    </div>

    <h3>3.2 Ecobonus</h3>
    <p>Per il solare termico l'Ecobonus prevede una detrazione del 65% in 10 anni:</p>

    <div class="formula-box">
        <strong>Detrazione:</strong> D = min(Spesa × 65%, 60.000 EUR)<br><br>
        <strong>Fruizione:</strong> 10 rate annuali di pari importo
    </div>

    <h3>3.3 Valore Attuale Netto (NPV)</h3>
    <div class="formula-box">
        NPV = Σ (CF<sub>i</sub> / (1 + r)<sup>i</sup>) per i = 0, 1, 2, ..., n<br><br>
        dove r = {tasso_sconto*100:.1f}% (tasso di sconto)
    </div>

    <div class="page-break"></div>
    <h2>4. Risultati Dettagliati</h2>
"""

    for i, scenario in enumerate(scenari, 1):
        html += f"""
    <h3>4.{i} Scenario: {scenario.nome}</h3>

    <div class="comparison-grid">
        <div class="comparison-card ct">
            <h4>Conto Termico 3.0</h4>
            <div class="big-number">{scenario.ct_incentivo:,.2f} EUR</div>
            <div>NPV: {scenario.npv_ct:,.2f} EUR</div>
            <div>Erogazione: {scenario.ct_annualita} anni</div>
        </div>
        <div class="comparison-card eco">
            <h4>Ecobonus</h4>
            <div class="big-number">{scenario.eco_detrazione:,.2f} EUR</div>
            <div>NPV: {scenario.npv_eco:,.2f} EUR</div>
            <div>Erogazione: 10 anni</div>
        </div>
    </div>

    <table>
        <tr>
            <th>Parametro</th>
            <th>Conto Termico 3.0</th>
            <th>Ecobonus</th>
        </tr>
        <tr>
            <td>Ammissibilità</td>
            <td class="{'positive' if scenario.ct_ammissibile else 'negative'}">
                {'Ammesso' if scenario.ct_ammissibile else 'Non ammesso'}
            </td>
            <td class="{'positive' if scenario.eco_ammissibile else 'negative'}">
                {'Ammesso' if scenario.eco_ammissibile else 'Non ammesso'}
            </td>
        </tr>
        <tr>
            <td>Incentivo nominale</td>
            <td>{scenario.ct_incentivo:,.2f} EUR</td>
            <td>{scenario.eco_detrazione:,.2f} EUR</td>
        </tr>
        <tr>
            <td>Valore attuale (NPV)</td>
            <td class="{'highlight' if scenario.npv_ct > scenario.npv_eco else ''}">{scenario.npv_ct:,.2f} EUR</td>
            <td class="{'highlight' if scenario.npv_eco > scenario.npv_ct else ''}">{scenario.npv_eco:,.2f} EUR</td>
        </tr>
        <tr>
            <td>% sulla spesa</td>
            <td>{scenario.ct_incentivo/scenario.spesa*100:.1f}%</td>
            <td>{scenario.eco_detrazione/scenario.spesa*100:.1f}%</td>
        </tr>
        <tr>
            <td>Durata erogazione</td>
            <td>{scenario.ct_annualita} anni</td>
            <td>10 anni</td>
        </tr>
    </table>

    <div class="note">
        <strong>Calcoli CT:</strong> Ia = {scenario.ct_ci:.2f} × {scenario.producibilita_qu:.0f} × {scenario.superficie_m2:.1f}
        = {scenario.ct_ia:,.2f} EUR/anno × {scenario.ct_annualita} anni
    </div>
"""

    # Raccomandazione
    miglior_scenario = max(scenari, key=lambda s: max(s.npv_ct, s.npv_eco))
    miglior_incentivo = "Conto Termico 3.0" if miglior_scenario.npv_ct > miglior_scenario.npv_eco else "Ecobonus"
    miglior_npv = max(miglior_scenario.npv_ct, miglior_scenario.npv_eco)

    html += f"""
    <h2>5. Raccomandazione</h2>

    <div class="recommendation">
        <h3>Opzione Consigliata</h3>
        <p>
            Sulla base dell'analisi NPV effettuata, si consiglia di optare per
            <strong>{miglior_incentivo}</strong> per lo scenario <strong>"{miglior_scenario.nome}"</strong>.
        </p>
        <p style="margin-top: 10px;">
            <strong>Valore attuale netto:</strong> {miglior_npv:,.2f} EUR<br>
            <strong>Vantaggio rispetto all'alternativa:</strong> {abs(miglior_scenario.npv_ct - miglior_scenario.npv_eco):,.2f} EUR
        </p>
    </div>

    <div class="note">
        <strong>Nota importante:</strong> La scelta finale deve considerare anche:
        <ul style="margin-top: 5px; margin-left: 20px;">
            <li>Capienza fiscale del contribuente (per Ecobonus)</li>
            <li>Necessità di liquidità immediata (CT pagato in 2-5 anni)</li>
            <li>Complessità amministrativa della pratica GSE</li>
        </ul>
    </div>

    <h2>Riferimenti Normativi</h2>
    <ul>
        <li>DM 7 agosto 2025 - Conto Termico 3.0</li>
        <li>Regole Applicative GSE - Conto Termico 3.0 (Par. 9.12)</li>
        <li>D.L. 63/2013 convertito in L. 90/2013 - Ecobonus</li>
        <li>EN 12975/12976 - Certificazione Solar Keymark</li>
    </ul>

    <div class="footer">
        <p>
            Documento generato automaticamente da Energy Incentive Manager<br>
            I calcoli sono indicativi e non sostituiscono la consulenza di un professionista abilitato.
        </p>
    </div>
</body>
</html>
"""

    return html


def genera_report_scaldacqua_html(
    scenari,
    tipo_soggetto: str,
    tipo_abitazione: str,
    anno: int,
    tasso_sconto: float
) -> str:
    """Genera report HTML per scaldacqua a pompa di calore."""
    from modules.report_generator import ScenarioScaldacqua

    data_generazione = datetime.now().strftime("%d/%m/%Y %H:%M")

    righe_scenari = ""
    for s in scenari:
        iter_badge = '<span style="background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em;">ITER SEMPLIFICATO</span>' if s.iter_semplificato else ""
        prodotto_info = f"{s.prodotto_marca} {s.prodotto_modello}" if s.prodotto_marca else "N/D"

        righe_scenari += f"""
        <tr>
            <td>{s.nome} {iter_badge}</td>
            <td>{prodotto_info}</td>
            <td>{s.classe_energetica}</td>
            <td>{s.capacita_litri} L</td>
            <td>{s.potenza_kw:.1f} kW</td>
            <td>€ {s.spesa_lavori:,.0f}</td>
            <td style="background: #E8F5E9;">€ {s.ct_incentivo:,.0f}</td>
            <td style="font-weight: bold; color: #1565C0;">€ {s.ct_npv:,.0f}</td>
            <td style="background: #E3F2FD;">€ {s.eco_detrazione:,.0f}</td>
            <td style="font-weight: bold; color: #1565C0;">€ {s.eco_npv:,.0f}</td>
            <td><strong>{s.piu_conveniente}</strong></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Relazione Tecnica - Scaldacqua PdC</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2E7D32; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #4CAF50; color: white; padding: 12px; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        .info-box {{ background: #E3F2FD; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Relazione Tecnica - Scaldacqua a Pompa di Calore (III.E)</h1>
        <div class="info-box">
            Soggetto: {tipo_soggetto} | Abitazione: {tipo_abitazione} | Anno: {anno} | Tasso NPV: {tasso_sconto*100:.1f}% | Data: {data_generazione}
        </div>
        <table>
            <thead>
                <tr><th>Scenario</th><th>Prodotto</th><th>Classe</th><th>Capacità</th><th>Potenza</th><th>Spesa</th><th>CT</th><th>CT NPV</th><th>Eco</th><th>Eco NPV</th><th>Migliore</th></tr>
            </thead>
            <tbody>{righe_scenari}</tbody>
        </table>
        <div class="info-box"><em>DM 7/8/2025 - Art. 8, comma 1, lettera e)</em></div>
    </div>
</body>
</html>"""
    return html

def genera_report_multi_intervento_html(scenario, anno, tasso_sconto):
    """Genera report HTML per progetto multi-intervento."""
    from datetime import datetime

    convenienza = "Conto Termico 3.0" if scenario.piu_conveniente == "CT" else "Ecobonus"
    righe_interventi = ""
    for idx, intervento in enumerate(scenario.interventi, 1):
        righe_interventi += f"""<tr><td>{idx}</td><td>{intervento.tipo_label}</td><td>{intervento.nome}</td><td class="number">{intervento.spesa_totale:,.0f} €</td><td class="number">{intervento.ct_incentivo:,.0f} €</td><td class="number">{intervento.eco_detrazione:,.0f} €</td></tr>"""

    # Sezione bonus (mostra entrambi se presenti)
    bonus_section = ""
    if scenario.ct_bonus_multi_5 > 0 or scenario.ct_bonus_multi_15 > 0:
        bonus_section = '<div class="success-box">'
        if scenario.ct_bonus_multi_5 > 0:
            bonus_section += f'<p><strong>✨ Bonus Multi-Intervento (+5%): {scenario.ct_bonus_multi_5:,.0f} €</strong></p><p>Intensità aumentata dal 25% al 30% per imprese su interventi Titolo II (Art. 27 comma 3)</p>'
        if scenario.ct_bonus_multi_15 > 0:
            bonus_section += f'<p style="margin-top:10px;"><strong>🌟 Bonus Riduzione Energia Primaria (+15%): {scenario.ct_bonus_multi_15:,.0f} €</strong></p><p>Riduzione EPgl,nren: {scenario.riduzione_ep_perc:.1f}% (≥40% richiesto - Art. 27 comma 4)</p>'
            if scenario.ape_ante_operam and scenario.ape_post_operam:
                bonus_section += f'<p style="font-size:0.9em;">APE ante-operam: {scenario.ape_ante_operam:.1f} kWh/m²anno → APE post-operam: {scenario.ape_post_operam:.1f} kWh/m²anno</p>'
        if scenario.ct_bonus_multi_5 > 0 and scenario.ct_bonus_multi_15 > 0:
            bonus_totale = scenario.ct_bonus_multi_5 + scenario.ct_bonus_multi_15
            bonus_section += f'<p style="margin-top:10px;border-top:1px solid #28a745;padding-top:10px;"><strong>Bonus Totale: {bonus_totale:,.0f} €</strong></p>'
        bonus_section += '</div>'
    
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8"><title>Multi-Intervento - {scenario.nome_progetto}</title>
<style>body{{font-family:Arial;max-width:1200px;margin:0 auto;padding:20px;background:#f5f5f5}}.header{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:30px;border-radius:10px;margin-bottom:30px}}.section{{background:white;padding:25px;margin-bottom:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}h2{{color:#667eea;border-bottom:2px solid #667eea;padding-bottom:10px}}table{{width:100%;border-collapse:collapse;margin:15px 0}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}th{{background-color:#667eea;color:white}}.number{{text-align:right;font-family:monospace}}.success-box{{background:#d4edda;border-left:4px solid #28a745;padding:15px;margin:15px 0}}.info-box{{background:#e7f3ff;border-left:4px solid #2196F3;padding:15px;margin:15px 0}}</style></head><body>
<div class="header"><h1>🔗 Relazione Tecnica Multi-Intervento</h1><p><strong>Progetto:</strong> {scenario.nome_progetto}</p><p><strong>Indirizzo:</strong> {scenario.indirizzo}</p><p><strong>Tipo:</strong> {scenario.tipo_edificio.capitalize()}</p><p><strong>Data:</strong> {datetime.now().strftime("%d/%m/%Y")}</p></div>
<div class="section"><h2>🔧 Interventi Inclusi nel Progetto</h2><table><thead><tr><th>#</th><th>Tipologia</th><th>Nome</th><th>Spesa</th><th>CT</th><th>Eco</th></tr></thead><tbody>{righe_interventi}</tbody><tfoot><tr style="font-weight:bold;background:#f8f9fa"><td colspan="3">TOTALE</td><td class="number">{scenario.spesa_totale:,.0f} €</td><td class="number">{scenario.ct_incentivo_base:,.0f} €</td><td class="number">{scenario.eco_detrazione_totale:,.0f} €</td></tr></tfoot></table></div>
<div class="section"><h2>💰 Riepilogo Economico</h2>{bonus_section}<table><tr><th>Incentivo</th><th>Totale</th><th>NPV ({tasso_sconto*100:.1f}%)</th></tr><tr><td>Conto Termico</td><td>{scenario.ct_incentivo_totale:,.0f} €</td><td>{scenario.ct_npv:,.0f} €</td></tr><tr><td>Ecobonus</td><td>{scenario.eco_detrazione_totale:,.0f} €</td><td>{scenario.eco_npv:,.0f} €</td></tr></table>
<div class="success-box"><p><strong>✅ Più conveniente: {convenienza}</strong></p><p>Differenza NPV: {abs(scenario.differenza_npv):,.0f} €</p></div></div>
<div class="section"><h2>📝 Note Normative</h2><div class="info-box"><p><strong>Riferimenti:</strong></p><ul><li>DM 7/8/2025 - Art. 2, comma 1, lettera cc) - Definizione Multi-Intervento</li><li>Art. 27, comma 3 - Intensità incentivi per imprese</li><li>Regole GSE - Par. 12.4 - Multi-intervento</li></ul><p><strong>N.B.</strong> Presentare unica scheda-domanda GSE per tutti gli interventi</p></div></div></body></html>"""
