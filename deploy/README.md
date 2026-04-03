# Déploiement VPS OVH

Ce projet est prévu pour un VPS Linux avec:

- un worker Python qui tourne deux fois par jour
- une page de statut statique servie par Nginx sur un sous-domaine dédié
- des secrets fournis par fichier `.env` ou variables d'environnement

## Vérification préalable

Exécutez `deploy/audit_vps.sh` sur le VPS et vérifiez:

- que le sous-domaine choisi n'est pas déjà utilisé
- qu'aucun service ne monopolise les ports 80/443 ou le port prévu
- que Nginx / Caddy / Traefik n'ont pas déjà une route sur ce sous-domaine
- que le certificat TLS peut inclure le nouveau nom DNS

## Installation

1. Créez un utilisateur système dédié, par exemple `veillecasting`.
2. Déployez le dépôt dans `/opt/veillecasting`.
3. Créez un venv Python et installez:

   ```bash
   pip install -r requirements.txt
   ```

4. Créez `/etc/veillecasting.env` à partir de `deploy/env.example`.
5. Installez les unités systemd:

   ```bash
   sudo cp deploy/veillecasting.service /etc/systemd/system/
   sudo cp deploy/veillecasting.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now veillecasting.timer
   ```

6. Configurez Nginx avec `deploy/nginx-casting-paca.conf.example` en pointant vers:

   ```text
   /var/lib/veillecasting/public
   ```

## Résultat attendu

Le worker produit automatiquement:

- `status.json`
- `index.html`
- `veille.log`
- `audit.jsonl`

dans le répertoire `VEILLECASTING_DATA_DIR`.
