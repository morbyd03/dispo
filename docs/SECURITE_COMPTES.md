# Securite des comptes Dispo

## Architecture

Dispo conserve les comptes utilisateurs, les sessions
et les mecanismes cryptographiques natifs de Django.

Le modele SecuriteCompte, introduit par la migration
0018, ajoute une version de securite independante
du profil operationnel.

Un compte sans enregistrement de securite possede
implicitement la version initiale 0.

## Revocation des acces

Le service revoquer_acces_compte incremente la version
de securite directement en base de donnees.

Les changements effectifs de statut realises par
le service modifier_statut_agent declenchent
automatiquement cette revocation.

Une desactivation suivie d'une reactivation ne
restaure pas les anciennes autorisations de session.

Le mot de passe, les disponibilites et les qualifications
sont conserves.

## Sessions

La version de securite est enregistree lors de la
connexion de l'utilisateur.

Un middleware controle ensuite cette version lors
des requetes authentifiees.

Une session obsolete ou depourvue de version est
invalidee.

La revocation intervient lors de la prochaine requete.
Elle n'interrompt pas une requete deja en cours.

## Activation et reinitialisation

Le generateur de jetons etend celui de Django avec :

- La version de securite du compte.
- Le statut actif du compte.

Les liens d'activation, de reinitialisation administrative
et de mot de passe oublie utilisent ce generateur commun.

Les protections natives de Django sont conservees,
notamment la duree de validite des jetons.

Les anciens liens restent invalides apres reactivation.

Un formulaire de reinitialisation deja ouvert ne permet
pas de contourner une revocation ulterieure.

## Changement de mot de passe

Le changement de mot de passe personnel conserve
la session courante en cas de succes.

Les autres sessions et anciens liens de reinitialisation
sont invalides par les mecanismes de Django.

L'utilisateur et son etat de securite sont verifies
a nouveau dans la transaction avant modification.

## Transactions

SQLite utilise le mode IMMEDIATE avec un delai
de verrouillage de 20 secondes.

Les transactions automatiques globales par requete
HTTP ne sont pas activees.

Les connexions fonctionnelles et techniques,
la reinitialisation et le changement personnel de
mot de passe utilisent des transactions ciblees.

En cas d'erreur operationnelle, une reponse HTTP 503
est retournee et une deconnexion preventive est tentee.

Les transactions IMMEDIATE serialisent les transactions
d'ecriture mais peuvent aussi reserver un verrou
lors d'une transaction de lecture explicite.

## Consequences du deploiement

Lors du deploiement de cette evolution :

- La migration 0018 doit etre appliquee.
- Les anciennes sessions deviennent invalides.
- Les utilisateurs doivent se reconnecter.
- Les anciens liens d'activation et de reinitialisation
  doivent etre renouveles.

Les mots de passe existants restent utilisables.

## Validation

Bilan local du 28 novembre 2026 :

- 616 tests recenses.
- 612 tests reussis dans la suite standard.
- 3 tests de concurrence Django ignores dans cette suite
  et valides separement sur une base SQLite sur disque.
- 1 test historique d'affichage suspendu.
- Aucun echec ni erreur dans la suite standard.

Les tests de concurrence sont integres au workflow
GitHub avec une configuration dediee.

## Limites et travaux restants

- Les changements directs de statut des comptes techniques
  depuis Django Admin ne declenchent pas encore
  automatiquement la revocation par version.
- Une indisponibilite de la base peut empecher la
  suppression persistante d'une session.
- Les tests concurrents valident le moteur SQLite et
  le service de revocation, pas tous les parcours HTTP
  simultanes.
- Les requetes deja autorisees et en cours ne sont
  pas systematiquement interrompues par une revocation.
- La limitation des tentatives de connexion et des
  demandes de courriels reste a implementer.
- La connexion par matricule ou adresse electronique
  reste a finaliser.
- La gestion securisee des changements d'adresse
  electronique reste a implementer.
- La politique de conservation des journaux reste
  a definir.
- Le test TestsAffichageDiagnostics doit etre adapte
  ou reactive avant la publication de la v0.2.0.

La validation locale ne constitue pas un audit
de securite exhaustif.
