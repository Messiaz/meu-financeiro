import pandas as pd
from ofxparse import OfxParser
import io

def load_ofx_data(file_obj):
    # Suporte para bytes do Streamlit uploader
    if isinstance(file_obj, (bytes, io.BytesIO)):
        ofx = OfxParser.parse(file_obj)
    else:
        ofx = OfxParser.parse(file_obj)
        
    transactions = []
    for account in ofx.accounts:
        for transaction in account.statement.transactions:
            transactions.append({
                'Data': transaction.date,
                'Descrição': transaction.memo,
                'Valor': float(transaction.amount),
                'ID_Transacao': transaction.id,
                'Banco': account.institution.organization if account.institution else "OFX"
            })
    return pd.DataFrame(transactions)
