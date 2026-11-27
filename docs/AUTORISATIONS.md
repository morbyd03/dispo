# Autorisations de Dispo

## Principes

Les autorisations sont independantes des grades,
des fonctions et des qualifications operationnelles.

Les services metier controlent les droits de leur auteur.
Les interfaces doivent transmettre l'identifiant issu
de la session authentifiee, jamais celui fourni par
un formulaire utilisateur.

## Agent

- Gestion de ses propres disponibilites.
- Consultation du planning collectif.
- Consultation de ses informations personnelles.
- Aucune administration des autres comptes.

## Administrateur Dispo

- Appartenance au groupe Administrateurs Dispo.
- Creation des agents avec la permission correspondante.
- Modification des agents ordinaires avec la permission
  correspondante.
- Gestion des qualifications selon les permissions accordees.
- Aucune modification des comptes techniques.
- Aucune modification de son propre compte par les
  services administratifs.

## Superutilisateur

- Administration generale de Dispo.
- Gestion des agents disposant de droits administratifs.
- Import et export des agents.
- Rattachement des profils aux comptes existants.
- Administration technique Django si le compte est
  egalement actif et staff.

## Delegation des qualifications

Les permissions de creation, modification et retrait
des qualifications peuvent etre accordees separement.

Un validateur ne peut pas modifier ses propres qualifications.

Les comptes techniques sont proteges.
Les qualifications des comptes privilegies necessitent
un superutilisateur.

## Protection des comptes

Un compte est considere comme privilegie s'il dispose :

- Du statut superutilisateur.
- Du statut staff.
- D'une appartenance a un groupe.
- De permissions individuelles.

Les services agents exigent un auteur actif et identifie.

## Etat implementation

Les autorisations centrales et leur raccordement aux
services agents, qualifications et import/export sont testes.

Les anciennes interfaces doivent encore etre remplacees.
La journalisation des operations individuelles sur les
profils reste a integrer.

La gestion des disponibilites et du planning devra
appliquer les controles d'acces appropries.

Les permissions decrites pour les futures interfaces
constituent la politique cible et non une garantie
que les anciennes interfaces sont deja conformes.
