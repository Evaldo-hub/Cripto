"""
🧪 Teste Telegram Notifier
Testa o sistema de notificações Telegram sem depender do dashboard
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from telegram_notifier import TelegramNotifier
import time

def test_telegram_notifier():
    """Testa o Telegram Notifier com diferentes tipos de mensagens"""
    
    print("🧪 TESTE TELEGRAM NOTIFIER")
    print("=" * 50)
    
    # Configurações (substitua com suas credenciais)
    token = input("🔑 Digite seu Token Telegram: ").strip()
    chat_id = input("💬 Digite seu Chat ID: ").strip()
    
    if not token or not chat_id:
        print("❌ Token e Chat ID são obrigatórios!")
        return
    
    # Criar notifier
    notifier = TelegramNotifier(token, chat_id)
    
    print("\n1️⃣ Testando conexão com API...")
    if notifier.test_connection():
        print("✅ Conexão bem-sucedida!")
    else:
        print("❌ Falha na conexão!")
        return
    
    print("\n2️⃣ Enviando mensagem de teste...")
    if notifier.send_test_message():
        print("✅ Mensagem de teste enviada!")
    else:
        print("❌ Erro ao enviar mensagem de teste!")
        return
    
    print("\n3️⃣ Enviando sinal de compra...")
    if notifier.send_buy_signal("BTC/USDT", 50000.0, 85, 22.5, "EMA 9 < EMA 21"):
        print("✅ Sinal de compra enviado!")
    else:
        print("❌ Erro ao enviar sinal de compra!")
    
    print("\n4️⃣ Enviando sinal de venda...")
    if notifier.send_sell_signal("ETH/USDT", 3000.0, 75, 68.5, "RSI > 70"):
        print("✅ Sinal de venda enviado!")
    else:
        print("❌ Erro ao enviar sinal de venda!")
    
    print("\n5️⃣ Enviando atualização da estratégia...")
    opportunities = [
        {'symbol': 'BTC/USDT', 'price': 50000.0, 'score_entrada': 85, 'rsi': 22.5, 'sinal_entrada': '🟢 COMPRA 1H+15m CONFIRMADA'},
        {'symbol': 'ETH/USDT', 'price': 3000.0, 'score_entrada': 72, 'rsi': 28.0, 'sinal_entrada': '🟢 COMPRA 1H+15m CONFIRMADA'},
        {'symbol': 'BNB/USDT', 'price': 400.0, 'score_entrada': 68, 'rsi': 32.0, 'sinal_entrada': 'AGUARDAR'}
    ]
    
    if notifier.send_strategy_update(10, 2, 0, opportunities):
        print("✅ Atualização da estratégia enviada!")
    else:
        print("❌ Erro ao enviar atualização!")
    
    print("\n6️⃣ Enviando alerta urgente...")
    urgent_details = {
        'price': 45000.0,
        'rsi': 78.5,
        'reason': 'RSI > 75 + Volume elevado'
    }
    
    if notifier.send_urgent_alert("BTC/USDT", "URGENT", urgent_details):
        print("✅ Alerta urgente enviado!")
    else:
        print("❌ Erro ao enviar alerta urgente!")
    
    print("\n🎉 TESTE CONCLUÍDO!")
    print("Verifique seu Telegram para todas as mensagens!")

if __name__ == "__main__":
    test_telegram_notifier()
