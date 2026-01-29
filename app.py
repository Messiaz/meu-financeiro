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
                'Banco': 'Manual/Dinheiro',
                'Tipo': '🟢 Crédito' if val_man > 0 else '🔴 Débito',
                'Contabilizar': True,
                'Segmento': 'PF'
            }])
            save_to_database(novo_lanc, f"{data_man.strftime('%b')}/{data_man.year}")
            st.success("Salvo com sucesso!")
            st.rerun()

    st.divider()
    mes_nome = st.selectbox("Mês Referência", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"

# Carregar dados
df_all = carregar_todos_extratos()
df_hist = load_database()

# --- SEÇÃO MEI (RASTRADOR) ---
if not df_hist.empty:
    df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], format='mixed')
    fat_anual = df_hist[(df_hist['Data_DT'].dt.year == ano_ref) & (df_hist['Valor'] > 0)]['Valor'].sum()
    limite_mei = 81000.00
    perc = (fat_anual / limite_mei)
    
    st.write(f"### 🛡️ Limite MEI {ano_ref}")
    col_mei1, col_mei2 = st.columns([3, 1])
    col_mei1.progress(min(perc, 1.0), text=f"Faturamento: {format_brl(fat_anual)}")
    col_mei2.metric("Disponível", format_brl(limite_mei - fat_anual))

# --- ABAS ---
tab_concilia, tab_mensal, tab_anual = st.tabs(["📝 Conciliação", "📈 Evolução Mensal", "📊 Evolução Anual"])

with tab_concilia:
    if not df_all.empty:
        meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
        df_all['Data_DT'] = pd.to_datetime(df_all['Data'], format='mixed')
        df_mes_ofx = df_all[(df_all['Data_DT'].dt.month == meses_map[mes_nome]) & (df_all['Data_DT'].dt.year == ano_ref)].copy()
        
        if df_mes_ofx.empty:
            st.warning(f"Sem transações OFX para {label_ref}.")
        else:
            df_input = predict_data(df_mes_ofx, df_hist)
            df_edited = st.data_editor(df_input, hide_index=True, use_container_width=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status"),
                    "Contabilizar": st.column_config.CheckboxColumn("✅"),
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large"),
                    "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS)
                },
                disabled=["Data", "Descrição", "ID_Transacao", "Banco", "Descrição_Visual", "Tipo", "Status", "Data_DT"])
            
            if st.button("🚀 EFETIVAR NO HISTÓRICO", type="primary"):
                to_save = df_edited[df_edited['Contabilizar'] == True].copy()
                if not to_save.empty:
                    if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual', 'Data_DT'])
                    save_to_database(to_save, label_ref)
                    st.success("Dados salvos!")
                    st.rerun()
    else: st.info("Suba um arquivo OFX pela lateral para começar.")

with tab_mensal:
    if not df_hist.empty:
        df_v = df_hist[df_hist['Mes_Referencia'] == label_ref].copy()
        if not df_v.empty:
            c1, c2, c3 = st.columns(3)
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            c3.metric("Saldo", format_brl(ent - sai))

            col_esq, col_dir = st.columns(2)
            with col_esq:
                fig_pie = px.pie(df_v, values=df_v['Valor'].abs(), names='Categoria', hole=0.6, title="Categorias")
                fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_dir:
                fig_bar = px.bar(df_v, x='Categoria', y='Valor', color='Tipo', barmode='group', title="Crédito vs Débito",
                                 color_discrete_map={'🟢 Crédito': '#28a745', '🔴 Débito': '#dc3545'})
                st.plotly_chart(fig_bar, use_container_width=True)
        else: st.info("Nenhum registro para este mês.")

with tab_anual:
    if not df_hist.empty:
        df_ano = df_hist[df_hist['Data_DT'].dt.year == ano_ref].copy()
        if not df_ano.empty:
            # Gráfico de evolução mensal acumulada
            df_ano['Mes_Num'] = df_ano['Data_DT'].dt.month
            evol = df_ano.groupby(['Mes_Num', 'Mes_Referencia'])['Valor'].agg(In=lambda x: x[x>0].sum(), Out=lambda x: abs(x[x<0].sum()), Saldo='sum').reset_index().sort_values('Mes_Num')
            
            fig_anual = go.Figure()
            fig_anual.add_trace(go.Bar(x=evol['Mes_Referencia'], y=evol['In'], name='Entradas', marker_color='#28a745'))
            fig_anual.add_trace(go.Bar(x=evol['Mes_Referencia'], y=evol['Out'], name='Saídas', marker_color='#dc3545'))
            fig_anual.add_trace(go.Scatter(x=evol['Mes_Referencia'], y=evol['Saldo'], name='Resultado', line=dict(color='#2c3e50', width=4)))
            st.plotly_chart(fig_anual, use_container_width=True)
