# AI Background Generation Setup Guide

## Quick Start

Your API key should go in the file: **`api_keys.py`** (already created in the project root)

---

## Step 1: Choose Your AI Service

You have two options:

### Option A: OpenAI DALL-E 3 (Recommended)

- **Quality**: Excellent, photorealistic
- **Cost**: $0.04 - $0.08 per image
- **Speed**: Fast (10-30 seconds)
- **Setup**: Simple API key

### Option B: Stability AI (Stable Diffusion)

- **Quality**: Very good, artistic
- **Cost**: Credits-based (~$0.002 per image)
- **Speed**: Fast (5-15 seconds)
- **Setup**: Simple API key

---

## Step 2: Get Your API Key

### For OpenAI DALL-E:

1. Go to https://platform.openai.com/signup
2. Create an account (or sign in)
3. Go to https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (starts with `sk-proj-...`)
6. Add at least $5 credit to your account

### For Stability AI:

1. Go to https://platform.stability.ai/
2. Create an account
3. Go to https://platform.stability.ai/account/keys
4. Generate a new API key
5. Copy the key (starts with `sk-...`)
6. Purchase credits ($10 = ~5000 images)

---

## Step 3: Add Key to api_keys.py

Open `api_keys.py` and edit it:

### For OpenAI:

```python
OPENAI_API_KEY = "sk-proj-YOUR_KEY_HERE"
AI_BACKGROUND_SERVICE = "openai"
```

### For Stability AI:

```python
STABILITY_API_KEY = "sk-YOUR_KEY_HERE"
AI_BACKGROUND_SERVICE = "stability"
```

**Important**: Keep the quotes around your key!

---

## Step 4: Install Required Package

### For OpenAI:

```bash
pip install openai
```

### For Stability AI:

```bash
pip install requests
```

(Note: `requests` is probably already installed)

---

## Step 5: Test It!

1. Start the game: `python game_server_pyglet_complete.py`
2. Select players (you must be Player 1 to be the DM)
3. Look for the DM Control Panel
4. Click "Change Scene" button
5. Click "AI Generate"
6. Wait 10-30 seconds
7. Your background will be generated!

---

## Troubleshooting

### "API Keys Missing" error

- Make sure `api_keys.py` exists in the project root
- Check that you saved the file after editing

### "API Key Missing" error

- You forgot to add your key between the quotes
- Make sure there are no extra spaces

### "OpenAI Not Installed" or "Requests Not Installed"

- Run the pip install command from Step 4

### "Invalid API key" error

- Double-check you copied the entire key
- Make sure the key hasn't expired
- Verify you have credits/balance in your account

### Generation takes too long

- First generation can take 30-60 seconds
- Check your internet connection
- Try again - sometimes API servers are busy

### Image doesn't appear

- The current version shows a confirmation popup
- Full image display will be added in a future update
- Check the console/terminal for the image URL

---

## Cost Estimates

### OpenAI DALL-E 3:

- **1024x1792**: $0.080 per image
- 100 backgrounds = $8.00

### Stability AI:

- **SDXL 1.0**: ~25 credits per image
- 100 backgrounds = ~$0.50

---

## Security Notes

⚠️ **NEVER share your API keys publicly!**
⚠️ **NEVER commit api_keys.py to GitHub!**

The `.gitignore` file is configured to exclude `api_keys.py`, but be careful:

- Don't screenshot your keys
- Don't paste them in chat/forums
- Regenerate keys if accidentally exposed

---

## Advanced: Using Local AI (Free)

If you have a good GPU (RTX 3060 or better), you can run Stable Diffusion locally:

```bash
pip install diffusers transformers torch accelerate
```

This requires ~5GB of VRAM and will be slower (1-2 minutes per image) but is completely free!

(Implementation coming soon)

---

## Example Prompts Used

The game automatically generates themed prompts:

- **Tavern**: "Medieval fantasy tavern interior, warm firelight..."
- **Dungeon**: "Dark stone dungeon corridor, torches on walls..."
- **Forest**: "Enchanted forest path, mystical atmosphere..."
- **Castle**: "Grand castle throne room, high ceilings..."
- **Cave**: "Underground cave with glowing crystals..."
- **Battlefield**: "Epic fantasy battlefield, dramatic lighting..."
- **Temple**: "Ancient temple ruins, overgrown with vines..."
- **Village**: "Peaceful fantasy village, thatched roofs..."

Each prompt is optimized for D&D-style backgrounds!

---

## Need More Help?

Check the main documentation: `DM_GUIDE.md`

Or ask in the project issues: https://github.com/Acvariii/ARPi2/issues
