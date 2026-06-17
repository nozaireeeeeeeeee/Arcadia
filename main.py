import os
import threading
import datetime
import requests
from flask import Flask
import nextcord
from nextcord.ext import commands

# 1. Configuration
intents = nextcord.Intents.default()
bot = commands.Bot(intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = os.environ.get("SERVER_ID")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")
MINESTRATOR_TOKEN = os.environ.get("MINESTRATOR_TOKEN")

# 2. Serveur Web (Keep-Alive pour Railway)
app = Flask('')
@app.route('/')
def home():
    return "Bot actif"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Fonction API principale
def api_worker(action, server_id, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    # On teste les deux routes courantes
    base_urls = [f"https://api.minestrator.com/v1/server/{server_id}", f"https://api.minestrator.com/v1/serveur/{server_id}"]
    
    for url in base_urls:
        if action == "statut":
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200: return f"Statut : {res.json().get('status', 'inconnu')}"
        elif action in ["start", "stop"]:
            res = requests.post(f"{url}/action", headers=headers, json={"action": action}, timeout=5)
            if res.status_code in [200, 201, 204]: return f"Action {action} réussie."
    
    return "Erreur 404 : Serveur introuvable. Utilise /debug pour vérifier ton ID."

# 4. Commandes
@bot.slash_command(name="statut")
async def statut(interaction: nextcord.Interaction):
    await interaction.response.defer()
    res = api_worker("statut", SERVER_ID, MINESTRATOR_TOKEN)
    await interaction.followup.send(res)

@bot.slash_command(name="debug", description="Affiche tes serveurs pour trouver l'ID")
async def debug_server(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    headers = {"Authorization": f"Bearer {MINESTRATOR_TOKEN}", "Accept": "application/json"}
    try:
        response = requests.get("https://api.minestrator.com/v1/servers", headers=headers, timeout=10)
        await interaction.followup.send(f"Réponse API :\n
http://googleusercontent.com/immersive_entry_chip/0

---

### 🚀 Ce que tu dois faire maintenant :

1. **Copie/Colle ce code** dans ton fichier `main.py` sur GitHub et enregistre.
2. Attends que **Railway** redémarre le bot.
3. Va sur ton serveur Discord, tape **/debug** et **envoie-moi le résultat** (le texte qui s'affiche dans le bloc gris).

Dès que j'ai ce résultat, je te donne l'ID exact à mettre dans ta variable `SERVER_ID` et tout sera réglé.
