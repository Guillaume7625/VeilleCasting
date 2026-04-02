# VeilleCasting

Surveillance automatique des annonces de casting et de mannequins/modèles, strictement limitée à la région PACA.
Le filtre est strict: uniquement des opportunités de casting actionnables, avec contact exploitable, sans actualités généralistes.
Les profils hommes 40-60 et mannequins/modèles 40+ / senior sont inclus en priorité.
Les sources hors PACA sont ignorées.
La phase 2 ajoute des collecteurs sociaux publics PACA (Facebook / Instagram) uniquement quand leurs pages publiques sont lisibles sans contournement de connexion. Si une source est verrouillée, elle est marquée `unsupported` et la veille continue.
Les alertes sont envoyées via l'API e-mail [Resend](https://resend.com/emails) deux fois par jour (9 h et 16 h).

## Télécharger

[**Télécharger VeilleCasting_Setup.exe**](https://github.com/Guillaume7625/VeilleCasting/releases/latest/download/VeilleCasting_Setup.exe)

## Installer

1. Téléchargez le fichier ci-dessus.
2. Double-cliquez dessus. Si Windows affiche « Windows a protégé votre ordinateur », cliquez **Informations complémentaires** puis **Exécuter quand même**.
3. Suivez l'assistant. Il vous demandera :
   - Votre **clé API Resend**.
   - Votre **adresse d'expédition Resend** (par exemple `VeilleCasting <newsletter@votre-domaine.fr>`).
4. Cliquez « Installer », puis « Terminer ».

## Préparer Resend

1. Créez une clé API : <https://resend.com/api-keys>
2. Vérifiez l'adresse ou le domaine d'expédition dans votre compte Resend.
3. Utilisez une adresse `from` autorisée par Resend dans la configuration.

## Vérifier

1. Ouvrez le **Planificateur de tâches** (cherchez « Planificateur » dans le menu Démarrer).
2. Repérez la tâche **VeilleCasting_2xJour** avec deux déclencheurs (9 h 00 et 16 h 00).
3. Cliquez droit → **Exécuter** pour tester immédiatement.
4. Consultez le journal : appuyez sur `Win + R`, tapez `%APPDATA%\VeilleCasting\veille.log`, Entrée.

## Sécurité

La clé API Resend est stockée dans `%APPDATA%\VeilleCasting\config.json`.
Toute personne ayant accès à votre session Windows peut la lire.
Révoquez la clé à tout moment depuis le tableau de bord Resend.

Installez l'application depuis le compte Windows qui l'utilisera au quotidien.

## Désinstaller

Paramètres Windows → Applications → **Veille Casting** → Désinstaller.
La tâche planifiée est automatiquement supprimée.
