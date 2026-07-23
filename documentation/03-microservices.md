# 3. Description des microservices

Chaque service suit le principe **database per service** : il est l'unique propriétaire de ses données ; les autres services n'y accèdent que via son API ou ses événements. Les modèles de données détaillés des trois services clés sont illustrés ci-dessous.

![Modèles de données simplifiés](diagrams/modele-donnees.png)

---

## 3.1 Service Client

|                     |                                                                                                                                                           |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Inscription, authentification (émission de JWT), profil, adresses de livraison, consultation de l'historique de commandes (par appel au service Commande) |
| **Base de données** | PostgreSQL `clients_db`                                                                                                                                   |
| **Expose**          | REST `/v1/clients`, `/v1/auth`                                                                                                                            |
| **Publie**          | `client.cree`, `client.modifie`                                                                                                                           |

**Modèle principal** : `clients` (id UUID, email unique, hash mot de passe, nom, téléphone), `adresses` (id, client_id FK, libellé, rue, ville, code postal, géolocalisation, par défaut O/N).

## 3.2 Service Restaurant

|                     |                                                                                                                                            |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Profil restaurant, menus/plats/options, horaires d'ouverture, **acceptation ou refus des commandes**, suivi des commandes en préparation   |
| **Base de données** | MongoDB `restaurants_db` — le menu complet est un **agrégat documentaire unique** (lecture en une requête, schéma flexible par restaurant) |
| **Expose**          | REST `/v1/restaurants`, `/v1/restaurants/{id}/menus`, `/v1/restaurants/{id}/commandes`                                                     |
| **Consomme**        | `restaurant.acceptation.demandee` (étape de la SAGA)                                                                                       |
| **Publie**          | `order.acceptee`, `order.refusee`, `order.prete`, `menu.mis-a-jour`                                                                        |

**Modèle principal** : collection `restaurants` — document contenant identité, adresse + géolocalisation, type de cuisine, horaires, et `menus[] → plats[]` (libellé, description, prix, options, disponibilité).

## 3.3 Service Catalogue

|                     |                                                                                                                                                |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Recherche de restaurants par localisation / type de cuisine, recherche de plats, affichage des menus — **read model dénormalisé** (CQRS léger) |
| **Base de données** | MongoDB `catalogue_db` (index géospatial + texte) et cache Redis (résultats chauds, TTL 60 s)                                                  |
| **Expose**          | REST `/v1/catalogue/restaurants?lat=&lng=&cuisine=&q=`                                                                                         |
| **Consomme**        | `menu.mis-a-jour`, `restaurant.ouvert/ferme` (projection)                                                                                      |

Le catalogue peut être **entièrement reconstruit** à partir des événements du service Restaurant : la perte de sa base n'est pas critique.

## 3.4 Service Commande — cœur du système

|                       |                                                                                                                                                                                                                            |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités**   | Panier, création de commande, calcul du prix total (plats + frais de livraison), gestion du cycle de vie (`RECUE → EN_PREPARATION → EN_LIVRAISON → LIVREE / ANNULEE`), **orchestration de la SAGA** de passage de commande |
| **Base de données**   | PostgreSQL `commandes_db`                                                                                                                                                                                                  |
| **Expose* *           | REST `/v1/commandes` (voir [contrat OpenAPI](api/order-service.openapi.yaml))                                                                                                                                              |
| **Appelle (sync)**    | Service Paiement (autorisation, capture, remboursement) — protégé par circuit breaker                                                                                                                                      |
| **Publie / consomme** | Commandes et événements de la SAGA (voir [06-coherence-saga.md](06-coherence-saga.md))                                                                                                                                     |

