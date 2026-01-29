import pandas as pd
import os

DB_PATH = 'data/meu_historico_financeiro.csv'
MAP_PATH = 'data/category_map.csv'

def save_to_database(df_new, month_ref):
    df_new['Mes_Referencia'] = month_ref
    
    if not os.path.exists(DB_PATH):
        df_new.to_csv(DB_PATH, index=False)
    else:
        df_old = pd.read_csv(DB_PATH)
        
        # REMOVE TUDO O QUE JÁ EXISTE PARA O MÊS QUE VOCÊ ESTÁ SUBINDO
        # Isso garante que se você clicar 10x, ele apaga a versão anterior e coloca a nova
        df_base_limpa = df_old[df_old['Mes_Referencia'] != month_ref]
        
        # Junta os meses antigos com os dados novos que você acabou de validar
        df_final = pd.concat([df_base_limpa, df_new], ignore_index=True)
        df_final.to_csv(DB_PATH, index=False)

    # Lógica de Aprendizado (Category Map) continua igual
    mapping_cols = ['Descrição', 'Segmento', 'Categoria', 'Tipo']
    new_map = df_new[mapping_cols].drop_duplicates()
    if os.path.exists(MAP_PATH) and os.path.getsize(MAP_PATH) > 0:
        old_map = pd.read_csv(MAP_PATH)
        updated_map = pd.concat([old_map, new_map]).drop_duplicates(subset=['Descrição'], keep='last')
        updated_map.to_csv(MAP_PATH, index=False)
    else:
        new_map.to_csv(MAP_PATH, index=False)
        
def load_database():
    if os.path.exists(DB_PATH):
        return pd.read_csv(DB_PATH)
    return pd.DataFrame()