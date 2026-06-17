import os
import threading
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

# 1. Serveur Web pour Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot MineStrator Selenium en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Configuration du Bot Discord
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")
MINE_EMAIL = os.environ.get("MINE_EMAIL")
MINE_PASSWORD = os.environ.get("MINE_PASSWORD")

# Configuration du navigateur invisible (Headless) pour Railway
def get_selenium_driver():
    options = Options()
    options.add_argument("--headless") # Obligatoire sur Railway (pas d'écran)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

@bot.event
async def on_ready():
    print(f"✅ Bot connecté avec Selenium : {bot.user}")
    try:
        await bot.sync_all_application_commands()
        print("✅ Commandes synchronisées !")
    except Exception as e:
        print(f"⚠️ Erreur sync : {e}")

# 3. Fonction de pilotage par navigateur
def run_selenium_action(action):
    driver = get_selenium_driver()
    try:
        # 1. Connexion au panel
        driver.get("https://panel.minestrator.com/login")
        time.sleep(3) # Attente du chargement
        
        # Remplissage du formulaire de connexion
        # Note : Les sélecteurs (ID/Name) dépendent de la page de MineStrator
        driver.find_element(By.NAME, "email").send_keys(MINE_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(MINE_PASSWORD)
        
        # Clic sur le bouton de connexion
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        time.sleep(4)
        
        # 2. Navigation vers la page du serveur
        driver.get(f"https://panel.minestrator.com/instance/{SERVER_ID}")
        time.sleep(4)
        
        if action == "statut":
            # Exemple théorique : récupérer le texte contenant le statut
            status_element = driver.find_element(By.CLASS_NAME, "badge") # À adapter selon le site
            return f"Le statut textuel détecté est : {status_element.text}"
            
        elif action in ["start", "stop"]:
            # Exemple théorique : cliquer sur le bouton start ou stop
            btn = driver.find_element(By.XPATH, f"//button[contains(@class, '{action}')]")
            btn.click()
            time.sleep(2)
            return f"Action {action.upper()} envoyée via le clic navigateur !"
            
    except Exception as e:
        return f"Erreur Selenium : {str(e)}"
    finally:
        driver.quit() # Toujours fermer le navigateur pour éviter de saturer la RAM

# 4. Commandes Slash
@bot.slash_command(name="start", description="Démarre le serveur via Navigateur")
async def start_server(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Hors de question.", ephemeral=True)
        return
        
    await interaction.response.defer()
    # On execute Selenium dans un thread séparé pour ne pas faire crash Discord (qui n'attend pas)
    result = run_selenium_action("start")
    await interaction.followup.send(result)

@bot.slash_command(name="stop", description="Arrête le serveur via Navigateur")
async def stop_server(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Hors de question.", ephemeral=True)
        return
        
    await interaction.response.defer()
    result = run_selenium_action("stop")
    await interaction.followup.send(result)

@bot.slash_command(name="statut", description="Vérifie le statut via Navigateur")
async def status_server(interaction: nextcord.Interaction):
    if str(interaction.user.id) not in ALLOWED_USERS:
        await interaction.response.send_message("❌ Hors de question.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    result = run_selenium_action("statut")
    await interaction.followup.send(result, ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(TOKEN)
