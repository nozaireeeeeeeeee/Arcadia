import os
import threading
import requests
from flask import Flask
import nextcord
from nextcord.ext import commands

# 1. Configuration
bot = commands.Bot(intents=nextcord.Intents.default())
TOKEN = os.environ.get("DISCORD_TOKEN")
MINESTRATOR_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")

# 2. Serveur Web
app = Flask('')
@app.route('/')
def home(): return "Bot Actif"
def run_web_server(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# 3. Fonction API (URL corrigée pour MineStrator)
def api_worker(action, server_id, token):
    # L'API MineStrator utilise souvent cette racine
    base_url = "https://api.minestrator.com"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        if action == "debug":
            # On tente de lister les serveurs à la racine de la v1
            res = requests.get(f"{base_url}/v1/servers", headers=headers, timeout=10)
            return f"Code {res.status_code}: {res.text[:1000]}"
            
        elif action == "statut":
            res = requests.get(f"{base_url}/v1/server/{server_id}", headers=headers, timeout=5)
            if res.status_code == 200: return f"Statut : {res.json().get('status')}"
            return f"Erreur {res.status_code}"

    except Exception as e: return f"Erreur : {str(e)}"

# 4. Commandes
@bot.slash_command(name="debug")
async def debug(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    res = api_worker("debug", "", MINESTRATOR_TOKEN)
    await interaction.followup.send(f"```json\n{res}\n```", ephemeral=True)

@bot.slash_command(name="statut")
async def statut(interaction: nextcord.Interaction):
    await interaction.response.defer()
    res = api_worker("statut", SERVER_ID, MINESTRATOR_TOKEN)
    await interaction.followup.send(res)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
