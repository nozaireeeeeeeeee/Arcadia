import os
import threading
import pickle
from flask import Flask
import nextcord
from nextcord.ext import commands
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
import pyotp

# ----------------- PARTIE SERVEUR WEB (ANTI-VEILLE) -----------------
app = Flask('')

@app.route('/')
def home():
    return "Le bot est en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------- PARTIE BOT DISCORD -----------------
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

bot = commands.Bot()
guild_ids_list = [int(GUILD_ID)] if GUILD_ID else None

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.sync_all_application_commands()

# Fonction pour se connecter à MineStrator avec gestion 2FA et cookies
def connect_to_minestrator():
    # Configuration de Selenium pour Render
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Démarrage du navigateur
    driver = webdriver.Chrome(options=chrome_options)
    
    # Essayer de charger les cookies s'ils existent
    cookies_file = "/tmp/minestrator_cookies.pkl"  # Utiliser /tmp pour Render
    try:
        driver.get("https://minestrator.com")
        with open(cookies_file, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()
        
        # Vérifier si la connexion fonctionne
        WebDriverWait(driver, 5).until(EC.url_contains("dashboard"))
        print("Connexion via cookies réussie")
        
    except (FileNotFoundError, Exception):
        # Les cookies n'existent pas ou sont invalides, se connecter normalement
        print("Connexion via formulaire avec 2FA")
        driver.get("https://minestrator.com/login")
        
        # Remplir le formulaire de connexion
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "email")))
        driver.find_element(By.ID, "email").send_keys(os.environ.get("MINESTRATOR_EMAIL"))
        driver.find_element(By.ID, "password").send_keys(os.environ.get("MINESTRATOR_PASSWORD"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # Vérifier si une page 2FA apparaît
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "2fa-code")))
            
            # Générer un code 2FA
            totp = pyotp.TOTP(os.environ.get("MINESTRATOR_2FA_SECRET"))
            code_2fa = totp.now()
            
            # Entrer le code 2FA
            driver.find_element(By.ID, "2fa-code").send_keys(code_2fa)
            driver.find_element(By.CSS_SELECTOR, "button.verify-2fa").click()
            
        except:
            pass
        
        # Attendre la connexion
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))
        
        # Sauvegarder les cookies pour la prochaine fois
        with open(cookies_file, "wb") as file:
            pickle.dump(driver.get_cookies(), file)
    
    return driver

@bot.slash_command(
    name="start",
    description="Démarre le serveur Minecraft.",
    guild_ids=guild_ids_list
)
async def start_server(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Démarrage du serveur en cours...")
    
    try:
        driver = connect_to_minestrator()
        
        # Naviguer vers la page des serveurs
        server_url = f"https://minestrator.com/server/{os.environ.get('SERVER_ID')}"
        driver.get(server_url)
        
        # Cliquer sur le bouton de démarrage
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.start-server")))
        driver.find_element(By.CSS_SELECTOR, "button.start-server").click()
        
        # Attendre la confirmation
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".server-status.running")))
        
        await interaction.followup.send("✅ Serveur Minecraft démarré avec succès !")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors du démarrage : {str(e)}")
        print(f"Erreur : {str(e)}")
    finally:
        driver.quit()

@bot.slash_command(
    name="stop",
    description="Arrête le serveur Minecraft.",
    guild_ids=guild_ids_list
)
async def stop_server(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Arrêt du serveur en cours...")
    
    try:
        driver = connect_to_minestrator()
        
        # Naviguer vers la page des serveurs
        server_url = f"https://minestrator.com/server/{os.environ.get('SERVER_ID')}"
        driver.get(server_url)
        
        # Cliquer sur le bouton d'arrêt
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.stop-server")))
        driver.find_element(By.CSS_SELECTOR, "button.stop-server").click()
        
        # Attendre la confirmation (selon l'interface de MineStrator)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".server-status.stopped")))
        
        await interaction.followup.send("✅ Serveur Minecraft arrêté avec succès !")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de l'arrêt : {str(e)}")
        print(f"Erreur : {str(e)}")
    finally:
        driver.quit()

# Lancement du serveur Web anti-veille
threading.Thread(target=run_web_server).start()

# Lancement du bot Discord
bot.run(TOKEN)
