"""
💰 Gestor de Posições e Vendas com Lucro
Sistema para registrar compras e calcular vendas com lucro baseado em reversão de baixa
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class PositionManager:
    """Gerencia posições abertas e calcula vendas com lucro"""
    
    def __init__(self, positions_file: str = "positions.json"):
        self.positions_file = positions_file
        self.positions = self.load_positions()
    
    def load_positions(self) -> Dict:
        """Carrega posições do arquivo"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                logger.info(f"Carregadas {len(positions.get('open_positions', {}))} posições abertas")
                return positions
            else:
                logger.info("Arquivo de posições não encontrado, usando defaults")
                return self.get_default_positions()
        except Exception as e:
            logger.error(f"Erro ao carregar posições: {e}")
            return self.get_default_positions()
    
    def get_default_positions(self) -> Dict:
        """Retorna estrutura padrão de posições"""
        return {
            "open_positions": {},  # symbol: position_data
            "closed_positions": {},  # symbol: [position_data]
            "settings": {
                "default_stop_loss": 5.0,  # %
                "default_take_profit": 10.0,  # %
                "trailing_stop": True,
                "min_profit": 2.0  # %
            }
        }
    
    def save_positions(self) -> bool:
        """Salva posições no arquivo"""
        try:
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(self.positions, f, indent=2, ensure_ascii=False, default=str)
            logger.info("Posições salvas com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar posições: {e}")
            return False
    
    def open_position(self, symbol: str, buy_price: float, quantity: float = 0.0, 
                   stop_loss: float = None, take_profit: float = None) -> Dict:
        """Abre uma nova posição"""
        try:
            # Calcula stop loss e take profit se não informados
            settings = self.positions.get('settings', {})
            
            if stop_loss is None:
                stop_loss = buy_price * (1 - settings.get('default_stop_loss', 5.0) / 100)
            
            if take_profit is None:
                take_profit = buy_price * (1 + settings.get('default_take_profit', 10.0) / 100)
            
            position = {
                "symbol": symbol,
                "buy_price": buy_price,
                "quantity": quantity,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "current_price": buy_price,
                "profit_percent": 0.0,
                "profit_amount": 0.0,
                "highest_price": buy_price,
                "trailing_stop": stop_loss if settings.get('trailing_stop', True) else None,
                "open_time": datetime.now(timezone.utc).isoformat(),
                "status": "open",
                "notes": f"Compra em ${buy_price:.4f}"
            }
            
            self.positions['open_positions'][symbol] = position
            self.save_positions()
            
            logger.info(f"Posição aberta: {symbol} @ ${buy_price:.4f}")
            return position
            
        except Exception as e:
            logger.error(f"Erro ao abrir posição {symbol}: {e}")
            return {}
    
    def close_position(self, symbol: str, sell_price: float, reason: str = "manual") -> Optional[Dict]:
        """Fecha uma posição e calcula lucro"""
        try:
            if symbol not in self.positions['open_positions']:
                logger.warning(f"Posição {symbol} não encontrada")
                return None
            
            position = self.positions['open_positions'][symbol]
            
            # Calcula lucro
            buy_price = position['buy_price']
            quantity = position['quantity']
            
            if quantity > 0:
                profit_amount = (sell_price - buy_price) * quantity
                profit_percent = ((sell_price - buy_price) / buy_price) * 100
            else:
                profit_amount = 0
                profit_percent = ((sell_price - buy_price) / buy_price) * 100
            
            # Atualiza dados da posição
            position.update({
                "sell_price": sell_price,
                "current_price": sell_price,
                "profit_percent": profit_percent,
                "profit_amount": profit_amount,
                "close_time": datetime.now(timezone.utc).isoformat(),
                "status": "closed",
                "close_reason": reason,
                "notes": f"{position.get('notes', '')} | Venda em ${sell_price:.4f} ({reason})"
            })
            
            # Move para posições fechadas
            if symbol not in self.positions['closed_positions']:
                self.positions['closed_positions'][symbol] = []
            
            self.positions['closed_positions'][symbol].append(position)
            del self.positions['open_positions'][symbol]
            
            self.save_positions()
            
            logger.info(f"Posição fechada: {symbol} | Lucro: {profit_percent:.2f}% (${profit_amount:.2f}) | Motivo: {reason}")
            return position
            
        except Exception as e:
            logger.error(f"Erro ao fechar posição {symbol}: {e}")
            return None
    
    def update_position_price(self, symbol: str, current_price: float) -> bool:
        """Atualiza preço atual de uma posição"""
        try:
            if symbol not in self.positions['open_positions']:
                return False
            
            position = self.positions['open_positions'][symbol]
            buy_price = position['buy_price']
            quantity = position['quantity']
            
            # Calcula lucro atual
            if quantity > 0:
                profit_amount = (current_price - buy_price) * quantity
                profit_percent = ((current_price - buy_price) / buy_price) * 100
            else:
                profit_amount = 0
                profit_percent = ((current_price - buy_price) / buy_price) * 100
            
            # Atualiza trailing stop se ativado
            settings = self.positions.get('settings', {})
            if settings.get('trailing_stop', True) and current_price > position.get('highest_price', buy_price):
                # Atualiza maior preço
                position['highest_price'] = current_price
                
                # Calcula novo trailing stop
                trailing_distance = (position['stop_loss'] - buy_price) / buy_price
                new_trailing_stop = current_price * (1 - abs(trailing_distance))
                position['trailing_stop'] = max(position['trailing_stop'], new_trailing_stop)
            
            # Atualiza posição
            position.update({
                "current_price": current_price,
                "profit_percent": profit_percent,
                "profit_amount": profit_amount
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar posição {symbol}: {e}")
            return False
    
    def check_sell_signals(self, symbol: str, analysis_result: Dict) -> Tuple[bool, str, float]:
        """Verifica sinais de venda baseados na análise"""
        try:
            if symbol not in self.positions['open_positions']:
                return False, "Posição não encontrada", 0.0
            
            position = self.positions['open_positions'][symbol]
            current_price = analysis_result.get('price', position['current_price'])
            
            # Atualiza preço atual
            self.update_position_price(symbol, current_price)
            
            # 1. REVERSÃO DE BAIXA FORTE (prioridade máxima)
            if analysis_result.get('sinal_saida', False):
                nivel = analysis_result.get('nivel_saida', 'atencao')
                motivo = analysis_result.get('motivo_saida', '')
                
                if nivel == 'urgente':
                    return True, f"VENDA URGENTE: {motivo}", current_price
                elif nivel == 'atencao':
                    # Verifica se já tem lucro mínimo
                    if position['profit_percent'] >= self.positions.get('settings', {}).get('min_profit', 2.0):
                        return True, f"VENDA COM LUCRO: {motivo} (Lucro: {position['profit_percent']:.2f}%)", current_price
            
            # 2. TAKE PROFIT
            if current_price >= position['take_profit']:
                return True, f"TAKE PROFIT: Alvo de {((position['take_profit']/position['buy_price'])-1)*100:.1f}% atingido", current_price
            
            # 3. STOP LOSS
            stop_loss_to_use = position.get('trailing_stop', position['stop_loss'])
            if current_price <= stop_loss_to_use:
                return True, f"STOP LOSS: Perda máxima de {((position['buy_price']-stop_loss_to_use)/position['buy_price'])*100:.1f}% atingida", current_price
            
            # 4. REVERSÃO TÉCNICA (RSI alto + EMA cruzada)
            rsi = analysis_result.get('rsi', 50)
            ema_9 = analysis_result.get('ema_9', 0)
            ema_21 = analysis_result.get('ema_21', 0)
            
            if (rsi > 70 and ema_9 < ema_21 and position['profit_percent'] > 1.0):
                return True, f"REVERSÃO TÉCNICA: RSI={rsi:.1f}, EMA9<EMA21 (Lucro: {position['profit_percent']:.2f}%)", current_price
            
            # 5. PADRÕES DE CANDLESTICK DE VENDA
            if analysis_result.get('is_shooting_star', False) and position['profit_percent'] > 0.5:
                return True, f"SHOOTING STAR: Padrão de reversão (Lucro: {position['profit_percent']:.2f}%)", current_price
            
            if analysis_result.get('is_falling_candle', False) and position['profit_percent'] > 1.0:
                return True, f"QUEDA FORTE: Candle de baixa (Lucro: {position['profit_percent']:.2f}%)", current_price
            
            return False, "MANTER: Sem sinal de venda", current_price
            
        except Exception as e:
            logger.error(f"Erro ao verificar sinais de venda para {symbol}: {e}")
            return False, f"Erro na verificação: {e}", 0.0
    
    def get_open_positions(self) -> Dict:
        """Retorna posições abertas"""
        return self.positions.get('open_positions', {})
    
    def get_closed_positions(self) -> Dict:
        """Retorna posições fechadas"""
        return self.positions.get('closed_positions', {})
    
    def get_position_summary(self) -> Dict:
        """Retorna resumo das posições"""
        open_pos = self.get_open_positions()
        closed_pos = self.get_closed_positions()
        
        # Métricas posições abertas
        open_count = len(open_pos)
        open_profit = sum(pos.get('profit_amount', 0) for pos in open_pos.values())
        open_profit_percent = sum(pos.get('profit_percent', 0) for pos in open_pos.values()) / open_count if open_count > 0 else 0
        
        # Métricas posições fechadas
        all_closed = []
        for symbol_positions in closed_pos.values():
            all_closed.extend(symbol_positions)
        
        closed_count = len(all_closed)
        closed_profit = sum(pos.get('profit_amount', 0) for pos in all_closed)
        closed_profit_percent = sum(pos.get('profit_percent', 0) for pos in all_closed) / closed_count if closed_count > 0 else 0
        
        # Win rate
        wins = len([pos for pos in all_closed if pos.get('profit_percent', 0) > 0])
        win_rate = (wins / closed_count * 100) if closed_count > 0 else 0
        
        return {
            "open_positions": open_count,
            "open_profit": open_profit,
            "open_profit_percent": open_profit_percent,
            "closed_positions": closed_count,
            "closed_profit": closed_profit,
            "closed_profit_percent": closed_profit_percent,
            "total_profit": open_profit + closed_profit,
            "win_rate": win_rate,
            "wins": wins,
            "losses": closed_count - wins
        }

# Instância global do gestor de posições
position_manager = PositionManager()
