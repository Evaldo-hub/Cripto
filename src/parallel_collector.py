"""
Parallel Data Collector for 500+ Symbols
Coleta paralela de dados de múltiplas exchanges com alta performance
"""
import ccxt
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import queue
import json
from dataclasses import dataclass
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CollectionStats:
    """Estatísticas da coleta"""
    total_symbols: int
    successful: int
    failed: int
    start_time: datetime
    end_time: datetime
    avg_response_time: float

class ParallelDataCollector:
    def __init__(self, max_workers: int = 20, use_processes: bool = False):
        self.max_workers = max_workers
        self.use_processes = use_processes
        self.exchanges = {
            'binance': ccxt.binance({'enableRateLimit': True}),
            'bybit': ccxt.bybit({'enableRateLimit': True}),
            'okx': ccxt.okx({'enableRateLimit': True})
        }
        self.stats = CollectionStats(0, 0, 0, datetime.now(), datetime.now(), 0.0)
        self._lock = threading.Lock()
        
        # Cache de mercados para evitar reloads
        self._markets_cache = {}
        self._cache_lock = threading.Lock()
        
    @lru_cache(maxsize=1)
    def get_usdt_symbols(self, exchange_name: str, min_volume: float = 1000000) -> List[str]:
        """
        Obtém símbolos USDT com volume mínimo usando cache
        """
        try:
            with self._cache_lock:
                if exchange_name in self._markets_cache:
                    return self._markets_cache[exchange_name]
            
            exchange = self.exchanges[exchange_name]
            markets = exchange.load_markets()
            
            # Filtra pares USDT ativos
            usdt_symbols = []
            for symbol, market in markets.items():
                if (symbol.endswith('/USDT') and 
                    market['active'] and 
                    market['type'] == 'spot'):
                    
                    # Verifica volume se disponível (simplificado)
                    try:
                        volume = market.get('info', {}).get('quoteVolume', 0)
                        volume = float(volume) if volume else 0
                    except:
                        volume = 0
                    
                    # Se volume mínimo for 0, pega todos; senão filtra
                    if min_volume == 0 or volume >= min_volume:
                        usdt_symbols.append(symbol)
            
            # Ordena alfabeticamente e limita
            usdt_symbols.sort()
            
            with self._cache_lock:
                self._markets_cache[exchange_name] = usdt_symbols[:500]  # Limita a 500
            
            logger.info(f"Carregados {len(self._markets_cache[exchange_name])} símbolos de {exchange_name}")
            return self._markets_cache[exchange_name]
            
        except Exception as e:
            logger.error(f"Erro ao carregar símbolos de {exchange_name}: {e}")
            return []
    
    def fetch_single_symbol(self, args: Tuple[str, str, str, int]) -> Optional[pd.DataFrame]:
        """
        Coleta dados de um único símbolo
        args: (symbol, timeframe, limit, exchange_name)
        """
        symbol, timeframe, limit, exchange_name = args
        start_time = time.time()
        
        try:
            exchange = self.exchanges[exchange_name]
            
            # Coleta dados
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
            df.attrs['fetch_time'] = datetime.now()
            df.attrs['response_time'] = time.time() - start_time
            
            logger.debug(f"Dados coletados para {symbol}: {len(df)} velas em {time.time() - start_time:.2f}s")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao coletar {symbol}: {e}")
            return None
    
    def collect_parallel(self, symbols: List[str], timeframe: str = '1h', 
                         limit: int = 200, exchange_name: str = 'binance') -> Dict[str, pd.DataFrame]:
        """
        Coleta dados em paralelo para múltiplos símbolos
        """
        start_time = datetime.now()
        logger.info(f"Iniciando coleta paralela: {len(symbols)} símbolos, {self.max_workers} workers")
        
        # Prepara argumentos
        args_list = [(symbol, timeframe, limit, exchange_name) for symbol in symbols]
        
        results = {}
        response_times = []
        
        # Escolha do executor
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submete todas as tarefas
            future_to_symbol = {
                executor.submit(self.fetch_single_symbol, args): args[0] 
                for args in args_list
            }
            
            # Coleta resultados conforme completam
            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                try:
                    df = future.result(timeout=30)  # Timeout de 30s
                    if df is not None:
                        results[symbol] = df
                        response_times.append(df.attrs.get('response_time', 0))
                    
                    completed += 1
                    
                    # Progresso
                    if completed % 50 == 0 or completed == len(symbols):
                        progress = (completed / len(symbols)) * 100
                        logger.info(f"Progresso: {completed}/{len(symbols)} ({progress:.1f}%)")
                
                except Exception as e:
                    logger.error(f"Falha em {symbol}: {e}")
                    continue
        
        # Atualiza estatísticas
        end_time = datetime.now()
        avg_response_time = np.mean(response_times) if response_times else 0
        
        with self._lock:
            self.stats = CollectionStats(
                total_symbols=len(symbols),
                successful=len(results),
                failed=len(symbols) - len(results),
                start_time=start_time,
                end_time=end_time,
                avg_response_time=avg_response_time
            )
        
        duration = (end_time - start_time).total_seconds()
        success_rate = (len(results) / len(symbols)) * 100 if symbols else 0
        
        logger.info(f"Coleta concluída em {duration:.2f}s: {len(results)} sucesso, {success_rate:.1f}% taxa")
        return results
    
    def collect_all_exchanges(self, timeframe: str = '1h', limit: int = 200, 
                            symbols_per_exchange: int = 200) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Coleta dados de todas as exchanges em paralelo
        """
        all_results = {}
        
        for exchange_name in self.exchanges.keys():
            logger.info(f"Coletando dados de {exchange_name}")
            
            # Obtém símbolos da exchange
            symbols = self.get_usdt_symbols(exchange_name)[:symbols_per_exchange]
            
            if symbols:
                # Coleta em paralelo
                exchange_results = self.collect_parallel(symbols, timeframe, limit, exchange_name)
                all_results[exchange_name] = exchange_results
        
        return all_results
    
    def collect_batch_with_retry(self, symbols: List[str], timeframe: str = '1h', 
                                limit: int = 200, exchange_name: str = 'binance', 
                                max_retries: int = 2) -> Dict[str, pd.DataFrame]:
        """
        Coleta com retry para falhas
        """
        all_results = {}
        failed_symbols = symbols.copy()
        
        for attempt in range(max_retries + 1):
            if not failed_symbols:
                break
                
            logger.info(f"Tentativa {attempt + 1}/{max_retries + 1} para {len(failed_symbols)} símbolos")
            
            # Coleta apenas os símbolos que falharam
            batch_results = self.collect_parallel(failed_symbols, timeframe, limit, exchange_name)
            
            # Adiciona resultados bem-sucedidos
            for symbol, df in batch_results.items():
                all_results[symbol] = df
                failed_symbols.remove(symbol)
            
            # Pequena pausa entre tentativas
            if failed_symbols and attempt < max_retries:
                time.sleep(2)
        
        if failed_symbols:
            logger.warning(f"{len(failed_symbols)} símbolos falharam após {max_retries + 1} tentativas")
        
        return all_results
    
    def get_collection_stats(self) -> Dict:
        """Retorna estatísticas da última coleta"""
        with self._lock:
            if self.stats.total_symbols == 0:
                return {}
            
            duration = (self.stats.end_time - self.stats.start_time).total_seconds()
            success_rate = (self.stats.successful / self.stats.total_symbols) * 100
            
            return {
                'total_symbols': self.stats.total_symbols,
                'successful': self.stats.successful,
                'failed': self.stats.failed,
                'success_rate': round(success_rate, 2),
                'duration_seconds': round(duration, 2),
                'avg_response_time': round(self.stats.avg_response_time, 3),
                'symbols_per_second': round(self.stats.total_symbols / duration, 2) if duration > 0 else 0,
                'start_time': self.stats.start_time.isoformat(),
                'end_time': self.stats.end_time.isoformat()
            }
    
    def pre_cache_markets(self):
        """Pré-cache de mercados de todas as exchanges"""
        logger.info("Pré-cache de mercados...")
        
        for exchange_name in self.exchanges.keys():
            self.get_usdt_symbols(exchange_name)
        
        logger.info("Pré-cache concluído")

# Singleton global
_collector_instance = None

def get_parallel_collector(max_workers: int = 20, use_processes: bool = False) -> ParallelDataCollector:
    """Retorna instância singleton do coletor paralelo"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = ParallelDataCollector(max_workers, use_processes)
    return _collector_instance

if __name__ == "__main__":
    # Teste do coletor paralelo
    collector = get_parallel_collector(max_workers=15)
    
    # Pré-cache de mercados
    collector.pre_cache_markets()
    
    # Coleta de teste
    symbols = collector.get_usdt_symbols('binance')[:50]  # Teste com 50 símbolos
    
    if symbols:
        logger.info(f"Testando coleta com {len(symbols)} símbolos")
        
        start_time = time.time()
        results = collector.collect_parallel(symbols, '1h', 100, 'binance')
        duration = time.time() - start_time
        
        logger.info(f"Coleta teste concluída em {duration:.2f}s")
        logger.info(f"Estatísticas: {collector.get_collection_stats()}")
        
        # Mostra alguns resultados
        for i, (symbol, df) in enumerate(list(results.items())[:3]):
            logger.info(f"{symbol}: {len(df)} velas, preço atual: ${df['close'].iloc[-1]:.4f}")
