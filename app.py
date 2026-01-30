import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
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

# Carregar histórico
df_hist = load_database()

# --- ABAS ---
tab_conferir, tab_dash, tab_impostos = st.tabs(["📝 Conferência Unificada", "📈 Evolução", "🏛️ Impostos"])

with tab_conferir:
    if not st.session_state['fila'].empty:
        df_input = predict_data(st.session_state['fila'], df_hist)
        cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        df_view = df_input[cols_ordem]

        df_edited = st.data_editor(
            df_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Contabilizar": st.column_config.CheckboxColumn("✅"),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
            },
            disabled=['Valor', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        )
        
        if st.button("🚀 SALVAR SELECIONADOS", type="primary"):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                ids_para_remover = to_save['ID_Transacao'].tolist()
                if 'Descrição_Visual' in to_save.columns:
                    to_save = to_save.drop(columns=['Descrição_Visual'])
                save_to_database(to_save, label_ref)
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
                st.success("Itens salvos!")
                st.rerun()
    else:
        st.info("Fila vazia. Adicione OFX na lateral.")

         # (Dashboards e Impostos podem ser adicionados conforme os modelos anteriores)
        st.warning("Nenhum arquivo selecionado.")

    st.divider()
    mes_nome = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    
    if st.button("🧹 Limpar Fila Temporária", use_container_width=True):
        st.session_state['fila'] = pd.DataFrame()
        st.rerun()

# Carregar histórico salvo
df_hist = load_database()

# --- ABAS ---
tab_conferir, tab_dash, tab_impostos = st.tabs(["📝 Conferência Unificada", "📈 Evolução", "🏛️ Impostos"])

with tab_conferir:
    if not st.session_state['fila'].empty:
        # Validação (Sugerir categorias e checar duplicados no CSV)
        df_input = predict_data(st.session_state['fila'], df_hist)
        
        # Ordem: Valor, Checkbox, Categoria
        cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        df_view = df_input[cols_ordem]

        st.subheader(f"Fila de Conferência para {label_ref}")
        
        df_edited = st.data_editor(
            df_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Contabilizar": st.column_config.CheckboxColumn("✅"),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large"),
                "Status": st.column_config.TextColumn("Info")
            },
            disabled=['Valor', 'Descrição_Visual', 'Status', 'Data', 'Banco', 'ID_Transacao']
        )
        
        if st.button("🚀 SALVAR SELECIONADOS NO HISTÓRICO", type="primary"):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                # Limpa colunas visuais antes de salvar no CSV
                ids_para_remover = to_save['ID_Transacao'].tolist()
                to_save = to_save.drop(columns=['Descrição_Visual'])
                
                save_to_database(to_save, label_ref)
                
                # Remove da fila apenas o que foi salvo
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_para_remover)]
                
                st.success(f"{len(to_save)} itens salvos!")
                st.rerun()
    else:
        st.info("A fila está vazia. Adicione arquivos OFX pela barra lateral.")

with tab_dash:
    if not df_hist.empty:
        st.subheader(f"Dashboard - {label_ref}")
        df_v = df_hist[df_hist['Mes_Referencia'] == label_ref]
        if not df_v.empty:
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1, c2 = st.columns(2)
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            
            fig = px.pie(df_v, values=df_v['Valor'].abs(), names='Categoria', hole=0.5)
            st.plotly_chart(fig, use_container_width=True)

with tab_impostos:
    if not df_hist.empty:
        st.header("🏛️ Impostos e MEI")
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], errors='coerce')
        fat_mei = df_hist[(df_hist['Categoria'] == "Aulas Particulares - MEI") & (df_hist['Data_DT'].dt.year == ano_ref)]['Valor'].sum()
        st.metric("Faturamento MEI Acumulado", format_brl(fat_mei))
        st.progress(min(fat_mei/81000, 1.0), text=f"{int((fat_mei/81000)*100)}% do limite")
        save_to_database(novo_lanc, f"{data_man.strftime('%b')}/{data_man.year}")
        st.rerun()

    st.divider()
    mes_nome = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    
    if st.button(f"🗑️ Limpar {label_ref}"):
        delete_month_from_database(label_ref)
        st.rerun()

