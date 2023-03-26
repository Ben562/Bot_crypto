from main import Kucoin, Message_discord, os, Process, kill_process, datetime, ZoneInfo, sleep, Thread
from subprocess import Popen
from discord.ext import commands
import asyncio
import runpy
import sys


class Bot_Discord(commands.Bot):

    def __init__(self):
        """
        Initialise le bot discord
        """
        super().__init__(command_prefix="!")

        # Objet Kucoin pour interagir avec le serveur
        self.kucoin = Kucoin("Discord", False)

        # Message discord
        self.msg_discord = Message_discord()

        # Stocke tous les bots lancés
        self.list_bot_started = []
        self.list_symbol_bot_started = []

        # Boucle qui permet de lancer la suppression automatique des messages
        self.loop = asyncio.get_event_loop_policy().get_event_loop()

        # Liste des cryptos supportées
        with open("Other_files/supported_crypto.txt", "r") as f:
            self.crypto_supporter = f.read().split(";")

        def lancement_bot(symbol):
            """
            Permet de lancer le bot
            Renvoi l'erreur sur le serveur s'il y en a une qui apparait
            """
            try:
                self.msg_discord.message_canal(
                    "général", f"Bot {symbol} est lancé !")
                sys.argv = ['', symbol]
                runpy.run_path("bot.py")
            except Exception as error:
                self.msg_discord.message_erreur(
                    error, f"Erreur survenue au niveau du bot {symbol}, arrêt du programme")

                self.msg_discord.message_canal("général",
                                               "Le bot s'est arrêté !")

        def stop_manual_bot(symbol):
            """
            Arrête le bot
            """
            for p in self.list_bot_started:
                if p.name == symbol:
                    # On supprime le processus des listes
                    self.list_bot_started.remove(p)
                    self.list_symbol_bot_started.remove(symbol)

                    # On récupère l'id du processus du bot et on l'arrête
                    os.kill(p.ident, 9)

                    break

        def message_state_bot_discord():
            """
            Envoi sur le canal discord le ou les statuts des bots
            """
            symbole = "".join(
                f"{symbole}, " for symbole in self.list_symbol_bot_started)

            date = datetime.now(tz=ZoneInfo("Europe/Paris")
                                ).strftime("%A %d %B %Y %H:%M:%S")

            msg = f"Bot {symbole[:-2]} toujours en cour d'exécution le : {date}"

            self.msg_discord.message_canal("état_bot", msg)

        def message_bot_started():
            """
            Envoi sur le canal d'état les bots démarrés
            """
            temps_max = 0
            vide = self.list_symbol_bot_started == []

            while True:
                if self.list_symbol_bot_started:
                    # Si on vient de lancer un bot, on envoie un message
                    if vide:
                        sleep(90)

                        message_state_bot_discord()

                        vide = False

                    # On fait la moyenne de temps des bots lancé
                    # Message de statut des bots au niveau de leur fonctionnement à eux
                    for symbole in self.list_symbol_bot_started:
                        with open(f"state_bot_{symbole}.txt", "r") as file:
                            date_crypto = file.read().split(";")[0]

                            date_crypto = datetime.strptime(
                                date_crypto, "%A %d %B %Y %H:%M:%S")

                            date_crypto = int(date_crypto.strftime("%s"))

                            if date_crypto >= temps_max:
                                temps_max = date_crypto

                    # Ajout prochaine heure envoi message
                    temps_max += 3600

                    # Horodatage actuelle
                    date = datetime.now(tz=ZoneInfo("Europe/Paris")
                                        ).strftime("%A %d %B %Y %H:%M:%S")

                    date = datetime.strptime(date, "%A %d %B %Y %H:%M:%S")

                    date = int(date.strftime("%s"))

                    # Moyenne des temps - la date actuelle + 10 secondes safe
                    waiting_time = temps_max - date + 10

                    sleep(waiting_time)

                    # Nouvelle vérification si arrêt des bots entre temps
                    if self.list_symbol_bot_started:
                        message_state_bot_discord()

                        # Puis, on attend que tous les bots passent leur passage de prédiction
                        # Pour de nouveau voir le temps d'attente avant le prochain message
                        sleep(10)

                else:
                    vide = True
                    sleep(30)

        async def lancement_processus(symbol):
            """
            Lance le processus du bot
            """
            p = Process(target=lancement_bot,
                        name=symbol, args=[symbol])

            # Puis, on ajoute le processus du bot dans les listes pour garder une trace de tous les bots lancés
            self.list_bot_started.append(p)
            self.list_symbol_bot_started.append(symbol)

            # Trie la liste de symbol dans l'ordre croissant
            self.list_symbol_bot_started.sort()

            p.start()

        async def stop_auto_bot():
            """
            Supprime automatiquement de la liste les processus arrêtés
            """
            while True:
                for process in self.list_bot_started:
                    if process.exitcode is not None:
                        symbol = process.name

                        kill_process(process)

                        self.list_bot_started.remove(process)
                        self.list_symbol_bot_started.remove(symbol)

                await asyncio.sleep(2)

        async def suppression_auto_message():
            """
            Supprime automatiquement les messages sur les canaux état-bot et prise-position
            s'il y a plus de 10 messages
            évite que les canaux soient trop chargés par les messages du bot
            évite la suppression manuelle et totale des messages
            """
            id_state_bot = 972545416786751488

            # id_prise_position = 973269585547653120

            # On attend que le client soit prêt
            # sinon get_channel renvoi none
            await self.wait_until_ready()

            state_bot = self.get_channel(id_state_bot)

            # prise_position = self.get_channel(id_prise_position)

            async def suppression_messages(channel):
                """
                Supprime les messages d'un canal
                """
                while True:
                    # Récupération des messages
                    messages = await channel.history().flatten()

                    # S'il y en a plus de 10
                    # Alors on inverse la liste pour avoir les anciens messages en premier
                    if len(messages) > 10:
                        messages.reverse()

                        # On ne garde que les plus anciens
                        messages = messages[:len(messages) - 10]

                        # Puis, on les supprime
                        for msg in messages[:10]:
                            await msg.delete()
                            await asyncio.sleep(0.2)

                    # Et enfin on attend une heure soit le temps d'attente du bot
                    await asyncio.sleep(60 * 60)

            # Démarrage suppression dans les deux canaux
            self.loop.create_task(suppression_messages(state_bot))
            # self.loop.create_task(suppression_messages(prise_position))

        # Démarrage tache async et thread
        self.loop.create_task(suppression_auto_message())
        self.loop.create_task(stop_auto_bot())

        th = Thread(target=message_bot_started)
        th.start()

        @self.command(name="del")
        async def delete(ctx):
            """
            Supprime tous les messages de la conversation
            """
            messages = await ctx.channel.history().flatten()

            for each_message in messages:
                await each_message.delete()
                await asyncio.sleep(0.2)

        @self.command(name="aide")
        async def aide(ctx):
            """
            Fonction complémentaire de la fonction de base "help" de discord
            """
            commandes = """
            Voici les commandes disponibles :

            aide / help : affiche l'aide soit de la commande aide du bot/soit de discord

            del : supprime tous les messages de la conversation

            start : lance le bot sur la crypto voulus

            stop : arrête le bot

            prix : donne le prix actuel de la cryptomonnaie voulus

            statut : affiche le statut du bot discord et du bot crypto

            vente : vend toutes les cryptomonnaie du compte

            montant : renvoie le montant des cryptos du compte

            restart : redémarre le bot en mettant à jour les fichiers de celui-ci

            estimation : donne le prix estimer de l'ordre limite sur le marché de base

            """

            await ctx.send(commandes)

        @self.command(name="prix")
        async def prix(ctx):
            """
            Affiche le prix en temps réel de la crypto
            """
            for crypto in self.crypto_supporter:
                await ctx.send(f"Le prix de {crypto} est de : {self.kucoin.prix_temps_reel_kucoin(f'{crypto}-USDT')}")

        @self.command(name="start")
        async def start(ctx):
            """
            Lance en processus le bot de crypto
            Permet de ne pas bloquer le bot discord et donc d'exécuter d'autres commandes à côté
            Comme l'arrêt du bot ou le relancer, le prix à l'instant T, etc...
            """
            question = "Sur quelles crypto trader ? " + "".join(f"{symbol} ? " for symbol in self.crypto_supporter)

            await ctx.send(question)

            # Vérifie que le message n'est pas celui envoyé par le bot
            def check(m):
                return m.content != question and m.channel == ctx.channel

            # On attend la réponse
            msg = await bot.wait_for("message", check=check)

            # On récupère la crypto
            crypto = msg.content

            if crypto == "all":
                for symbol in self.crypto_supporter:
                    if symbol not in self.list_symbol_bot_started:
                        # Lancement du processus puis attente de deux secondes
                        await lancement_processus(symbol)

                        # Dès que le bot est démarré, on attend (gestion multibot) et on passe au suivant
                        while True:
                            if f"{symbol}_started" in self.kucoin.dico_partage:
                                del self.kucoin.dico_partage[f"{symbol}_started"]

                                await asyncio.sleep(10)

                                break

            else:
                # Si elle est supporter et pas lancé, alors on lance le bot
                if crypto in self.crypto_supporter:
                    if crypto not in self.list_symbol_bot_started:
                        await lancement_processus(crypto)

                        # Dès que le bot est démarré, on peut supprimer la variable
                        while True:
                            if f"{crypto}_started" in self.kucoin.dico_partage:
                                del self.kucoin.dico_partage[f"{crypto}_started"]

                                break

                    else:
                        await ctx.send("Le bot est déjà lancé !")

                else:
                    await ctx.send("Le bot n'existe pas !")

        @self.command(name="stop")
        async def stop(ctx):
            """
            Stop le bot (tue son processus)
            """
            if not self.list_symbol_bot_started:
                await ctx.send("Aucun bot lancé !")
                return

            question = "Quel bot arrêté ?"
            bot_started = "Bot lancé : " + "".join(f"{symbol} " for symbol in self.list_symbol_bot_started)

            await ctx.send(question)
            await ctx.send(bot_started)

            # Vérifie que le message n'est pas celui envoyé par le bot
            def check(m):
                return m.content != question and m.content != bot_started and m.channel == ctx.channel

            # On attend la réponse
            msg = await bot.wait_for("message", check=check)

            # On récupère la crypto
            crypto = msg.content

            if crypto == "all":
                copy_symbol = self.list_symbol_bot_started[:]

                for symbol in copy_symbol:
                    stop_manual_bot(symbol)

                await ctx.send("Tous les bots ont été arrêtés !")

            else:
                # Puis, on l'arrête si le bot est lancé
                if crypto in self.crypto_supporter:
                    if crypto in self.list_symbol_bot_started:
                        stop_manual_bot(crypto)

                        await ctx.send("Bot arrêté !")
                    else:
                        await ctx.send("Bot déjà à l'arrêt !")

                else:
                    await ctx.send("Bot inexistant !")

        @self.command(name="statut")
        async def statut(ctx):
            """
            Renvoie le statut du bot discord et celui de trading
            """
            await ctx.send("Bot discord toujours en cours d'exécution !")

            # Regarde s'il y a des bots lancés ou non
            if self.list_symbol_bot_started:
                crypto = ""

                for symbol in self.list_symbol_bot_started:
                    crypto += f"{symbol} "

                await ctx.send(f"Bot lancé : {crypto}")
            else:
                await ctx.send("Aucun Bot lancé !")

        @self.command(name="vente")
        async def vente(ctx):
            """
            Permet de vendre les cryptomonnaies du bot à distance
            Sans devoir accéder à la platform
            """
            question = "Quelle crypto ? " + "".join(f"{crypto} ? " for crypto in self.crypto_supporter)

            await ctx.send(question)

            # Vérifie que le message n'est pas celui envoyé par le bot
            def check(m):
                return m.content != question and m.channel == ctx.channel

            # On attend la réponse
            msg = await bot.wait_for("message", check=check)

            # On récupère la crypto
            crypto_symbol = msg.content

            # On vérifie que la crypto existe bien
            if crypto_symbol in self.crypto_supporter:

                # On regarde le montant des deux cryptos
                crypto_up = self.kucoin.montant_compte(f"{crypto_symbol}3L")
                crypto_down = self.kucoin.montant_compte(f"{crypto_symbol}3S")

                kucoin = Kucoin(crypto_symbol, False)

                # Et on vend la ou les cryptos en supprimant les ordres placés
                if crypto_up > self.kucoin.minimum_crypto_up:
                    kucoin.achat_vente(
                        crypto_up, f"{crypto_symbol}3L-USDT", False)

                    await ctx.send(f"{crypto_up} crypto up vendu !")

                if crypto_down > self.kucoin.minimum_crypto_down:
                    kucoin.achat_vente(
                        crypto_down, f"{crypto_symbol}3S-USDT", False)

                    await ctx.send(f"{crypto_down} crypto down vendu !")
            else:
                await ctx.send("Crypto non supportée !")

            # Et on renvoie les nouveaux montants sur le discord
            await montant(ctx)

        @self.command(name="montant")
        async def montant(ctx):
            """
            Renvoie le montant du compte des cryptos
            """

            argent = self.kucoin.montant_compte(self.kucoin.devise, None, True)
            await ctx.send(f"Le compte possède {argent} USDT")

            for crypto in self.crypto_supporter:
                crypto_up = self.kucoin.montant_compte(f"{crypto}3L")
                crypto_down = self.kucoin.montant_compte(f"{crypto}3S")

                await ctx.send(f"Le compte possède {crypto_up} {crypto}_UP, {crypto_down} {crypto}_DOWN")

        @self.command(name="restart")
        async def restart(ctx):
            """
            Redémarre le bot discord et met à jour ses fichiers
            """
            # Récupère toutes les positions en cours
            cryptos_position = self.kucoin.presence_position_all()

            # S'il y a bien des symboles, alors on bloque le redémarrage
            if cryptos_position is not None:
                await ctx.send("Impossible de redémarrer, des positions sont en cours")

                crypto = "".join(f"{elt}, " for elt in cryptos_position)

                await ctx.send(f"Cryptos ayant une position : {crypto[:-2]}")

            else:
                Popen("nohup python3.10 restart.py >/dev/null 2>&1", shell=True)

        @self.command(name="estimation")
        async def estimation(ctx):
            """
            Renvoi le prix estimer de vente de la crypto
            """
            prix_estimer = None

            # On parcourt le dictionnaire à la recherche de prix estimer
            for cle, valeur in self.kucoin.dico_partage.items():
                if "prix_estimer_" in cle:
                    crypto = cle.split("_")[-1]
                    await ctx.send(f"Le prix de vente estimer de {crypto} est de {valeur}")
                    await ctx.send(f"Le prix de marché est de {self.kucoin.prix_temps_reel_kucoin(f'{crypto}-USDT')}")

                    # S'il y a bien un prix estimé, alors le message d'en dessous ne sert à rien
                    prix_estimer = True

            if prix_estimer is None:
                await ctx.send("Il n'y a pas de position prise à l'heure actuel ou de prix enregistrer")

    async def on_ready(self):
        """
        Affiche dans le canal général "Bot Discord démarré !" lorsqu'il est opérationnel
        """
        self.msg_discord.message_canal("général", "Bot Discord démarré !")


if __name__ == "__main__":
    os.system("clear")
    try:
        bot = Bot_Discord()
        bot.run("OTcyNDY0NDAwNzY4MzM1ODkz.YnZcDA.LYfcnXeeBB2aEO0-ZX7bNvM1T-8")
    except Exception as e:
        message_discord = Message_discord()

        message_discord.message_erreur(
            e, "Erreur survenue dans le bot discord, arrêt de tous les programmes")
