"""Complete American Monopoly game data and rules."""
from typing import List, Dict, Tuple, Optional

# Starting values
STARTING_MONEY = 1500
PASSING_GO_MONEY = 200
LUXURY_TAX = 100
INCOME_TAX = 200
JAIL_POSITION = 10
GO_TO_JAIL_POSITION = 30
JAIL_FINE = 50
MAX_JAIL_TURNS = 3
MAX_HOUSES_PER_PROPERTY = 4

# Property definitions with complete rent information
PROPERTIES: List[Dict] = [
    # Brown Properties
    {
        "name": "Mediterranean Avenue",
        "position": 1,
        "price": 60,
        "rent": [2, 10, 30, 90, 160, 250],  # [base, 1h, 2h, 3h, 4h, hotel]
        "house_cost": 50,
        "mortgage_value": 30,
        "color": (149, 84, 54),
        "group": "Brown"
    },
    {
        "name": "Baltic Avenue",
        "position": 3,
        "price": 60,
        "rent": [4, 20, 60, 180, 320, 450],
        "house_cost": 50,
        "mortgage_value": 30,
        "color": (149, 84, 54),
        "group": "Brown"
    },
    
    # Light Blue Properties
    {
        "name": "Oriental Avenue",
        "position": 6,
        "price": 100,
        "rent": [6, 30, 90, 270, 400, 550],
        "house_cost": 50,
        "mortgage_value": 50,
        "color": (170, 224, 250),
        "group": "Light Blue"
    },
    {
        "name": "Vermont Avenue",
        "position": 8,
        "price": 100,
        "rent": [6, 30, 90, 270, 400, 550],
        "house_cost": 50,
        "mortgage_value": 50,
        "color": (170, 224, 250),
        "group": "Light Blue"
    },
    {
        "name": "Connecticut Avenue",
        "position": 9,
        "price": 120,
        "rent": [8, 40, 100, 300, 450, 600],
        "house_cost": 50,
        "mortgage_value": 60,
        "color": (170, 224, 250),
        "group": "Light Blue"
    },
    
    # Pink Properties
    {
        "name": "St. Charles Place",
        "position": 11,
        "price": 140,
        "rent": [10, 50, 150, 450, 625, 750],
        "house_cost": 100,
        "mortgage_value": 70,
        "color": (217, 58, 150),
        "group": "Pink"
    },
    {
        "name": "States Avenue",
        "position": 13,
        "price": 140,
        "rent": [10, 50, 150, 450, 625, 750],
        "house_cost": 100,
        "mortgage_value": 70,
        "color": (217, 58, 150),
        "group": "Pink"
    },
    {
        "name": "Virginia Avenue",
        "position": 14,
        "price": 160,
        "rent": [12, 60, 180, 500, 700, 900],
        "house_cost": 100,
        "mortgage_value": 80,
        "color": (217, 58, 150),
        "group": "Pink"
    },
    
    # Orange Properties
    {
        "name": "St. James Place",
        "position": 16,
        "price": 180,
        "rent": [14, 70, 200, 550, 750, 950],
        "house_cost": 100,
        "mortgage_value": 90,
        "color": (247, 148, 29),
        "group": "Orange"
    },
    {
        "name": "Tennessee Avenue",
        "position": 18,
        "price": 180,
        "rent": [14, 70, 200, 550, 750, 950],
        "house_cost": 100,
        "mortgage_value": 90,
        "color": (247, 148, 29),
        "group": "Orange"
    },
    {
        "name": "New York Avenue",
        "position": 19,
        "price": 200,
        "rent": [16, 80, 220, 600, 800, 1000],
        "house_cost": 100,
        "mortgage_value": 100,
        "color": (247, 148, 29),
        "group": "Orange"
    },
    
    # Red Properties
    {
        "name": "Kentucky Avenue",
        "position": 21,
        "price": 220,
        "rent": [18, 90, 250, 700, 875, 1050],
        "house_cost": 150,
        "mortgage_value": 110,
        "color": (237, 27, 36),
        "group": "Red"
    },
    {
        "name": "Indiana Avenue",
        "position": 23,
        "price": 220,
        "rent": [18, 90, 250, 700, 875, 1050],
        "house_cost": 150,
        "mortgage_value": 110,
        "color": (237, 27, 36),
        "group": "Red"
    },
    {
        "name": "Illinois Avenue",
        "position": 24,
        "price": 240,
        "rent": [20, 100, 300, 750, 925, 1100],
        "house_cost": 150,
        "mortgage_value": 120,
        "color": (237, 27, 36),
        "group": "Red"
    },
    
    # Yellow Properties
    {
        "name": "Atlantic Avenue",
        "position": 26,
        "price": 260,
        "rent": [22, 110, 330, 800, 975, 1150],
        "house_cost": 150,
        "mortgage_value": 130,
        "color": (254, 242, 0),
        "group": "Yellow"
    },
    {
        "name": "Ventnor Avenue",
        "position": 27,
        "price": 260,
        "rent": [22, 110, 330, 800, 975, 1150],
        "house_cost": 150,
        "mortgage_value": 130,
        "color": (254, 242, 0),
        "group": "Yellow"
    },
    {
        "name": "Marvin Gardens",
        "position": 29,
        "price": 280,
        "rent": [24, 120, 360, 850, 1025, 1200],
        "house_cost": 150,
        "mortgage_value": 140,
        "color": (254, 242, 0),
        "group": "Yellow"
    },
    
    # Green Properties
    {
        "name": "Pacific Avenue",
        "position": 31,
        "price": 300,
        "rent": [26, 130, 390, 900, 1100, 1275],
        "house_cost": 200,
        "mortgage_value": 150,
        "color": (31, 178, 90),
        "group": "Green"
    },
    {
        "name": "North Carolina Avenue",
        "position": 32,
        "price": 300,
        "rent": [26, 130, 390, 900, 1100, 1275],
        "house_cost": 200,
        "mortgage_value": 150,
        "color": (31, 178, 90),
        "group": "Green"
    },
    {
        "name": "Pennsylvania Avenue",
        "position": 34,
        "price": 320,
        "rent": [28, 150, 450, 1000, 1200, 1400],
        "house_cost": 200,
        "mortgage_value": 160,
        "color": (31, 178, 90),
        "group": "Green"
    },
    
    # Dark Blue Properties
    {
        "name": "Park Place",
        "position": 37,
        "price": 350,
        "rent": [35, 175, 500, 1100, 1300, 1500],
        "house_cost": 200,
        "mortgage_value": 175,
        "color": (0, 114, 187),
        "group": "Dark Blue"
    },
    {
        "name": "Boardwalk",
        "position": 39,
        "price": 400,
        "rent": [50, 200, 600, 1400, 1700, 2000],
        "house_cost": 200,
        "mortgage_value": 200,
        "color": (0, 114, 187),
        "group": "Dark Blue"
    },
]

