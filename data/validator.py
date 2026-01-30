import pandas as pd
import re

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

    
def predict_data(df, df_hist, nome_usuario):
    if df.empty: return df
    
    # Garantia de colunas básicas
    ids_salvos = df_hist['ID_Transacao'].astype(str).unique() if (df_hist is not None and not df_hist.empty) else []
    
    df['Status'] = df['ID_Transacao'].astype(str).apply(lambda x: "❌ SALVO" if x in ids_salvos else "✅ NOVO")
    df['Contabilizar'] = df['Status'] == "✅ NOVO"
    # df['Tipo'] = df['Valor'].apply(lambda x: '🟢 Crédito' if x > 0 else '🔴 Débito')
    df['Tipo'] = df['Valor'].apply(lambda x: 'Débito')
    df['Categoria'] = "Outros"
    df['Segmento'] = "PF"
    
    nome_alvo = str(nome_usuario).lower()
    
    for i, row in df.iterrows():
        desc = str(row['Descrição']).lower()
        valor = row['Valor']

        # INVESTIMENTOS
        if any(k in desc for k in ["tesouro", "cdi", "rdb", "invest", "aplic", "resgate", "lca", "lci"]):
            df.at[i, 'Categoria'] = "Investimentos"
            continue

        # SALÁRIO
        if any(k in desc for k in ["salario", "recebimento", "folha", "prolabore"]) and valor > 0:
            df.at[i, 'Categoria'] = "Salário"
            continue

        # TRANSFERÊNCIA (Busca seu nome)
        if nome_alvo in desc:
            df.at[i, 'Categoria'] = "Transferência"
            continue

        # FATURA
        if any(k in desc for k in ["fatura", "cartao", "pagamento"]) and valor < 0:
            df.at[i, 'Categoria'] = "Fatura"
            continue

        # MEI / AULAS
        if any(k in desc for k in ["das ", "mei", "simples"]):
            df.at[i, 'Categoria'] = "MEI"
            df.at[i, 'Segmento'] = "MEI"
        elif valor > 0 and "pix" in desc:
            df.at[i, 'Categoria'] = "Aulas Particulares - MEI"
            df.at[i, 'Segmento'] = "MEI"

    return df