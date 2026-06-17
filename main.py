import os
import threading
import datetime
import time
import requests
from flask import Flask
import nextcord
from nextcord.ext import commands

# 1. Moteur de double journalisation
def write_bot_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [DISCORD] {message}\n"
    print(line.strip())
    with open("log_bot.txt", "a", encoding="utf-8") as f:
        f.write(line)

def write_mine_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [API_MINESTRATOR] {message}\n"
    print(line.strip())
    with open("log_minestrator.txt", "a", encoding="utf-8") as f:
        f.write(line)

for filename in ["log_bot.txt", "log_minestrator.txt"]:
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- Création du fichier le {datetime.datetime.now()} ---\n")

# 2. Serveur Web pour Railway (Keep-Alive)
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator API actif (Zéro Selenium) !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")
MINESTRATOR_TOKEN = os.environ.get("MINESTRATOR_TOKEN")

@bot.event
async def on_ready():
    write_bot_log(f"Bot connecté sous le nom : {bot.user}")

@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, exception):
    write_bot_log(f"Crash commande /{interaction.application_command.name} | Erreur : {str(exception)}")
    try:
        msg = "❌ Le bot a rencontré une erreur. Utilise `/log` pour télécharger les rapports."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# 4. Traitement des requêtes vers l'API de MineStrator
def api_worker(action, server_id, token):
    if not token or token == "None":
        write_mine_log("❌ ERREUR : La variable MINESTRATOR_TOKEN n'est pas configurée sur Railway !")
        return "❌ Erreur : Le Token d'API MineStrator est introuvable dans tes variables Railway."

    write_mine_log(f"Envoi de la requête API pour l'action : [{action.upper()}]")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # On teste d'abord la route globale de l'API
    base_url = f"https://api.minestrator.com/v1/server/{server_id}"

    try:
        # CAS 1 : Lecture du statut ou détails du serveur
        if action in ["statut", "list_servers"]:
            response = requests.get(base_url, headers=headers, timeout=10)
            write_mine_log(f"Réponse API Statut (Route 1) Code: {response.status_code}")
            
            # Secours si l'API utilise une route alternative
            if response.status_code == 404:
                base_url = f"https://api.minestrator.com/v1/serveur/{server_id}"
                response = requests.get(base_url, headers=headers, timeout=10)
                write_mine_log(f"Réponse API Statut (Route 2) Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                status_raw = data.get("status", data.get("data", {}).get("status", "unknown")).lower()
                
                if action == "statut":
                    if status_raw in ["on", "online", "started", "running"]:
                        return f"🟢 **EN LIGNE**"
                    elif status_raw in ["off", "offline", "stopped"]:
                        return f"🔴 **ÉTEINT**"
                    else:
                        return f"🟠 **STATUT : {status_raw.upper()}** (En cours)"
                
                elif action == "list_servers":
                    name = data.get("name", data.get("data", {}).get("name", "Serveur Minecraft"))
                    return f"📋 **Détails de ton instance :**\n• **Nom :** `{name}`\n• **ID :** `{server_id}`\n• **Statut :** `{status_raw.upper()}`\n• **Connexion :** API Directe ⚡"
            
            elif response.status_code == 401:
                return "❌ Erreur : Ton `MINESTRATOR_TOKEN` sur Railway est incorrect ou expiré."
            else:
                return f"❌ Erreur API MineStrator (Code {response.status_code})."

        # CAS 2 : Actions d'alimentation (Démarrer / Arrêter)
        elif action in ["start", "stop"]:
            action_url = f"https://api.minestrator.com/v1/server/{server_id}/action"
            payload = {"action": action}
            
            response = requests.post(action_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 404:
                action_url = f"https://api.minestrator.com/v1/serveur/{server_id}/action"
                response = requests.post(action_url, headers=headers, json=payload, timeout=10)

            write_mine_log(f"Réponse API Action Code: {response.status_code}")
            
            if response.status_code in [200, 201, 204]:
                return f"✅ L'ordre de **{action.upper()}** a été transmis à ton serveur !"
            else:
                return f"❌ Impossible d'exécuter l'action. Code API : {response.status_code}"

    except Exception as e:
        write_mine_log(f"❌ CRASH API : {str(e)}")
        return f"❌ Échec de la connexion avec MineStrator."

# 5. Connecteurs de Commandes Discord Slash
async def run_command_flow(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    write_bot_log(f"Commande /{action} lancée")
    await interaction.response.defer(ephemeral=(action in ["statut", "list_servers"]))
    
    def thread_target():
        res = api_worker(action, SERVER_ID, MINESTRATOR_TOKEN)
        bot.loop.create_task(interaction.followup.send(res))
        
    threading.Thread(target=thread_target, daemon=True).start()

@bot.slash_command(name="start", description="Démarre le serveur via l'API MineStrator")
async def start_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur via l'API MineStrator")
async def stop_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut du serveur")
async def status_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "statut")

@bot.slash_command(name="list_servers", description="Affiche les configurations de ton instance")
async def list_servers(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "list_servers")

# Commande de debug pour afficher la liste de tes serveurs et leurs IDs
@bot.slash_command(name="debug", description="Affiche la liste de tes serveurs pour trouver le bon ID")
async def debug_server(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    headers = {"Authorization": f"Bearer {MINESTRATOR_TOKEN}", "Accept": "application/json"}
    try:
        # On interroge l'API pour lister TOUS les serveurs associés au token
        response = requests.get("https://api.minestrator.com/v1/servers", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # On formate la réponse pour qu'elle soit lisible sur Discord
            res_text = str(data)[:1900] # Limite de caractères Discord
            await interaction.followup.send(f"📋 **Voici ce que l'API renvoie :**\n```json\n{res_text}\n```", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Erreur API : {response.status_code} - {response.text}", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur : {str(e)}", ephemeral=True)

@bot.slash_command(name="log", description="Télécharge les fichiers de log")
async def get_bot_logs(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    files_to_send = []
    if os.path.exists("log_bot.txt"):
        files_to_send.append(nextcord.File("log_bot.txt"))
    if os.path.exists("log_minestrator.txt"):
        files_to_send.append(nextcord.File("log_minestrator.txt"))

    if files_to_send:
        await interaction.followup.send(content="📋 **Logs :**", files=files_to_send, ephemeral=True)
    else:
        await interaction.followup.send("⚠️ Aucun log.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
