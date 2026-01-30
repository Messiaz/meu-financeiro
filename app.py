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

st.title("🏦 Gestão Financeira Unificada")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📤 Carregar Extratos")
    arquivos = st.file_uploader("Selecione arquivos OFX", type="ofx", accept_multiple_files=True)
    
    if st.button("📥 Adicionar à Fila", use_container_width=True):
        if arquivos:
            list_dfs = []
            for arq in arquivos:
                df_arq = load_ofx_data(arq)
                list_dfs.append(df_arq)
            df_novos = pd.concat(list_dfs, ignore_index=True)
            res_fila = pd.concat([st.session_state['fila'], df_novos], ignore_index=True)
            st.session_state['fila'] = res_fila.drop_duplicates(subset=['ID_Transacao'])
            st.success(f"Fila: {len(st.session_state['fila'])} itens.")
        else:
            st.warning("Selecione arquivos.")

    st.divider()
    st.header("➕ Registro Manual")
    with st.expander("Dinheiro/Extras"):
        desc_man = st.text_input("Descrição")
        val_man = st.number_input("Valor ", step=0.01)
        cat_man = st.selectbox("Categoria", CAT_ENTRADAS + CAT_SAIDAS)
        data_man = st.date_input("Data ", datetime.now())
        if st.button("Salvar Manual"):
            novo_lanc = pd.DataFrame([{
                'Data': data_man.strftime('%Y-%m-%d'),
                'Descrição': desc_man,
                'Valor': val_man,
                'Categoria': cat_man,
                'ID_Transacao': f"MAN-{datetime.now().timestamp()}",
                'Banco': 'Manual',
                'Tipo': '🟢 Crédito' if val_man > 0 else '🔴 Débito',
                'Contabilizar': True
            }])
            save_to_database(novo_lanc, f"{data_man.strftime('%b')}/{data_man.year}")
            st.success("Salvo!")
            st.rerun()

    st.divider()
    mes_nome = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    
    if st.button("🧹 Limpar Fila"):
        st.session_state['fila'] = pd.DataFrame()
        st.rerun()

    if st.button(f"🗑️ Deletar Mês {label_ref}"):
        delete_month_from_database(label_ref)
        st.warning(f"Dados de {label_ref} removidos do histórico.")
        st.rerun()

# Carregar histórico do CSV
df_hist = load_database()

# --- ABAS ---
tab_conferir, tab_dash, tab_impostos = st.tabs(["📝 Conferência Unificada", "📈 Evolução", "🏛️ Impostos"])

# with tab_conferir:
#     if not st.session_state['fila'].empty:
#         df_input = predict_data(st.session_state['fila'], df_hist)
#         cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
#         df_view = df_input[cols_ordem]

#         st.subheader(f"Transações Pendentes")
#         df_edited = st.data_editor(
#             df_view,
#             hide_index=True,
#             use_container_width=True,
#             column_config={
#                 "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
#                 "Contabilizar": st.column_config.CheckboxColumn("✅"),
#                 "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
#                 "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
#             },
#             disabled=['Valor', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
#         )
        
#         if st.button("🚀 SALVAR SELECIONADOS NO HISTÓRICO", type="primary"):
#             to_save = df_edited[df_edited['Contabilizar'] == True].copy()
#             if not to_save.empty:
#                 ids_para_remover = to_save['ID_Transacao'].tolist()
#                 if 'Descrição_Visual' in to_save.columns:
#                     to_save = to_save.drop(columns=['Descrição_Visual'])
#                 save_to_database(to_save, label_ref)
#                 st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
#                 st.success("Itens salvos!")
#                 st.rerun()
with tab_conferir:
    if not st.session_state['fila'].empty:
        df_input = predict_data(st.session_state['fila'], df_hist)
        
        # NOVA ORDEM: Valor, Checkbox, Categoria, Segmento, Tipo...
        cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Segmento', 'Tipo', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        df_view = df_input[cols_ordem]

        st.subheader("📋 Conferência Unificada")
        df_edited = st.data_editor(
            df_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Contabilizar": st.column_config.CheckboxColumn("✅"),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Segmento": st.column_config.SelectboxColumn("Segmento", options=["PF", "MEI"]),
                "Tipo": st.column_config.TextColumn("Tipo"),
                "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
            },
            disabled=['Valor', 'Tipo', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        )
        
        if st.button("🚀 SALVAR SELECIONADOS NO HISTÓRICO", type="primary"):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                ids_para_remover = to_save['ID_Transacao'].tolist()
                # Removemos apenas a coluna visual, mantemos Segmento e Tipo para o CSV
                if 'Descrição_Visual' in to_save.columns:
                    to_save = to_save.drop(columns=['Descrição_Visual'])
                
                save_to_database(to_save, label_ref)
                
                # Atualiza a fila removendo o que foi salvo
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
                st.success(f"{len(to_save)} transações contabilizadas!")
                st.rerun()
    else:
        st.info("Fila vazia. Adicione OFX na lateral.")

with tab_dash:
    if not df_hist.empty:
        st.subheader(f"Resumo Financeiro - {label_ref}")
        df_v = df_hist[df_hist['Mes_Referencia'] == label_ref].copy()
        if not df_v.empty:
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            c3.metric("Saldo", format_brl(ent - sai))
            
            st.divider()
            fig = px.pie(df_v, values=df_v['Valor'].abs(), names='Categoria', hole=0.5, title="Distribuição por Categoria")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Nenhum dado salvo para {label_ref} ainda.")

with tab_impostos:
    if not df_hist.empty:
        st.header(f"🏛️ Planejamento de Impostos {ano_ref}")
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], errors='coerce')
        fat_mei = df_hist[(df_hist['Categoria'] == "Aulas Particulares - MEI") & (df_hist['Data_DT'].dt.year == ano_ref)]['Valor'].sum()
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Faturamento MEI", format_brl(fat_mei))
        col_m2.metric("Limite Restante", format_brl(81000 - fat_mei))
        st.progress(min(fat_mei/81000, 1.0), text=f"Uso do Limite MEI: {int((fat_mei/81000)*100)}%")
        
        st.divider()
        dedutivel = df_hist[df_hist['Categoria'].str.contains("Dedutível", na=False)]
        st.subheader("📊 Deduções IRPF Identificadas")
        st.metric("Total Dedutível", format_brl(abs(dedutivel['Valor'].sum())))
        st.dataframe(dedutivel[['Data', 'Descrição', 'Valor', 'Categoria']], hide_index=True)
