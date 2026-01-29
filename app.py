import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database

st.set_page_config(page_title="Financeiro 360 - Evolução Prof", layout="wide")

EXTRATOS_DIR = "extratos"
if not os.path.exists(EXTRATOS_DIR): os.makedirs(EXTRATOS_DIR)

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

# --- SIDEBAR ---
with st.sidebar:
    st.header("📅 Navegação")
    mes_nome = st.selectbox("Selecione o Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    if st.button("🔄 Sincronizar Extratos"):
        st.cache_data.clear()
        st.rerun()

df_all = carregar_todos_extratos()
df_hist = load_database()

# --- CORREÇÃO DE DATA GLOBAL ---
if not df_hist.empty:
    # Usando format='mixed' para evitar o erro de 'unconverted data'
    df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], format='mixed', dayfirst=False)

# Abas
tab_concilia, tab_mensal, tab_anual = st.tabs(["📝 Conciliação", "📈 Evolução Mensal", "📊 Evolução Anual"])

# --- ABA 1: CONCILIAÇÃO ---
with tab_concilia:
    if not df_all.empty:
        meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
        df_all['Data_DT'] = pd.to_datetime(df_all['Data'], format='mixed')
        df_mes_ofx = df_all[(df_all['Data_DT'].dt.month == meses_map[mes_nome]) & (df_all['Data_DT'].dt.year == ano_ref)].copy()
        
        if df_mes_ofx.empty:
            st.warning(f"Sem arquivos para {label_ref} na pasta /extratos.")
        else:
            df_input = predict_data(df_mes_ofx, df_hist)
            st.subheader(f"Movimentações de {label_ref}")
            df_edited = st.data_editor(df_input, hide_index=True, use_container_width=True,
                column_config={"Status": st.column_config.TextColumn("Status"), "Contabilizar": st.column_config.CheckboxColumn("✅"),
                               "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                               "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large"),
                               "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS)},
                disabled=["Data", "Descrição", "ID_Transacao", "Banco", "Descrição_Visual", "Tipo", "Status", "Data_DT"])
            
            if st.button("🚀 SALVAR SELECIONADAS", type="primary"):
                to_save = df_edited[df_edited['Contabilizar'] == True].copy()
                if not to_save.empty:
                    if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual', 'Data_DT'])
                    save_to_database(to_save, label_ref)
                    st.success("Dados salvos no histórico!")
                    st.rerun()
    else: st.info("Adicione arquivos na pasta /extratos")

# --- ABA 2: EVOLUÇÃO MENSAL ---
with tab_mensal:
    if not df_hist.empty:
        df_v = df_hist[(df_hist['Mes_Referencia'] == label_ref)].copy()
        
        if not df_v.empty:
            st.subheader(f"Resumo de {label_ref}")
            c1, c2, c3 = st.columns(3)
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            c3.metric("Saldo", format_brl(ent - sai))

            col_esq, col_dir = st.columns(2)
            with col_esq:
                fig_pie = px.pie(df_v, values=df_v['Valor'].abs(), names='Categoria', hole=0.6, title="Distribuição de Gastos")
                fig_pie.update_traces(hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_dir:
                fig_bar = px.bar(df_v, x='Categoria', y='Valor', color='Tipo', title="Entradas vs Saídas", barmode='group',
                                 color_discrete_map={'🟢 Crédito': '#28a745', '🔴 Débito': '#dc3545'})
                st.plotly_chart(fig_bar, use_container_width=True)
        else: st.info(f"Nenhum dado salvo para {label_ref}.")

# --- ABA 3: EVOLUÇÃO ANUAL ---
with tab_anual:
    if not df_hist.empty:
        df_ano = df_hist[df_hist['Data_DT'].dt.year == ano_ref].copy()
        if not df_ano.empty:
            st.subheader(f"Evolução Anual - {ano_ref}")
            
            # Agrupar para o gráfico de tendência
            df_ano['Mes_Num'] = df_ano['Data_DT'].dt.month
            evol = df_ano.groupby(['Mes_Num', 'Mes_Referencia'])['Valor'].agg(
                Entradas=lambda x: x[x>0].sum(),
                Saídas=lambda x: abs(x[x<0].sum()),
                Saldo='sum'
            ).reset_index().sort_values('Mes_Num')

            fig_anual = go.Figure()
            fig_anual.add_trace(go.Bar(x=evol['Mes_Referencia'], y=evol['Entradas'], name='Entradas', marker_color='#28a745'))
            fig_anual.add_trace(go.Bar(x=evol['Mes_Referencia'], y=evol['Saídas'], name='Saídas', marker_color='#dc3545'))
            fig_anual.add_trace(go.Scatter(x=evol['Mes_Referencia'], y=evol['Saldo'], name='Saldo (Tendência)', line=dict(color='#2c3e50', width=4)))
            
            fig_anual.update_layout(barmode='group', title="Fluxo de Caixa Mensal")
            st.plotly_chart(fig_anual, use_container_width=True)
            
            st.write("### Tabela Consolidada")
            st.dataframe(evol[['Mes_Referencia', 'Entradas', 'Saídas', 'Saldo']].style.format({
                "Entradas": format_brl, "Saídas": format_brl, "Saldo": format_brl
            }), use_container_width=True)
    else: st.info("Histórico ainda está vazio.")