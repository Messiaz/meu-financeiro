import streamlit as st
import pandas as pd
import io
from data.validator import predict_data, CAT_ENTRADAS, CAT_SAIDAS
from data.persistence import save_to_database, load_database

st.set_page_config(page_title="Financeiro 360", layout="wide")

if 'fila' not in st.session_state:
    st.session_state['fila'] = pd.DataFrame()

# --- SIDEBAR: APENAS UPLOAD ---
with st.sidebar:
    st.header("📤 Importar Extratos")
    arquivos = st.file_uploader("Arquivos OFX", type="ofx", accept_multiple_files=True)
    if st.button("📥 Colocar na Fila", use_container_width=True):
        from openfinance.loader import load_ofx_data
        if arquivos:
            dfs = [load_ofx_data(a) for a in arquivos]
            st.session_state['fila'] = pd.concat([st.session_state['fila']] + dfs).drop_duplicates(subset=['ID_Transacao'])
            st.success("Fila atualizada!")

df_hist = load_database()

# --- ABA DE CONFERÊNCIA ---
st.subheader("📝 Conferência Manual por Mês")

# Seletores de Mês e Ano (Filtram o que você vê na tabela)
c1, c2 = st.columns(2)
mes_ref = c1.selectbox("Ver transações de:", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
ano_ref = c2.selectbox("Ano:", [2025, 2026])
label_ref = f"{mes_ref}/{ano_ref}"
meses_map = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}

if not st.session_state['fila'].empty:
    df_f = st.session_state['fila'].copy()
    df_f['Data_DT'] = pd.to_datetime(df_f['Data'], errors='coerce')
    
    # FILTRO: Mostra apenas o mês que você quer trabalhar agora
    df_mes = df_f[(df_f['Data_DT'].dt.month == meses_map[mes_ref]) & (df_f['Data_DT'].dt.year == ano_ref)].copy()

    if not df_mes.empty:
        # Passa pelo validador para pegar as sugestões automáticas de Categoria/Segmento
        df_input = predict_data(df_mes, df_hist)
        
        st.write(f"Exibindo **{len(df_input)}** transações de **{label_ref}**")
        
        # TABELA PARA CATEGORIZAÇÃO MANUAL
        df_edited = st.data_editor(
            df_input[['Contabilizar', 'Valor', 'Categoria', 'Segmento', 'Tipo', 'Descrição', 'Data', 'ID_Transacao']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Contabilizar": st.column_config.CheckboxColumn("Salvar?"),
                "Valor": st.column_config.NumberColumn(format="R$ %.2f", disabled=True),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=CAT_ENTRADAS + CAT_SAIDAS),
                "Segmento": st.column_config.SelectboxColumn("PF/MEI", options=["PF", "MEI"]),
                "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "Descrição": st.column_config.TextColumn("Descrição", width="large", disabled=True),
                "Data": st.column_config.TextColumn("Data", disabled=True),
            }
        )
        
        if st.button(f"💾 SALVAR TRANSAÇÕES EM {label_ref.upper()}", type="primary", use_container_width=True):
            to_save = df_edited[df_edited['Contabilizar'] == True].copy()
            if not to_save.empty:
                save_to_database(to_save, label_ref)
                # Remove da fila apenas o que foi salvo
                ids_salvos = to_save['ID_Transacao'].tolist()
                st.session_state['fila'] = st.session_state['fila'][~st.session_state['fila']['ID_Transacao'].isin(ids_salvos)]
                st.success(f"{len(to_save)} transações salvas no histórico!")
                st.rerun()
    else:
        st.info(f"Nenhuma transação de {label_ref} encontrada nos arquivos enviados.")
else:
    st.info("A fila está vazia. Suba um OFX na lateral.")