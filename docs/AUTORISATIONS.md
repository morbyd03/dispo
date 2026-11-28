# Autorisations de Dispo

## Principes

Les autorisations sont independantes des grades,
des fonctions et des qualifications operationnelles.

Les services metier controlent les droits de leur auteur.
Les interfaces transmettent l'identifiant issu de la
session authentifiee, jamais celui fourni par un formulaire.

Les controles des services ne reposent pas uniquement
sur la visibilite des boutons dans les interfaces.

## Agent

- Gestion de ses propres disponibilites.
- Consultation du planning collectif.
- Consultation de ses informations personnelles.
- Changement de son mot de passe.
- Aucune administration des autres comptes.

Un profil operationnel est necessaire pour declarer
des disponibilites.

## Administrateur Dispo

L'administration fonctionnelle repose sur le groupe
Administrateurs Dispo et les permissions correspondantes.

Ce groupe dispose des permissions suivantes :

- auth.view_user
- auth.add_user
- auth.change_user
- planning.view_competenceagent
- planning.add_competenceagent
- planning.change_competenceagent
- planning.delete_competenceagent

Les administrateurs peuvent consulter, creer et modifier
les agents ordinaires, gerer leur statut et transmettre
des liens d'activation ou de reinitialisation.

Ils peuvent gerer les qualifications selon leurs droits.

Ils ne peuvent pas modifier leurs propres droits,
administrer les comptes techniques ou administrer
les comptes privilegies.

La commande initialiser_dispo maintient la composition
exacte des permissions du groupe reserve.

## Superutilisateur

- Administration generale de Dispo.
- Gestion des agents disposant de droits administratifs.
- Attribution et retrait des droits administratifs.
- Attribution et retrait des delegations.
- Import et export des agents par les services metier.
- Rattachement des profils aux comptes existants.
- Administration technique Django si le compte est
  egalement actif et staff.

Les restrictions relatives a l'auto-administration
et aux comptes techniques restent applicables dans
les services fonctionnels.

## Delegation des qualifications

Les permissions suivantes peuvent etre accordees
individuellement, sans appartenance au groupe
Administrateurs Dispo :

- planning.add_competenceagent
- planning.change_competenceagent
- planning.delete_competenceagent

Une delegation permet d'acceder a la gestion des
qualifications sans autoriser la modification generale
des informations administratives des agents.

Un validateur ne peut pas modifier ses propres
qualifications.

Les comptes techniques sont proteges.
La gestion des qualifications des comptes privilegies
necessite un superutilisateur.

## Protection des comptes

Un compte est considere comme privilegie s'il dispose :

- Du statut superutilisateur.
- Du statut staff.
- D'une appartenance a un groupe.
- De permissions individuelles.

Les services agents exigent un auteur actif et identifie.

Les comptes staff et superutilisateurs sont exclus
des operations fonctionnelles de gestion des agents.

## Modification des droits

L'interface de modification des droits est reservee
aux superutilisateurs.

Elle permet de modifier :

- L'appartenance au groupe Administrateurs Dispo.
- Les trois permissions individuelles delegables.

Les autres groupes et permissions sont conserves.

Une confirmation signee, valable 30 minutes, associe
l'auteur, le profil concerne et l'etat initial des droits.

Le service refuse une confirmation invalide, expiree
ou correspondant a un etat devenu obsolete.

Cette confirmation n'est pas un jeton a usage unique.
Les droits obtenus par d'autres groupes ne sont pas
automatiquement retires.

## Journalisation

Les operations suivantes sont journalisees :

- Creation d'un agent.
- Modification de son profil.
- Rattachement d'un profil.
- Activation et desactivation.
- Modification des droits.
- Attribution, modification et retrait des qualifications.
- Import des agents.

Les modifications sans changement effectif ne generent
pas de journal de modification correspondant.

Les operations transactionnelles et leurs journaux
sont annules ensemble en cas d'echec.

## Etat implementation

Les services metier et les interfaces individuelles
de gestion des agents, qualifications et droits sont
implementes et testes.

Le profil personnel et la gestion des disponibilites
utilisent le nouveau modele ProfilAgent.

Les services d'import et d'export sont implementes.
Leurs interfaces restent a construire.

La gestion collective des qualifications et le
planning mensuel restent a implementer.

Voir SECURITE_COMPTES.md pour la gestion des sessions,
des mots de passe et des revocations.
