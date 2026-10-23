# Lanceur des éditeurs Blockly (Technologie Services)

Une page d'accueil propose les 5 éditeurs Blockly. Un clic sur une tuile démarre le serveur local de l'éditeur choisi
et l'ouvre dans le navigateur.

## Lancer

- Double-cliquer sur `lancer_projet.bat` (ou `python lanceur.py`) : la page d'accueil s'ouvre sur http://localhost:8090.
- Fermer la fenêtre du lanceur arrête aussi tous les éditeurs qu'il a démarrés.
- Python 3.8 ou plus récent, bibliothèque standard uniquement.

## Les éditeurs

Les projets restent dans leur dossier, **à côté** du dossier du lanceur. Chacun a son port : les programmes enregistrés
dans le navigateur (localStorage) restent ainsi séparés d'un éditeur à l'autre.

| Tuile | Dossier | Port | Serveur démarré |
|---|---|---|---|
| Blockly de base | `../blockly_ts_adacraft_vilain` | 8092 | `app.py` |
| Mode classe | `../blockly_ts_mode_classe` | 8091 | `app.py` |
| Plateforme | `../blockly_ts_plateforme` | 8093 | `plateforme/serveur.py` (port par `PLATEFORME_PORT`) |
| mBot1 | `../blocky_ts_mbot1` | 8094 | `app.py` |
| mBot2 | `../blocky_ts_mbot2` | 8095 | `app.py` |

Le lanceur utilise 8090 et non 8080 : la plateforme lancée seule prend 8080 par défaut. Les ports 8091 à 8095 sont hors
des plages où les éditeurs lancés seuls se replient quand leur port est pris (8000 à 8009, 8020 à 8039) : un éditeur
ouvert à côté par `lancer_projet.bat` ne peut donc pas occuper le port d'une tuile.

L'éditeur s'ouvre avec le paramètre `?lanceur=8090` : il peut ainsi afficher un bouton « Accueil » qui ramène ici.

## Version en ligne (GitHub Pages)

https://jreynaud42000.github.io/blockly_ts_lanceur/ : `index.html` à la racine renvoie vers `page/`. Hors du lanceur
(autre adresse que `localhost`, ou fichier ouvert directement), la page passe en version en ligne : pas de serveur à
démarrer, les tuiles des éditeurs publiés ouvrent leur site, les autres affichent « Bientôt en ligne ». Liste des
éditeurs publiés : objet `EN_LIGNE` dans `page/index.html` (Plateforme, mBot1 et mBot2 pour l'instant ; la Plateforme en ligne n'est que l'éditeur, sans comptes ni séances). Aperçu depuis le lanceur local :
http://localhost:8090/?en-ligne

## Fonctionnement

- `lanceur.py` : sert le dossier `page/` et l'API (`GET /api/projets`, `POST /api/demarrer/<id>`, lien direct
  `/ouvrir/<id>`). Un serveur déjà démarré n'est pas relancé. Un port déjà pris par un autre programme donne un message
  clair sur la tuile. Sous Windows, les serveurs sont rattachés à un « job » : ils s'arrêtent avec le lanceur, même si
  sa fenêtre est fermée brutalement.
- `demarrer_projet.py` : adaptateur pour les `app.py` qui n'acceptent pas encore l'option `--port` (ligne `PORT = ...`
  remplacée au chargement, navigateur non ouvert). Dès qu'un `app.py` accepte `--port` et `--sans-navigateur`, le
  lanceur l'appelle directement.
- `bouton_accueil.js` : code du bouton « Accueil » à coller à la fin du `bandeau.js` de chaque éditeur (voir
  `MODIFICATION_EDITEURS.md`, qui décrit aussi l'option `--port` facultative des `app.py`).
- `journaux/` : sortie de chaque serveur démarré (`<id>.log`), utile en cas d'échec. Non versionné.

## Images

- `page/logo_ts.png`, `page/logo.png` : copiés de `blockly_ts_mode_classe`.
- `page/images/mbot1.png` : copié de `blocky_ts_mbot1`.
- `page/images/maqueenlite.png` : copié de `blockly_ts_mode_classe` (non utilisé pour l'instant).
- Cartes à DEL (micro:bit) et robot mBot2 : illustrations SVG originales dessinées dans la page.
