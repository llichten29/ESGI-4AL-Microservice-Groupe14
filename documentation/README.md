# Documentation d'architecture — DashEat

> Projet ESGI 4AL — Architecture Microservices — Groupe 14

Cette documentation décrit la conception de **DashEat**, une architecture microservices pour une plateforme de livraison de repas de type Uber Eats / Deliveroo, conformément à l'énoncé du projet (`Enonce projet.pdf`).

## Sommaire

| # | Document | Contenu |
|---|----------|---------|
| 1 | [Architecture générale](01-architecture-generale.md) | Description générale de l'architecture proposée, vue d'ensemble, Clean Architecture des services, stack technique |
| 2 | [Analyse du domaine](02-analyse-domaine.md) | Analyse DDD, Bounded Contexts et justification du découpage en microservices |
| 3 | [Microservices](03-microservices.md) | Description de chaque microservice : responsabilités et modèle de données principal |
| 4 | [Communication inter-services](04-communication.md) | Patterns de communication synchrone (REST) et asynchrone (RabbitMQ), versioning |
| 5 | [Contrats d'API](05-contrats-api.md) | Contrats OpenAPI 3 des dix services et validation des requêtes à l'exécution |
| 6 | [Cohérence & SAGA](06-coherence-saga.md) | Stratégie de gestion de la cohérence et SAGA orchestrée du passage de commande |
| 7 | [Résilience](07-resilience.md) | Points de défaillance et patterns Circuit Breaker, Retry, Timeout, Fallback |

## Architecture Decision Records (ADRs)

| ADR | Décision |
|-----|----------|
| [ADR-001](adr/ADR-001-architecture-microservices-ddd.md) | Adopter une architecture microservices découpée selon les Bounded Contexts (DDD) |
| [ADR-002](adr/ADR-002-database-per-service-polyglotte.md) | Une base de données par service, avec persistance polyglotte |
| [ADR-003](adr/ADR-003-communication-rest-et-rabbitmq.md) | REST synchrone + événements asynchrones via RabbitMQ |
| [ADR-004](adr/ADR-004-saga-orchestration.md) | SAGA orchestrée pour le processus de passage de commande |
| [ADR-005](adr/ADR-005-api-gateway-kong.md) | API Gateway Kong comme point d'entrée unique |
| [ADR-006](adr/ADR-006-resilience-circuit-breaker.md) | Circuit Breaker (+ Retry, Timeout, Fallback) sur les appels synchrones critiques |
| [ADR-007](adr/ADR-007-choix-moteurs-persistance.md) | Choix des moteurs de persistance par service (PostgreSQL, MongoDB, Elasticsearch, Redis) |

## Diagrammes (draw.io)

Tous les diagrammes sont réalisés avec **draw.io** : les sources `.drawio` (éditables sur [app.diagrams.net](https://app.diagrams.net)) et leurs exports PNG sont dans [`diagrams/`](diagrams/).

| Diagramme | Source | Image |
|-----------|--------|-------|
| Contexte système (C4 niveau 1) | [c1-contexte-systeme.drawio](diagrams/c1-contexte-systeme.drawio) | [PNG](diagrams/c1-contexte-systeme.png) |
| Conteneurs (C4 niveau 2) | [c2-conteneurs.drawio](diagrams/c2-conteneurs.drawio) | [PNG](diagrams/c2-conteneurs.png) |
| Séquence — SAGA « passage de commande » | [seq-saga-commande.drawio](diagrams/seq-saga-commande.drawio) | [PNG](diagrams/seq-saga-commande.png) |
| Séquence — Circuit Breaker | [seq-circuit-breaker.drawio](diagrams/seq-circuit-breaker.drawio) | [PNG](diagrams/seq-circuit-breaker.png) |
| Modèles de données simplifiés | [modele-donnees.drawio](diagrams/modele-donnees.drawio) | [PNG](diagrams/modele-donnees.png) |

## Contrats d'API (OpenAPI 3)

La source autoritaire des contrats est `services/ressources/endpoints/` (chargée par les services à l'exécution) ; le dossier [`api/`](api/) en est le miroir documentaire.

- [`api/api-gateway.openapi.yaml`](api/api-gateway.openapi.yaml)
- [`api/order-service.openapi.yaml`](api/order-service.openapi.yaml)
- [`api/restaurant-service.openapi.yaml`](api/restaurant-service.openapi.yaml)
- [`api/catalog-service.openapi.yaml`](api/catalog-service.openapi.yaml)
- [`api/payment-service.openapi.yaml`](api/payment-service.openapi.yaml)
- [`api/delivery-service.openapi.yaml`](api/delivery-service.openapi.yaml)
- [`api/notification-service.openapi.yaml`](api/notification-service.openapi.yaml)
- [`api/rating-service.openapi.yaml`](api/rating-service.openapi.yaml)
- [`api/customer-service.openapi.yaml`](api/customer-service.openapi.yaml)
- [`api/deliverer-service.openapi.yaml`](api/deliverer-service.openapi.yaml)