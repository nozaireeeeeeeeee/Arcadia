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

bot = commands.Bot()

@bot.event
async def on_ready():
    print(f"Bot connected: {bot.user}")
    await bot.sync_all_application_commands()

async def call_action(interaction, action):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Pas de permission.", ephemeral=True)
        return
    await interaction.response.defer()
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = {"hashsupport": SERVER_ID, "action": action}
    url = "https://rest.minestrator.com/api/v1/server/action"
    try:
        r = requests.post(url, headers=headers, data=data, timeout=20)
        print(f"[{action.upper()}] {r.status_code} | {r.text[:500]}")
        if r.status_code in (200, 204):
            await interaction.followup.send(f"✅ **{action.upper()}** OK")
        else:
            await interaction.followup.send(f"❌ {action} : {r.status_code}")
    except Exception as e:
        await interaction.followup.send(f"Erreur {action} : {str(e)[:150]}")

@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_action(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_action(interaction, "stop")

threading.Thread(target=run_web_server).start()
bot.run(TOKEN)
