import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def load_database(username="default"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # O argumento ttl=0 garante que ele pegue o dado MAIS RECENTE da planilha
        return conn.read(worksheet=username, ttl=0)
    except:
        return pd.DataFrame(columns=['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia'])

def save_to_database(df_new, label_ref, username="default"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_old = load_database(username)
    
    df_new['Mes_Referencia'] = label_ref
    # Colunas padrão para manter a planilha organizada
    colunas = ['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia']
    
    # Filtra apenas as colunas necessárias e une
    df_to_save = df_new[colunas]
    df_final = pd.concat([df_old[colunas], df_to_save]).drop_duplicates(subset=['ID_Transacao'], keep='first')
    
    conn.update(worksheet=username, data=df_final)
    st.cache_data.clear() # Limpa o cache para mostrar o dado novo na hora
    st.success(f"Nuvem atualizada para {username}!")