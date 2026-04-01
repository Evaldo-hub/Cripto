"""
Dashboard Estratégia 1h - Versão Otimizada
Estratégia personalizada com RSI < 25, candle de rejeição e suporte
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import logging
import requests

# Configuração do Logger (deve vir antes dos imports que o usam)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona src ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importa o Telegram Notifier
try:
    from telegram_notifier import create_telegram_notifier
    TELEGRAM_AVAILABLE = True
    logger.info("✅ Telegram Notifier importado com sucesso")
except ImportError as e:
    logger.error(f"❌ Erro ao importar Telegram Notifier: {e}")
    TELEGRAM_AVAILABLE = False
    
    def create_telegram_notifier():
        """Mock function when telegram_notifier is not available"""
        class MockNotifier:
            def test_connection(self): return False
            def send_message(self, msg): return False
            def send_buy_signal(self, *args, **kwargs): return False
            def send_sell_signal(self, *args, **kwargs): return False
            def send_strategy_update(self, *args, **kwargs): return False
            def send_test_message(self): return False
            def send_error_alert(self, *args, **kwargs): return False
            def send_urgent_alert(self, *args, **kwargs): return False
        return MockNotifier()

from parallel_collector import get_parallel_collector
from simple_quant_engine import get_simple_quant_engine, SimpleAnalysisResult
# from pdf_generator import generate_simple_pdf  # Temporarily disabled
from database_manager_simple import db_manager
import ta

# Importar gerenciador de configurações
try:
    from config_manager import config_manager
    CONFIG_MANAGER_AVAILABLE = True
    logger.info("✅ ConfigManager importado com sucesso")
except ImportError as e:
    logger.error(f"❌ Erro ao importar ConfigManager: {e}")
    CONFIG_MANAGER_AVAILABLE = False
    
    class MockConfigManager:
        def __init__(self):
            self.config = {}
        def get_telegram_config(self): return {"token": "", "chat_id": "", "enabled": False}
        def set_telegram_config(self, *args, **kwargs): return False
        def is_telegram_configured(self): return False
        def update_from_session_state(self, *args, **kwargs): return False
        def get_favorites(self): return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        def get_strategy_config(self): return {}
    
    config_manager = MockConfigManager()

# Importar gestor de posições
try:
    from position_manager import position_manager
    POSITION_MANAGER_AVAILABLE = True
    logger.info("✅ PositionManager importado com sucesso")
except ImportError as e:
    logger.error(f"❌ Erro ao importar PositionManager: {e}")
    POSITION_MANAGER_AVAILABLE = False
    
    class MockPositionManager:
        def __init__(self):
            pass
        def open_position(self, *args, **kwargs): return {}
        def close_position(self, *args, **kwargs): return None
        def update_position_price(self, *args, **kwargs): return False
        def check_sell_signals(self, *args, **kwargs): return False, "Mock", 0.0
        def get_open_positions(self): return {}
        def get_closed_positions(self): return {}
        def get_position_summary(self): return {}
    
    position_manager = MockPositionManager()

# Configuração da Página
st.set_page_config(
    page_title="Estratégia 1h - Crypto Scanner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Avançado
st.markdown("""
<style>
.estrategia-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 15px;
    color: white;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.entrada-ideal { 
    background: linear-gradient(45deg, #00c851, #00ff00);
    color: white; 
    font-weight: bold; 
    padding: 10px;
    border-radius: 8px;
}
.saida-ideal { 
    background: linear-gradient(45deg, #ff4444, #cc0000);
    color: white; 
    font-weight: bold; 
    padding: 10px;
    border-radius: 8px;
}
.saida-urgente {
    background: linear-gradient(45deg, #ff0000, #cc0000);
    color: white;
    font-weight: bold;
    padding: 8px;
    border-radius: 6px;
    text-align: center;
}
.saida-atencao {
    background: linear-gradient(45deg, #ffaa00, #ff8800);
    color: white;
    font-weight: bold;
    padding: 8px;
    border-radius: 6px;
    text-align: center;
}
.saida-manter {
    background: linear-gradient(45deg, #00ff00, #00cc00);
    color: white;
    font-weight: bold;
    padding: 8px;
    border-radius: 6px;
    text-align: center;
}
.signal-buy {
    background: linear-gradient(45deg, #00ff00, #00cc00);
    color: white;
    font-weight: bold;
    border: 2px solid #00aa00;
}
.signal-sell {
    background: linear-gradient(45deg, #ff4444, #cc0000);
    color: white;
    font-weight: bold;
    border: 2px solid #aa0000;
}
.signal-wait {
    background: linear-gradient(45deg, #ffaa00, #ff8800);
    color: white;
    font-weight: bold;
    border: 2px solid #cc6600;
}
.score-high { color: #00ff00; font-weight: bold; font-size: 1.2em; }
.score-medium { color: #ffaa00; font-weight: bold; }
.score-low { color: #ff4444; font-weight: bold; }
.heatmap-cell { text-align: center; font-weight: bold; }
</style>
""")

def get_saida_display(result):
    """Formata display do sinal de saída com nível"""
    if result.get('sinal_saida', False):
        nivel = result.get('nivel_saida', 'atencao')
        motivo = result.get('motivo_saida', 'Detectado')
        
        if nivel == 'urgente':
            return f"🔴 {motivo}"
        elif nivel == 'atencao':
            return f"🟡 {motivo}"
        else:
            return f"🟢 {motivo}"
    else:
        return "🟢 MANTER"

def get_saida_class(result):
    """Retorna classe CSS para sinal de saída"""
    if result.get('sinal_saida', False):
        nivel = result.get('nivel_saida', 'atencao')
        if nivel == 'urgente':
            return 'saida-urgente'
        elif nivel == 'atencao':
            return 'saida-atencao'
    return 'saida-manter'

def get_saida_emoji(result):
    """Retorna emoji para sinal de saída"""
    if result.get('sinal_saida', False):
        nivel = result.get('nivel_saida', 'atencao')
        if nivel == 'urgente':
            return "🔴"
        elif nivel == 'atencao':
            return "🟡"
    return "🟢"

# Session State - Carrega configurações salvas
if 'results' not in st.session_state:
    st.session_state.results = []
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None
if 'analysis_running' not in st.session_state:
    st.session_state.analysis_running = False

# Carrega configurações do Telegram salvas
if CONFIG_MANAGER_AVAILABLE:
    telegram_config = config_manager.get_telegram_config()
    if 'telegram_token' not in st.session_state:
        st.session_state.telegram_token = telegram_config.get('token', '')
    if 'telegram_chat_id' not in st.session_state:
        st.session_state.telegram_chat_id = telegram_config.get('chat_id', '')

# Carrega moedas favoritas salvas
if CONFIG_MANAGER_AVAILABLE and 'favorite_coins' not in st.session_state:
    st.session_state.favorite_coins = config_manager.get_favorites()
elif 'favorite_coins' not in st.session_state:
    # Lista de moedas favoritas (prioridade alta)
    FAVORITE_COINS = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 
        'AVAX/USDT', 'XRP/USDT', 'TLM/USDT', 'DEXE/USDT',
        'INJ/USDT', 'MASK/USDT', 'OP/USDT', 'HBAR/USDT', 'ILV/USDT'
    ]
    st.session_state.favorite_coins = FAVORITE_COINS

# Carrega configurações da estratégia salvas
if CONFIG_MANAGER_AVAILABLE:
    strategy_config = config_manager.get_strategy_config()
    strategy_defaults = {
        'rsi_entrada': 25,
        'rsi_saida_min': 70,
        'rsi_saida_max': 75,
        'multi_timeframe_validation': True,
        'timeframe_confirmation': True,
        'require_real_closing': True
    }
    
    for key, default_value in strategy_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = strategy_config.get(key, default_value)

if 'last_analysis_time' not in st.session_state:
    # Inicializa com uma hora no passado para permitir primeira análise
    from datetime import datetime, timedelta, timezone
    st.session_state.last_analysis_time = datetime.now(timezone.utc) - timedelta(hours=1)

class Estrategia1hEngine:
    """Motor de análise para estratégia 1h personalizada"""
    
    def __init__(self):
        self.estrategia_config = {
            'rsi_entrada_max': 25,  # Ajustado para 1h (menos extremo)
            'rsi_saida_min': 65,   # Ajustado para 1h
            'rsi_saida_max': 75,   # Ajustado para 1h
            'rsi_period': 14,
            'min_candles': 50,
            'multi_timeframe_validation': True,
            'timeframes': ['1h', '15m'],  # Mudado para 1h principal
            'real_1h_closing_times': list(range(24)),  # Cada hora tem fechamento real
            'require_real_closing': True  # Obrigatório usar fechamento real
        }
    
    def calculate_indicators_estrategia(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores específicos da estratégia"""
        if len(df) < self.estrategia_config['min_candles']:
            return df
        
        # RSI para estratégia
        df['rsi'] = ta.momentum.rsi(df['close'], window=self.estrategia_config['rsi_period'])
        
        # EMAs para tendência
        df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
        df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
        df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
        
        # Sinais de EMAs
        df['ema_9_below_21'] = df['ema_9'] < df['ema_21']
        df['close_below_emas'] = (df['close'] < df['ema_9']) & (df['close'] < df['ema_21'])
        df['price_below_ema200'] = df['close'] < df['ema_200']
        
        # Sinal completo de tendência EMA
        df['trend_signal'] = (
            df['price_below_ema200'] & 
            df['ema_9_below_21'] & 
            df['close_below_emas']
        )
        
        # Suportes e Resistências
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        # Candle de rejeição (hammer/doji/shooting star)
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['total_range'] = df['high'] - df['low']
        
        # Tipos de candles de rejeição
        df['is_hammer'] = (df['lower_shadow'] > df['body_size'] * 2) & (df['upper_shadow'] < df['body_size'] * 0.5)
        df['is_doji'] = df['body_size'] < df['total_range'] * 0.1
        df['is_shooting_star'] = (df['upper_shadow'] > df['body_size'] * 2) & (df['lower_shadow'] < df['body_size'] * 0.5)
        
        # Shooting Star específicos
        df['is_shooting_star_fall'] = df['is_shooting_star'] & (df['close'] < df['open'])  # Shooting de queda
        df['is_shooting_star_rise'] = df['is_shooting_star'] & (df['close'] > df['open'])  # Shooting de alta
        df['is_rejection_candle'] = df['is_hammer'] | df['is_doji'] | df['is_shooting_star']
        
        # Candle de queda forte
        df['is_falling_candle'] = (df['close'] < df['open']) & (df['body_size'] > df['total_range'] * 0.6)
        df['is_strong_fall'] = df['is_falling_candle'] & (df['body_size'] > df['total_range'] * 0.8)
        
        # Candle de alta forte
        df['is_rising_candle'] = (df['close'] > df['open']) & (df['body_size'] > df['total_range'] * 0.6)
        df['is_strong_rise'] = df['is_rising_candle'] & (df['body_size'] > df['total_range'] * 0.8)
        
        # Topo anterior (para saída)
        df['previous_high'] = df['high'].rolling(window=10).max().shift(1)
        
        # Stop Loss e Resistências
        df['stop_loss'] = df['low'].rolling(window=5).min()  # Mínima dos últimos 5 períodos
        df['resistance_20'] = df['high'].rolling(window=20).max()  # Resistência de 20 períodos
        df['support_20'] = df['low'].rolling(window=20).min()  # Suporte de 20 períodos
        
        # Stop Profit (Take Profit)
        df['take_profit_1r'] = df['close'] * 1.02  # 2% de ganho
        df['take_profit_2r'] = df['close'] * 1.03  # 3% de ganho
        df['take_profit_3r'] = df['close'] * 1.05  # 5% de ganho
        df['nearest_resistance'] = df[['resistance_20', 'previous_high']].min(axis=1)  # Resistência mais próxima
        
        # Cálculo de distâncias percentuais
        df['support_distance_pct'] = (df['close'] - df['support_20']) / df['close'] * 100
        df['resistance_distance_pct'] = (df['resistance_20'] - df['close']) / df['close'] * 100
        df['stop_loss_distance_pct'] = (df['close'] - df['stop_loss']) / df['close'] * 100
        
        # Stop Profit distances
        df['take_profit_1r_distance_pct'] = (df['take_profit_1r'] - df['close']) / df['close'] * 100
        df['take_profit_2r_distance_pct'] = (df['take_profit_2r'] - df['close']) / df['close'] * 100
        df['take_profit_3r_distance_pct'] = (df['take_profit_3r'] - df['close']) / df['close'] * 100
        df['nearest_resistance_distance_pct'] = (df['nearest_resistance'] - df['close']) / df['close'] * 100
        
        # Momentum do RSI
        df['rsi_momentum'] = df['rsi'].diff()
        df['rsi_turning_up'] = df['rsi_momentum'] > 0
        
        # RSI Estocástico (StochRSI)
        period = 14
        df['rsi_min'] = df['rsi'].rolling(window=period).min()
        df['rsi_max'] = df['rsi'].rolling(window=period).max()
        df['stoch_rsi'] = 100 * (df['rsi'] - df['rsi_min']) / (df['rsi_max'] - df['rsi_min'])
        
        # Linhas de sinal do StochRSI
        df['stoch_signal'] = df['stoch_rsi'].rolling(window=3).mean()
        df['stoch_signal_slow'] = df['stoch_rsi'].rolling(window=9).mean()
        
        # Detecção de cruzamentos
        df['stoch_cross_up'] = (df['stoch_rsi'] > df['stoch_signal']) & (df['stoch_rsi'].shift(1) <= df['stoch_signal'].shift(1))
        df['stoch_cross_down'] = (df['stoch_rsi'] < df['stoch_signal']) & (df['stoch_rsi'].shift(1) >= df['stoch_signal'].shift(1))
        df['stoch_cross_up_slow'] = (df['stoch_rsi'] > df['stoch_signal_slow']) & (df['stoch_rsi'].shift(1) <= df['stoch_signal_slow'].shift(1))
        df['stoch_cross_down_slow'] = (df['stoch_rsi'] < df['stoch_signal_slow']) & (df['stoch_rsi'].shift(1) >= df['stoch_signal_slow'].shift(1))
        
        # Zonas de sobrecompra/sobrevenda
        df['stoch_oversold'] = df['stoch_rsi'] < 20
        df['stoch_overbought'] = df['stoch_rsi'] > 80
        df['stoch_bullish_zone'] = (df['stoch_rsi'] > 20) & (df['stoch_rsi'] < 80) & (df['stoch_rsi'] > df['stoch_signal'])
        
        return df
    
    def calculate_score_entrada(self, df: pd.DataFrame) -> int:
        """Calcula score de entrada baseado nos critérios da estratégia"""
        if len(df) < 2:
            return 0
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        
        # Critério 1: Sinal de Tendência EMA (30 pontos)
        if last['trend_signal']:
            score += 30
        
        # Critério 2: RSI oversold (20 pontos) - Ajustado para 1h
        if last['rsi'] < 20:  # Menos extremo que 4h
            score += 20
        elif last['rsi'] < 30:  # Ajustado para 1h
            score += 10
        
        # Critério 3: Candle de rejeição (20 pontos)
        if last['is_rejection_candle']:
            score += 20
        
        # Critério 4: Proximidade do suporte (20 pontos)
        support_distance = ((last['close'] - last['support']) / last['close']) * 100
        if support_distance < 2:  # Menos de 2% do suporte
            score += 20
        
        # Critério 5: Volume acima da média (10 pontos)
        if 'volume' in df.columns:
            volume_avg = df['volume'].rolling(20).mean().iloc[-1]
            if last['volume'] > volume_avg * 1.5:
                score += 10
        
        # Critério 6: Cruzamento de StochRSI (15 pontos)
        if last.get('stoch_cross_up', False):
            score += 15
        
        # Critério 7: RSI virando para cima (10 pontos)
        if last.get('rsi_turning_up', False):
            score += 10
        
        return min(score, 120)  # Máximo 120 pontos   
    def calculate_prob_reversao(self, df: pd.DataFrame) -> float:
        """Calcula probabilidade de reversão (0-100%)"""
        if len(df) < 20:
            return 50.0
        
        last = df.iloc[-1]
        
        prob = 50.0  # Base neutra
        
        # Fatores que aumentam probabilidade de reversão:
        
        # Sinal de tendência EMA forte (+25%)
        if last['trend_signal']:
            prob += 25
        
        # RSI extremamente oversold (+20%)
        if last['rsi'] < 15:
            prob += 20
        elif last['rsi'] < 25:
            prob += 10
        
        # Candle de rejeição (+15%)
        if last['is_rejection_candle']:
            prob += 15
        
        # Volume elevado (+10%)
        if 'volume' in df.columns:
            volume_avg = df['volume'].rolling(20).mean().iloc[-1]
            if last['volume'] > volume_avg * 1.5:
                prob += 10
        
        # StochRSI sobrevenda (+15%)
        if last.get('stoch_oversold', False):
            prob += 15
        
        # Cruzamento StochRSI (+10%)
        if last.get('stoch_cross_up', False) or last.get('stoch_cross_up_slow', False):
            prob += 10
        
        # RSI virando para cima (+5%)
        if last.get('rsi_turning_up', False):
            prob += 5
        
        return min(prob, 95.0)  # Máximo 95%
    
    def check_ema_crossover(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Verifica cruzamento de EMAs no timeframe principal (1h)"""
        if len(df) < 3:
            return False, "Dados insuficientes"
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Verifica cruzamento EMA 9 > EMA 21
        if (last['ema_9'] > last['ema_21'] and 
            prev['ema_9'] <= prev['ema_21']):
            return True, "EMA 9 cruzou acima da EMA 21 (1h)"
        
        # Verifica cruzamento EMA 9 < EMA 21  
        if (last['ema_9'] < last['ema_21'] and 
            prev['ema_9'] >= prev['ema_21']):
            return True, "EMA 9 cruzou abaixo da EMA 21 (1h)"
        
        return False, "Sem cruzamento detectado"
    
    def validate_1h_closing_with_crossover(self, df: pd.DataFrame) -> Tuple[bool, str, str]:
        """Valida se é fechamento real de 1h E se há cruzamento de EMAs"""
        if len(df) < 3:
            return False, "Dados insuficientes", "insufficient_data"
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Verifica se é fechamento real de 1h
        current_hour = last.name.hour if hasattr(last.name, 'hour') else pd.Timestamp.now().hour
        
        # Para 1h, cada hora é fechamento real
        is_real_closing = True
        closing_message = f"Fechamento real 1h: {current_hour:02d}:00 UTC"
        
        # Verifica cruzamento
        crossover_valid, crossover_msg = self.check_ema_crossover(df)
        
        if crossover_valid:
            return True, f"{closing_message} | {crossover_msg}", "crossover_detected"
        else:
            return False, f"{closing_message} | Sem cruzamento", "no_crossover"
    
    def validate_timeframe_confirmation(self, df_15m: pd.DataFrame, signal_type: str) -> Tuple[bool, str]:
        """Valida sinal no timeframe de confirmação (15m) para estratégia 1h"""
        if len(df_15m) < 20:
            return False, "Dados 15m insuficientes"
        
        last_15m = df_15m.iloc[-1]
        prev_15m = df_15m.iloc[-2]
        
        # Para sinal de COMPRA (EMA 9 cruzou acima EMA 21)
        if signal_type == "bullish":
            # Verifica tendência alinhada em 15m
            if last_15m['ema_9'] > last_15m['ema_21']:
                # Verifica se preço não está esticado
                rsi_15m = last_15m.get('rsi', 50)
                if rsi_15m < 70:  # Menos esticado para 1h
                    return True, "✅ Confirmação 15m: Tendência alinhada, EMA9>EMA21, RSI<70"
                else:
                    return False, "❌ Rejeição 15m: Preço esticado (RSI>70)"
            else:
                return False, "❌ Rejeição 15m: Tendência não alinhada (EMA9<EMA21)"
        
        # Para sinal de VENDA (EMA 9 cruzou abaixo EMA 21)
        elif signal_type == "bearish":
            if last_15m['ema_9'] < last_15m['ema_21']:
                rsi_15m = last_15m.get('rsi', 50)
                if rsi_15m > 30:  # Menos sobrevendido para 1h
                    return True, "✅ Confirmação 15m: Tendência baixista, EMA9<EMA21, RSI>30"
                else:
                    return False, "❌ Rejeição 15m: Preço sobrevendido (RSI<30)"
            else:
                return False, "❌ Rejeição 15m: Tendência não alinhada (EMA9>EMA21)"
        
        return False, "Tipo de sinal desconhecido"
    
    def multi_timeframe_analysis(self, symbol: str, df_1h: pd.DataFrame, df_15m: pd.DataFrame = None) -> Dict:
        """Análise multi-timeframe completa com validação de fechamento real 1h"""
        
        # 1. Validação principal: cruzamento em fechamento real 1h
        crossover_valid, crossover_msg, crossover_status = self.validate_1h_closing_with_crossover(df_1h)
        
        result = {
            'symbol': symbol,
            'timeframe_principal': '1h',
            'is_real_1h_closing': False,
            'real_1h_message': '',
            'crossover_1h_detected': False,
            'crossover_1h_message': '',
            'multi_timeframe_validation': False,
            'confirmation_15m': False,
            'confirmation_15m_message': '',
            'final_signal': 'AGUARDAR',
            'signal_type': 'none',
            'crossover_status': crossover_status
        }
        
        # 2. Processa validação de fechamento real
        if "Fechamento real" in crossover_msg:
            result['is_real_1h_closing'] = True
            result['real_1h_message'] = crossover_msg
        
        # 3. Processa cruzamento
        if crossover_valid:
            result['crossover_1h_detected'] = True
            result['crossover_1h_message'] = crossover_msg
            
            # Determina tipo de sinal
            if "acima" in crossover_msg:
                signal_type = "bullish"
                result['signal_type'] = 'bullish'
            elif "abaixo" in crossover_msg:
                signal_type = "bearish"
                result['signal_type'] = 'bearish'
            else:
                return result
            
            # 4. Validação multi-timeframe (15m)
            if self.estrategia_config['multi_timeframe_validation'] and df_15m is not None:
                # Valida no 15m apenas se for fechamento real 1h
                confirmation, confirmation_msg = self.validate_timeframe_confirmation(df_15m, signal_type)
                
                result['confirmation_15m'] = confirmation
                result['confirmation_15m_message'] = confirmation_msg
                result['multi_timeframe_validation'] = True
                
                # Sinal final apenas se confirmado
                if confirmation:
                    if signal_type == "bullish":
                        result['final_signal'] = '🟢 COMPRA 1H+15m CONFIRMADA'
                    else:
                        result['final_signal'] = '🔴 VENDA 1H+15m CONFIRMADA'
                else:
                    result['final_signal'] = '❌ SINAL 1H REJEITADO PELO 15m'
            else:
                # Sem validação - sinal direto do 1h real
                if signal_type == "bullish":
                    result['final_signal'] = '🔵 COMPRA 1H REAL'
                else:
                    result['final_signal'] = '🔴 VENDA 1H REAL'
                result['multi_timeframe_validation'] = False
        
        return result
    
    def check_saida_conditions(self, df: pd.DataFrame) -> Tuple[bool, str, str]:
        """Verifica condições de saída com níveis de alerta"""
        if len(df) < 5:
            return False, "Dados insuficientes", "espera"
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        volume_avg = df['volume'].rolling(20).mean().iloc[-1]
        
        # NÍVEL URGENTE - Venda Imediata
        if (last['rsi'] > 70 and 
            last['ema_9'] < last['ema_21'] and 
            last['volume'] > volume_avg * 2):
            return True, "URGENTE: Múltiplos sinais de venda (RSI>70, EMA9<EMA21, Volume>2x)", "urgente"
        
        # NÍVEL URGENTE - Rompimento de EMA 200
        if (last['close'] > last['ema_200'] and 
            prev['close'] <= prev['ema_200']):
            return True, "URGENTE: Rompimento da EMA 200 (tendência revertida)", "urgente"
        
        # NÍVEL URGENTE - Candle de reversão forte
        if (last['is_shooting_star'] or last['is_strong_fall']) and last['volume'] > volume_avg * 1.5:
            return True, "URGENTE: Candle de reversão com volume elevado", "urgente"
        
        # NÍVEL ATENÇÃO - Preparar Venda (ajustado para 1h)
        if (self.estrategia_config['rsi_saida_min'] <= last['rsi'] <= self.estrategia_config['rsi_saida_max']):
            return True, "ATENÇÃO: RSI na zona de saída (65-75)", "atencao"
        
        # NÍVEL ATENÇÃO - Próximo do topo anterior
        if last['close'] >= last['previous_high'] * 0.98:
            return True, "ATENÇÃO: Próximo do topo anterior (2% abaixo)", "atencao"
        
        # NÍVEL ATENÇÃO - EMA 9 se aproximando de EMA 21
        if (last['ema_9'] < last['ema_21'] and 
            last['ema_9'] > last['ema_21'] * 0.98 and 
            prev['ema_9'] <= prev['ema_21'] * 0.98):
            return True, "ATENÇÃO: EMA 9 se aproximando da EMA 21 (possível cruzamento)", "atencao"
        
        # NÍVEL ATENÇÃO - Volume elevado sem preço
        if last['volume'] > volume_avg * 2 and last['rsi'] > 65:
            return True, "ATENÇÃO: Volume elevado com RSI alto", "atencao"
        
        return False, "MANTER: Sem sinais de saída", "espera"
    
    def check_real_1h_closing(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Verifica se o último candle é um fechamento real de 1h"""
        if len(df) < 2:
            return False, "Dados insuficientes"
        
        last_candle = df.iloc[-1]
        last_time = pd.to_datetime(last_candle.name) if hasattr(last_candle.name, 'hour') else pd.to_datetime(last_candle['timestamp'])
        
        # Para 1h, cada hora é fechamento real
        closing_hour = last_time.hour
        is_real_closing = True  # Sempre verdade para 1h
        
        return True, f"✅ Fechamento real 1h às {closing_hour:02d}:00 UTC"
    
    def analyze_symbol_estrategia(self, symbol: str, collector) -> Dict:
        """Análise completa para um símbolo usando estratégia 1h"""
        try:
            # Coleta dados para timeframes
            df_1h = collector.fetch_single_symbol((symbol, '1h', 100, 'binance'))
            df_15m = None
            
            if self.estrategia_config['multi_timeframe_validation']:
                df_15m = collector.fetch_single_symbol((symbol, '15m', 50, 'binance'))
            
            if df_1h is None or len(df_1h) < self.estrategia_config['min_candles']:
                return {
                    'symbol': symbol,
                    'error': f'Dados insuficientes para {symbol}',
                    'price': 0,
                    'score_entrada': 0,
                    'sinal_saida': False,
                    'motivo_saida': '',
                    'nivel_saida': 'espera'
                }
            
            # Calcula indicadores
            df_1h = self.calculate_indicators_estrategia(df_1h)
            
            if df_15m is not None:
                df_15m = self.calculate_indicators_estrategia(df_15m)
            
            # Análise multi-timeframe
            mt_result = self.multi_timeframe_analysis(symbol, df_1h, df_15m)
            
            # Calcula scores
            score_entrada = self.calculate_score_entrada(df_1h)
            prob_reversao = self.calculate_prob_reversao(df_1h)
            
            # Verifica condições de saída
            sinal_saida, motivo_saida, nivel_saida = self.check_saida_conditions(df_1h)
            
            # Informações de preço
            last_candle = df_1h.iloc[-1]
            price = last_candle['close']
            
            # Suportes e resistências
            support = last_candle['support_20']
            resistance = last_candle['resistance_20']
            stop_loss = last_candle['stop_loss']
            
            # Informações do candle
            candle_type = '🟢 Alta' if last_candle['close'] > last_candle['open'] else '🔴 Baixa'
            body_pct = (abs(last_candle['close'] - last_candle['open']) / last_candle['close']) * 100
            
            # Status dos EMAs
            ema_status = '📈 Acima' if last_candle['ema_9'] > last_candle['ema_21'] else '📉 Abaixo'
            
            # Volume
            volume_avg = df_1h['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = last_candle['volume'] / volume_avg
            
            return {
                'symbol': symbol,
                'price': price,
                'score_entrada': score_entrada,
                'prob_reversao': prob_reversao,
                'sinal_entrada': mt_result.get('final_signal', 'N/A'),
                'sinal_saida': sinal_saida,
                'motivo_saida': motivo_saida,
                'nivel_saida': nivel_saida,
                'timeframe': '1h',
                'rsi': last_candle['rsi'],
                'ema_9': last_candle['ema_9'],
                'ema_21': last_candle['ema_21'],
                'ema_200': last_candle['ema_200'],
                'support': support,
                'resistance': resistance,
                'stop_loss': stop_loss,
                'candle_type': candle_type,
                'body_pct': body_pct,
                'volume_ratio': volume_ratio,
                'ema_status': ema_status,
                'timestamp': pd.Timestamp.now(),
                # Adicionar campos de distância e take profit
                'support_distance_pct': last_candle['support_distance_pct'],
                'stop_loss_distance_pct': last_candle['stop_loss_distance_pct'],
                'take_profit_1r': last_candle['take_profit_1r'],
                'take_profit_1r_distance_pct': last_candle['take_profit_1r_distance_pct'],
                'take_profit_3r': last_candle['take_profit_3r'],
                'take_profit_3r_distance_pct': last_candle['take_profit_3r_distance_pct'],
                'nearest_resistance': last_candle['nearest_resistance'],
                'nearest_resistance_distance_pct': last_candle['nearest_resistance_distance_pct'],
                **mt_result  # Inclui resultados do multi-timeframe
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'price': 0,
                'score_entrada': 0,
                'sinal_saida': False,
                'motivo_saida': '',
                'nivel_saida': 'espera'
            }
                
                        
    def create_rsi_heatmap(self, results: List[Dict]) -> pd.DataFrame:
        """Cria heatmap de RSI"""
        if not results:
            return pd.DataFrame()
        
        # Cria matriz de RSI x Score
        rsi_ranges = ['<10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '>80']
        score_ranges = ['0-20', '20-40', '40-60', '60-80', '80-100']
        
        heatmap_data = pd.DataFrame(0, index=rsi_ranges, columns=score_ranges)
        
        for result in results:
            if 'error' in result:
                continue
                
            rsi = result['rsi']
            score = result['score_entrada']
            
            # Classifica RSI
            if rsi < 10:
                rsi_cat = '<10'
            elif rsi < 20:
                rsi_cat = '10-20'
            elif rsi < 30:
                rsi_cat = '20-30'
            elif rsi < 40:
                rsi_cat = '30-40'
            elif rsi < 50:
                rsi_cat = '40-50'
            elif rsi < 60:
                rsi_cat = '50-60'
            elif rsi < 70:
                rsi_cat = '60-70'
            elif rsi < 80:
                rsi_cat = '70-80'
            else:
                rsi_cat = '>80'
            
            # Classifica Score
            if score < 20:
                score_cat = '0-20'
            elif score < 40:
                score_cat = '20-40'
            elif score < 60:
                score_cat = '40-60'
            elif score < 80:
                score_cat = '60-80'
            else:
                score_cat = '80-100'
            
            heatmap_data.loc[rsi_cat, score_cat] += 1
        
        return heatmap_data

def run_estrategia_analysis():
    """Executa análise da estratégia 1h"""
    try:
        st.session_state.analysis_running = True
        logger.info("Iniciando análise estratégia 1h...")
        st.info("🔄 Iniciando análise da estratégia 1h...")
        
        # Inicializa componentes
        logger.info("Criando collector...")
        collector = get_parallel_collector(max_workers=15)
        logger.info("Collector criado com sucesso")
        
        logger.info("Criando engine...")
        engine = Estrategia1hEngine()
        logger.info("Engine criada com sucesso")
        
        # Obtém símbolos (apenas moedas favoritas)
        logger.info("Obtendo símbolos para timeframe 1h...")
        st.info("📊 Obtendo lista de símbolos...")
        all_symbols = collector.get_usdt_symbols('binance', min_volume=0)
        logger.info(f"Total de símbolos encontrados: {len(all_symbols)}")
        
        # Usa apenas moedas favoritas
        favorite_symbols = [s for s in st.session_state.favorite_coins if s in all_symbols]
        symbols = favorite_symbols
        logger.info(f"Moedas favoritas encontradas: {len(symbols)}")
        st.info(f"📈 {len(symbols)} moedas favoritas encontradas para análise")
        
        if not symbols:
            st.error("Nenhuma moeda favorita encontrada para análise")
            return
        
        logger.info(f"Analisando apenas {len(symbols)} moedas favoritas com estratégia 1h...")
        logger.info(f"Moedas favoritas: {len(favorite_symbols)} encontradas")
        st.info(f"⚡ Analisando {len(symbols)} moedas: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
        
        # Coleta dados em 1h
        start_time = time.time()
        symbols_data = {}
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"Coletando dados para {symbol} ({i}/{len(symbols)})")
                st.info(f"🔄 Coletando {symbol} ({i}/{len(symbols)})")
                df = collector.fetch_single_symbol((symbol, '1h', 100, 'binance'))  # 1h timeframe
                if df is not None and len(df) > 0:
                    symbols_data[symbol] = df
                    logger.info(f"✅ {symbol}: {len(df)} candles coletados")
                else:
                    logger.warning(f"❌ {symbol}: Sem dados")
            except Exception as e:
                logger.warning(f"Erro ao coletar {symbol}: {e}")
                st.warning(f"⚠️ Erro ao coletar {symbol}: {str(e)[:50]}...")
        
        collection_time = time.time() - start_time
        
        if not symbols_data:
            st.error("Nenhum dado coletado")
            return
        
        logger.info(f"Dados coletados: {len(symbols_data)} símbolos em {collection_time:.2f}s")
        st.success(f"✅ Dados coletados: {len(symbols_data)} símbolos em {collection_time:.1f}s")
        
        # Análise da estratégia
        start_time = time.time()
        strategy_results = []
        
        for symbol, df in symbols_data.items():
            result = engine.analyze_symbol_estrategia(symbol, collector)
            strategy_results.append(result)
        
        # Remove resultados com erro
        valid_results = [r for r in strategy_results if 'error' not in r]
        
        # Ordena: favoritas primeiro, depois por score de entrada
        valid_results.sort(key=lambda x: (
            0 if x['symbol'] in st.session_state.favorite_coins else 1,  # Favoritas primeiro
            -x['score_entrada']  # Maior score primeiro
        ))
        
        analysis_time = time.time() - start_time
        
        logger.info(f"Análise concluída: {len(valid_results)} resultados em {analysis_time:.2f}s")
        st.success(f"🎯 Análise concluída: {len(valid_results)} resultados em {analysis_time:.1f}s")
        
        # Atualiza session state
        st.session_state.results = valid_results
        st.session_state.last_analysis = {
            'total_symbols': len(symbols),
            'successful': len(symbols_data),
            'analyzed': len(valid_results),
            'collection_time': collection_time,
            'analysis_time': analysis_time,
            'timestamp': datetime.now(timezone.utc),  # Usar UTC consistentemente
            'entradas_ideais': len([r for r in valid_results if r['score_entrada'] >= 70]),
            'saidas_detectadas': len([r for r in valid_results if r['sinal_saida']]),
            'favorite_found': len([r for r in valid_results if r['symbol'] in st.session_state.favorite_coins])
        }
        
        # Salva timestamp específico para auto-refresh
        st.session_state.last_analysis_time = datetime.now(timezone.utc)
        
        # Processar sinais com Telegram Notifier e Position Manager
        telegram_token = st.session_state.get('telegram_token', '')
        
        # Debug: Mostra informações sobre sinais encontrados
        st.markdown("### 🐛 Debug - Processamento de Sinais")
        
        # Separa sinais de compra e venda
        buy_signals = [r for r in valid_results if "COMPRA" in r.get('sinal_entrada', '').upper()]
        sell_signals = [r for r in valid_results if "VENDA" in r.get('sinal_entrada', '').upper()]
        strong_signals = [r for r in valid_results if r.get('score_entrada', 0) >= 70]
        
        # Mostra debug dos sinais
        col_debug1, col_debug2, col_debug3 = st.columns(3)
        with col_debug1:
            st.metric("🟢 Sinais Compra", len(buy_signals))
        with col_debug2:
            st.metric("🔴 Sinais Venda", len(sell_signals))
        with col_debug3:
            st.metric("⚡ Sinais Fortes", len(strong_signals))
        
        # Mostra detalhes dos sinais de compra
        if buy_signals:
            st.markdown("#### 🟢 Detalhes dos Sinais de Compra:")
            for signal in buy_signals:
                with st.expander(f"📊 {signal['symbol']} - {signal.get('sinal_entrada', 'N/A')}"):
                    st.json({
                        "symbol": signal['symbol'],
                        "sinal_entrada": signal.get('sinal_entrada', 'N/A'),
                        "score_entrada": signal.get('score_entrada', 0),
                        "price": signal.get('price', 0),
                        "rsi": signal.get('rsi', 0)
                    })
        
        if telegram_token and TELEGRAM_AVAILABLE:
            if buy_signals or sell_signals or strong_signals:
                st.info(f"🚀 Processando {len(buy_signals)} compras, {len(sell_signals)} vendas, {len(strong_signals)} sinais fortes...")
                
                # Get Telegram notifier
                notifier = create_telegram_notifier()
                
                # Processa TODOS os sinais de compra - ABRE POSIÇÕES
                for signal in buy_signals:
                    symbol = signal['symbol']
                    price = signal['price']
                    score = signal['score_entrada']
                    rsi = signal['rsi']
                    ema_status = signal.get('ema_status', 'N/A')
                    sinal_entrada = signal.get('sinal_entrada', 'AGUARDAR')
                    
                    success = notifier.send_buy_signal(symbol, price, score, rsi, ema_status)
                    signal_type = "🟢 COMPRA"
                    
                    # Abre posição automaticamente se disponível
                    if POSITION_MANAGER_AVAILABLE:
                        open_positions = position_manager.get_open_positions()
                        st.info(f"🔍 Verificando posição para {symbol}: Já existe? {symbol in open_positions}")
                        
                        if symbol not in open_positions:
                            st.info(f"🔍 Abrindo posição para {symbol}...")
                            position = position_manager.open_position(
                                symbol=symbol,
                                buy_price=price,
                                quantity=1.0,
                                stop_loss=signal.get('stop_loss', price * 0.95),
                                take_profit=signal.get('take_profit_1r', price * 1.10)
                            )
                            
                            if position:
                                st.success(f"✅ Posição aberta com sucesso: {symbol}")
                                notifier.send_message(
                                    f"💰 **POSIÇÃO ABERTA**\n"
                                    f"📈 {symbol}\n"
                                    f"💵 Compra: ${price:.4f}\n"
                                    f"🛡️ Stop Loss: ${position.get('stop_loss', 0):.4f}\n"
                                    f"🎯 Take Profit: ${position.get('take_profit', 0):.4f}\n"
                                    f"📊 Score: {score:.0f}\n"
                                    f"📈 RSI: {rsi:.1f}\n"
                                    f"📝 Sinal: {sinal_entrada}"
                                )
                            else:
                                st.error(f"❌ Erro ao abrir posição para {symbol}")
                        else:
                            st.warning(f"⚠️ Posição já existe para {symbol}")
                    
                    if success:
                        st.success(f"✅ Alerta enviado: {symbol} ({signal_type})")
                    else:
                        st.warning(f"⚠️ Erro ao enviar alerta: {symbol}")
                
                # Processa sinais de venda
                for signal in sell_signals:
                    symbol = signal['symbol']
                    price = signal['price']
                    score = signal['score_entrada']
                    rsi = signal['rsi']
                    sinal_entrada = signal.get('sinal_entrada', 'AGUARDAR')
                    
                    success = notifier.send_sell_signal(symbol, price, score, rsi, sinal_entrada)
                    signal_type = "🔴 VENDA"
                    
                    # Verifica posições abertas para venda
                    if POSITION_MANAGER_AVAILABLE:
                        open_positions = position_manager.get_open_positions()
                        if symbol in open_positions:
                            should_sell, sell_reason, sell_price = position_manager.check_sell_signals(symbol, signal)
                            
                            if should_sell:
                                closed_position = position_manager.close_position(symbol, sell_price, sell_reason)
                                
                                if closed_position:
                                    notifier.send_message(
                                        f"💸 **POSIÇÃO FECHADA**\n"
                                        f"📉 {symbol}\n"
                                        f"💵 Venda: ${sell_price:.4f}\n"
                                        f"📈 Compra: ${closed_position.get('buy_price', 0):.4f}\n"
                                        f"💰 Lucro: {closed_position.get('profit_percent', 0):.2f}% (${closed_position.get('profit_amount', 0):.2f})\n"
                                        f"📝 Motivo: {sell_reason}"
                                    )
                                    st.success(f"✅ Posição fechada: {symbol} - Lucro: {closed_position.get('profit_percent', 0):.2f}%")
                    
                    if success:
                        st.success(f"✅ Alerta enviado: {symbol} ({signal_type})")
                    else:
                        st.warning(f"⚠️ Erro ao enviar alerta: {symbol}")
                
                # Verifica posições abertas para sinais de saída (análise contínua)
                if POSITION_MANAGER_AVAILABLE:
                    open_positions = position_manager.get_open_positions()
                    
                    for symbol, position in open_positions.items():
                        # Encontra análise correspondente
                        symbol_analysis = next((r for r in valid_results if r['symbol'] == symbol), None)
                        
                        if symbol_analysis:
                            should_sell, sell_reason, sell_price = position_manager.check_sell_signals(symbol, symbol_analysis)
                            
                            if should_sell:
                                closed_position = position_manager.close_position(symbol, sell_price, sell_reason)
                                
                                if closed_position:
                                    notifier.send_message(
                                        f"💸 **POSIÇÃO FECHADA - REVERSÃO DETECTADA**\n"
                                        f"📉 {symbol}\n"
                                        f"💵 Venda: ${sell_price:.4f}\n"
                                        f"📈 Compra: ${closed_position.get('buy_price', 0):.4f}\n"
                                        f"💰 Lucro: {closed_position.get('profit_percent', 0):.2f}% (${closed_position.get('profit_amount', 0):.2f})\n"
                                        f"📝 Motivo: {sell_reason}"
                                    )
                                    st.success(f"✅ Posição fechada por reversão: {symbol} - Lucro: {closed_position.get('profit_percent', 0):.2f}%")
                
                # Processa sinais fortes adicionais (para notificações especiais)
                for signal in strong_signals:
                    symbol = signal['symbol']
                    price = signal['price']
                    score = signal['score_entrada']
                    rsi = signal['rsi']
                    ema_status = signal.get('ema_status', 'N/A')
                    sinal_entrada = signal.get('sinal_entrada', 'AGUARDAR')
                    
                    # Envia notificação especial para sinais fortes
                    if "COMPRA" not in sinal_entrada.upper() and "VENDA" not in sinal_entrada.upper():
                        notifier.send_strategy_update(len(valid_results), 
                                                               len(buy_signals),
                                                               len(sell_signals),
                                                               strong_signals)
                        st.success(f"✅ Alerta especial enviado: {symbol} (Score: {score})")
                
                # Send strategy summary
                if buy_signals or sell_signals:
                    notifier.send_strategy_update(
                        len(valid_results),
                        len(buy_signals),
                        len(sell_signals),
                        strong_signals
                    )
        elif telegram_token and not TELEGRAM_AVAILABLE:
            st.warning("⚠️ Telegram configurado mas módulo não disponível neste ambiente")
        else:
            st.info("📱 Configure o Telegram no sidebar para receber alertas")
        
        # Salva no banco de dados
        try:
            db_manager.save_analysis_results(valid_results)
            db_manager.update_daily_stats(valid_results)
            logger.info(f"Análise salva no banco de dados: {len(valid_results)} resultados")
        except Exception as e:
            logger.error(f"Erro ao salvar no banco de dados: {e}")
        
        logger.info("Análise estratégia 1h concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        st.error(f"Erro na análise: {e}")
    finally:
        st.session_state.analysis_running = False

def create_strategy_chart(result: Dict) -> go.Figure:
    """Cria gráfico específico para estratégia"""
    # Simulação de dados para visualização
    x = list(range(50))
    base_price = result['price']
    
    # Gera candles simulados baseados no RSI
    np.random.seed(42)
    price_changes = np.random.normal(0, 0.02, 50)
    prices = [base_price]
    for change in price_changes:
        prices.append(prices[-1] * (1 + change))
    
    prices = prices[1:]
    
    fig = go.Figure()
    
    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=x,
        open=[p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        high=[p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        low=[p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        close=prices,
        name=result['symbol'],
        increasing_line_color='#00ff00',
        decreasing_line_color='#ff0000'
    ))
    
    # Linha de suporte
    support_level = result['price'] * (1 - result.get('support_distance', 2) / 100)
    fig.add_hline(y=support_level, line_dash="dash", line_color="blue", 
                  annotation_text="Suporte", annotation_position="bottom right")
    
    # RSI plot (secundário)
    fig.add_trace(go.Scatter(
        x=x,
        y=[result['rsi']] * len(x),
        mode='lines',
        name=f'RSI: {result["rsi"]:.1f}',
        yaxis='y2',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title=f"📈 {result['symbol']} - Score: {result['score_entrada']:.0f}",
        template="plotly_dark",
        height=400,
        xaxis=dict(title="Período"),
        yaxis=dict(title="Preço"),
        yaxis2=dict(title="RSI", overlaying='y', side='right'),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

# Sidebar
st.sidebar.markdown("# ⚡ Estratégia 1H PRO")
st.sidebar.markdown("---")

# Telegram Configuration
st.sidebar.markdown("### 📱 Configuração Telegram")

# Show Telegram availability status
if not TELEGRAM_AVAILABLE:
    st.sidebar.error("❌ Módulo Telegram não disponível")
    st.sidebar.warning("Funcionalidades Telegram desativadas")
else:
    st.sidebar.success("✅ Módulo Telegram disponível")

telegram_token = st.sidebar.text_input(
    "🔑 Token Telegram Bot",
    value=st.session_state.get('telegram_token', ''),
    type="password",
    help="Token do bot criado com @BotFather",
    on_change=lambda: save_telegram_config()
)

telegram_chat_id = st.sidebar.text_input(
    "💬 Chat ID",
    value=st.session_state.get('telegram_chat_id', ''),
    help="ID do chat para receber mensagens",
    on_change=lambda: save_telegram_config()
)

# Show if Telegram is configured (moved after input definitions)
if CONFIG_MANAGER_AVAILABLE and config_manager.is_telegram_configured():
    st.sidebar.success("💾 Configurações salvas")
elif telegram_token and telegram_chat_id:
    st.sidebar.info("📝 Configurações não salvas ainda")

# Função para salvar configurações do Telegram
def save_telegram_config():
    """Salva configurações do Telegram automaticamente"""
    if CONFIG_MANAGER_AVAILABLE:
        token = st.session_state.get('telegram_token', '')
        chat_id = st.session_state.get('telegram_chat_id', '')
        config_manager.set_telegram_config(token, chat_id, bool(token and chat_id))
        logger.info("Configurações do Telegram salvas automaticamente")

# Save Telegram settings
st.session_state.telegram_token = telegram_token
st.session_state.telegram_chat_id = telegram_chat_id

# Test Telegram connection
if st.sidebar.button("🧪 Testar Telegram", key="test_telegram") and TELEGRAM_AVAILABLE:
    if telegram_token and telegram_chat_id:
        with st.sidebar:
            with st.spinner("Testando conexão..."):
                notifier = create_telegram_notifier()
                if notifier.test_connection():
                    if notifier.send_test_message():
                        st.success("✅ Telegram configurado com sucesso!")
                    else:
                        st.error("❌ Erro ao enviar mensagem")
                else:
                    st.error("❌ Falha na conexão com Telegram")
    else:
        st.sidebar.warning("⚠️ Preencha Token e Chat ID")
elif not TELEGRAM_AVAILABLE:
    st.sidebar.info("📡 Telegram não disponível neste ambiente")

st.sidebar.markdown("---")

# Moedas Favoritas
st.sidebar.markdown("### ⭐ Moedas Favoritas")
favorite_coins_str = ", ".join([coin.replace("/USDT", "") for coin in st.session_state.favorite_coins])
st.sidebar.markdown(f"**{favorite_coins_str}**")
st.sidebar.markdown("*Priorizadas na análise*")

# Parâmetros da Estratégia
st.sidebar.markdown("### 🎯 Parâmetros da Estratégia")

# Carrega valores salvos ou usa defaults
rsi_entrada = st.sidebar.slider(
    "RSI Máximo para Entrada", 
    10, 40, 
    st.session_state.get('rsi_entrada', 25),
    on_change=lambda: save_strategy_config()
)
rsi_saida_min = st.sidebar.slider(
    "RSI Mínimo para Saída", 
    60, 80, 
    st.session_state.get('rsi_saida_min', 70),
    on_change=lambda: save_strategy_config()
)
rsi_saida_max = st.sidebar.slider(
    "RSI Máximo para Saída", 
    70, 90, 
    st.session_state.get('rsi_saida_max', 75),
    on_change=lambda: save_strategy_config()
)
max_symbols = st.sidebar.slider("Símbolos para Análise", 20, 150, 80)
multi_tf_validation = st.sidebar.checkbox(
    "🔄 Validação Multi-Timeframe", 
    value=st.session_state.get('multi_timeframe_validation', True), 
    help="Usa 15m para confirmar sinais do 1h",
    on_change=lambda: save_strategy_config()
)
timeframe_confirm = st.sidebar.selectbox(
    "⏰ Timeframe Confirmação", 
    ["15m", "30m", "5m"], 
    index=0, 
    help="Timeframe para validar sinais do 1h"
)
real_1h_closing = st.sidebar.checkbox(
    "🕐 Fechamento Real 1H (Obrigatório)", 
    value=st.session_state.get('require_real_closing', True), 
    help="Usa apenas fechamentos reais de cada hora",
    on_change=lambda: save_strategy_config()
)

# Função para salvar configurações da estratégia
def save_strategy_config():
    """Salva configurações da estratégia automaticamente"""
    if CONFIG_MANAGER_AVAILABLE:
        config_manager.set_strategy_config(
            rsi_entrada=rsi_entrada,
            rsi_saida_min=rsi_saida_min,
            rsi_saida_max=rsi_saida_max,
            multi_timeframe_validation=multi_tf_validation,
            timeframe_confirmation=timeframe_confirm,
            require_real_closing=real_1h_closing
        )
        logger.info("Configurações da estratégia salvas automaticamente")

# Position Management Section
if POSITION_MANAGER_AVAILABLE:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💰 Gestão de Posições")
    
    # Resumo das posições
    position_summary = position_manager.get_position_summary()
    
    col_pos1, col_pos2 = st.sidebar.columns(2)
    with col_pos1:
        st.sidebar.metric("📊 Posições Abertas", position_summary.get('open_positions', 0))
    with col_pos2:
        st.sidebar.metric("💎 Lucro Aberto", f"${position_summary.get('open_profit', 0):.2f}")
    
    # Botões de gestão
    if st.sidebar.button("📋 Ver Posições", key="view_positions"):
        st.session_state.show_positions = True
    
    if st.sidebar.button("➕ Abrir Posição Manual", key="open_position_manual"):
        st.session_state.show_open_position = True
    
    # Lista de posições abertas
    open_positions = position_manager.get_open_positions()
    if open_positions:
        st.sidebar.markdown("#### 📈 Posições Ativas")
        for symbol, pos in open_positions.items():
            profit_color = "green" if pos.get('profit_percent', 0) > 0 else "red"
            st.sidebar.markdown(f"""
            **{symbol}**
            - Preço: ${pos.get('buy_price', 0):.4f}
            - Atual: ${pos.get('current_price', 0):.4f}
            - Lucro: <span style="color:{profit_color}">{pos.get('profit_percent', 0):.2f}%</span>
            """, unsafe_allow_html=True)
    else:
        st.sidebar.info("💭 Nenhuma posição aberta")

else:
    st.sidebar.info("💰 Gestão de posições não disponível")
if st.sidebar.button("⚡ ANALISAR ESTRATÉGIA 1H", disabled=st.session_state.analysis_running):
    # Atualiza configurações
    if 'engine' not in st.session_state:
        st.session_state.engine = Estrategia1hEngine()
    
    st.session_state.engine.estrategia_config.update({
        'rsi_entrada_max': rsi_entrada,
        'rsi_saida_min': rsi_saida_min,
        'rsi_saida_max': rsi_saida_max,
        'multi_timeframe_validation': multi_tf_validation,
        'timeframe_confirmation': timeframe_confirm,
        'require_real_closing': real_1h_closing
    })
    
    run_estrategia_analysis()

# Auto-Refresh Logic
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔄 Controle de Atualização")

# Botão de controle do auto-refresh
auto_refresh_active = st.sidebar.checkbox("🔄 ATUALIZAÇÃO AUTOMÁTICA", value=False, help="Ativa atualização automática dos dados")

if auto_refresh_active:
    refresh_interval = st.sidebar.selectbox("⏱️ Intervalo de Atualização", ["5 min", "10 min", "15 min", "30 min"], index=1)
    
    # Mostrar status do auto-refresh
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Status da Atualização")
    
    # Verificar última atualização
    from datetime import datetime, timedelta
    last_update = st.session_state.get('last_analysis_time', None)
    now = datetime.now(timezone.utc)
    
    # Calcular próxima atualização
    interval_minutes = {
        "5 min": 5,
        "10 min": 10, 
        "15 min": 15,
        "30 min": 30
    }.get(refresh_interval, 10)
    
    if last_update:
        time_diff = now - last_update
        minutes_ago = int(time_diff.total_seconds() / 60)
        seconds_ago = int(time_diff.total_seconds() % 60)
        st.sidebar.markdown(f"**Última análise:** {minutes_ago}min {seconds_ago}s atrás")
        
        next_update = last_update + timedelta(minutes=interval_minutes)
        
        # Verificar se é hora de atualizar
        if now >= next_update:
            st.sidebar.markdown("**Status:** 🔄 ATUALIZANDO AGORA...")
            
            # Atualiza automaticamente
            if 'engine' not in st.session_state:
                st.session_state.engine = Estrategia1hEngine()
            
            st.session_state.engine.estrategia_config.update({
                'rsi_entrada_max': rsi_entrada,
                'rsi_saida_min': rsi_saida_min,
                'rsi_saida_max': rsi_saida_max,
                'multi_timeframe_validation': multi_tf_validation,
                'timeframe_confirmation': timeframe_confirm,
                'require_real_closing': real_1h_closing
            })
            
            # Atualiza timestamp ANTES de rodar a análise
            st.session_state.last_analysis_time = now
            
            # Força atualização
            st.session_state.force_refresh = True
            run_estrategia_analysis()
            st.rerun()
            
        else:
            time_until_next = next_update - now
            minutes_until = int(time_until_next.total_seconds() / 60)
            seconds_until = int(time_until_next.total_seconds() % 60)
            st.sidebar.markdown(f"**Próxima atualização:** {minutes_until}min {seconds_until}s")
            st.sidebar.markdown(f"**Intervalo:** {refresh_interval}")
            
            # Usar sistema nativo do Streamlit com refresh contínuo
            try:
                from streamlit_autorefresh import st_autorefresh
                # Configurar refresh para verificar a cada 30 segundos
                count = st_autorefresh(interval=30000, limit=None, key="auto_refresh_counter")
                
                # Quando o contador atualizar, verifica se é hora de analisar
                current_time = datetime.now(timezone.utc)
                if count > 0 and current_time >= next_update:
                    st.sidebar.markdown("**Status:** 🔄 VERIFICANDO...")
                    if 'engine' not in st.session_state:
                        st.session_state.engine = Estrategia1hEngine()
                    
                    st.session_state.engine.estrategia_config.update({
                        'rsi_entrada_max': rsi_entrada,
                        'rsi_saida_min': rsi_saida_min,
                        'rsi_saida_max': rsi_saida_max,
                        'multi_timeframe_validation': multi_tf_validation,
                        'timeframe_confirmation': timeframe_confirm,
                        'require_real_closing': real_1h_closing
                    })
                    
                    # Atualiza timestamp antes de rodar a análise
                    st.session_state.last_analysis_time = current_time
                    run_estrategia_analysis()
                    st.rerun()
                    
            except ImportError:
                # Se não tiver streamlit-autorefresh, usa método alternativo
                st.sidebar.markdown("**Info:** Install streamlit-autorefresh para melhor performance")
                st.sidebar.markdown("`pip install streamlit-autorefresh`")
                
                # Método alternativo simples - verifica a cada refresh manual
                current_time = datetime.now(timezone.utc)
                if current_time >= next_update:
                    st.session_state.last_analysis_time = current_time
                    st.session_state.force_refresh = True
                    run_estrategia_analysis()
                    st.rerun()
    else:
        st.sidebar.markdown("**Status:** 🔄 AGUARDANDO PRIMEIRA ANÁLISE...")
        st.sidebar.markdown("**Ação:** Execute uma análise manual para iniciar o auto-refresh")
    
    # Informações sobre fechamentos de hora
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🕐 Fechamentos 1H UTC")
    st.sidebar.markdown("A cada hora: 00:00 | 01:00 | 02:00 | ... | 23:00")
    
    # Botão para parar auto-refresh
    if st.sidebar.button("⏹️ PARAR ATUALIZAÇÃO AUTOMÁTICA"):
        st.session_state.auto_refresh_disabled = True
        st.rerun()
        
else:
    st.sidebar.markdown("**Status:** ❌ Atualização automática DESATIVADA")
    st.sidebar.markdown("**Execute análise manual quando desejar**")
    st.sidebar.markdown("**Ative a opção acima para automação**")
    
    # Mostrar última análise se existir
    last_update = st.session_state.get('last_analysis_time', None)
    if last_update:
        from datetime import datetime, timedelta
        time_diff = datetime.now(timezone.utc) - last_update
        minutes_ago = int(time_diff.total_seconds() / 60)
        st.sidebar.markdown(f"**Última análise:** {minutes_ago} min atrás")

# Botão PDF (temporariamente desabilitado)
if st.sidebar.button("📄 GERAR PDF ESTRATÉGIA"):
    st.sidebar.warning("Função PDF temporariamente desabilitada para correção técnica")
    # if st.session_state.results:
    #     try:
    #         # Converte resultados para formato compatível com PDF
    #         pdf_results = []
    #         for result in st.session_state.results:
    #             pdf_results.append(SimpleAnalysisResult(
    #                 symbol=result['symbol'],
    #                 price=result['price'],
    #                 score=result['score_entrada'],
    #                 signal=result['sinal_entrada'],
    #                 confidence=result['prob_reversao'],
    #                 indicators={'rsi': result['rsi']},
    #                 detailed_scores={'entrada_score': result['score_entrada'], 'reversao_prob': result['prob_reversao']},
    #                 timestamp=result['timestamp'],
    #                 processing_time=0.0,
    #                 signal_timestamp=result['timestamp']
    #             ))
    #         
    #         filename = generate_simple_pdf(pdf_results)
    #         if filename:
    #             st.success(f"PDF da estratégia gerado: {filename}")
    #             with open(filename, "rb") as file:
    #                 st.sidebar.download_button(
    #                     label="📥 BAIXAR PDF ESTRATÉGIA",
    #                     data=file.read(),
    #                     file_name=filename,
    #                     mime="application/pdf"
    #                 )
    #     except Exception as e:
    #         st.error(f"Erro ao gerar PDF: {e}")
    # else:
    #     st.sidebar.warning("Execute uma análise primeiro")

# Telegram Status Panel
st.markdown("---")
st.markdown("### 📱 Status Telegram")

telegram_token = st.session_state.get('telegram_token', '')
telegram_chat_id = st.session_state.get('telegram_chat_id', '')

if telegram_token and telegram_chat_id:
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🔑 Token", "✅ Configurado")
    with col2:
        st.metric("💬 Chat ID", "✅ Configurado")
    
    # Test connection button
    if st.button("🧪 Testar Conexão Telegram", key="main_test_telegram") and TELEGRAM_AVAILABLE:
        with st.spinner("Testando..."):
            notifier = create_telegram_notifier()
            if notifier.test_connection():
                if notifier.send_test_message():
                    st.success("✅ Telegram 100% funcional!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao enviar mensagem")
            else:
                st.error("❌ Falha na conexão")
    elif not TELEGRAM_AVAILABLE:
        st.warning("⚠️ Módulo Telegram não disponível neste ambiente")
else:
    st.warning("⚠️ Configure o Token e Chat ID no sidebar para ativar notificações")
    
    st.info("""
    📱 **Como configurar:**
    1. Abra o Telegram e procure por **@BotFather**
    2. Envie `/newbot` e siga as instruções
    3. Copie o token do bot
    4. Inicie uma conversa com seu bot
    5. Envie qualquer mensagem
    6. Use: `https://api.telegram.org/botSEU_TOKEN/getUpdates`
    7. Copie seu Chat ID
    8. Configure no sidebar acima
    """)

# Configuration Management Section
if CONFIG_MANAGER_AVAILABLE:
    st.markdown("---")
    st.markdown("### ⚙️ Gerenciamento de Configurações")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Salvar Todas Configurações"):
            success = config_manager.update_from_session_state(st.session_state)
            if success:
                st.success("✅ Todas as configurações salvas com sucesso!")
            else:
                st.error("❌ Erro ao salvar configurações")
    
    with col2:
        if st.button("🔄 Recarregar Configurações"):
            # Recarrega do arquivo
            config_manager.config = config_manager.load_config()
            # Atualiza session state
            telegram_config = config_manager.get_telegram_config()
            st.session_state.telegram_token = telegram_config.get('token', '')
            st.session_state.telegram_chat_id = telegram_config.get('chat_id', '')
            st.success("✅ Configurações recarregadas!")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Resetar Configurações"):
            if st.checkbox("Confirmar reset", key="confirm_reset"):
                # Remove arquivo de configuração
                import os
                if os.path.exists(config_manager.config_file):
                    os.remove(config_manager.config_file)
                st.success("✅ Configurações resetadas!")
                st.rerun()
    
    # Mostra configurações atuais
    with st.expander("📋 Ver Configurações Atuais"):
        st.json(config_manager.config)
else:
    st.info("⚙️ Gerenciamento de configurações não disponível neste ambiente")

# Position Management Section
if POSITION_MANAGER_AVAILABLE:
    st.markdown("---")
    st.markdown("### 💰 Gestão de Posições")
    
    # Tabs para diferentes visualizações
    pos_tab1, pos_tab2, pos_tab3 = st.tabs(["📊 Resumo", "📈 Posições Abertas", "📉 Histórico"])
    
    with pos_tab1:
        # Resumo das posições
        position_summary = position_manager.get_position_summary()
        
        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        
        with col_sum1:
            st.metric("📊 Posições Abertas", position_summary.get('open_positions', 0))
        
        with col_sum2:
            st.metric("💎 Lucro Aberto", f"${position_summary.get('open_profit', 0):.2f}")
        
        with col_sum3:
            st.metric("📈 Win Rate", f"{position_summary.get('win_rate', 0):.1f}%")
        
        with col_sum4:
            total_profit = position_summary.get('total_profit', 0)
            profit_color = "green" if total_profit > 0 else "red"
            st.markdown(f"### 💰 Lucro Total")
            st.markdown(f"<span style='color:{profit_color}; font-size:24px; font-weight:bold;'>${total_profit:.2f}</span>", unsafe_allow_html=True)
        
        # Gráfico de desempenho
        if position_summary.get('closed_positions', 0) > 0:
            closed_positions = position_manager.get_closed_positions()
            all_trades = []
            
            for symbol_positions in closed_positions.values():
                all_trades.extend(symbol_positions)
            
            if all_trades:
                df_trades = pd.DataFrame(all_trades)
                df_trades['close_time'] = pd.to_datetime(df_trades['close_time'])
                df_trades['cumulative_profit'] = df_trades['profit_amount'].cumsum()
                
                fig_profit = go.Figure()
                fig_profit.add_trace(go.Scatter(
                    x=df_trades['close_time'],
                    y=df_trades['cumulative_profit'],
                    mode='lines+markers',
                    name='Lucro Acumulado',
                    line=dict(color='green', width=2)
                ))
                
                fig_profit.update_layout(
                    title="📈 Lucro Acumulado por Trade",
                    xaxis_title="Data",
                    yaxis_title="Lucro ($)",
                    height=400
                )
                
                st.plotly_chart(fig_profit, use_container_width=True)
    
    with pos_tab2:
        # Posições abertas
        open_positions = position_manager.get_open_positions()
        
        if open_positions:
            st.markdown("#### 📈 Posições Ativas")
            
            for symbol, pos in open_positions.items():
                with st.expander(f"📊 {symbol} - Lucro: {pos.get('profit_percent', 0):.2f}%"):
                    col_pos1, col_pos2, col_pos3 = st.columns(3)
                    
                    with col_pos1:
                        st.markdown("### 💰 Informações")
                        st.markdown(f"**Preço Compra:** ${pos.get('buy_price', 0):.4f}")
                        st.markdown(f"**Preço Atual:** ${pos.get('current_price', 0):.4f}")
                        st.markdown(f"**Quantidade:** {pos.get('quantity', 0):.2f}")
                        
                        # Indicador de lucro
                        profit_percent = pos.get('profit_percent', 0)
                        profit_color = "green" if profit_percent > 0 else "red"
                        st.markdown(f"### 💎 Lucro/Perda")
                        st.markdown(f"<span style='color:{profit_color}; font-size:20px; font-weight:bold;'>{profit_percent:.2f}%</span>", unsafe_allow_html=True)
                        st.markdown(f"<span style='color:{profit_color}; font-size:16px;'>${pos.get('profit_amount', 0):.2f}</span>", unsafe_allow_html=True)
                    
                    with col_pos2:
                        st.markdown("### 🛡️ Gerenciamento de Risco")
                        st.markdown(f"**Stop Loss:** ${pos.get('stop_loss', 0):.4f}")
                        st.markdown(f"**Take Profit:** ${pos.get('take_profit', 0):.4f}")
                        
                        trailing_stop = pos.get('trailing_stop')
                        if trailing_stop:
                            st.markdown(f"**Trailing Stop:** ${trailing_stop:.4f}")
                        
                        # Distâncias
                        buy_price = pos.get('buy_price', 0)
                        current_price = pos.get('current_price', 0)
                        
                        if buy_price > 0:
                            dist_to_sl = ((current_price - pos.get('stop_loss', 0)) / buy_price) * 100
                            dist_to_tp = ((pos.get('take_profit', 0) - current_price) / buy_price) * 100
                            
                            st.markdown(f"**Distância SL:** {dist_to_sl:.2f}%")
                            st.markdown(f"**Distância TP:** {dist_to_tp:.2f}%")
                    
                    with col_pos3:
                        st.markdown("### 📅 Tempo")
                        open_time = pos.get('open_time', '')
                        if open_time:
                            dt = pd.to_datetime(open_time)
                            now = pd.Timestamp.now(tz='UTC')
                            duration = now - dt
                            
                            st.markdown(f"**Abertura:** {dt.strftime('%H:%M:%S')}")
                            st.markdown(f"**Duração:** {duration.components.hours}h {duration.components.minutes}m")
                        
                        # Botão de fechar manual
                        if st.button(f"❌ Fechar {symbol}", key=f"close_{symbol}"):
                            closed_pos = position_manager.close_position(symbol, pos.get('current_price', 0), "Fechamento Manual")
                            if closed_pos:
                                st.success(f"✅ Posição {symbol} fechada manualmente!")
                                st.rerun()
        else:
            st.info("💭 Nenhuma posição aberta no momento")
    
    with pos_tab3:
        # Histórico de posições fechadas
        closed_positions = position_manager.get_closed_positions()
        
        if closed_positions:
            st.markdown("#### 📉 Histórico de Trades")
            
            all_closed = []
            for symbol_positions in closed_positions.values():
                all_closed.extend(symbol_positions)
            
            if all_closed:
                df_closed = pd.DataFrame(all_closed)
                
                # Formatação para exibição
                display_df = df_closed[['symbol', 'buy_price', 'sell_price', 'profit_percent', 'profit_amount', 'close_reason', 'close_time']].copy()
                display_df.columns = ['Símbolo', 'Compra', 'Venda', 'Lucro %', 'Lucro $', 'Motivo', 'Data/Hora']
                
                # Formata valores
                display_df['Compra'] = display_df['Compra'].apply(lambda x: f"${x:.4f}")
                display_df['Venda'] = display_df['Venda'].apply(lambda x: f"${x:.4f}")
                display_df['Lucro %'] = display_df['Lucro %'].apply(lambda x: f"{x:.2f}%")
                display_df['Lucro $'] = display_df['Lucro $'].apply(lambda x: f"${x:.2f}")
                display_df['Data/Hora'] = pd.to_datetime(display_df['Data/Hora']).dt.strftime('%d/%m %H:%M')
                
                # Destaque lucros/perdas
                def color_profit(val):
                    # Tenta extrair valor numérico de strings formatadas
                    if isinstance(val, str):
                        try:
                            if '%' in val:
                                num_val = float(val.replace('%', ''))
                            elif '$' in val:
                                num_val = float(val.replace('$', ''))
                            else:
                                num_val = float(val)
                        except:
                            return 'color: gray'
                    else:
                        num_val = val
                    
                    color = 'green' if num_val > 0 else 'red' if num_val < 0 else 'gray'
                    return f'color: {color}'
                
                display_df = display_df.style.map(color_profit, subset=['Lucro %', 'Lucro $'])
                
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("📭 Nenhuma posição fechada ainda")

else:
    st.info("💰 Gestão de posições não disponível neste ambiente")
st.markdown("---")
st.markdown("## 📊 Resultados da Análise")

if st.session_state.results:
    results = st.session_state.results
    
    # Métricas da Análise
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        entradas_ideais = len([r for r in results if r['score_entrada'] >= 70])
        st.metric("🟢 Entradas Ideais", entradas_ideais)
    
    with col2:
        saidas_urgentes = len([r for r in results if r.get('sinal_saida') and r.get('nivel_saida') == 'urgente'])
        saidas_atencao = len([r for r in results if r.get('sinal_saida') and r.get('nivel_saida') == 'atencao'])
        total_saidas = saidas_urgentes + saidas_atencao
        
        if saidas_urgentes > 0:
            st.metric("🔴 Saídas Urgentes", saidas_urgentes)
        elif saidas_atencao > 0:
            st.metric("🟡 Saídas Atenção", saidas_atencao)
        else:
            st.metric("🟢 Manter Posições", len(results) - total_saidas)
    
    with col3:
        avg_score = sum(r['score_entrada'] for r in results) / len(results) if results else 0
        st.metric("📊 Score Médio", f"{avg_score:.1f}")
    
    with col4:
        avg_prob = sum(r['prob_reversao'] for r in results) / len(results) if results else 0
        st.metric("📈 Prob. Média Reversão", f"{avg_prob:.1f}%")
    
    with col5:
        hammers = len([r for r in results if r.get('is_hammer', False)])
        st.metric("🔨 Hammers", hammers)
    
    with col6:
        avg_rsi = sum(r['rsi'] for r in results) / len(results) if results else 0
        st.metric("📉 RSI Médio", f"{avg_rsi:.1f}")
    
    # Trading Metrics
    st.markdown("---")
    st.markdown("### 📈 Métricas de Trading")
    
    col_trade1, col_trade2, col_trade3, col_trade4 = st.columns(4)
    
    with col_trade1:
        # Calcula R/R Ratio médio
        valid_rr = [r for r in results if r.get('stop_loss') and r.get('take_profit_1r')]
        if valid_rr:
            rr_ratios = []
            for r in valid_rr:
                risk = abs(r['price'] - r['stop_loss'])
                reward = abs(r['take_profit_1r'] - r['price'])
                if risk > 0:
                    rr_ratios.append(reward / risk)
            avg_rr = sum(rr_ratios) / len(rr_ratios) if rr_ratios else 0
            st.metric("⚖️ R/R Médio", f"1:{avg_rr:.2f}")
        else:
            st.metric("⚖️ R/R Médio", "N/A")
    
    with col_trade2:
        # Conta padrões
        total_patterns = 0
        pattern_counts = {
            "Hammer": 0,
            "Doji": 0,
            "Shooting Star": 0,
            "Falling": 0
        }
        
        for r in results:
            if r.get('is_hammer', False):
                pattern_counts["Hammer"] += 1
                total_patterns += 1
            if r.get('is_doji', False):
                pattern_counts["Doji"] += 1
                total_patterns += 1
            if r.get('is_shooting_star', False):
                pattern_counts["Shooting Star"] += 1
                total_patterns += 1
            if r.get('is_falling_candle', False):
                pattern_counts["Falling"] += 1
                total_patterns += 1
        
        most_common = max(pattern_counts, key=pattern_counts.get) if total_patterns > 0 else None
        if most_common and pattern_counts[most_common] > 0:
            st.metric("🕯️ Padrão Principal", f"{most_common} ({pattern_counts[most_common]})")
        else:
            st.metric("🕯️ Padrão Principal", "N/A")
    
    with col_trade3:
        # Volume médio
        volume_ratios = [r.get('volume_ratio', 0) for r in results if r.get('volume_ratio')]
        if volume_ratios:
            avg_volume = sum(volume_ratios) / len(volume_ratios)
            st.metric("📊 Volume Médio", f"{avg_volume:.2f}x")
        else:
            st.metric("📊 Volume Médio", "N/A")
    
    with col_trade4:
        # Preço médio das oportunidades
        if results:
            avg_price = sum(r['price'] for r in results) / len(results)
            st.metric("💰 Preço Médio", f"${avg_price:.4f}")
        else:
            st.metric("💰 Preço Médio", "N/A")
    
    # Tabela de Resultados
    st.markdown("### 🎯 Análise Detalhada")
    
    # Opções de exibição
    col_view1, col_view2 = st.columns([2, 1])
    with col_view1:
        view_mode = st.selectbox(
            "📊 Modo de Visualização",
            ["Completo", "Essencial", "Trading", "Padrões"],
            help="Escolha quais colunas exibir"
        )
    
    with col_view2:
        show_favorites_only = st.checkbox(
            "⭐ Apenas Favoritas", 
            value=False,
            help="Mostra apenas moedas favoritas"
        )
    
    # Filtra resultados se necessário
    display_results = results
    if show_favorites_only:
        display_results = [r for r in results if r['symbol'] in st.session_state.favorite_coins]
    
    # Prepara dados para exibição
    results_data = []
    for result in display_results:
        # Destaque para moedas favoritas
        symbol_display = result['symbol'].replace("/USDT", "")
        if result['symbol'] in st.session_state.favorite_coins:
            symbol_display = f"⭐ {symbol_display}"
        
        # Formatação do sinal de saída
        if result.get('sinal_saida', False):
            nivel = result.get('nivel_saida', 'atencao')
            if nivel == 'urgente':
                saida_display = "🔴 URGENTE"
            elif nivel == 'atencao':
                saida_display = "🟡 ATENÇÃO"
            else:
                saida_display = "🟢 MANTER"
        else:
            saida_display = "🟢 MANTER"
        
        # Dados básicos sempre visíveis
        base_data = {
            "Símbolo": symbol_display,
            "Preço": f"${result['price']:.4f}",
            "RSI": f"{result['rsi']:.1f}",
            "Score": f"{result['score_entrada']:.0f}",
            "Sinal Entrada": result['sinal_entrada'],
            "Sinal Saída": saida_display
        }
        
        # Adiciona colunas conforme modo de visualização
        if view_mode in ["Completo", "Essencial"]:
            base_data.update({
                "Prob. Reversão": f"{result['prob_reversao']:.0f}%",
                "Motivo Saída": result.get('motivo_saida', 'N/A')
            })
        
        if view_mode in ["Completo", "Trading"]:
            base_data.update({
                "Stop Loss": f"${result.get('stop_loss', 0):.4f}" if result.get('stop_loss') else "N/A",
                "Take Profit 1R": f"${result.get('take_profit_1r', 0):.4f}" if result.get('take_profit_1r') else "N/A",
                "Take Profit 3R": f"${result.get('take_profit_3r', 0):.4f}" if result.get('take_profit_3r') else "N/A"
            })
        
        if view_mode in ["Completo", "Padrões"]:
            base_data.update({
                "Hammer": "🔨" if result.get('is_hammer', False) else "❌",
                "Doji": "🔄" if result.get('is_doji', False) else "❌",
                "Shooting Star": "⭐" if result.get('is_shooting_star', False) else "❌",
                "Falling Candle": "📉" if result.get('is_falling_candle', False) else "❌"
            })
        
        if view_mode == "Completo":
            base_data.update({
                "Volume Ratio": f"{result.get('volume_ratio', 0):.2f}" if result.get('volume_ratio') else "N/A",
                "Suporte": f"${result.get('support', 0):.4f}" if result.get('support') else "N/A",
                "Resistência": f"${result.get('resistance', 0):.4f}" if result.get('resistance') else "N/A"
            })
        
        results_data.append(base_data)
    
    # Exibe tabela
    if results_data:
        df_results = pd.DataFrame(results_data)
        
        # Ajusta largura das colunas
        st.dataframe(
            df_results,
            use_container_width=True,
            height=400 if len(results_data) > 10 else None,
            column_config={
                "Símbolo": st.column_config.TextColumn(width="small"),
                "Preço": st.column_config.TextColumn(width="small"),
                "RSI": st.column_config.TextColumn(width="small"),
                "Score": st.column_config.TextColumn(width="small"),
                "Sinal Entrada": st.column_config.TextColumn(width="medium"),
                "Sinal Saída": st.column_config.TextColumn(width="small"),
                "Stop Loss": st.column_config.TextColumn(width="small"),
                "Take Profit 1R": st.column_config.TextColumn(width="small"),
                "Take Profit 3R": st.column_config.TextColumn(width="small"),
                "Hammer": st.column_config.TextColumn(width="small"),
                "Doji": st.column_config.TextColumn(width="small"),
                "Shooting Star": st.column_config.TextColumn(width="small"),
                "Falling Candle": st.column_config.TextColumn(width="small"),
                "Volume Ratio": st.column_config.TextColumn(width="small"),
                "Suporte": st.column_config.TextColumn(width="small"),
                "Resistência": st.column_config.TextColumn(width="small")
            }
        )
    else:
        st.info("📭 Nenhum resultado para exibir com os filtros atuais")
    
    # Top 5 Oportunidades
    if results:
        st.markdown("### 🏆 Top 5 Oportunidades")
        
        # Filtra se apenas favoritas
        top_display_results = results
        if show_favorites_only:
            top_display_results = [r for r in results if r['symbol'] in st.session_state.favorite_coins]
        
        top_results = sorted(top_display_results, key=lambda x: x['score_entrada'], reverse=True)[:5]
        
        for i, result in enumerate(top_results, 1):
            with st.expander(f"{i}. {result['symbol']} - {result['sinal_entrada']} (Score: {result['score_entrada']:.0f})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📊 Indicadores Principais")
                    st.markdown(f"**RSI:** {result['rsi']:.1f}")
                    st.markdown(f"**Score Entrada:** {result['score_entrada']:.0f}/100")
                    st.markdown(f"**Prob. Reversão:** {result['prob_reversao']:.0f}%")
                    st.markdown(f"**Preço:** ${result['price']:.4f}")
                    
                    # Trading Information
                    st.markdown("### 💰 Trading Info")
                    if result.get('stop_loss'):
                        st.markdown(f"**Stop Loss:** ${result['stop_loss']:.4f}")
                    if result.get('take_profit_1r'):
                        st.markdown(f"**Take Profit 1R:** ${result['take_profit_1r']:.4f}")
                    if result.get('take_profit_3r'):
                        st.markdown(f"**Take Profit 3R:** ${result['take_profit_3r']:.4f}")
                    
                    # Risk/Reward
                    if result.get('stop_loss') and result.get('take_profit_1r'):
                        risk = abs(result['price'] - result['stop_loss'])
                        reward = abs(result['take_profit_1r'] - result['price'])
                        if risk > 0:
                            rr_ratio = reward / risk
                            st.markdown(f"**R/R Ratio:** 1:{rr_ratio:.2f}")
                
                with col2:
                    st.markdown("### 🎯 Status")
                    st.markdown(f"**Sinal Entrada:** {result['sinal_entrada']}")
                    if result.get('sinal_saida', False):
                        st.markdown(f"**Sinal Saída:** 🔴 {result.get('motivo_saida', 'Detectado')}")
                    else:
                        st.markdown("**Sinal Saída:** 🟢 MANTER")
                    
                    # Pattern Recognition
                    st.markdown("### 🕯️ Padrões Detectados")
                    patterns = []
                    if result.get('is_hammer', False):
                        patterns.append("🔨 Hammer")
                    if result.get('is_doji', False):
                        patterns.append("🔄 Doji")
                    if result.get('is_shooting_star', False):
                        patterns.append("⭐ Shooting Star")
                    if result.get('is_falling_candle', False):
                        patterns.append("📉 Falling Candle")
                    
                    if patterns:
                        for pattern in patterns:
                            st.markdown(f"**{pattern}**")
                    else:
                        st.markdown("**Nenhum padrão detectado**")
                    
                    # Support & Resistance
                    st.markdown("### 📈 Suporte & Resistência")
                    if result.get('support'):
                        st.markdown(f"**Suporte:** ${result['support']:.4f}")
                    if result.get('resistance'):
                        st.markdown(f"**Resistência:** ${result['resistance']:.4f}")
                    
                    # Volume Analysis
                    if result.get('volume_ratio'):
                        st.markdown("### 📊 Volume")
                        st.markdown(f"**Volume Ratio:** {result['volume_ratio']:.2f}x")
                        if result['volume_ratio'] > 1.5:
                            st.markdown("**🔥 Volume Elevado**")
                        elif result['volume_ratio'] > 1.2:
                            st.markdown("**📈 Volume Acima da Média**")
                        else:
                            st.markdown("**📉 Volume Normal**")
                    
                    # Gráfico
                    st.markdown("### 📈 Gráfico de Preços")
                    fig = create_strategy_chart(result)
                    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("🔄 Execute uma análise para ver os resultados")
    st.markdown("""
    ### 🚀 Como executar análise:
    1. Configure os parâmetros na sidebar
    2. Clique em **"⚡ ANALISAR ESTRATÉGIA 1H"**
    3. Aguarde o processamento
    4. Visualize os resultados aqui
    """)

# Main execution
if 'favorite_coins' not in st.session_state:
    st.session_state.favorite_coins = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
if 'last_analysis_time' not in st.session_state:
    st.session_state.last_analysis_time = None
if 'analysis_running' not in st.session_state:
    st.session_state.analysis_running = False
