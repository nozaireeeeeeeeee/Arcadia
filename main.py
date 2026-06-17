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

# Configuration des headers avec "User-Agent" pour contourner Nginx
def get_headers():
    return {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

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
    headers = get_headers()
    
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
            continue
            
    await interaction.followup.send(f"❌ Erreur : MineStrator refuse l'accès (403/404). Vérifie les permissions de ta clé API principale.")

# 4. Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut en temps réel du serveur")
async def server_status(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    headers = get_headers()
    
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
                status = str(data.get('status', 'Inconnu')).lower()
                
                # Choix de l'émoji selon la réponse de MineStrator
                if status in ["online", "en ligne", "started", "running"]:
                    emoji = "🟢"
                elif status in ["offline", "éteint", "stopped", "off"]:
                    emoji = "🔴"
                else:
                    emoji = "🟠" # Pour "starting" ou "stopping"
                
                await interaction.followup.send(f"{emoji} **Statut actuel :** {status.upper()}", ephemeral=True)
                return
        except Exception:
            continue
            
    await interaction.followup.send(f"❌ Impossible de récupérer le statut. Nginx ou l'API MineStrator bloque la requête.", ephemeral=True)

@bot.slash_command(name="list_servers", description="Affiche les détails complets de ton serveur")
async def list_servers(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    headers = get_headers()
    
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
            
    await interaction.followup.send(f"❌ Impossible de récupérer les détails. Nginx ou l'API MineStrator bloque la requête.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
