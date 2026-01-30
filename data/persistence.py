import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def load_database(username="default"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(worksheet=username, ttl=0)
    except:
        # Colunas padrão que a planilha DEVE ter
        return pd.DataFrame(columns=['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia'])

def save_to_database(df_new, label_ref, username="default"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_old = load_database(username)
    
    # Define as colunas que queremos salvar
    colunas_esperadas = ['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia']
    
    # Garante que o df_new tenha a coluna de referência
    df_new['Mes_Referencia'] = label_ref
    
    # MÁGICA CONTRA O KEYERROR: 
    # Se alguma coluna esperada não estiver no df_new, cria ela como vazia
    for col in colunas_esperadas:
        if col not in df_new.columns:
            df_new[col] = ""

    # Agora filtramos apenas as colunas que a planilha aceita, sem risco de erro
    df_to_save = df_new[colunas_esperadas]
    
    # Une com o histórico e remove duplicatas
    df_final = pd.concat([df_old, df_to_save]).drop_duplicates(subset=['ID_Transacao'], keep='last')
    
    # Envia para o Google Sheets
    conn.update(worksheet=username, data=df_final)
    st.cache_data.clear()
    st.success(f"Dados sincronizados com sucesso para {username}!")