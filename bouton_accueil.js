// ---------- Bouton « Accueil » : retour a la page d'accueil du lanceur (blockly_ts_lanceur) ----------
// L'editeur ouvert depuis la page d'accueil recoit l'adresse de retour :
//  - ?lanceur=<port>  lanceur local : retour vers http://localhost:<port>/ ;
//  - ?accueil=<url>   version en ligne : retour vers cette adresse, acceptee seulement sur jreynaud42000.github.io
//                     (ou localhost) pour qu'un lien exterieur ne puisse pas detourner le bouton.
// L'adresse est gardee pour l'onglet (sessionStorage) : le bouton reste apres un rechargement sans le parametre.
// Ouvert autrement (lancer_projet.bat, favori, exe), l'editeur n'affiche pas ce bouton.
function adresseAccueil() {
    const parametres = new URLSearchParams(location.search);
    const port = parametres.get('lanceur');
    if (/^\d{2,5}$/.test(port || '')) return 'http://localhost:' + port + '/';
    try {
        const url = new URL(parametres.get('accueil') || '');
        const local = url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname);
        if (local || (url.protocol === 'https:' && url.hostname === 'jreynaud42000.github.io')) return url.href;
    } catch (e) { /* parametre absent ou adresse invalide */ }
    return null;
}
function installerAccueil() {
    let adresse = adresseAccueil();
    try {
        if (adresse) sessionStorage.setItem('accueilLanceur', adresse);
        else adresse = sessionStorage.getItem('accueilLanceur');
    } catch (e) { /* stockage refuse : bouton seulement si le parametre est la */ }
    const barre = $('toolbar');
    if (!adresse || !barre || $('tb-accueil')) return;
    const lien = document.createElement('a');
    lien.id = 'tb-accueil';
    lien.className = 'tb-btn';
    lien.href = adresse;
    lien.title = "Revenir à l'accueil : choix de l'éditeur";
    lien.style.textDecoration = 'none';
    lien.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>' +
        '<span>Accueil</span>';
    barre.insertBefore(lien, barre.firstChild);
}
installerAccueil();
