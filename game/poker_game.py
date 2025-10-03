import random
import asyncio
from typing import Dict, List, Optional, Tuple
from db.database import Database
from game.poker_hands import PokerHandEvaluator

db = Database()

class PokerGame:
    def __init__(self, game_id: str, creator_id: int, min_bet: int = 50):
        self.game_id = game_id
        self.creator_id = creator_id
        self.min_bet = min_bet
        self.small_blind = min_bet // 2
        self.big_blind = min_bet
        self.evaluator = PokerHandEvaluator()
        
        # Estado del juego
        self.players: Dict[int, dict] = {}
        self.spectators: List[int] = []
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_position = 0
        self.current_player_index = 0
        self.game_phase = "waiting"
        self.game_started = False
        
    def crear_mazo(self) -> List[str]:
        """Crea y baraja un mazo de cartas"""
        palos = ['♠', '♥', '♦', '♣']
        valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        mazo = [f"{valor}{palo}" for valor in valores for palo in palos]
        random.shuffle(mazo)
        return mazo
    
    def agregar_jugador(self, user_id: int, user_name: str) -> bool:
        """Agrega un jugador al juego"""
        if len(self.players) >= 6:
            return False
            
        if user_id in self.players:
            return False
        
        credits = db.get_credits(user_id)
        if credits < self.min_bet * 10:
            return False
            
        self.players[user_id] = {
            "name": user_name,
            "chips": credits,
            "hand": [],
            "folded": False,
            "all_in": False,
            "bet": 0,
            "total_bet": 0
        }
        return True
    
    def empezar_juego(self) -> bool:
        """Inicia el juego si hay suficientes jugadores"""
        if len(self.players) < 2:
            return False
            
        self.game_started = True
        self.game_phase = "preflop"
        self.deck = self.crear_mazo()
        self.community_cards = []
        self.pot = 0
        self.current_bet = self.big_blind
        
        # Repartir cartas
        for player_id in self.players:
            self.players[player_id]["hand"] = [self.deck.pop(), self.deck.pop()]
            self.players[player_id]["folded"] = False
            self.players[player_id]["all_in"] = False
            self.players[player_id]["bet"] = 0
            self.players[player_id]["total_bet"] = 0
        
        # Aplicar blinds
        player_ids = list(self.players.keys())
        small_blind_player = player_ids[self.dealer_position]
        big_blind_player = player_ids[(self.dealer_position + 1) % len(player_ids)]
        
        self.hacer_apuesta(small_blind_player, self.small_blind)
        self.hacer_apuesta(big_blind_player, self.big_blind)
        
        self.current_player_index = (self.dealer_position + 2) % len(player_ids)
        return True
    
    def hacer_apuesta(self, player_id: int, cantidad: int) -> bool:
        """Realiza una apuesta usando créditos reales"""
        if player_id not in self.players:
            return False
            
        player = self.players[player_id]
        
        if cantidad > player["chips"]:
            return False
        
        success = db.update_credits(player_id, -cantidad, "bet", "poker", f"Apuesta poker: {cantidad}")
        if not success:
            return False
            
        player["chips"] -= cantidad
        player["bet"] += cantidad
        player["total_bet"] += cantidad
        self.pot += cantidad
        
        if player["bet"] > self.current_bet:
            self.current_bet = player["bet"]
            
        return True
    
    def entregar_premio(self, player_id: int, cantidad: int):
        """Entrega el premio al ganador"""
        if player_id not in self.players:
            return False
            
        success = db.update_credits(player_id, cantidad, "win", "poker", f"Ganador poker: {cantidad}")
        if success:
            self.players[player_id]["chips"] += cantidad
        return success
    
    def determinar_ganador(self) -> List[Tuple[int, int]]:
        """Determina el ganador o ganadores de la mano"""
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"]]
        
        if not jugadores_activos:
            return []
        
        # Evaluar manos de todos los jugadores activos
        manos_evaluadas = []
        for player_id in jugadores_activos:
            mano = self.players[player_id]["hand"]
            evaluacion = self.evaluator.evaluar_mano(mano, self.community_cards)
            manos_evaluadas.append((player_id, evaluacion))
        
        # Encontrar la mejor mano
        mejor_mano = max(manos_evaluadas, key=lambda x: (x[1][0], x[1][1]))
        mejor_ranking = mejor_mano[1][0]
        mejores_valores = mejor_mano[1][1]
        
        # Encontrar todos los jugadores con la mejor mano
        ganadores = []
        for player_id, (ranking, valores, nombre) in manos_evaluadas:
            if ranking == mejor_ranking:
                # Verificar si los valores de desempate son iguales
                if valores == mejores_valores:
                    ganadores.append(player_id)
        
        # Repartir el pozo entre los ganadores
        premio_por_ganador = self.pot // len(ganadores)
        resultados = []
        
        for ganador_id in ganadores:
            # Aplicar multiplicador del Gacha
            premio_final = premio_por_ganador
            gacha_cog = self._get_gacha_cog()
            
            if gacha_cog and premio_por_ganador > 0:
                multiplicador = gacha_cog.obtener_multiplicador_activo(ganador_id)
                if multiplicador > 1.0:
                    premio_final = gacha_cog.aplicar_multiplicador_ganancias(ganador_id, premio_por_ganador)
            
            # Entregar premio
            success = self.entregar_premio(ganador_id, premio_final)
            if success:
                resultados.append((ganador_id, premio_final))
        
        self.pot = 0
        return resultados
    
    def _get_gacha_cog(self):
        """Obtiene el cog de Gacha si está disponible"""
        # Esto se implementará en el cog principal
        return None
    
    def obtener_info_manos(self) -> List[Tuple[str, str, List[str]]]:
        """Retorna información de las manos para mostrar al final"""
        info = []
        for player_id, player in self.players.items():
            if not player["folded"]:
                mano = player["hand"]
                evaluacion = self.evaluator.evaluar_mano(mano, self.community_cards)
                ranking, valores, nombre_mano = evaluacion
                info.append((player["name"], nombre_mano, mano))
        return info
    
    # Los demás métodos permanecen igual...
    def fold(self, player_id: int) -> bool:
        if player_id not in self.players:
            return False
        self.players[player_id]["folded"] = True
        return True
    
    def check(self, player_id: int) -> bool:
        if player_id not in self.players:
            return False
        player = self.players[player_id]
        return player["bet"] >= self.current_bet
    
    def call(self, player_id: int) -> bool:
        if player_id not in self.players:
            return False
        player = self.players[player_id]
        cantidad_a_igualar = self.current_bet - player["bet"]
        if cantidad_a_igualar <= 0:
            return self.check(player_id)
        return self.hacer_apuesta(player_id, cantidad_a_igualar)
    
    def raise_bet(self, player_id: int, cantidad: int) -> bool:
        if player_id not in self.players:
            return False
        cantidad_total = self.current_bet - self.players[player_id]["bet"] + cantidad
        if cantidad_total < self.min_bet:
            return False
        return self.hacer_apuesta(player_id, cantidad_total)
    
    def siguiente_fase(self):
        if self.game_phase == "preflop":
            self.game_phase = "flop"
            for _ in range(3):
                self.community_cards.append(self.deck.pop())
        elif self.game_phase == "flop":
            self.game_phase = "turn"
            self.community_cards.append(self.deck.pop())
        elif self.game_phase == "turn":
            self.game_phase = "river"
            self.community_cards.append(self.deck.pop())
        elif self.game_phase == "river":
            self.game_phase = "showdown"
            return self.determinar_ganador()
        
        for player_id in self.players:
            self.players[player_id]["bet"] = 0
        self.current_bet = 0
        return None
    
    def siguiente_turno(self):
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"] and not p["all_in"]]
        if not jugadores_activos:
            return False
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        current_player_id = list(self.players.keys())[self.current_player_index]
        if current_player_id == list(self.players.keys())[self.dealer_position]:
            ganador = self.siguiente_fase()
            if ganador:
                return ganador
        return True
    
    def obtener_estado_juego(self) -> dict:
        return {
            "game_id": self.game_id,
            "phase": self.game_phase,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "community_cards": self.community_cards,
            "players": {
                pid: {
                    "name": p["name"],
                    "chips": p["chips"],
                    "hand": p["hand"] if self.game_phase == "showdown" else ["??", "??"],
                    "folded": p["folded"],
                    "all_in": p["all_in"],
                    "bet": p["bet"],
                    "is_turn": pid == list(self.players.keys())[self.current_player_index]
                }
                for pid, p in self.players.items()
            },
            "current_player": list(self.players.keys())[self.current_player_index] if self.players else None
        }
    
    def puede_unirse(self, user_id: int) -> bool:
        if user_id in self.players:
            return False
        credits = db.get_credits(user_id)
        return credits >= self.min_bet * 10