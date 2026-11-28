# Import et export des agents

## Objectifs

Permettre la gestion collective des agents sans dépendance
à un tableur particulier ni à un service externe.

Les opérations reposent sur les services métier de Dispo,
indépendamment des futures interfaces web et API.

## Format CSV

- Encodage UTF-8, avec ou sans BOM à l'import.
- Séparateur point-virgule ou virgule à l'import.
- Séparateur point-virgule à l'export.
- Limite d'import : 2 Mio et 1000 lignes de données.

### Colonnes obligatoires

| Colonne | Description |
| --- | --- |
| matricule | Identifiant unique de l'agent |
| nom | Nom de famille |
| prenom | Prénom |
| grade | Code du grade dans le référentiel |
| email | Adresse électronique |

### Colonnes facultatives

| Colonne | Description |
| --- | --- |
| telephone | Numéro de téléphone |
| fonction | Fonctions séparées par une barre verticale |

Les matricules sont actuellement validés comme des chaînes
de chiffres ASCII. Les zéros initiaux sont conservés.

Le format définitif des matricules reste à confirmer.

Les grades, fonctions et qualifications proviennent des
référentiels configurés dans Dispo.

## Qualifications

Les colonnes de qualifications correspondent aux codes
des qualifications actives.

Valeurs acceptées :

- 1 : attribuer ou conserver la qualification.
- 0 : retirer la qualification si elle existe.
- Cellule vide : ne pas modifier la qualification.
- Colonne absente : ne pas modifier la qualification.

Les dates et le validateur des attributions existantes
sont conservés lorsque celles-ci restent inchangées.

Tout retrait nécessite une confirmation explicite.

## Identification des agents

Le rapprochement repose sur le matricule.

Trois opérations sont possibles :

- Création d'un compte et de son profil.
- Modification d'un profil existant.
- Rattachement d'un profil à un compte historique.

L'absence d'un agent dans le fichier ne provoque
ni suppression ni désactivation.

Les comptes historiques incomplets peuvent nécessiter
une régularisation préalable.

## Adresses électroniques

Chaque agent doit disposer d'une adresse électronique
explicitement renseignée dans le fichier CSV.

Dispo ne génère aucune adresse automatiquement
et n'impose aucun domaine de messagerie.

Les adresses personnelles et professionnelles
sont acceptées sous réserve de validité et d'unicité.

Une adresse absente, vide, invalide ou en doublon
bloque l'import.

Cette obligation concerne également les agents
déjà présents dans Dispo.

Le changement d'une adresse électronique existante
nécessite une procédure distincte.

## Prévisualisation et confirmation

La prévisualisation ne réalise aucune écriture.

Elle présente les créations, modifications, rattachements,
attributions et retraits envisagés.

La confirmation repose sur un jeton signé :

- Durée de validité de 30 minutes.
- Association à l'administrateur.
- Identifiant unique.
- Empreinte du fichier original.
- Empreinte de la prévisualisation et de l'état initial.
- Protection contre les rejeux par unicité en base.

Un changement détecté depuis la prévisualisation
impose une nouvelle confirmation.

Les opérations et la consommation du jeton appartiennent
à une même transaction.

En cas d'échec, l'ensemble des opérations est annulé.

## Protection des comptes

L'import ne modifie pas les mots de passe, les matricules,
les adresses électroniques existantes, les permissions
ou les statuts des comptes existants.

Les nouveaux comptes sont créés actifs, sans mot de passe
utilisable et sans privilège administratif.

Aucun courrier électronique n'est envoyé automatiquement.

## Modes d'export

### Consultation

Mode par défaut, destiné à la consultation des données.

Les valeurs potentiellement interprétables comme des
formules sont neutralisées par une apostrophe.

Ce mode peut modifier la représentation de certaines
valeurs et n'est pas destiné au réimport.

### Réimport

Mode destiné aux échanges avec Dispo.

Les valeurs sont conservées sans transformation.

Les valeurs potentiellement dangereuses sont refusées,
sauf les téléphones internationaux strictement numériques.

Le fichier est soumis au moteur de prévisualisation.
L'export est refusé si un réimport immédiat entraînerait
une modification détectée des données existantes.

Ce fichier ne doit pas être ouvert directement dans un
tableur susceptible d'interpréter les cellules.

## Autorisations et journalisation

Les imports et exports sont actuellement réservés
aux superutilisateurs actifs.

Les opérations de modification sont journalisées.

La prévisualisation et l'export ne modifient pas
les données des agents.

## Limites

- Le CSV ne constitue pas une sauvegarde complète.
- Les disponibilités ne sont pas exportées.
- Les dates de validité des qualifications ne sont pas exportées.
- Les qualifications désactivées ne sont pas exportées.
- Les mots de passe et les permissions ne sont pas exportés.
- Les cellules vides de téléphone ou de fonction ne permettent
  pas actuellement d'effacer une valeur existante.
- Les tableurs peuvent supprimer les zéros initiaux.
- La protection CSV ne garantit pas la sécurité dans
  tous les tableurs.
- Les tests de concurrence réelle restent à réaliser.
- La gestion des verrouillages SQLite reste à compléter.
- La politique de purge des confirmations consommées
  et de conservation du journal reste à définir.
- Les interfaces web et API restent à développer.

## Tests automatisés

Les tests métier sont regroupés notamment dans :

- planning.test_import_agents
- planning.test_export_agents
- planning.test_services_agents
- planning.test_services_competences
- planning.test_integrite_donnees
- planning.test_identites
- planning.test_journal

Ces tests utilisent exclusivement des données fictives.
