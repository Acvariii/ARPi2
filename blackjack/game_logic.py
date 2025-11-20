import random
from typing import List, Tuple

class BlackjackLogic:
    
    SUITS = ['S', 'H', 'D', 'C']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    @staticmethod
    def create_deck() -> List[Tuple[str, str]]:
        deck = [(rank, suit) for suit in BlackjackLogic.SUITS for rank in BlackjackLogic.RANKS]
        random.shuffle(deck)
        return deck
    
    @staticmethod
    def card_value(card: Tuple[str, str], current_total: int = 0) -> int:
        rank = card[0]
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11 if current_total + 11 <= 21 else 1
        else:
            return int(rank)
    
    @staticmethod
    def hand_value(hand: List[Tuple[str, str]]) -> int:
        total = 0
        aces = 0
        
        for card in hand:
            rank = card[0]
            if rank == 'A':
                aces += 1
                total += 11
            elif rank in ['J', 'Q', 'K']:
                total += 10
            else:
                total += int(rank)
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    @staticmethod
    def is_blackjack(hand: List[Tuple[str, str]]) -> bool:
        return len(hand) == 2 and BlackjackLogic.hand_value(hand) == 21
    
    @staticmethod
    def can_split(hand: List[Tuple[str, str]]) -> bool:
        if len(hand) != 2:
            return False
        v1 = BlackjackLogic.card_value(hand[0])
        v2 = BlackjackLogic.card_value(hand[1])
        return v1 == v2
    
    @staticmethod
    def can_double_down(hand: List[Tuple[str, str]]) -> bool:
        return len(hand) == 2
