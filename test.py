from main import *
from datetime import datetime
from backports.zoneinfo import ZoneInfo
import locale

locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

etat = etat_bot("lecture").split(";")

# Conversion de l'ancienne date sauvegarder et de la date actuelle en seconde
ancienne_date = datetime.strptime(etat[0], "%A %d %B %Y %H:%M:%S")

ancienne_date = int(ancienne_date.strftime("%s"))

date = datetime.strptime(str(datetime.now(tz=ZoneInfo("Europe/Paris"))), "%Y-%m-%d %H:%M:%S")

date = date.strftime("%s")

print(date, ancienne_date)
