"""Demarre l'app.py d'un projet sur un port impose, sans ouvrir le navigateur (adaptateur de compatibilite).

Usage (par lanceur.py) : python demarrer_projet.py <chemin de app.py> <port>

Les app.py actuels n'acceptent pas de port impose (PORT = 8000, 8020 ou 8030 ecrit en dur) et les editeurs micro:bit
ouvrent toujours le navigateur. Sans modifier le projet, cet adaptateur execute app.py comme `python app.py` en
remplacant seulement la ligne `PORT = ...` et en neutralisant webbrowser.open. Des que l'app.py d'un projet accepte
l'option --port, lanceur.py l'appelle directement et cet adaptateur ne sert plus pour lui.
"""

import os
import re
import sys
import webbrowser

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage : python demarrer_projet.py <chemin de app.py> <port>")
    chemin = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2])
    with open(chemin, encoding="utf-8") as f:
        source = f.read()
    source, remplacements = re.subn(r"^PORT = \d+", "PORT = %d" % port, source, count=1, flags=re.M)
    if remplacements != 1:
        sys.exit("Ligne « PORT = ... » introuvable dans %s : impossible d'imposer le port." % chemin)

    # Le lanceur redirige lui-meme la page d'accueil vers l'editeur : pas de nouvel onglet.
    webbrowser.open = lambda *args, **kwargs: True
    dossier = os.path.dirname(chemin)
    sys.path[0] = dossier                           # import classe (mode classe) depuis le dossier du projet
    sys.argv = [chemin, "--sans-navigateur"]
    os.chdir(dossier)
    exec(compile(source, chemin, "exec"), {"__name__": "__main__", "__file__": chemin, "__builtins__": __builtins__})
