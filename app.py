import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openfinance.loader import load_ofx_data
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database

# Configuração da Página
st.set_page_config(page_title="Financeiro 360 - Gabriel", layout="wide")

# Inicialização da Fila de Transações
if 'fila' not in st.session_state:
    st.session_state['fila'] = pd.DataFrame()

# --- SIDEBAR: PERFIL E UPLOAD ---
with st.sidebar:
    st.header("👤 Perfil do Usuário")
    user_name = st.text_input("Seu Nome Completo", value="Gabriel Messias Marques Eiras")
    st.info(f"Conectado como: **{user_name}**")
    
    st.divider()
    
    st.header("📤 Importar Extratos")
    arquivos = st.file_uploader("Selecione seus arquivos OFX", type="ofx", accept_multiple_files=True)
    if st.button("🚀 Adicionar à Fila", use_container_width=True):
        if arquivos:
            dfs = [load_ofx_data(a) for a in arquivos]
            # Concatena novos arquivos à fila e remove duplicatas por ID
            st.session_state['fila'] = pd.concat([st.session_state['fila']] + dfs).drop_duplicates(subset=['ID_Transacao'])
            st.success("Fila atualizada com sucesso!")
            st.rerun()

# Carregamento do Banco de Dados (Google Sheets)
df_hist = load_database(user_name)

# --- CORPO PRINCIPAL: ABAS ---
tab_conferir, tab_evolucao, tab_impostos = st.tabs(["📝 Conciliação Mensal", "📊 Evolução Mensal/Anual", "🏛️ Radar de Impostos"])

# --- ABA 1: CONFERÊNCIA E CATEGORIZAÇÃO ---
with tab_conferir:
    st.subheader("📝 Conferência de Lançamentos")
    
    c1, c2 = st.columns(2)
    mes_ref = c1.selectbox("Mês de Referência", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ano_ref = c2.selectbox("Ano de Referência", [2025, 2026])
    label_ref = f"{mes_ref}/{ano_ref}"
    meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}

    if not st.session_state['fila'].empty:
        df_f = st.session_state['fila'].copy()
        df_f['Data_DT'] = pd.to_datetime(df_f['Data'], errors='coerce')
        
        # Filtra apenas transações do mês selecionado que estão na fila
        df_mes = df_f[(df_f['Data_DT'].dt.month == meses_map[mes_ref]) & (df_f['Data_DT'].dt.year == ano_ref)].copy()

        if not df_mes.empty:
            # Aplica inteligência de predição (Passando os 3 argumentos corrigidos)
            df_input = predict_data(df_mes, df_hist, user_name)
            
            st.write(f"Você tem **{len(df_input)}** transações pendentes para **{label_ref}**.")
            
            # Editor de dados interativo
            df_edited = st.data_editor(
                df_input[['Contabilizar', 'Valor', 'Categoria', 'Segmento', 'Descrição', 'Data', 'ID_Transacao']],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Contabilizar": st.column_config.CheckboxColumn("Salvar?"),
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f", disabled=True),
                    "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                    "Segmento": st.column_config.SelectboxColumn("Segmento", options=["PF", "MEI"]),
                    "Descrição": st.column_config.TextColumn("Descrição", width="large", disabled=True),
                    "Data": st.column_config.TextColumn("Data", disabled=True),
                    "ID_Transacao": None # Oculta o ID
                }
            )
            
            if st.button(f"💾 SALVAR TRANSAÇÕES EM {label_ref.upper()}", type="primary", use_container_width=True):
                to_save = df_edited[df_edited['Contabilizar'] == True].copy()
                if not to_save.empty:
                    # Salva no Google Sheets
                    save_to_database(to_save, label_ref, user_name)
                    # Remove da fila apenas o que foi salvo
                    ids_salvos = to_save['ID_Transacao'].tolist()
                    st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_salvos)]
                    st.rerun()
        else:
            st.info(f"Nenhuma transação de {label_ref} encontrada na fila de upload.")
    else:
        st.info("A fila está vazia. Faça o upload de arquivos OFX na barra lateral.")

