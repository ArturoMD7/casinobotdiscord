import random
from typing import List, Tuple, Dict

class BlackjackGame:
    def __init__(self, bet: int, user_id: int):
        self.deck = self.generate_deck()
        self.player_hand: List[str] = []
        self.dealer_hand: List[str] = []
        self.bet = bet
        self.user_id = user_id
        self.finished = False
        self.result = None
        self.payout = 0

        # Repartir cartas iniciales
        self.player_hand.append(self.draw_card())
        self.player_hand.append(self.draw_card())
        self.dealer_hand.append(self.draw_card())
        self.dealer_hand.append(self.draw_card())

    def generate_deck(self) -> List[str]:
        """Genera un mazo de 6 barajas para mejor aleatoriedad"""
        suits = ["♠", "♥", "♦", "♣"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [f"{value}{suit}" for value in values for suit in suits] * 6
        random.shuffle(deck)
        return deck

    def draw_card(self) -> str:
        """Roba una carta del mazo"""
        if len(self.deck) < 15:
            self.deck = self.generate_deck()  # Rebarajar si quedan pocas cartas
        return self.deck.pop()

    def hand_value(self, hand: List[str]) -> Tuple[int, bool]:
        """Calcula el valor de una mano y si es soft (contiene As contado como 11)"""
        value = 0
        aces = 0
        
        for card in hand:
            rank = card[:-1]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                value += 11
                aces += 1
            else:
                value += int(rank)
        
        # Ajustar Ases si nos pasamos de 21
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        soft = aces > 0 and value <= 21
        return value, soft

    def can_double(self) -> bool:
        """Verifica si el jugador puede hacer double down"""
        return len(self.player_hand) == 2

    def can_split(self) -> bool:
        """Verifica si el jugador puede hacer split"""
        if len(self.player_hand) == 2:
            rank1 = self.player_hand[0][:-1]
            rank2 = self.player_hand[1][:-1]
            return rank1 == rank2
        return False

    def player_hit(self) -> Tuple[str, int, bool]:
        """Jugador pide carta"""
        self.player_hand.append(self.draw_card())
        value, _ = self.hand_value(self.player_hand)
        
        if value > 21:
            self.finished = True
            self.result = "loss"
            self.payout = -self.bet
            return "bust", value, True
        else:
            return "hit", value, False

    def player_stand(self) -> str:
        """Jugador se planta"""
        self.finished = True
        return self._determine_result()

    def player_double_down(self) -> Tuple[str, int]:
        """Jugador hace double down"""
        if not self.can_double():
            return "cannot_double", 0
        
        self.bet *= 2
        self.player_hand.append(self.draw_card())
        value, _ = self.hand_value(self.player_hand)
        
        if value > 21:
            self.result = "loss"
            self.payout = -self.bet
            return "bust", value
        else:
            result = self._determine_result()
            return result, value

    def _determine_result(self) -> str:
        """Determina el resultado final del juego"""
        # La banca juega automáticamente
        while self.hand_value(self.dealer_hand)[0] < 17:
            self.dealer_hand.append(self.draw_card())

        player_value, player_soft = self.hand_value(self.player_hand)
        dealer_value, dealer_soft = self.hand_value(self.dealer_hand)

        # Blackjack natural (21 con 2 cartas)
        player_blackjack = player_value == 21 and len(self.player_hand) == 2
        dealer_blackjack = dealer_value == 21 and len(self.dealer_hand) == 2

        if player_blackjack and not dealer_blackjack:
            self.result = "blackjack"
            self.payout = int(self.bet * 1.5)  # Pago 3:2 para blackjack
        elif dealer_blackjack and not player_blackjack:
            self.result = "loss"
            self.payout = -self.bet
        elif player_blackjack and dealer_blackjack:
            self.result = "push"
            self.payout = 0
        elif player_value > 21:
            self.result = "loss"
            self.payout = -self.bet
        elif dealer_value > 21:
            self.result = "win"
            self.payout = self.bet
        elif player_value > dealer_value:
            self.result = "win"
            self.payout = self.bet
        elif player_value < dealer_value:
            self.result = "loss"
            self.payout = -self.bet
        else:
            self.result = "push"
            self.payout = 0

        return self.result

    def get_game_state(self) -> Dict:
        """Obtiene el estado actual del juego"""
        player_value, player_soft = self.hand_value(self.player_hand)
        dealer_value, dealer_soft = self.hand_value(self.dealer_hand)
        
        return {
            "player_hand": self.player_hand,
            "player_value": player_value,
            "player_soft": player_soft,
            "dealer_hand": self.dealer_hand if self.finished else [self.dealer_hand[0], "❓"],
            "dealer_value": dealer_value if self.finished else self.hand_value([self.dealer_hand[0]])[0],
            "dealer_soft": dealer_soft if self.finished else False,
            "bet": self.bet,
            "finished": self.finished,
            "result": self.result,
            "payout": self.payout,
            "can_double": self.can_double(),
            "can_split": self.can_split()
        }