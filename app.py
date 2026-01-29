import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database

st.set_page_config(page_title="Financeiro 360 - Professor", layout="wide")

# Configuração de Pastas (Caminhos relativos para o Servidor)
EXTRATOS_DIR = "extratos"
if not os.path.exists(EXTRATOS_DIR): 
    os.makedirs(EXTRATOS_DIR)

def format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def carregar_todos_extratos():
    arquivos = [f for f in os.listdir(EXTRATOS_DIR) if f.endswith('.ofx')]
    lista_df = []
    for arq in arquivos:
        caminho = os.path.join(EXTRATOS_DIR, arq)
        try:
            with open(caminho, 'rb') as f:
                df_arq = load_ofx_data(f)
                lista_df.append(df_arq)
        except: continue
    return pd.concat(lista_df, ignore_index=True) if lista_df else pd.DataFrame()

st.title("🏦 Central de Inteligência Financeira")

# --- SIDEBAR: MOBILIDADE E LANÇAMENTO ---
with st.sidebar:
    st.header("📤 Enviar do Tablet")
    uploaded_ofx = st.file_uploader("Subir novo OFX", type="ofx")
    if uploaded_ofx:
        with open(os.path.join(EXTRATOS_DIR, uploaded_ofx.name), "wb") as f:
            f.write(uploaded_ofx.getbuffer())
        st.success("Extrato pronto para conciliação!")
        st.cache_data.clear()

    st.divider()
    st.header("➕ Lançamento Manual")
    with st.expander("Dinheiro ou Extra"):
        desc_man = st.text_input("Descrição")
        val_man = st.number_input("Valor", step=0.01)
        cat_man = st.selectbox("Categoria ", CAT_ENTRADAS + CAT_SAIDAS)
        data_man = st.date_input("Data", datetime.now())
        if st.button("Salvar Registro"):
            novo_lanc = pd.DataFrame([{
                'Data': data_man.strftime('%Y-%m-%d'),
                'Descrição': desc_man,
                'Valor': val_man,
                'Categoria': cat_man,
                'ID_Transacao': f"MAN-{datetime.now().timestamp()}",
                'Banco': 'Manual/Dinheiro
