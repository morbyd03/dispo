# Feuille de route de Dispo

Dispo — Déclarer simplement, anticiper collectivement.

Cette feuille de route présente les orientations du projet.
Les versions et leur contenu sont prévisionnels et peuvent
évoluer selon les besoins et les retours des utilisateurs.

## v0.1.0 — Socle initial

Statut : terminée et déployée en production.

- [x] Gestion individuelle des disponibilités.
- [x] Planning collectif hebdomadaire.
- [x] Analyse de la couverture SSUAP et incendie.
- [x] Gestion des agents et des qualifications.
- [x] Activation et réinitialisation des comptes.
- [x] Installation autonome avec Docker Compose.
- [x] Sauvegarde et restauration.
- [x] Documentation et tests automatisés.
- [x] Environnement de préproduction.

## v0.2.0 — Mise en service réelle

Priorité : permettre l'intégration des agents d'un centre.

- [ ] Matricule ou identifiant de connexion.
- [ ] Catalogue des grades et abréviations.
- [ ] Représentations graphiques des galons.
- [ ] Fiches agents enrichies.
- [ ] Annuaire accessible aux agents connectés.
- [ ] Modification des coordonnées avec validation administrative.
- [ ] Définition et documentation du format d'import CSV.
- [ ] Import et export des agents.
- [ ] Import et export des qualifications.
- [ ] Prévisualisation et validation des imports.
- [ ] Activation des comptes en masse.
- [ ] Désactivation des comptes.
- [ ] Limitation des tentatives de connexion.
- [ ] Contrôle des accès aux données personnelles.
- [ ] Journalisation des opérations administratives sensibles.
- [ ] Authentification renforcée des administrateurs.

Les imports ne doivent jamais écraser les mots de passe,
modifier implicitement les droits administratifs ou supprimer
automatiquement les agents absents du fichier.

L'utilisation de données réelles nécessite une validation
préalable des conditions d'hébergement, de sécurité et
de protection des données.

## v0.2.1 — Adoption mobile immédiate

Priorité : faciliter l'accès quotidien à Dispo.

- [ ] Progressive Web App (PWA).
- [ ] Installation sur Android et iOS.
- [ ] Icône sur l'écran d'accueil.
- [ ] Optimisation de l'ergonomie mobile.
- [ ] Connexion persistante, sécurisée et révocable.
- [ ] Guide d'installation destiné aux agents.

## v0.2.2 — Anticipation collective

Priorité : obtenir un mois de visibilité prévisionnelle.

- [ ] Planning mensuel accessible à tous les agents.
- [ ] Horizon de prévision glissant à un mois.
- [ ] Indicateurs de couverture insuffisante, fragile,
      satisfaisante et non évaluée.
- [ ] Marge de couverture configurable.
- [ ] Distinction entre couverture collective et
      déclaration individuelle.
- [ ] Confirmation individuelle des déclarations
      jusqu'à une date choisie.
- [ ] Suivi administratif des déclarations manquantes.

Une couverture satisfaisante ne dispense jamais
un agent de renseigner ses disponibilités.

## v0.3.0 — Clients mobiles Android et iOS

Priorité : favoriser durablement l'adoption.

- [ ] API REST sécurisée et documentée.
- [ ] Authentification adaptée aux clients mobiles.
- [ ] Application Android.
- [ ] Application iOS.
- [ ] Configuration de l'adresse du serveur.
- [ ] Notifications push.
- [ ] Étude des modalités de distribution.
- [ ] Authentification à deux facteurs des agents.

## v0.3.1 — Faciliter les déclarations

- [ ] Disponibilités récurrentes.
- [ ] Gestion des exceptions aux récurrences.
- [ ] Déclaration rapide sur plusieurs semaines.
- [ ] Identification personnalisée des besoins de renfort.
- [ ] Rappels mensuels configurables.
- [ ] Relances individuelles ciblées.

Les relances doivent encourager la participation
sans culpabiliser les agents.

## v0.4.0 — Préparation NEXSIS

- [ ] Vue administrative dédiée au report des disponibilités.
- [ ] Filtres par période et par agent.
- [ ] Export des créneaux prévisionnels.
- [ ] Suivi des disponibilités déjà reportées.
- [ ] Détection des modifications après report.
- [ ] Détection des suppressions après report.
- [ ] Historique des modifications.

Dispo ne remplace pas NEXSIS.
Le report manuel reste le fonctionnement de référence.

## v0.5.0 — Personnalisation opérationnelle

- [ ] Types de disponibilité configurables.
- [ ] Étude des statuts Garde, A1, D1, D2, Conventionné.
- [ ] Analyse de la couverture FDF.
- [ ] Règles de couverture personnalisables.
- [ ] Statistiques prévisionnelles.
- [ ] Suivi des échéances des qualifications.
- [ ] Étude des possibilités d'interopérabilité avec NEXSIS.

## Sujets métier restant à étudier

- Signification et incidence opérationnelle des différents
  types de disponibilité selon les SDIS.
- Modalités concrètes de report des disponibilités dans NEXSIS.
- Formats d'export éventuellement disponibles ou autorisés.
- Définition précise des marges de couverture.
- Modalités de distribution des applications mobiles.

## Principes de développement

Chaque évolution significative suit un cycle comprenant :

1. Définition du besoin.
2. Développement sur une branche dédiée.
3. Tests automatisés.
4. Validation en préproduction.
5. Pull Request et revue.
6. Publication d'une version.
7. Déploiement en production.

La sécurité, la confidentialité, l'accessibilité,
la documentation et la maintenabilité sont des
exigences transversales à toutes les versions.

Consulter également [la vision du projet](docs/VISION.md).
