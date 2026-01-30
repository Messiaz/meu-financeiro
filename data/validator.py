import pandas as pd
import re

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

def predict_data(df, df_hist, nome_usuario):
    if df.empty: return df
    
    # Identifica o que já existe para não duplicar
    ids_salvos = df_hist['ID_Transacao'].astype(str).unique() if not df_hist.empty else []
    
    df['Status'] = df['ID_Transacao'].astype(str).apply(lambda x: "❌ SALVO" if x in ids_salvos else "✅ NOVO")
    df['Contabilizar'] = df['Status'] == "✅ NOVO"
    # df['Tipo'] = df['Valor'].apply(lambda x: '🟢 Crédito' if x > 0 else '🔴 Débito')
    df['Tipo'] = df['Valor'].apply(lambda x: 'Débito')
    
    # Padrões iniciais
    df['Categoria'] = "Outros"
    df['Segmento'] = "PF"
    
    # Normalizamos o nome do usuário para busca
    nome_alvo = str(nome_usuario).lower()
    
    for i, row in df.iterrows():
        # A MÁGICA: Tudo para minúsculo para a comparação não falhar
        desc = str(row['Descrição']).lower()
        valor = row['Valor']

        # --- ORDEM DE PRIORIDADE DAS REGRAS ---

        # 1. INVESTIMENTOS (Busca por pedaços da palavra)
        keys_inv = ["tesouro", "cdi", "rdb", "invest", "aplic", "resgate", "lca", "lci"]
        if any(k in desc for k in keys_inv):
            df.at[i, 'Categoria'] = "Investimentos"
            df.at[i, 'Segmento'] = "PF"
            continue

        # 2. SALÁRIO
        keys_sal = ["salario", "recebimento", "folha", "prolabore", "vencimento"]
        if any(k in desc for k in keys_sal) and valor > 0:
            df.at[i, 'Categoria'] = "Salário"
            df.at[i, 'Segmento'] = "PF"
            continue

        # 3. TRANSFERÊNCIA INTERNA (Usa o nome do usuário)
        if nome_alvo in desc:
            df.at[i, 'Categoria'] = "Transferência"
            df.at[i, 'Segmento'] = "PF"
            continue

        # 4. FATURA
        if "fatura" in desc or "cartao" in desc or "nubank" in desc:
            # Evita marcar 'recebimento' de estorno como fatura
            if valor < 0:
                df.at[i, 'Categoria'] = "Fatura"
                df.at[i, 'Segmento'] = "PF"
                continue

        # 5. MEI (Impostos)
        if any(k in desc for k in ["das ", "mei", "simples"]):
            df.at[i, 'Categoria'] = "MEI"
            df.at[i, 'Segmento'] = "MEI"
            continue

        # 6. AULAS (Se for entrada e não caiu em nenhuma regra acima)
        if valor > 0 and any(k in desc for k in ["pix", "transf", "ted"]):
            df.at[i, 'Categoria'] = "Aulas Particulares - MEI"
            df.at[i, 'Segmento'] = "MEI"

    return df