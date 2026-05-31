import discord
from discord import app_commands
from discord.ext import commands
import db

class AltsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alts", description="List all characters linked to your profile")
    async def alts(self, interaction: discord.Interaction):
        characters = db.get_all_characters(interaction.user.id)
        if not characters:
            await interaction.response.send_message("❌ You haven't linked any characters yet! Use `/link`.", ephemeral=True)
            return
            
        # Updated Title
        embed = discord.Embed(title=f"Alts for {interaction.user.display_name}", color=discord.Color.dark_theme())
        
        char_list = ""
        for char in characters:
            if char['is_active']:
                char_list += f"🟢 **{char['name']}** *(Active)*\n"
            else:
                char_list += f"⚪ {char['name']}\n"
                
        embed.description = char_list
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="whoami", description="Check which character you are currently rolling as")
    async def whoami(self, interaction: discord.Interaction):
        active = db.get_active_character(interaction.user.id)
        if not active:
            await interaction.response.send_message("You don't have an active character loaded. Use `/link`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"🎭 You are currently playing as: **{active['name']}**", ephemeral=True)

    async def switch_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        characters = db.get_all_characters(interaction.user.id)
        choices = []
        for char in characters:
            if current.lower() in char['name'].lower():
                choices.append(app_commands.Choice(name=char['name'], value=str(char['entity_id'])))
        return choices[:25]

    @app_commands.command(name="switch", description="Switch your active character")
    @app_commands.autocomplete(character=switch_autocomplete)
    async def switch(self, interaction: discord.Interaction, character: str):
        entity_id = int(character)
        characters = db.get_all_characters(interaction.user.id)
        
        for char in characters:
            if char['entity_id'] == entity_id:
                # 1. Update the database
                db.set_active_character(interaction.user.id, entity_id)
                
                # 2. Reply to the user silently (ephemeral)
                await interaction.response.send_message(f"🔄 You have switched to **{char['name']}**! All `/roll` commands will now use their stats.", ephemeral=True)
                
                # 3. Post the public embed to #transcripts
                if interaction.guild:
                    transcripts_channel = discord.utils.get(interaction.guild.text_channels, name="transcripts")
                    
                    if transcripts_channel:
                        embed = discord.Embed(
                            description=f"🎭 {interaction.user.mention} is now playing as **{char['name']}**.",
                            color=discord.Color.dark_purple()
                        )
                        await transcripts_channel.send(embed=embed)
                
                return
                
        # Updated Error Text
        await interaction.response.send_message("❌ Character not found in your alts.", ephemeral=True)

async def setup(bot):
    # Updated Class Name
    await bot.add_cog(AltsCog(bot))