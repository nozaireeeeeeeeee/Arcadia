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
    return "Bot MineStrator en ligne sur Railway !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuration du Bot Discord
bot = commands.Bot()

TOKEN = os.environ.get("DISCORD_TOKEN")
MINE_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")

@bot.event
async def on_ready():
    print(f"Bot connecté sur Railway : {bot.user}")
    await bot.sync_all_application_commands()

# 3. Fonction d'appel API MineStrator Direct
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    await interaction.response.defer()

    # En-têtes pour l'API classique de MineStrator
    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # URL de l'API MineStrator pour les actions de puissance (start/stop/restart)
    url = f"https://api.minestrator.com/public/v1/server/{SERVER_ID}/action"
    payload = {"action": action}

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"[MINESTRATOR] Action: {action.upper()} | Code HTTP: {r.status_code}")
        
        if r.status_code in (200, 204):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** transmise à MineStrator !")
        elif r.status_code == 401:
            await interaction.followup.send("❌ **Erreur 401** : Clé API MineStrator incorrecte.")
        else:
            await interaction.followup.send(f"❌ MineStrator a répondu avec le code {r.status_code}.")
            
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
    bot.run(TOKEN)
