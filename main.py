import os
import threading
import datetime
import time
from flask import Flask
import nextcord
from nextcord.ext import commands

# Retour à Selenium Furtif
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# 1. Moteur de double journalisation
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
    return "Bot MineStrator Furtif (Rotation Proxies) Actif !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")
# Récupération des identifiants (Assure-toi de les remettre/laisser sur Railway !)
MINE_EMAIL = os.environ.get("MINE_EMAIL")
MINE_PASSWORD = os.environ.get("MINE_PASSWORD")

# 🌐 LISTE DE PROXIES FRAIS ET UNIQUEMENT EUROPÉENS (SÉCURITÉ)
# Si l'un échoue, le script testera automatiquement le suivant.
PROXY_POOL = [
    "http://94.156.114.132:524",   # Allemagne
    "http://45.84.222.25:1080",    # Pays-Bas
    "http://138.124.113.102:7443", # Pays-Bas 2
    "http://2.26.87.216:1080"      # Finlande
]

def get_selenium_driver(proxy_url):
    options = uc.ChromeOptions()
    
    # Injection du proxy sélectionné
    options.add_argument(f'--proxy-server={proxy_url}')
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--lang=fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")
    options.add_argument("window-size=1920,1080")
    
    driver = uc.Chrome(
        options=options, 
        headless=True,
        browser_executable_path="/usr/bin/chromium",
        driver_executable_path="/usr/bin/chromedriver"
    )
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver

@bot.event
async def on_ready():
    bot.add_all_application_commands()
    write_bot_log(f"Bot connecté sous le nom : {bot.user}")

@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, exception):
    write_bot_log(f"Crash commande /{interaction.application_command.name} | Erreur : {str(exception)}")
    try:
        msg = "❌ Le bot a rencontré une erreur. Utilise `/log` pour voir les rapports."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

# 4. Worker Selenium avec boucle de secours sur les Proxies
def selenium_worker(action, server_id, email, password):
    if not email or not password or email == "None":
        write_mine_log("❌ ERREUR : Les variables MINE_EMAIL ou MINE_PASSWORD ne sont pas configurées sur Railway !")
        return "❌ Erreur : Identifiants de connexion manquants sur Railway."

    driver = None
    success = False
    result_message = ""

    # Parcourt la liste des proxies disponibles jusqu'à ce qu'un fonctionne
    for current_proxy in PROXY_POOL:
        write_mine_log(f"Tentative de connexion via le proxy : {current_proxy}")
        try:
            driver = get_selenium_driver(current_proxy)
            
            write_mine_log("Navigation furtive vers la page de login...")
            driver.get("https://panel.minestrator.com/login")
            time.sleep(7) # Laisse le temps d'esquiver Cloudflare
            
            # Vérification : si on est bloqué sur une page d'erreur Chrome ou Nginx, on force l'erreur pour changer de proxy
            if "403" in driver.title or "inaccessible" in driver.title.lower() or "panel.minestrator.com" not in driver.title.lower():
                raise Exception(f"Proxy instable ou bloqué (Titre détecté: '{driver.title}')")

            write_mine_log(f"Formulaire trouvé. Tentative d'identification pour : {email}")
            driver.find_element(By.NAME, "email").send_keys(email)
            driver.find_element(By.NAME, "password").send_keys(password)
            
            submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_btn.click()
            time.sleep(5)
            
            target_url = f"https://panel.minestrator.com/instance/{server_id}"
            write_mine_log(f"Navigation vers l'instance : {target_url}")
            driver.get(target_url)
            time.sleep(5)
            
            page_text = driver.page_source.lower()
            
            if action == "statut":
                if "en ligne" in page_text or "online" in page_text or "started" in page_text:
                    result_message = "🟢 EN LIGNE"
                elif "éteint" in page_text or "offline" in page_text or "stopped" in page_text:
                    result_message = "🔴 ÉTEINT"
                else:
                    result_message = "🟠 EN COURS DE DÉMARRAGE / ARRÊT"
                    
            elif action == "list_servers":
                status_info = "🟢 EN LIGNE" if ("en ligne" in page_text or "online" in page_text) else "🔴 ÉTEINT"
                result_message = f"📋 **Détails de ton serveur MineStrator :**\n• **ID de l'instance :** `{server_id}`\n• **Statut actuel :** {status_info}\n• **Réseau :** Masqué par tunnel Proxy"

            elif action in ["start", "stop"]:
                keyword = "Démarrer" if action == "start" else "Arrêter"
                btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{keyword}')] | //a[contains(text(), '{keyword}')]")
                btn.click()
                time.sleep(2)
                result_message = f"✅ L'action navigateur **{action.upper()}** a été transmise au panel !"

            success = True
            break # On a réussi, on sort de la boucle de proxies !

        except Exception as e:
            write_mine_log(f"⚠️ Échec avec le proxy {current_proxy} : {str(e)}")
            if driver:
                driver.quit()
                driver = None
            continue # Le proxy a échoué, la boucle passe au suivant automatique

    if driver:
        driver.quit()
        write_mine_log("Navigateur Chrome fermé proprement.")

    if success:
        return result_message
    else:
        return "❌ Tous les proxies configurés ont échoué ou ont été rejetés. Réessaye dans quelques instants."

# 5. Connecteurs de Commandes Discord Slash
async def run_command_flow(interaction: nextcord.Interaction, action: str):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Tu n'as pas l'autorisation.", ephemeral=True)
        return

    write_bot_log(f"Commande /{action} initiée par {interaction.user.name}")
    await interaction.response.defer(ephemeral=(action in ["statut", "list_servers"]))
    
    def thread_target():
        res = selenium_worker(action, SERVER_ID, MINE_EMAIL, MINE_PASSWORD)
        bot.loop.create_task(interaction.followup.send(res))
        
    threading.Thread(target=thread_target, daemon=True).start()

@bot.slash_command(name="start", description="Démarre le serveur Minecraft via simulation proxy")
async def start_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "start")

@bot.slash_command(name="stop", description="Arrête le serveur Minecraft via simulation proxy")
async def stop_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "stop")

@bot.slash_command(name="statut", description="Affiche le statut en direct de la machine")
async def status_server(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "statut")

@bot.slash_command(name="list_servers", description="Affiche les configurations de ton instance")
async def list_servers(interaction: nextcord.Interaction):
    await run_command_flow(interaction, "list_servers")

@bot.slash_command(name="log", description="Télécharge instantanément les deux boîtes noires")
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
