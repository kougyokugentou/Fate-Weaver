import sqlite3

DB_FILE = 'users.sqlite'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Created a new table structure to handle multiple characters
        conn.execute('''CREATE TABLE IF NOT EXISTS characters (
            discord_id TEXT,
            campaign_id INTEGER,
            entity_id INTEGER,
            name TEXT,
            is_active INTEGER,
            PRIMARY KEY (discord_id, entity_id)
        )''')
        conn.commit()

def add_character(discord_id, campaign_id, entity_id, name):
    with sqlite3.connect(DB_FILE) as conn:
        # First, set all of this user's existing characters to inactive
        conn.execute('UPDATE characters SET is_active = 0 WHERE discord_id = ?', (str(discord_id),))
        # Then, insert the new one (or update it if it exists) and make it the active one
        conn.execute('''REPLACE INTO characters (discord_id, campaign_id, entity_id, name, is_active)
                        VALUES (?, ?, ?, ?, 1)''', (str(discord_id), campaign_id, entity_id, name))
        conn.commit()

def get_active_character(discord_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute('SELECT campaign_id, entity_id, name FROM characters WHERE discord_id = ? AND is_active = 1', (str(discord_id),))
        row = cursor.fetchone()
        if row:
            return {'campaign_id': row[0], 'entity_id': row[1], 'name': row[2]}
        return None

def get_all_characters(discord_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute('SELECT campaign_id, entity_id, name, is_active FROM characters WHERE discord_id = ?', (str(discord_id),))
        return [{'campaign_id': r[0], 'entity_id': r[1], 'name': r[2], 'is_active': r[3]} for r in cursor.fetchall()]

def set_active_character(discord_id, entity_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('UPDATE characters SET is_active = 0 WHERE discord_id = ?', (str(discord_id),))
        conn.execute('UPDATE characters SET is_active = 1 WHERE discord_id = ? AND entity_id = ?', (str(discord_id), entity_id))
        conn.commit()