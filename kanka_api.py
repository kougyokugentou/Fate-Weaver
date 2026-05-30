import os
import aiohttp
import re

# Base Kanka API URL
BASE_URL = "https://api.kanka.io/1.0"

async def get_headers():
    return {
        "Authorization": f"Bearer {os.getenv('KANKA_TOKEN')}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

async def get_campaign_id(identifier):
    """Translates a string slug into the numeric ID Kanka's API requires, handling pagination."""
    if str(identifier).isdigit():
        return int(identifier)
        
    url = f"{BASE_URL}/campaigns"
    headers = await get_headers()
    
    async with aiohttp.ClientSession() as session:
        while url:  
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for cmp in data.get("data", []):
                        if cmp.get("slug") == identifier:
                            return cmp.get("id")
                        
                        expected_slug = str(cmp.get("name", "")).lower().replace(" ", "-")
                        expected_slug = re.sub(r'[^a-z0-9\-]', '', expected_slug)
                        if expected_slug == identifier:
                            return cmp.get("id")
                    
                    links = data.get("links", {})
                    url = links.get("next") 
                else:
                    print(f"API Error fetching campaigns: {resp.status}")
                    break
    return None

async def get_entity_data(campaign_id, entity_id):
    url = f"{BASE_URL}/campaigns/{campaign_id}/entities/{entity_id}"
    headers = await get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return (await resp.json()).get("data")
    return None

async def get_character_data(campaign_id, character_id):
    url = f"{BASE_URL}/campaigns/{campaign_id}/characters/{character_id}"
    headers = await get_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return (await resp.json()).get("data")
    return None

async def get_character_attributes(campaign_id, entity_id):
    url = f"{BASE_URL}/campaigns/{campaign_id}/entities/{entity_id}/attributes"
    headers = await get_headers()
    attributes = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                for attr in data.get("data", []):
                    attributes[attr.get("name")] = attr.get("value")
    return attributes