df_all = carregar_todos_extratos()
df_hist = load_database()

# --- ABAS ---
tab_concilia, tab_dash, tab_impostos = st.tabs(["📝 Conciliação", "📈 Dashboards", "🏛️ Impostos"])

with tab_concilia:
    if not df_all.empty:
        meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
        df_all['Data_DT'] = pd.to_datetime(df_all['Data'], format='mixed', errors='coerce')
        df_mes = df_all[(df_all['Data_DT'].dt.month == meses_map[mes_nome]) & (df_all['Data_DT'].dt.year == ano_ref)].copy()
        
        if not df_mes.empty:
            df_input = predict_data(df_mes, df_hist)
            # Reordenando: Valor, Checkbox, Categoria
            cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Descrição_Visual', 'Status', 'Data', 'Banco']
            df_input = df_input[cols_ordem]

            df_edited = st.data_editor(df_input, hide_index=True, use_container_width=True,
                column_config={
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Contabilizar": st.column_config.CheckboxColumn("✅"),
                    "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                    "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
                },
                disabled=['Valor', 'Descrição_Visual', 'Status', 'Data', 'Banco'])
            
            if st.button("🚀 CONTABILIZAR MARCADOS", type="primary"):
                to_save = df_edited[df_edited['Contabilizar'] == True].copy()
                if not to_save.empty:
                    if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual'])
                    save_to_database(to_save, label_ref)
                    st.success("Salvo com sucesso!")
                    st.rerun()
    else: st.info("Suba um arquivo OFX para começar.")

with tab_dash:
    if not df_hist.empty:
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], format='mixed')
        # Gráficos Evolução Mensal
        df_v = df_hist[df_hist['Mes_Referencia'] == label_ref].copy()
        if not df_v.empty:
            st.subheader(f"Resumo {label_ref}")
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            c3.metric("Saldo", format_brl(ent - sai))
            
            fig = px.bar(df_v, x="Categoria", y="Valor", color="Categoria", title="Gastos por Categoria")
            st.plotly_chart(fig, use_container_width=True)

with tab_impostos:
    st.header("🏛️ Planejamento Tributário")
    if not df_hist.empty:
        # Lógica MEI
        faturamento_mei = df_hist[(df_hist['Categoria'] == "Aulas Particulares - MEI")]['Valor'].sum()
        st.metric("Faturamento Acumulado MEI", format_brl(faturamento_mei))
        st.progress(min(faturamento_mei/81000, 1.0), text=f"{int((faturamento_mei/81000)*100)}% do limite anual")
        
        # Deduções
        dedutivel = df_hist[df_hist['Categoria'].str.contains("Dedutível", na=False)]
        st.write("### Deduções previstas (IRPF)")
        st.metric("Total Dedutível", format_brl(abs(dedutivel['Valor'].sum())))
        st.dataframe(dedutivel[['Data', 'Descrição', 'Valor', 'Categoria']], hide_index=True)
        delete_month_from_database(label_ref)
        st.rerun()

df_all = carregar_todos_extratos()
df_hist = load_database()

# --- ABAS ---
tab_concilia, tab_dash, tab_impostos = st.tabs(["📝 Conciliação", "📈 Dashboards", "🏛️ Impostos"])

