"""
Componenti UI riutilizzabili per Streamlit.

Contiene funzioni per rendering consistente di risultati, warning, input comuni.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime


def format_currency(valore: float, simbolo: str = "€") -> str:
    """
    Formatta valore come valuta.

    Args:
        valore: Valore numerico
        simbolo: Simbolo valuta

    Returns:
        Stringa formattata
    """
    return f"{valore:,.2f} {simbolo}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percentage(valore: float, decimali: int = 1) -> str:
    """
    Formatta valore come percentuale.

    Args:
        valore: Valore decimale (0.15 = 15%)
        decimali: Numero decimali

    Returns:
        Stringa formattata
    """
    return f"{valore * 100:.{decimali}f}%"


def render_risultato_incentivo(
    risultato: Dict[str, Any],
    tipo_intervento: str,
    mostra_dettagli: bool = True,
    key_prefix: str = ""
) -> None:
    """
    Renderizza risultato calcolo incentivo in modo uniforme.

    Args:
        risultato: Dizionario risultato da calculator
        tipo_intervento: Nome intervento (es. "Pompe di Calore", "Serramenti")
        mostra_dettagli: Se mostrare sezione dettagli espandibile
        key_prefix: Prefisso per chiavi Streamlit
    """
    # Header con incentivo totale
    st.success(f"### Incentivo Totale: {format_currency(risultato['incentivo_totale'])}")

    # Riepilogo principale
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Spesa ammissibile",
            value=format_currency(risultato.get('costo_ammissibile', risultato.get('spesa_ammissibile', 0)))
        )

    with col2:
        anni = risultato.get('erogazione', {}).get('numero_rate', 2)
        st.metric(
            label="Erogazione",
            value=f"{anni} anni" if risultato['incentivo_totale'] > 15000 else "Rata unica"
        )

    with col3:
        if 'percentuale_copertura' in risultato:
            st.metric(
                label="Copertura spesa",
                value=f"{risultato['percentuale_copertura']:.1f}%"
            )

    # Rateizzazione
    if 'erogazione' in risultato and risultato['erogazione']['numero_rate'] > 1:
        st.divider()
        st.subheader("Rateizzazione")

        erogazione = risultato['erogazione']
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Prima rata**: {format_currency(erogazione['prima_rata'])}")
            st.write(f"**Rate successive** ({erogazione['numero_rate']-1}): {format_currency(erogazione['rata_annua'])} ciascuna")

        with col2:
            # Tabella rate
            rate_data = []
            for i in range(erogazione['numero_rate']):
                anno = i + 1
                importo = erogazione['prima_rata'] if i == 0 else erogazione['rata_annua']
                rate_data.append({
                    "Anno": anno,
                    "Importo": format_currency(importo)
                })

            df_rate = pd.DataFrame(rate_data)
            st.dataframe(df_rate, hide_index=True, use_container_width=True)

    # Dettagli tecnici (opzionale)
    if mostra_dettagli:
        with st.expander("Dettagli calcolo"):
            st.json(risultato, expanded=False)


def render_warning_vincoli(
    messaggio: str,
    tipo: str = "warning",  # "warning", "error", "info"
    dismissible: bool = False
) -> None:
    """
    Renderizza warning/errore vincoli terziario in modo consistente.

    Args:
        messaggio: Messaggio da mostrare
        tipo: Tipo alert ("warning", "error", "info")
        dismissible: Se l'alert può essere chiuso
    """
    if tipo == "error":
        st.error(messaggio, icon="🚫")
    elif tipo == "warning":
        st.warning(messaggio, icon="⚠️")
    else:
        st.info(messaggio, icon="ℹ️")


def render_storico_calcoli(
    storico: List[Dict[str, Any]],
    tipo_intervento: Optional[str] = None,
    max_items: int = 10,
    key_prefix: str = "storico"
) -> None:
    """
    Renderizza storico calcoli in formato tabella.

    Args:
        storico: Lista calcoli precedenti
        tipo_intervento: Filtra per tipo intervento (opzionale)
        max_items: Numero massimo elementi da mostrare
        key_prefix: Prefisso chiavi Streamlit
    """
    if not storico:
        st.info("Nessun calcolo salvato ancora.")
        return

    # Filtra per tipo intervento se specificato
    if tipo_intervento:
        storico_filtrato = [s for s in storico if s.get('tipo_intervento') == tipo_intervento]
    else:
        storico_filtrato = storico

    if not storico_filtrato:
        st.info(f"Nessun calcolo salvato per {tipo_intervento}.")
        return

    # Limita numero elementi
    storico_limitato = storico_filtrato[-max_items:]

    # Prepara dati per tabella
    dati_tabella = []
    for idx, calc in enumerate(reversed(storico_limitato)):
        dati_tabella.append({
            "Data": calc.get('timestamp', 'N/A'),
            "Tipo": calc.get('tipo_intervento', 'N/A'),
            "Incentivo": format_currency(calc.get('incentivo_totale', 0)),
            "Soggetto": calc.get('tipo_soggetto', 'N/A'),
            "Note": calc.get('note', '')[:50]  # Limita lunghezza
        })

    df_storico = pd.DataFrame(dati_tabella)
    st.dataframe(df_storico, hide_index=True, use_container_width=True)

    # Bottone esporta CSV
    if st.button("Esporta storico CSV", key=f"{key_prefix}_export"):
        csv = df_storico.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"storico_ct_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key=f"{key_prefix}_download"
        )


def render_card_info(
    titolo: str,
    valore: str,
    descrizione: Optional[str] = None,
    icona: Optional[str] = None,
    colore: str = "blue"
) -> None:
    """
    Renderizza card informativa.

    Args:
        titolo: Titolo card
        valore: Valore principale
        descrizione: Descrizione aggiuntiva
        icona: Emoji icona
        colore: Colore sfondo ("blue", "green", "red", "orange")
    """
    colore_map = {
        "blue": "#E3F2FD",
        "green": "#E8F5E9",
        "red": "#FFEBEE",
        "orange": "#FFF3E0"
    }

    bg_color = colore_map.get(colore, "#E3F2FD")

    html = f"""
    <div style="
        background-color: {bg_color};
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid {colore};
        margin: 10px 0;
    ">
        <div style="font-size: 14px; color: #666;">
            {icona + ' ' if icona else ''}{titolo}
        </div>
        <div style="font-size: 24px; font-weight: bold; margin: 5px 0;">
            {valore}
        </div>
        {f'<div style="font-size: 12px; color: #888;">{descrizione}</div>' if descrizione else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_progress_bar(
    valore_attuale: float,
    valore_target: float,
    label: str = "",
    formato: str = "percentuale"  # "percentuale" o "valore"
) -> None:
    """
    Renderizza barra progresso con label.

    Args:
        valore_attuale: Valore corrente
        valore_target: Valore target/massimo
        label: Label descrittiva
        formato: Come formattare i valori
    """
    percentuale = min(valore_attuale / valore_target, 1.0) if valore_target > 0 else 0

    if formato == "percentuale":
        testo = f"{label}: {percentuale*100:.1f}% ({valore_attuale:.1f}/{valore_target:.1f})"
    else:
        testo = f"{label}: {format_currency(valore_attuale)} / {format_currency(valore_target)}"

    st.progress(percentuale, text=testo)


def render_alert_normativa(
    articolo: str,
    testo: str,
    tipo: str = "info"
) -> None:
    """
    Renderizza alert con riferimento normativo.

    Args:
        articolo: Riferimento articolo (es. "Art. 25, comma 2")
        testo: Testo normativa
        tipo: Tipo alert
    """
    messaggio = f"**{articolo}**: {testo}"

    if tipo == "warning":
        st.warning(messaggio, icon="⚖️")
    elif tipo == "error":
        st.error(messaggio, icon="⚖️")
    else:
        st.info(messaggio, icon="⚖️")
