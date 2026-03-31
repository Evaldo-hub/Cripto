"""
Database Manager for Strategy Analysis
Gerencia armazenamento de resultados das análises
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "crypto_analysis.db"):
        """Inicializa o gerenciador de banco de dados"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Cria as tabelas do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabela principal de análises
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    price REAL NOT NULL,
                    rsi REAL NOT NULL,
                    stoch_rsi REAL,
                    score_entrada INTEGER NOT NULL,
                    probabilidade_reversao REAL NOT NULL,
                    sinal_entrada TEXT NOT NULL,
                    sinal_saida BOOLEAN NOT NULL,
                    motivo_saida TEXT,
                    is_rejection_candle BOOLEAN,
                    is_hammer BOOLEAN,
                    is_doji BOOLEAN,
                    is_shooting_star BOOLEAN,
                    is_shooting_star_fall BOOLEAN,
                    is_shooting_star_rise BOOLEAN,
                    is_falling_candle BOOLEAN,
                    is_strong_fall BOOLEAN,
                    is_rising_candle BOOLEAN,
                    is_strong_rise BOOLEAN,
                    support_distance_pct REAL,
                    resistance_distance_pct REAL,
                    stop_loss REAL,
                    stop_loss_distance_pct REAL,
                    resistance_20 REAL,
                    support_20 REAL,
                    take_profit_1r REAL,
                    take_profit_2r REAL,
                    take_profit_3r REAL,
                    nearest_resistance REAL,
                    nearest_resistance_distance_pct REAL,
                    stoch_signal REAL,
                    stoch_signal_slow REAL,
                    stoch_cross_up BOOLEAN,
                    stoch_cross_down BOOLEAN,
                    stoch_cross_up_slow BOOLEAN,
                    stoch_cross_down_slow BOOLEAN,
                    stoch_oversold BOOLEAN,
                    stoch_overbought BOOLEAN,
                    stoch_bullish_zone BOOLEAN,
                    rsi_turning_up BOOLEAN,
                    volume_ratio REAL,
                    timeframe TEXT DEFAULT '4h'
                )
            ''')
            
            # Tabela de estatísticas diárias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_analyzed INTEGER NOT NULL,
                    ideal_entries INTEGER NOT NULL,
                    possible_entries INTEGER NOT NULL,
                    exits_detected INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    avg_probability REAL NOT NULL,
                    avg_rsi REAL NOT NULL,
                    avg_stoch_rsi REAL,
                    hammers_count INTEGER,
                    shooting_stars_count INTEGER,
                    stoch_cross_up_count INTEGER,
                    stoch_oversold_count INTEGER,
                    top_symbols TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            # Tabela de performance histórica
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    entry_date DATE NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_score INTEGER NOT NULL,
                    entry_rsi REAL NOT NULL,
                    entry_stoch_rsi REAL,
                    exit_date DATE,
                    exit_price REAL,
                    exit_reason TEXT,
                    profit_loss_pct REAL,
                    holding_days INTEGER,
                    strategy_version TEXT DEFAULT '1.0',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Índices para melhor performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_symbol_timestamp ON analysis_results(symbol, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_results(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_score ON analysis_results(score_entrada)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_symbol ON performance_history(symbol)')
            
            conn.commit()
            conn.close()
            logger.info("Banco de dados inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise
    
    def save_analysis_results(self, results: List[Dict], timeframe: str = '4h'):
        """Salva os resultados de uma análise no banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            
            for result in results:
                cursor.execute('''
                    INSERT INTO analysis_results (
                        symbol, timestamp, price, rsi, stoch_rsi, score_entrada,
                        probabilidade_reversao, sinal_entrada, sinal_saida, motivo_saida,
                        is_rejection_candle, is_hammer, is_doji, is_shooting_star,
                        is_shooting_star_fall, is_shooting_star_rise, is_falling_candle,
                        is_strong_fall, is_rising_candle, is_strong_rise,
                        stop_loss, stop_loss_distance_pct, resistance_20, support_20,
                        take_profit_1r, take_profit_2r, take_profit_3r,
                        nearest_resistance, nearest_resistance_distance_pct,
                        stoch_signal, stoch_signal_slow, stoch_cross_up, stoch_cross_down,
                        stoch_cross_up_slow, stoch_cross_down_slow, stoch_oversold,
                        stoch_overbought, stoch_bullish_zone, rsi_turning_up,
                        volume_ratio
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.get('symbol'),
                    timestamp,
                    result.get('price'),
                    result.get('rsi'),
                    result.get('stoch_rsi'),
                    result.get('score_entrada'),
                    result.get('probabilidade_reversao'),
                    result.get('sinal_entrada'),
                    result.get('sinal_saida', False),
                    result.get('motivo_saida'),
                    result.get('is_rejection_candle'),
                    result.get('is_hammer'),
                    result.get('is_doji'),
                    result.get('is_shooting_star'),
                    result.get('is_shooting_star_fall'),
                    result.get('is_shooting_star_rise'),
                    result.get('is_falling_candle'),
                    result.get('is_strong_fall'),
                    result.get('is_rising_candle'),
                    result.get('is_strong_rise'),
                    result.get('stop_loss'),
                    result.get('stop_loss_distance_pct'),
                    result.get('resistance_20'),
                    result.get('support_20'),
                    result.get('take_profit_1r'),
                    result.get('take_profit_2r'),
                    result.get('take_profit_3r'),
                    result.get('nearest_resistance'),
                    result.get('nearest_resistance_distance_pct'),
                    result.get('stoch_signal'),
                    result.get('stoch_signal_slow'),
                    result.get('stoch_cross_up'),
                    result.get('stoch_cross_down'),
                    result.get('stoch_cross_up_slow'),
                    result.get('stoch_cross_down_slow'),
                    result.get('stoch_oversold'),
                    result.get('stoch_overbought'),
                    result.get('stoch_bullish_zone'),
                    result.get('rsi_turning_up'),
                    result.get('volume_ratio')
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Salvos {len(results)} resultados no banco de dados")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")
            raise
    
    def update_daily_stats(self, results: List[Dict]):
        """Atualiza as estatísticas diárias"""
        try:
            if not results:
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().date()
            
            # Calcula estatísticas
            total_analyzed = len(results)
            ideal_entries = len([r for r in results if r.get('score_entrada', 0) >= 70])
            possible_entries = len([r for r in results if 50 <= r.get('score_entrada', 0) < 70])
            exits_detected = len([r for r in results if r.get('sinal_saida', False)])
            avg_score = sum(r.get('score_entrada', 0) for r in results) / total_analyzed
            avg_probability = sum(r.get('probabilidade_reversao', 0) for r in results) / total_analyzed
            avg_rsi = sum(r.get('rsi', 0) for r in results) / total_analyzed
            avg_stoch_rsi = sum(r.get('stoch_rsi', 0) for r in results) / total_analyzed
            
            hammers_count = len([r for r in results if r.get('is_hammer', False)])
            shooting_stars_count = len([r for r in results if r.get('is_shooting_star', False)])
            stoch_cross_up_count = len([r for r in results if r.get('stoch_cross_up', False) or r.get('stoch_cross_up_slow', False)])
            stoch_oversold_count = len([r for r in results if r.get('stoch_oversold', False)])
            
            # Top 5 símbolos por score
            top_symbols = sorted(results, key=lambda x: x.get('score_entrada', 0), reverse=True)[:5]
            top_symbols_json = json.dumps([s['symbol'] for s in top_symbols])
            
            # Insere ou atualiza estatísticas
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats (
                    date, total_analyzed, ideal_entries, possible_entries,
                    exits_detected, avg_score, avg_probability, avg_rsi,
                    avg_stoch_rsi, hammers_count, shooting_stars_count,
                    stoch_cross_up_count, stoch_oversold_count, top_symbols
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today, total_analyzed, ideal_entries, possible_entries,
                exits_detected, avg_score, avg_probability, avg_rsi,
                avg_stoch_rsi, hammers_count, shooting_stars_count,
                stoch_cross_up_count, stoch_oversold_count, top_symbols_json
            ))
            
            conn.commit()
            conn.close()
            logger.info("Estatísticas diárias atualizadas")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
            raise
    
    def get_historical_data(self, symbol: str = None, days: int = 30) -> pd.DataFrame:
        """Recupera dados históricos de análise"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = '''
                SELECT * FROM analysis_results 
                WHERE timestamp >= ?
            '''
            params = [since_date]
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            query += ' ORDER BY timestamp DESC'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao recuperar dados históricos: {e}")
            return pd.DataFrame()
    
    def get_daily_stats(self, days: int = 30) -> pd.DataFrame:
        """Recupera estatísticas diárias"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = '''
                SELECT * FROM daily_stats 
                WHERE date >= ?
                ORDER BY date DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=[since_date])
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao recuperar estatísticas diárias: {e}")
            return pd.DataFrame()
    
    def get_symbol_performance(self, symbol: str, days: int = 30) -> Dict:
        """Recupera performance específica de um símbolo"""
        try:
            df = self.get_historical_data(symbol, days)
            
            if df.empty:
                return {}
            
            # Calcula métricas de performance
            avg_score = df['score_entrada'].mean()
            avg_rsi = df['rsi'].mean()
            avg_stoch_rsi = df['stoch_rsi'].mean()
            entry_signals = df[df['score_entrada'] >= 70].shape[0]
            exit_signals = df[df['sinal_saida'] == True].shape[0]
            
            # Evolução do score
            recent_score = df.iloc[0]['score_entrada'] if len(df) > 0 else 0
            previous_score = df.iloc[7]['score_entrada'] if len(df) > 7 else 0
            score_trend = recent_score - previous_score
            
            return {
                'symbol': symbol,
                'total_analyses': len(df),
                'avg_score': avg_score,
                'avg_rsi': avg_rsi,
                'avg_stoch_rsi': avg_stoch_rsi,
                'entry_signals': entry_signals,
                'exit_signals': exit_signals,
                'recent_score': recent_score,
                'score_trend': score_trend,
                'last_analysis': df.iloc[0]['timestamp'] if len(df) > 0 else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular performance do símbolo: {e}")
            return {}
    
    def get_top_performers(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Recupera os melhores performers recentes"""
        try:
            df = self.get_historical_data(days=days)
            
            if df.empty:
                return []
            
            # Agrupa por símbolo e calcula métricas
            performers = []
            for symbol in df['symbol'].unique():
                symbol_data = df[df['symbol'] == symbol]
                
                avg_score = symbol_data['score_entrada'].mean()
                recent_score = symbol_data.iloc[0]['score_entrada']
                entry_count = symbol_data[symbol_data['score_entrada'] >= 70].shape[0]
                
                performers.append({
                    'symbol': symbol,
                    'avg_score': avg_score,
                    'recent_score': recent_score,
                    'entry_count': entry_count,
                    'total_analyses': len(symbol_data)
                })
            
            # Ordena por score médio
            performers.sort(key=lambda x: x['avg_score'], reverse=True)
            
            return performers[:limit]
            
        except Exception as e:
            logger.error(f"Erro ao recuperar top performers: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Limpa dados antigos do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Remove análises antigas
            cursor.execute('DELETE FROM analysis_results WHERE timestamp < ?', (cutoff_date,))
            
            # Remove estatísticas diárias antigas
            cursor.execute('DELETE FROM daily_stats WHERE date < ?', (cutoff_date.date(),))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Dados antigos removidos (anteriores a {cutoff_date})")
            
        except Exception as e:
            logger.error(f"Erro ao limpar dados antigos: {e}")
            raise
    
    def get_database_stats(self) -> Dict:
        """Retorna estatísticas do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Contagem de registros
            cursor.execute('SELECT COUNT(*) FROM analysis_results')
            total_analyses = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM daily_stats')
            daily_stats_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM performance_history')
            performance_count = cursor.fetchone()[0]
            
            # Data mais recente e mais antiga
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM analysis_results')
            date_range = cursor.fetchone()
            
            # Símbolos únicos
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM analysis_results')
            unique_symbols = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_analyses': total_analyses,
                'daily_stats_count': daily_stats_count,
                'performance_count': performance_count,
                'unique_symbols': unique_symbols,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do banco: {e}")
            return {}

# Instância global do gerenciador
db_manager = DatabaseManager()
