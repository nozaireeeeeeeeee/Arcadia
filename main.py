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
    # Sécurité : Seuls les admins du Discord peuvent l'utiliser
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    # Indique à Discord que le bot réfléchit (évite le timeout)
    await interaction.response.defer()

    # Configuration de la requête vers MineStrator
    url = f"https://api.minestrator.com/v1/server/{SERVER_ID}/action/start"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Envoi de la demande à MineStrator
        response = requests.post(url, headers=headers)
        
        # Affichage de sécurité dans les logs de Render pour le débug
        print(f"[DEBUG] Code HTTP reçu de MineStrator : {response.status_code}")
        print(f"[DEBUG] Réponse brute reçue : {response.text}")

        # Si MineStrator répond que tout s'est bien passé (Code 200)
        if response.status_code == 200:
            await interaction.followup.send("🚀 **Le serveur MineStrator est en cours de démarrage !**")
        else:
            # Si le code n'est pas 200, on affiche le texte brut reçu pour comprendre l'erreur
            # Cela évite le crash "Extra data" si MineStrator renvoie du HTML ou du texte pur
            texte_erreur = response.text[:200]  # On prend les 200 premiers caractères max
            await interaction.followup.send(
                f"⚠️ L'API MineStrator a refusé la demande.\n"
                f"• **Code HTTP :** `{response.status_code}`\n"
                f"• **Message reçu :** `{texte_erreur}`"
            )
            
    except Exception as e:
        # En cas de coupure de connexion ou problème réseau majeur
        await interaction.followup.send(f"💥 Une erreur critique est survenue dans le script : `{str(e)}`")

# Lancement du serveur Web anti-veille dans un thread séparé
threading.Thread(target=run_web_server).start()

# Lancement du bot Discord
bot.run(TOKEN)
