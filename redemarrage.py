from bot_discord import commande_bot_terminale
from subprocess import Popen, PIPE
from time import sleep
import os

# D'abord on arrête tous les processus du bot
proc = Popen(commande_bot_terminale, shell=True, stdout=PIPE, stderr=PIPE)

sortie, autre = proc.communicate()

processus = sortie.decode('utf-8').split("\n")[:-1]

for elt in processus:
    os.system(f"kill -9 {elt}")

# Puis on dort quelques secondes pour être sur
sleep(3)

# On met à jour les fichiers
os.system("git pull")

sleep(3)

# Et enfin on redémarre le bot
Popen("python3 bot_discord.py >/dev/null", shell=True)
