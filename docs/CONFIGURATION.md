# Configuration de Dispo

La configuration est centralisée dans le fichier .env.

Le fichier .env.example fournit un modèle à compléter.

Après une modification du fichier .env :

    docker compose up -d --force-recreate

## Réseau

| Variable | Description |
|---|---|
| DISPO_DOMAIN | Nom de domaine sans protocole ni chemin |
| DISPO_PORT | Port HTTP local sur la machine hôte |
| DJANGO_ALLOWED_HOSTS | Domaines autorisés, séparés par des virgules |
| DJANGO_CSRF_TRUSTED_ORIGINS | Origines CSRF autorisées avec protocole |

## Sécurité

| Variable | Description |
|---|---|
| DJANGO_SECRET_KEY | Clé secrète unique et obligatoire |
| DJANGO_DEBUG | Doit rester False en production |
| DJANGO_HTTPS | Active les protections liées à HTTPS |
| DJANGO_TRUST_PROXY | Autorise la confiance dans X-Forwarded-Proto |
| DJANGO_HSTS_SECONDS | Durée HSTS en secondes |

DJANGO_TRUST_PROXY ne doit être activé que derrière un
reverse proxy de confiance qui contrôle les en-têtes transmis.

Le serveur applicatif ne doit pas être directement
accessible depuis Internet.

Activer HSTS progressivement après validation du HTTPS.

HSTS pour les sous-domaines et HSTS Preload ne sont pas
activés par défaut.

## Messagerie

| Variable | Description |
|---|---|
| EMAIL_BACKEND | Moteur d'envoi des e-mails |
| EMAIL_HOST | Serveur SMTP |
| EMAIL_PORT | Port SMTP |
| EMAIL_HOST_USER | Identifiant SMTP |
| EMAIL_HOST_PASSWORD | Mot de passe SMTP |
| EMAIL_USE_TLS | Utilisation de STARTTLS |
| EMAIL_USE_SSL | Utilisation de TLS implicite |
| DEFAULT_FROM_EMAIL | Adresse d'expédition |
| SERVER_EMAIL | Adresse utilisée pour les messages serveur |

Ne pas activer simultanément EMAIL_USE_TLS et EMAIL_USE_SSL.

Les paramètres exacts dépendent du fournisseur SMTP.

## Personnalisation

| Variable | Description |
|---|---|
| DISPO_NAME | Nom de l'application |
| DISPO_CENTRE | Nom du centre de secours |
| DISPO_LOGO | Nom du fichier image personnalisé |
| TZ | Fuseau horaire |

## Logo personnalisé

Placer une image PNG, JPEG ou WebP dans le dossier branding.

Exemple :

    branding/logo.png

Configurer :

    DISPO_LOGO=logo.png

Vérifier les permissions :

    chmod 755 branding
    chmod 644 branding/logo.png

Recréer le conteneur :

    docker compose up -d --force-recreate

Aucune reconstruction de l'image Docker n'est nécessaire.

Pour revenir au logo générique :

    DISPO_LOGO=

Puis recréer le conteneur.

Les fichiers de personnalisation sont exclus du dépôt Git.

## Fuseau horaire

Le fuseau horaire par défaut est Europe/Paris.

## Environnement de préproduction

La variable suivante permet d'afficher un bandeau orange
sur les pages de l'application :

    DISPO_PREPRODUCTION=True

Par défaut, cette option est désactivée.

Le bandeau permet de distinguer visuellement une installation
de test d'une installation de production.

Cette option est uniquement visuelle. Elle ne protège pas
l'accès à l'application et n'empêche pas les envois d'e-mails.

Pour une préproduction, il est recommandé d'utiliser :

- Une base de données indépendante.
- Des comptes et des données fictifs.
- Une clé secrète distincte.
- Une protection supplémentaire du reverse proxy.
- Le backend email console de Django.