with tab_concilia:
    if not df_all.empty:
        meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
        df_all['Data_DT'] = pd.to_datetime(df_all['Data'], format='mixed', errors='coerce')
        df_mes = df_all[(df_all['Data_DT'].dt.month == meses_map[mes_nome]) & (df_all['Data_DT'].dt.year == ano_ref)].copy()
        
        if not df_mes.empty:
            df_input = predict_data(df_mes, df_hist)
            # Reordenando: Valor, Checkbox, Categoria
            cols_ordem = ['Valor', 'Contabilizar', 'Categoria', 'Descrição_Visual', 'Status', 'Data', 'Banco']
            df_input = df_input[cols_ordem]

            df_edited = st.data_editor(df_input, hide_index=True, use_container_width=True,
                column_config={
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Contabilizar": st.column_config.CheckboxColumn("✅"),
                    "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                    "Descrição_Visual": st.column_config.TextColumn("Descrição", width="large")
                },
                disabled=['Valor', 'Descrição_Visual', 'Status', 'Data', 'Banco'])
            
            if st.button("🚀 CONTABILIZAR MARCADOS", type="primary"):
                to_save = df_edited[df_edited['Contabilizar'] == True].copy()
                if not to_save.empty:
                    if 'Descrição_Visual' in to_save.columns: to_save = to_save.drop(columns=['Descrição_Visual'])
                    save_to_database(to_save, label_ref)
                    st.success("Salvo com sucesso!")
                    st.rerun()
    else: st.info("Suba um arquivo OFX para começar.")

