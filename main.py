import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# 1. Serveur Web pour la compatibilité Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuration du Bot Discord (Intents obligatoires pour Nextcord)
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
MINE_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté avec succès sur Railway : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("✅ Les commandes Slash ont été synchronisées avec Discord !")
    except Exception as e:
        print(f"⚠️ Erreur lors de la synchronisation : {e}")

# 3. Fonction d'appel API MineStrator
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    await interaction.response.defer()

    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # URL exacte basée sur tes recherches : .../v1/servers/456343/start
    url = f"https://api.minestrator.com/v1/servers/{SERVER_ID}/{action}"

    try:
        r = requests.post(url, headers=headers, timeout=15)
        print(f"[MINESTRATOR] Action: {action.upper()} | Code HTTP: {r.status_code}")
        
        if r.status_code in (200, 204, 201):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** validée par MineStrator avec succès !")
        elif r.status_code == 404:
            await interaction.followup.send(f"❌ **Erreur 404** : Le serveur `{SERVER_ID}` est introuvable sur ton compte.")
        elif r.status_code == 401:
            await interaction.followup.send("❌ **Erreur 401** : Ta clé API `MINESTRATOR_TOKEN` est refusée.")
        else:
            await interaction.followup.send(f"❌ MineStrator a répondu avec le code : {r.status_code}")
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}")

# 4. Commandes Slash Discord
@bot.slash_command(name="start", description="Démarre le serveur MineStrator")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur MineStrator")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    
    if not TOKEN:
        print("❌ ERREUR : La variable DISCORD_TOKEN est vide sur Railway !")
    else:
        bot.run(TOKEN)
