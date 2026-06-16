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

# Récupération de la Whitelist (séparée par des virgules si plusieurs ID)
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté avec succès sur Railway : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("✅ Toutes les commandes (start, stop, list_servers) ont été synchronisées !")
    except Exception as e:
        print(f"⚠️ Erreur lors de la synchronisation : {e}")

# 3. Fonction d'appel API MineStrator (Start / Stop)
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    # WHITELIST : Vérification de l'ID
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation d'utiliser cette commande.", ephemeral=True)
        return

    await interaction.response.defer()

    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.minestrator.com/v1/servers/{SERVER_ID}/{action}"

    try:
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code in (200, 204, 201):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** validée par MineStrator !")
        elif r.status_code == 404:
            await interaction.followup.send(f"❌ **Erreur 404** : Le serveur `{SERVER_ID}` est introuvable.")
        elif r.status_code == 401:
            await interaction.followup.send("❌ **Erreur 401** : Ta clé API MineStrator est refusée.")
        else:
            await interaction.followup.send(f"❌ MineStrator a répondu avec le code : {r.status_code}")
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}")

# 4. Commandes Slash Discord

@bot.slash_command(name="start", description="Démarre le serveur MineStrator")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur MineStrator")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

@bot.slash_command(name="list_servers", description="Affiche la liste de tes serveurs")
async def list_servers(interaction: nextcord.Interaction):
    # WHITELIST
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Tentative avec /me/servers
    url = "https://api.minestrator.com/v1/me/servers"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            await interaction.followup.send(f"✅ Succès ! Voici la réponse : {r.text[:1000]}", ephemeral=True)
        else:
            # Cette fois, on affiche le code ET le texte renvoyé par l'API
            await interaction.followup.send(f"❌ Erreur {r.status_code}. Texte de l'API : {r.text}", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    url = "https://api.minestrator.com/v1/servers"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            servers = data.get("servers", data)
            
            if isinstance(servers, list) and len(servers) > 0:
                msg = "📋 **Tes serveurs MineStrator trouvés :**\n"
                for s in servers:
                    s_id = s.get("id") or s.get("server_id") or s.get("uuid") or "Inconnu"
                    s_name = s.get("name") or "Serveur Minecraft"
                    msg += f"• **Nom :** {s_name} | **ID :** `{s_id}`\n"
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.followup.send("📋 Aucun serveur trouvé.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Impossible de récupérer la liste (Code HTTP {r.status_code}).", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {str(e)}", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
