# Fichero: game/poker_hands.py
# VERSIÓN CORREGIDA Y MEJORADA

from typing import List, Tuple, Dict
from itertools import combinations

class PokerHandEvaluator:
    def __init__(self):
        self.card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                              '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        self.hand_names = {
            10: "Escalera Real",
            9: "Escalera de Color",
            8: "Póker",
            7: "Full House",
            6: "Color",
            5: "Escalera",
            4: "Trío",
            3: "Doble Pareja",
            2: "Pareja",
            1: "Carta Alta"
        }

    def evaluate_hand(self, hand: List[str], community_cards: List[str]) -> Tuple[int, List[int], str]:
        """
        Evalúa la mejor mano de 5 cartas posible de una combinación de 7 cartas (Texas Hold'em).
        Retorna el ranking, los valores de desempate y el nombre de la mano.
        """
        all_cards = hand + community_cards
        best_hand_rank = (0, [], "Nada")

        # Generar todas las combinaciones posibles de 5 cartas
        if len(all_cards) < 5:
            return best_hand_rank
            
        for combo in combinations(all_cards, 5):
            current_rank = self._evaluate_five_card_hand(list(combo))
            # Comparar con la mejor mano encontrada hasta ahora
            if self._compare_ranks(current_rank, best_hand_rank) > 0:
                best_hand_rank = current_rank
                
        return best_hand_rank

    def _evaluate_five_card_hand(self, hand: List[str]) -> Tuple[int, List[int], str]:
        """Evalúa una mano específica de 5 cartas."""
        values = sorted([self.get_card_value(c) for c in hand], reverse=True)
        suits = [self.get_card_suit(c) for c in hand]
        
        is_flush = len(set(suits)) == 1
        is_straight, straight_values = self._is_straight(values)
        
        # Si es escalera, usamos los valores corregidos (para el caso de A-5)
        if is_straight:
            values = straight_values

        if is_straight and is_flush:
            if values[0] == 14: # As-alto (Royal Flush)
                return 10, values, self.hand_names[10]
            return 9, values, self.hand_names[9]

        counts = self._count_values(values)
        sorted_counts = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
        
        if sorted_counts[0][1] == 4: # Four of a Kind
            kickers = [v for v in values if v != sorted_counts[0][0]]
            return 8, [sorted_counts[0][0], kickers[0]], self.hand_names[8]
        
        if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2: # Full House
            return 7, [sorted_counts[0][0], sorted_counts[1][0]], self.hand_names[7]

        if is_flush:
            return 6, values, self.hand_names[6]

        if is_straight:
            return 5, values, self.hand_names[5]

        if sorted_counts[0][1] == 3: # Three of a Kind
            kickers = sorted([v for v in values if v != sorted_counts[0][0]], reverse=True)
            return 4, [sorted_counts[0][0]] + kickers, self.hand_names[4]

        if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2: # Two Pair
            pairs = sorted([sorted_counts[0][0], sorted_counts[1][0]], reverse=True)
            kicker = [v for v in values if v not in pairs][0]
            return 3, pairs + [kicker], self.hand_names[3]

        if sorted_counts[0][1] == 2: # One Pair
            pair_value = sorted_counts[0][0]
            kickers = sorted([v for v in values if v != pair_value], reverse=True)
            return 2, [pair_value] + kickers, self.hand_names[2]

        return 1, values, self.hand_names[1]

    def get_card_value(self, card: str) -> int:
        value_str = card[:-1]
        return self.card_values[value_str]

    def get_card_suit(self, card: str) -> str:
        return card[-1]

    def _is_straight(self, values: List[int]) -> Tuple[bool, List[int]]:
        """Verifica si hay escalera y devuelve los valores correctos para el As-bajo."""
        # Caso especial para A-2-3-4-5
        if set(values) == {14, 2, 3, 4, 5}:
            return True, [5, 4, 3, 2, 14] # El 5 es la carta alta
        # Escalera normal
        unique_values = sorted(list(set(values)), reverse=True)
        if len(unique_values) < 5:
            return False, values
            
        for i in range(len(unique_values) - 4):
            if unique_values[i] - unique_values[i+4] == 4:
                return True, unique_values[i:i+5]

        return False, values

    def _count_values(self, values: List[int]) -> Dict[int, int]:
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        return counts

    def _compare_ranks(self, rank1: Tuple, rank2: Tuple) -> int:
        """Compara dos rangos de manos. Devuelve 1 si rank1 es mejor, -1 si rank2 es mejor, 0 si son iguales."""
        r1, v1, _ = rank1
        r2, v2, _ = rank2
        
        if r1 > r2: return 1
        if r1 < r2: return -1
        
        # Mismo rango, comparar valores de desempate (kickers)
        for val1, val2 in zip(v1, v2):
            if val1 > val2: return 1
            if val1 < val2: return -1
            
        return 0