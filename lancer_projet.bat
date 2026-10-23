@echo off
TITLE Lanceur des editeurs Blockly
color 0A

REM Se placer dans le dossier du .bat : sinon le lanceur ne trouve pas sa page d'accueil.
cd /d "%~dp0"

echo ========================================================
echo   LANCEUR DES EDITEURS BLOCKLY (Technologie Services)
echo ========================================================
echo.

if not exist "lanceur.py" (
  echo ERREUR : lanceur.py est introuvable dans ce dossier.
  pause
  exit /b 1
)

echo La page d'accueil s'ouvre dans le navigateur : http://localhost:8090
echo Chaque editeur demarre sur son propre port (8091 a 8095) au clic sur sa tuile.
echo ATTENTION : si vous fermez cette fenetre, le lanceur ET les editeurs s'arreteront.
echo.
python lanceur.py

echo.
echo Le lanceur s'est arrete.
pause
