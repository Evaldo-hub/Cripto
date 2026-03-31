"""
Simple Database Manager for Strategy Analysis
Versão simplificada para garantir funcionamento
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)

class SimpleDatabaseManager:
    def __init__(self, db_path: str = "crypto_analysis_simple.db"):
        """Inicializa o gerenciador de banco de dados simplificado"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Cria as tabelas do banco de dados simplificadas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabela principal simplificada
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    price REAL NOT NULL,
                    rsi REAL NOT NULL,
                    stoch_rsi REAL,
                    score_entrada INTEGER NOT NULL,
                    prob_reversao REAL NOT NULL,
                    sinal_entrada TEXT NOT NULL,
                    sinal_saida BOOLEAN NOT NULL,
                    motivo_saida TEXT,
                    is_hammer BOOLEAN,
                    is_doji BOOLEAN,
                    is_shooting_star BOOLEAN,
                    is_falling_candle BOOLEAN,
                    stop_loss REAL,
                    take_profit_1r REAL,
                    take_profit_3r REAL,
                    volume_ratio REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: Rename column if it exists with old name
            cursor.execute("PRAGMA table_info(analysis_results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'probabilidade_reversao' in columns and 'prob_reversao' not in columns:
                cursor.execute("ALTER TABLE analysis_results RENAME COLUMN probabilidade_reversao TO prob_reversao")
                logger.info("Column 'probabilidade_reversao' renamed to 'prob_reversao'")
            
            # Tabela de estatísticas diárias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_analyzed INTEGER NOT NULL,
                    ideal_entries INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    avg_probability REAL NOT NULL,
                    avg_rsi REAL NOT NULL,
                    top_symbols TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Banco de dados simplificado inicializado com sucesso")
            
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
                        prob_reversao, sinal_entrada, sinal_saida, motivo_saida,
                        is_hammer, is_doji, is_shooting_star, is_falling_candle,
                        stop_loss, take_profit_1r, take_profit_3r, volume_ratio
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.get('symbol'),
                    timestamp,
                    result.get('price'),
                    result.get('rsi'),
                    result.get('stoch_rsi'),
                    result.get('score_entrada'),
                    result.get('prob_reversao'),
                    result.get('sinal_entrada'),
                    result.get('sinal_saida', False),
                    result.get('motivo_saida'),
                    result.get('is_hammer', False),
                    result.get('is_doji', False),
                    result.get('is_shooting_star', False),
                    result.get('is_falling_candle', False),
                    result.get('stop_loss'),
                    result.get('take_profit_1r'),
                    result.get('take_profit_3r'),
                    result.get('volume_ratio')
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Salvos {len(results)} resultados no banco de dados simplificado")
            
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
            avg_score = sum(r.get('score_entrada', 0) for r in results) / total_analyzed
            avg_probability = sum(r.get('probabilidade_reversao', 0) for r in results) / total_analyzed
            avg_rsi = sum(r.get('rsi', 0) for r in results) / total_analyzed
            
            # Top 5 símbolos por score
            top_symbols = sorted(results, key=lambda x: x.get('score_entrada', 0), reverse=True)[:5]
            top_symbols_json = json.dumps([s['symbol'] for s in top_symbols])
            
            # Insere ou atualiza estatísticas
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats (
                    date, total_analyzed, ideal_entries, avg_score,
                    avg_probability, avg_rsi, top_symbols
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                today, total_analyzed, ideal_entries, avg_score,
                avg_probability, avg_rsi, top_symbols_json
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
                'unique_symbols': unique_symbols,
                'earliest_date': date_range[0],
                'latest_date': date_range[1],
                'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do banco: {e}")
            return {}

# Instância global do gerenciador simplificado
db_manager = SimpleDatabaseManager()
