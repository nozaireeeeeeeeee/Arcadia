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
bot = commands.Bot()

TOKEN = os.environ.get("DISCORD_TOKEN")
MINE_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")

@bot.event
async def on_ready():
    print(f"Bot connecté sur Railway : {bot.user}")
    await bot.sync_all_application_commands()

# 3. Fonction API MineStrator (Retour à l'adresse d'origine fonctionnelle)
async def call_minestrator(interaction: nextcord.Interaction, action: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    await interaction.response.defer()

    headers = {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # On remet l'ID directement dans l'URL comme à l'origine
    url = f"https://api.minestrator.com/public/v1/server/{SERVER_ID}/action"
    payload = {"action": action}

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"[MINESTRATOR] Action: {action.upper()} | Code HTTP: {r.status_code}")
        
        if r.status_code in (200, 204):
            await interaction.followup.send(f"🟢 Commande **{action.upper()}** transmise à MineStrator avec succès !")
        elif r.status_code == 404:
            await interaction.followup.send(
                f"❌ **Erreur 404** : MineStrator ne trouve aucun serveur avec l'ID `{SERVER_ID}` pour ce token.\n"
                "Utilise la commande `/list_servers` pour découvrir le bon ID."
            )
        elif r.status_code == 401:
            await interaction.followup.send("❌ **Erreur 401** : Ta clé API `MINESTRATOR_TOKEN` est refusée par MineStrator.")
        else:
            await interaction.followup.send(f"❌ MineStrator a renvoyé le code {r.status_code}.")
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur de connexion : {str(e)}")

# NOUVELLE COMMANDE DE DIAGNOSTIC
@bot.slash_command(name="list_servers", description="Affiche la liste de tes serveurs pour trouver le bon ID")
async def list_servers(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    headers = {"Authorization": f"Bearer {MINE_TOKEN}"}
    url = "https://api.minestrator.com/public/v1/servers"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            servers = data.get("servers", data)
            if isinstance(servers, list) and len(servers) > 0:
                msg = "📋 **Tes serveurs MineStrator trouvés :**\n"
                for s in servers:
                    s_id = s.get("id") or s.get("server_id") or s.get("uuid")
                    s_name = s.get("name") or "Serveur Minecraft"
                    msg += f"• **Nom :** {s_name} | **ID à mettre sur Railway :** `{s_id}`\n"
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.followup.send(f"📋 Aucun serveur trouvé. Réponse de l'API : `{r.text[:200]}`", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Impossible de lister les serveurs. Code HTTP MineStrator : {r.status_code}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {str(e)}", ephemeral=True)

# 4. Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur MineStrator")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur MineStrator")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
