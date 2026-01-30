import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database, delete_month_from_database

st.set_page_config(page_title="Financeiro 360", layout="wide")

if 'fila' not in st.session_state:
    st.session_state['fila'] = pd.DataFrame()

def format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("🏦 Dashboard Financeiro & Tributário")

# --- SIDEBAR LIMPA ---
with st.sidebar:
    st.header("📤 Importação")
    arquivos = st.file_uploader("Arquivos OFX", type="ofx", accept_multiple_files=True)
    if st.button("📥 Adicionar à Fila", use_container_width=True):
        if arquivos:
            list_dfs = [load_ofx_data(arq) for arq in arquivos]
            st.session_state['fila'] = pd.concat([st.session_state['fila']] + list_dfs, ignore_index=True).drop_duplicates(subset=['ID_Transacao'])
            st.success("Fila atualizada!")

    st.divider()
    st.header("⚙️ Gestão de Dados")
    if st.button("🧹 Limpar Fila Temporária", use_container_width=True):
        st.session_state['fila'] = pd.DataFrame()
        st.rerun()
    
    # Botão de deletar histórico movido para uma área de perigo
    with st.expander("⚠️ Área de Perigo"):
        mes_del = st.selectbox("Mês para deletar", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
        ano_del = st.selectbox("Ano para deletar", [2025, 2026])
        if st.button(f"Deletar {mes_del}/{ano_del}"):
            delete_month_from_database(f"{mes_del}/{ano_del}")
            st.rerun()

df_hist = load_database()

# --- ABAS ---
tab_conferir, tab_evolucao, tab_impostos = st.tabs(["📝 Conciliar Transações", "📈 Evolução & Metas", "🏛️ Imposto de Renda"])

# --- ABA 1: CONCILIAR (O seletor de mês fica aqui) ---
with tab_conferir:
    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1:
        mes_ref = st.selectbox("Mês de Destino", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    with col_sel2:
        ano_ref = st.selectbox("Ano de Destino", [2025, 2026])
    
    label_ref = f"{mes_ref}/{ano_ref}"

    if not st.session_state['fila'].empty:
        df_input = predict_data(st.session_state['fila'], df_hist)
        cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Segmento', 'Tipo', 'Descrição_Visual', 'Data', 'Banco', 'ID_Transacao']
        
        df_edited = st.data_editor(
            df_input[cols_ordem],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Contabilizar": st.column_config.CheckboxColumn("✅"),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Segmento": st.column_config.SelectboxColumn("Segmento", options=["PF", "MEI"]),
            },
            disabled=['Valor', 'Tipo', 'Descrição_Visual', 'Data', 'Banco', 'ID_Transacao']
        )
        
        if st.button("🚀 CONTABILIZAR EM " + label_ref.upper(), type="primary"):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                ids_para_remover = to_save['ID_Transacao'].tolist()
                if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual'])
                save_to_database(to_save, label_ref)
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
                st.rerun()
    else:
        st.info("Suba arquivos OFX para processar transações.")

# --- ABA 2: EVOLUÇÃO (Focada nos seus limites de 5k/60k) ---
with tab_evolucao:
    if not df_hist.empty:
        # Cálculos de Renda (Entradas PF + MEI)
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], errors='coerce')
        ano_atual = datetime.now().year
        df_ano = df_hist[df_hist['Data_DT'].dt.year == ano_atual]
        
        renda_anual = df_ano[df_ano['Valor'] > 0]['Valor'].sum()
        
        st.subheader(f"📊 Monitoramento de Renda {ano_atual}")
        
        # Termômetro Anual (Limite 60k)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            perc_anual = min(renda_anual / 60000, 1.0)
            cor_barra = "green" if perc_anual < 0.8 else "orange" if perc_anual < 0.95 else "red"
            st.write(f"**Limite Anual (Isenção/MEI):** {format_brl(renda_anual)} de R$ 60.000,00")
            st.progress(perc_anual)
        with col_t2:
            st.metric("Disponível no Ano", format_brl(60000 - renda_anual))

        st.divider()

        # Gráfico de Barras Mensais
        ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        df_ev = df_hist.copy()
        df_ev['Mes_Nome'] = df_ev['Mes_Referencia'].apply(lambda x: x.split('/')[0])
        df_ev['Entradas'] = df_ev['Valor'].apply(lambda x: x if x > 0 else 0)
        df_ev['Saidas'] = df_ev['Valor'].apply(lambda x: abs(x) if x < 0 else 0)
        
        evolucao = df_ev.groupby('Mes_Referencia').agg({'Entradas':'sum', 'Saidas':'sum'}).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=evolucao['Mes_Referencia'], y=evolucao['Entradas'], name='Entradas', marker_color='#2ECC71'))
        fig.add_trace(go.Bar(x=evolucao['Mes_Referencia'], y=evolucao['Saidas'], name='Saídas', marker_color='#E74C3C'))
        
        # Linha de Meta (5k mensal)
        fig.add_shape(type="line", x0=-0.5, x1=len(evolucao)-0.5, y0=5000, y1=5000, 
                      line=dict(color="Yellow", width=2, dash="dash"))
        
        fig.update_layout(title="Entradas vs Saídas Mensais (Linha Amarela = Alerta 5k/mês)", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando dados históricos para gerar evolução.")