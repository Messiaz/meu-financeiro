import pandas as pd
from ofxparse import OfxParser
from data.logger import logger

def load_ofx_data(file):
    try:
        ofx = OfxParser.parse(file)
        account = ofx.account
        statement = account.statement
        transactions = statement.transactions

        data = []
        for tx in transactions:
            data.append({
                "Data": tx.date,
                "Valor": float(tx.amount),
                "Descrição": tx.memo,
                "ID_Transacao": tx.id,
                "Banco": account.institution.organization if account.institution else "Desconhecido"
            })
        
        df = pd.DataFrame(data)
        logger.info(f"OFX carregado com sucesso: {len(df)} transações encontradas.")
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar OFX: {e}")
        return pd.DataFrame()