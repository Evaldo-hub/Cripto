"""
Scalable Orchestrator for 500+ Symbols
Orquestrador otimizado para alto volume de processamento
"""
import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp

# Adiciona src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from parallel_collector import get_parallel_collector
from high_performance_cache import get_high_performance_cache
from batch_quant_engine import get_batch_quant_engine
from performance_monitor import get_performance_monitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScalableCryptoOrchestrator:
    def __init__(self, max_symbols: int = 500, max_workers: int = 20):
        """
        Inicializa orquestrador escalável
        """
        self.max_symbols = max_symbols
        self.max_workers = max_workers
        
        # Inicializa componentes
        self.collector = get_parallel_collector(max_workers=max_workers)
        self.cache = get_high_performance_cache(memory_limit_mb=2048)  # 2GB
        self.quant_engine = get_batch_quant_engine(max_workers=max_workers)
        self.performance_monitor = get_performance_monitor(monitoring_interval=30)
        
        # Configurações
        self.default_timeframes = ['1h', '4h', '1d']
        self.exchanges = ['binance', 'bybit', 'okx']
        
        # Estado
        self.last_analysis_time = None
        self.analysis_stats = {}
        
        logger.info(f"Orquestrador escalável inicializado: {max_symbols} símbolos, {max_workers} workers")
    
    def collect_all_exchanges_parallel(self, timeframe: str = '1h', symbols_per_exchange: int = 200) -> Dict[str, Dict]:
        """
        Coleta dados de todas as exchanges em paralelo
        """
        logger.info(f"Coletando dados de todas as exchanges: {timeframe}")
        start_time = time.time()
        
        all_results = {}
        
        # Usa ThreadPool para coleta paralela entre exchanges
        def collect_exchange(exchange_name):
            try:
                # Obtém símbolos da exchange
                symbols = self.collector.get_usdt_symbols(exchange_name, min_volume=1000000)
                symbols = symbols[:symbols_per_exchange]
                
                if not symbols:
                    logger.warning(f"Nenhum símbolo encontrado para {exchange_name}")
                    return exchange_name, {}
                
                # Coleta dados
                exchange_data = self.collector.collect_parallel(symbols, timeframe, 200, exchange_name)
                
                # Armazena no cache
                self.cache.store_batch(exchange_data, timeframe, exchange_name)
                
                # Registra métricas
                for symbol in exchange_data.keys():
                    self.performance_monitor.record_symbol_processed()
                
                logger.info(f"{exchange_name}: {len(exchange_data)}/{len(symbols)} símbolos coletados")
                return exchange_name, exchange_data
                
            except Exception as e:
                logger.error(f"Erro na coleta de {exchange_name}: {e}")
                return exchange_name, {}
        
        # Executa coleta em paralelo
        with ThreadPoolExecutor(max_workers=len(self.exchanges)) as executor:
            future_to_exchange = {
                executor.submit(collect_exchange, exchange): exchange 
                for exchange in self.exchanges
            }
            
            for future in as_completed(future_to_exchange):
                exchange_name, exchange_data = future.result()
                if exchange_data:
                    all_results[exchange_name] = exchange_data
        
        duration = time.time() - start_time
        total_symbols = sum(len(data) for data in all_results.values())
        
        logger.info(f"Coleta concluída em {duration:.2f}s: {total_symbols} símbolos totais")
        
        # Atualiza estatísticas
        self.analysis_stats['collection'] = {
            'duration': duration,
            'total_symbols': total_symbols,
            'exchanges': list(all_results.keys()),
            'timestamp': datetime.now()
        }
        
        return all_results
    
    def analyze_all_data_parallel(self, all_data: Dict[str, Dict], timeframe: str) -> Dict[str, List]:
        """
        Analisa dados de todas as exchanges em paralelo
        """
        logger.info(f"Iniciando análise paralela: {timeframe}")
        start_time = time.time()
        
        all_results = {}
        
        # Analisa cada exchange em paralelo
        def analyze_exchange(exchange_name, exchange_data):
            try:
                if not exchange_data:
                    return exchange_name, []
                
                # Análise quantitativa
                results = self.quant_engine.analyze_batch_parallel(exchange_data)
                
                # Registra métricas
                for result in results:
                    self.performance_monitor.record_symbol_processed()
                    if result.score >= 60:  # Oportunidade
                        self.performance_monitor.increment_counter('opportunities')
                
                logger.info(f"{exchange_name}: {len(results)} símbolos analisados")
                return exchange_name, results
                
            except Exception as e:
                logger.error(f"Erro na análise de {exchange_name}: {e}")
                return exchange_name, []
        
        # Executa análise em paralelo
        with ThreadPoolExecutor(max_workers=len(self.exchanges)) as executor:
            future_to_exchange = {
                executor.submit(analyze_exchange, exchange_name, exchange_data): exchange_name 
                for exchange_name, exchange_data in all_data.items()
            }
            
            for future in as_completed(future_to_exchange):
                exchange_name, results = future.result()
                all_results[exchange_name] = results
        
        duration = time.time() - start_time
        total_analyzed = sum(len(results) for results in all_results.values())
        
        logger.info(f"Análise concluída em {duration:.2f}s: {total_analyzed} símbolos totais")
        
        # Atualiza estatísticas
        self.analysis_stats['analysis'] = {
            'duration': duration,
            'total_analyzed': total_analyzed,
            'exchanges': list(all_results.keys()),
            'timestamp': datetime.now()
        }
        
        self.last_analysis_time = datetime.now()
        
        return all_results
    
    def get_top_opportunities_all_exchanges(self, min_score: float = 60, limit: int = 50) -> List[Dict]:
        """
        Obtém melhores oportunidades de todas as exchanges
        """
        all_opportunities = []
        
        # Para cada timeframe
        for timeframe in self.default_timeframes:
            try:
                # Coleta dados
                all_data = self.collect_all_exchanges_parallel(timeframe)
                
                # Analisa dados
                all_results = self.analyze_all_data_parallel(all_data, timeframe)
                
                # Coleta oportunidades
                for exchange_name, results in all_results.items():
                    for result in results:
                        if result.score >= min_score:
                            all_opportunities.append({
                                'symbol': result.symbol,
                                'exchange': exchange_name,
                                'timeframe': timeframe,
                                'score': result.score,
                                'signal': result.signal,
                                'price': result.price,
                                'confidence': result.confidence,
                                'indicators': result.indicators
                            })
                
            except Exception as e:
                logger.error(f"Erro na análise de {timeframe}: {e}")
                continue
        
        # Ordena por score
        all_opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return all_opportunities[:limit]
    
    def generate_comprehensive_report(self) -> Dict:
        """
        Gera relatório completo da análise
        """
        logger.info("Gerando relatório completo")
        
        # Métricas de performance
        performance_summary = self.performance_monitor.get_performance_summary(minutes=60)
        current_metrics = self.performance_monitor.get_current_metrics()
        
        # Métricas das análises
        collection_stats = self.analysis_stats.get('collection', {})
        analysis_stats = self.analysis_stats.get('analysis', {})
        
        # Cache metrics
        cache_metrics = self.cache.get_metrics()
        
        # Coletor stats
        collector_stats = self.collector.get_collection_stats()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
                'total_symbols_target': self.max_symbols,
                'exchanges_analyzed': self.exchanges,
                'timeframes_analyzed': self.default_timeframes
            },
            'performance': {
                'current_metrics': current_metrics,
                'summary_60min': performance_summary,
                'cache_metrics': cache_metrics,
                'collector_stats': collector_stats
            },
            'analysis_stats': {
                'collection': collection_stats,
                'analysis': analysis_stats
            },
            'system_health': {
                'cpu_usage': current_metrics.get('system', {}).get('cpu_percent', 0),
                'memory_usage': current_metrics.get('system', {}).get('memory_percent', 0),
                'cache_hit_rate': cache_metrics.get('hit_rate_percent', 0),
                'error_rate': performance_summary.get('alerts', {}).get('total', 0)
            }
        }
        
        return report
    
    def run_full_analysis_cycle(self) -> Dict:
        """
        Executa ciclo completo de análise
        """
        logger.info("Iniciando ciclo completo de análise")
        cycle_start = time.time()
        
        try:
            # Coleta e análise para cada timeframe
            all_results = {}
            
            for timeframe in self.default_timeframes:
                logger.info(f"Processando timeframe: {timeframe}")
                
                # Coleta dados
                all_data = self.collect_all_exchanges_parallel(timeframe)
                
                # Análise
                analysis_results = self.analyze_all_data_parallel(all_data, timeframe)
                all_results[timeframe] = analysis_results
            
            # Gera oportunidades
            opportunities = self.get_top_opportunities_all_exchanges(min_score=60, limit=100)
            
            # Gera relatório
            report = self.generate_comprehensive_report()
            
            cycle_duration = time.time() - cycle_start
            
            # Adiciona estatísticas do ciclo
            report['cycle_stats'] = {
                'duration': cycle_duration,
                'total_opportunities': len(opportunities),
                'timeframes_processed': list(all_results.keys()),
                'success': True
            }
            
            logger.info(f"Ciclo completo em {cycle_duration:.2f}s: {len(opportunities)} oportunidades")
            
            return {
                'success': True,
                'report': report,
                'opportunities': opportunities,
                'all_results': all_results
            }
            
        except Exception as e:
            logger.error(f"Erro no ciclo de análise: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'cycle_duration': time.time() - cycle_start
            }
    
    def run_scheduled_analysis(self):
        """
        Executa análises agendadas
        """
        logger.info("Iniciando análises agendadas")
        
        # Agenda análises
        schedule.every(1).hours.do(self.run_full_analysis_cycle)
        schedule.every(30).minutes.do(self.generate_comprehensive_report)
        schedule.every(5).minutes.do(self.performance_monitor.get_performance_summary, minutes=5)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
            except KeyboardInterrupt:
                logger.info("Análises agendadas interrompidas")
                break
            except Exception as e:
                logger.error(f"Erro nas análises agendadas: {e}")
                time.sleep(300)  # Espera 5 minutos em caso de erro
    
    def warm_up_system(self):
        """
        Aquece o sistema com dados principais
        """
        logger.info("Aquecendo sistema...")
        
        # Pré-cache de mercados
        self.collector.pre_cache_markets()
        
        # Coleta dados principais para aquecer cache
        main_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'AVAX/USDT']
        
        for timeframe in ['1h', '4h']:
            for symbol in main_symbols:
                try:
                    # Tenta obter do cache primeiro
                    cached_data = self.cache.get_data(symbol, timeframe, 'binance')
                    if cached_data is None:
                        # Coleta da API
                        fresh_data = self.collector.fetch_single_symbol((symbol, timeframe, 200, 'binance'))
                        if fresh_data is not None:
                            self.cache.store_data(symbol, fresh_data, timeframe, 'binance')
                            logger.debug(f"Sistema aquecido para {symbol} ({timeframe})")
                except Exception as e:
                    logger.error(f"Erro ao aquecer {symbol}: {e}")
        
        logger.info("Sistema aquecido com sucesso")

