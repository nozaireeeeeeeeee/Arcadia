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
from webdriver_manager.chrome import ChromeDriverManager

# 1. Moteur de double journalisation (File Logging)
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

# Initialisation des fichiers pour éviter les bugs de lecture
for filename in ["log_bot.txt", "log_minestrator.txt"]:
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- Création du fichier le {datetime.datetime.now()} ---\n")

# 2. Serveur Web de maintien en vie pour Railway
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
    options.add_argument("--headless")  # Mode sans écran indispensable sur Railway
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
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
        msg = "❌ Le bot a rencontré une erreur de script. Utilise `/log` pour télécharger la boîte noire."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# 4. Cerveau d'automatisation Selenium (Exécuté en tâche de fond)
def selenium_worker(action, server_id, email, password):
    write_mine_log(f"Démarrage du navigateur pour l'action : [{action.upper()}]")
    driver = None
    try:
        driver = get_selenium_driver()
        
        # Étape 1 : Connexion à MineStrator
        write_mine_log("Navigation vers la page de login...")
        driver.get("https://panel.minestrator.com/login")
        time.sleep(4)
        
        write_mine_log(f"Tentative d'identification pour l'adresse : {email}")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()
        time.sleep(5)
        write_mine_log("Formulaire de connexion soumis avec succès.")
        
        # Étape 2 : Accès à l'instance du serveur
        target_url = f"https://panel.minestrator.com/instance/{server_id}"
        write_mine_log(f"Navigation vers l'instance du serveur Minecraft : {target_url}")
        driver.get(target_url)
        time.sleep(5)
        
        # Étape 3 : Traitement des actions
        if action == "statut":
            write_mine_log("Scraping du statut du serveur...")
            # Recherche textuelle globale ou par classe générique du badge de statut
            page_text = driver.page_source.lower()
            if "en ligne" in page_text or "online" in page_text or "started" in page_text:
                return "🟢 EN LIGNE"
            elif "éteint" in page_text or "offline" in page_text or "stopped" in page_text:
                return "🔴 ÉTEINT"
            else:
                return "🟠 EN COURS DE DÉMARRAGE / ARRÊT"
                
        elif action in ["start", "stop"]:
            write_mine_log(f"Recherche du bouton de contrôle [{action.upper()}]...")
            # Recherche d'un bouton contenant le mot clé (s'adapte si le panel change de structure)
            keyword = "Démarrer" if action == "start" else "Arrêter"
            btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{keyword}')] | //a[contains(text(), '{keyword}')]")
            btn.click()
            write_mine_log(f"Clic effectué sur le bouton {keyword}.")
            time.sleep(2)
            return f"✅ L'action navigateur **{action.upper()}** a été envoyée au panel MineStrator !"

    except Exception as e:
        write_mine_log(f"❌ CRASH SÉLENIUM : {str(e)}")
        return f"❌ Échec de la simulation de navigation. Consulte `/log` pour voir le rapport."
    finally:
        if driver:
            driver.quit()
            write_mine_log("Navigateur Chrome fermé proprement.")

# 5. Commandes de contrôle sur Discord
async def run_command_flow(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        write_bot_log(f"Alerte sécurité : L'utilisateur {interaction.user.name} ({interaction.user.id}) a tenté d'utiliser /{action} sans autorisation.")
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    write_bot_log(f"Commande /{action} activée par {interaction.user.name}")
    await interaction.response.defer(ephemeral=(action == "statut"))
    
    # Exécution dans un thread séparé pour ne pas faire geler ou expirer l'interaction Discord
    def thread_target():
        res = selenium_worker(action, SERVER_ID, MINE_EMAIL, MINE_PASSWORD)
        bot.loop.create_task(interaction.followup.send(res))
        
    threading.Thread(target=thread_target, daemon=True).start()

@bot.slash_command(name="start", description="Démarre le serveur via simulation Chrome")
async def start_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur via simulation Chrome")
async def stop_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "stop")

@bot.slash_command(name="statut", description="Scrape le statut réel sur l'écran MineStrator")
async def status_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "statut")

# 🛠️ LA COMMANDE /LOG DOUBLE EXTRACTION
@bot.slash_command(name="log", description="Télécharge directement les fichiers de logs du bot et de MineStrator")
async def get_bot_logs(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Réservé aux administrateurs du bot.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    write_bot_log(f"Extraction des fichiers de logs demandée par {interaction.user.name}")

    files_to_send = []
    if os.path.exists("log_bot.txt"):
        files_to_send.append(nextcord.File("log_bot.txt"))
    if os.path.exists("log_minestrator.txt"):
        files_to_send.append(nextcord.File("log_minestrator.txt"))

    if files_to_send:
        await interaction.followup.send(
            content="📋 **Voici les boîtes noires demandées :**\n- `log_bot.txt` (Activité Discord)\n- `log_minestrator.txt` (Activité Chrome/Selenium)",
            files=files_to_send,
            ephemeral=True
        )
    else:
        await interaction.followup.send("⚠️ Aucun fichier de log trouvé sur le serveur.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
