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
        
        # Verificar créditos mínimos
        credits = db.get_credits(user_id)
        if credits < self.min_bet * 10:
            return False
            
        self.players[user_id] = {
            "name": user_name,
            "chips": 1000,  # Fichas iniciales para el juego
            "credits": credits,
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
        
        # Resetear estado de todos los jugadores
        for player_id in self.players:
            self.players[player_id]["hand"] = [self.deck.pop(), self.deck.pop()]
            self.players[player_id]["folded"] = False
            self.players[player_id]["all_in"] = False
            self.players[player_id]["bet"] = 0
            self.players[player_id]["total_bet"] = 0
        
        # Aplicar blinds
        player_ids = list(self.players.keys())
        
        # Small blind
        small_blind_player = player_ids[self.dealer_position]
        self.hacer_apuesta(small_blind_player, self.small_blind)
        
        # Big blind
        big_blind_player = player_ids[(self.dealer_position + 1) % len(player_ids)]
        self.hacer_apuesta(big_blind_player, self.big_blind)
        
        # El primer jugador después del big blind inicia
        self.current_player_index = (self.dealer_position + 2) % len(player_ids)
        return True
    
    def hacer_apuesta(self, player_id: int, cantidad: int) -> bool:
        """Realiza una apuesta usando fichas del juego"""
        if player_id not in self.players:
            return False
            
        player = self.players[player_id]
        
        if cantidad > player["chips"]:
            # Si no tiene suficientes fichas, va all-in
            cantidad = player["chips"]
            player["all_in"] = True
        
        player["chips"] -= cantidad
        player["bet"] += cantidad
        player["total_bet"] += cantidad
        self.pot += cantidad
        
        if player["bet"] > self.current_bet:
            self.current_bet = player["bet"]
            
        return True
    
    def determinar_ganador(self) -> List[Tuple[int, int]]:
        """Determina el ganador o ganadores de la mano"""
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"]]
        
        if not jugadores_activos:
            return []
        
        # Si solo queda un jugador activo, gana automáticamente
        if len(jugadores_activos) == 1:
            ganador_id = jugadores_activos[0]
            premio_en_creditos = self.pot
            success = db.update_credits(ganador_id, premio_en_creditos, "win", "poker", f"Ganador poker: {premio_en_creditos}")
            if success:
                return [(ganador_id, premio_en_creditos)]
            return []
        
        # Evaluar manos de todos los jugadores activos
        manos_evaluadas = []
        for player_id in jugadores_activos:
            mano = self.players[player_id]["hand"]
            evaluacion = self.evaluator.evaluar_mano(mano, self.community_cards)
            manos_evaluadas.append((player_id, evaluacion))
        
        # Ordenar manos por ranking (mejor primero)
        manos_ordenadas = sorted(manos_evaluadas, key=lambda x: (x[1][0], x[1][1]), reverse=True)
        
        # Encontrar ganadores (puede haber empate)
        mejor_ranking = manos_ordenadas[0][1][0]
        mejor_valor = manos_ordenadas[0][1][1]
        
        ganadores = []
        for player_id, (ranking, valores, _) in manos_ordenadas:
            if ranking == mejor_ranking and valores == mejor_valor:
                ganadores.append(player_id)
        
        # Distribuir el pozo entre ganadores
        resultados = []
        premio_por_ganador = self.pot // len(ganadores)
        
        for ganador_id in ganadores:
            premio_en_creditos = premio_por_ganador
            success = db.update_credits(ganador_id, premio_en_creditos, "win", "poker", f"Ganador poker: {premio_en_creditos}")
            if success:
                resultados.append((ganador_id, premio_en_creditos))
        
        self.pot = 0
        return resultados
    
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
    
    def fold(self, player_id: int) -> bool:
        """Jugador se retira de la mano"""
        if player_id not in self.players:
            return False
        self.players[player_id]["folded"] = True
        return True
    
    def call(self, player_id: int) -> bool:
        """Jugador iguala la apuesta actual"""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        cantidad_a_igualar = self.current_bet - player["bet"]
        
        if cantidad_a_igualar <= 0:
            return True  # Check
        
        if cantidad_a_igualar > player["chips"]:
            # All-in
            cantidad_a_igualar = player["chips"]
            player["all_in"] = True
        
        return self.hacer_apuesta(player_id, cantidad_a_igualar)
    
    def raise_bet(self, player_id: int, cantidad: int) -> bool:
        """Jugador sube la apuesta"""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        cantidad_total = self.current_bet - player["bet"] + cantidad
        
        # Verificar que la subida sea válida
        if cantidad < self.min_bet:
            return False
        
        if cantidad_total > player["chips"]:
            # All-in
            cantidad_total = player["chips"]
            player["all_in"] = True
        
        return self.hacer_apuesta(player_id, cantidad_total)
    
    def siguiente_fase(self):
        """Avanza a la siguiente fase del juego"""
        if self.game_phase == "preflop":
            self.game_phase = "flop"
            for _ in range(3):
                if self.deck:
                    self.community_cards.append(self.deck.pop())
        elif self.game_phase == "flop":
            self.game_phase = "turn"
            if self.deck:
                self.community_cards.append(self.deck.pop())
        elif self.game_phase == "turn":
            self.game_phase = "river"
            if self.deck:
                self.community_cards.append(self.deck.pop())
        elif self.game_phase == "river":
            self.game_phase = "showdown"
            return self.determinar_ganador()
        
        # Resetear apuestas para nueva ronda
        for player_id in self.players:
            self.players[player_id]["bet"] = 0
        self.current_bet = 0
        
        # Empezar desde el dealer
        self.current_player_index = self.dealer_position
        return None
    
    def siguiente_turno(self):
        """Avanza al siguiente turno"""
        # Verificar si el juego debe terminar
        jugadores_activos = [pid for pid, p in self.players.items() if not p["folded"] and not p["all_in"]]
        
        if len(jugadores_activos) <= 1:
            # Solo queda un jugador activo o todos all-in, terminar juego
            return self.determinar_ganador()
        
        # Encontrar siguiente jugador activo
        jugadores_orden = list(self.players.keys())
        intentos = 0
        jugador_encontrado = False
        
        while intentos < len(self.players) and not jugador_encontrado:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            current_player_id = jugadores_orden[self.current_player_index]
            
            player = self.players[current_player_id]
            if not player["folded"] and not player["all_in"]:
                jugador_encontrado = True
            intentos += 1
        
        if not jugador_encontrado:
            # No hay más jugadores activos, avanzar fase
            resultado_fase = self.siguiente_fase()
            if resultado_fase:
                return resultado_fase
            else:
                # Continuar con el siguiente turno después de cambiar fase
                return self.siguiente_turno()
        
        # Verificar si hemos completado una ronda (volvemos al primer jugador después del dealer)
        if self.current_player_index == self.dealer_position:
            resultado_fase = self.siguiente_fase()
            if resultado_fase:
                return resultado_fase
        
        return True
    
    def obtener_estado_juego(self) -> dict:
        """Obtiene el estado actual del juego para mostrar"""
        current_player_id = None
        if self.players and 0 <= self.current_player_index < len(self.players):
            current_player_id = list(self.players.keys())[self.current_player_index]
        
        estado_players = {}
        for pid, player in self.players.items():
            estado_players[pid] = {
                "name": player["name"],
                "chips": player["chips"],
                "hand": player["hand"],
                "folded": player["folded"],
                "all_in": player["all_in"],
                "bet": player["bet"],
                "is_turn": pid == current_player_id
            }
        
        return {
            "game_id": self.game_id,
            "phase": self.game_phase,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "community_cards": self.community_cards,
            "players": estado_players,
            "current_player": current_player_id
        }
    
    def obtener_mano_jugador(self, player_id: int) -> List[str]:
        """Obtiene la mano de un jugador específico"""
        if player_id in self.players:
            return self.players[player_id]["hand"]
        return []
    
    def puede_unirse(self, user_id: int) -> bool:
        """Verifica si un usuario puede unirse al juego"""
        if user_id in self.players:
            return False
        credits = db.get_credits(user_id)
        return credits >= self.min_bet * 10