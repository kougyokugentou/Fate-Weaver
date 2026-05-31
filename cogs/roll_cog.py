import discord
from discord import app_commands
from discord.ext import commands
import random
import re

import db
import kanka_api

class RollingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def evaluate_pool(self, expression: str, attributes: dict):
        attrs = {k.lower(): str(v).strip() for k, v in attributes.items() if str(v).strip().replace('-', '', 1).isdigit()}
        keys_sorted = sorted(attrs.keys(), key=len, reverse=True)
        
        expr_lower = expression.lower()
        for k in keys_sorted:
            if k in expr_lower:
                expr_lower = expr_lower.replace(k, attrs[k])
                
        if re.search(r'[a-z_]', expr_lower):
            raise ValueError(f"Unrecognized stats or non-numeric properties.\nParsed as: `{expr_lower}`")
            
        try:
            if not re.match(r'^[\d\+\-\s\(\)\*\/]+$', expr_lower):
                raise ValueError("Invalid mathematical characters in expression.")
            
            pool_size = eval(expr_lower)
            return int(pool_size), expr_lower
        except Exception:
            raise ValueError("Could not calculate pool size. Check your spelling and formatting.")

    def roll_cofd_dice(self, pool: int, again: int = 10, rote: bool = False):
        if pool < 1:
            roll = random.randint(1, 10)
            if roll == 10:
                return {"successes": 1, "rolls": [roll], "is_chance": True, "dramatic_failure": False}
            elif roll == 1:
                return {"successes": -1, "rolls": [roll], "is_chance": True, "dramatic_failure": True}
            else:
                return {"successes": 0, "rolls": [roll], "is_chance": True, "dramatic_failure": False}

        successes = 0
        rolls = []
        dice_to_roll = pool

        while dice_to_roll > 0:
            current_rolls = [random.randint(1, 10) for _ in range(dice_to_roll)]
            rolls.extend(current_rolls)
            successes += sum(1 for die in current_rolls if die >= 8)
            
            if rote:
                failed_dice = sum(1 for die in current_rolls if die < 8)
                rote_rolls = [random.randint(1, 10) for _ in range(failed_dice)]
                rolls.extend(rote_rolls)
                successes += sum(1 for die in rote_rolls if die >= 8)
                current_rolls.extend(rote_rolls)
                rote = False

            dice_to_roll = sum(1 for die in current_rolls if die >= again)

        return {"successes": successes, "rolls": rolls, "is_chance": False, "dramatic_failure": False}

    @app_commands.command(name="roll", description="Roll a CofD dice pool using your Kanka stats")
    @app_commands.describe(
        pool="Your dice pool equation (e.g., 'Wits + Composure - 2')", 
        again="Explode on (default 10)", 
        rote="Apply Rote Quality?"
    )
    async def roll(self, interaction: discord.Interaction, pool: str, again: int = 10, rote: bool = False):
        link_data = db.get_active_character(interaction.user.id)
        if not link_data:
            await interaction.response.send_message("❌ You must `/link` your character first to pull attributes.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        entity_data = await kanka_api.get_entity_data(link_data['campaign_id'], link_data['entity_id'])
        if not entity_data:
            await interaction.followup.send("❌ Could not fetch character data from Kanka. Ensure the API token is valid.")
            return
            
        attributes = await kanka_api.get_character_attributes(link_data['campaign_id'], link_data['entity_id'])
        
        try:
            pool_size, math_expr = self.evaluate_pool(pool, attributes)
        except ValueError as e:
            await interaction.followup.send(f"❌ **Error parsing pool:** {e}")
            return
            
        result = self.roll_cofd_dice(pool_size, again, rote)
        char_name = entity_data.get('name', 'Character')
        
        formatted_rolls = [f"**{r}**" if r >= 8 else str(r) for r in result["rolls"]]
        rolls_str = ", ".join(formatted_rolls)
        
        color = discord.Color.green() if result['successes'] > 0 else discord.Color.red()
        if result['is_chance'] and result['dramatic_failure']:
            color = discord.Color.dark_red()
            
        embed = discord.Embed(title=f"{interaction.user.display_name} rolls for {char_name}", color=color)
        
        pool_desc = f"`{pool}`\n↳ `{math_expr}` = **{pool_size} dice**"
        
        # Track our modifiers for the transcript log
        modifiers = []
        if again != 10: 
            modifiers.append(f"{again}-again")
            pool_desc += f" *( {again}-again )*"
        if rote: 
            modifiers.append("Rote")
            pool_desc += " *( Rote )*"
            
        embed.add_field(name="Pool Equation", value=pool_desc, inline=False)
        
        # Determine outcome string for both the chat and the transcript log
        outcome_str = ""
        if result['is_chance']:
            embed.add_field(name="Chance Die Roll", value=f"[{rolls_str}]", inline=False)
            if result['dramatic_failure']:
                outcome_str = "💀 Dramatic Failure!"
            elif result['successes'] == 1:
                outcome_str = "🟢 Success!"
            else:
                outcome_str = "🔴 Failure"
        else:
            embed.add_field(name="Dice Results", value=f"[{rolls_str}]", inline=False)
            if result['successes'] >= 5:
                outcome_str = f"🌟 Exceptional Success! ({result['successes']} successes)"
                embed.color = discord.Color.gold()
                color = discord.Color.gold()
            elif result['successes'] > 0:
                outcome_str = f"🟢 Success ({result['successes']} successes)"
            else:
                outcome_str = "🔴 Failure (0 successes)"

        embed.description = f"### {outcome_str}"

        # Send the main roll response to the channel where it was typed
        await interaction.followup.send(embed=embed)

        # --- NEW: Post to #transcripts ---
        if interaction.guild:
            transcripts_channel = discord.utils.get(interaction.guild.text_channels, name="transcripts")
            if transcripts_channel:
                mod_str = f" *( {', '.join(modifiers)} )*" if modifiers else ""
                
                log_embed = discord.Embed(
                    description=f"🎲 {interaction.user.mention} rolled `{pool}`{mod_str} for **{char_name}**.\n↳ **Result:** {outcome_str}",
                    color=color
                )
                await transcripts_channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(RollingCog(bot))