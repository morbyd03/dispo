# Composants tiers

Dispo utilise plusieurs composants logiciels tiers.

Ces composants conservent leurs licences respectives,
indépendamment de la licence AGPL-3.0 de Dispo.

## Dépendances Python

Les dépendances directes sont déclarées dans
app/requirements.txt.

Les versions exactes installées sont répertoriées
dans app/requirements.lock.

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
| Preact | ~10.12.1 (dependance declaree) | MIT |

Preact est une dependance de FullCalendar Core.

Site officiel : https://preactjs.com/

Les textes des licences sont conserves dans le repertoire
des composants JavaScript.

La version exacte de Preact integree au bundle doit
encore etre confirmee.

Ces composants restent soumis a leurs licences originales.