**Modèle principal** : `orders`, `order_items` (lignes figées : libellé et prix copiés au moment de l'achat), `saga_state` (étape courante et statut de chaque SAGA) et `outbox_events` (pattern **Transactional Outbox** : l'événement est écrit dans la même transaction que l'état, puis publié vers RabbitMQ par un relai).

## 3.5 Service Paiement

|                     |                                                                                                                                                             |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Façade vers le PSP externe (Stripe simulé) : **autorisation** à la commande, **capture** à la livraison, **remboursement total ou partiel** en compensation |
| **Base de données** | PostgreSQL `paiements_db`                                                                                                                                   |
| **Expose**          | REST interne `/v1/paiements` (non exposé via le gateway ; consommé uniquement par le service Commande)                                                      |
| **Publie**          | `paiement.autorise`, `paiement.capture`, `paiement.rembourse`, `paiement.refuse`                                                                            |

**Modèle principal** : `paiements` (id, order_id, montant, statut `AUTORISE / CAPTURE / REMBOURSE / REFUSE`, référence PSP, horodatages). Les données de carte **ne transitent jamais** par notre système (tokenisation côté PSP).

## 3.6 Service Livraison

|                     |                                                                                                                                                                                                                              |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Suivi des **courses** : création d'une livraison lorsque la commande est prête, demande d'affectation d'un livreur (déléguée au service Livreur), suivi de position en temps réel, confirmation de remise ou constat d'échec |
| **Base de données** | MongoDB `delivery_db`                                                                                                                                                                                                        |
| **Expose**          | REST `/deliveries` (création, détail, `PATCH /deliveries/{id}/location`, `POST /deliveries/{id}/confirm` / `/fail`), `/orders/{order_id}/delivery` — port 8005 (voir [contrat OpenAPI](api/delivery-service.openapi.yaml))   |
| **Appelle (sync)**  | Service Livreur : `POST /deliverers/assign` à la création de la course, `POST /deliverers/{id}/release` à la remise ou en cas d'échec                                                                                        |
| **Consomme**        | `order.ready` (une commande prête déclenche la création de la course)                                                                                                                                                        |
| **Publie**          | `delivery.assigned`, `delivery.in_transit`, `delivery.completed`, `delivery.failed`                                                                                                                                          |

**Modèle principal** : `deliveries` (order_id en référence externe, deliverer_id + deliverer_name **copiés au moment de l'affectation**, customer_id, restaurant_id, statut `PENDING → ASSIGNED → PICKED_UP → DELIVERED / FAILED`, position courante, horodatages). Le livreur n'y figure que comme référence : la flotte appartient au service Livreur.

## 3.7 Service Livreur

|                     |                                                                                                                                                                                                                            |
|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Gestion de la **flotte** : enregistrement des livreurs, gestion de la disponibilité, affectation du premier livreur disponible et libération en fin de course — **source de vérité unique de la disponibilité**            |
| **Base de données** | MongoDB `deliverer_db`                                                                                                                                                                                                     |
| **Expose**          | REST `/deliverers` (enregistrement, liste, détail), `PATCH /deliverers/{id}/availability`, `POST /deliverers/assign` / `/deliverers/{id}/release` — port 8009 (voir [contrat OpenAPI](api/deliverer-service.openapi.yaml)) |
| **Publie**          | `deliverer.registered`, `deliverer.availability_changed`                                                                                                                                                                   |

**Modèle principal** : `deliverers` (id, nom, téléphone, véhicule `BIKE / SCOOTER / CAR`, statut `AVAILABLE / BUSY / OFFLINE`, position, horodatages). Seul ce service modifie le statut d'un livreur ; le service Livraison n'interagit avec la flotte que via les deux appels idempotents `assign` / `release` (justification du découpage en [section 2.5](02-analyse-domaine.md)).

## 3.8 Service Notation

|                     |                                                                                                |
|---------------------|------------------------------------------------------------------------------------------------|
| **Responsabilités** | Dépôt et consultation d'avis : client → restaurant et client → livreur ; calcul des moyennes   |
| **Base de données** | MongoDB `notations_db`                                                                         |
| **Expose**          | REST `/v1/notations`                                                                           |
| **Consomme**        | `order.livree` (autorise la notation d'une commande réellement livrée)                         |
| **Publie**          | `notation.deposee` (permet aux services Restaurant/Livreur de mettre à jour leur note moyenne) |

**Modèle principal** : collection `avis` (order_id, auteur, cible restaurant|livreur, note 1–5, commentaire, date). Un avis n'est accepté que si la commande est passée à l'état LIVREE (règle vérifiée par projection locale des événements).

## 3.9 Service Notification

|                     |                                                                                                                       |
|---------------------|-----------------------------------------------------------------------------------------------------------------------|
| **Responsabilités** | Envoi des notifications aux clients, restaurateurs et livreurs sur trois canaux : email, push (simulé), SMS (simulé)  |
| **Base de données** | Aucune (stateless) — journalisation console/logs pour la démo                                                         |
| **Consomme**        | Tous les événements métier pertinents (`order.*`, `delivery.*`, `paiement.*`) via une file dédiée sur l'échange topic |

Service purement réactif : ajouter un canal ou un destinataire ne modifie aucun autre service.

---

## Récapitulatif

| Service      | BDD             | Sync (expose)                      | Async (publie)                       | Async (consomme)                |
|--------------|-----------------|------------------------------------|--------------------------------------|---------------------------------|
| Client       | PostgreSQL      | /v1/clients, /v1/auth              | client.*                             | —                               |
| Restaurant   | MongoDB         | /v1/restaurants                    | order.acceptee/refusee/prete, menu.* | restaurant.acceptation.demandee |
| Catalogue    | MongoDB + Redis | /v1/catalogue                      | —                                    | menu.*, restaurant.*            |
| Commande     | PostgreSQL      | /v1/commandes                      | order.*, cmds SAGA                   | order.*, delivery.*, paiement.* |
| Paiement     | PostgreSQL      | /v1/paiements (interne)            | paiement.*                           | —                               |
| Livraison    | MongoDB         | /deliveries, /orders/{id}/delivery | delivery.*                           | order.ready                     |
| Livreur      | MongoDB         | /deliverers                        | deliverer.*                          | —                               |
| Notation     | MongoDB         | /v1/notations                      | notation.deposee                     | order.livree                    |
| Notification | —               | —                                  | —                                    | tous les événements             |
