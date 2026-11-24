# Configuration d'un reverse proxy

Pour une installation publique, Dispo doit être accessible
en HTTPS derrière un reverse proxy de confiance.

## Configuration commune

Dans le fichier .env :

    DISPO_DOMAIN=dispo.example.com
    DISPO_PORT=8000
    DJANGO_DEBUG=False
    DJANGO_HTTPS=True
    DJANGO_TRUST_PROXY=True
    DJANGO_HSTS_SECONDS=0

Le nom de domaine doit pointer vers le serveur.

Le reverse proxy doit contrôler les en-têtes transmis,
notamment X-Forwarded-Proto, et préserver le nom d'hôte.

Le serveur Gunicorn ne doit pas être directement accessible
depuis Internet.

## Nginx

Exemple de bloc serveur HTTPS pour Nginx installé sur l'hôte.

Les certificats doivent être obtenus au préalable.

    server {
        listen 443 ssl;
        server_name dispo.example.com;

        ssl_certificate /etc/letsencrypt/live/dispo.example.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/dispo.example.com/privkey.pem;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Redirection HTTP vers HTTPS :

    server {
        listen 80;
        server_name dispo.example.com;
        return 301 https://dispo.example.com$request_uri;
    }

Vérifier la configuration avant rechargement :

    sudo nginx -t

## Caddy

Exemple pour Caddy installé directement sur l'hôte :

    dispo.example.com {
        reverse_proxy 127.0.0.1:8000
    }

Caddy peut gérer automatiquement les certificats HTTPS
si le domaine et les conditions réseau le permettent.

## Traefik

Un fichier Docker Compose complémentaire est fourni :
docker-compose.traefik.yml.

Cette configuration suppose un Traefik déjà opérationnel
avec le fournisseur Docker activé.

Dans le fichier .env, adapter :

    DJANGO_HTTPS=True
    DJANGO_TRUST_PROXY=True
    TRAEFIK_NETWORK=traefik
    TRAEFIK_ROUTER=dispo
    TRAEFIK_ENTRYPOINT=websecure
    TRAEFIK_CERTRESOLVER=letsencrypt

Le réseau Docker doit déjà exister et Traefik doit
y être connecté.

Le nom du routeur doit être unique pour chaque
installation utilisant le même Traefik.

Démarrer Dispo avec :

    docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build

Cette variante nécessite une version de Docker Compose
prenant en charge la directive !reset.

Le port applicatif n'est plus publié sur l'hôte.
Traefik accède directement au conteneur.

La redirection HTTP vers HTTPS doit être configurée
dans Traefik, ainsi que la gestion des certificats.

Conserver les mêmes fichiers Compose pour les futures
commandes de gestion et de maintenance.

Pour les scripts de sauvegarde et restauration :

    export COMPOSE_FILE=docker-compose.yml:docker-compose.traefik.yml

## Validation

Vérifier :

- L'accès HTTPS.
- La redirection HTTP vers HTTPS.
- La connexion des utilisateurs.
- L'absence d'erreur CSRF.
- Le chargement des ressources statiques.
- Les liens HTTPS dans les e-mails.
- L'impossibilité d'accéder directement à Gunicorn
  depuis Internet.

Activer HSTS progressivement après ces vérifications.

## Attention

Lorsqu'un reverse proxy fonctionne dans un conteneur,
127.0.0.1 désigne ce conteneur et non la machine hôte.

Les exemples Nginx et Caddy ci-dessus concernent donc
des services installés directement sur l'hôte.

### Validation de la variante Traefik

La variante Docker Compose a ete testee le 24 novembre 2026
avec Traefik 3.0 et Let's Encrypt.

Les verifications suivantes ont reussi :

- Routage HTTPS vers Dispo.
- Obtention automatique du certificat TLS.
- Validation du certificat par curl.
- Acces HTTP/2 avec un statut 200.
- Absence de publication directe du port applicatif.
- Presence de l'attribut Secure sur le cookie CSRF.

La redirection HTTP vers HTTPS doit etre configuree
separement dans Traefik si elle est souhaitee.
Sans route HTTP, Traefik peut retourner un statut 404.

Le reseau partage avec le reverse proxy doit etre
reserve a des conteneurs de confiance.
