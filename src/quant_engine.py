"""
Quantitative Analysis Engine
Responsável por análise técnica e scoring de ativos
"""
import pandas as pd
import numpy as np
import ta
from typing import Dict, Tuple, Optional, List
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Resultado da análise quantitativa"""
    symbol: str
    price: float
    score: float
    signal: str
    confidence: float
    indicators: Dict
    signals: Dict
    timestamp: datetime

class QuantitativeEngine:
    def __init__(self):
        self.indicator_weights = {
            'rsi': 0.20,
            'macd': 0.15,
            'volume': 0.15,
            'trend': 0.20,
            'volatility': 0.10,
            'momentum': 0.20
        }
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos usando a biblioteca TA
        """
        try:
            # Trend Indicators
            df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
            
            # MACD
            df['macd'] = ta.trend.macd(df['close'])
            df['macd_signal'] = ta.trend.macd_signal(df['close'])
            df['macd_diff'] = ta.trend.macd_diff(df['close'])
            
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['rsi_sma'] = ta.trend.sma_indicator(df['rsi'], window=14)
            
            # Stochastic
            df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
            df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'])
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Volume Indicators
            df['volume_sma'] = ta.volume.volume_sma(df['close'], df['volume'], window=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
            
            # ADX (Trend Strength)
            df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
            
            # ATR (Volatility)
            df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
            df['atr_pct'] = df['atr'] / df['close'] * 100
            
            # Momentum
            df['roc'] = ta.momentum.roc(df['close'], window=10)
            df['williams_r'] = ta.momentum.williams_r(df['high'], df['low'], df['close'])
            
            # Ichimoku Cloud
            ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'])
            df['ichimoku_a'] = ichimoku.ichimoku_a()
            df['ichimoku_b'] = ichimoku.ichimoku_b()
            df['ichimoku_base'] = ichimoku.ichimoku_base_line()
            df['ichimoku_conversion'] = ichimoku.ichimoku_conversion_line()
            
            logger.debug(f"Indicadores calculados: {len(df.columns)} colunas")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            return df
    
    def calculate_rsi_score(self, rsi: float) -> float:
        """Calcula score baseado no RSI"""
        if pd.isna(rsi):
            return 0.0
        
        if rsi < 30:
            return 80  # Sobrevendido - oportunidade de compra
        elif rsi < 40:
            return 60  # Tendendo para sobrevendido
        elif rsi > 70:
            return 20  # Sobrecomprado - oportunidade de venda
        elif rsi > 60:
            return 40  # Tendendo para sobrecomprado
        else:
            return 50  # Neutro
    
    def calculate_macd_score(self, macd: float, macd_signal: float, macd_diff: float) -> float:
        """Calcula score baseado no MACD"""
        if pd.isna(macd) or pd.isna(macd_signal) or pd.isna(macd_diff):
            return 0.0
        
        # MACD cruzando acima da linha de sinal = bullish
        if macd_diff > 0:
            if macd > 0:
                return 80  # Forte tendência de alta
            else:
                return 60  # Reversão bullish
        else:
            if macd < 0:
                return 20  # Forte tendência de baixa
            else:
                return 40  # Reversão bearish
    
    def calculate_volume_score(self, volume_ratio: float, price_change: float) -> float:
        """Calcula score baseado no volume"""
        if pd.isna(volume_ratio):
            return 0.0
        
        # Volume alto com movimento de preço = forte sinal
        if volume_ratio > 2.0:
            if price_change > 0:
                return 85  # Compra forte com volume
            else:
                return 15  # Venda forte com volume
        elif volume_ratio > 1.5:
            if price_change > 0:
                return 70  # Compra moderada com volume
            else:
                return 30  # Venda moderada com volume
        else:
            return 50  # Volume normal
    
    def calculate_trend_score(self, price: float, ema_20: float, ema_50: float, ema_200: float) -> float:
        """Calcula score baseado na tendência"""
        if pd.isna(ema_20) or pd.isna(ema_50) or pd.isna(ema_200):
            return 0.0
        
        score = 50  # Base neutro
        
        # Preço vs EMAs
        if price > ema_20 > ema_50 > ema_200:
            score = 90  # Forte tendência de alta
        elif price > ema_20 > ema_50:
            score = 75  # Tendência de alta
        elif price > ema_20:
            score = 60  # Leve tendência de alta
        elif price < ema_20 < ema_50 < ema_200:
            score = 10  # Forte tendência de baixa
        elif price < ema_20 < ema_50:
            score = 25  # Tendência de baixa
        elif price < ema_20:
            score = 40  # Leve tendência de baixa
        
        return score
    
    def calculate_volatility_score(self, atr_pct: float, bb_position: float) -> float:
        """Calcula score baseado na volatilidade"""
        if pd.isna(atr_pct) or pd.isna(bb_position):
            return 0.0
        
        # Volatilidade muito alta pode indicar oportunidade ou risco
        if atr_pct > 5.0:
            return 30  # Muito volátil - arriscado
        elif atr_pct > 3.0:
            return 60  # Volatilidade moderada - oportunidade
        elif atr_pct > 1.0:
            return 75  # Volatilidade ideal
        else:
            return 40  # Baixa volatilidade - menos oportunidade
    
    def calculate_momentum_score(self, roc: float, williams_r: float) -> float:
        """Calcula score baseado no momentum"""
        if pd.isna(roc) or pd.isna(williams_r):
            return 0.0
        
        score = 50
        
        # Rate of Change
        if roc > 5:
            score += 20
        elif roc > 2:
            score += 10
        elif roc < -5:
            score -= 20
        elif roc < -2:
            score -= 10
        
        # Williams %R
        if williams_r < -80:
            score += 15  # Sobrevendido
        elif williams_r < -50:
            score += 5
        elif williams_r > -20:
            score -= 15  # Sobrecomprado
        elif williams_r > -50:
            score -= 5
        
        return max(0, min(100, score))
    
    def calculate_overall_score(self, df: pd.DataFrame) -> Tuple[float, str, Dict]:
        """
        Calcula score geral e gera sinal
        """
        if len(df) < 20:
            return 0.0, "NEUTRO", {}
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Calcula scores individuais
        rsi_score = self.calculate_rsi_score(last_row['rsi'])
        macd_score = self.calculate_macd_score(last_row['macd'], last_row['macd_signal'], last_row['macd_diff'])
        volume_score = self.calculate_volume_score(last_row['volume_ratio'], 
                                                 (last_row['close'] - prev_row['close']) / prev_row['close'] * 100)
        trend_score = self.calculate_trend_score(last_row['close'], last_row['ema_20'], 
                                                last_row['ema_50'], last_row['ema_200'])
        volatility_score = self.calculate_volatility_score(last_row['atr_pct'], last_row['bb_position'])
        momentum_score = self.calculate_momentum_score(last_row['roc'], last_row['williams_r'])
        
        # Calcula score ponderado
        overall_score = (
            rsi_score * self.indicator_weights['rsi'] +
            macd_score * self.indicator_weights['macd'] +
            volume_score * self.indicator_weights['volume'] +
            trend_score * self.indicator_weights['trend'] +
            volatility_score * self.indicator_weights['volatility'] +
            momentum_score * self.indicator_weights['momentum']
        )
        
        # Gera sinal
        if overall_score >= 75:
            signal = "COMPRA FORTE"
        elif overall_score >= 60:
            signal = "COMPRA"
        elif overall_score >= 45:
            signal = "NEUTRO"
        elif overall_score >= 30:
            signal = "VENDA"
        else:
            signal = "VENDA FORTE"
        
        # Compila indicadores
        indicators = {
            'rsi': round(last_row['rsi'], 2) if not pd.isna(last_row['rsi']) else None,
            'macd': round(last_row['macd'], 6) if not pd.isna(last_row['macd']) else None,
            'volume_ratio': round(last_row['volume_ratio'], 2) if not pd.isna(last_row['volume_ratio']) else None,
            'atr_pct': round(last_row['atr_pct'], 2) if not pd.isna(last_row['atr_pct']) else None,
            'roc': round(last_row['roc'], 2) if not pd.isna(last_row['roc']) else None
        }
        
        # Compila scores detalhados
        detailed_scores = {
            'rsi_score': rsi_score,
            'macd_score': macd_score,
            'volume_score': volume_score,
            'trend_score': trend_score,
            'volatility_score': volatility_score,
            'momentum_score': momentum_score,
            'overall_score': round(overall_score, 2)
        }
        
        return overall_score, signal, {'indicators': indicators, 'scores': detailed_scores}
    
    def analyze_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[AnalysisResult]:
        """
        Analisa um símbolo completo
        """
        try:
            if len(df) < 50:
                logger.warning(f"Dados insuficientes para {symbol}: {len(df)} velas")
                return None
            
            # Calcula indicadores
            df_with_indicators = self.calculate_technical_indicators(df)
            
            # Calcula score e sinal
            score, signal, analysis_data = self.calculate_overall_score(df_with_indicators)
            
            # Calcula confiança baseada na quantidade e qualidade dos dados
            confidence = min(100, (len(df) / 200) * 100)
            
            # Cria resultado
            result = AnalysisResult(
                symbol=symbol,
                price=df_with_indicators.iloc[-1]['close'],
                score=score,
                signal=signal,
                confidence=confidence,
                indicators=analysis_data['indicators'],
                signals=analysis_data['scores'],
                timestamp=datetime.now()
            )
            
            logger.debug(f"Análise concluída para {symbol}: {signal} (Score: {score:.1f})")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao analisar {symbol}: {e}")
            return None
    
    def analyze_batch(self, symbols_data: Dict[str, pd.DataFrame]) -> List[AnalysisResult]:
        """
        Analisa múltiplos símbolos em lote
        """
        results = []
        
        for symbol, df in symbols_data.items():
            try:
                result = self.analyze_symbol(symbol, df)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Falha na análise de {symbol}: {e}")
                continue
        
        # Ordena por score
        results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Análise em lote concluída: {len(results)} símbolos analisados")
        return results

# Singleton para uso global
_quant_engine_instance = None

def get_quant_engine() -> QuantitativeEngine:
    """Retorna instância singleton do motor quantitativo"""
    global _quant_engine_instance
    if _quant_engine_instance is None:
        _quant_engine_instance = QuantitativeEngine()
    return _quant_engine_instance

if __name__ == "__main__":
    # Teste do motor quantitativo
    engine = get_quant_engine()
    
    # Cria dados de teste
    test_data = pd.DataFrame({
        'close': np.random.uniform(100, 110, 100),
        'high': np.random.uniform(110, 120, 100),
        'low': np.random.uniform(90, 100, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    # Testa análise
    result = engine.analyze_symbol('TEST/USDT', test_data)
    if result:
        print(f"Resultado para {result.symbol}:")
        print(f"Sinal: {result.signal}")
        print(f"Score: {result.score:.2f}")
        print(f"Preço: {result.price:.2f}")
