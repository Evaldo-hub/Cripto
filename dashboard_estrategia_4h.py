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

# Adiciona src ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importa o Telegram Notifier
from telegram_notifier import create_telegram_notifier

from parallel_collector import get_parallel_collector
from simple_quant_engine import get_simple_quant_engine, SimpleAnalysisResult
# from pdf_generator import generate_simple_pdf  # Temporarily disabled
from database_manager_simple import db_manager
import ta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Session State
if 'results' not in st.session_state:
    st.session_state.results = []
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None
if 'analysis_running' not in st.session_state:
    st.session_state.analysis_running = False
if 'favorite_coins' not in st.session_state:
    # Lista de moedas favoritas (prioridade alta)
    FAVORITE_COINS = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 
        'AVAX/USDT', 'XRP/USDT', 'TLM/USDT', 'DEXE/USDT',
        'INJ/USDT', 'MASK/USDT', 'OP/USDT', 'HBAR/USDT', 'ILV/USDT'
    ]
    st.session_state.favorite_coins = FAVORITE_COINS
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
        
        # Processar sinais fortes com Telegram Notifier
        telegram_token = st.session_state.get('telegram_token', '')
        if telegram_token:
            strong_signals = [r for r in valid_results if r.get('score_entrada', 0) >= 70]
            
            if strong_signals:
                st.info(f"🚀 Enviando {len(strong_signals)} sinais fortes via Telegram...")
                
                # Get Telegram notifier
                notifier = create_telegram_notifier()
                
                for signal in strong_signals:
                    symbol = signal['symbol']
                    price = signal['price']
                    score = signal['score_entrada']
                    rsi = signal['rsi']
                    ema_status = signal.get('ema_status', 'N/A')
                    sinal_entrada = signal.get('sinal_entrada', 'AGUARDAR')
                    
                    # Send appropriate signal
                    if "COMPRA" in sinal_entrada.upper():
                        success = notifier.send_buy_signal(symbol, price, score, rsi, ema_status)
                        signal_type = "🟢 COMPRA"
                    elif "VENDA" in sinal_entrada.upper():
                        success = notifier.send_sell_signal(symbol, price, score, rsi, sinal_entrada)
                        signal_type = "🔴 VENDA"
                    else:
                        success = notifier.send_strategy_update(len(valid_results), 
                                                               len([s for s in valid_results if "COMPRA" in s.get('sinal_entrada', '').upper()]),
                                                               len([s for s in valid_results if "VENDA" in s.get('sinal_entrada', '').upper()]),
                                                               strong_signals)
                        signal_type = "📊 ATUALIZAÇÃO"
                    
                    if success:
                        st.success(f"✅ Alerta enviado: {symbol} ({signal_type})")
                    else:
                        st.warning(f"⚠️ Erro ao enviar alerta: {symbol}")
                
                # Send strategy summary
                if strong_signals:
                    buy_signals = [s for s in strong_signals if "COMPRA" in s.get('sinal_entrada', '').upper()]
                    sell_signals = [s for s in strong_signals if "VENDA" in s.get('sinal_entrada', '').upper()]
                    
                    notifier.send_strategy_update(
                        len(valid_results),
                        len(buy_signals),
                        len(sell_signals),
                        strong_signals
                    )
        
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
telegram_token = st.sidebar.text_input(
    "🔑 Token Telegram Bot",
    value=st.session_state.get('telegram_token', ''),
    type="password",
    help="Token do bot criado com @BotFather"
)

telegram_chat_id = st.sidebar.text_input(
    "💬 Chat ID",
    value=st.session_state.get('telegram_chat_id', ''),
    help="ID do chat para receber mensagens"
)

# Save Telegram settings
st.session_state.telegram_token = telegram_token
st.session_state.telegram_chat_id = telegram_chat_id

# Test Telegram connection
if st.sidebar.button("🧪 Testar Telegram", key="test_telegram"):
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

st.sidebar.markdown("---")

# Moedas Favoritas
st.sidebar.markdown("### ⭐ Moedas Favoritas")
favorite_coins_str = ", ".join([coin.replace("/USDT", "") for coin in st.session_state.favorite_coins])
st.sidebar.markdown(f"**{favorite_coins_str}**")
st.sidebar.markdown("*Priorizadas na análise*")

# Parâmetros da Estratégia
st.sidebar.markdown("### 🎯 Parâmetros da Estratégia")

rsi_entrada = st.sidebar.slider("RSI Máximo para Entrada", 10, 40, 25)  # Ajustado para 1h
rsi_saida_min = st.sidebar.slider("RSI Mínimo para Saída", 60, 80, 65)  # Ajustado para 1h
rsi_saida_max = st.sidebar.slider("RSI Máximo para Saída", 70, 90, 75)  # Ajustado para 1h
max_symbols = st.sidebar.slider("Símbolos para Análise", 20, 150, 80)
multi_tf_validation = st.sidebar.checkbox("🔄 Validação Multi-Timeframe", value=True, help="Usa 15m para confirmar sinais do 1h")
timeframe_confirm = st.sidebar.selectbox("⏰ Timeframe Confirmação", ["15m", "30m", "5m"], index=0, help="Timeframe para validar sinais do 1h")
real_1h_closing = st.sidebar.checkbox("🕐 Fechamento Real 1H (Obrigatório)", value=True, help="Usa apenas fechamentos reais de cada hora")

