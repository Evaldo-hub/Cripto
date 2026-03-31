"""
📱 Gerenciador de Configurações do Dashboard
Salva e carrega configurações do Telegram e outras preferências
"""

import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gerencia configurações persistentes do dashboard"""
    
    def __init__(self, config_file: str = "dashboard_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Configurações carregadas de {self.config_file}")
                return config
            else:
                logger.info("Arquivo de configuração não encontrado, usando defaults")
                return self.get_default_config()
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Retorna configurações padrão"""
        return {
            "telegram": {
                "token": "",
                "chat_id": "",
                "enabled": False
            },
            "strategy": {
                "rsi_entrada": 25,
                "rsi_saida_min": 70,
                "rsi_saida_max": 75,
                "multi_timeframe": True,
                "timeframe_confirmation": True,
                "real_closing": True
            },
            "favorites": [
                "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", 
                "AVAX/USDT", "XRP/USDT", "TLM/USDT", "DEXE/USDT",
                "INJ/USDT", "MASK/USDT", "OP/USDT", "HBAR/USDT", "ILV/USDT"
            ],
            "ui": {
                "auto_refresh": True,
                "refresh_interval": 5
            }
        }
    
    def save_config(self) -> bool:
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configurações salvas em {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return False
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Retorna configurações do Telegram"""
        return self.config.get("telegram", {})
    
    def set_telegram_config(self, token: str = "", chat_id: str = "", enabled: bool = False) -> bool:
        """Define configurações do Telegram"""
        self.config["telegram"] = {
            "token": token,
            "chat_id": chat_id,
            "enabled": enabled and token and chat_id
        }
        return self.save_config()
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Retorna configurações da estratégia"""
        return self.config.get("strategy", {})
    
    def set_strategy_config(self, **kwargs) -> bool:
        """Define configurações da estratégia"""
        if "strategy" not in self.config:
            self.config["strategy"] = {}
        
        for key, value in kwargs.items():
            self.config["strategy"][key] = value
        
        return self.save_config()
    
    def get_favorites(self) -> list:
        """Retorna moedas favoritas"""
        return self.config.get("favorites", [])
    
    def set_favorites(self, favorites: list) -> bool:
        """Define moedas favoritas"""
        self.config["favorites"] = favorites
        return self.save_config()
    
    def is_telegram_configured(self) -> bool:
        """Verifica se Telegram está configurado"""
        telegram_config = self.get_telegram_config()
        return bool(telegram_config.get("token") and telegram_config.get("chat_id"))
    
    def update_from_session_state(self, session_state) -> bool:
        """Atualiza configurações a partir do session state"""
        try:
            # Telegram
            if hasattr(session_state, 'telegram_token') or 'telegram_token' in session_state:
                token = session_state.get('telegram_token', '')
                chat_id = session_state.get('telegram_chat_id', '')
                self.set_telegram_config(token, chat_id, bool(token and chat_id))
            
            # Estratégia
            strategy_updates = {}
            strategy_keys = [
                'rsi_entrada', 'rsi_saida_min', 'rsi_saida_max',
                'multi_timeframe_validation', 'timeframe_confirmation', 'require_real_closing'
            ]
            
            for key in strategy_keys:
                if key in session_state:
                    strategy_updates[key] = session_state[key]
            
            if strategy_updates:
                self.set_strategy_config(**strategy_updates)
            
            # Favoritas
            if 'favorite_coins' in session_state:
                self.set_favorites(session_state['favorite_coins'])
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar configurações do session state: {e}")
            return False

# Instância global do gerenciador de configurações
config_manager = ConfigManager()