# Railroads
RAILROADS: List[Dict] = [
    {
        "name": "Reading Railroad",
        "position": 5,
        "price": 200,
        "rent": [25, 50, 100, 200],  # Rent for [1, 2, 3, 4] railroads owned
        "mortgage_value": 100,
        "color": (0, 0, 0),
        "group": "Railroad"
    },
    {
        "name": "Pennsylvania Railroad",
        "position": 15,
        "price": 200,
        "rent": [25, 50, 100, 200],
        "mortgage_value": 100,
        "color": (0, 0, 0),
        "group": "Railroad"
    },
    {
        "name": "B. & O. Railroad",
        "position": 25,
        "price": 200,
        "rent": [25, 50, 100, 200],
        "mortgage_value": 100,
        "color": (0, 0, 0),
        "group": "Railroad"
    },
    {
        "name": "Short Line",
        "position": 35,
        "price": 200,
        "rent": [25, 50, 100, 200],
        "mortgage_value": 100,
        "color": (0, 0, 0),
        "group": "Railroad"
    },
]

# Utilities
UTILITIES: List[Dict] = [
    {
        "name": "Electric Company",
        "position": 12,
        "price": 150,
        "mortgage_value": 75,
        "color": (200, 200, 200),
        "group": "Utility"
    },
    {
        "name": "Water Works",
        "position": 28,
        "price": 150,
        "mortgage_value": 75,
        "color": (200, 200, 200),
        "group": "Utility"
    },
]

# Build complete board (40 spaces)
def build_board() -> List[Dict]:
    """Build the complete 40-space Monopoly board."""
    board = [None] * 40
    
    # Special spaces
    board[0] = {"name": "GO", "type": "go"}
    board[2] = {"name": "Community Chest", "type": "community_chest"}
    board[4] = {"name": "Income Tax", "type": "income_tax"}
    board[7] = {"name": "Chance", "type": "chance"}
    board[10] = {"name": "Jail", "type": "jail"}
    board[17] = {"name": "Community Chest", "type": "community_chest"}
    board[20] = {"name": "Free Parking", "type": "free_parking"}
    board[22] = {"name": "Chance", "type": "chance"}
    board[30] = {"name": "Go To Jail", "type": "go_to_jail"}
    board[33] = {"name": "Community Chest", "type": "community_chest"}
    board[36] = {"name": "Chance", "type": "chance"}
    board[38] = {"name": "Luxury Tax", "type": "luxury_tax"}
    
    # Properties
    for prop in PROPERTIES:
        board[prop["position"]] = {**prop, "type": "property"}
    
    # Railroads
    for railroad in RAILROADS:
        board[railroad["position"]] = {**railroad, "type": "railroad"}
    
    # Utilities
    for utility in UTILITIES:
        board[utility["position"]] = {**utility, "type": "utility"}
    
    return board

