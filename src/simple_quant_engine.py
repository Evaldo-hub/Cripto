"""
Simple Quantitative Analysis Engine
Versão simplificada sem threading para testes
"""
import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimpleAnalysisResult:
    """Resultado da análise simplificada"""
    symbol: str
    price: float
    score: float
    signal: str
    confidence: float
    indicators: Dict
    detailed_scores: Dict
    timestamp: datetime
    processing_time: float
    signal_timestamp: datetime = None  # Data/hora do sinal

class SimpleQuantEngine:
    def __init__(self):
        """Inicializa motor quantitativo simplificado"""
        # Pesos dos indicadores
        self.indicator_weights = {
            'rsi': 0.20,
            'macd': 0.15,
            'volume': 0.15,
            'trend': 0.20,
            'volatility': 0.10,
            'momentum': 0.20
        }
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        try:
            if len(df) < 50:
                return df
            
            # Trend Indicators
            df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            
            # MACD
            df['macd'] = ta.trend.macd(df['close'])
            df['macd_signal'] = ta.trend.macd_signal(df['close'])
            df['macd_diff'] = ta.trend.macd_diff(df['close'])
            
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # Volume Indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()  # SMA simples do volume
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # ATR
            df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
            df['atr_pct'] = df['atr'] / df['close'] * 100
            
            # Momentum
            df['roc'] = ta.momentum.roc(df['close'], window=10)
            
            logger.debug(f"Indicadores calculados para {len(df)} velas")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            return df
    
    def calculate_rsi_score(self, rsi: float) -> float:
        """Calcula score baseado no RSI"""
        if pd.isna(rsi):
            return 50.0
        
        if rsi < 30:
            return 80.0
        elif rsi < 40:
            return 60.0
        elif rsi > 70:
            return 20.0
        elif rsi > 60:
            return 40.0
        else:
            return 50.0
    
    def calculate_macd_score(self, macd: float, macd_signal: float, macd_diff: float) -> float:
        """Calcula score baseado no MACD"""
        if pd.isna(macd) or pd.isna(macd_signal) or pd.isna(macd_diff):
            return 50.0
        
        if macd_diff > 0:
            if macd > 0:
                return 80.0
            else:
                return 60.0
        else:
            if macd < 0:
                return 20.0
            else:
                return 40.0
    
    def calculate_volume_score(self, volume_ratio: float, price_change: float) -> float:
        """Calcula score baseado no volume"""
        if pd.isna(volume_ratio):
            return 50.0
        
        if volume_ratio > 2.0:
            return 85.0 if price_change > 0 else 15.0
        elif volume_ratio > 1.5:
            return 70.0 if price_change > 0 else 30.0
        else:
            return 50.0
    
    def calculate_trend_score(self, price: float, ema_20: float, ema_50: float) -> float:
        """Calcula score baseado na tendência"""
        if pd.isna(ema_20) or pd.isna(ema_50):
            return 50.0
        
        score = 50.0
        
        if price > ema_20 > ema_50:
            score = 90.0
        elif price > ema_20:
            score = 75.0
        elif price > ema_20:
            score = 60.0
        elif price < ema_20 < ema_50:
            score = 10.0
        elif price < ema_20:
            score = 25.0
        elif price < ema_20:
            score = 40.0
        
        return score
    
    def calculate_volatility_score(self, atr_pct: float) -> float:
        """Calcula score baseado na volatilidade"""
        if pd.isna(atr_pct):
            return 50.0
        
        if atr_pct > 5.0:
            return 30.0
        elif atr_pct > 3.0:
            return 60.0
        elif atr_pct > 1.0:
            return 75.0
        else:
            return 40.0
    
    def calculate_momentum_score(self, roc: float) -> float:
        """Calcula score baseado no momentum"""
        if pd.isna(roc):
            return 50.0
        
        score = 50.0
        
        if roc > 5:
            score += 20
        elif roc > 2:
            score += 10
        elif roc < -5:
            score -= 20
        elif roc < -2:
            score -= 10
        
        return max(0, min(100, score))
    
    def calculate_overall_score(self, df: pd.DataFrame) -> Tuple[float, str, Dict]:
        """Calcula score geral e gera sinal"""
        if len(df) < 20:
            return 0.0, "DADOS_INSUFICIENTES", {}
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Calcula scores individuais
        rsi_score = self.calculate_rsi_score(last_row['rsi'])
        macd_score = self.calculate_macd_score(last_row['macd'], last_row['macd_signal'], last_row['macd_diff'])
        volume_score = self.calculate_volume_score(last_row['volume_ratio'], 
                                                 (last_row['close'] - prev_row['close']) / prev_row['close'] * 100)
        trend_score = self.calculate_trend_score(last_row['close'], last_row['ema_20'], last_row['ema_50'])
        volatility_score = self.calculate_volatility_score(last_row['atr_pct'])
        momentum_score = self.calculate_momentum_score(last_row['roc'])
        
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
            signal = "COMPRA_FORTE"
        elif overall_score >= 60:
            signal = "COMPRA"
        elif overall_score >= 45:
            signal = "NEUTRO"
        elif overall_score >= 30:
            signal = "VENDA"
        else:
            signal = "VENDA_FORTE"
        
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
    
    def analyze_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[SimpleAnalysisResult]:
        """Analisa um símbolo"""
        try:
            if len(df) < 50:
                logger.warning(f"Dados insuficientes para {symbol}: {len(df)} velas")
                return None
            
            # Calcula indicadores
            df_with_indicators = self.calculate_indicators(df)
            
            # Calcula score e sinal
            score, signal, analysis_data = self.calculate_overall_score(df_with_indicators)
            
            # Calcula confiança
            confidence = min(100, (len(df) / 200) * 100)
            
            # Cria resultado
            result = SimpleAnalysisResult(
                symbol=symbol,
                price=df_with_indicators.iloc[-1]['close'],
                score=score,
                signal=signal,
                confidence=confidence,
                indicators=analysis_data['indicators'],
                detailed_scores=analysis_data['scores'],
                timestamp=datetime.now(),
                processing_time=0.0,  # Simplificado
                signal_timestamp=datetime.now()  # Data/hora do sinal
            )
            
            logger.debug(f"Análise concluída para {symbol}: {signal} (Score: {score:.1f})")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao analisar {symbol}: {e}")
            return None
    
    def analyze_batch(self, symbols_data: Dict[str, pd.DataFrame]) -> List[SimpleAnalysisResult]:
        """Analisa múltiplos símbolos em sequência (simplificado)"""
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
    
    def generate_report(self, results: List[SimpleAnalysisResult]) -> Dict:
        """Gera relatório da análise"""
        if not results:
            return {}
        
        scores = [r.score for r in results]
        
        # Contagem de sinais
        signal_counts = {}
        for result in results:
            signal_counts[result.signal] = signal_counts.get(result.signal, 0) + 1
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_analyzed': len(results),
                'avg_score': round(np.mean(scores), 2),
                'max_score': round(np.max(scores), 2),
                'min_score': round(np.min(scores), 2),
                'signal_distribution': signal_counts
            },
            'top_opportunities': [
                {
                    'symbol': r.symbol,
                    'score': r.score,
                    'signal': r.signal,
                    'price': r.price,
                    'confidence': r.confidence,
                    'signal_timestamp': r.signal_timestamp.isoformat() if r.signal_timestamp else None
                } for r in results[:10]
            ]
        }
        
        return report

# Singleton global
_simple_engine_instance = None

def get_simple_quant_engine() -> SimpleQuantEngine:
    """Retorna instância singleton do motor simplificado"""
    global _simple_engine_instance
    if _simple_engine_instance is None:
        _simple_engine_instance = SimpleQuantEngine()
    return _simple_engine_instance

if __name__ == "__main__":
    # Teste do motor simplificado
    engine = get_simple_quant_engine()
    
    # Cria dados de teste
    test_data = {}
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    for symbol in symbols:
        df = pd.DataFrame({
            'close': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(200, 220, 100),
            'low': np.random.uniform(80, 100, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        })
        test_data[symbol] = df
    
    # Testa análise
    results = engine.analyze_batch(test_data)
    
    print(f"Análise teste concluída: {len(results)} resultados")
    for result in results:
        print(f"{result.symbol}: {result.signal} (Score: {result.score:.1f})")
