class BlackjackPlayer:
    
    def __init__(self, idx: int, color: tuple):
        self.idx = idx
        self.color = color
        self.chips = 1000
        self.current_bet = 0
        self.hands = []
        self.is_active = True
        self.is_busted = False
        self.is_standing = False
        self.current_hand_idx = 0
        
    def place_bet(self, amount: int) -> bool:
        if amount <= self.chips and amount > 0:
            self.chips -= amount
            self.current_bet = amount
            return True
        return False
    
    def win_bet(self, multiplier: float = 2.0):
        winnings = int(self.current_bet * multiplier)
        self.chips += winnings
        self.current_bet = 0
    
    def lose_bet(self):
        self.current_bet = 0
    
    def push_bet(self):
        self.chips += self.current_bet
        self.current_bet = 0
    
    def reset_hand(self):
        self.hands = [[]]
        self.is_busted = False
        self.is_standing = False
        self.current_hand_idx = 0
    
    def get_current_hand(self):
        if self.current_hand_idx < len(self.hands):
            return self.hands[self.current_hand_idx]
        return []
    
    def add_card(self, card: tuple):
        if self.current_hand_idx < len(self.hands):
            self.hands[self.current_hand_idx].append(card)
