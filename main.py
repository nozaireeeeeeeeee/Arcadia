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
    
    # URL de base de l'API officielle pour ton instance
    base_url = f"https://api.minestrator.com/v1/instance/{server_id}"

    try:
        # CAS 1 : Lecture du statut ou détails du serveur
        if action in ["statut", "list_servers"]:
            response = requests.get(base_url, headers=headers, timeout=10)
            write_mine_log(f"Réponse API Statut reçue Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Extraction du statut depuis le format JSON de MineStrator
                status_raw = data.get("status", data.get("data", {}).get("status", "unknown")).lower()
                
                if action == "statut":
                    if status_raw in ["on", "online", "started", "running"]:
                        return f"🟢 **EN LIGNE**"
                    elif status_raw in ["off", "offline", "stopped"]:
                        return f"🔴 **ÉTEINT**"
                    else:
                        return f"🟠 **STATUT : {status_raw.upper()}** (En cours de changement)"
                
                elif action == "list_servers":
                    name = data.get("name", data.get("data", {}).get("name", "Serveur Minecraft"))
                    slots = data.get("slots", data.get("data", {}).get("slots", "N/A"))
                    return f"📋 **Détails de ton instance MineStrator :**\n• **Nom :** `{name}`\n• **ID d'instance :** `{server_id}`\n• **Statut :** `{status_raw.upper()}`\n• **Slots :** `{slots}`\n• **Connexion :** Directe par API Sécurisée ⚡"
            
            elif response.status_code == 401:
                return "❌ Erreur : Ton `MINESTRATOR_TOKEN` est invalide ou a expiré. Régénère-le sur ton panel."
            else:
                return f"❌ L'API a répondu avec une erreur {response.status_code}."

        # CAS 2 : Actions d'alimentation (Démarrer / Arrêter)
        elif action in ["start", "stop"]:
            action_url = f"{base_url}/action"
            # Payload attendu par l'API MineStrator pour piloter la machine
            payload = {"action": action}
            
            response = requests.post(action_url, headers=headers, json=payload, timeout=10)
            write_mine_log(f"Réponse API Action [{action.upper()}] reçue Code: {response.status_code}")
            
            if response.status_code in [200, 201, 204]:
                return f"✅ L'ordre de **{action.upper()}** a été transmis instantanément à ton serveur !"
            elif response.status_code == 401:
                return "❌ Erreur d'authentification : Ton token d'API est incorrect."
            else:
                return f"❌ Impossible d'exécuter l'action. Code API : {response.status_code}"

    except Exception as e:
        write_mine_log(f"❌ CRASH INTERNE DE L'API : {str(e)}")
        return f"❌ Échec de la connexion avec l'API MineStrator. (Vérifie tes logs avec `/log`)"

# 5. Connecteurs de Commandes Discord Slash
async def run_command_flow(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        write_bot_log(f"Alerte sécurité : /{action} refusé pour l'utilisateur {interaction.user.name}")
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    write_bot_log(f"Commande /{action} initiée par {interaction.user.name}")
    
    # On diffère la réponse car l'API peut mettre une demi-seconde à répondre
    await interaction.response.defer(ephemeral=(action in ["statut", "list_servers"]))
    
    def thread_target():
        res = api_worker(action, SERVER_ID, MINESTRATOR_TOKEN)
        bot.loop.create_task(interaction.followup.send(res))
        
    threading.Thread(target=thread_target, daemon=True).start()

@bot.slash_command(name="start", description="Démarre instantanément le serveur via l'API MineStrator")
async def start_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "start")

@bot.slash_command(name="stop", description="Arrête instantanément le serveur via l'API MineStrator")
async def stop_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut en direct de la machine via l'API")
async def status_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "statut")

@bot.slash_command(name="list_servers", description="Affiche les configurations de ton instance via l'API")
async def list_servers(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "list_servers")

@bot.slash_command(name="log", description="Télécharge instantanément les fichiers de log du système")
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
        await interaction.followup.send(
            content="📋 **Voici l'extraction complète de tes logs :**",
            files=files_to_send,
            ephemeral=True
        )
    else:
        await interaction.followup.send("⚠️ Aucun fichier de log généré pour le moment.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
