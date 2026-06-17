import os
import threading
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# 1. Serveur Web pour Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
MINE_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("✅ Commandes synchronisées !")
    except Exception as e:
        print(f"⚠️ Erreur sync : {e}")

# 3. Fonction d'appel API automatique (Start / Stop)
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    await interaction.response.defer()
    headers = {"Authorization": f"Bearer {MINE_TOKEN}", "Content-Type": "application/json"}
    
    # Le bot va tester ces 3 URLs de MineStrator l'une après l'autre
    urls_to_try = [
        f"https://api.minestrator.com/v1/server/{SERVER_ID}/{action}",
        f"https://api.minestrator.com/v1/servers/{SERVER_ID}/{action}",
        f"https://api.minestrator.com/v1/server/{SERVER_ID}/action/{action}"
    ]

    for url in urls_to_try:
        try:
            r = requests.post(url, headers=headers, timeout=5)
            if r.status_code in (200, 204, 201):
                await interaction.followup.send(f"🟢 Commande **{action.upper()}** validée !")
                return
        except Exception:
            continue # Si ça échoue (404), on passe à l'URL suivante
            
    await interaction.followup.send("❌ Erreur 404 : MineStrator n'a accepté aucune des URLs. Vérifie que ton `SERVER_ID` dans Railway est correct.")

# 4. Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

@bot.slash_command(name="list_servers", description="Affiche tes serveurs")
async def list_servers(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    headers = {"Authorization": f"Bearer {MINE_TOKEN}", "Content-Type": "application/json"}
    
    # Le bot va tester ces 3 structures pour récupérer les infos
    urls_to_try = [
        f"https://api.minestrator.com/v1/server/{SERVER_ID}",
        f"https://api.minestrator.com/v1/servers/{SERVER_ID}",
        f"https://api.minestrator.com/v1/server/{SERVER_ID}/status"
    ]
    
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                msg = f"📋 **Informations du serveur :**\n"
                msg += f"• **Nom :** {data.get('name', 'Inconnu')}\n"
                msg += f"• **ID :** {data.get('id', SERVER_ID)}\n"
                msg += f"• **Statut :** {data.get('status', 'Inconnu')}\n"
                await interaction.followup.send(msg, ephemeral=True)
                return
        except Exception:
            continue
            
    await interaction.followup.send("❌ Erreur 404 : Impossible de trouver ton serveur. Vérifie ton `SERVER_ID` et ton `MINESTRATOR_TOKEN` dans Railway.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
