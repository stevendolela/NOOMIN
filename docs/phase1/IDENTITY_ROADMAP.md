# NOOMIN — MFA et connexion aux annuaires clients

**Statut :** exigences enregistrées pour une prochaine étape ; aucune fonction MFA ou SSO n’est encore implémentée.

## Décision produit

L’authentification est gérée par utilisateur, tandis que les exigences d’accès fédéré sont configurées par organisation. NOOMIN reste multi-tenant : après authentification, chaque requête conserve les contrôles d’adhésion et de permissions de l’organisation sélectionnée.

## MFA géré par NOOMIN

- Ajouter une option MFA TOTP avec applications d’authentification, codes de récupération à usage unique et procédure de remplacement/révocation de facteur.
- Prévoir une politique permettant à une organisation d’exiger le MFA pour ses membres, tout en gardant une voie sécurisée de récupération pour ses administrateurs.
- Ne pas utiliser le SMS comme mécanisme MFA de première intention.
- Chiffrer les secrets TOTP au repos ; ne jamais les exposer après l’activation. Hasher les codes de récupération et les invalider après usage.
- Réduire les risques de contournement : connexion, récupération de compte, invitations et changement d’e-mail doivent respecter l’état MFA.
- Garder l’authentification extensible pour ajouter des passkeys/WebAuthn plus tard.

## Annuaire et SSO d’entreprise

- Permettre à chaque organisation de configurer son propre fournisseur d’identité et de rattacher les connexions fédérées à cette organisation.
- Privilégier OpenID Connect pour une nouvelle intégration ; proposer SAML 2.0 quand le client ou son fournisseur l’exige.
- Prendre Microsoft Entra ID en charge en premier pour les clients dont l’Active Directory est synchronisé ou fédéré avec Entra. Prendre en charge AD FS via fédération SAML si un client utilise un Active Directory local.
- Ne pas ouvrir une connexion LDAP entrante directe depuis NOOMIN vers le réseau du client. L’authentification passe par un fournisseur d’identité fédéré.
- Valider l’émetteur, l’audience, les signatures, les états/nonce et les URLs de redirection ; vérifier et documenter les métadonnées/certificats IdP.
- Prévoir la validation de domaine et l’association contrôlée des identités externes aux membres existants afin d’éviter les prises de compte par collision d’adresse.
- Laisser l’IdP client appliquer sa politique MFA lorsque SSO est activé ; ne pas présumer qu’un login fédéré signifie MFA sans signal vérifié de l’IdP.
- Définir ultérieurement le provisioning/déprovisioning (SCIM ou procédure manuelle), les règles d’accès pour les invités, et un compte d’urgence contrôlé.

## Ordre de livraison proposé

1. MFA TOTP optionnel par compte, codes de récupération, révocation de sessions et tests des parcours de récupération.
2. Politique MFA obligatoire par organisation et tests de non-contournement.
3. SSO OIDC pour une organisation pilote Microsoft Entra ID, avec configuration tenant-scoped et audit.
4. SAML 2.0/AD FS si confirmé par les besoins clients ; provisioning SCIM après le premier pilote fédéré.

## Références de conception

- OWASP recommande notamment de protéger les secrets TOTP, de traiter la récupération comme un parcours d’authentification sensible et d’éviter qu’elle contourne le MFA : [OWASP Multifactor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).
- Microsoft documente OpenID Connect et SAML comme options de SSO, avec SAML fréquemment utilisé avec AD FS : [Microsoft identity platform — authentication scenarios](https://learn.microsoft.com/en-us/azure/active-directory/active-directory-authentication-scenarios).
- Pour les nouvelles applications d’entreprise, Microsoft recommande OIDC par défaut et accepte SAML pour les intégrations d’entreprise existantes : [Plan SSO integration with Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/plan-sso-integration-isv).