def main():
    """
    Função principal para execução do orquestrador escalável
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Scalable Crypto Scanner Orchestrator')
    parser.add_argument('--mode', choices=['single', 'scheduled', 'warmup', 'report'], 
                       default='single', help='Modo de execução')
    parser.add_argument('--max-symbols', type=int, default=500, help='Máximo de símbolos')
    parser.add_argument('--max-workers', type=int, default=20, help='Máximo de workers')
    parser.add_argument('--min-score', type=float, default=60, help='Score mínimo')
    parser.add_argument('--limit', type=int, default=50, help='Limite de oportunidades')
    
    args = parser.parse_args()
    
    # Inicializa orquestrador
    orchestrator = ScalableCryptoOrchestrator(args.max_symbols, args.max_workers)
    
    if args.mode == 'warmup':
        orchestrator.warm_up_system()
    
    elif args.mode == 'single':
        # Análise única
        result = orchestrator.run_full_analysis_cycle()
        
        if result['success']:
            opportunities = result['opportunities']
            report = result['report']
            
            print(f"\n🎯 Top {len(opportunities)} Oportunidades:")
            print("-" * 80)
            for i, opp in enumerate(opportunities[:10]):
                print(f"{i+1}. {opp['symbol']} ({opp['exchange']} - {opp['timeframe']}): "
                      f"{opp['signal']} - Score: {opp['score']:.1f} - Preço: ${opp['price']:.4f}")
            
            print(f"\n📊 Resumo do Ciclo:")
            print(f"Duração: {report['cycle_stats']['duration']:.2f}s")
            print(f"Oportunidades: {len(opportunities)}")
            print(f"Cache Hit Rate: {report['performance']['cache_metrics']['hit_rate_percent']:.1f}%")
        else:
            print(f"Erro na análise: {result['error']}")
    
    elif args.mode == 'scheduled':
        # Análise agendada
        orchestrator.warm_up_system()
        orchestrator.run_scheduled_analysis()
    
    elif args.mode == 'report':
        # Gera relatório
        report = orchestrator.generate_comprehensive_report()
        print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    main()
