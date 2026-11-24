# Composants tiers

Dispo utilise plusieurs composants logiciels tiers.

Ces composants conservent leurs licences respectives,
indépendamment de la licence AGPL-3.0 de Dispo.

## Dépendances Python

Les dépendances directes sont déclarées dans
app/requirements.txt.

Les versions exactes installées sont répertoriées
dans app/requirements.lock.

| Composant | Version | Licence |
|---|---|---|
| Django | 5.2.19 | BSD-3-Clause |
| Gunicorn | 23.0.0 | MIT |
| WhiteNoise | 6.12.0 | MIT |
| asgiref | 3.13.0 | BSD-3-Clause |
| packaging | 26.4 | Apache-2.0 OR BSD-2-Clause |
| sqlparse | 0.6.1 | BSD-3-Clause |

Les textes des licences de ces dépendances sont fournis
avec leurs distributions respectives.

Django fournit également des ressources statiques pour
son interface d'administration, accompagnées des mentions
de licence de sa distribution.


## FullCalendar

Version intégrée : 6.1.19.

Site officiel : https://fullcalendar.io/

Les fichiers JavaScript sont hébergés localement.

Sources de distribution :

- https://cdn.jsdelivr.net/npm/fullcalendar@6.1.19/index.global.min.js
- https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.19/locales/fr.global.min.js

Les mentions originales de copyright sont conservées.

Les licences fournies avec FullCalendar sont disponibles
dans app/planning/static/planning/vendor/fullcalendar/.

### Composants FullCalendar

| Composant | Version | Licence |
|---|---|---|
| FullCalendar Standard Bundle | 6.1.19 | MIT |
| @fullcalendar/core | 6.1.19 | MIT |
| @fullcalendar/daygrid | 6.1.19 | MIT |
| @fullcalendar/timegrid | 6.1.19 | MIT |
| @fullcalendar/list | 6.1.19 | MIT |
| @fullcalendar/interaction | 6.1.19 | MIT |
| @fullcalendar/multimonth | 6.1.19 | MIT |
| Preact | 10.12.1 (version verrouillée) | MIT |

Preact est une dependance de FullCalendar Core.

Site officiel : https://preactjs.com/

Les textes des licences sont conserves dans le repertoire
des composants JavaScript.

Le fichier pnpm-lock.yaml du dépôt officiel FullCalendar
au tag v6.1.19 indique la version Preact 10.12.1.

Source :
https://github.com/fullcalendar/fullcalendar/blob/v6.1.19/pnpm-lock.yaml

La version verrouillée est ainsi identifiée, sans vérification
indépendante de la composition du bundle distribué.

Ces composants restent soumis a leurs licences originales.
