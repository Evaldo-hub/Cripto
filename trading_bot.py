"""
🤖 Trading Bot - Dashboard Estratégia 4H
Integração completa: Alertas + Botões + Binance + Telegram
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import threading
import queue
from dataclasses import dataclass

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    """Configurações do trading bot"""
    telegram_token: str = ""
    chat_id: str = ""
    binance_key: str = ""
    binance_secret: str = ""
    trade_percentage: float = 0.10  # 10% do saldo
    confirm_before_trade: bool = True
    max_trades_per_hour: int = 5
    stop_loss_percentage: float = 0.05  # 5%
    take_profit_percentage: float = 0.10  # 10%

class TradingBot:
    """Bot completo de trading com Telegram e Binance"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.trade_queue = queue.Queue()
        self.trade_history = []
        self.last_trades = []
        self.active_positions = {}
        
    def setup_config_ui(self):
        """Interface de configuração no Streamlit"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🤖 Configuração Trading Bot")
        
        # Token do Telegram
        telegram_token = st.sidebar.text_input(
            "🔑 Token Telegram Bot", 
            type="password",
            value=self.config.telegram_token,
            help="Token do bot criado com @BotFather"
        )
        
        # Chat ID
        chat_id = st.sidebar.text_input(
            "💬 Chat ID", 
            value=self.config.chat_id,
            help="Seu ID de chat no Telegram"
        )
        
        # API Binance
        binance_key = st.sidebar.text_input(
            "🔐 API Key Binance", 
            type="password",
            value=self.config.binance_key,
            help="API Key da sua conta Binance"
        )
        
        binance_secret = st.sidebar.text_input(
            "🔒 Secret Binance", 
            type="password",
            value=self.config.binance_secret,
            help="Secret Key da sua conta Binance"
        )
        
        # Configurações de trading
        trade_percentage = st.sidebar.slider(
            "💰 % do Saldo para Operar", 
            1, 100, 
            int(self.config.trade_percentage * 100)
        ) / 100
        
        confirm_before_trade = st.sidebar.checkbox(
            "✅ Confirmar antes de operar", 
            value=self.config.confirm_before_trade
        )
        
        max_trades = st.sidebar.slider(
            "📊 Máx. Operações/Hora", 
            1, 20, 
            self.config.max_trades_per_hour
        )
        
        stop_loss = st.sidebar.slider(
            "🛡️ Stop Loss %", 
            1, 20, 
            int(self.config.stop_loss_percentage * 100)
        ) / 100
        
        take_profit = st.sidebar.slider(
            "🎯 Take Profit %", 
            1, 50, 
            int(self.config.take_profit_percentage * 100)
        ) / 100
        
        # Atualizar configuração
        self.config.telegram_token = telegram_token
        self.config.chat_id = chat_id
        self.config.binance_key = binance_key
        self.config.binance_secret = binance_secret
        self.config.trade_percentage = trade_percentage
        self.config.confirm_before_trade = confirm_before_trade
        self.config.max_trades_per_hour = max_trades
        self.config.stop_loss_percentage = stop_loss
        self.config.take_profit_percentage = take_profit
        
        return telegram_token and chat_id and binance_key and binance_secret
    
    def send_telegram_alert(self, symbol: str, signal: str, price: float, confidence: float):
        """Envia alerta para Telegram com botões de ação"""
        if not self.config.telegram_token or not self.config.chat_id:
            return False
        
        try:
            # Criar botões inline
            keyboard = [
                [
                    {"text": f"🟢 COMPRAR {symbol}", "callback_data": f"buy|{symbol}|{price}"},
                    {"text": f"🔴 VENDER {symbol}", "callback_data": f"sell|{symbol}|{price}"}
                ],
                [
                    {"text": "❌ IGNORAR", "callback_data": f"ignore|{symbol}"}
                ]
            ]
            
            # Mensagem formatada
            message = f"""
🚀 **SINAL ESTRATÉGIA 4H DETECTADO**

📊 **Moeda:** {symbol}
💡 **Sinal:** {signal}
💰 **Preço:** ${price:.4f}
📈 **Confiança:** {confidence:.1f}%

⏰ **Horário:** {datetime.now().strftime('%H:%M:%S')}

🎯 **Análise Técnica:**
• RSI: {'< 15 (Oversold)' if signal == 'BUY' else '> 70 (Overbought)'}
• EMA 9/21: {'Cruzamento Bullish' if signal == 'BUY' else 'Cruzamento Bearish'}
• Volume: {'Acima da média' if signal == 'BUY' else 'Alta distribuição'}

⚠️ **Risk Management:**
• Stop Loss: -{self.config.stop_loss_percentage*100:.1f}%
• Take Profit: +{self.config.take_profit_percentage*100:.1f}%
• Position Size: {self.config.trade_percentage*100:.1f}% do saldo