with tab_dash:
    if not df_hist.empty:
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], format='mixed')
        # Gráficos Evolução Mensal
        df_v = df_hist[df_hist['Mes_Referencia'] == label_ref].copy()
        if not df_v.empty:
            st.subheader(f"Resumo {label_ref}")
            ent = df_v[df_v['Valor'] > 0]['Valor'].sum()
            sai = abs(df_v[df_v['Valor'] < 0]['Valor'].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", format_brl(ent))
            c2.metric("Saídas", format_brl(sai))
            c3.metric("Saldo", format_brl(ent - sai))
            
            fig = px.bar(df_v, x="Categoria", y="Valor", color="Categoria", title="Gastos por Categoria")
            st.plotly_chart(fig, use_container_width=True)

with tab_impostos:
    st.header("🏛️ Planejamento Tributário")
    if not df_hist.empty:
        # Lógica MEI
        faturamento_mei = df_hist[(df_hist['Categoria'] == "Aulas Particulares - MEI")]['Valor'].sum()
        st.metric("Faturamento Acumulado MEI", format_brl(faturamento_mei))
        st.progress(min(faturamento_mei/81000, 1.0), text=f"{int((faturamento_mei/81000)*100)}% do limite anual")
        
        # Deduções
        dedutivel = df_hist[df_hist['Categoria'].str.contains("Dedutível", na=False)]
        st.write("### Deduções previstas (IRPF)")
        st.metric("Total Dedutível", format_brl(abs(dedutivel['Valor'].sum())))
        st.dataframe(dedutivel[['Data', 'Descrição', 'Valor', 'Categoria']], hide_index=True)
    uploaded_ofx = st.file_uploader("Novo OFX", type="ofx")
    if uploaded_ofx:
        with open(os.path.join(EXTRATOS_DIR, uploaded_ofx.name), "wb") as f:
            f.write(uploaded_ofx.getbuffer())
        st.success("Enviado!")
        st.cache_data.clear()

    st.divider()
    st.header("➕ Lançamento Manual")
    with st.expander("Registrar"):
        desc_man = st.text_input("Descrição")
        val_man = st.number_input("Valor", step=0.01)
        cat_man = st.selectbox("Categoria", CAT_ENTRADAS + CAT_SAIDAS)
        data_man = st.date_input("Data", datetime.now())
        if st.button("Salvar"):
            novo_lanc = pd.DataFrame([{
                'Data': data_man.strftime('%Y-%m-%d'), 'Descrição': desc_man,
                'Valor': val_man, 'Categoria': cat_man,
                'ID_Transacao': f"MAN-{datetime.now().timestamp()}",
                'Banco': 'Manual', 'Tipo': 'Débito',
                'Contabilizar': True, 'Segmento': 'PF'
            }])
            save_to_database(novo_lanc, f"{data_man.strftime('%b')}/{data_man.year}")
            st.rerun()

    st.divider()
    mes_nome = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = st.selectbox("Ano", [2025, 2026])
    label_ref = f"{mes_nome}/{ano_ref}"
    
    if st.button(f"🗑️ Limpar {label_ref}"):
        delete_month_from_database(label_ref)
        st.rerun()

df_all = carregar_todos_extratos()
df_hist = load_database()

# --- ABAS ---
tab_concilia, tab_mensal, tab_anual, tab_impostos = st.tabs(["📝 Conciliação", "📈 Mensal", "📊 Anual", "🏛️ Impostos"])

# --- ABA IMPOSTOS (NOVA) ---
with tab_impostos:
    st.header(f"Planejamento Tributário {ano_ref}")
    if not df_hist.empty:
        df_hist['Data_DT'] = pd.to_datetime(df_hist['Data'], format='mixed')
        df_ano = df_hist[df_hist['Data_DT'].dt.year == ano_ref].copy()

        # Cálculos MEI
        fat_pj = df_ano[df_ano['Categoria'] == "Aulas Particulares - MEI"]['Valor'].sum()
        limite_mei = 81000.00
        disp_mei = limite_mei - fat_pj

        # Cálculos PF (Deduções)
        deducoes = df_ano[df_ano['Categoria'].str.contains("Dedutível", na=False)]
        total_dedutivel = abs(deducoes['Valor'].sum())

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📌 Situação MEI")
            st.metric("Faturamento MEI", format_brl(fat_pj))
            st.progress(min(fat_pj/limite_mei, 1.0), text=f"{int((fat_pj/limite_mei)*100)}% do limite utilizado")
            if disp_mei < 10000:
                st.error(f"Atenção: Você tem apenas {format_brl(disp_mei)} de margem até o fim do ano!")
            else:
                st.success(f"Margem segura: {format_brl(disp_mei)} restantes.")

        with col2:
            st.subheader("📌 Pessoa Física (IRPF)")
            st.metric("Total de Deduções Identificadas", format_brl(total_dedutivel))
            if not deducoes.empty:
                st.write("Gastos que abatem imposto:")
                st.dataframe(deducoes[['Data', 'Descrição', 'Valor', 'Categoria']], hide_index=True)
            else:
                st.info("Nenhum gasto dedutível (Saúde/Educação) encontrado ainda.")

        st.divider()
        st.subheader("💡 Sugestões do Especialista")
        c_sug1, c_sug2 = st.columns(2)
        with c_sug1:
            st.info("**Para o seu MEI:**\n\n1. Guarde todos os comprovantes de despesas da empresa (internet, luz, materiais) para o cálculo do lucro isento.\n2. Se o faturamento ultrapassar R$ 81k, prepare-se para migrar para ME.")
        with c_sug2:
            st.info("**Para seu IRPF:**\n\n1. Continue categorizando gastos com Saúde e Educação como 'Dedutível'.\n2. Considere um PGBL (Previdência) se quiser abater até 12% da renda tributável.")
    else:
        st.warning("Sem dados históricos para calcular impostos.")

# --- OUTRAS ABAS (Resumidas para o código completo) ---
with tab_concilia:
    if not df_all.empty:
        meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
        
        # Converter para data garantindo que não dê erro
        df_all['Data_DT'] = pd.to_datetime(df_all['Data'], errors='coerce')
        
        # Filtra pelo mês e ano selecionados
        df_mes = df_all[
            (df_all['Data_DT'].dt.month == meses_map[mes_nome]) & 
            (df_all['Data_DT'].dt.year == ano_ref)
        ].copy()
        
        if df_mes.empty:
            st.warning(f"Nenhuma transação (incluindo transferências) encontrada para {label_ref}. Verifique a data no arquivo OFX.")
            # Opcional: mostrar as últimas 5 transações do arquivo para depuração
            st.write("Últimas transações lidas do arquivo:")
            st.write(df_all.tail(5))
        else:
            # Chama o validator que agora aceita transferências
            df_input = predict_data(df_mes, df_hist)
            
            # EXIBIÇÃO NA TABELA
            df_edited = st.data_editor(
                df_input,
                # ... (restante das configurações do data_editor permanecem iguais)
            )
with tab_mensal:
    if not df_hist.empty:
        # Gráficos de pizza e barras por categoria
        st.write("Visualização de gastos e entradas mensais.")







