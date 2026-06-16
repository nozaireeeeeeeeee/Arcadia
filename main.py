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
    return "Le bot Arcadia est en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------- PARTIE BOT DISCORD -----------------
TOKEN = os.environ.get("DISCORD_TOKEN")
API_KEY = os.environ.get("MINESTRATOR_API_KEY")
URL_DEMARRAGE = os.environ.get("MINESTRATOR_URL")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

bot = commands.Bot()

# Force l'activation instantanée de la commande sur ton serveur Discord précis
guild_ids_list = [int(GUILD_ID)] if GUILD_ID else None

@bot.event
async def on_ready():
    print(f"✅ Arcadia Bot connecté avec succès en tant que : {bot.user}")
    await bot.sync_all_application_commands()

@bot.slash_command(
    name="start",
    description="Lance le serveur Minecraft Arcadia SMP.",
    guild_ids=guild_ids_list
)
async def start_server(interaction: nextcord.Interaction):
    # Sécurité : Seuls les admins du Discord peuvent l'utiliser
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    # Évite le message "This command is outdated" ou les timeouts Discord
    await interaction.response.defer()

    # Configuration des Headers avec le USER-AGENT pour contourner le blocage 403 Forbidden
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Envoi de la requête à MineStrator
        response = requests.post(URL_DEMARRAGE, headers=headers)
        
        # Si MineStrator répond positivement (Code 200 ou 204)
        if response.status_code in [200, 204]:
            await interaction.followup.send("🚀 **Le serveur Arcadia SMP est en cours de démarrage !**")
        else:
            await interaction.followup.send(
                f"⚠️ L'API MineStrator a refusé la demande.\n"
                f"• **Code HTTP :** `{response.status_code}`\n"
                f"• **Réponse :** `{response.text[:150]}`"
            )
            
    except Exception as e:
        await interaction.followup.send(f"💥 Une erreur est survenue dans le script : `{str(e)}`")

# Lancement du serveur Web anti-veille (UptimeRobot)
threading.Thread(target=run_web_server).start()

# Lancement du bot Discord
bot.run(TOKEN)
