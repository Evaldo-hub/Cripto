"""
Render-specific Data Collector with Network Error Handling
Coletor com tratamento específico para limitações do Render
"""
import ccxt
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class RenderDataCollector:
    """Coletor otimizado para ambiente Render com tratamento de erros de rede"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configura retry strategy para Render
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configuração do CCXT para Render
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 30000,  # 30 segundos
            'rateLimit': 1200,  # Mais conservador
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        })
        
        # Cache simples para evitar requisições repetidas
        self.cache = {}
        self.cache_timeout = 60  # 1 minuto
        
    def check_connectivity(self) -> bool:
        """Verifica conectividade com APIs externas"""
        try:
            # Testa conectividade básica
            response = self.session.get('https://api.binance.com/api/v3/ping', timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Erro de conectividade: {e}")
            return False
    
    def get_fallback_symbols(self) -> List[str]:
        """Retorna símbolos fallback se API falhar"""
        # Símbolos mais populares e estáveis
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT',
            'XRP/USDT', 'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'MATIC/USDT',
            'LINK/USDT', 'UNI/USDT', 'LTC/USDT', 'ATOM/USDT', 'FIL/USDT'
        ]
    
    def fetch_with_fallback(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[pd.DataFrame]:
        """Busca dados com fallback para erros de rede"""
        cache_key = f"{symbol}_{timeframe}_{limit}"
        now = time.time()
        
        # Verifica cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if now - cached_time < self.cache_timeout:
                logger.debug(f"Usando cache para {symbol}")
                return cached_data
        
        try:
            # Tenta busca normal
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"Sem dados para {symbol}")
                return None
            
            # Converte para DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Adiciona metadados
            df.attrs['symbol'] = symbol
            df.attrs['exchange'] = 'binance'
            df.attrs['timeframe'] = timeframe
            df.attrs['fetch_time'] = datetime.now()
            
            # Cacheia resultado
            self.cache[cache_key] = (df, now)
            
            logger.info(f"Dados coletados para {symbol}: {len(df)} velas")
            return df
            
        except ccxt.NetworkError as e:
            logger.error(f"Erro de rede para {symbol}: {e}")
            return None
        except ccxt.RateLimitExceeded as e:
            logger.error(f"Rate limit para {symbol}: {e}")
            time.sleep(5)  # Espera antes de tentar novamente
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Erro da exchange para {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro genérico para {symbol}: {e}")
            return None
    
    def collect_batch_render(self, symbols: List[str], timeframe: str = '1h', limit: int = 100) -> Dict[str, pd.DataFrame]:
        """Coleta em lote otimizado para Render"""
        logger.info(f"Iniciando coleta Render: {len(symbols)} símbolos")
        
        if not self.check_connectivity():
            logger.warning("Sem conectividade, usando símbolos fallback")
            symbols = self.get_fallback_symbols()[:10]  # Limita para não sobrecarregar
        
        results = {}
        successful = 0
        failed = 0
        
        for symbol in symbols:
            try:
                df = self.fetch_with_fallback(symbol, timeframe, limit)
                if df is not None:
                    results[symbol] = df
                    successful += 1
                else:
                    failed += 1
                
                # Pequeno delay entre requisições para não sobrecarregar
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro fatal ao coletar {symbol}: {e}")
                failed += 1
        
        logger.info(f"Coleta concluída: {successful} sucesso, {failed} falhas")
        return results

# Função de compatibilidade
def get_render_collector():
    """Retorna instância do coletor Render"""
    return RenderDataCollector()
