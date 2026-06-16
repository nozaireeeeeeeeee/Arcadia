import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# --- SERVEUR WEB ANTI-VEILLE ---
app = Flask('')
@app.route('/')
def home(): return "Bot en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT DISCORD ---
TOKEN = os.environ.get("DISCORD_TOKEN")
API_KEY = os.environ.get("MINESTRATOR_API_KEY")
# On récupère l'URL complète directement depuis Render
URL_DEMARRAGE = os.environ.get("MINESTRATOR_URL")

bot = commands.Bot()

@bot.event
async def on_ready():
    print(f"✅ Bot connecté")

@bot.slash_command(name="start", description="Lance le serveur Minecraft.")
async def start_server(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Pas la permission.", ephemeral=True)
        return

    await interaction.response.defer()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(URL_DEMARRAGE, headers=headers)
        
        if response.status_code in [200, 204]: # 200 ou 204 = Succès
            await interaction.followup.send("🚀 **Le serveur démarre enfin !**")
        else:
            await interaction.followup.send(
                f"⚠️ MineStrator bloque.\n"
                f"• Code HTTP : `{response.status_code}`\n"
                f"• Message : `{response.text[:150]}`"
            )
    except Exception as e:
        await interaction.followup.send(f"💥 Erreur script : `{str(e)}`")

threading.Thread(target=run_web_server).start()
bot.run(TOKEN)
