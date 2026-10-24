"""Lanceur des editeurs Blockly (Technologie Services).

Sert la page d'accueil sur http://localhost:8090 et ouvre le navigateur. Un clic sur une tuile demande au lanceur de
demarrer le serveur du projet choisi, chacun sur son propre port (8091 a 8097), puis la page redirige vers l'editeur.
Un port par projet : les donnees enregistrees dans le navigateur (localStorage) restent separees entre editeurs.

Les 5 projets restent dans leur dossier, a cote de celui du lanceur (voir PROJETS). Un serveur deja demarre n'est
pas relance. A la fermeture du lanceur (Ctrl+C ou fenetre fermee), les serveurs qu'il a demarres sont arretes :
sous Windows ils sont rattaches a un « job » que le systeme ferme avec le lanceur, meme en cas d'arret brutal.

Port 8090 et non 8080 : la plateforme utilise 8080 par defaut quand on la lance seule.
Editeurs sur 8091 a 8097, en dehors des plages ou les app.py lances seuls se replient quand leur port est pris
(micro:bit 8000 a 8009, mBot2 8020 a 8029, mBot1 8030 a 8039) : sinon un editeur lance a cote (lancer_projet.bat,
apercu) peut occuper le port d'une tuile.

Affichage a 80 % : la page d'accueil s'ouvre dans une fenetre dediee d'Edge (ou de Chrome), sans barre d'adresse, avec
--force-device-scale-factor=0.8. Le zoom CSS dans le code casse le glisser-deposer des blocs Blockly ; ce facteur
d'echelle, applique par le navigateur, ne gene aucune application. Il ne vaut que pour une instance de navigateur
demarree avec lui : la fenetre utilise donc son propre profil (%LOCALAPPDATA%\\LanceurBlockly\\profil), separe du
navigateur habituel (extensions, mots de passe et donnees locales a part).

Options :
  --sans-navigateur      n'ouvre pas le navigateur (apercu integre, tests).
  --navigateur-habituel  ouvre la page d'accueil dans le navigateur par defaut, a 100 %, au lieu de la fenetre dediee.
"""

import html
import http.server
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from functools import partial

PORT = 8090
NOM_APPLICATION = "LanceurBlockly"
DOSSIER = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(DOSSIER, "page")
JOURNAUX = os.path.join(DOSSIER, "journaux")
DOSSIER_PROJETS = os.path.dirname(DOSSIER)          # les projets sont a cote du dossier du lanceur
DEMARRER = os.path.join(DOSSIER, "demarrer_projet.py")
DELAI_DEMARRAGE = 30                                 # s : premier demarrage lent (OneDrive, antivirus)

# id -> dossier du projet, port impose, type de serveur.
#   "app"        : app.py du projet (sert le dossier, sur le port 8000 ou 8020 / 8030 par defaut)
#   "plateforme" : plateforme/serveur.py (comptes, seances ; port choisi par la variable PLATEFORME_PORT)
#   "statique"   : page web sans serveur propre (frise, simulateur RDM : index.html seul), servie par python -m http.server
PROJETS = {
    "mode-classe":     {"dossier": "blockly_ts_mode_classe",     "port": 8091, "serveur": "app"},
    "adacraft-vilain": {"dossier": "blockly_ts_adacraft_vilain", "port": 8092, "serveur": "app"},
    "plateforme":      {"dossier": "blockly_ts_plateforme",      "port": 8093, "serveur": "plateforme"},
    "mbot1":           {"dossier": "blocky_ts_mbot1",            "port": 8094, "serveur": "app"},
    "mbot2":           {"dossier": "blocky_ts_mbot2",            "port": 8095, "serveur": "app"},
    "frise":           {"dossier": "frise",                      "port": 8096, "serveur": "statique"},
    "simulation-rdm":  {"dossier": "simulation_rdm",             "port": 8097, "serveur": "statique"},
}

_processus = {}                                     # id -> subprocess.Popen demarre par ce lanceur
_verrous = {cle: threading.Lock() for cle in PROJETS}


class EchecDemarrage(Exception):
    """Message destine a l'utilisateur (affiche sur la tuile)."""


# --- Rattachement des serveurs au lanceur (Windows) -------------------------------------------------------------

