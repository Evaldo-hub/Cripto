"""
Script de teste para verificar o problema do logger
"""

import logging

# Configuração do Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Testando logger...")
logger.info("Logger funcionando!")

# Teste de import
try:
    import streamlit as st
    print("Streamlit importado com sucesso")
    
    # Teste do telegram_notifier
    import sys
    import os
    
    # Adiciona src ao path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Importa o Telegram Notifier
    try:
        from telegram_notifier import create_telegram_notifier
        logger.info("✅ Telegram Notifier importado com sucesso")
        print("Telegram Notifier importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar Telegram Notifier: {e}")
        print(f"Erro ao importar Telegram Notifier: {e}")
    
    print("Todos os imports funcionaram!")
    
except Exception as e:
    print(f"Erro geral: {e}")
    import traceback
    traceback.print_exc()
