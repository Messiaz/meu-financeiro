import pandas as pd
from ofxparse import OfxParser
import io

def load_ofx_data(file_obj):
    # Lê o conteúdo do arquivo (funciona para Streamlit ou Local)
    content = file_obj.read() if hasattr(file_obj, 'read') else file_obj
    ofx = OfxParser.parse(io.BytesIO(content) if isinstance(content, bytes) else content)
    
    transactions = []
    for account in ofx.accounts:
        for transaction in account.statement.transactions:
            transactions.append({
                'Data': transaction.date,
                'Descrição': transaction.memo,
                'Valor': float(transaction.amount),
                'ID_Transacao': str(transaction.id),
                'Banco': account.institution.organization if account.institution else "OFX"
            })
    return pd.DataFrame(transactions)
