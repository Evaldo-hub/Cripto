"""
📱 Telegram Notifier - Sistema de Notificações
Envia alertas de compra, venda e situações do dashboard via Telegram
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Sistema de notificações via Telegram"""
    
    def __init__(self, token: str = "", chat_id: str = ""):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_message_time = {}
        self.message_queue = []
        
    def test_connection(self) -> bool:
        """Testa conexão com a API do Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200 and response.json().get("ok", False)
        except Exception as e:
            logger.error(f"Erro ao testar conexão Telegram: {e}")
            return False
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Envia mensagem via Telegram"""
        try:
            if not self.token or not self.chat_id:
                logger.warning("Token ou Chat ID não configurados")
                return False
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200 and response.json().get("ok", False)
            
            if success:
                logger.info("✅ Mensagem enviada com sucesso")
            else:
                logger.error(f"❌ Erro ao enviar mensagem: {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem Telegram: {e}")
            return False
    
    def send_buy_signal(self, symbol: str, price: float, score: int, 
                       rsi: float, ema_status: str, timeframe: str = "1H") -> bool:
        """Envia sinal de compra"""
        
        message = f"""
🚀 **SINAL DE COMPRA DETECTADO**

📊 **Ativo:** {symbol}
💰 **Preço:** ${price:.6f}
📈 **Score:** {score}/100
📉 **RSI:** {rsi:.2f}
🔄 **EMA Status:** {ema_status}
⏰ **Timeframe:** {timeframe}

🔥 **Recomendação:** Considerar entrada long
📱 **Análise:** Estratégia 1H + 15m

⏰ Horário: {datetime.now().strftime('%H:%M:%S')}
        """
        
        return self.send_message(message)
    
    def send_sell_signal(self, symbol: str, price: float, score: int,
                        rsi: float, exit_reason: str, timeframe: str = "1H") -> bool:
        """Envia sinal de venda"""
        
        message = f"""
📉 **SINAL DE VENDA DETECTADO**

📊 **Ativo:** {symbol}
💰 **Preço:** ${price:.6f}
📈 **Score:** {score}/100
📉 **RSI:** {rsi:.2f}
🚪 **Motivo Saída:** {exit_reason}
⏰ **Timeframe:** {timeframe}

🔥 **Recomendação:** Considerar saída/short
📱 **Análise:** Estratégia 1H + 15m

⏰ Horário: {datetime.now().strftime('%H:%M:%S')}
        """
        
        return self.send_message(message)
    
    def send_strategy_update(self, total_analyzed: int, buy_signals: int, 
                           sell_signals: int, top_opportunities: List[Dict]) -> bool:
        """Envia atualização da estratégia"""
        
        message = f"""
📊 **ATUALIZAÇÃO ESTRATÉGIA 1H**

🔍 **Analisados:** {total_analyzed} ativos
📈 **Sinais Compra:** {buy_signals}
📉 **Sinais Venda:** {sell_signals}

🏆 **TOP OPORTUNIDADES:**
"""
        
        for i, opp in enumerate(top_opportunities[:3], 1):
            signal_emoji = "🚀" if "COMPRA" in opp.get('sinal_entrada', '') else "📉" if "VENDA" in opp.get('sinal_entrada', '') else "⏳"
            message += f"""
{i}. {signal_emoji} {opp.get('symbol', 'N/A')}
   💰 ${opp.get('price', 0):.6f}
   📈 Score: {opp.get('score_entrada', 0)}
   📉 RSI: {opp.get('rsi', 0):.2f}
   🔄 {opp.get('sinal_entrada', 'N/A')}
"""
        
        message += f"""
⏰ Horário: {datetime.now().strftime('%H:%M:%S')}
📱 Dashboard: Estratégia 1H Crypto Scanner Pro
        """
        
        return self.send_message(message)
    
    def send_error_alert(self, error_message: str, component: str = "Dashboard") -> bool:
        """Envia alerta de erro"""
        
        message = f"""
⚠️ **ALERTA DE ERRO**

🔧 **Componente:** {component}
❌ **Erro:** {error_message}

⏰ Horário: {datetime.now().strftime('%H:%M:%S')}
📱 Verificar logs para mais detalhes
        """
        
        return self.send_message(message)
    
    def send_test_message(self) -> bool:
        """Envia mensagem de teste"""
        
        message = f"""
🧪 **TESTE DE CONEXÃO - TELEGRAM NOTIFIER**

✅ **Bot Online e Funcional!**
📱 **Chat ID:** {self.chat_id}
🔧 **Componente:** Estratégia 1H Dashboard
⏰ **Teste:** {datetime.now().strftime('%H:%M:%S')}

🚀 Sistema pronto para receber alertas!
        """
        
        return self.send_message(message)
    
    def send_urgent_alert(self, symbol: str, alert_type: str, 
                         details: Dict) -> bool:
        """Envia alerta urgente"""
        
        urgency_emoji = "🚨" if alert_type == "URGENT" else "⚠️"
        
        message = f"""
{urgency_emoji} **ALERTA URGENTE - {alert_type}**

📊 **Ativo:** {symbol}
💰 **Preço:** ${details.get('price', 0):.6f}
📈 **RSI:** {details.get('rsi', 0):.2f}
📉 **Motivo:** {details.get('reason', 'N/A')}

🔥 **Ação Imediata Recomendada!**
📱 **Estratégia:** 1H + 15m

⏰ Horário: {datetime.now().strftime('%H:%M:%S')}
        """
        
        return self.send_message(message)

def create_telegram_notifier() -> TelegramNotifier:
    """Cria instância do Telegram notifier com configurações do session state"""
    import streamlit as st
    
    if 'telegram_notifier' not in st.session_state:
        token = st.session_state.get('telegram_token', '')
        chat_id = st.session_state.get('telegram_chat_id', '')
        st.session_state.telegram_notifier = TelegramNotifier(token, chat_id)
    
    return st.session_state.telegram_notifier
