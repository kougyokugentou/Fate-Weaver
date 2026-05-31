import discord
from discord import app_commands
from discord.ext import commands
import os
import re

import db
import kanka_api

STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))

class KankaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link", description="Link a Kanka character to your profile")
    async def link(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(ephemeral=True)

        match_new = re.search(r'w/([^/]+)/entities/(\d+)', url)
        match_old = re.search(r'campaigns/([^/]+)/(?:characters|entities)/(\d+)', url)

        campaign_id, entity_id, slug = None, None, None

        if match_new:
            slug = match_new.group(1)
            entity_id = int(match_new.group(2))
            campaign_id = await kanka_api.get_campaign_id(slug)
        elif match_old:
            slug = match_old.group(1)
            extracted_id = int(match_old.group(2))
            campaign_id = await kanka_api.get_campaign_id(slug)
            
            if "/characters/" in url:
                char_data = await kanka_api.get_character_data(campaign_id, extracted_id)
                if char_data:
                    entity_id = char_data.get("entity_id")
            else:
                entity_id = extracted_id
        else:
            await interaction.followup.send("❌ Could not parse URL. Must be like: `https://app.kanka.io/w/campaign/entities/123`")
            return

        if not campaign_id:
            await interaction.followup.send(f"❌ Could not find a Campaign matching `{slug}`. Does your API Token have access to it?")
            return
        if not entity_id:
            await interaction.followup.send(f"❌ Campaign found, but could not locate Entity ID in Kanka.")
            return
            
        entity_data = await kanka_api.get_entity_data(campaign_id, entity_id)
        if not entity_data:
            await interaction.followup.send("❌ Could not fetch Entity data from Kanka. (Check API Token permissions).")
            return
            
        name = entity_data.get('name', 'Unknown')
        
        # 1. Update the database
        db.add_character(interaction.user.id, campaign_id, entity_id, name)
        
        # 2. Reply to the user silently (ephemeral)
        await interaction.followup.send(f"✅ Successfully linked to **{name}**! They are now your active character.")

        # 3. Post the public embed to #transcripts
        if interaction.guild:
            transcripts_channel = discord.utils.get(interaction.guild.text_channels, name="transcripts")
            
            if transcripts_channel:
                embed = discord.Embed(
                    description=f"🔗 {interaction.user.mention} linked **{name}** @ [Kanka Profile]({url})",
                    color=discord.Color.green()
                )
                await transcripts_channel.send(embed=embed)

    @app_commands.command(name="sheet", description="View the active character sheet linked to a profile")
    @app_commands.describe(mention="Staff only: View another player's active character")
    async def sheet(self, interaction: discord.Interaction, mention: discord.Member = None):
        target = mention or interaction.user
        
        # Staff check for viewing others
        if target.id != interaction.user.id:
            if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("❌ You do not have the Staff role required to view other users' sheets.", ephemeral=True)
                return

        link_data = db.get_active_character(target.id)
        if not link_data:
            await interaction.response.send_message(f"❌ {target.display_name} has no active character. Use `/link`.", ephemeral=True)
            return
                
        await interaction.response.defer()
        
        entity_data = await kanka_api.get_entity_data(link_data['campaign_id'], link_data['entity_id'])
        attributes = await kanka_api.get_character_attributes(link_data['campaign_id'], link_data['entity_id'])
        
        kanka_url = f"https://app.kanka.io/w/{link_data['campaign_id']}/entities/{link_data['entity_id']}"
        embed = discord.Embed(title=f"Character Sheet: {entity_data.get('name')}", url=kanka_url, color=discord.Color.blurple())
        
        if entity_data.get("type") == "character" and entity_data.get("child_id"):
            char_data = await kanka_api.get_character_data(link_data['campaign_id'], entity_data.get("child_id"))
            if char_data and char_data.get('image_full'):
                embed.set_thumbnail(url=char_data.get('image_full'))
            
        desc_lines = []
        for k, v in list(attributes.items())[:30]:  
            desc_lines.append(f"**{k}:** {v}")
            
        embed.description = "\n".join(desc_lines) if desc_lines else "*No numeric properties found.*"
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(KankaCog(bot))