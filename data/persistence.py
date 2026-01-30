import pandas as pd
import os

DB_PATH = "data/meu_historico_financeiro.csv"

def load_database():
    if os.path.exists(DB_PATH):
        return pd.read_csv(DB_PATH)
    return pd.DataFrame()

def save_to_database(df_new, label_ref):
    df_new['Mes_Referencia'] = label_ref
    df_old = load_database()
    df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['ID_Transacao'], keep='last')
    
    # Garante que a pasta exista
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    df_final.to_csv(DB_PATH, index=False)

def delete_month_from_database(label_ref):
    df = load_database()
    if not df.empty:
        df = df[df['Mes_Referencia'] != label_ref]
        df.to_csv(DB_PATH, index=False)
