import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import yfinance as yf
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patrimonio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            categoria TEXT,
            descrizione TEXT,
            valore REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS titoli (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            nome TEXT,
            tipo TEXT,
            quantita REAL NOT NULL,
            prezzo_acquisto REAL NOT NULL,
            data_acquisto DATE NOT NULL,
            broker TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ============================================================
# FUNZIONI - PATRIMONIO
# ============================================================
def aggiungi_voce_patrimonio(data, categoria, descrizione, valore):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO patrimonio (data, categoria, descrizione, valore)
        VALUES (?, ?, ?, ?)
    ''', (data, categoria, descrizione, valore))
    conn.commit()
    conn.close()

def leggi_patrimonio():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM patrimonio ORDER BY data", conn)
    conn.close()
    return df

def elimina_voce_patrimonio(id_voce):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patrimonio WHERE id = ?", (id_voce,))
    conn.commit()
    conn.close()

# ============================================================
# FUNZIONI - TITOLI
# ============================================================
def aggiungi_titolo(ticker, nome, tipo, quantita, prezzo_acquisto, data_acquisto, broker):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO titoli (ticker, nome, tipo, quantita, prezzo_acquisto, data_acquisto, broker)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ticker.upper(), nome, tipo, quantita, prezzo_acquisto, data_acquisto, broker))
    conn.commit()
    conn.close()

def leggi_titoli():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM titoli", conn)
    conn.close()
    return df

def elimina_titolo(id_titolo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM titoli WHERE id = ?", (id_titolo,))
    conn.commit()
    conn.close()

@st.cache_data(ttl=300)  # cache 5 minuti per non martellare Yahoo Finance
def prezzo_attuale(ticker):
    try:
        dati = yf.Ticker(ticker).history(period="1d")
        if not dati.empty:
            return round(dati['Close'].iloc[-1], 2)
    except Exception:
        pass
    return None

# ============================================================
# STREAMLIT APP
# ============================================================
st.set_page_config(page_title="Il Mio Patrimonio", layout="wide")
st.title("💰 Il Mio Patrimonio")

tab1, tab2 = st.tabs(["📊 Patrimonio Generale", "📈 Portafoglio Titoli"])

# ------------------------------------------------------------
# TAB 1 - PATRIMONIO
# ------------------------------------------------------------
with tab1:
    st.subheader("Aggiungi voce al patrimonio")

    with st.form("nuovo_dato_patrimonio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", key="data_patr")
            categoria = st.selectbox("Categoria",
                                       ["Conto corrente", "Investimenti", "Immobili", "Altro"])
        with col2:
            descrizione = st.text_input("Descrizione")
            valore = st.number_input("Valore (€)", step=100.0)

        if st.form_submit_button("➕ Aggiungi"):
            aggiungi_voce_patrimonio(data, categoria, descrizione, valore)
            st.success("Dato aggiunto!")
            st.rerun()

    df_patrimonio = leggi_patrimonio()

    if not df_patrimonio.empty:
        st.subheader("📋 Tabella patrimonio")
        st.dataframe(df_patrimonio, use_container_width=True)

        # Elimina voce
        with st.expander("🗑️ Elimina una voce"):
            id_da_eliminare = st.number_input("ID da eliminare", min_value=0, step=1)
            if st.button("Elimina voce patrimonio"):
                elimina_voce_patrimonio(id_da_eliminare)
                st.success("Voce eliminata!")
                st.rerun()

        # Grafico andamento nel tempo
        df_patrimonio['data'] = pd.to_datetime(df_patrimonio['data'])
        df_grouped = df_patrimonio.groupby('data')['valore'].sum().reset_index()
        df_grouped['patrimonio_totale'] = df_grouped['valore'].cumsum()

        fig1 = px.line(df_grouped, x='data', y='patrimonio_totale',
                        title="Andamento del patrimonio nel tempo", markers=True)
        st.plotly_chart(fig1, use_container_width=True)

        # Grafico per categoria
        fig2 = px.pie(df_patrimonio, values='valore', names='categoria',
                       title="Distribuzione per categoria")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nessun dato ancora inserito nel patrimonio.")

# ------------------------------------------------------------
# TAB 2 - TITOLI
# ------------------------------------------------------------
with tab2:
    st.subheader("Aggiungi titolo al portafoglio")

    with st.form("nuovo_titolo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("Ticker (es. AAPL, VWCE.MI)")
            tipo = st.selectbox("Tipo", ["Azione", "ETF", "Obbligazione", "Crypto"])
        with col2:
            quantita = st.number_input("Quantità", min_value=0.0, step=1.0)
            prezzo_acquisto = st.number_input("Prezzo acquisto (€)", min_value=0.0)
        with col3:
            data_acquisto = st.date_input("Data acquisto", key="data_titolo")
            broker = st.text_input("Broker")

        if st.form_submit_button("➕ Aggiungi titolo"):
            if ticker.strip() == "":
                st.error("Inserisci un ticker valido.")
            else:
                aggiungi_titolo(ticker, ticker.upper(), tipo, quantita,
                                 prezzo_acquisto, data_acquisto, broker)
                st.success("Titolo aggiunto!")
                st.rerun()

    df_titoli = leggi_titoli()

    if not df_titoli.empty:
        with st.spinner("Recupero prezzi aggiornati..."):
            df_titoli['prezzo_attuale'] = df_titoli['ticker'].apply(prezzo_attuale)

        df_titoli['valore_investito'] = df_titoli['quantita'] * df_titoli['prezzo_acquisto']
        df_titoli['valore_attuale'] = df_titoli['quantita'] * df_titoli['prezzo_attuale']
        df_titoli['guadagno_perdita'] = df_titoli['valore_attuale'] - df_titoli['valore_investito']
        df_titoli['rendimento_%'] = (df_titoli['guadagno_perdita'] / df_titoli['valore_investito'] * 100).round(2)

        st.subheader("📋 Tabella titoli")
        st.dataframe(df_titoli, use_container_width=True)

        # Elimina titolo
        with st.expander("🗑️ Elimina un titolo"):
            id_titolo_elim = st.number_input("ID titolo da eliminare", min_value=0, step=1)
            if st.button("Elimina titolo"):
                elimina_titolo(id_titolo_elim)
                st.success("Titolo eliminato!")
                st.rerun()

        # Metriche riassuntive
        totale_investito = df_titoli['valore_investito'].sum()
        totale_attuale = df_titoli['valore_attuale'].sum()
        gl_totale = df_titoli['guadagno_perdita'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Totale investito", f"€ {totale_investito:,.2f}")
        col2.metric("Valore attuale", f"€ {totale_attuale:,.2f}")
        col3.metric("Guadagno/Perdita", f"€ {gl_totale:,.2f}",
                    delta=f"{(gl_totale/totale_investito*100):.2f}%" if totale_investito else "0%")

        # Grafico composizione portafoglio
        fig3 = px.pie(df_titoli, values='valore_attuale', names='ticker',
                       title="Composizione portafoglio")
        st.plotly_chart(fig3, use_container_width=True)

        # Grafico guadagno/perdita per titolo
        fig4 = px.bar(df_titoli, x='ticker', y='guadagno_perdita',
                       color='guadagno_perdita',
                       color_continuous_scale=['red', 'green'],
                       title="Guadagno/Perdita per titolo")
        st.plotly_chart(fig4, use_container_width=True)

        # Bottone per sincronizzare col patrimonio generale
        st.divider()
        if st.button("🔄 Sincronizza valore titoli nel Patrimonio Generale"):
            aggiungi_voce_patrimonio(
                data=datetime.today().date(),
                categoria="Investimenti",
                descrizione="Portafoglio titoli (auto-sync)",
                valore=totale_attuale
            )
            st.success(f"Aggiunto € {totale_attuale:,.2f} al patrimonio generale!")
            st.rerun()
    else:
        st.info("Nessun titolo ancora inserito nel portafoglio.")
