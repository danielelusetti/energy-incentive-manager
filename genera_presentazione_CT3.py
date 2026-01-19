"""
Script per generare presentazione PDF sul Conto Termico 3.0
Basato su Regole Applicative DM 7 agosto 2025
Requisiti: pip install reportlab pillow
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

def create_presentation():
    """Crea la presentazione PDF sul Conto Termico 3.0"""

    filename = "Presentazione_Conto_Termico_3.0.pdf"
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    # Stili
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=16,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2c5f8d'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=6,
        leading=14,
        fontName='Helvetica'
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        leftIndent=15,
        spaceAfter=5,
        leading=13,
        fontName='Helvetica'
    )

    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#d9534f'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=4,
        leading=11,
        fontName='Helvetica'
    )

    story = []

    # ===== SLIDE 1 - INTRODUZIONE =====
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("Conto Termico 3.0", title_style))
    story.append(Paragraph("Incentivi per efficienza energetica e fonti rinnovabili", subtitle_style))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("<b>Cosa è il Conto Termico 3.0?</b>", body_style))
    story.append(Paragraph("• Incentivo statale per efficienza energetica e fonti rinnovabili termiche", bullet_style))
    story.append(Paragraph("• Gestito dal GSE (Gestore Servizi Energetici)", bullet_style))
    story.append(Paragraph("• D.M. 7 agosto 2025 - Regole Applicative 5/12/2025", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Perché conviene?</b>", body_style))
    story.append(Paragraph("• <b>Contributo a fondo perduto</b> fino al 100% per edifici pubblici specifici", bullet_style))
    story.append(Paragraph("• <b>NOVITA CT 3.0:</b> erogazione unica rata fino a 15.000 EUR (era 5.000)", bullet_style))
    story.append(Paragraph("• Procedura online semplificata", bullet_style))
    story.append(Paragraph("• Cumulabile con altri incentivi (con limiti)", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Budget: 900 milioni EUR/anno</b>", highlight_style))
    story.append(Paragraph("400M per PA/ETS non economici - 500M per privati/imprese", small_style))
    story.append(PageBreak())

    # ===== SLIDE 2 - CHI PUO ACCEDERE =====
    story.append(Paragraph("Chi può accedere", title_style))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("<b>Pubbliche Amministrazioni</b>", subtitle_style))
    story.append(Paragraph("• Tutti gli interventi Titolo II e III", bullet_style))
    story.append(Paragraph("• Intensità 100% su edifici pubblici specifici (scuole, ospedali, comuni <15k ab.)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Soggetti Privati</b>", subtitle_style))
    story.append(Paragraph("• Residenziale: persone fisiche, condomini - Tutti interventi Titolo II e III", bullet_style))
    story.append(Paragraph("• Terziario: titolari reddito impresa/agrario - Tutti interventi con vincoli", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Enti del Terzo Settore (ETS)</b>", subtitle_style))
    story.append(Paragraph("• Non economici: assimilati a PA", bullet_style))
    story.append(Paragraph("• Economici: assimilati a imprese", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>ESCO e Soggetti abilitati</b>", subtitle_style))
    story.append(Paragraph("• Possono presentare domanda per conto PA/ETS/privati", bullet_style))
    story.append(Paragraph("• Comunita Energetiche Rinnovabili (CER) e configurazioni autoconsumo", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 3 - EROGAZIONE INCENTIVI =====
    story.append(Paragraph("Modalita di erogazione incentivi", title_style))
    story.append(Paragraph("<font color='#d9534f'>NOVITA PRINCIPALE CT 3.0</font>", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Soglia pagamento unico aumentata:</b>", body_style))
    story.append(Paragraph("• CT 2.0: unica rata se incentivo < 5.000 EUR", bullet_style))
    story.append(Paragraph("• <b>CT 3.0: unica rata se incentivo < 15.000 EUR</b>", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Modalita standard:</b>", subtitle_style))
    story.append(Paragraph("• < 15.000 EUR: <b>UNICA RATA</b>", bullet_style))
    story.append(Paragraph("• >= 15.000 EUR: Rate annuali costanti (2 o 5 anni secondo potenza)", bullet_style))
    story.append(Paragraph("  - 2 anni: generatori <= 35 kW", bullet_style))
    story.append(Paragraph("  - 5 anni: generatori > 35 kW, isolamento, serramenti", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Eccezioni (unica rata anche > 15.000 EUR):</b>", subtitle_style))
    story.append(Paragraph("• PA e ETS non economici: se accesso diretto", bullet_style))
    story.append(Paragraph("• ETS economici: solo per interventi Titolo III", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("Prima rata: entro ultimo giorno mese successivo al bimestre attivazione", small_style))
    story.append(Paragraph("Conservazione documenti: 5 anni dopo ultima erogazione", small_style))
    story.append(PageBreak())

    # ===== SLIDE 4 - INTERVENTI 6 PIU RICHIESTI =====
    story.append(Paragraph("I 6 interventi piu richiesti", title_style))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("<b>1. POMPE DI CALORE (III.A)</b>", body_style))
    story.append(Paragraph("Sostituzione impianti con pompe di calore elettriche/gas - Max 2.000 kW", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>2. FOTOVOLTAICO COMBINATO (II.H)</b> - <font color='#d9534f'>NOVITA 2025</font>", body_style))
    story.append(Paragraph("FV + accumulo, SOLO abbinato a pompa di calore elettrica (III.A)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>3. ISOLAMENTO TERMICO (II.A)</b>", body_style))
    story.append(Paragraph("Cappotto, coperture, pavimenti - 40-100% secondo zona e configurazione", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>4. SERRAMENTI (II.B)</b>", body_style))
    story.append(Paragraph("Finestre e porte verso esterno - 40-100% - Obbl. termoregolazione", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>5. GENERATORI BIOMASSA (III.C)</b>", body_style))
    story.append(Paragraph("Caldaie, stufe, termocamini pellet/legna - Classe 5 stelle solo se sostituisci biomassa", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>6. COLONNINE RICARICA VE (II.G)</b> - <font color='#d9534f'>NOVITA 2025</font>", body_style))
    story.append(Paragraph("Infrastrutture ricarica veicoli elettrici, SOLO abbinato a PDC elettrica", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 5 - POMPE DI CALORE DETTAGLIO =====
    story.append(Paragraph("Pompe di Calore (III.A) - Dettaglio", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Requisiti ammissibilita:</b>", subtitle_style))
    story.append(Paragraph("• Sostituzione impianto climatizzazione invernale esistente", bullet_style))
    story.append(Paragraph("• Potenza termica utile nominale <= 2.000 kW", bullet_style))
    story.append(Paragraph("• SCOP minimo secondo regolamenti Ecodesign (es. aria/acqua SCOP>=2,825)", bullet_style))
    story.append(Paragraph("• Valvole termostatiche su tutti corpi scaldanti (con eccezioni)", bullet_style))
    story.append(Paragraph("• Contabilizzazione individuale se impianto centralizzato", bullet_style))
    story.append(Paragraph("• Se > 200 kW: contabilizzazione calore + trasmissione dati GSE", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo (elettriche):</b>", subtitle_style))
    story.append(Paragraph("I = Energia termica prodotta annua × Coefficiente valorizzazione Ci", bullet_style))
    story.append(Paragraph("• Ci varia da 0,055 a 0,200 EUR/kWh secondo tipo e potenza", bullet_style))
    story.append(Paragraph("• Es. aria/acqua <=35kW: Ci=0,15 EUR/kWh", bullet_style))
    story.append(Paragraph("• Es. geotermiche <=35kW: Ci=0,160 EUR/kWh", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>IMPRESE/ETS economici: NO pompe di calore a gas</b>", highlight_style))
    story.append(PageBreak())

    # ===== SLIDE 6 - FOTOVOLTAICO COMBINATO =====
    story.append(Paragraph("Fotovoltaico Combinato (II.H)", title_style))
    story.append(Paragraph("<font color='#d9534f'>NOVITA 2025 - Sempre abbinato a PDC elettrica</font>", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Requisiti ammissibilita:</b>", subtitle_style))
    story.append(Paragraph("• <b>OBBLIGATORIO abbinamento</b> con sostituzione impianto PDC elettrica (III.A)", bullet_style))
    story.append(Paragraph("• Assetto autoconsumo (cessione parziale)", bullet_style))
    story.append(Paragraph("• Potenza FV: 2 kW <= P <= 1 MW (e potenza disponibile punto prelievo)", bullet_style))
    story.append(Paragraph("• Moduli e inverter nuovi, marcatura CE, garanzia >=10 anni", bullet_style))
    story.append(Paragraph("• Garanzia rendimento moduli: >=90% dopo 10 anni", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", subtitle_style))
    story.append(Paragraph("I = min(20% spesa FV+accumulo ; incentivo PDC)", bullet_style))
    story.append(Paragraph("• <b>L'incentivo NON puo superare quello della PDC combinata</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Costi massimi ammissibili FV:</b>", body_style))
    story.append(Paragraph("• <=20 kW: 1.500 EUR/kW  |  20-200 kW: 1.200 EUR/kW", bullet_style))
    story.append(Paragraph("• 200-600 kW: 1.100 EUR/kW  |  600-1.000 kW: 1.050 EUR/kW", bullet_style))
    story.append(Paragraph("• Accumulo: max 1.000 EUR/kWh", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Maggiorazioni:</b> +5/10/15% se moduli registro tecnologie fotovoltaico", body_style))
    story.append(PageBreak())

    # ===== SLIDE 7 - ISOLAMENTO TERMICO =====
    story.append(Paragraph("Isolamento Termico (II.A)", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Superfici ammesse:</b>", subtitle_style))
    story.append(Paragraph("• Strutture opache orizzontali: coperture, pavimenti", bullet_style))
    story.append(Paragraph("• Strutture opache verticali: pareti perimetrali", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", subtitle_style))
    story.append(Paragraph("I = Percentuale × Costo × Superficie intervento", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Percentuali:</b>", body_style))
    story.append(Paragraph("• Base: 40% | Zone E,F: 50%", bullet_style))
    story.append(Paragraph("• <b>55%</b> se combinato con III.A, III.B, III.C o III.E", bullet_style))
    story.append(Paragraph("• <b>100%</b> edifici pubblici specifici (scuole, ospedali, comuni <15k ab.)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Costi massimi ammissibili:</b>", body_style))

    data_iso = [
        ['Tipo', 'Cmax (EUR/m2)'],
        ['Coperture esterne', '300'],
        ['Coperture interne', '150'],
        ['Coperture ventilate', '350'],
        ['Pavimenti esterni', '170'],
        ['Pavimenti interni', '150'],
        ['Pareti esterne', '200'],
        ['Pareti interne', '100'],
        ['Pareti ventilate', '250']
    ]

    t_iso = Table(data_iso, colWidths=[8*cm, 4*cm])
    t_iso.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    story.append(t_iso)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("Incentivo max cumulativo: 1.000.000 EUR | Durata: 5 anni", small_style))
    story.append(Paragraph("Maggiorazione +10% se componenti prodotti UE", small_style))
    story.append(PageBreak())

    # ===== SLIDE 8 - SERRAMENTI =====
    story.append(Paragraph("Serramenti (II.B)", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Requisiti ammissibilita:</b>", subtitle_style))
    story.append(Paragraph("• Chiusure trasparenti comprensive infissi delimitanti volume climatizzato", bullet_style))
    story.append(Paragraph("• <b>OBBLIGATORIO:</b> sistemi termoregolazione o valvole termostatiche", bullet_style))
    story.append(Paragraph("• Trasmittanza massima per zona climatica (W/m2K):", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    data_serr = [
        ['Zona', 'Umax (W/m2K)'],
        ['A, B', '2,60'],
        ['C', '1,75'],
        ['D', '1,67'],
        ['E', '1,30'],
        ['F', '1,00']
    ]

    t_serr = Table(data_serr, colWidths=[6*cm, 6*cm])
    t_serr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10)
    ]))
    story.append(t_serr)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Incentivo:</b>", subtitle_style))
    story.append(Paragraph("• Base: 40% | 55% se combinato con II.A + (III.A o III.B o III.C o III.E)", bullet_style))
    story.append(Paragraph("• 100% edifici pubblici specifici", bullet_style))
    story.append(Paragraph("• Costi max: Zone A,B,C: 700 EUR/m2 | Zone D,E,F: 800 EUR/m2", bullet_style))
    story.append(Paragraph("• Incentivo max: 500.000 EUR | Durata: 5 anni", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 9 - BIOMASSA =====
    story.append(Paragraph("Generatori a Biomassa (III.C)", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Generatori ammessi:</b>", subtitle_style))
    story.append(Paragraph("• Caldaie biomassa <=500 kW: classe UNI EN 303-5 classe 5, rend >=87+log(Pn)", bullet_style))
    story.append(Paragraph("• Caldaie 500-2.000 kW: rendimento >=92%, abbattimento particolato", bullet_style))
    story.append(Paragraph("• Stufe/termocamini pellet: UNI EN 16510:2023, rendimento >85%", bullet_style))
    story.append(Paragraph("• Termocamini/stufe legna: UNI EN 16510:2023, rendimento >85%", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Classe ambientale 5 stelle (DM 186/2017):</b>", body_style))
    story.append(Paragraph("• OBBLIGATORIA se sostituisci biomassa/carbone/olio/gasolio esistente", bullet_style))
    story.append(Paragraph("• OBBLIGATORIA per aziende agricole/forestali in nuova installazione", bullet_style))
    story.append(Paragraph("• NON obbligatoria se sostituisci caldaia gas/GPL con biomassa", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", subtitle_style))
    story.append(Paragraph("Caldaie: I = Pn × hr × Ci × Ce", bullet_style))
    story.append(Paragraph("Stufe/termocamini: I = 3,35 × ln(Pn) × hr × Ci × Ce", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Coefficienti Ci (EUR/kWh):</b>", body_style))

    data_biom = [
        ['Tipo', '<=35kW', '35-500kW', '>500kW'],
        ['Caldaie biomassa', '0,060', '0,025', '0,020'],
        ['Termocamini/stufe legna', '0,045', '-', '-'],
        ['Termocamini/stufe pellet', '0,055', '-', '-']
    ]

    t_biom = Table(data_biom, colWidths=[6*cm, 3*cm, 3*cm, 3*cm])
    t_biom.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    story.append(t_biom)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("Ce (emissioni polveri): 1 / 1,2 / 1,5 secondo riduzione vs classe 5 stelle", small_style))
    story.append(Paragraph("Manutenzione biennale OBBLIGATORIA per tutta durata incentivo", small_style))
    story.append(PageBreak())

    # ===== SLIDE 10 - COLONNINE VE =====
    story.append(Paragraph("Colonnine Ricarica VE (II.G)", title_style))
    story.append(Paragraph("<font color='#d9534f'>NOVITA 2025 - Elettrificazione mobilita</font>", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Requisiti ammissibilita:</b>", subtitle_style))
    story.append(Paragraph("• <b>OBBLIGATORIO abbinamento</b> con PDC elettrica (III.A) stesso edificio", bullet_style))
    story.append(Paragraph("• Utenze BT/MT", bullet_style))
    story.append(Paragraph("• Potenza min: 7,4 kW", bullet_style))
    story.append(Paragraph("• Dispositivi smart: misura, trasmissione, comandi esterni", bullet_style))
    story.append(Paragraph("• Modo 3 o Modo 4 (CEI EN 61851)", bullet_style))
    story.append(Paragraph("• Dichiarazione conformita DM 37/2008", bullet_style))
    story.append(Paragraph("• Se uso pubblico: registrazione Piattaforma Unica Nazionale", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", subtitle_style))
    story.append(Paragraph("I = min(30% spesa colonnina ; incentivo PDC)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Costi massimi ammissibili:</b>", body_style))

    data_col = [
        ['Potenza', 'Cmax'],
        ['7,4-22 kW monofase', '2.400 EUR/punto'],
        ['7,4-22 kW trifase', '8.400 EUR/punto'],
        ['22-50 kW', '1.200 EUR/kW'],
        ['50-100 kW', '60.000 EUR/infrastr'],
        ['>100 kW', '110.000 EUR/infrastr']
    ]

    t_col = Table(data_col, colWidths=[8*cm, 7*cm])
    t_col.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    story.append(t_col)
    story.append(PageBreak())

    # ===== SLIDE 11 - REQUISITI TECNICI ZONE CLIMATICHE =====
    story.append(Paragraph("Requisiti tecnici per zona climatica", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Zone climatiche Italia (DPR 412/93):</b>", subtitle_style))
    story.append(Paragraph("Zone definite in base a gradi-giorno (GG) del comune:", small_style))
    story.append(Spacer(1, 0.2*cm))

    data_zone = [
        ['Zona', 'GG', 'Coefficiente ore (hr/Quf)', 'Esempi comuni'],
        ['A', '<=600', '600 h', 'Lampedusa, Porto Empedocle'],
        ['B', '601-900', '850 h', 'Catania, Palermo, Reggio Cal.'],
        ['C', '901-1.400', '1.100 h', 'Napoli, Bari, Cagliari'],
        ['D', '1.401-2.100', '1.400 h', 'Roma, Firenze, Ancona'],
        ['E', '2.101-3.000', '1.700 h', 'Milano, Torino, Bologna'],
        ['F', '>3.000', '1.800 h', 'Belluno, Cuneo, Trento']
    ]

    t_zone = Table(data_zone, colWidths=[1.5*cm, 2*cm, 4*cm, 7.5*cm])
    t_zone.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    story.append(t_zone)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Impatto sui calcoli incentivo:</b>", body_style))
    story.append(Paragraph("• Pompe di calore e biomassa: coefficiente hr aumenta in zone fredde", bullet_style))
    story.append(Paragraph("• Isolamento: percentuali incentivo maggiori in zone E,F (50% vs 40%)", bullet_style))
    story.append(Paragraph("• Serramenti: trasmittanza max piu restrittiva in zone fredde", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Zona climatica determina energia termica producibile e quindi incentivo</b>", highlight_style))
    story.append(PageBreak())

    # ===== SLIDE 12 - DIFFERENZE RESIDENZIALE/TERZIARIO =====
    story.append(Paragraph("Differenze Residenziale vs Terziario", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>AMBITO RESIDENZIALE</b>", subtitle_style))
    story.append(Paragraph("• Categorie catastali: A (escluso A/10)", bullet_style))
    story.append(Paragraph("• Soggetti: persone fisiche, condomini", bullet_style))
    story.append(Paragraph("• <b>Accesso: TUTTI interventi Titolo II e III</b>", bullet_style))
    story.append(Paragraph("• <b>NESSUN vincolo riduzione energia primaria</b>", bullet_style))
    story.append(Paragraph("• Intensita incentivo: percentuali standard", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>AMBITO TERZIARIO</b>", subtitle_style))
    story.append(Paragraph("• Categorie catastali: B, C, D, E (Tabella 1 Allegato 1)", bullet_style))
    story.append(Paragraph("• Soggetti: titolari reddito impresa/agrario, ETS economici", bullet_style))
    story.append(Paragraph("• <b>Accesso: TUTTI interventi Titolo II e III CON VINCOLI</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>VINCOLI SPECIFICI IMPRESE/ETS ECONOMICI su edifici terziario:</b>", body_style))
    story.append(Paragraph("• <b>NON ammesse pompe di calore a gas</b> (art. 25, comma 2)", bullet_style))
    story.append(Paragraph("• <b>Riduzione domanda energia primaria OBBLIGATORIA:</b>", bullet_style))
    story.append(Paragraph("  - 10% per: II.B (serramenti), II.E (illuminazione), II.F (building autom.)", bullet_style))
    story.append(Paragraph("  - 20% per: multi-intervento II.B+altro Titolo II, II.E+altro Tit.II, II.F+altro Tit.II", bullet_style))
    story.append(Paragraph("  - 20% per: II.G (colonnine VE), II.H (fotovoltaico), II.D (nZEB)", bullet_style))
    story.append(Paragraph("• Verifica tramite APE ante e post operam", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>IMPORTANTE: Edifici pubblici specifici (scuole, ospedali, comuni <15k ab.) hanno intensita 100%</b>", highlight_style))
    story.append(PageBreak())

    # ===== SLIDE 13 - MULTI-INTERVENTO =====
    story.append(Paragraph("Multi-intervento - Combinazioni", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Regole generali:</b>", subtitle_style))
    story.append(Paragraph("• Piu interventi nella stessa domanda su stesso edificio/unita", bullet_style))
    story.append(Paragraph("• Ogni intervento mantiene proprie condizioni ammissibilita", bullet_style))
    story.append(Paragraph("• Incentivo totale: somma incentivi singoli", bullet_style))
    story.append(Paragraph("• Tutti interventi devono essere realizzati", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Combinazioni piu comuni:</b>", subtitle_style))
    story.append(Paragraph("• <b>Riqualificazione completa involucro:</b> II.A (isolamento) + II.B (serramenti)", bullet_style))
    story.append(Paragraph("  - Incentivo aumenta a 55% se aggiunto III.A, III.B, III.C o III.E", bullet_style))
    story.append(Spacer(1, 0.1*cm))

    story.append(Paragraph("• <b>Elettrificazione totale:</b> III.A (PDC) + II.H (FV) + II.G (Colonnine VE)", bullet_style))
    story.append(Paragraph("  - II.H e II.G DEVONO essere abbinati a III.A", bullet_style))
    story.append(Paragraph("  - Incentivo II.H e II.G limitati a incentivo III.A", bullet_style))
    story.append(Spacer(1, 0.1*cm))

    story.append(Paragraph("• <b>Riqualificazione profonda:</b> II.A + II.B + III.A + II.H", bullet_style))
    story.append(Paragraph("  - Massimizza incentivo e risparmio energetico", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Vantaggi:</b>", body_style))
    story.append(Paragraph("• Unica pratica GSE | Percentuali incentivo maggiori (55%)", bullet_style))
    story.append(Paragraph("• Riqualificazione energetica completa | Massimizzazione incentivo", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 14 - PROCEDURA E DOCUMENTAZIONE =====
    story.append(Paragraph("Modalita accesso e documentazione", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>1. ACCESSO DIRETTO (lavori gia conclusi):</b>", subtitle_style))
    story.append(Paragraph("• Richiesta dopo conclusione lavori (max 60 giorni)", bullet_style))
    story.append(Paragraph("• Tutti i soggetti", bullet_style))
    story.append(Paragraph("• Documentazione completa + fatture quietanzate + pagamenti", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>2. PRENOTAZIONE (lavori da iniziare):</b>", subtitle_style))
    story.append(Paragraph("• Solo PA, ETS, ESCO per conto PA/ETS", bullet_style))
    story.append(Paragraph("• Richiesta PRIMA inizio lavori", bullet_style))
    story.append(Paragraph("• Certezza incentivo prima di investire", bullet_style))
    story.append(Paragraph("• Acconti possibili: 50% se 2 anni, 40% se 5 anni", bullet_style))
    story.append(Paragraph("• Rata intermedia al 50% avanzamento lavori", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Documenti comuni per tutti:</b>", subtitle_style))
    story.append(Paragraph("• Scheda-domanda firmata digitalmente", bullet_style))
    story.append(Paragraph("• Fatture quietanzate e bonifici/mandati pagamento", bullet_style))
    story.append(Paragraph("• Visura catastale edificio", bullet_style))
    story.append(Paragraph("• Asseverazione tecnico abilitato (non per Catalogo <=35kW se I<3.500EUR)", bullet_style))
    story.append(Paragraph("• Schede tecniche apparecchiature con marcature CE", bullet_style))
    story.append(Paragraph("• Dichiarazione conformita impianti DM 37/08", bullet_style))
    story.append(Paragraph("• Documentazione fotografica ante/durante/post", bullet_style))
    story.append(Paragraph("• APE ante e post (per alcuni interventi e sempre per terziario)", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 15 - ESEMPI CALCOLO (RESIDENZIALE) =====
    story.append(Paragraph("Esempio 1 - Villetta residenziale", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Contesto: Villetta unifamiliare - Zona E - Residenziale</b>", body_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Intervento: Pompa di calore aria/acqua 12 kW</b>", subtitle_style))
    story.append(Paragraph("• Potenza: 12 kW | SCOP: 3,5 (>minimo 2,825)", bullet_style))
    story.append(Paragraph("• Spesa totale: 18.000 EUR (installazione + dismissione)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", body_style))
    story.append(Paragraph("• Energia termica annua: Qu = Prated × Quf = 12 kW × 1.700 h = 20.400 kWh", bullet_style))
    story.append(Paragraph("• Ei = Qu × [1 - 1/SCOP] × kp = 20.400 × 0,714 × 1,24 = 18.060 kWh", bullet_style))
    story.append(Paragraph("• Ci (aria/acqua <=35kW) = 0,15 EUR/kWh", bullet_style))
    story.append(Paragraph("• <b>I annuo = 18.060 × 0,15 = 2.709 EUR/anno</b>", bullet_style))
    story.append(Paragraph("• <b>I totale (2 anni) = 5.418 EUR</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Erogazione: Unica rata (< 15.000 EUR)</b>", highlight_style))
    story.append(Paragraph("Tempistica: 2-4 mesi da ammissione", small_style))
    story.append(PageBreak())

    # ===== SLIDE 16 - ESEMPIO AZIENDALE =====
    story.append(Paragraph("Esempio 2 - Capannone aziendale", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Contesto: Capannone artigianale - Zona D - Terziario</b>", body_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Intervento: Isolamento copertura 600 m2</b>", subtitle_style))
    story.append(Paragraph("• Superficie: 600 m2 | Trasmittanza post: 0,20 W/m2K", bullet_style))
    story.append(Paragraph("• Spesa: 48.000 EUR (80 EUR/m2)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Calcolo incentivo:</b>", body_style))
    story.append(Paragraph("• Cmax coperture esterne = 300 EUR/m2", bullet_style))
    story.append(Paragraph("• Spesa ammissibile = min(48.000 ; 600×300) = 48.000 EUR", bullet_style))
    story.append(Paragraph("• Percentuale base zona D: 40%", bullet_style))
    story.append(Paragraph("• <b>Incentivo = 40% × 48.000 = 19.200 EUR</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Erogazione: 5 rate annuali da 3.840 EUR</b>", highlight_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>NOTA IMPRESE su TERZIARIO:</b>", body_style))
    story.append(Paragraph("APE ante e post OBBLIGATORI per verificare riduzione energia primaria", small_style))
    story.append(Paragraph("Se combinato con III.A/B/C/E: incentivo aumenta a 55% = 26.400 EUR", small_style))
    story.append(PageBreak())

    # ===== SLIDE 17 - ESEMPIO MULTI-INTERVENTO =====
    story.append(Paragraph("Esempio 3 - Multi-intervento condominio", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Contesto: Condominio 8 unita - Zona E - Residenziale</b>", body_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Intervento combinato: PDC 80 kW + FV 40 kWp + accumulo 50 kWh</b>", subtitle_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>1. Pompa di Calore geotermie salamoia/acqua 80 kW:</b>", body_style))
    story.append(Paragraph("• Spesa: 85.000 EUR | SCOP: 3,5", bullet_style))
    story.append(Paragraph("• Energia annua: Qu = 80 × 1.700 = 136.000 kWh", bullet_style))
    story.append(Paragraph("• Ei = 136.000 × 0,714 × 1,24 = 120.400 kWh", bullet_style))
    story.append(Paragraph("• Ci (salamoia/acqua >35kW) = 0,06 EUR/kWh", bullet_style))
    story.append(Paragraph("• <b>I PDC totale (5 anni) = 120.400 × 0,06 = 7.224 EUR/anno × 5 = 36.120 EUR</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>2. Fotovoltaico + accumulo:</b>", body_style))
    story.append(Paragraph("• FV 40 kWp: spesa 52.000 EUR → ammissibile: 40 × 1.500 = 60.000 (OK)", bullet_style))
    story.append(Paragraph("• Accumulo 50 kWh: spesa 38.000 EUR → ammissibile: 50 × 1.000 = 50.000 (OK)", bullet_style))
    story.append(Paragraph("• Incentivo FV: 20% × (52.000 + 38.000) = 18.000 EUR", bullet_style))
    story.append(Paragraph("• <b>Limitato a incentivo PDC = 18.000 EUR (OK)</b>", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>INCENTIVO TOTALE: 36.120 + 18.000 = 54.120 EUR</b>", highlight_style))
    story.append(Paragraph("Erogazione: 5 rate annuali da 10.824 EUR", body_style))
    story.append(PageBreak())

    # ===== SLIDE 18 - TEMPISTICHE E SCADENZE =====
    story.append(Paragraph("Tempistiche e scadenze", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Presentazione domanda:</b>", subtitle_style))
    story.append(Paragraph("• Accesso diretto: <b>entro 60 giorni dalla conclusione lavori</b>", bullet_style))
    story.append(Paragraph("• Prenotazione: prima inizio lavori", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Istruttoria GSE:</b>", subtitle_style))
    story.append(Paragraph("• Verifica formale: 30 giorni", bullet_style))
    story.append(Paragraph("• Istruttoria completa: 60-90 giorni mediamente", bullet_style))
    story.append(Paragraph("• Possibili richieste integrazioni", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Realizzazione (prenotazione):</b>", subtitle_style))
    story.append(Paragraph("• Comunicazione avvio lavori: entro 90 giorni da ammissione", bullet_style))
    story.append(Paragraph("• Conclusione lavori: entro 24 mesi (36 per PA)", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Conservazione documenti e vincoli:</b>", subtitle_style))
    story.append(Paragraph("• Documenti: 5 anni dopo ultima erogazione", bullet_style))
    story.append(Paragraph("• Mantenimento destinazione uso: per durata incentivo", bullet_style))
    story.append(Paragraph("• Controlli GSE possibili in qualsiasi momento", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Prima erogazione: entro ultimo giorno mese successivo al bimestre attivazione</b>", highlight_style))
    story.append(PageBreak())

    # ===== SLIDE 19 - CUMULABILITA =====
    story.append(Paragraph("Cumulabilita con altri incentivi", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>REGOLA GENERALE:</b>", subtitle_style))
    story.append(Paragraph("<b>NON cumulabile con altri incentivi statali</b>", highlight_style))
    story.append(Paragraph("(eccetto fondi garanzia, fondi rotazione, contributi conto interesse)", small_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>ECCEZIONI - Cumulabile con:</b>", subtitle_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>1. Edifici PA (proprieta e utilizzo diretto):</b>", body_style))
    story.append(Paragraph("• Cumulabile con incentivi conto capitale (statali e non)", bullet_style))
    story.append(Paragraph("• Limite: finanziamento complessivo max 100% spese ammissibili", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>2. CER e configurazioni autoconsumo:</b>", body_style))
    story.append(Paragraph("• Cumulabile con incentivi condivisione energia (DM CACER 414/2023)", bullet_style))
    story.append(Paragraph("• Nei limiti intensita aiuto previste", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>3. Imprese ed ETS economici:</b>", body_style))
    story.append(Paragraph("• Cumulabile con altri aiuti di Stato", bullet_style))
    story.append(Paragraph("• Nei limiti intensita aiuti art. 27 Decreto", bullet_style))
    story.append(Paragraph("• Verifica tramite Registro Nazionale Aiuti (RNA) e SIAN", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Aspetti fiscali:</b>", body_style))
    story.append(Paragraph("• Contributo in conto impianti", bullet_style))
    story.append(Paragraph("• NO ritenuta 4% | Fuori campo IVA | No obbligo fattura", bullet_style))
    story.append(PageBreak())

    # ===== SLIDE 20 - PUNTI CHIAVE E CONCLUSIONI =====
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Punti chiave da ricordare", title_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Novita CT 3.0 rispetto a CT 2.0:</b>", subtitle_style))
    story.append(Paragraph("• Soglia pagamento unico: 5.000 → <b>15.000 EUR</b>", bullet_style))
    story.append(Paragraph("• Nuovi interventi: <b>Colonnine VE (II.G)</b> e <b>Fotovoltaico combinato (II.H)</b>", bullet_style))
    story.append(Paragraph("• Biomassa: classe 5 stelle se sostituisci biomassa/carbone/olio/gasolio", bullet_style))
    story.append(Paragraph("• Maggiorazioni: +10% componenti UE, +5/10/15% FV registro tecnologie", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Prima di iniziare verificare:</b>", subtitle_style))
    story.append(Paragraph("• Edificio esistente, regolarmente accatastato, impianti a norma", bullet_style))
    story.append(Paragraph("• Zona climatica e requisiti tecnici minimi specifici", bullet_style))
    story.append(Paragraph("• Per terziario imprese: vincoli riduzione energia primaria", bullet_style))
    story.append(Paragraph("• Abbinamenti obbligatori: II.H e II.G con III.A", bullet_style))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Strategie massimizzazione:</b>", subtitle_style))
    story.append(Paragraph("• Multi-intervento: involucro (II.A+II.B) + impianti (III.A) = 55%", bullet_style))
    story.append(Paragraph("• Elettrificazione: III.A + II.H + II.G per indipendenza energetica", bullet_style))
    story.append(Paragraph("• Prenotazione PA/ETS: certezza incentivo + acconti", bullet_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Contatti utili:</b>", body_style))
    story.append(Paragraph("Portale: <b>portaltermico.gse.it</b> | Tel: <b>800 19 00 81</b> | Email: <b>contotermico@gse.it</b>", bullet_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("<b>GRAZIE PER L'ATTENZIONE!</b>", title_style))

    # Genera PDF
    doc.build(story)

    print(f"\nPresentazione creata con successo!")
    print(f"File: {filename}")
    print(f"Percorso: {os.path.abspath(filename)}")
    print(f"\nLa presentazione contiene 20 slide sul Conto Termico 3.0")
    print(f"Basata su Regole Applicative DM 7 agosto 2025")

if __name__ == "__main__":
    print("Generazione presentazione Conto Termico 3.0...")
    print("Basata su dati ufficiali estratti da Regole_Extracted.txt")
    print("Creazione in corso...\n")

    try:
        create_presentation()
    except ImportError as e:
        print("\nERRORE: Librerie mancanti!")
        print("\nInstalla le dipendenze con:")
        print("   pip install reportlab pillow")
        print("\nPoi esegui nuovamente lo script.")
    except Exception as e:
        print(f"\nERRORE: {str(e)}")
        print("\nControlla che tutte le librerie siano installate correttamente.")
