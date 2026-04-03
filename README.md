# VeilleCasting

Surveillance automatique des annonces de casting et de mannequins/modèles, strictement limitée à la région PACA.
Le filtre est strict: uniquement des opportunités de casting actionnables, avec contact exploitable, sans actualités généralistes.
Les profils hommes 40-60 et mannequins/modèles 40+ / senior sont inclus en priorité.
Les sources hors PACA sont ignorées.
La phase 2 ajoute des collecteurs sociaux publics PACA (Facebook / Instagram) uniquement quand leurs pages publiques sont lisibles sans contournement de connexion. Si une source est verrouillée, elle est marquée `unsupported` et la veille continue.
L'IA OpenAI est optionnelle: elle sert à mieux qualifier les annonces candidates et à enrichir la synthèse, sans remplacer les filtres PACA et le contrôle du contact exploitable.
Les alertes sont envoyées via l'API e-mail [Resend](https://resend.com/emails) deux fois par jour (9 h et 16 h).
La version de production est prévue pour un **VPS OVH Linux** avec un **sous-domaine dédié** qui sert une page de statut statique mise à jour automatiquement.

## Préparer Resend

1. Créez une clé API : <https://resend.com/api-keys>
2. Vérifiez l'adresse ou le domaine d'expédition dans votre compte Resend.
3. Utilisez `piccinno@hotmail.com` ou une autre adresse `from` autorisée par Resend dans la configuration.

## Préparer OpenAI

1. Créez une clé API OpenAI si vous voulez activer le raffinement par IA.
2. Laissez le champ OpenAI vide si vous préférez fonctionner uniquement avec les règles et le scoring local.
3. Le modèle par défaut recommandé est `gpt-5.1-mini`, mais vous pouvez le changer dans la configuration.
4. Si vous préférez ne rien saisir dans l'installateur, vous pouvez aussi définir `OPENAI_API_KEY` et `OPENAI_MODEL` dans l'environnement Windows du compte qui exécute la tâche.

## Déploiement VPS OVH

1. Réservez un sous-domaine, par exemple `casting-paca.votredomaine.tld`.
2. Vérifiez que ce sous-domaine ne sert déjà aucun autre site sur le VPS.
3. Utilisez les fichiers de déploiement dans `deploy/`:
   - `deploy/veillecasting.service`
   - `deploy/veillecasting.timer`
   - `deploy/nginx-casting-paca.conf.example`
   - `deploy/env.example`
   - `deploy/audit_vps.sh`
4. Créez un environnement Python, installez `requirements.txt`, puis lancez le worker via systemd.
5. Servez `VEILLECASTING_DATA_DIR/public` derrière Nginx sur le sous-domaine.

## Mode quasi automatique

Si vous voulez vraiment minimiser la saisie:

1. Laissez le projet utiliser `piccinno@hotmail.com` comme expéditeur par défaut.
2. Renseignez uniquement la clé Resend une fois, ou fournissez `RESEND_API_KEY` dans l'environnement.
3. Si vous voulez l'IA, fournissez `OPENAI_API_KEY` dans l'environnement ou collez-la une seule fois dans la configuration.
4. Le reste est automatique: planification Linux, heures d'envoi, filtrage PACA, newsletter, envoi Resend, et page de statut statique du sous-domaine.

## Vérifier

1. Sur Linux, consultez le journal système du service `veillecasting`.
2. Ouvrez `status.json` ou `index.html` dans `VEILLECASTING_DATA_DIR/public`.
3. Vérifiez le sous-domaine via le reverse proxy Nginx.

## Sécurité

La clé API Resend est stockée dans le répertoire de données de l'application, ou dans les variables d'environnement du service.
Révoquez la clé à tout moment depuis le tableau de bord Resend.

Sur un VPS partagé par plusieurs services, utilisez un utilisateur système dédié et un répertoire de données isolé.

## Désinstaller

Supprimez le service systemd, le timer, le répertoire de données et la configuration Nginx du sous-domaine.
