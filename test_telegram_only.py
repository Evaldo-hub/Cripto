"""
🧪 TESTE TELEGRAM APENAS
Valida configuração do bot sem necessidade da Binance
"""

import requests
import time
from datetime import datetime

class TelegramTestBot:
    """Bot de teste apenas para Telegram"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def test_connection(self) -> bool:
        """Testa conexão básica com a API do Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_name = bot_info['result']['username']
                    print(f"✅ Conexão OK! Bot: @{bot_name}")
                    return True
                else:
                    print(f"❌ Erro na resposta: {bot_info}")
                    return False
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Envia mensagem de teste"""
        try:
            message = f"""
🧪 **TELEGRAM BOT - TESTE**

✅ **Conexão Testada com Sucesso!**

📊 **Informações:**
• Bot Token: ✅ Válido
• Chat ID: {self.chat_id}
• Hora: {datetime.now().strftime('%H:%M:%S')}
• Data: {datetime.now().strftime('%d/%m/%Y')}

🎯 **Próximos Passos:**
1. ✅ Configurar API Binance (quando desejar)
2. ✅ Ativar modo trading real
3. ✅ Receber alertas automáticos

🚀 **Seu bot está pronto para uso!**

---
*Teste executado via Dashboard Estratégia 4H*
            """
            
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    print(f"✅ Mensagem enviada! ID: {message_id}")
                    return True
                else:
                    print(f"❌ Erro no envio: {result}")
                    return False
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
            return False
    
    def send_test_buttons(self) -> bool:
        """Envia mensagem com botões de teste"""
        try:
            message = f"""
🚀 **TESTE DE BOTÕES**

📊 **Simulação de Sinal:**
• Moeda: BTC/USDT
• Sinal: BUY
• Preço: $50,000.00
• Confiança: 85%

👇 **Teste os botões abaixo:**
            """
            
            # Criar botões inline
            keyboard = [
                [
                    {"text": "🟢 SIM - COMPRAR", "callback_data": "test_buy|BTCUSDT"},
                    {"text": "🔴 NÃO - VENDER", "callback_data": "test_sell|BTCUSDT"}
                ],
                [
                    {"text": "❌ IGNORAR", "callback_data": "test_ignore|BTCUSDT"}
                ]
            ]
            
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": keyboard
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    print(f"✅ Mensagem com botões enviada! ID: {message_id}")
                    return True
                else:
                    print(f"❌ Erro no envio: {result}")
                    return False
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao enviar botões: {e}")
            return False
    
    def check_chat_access(self) -> bool:
        """Verifica se o bot pode enviar mensagens para o chat"""
        try:
            # Tenta enviar uma mensagem simples
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": f"🔍 Verificando acesso ao chat... {datetime.now().strftime('%H:%M:%S')}"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print(f"✅ Acesso ao chat {self.chat_id} confirmado!")
                    return True
                else:
                    error_desc = result.get('description', 'Erro desconhecido')
                    print(f"❌ Erro de acesso: {error_desc}")
                    return False
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao verificar acesso: {e}")
            return False
    
    def run_complete_test(self):
        """Executa teste completo do bot"""
        print("🧪 INICIANDO TESTE COMPLETO DO TELEGRAM BOT")
        print("=" * 60)
        
        # Teste 1: Conexão com API
        print("\n1️⃣ Testando conexão com API do Telegram...")
        if not self.test_connection():
            print("❌ FALHA: Não foi possível conectar à API do Telegram")
            return False
        
        # Teste 2: Acesso ao chat
        print("\n2️⃣ Verificando acesso ao chat...")
        if not self.check_chat_access():
            print("❌ FALHA: Bot não pode enviar mensagens para este chat")
            print("💡 Dica: Inicie uma conversa com seu bot e envie qualquer mensagem")
            return False
        
        # Teste 3: Envio de mensagem
        print("\n3️⃣ Enviando mensagem de teste...")
        if not self.send_test_message():
            print("❌ FALHA: Não foi possível enviar mensagem de teste")
            return False
        
        # Teste 4: Envio de botões
        print("\n4️⃣ Enviando mensagem com botões...")
        if not self.send_test_buttons():
            print("❌ FALHA: Não foi possível enviar botões")
            return False
        
        # Sucesso!
        print("\n" + "=" * 60)
        print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("\n✅ Seu bot Telegram está 100% funcional!")
        print("✅ Pronto para receber alertas da estratégia 4H!")
        print("✅ Botões interativos funcionando perfeitamente!")
        
        print("\n📋 Próximos passos:")
        print("1. Configure as APIs da Binance (quando desejar trading real)")
        print("2. Ative o modo trading no dashboard")
        print("3. Execute análises para receber alertas automáticos")
        
        return True

def main():
    """Função principal de teste"""
    print("🤖 TESTE TELEGRAM BOT - ESTRATÉGIA 4H")
    print("=" * 60)
    
    # Obter credenciais
    token = input("🔑 Digite seu Token do Bot Telegram: ").strip()
    chat_id = input("💬 Digite seu Chat ID: ").strip()
    
    if not token or not chat_id:
        print("❌ Token e Chat ID são obrigatórios!")
        return
    
    # Criar bot e executar teste
    bot = TelegramTestBot(token, chat_id)
    success = bot.run_complete_test()
    
    if success:
        print(f"\n🚀 Parabéns! Seu bot está pronto para usar!")
        print(f"📱 Acesse o Telegram e veja as mensagens de teste!")
    else:
        print(f"\n❌ Ocorreram erros durante o teste.")
        print(f"💡 Verifique:")
        print(f"   • Token está correto?")
        print(f"   • Chat ID está correto?")
        print(f"   • Você iniciou conversa com o bot?")
        print(f"   • Bot está ativo no Telegram?")

if __name__ == "__main__":
    main()
