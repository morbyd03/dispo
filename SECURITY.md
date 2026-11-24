# Politique de sécurité

## Versions prises en charge

Dispo est actuellement en développement actif.

Les corrections de sécurité sont appliquées à la version
maintenue du projet.

## Signalement d'une vulnérabilité

Ne pas publier de vulnérabilité exploitable dans une issue
publique avant qu'une correction soit disponible.

Utiliser le mécanisme de signalement privé de GitHub,
lorsqu'il est disponible, ou contacter le mainteneur
par un canal privé.

Ne jamais transmettre de données personnelles d'agents,
de mots de passe, de clés secrètes ou de bases de données.

## Recommandations de déploiement

- Utiliser HTTPS en production.
- Utiliser des mots de passe robustes.
- Conserver DJANGO_DEBUG=False.
- Générer une clé secrète unique par installation.
- Protéger le fichier .env.
- Ne pas exposer directement Gunicorn sur Internet.
- Maintenir Docker et les dépendances à jour.
- Sauvegarder régulièrement les données.
- Limiter les droits administrateurs.
- Contrôler les accès au serveur et aux sauvegardes.

## Limites

Dispo est un outil d'aide à la gestion des disponibilités.

Les tests automatisés et les audits de dépendances
ne constituent pas une certification de sécurité.

L'application ne remplace pas les systèmes officiels
d'alerte et de mobilisation des secours.
