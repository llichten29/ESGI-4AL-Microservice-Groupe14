# DashEat

**DashEat** est une plateforme de livraison de repas (type Uber Eats / Deliveroo) -- Preuve de concept microservices (projet ESGI-4AL-Microservice-Groupe14).

## Architecture

10 microservices autonomes, chacun proprietaire de ses donnees, orchestrant un pattern SAGA pour le traitement des commandes.

| Service              | Port | Role                                                            |
| -------------------- | ---- | --------------------------------------------------------------- |
| api-gateway          | 8000 | Point d'entree unique, routage pilote par les contrats OpenAPI  |
| order-service        | 8001 | Orchestrateur SAGA, cycle de vie des commandes, Circuit Breaker |
| restaurant-service   | 8002 | Gestion des restaurants, menus, validation et acceptation       |
| catalog-service      | 8003 | Recherche et indexation des restaurants/plats                   |
| payment-service      | 8004 | Traitement des paiements avec retry et backoff exponentiel      |
| delivery-service     | 8005 | Suivi des livraisons (courses)                                  |
| notification-service | 8006 | Notifications multi-canaux (email, SMS, push simules)           |
| rating-service       | 8007 | Evaluations et avis clients                                     |
| customer-service     | 8008 | Comptes clients, authentification JWT, adresses                 |
| deliverer-service    | 8009 | Gestion des livreurs (disponibilite, affectation)               |

## Stack technique

- **Langage** : Python 3.10
- **Framework** : Flask 3.0
- **Architecture interne** : Clean Architecture par service (domain / application / infrastructure / interfaces), voir [documentation/01-architecture-generale.md](documentation/01-architecture-generale.md)
- **Message Broker** : RabbitMQ (event-driven architecture)
- **Persistance** : polyglotte -- PostgreSQL, MongoDB, Elasticsearch, Redis (cache), voir [ADR-007](documentation/adr/ADR-007-choix-moteurs-persistance.md) ; customer-service et deliverer-service utilisent MongoDB, les autres services fonctionnent en memoire derriere des interfaces de repository
- **Contrats d'API** : OpenAPI 3.0.3 par service, valides a l'execution (PyYAML + jsonschema)
- **Conteneurisation** : Docker + Docker Compose
- **Communication** : REST (synchrone) + Events (asynchrone)
- **Tests** : pytest (`services/tests/`)
- **Qualite** : SonarQube (`sonar-project.properties`)

## Structure du projet

```
services/
  main/
    shared/                  # Modules partages (message broker, circuit breaker, retry, validateur OpenAPI)
    api-gateway/             # Port 8000
    order-service/           # Port 8001
    restaurant-service/      # Port 8002
    catalog-service/         # Port 8003
    payment-service/         # Port 8004
    delivery-service/        # Port 8005
    notification-service/    # Port 8006
    rating-service/          # Port 8007
    customer-service/        # Port 8008
    deliverer-service/       # Port 8009
      domain/                # Entites et regles metier
      application/           # Cas d'utilisation et services
      infrastructure/        # Repositories et adaptateurs
      interfaces/
        http/                # Routes et serializers
        events/              # Consommateurs et producteurs d'evenements
      config.py              # Configuration Flask
      app.py                 # Factory d'application
      Dockerfile             # Image Docker du service
  ressources/
    endpoints/               # Contrats OpenAPI par service (source de verite)
  tests/                     # Suites pytest par service
documentation/               # Chapitres d'architecture, ADRs, diagrammes, miroir des contrats
docker-compose.yml           # Orchestration complete
```

## Contrats d'API

Chaque service possede un contrat OpenAPI 3.0.3 dans `services/ressources/endpoints/`, charge au demarrage :

- chaque service valide ses requetes entrantes contre son contrat (400 en cas de violation de schema) et l'expose sur `GET /openapi.yaml` ;
- l'api-gateway construit sa table de routage a partir de ces contrats et sert la specification agregee sur http://localhost:8000/openapi.yaml, navigable via Swagger UI sur http://localhost:8000/docs.

Voir [documentation/05-contrats-api.md](documentation/05-contrats-api.md).

## Demarrage

### Prerequis

- Docker Engine 24+
- Docker Compose v2

### Lancer l'infrastructure

```bash
docker compose up -d
```

### Verifier l'etat des services

```bash
docker compose ps
```

Chaque service expose un endpoint `/health` :

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Documentation interactive

Swagger UI de la plateforme : http://localhost:8000/docs

### Management RabbitMQ

Interface web disponible sur http://localhost:15672 (guest/guest).

### Lancer les tests

```bash
python -m pytest services/tests
```

### Arreter l'infrastructure

```bash
docker compose down
```

Pour arreter et supprimer les volumes :

```bash
docker compose down -v
```

## Patterns implementes

- **SAGA Orchestree** : L'order-service orchestre le workflow de creation de commande avec compensations en cas d'echec
- **Circuit Breaker** : Protection des appels REST inter-services (seuil: 5 erreurs, recovery: 30s)
- **Retry avec Backoff Exponentiel** : Paiement avec 3 tentatives (1s, 2s, 4s)
- **Event-Driven** : Communication asynchrone via RabbitMQ pour le decouplage des services
- **Contract-First** : Contrats OpenAPI par service, sources du routage du gateway et de la validation des requetes

## Documentation architecture

Voir [documentation/README.md](documentation/README.md) pour la documentation complete : 
diagrammes C4, contrats d'API OpenAPI, Architecture Decision Records (ADRs), et specifications detaillees.
