"""
Performance Monitoring System
Monitoramento de métricas e performance para o sistema escalável
"""
import time
import psutil
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
from collections import deque
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """Métricas do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    active_threads: int

@dataclass
class ApplicationMetrics:
    """Métricas da aplicação"""
    timestamp: datetime
    symbols_processed: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    error_count: int
    active_connections: int

@dataclass
class PerformanceAlert:
    """Alerta de performance"""
    timestamp: datetime
    alert_type: str
    severity: str
    message: str
    metrics: Dict

class PerformanceMonitor:
    def __init__(self, monitoring_interval: int = 30, history_size: int = 1000):
        """
        Inicializa monitor de performance
        """
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        
        # Histórico de métricas
        self.system_history = deque(maxlen=history_size)
        self.application_history = deque(maxlen=history_size)
        self.alerts_history = deque(maxlen=100)
        
        # Contadores
        self.counters = {
            'total_symbols': 0,
            'total_requests': 0,
            'total_errors': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Locks para thread safety
        self._metrics_lock = threading.Lock()
        self._counters_lock = threading.Lock()
        
        # Thresholds para alertas
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'response_time_warning': 5.0,
            'response_time_critical': 10.0,
            'error_rate_warning': 5.0,
            'error_rate_critical': 10.0
        }
        
        # Thread de monitoramento
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Inicia monitoramento
        self._start_monitoring()
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Coleta métricas do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memória
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Rede
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Threads
            active_threads = threading.active_count()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory_mb,
                disk_usage_percent=disk_usage_percent,
                network_io=network_io,
                active_threads=active_threads
            )
            
        except Exception as e:
            logger.error(f"Erro ao coletar métricas do sistema: {e}")
            return None
    
    def _collect_application_metrics(self) -> ApplicationMetrics:
        """Coleta métricas da aplicação"""
        try:
            with self._counters_lock:
                total_requests = self.counters['total_requests']
                total_errors = self.counters['total_errors']
                cache_hits = self.counters['cache_hits']
                cache_misses = self.counters['cache_misses']
            
            # Calcula taxas
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
            
            # Tempo médio de resposta (simulado - em produção viria das medições reais)
            avg_response_time = np.random.uniform(0.1, 2.0)  # Simulação
            
            return ApplicationMetrics(
                timestamp=datetime.now(),
                symbols_processed=self.counters['total_symbols'],
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                avg_response_time=avg_response_time,
                error_count=total_errors,
                active_connections=threading.active_count()
            )
            
        except Exception as e:
            logger.error(f"Erro ao coletar métricas da aplicação: {e}")
            return None
    
    def _check_alerts(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """Verifica condições de alerta"""
        alerts = []
        
        # Alertas de CPU
        if system_metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='CPU',
                severity='CRITICAL',
                message=f"CPU em uso crítico: {system_metrics.cpu_percent:.1f}%",
                metrics={'cpu_percent': system_metrics.cpu_percent}
            ))
        elif system_metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='CPU',
                severity='WARNING',
                message=f"CPU em uso elevado: {system_metrics.cpu_percent:.1f}%",
                metrics={'cpu_percent': system_metrics.cpu_percent}
            ))
        
        # Alertas de memória
        if system_metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='MEMORY',
                severity='CRITICAL',
                message=f"Memória em uso crítico: {system_metrics.memory_percent:.1f}%",
                metrics={'memory_percent': system_metrics.memory_percent}
            ))
        elif system_metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='MEMORY',
                severity='WARNING',
                message=f"Memória em uso elevado: {system_metrics.memory_percent:.1f}%",
                metrics={'memory_percent': system_metrics.memory_percent}
            ))
        
        # Alertas de tempo de resposta
        if app_metrics.avg_response_time >= self.thresholds['response_time_critical']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='RESPONSE_TIME',
                severity='CRITICAL',
                message=f"Tempo de resposta crítico: {app_metrics.avg_response_time:.2f}s",
                metrics={'avg_response_time': app_metrics.avg_response_time}
            ))
        elif app_metrics.avg_response_time >= self.thresholds['response_time_warning']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='RESPONSE_TIME',
                severity='WARNING',
                message=f"Tempo de resposta elevado: {app_metrics.avg_response_time:.2f}s",
                metrics={'avg_response_time': app_metrics.avg_response_time}
            ))
        
        # Armazena alertas
        with self._metrics_lock:
            self.alerts_history.extend(alerts)
        
        # Log de alertas críticos
        for alert in alerts:
            if alert.severity == 'CRITICAL':
                logger.critical(f"ALERTA CRÍTICO: {alert.message}")
            elif alert.severity == 'WARNING':
                logger.warning(f"ALERTA: {alert.message}")
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        logger.info("Iniciando monitoramento de performance")
        
        while not self._stop_monitoring.wait(self.monitoring_interval):
            try:
                # Coleta métricas
                system_metrics = self._collect_system_metrics()
                app_metrics = self._collect_application_metrics()
                
                if system_metrics and app_metrics:
                    # Armazena no histórico
                    with self._metrics_lock:
                        self.system_history.append(system_metrics)
                        self.application_history.append(app_metrics)
                    
                    # Verifica alertas
                    self._check_alerts(system_metrics, app_metrics)
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                continue
        
        logger.info("Monitoramento de performance encerrado")
    
    def _start_monitoring(self):
        """Inicia thread de monitoramento"""
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Incrementa contador"""
        with self._counters_lock:
            if counter_name in self.counters:
                self.counters[counter_name] += value
    
    def record_symbol_processed(self):
        """Registra processamento de símbolo"""
        self.increment_counter('total_symbols')
        self.increment_counter('total_requests')
    
    def record_cache_hit(self):
        """Registra cache hit"""
        self.increment_counter('cache_hits')
    
    def record_cache_miss(self):
        """Registra cache miss"""
        self.increment_counter('cache_misses')
        self.increment_counter('total_requests')
    
    def record_error(self):
        """Registra erro"""
        self.increment_counter('total_errors')
        self.increment_counter('total_requests')
    
    def get_current_metrics(self) -> Dict:
        """Retorna métricas atuais"""
        try:
            system_metrics = self._collect_system_metrics()
            app_metrics = self._collect_application_metrics()
            
            with self._counters_lock:
                counters = self.counters.copy()
            
            return {
                'system': asdict(system_metrics) if system_metrics else {},
                'application': asdict(app_metrics) if app_metrics else {},
                'counters': counters,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas atuais: {e}")
            return {}
    
    def get_performance_summary(self, minutes: int = 60) -> Dict:
        """Retorna resumo de performance do último período"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            # Filtra métricas do período
            recent_system = [
                m for m in self.system_history 
                if m.timestamp >= cutoff_time
            ]
            recent_app = [
                m for m in self.application_history 
                if m.timestamp >= cutoff_time
            ]
            recent_alerts = [
                a for a in self.alerts_history 
                if a.timestamp >= cutoff_time
            ]
            
            if not recent_system or not recent_app:
                return {}
            
            # Calcula estatísticas
            cpu_values = [m.cpu_percent for m in recent_system]
            memory_values = [m.memory_percent for m in recent_system]
            response_times = [m.avg_response_time for m in recent_app]
            
            summary = {
                'period_minutes': minutes,
                'data_points': len(recent_system),
                'system': {
                    'avg_cpu': round(np.mean(cpu_values), 2),
                    'max_cpu': round(np.max(cpu_values), 2),
                    'avg_memory': round(np.mean(memory_values), 2),
                    'max_memory': round(np.max(memory_values), 2)
                },
                'application': {
                    'avg_response_time': round(np.mean(response_times), 3),
                    'max_response_time': round(np.max(response_times), 3),
                    'total_symbols_processed': sum(m.symbols_processed for m in recent_app),
                    'total_cache_hits': sum(m.cache_hits for m in recent_app),
                    'total_cache_misses': sum(m.cache_misses for m in recent_app)
                },
                'alerts': {
                    'total': len(recent_alerts),
                    'critical': len([a for a in recent_alerts if a.severity == 'CRITICAL']),
                    'warnings': len([a for a in recent_alerts if a.severity == 'WARNING'])
                }
            }
            
            # Calcula cache hit rate
            total_cache_requests = summary['application']['total_cache_hits'] + summary['application']['total_cache_misses']
            if total_cache_requests > 0:
                summary['application']['cache_hit_rate'] = round(
                    (summary['application']['total_cache_hits'] / total_cache_requests) * 100, 2
                )
            else:
                summary['application']['cache_hit_rate'] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo de performance: {e}")
            return {}
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Retorna alertas recentes"""
        with self._metrics_lock:
            recent_alerts = list(self.alerts_history)[-limit:]
            return [asdict(alert) for alert in recent_alerts]
    
    def export_metrics(self, filename: str = None) -> str:
        """Exporta métricas para arquivo JSON"""
        try:
            if filename is None:
                filename = f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Prepara dados para exportação
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_history': [asdict(m) for m in self.system_history],
                'application_history': [asdict(m) for m in self.application_history],
                'alerts_history': [asdict(a) for a in self.alerts_history],
                'counters': self.counters,
                'thresholds': self.thresholds
            }
            
            # Converte datetime para string
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, default=convert_datetime, indent=2)
            
            logger.info(f"Métricas exportadas para {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao exportar métricas: {e}")
            return ""
    
    def reset_counters(self):
        """Reseta contadores"""
        with self._counters_lock:
            for key in self.counters:
                self.counters[key] = 0
        logger.info("Contadores resetados")
    
    def __del__(self):
        """Cleanup ao destruir objeto"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=1)

# Singleton global
_monitor_instance = None

def get_performance_monitor(monitoring_interval: int = 30, history_size: int = 1000) -> PerformanceMonitor:
    """Retorna instância singleton do monitor de performance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor(monitoring_interval, history_size)
    return _monitor_instance

if __name__ == "__main__":
    # Teste do monitor de performance
    monitor = get_performance_monitor(monitoring_interval=5)  # 5 segundos para teste
    
    # Simula alguma atividade
    for i in range(10):
        monitor.record_symbol_processed()
        if i % 3 == 0:
            monitor.record_cache_hit()
        else:
            monitor.record_cache_miss()
        
        time.sleep(1)
    
    # Mostra métricas atuais
    current = monitor.get_current_metrics()
    print("Métricas atuais:", current)
    
    # Mostra resumo
    summary = monitor.get_performance_summary(minutes=1)
    print("Resumo de performance:", summary)
    
    # Mostra alertas
    alerts = monitor.get_recent_alerts()
    print("Alertas recentes:", alerts)