def creer_job():
    """Job Windows qui tue ses processus quand le lanceur se termine (fenetre fermee, plantage) ; None ailleurs."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(nom, ctypes.c_ulonglong) for nom in ("ReadOperationCount", "WriteOperationCount",
                        "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", IO_COUNTERS),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        noyau = ctypes.WinDLL("kernel32", use_last_error=True)
        noyau.CreateJobObjectW.restype = wintypes.HANDLE
        noyau.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        noyau.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        noyau.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

        job = noyau.CreateJobObjectW(None, None)
        if not job:
            return None
        infos = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        infos.BasicLimitInformation.LimitFlags = 0x2000           # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not noyau.SetInformationJobObject(job, 9, ctypes.byref(infos), ctypes.sizeof(infos)):  # 9 : infos etendues
            return None
        return lambda processus: noyau.AssignProcessToJobObject(job, int(processus._handle))
    except Exception as erreur:                     # sans job, l'arret propre a la fermeture reste assure (finally)
        print("Job Windows indisponible :", erreur)
        return None


rattacher = creer_job()


# --- Demarrage et arret des serveurs des projets ----------------------------------------------------------------

def port_occupe(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def repond(port):
    """Vrai si un serveur HTTP repond sur ce port (n'importe quel code de reponse)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2):
            return True
    except urllib.error.HTTPError:
        return True                                 # 401, 404... : le serveur est bien la
    except Exception:
        return False


def commande(projet):
    """Commande et variables d'environnement qui demarrent le serveur du projet sur son port, sans navigateur."""
    dossier = os.path.join(DOSSIER_PROJETS, projet["dossier"])
    port = projet["port"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    if projet["serveur"] == "statique":
        if not os.path.isfile(os.path.join(dossier, "index.html")):
            raise EchecDemarrage("index.html est introuvable dans %s." % projet["dossier"])
        return [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", dossier], env
    if projet["serveur"] == "plateforme":
        serveur = os.path.join(dossier, "plateforme", "serveur.py")
        if not os.path.isfile(serveur):
            raise EchecDemarrage("plateforme/serveur.py est introuvable dans %s." % projet["dossier"])
        env.update(PLATEFORME_PORT=str(port), PLATEFORME_HOTE="127.0.0.1")
        return [sys.executable, serveur], env
    app = os.path.join(dossier, "app.py")
    if not os.path.isfile(app):
        raise EchecDemarrage("app.py est introuvable dans %s." % projet["dossier"])
    with open(app, encoding="utf-8") as f:
        accepte_port = "--port" in f.read()
    if accepte_port:
        return [sys.executable, app, "--port", str(port), "--sans-navigateur"], env
    # app.py sans option --port : demarrer_projet.py impose le port et neutralise l'ouverture du navigateur.
    return [sys.executable, DEMARRER, app, str(port)], env


def fin_du_journal(chemin, lignes=6):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return "\n".join(l.rstrip() for l in f.readlines()[-lignes:] if l.strip())
    except OSError:
        return ""


def demarrer(cle):
    """Demarre le serveur du projet s'il ne tourne pas deja ; renvoie l'adresse de l'editeur."""
    projet = PROJETS[cle]
    port = projet["port"]
    url = "http://localhost:%d/?lanceur=%d" % (port, PORT)
    with _verrous[cle]:
        processus = _processus.get(cle)
        if processus is not None and processus.poll() is None:
            if attendre(processus, port, None):
                return url
            raise EchecDemarrage("Le serveur est démarré mais ne répond pas. Fermez le lanceur puis relancez-le.")
        if not os.path.isdir(os.path.join(DOSSIER_PROJETS, projet["dossier"])):
            raise EchecDemarrage("Le dossier %s est introuvable à côté du lanceur." % projet["dossier"])
        if port_occupe(port):
            raise EchecDemarrage("Le port %d est déjà utilisé par un autre programme. "
                                 "Fermez-le (ou la fenêtre de serveur restée ouverte) puis réessayez." % port)
        args, env = commande(projet)
        os.makedirs(JOURNAUX, exist_ok=True)
        journal = os.path.join(JOURNAUX, cle + ".log")
        with open(journal, "w", encoding="utf-8") as sortie:
            processus = subprocess.Popen(args, cwd=os.path.join(DOSSIER_PROJETS, projet["dossier"]), env=env, stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if rattacher:
            rattacher(processus)
        _processus[cle] = processus
        print("Démarrage de %s sur le port %d (processus %d)" % (cle, port, processus.pid))
        if not attendre(processus, port, journal):
            arreter(cle)
            raise EchecDemarrage("Le serveur n'a pas répondu au bout de %d s." % DELAI_DEMARRAGE)
        return url


def attendre(processus, port, journal):
    """Attend que le serveur reponde ; leve EchecDemarrage s'il s'arrete en route."""
    limite = time.time() + DELAI_DEMARRAGE
    while time.time() < limite:
        if processus.poll() is not None:
            detail = fin_du_journal(journal) if journal else ""
            raise EchecDemarrage("Le serveur s'est arrêté au démarrage." + ("\n" + detail if detail else ""))
        if repond(port):
            return True
        time.sleep(0.25)
    return False


def arreter(cle):
    processus = _processus.pop(cle, None)
    if processus is None or processus.poll() is not None:
        return
    processus.terminate()
    try:
        processus.wait(timeout=3)
    except subprocess.TimeoutExpired:
        processus.kill()


def arreter_tout():
    for cle in list(_processus):
        arreter(cle)


def etat(cle):
    processus = _processus.get(cle)
    return "en-marche" if processus is not None and processus.poll() is None else "arrete"


# --- Serveur de la page d'accueil -------------------------------------------------------------------------------

class Serveur(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # Pas sous Windows : cette option y laisse deux serveurs ecouter le meme port.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    """Sert le dossier page/ (sans cache) et l'API du lanceur.

      GET  /api/projets          etat et port de chaque projet
      POST /api/demarrer/<id>    demarre le projet (si besoin) et renvoie {"ok", "url"} ou {"ok": false, "message"}
    Le POST exige l'en-tete X-Lanceur : une autre page web ne peut pas l'envoyer sans autorisation CORS.
    """

    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map,
                          **{".js": "text/javascript", ".svg": "image/svg+xml"})

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def repondre(self, donnees, statut=200):
        corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
        self.send_response(statut)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        chemin = self.path.split("?")[0]
        if chemin == "/api/projets":
            self.repondre({"app": NOM_APPLICATION, "projets": {cle: {"port": p["port"], "etat": etat(cle)}
                                                                for cle, p in PROJETS.items()}})
        elif chemin.startswith("/ouvrir/") and chemin[len("/ouvrir/"):] in PROJETS:
            self.ouvrir(chemin[len("/ouvrir/"):])
        else:
            super().do_GET()

    def ouvrir(self, cle):
        """Lien direct d'une tuile (nouvel onglet, page sans JavaScript) : demarre puis redirige vers l'editeur."""
        try:
            url = demarrer(cle)
        except EchecDemarrage as erreur:
            corps = ("<!DOCTYPE html><meta charset='utf-8'><title>Échec</title><body style='font-family:Segoe UI,Arial;"
                     "margin:40px'><h1>Impossible d'ouvrir l'éditeur</h1><p style='white-space:pre-line'>%s</p>"
                     "<p><a href='/'>Retour à l'accueil</a></p>" % html.escape(str(erreur))).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
            return
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_POST(self):
        chemin = self.path.split("?")[0].rstrip("/")
        if not chemin.startswith("/api/demarrer/"):
            self.send_error(404)
            return
        if self.headers.get("X-Lanceur") != "1":
            self.send_error(403)
            return
        cle = chemin[len("/api/demarrer/"):]
        if cle not in PROJETS:
            self.repondre({"ok": False, "message": "Projet inconnu : %s" % cle}, 404)
            return
        try:
            self.repondre({"ok": True, "url": demarrer(cle)})
        except EchecDemarrage as erreur:
            print("Échec du démarrage de %s : %s" % (cle, erreur))
            self.repondre({"ok": False, "message": str(erreur)})
        except Exception as erreur:
            print("Erreur inattendue (%s) : %r" % (cle, erreur))
            self.repondre({"ok": False, "message": "Erreur inattendue : %s" % erreur})

    def log_message(self, format, *args):
        pass  # journal silencieux : la console reste lisible


ECHELLE = "0.8"                                      # affichage a 80 % dans la fenetre dediee
NAVIGATEURS = [                                      # Edge d'abord : present sur tous les postes Windows
    os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), r"Microsoft\Edge\Application\msedge.exe"),
    os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), r"Microsoft\Edge\Application\msedge.exe"),
    os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
]


def ouvrir_page(url):
    """Ouvre la page d'accueil dans une fenetre dediee d'Edge ou de Chrome a 80 %, sinon dans le navigateur par defaut."""
    if "--navigateur-habituel" not in sys.argv:
        executable = next((n for n in NAVIGATEURS if os.path.isfile(n)), None)
        if executable:
            profil = os.path.join(os.environ.get("LOCALAPPDATA") or DOSSIER, "LanceurBlockly", "profil")
            try:
                subprocess.Popen([executable, "--app=" + url, "--user-data-dir=" + profil,
                                  "--force-device-scale-factor=" + ECHELLE, "--no-first-run", "--no-default-browser-check"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError as erreur:
                print("Fenêtre dédiée impossible (%s) : navigateur par défaut." % erreur)
        else:
            print("Ni Edge ni Chrome trouvé : navigateur par défaut, à 100 %.")
    webbrowser.open(url)


def lanceur_existant():
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/projets" % PORT, timeout=1) as reponse:
            return json.load(reponse).get("app") == NOM_APPLICATION
    except Exception:
        return False


if __name__ == "__main__":
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    navigateur = "--sans-navigateur" not in sys.argv
    url = "http://localhost:%d" % PORT
    print("Lanceur des éditeurs Blockly (Technologie Services)")
    print("Projets cherchés dans :", DOSSIER_PROJETS)
    try:
        httpd = Serveur(("127.0.0.1", PORT), partial(Handler, directory=PAGE))
    except OSError as erreur:
        if lanceur_existant():
            # Deuxieme double-clic : le lanceur tourne deja, on rouvre simplement la page d'accueil.
            print("Le lanceur est déjà ouvert :", url)
            if navigateur:
                ouvrir_page(url)
            sys.exit(0)
        print("Port %d indisponible : %s" % (PORT, erreur))
        sys.exit(1)

    if navigateur:
        threading.Timer(0.5, ouvrir_page, [url]).start()
    print("Page d'accueil disponible sur", url)
    print("Fermez cette fenêtre pour arrêter le lanceur et les éditeurs qu'il a démarrés.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du lanceur.")
    finally:
        arreter_tout()
        httpd.server_close()
