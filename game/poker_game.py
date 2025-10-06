# Fichero: game/poker_game.py

import random
from typing import Dict, List, Optional, Tuple
from game.poker_hands import PokerHandEvaluator
from db.database import Database  # <--- IMPORTACIÓN DE TU CLASE

db = Database() # <--- INSTANCIA DE TU BASE DE DATOS

class PokerGame:
    def __init__(self, game_id: str, creator_id: int, min_bet: int = 50):
        self.game_id = game_id
        self.creator_id = creator_id
        self.min_bet = min_bet
        self.small_blind = min_bet // 2
        self.big_blind = min_bet
        self.evaluator = PokerHandEvaluator()
        
        self.players: Dict[int, dict] = {}
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_pos = -1 # Inicia en -1 para que la primera ronda sea 0
        self.current_player_idx = 0
        self.game_phase = "waiting"
        self.game_started = False
        self.player_order: List[int] = []

    def create_deck(self) -> List[str]:
        # ... (código sin cambios)
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [f"{value}{suit}" for value in values for suit in suits]
        random.shuffle(deck)
        return deck

    def add_player(self, user_id: int, user_name: str) -> bool:
        if len(self.players) >= 6 or user_id in self.players:
            return False
        
        # Usa la DB real para obtener los créditos
        credits = db.get_credits(user_id)
        if credits < self.big_blind * 10:
            return False
            
        self.players[user_id] = {
            "name": user_name, "chips": credits, "hand": [], "folded": False,
            "all_in": False, "bet_this_round": 0, "has_acted": False,
        }
        return True

    def start_game(self) -> bool:
        if len(self.players) < 2: return False
        self.game_started = True
        self.player_order = list(self.players.keys())
        self.start_new_hand()
        return True

    def start_new_hand(self):
        # ... (código sin cambios, prepara la mano)
        self.deck = self.create_deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        
        active_players = {pid: pdata for pid, pdata in self.players.items() if pdata['chips'] > 0}
        self.player_order = [pid for pid in self.player_order if pid in active_players]

        if len(self.player_order) < 2:
            # No hay suficientes jugadores para continuar
            self.game_phase = "ended"
            return
            
        for player_id in self.player_order:
            player = self.players[player_id]
            player["hand"] = [self.deck.pop(), self.deck.pop()]
            player["folded"] = False; player["all_in"] = False; 
            player["bet_this_round"] = 0; player["has_acted"] = False
        
        self.dealer_pos = (self.dealer_pos + 1) % len(self.player_order)
        self._post_blinds()
        self.game_phase = "preflop"
        self.current_player_idx = (self.dealer_pos + 3) % len(self.player_order) if len(self.player_order) > 2 else self.dealer_pos
        self.current_bet = self.big_blind

    def _post_blinds(self):
        num_players = len(self.player_order)
        sb_pos = (self.dealer_pos + 1) % num_players
        bb_pos = (self.dealer_pos + 2) % num_players
        
        self._make_bet(self.player_order[sb_pos], self.small_blind)
        self._make_bet(self.player_order[bb_pos], self.big_blind)

    def get_next_player(self) -> Optional[int]:
        # ... (código sin cambios)
        for _ in range(len(self.player_order)):
            self.current_player_idx = (self.current_player_idx + 1) % len(self.player_order)
            player_id = self.player_order[self.current_player_idx]
            player = self.players[player_id]
            if not player["folded"] and not player["all_in"]:
                return player_id
        return None

    def _make_bet(self, player_id: int, amount: int) -> bool:
        player = self.players[player_id]
        bet_amount = min(amount, player["chips"])
        
        # Usa la DB real para actualizar créditos
        success = db.update_credits(player_id, -bet_amount, "bet", "poker", f"Apuesta poker: {bet_amount}")
        if not success: return False
            
        player["chips"] -= bet_amount
        player["bet_this_round"] += bet_amount
        self.pot += bet_amount
        
        if player["chips"] == 0: player["all_in"] = True
        if player["bet_this_round"] > self.current_bet:
            self.current_bet = player["bet_this_round"]
            for pid in self.player_order:
                p = self.players[pid]
                if pid != player_id and not p["folded"] and not p["all_in"]:
                    p["has_acted"] = False
        return True

    def player_action(self, player_id: int, action: str, amount: int = 0) -> bool:
        # ... (código sin cambios)
        if player_id != self.player_order[self.current_player_idx]: return False
        player = self.players[player_id]
        
        if action == "fold": player["folded"] = True
        elif action == "check":
            if player["bet_this_round"] < self.current_bet: return False
        elif action == "call":
            if not self._make_bet(player_id, self.current_bet - player["bet_this_round"]): return False
        elif action == "raise":
            required_bet = self.current_bet - player["bet_this_round"]
            total_bet = required_bet + amount
            if amount < self.big_blind or total_bet > player['chips']: return False
            if not self._make_bet(player_id, total_bet): return False
        
        player["has_acted"] = True
        return True

    def is_round_over(self) -> bool:
        # ... (código sin cambios)
        active_players = [p for pid, p in self.players.items() if pid in self.player_order and not p["folded"]]
        if len(active_players) <= 1: return True
        
        non_all_in_players = [p for p in active_players if not p["all_in"]]
        if not non_all_in_players: return True

        for p in non_all_in_players:
            if not p["has_acted"] or p["bet_this_round"] != self.current_bet:
                return False
        return True

    def advance_to_next_phase(self):
        # ... (código sin cambios)
        for player in self.players.values():
            player["bet_this_round"] = 0; player["has_acted"] = False
        self.current_bet = 0
        self.current_player_idx = self.dealer_pos
        
        phase_map = {"preflop": "flop", "flop": "turn", "turn": "river", "river": "showdown"}
        self.game_phase = phase_map.get(self.game_phase)

        if self.game_phase == "flop": self.community_cards.extend([self.deck.pop() for _ in range(3)])
        elif self.game_phase in ["turn", "river"]: self.community_cards.append(self.deck.pop())

    def determine_winner(self) -> List[Tuple[int, int, str]]:
        active_players = [(pid, p) for pid, p in self.players.items() if pid in self.player_order and not p["folded"]]
        
        # GANA POR ABANDONO
        if len(active_players) == 1:
            winner_id = active_players[0][0]
            prize = self.pot
            self.award_pot(winner_id, prize, "Ganador por abandono")
            self.record_losses([p[0] for p in self.players.items() if p[0] != winner_id and p[0] in self.player_order])
            return [(winner_id, prize, "Ganador por abandono")]

        # SHOWDOWN
        evaluated_hands = [(pid, self.evaluator.evaluate_hand(p["hand"], self.community_cards)) for pid, p in active_players]
        evaluated_hands.sort(key=lambda x: (x[1][0], x[1][1]), reverse=True)
        
        best_rank = evaluated_hands[0][1]
        winners = [ (pid, rank) for pid, rank in evaluated_hands if self.evaluator._compare_ranks(rank, best_rank) == 0 ]
        
        prize_per_winner = self.pot // len(winners)
        results = []
        winner_ids = [w[0] for w in winners]

        for winner_id, rank in winners:
            self.award_pot(winner_id, prize_per_winner, rank[2])
            results.append((winner_id, prize_per_winner, rank[2]))
        
        loser_ids = [pid for pid in self.player_order if pid not in winner_ids]
        self.record_losses(loser_ids)
        
        self.pot = 0
        return results

    def award_pot(self, player_id: int, amount: int, hand_name: str):
        # Usa la DB real con transaction_type='win'
        db.update_credits(player_id, amount, "win", "poker", f"Gana con {hand_name}")
        if player_id in self.players: self.players[player_id]["chips"] += amount

    def record_losses(self, loser_ids: List[int]):
        # Registra la partida jugada para los perdedores
        for loser_id in loser_ids:
            db.update_credits(loser_id, 0, "loss", "poker", "Participó en la mano")
            
    def get_game_state(self) -> dict:
        player_states = {}
        for pid in self.player_order:
            if pid not in self.players: continue
            p = self.players[pid]
            player_states[pid] = {
                "name": p["name"], "chips": p["chips"],
                "hand": p["hand"] if self.game_phase == "showdown" else [],
                "folded": p["folded"], "all_in": p["all_in"], "bet": p["bet_this_round"],
                "is_turn": pid == (self.player_order[self.current_player_idx] if self.player_order else None) and self.game_phase != "showdown",
            }
        return {
            "game_id": self.game_id, "phase": self.game_phase, "pot": self.pot, "current_bet": self.current_bet,
            "community_cards": self.community_cards, "players": player_states,
            "current_player_id": self.player_order[self.current_player_idx] if self.player_order and self.game_started else None
        }