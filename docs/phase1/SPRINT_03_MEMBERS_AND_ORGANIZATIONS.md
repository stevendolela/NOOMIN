# NOOMIN — Phase 1, Sprint 03 : membres et organisations

**Objectif :** rendre l’organisation active sélectionnable et livrer les premiers outils d’administration des adhésions.  
**État :** implémenté et vérifié.

## Livré

- Sélecteur d’organisation actif dans la navigation, disponible lorsque le compte possède plusieurs organisations.
- API pour lister les adhésions, changer un rôle et retirer une adhésion ; les contrôles d’accès sont appliqués côté serveur.
- Interface « Accès et membres » pour propriétaires et administrateurs.
- Les administrateurs peuvent gérer les rôles Analyste et Lecteur des membres non privilégiés ; seul un propriétaire peut gérer les administrateurs/propriétaires.
- Une organisation doit conserver au moins un propriétaire.
- Retirer une adhésion ne supprime pas le compte utilisateur.
- Test des contrôles de rôle, du retrait d’adhésion et de l’interdiction de retirer le dernier propriétaire.

## Décisions et limites

- L’ajout par invitation e-mail n’est pas implémenté. L’écran l’indique explicitement ; aucun message ni e-mail n’est simulé.
- Aucun changement de schéma : les routes utilisent les tables `users` et `memberships` déjà migrées.
- La gestion des rôles prend effet immédiatement et n’a pas encore de journal d’audit.
- La route de consultation des membres est réservée aux propriétaires et administrateurs.

## Vérification

- Tests API : **17 réussis** sous Python 3.12.14.
- Build frontend, lint et `git diff --check` réussis.
- Un avertissement connu concerne la dépréciation de `Starlette TestClient` avec `httpx`.
