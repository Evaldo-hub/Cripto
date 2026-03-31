"""
Orchestrator Principal
Coordena todos os componentes do sistema
"""
import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import json
import sys
import os

# Adiciona src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_collector import get_data_collector
from cache_manager import get_cache_manager
from quant_engine import get_quant_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CryptoScannerOrchestrator:
    def __init__(self):
        self.collector = get_data_collector()
        self.cache = get_cache_manager()
        self.quant_engine = get_quant_engine()
        
        # Configurações padrão
        self.default_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'AVAX/USDT',
            'INJ/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT'
        ]
        self.timeframes = ['1h', '4h', '1d']
        self.exchange = 'binance'
        
    def collect_and_analyze(self, symbols: List[str] = None, timeframes: List[str] = None):
        """
        Coleta dados e realiza análise completa
        """
        if symbols is None:
            symbols = self.default_symbols
        if timeframes is None:
            timeframes = self.timeframes
            
        logger.info(f"Iniciando coleta e análise para {len(symbols)} símbolos")
        
        all_results = {}
        
        for timeframe in timeframes:
            logger.info(f"Processando timeframe: {timeframe}")
            
            # Coleta dados em lote
            batch_data = {}
            for symbol in symbols:
                try:
                    # Tenta cache primeiro
                    cached_data = self.cache.get_data(symbol, timeframe, self.exchange)
                    if cached_data is not None:
                        batch_data[symbol] = cached_data
                        logger.debug(f"Dados do cache usados para {symbol}")
                    else:
                        # Coleta da API
                        fresh_data = self.collector.fetch_ohlcv_data(symbol, timeframe, 200, self.exchange)
                        if fresh_data is not None:
                            batch_data[symbol] = fresh_data
                            self.cache.store_data(symbol, fresh_data, timeframe, self.exchange)
                            logger.debug(f"Dados coletados da API para {symbol}")
                except Exception as e:
                    logger.error(f"Erro ao processar {symbol}: {e}")
                    continue
            
            # Análise quantitativa
            if batch_data:
                analysis_results = self.quant_engine.analyze_batch(batch_data)
                all_results[timeframe] = analysis_results
                logger.info(f"Análise {timeframe}: {len(analysis_results)} resultados")
        
        return all_results
    
    def get_top_opportunities(self, min_score: float = 60, limit: int = 10):
        """
        Retorna as melhores oportunidades de trading
        """
        all_results = self.collect_and_analyze()
        
        opportunities = []
        for timeframe, results in all_results.items():
            for result in results:
                if result.score >= min_score:
                    opportunities.append({
                        'symbol': result.symbol,
                        'timeframe': timeframe,
                        'score': result.score,
                        'signal': result.signal,
                        'price': result.price,
                        'confidence': result.confidence,
                        'indicators': result.indicators
                    })
        
        # Ordena por score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities[:limit]
    
    def generate_report(self, save_to_file: bool = True):
        """
        Gera relatório completo da análise
        """
        logger.info("Gerando relatório de análise")
        
        all_results = self.collect_and_analyze()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'exchange': self.exchange,
            'summary': {},
            'timeframes': {}
        }
        
        total_opportunities = 0
        
        for timeframe, results in all_results.items():
            buy_signals = len([r for r in results if "COMPRA" in r.signal])
            sell_signals = len([r for r in results if "VENDA" in r.signal])
            avg_score = sum(r.score for r in results) / len(results) if results else 0
            
            report['timeframes'][timeframe] = {
                'total_analyzed': len(results),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'avg_score': round(avg_score, 2),
                'top_opportunities': [
                    {
                        'symbol': r.symbol,
                        'score': r.score,
                        'signal': r.signal,
                        'price': r.price
                    } for r in results[:5]
                ]
            }
            
            total_opportunities += buy_signals + sell_signals
        
        report['summary'] = {
            'total_opportunities': total_opportunities,
            'cache_info': self.cache.get_cache_info()
        }
        
        if save_to_file:
            filename = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Relatório salvo em: {filename}")
        
        return report
    
    def run_scheduled_analysis(self):
        """
        Executa análise agendada
        """
        logger.info("Iniciando análise agendada")
        
        # Agenda análises
        schedule.every(1).hours.do(self.collect_and_analyze)
        schedule.every(6).hours.do(self.generate_report)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
            except KeyboardInterrupt:
                logger.info("Análise agendada interrompida")
                break
            except Exception as e:
                logger.error(f"Erro na análise agendada: {e}")
                time.sleep(300)  # Espera 5 minutos em caso de erro
    
    def warm_up_cache(self):
        """
        Aquece o cache com dados principais
        """
        logger.info("Aquecendo cache...")
        
        for timeframe in self.timeframes:
            for symbol in self.default_symbols:
                try:
                    cached_data = self.cache.get_data(symbol, timeframe, self.exchange)
                    if cached_data is None:
                        fresh_data = self.collector.fetch_ohlcv_data(symbol, timeframe, 200, self.exchange)
                        if fresh_data is not None:
                            self.cache.store_data(symbol, fresh_data, timeframe, self.exchange)
                            logger.debug(f"Cache aquecido para {symbol} ({timeframe})")
                except Exception as e:
                    logger.error(f"Erro ao aquecer cache para {symbol}: {e}")
        
        logger.info("Cache aquecido com sucesso")

def main():
    """
    Função principal para execução do orchestrator
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Scanner Orchestrator')
    parser.add_argument('--mode', choices=['single', 'scheduled', 'warmup'], 
                       default='single', help='Modo de execução')
    parser.add_argument('--symbols', nargs='+', help='Símbolos para analisar')
    parser.add_argument('--timeframes', nargs='+', help='Timeframes para analisar')
    parser.add_argument('--min-score', type=float, default=60, help='Score mínimo para oportunidades')
    parser.add_argument('--limit', type=int, default=10, help='Limite de oportunidades')
    
    args = parser.parse_args()
    
    orchestrator = CryptoScannerOrchestrator()
    
    if args.mode == 'warmup':
        orchestrator.warm_up_cache()
    
    elif args.mode == 'single':
        # Análise única
        results = orchestrator.collect_and_analyze(args.symbols, args.timeframes)
        
        # Mostra oportunidades
        opportunities = orchestrator.get_top_opportunities(args.min_score, args.limit)
        
        print(f"\n🎯 Top {len(opportunities)} Oportunidades:")
        print("-" * 80)
        for opp in opportunities:
            print(f"{opp['symbol']} ({opp['timeframe']}): {opp['signal']} - Score: {opp['score']:.1f} - Preço: ${opp['price']:.4f}")
        
        # Gera relatório
        report = orchestrator.generate_report()
        print(f"\n📊 Resumo:")
        print(f"Total de oportunidades: {report['summary']['total_opportunities']}")
        
    elif args.mode == 'scheduled':
        # Análise agendada
        orchestrator.warm_up_cache()
        orchestrator.run_scheduled_analysis()

if __name__ == "__main__":
    main()
