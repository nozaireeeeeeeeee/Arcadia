import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# 1. Serveur Web (Optionnel sur Railway, mais conserve la compatibilité)
app = Flask('')

@app.route('/')
def home():
    return "Bot en ligne sur Railway !"

def run_web_server():
    # Railway fournit automatiquement la variable PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuration du Bot
bot = commands.Bot()

TOKEN = os.environ.get("DISCORD_TOKEN")
API_KEY = os.environ.get("WISPBYTE_API_KEY")
SERVER_ID = os.environ.get("SERVER_ID")
BASE_URL = "https://panel.wispbyte.com" 

@bot.event
async def on_ready():
    print(f"Bot connecté sur Railway : {bot.user}")
    await bot.sync_all_application_commands()

# 3. Fonction API WispByte
async def call_wisp(interaction: nextcord.Interaction, action: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Pas de permission.", ephemeral=True)
        return

    await interaction.response.defer()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url = f"{BASE_URL}/api/client/servers/{SERVER_ID}/power"
    data = {"signal": action}

    try:
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"[WISPBYTE] {action.upper()} | Code HTTP: {r.status_code}")
        
        if r.status_code in (204, 200):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** exécutée avec succès !")
        else:
            await interaction.followup.send(f"❌ Erreur WispByte : {r.status_code}")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}")

@bot.slash_command(name="start", description="Démarre le serveur Minecraft")
async def start_server(interaction: nextcord.Interaction):
    await call_wisp(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur Minecraft")
async def stop_server(interaction: nextcord.Interaction):
    await call_wisp(interaction, "stop")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
