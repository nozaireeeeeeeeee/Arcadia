import os
import threading
import datetime
import io
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests

# 1. Système de gestion des Logs en mémoire
BOT_LOGS = []

def add_log(category, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] [{category.upper()}] {message}"
    print(log_line) # Reste visible sur Railway
    BOT_LOGS.append(log_line)
    if len(BOT_LOGS) > 50:
        BOT_LOGS.pop(0)

# 2. Serveur Web pour Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
MINE_TOKEN = os.environ.get("MINESTRATOR_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

def get_headers():
    return {
        "Authorization": f"Bearer {MINE_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

@bot.event
async def on_ready():
    add_log("system", f"Bot connecté : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        add_log("system", "Commandes Slash synchronisées avec Discord !")
    except Exception as e:
        add_log("error", f"Erreur de synchronisation : {str(e)}")

# Intercepteur universel d'erreurs Discord
@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, exception):
    error_msg = f"La commande /{interaction.application_command.name} a crashé. Raison : {str(exception)}"
    add_log("crash", error_msg)
    
    try:
        msg = "❌ Une erreur interne est survenue. Tape `/log` pour voir le rapport d'erreur."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# 4. Fonction d'appel API automatique
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

    add_log("api", f"Tentative d'action [{action.upper()}] pour le serveur {SERVER_ID}")

    for url in urls_to_try:
        try:
            r = requests.post(url, headers=headers, timeout=5)
            add_log("api", f"Test URL: {url} -> Code reçu: {r.status_code}")
            if r.status_code in (200, 204, 201):
                await interaction.followup.send(f"🟢 Commande **{action.upper()}** validée !")
                add_log("success", f"Action {action.upper()} réussie.")
                return
        except Exception as e:
            add_log("error", f"Échec de connexion sur {url} : {str(e)}")
            continue
            
    await interaction.followup.send(f"❌ L'API MineStrator a refusé la commande. Fais `/log` pour enquêter.")

# 5. Les Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur")
async def start_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur")
async def stop_server(interaction: nextcord.Interaction):
    await call_minestrator(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut du serveur")
async def server_status(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Pas d'autorisation.", ephemeral=True)
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
            add_log("api", f"Test Statut URL: {url} -> Code: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                status = str(data.get('status', 'Inconnu')).lower()
                emoji = "🟢" if "on" in status or "run" in status else "🔴"
                await interaction.followup.send(f"{emoji} **Statut :** {status.upper()}", ephemeral=True)
                return
        except Exception as e:
            add_log("error", f"Échec statut sur {url} : {str(e)}")
            continue
            
    await interaction.followup.send(f"❌ Impossible de récupérer le statut. Fais `/log`.", ephemeral=True)

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
            
    await interaction.followup.send(f"❌ Impossible de récupérer les détails. Fais `/log`.", ephemeral=True)

# 🛠️ LA COMMANDE DE LOGS ET DIAGNOSTIC REMASTERISÉE
@bot.slash_command(name="log", description="Affiche l'historique des erreurs et l'aide au diagnostic")
async def get_bot_logs(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Réservé aux administrateurs du bot.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    recap_diagnostic = (
        "📊 **GUIDE DE DIAGNOSTIC RAPIDE (Pourquoi ça rate ?)**\n"
        "---\n"
        "• 🔒 **Erreur 403 Forbidden :** Ton token `MINESTRATOR_TOKEN` n'est pas le bon (prends la **Clé principale** tout en haut sur leur site) OU alors MineStrator bloque Railway avec leur protection DDoS.\n"
        "• 🔍 **Erreur 404 Not Found :** L'ID du serveur dans `SERVER_ID` sur Railway est faux.\n"
        "---\n"
        "📋 **HISTORIQUE RÉCENT DES ERREURS DU BOT :**\n"
    )

    if not BOT_LOGS:
        log_text = "Aucune erreur enregistrée pour le moment. Le bot tourne parfaitement !"
    else:
        log_text = "\n".join(BOT_LOGS)

    full_message = f"{recap_diagnostic}```txt\n{log_text}\n```"

    if len(full_message) > 1950:
        clean_logs = "\n".join(BOT_LOGS)
        log_file = nextcord.File(io.StringIO(clean_logs), filename="logs_erreur_bot.txt")
        await interaction.followup.send(content=recap_diagnostic + "⚠️ *Logs trop longs, envoyés en fichier joint :*", file=log_file, ephemeral=True)
    else:
        await interaction.followup.send(full_message, ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
