# VeilleCasting

Surveillance automatique des annonces de casting et de mannequins/modèles, strictement limitée à la région PACA.
Le filtre est strict: uniquement des opportunités de casting actionnables, avec contact exploitable, sans actualités généralistes.
Les profils hommes 40-60 et mannequins/modèles 40+ / senior sont inclus en priorité.
Les sources hors PACA sont ignorées.
La phase 2 ajoute des collecteurs sociaux publics PACA (Facebook / Instagram) uniquement quand leurs pages publiques sont lisibles sans contournement de connexion. Si une source est verrouillée, elle est marquée `unsupported` et la veille continue.
L'IA OpenAI est optionnelle: elle sert à mieux qualifier les annonces candidates et à enrichir la synthèse, sans remplacer les filtres PACA et le contrôle du contact exploitable.
Les alertes sont envoyées via l'API e-mail [Resend](https://resend.com/emails) deux fois par jour (9 h et 16 h).

## Télécharger

[**Télécharger VeilleCasting_Setup.exe**](https://github.com/Guillaume7625/VeilleCasting/releases/latest/download/VeilleCasting_Setup.exe)

## Installer

1. Téléchargez le fichier ci-dessus.
2. Double-cliquez dessus. Si Windows affiche « Windows a protégé votre ordinateur », cliquez **Informations complémentaires** puis **Exécuter quand même**.
3. Suivez l'assistant. Il vous demandera :
   - Votre **clé API Resend**.
   - Votre **adresse d'expédition Resend**. Pour ce projet, l'adresse validée utilisée par défaut est `piccinno@hotmail.com`.
   - Si vous voulez l'IA, votre **clé API OpenAI** et éventuellement le **modèle OpenAI** à utiliser.
4. Cliquez « Installer », puis « Terminer ».

## Préparer Resend

1. Créez une clé API : <https://resend.com/api-keys>
2. Vérifiez l'adresse ou le domaine d'expédition dans votre compte Resend.
3. Utilisez `piccinno@hotmail.com` ou une autre adresse `from` autorisée par Resend dans la configuration.

## Préparer OpenAI

1. Créez une clé API OpenAI si vous voulez activer le raffinement par IA.
2. Laissez le champ OpenAI vide si vous préférez fonctionner uniquement avec les règles et le scoring local.
3. Le modèle par défaut recommandé est `gpt-5.1-mini`, mais vous pouvez le changer dans la configuration.
4. Si vous préférez ne rien saisir dans l'installateur, vous pouvez aussi définir `OPENAI_API_KEY` et `OPENAI_MODEL` dans l'environnement Windows du compte qui exécute la tâche.

## Mode quasi automatique

Si vous voulez vraiment minimiser la saisie:

1. Laissez le projet utiliser `piccinno@hotmail.com` comme expéditeur par défaut.
2. Renseignez uniquement la clé Resend une fois dans l'installateur, ou fournissez `RESEND_API_KEY` dans l'environnement.
3. Si vous voulez l'IA, fournissez `OPENAI_API_KEY` dans l'environnement ou collez-la une seule fois dans l'installateur.
4. Le reste est automatique: tâches planifiées, heures d'envoi, filtrage PACA, newsletter et envoi Resend.

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
