"""
Cache Manager Module
Responsável por gerenciar cache de dados de mercado
"""
import pandas as pd
import pickle
import json
import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class MarketDataCache:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        self.cache_ttl = {
            '1m': timedelta(minutes=5),
            '5m': timedelta(minutes=15),
            '15m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        
    def _get_cache_path(self, symbol: str, timeframe: str, exchange: str = 'binance') -> Path:
        """Gera caminho do arquivo de cache"""
        safe_symbol = symbol.replace('/', '_')
        filename = f"{exchange}_{safe_symbol}_{timeframe}.pkl"
        return self.cache_dir / filename
    
    def _is_cache_valid(self, cache_path: Path, timeframe: str) -> bool:
        """Verifica se o cache ainda é válido"""
        if not cache_path.exists():
            return False
            
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        ttl = self.cache_ttl.get(timeframe, timedelta(hours=1))
        
        return datetime.now() - file_time < ttl
    
    def store_data(self, symbol: str, data: pd.DataFrame, timeframe: str, 
                   exchange: str = 'binance') -> None:
        """
        Armazena dados no cache (memória e disco)
        """
        try:
            # Cache em memória
            cache_key = f"{exchange}_{symbol}_{timeframe}"
            self.memory_cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now(),
                'symbol': symbol,
                'timeframe': timeframe,
                'exchange': exchange
            }
            
            # Cache em disco
            cache_path = self._get_cache_path(symbol, timeframe, exchange)
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'data': data,
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'exchange': exchange
                }, f)
            
            logger.debug(f"Dados cacheados para {symbol} ({timeframe})")
            
        except Exception as e:
            logger.error(f"Erro ao armazenar cache para {symbol}: {e}")
    
    def get_data(self, symbol: str, timeframe: str, exchange: str = 'binance') -> Optional[pd.DataFrame]:
        """
        Recupera dados do cache (memória ou disco)
        """
        try:
            # Primeiro tenta cache em memória
            cache_key = f"{exchange}_{symbol}_{timeframe}"
            if cache_key in self.memory_cache:
                cached_item = self.memory_cache[cache_key]
                ttl = self.cache_ttl.get(timeframe, timedelta(hours=1))
                
                if datetime.now() - cached_item['timestamp'] < ttl:
                    logger.debug(f"Dados recuperados do cache memória: {symbol}")
                    return cached_item['data'].copy()
                else:
                    # Remove cache expirado da memória
                    del self.memory_cache[cache_key]
            
            # Tenta cache em disco
            cache_path = self._get_cache_path(symbol, timeframe, exchange)
            if self._is_cache_valid(cache_path, timeframe):
                with open(cache_path, 'rb') as f:
                    cached_item = pickle.load(f)
                
                # Recarrega no cache de memória
                self.memory_cache[cache_key] = cached_item
                logger.debug(f"Dados recuperados do cache disco: {symbol}")
                return cached_item['data'].copy()
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao recuperar cache para {symbol}: {e}")
            return None
    
    def store_batch_data(self, batch_data: Dict[str, pd.DataFrame], timeframe: str, 
                        exchange: str = 'binance') -> None:
        """
        Armazena dados em lote no cache
        """
        for symbol, data in batch_data.items():
            self.store_data(symbol, data, timeframe, exchange)
    
    def get_all_cached_symbols(self, timeframe: str, exchange: str = 'binance') -> list:
        """
        Retorna todos os símbolos cacheados para um timeframe
        """
        symbols = []
        pattern = f"{exchange}_*_{timeframe}.pkl"
        
        for cache_file in self.cache_dir.glob(pattern):
            if self._is_cache_valid(cache_file, timeframe):
                symbol = cache_file.stem.replace(f"{exchange}_", "").replace(f"_{timeframe}", "").replace("_", "/")
                symbols.append(symbol)
        
        return symbols
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> None:
        """
        Limpa o cache
        """
        try:
            if symbol and timeframe:
                # Limpa cache específico
                cache_path = self._get_cache_path(symbol, timeframe)
                if cache_path.exists():
                    cache_path.unlink()
                
                cache_key = f"binance_{symbol}_{timeframe}"
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
            
            elif timeframe:
                # Limpa todos os caches de um timeframe
                pattern = f"*_{timeframe}.pkl"
                for cache_file in self.cache_dir.glob(pattern):
                    cache_file.unlink()
                
                # Limpa cache de memória
                keys_to_remove = [k for k in self.memory_cache.keys() if k.endswith(f"_{timeframe}")]
                for key in keys_to_remove:
                    del self.memory_cache[key]
            
            else:
                # Limpa tudo
                for cache_file in self.cache_dir.glob("*.pkl"):
                    cache_file.unlink()
                self.memory_cache.clear()
            
            logger.info("Cache limpo com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o cache
        """
        try:
            disk_files = list(self.cache_dir.glob("*.pkl"))
            disk_size = sum(f.stat().st_size for f in disk_files)
            
            return {
                'memory_cache_size': len(self.memory_cache),
                'disk_cache_files': len(disk_files),
                'disk_cache_size_mb': round(disk_size / (1024 * 1024), 2),
                'cache_directory': str(self.cache_dir)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do cache: {e}")
            return {}

# Singleton para uso global
_cache_instance = None

def get_cache_manager() -> MarketDataCache:
    """Retorna instância singleton do cache manager"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MarketDataCache()
    return _cache_instance

if __name__ == "__main__":
    # Teste do cache
    cache = get_cache_manager()
    
    # Cria dados de teste
    test_data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    # Testa armazenamento
    cache.store_data('BTC/USDT', test_data, '1h')
    
    # Testa recuperação
    retrieved = cache.get_data('BTC/USDT', '1h')
    print("Dados recuperados:", retrieved is not None)
    
    # Mostra informações do cache
    print("Informações do cache:", cache.get_cache_info())
