# D&D Dungeon Master Guide

## Getting Started

### 1. Start the Game

```bash
python game_server_pyglet_complete.py
```

### 2. Player Selection

- Touch a slot to join the game
- **First player (P1) is automatically the Dungeon Master**
- Need at least 2 players (1 DM + 1 adventurer)
- Hold on START button to begin

### 3. Character Loading

- Characters are automatically loaded from previous sessions
- New players get randomly generated characters
- All characters are saved automatically

---

## DM Control Panel

Located at the top-right of the screen (or your panel position). Four buttons:

### 🗡️ Spawn Enemy

**Purpose**: Start a combat encounter

**How to Use**:

1. Click "Spawn Enemy"
2. Select a monster from the list
3. Combat begins automatically

**Available Monsters**:

- **Goblin** (CR 1/4): Weak, good for level 1-2 parties
- **Orc** (CR 1/2): Moderate threat
- **Skeleton** (CR 1/4): Undead minion
- **Wolf** (CR 1/4): Fast natural creature
- **Ogre** (CR 2): Strong brute
- **Troll** (CR 5): Regenerating tank
- **Dragon Wyrmling** (CR 3): Young dragon, breath weapon

**Tips**:

- Match CR to party level for balanced fights
- Lower level parties should fight CR 1/4 to 1/2
- Level 3-5 parties can handle CR 2-3
- Combine multiple weak enemies for variety

### 👥 Add NPC

**Purpose**: Add non-player characters (allies, quest givers, merchants)

**Status**: Coming soon

- Will allow friendly NPCs to join the party
- NPCs won't take player slots
- DM controls NPC actions

### 🖼️ Change Scene

**Purpose**: Set the background and atmosphere

**How to Use**:

1. Click "Change Scene"
2. Select a preset scene OR
3. Click "AI Generate" for custom background

**Preset Scenes**:

- **Tavern**: Cozy inn, start of adventures
- **Dungeon**: Dark underground passages
- **Forest**: Mystical woodland paths
- **Castle**: Grand fortress halls
- **Cave**: Underground caverns
- **Battlefield**: Open combat zones

**AI Generate** (Requires API Setup):

- Creates unique backgrounds using AI
- Uses themed prompts for best results
- Saves generated images for reuse

### 🎁 Give Item

**Purpose**: Reward players with treasure and equipment

**How to Use**:

1. Click "Give Item"
2. Select a player
3. Choose item from list

**Item Categories**:

- **Weapons**: Longsword, Bow, Dagger, Staff
- **Armor**: Leather, Chain Mail, Plate
- **Consumables**: Potions, Scrolls
- **Magic Items**: Enchanted gear (future)

---

## Running Combat

### Initiative

- Automatically rolled when you spawn an enemy
- Order shown on right side of screen
- Highest roll goes first

### Player Turns

When a player's turn comes up:

- Two buttons appear: **Attack** and **End Turn**
- Attack: Roll d20 + modifiers vs enemy AC
- If hit, roll damage dice
- Damage appears as floating numbers
- Turn ends automatically

### Enemy Turns

- Controlled by AI automatically
- Enemy attacks random player
- Results shown in dice roll display
- Turn ends automatically

### Combat End

**Victory**: All enemies defeated

- Players gain XP
- Automatic leveling if enough XP
- Return to exploration mode

**Defeat**: All players at 0 HP

- Respawn at tavern (future)
- No XP penalty

---

## DM Tips & Strategies

### Encounter Design

1. **Start Easy**: First encounter should be 1-2 weak enemies
2. **Scale Up**: Add more/stronger enemies as party levels
3. **Variety**: Mix enemy types for interesting fights
4. **Rest Periods**: Give players time between major fights

### Storytelling

1. **Set the Scene**: Use "Change Scene" to match story
2. **Describe Actions**: Narrate what's happening
3. **Reward Exploration**: Give items for clever solutions
4. **Build Tension**: Gradual difficulty increase

### Balancing Difficulty

- **1 CR 1/4 enemy per player**: Easy fight
- **1 CR 1/2 enemy per 2 players**: Medium fight
- **1 CR 1 enemy per player**: Hard fight
- **Boss Fights**: CR = Party level + 2

### Session Structure

1. **Intro** (5 min): Set scene, describe situation
2. **Exploration** (10 min): Players investigate, interact
3. **First Encounter** (5 min): Easy combat to warm up
4. **Challenge** (10 min): Harder fight or puzzle
5. **Climax** (10 min): Boss fight or major event
6. **Conclusion** (5 min): Wrap up, distribute rewards

---

## Quick Reference

### Difficulty Classes (for skill checks)

- **Very Easy**: DC 5
- **Easy**: DC 10
- **Medium**: DC 15
- **Hard**: DC 20
- **Very Hard**: DC 25
- **Nearly Impossible**: DC 30

### Experience Points

- Level 1 → 2: 300 XP
- Level 2 → 3: 900 XP
- Level 3 → 4: 2700 XP
- Level 4 → 5: 6500 XP
- Level 5 → 6: 14000 XP

### Combat Shorthand

- **AC**: Armor Class (defense)
- **HP**: Hit Points (health)
- **CR**: Challenge Rating (difficulty)
- **XP**: Experience Points (progression)
- **d20**: 20-sided die (attacks, checks)
- **d6/d8/d12**: Damage dice

---

## Troubleshooting

**Players not appearing?**

- Make sure hand tracking is active
- Check camera is connected
- Verify fingertips are detected

**Combat not starting?**

- Make sure you selected an enemy
- Check that at least one player character exists
- Try spawning a different enemy

**Characters not saving?**

- Check `dnd_characters/` folder exists
- Verify write permissions
- Characters save automatically on creation

**Want to reset?**

- Delete files in `dnd_characters/` folder
- Restart game
- New characters will be created

---

## Advanced: AI Background Setup

### Option 1: OpenAI DALL-E

```python
# In gameplay.py, add to _generate_ai_background():
import openai
openai.api_key = "your-api-key"
response = openai.Image.create(
    prompt=AI_BACKGROUND_PROMPTS[self.current_scene],
    n=1,
    size="1792x1024"
)
image_url = response['data'][0]['url']
# Download and display image
```

### Option 2: Stability AI

```python
import stability_sdk
# Similar setup with Stability API
```

### Option 3: Local Model

```python
from diffusers import StableDiffusionPipeline
# Run Stable Diffusion locally (requires GPU)
```

---

## Future Features (Coming Soon)

- [ ] Custom character creation UI
- [ ] Spell casting system
- [ ] Inventory management
- [ ] NPC system
- [ ] Multiple enemy support
- [ ] Loot drops
- [ ] Status effects (poisoned, stunned, etc.)
- [ ] Character death mechanics
- [ ] Campaign save/load
- [ ] Class-specific abilities

---

## Need Help?

Check the technical documentation: `DND_IMPLEMENTATION.md`

Have fun running your D&D game! 🎲⚔️🐉
