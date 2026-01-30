import pandas as pd

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

def predict_data(df, df_hist=None):
    if df.empty: return df
    
    # Garante que IDs de transação sejam tratados como string para comparação
    ids_banco = []
    if df_hist is not None and not df_hist.empty:
        ids_banco = df_hist['ID_Transacao'].astype(str).unique()
    
    # Status de duplicado
    df['Status'] = df['ID_Transacao'].astype(str).apply(
        lambda x: "❌ JÁ SALVO" if x in ids_banco else "✅ NOVO"
    )
    
    df['Descrição_Visual'] = df.apply(
        lambda x: f"⚠️ {x['Descrição']}" if x['Status'] == "❌ JÁ SALVO" else x['Descrição'], axis=1
    )

    df['Contabilizar'] = False 
    df['Segmento'] = "PF"
    df['Tipo'] = df['Valor'].apply(lambda x: '🟢 Crédito' if x > 0 else '🔴 Débito')
    
    # Lógica de sugestão de categoria (pode ser expandida)
    def sugerir_categoria(row):
        desc = str(row['Descrição']).upper()
        if any(word in desc for word in ["TRANSFERENCIA", "TRANSF", "PIX ENVIADO", "PIX RECEBIDO"]):
            return "Transferência"
        if row['Valor'] > 0:
            return "Salário"
        return "Outros"

    df['Categoria'] = df.apply(sugerir_categoria, axis=1)
    
    return df