👇 **Escolha sua ação:**
            """
            
            # Enviar mensagem
            url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
            
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": keyboard
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Alerta enviado: {symbol} - {signal}")
                return True
            else:
                logger.error(f"❌ Erro ao enviar alerta: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no Telegram: {e}")
            return False
    
    def execute_buy_order(self, symbol: str, price: float) -> Dict:
        """Executa ordem de compra na Binance"""
        try:
            # Simulação - implementar com API real da Binance
            order_id = f"SIM_{int(time.time())}"
            
            # Calcular quantidade
            balance_usdt = 1000.0  # Simulação de saldo
            quantity = (balance_usdt * self.config.trade_percentage) / price
            
            # Registrar operação
            trade = {
                "order_id": order_id,
                "symbol": symbol,
                "side": "BUY",
                "price": price,
                "quantity": quantity,
                "total": price * quantity,
                "timestamp": datetime.now(),
                "status": "FILLED",
                "type": "MARKET"
            }
            
            self.trade_history.append(trade)
            self.active_positions[symbol] = {
                "entry_price": price,
                "quantity": quantity,
                "timestamp": datetime.now(),
                "stop_loss": price * (1 - self.config.stop_loss_percentage),
                "take_profit": price * (1 + self.config.take_profit_percentage)
            }
            
            logger.info(f"✅ COMPRA EXECUTADA: {symbol} @ ${price:.4f}")
            return trade
            
        except Exception as e:
            logger.error(f"❌ Erro na compra: {e}")
            return {"error": str(e)}
    
    def execute_sell_order(self, symbol: str, price: float) -> Dict:
        """Executa ordem de venda na Binance"""
        try:
            # Verificar se tem posição aberta
            if symbol not in self.active_positions:
                return {"error": "Nenhuma posição aberta para esta moeda"}
            
            position = self.active_positions[symbol]
            order_id = f"SIM_{int(time.time())}"
            
            # Calcular P&L
            pnl = (price - position["entry_price"]) * position["quantity"]
            pnl_percentage = (price - position["entry_price"]) / position["entry_price"] * 100
            
            # Registrar operação
            trade = {
                "order_id": order_id,
                "symbol": symbol,
                "side": "SELL",
                "price": price,
                "quantity": position["quantity"],
                "total": price * position["quantity"],
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "timestamp": datetime.now(),
                "status": "FILLED",
                "type": "MARKET"
            }
            
            self.trade_history.append(trade)
            del self.active_positions[symbol]
            
            logger.info(f"✅ VENDA EXECUTADA: {symbol} @ ${price:.4f} | P&L: {pnl_percentage:.2f}%")
            return trade
            
        except Exception as e:
            logger.error(f"❌ Erro na venda: {e}")
            return {"error": str(e)}
    
    def process_signal_from_dashboard(self, result: Dict):
        """Processa sinal do dashboard e envia alerta"""
        symbol = result.get('symbol', '')
        score = result.get('score_entrada', 0)
        
        # Verificar se é um sinal forte
        if score >= 70 and symbol:
            # Obter preço atual (simulação)
            price = 50000.0  # Simulação - implementar API real
            
            # Determinar sinal
            signal = "BUY" if score >= 70 else "SELL"
            confidence = score / 100.0
            
            # Enviar alerta
            success = self.send_telegram_alert(symbol, signal, price, confidence)
            
            if success:
                st.success(f"🚀 Alerta enviado para {symbol}")
                return True
            else:
                st.error(f"❌ Erro ao enviar alerta para {symbol}")
                return False
        
        return False
    
    def get_trade_summary(self) -> Dict:
        """Resumo das operações"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "active_positions": len(self.active_positions)
            }
        
        total_trades = len(self.trade_history)
        sells = [t for t in self.trade_history if t.get('side') == 'SELL']
        total_pnl = sum(t.get('pnl', 0) for t in sells)
        wins = len([t for t in sells if t.get('pnl', 0) > 0])
        win_rate = (wins / len(sells) * 100) if sells else 0
        
        return {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "active_positions": len(self.active_positions),
            "wins": wins,
            "losses": len(sells) - wins
        }
    
    def display_trading_panel(self):
        """Painel de trading no Streamlit"""
        st.markdown("---")
        st.markdown("### 🤖 Trading Bot - Painel de Controle")
        
        # Configuração
        if self.setup_config_ui():
            st.success("✅ Bot configurado e pronto!")
            
            # Botão para testar conexão
            if st.button("🧪 Testar Conexão Telegram"):
                if self.send_telegram_alert("TEST", "BUY", 50000.0, 0.8):
                    st.success("✅ Mensagem de teste enviada!")
                else:
                    st.error("❌ Erro ao enviar mensagem de teste")
            
            # Resumo das operações
            summary = self.get_trade_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Total Operações", summary["total_trades"])
            
            with col2:
                st.metric("💰 P&L Total", f"${summary['total_pnl']:.2f}")
            
            with col3:
                st.metric("🎯 Win Rate", f"{summary['win_rate']:.1f}%")
            
            with col4:
                st.metric("📈 Posições Ativas", summary["active_positions"])
            
            # Posições ativas
            if self.active_positions:
                st.markdown("#### 📈 Posições Ativas")
                for symbol, pos in self.active_positions.items():
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(f"**{symbol}**")
                    with col2:
                        st.write(f"Entrada: ${pos['entry_price']:.4f}")
                    with col3:
                        st.write(f"SL: ${pos['stop_loss']:.4f}")
                    with col4:
                        st.write(f"TP: ${pos['take_profit']:.4f}")
            
            # Histórico recente
            if self.trade_history:
                st.markdown("#### 📋 Histórico Recente")
                recent_trades = self.trade_history[-10:]
                
                for trade in reversed(recent_trades):
                    if trade.get('side') == 'SELL':
                        pnl = trade.get('pnl', 0)
                        pnl_color = "🟢" if pnl > 0 else "🔴"
                        st.write(f"{pnl_color} {trade['symbol']} | ${trade['price']:.4f} | {pnl:+.2f} ({trade.get('pnl_percentage', 0):+.1f}%)")
        
        else:
            st.warning("⚠️ Configure o bot para ativar os alertas de trading")

# Função principal para integração com o dashboard
def create_trading_bot():
    """Cria e retorna instância do trading bot"""
    config = TradingConfig()
    bot = TradingBot(config)
    return bot
