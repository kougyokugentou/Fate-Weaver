import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

import db

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize SQLite database
db.init_db()

# --- NEW INTENTS SETUP ---
intents = discord.Intents.default()
intents.message_content = True 

class KankaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents  # Pass the updated intents here
        )

    async def setup_hook(self):
        # Load our logical groupings (Cogs) dynamically
        initial_extensions = [
            'cogs.kanka_cog',
            'cogs.roll_cog',
            'cogs.alts_cog'
        ]
        
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
        
        # Sync slash commands globally to Discord
        try:
            synced = await self.tree.sync()
            print(f"🔄 Synced {len(synced)} command(s) globally.")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

bot = KankaBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready to roll!")

if __name__ == "__main__":
    bot.run(TOKEN)