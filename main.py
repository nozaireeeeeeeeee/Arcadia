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
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("✅ Commandes synchronisées !")
    except Exception as e:
        print(f"⚠️ Erreur sync : {e}")

# 3. Fonction d'appel API (Start / Stop)
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    # Vérification Whitelist
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    # On prévient Discord qu'on travaille (defer)
    await interaction.response.defer()
    
    headers = {"Authorization": f"Bearer {MINE_TOKEN}", "Content-Type": "application/json"}
    url = f"https://api.minestrator.com/v1/servers/{SERVER_ID}/{action}"

    try:
        r = requests.post(url, headers=headers, timeout=15)
        if r.status_code in (200, 204, 201):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** validée !")
        else:
            await interaction.followup.send(f"❌ Erreur {r.status_code} : {r.text}")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {str(e)}")

# 4. Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

@bot.slash_command(name="list_servers", description="Affiche la liste de tes serveurs")
async def list_servers(interaction: nextcord.Interaction):
    # 1. Vérification Whitelist
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    # 2. Defer unique (pour éviter les erreurs d'interaction)
    await interaction.response.defer(ephemeral=True)
    
    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}", 
        "Content-Type": "application/json"
    }
    
    # Tentative avec /me/servers (plus probable pour lister tes serveurs)
    url = "https://api.minestrator.com/v1/me/servers"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Construction du message
            msg = "📋 **Tes serveurs trouvés :**\n"
            # On vérifie si c'est une liste ou un dict
            servers = data if isinstance(data, list) else data.get("servers", [])
            
            if not servers:
                msg = "📋 Aucun serveur trouvé sous ce compte."
            else:
                for s in servers:
                    msg += f"• {s.get('name', 'Serveur')} | ID : `{s.get('id', 'N/A')}`\n"
            
            await interaction.followup.send(msg, ephemeral=True)
            
        else:
            # Si ça échoue encore, on affiche la réponse exacte pour comprendre
            await interaction.followup.send(f"❌ Erreur {r.status_code} : {r.text}", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {str(e)}", ephemeral=True)
        return

    # 2. On "defer" une seule fois, UNIQUEMENT si l'utilisateur est autorisé
    await interaction.response.defer(ephemeral=True)
    
    headers = {"Authorization": f"Bearer {MINE_TOKEN}", "Content-Type": "application/json"}
    url = "https://api.minestrator.com/v1/me/servers"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            servers = data if isinstance(data, list) else data.get("servers", [])
            
            if not servers:
                await interaction.followup.send("📋 Aucun serveur trouvé.", ephemeral=True)
            else:
                msg = "📋 **Tes serveurs trouvés :**\n"
                for s in servers:
                    s_id = s.get("id") or "Inconnu"
                    s_name = s.get("name") or "Serveur Minecraft"
                    msg += f"• {s_name} | ID : `{s_id}`\n"
                await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Erreur {r.status_code} : {r.text}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
