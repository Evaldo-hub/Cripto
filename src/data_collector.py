"""
Data Collector Module
Responsável por coletar dados das exchanges de forma eficiente
"""
import ccxt
import pandas as pd
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataCollector:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance({'enableRateLimit': True}),
            'bybit': ccxt.bybit({'enableRateLimit': True}),
            'okx': ccxt.okx({'enableRateLimit': True})
        }
        self.supported_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
    def get_top_volume_symbols(self, exchange_name: str = 'binance', limit: int = 100) -> List[str]:
        """
        Obtém os símbolos com maior volume de negociação
        """
        try:
            exchange = self.exchanges[exchange_name]
            markets = exchange.load_markets()
            
            # Filtra apenas pares USDT com volume significativo
            usdt_pairs = [
                symbol for symbol, market in markets.items()
                if symbol.endswith('/USDT') and 
                market['active'] and 
                market['type'] == 'spot'
            ]
            
            # Ordena por volume (quando disponível)
            top_symbols = usdt_pairs[:limit]
            logger.info(f"Coletados {len(top_symbols)} símbolos de {exchange_name}")
            return top_symbols
            
        except Exception as e:
            logger.error(f"Erro ao obter símbolos de {exchange_name}: {e}")
            return []
    
    def fetch_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 200, 
                         exchange_name: str = 'binance') -> Optional[pd.DataFrame]:
        """
        Coleta dados OHLCV de um símbolo específico
        """
        try:
            exchange = self.exchanges[exchange_name]
            
            # Coleta os dados
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"Sem dados para {symbol}")
                return None
                
            # Converte para DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Adiciona metadados
            df.attrs['symbol'] = symbol
            df.attrs['exchange'] = exchange_name
            df.attrs['timeframe'] = timeframe
            df.attrs['last_update'] = datetime.now()
            
            logger.debug(f"Dados coletados para {symbol}: {len(df)} velas")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados de {symbol}: {e}")
            return None
    
    def collect_batch_data(self, symbols: List[str], timeframe: str = '1h', 
                           limit: int = 200, exchange_name: str = 'binance') -> Dict[str, pd.DataFrame]:
        """
        Coleta dados em lote para múltiplos símbolos
        """
        batch_data = {}
        failed_symbols = []
        
        logger.info(f"Iniciando coleta em lote: {len(symbols)} símbolos")
        
        for i, symbol in enumerate(symbols):
            try:
                df = self.fetch_ohlcv_data(symbol, timeframe, limit, exchange_name)
                if df is not None:
                    batch_data[symbol] = df
                else:
                    failed_symbols.append(symbol)
                
                # Rate limiting para não sobrecarregar a API
                if i % 10 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Falha ao processar {symbol}: {e}")
                failed_symbols.append(symbol)
        
        logger.info(f"Coleta concluída: {len(batch_data)} sucesso, {len(failed_symbols)} falhas")
        return batch_data
    
    def get_market_overview(self, exchange_name: str = 'binance') -> Dict:
        """
        Obtém visão geral do mercado
        """
        try:
            exchange = self.exchanges[exchange_name]
            
            # Tenta obter dados de mercado
            ticker = exchange.fetch_ticker('BTC/USDT')
            
            overview = {
                'exchange': exchange_name,
                'btc_price': ticker['last'] if ticker else None,
                'btc_change': ticker['percentage'] if ticker else None,
                'timestamp': datetime.now()
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Erro ao obter overview do mercado: {e}")
            return {'exchange': exchange_name, 'error': str(e)}

# Singleton para uso global
_collector_instance = None

def get_data_collector() -> MarketDataCollector:
    """Retorna instância singleton do coletor"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MarketDataCollector()
    return _collector_instance

if __name__ == "__main__":
    # Teste do coletor
    collector = get_data_collector()
    
    # Testa coleta de símbolos
    symbols = collector.get_top_volume_symbols('binance', 10)
    print(f"Símbolos coletados: {symbols}")
    
    # Testa coleta de dados
    if symbols:
        test_symbol = symbols[0]
        data = collector.fetch_ohlcv_data(test_symbol, '1h', 50)
        if data is not None:
            print(f"Dados para {test_symbol}:")
            print(data.tail())
