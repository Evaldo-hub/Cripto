"""
High Performance Cache System
Cache otimizado para 500+ símbolos com Redis e memória
"""
import pandas as pd
import numpy as np
import pickle
import json
import redis
import threading
import time
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import gc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """Métricas de performance do cache"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    memory_usage_mb: float = 0.0
    last_cleanup: datetime = None

class HighPerformanceCache:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 redis_db: int = 0, memory_limit_mb: int = 1024, 
                 enable_redis: bool = False):
        """
        Inicializa cache de alta performance
        """
        self.enable_redis = enable_redis
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Cache em memória com LRU
        self.memory_cache = {}
        self.access_times = {}
        self.cache_sizes = {}
        
        # Redis client
        self.redis_client = None
        if enable_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, 
                    port=redis_port, 
                    db=redis_db,
                    decode_responses=False,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Testa conexão
                self.redis_client.ping()
                logger.info("Redis conectado com sucesso")
            except Exception as e:
                logger.warning(f"Redis não disponível: {e}. Usando apenas cache em memória.")
                self.enable_redis = False
        
        # TTL por timeframe
        self.cache_ttl = {
            '1m': timedelta(minutes=2),
            '5m': timedelta(minutes=8),
            '15m': timedelta(minutes=20),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        
        # Métricas
        self.metrics = CacheMetrics()
        self.metrics_lock = threading.Lock()
        
        # Background cleanup
        self.cleanup_interval = 300  # 5 minutos
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # Inicia cleanup automático
        self._start_cleanup_thread()
    
    def _generate_key(self, symbol: str, timeframe: str, exchange: str = 'binance') -> str:
        """Gera chave única para cache"""
        key_str = f"{exchange}:{symbol}:{timeframe}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _estimate_size(self, obj: Any) -> int:
        """Estima tamanho em bytes de um objeto"""
        try:
            if isinstance(obj, pd.DataFrame):
                return obj.memory_usage(deep=True).sum()
            else:
                return len(pickle.dumps(obj))
        except:
            return 1024  # Estimativa padrão
    
    def _cleanup_memory_cache(self):
        """Limpa cache em memória baseado em LRU e limite de memória"""
        try:
            current_memory = sum(self.cache_sizes.values())
            
            # Remove itens expirados
            now = datetime.now()
            expired_keys = []
            
            for key, (data, timestamp, ttl) in self.memory_cache.items():
                if now - timestamp > ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_from_memory(key)
                with self.metrics_lock:
                    self.metrics.evictions += 1
            
            # Se ainda acima do limite, remove por LRU
            if current_memory > self.memory_limit_bytes:
                # Ordena por tempo de acesso
                sorted_keys = sorted(
                    self.access_times.items(), 
                    key=lambda x: x[1]
                )
                
                # Remove até ficar abaixo do limite
                for key, _ in sorted_keys:
                    if current_memory <= self.memory_limit_bytes * 0.8:  # 80% do limite
                        break
                    self._remove_from_memory(key)
                    current_memory -= self.cache_sizes.get(key, 0)
                    with self.metrics_lock:
                        self.metrics.evictions += 1
            
            # Força garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Erro no cleanup de memória: {e}")
    
    def _remove_from_memory(self, key: str):
        """Remove item do cache em memória"""
        if key in self.memory_cache:
            del self.memory_cache[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.cache_sizes:
            del self.cache_sizes[key]
    
    def _cleanup_thread_func(self):
        """Função do thread de cleanup"""
        while not self._stop_cleanup.wait(self.cleanup_interval):
            self._cleanup_memory_cache()
            with self.metrics_lock:
                self.metrics.last_cleanup = datetime.now()
    
    def _start_cleanup_thread(self):
        """Inicia thread de cleanup"""
        self._cleanup_thread = threading.Thread(target=self._cleanup_thread_func, daemon=True)
        self._cleanup_thread.start()
    
    def store_data(self, symbol: str, data: pd.DataFrame, timeframe: str, 
                   exchange: str = 'binance', force: bool = False):
        """
        Armazena dados no cache (memória e Redis)
        """
        try:
            key = self._generate_key(symbol, timeframe, exchange)
            ttl = self.cache_ttl.get(timeframe, timedelta(hours=1))
            
            # Metadados
            metadata = {
                'symbol': symbol,
                'exchange': exchange,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'data_shape': data.shape,
                'columns': list(data.columns)
            }
            
            # Prepara dados para armazenamento
            cache_data = {
                'data': data,
                'metadata': metadata,
                'cache_time': datetime.now()
            }
            
            # Cache em memória
            if force or key not in self.memory_cache:
                data_size = self._estimate_size(data)
                
                # Verifica limite de memória
                current_memory = sum(self.cache_sizes.values())
                if current_memory + data_size > self.memory_limit_bytes:
                    self._cleanup_memory_cache()
                
                # Armazena em memória
                self.memory_cache[key] = (cache_data, datetime.now(), ttl)
                self.access_times[key] = time.time()
                self.cache_sizes[key] = data_size
                
                with self.metrics_lock:
                    self.metrics.sets += 1
            
            # Redis (se disponível)
            if self.enable_redis:
                try:
                    # Serializa dados
                    serialized = pickle.dumps(cache_data)
                    
                    # Armazena no Redis com TTL
                    self.redis_client.setex(
                        key, 
                        int(ttl.total_seconds()), 
                        serialized
                    )
                    
                    # Armazena metadados separadamente para consulta rápida
                    metadata_key = f"meta:{key}"
                    self.redis_client.setex(
                        metadata_key,
                        int(ttl.total_seconds()),
                        json.dumps(metadata)
                    )
                    
                except Exception as e:
                    logger.warning(f"Erro ao armazenar no Redis: {e}")
            
            logger.debug(f"Dados cacheados para {symbol} ({timeframe})")
            
        except Exception as e:
            logger.error(f"Erro ao armazenar cache para {symbol}: {e}")
    
    def get_data(self, symbol: str, timeframe: str, exchange: str = 'binance') -> Optional[pd.DataFrame]:
        """
        Recupera dados do cache (memória -> Redis -> None)
        """
        try:
            key = self._generate_key(symbol, timeframe, exchange)
            
            # Primeiro tenta cache em memória
            if key in self.memory_cache:
                cache_data, timestamp, ttl = self.memory_cache[key]
                
                # Verifica se ainda é válido
                if datetime.now() - timestamp <= ttl:
                    self.access_times[key] = time.time()  # Atualiza acesso
                    with self.metrics_lock:
                        self.metrics.hits += 1
                    return cache_data['data'].copy()
                else:
                    # Remove expirado
                    self._remove_from_memory(key)
                    with self.metrics_lock:
                        self.metrics.evictions += 1
            
            # Tenta Redis
            if self.enable_redis:
                try:
                    serialized = self.redis_client.get(key)
                    if serialized:
                        cache_data = pickle.loads(serialized)
                        
                        # Verifica TTL
                        cache_time = cache_data['cache_time']
                        ttl = self.cache_ttl.get(timeframe, timedelta(hours=1))
                        
                        if datetime.now() - cache_time <= ttl:
                            # Recarrega no cache em memória
                            self.store_data(
                                symbol, 
                                cache_data['data'], 
                                timeframe, 
                                exchange,
                                force=True
                            )
                            
                            with self.metrics_lock:
                                self.metrics.hits += 1
                            return cache_data['data'].copy()
                        else:
                            # Remove do Redis
                            self.redis_client.delete(key)
                            self.redis_client.delete(f"meta:{key}")
                
                except Exception as e:
                    logger.warning(f"Erro ao recuperar do Redis: {e}")
            
            # Cache miss
            with self.metrics_lock:
                self.metrics.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Erro ao recuperar cache para {symbol}: {e}")
            return None
    
    def store_batch(self, symbols_data: Dict[str, pd.DataFrame], timeframe: str, 
                   exchange: str = 'binance'):
        """
        Armazena dados em lote com threading para performance
        """
        def store_single(args):
            symbol, data = args
            return self.store_data(symbol, data, timeframe, exchange)
        
        # Usa threading para armazenamento paralelo
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(store_single, symbols_data.items()))
        
        logger.info(f"Lote cacheado: {len(symbols_data)} símbolos ({timeframe})")
    
    def get_cached_symbols(self, timeframe: str, exchange: str = 'binance') -> List[str]:
        """
        Retorna todos os símbolos cacheados para um timeframe
        """
        symbols = []
        
        # Verifica cache em memória
        for key, (cache_data, timestamp, ttl) in self.memory_cache.items():
            if (datetime.now() - timestamp <= ttl and 
                cache_data['metadata']['timeframe'] == timeframe and
                cache_data['metadata']['exchange'] == exchange):
                symbols.append(cache_data['metadata']['symbol'])
        
        # Verifica Redis
        if self.enable_redis:
            try:
                pattern = f"meta:*"
                for meta_key in self.redis_client.scan_iter(match=pattern):
                    try:
                        metadata = json.loads(self.redis_client.get(meta_key))
                        if (metadata['timeframe'] == timeframe and 
                            metadata['exchange'] == exchange and
                            metadata['symbol'] not in symbols):
                            symbols.append(metadata['symbol'])
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Erro ao listar símbolos no Redis: {e}")
        
        return symbols
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None, 
                   exchange: Optional[str] = None):
        """
        Limpa cache seletivo
        """
        try:
            keys_to_remove = []
            
            # Identifica chaves para remover
            for key, (cache_data, timestamp, ttl) in self.memory_cache.items():
                metadata = cache_data['metadata']
                
                should_remove = True
                if symbol and metadata['symbol'] != symbol:
                    should_remove = False
                if timeframe and metadata['timeframe'] != timeframe:
                    should_remove = False
                if exchange and metadata['exchange'] != exchange:
                    should_remove = False
                
                if should_remove:
                    keys_to_remove.append(key)
            
            # Remove da memória
            for key in keys_to_remove:
                self._remove_from_memory(key)
            
            # Remove do Redis
            if self.enable_redis:
                try:
                    # Remove dados
                    for key in keys_to_remove:
                        self.redis_client.delete(key)
                        self.redis_client.delete(f"meta:{key}")
                except Exception as e:
                    logger.warning(f"Erro ao limpar Redis: {e}")
            
            logger.info(f"Cache limpo: {len(keys_to_remove)} itens removidos")
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
    
    def get_metrics(self) -> Dict:
        """Retorna métricas de performance"""
        with self.metrics_lock:
            total_requests = self.metrics.hits + self.metrics.misses
            hit_rate = (self.metrics.hits / total_requests * 100) if total_requests > 0 else 0
            
            current_memory = sum(self.cache_sizes.values())
            
            return {
                'hits': self.metrics.hits,
                'misses': self.metrics.misses,
                'sets': self.metrics.sets,
                'evictions': self.metrics.evictions,
                'hit_rate_percent': round(hit_rate, 2),
                'memory_usage_mb': round(current_memory / (1024 * 1024), 2),
                'memory_limit_mb': round(self.memory_limit_bytes / (1024 * 1024), 2),
                'cached_items': len(self.memory_cache),
                'redis_enabled': self.enable_redis,
                'last_cleanup': self.metrics.last_cleanup.isoformat() if self.metrics.last_cleanup else None
            }
    
    def optimize_for_batch_size(self, target_symbols: int):
        """
        Otimiza configurações para tamanho de lote específico
        """
        # Ajusta limite de memória baseado no número de símbolos
        estimated_per_symbol = 50 * 1024  # ~50KB por DataFrame
        required_memory = target_symbols * estimated_per_symbol
        
        if required_memory > self.memory_limit_bytes:
            logger.warning(f"Memória insuficiente para {target_symbols} símbolos. "
                          f"Requerido: {required_memory/(1024*1024):.1f}MB, "
                          f"Disponível: {self.memory_limit_bytes/(1024*1024):.1f}MB")
        
        return required_memory <= self.memory_limit_bytes
    
    def __del__(self):
        """Cleanup ao destruir objeto"""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=1)

# Singleton global
_cache_instance = None

def get_high_performance_cache(redis_host: str = 'localhost', redis_port: int = 6379,
                              memory_limit_mb: int = 1024, enable_redis: bool = False) -> HighPerformanceCache:
    """Retorna instância singleton do cache de alta performance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = HighPerformanceCache(
            redis_host, redis_port, 0, memory_limit_mb, enable_redis
        )
    return _cache_instance

if __name__ == "__main__":
    # Teste do cache de alta performance
    cache = get_high_performance_cache(memory_limit_mb=512, enable_redis=False)
    
    # Cria dados de teste
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    for symbol in test_symbols:
        test_data = pd.DataFrame({
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        })
        cache.store_data(symbol, test_data, '1h')
    
    # Testa recuperação
    for symbol in test_symbols:
        data = cache.get_data(symbol, '1h')
        print(f"{symbol}: {'Recuperado' if data is not None else 'Não encontrado'}")
    
    # Mostra métricas
    print("Métricas:", cache.get_metrics())
