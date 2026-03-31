"""
🧪 TESTE SIMPLES TELEGRAM
Sem problemas de encoding
"""

import requests
import sys

def test_telegram_bot(token, chat_id):
    """Testa bot Telegram de forma simples"""
    
    print("TESTE TELEGRAM BOT - Estrategia 4H")
    print("=" * 50)
    
    # Teste 1: Conexão com API
    print("\n1. Testando conexao com API...")
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_name = data['result']['username']
                print(f"   OK! Bot conectado: @{bot_name}")
            else:
                print(f"   ERRO: {data}")
                return False
        else:
            print(f"   ERRO HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERRO: {e}")
        return False
    
    # Teste 2: Envio de mensagem
    print("\n2. Enviando mensagem de teste...")
    try:
        message = f"""
TESTE BOT ESTRATEGIA 4H

Conexao: OK
Chat ID: {chat_id}
Hora: {requests.get('https://api.telegram.org/bot' + token + '/getMe').json()['result']['username']}

Seu bot esta funcionando!
        """
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"   OK! Mensagem enviada com sucesso!")
                print(f"   ID da mensagem: {result['result']['message_id']}")
            else:
                print(f"   ERRO: {result}")
                return False
        else:
            print(f"   ERRO HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERRO: {e}")
        return False
    
    # Teste 3: Botões
    print("\n3. Enviando mensagem com botoes...")
    try:
        message = """
TESTE DE BOTOES

Moeda: BTC/USDT
Sinal: BUY
Preco: $50,000

Escolha acao:
        """
        
        keyboard = [
            [
                {"text": "COMPRAR", "callback_data": "buy|BTCUSDT"},
                {"text": "VENDER", "callback_data": "sell|BTCUSDT"}
            ],
            [
                {"text": "IGNORAR", "callback_data": "ignore|BTCUSDT"}
            ]
        ]
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "reply_markup": {
                "inline_keyboard": keyboard
            }
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"   OK! Mensagem com botoes enviada!")
                print(f"   ID da mensagem: {result['result']['message_id']}")
            else:
                print(f"   ERRO: {result}")
                return False
        else:
            print(f"   ERRO HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ERRO: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("TODOS OS TESTES PASSARAM!")
    print("Seu bot Telegram esta 100% funcional!")
    return True

def main():
    """Funcao principal"""
    print("Digite suas credenciais:")
    token = input("Token Telegram: ").strip()
    chat_id = input("Chat ID: ").strip()
    
    if not token or not chat_id:
        print("Token e Chat ID sao obrigatorios!")
        return
    
    success = test_telegram_bot(token, chat_id)
    
    if success:
        print("\nPARABENS! Bot pronto para usar!")
    else:
        print("\nERRO: Verifique suas credenciais!")

if __name__ == "__main__":
    main()
