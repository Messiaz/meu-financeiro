import pandas as pd
import re

CAT_ENTRADAS = ["Salário", "Aulas Particulares - MEI", "Rendimento", "Transferência", "Outros"]
CAT_SAIDAS = ["Alimentação", "Lazer", "Investimento", "Saúde (Dedutível)", "Educação (Dedutível)", 
              "Livros", "Remédios","Fatura", "Doação", "Estudos", "Trabalho", "Transporte", "Manutenção", "MEI", "Impostos", "Transferência", "Outros"]

def predict_data(df, df_hist=None):
    if df.empty: return df
    
    ids_salvos = df_hist['ID_Transacao'].astype(str).unique() if df_hist is not None and not df_hist.empty else []
    
    df['Status'] = df['ID_Transacao'].astype(str).apply(lambda x: "❌ SALVO" if x in ids_salvos else "✅ NOVO")
    df['Contabilizar'] = df['Status'] == "✅ NOVO"
    # df['Tipo'] = df['Valor'].apply(lambda x: '🟢 Crédito' if x > 0 else '🔴 Débito')
    df['Tipo'] = df['Valor'].apply(lambda x: 'Débito')
    
    # Sugestões iniciais
    df['Categoria'] = "Outros"
    df['Segmento'] = "PF"
    
    # Nome para busca de transferência interna
    MEU_NOME = "GABRIEL MESSIAS MARQUES EIRAS"
    
    for i, row in df.iterrows():
        desc = str(row['Descrição']).upper()
        valor_abs = abs(row['Valor'])
        
        # 1. REGRA: TRANSFERÊNCIA INTERNA (Mesmo valor + Nome Gabriel + Mesma Data)
        # Busca na fila por um par com valor oposto no mesmo dia que também cite seu nome
        par_interno = df[
            (df['Data'] == row['Data']) & 
            (abs(df['Valor']) == valor_abs) & 
            (df['Valor'] == -row['Valor']) & 
            (df.index != i)
        ]
        
        # Se contiver seu nome e tiver um par de valor igual no dia
        if MEU_NOME in desc and not par_interno.empty:
            df.at[i, 'Categoria'] = "Transferência"
            df.at[i, 'Segmento'] = "PF"
            continue # Passa para a próxima transação

        # 2. REGRA: FATURA
        if "PAGAMENTO DE FATURA" in desc or "PGTO FATURA" in desc:
            df.at[i, 'Categoria'] = "Fatura"
            df.at[i, 'Segmento'] = "PF"
            continue

        # 3. REGRA: INVESTIMENTOS
        keywords_inv = ["TESOURO DIRETO", "CDI", "INVESTIMENTO", "RDB", "APLICAÇÃO", "RESGATE"]
        if any(key in desc for key in keywords_inv):
            df.at[i, 'Categoria'] = "Investimentos"
            df.at[i, 'Segmento'] = "PF"
            continue

        # 4. REGRA: AULAS/MEI (Sugerido para entradas PIX que não são transferências)
        if row['Valor'] > 0 and any(w in desc for w in ["PIX", "RECEBIDO"]):
            df.at[i, 'Categoria'] = "Aulas Particulares - MEI"
            df.at[i, 'Segmento'] = "MEI"

    return df