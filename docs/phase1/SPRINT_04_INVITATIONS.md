# NOOMIN — Phase 1, Sprint 04 : invitations par lien

**Objectif :** rattacher de nouveaux comptes à une organisation via un lien d’invitation sécurisé.  
**État :** implémenté et vérifié.

## Livré

- Migration Alembic `0006_organization_invitations` et modèle de stockage des invitations.
- Création d’invitations réservée aux propriétaires/administrateurs, avec contrôle du rôle attribuable.
- Jeton aléatoire à usage unique ; seule son empreinte SHA-256 est stockée en base.
- Expiration après 7 jours, consultation sans cache, acceptation unique et révocation par les gestionnaires autorisés.
- Nouveau compte invité créé avec Argon2id et rattaché à l’organisation avec le rôle prévu ; une personne ayant déjà un compte doit être connectée sur ce compte.
- Interface d’administration pour créer un lien, le copier, voir les invitations en attente et les révoquer.
- Lien transmis en fragment URL, pour éviter qu’il soit envoyé dans l’en-tête HTTP Referer.
- Tests pour la création, l’acceptation, l’usage unique, l’expiration et l’interdiction pour un administrateur d’accorder un rôle admin/propriétaire.

## Limites

- NOOMIN n’envoie pas d’e-mail : le gestionnaire transmet le lien manuellement.
- Le lien secret est affiché à sa création seulement. S’il est perdu, il faut révoquer l’invitation et en créer une nouvelle.
- Pas de vérification de boîte e-mail, audit des invitations ou limitation de débit.
- Le parcours de migration PostgreSQL est écrit ; aucun service PostgreSQL/Docker réel n’était disponible dans cette validation.

## Vérification

- Tests API : **20 réussis** sous Python 3.12.14.
- Build frontend, lint et `git diff --check` réussis.
- Un avertissement connu concerne la dépréciation de `Starlette TestClient` avec `httpx`.
