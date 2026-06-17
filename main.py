import os
import threading
import datetime
import time
from flask import Flask
import nextcord
from nextcord.ext import commands

# Imports Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# 1. Moteur de double journalisation (Fichiers locaux)
def write_bot_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [DISCORD] {message}\n"
    print(line.strip())
    with open("log_bot.txt", "a", encoding="utf-8") as f:
        f.write(line)

def write_mine_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [SELENIUM] {message}\n"
    print(line.strip())
    with open("log_minestrator.txt", "a", encoding="utf-8") as f:
        f.write(line)

for filename in ["log_bot.txt", "log_minestrator.txt"]:
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- Création du fichier le {datetime.datetime.now()} ---\n")

# 2. Serveur Web pour Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator Selenium actif !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")
MINE_EMAIL = os.environ.get("MINE_EMAIL")
MINE_PASSWORD = os.environ.get("MINE_PASSWORD")

def get_selenium_driver():
    options = Options()
    options.add_argument("--headless")  # Obligatoire sur serveur en cloud
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Chemins d'accès natifs injectés par notre Dockerfile
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

@bot.event
async def on_ready():
    write_bot_log(f"Bot connecté sous le nom : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        write_bot_log("Commandes slash synchronisées.")
    except Exception as e:
        write_bot_log(f"Erreur sync : {str(e)}")

@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, exception):
    write_bot_log(f"Crash commande /{interaction.application_command.name} | Erreur : {str(exception)}")
    try:
        msg = "❌ Le bot a rencontré une erreur. Utilise `/log` pour télécharger la boîte noire."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# 4. Automatisation de la simulation Chrome
def selenium_worker(action, server_id, email, password):
    write_mine_log(f"Démarrage du navigateur pour l'action : [{action.upper()}]")
    driver = None
    try:
        driver = get_selenium_driver()
        
        # Connexion au panel
        write_mine_log("Navigation vers la page de login...")
        driver.get("https://panel.minestrator.com/login")
        time.sleep(4)
        
        write_mine_log(f"Tentative d'identification pour : {email}")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()
        time.sleep(5)
        write_mine_log("Formulaire de connexion soumis.")
        
        # Navigation vers le serveur ciblé
        target_url = f"https://panel.minestrator.com/instance/{server_id}"
        write_mine_log(f"Navigation vers l'instance : {target_url}")
        driver.get(target_url)
        time.sleep(5)
        
        page_text = driver.page_source.lower()
        
        # Traitement de l'action demandée
        if action == "statut":
            write_mine_log("Lecture du statut sur la page...")
            if "en ligne" in page_text or "online" in page_text or "started" in page_text:
                return "🟢 EN LIGNE"
            elif "éteint" in page_text or "offline" in page_text or "stopped" in page_text:
                return "🔴 ÉTEINT"
            else:
                return "🟠 EN COURS DE DÉMARRAGE / ARRÊT"
                
        elif action == "list_servers":
            write_mine_log("Lecture des détails de l'instance pour list_servers...")
            status_info = "🟢 EN LIGNE" if ("en ligne" in page_text or "online" in page_text) else "🔴 ÉTEINT"
            return f"📋 **Détails de ton serveur MineStrator :**\n• **ID de l'instance :** `{server_id}`\n• **Statut actuel :** {status_info}\n• **Mode d'accès :** Navigateur Émulé (Sécurisé)"

        elif action in ["start", "stop"]:
            write_mine_log(f"Recherche du bouton [{action.upper()}]...")
            keyword = "Démarrer" if action == "start" else "Arrêter"
            btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{keyword}')] | //a[contains(text(), '{keyword}')]")
            btn.click()
            write_mine_log(f"Clic effectué sur le bouton {keyword}.")
            time.sleep(2)
            return f"✅ L'action navigateur **{action.upper()}** a été transmise avec succès au panel !"

    except Exception as e:
        write_mine_log(f"❌ CRASH SÉLENIUM : {str(e)}")
        return f"❌ Échec de l'opération. Télécharge le fichier `log_minestrator.txt` via la commande `/log`."
    finally:
        if driver:
            driver.quit()
            write_mine_log("Navigateur Chrome fermé proprement.")

# 5. Connecteurs de Commandes Discord Slash
async def run_command_flow(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        write_bot_log(f"Alerte sécurité : /{action} refusé pour l'utilisateur {interaction.user.name}")
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    write_bot_log(f"Commande /{action} initiée par {interaction.user.name}")
    await interaction.response.defer(ephemeral=(action in ["statut", "list_servers"]))
    
    def thread_target():
        res = selenium_worker(action, SERVER_ID, MINE_EMAIL, MINE_PASSWORD)
        bot.loop.create_task(interaction.followup.send(res))
        
    threading.Thread(target=thread_target, daemon=True).start()

@bot.slash_command(name="start", description="Démarre le serveur Minecraft via simulation Chrome")
async def start_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur Minecraft via simulation Chrome")
async def stop_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut en direct de la machine")
async def status_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "statut")

@bot.slash_command(name="list_servers", description="Affiche les configurations de ton instance")
async def list_servers(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "list_servers")

@bot.slash_command(name="log", description="Télécharge instantanément les deux boîtes noires du système")
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
