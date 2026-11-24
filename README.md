# Dispo

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Django](https://img.shields.io/badge/django-5.2-green)

Application web auto-hébergée de gestion des disponibilités
des sapeurs-pompiers volontaires.

Dispo permet aux agents de déclarer leurs disponibilités
et aux responsables de centre de visualiser les périodes
de couverture opérationnelle.

## Fonctionnalités

- Déclaration et modification des disponibilités.
- Créneaux horaires pouvant traverser minuit.
- Calendrier individuel interactif.
- Copie des disponibilités vers plusieurs journées.
- Planning hebdomadaire collectif.
- Analyse de la couverture SSUAP et incendie.
- Détection des qualifications manquantes.
- Gestion des agents et des compétences.
- Dates de validité des qualifications.
- Gestion des droits administrateurs.
- Activation des comptes par e-mail.
- Réinitialisation des mots de passe.
- Rappel de l'identifiant de connexion dans les e-mails.
- Interface adaptée aux ordinateurs et smartphones.
- Thèmes clair et sombre.
- Personnalisation du nom, du centre et du logo.
- Bandeau configurable de préproduction.
- Sauvegarde et restauration sécurisées des données.

## Technologies

- Python 3.13
- Django 5.2 LTS
- SQLite
- Gunicorn
- WhiteNoise
- FullCalendar
- Docker et Docker Compose

## Installation

Dispo est conçu pour fonctionner sur un serveur
auto-hébergé avec Docker Compose.

L'installation initialise automatiquement la base de
données, le catalogue de compétences et les permissions
administratives.

Consulter le [guide d'installation](docs/INSTALLATION.md).

## Documentation

- [Vision et objectifs du projet](docs/VISION.md)
- [Feuille de route](ROADMAP.md)

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Reverse proxies et HTTPS](docs/REVERSE_PROXY.md)
- [Sauvegarde et restauration](docs/SAUVEGARDES.md)
- [Politique de sécurité](SECURITY.md)
- [Historique des versions](CHANGELOG.md)
- [Composants tiers](THIRD_PARTY_NOTICES.md)
- [Licence AGPL-3.0](LICENSE)

## Tests

La version 0.1.0 dispose de 51 tests automatisés.

Depuis le répertoire du projet :

    docker compose exec -T web python manage.py test planning

## Sécurité

Dispo traite des données personnelles et opérationnelles.

Une installation publique doit utiliser HTTPS et disposer
d'une politique de sauvegarde adaptée.

Dispo constitue un outil d'aide à la gestion des
disponibilités. Il ne remplace pas les systèmes officiels
d'alerte, de mobilisation ou de gestion opérationnelle.

## État du projet

Version actuelle : **0.1.0**

Projet en développement actif. Cette première version est expérimentale.

## Développement et contributions

Dispo est un projet né d'un besoin concret de gestion des
disponibilités au sein d'un centre de secours.

L'application est développée en collaboration avec
ChatGPT (OpenAI), dans une démarche de développement
assisté par intelligence artificielle.

Le porteur du projet apporte son expérience opérationnelle,
définit les besoins, oriente les choix fonctionnels et
techniques, réalise les tests et valide les évolutions.

ChatGPT contribue à la conception de l'architecture,
à la rédaction du code, à la résolution des problèmes
techniques, à la sécurisation de l'application et à la
rédaction de la documentation.

Cette collaboration est volontairement mentionnée par
souci de transparence et de reconnaissance des contributions.

Le projet reste placé sous la responsabilité humaine
de son mainteneur.

## Licence

Dispo est distribué sous licence GNU AGPL-3.0.
Consulter le fichier [LICENSE](LICENSE).

Les composants tiers conservent leurs licences respectives.
