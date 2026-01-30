import streamlit as st
import pandas as pd
import plotly.express as px
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database

st.set_page_config(page_title="Financeiro 360", layout="wide", initial_sidebar_state="collapsed")

# Inicializa sessão
if 'fila' not in st.session_state: st.session_state['fila'] = pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Usuário")
    user_name = st.text_input("Nome", value="Gabriel")
    arquivos = st.file_uploader("Subir OFX", type="ofx", accept_multiple_files=True)
    if st.button("Processar"):
        if arquivos:
            dfs = [load_ofx_data(a) for a in arquivos]
            st.session_state['fila'] = pd.concat([st.session_state['fila']] + dfs).drop_duplicates(subset=['ID_Transacao'])
            st.rerun()

# --- CARREGAR DADOS ---
df_hist = load_database(user_name)

# --- TABS ---
t1, t2, t3 = st.tabs(["📑 Conferência", "📈 Evolução", "⚖️ Impostos"])

with t1:
    c1, c2 = st.columns(2)
    mes = c1.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano = c2.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes}/{ano}"
    
    if not st.session_state['fila'].empty:
        df_input = predict_data(st.session_state['fila'], df_hist, user_name)
        df_input['Data_Ex'] = pd.to_datetime(df_input['Data']).dt.strftime('%d/%m/%Y')
        
        df_ed = st.data_editor(
            df_input[['Contabilizar', 'Valor', 'Categoria', 'Segmento', 'Descrição', 'Data_Ex', 'ID_Transacao']],
            hide_index=True, use_container_width=True,
            column_config={"Categoria": st.column_config.SelectboxColumn(options=CAT_ENTRADAS + CAT_SAIDAS),
                           "Segmento": st.column_config.SelectboxColumn(options=["PF", "MEI"]),
                           "ID_Transacao": None}
        )
        
        if st.button(f"💾 SALVAR EM {label_ref.upper()}", type="primary", use_container_width=True):
            to_save = df_ed[df_ed['Contabilizar'] == True].copy()
            if not to_save.empty:
                to_save['Data'] = to_save['Data_Ex']
                save_to_database(to_save, label_ref, user_name)
                ids = to_save['ID_Transacao'].tolist()
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids)]
                st.rerun()

with t2:
    if not df_hist.empty:
        st.subheader("📊 Evolução Mensal")
        df_hist['Valor'] = pd.to_numeric(df_hist['Valor'])
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], dayfirst=True)
        # Gráfico de Barras Entradas vs Saídas
        res = df_hist.groupby('Mes_Referencia')['Valor'].agg([('Ganhos', lambda x: x[x>0].sum()), ('Gastos', lambda x: abs(x[x<0].sum()))]).reset_index()
        st.bar_chart(res.set_index('Mes_Referencia'))
    else: st.info("Sem dados para exibir.")

with t3:
    if not df_hist.empty:
        fat_mei = df_hist[(df_hist['Segmento'] == 'MEI') & (df_hist['Valor'] > 0)]['Valor'].sum()
        st.metric("Faturamento MEI (Limite 81k)", f"R$ {fat_mei:,.2f}")
        st.progress(min(fat_mei/81000, 1.0))