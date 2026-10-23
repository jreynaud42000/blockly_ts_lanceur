// ---------- Bouton « Accueil » : retour a la page d'accueil du lanceur (blockly_ts_lanceur) ----------
// L'editeur ouvert par le lanceur recoit ?lanceur=<port> : un bouton « Accueil » est ajoute en tete du bandeau, vers
// http://localhost:<port>/. Le port est garde pour l'onglet (sessionStorage) : le bouton reste apres un rechargement
// sans le parametre. Ouvert autrement (lancer_projet.bat, site_web, exe), l'editeur n'affiche pas ce bouton.
function installerAccueil() {
    let port = new URLSearchParams(location.search).get('lanceur');
    try {
        if (port) sessionStorage.setItem('portLanceur', port);
        else port = sessionStorage.getItem('portLanceur');
    } catch (e) { /* stockage refuse : bouton seulement si le parametre est la */ }
    const barre = $('toolbar');
    if (!/^\d{2,5}$/.test(port || '') || !barre || $('tb-accueil')) return;
    const lien = document.createElement('a');
    lien.id = 'tb-accueil';
    lien.className = 'tb-btn';
    lien.href = 'http://localhost:' + port + '/';
    lien.title = "Revenir à l'accueil : choix de l'éditeur";
    lien.style.textDecoration = 'none';
    lien.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>' +
        '<span>Accueil</span>';
    barre.insertBefore(lien, barre.firstChild);
}
installerAccueil();
