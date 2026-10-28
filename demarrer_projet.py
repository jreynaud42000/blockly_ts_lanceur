"""Demarre l'app.py d'un projet sur un port impose, sans ouvrir le navigateur (adaptateur de compatibilite).

Usage (par lanceur.py) : python demarrer_projet.py <chemin de app.py> <port>

Les app.py actuels n'acceptent pas de port impose (PORT = 8000, 8020 ou 8030 ecrit en dur) et les editeurs micro:bit
ouvrent toujours le navigateur. Sans modifier le projet, cet adaptateur execute app.py comme `python app.py` en
remplacant seulement la ligne `PORT = ...` et en neutralisant webbrowser.open. Des que l'app.py d'un projet accepte
l'option --port, lanceur.py l'appelle directement et cet adaptateur ne sert plus pour lui.

Les deux fonctions servent aussi a l'application Windows (LanceurTS.exe) : il n'y a pas de Python separe, l'exe se
relance lui-meme avec --serveur <projet> et appelle executer_app ou servir_statique.
"""

import http.server
import os
import re
import sys
import webbrowser
from functools import partial


def executer_app(chemin, port):
    """Execute app.py comme `python app.py`, sur le port impose et sans ouvrir de navigateur. Ne revient pas."""
    chemin = os.path.abspath(chemin)
    with open(chemin, encoding="utf-8") as f:
        source = f.read()
    source, remplacements = re.subn(r"^PORT = \d+", "PORT = %d" % port, source, count=1, flags=re.M)
    if remplacements != 1:
        sys.exit("Ligne « PORT = ... » introuvable dans %s : impossible d'imposer le port." % chemin)

    # Le lanceur redirige lui-meme la page d'accueil vers l'editeur : pas de nouvel onglet.
    webbrowser.open = lambda *args, **kwargs: True
    # Dans l'exe, sys.frozen ferait croire a app.py qu'il est son propre exe PyInstaller (dossier sys._MEIPASS,
    # arret automatique, boites de dialogue) : app.py doit se comporter comme lance par `python app.py`.
    if hasattr(sys, "frozen"):
        del sys.frozen
    dossier = os.path.dirname(chemin)
    sys.path.insert(0, dossier)                     # import classe (mode classe) depuis le dossier du projet
    sys.argv = [chemin, "--sans-navigateur"]
    os.chdir(dossier)
    exec(compile(source, chemin, "exec"), {"__name__": "__main__", "__file__": chemin, "__builtins__": __builtins__})


def servir_statique(dossier, port):
    """Sert un dossier de pages web (index.html seul) sur 127.0.0.1, comme `python -m http.server`. Ne revient pas."""
    gestionnaire = partial(http.server.SimpleHTTPRequestHandler, directory=dossier)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), gestionnaire) as serveur:
        print("Dossier servi :", dossier)
        print("Application disponible sur http://localhost:%d" % port)
        serveur.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage : python demarrer_projet.py <chemin de app.py> <port>")
    executer_app(sys.argv[1], int(sys.argv[2]))
