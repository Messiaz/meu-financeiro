import pandas as pd
from ofxparse import OfxParser
import io

def load_ofx_data(file_obj):
    # Se o arquivo vier como bytes (do uploader ou open rb)
    if isinstance(file_obj, bytes):
        file_obj = io.BytesIO(file_obj)
        
    ofx = OfxParser.parse(file_obj)
    transactions = []
    
    for account in ofx.accounts:
        for transaction in account.statement.transactions:
            transactions.append({
                'Data': transaction.date,
                'Descrição': transaction.memo,
                'Valor': float(transaction.amount),
                'ID_Transacao': transaction.id,
                'Banco': account.institution.organization if account.institution else "Desconhecido"
            })
    
    return pd.DataFrame(transactions)
