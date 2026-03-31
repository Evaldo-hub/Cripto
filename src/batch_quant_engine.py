"""
Batch Quantitative Analysis Engine
Motor quantitativo otimizado para processamento em lote de 500+ símbolos
"""
import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import lru_cache
import time
import gc
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BatchAnalysisResult:
    """Resultado da análise em lote"""
    symbol: str
    price: float
    score: float
    signal: str
    confidence: float
    indicators: Dict
    detailed_scores: Dict
    timestamp: datetime
    processing_time: float

class BatchQuantEngine:
    def __init__(self, max_workers: int = None, use_processes: bool = False):
        """
        Inicializa motor quantitativo para processamento em lote
        """
        self.max_workers = max_workers or min(32, (mp.cpu_count() or 1) + 4)
        self.use_processes = use_processes
        
        # Pesos dos indicadores (otimizados para volume)
        self.indicator_weights = {
            'rsi': 0.18,
            'macd': 0.14,
            'volume': 0.16,
            'trend': 0.22,
            'volatility': 0.12,
            'momentum': 0.18
        }
        
        # Cache de cálculos para evitar repetição
        self._indicator_cache = {}
        self._cache_lock = mp.Lock() if use_processes else threading.Lock()
        
    @lru_cache(maxsize=1000)
    def _calculate_rsi_series(self, prices: Tuple, window: int = 14) -> Tuple:
        """Calcula RSI com cache para séries repetidas"""
        try:
            series = pd.Series(prices)
            rsi = ta.momentum.rsi(series, window=window)
            return tuple(rsi.fillna(50).values)
        except:
            return tuple([50] * len(prices))
    
    def calculate_indicators_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos otimizado para batch processing
        """
        try:
            # Verifica se DataFrame tem dados suficientes
            if len(df) < 50:
                return df
            
            # Trend Indicators (batch operations)
            df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
            df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
            
            # MACD (evita recálculo desnecessário)
            macd_line = ta.trend.macd(df['close'])
            df['macd'] = macd_line
            df['macd_signal'] = ta.trend.macd_signal(df['close'])
            df['macd_diff'] = ta.trend.macd_diff(df['close'])
            
            # RSI (usando cache quando possível)
            close_tuple = tuple(df['close'].values)
            rsi_values = self._calculate_rsi_series(close_tuple)
            df['rsi'] = list(rsi_values)
            df['rsi_sma'] = ta.trend.sma_indicator(df['rsi'], window=14)
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            
            # Volume Indicators (batch)
            df['volume_sma'] = ta.volume.volume_sma(df['close'], df['volume'], window=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
            
            # ADX (trend strength)
            df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
            
            # ATR (volatility)
            df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
            df['atr_pct'] = df['atr'] / df['close'] * 100
            
            # Momentum (batch)
            df['roc'] = ta.momentum.roc(df['close'], window=10)
            df['williams_r'] = ta.momentum.williams_r(df['high'], df['low'], df['close'])
            
            # Ichimoku Cloud
            ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'])
            df['ichimoku_a'] = ichimoku.ichimoku_a()
            df['ichimoku_b'] = ichimoku.ichimoku_b()
            df['ichimoku_base'] = ichimoku.ichimoku_base_line()
            df['ichimoku_conversion'] = ichimoku.ichimoku_conversion_line()
            
            # Posições relativas (calculadas uma vez)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['price_vs_ema20'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
            df['price_vs_ema50'] = (df['close'] - df['ema_50']) / df['ema_50'] * 100
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            return df
    
    def calculate_scores_vectorized(self, df: pd.DataFrame) -> Tuple[float, str, Dict]:
        """
        Calcula scores usando operações vetorizadas para performance
        """
        try:
            if len(df) < 20:
                return 0.0, "DADOS_INSUFICIENTES", {}
            
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Arrays vetorizados para cálculo rápido
            rsi_values = df['rsi'].values
            macd_diff_values = df['macd_diff'].values
            volume_ratio_values = df['volume_ratio'].values
            
            # RSI Score (vetorizado)
            rsi_score = np.where(
                rsi_values[-1] < 30, 80,
                np.where(rsi_values[-1] < 40, 60,
                np.where(rsi_values[-1] > 70, 20,
                np.where(rsi_values[-1] > 60, 40, 50)))
            ).item()
            
            # MACD Score (vetorizado)
            macd_score = 50  # Base
            if macd_diff_values[-1] > 0:
                if last_row['macd'] > 0:
                    macd_score = 80
                else:
                    macd_score = 60
            else:
                if last_row['macd'] < 0:
                    macd_score = 20
                else:
                    macd_score = 40
            
            # Volume Score (vetorizado)
            price_change = (last_row['close'] - prev_row['close']) / prev_row['close'] * 100
            volume_score = 50
            if volume_ratio_values[-1] > 2.0:
                volume_score = 85 if price_change > 0 else 15
            elif volume_ratio_values[-1] > 1.5:
                volume_score = 70 if price_change > 0 else 30
            
            # Trend Score (otimizado)
            trend_score = 50
            if (not pd.isna(last_row['ema_20']) and not pd.isna(last_row['ema_50']) and 
                not pd.isna(last_row['ema_200'])):
                
                if (last_row['close'] > last_row['ema_20'] > last_row['ema_50'] > last_row['ema_200']):
                    trend_score = 90
                elif last_row['close'] > last_row['ema_20'] > last_row['ema_50']:
                    trend_score = 75
                elif last_row['close'] > last_row['ema_20']:
                    trend_score = 60
                elif last_row['close'] < last_row['ema_20'] < last_row['ema_50'] < last_row['ema_200']:
                    trend_score = 10
                elif last_row['close'] < last_row['ema_20'] < last_row['ema_50']:
                    trend_score = 25
                elif last_row['close'] < last_row['ema_20']:
                    trend_score = 40
            
            # Volatility Score
            volatility_score = 50
            if not pd.isna(last_row['atr_pct']):
                if last_row['atr_pct'] > 5.0:
                    volatility_score = 30
                elif last_row['atr_pct'] > 3.0:
                    volatility_score = 60
                elif last_row['atr_pct'] > 1.0:
                    volatility_score = 75
                else:
                    volatility_score = 40
            
            # Momentum Score (vetorizado)
            momentum_score = 50
            if not pd.isna(last_row['roc']) and not pd.isna(last_row['williams_r']):
                roc_contrib = 0
                if last_row['roc'] > 5:
                    roc_contrib = 20
                elif last_row['roc'] > 2:
                    roc_contrib = 10
                elif last_row['roc'] < -5:
                    roc_contrib = -20
                elif last_row['roc'] < -2:
                    roc_contrib = -10
                
                williams_contrib = 0
                if last_row['williams_r'] < -80:
                    williams_contrib = 15
                elif last_row['williams_r'] < -50:
                    williams_contrib = 5
                elif last_row['williams_r'] > -20:
                    williams_contrib = -15
                elif last_row['williams_r'] > -50:
                    williams_contrib = -5
                
                momentum_score = max(0, min(100, 50 + roc_contrib + williams_contrib))
            
            # Score geral ponderado
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
            
            # Compila resultados
            indicators = {
                'rsi': round(last_row['rsi'], 2) if not pd.isna(last_row['rsi']) else None,
                'macd': round(last_row['macd'], 6) if not pd.isna(last_row['macd']) else None,
                'volume_ratio': round(last_row['volume_ratio'], 2) if not pd.isna(last_row['volume_ratio']) else None,
                'atr_pct': round(last_row['atr_pct'], 2) if not pd.isna(last_row['atr_pct']) else None,
                'roc': round(last_row['roc'], 2) if not pd.isna(last_row['roc']) else None,
                'adx': round(last_row['adx'], 2) if not pd.isna(last_row['adx']) else None
            }
            
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
            
        except Exception as e:
            logger.error(f"Erro ao calcular scores: {e}")
            return 0.0, "ERRO", {}
    
    def analyze_single_symbol(self, args: Tuple[str, pd.DataFrame]) -> Optional[BatchAnalysisResult]:
        """
        Analisa um único símbolo (para processamento paralelo)
        """
        symbol, df = args
        start_time = time.time()
        
        try:
            # Verifica dados mínimos
            if len(df) < 50:
                return None
            
            # Calcula indicadores
            df_with_indicators = self.calculate_indicators_batch(df)
            
            # Calcula scores
            score, signal, analysis_data = self.calculate_scores_vectorized(df_with_indicators)
            
            # Calcula confiança
            confidence = min(100, (len(df) / 200) * 100)
            
            processing_time = time.time() - start_time
            
            result = BatchAnalysisResult(
                symbol=symbol,
                price=df_with_indicators.iloc[-1]['close'],
                score=score,
                signal=signal,
                confidence=confidence,
                indicators=analysis_data['indicators'],
                detailed_scores=analysis_data['scores'],
                timestamp=datetime.now(),
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao analisar {symbol}: {e}")
            return None
    
    def analyze_batch_parallel(self, symbols_data: Dict[str, pd.DataFrame]) -> List[BatchAnalysisResult]:
        """
        Analisa múltiplos símbolos em paralelo com performance otimizada
        """
        start_time = datetime.now()
        logger.info(f"Iniciando análise em lote: {len(symbols_data)} símbolos, {self.max_workers} workers")
        
        # Prepara argumentos
        args_list = [(symbol, df) for symbol, df in symbols_data.items()]
        
        results = []
        processing_times = []
        
        # Escolha do executor
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Processa em lote
            future_to_symbol = {
                executor.submit(self.analyze_single_symbol, args): args[0]
                for args in args_list
            }
            
            # Coleta resultados
            completed = 0
            for future in future_to_symbol:
                try:
                    result = future.result(timeout=10)  # Timeout de 10s por símbolo
                    if result:
                        results.append(result)
                        processing_times.append(result.processing_time)
                    
                    completed += 1
                    
                    # Progresso
                    if completed % 100 == 0 or completed == len(symbols_data):
                        progress = (completed / len(symbols_data)) * 100
                        logger.info(f"Análise: {completed}/{len(symbols_data)} ({progress:.1f}%)")
                
                except Exception as e:
                    symbol = future_to_symbol[future]
                    logger.error(f"Falha na análise de {symbol}: {e}")
                    continue
        
        # Ordena por score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Estatísticas
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        avg_processing_time = np.mean(processing_times) if processing_times else 0
        
        logger.info(f"Análise concluída em {duration:.2f}s: {len(results)} resultados")
        logger.info(f"Tempo médio por símbolo: {avg_processing_time:.3f}s")
        logger.info(f"Throughput: {len(symbols_data)/duration:.1f} símbolos/s")
        
        # Força garbage collection
        gc.collect()
        
        return results
    
    def get_top_opportunities(self, results: List[BatchAnalysisResult], 
                            min_score: float = 60, limit: int = 50) -> List[BatchAnalysisResult]:
        """
        Filtra e retorna as melhores oportunidades
        """
        # Filtra por score mínimo
        filtered = [r for r in results if r.score >= min_score]
        
        # Retorna top N
        return filtered[:limit]
    
    def generate_batch_report(self, results: List[BatchAnalysisResult]) -> Dict:
        """
        Gera relatório da análise em lote
        """
        if not results:
            return {}
        
        # Estatísticas gerais
        scores = [r.score for r in results]
        processing_times = [r.processing_time for r in results]
        
        # Contagem de sinais
        signal_counts = {}
        for result in results:
            signal_counts[result.signal] = signal_counts.get(result.signal, 0) + 1
        
        # Top oportunidades
        top_10 = results[:10]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_analyzed': len(results),
                'avg_score': round(np.mean(scores), 2),
                'max_score': round(np.max(scores), 2),
                'min_score': round(np.min(scores), 2),
                'avg_processing_time': round(np.mean(processing_times), 3),
                'total_processing_time': round(np.sum(processing_times), 2),
                'signal_distribution': signal_counts
            },
            'top_opportunities': [
                {
                    'symbol': r.symbol,
                    'score': r.score,
                    'signal': r.signal,
                    'price': r.price,
                    'confidence': r.confidence
                } for r in top_10
            ],
            'performance': {
                'symbols_per_second': round(len(results) / np.sum(processing_times), 2) if processing_times else 0,
                'avg_indicators_time': round(np.mean(processing_times), 3)
            }
        }
        
        return report
    
    def optimize_for_batch_size(self, target_symbols: int) -> Dict:
        """
        Otimiza configurações para tamanho de lote específico
        """
        # Estima recursos necessários
        estimated_time_per_symbol = 0.05  # 50ms por símbolo
        total_estimated_time = target_symbols * estimated_time_per_symbol
        
        # Ajusta número de workers
        optimal_workers = min(self.max_workers, target_symbols // 10, 32)
        
        # Recomendações
        recommendations = {
            'optimal_workers': optimal_workers,
            'estimated_time_seconds': total_estimated_time,
            'memory_requirement_mb': target_symbols * 2,  # ~2MB por símbolo
            'use_processes': target_symbols > 100,  # Processos para lotes grandes
            'batch_size': min(50, target_symbols // optimal_workers)
        }
        
        return recommendations

# Singleton global
_batch_engine_instance = None

def get_batch_quant_engine(max_workers: int = None, use_processes: bool = False) -> BatchQuantEngine:
    """Retorna instância singleton do motor quantitativo em lote"""
    global _batch_engine_instance
    if _batch_engine_instance is None:
        _batch_engine_instance = BatchQuantEngine(max_workers, use_processes)
    return _batch_engine_instance

if __name__ == "__main__":
    # Teste do motor em lote
    engine = get_batch_quant_engine(max_workers=8)
    
    # Cria dados de teste
    test_data = {}
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'INJ/USDT']
    
    for symbol in symbols:
        df = pd.DataFrame({
            'close': np.random.uniform(100, 200, 200),
            'high': np.random.uniform(200, 220, 200),
            'low': np.random.uniform(80, 100, 200),
            'volume': np.random.uniform(1000, 5000, 200)
        })
        test_data[symbol] = df
    
    # Testa análise em lote
    start_time = time.time()
    results = engine.analyze_batch_parallel(test_data)
    duration = time.time() - start_time
    
    print(f"Análise em lote concluída em {duration:.2f}s")
    print(f"Resultados: {len(results)}")
    
    # Mostra top 3
    for i, result in enumerate(results[:3]):
        print(f"{i+1}. {result.symbol}: {result.signal} (Score: {result.score:.1f})")
    
    # Gera relatório
    report = engine.generate_batch_report(results)
    print(f"Relatório: {report}")
