"""Construit l'application Windows du lanceur : dossier LanceurTS (LanceurTS.exe + applications/).

Usage : python construire_exe.py

- PyInstaller (mode dossier) empaquete lanceur.py, demarrer_projet.py et la page d'accueil (page/).
- Les projets des tuiles (PROJETS de lanceur.py) sont recopies dans LanceurTS/applications/, sans .git, site_web/,
  copies de construction ni caches. mBot1 garde ses outils de compilation (outils/arduino*), sans le cache de
  telechargement ni celui de construction.
- Simulateur RDM : Three.js r128 et OrbitControls (ressources/three/, licence MIT) remplacent les adresses Internet
  dans la copie : le simulateur fonctionne hors ligne. Le projet simulation_rdm lui-meme n'est pas modifie.

La construction se fait hors de OneDrive (%USERPROFILE%\\LanceurTS_construction) : plusieurs centaines de Mo y
seraient synchronises pour rien. Resultat : %USERPROFILE%\\LanceurTS_construction\\dist\\LanceurTS.
A relancer apres toute modification d'un projet ou du lanceur.
"""

import ast
import os
import shutil
import subprocess
import sys

import lanceur

DOSSIER = os.path.dirname(os.path.abspath(__file__))
NOM = "LanceurTS"
# Dossier personnel et non AppData : le Python du Microsoft Store redirige les ecritures dans %LOCALAPPDATA% vers
# son propre dossier (AppData\Local\Packages\...), ou l'on ne retrouverait pas l'application.
CONSTRUCTION = os.path.join(os.path.expanduser("~"), "LanceurTS_construction")
SORTIE = os.path.join(CONSTRUCTION, "dist", NOM)
# Dossiers et fichiers jamais recopies dans l'application.
EXCLUS = shutil.ignore_patterns(".git", "__pycache__", "dist", "build", "site_web", "node_modules", "release",
                                "frise-desktop", "graphify-out", ".claude", ".agents", "journaux",
                                "telechargements", "construction", "*.spec")
THREE = {
    "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js": "lib/three.min.js",
    "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js": "lib/OrbitControls.js",
}


def modules_des_projets():
    """Modules importes par les app.py / classe.py des projets : PyInstaller ne peut pas les deviner (exec)."""
    modules = {"demarrer_projet"}
    for projet in lanceur.PROJETS.values():
        dossier = os.path.join(lanceur.DOSSIER_PROJETS, projet["dossier"])
        locaux = {os.path.splitext(n)[0] for n in os.listdir(dossier) if n.endswith(".py")}
        for nom in os.listdir(dossier):
            if not nom.endswith(".py") or nom not in ("app.py", "classe.py"):
                continue
            with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                arbre = ast.parse(f.read())
            for noeud in ast.walk(arbre):
                if isinstance(noeud, ast.Import):
                    noms = [a.name for a in noeud.names]
                elif isinstance(noeud, ast.ImportFrom) and noeud.module and not noeud.level:
                    noms = [noeud.module]
                else:
                    continue
                modules.update(n for n in noms if n.split(".")[0] not in locaux)
    return sorted(modules)


def icone():
    """Icone .ico multi-resolution tiree de page/favicon.png (hexagone TS)."""
    from PIL import Image
    chemin = os.path.join(CONSTRUCTION, "LanceurTS.ico")
    Image.open(os.path.join(DOSSIER, "page", "favicon.png")).save(chemin, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    return chemin


def empaqueter():
    os.makedirs(CONSTRUCTION, exist_ok=True)
    commande = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
                "--name", NOM, "--icon", icone(),
                "--add-data", os.path.join(DOSSIER, "page") + os.pathsep + "page",
                "--workpath", os.path.join(CONSTRUCTION, "build"),
                "--distpath", os.path.join(CONSTRUCTION, "dist"),
                "--specpath", CONSTRUCTION,
                "--paths", DOSSIER]
    for module in modules_des_projets():
        commande += ["--hidden-import", module]
    commande.append(os.path.join(DOSSIER, "lanceur.py"))
    print("PyInstaller :", " ".join(commande[3:12]), "...")
    subprocess.run(commande, check=True)


def copier_projets():
    applications = os.path.join(SORTIE, "applications")
    for cle, projet in lanceur.PROJETS.items():
        source = os.path.join(lanceur.DOSSIER_PROJETS, projet["dossier"])
        cible = os.path.join(applications, projet["dossier"])
        print("Copie de", projet["dossier"], "...")
        shutil.copytree(source, cible, ignore=EXCLUS, dirs_exist_ok=True)
    # Simulateur RDM hors ligne : Three.js copie a cote de index.html et adresses Internet remplacees.
    rdm = os.path.join(applications, "simulation_rdm")
    if os.path.isdir(rdm):
        os.makedirs(os.path.join(rdm, "lib"), exist_ok=True)
        for nom in ("three.min.js", "OrbitControls.js", "LICENSE"):
            shutil.copy2(os.path.join(DOSSIER, "ressources", "three", nom), os.path.join(rdm, "lib", nom if nom != "LICENSE" else "LICENSE-three.txt"))
        page = os.path.join(rdm, "index.html")
        with open(page, encoding="utf-8", newline="") as f:
            texte = f.read()
        for adresse, local in THREE.items():
            if adresse not in texte:
                sys.exit("Adresse Three.js introuvable dans simulation_rdm/index.html : %s" % adresse)
            texte = texte.replace(adresse, local)
        with open(page, "w", encoding="utf-8", newline="") as f:
            f.write(texte)


def taille(dossier):
    return sum(os.path.getsize(os.path.join(r, n)) for r, _, fichiers in os.walk(dossier) for n in fichiers)


if __name__ == "__main__":
    if os.path.isdir(SORTIE):
        shutil.rmtree(SORTIE)                       # dossier produit par une construction precedente
    empaqueter()
    copier_projets()
    print("\nApplication construite :", SORTIE)
    print("Taille : %.0f Mo" % (taille(SORTIE) / 1e6))