BOARD_SPACES = build_board()

# Property groups for monopoly checking
PROPERTY_GROUPS = {
    "Brown": [1, 3],
    "Light Blue": [6, 8, 9],
    "Pink": [11, 13, 14],
    "Orange": [16, 18, 19],
    "Red": [21, 23, 24],
    "Yellow": [26, 27, 29],
    "Green": [31, 32, 34],
    "Dark Blue": [37, 39],
    "Railroad": [5, 15, 25, 35],
    "Utility": [12, 28],
}

# Community Chest cards (full list)
COMMUNITY_CHEST_CARDS = [
    {"id": "cc_collect_100", "text": "You set aside time every week to hang out with your elderly neighbor – you've heard some amazing stories! COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_collect_50",  "text": "You organize a group to clean up your town's footpaths. COLLECT $50.", "action": ("money", 50)},
    {"id": "cc_collect_10",  "text": "You volunteered at a blood donation. There were free cookies! COLLECT $10.", "action": ("money", 10)},
    {"id": "cc_pay_50",      "text": "You buy a few bags of cookies from that school bake sale. Yum! PAY $50.", "action": ("money", -50)},
    {"id": "cc_getout",      "text": "GET OUT OF JAIL FREE. Keep this card until needed.", "action": ("jail_free", 1)},
    {"id": "cc_collect_from_each_10", "text": "You organize a street party... COLLECT $10 FROM EACH PLAYER.", "action": ("collect_from_each", 10)},
    {"id": "cc_go_to_jail",  "text": "GO TO JAIL. DO NOT PASS GO.", "action": ("go_to_jail", None)},
    {"id": "cc_collect_20",  "text": "You help your neighbor bring in her groceries. COLLECT $20.", "action": ("money", 20)},
    {"id": "cc_collect_100_b","text": "You help build a new school playground – COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_collect_100_c","text": "You spend the day playing games with kids at a local children's hospital. COLLECT $100.", "action": ("money", 100)},
    {"id": "cc_pay_100",     "text": "You go to the local school's car wash fundraiser – PAY $100.", "action": ("money", -100)},
    {"id": "cc_advance_go",  "text": "ADVANCE TO GO. (COLLECT $200)", "action": ("advance", 0, True)},
    {"id": "cc_collect_200", "text": "You help your neighbors clean up after a storm. COLLECT $200.", "action": ("money", 200)},
    {"id": "cc_pay_50_b",    "text": "Donation to animal shelter. PAY $50.", "action": ("money", -50)},
    {"id": "cc_pay_for_repairs", "text": "For each house pay $40. For each hotel pay $115.", "action": ("pay_per_house_hotel", (40, 115))},
    {"id": "cc_collect_25",  "text": "You organize a bake sale. COLLECT $25.", "action": ("money", 25)}
]

# Chance cards (full list)
CHANCE_CARDS = [
    {"id": "ch_boardwalk", "text": "Advance to Boardwalk.", "action": ("advance", 39, False)},
    {"id": "ch_go",        "text": "Advance to Go (Collect $200).", "action": ("advance", 0, True)},
    {"id": "ch_illinois",  "text": "Advance to Illinois Avenue. If you pass Go, collect $200.", "action": ("advance", 24, True)},
    {"id": "ch_st_charles","text": "Advance to St. Charles Place. If you pass Go, collect $200.", "action": ("advance", 11, True)},
    {"id": "ch_nearest_rail","text": "Advance to the nearest Railroad.", "action": ("advance_nearest", "railroad")},
    {"id": "ch_nearest_rail_b","text": "Advance to the nearest Railroad.", "action": ("advance_nearest", "railroad")},
    {"id": "ch_nearest_utility","text": "Advance token to nearest Utility.", "action": ("advance_nearest", "utility")},
    {"id": "ch_dividend",  "text": "Bank pays you dividend of $50.", "action": ("money", 50)},
    {"id": "ch_getout",    "text": "Get Out of Jail Free.", "action": ("jail_free", 1)},
    {"id": "ch_back_3",    "text": "Go Back 3 Spaces.", "action": ("advance_relative", -3)},
    {"id": "ch_go_to_jail","text": "Go to Jail. Do not pass Go.", "action": ("go_to_jail", None)},
    {"id": "ch_repairs",   "text": "For each house pay $25. For each hotel pay $100.", "action": ("pay_per_house_hotel", (25, 100))},
    {"id": "ch_speeding",  "text": "Speeding fine $15.", "action": ("money", -15)},
    {"id": "ch_reading",   "text": "Advance to Reading Railroad.", "action": ("advance", 5, True)},
    {"id": "ch_chairman",  "text": "Pay each player $50.", "action": ("pay_each_player", 50)},
    {"id": "ch_loan",      "text": "Collect $150.", "action": ("money", 150)}
]