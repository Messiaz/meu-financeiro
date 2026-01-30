import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def load_database(username="default"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # Tenta ler a aba específica do usuário
        df = conn.read(worksheet=username)
        return df
    except:
        # Se a aba não existir, retorna um DataFrame vazio com as colunas certas
        return pd.DataFrame(columns=['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Status', 'Mes_Referencia'])

def save_to_database(df_new, label_ref, username="default"):
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Carrega o que já existe
    df_old = load_database(username)
    
    # 2. Adiciona o novo e remove duplicatas
    df_new['Mes_Referencia'] = label_ref
    df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['ID_Transacao'], keep='first')
    
    # 3. Salva de volta na aba do usuário
    conn.update(worksheet=username, data=df_final)
    st.success(f"Dados salvos com sucesso na nuvem para {username}!")