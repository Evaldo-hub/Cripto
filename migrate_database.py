"""
🔧 Database Migration Script
Corrige o nome da coluna de probabilidade_reversao para prob_reversao
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from database_manager_simple import SimpleDatabaseManager
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Executa a migração do banco de dados"""
    try:
        print("INICIANDO MIGRAÇÃO DO BANCO DE DADOS")
        print("=" * 50)
        
        # Caminho do banco de dados
        db_path = os.path.join(os.getcwd(), 'crypto_analysis.db')
        
        if not os.path.exists(db_path):
            print("Banco de dados não encontrado!")
            return
        
        print(f"Banco de dados: {db_path}")
        
        # Conecta ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica colunas atuais
        cursor.execute("PRAGMA table_info(analysis_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Colunas atuais: {columns}")
        
        # Verifica se precisa migrar
        if 'probabilidade_reversao' in columns:
            print("Coluna 'probabilidade_reversao' encontrada - migrando...")
            
            if 'prob_reversao' not in columns:
                # Renomeia a coluna
                cursor.execute("ALTER TABLE analysis_results RENAME COLUMN probabilidade_reversao TO prob_reversao")
                conn.commit()
                print("Coluna renomeada com sucesso!")
            else:
                print("Coluna 'prob_reversao' já existe!")
        else:
            print("Nenhuma migração necessária!")
        
        # Verifica resultado
        cursor.execute("PRAGMA table_info(analysis_results)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"Colunas após migração: {new_columns}")
        
        conn.close()
        
        print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        print(f"Erro na migração: {e}")
        raise

if __name__ == "__main__":
    migrate_database()
