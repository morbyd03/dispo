# Strategie de developpement de Dispo

## Statut du projet

La version 0.1.0 constitue un prototype technique.
Les installations existantes ne sont pas utilisees
en conditions reelles par les agents.

La version 0.2.0 vise le premier lancement officiel,
prevu debut janvier 2027.

## Compatibilite

Avant le lancement officiel :

- Aucune obligation de retrocompatibilite.
- Les bases de test peuvent etre recreees.
- Les modeles de donnees peuvent etre refondus.
- Les migrations peuvent etre consolidees.
- Les interfaces obsoletes peuvent etre remplacees.
- Les tests historiques obsoletes peuvent etre adaptes.
- Aucune reprise des donnees du prototype n'est exigee.

L'historique Git est conserve.

La retrocompatibilite deviendra une exigence lorsque
l'application sera declaree utilisee en conditions reelles.

## Priorites

1. Securite et integrite des donnees.
2. Simplicite et maintenabilite.
3. Architecture modulaire.
4. Utilite pour les agents.
5. Regles metier configurables.
6. Ergonomie.

## Objectifs prioritaires de la version 0.2.0

- Gestion des comptes et profils agents.
- Authentification par matricule ou adresse electronique.
- Import et export des agents.
- Gestion des grades, fonctions et qualifications.
- Declaration des disponibilites.
- Planning mensuel.
- Previsionnel collectif des effectifs et qualifications.
- Identification des periodes necessitant un renfort.

Les fonctionnalites secondaires peuvent etre reportees.

## Methode de travail

Le developpement est organise par chantiers fonctionnels.

Chaque chantier doit disposer :

- D'un perimetre clairement defini.
- De tests pertinents.
- D'une documentation adaptee.
- D'un commit Git coherent.
- D'un point d'arret identifiable.

La compatibilite avec le prototype ne doit pas justifier
une complexite technique inutile.