# --- ABA 2: EVOLUÇÃO MENSAL E ANUAL ---
with tab_evolucao:
    if not df_hist.empty:
        df_plot = df_hist.copy()
        df_plot['Data_DT'] = pd.to_datetime(df_plot['Data'], errors='coerce')
        df_plot['Ano'] = df_plot['Data_DT'].dt.year
        df_plot['Mes_Num'] = df_plot['Data_DT'].dt.month
        
        # Filtro de Ano para Evolução Mensal
        st.subheader("📈 Evolução Mensal")
        ano_alvo = st.selectbox("Escolha o ano para visualizar", df_plot['Ano'].unique(), index=0)
        df_ano = df_plot[df_plot['Ano'] == ano_alvo].copy()
        
        # Remove "Transferências" para não inflar o gráfico
        df_real = df_ano[df_ano['Categoria'] != "Transferência"].copy()
        
        res_mensal = df_real.groupby(['Mes_Referencia', 'Mes_Num']).agg({
            'Valor': lambda x: x[x > 0].sum(),
            'Valor_Neg': lambda x: abs(x[x < 0].sum())
        }).rename(columns={'Valor': 'Entradas', 'Valor_Neg': 'Saídas'}).reset_index().sort_values('Mes_Num')

        fig_evol = go.Figure()
        fig_evol.add_trace(go.Bar(x=res_mensal['Mes_Referencia'], y=res_mensal['Entradas'], name='Entradas', marker_color='#2ECC71'))
        fig_evol.add_trace(go.Bar(x=res_mensal['Mes_Referencia'], y=res_mensal['Saídas'], name='Saídas', marker_color='#E74C3C'))
        fig_evol.update_layout(barmode='group', title=f"Ganhos vs Gastos em {ano_alvo}")
        st.plotly_chart(fig_evol, use_container_width=True)
        
        st.divider()
        
        st.subheader("🗓️ Evolução Anual")
        res_anual = df_plot[df_plot['Categoria'] != "Transferência"].groupby('Ano').agg({
            'Valor': lambda x: x[x > 0].sum() - abs(x[x < 0].sum())
        }).reset_index()
        
        fig_anual = px.line(res_anual, x='Ano', y='Valor', title="Lucro Líquido por Ano", markers=True)
        st.plotly_chart(fig_anual, use_container_width=True)
    else:
        st.warning("Sem dados no histórico para gerar gráficos.")

# --- ABA 3: RADAR DE IMPOSTOS (MEI/PF) ---
with tab_impostos:
    if not df_hist.empty:
        st.subheader("🏛️ Controle Fiscal")
        
        # Seleção de ano para o imposto
        ano_fiscal = st.selectbox("Ano Fiscal", df_hist['Ano'].unique() if 'Ano' in df_hist.columns else [2025])
        df_fiscal = df_hist[pd.to_datetime(df_hist['Data']).dt.year == ano_fiscal]
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 💼 Limite MEI")
            # Faturamento MEI: Entradas marcadas como segmento MEI
            fat_mei = df_fiscal[(df_fiscal['Segmento'] == 'MEI') & (df_fiscal['Valor'] > 0)]['Valor'].sum()
            limite_mei = 81000
            st.metric("Faturamento MEI", f"R$ {fat_mei:,.2f}")
            st.progress(min(fat_mei/limite_mei, 1.0))
            st.caption(f"Você utilizou {fat_mei/limite_mei:.1%} do limite anual de R$ 81k.")
            
        with c2:
            st.markdown("#### 👤 Deduções IRPF")
            deducoes = df_fiscal[df_fiscal['Categoria'].str.contains('Dedutível', na=False)]['Valor'].abs().sum()
            investimentos = df_fiscal[df_fiscal['Categoria'] == 'Investimentos']['Valor'].abs().sum()
            
            st.metric("Saúde/Educação (Dedução)", f"R$ {deducoes:,.2f}")
            st.metric("Total em Investimentos", f"R$ {investimentos:,.2f}")
    else:
        st.warning("Adicione transações para ver o radar de impostos.")