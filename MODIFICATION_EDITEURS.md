# Modifications à faire appliquer dans les 5 éditeurs

Ces modifications se font **dans la session de chaque projet**, pas depuis le lanceur.

## 1. Bouton « Accueil » dans le bandeau (les 5 projets)

**Fichier** : `bandeau.js` du projet, et sa copie `site_web/bandeau.js` quand elle existe (Mode classe, Adacraft vilain,
Plateforme, mBot1).

**Emplacement** : à la fin du fichier, après la dernière ligne.

**Code** : le contenu de [`bouton_accueil.js`](bouton_accueil.js), à coller tel quel. Il utilise la fonction `$` déjà
définie en tête de `bandeau.js`. `bandeau.js` est chargé en module à la fin de la page : le bandeau `#toolbar` existe déjà.

**Effet** :
- l'éditeur ouvert par le lanceur reçoit `?lanceur=8090` : un bouton « Accueil » (icône maison) apparaît en tête du
  bandeau, avant le logo, et ramène à `http://localhost:8090/` ;
- le port est gardé pour l'onglet (`sessionStorage`) : le bouton reste après un rechargement de la page ;
- l'éditeur ouvert autrement (`lancer_projet.bat`, `site_web`, exe) n'affiche **pas** le bouton.

**Vérification** (faite le 23/10/2026 dans Mode classe, code injecté dans la page sans modifier le projet) : le bouton
s'affiche avec le style `.tb-btn` du bandeau et ramène à la page d'accueil, où la tuile indique « Ouvert · port 8091 ».

## 2. Facultatif : options `--port` dans les `app.py`

Le lanceur fonctionne **sans** cette modification : son adaptateur `demarrer_projet.py` remplace la ligne `PORT = ...`
au chargement et empêche l'ouverture d'un onglet. La modification rend le lancement plus robuste (aucune dépendance au
texte de `app.py`). Dès qu'un `app.py` contient `--port`, le lanceur l'appelle directement avec
`--port <port> --sans-navigateur`.

### Mode classe, Adacraft vilain, Plateforme : `app.py`

Dans le bloc `if __name__ == "__main__":`, juste avant `httpd = None` :

```python
    # Options du lanceur (blockly_ts_lanceur) : --port N impose ce port (sans essayer les suivants),
    # --sans-navigateur n'ouvre pas le navigateur (le lanceur redirige lui-meme sa page vers l'editeur).
    PORT_IMPOSE = "--port" in sys.argv
    if PORT_IMPOSE:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])
```

Puis remplacer `for port in range(PORT, PORT + 10):` par :

```python
    for port in range(PORT, PORT + (1 if PORT_IMPOSE else 10)):
```

Et remplacer `threading.Timer(0.5, webbrowser.open, ["http://localhost:%d" % PORT]).start()` par :

```python
    if "--sans-navigateur" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, ["http://localhost:%d" % PORT]).start()
```

Ajouter dans la docstring du haut :

```
Options :
  --port N            sert sur le port N (et lui seul) au lieu de 8000.
  --sans-navigateur   n'ouvre pas le navigateur (lanceur, apercu integre, tests).
```

### mBot1, mBot2 : `app.py`

`--sans-navigateur` existe déjà. Mêmes deux premiers changements (`PORT_IMPOSE` avant `httpd = None`, puis la boucle
`for port in range(...)`), et la ligne `--port N` dans la docstring.

### Plateforme : `plateforme/serveur.py`

Aucune modification : le lanceur passe le port par la variable `PLATEFORME_PORT` (8093) et ce serveur n'ouvre pas de
navigateur.