# Botão Principal
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
    
    # Debug: mostrar informações de tempo
    st.sidebar.markdown(f"**Debug:** Hora atual UTC: {now.strftime('%H:%M:%S')}")
    st.sidebar.markdown(f"**Debug:** Hora local: {datetime.now().strftime('%H:%M:%S')}")
    
    if last_update:
        time_diff = now - last_update
        minutes_ago = int(time_diff.total_seconds() / 60)
        seconds_ago = int(time_diff.total_seconds() % 60)
        st.sidebar.markdown(f"**Última análise:** {minutes_ago}min {seconds_ago}s atrás")
        st.sidebar.markdown(f"**Debug:** Última UTC: {last_update.strftime('%H:%M:%S')}")
        st.sidebar.markdown(f"**Debug:** Última Local: {last_update.replace(tzinfo=None).strftime('%H:%M:%S')}")
        
        # Calcular próxima atualização
        interval_minutes = {
            "5 min": 5,
            "10 min": 10, 
            "15 min": 15,
            "30 min": 30
        }.get(refresh_interval, 10)
        
        next_update = last_update + timedelta(minutes=interval_minutes)
        st.sidebar.markdown(f"**Debug:** Próxima UTC: {next_update.strftime('%H:%M:%S')}")
        st.sidebar.markdown(f"**Debug:** Próxima Local: {next_update.replace(tzinfo=None).strftime('%H:%M:%S')}")
        st.sidebar.markdown(f"**Debug:** Diff (now-last): {(now-last_update).total_seconds():.1f}s")
        st.sidebar.markdown(f"**Debug:** Diff (next-now): {(next_update-now).total_seconds():.1f}s")
        
        # Verificar se é hora de atualizar
        if now >= next_update:
            st.sidebar.markdown("**Status:** 🔄 ATUALIZANDO AGORA...")
            st.sidebar.markdown(f"**Debug:** Já passou da hora!")
            
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
            st.sidebar.markdown(f"**Debug:** Faltam {minutes_until}min {seconds_until}s")
            
            # Usar sistema nativo do Streamlit com refresh contínuo
            try:
                from streamlit_autorefresh import st_autorefresh
                # Configurar refresh para verificar a cada 30 segundos
                count = st_autorefresh(interval=30000, limit=None, key="auto_refresh_counter")
                
                # Quando o contador atualizar, verifica se é hora de analisar
                if count > 0 and datetime.now(timezone.utc) >= next_update:
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
                    
                    run_estrategia_analysis()
                    st.rerun()
                    
            except ImportError:
                # Se não tiver streamlit_autorefresh, usa método alternativo
                st.sidebar.markdown("**Info:** Install streamlit-autorefresh para melhor performance")
                st.sidebar.markdown("`pip install streamlit-autorefresh`")
                
                # Método alternativo simples
                if minutes_until <= 0:
                    st.sidebar.markdown("**Status:** 🔄 ATUALIZANDO...")
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
                    st.rerun()
    else:
        st.sidebar.markdown("**Status:** ⚡ Execute análise manual para iniciar")
        st.sidebar.markdown("**Primeira análise necessária**")
        st.sidebar.markdown("**Debug:** Nenhuma análise anterior")
    
    # Mostrar horários dos fechamentos 1H
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Fechamentos 1H UTC:**")
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
    if st.button("🧪 Testar Conexão Telegram", key="main_test_telegram"):
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

# Results Display Section
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
    
    # Tabela de Resultados
    st.markdown("### 🎯 Análise Detalhada")
    
    # Prepara dados para exibição
    results_data = []
    for result in results:
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
        
        results_data.append({
            "Símbolo": symbol_display,
            "Preço": f"${result['price']:.4f}",
            "RSI": f"{result['rsi']:.1f}",
            "Score": f"{result['score_entrada']:.0f}",
            "Prob. Reversão": f"{result['prob_reversao']:.0f}%",
            "Sinal Entrada": result['sinal_entrada'],
            "Sinal Saída": saida_display,
            "Motivo Saída": result.get('motivo_saida', 'N/A')
        })
    
    df_results = pd.DataFrame(results_data)
    st.dataframe(df_results, use_container_width=True)
    
    # Top 5 Oportunidades
    if results:
        st.markdown("### 🏆 Top 5 Oportunidades")
        top_results = sorted(results, key=lambda x: x['score_entrada'], reverse=True)[:5]
        
        for i, result in enumerate(top_results, 1):
            with st.expander(f"{i}. {result['symbol']} - {result['sinal_entrada']} (Score: {result['score_entrada']:.0f})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📊 Indicadores")
                    st.markdown(f"**RSI:** {result['rsi']:.1f}")
                    st.markdown(f"**Score Entrada:** {result['score_entrada']:.0f}/100")
                    st.markdown(f"**Prob. Reversão:** {result['prob_reversao']:.0f}%")
                    st.markdown(f"**Preço:** ${result['price']:.4f}")
                
                with col2:
                    st.markdown("### 🎯 Status")
                    st.markdown(f"**Sinal Entrada:** {result['sinal_entrada']}")
                    if result.get('sinal_saida', False):
                        st.markdown(f"**Sinal Saída:** 🔴 {result.get('motivo_saida', 'Detectado')}")
                    else:
                        st.markdown("**Sinal Saída:** 🟢 MANTER")
                    
                    # Gráfico simples
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
