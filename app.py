import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import io
from datetime import datetime
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database, delete_month_from_database

st.set_page_config(page_title="Financeiro 360", layout="wide")

# Inicialização da Fila Temporária
if 'fila' not in st.session_state:
    st.session_state['fila'] = pd.DataFrame()

def format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.title("🏦 Central de Inteligência Financeira")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📤 Importar Extratos")
    arquivos = st.file_uploader("Arquivos OFX", type="ofx", accept_multiple_files=True)
    
    if st.button("📥 Adicionar à Fila", use_container_width=True):
        if arquivos:
            list_dfs = [load_ofx_data(arq) for arq in arquivos]
            df_novos = pd.concat(list_dfs, ignore_index=True)
            res_fila = pd.concat([st.session_state['fila'], df_novos], ignore_index=True)
            st.session_state['fila'] = res_fila.drop_duplicates(subset=['ID_Transacao'])
            st.success(f"Fila: {len(st.session_state['fila'])} itens.")
        else:
            st.warning("Selecione arquivos.")

    st.divider()
    mes_nome = st.selectbox("Mês Referência", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    
    if st.button("🧹 Limpar Fila Temporária", use_container_width=True):
        st.session_state['fila'] = pd.DataFrame()
        st.rerun()

    if st.button(f"🗑️ Deletar Tudo de {label_ref}", type="secondary"):
        delete_month_from_database(label_ref)
        st.warning(f"Dados de {label_ref} removidos.")
        st.rerun()

# Carregar histórico do CSV
df_hist = load_database()

# --- ABAS ---
tab_conferir, tab_evolucao, tab_impostos = st.tabs(["📝 Conferência & Lançamentos", "📈 Evolução Anual", "🏛️ Impostos"])

with tab_conferir:
    # 1. Resumo Imediato do Mês Selecionado
    if not df_hist.empty:
        df_resumo = df_hist[df_hist['Mes_Referencia'] == label_ref]
        ent_m = df_resumo[df_resumo['Valor'] > 0]['Valor'].sum()
        sai_m = abs(df_resumo[df_resumo['Valor'] < 0]['Valor'].sum())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Entradas (Mês)", format_brl(ent_m))
        c2.metric("Saídas (Mês)", format_brl(sai_m))
        c3.metric("Saldo Líquido", format_brl(ent_m - sai_m))
        st.divider()

    # 2. Tabela de Conferência
    if not st.session_state['fila'].empty:
        df_input = predict_data(st.session_state['fila'], df_hist)
        # Ordem: Valor, Checkbox, Categoria, Segmento, Tipo...
        cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Segmento', 'Tipo', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        df_view = df_input[cols_ordem]

        st.subheader("📋 Transações na Fila")
        df_edited = st.data_editor(
            df_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Contabilizar": st.column_config.CheckboxColumn("✅"),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Segmento": st.column_config.SelectboxColumn("Segmento", options=["PF", "MEI"]),
                "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
            },
            disabled=['Valor', 'Tipo', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        )
        
        if st.button("🚀 SALVAR SELECIONADOS", type="primary"):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                ids_para_remover = to_save['ID_Transacao'].tolist()
                if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual'])
                save_to_database(to_save, label_ref)
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
                st.success("Dados contabilizados!")
                st.rerun()
    else:
        st.info("Suba um arquivo OFX para começar a conciliação.")

with tab_evolucao:
    if not df_hist.empty:
        st.subheader("📊 Evolução Mensal")
        
        # Preparação dos dados
        df_ev = df_hist.copy()
        df_ev['Entradas'] = df_ev['Valor'].apply(lambda x: x if x > 0 else 0)
        df_ev['Saidas'] = df_ev['Valor'].apply(lambda x: abs(x) if x < 0 else 0)
        
        # Ordenação Cronológica (Opcional, mas recomendado)
        ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        df_ev['Mes_Nome'] = df_ev['Mes_Referencia'].apply(lambda x: x.split('/')[0])
        df_ev['Mes_Sort'] = df_ev['Mes_Nome'].apply(lambda x: ordem_meses.index(x))
        
        evolucao_mensal = df_ev.groupby(['Mes_Sort', 'Mes_Referencia']).agg({'Entradas': 'sum', 'Saidas': 'sum'}).reset_index()
        evolucao_mensal['Saldo'] = evolucao_mensal['Entradas'] - evolucao_mensal['Saidas']

        # Gráfico Plotly
        fig = go.Figure()
        fig.add_trace(go.Bar(x=evolucao_mensal['Mes_Referencia'], y=evolucao_mensal['Entradas'], name='Entradas', marker_color='#2ECC71'))
        fig.add_trace(go.Bar(x=evolucao_mensal['Mes_Referencia'], y=evolucao_mensal['Saidas'], name='Saídas', marker_color='#E74C3C'))
        fig.add_trace(go.Scatter(x=evolucao_mensal['Mes_Referencia'], y=evolucao_mensal['Saldo'], name='Saldo', line=dict(color='#3498DB', width=4)))

        fig.update_layout(barmode='group', hovermode="x unified", title="Comparativo Entradas vs Saídas")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados históricos para exibir evolução.")

with tab_impostos:
    # (Mantém a lógica anterior de impostos enviada)
    st.write("Aba de Planejamento MEI e IRPF")