import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

app = Flask('')

@app.route('/')
def home():
    return "Bot online"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("DISCORD_TOKEN")
API_KEY = os.environ.get("MINESTRATOR_API_KEY")
SERVER_ID = os.environ.get("SERVER_ID")

BASE_URL = f"https://panel.minestrator.com/api/client/servers/{SERVER_ID}"

bot = commands.Bot()

@bot.event
async def on_ready():
    print(f"Bot connected: {bot.user}")
    await bot.sync_all_application_commands()

async def call_power(interaction, signal):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Pas de permission.", ephemeral=True)
        return
    await interaction.response.defer()
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = {"signal": signal}
    url = f"{BASE_URL}/power"
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"[{signal.upper()}] Code: {r.status_code} | Réponse: {r.text[:400]}")
        if r.status_code in (200, 204):
            await interaction.followup.send(f"Commande **{signal}** envoyée avec succès.")
        else:
            await interaction.followup.send(f"Échec {signal}: {r.status_code} - {r.text[:300]}")
    except Exception as e:
        await interaction.followup.send(f"Erreur réseau {signal}: {str(e)}")

@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_power(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_power(interaction, "stop")

threading.Thread(target=run_web_server).start()
bot.run(TOKEN)
