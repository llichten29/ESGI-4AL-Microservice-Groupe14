# 5. Contrats d'API

Chacun des dix services de la plateforme est documenté en **OpenAPI 3.0.3** par un contrat dédié. La **source de vérité** de ces contrats est le dossier `services/ressources/endpoints/` : les fichiers y sont versionnés avec le code, copiés dans chaque image Docker et **chargés par les services au démarrage**. Le dossier [`api/`](api/) de la documentation en est un miroir à l'identique.

| Service              | Contrat                                                                      | Port | Visibilité                     |
|----------------------|------------------------------------------------------------------------------|------|--------------------------------|
| API Gateway          | [`api-gateway.openapi.yaml`](api/api-gateway.openapi.yaml)                   | 8000 | Public (point d'entrée unique) |
| Commande (order)     | [`order-service.openapi.yaml`](api/order-service.openapi.yaml)               | 8001 | Public (via gateway)           |
| Restaurant           | [`restaurant-service.openapi.yaml`](api/restaurant-service.openapi.yaml)     | 8002 | Public (via gateway)           |
| Catalogue (catalog)  | [`catalog-service.openapi.yaml`](api/catalog-service.openapi.yaml)           | 8003 | Public (via gateway)           |
| Paiement (payment)   | [`payment-service.openapi.yaml`](api/payment-service.openapi.yaml)           | 8004 | Public (via gateway)           |
| Livraison (delivery) | [`delivery-service.openapi.yaml`](api/delivery-service.openapi.yaml)         | 8005 | Public (via gateway)           |
| Notification         | [`notification-service.openapi.yaml`](api/notification-service.openapi.yaml) | 8006 | Public (via gateway)           |
| Notes (rating)       | [`rating-service.openapi.yaml`](api/rating-service.openapi.yaml)             | 8007 | Public (via gateway)           |
| Client (customer)    | [`customer-service.openapi.yaml`](api/customer-service.openapi.yaml)         | 8008 | Public (via gateway), JWT      |
| Livreur (deliverer)  | [`deliverer-service.openapi.yaml`](api/deliverer-service.openapi.yaml)       | 8009 | Public (via gateway)           |

> Astuce : ouvrir ces fichiers dans [editor.swagger.io](https://editor.swagger.io) pour une vue interactive, ou consulter directement `http://localhost:8000/docs` (Swagger UI servi par le gateway).

## 5.1 Comment le code utilise les contrats

Les contrats ne sont pas seulement documentaires : ils pilotent le comportement des services à l'exécution.

### Validation des requêtes (tous les services métier)

Le module partagé `services/main/shared/openapi_validator.py` est branché dans la factory `create_app()` de chacun des neuf services métier :

```python
from main.shared.openapi_validator import register_openapi_validation
register_openapi_validation(app, service_name="order-service")
```

Au démarrage, le module charge le contrat du service (`services/ressources/endpoints/<service>.openapi.yaml`, surchargable par la variable d'environnement `OPENAPI_SPEC_PATH`), inline les `$ref` et compile un index des opérations. Un hook Flask `before_request` valide ensuite chaque requête entrante :

- corps JSON absent alors que `requestBody.required: true` → `400 INVALID_INPUT` ;
- corps JSON non conforme au schéma (champ requis manquant, type erroné, borne violée) → `400 SCHEMA_VALIDATION_FAILED` ;
- paramètre de query requis manquant → `400 MISSING_PARAMETER` ;
- route absente du contrat → laissée passer (le mode `strict=True` renvoie `404 ROUTE_NOT_IN_CONTRACT`).

Chaque service expose aussi son contrat sur `GET /openapi.yaml`. Si le fichier de contrat est introuvable, le service démarre sans validation (avertissement dans les logs) : la validation ne peut jamais empêcher un service de démarrer.

### Table de routage du gateway

L'API Gateway construit sa table de routage au démarrage **à partir des mêmes contrats** : il parcourt `services/ressources/endpoints/*.openapi.yaml` (répertoire surchargable par `OPENAPI_SPEC_DIR`), et pour chaque opération, le premier `tag` (`Orders`, `Payments`, `Customers`…) désigne le service cible via sa variable d'environnement `*_SERVICE_URL`. Les chemins propres à chaque service (`/health`, `/openapi.yaml`) sont exclus du routage.

Le gateway sert également sur `GET /openapi.yaml` une **spécification agrégée** de la plateforme, construite en mémoire par fusion des dix contrats, et navigable sur `GET /docs` (Swagger UI). Ajouter un endpoint dans un contrat suffit donc à le rendre routable et documenté au niveau du gateway.

## 5.2 Conventions communes

- **Format d'erreur uniforme** : `{ "error": { "code": "...", "message": "..." } }` — les codes d'erreur métier (`ORDER_NOT_FOUND`, `PAYMENT_DECLINED`, `INVALID_SCORE`…) sont stables et documentés par endpoint.
- **Authentification** : JWT uniquement sur customer-service (schéma `bearerAuth` dans son contrat) ; jeton émis par `/customers/register` et `/customers/login`. Les autres services communiquent en interne sur le réseau Docker.
- **Nommage** : les chemins et champs reflètent le code implémenté — camelCase pour order-service et catalog-service, snake_case pour les autres services.
- **Tags** : le premier tag de chaque opération est significatif ; il est utilisé par le gateway pour le routage (`Customers`, `Restaurants`, `Catalog`, `Orders`, `Payments`, `Deliveries`, `Deliverers`, `Notifications`, `Ratings`).
- **Santé** : chaque service expose `GET /health` → `{ "status": "healthy", "service": "<nom>" }`.
- **Codes notables** : `422` pour les violations de règles métier (`INVALID_ORDER`, `CANCELLATION_NOT_ALLOWED`, `INVALID_SCORE`), `402` pour un paiement refusé, `502` pour une passerelle de paiement injoignable, `503` quand le circuit breaker restaurant est ouvert (voir [résilience](07-resilience.md)).

## 5.3 Endpoints principaux par service

### API Gateway (8000)

| Méthode | Chemin                       | Rôle                                                 |
|---------|------------------------------|------------------------------------------------------|
| GET     | `/orders/{order_id}/details` | Agrégation commande + nom/localisation du restaurant |
| GET     | `/docs`                      | Swagger UI de la plateforme                          |
| GET     | `/openapi.yaml`              | Spécification agrégée                                |
| *       | `/*`                         | Proxy vers le service désigné par les contrats       |

### Commande — order-service (8001)

| Méthode | Chemin                            | Rôle                                                       |
|---------|-----------------------------------|------------------------------------------------------------|
| POST    | `/orders`                         | Créer une commande — **démarre la SAGA**                   |
| GET     | `/orders/{order_id}`              | Détail d'une commande                                      |
| DELETE  | `/orders/{order_id}`              | Annulation (statuts CREATED/PAID, déclenche remboursement) |
| GET     | `/customers/{customer_id}/orders` | Commandes d'un client                                      |
| GET     | `/orders/{order_id}/saga`         | État et historique de la SAGA                              |
| GET     | `/orders/circuit-breakers`        | État des circuit breakers                                  |

### Restaurant — restaurant-service (8002)

| Méthode                   | Chemin                                                    | Rôle                                         |
|---------------------------|-----------------------------------------------------------|----------------------------------------------|
| POST / GET                | `/restaurants`                                            | Inscription et liste                         |
| GET / PUT                 | `/restaurants/{restaurant_id}`                            | Profil                                       |
| GET / POST / PUT / DELETE | `/restaurants/{id}/menus[/{menu_id}[/items[/{item_id}]]]` | Gestion des menus et articles                |
| POST                      | `/restaurants/{id}/validate`                              | Validation d'une commande — étape de la SAGA |
| POST                      | `/restaurants/{id}/orders/{order_id}/accept` / `/reject`  | Décision du restaurateur                     |
| PATCH                     | `/restaurants/{id}/orders/{order_id}/status`              | Statut de préparation                        |

### Catalogue — catalog-service (8003)

| Méthode | Chemin                | Rôle                                                                         |
|---------|-----------------------|------------------------------------------------------------------------------|
| GET     | `/restaurants/search` | Recherche de restaurants (query, cuisineType, isOpen, minRating, pagination) |
| GET     | `/dishes/search`      | Recherche de plats                                                           |

### Paiement — payment-service (8004)

| Méthode | Chemin                          | Rôle                                              |
|---------|---------------------------------|---------------------------------------------------|
| POST    | `/payments`                     | Traitement d'un paiement — étape de la SAGA       |
| GET     | `/payments/{payment_id}`        | Consultation                                      |
| GET     | `/orders/{order_id}/payment`    | Paiement d'une commande                           |
| POST    | `/payments/{payment_id}/refund` | **Compensation** (remboursement total ou partiel) |

### Livraison — delivery-service (8005)

| Méthode | Chemin                                                      | Rôle                                              |
|---------|-------------------------------------------------------------|---------------------------------------------------|
| POST    | `/deliveries`                                               | Création d'une course et affectation d'un livreur |
| GET     | `/deliveries/{delivery_id}` / `/orders/{order_id}/delivery` | Suivi                                             |
| PATCH   | `/deliveries/{delivery_id}/location`                        | Position du livreur                               |
| POST    | `/deliveries/{delivery_id}/confirm` / `/fail`               | Issue de la course                                |

### Notification — notification-service (8006)

Service piloté par les événements RabbitMQ ; API HTTP en lecture seule : `GET /notifications` (filtres `recipient_id`, `type`) et `GET /notifications/{notification_id}`.

### Notes — rating-service (8007)

| Méthode | Chemin                                                | Rôle                                              |
|---------|-------------------------------------------------------|---------------------------------------------------|
| POST    | `/ratings`                                            | Créer une note (score 1 à 5)                      |
| GET     | `/ratings/{rating_id}`                                | Détail                                            |
| GET     | `/ratings/target/{target_type}/{target_id}[/summary]` | Notes et synthèse d'un restaurant ou d'un livreur |

### Client — customer-service (8008)

| Méthode                   | Chemin                                     | Rôle                                       |
|---------------------------|--------------------------------------------|--------------------------------------------|
| POST                      | `/customers/register` / `/customers/login` | Inscription et connexion (émission du JWT) |
| GET / PUT                 | `/customers/profile`                       | Profil du client connecté                  |
| GET / POST / PUT / DELETE | `/customers/addresses[/{address_id}]`      | Carnet d'adresses                          |
| GET                       | `/customers/orders`                        | Historique léger des commandes             |

### Livreur — deliverer-service (8009)

| Méthode    | Chemin                                                      | Rôle                                     |
|------------|-------------------------------------------------------------|------------------------------------------|
| POST / GET | `/deliverers`                                               | Enregistrement et liste                  |
| GET        | `/deliverers/{deliverer_id}`                                | Détail                                   |
| PATCH      | `/deliverers/{deliverer_id}/availability`                   | Disponibilité (AVAILABLE, BUSY, OFFLINE) |
| POST       | `/deliverers/assign` / `/deliverers/{deliverer_id}/release` | Affectation et libération                |
