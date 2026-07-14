# 5. Contrats d'API des services clés

Les trois services au cœur du processus critique (passage de commande) sont documentés en **OpenAPI 3.0** dans le dossier [`api/`](api/). Ces fichiers sont la **source de vérité** des contrats : ils sont versionnés avec le code et servent de base aux tests de contrat. Avec FastAPI, la documentation Swagger UI de chaque service est générée automatiquement et doit rester conforme à ces contrats.

| Service | Contrat | Visibilité |
|---------|---------|------------|
| Commande | [`commande-service.openapi.yaml`](api/commande-service.openapi.yaml) | Public (via gateway) |
| Paiement | [`paiement-service.openapi.yaml`](api/paiement-service.openapi.yaml) | **Interne** (réseau Docker uniquement) |
| Restaurant | [`restaurant-service.openapi.yaml`](api/restaurant-service.openapi.yaml) | Public (via gateway) |

> Astuce : ouvrir ces fichiers dans [editor.swagger.io](https://editor.swagger.io) pour une vue interactive.

## 5.1 Endpoints principaux

### Service Commande (`/v1/commandes`)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| POST | `/commandes` | Créer une commande — **démarre la SAGA** (idempotent via `Idempotency-Key`) |
| GET | `/commandes` | Lister les commandes du client (pagination, filtre par statut) |
| GET | `/commandes/{id}` | Détail + état de suivi (`RECUE`, `EN_PREPARATION`, `EN_LIVRAISON`, `LIVREE`, `ANNULEE`) |
| POST | `/commandes/{id}/annulation` | Annulation client (possible avant acceptation restaurant) |
| GET | `/commandes/{id}/evenements` | Historique des événements de la SAGA (suivi/audit) |

Codes notables : `503 + Retry-After` quand le circuit breaker du paiement est ouvert (fallback : commande conservée en `EN_ATTENTE_PAIEMENT`) ; `409` sur conflit de clé d'idempotence ; `422` si l'annulation n'est plus possible.

### Service Paiement (`/v1/paiements`, interne)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| POST | `/paiements` | **Autorisation** (fonds réservés) — étape 2 de la SAGA |
| GET | `/paiements/{id}` | Consultation |
| POST | `/paiements/{id}/capture` | **Capture** à la livraison — fin de SAGA |
| POST | `/paiements/{id}/remboursement` | **Compensation** (total ou partiel, avec motif) |

Toutes les écritures exigent `Idempotency-Key` : un retry (voir [résilience](07-resilience.md)) ne peut jamais débiter deux fois. Le `402` signale un refus PSP (déclenche l'annulation de la commande), le `504` un PSP injoignable (déclenche retry/circuit breaker côté appelant).

### Service Restaurant (`/v1/restaurants`)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| POST / PUT | `/restaurants`, `/restaurants/{id}` | Inscription et profil (horaires…) |
| GET | `/restaurants/{id}` | Consultation publique (profil + menus) |
| PUT | `/restaurants/{id}/menus` | Remplacement atomique des menus → publie `menu.mis-a-jour` |
| GET | `/restaurants/{id}/commandes` | Tickets de commande du restaurateur |
| POST | `/restaurants/{id}/commandes/{orderId}/decision` | **Accepter/refuser** une commande — étape 3 de la SAGA |
| POST | `/restaurants/{id}/commandes/{orderId}/prete` | Signaler la commande prête → déclenche l'affectation livreur |

## 5.2 Conventions communes

- **Authentification** : JWT (émis par le service Client) validé au gateway ; schéma `bearerAuth` dans les contrats.
- **Format d'erreur uniforme** : `{ "code": "...", "message": "...", "details": {} }` — les codes d'erreur métier sont stables et documentés par endpoint.
- **Idempotence** : en-tête `Idempotency-Key` (UUID) obligatoire sur toutes les écritures rejouables par la SAGA ou par un retry.
- **Identifiants** : UUID partout ; les références inter-services (`orderId`, `clientId`…) sont opaques, sans clé étrangère.
- **Versioning** : préfixe `/v1` ; politique détaillée dans [04-communication.md](04-communication.md#45-versioning-et-compatibilité-ascendante).
