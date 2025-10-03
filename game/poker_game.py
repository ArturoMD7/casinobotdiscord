import random
import asyncio
from typing import Dict, List, Optional

class PokerGame:
    def __init__(self, game_id: str, creator_id: int, min_bet: int = 50):
        self.game_id = game_id
        self.creator_id = creator_id
        self.min_bet = min_bet
        self.small_blind = min_bet // 2
        self.big_blind = min_bet
        
        # Estado del juego
        self.players: Dict[int, dict] = {}
        self.spectators: List[int] = []
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_position = 0
        self.current_player_index = 0
        self.game_phase = "waiting"  # waiting, preflop, flop, turn, river, showdown
        self.game_started = False
        
        # Temporizador
        self.timer_task = None
        
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
            
        self.players[user_id] = {
            "name": user_name,
            "chips": 1000,  # Fichas iniciales
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
        
        # Repartir cartas a los jugadores
        for player_id in self.players:
            self.players[player_id]["hand"] = [self.deck.pop(), self.deck.pop()]
            self.players[player_id]["folded"] = False
            self.players[player_id]["all_in"] = False
            self.players[player_id]["bet"] = 0
            self.players[player_id]["total_bet"] = 0
        
        # Aplicar blinds automáticamente
        player_ids = list(self.players.keys())
        small_blind_player = player_ids[self.dealer_position]
        big_blind_player = player_ids[(self.dealer_position + 1) % len(player_ids)]
        
        self.hacer_apuesta(small_blind_player, self.small_blind)
        self.hacer_apuesta(big_blind_player, self.big_blind)
        
        # Primer jugador después del big blind
        self.current_player_index = (self.dealer_position + 2) % len(player_ids)
        
        return True
    
    def hacer_apuesta(self, player_id: int, cantidad: int) -> bool:
        """Realiza una apuesta"""
        if player_id not in self.players:
            return False
            
        player = self.players[player_id]
        
        if cantidad > player["chips"]:
            return False
            
        player["chips"] -= cantidad
        player["bet"] += cantidad
        player["total_bet"] += cantidad
        self.pot += cantidad
        
        # Actualizar apuesta actual si es mayor
        if player["bet"] > self.current_bet:
            self.current_bet = player["bet"]
            
        return True
    
    def fold(self, player_id: int) -> bool:
        """Un jugador se retira de la mano"""
        if player_id not in self.players:
            return False
            
        self.players[player_id]["folded"] = True
        return True
    
    def check(self, player_id: int) -> bool:
        """Un jugador pasa si no hay que igualar"""
        if player_id not in self.players:
            return False
            
        player = self.players[player_id]
        return player["bet"] >= self.current_bet
    
    def call(self, player_id: int) -> bool:
        """Un jugador iguala la apuesta actual"""
        if player_id not in self.players:
            return False
            
        player = self.players[player_id]
        cantidad_a_igualar = self.current_bet - player["bet"]
        
        if cantidad_a_igualar <= 0:
            return self.check(player_id)
            
        return self.hacer_apuesta(player_id, cantidad_a_igualar)
    
    def raise_bet(self, player_id: int, cantidad: int) -> bool:
        """Un jugador sube la apuesta"""
        if player_id not in self.players:
            return False
            
        cantidad_total = self.current_bet - self.players[player_id]["bet"] + cantidad
        
        if cantidad_total < self.min_bet:
            return False
            
        return self.hacer_apuesta(player_id, cantidad_total)
    
    def siguiente_fase(self):
        """Avanza a la siguiente fase del juego"""
        if self.game_phase == "preflop":
            self.game_phase = "flop"
            # Repartir flop (3 cartas comunitarias)
            for _ in range(3):
                self.community_cards.append(self.deck.pop())
                
        elif self.game_phase == "flop":
            self.game_phase = "turn"
            # Repartir turn (1 carta)
            self.community_cards.append(self.deck.pop())
            
        elif self.game_phase == "turn":
            self.game_phase = "river"
            # Repartir river (1 carta)
            self.community_cards.append(self.deck.pop())
            
        elif self.game_phase == "river":
            self.game_phase = "showdown"
            # Determinar ganador
            return self.determinar_ganador()
        
        # Reiniciar apuestas para nueva ronda
        for player_id in self.players:
            self.players[player_id]["bet"] = 0
        self.current_bet = 0
        
        return None
    
    def determinar_ganador(self):
        """Determina el ganador de la mano (simplificado)"""
        # Por ahora, ganador aleatorio entre los que no se retiraron
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"]]
        
        if not jugadores_activos:
            return None
            
        ganador_id = random.choice(jugadores_activos)
        self.players[ganador_id]["chips"] += self.pot
        self.pot = 0
        
        return ganador_id
    
    def siguiente_turno(self):
        """Avanza al siguiente jugador"""
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"] and not p["all_in"]]
        
        if not jugadores_activos:
            return False
            
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        # Si todos han jugado, avanzar fase
        current_player_id = list(self.players.keys())[self.current_player_index]
        if current_player_id == list(self.players.keys())[self.dealer_position]:
            ganador = self.siguiente_fase()
            if ganador:
                return ganador
                
        return True
    
    def obtener_estado_juego(self) -> dict:
        """Retorna el estado actual del juego para la interfaz"""
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