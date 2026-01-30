import pandas as pd

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

# import pandas as pd

# CAT_ENTRADAS = ["Salário", "Venda MEI", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
# CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
#               "Livros", "Remédios", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

def predict_data(df, df_hist=None):
    if df.empty: return df
    ids_banco = df_hist['ID_Transacao'].astype(str).unique() if df_hist is not None and not df_hist.empty else []
    
    df['Status'] = df['ID_Transacao'].astype(str).apply(lambda x: "❌ JÁ SALVO" if x in ids_banco else "✅ NOVO")
    df['Descrição_Visual'] = df.apply(lambda x: f"⚠️ {x['Descrição']}" if x['Status'] == "❌ JÁ SALVO" else x['Descrição'], axis=1)
    df['Contabilizar'] = False 
    
    def sugerir(row):
        desc = str(row['Descrição']).upper()
        if any(w in desc for w in ["PIX", "TRANSF", "TED", "DOC"]): return "Transferência"
        if row['Valor'] > 0: return "Aulas Particulares - MEI"
        return "Outros"
        
    df['Categoria'] = df.apply(sugerir, axis=1)
    return df
