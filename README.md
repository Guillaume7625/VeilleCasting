# VeilleCasting

Surveillance automatique des annonces de casting (PACA / Occitanie).
Les alertes sont envoyées par e-mail à `piccinno@hotmail.com` deux fois par jour (9 h et 16 h).

## Télécharger

[**Télécharger VeilleCasting_Setup.exe**](https://github.com/Guillaume7625/VeilleCasting/releases/latest/download/VeilleCasting_Setup.exe)

## Installer

1. Téléchargez le fichier ci-dessus.
2. Double-cliquez dessus. Si Windows affiche « Windows a protégé votre ordinateur », cliquez **Informations complémentaires** puis **Exécuter quand même**.
3. Suivez l'assistant. Il vous demandera :
   - Votre **adresse Gmail** (celle qui enverra les alertes).
   - Votre **mot de passe d'application Gmail** (16 caractères, sans espaces).
4. Cliquez « Installer », puis « Terminer ».

## Obtenir le mot de passe d'application Gmail

1. Activez la validation en deux étapes : <https://myaccount.google.com/signinoptions/two-step-verification>
2. Créez un mot de passe d'application : <https://myaccount.google.com/apppasswords>
   - Nom : `VeilleCasting`
   - Copiez le code de 16 caractères affiché.

## Vérifier

1. Ouvrez le **Planificateur de tâches** (cherchez « Planificateur » dans le menu Démarrer).
2. Repérez la tâche **VeilleCasting_2xJour** avec deux déclencheurs (9 h 00 et 16 h 00).
3. Cliquez droit → **Exécuter** pour tester immédiatement.
4. Consultez le journal : appuyez sur `Win + R`, tapez `%APPDATA%\VeilleCasting\veille.log`, Entrée.

## Sécurité

Le mot de passe d'application Gmail est stocké dans `%APPDATA%\VeilleCasting\config.json`.
Toute personne ayant accès à votre session Windows peut le lire.
Ce mot de passe ne donne accès qu'à l'envoi d'e-mails (pas à votre compte Gmail complet).
Vous pouvez le révoquer à tout moment sur <https://myaccount.google.com/apppasswords>.

Installez l'application depuis le compte Windows qui l'utilisera au quotidien.

## Désinstaller

Paramètres Windows → Applications → **Veille Casting** → Désinstaller.
La tâche planifiée est automatiquement supprimée.
