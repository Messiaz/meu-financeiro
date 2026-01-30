import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def load_database(username="default"):
    # Limpa o nome para evitar erro de aba no Sheets
    safe_user = "".join(x for x in username if x.isalnum()) or "Geral"
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # ttl=0 força o app a buscar o dado novo, ignorando o cache
        df = conn.read(worksheet=safe_user, ttl=0)
        return df
    except Exception:
        # Se a aba não existir, retorna a estrutura correta
        return pd.DataFrame(columns=['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia'])

def save_to_database(df_new, label_ref, username="default"):
    safe_user = "".join(x for x in username if x.isalnum()) or "Geral"
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Busca o histórico atual
    df_old = load_database(safe_user)
    
    # 2. Prepara os novos dados
    df_new['Mes_Referencia'] = label_ref
    colunas = ['ID_Transacao', 'Data', 'Descrição', 'Valor', 'Categoria', 'Tipo', 'Segmento', 'Mes_Referencia']
    
    # Garante que as colunas existam
    for col in colunas:
        if col not in df_new.columns:
            df_new[col] = ""
            
    # 3. Une e remove duplicatas (mantendo o que foi editado por último)
    df_final = pd.concat([df_old[colunas], df_new[colunas]]).drop_duplicates(subset=['ID_Transacao'], keep='last')
    
    # 4. O segredo para não dar erro de permissão:
    # No Streamlit Cloud, você usará a URL da planilha que permite edição
    conn.update(worksheet=safe_user, data=df_final)
    
    st.cache_data.clear() # Limpa o cache global para atualizar os gráficos
    st.success(f"📌 Dados salvos na aba '{safe_user}' do Google Sheets!")