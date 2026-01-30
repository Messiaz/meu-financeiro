import pandas as pd

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

def predict_data(df, df_hist=None):
    if df.empty: return df
    
    ids_salvos = df_hist['ID_Transacao'].astype(str).unique() if df_hist is not None and not df_hist.empty else []
    
    # Status e Descrição Visual
    df['Status'] = df['ID_Transacao'].astype(str).apply(lambda x: "❌ JÁ SALVO" if x in ids_salvos else "✅ NOVO")
    df['Descrição_Visual'] = df.apply(lambda x: f"⚠️ {x['Descrição']}" if x['Status'] == "❌ JÁ SALVO" else x['Descrição'], axis=1)
    df['Contabilizar'] = df['Status'] == "✅ NOVO"
    
    # Lógica de Tipo (Crédito/Débito)
    # df['Tipo'] = df['Valor'].apply(lambda x: '🟢 Crédito' if x > 0 else '🔴 Débito')
    df['Tipo'] = df['Valor'].apply(lambda x: 'Débito')
    
    # Sugestão de Categoria e Segmento (PF/MEI)
    def classificar(row):
        desc = str(row['Descrição']).upper()
        valor = row['Valor']
        
        if any(w in desc for w in ["PIX", "TRANSF", "TED"]):
            return "Transferência", "PF"
        
        if valor > 0:
            return "Aulas Particulares - MEI", "MEI" # Sugestão padrão para entradas
        
        if any(w in desc for w in ["DAS ", "MEI", "SIMPLES"]):
            return "MEI", "MEI"
            
        return "Outros", "PF"
        
    # Aplica a classificação dupla
    classificacao = df.apply(classificar, axis=1)
    df['Categoria'] = [x[0] for x in classificacao]
    df['Segmento'] = [x[1] for x in classificacao]
    
    return df