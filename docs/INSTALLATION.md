# Installation de Dispo

## Prérequis

- Un serveur disposant de Docker et Docker Compose.
- Un accès Internet pour la construction initiale.
- Un nom de domaine pour une installation publique.
- Un reverse proxy avec HTTPS pour une installation publique.
- Un serveur SMTP pour l'envoi des e-mails aux agents.

## 1. Récupérer les sources

Récupérer le dépôt Git ou télécharger les sources du projet.

Se placer dans le répertoire contenant docker-compose.yml.

## 2. Préparer la configuration

    umask 077
    cp .env.example .env
    chmod 600 .env

Générer une clé secrète unique :

    python3 -c 'import secrets; print(secrets.token_urlsafe(64))'

Reporter cette clé dans DJANGO_SECRET_KEY dans le fichier .env.

Ne jamais partager cette clé ni publier le fichier .env.

## 3. Configurer un premier démarrage local

Pour tester l'application avant son exposition publique,
renseigner les paramètres suivants dans .env :

    DISPO_DOMAIN=localhost
    DISPO_PORT=8000
    DJANGO_DEBUG=False
    DJANGO_HTTPS=False
    DJANGO_TRUST_PROXY=False
    EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

Le mode console affiche les e-mails dans les journaux.
Il ne doit être utilisé que pour les essais.

## 4. Construire et démarrer Dispo

    docker compose config --quiet
    docker compose up -d --build

Consulter les journaux :

    docker compose logs -f web

L'initialisation automatique applique les migrations,
prépare les permissions et collecte les fichiers statiques.

## 5. Créer le premier administrateur

    docker compose exec web python manage.py createsuperuser

Choisir un identifiant, une adresse électronique valide
et un mot de passe robuste.

## 6. Accéder à l'application

Depuis la machine hébergeant Docker :

    http://localhost:8000/

Le port est publié sur l'interface locale du serveur.

Pour un serveur distant, utiliser un tunnel SSH autorisé
ou configurer un reverse proxy.

## 7. Préparer la mise en production

Configurer le nom de domaine, le reverse proxy HTTPS
et le serveur SMTP.

Ne pas exposer directement le serveur Gunicorn sur Internet.

Voir CONFIGURATION.md pour les paramètres disponibles.

## 8. Arrêter l'application

    docker compose down

Les données sont conservées dans un volume Docker.

ATTENTION : docker compose down -v supprime les volumes
associés au projet, y compris la base de données.

## 9. Consulter les journaux

    docker compose logs --tail=100 web

## 10. Exécuter les tests

    docker compose exec -T web python manage.py test planning
