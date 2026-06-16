import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# ----------------- PARTIE SERVEUR WEB (ANTI-VEILLE) -----------------
app = Flask('')

@app.route('/')
def home():
    return "Le bot est en ligne et fonctionnel !"

def run_web_server():
    # Render utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------- PARTIE BOT DISCORD -----------------
TOKEN = os.environ.get("DISCORD_TOKEN")
API_KEY = os.environ.get("MINESTRATOR_API_KEY")
SERVER_ID = os.environ.get("SERVER_ID")

bot = commands.Bot()

@bot.event
async def on_ready():
    print(f"✅ Bot connecté avec succès en tant que : {bot.user}")

@bot.slash_command(
    name="start",
    description="Lance automatiquement le serveur Minecraft MineStrator."
)
async def start_server(interaction: nextcord.Interaction):
    # Sécurité : Seuls les admins peuvent l'utiliser
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
        return

    await interaction.response.defer()

    url = f"https://api.minestrator.com/v1/server/{SERVER_ID}/action/start"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            await interaction.followup.send("🚀 **Le serveur MineStrator démarre !**")
        else:
            error_data = response.json()
            error_msg = error_data.get("message", "Erreur inconnue")
            await interaction.followup.send(f"⚠️ Erreur MineStrator : `{error_msg}`")
    except Exception as e:
        await interaction.followup.send(f"💥 Erreur critique : `{str(e)}`")

# Lancement du serveur Web dans un thread séparé
threading.Thread(target=run_web_server).start()

# Lancement du bot Discord
bot.run(TOKEN)
