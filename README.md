# ESGI-4AL-Microservice-Groupe14

Plateforme de livraison de repas (type Uber Eats / Deliveroo) -- Preuve de concept microservices.

## Architecture

8 microservices autonomes, chacun avec sa propre base de donnees en memoire, orchestrant un pattern SAGA pour le traitement des commandes.

| Service              | Port | Role                                                            |
| -------------------- | ---- | --------------------------------------------------------------- |
| api-gateway          | 8000 | Point d'entree unique, routage des requetes                     |
| order-service        | 8001 | Orchestrateur SAGA, cycle de vie des commandes, Circuit Breaker |
| restaurant-service   | 8002 | Gestion des restaurants, menus, validation et acceptation       |
| catalog-service      | 8003 | Recherche et indexation des restaurants/plats                   |
| payment-service      | 8004 | Traitement des paiements avec retry et backoff exponentiel      |
| delivery-service     | 8005 | Allocation des livreurs, suivi de livraison                     |
| notification-service | 8006 | Notifications multi-canaux (email, SMS, push simules)           |
| rating-service       | 8007 | Evaluations et avis clients                                     |

## Stack technique

- **Langage** : Python 3.10
- **Framework** : Flask 3.0
- **Message Broker** : RabbitMQ (event-driven architecture)
- **Cache** : Redis
- **Conteneurisation** : Docker + Docker Compose
- **Communication** : REST (synchrone) + Events (asynchrone)

## Structure du projet

```
services/
  shared/                    # Modules partages (message broker, circuit breaker)
  api-gateway/               # Port 8000
  order-service/             # Port 8001
  restaurant-service/        # Port 8002
  catalog-service/           # Port 8003
  payment-service/           # Port 8004
  delivery-service/          # Port 8005
  notification-service/      # Port 8006
  rating-service/            # Port 8007
    domain/                  # Entites et regles metier
    application/             # Cas d'utilisation et services
    infrastructure/          # Repositories et adaptateurs
    interfaces/
      http/                  # Routes et serializers
      events/                # Consommateurs et producteurs d'evenements
    config.py                # Configuration Flask
    app.py                   # Factory d'application
    Dockerfile               # Image Docker du service
docker-compose.yml           # Orchestration complete
```

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

### Management RabbitMQ

Interface web disponible sur http://localhost:15672 (guest/guest).

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

## Documentation architecture

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour la documentation complete : diagrammes C4, contrats d'API OpenAPI, Architecture Decision Records (ADRs), et specifications detaillees.
