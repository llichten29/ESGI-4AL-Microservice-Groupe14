# ESGI-4AL-Microservice-Groupe14

Conception d'une architecture microservices pour une **plateforme de livraison de repas** (type Uber Eats / Deliveroo) — projet du cours Architecture Microservices, ESGI 4AL.

## Contenu du dépôt

| Dossier / fichier | Contenu |
|-------------------|---------|
| [`docs/`](docs/README.md) | Documentation d'architecture complète (analyse DDD, microservices, communication, SAGA, résilience, ADRs) |
| [`docs/diagrams/`](docs/diagrams/) | Diagrammes draw.io (sources `.drawio` éditables + exports PNG) : contexte C4-1, conteneurs C4-2, séquences SAGA et circuit breaker, modèles de données |
| [`docs/api/`](docs/api/) | Contrats OpenAPI 3 des services clés (Commande, Paiement, Restaurant) |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (6 décisions majeures) |
| [`presentation/`](presentation/) | Support de soutenance PowerPoint |
| `Enonce projet.pdf` | Énoncé du projet |

## L'architecture en bref

- **8 microservices** découpés par bounded context (DDD) : Client, Restaurant, Catalogue, Commande, Paiement, Livraison, Notation, Notification — derrière un **API Gateway Kong** ;
- **Python / FastAPI**, persistance polyglotte (**PostgreSQL**, **MongoDB**, **Redis**), une base par service ;
- Communication **REST synchrone** + **événements asynchrones RabbitMQ** (échange topic `delivery.events`) ;
- **SAGA orchestrée** pour le passage de commande (orchestrateur dans le service Commande, compensations par remboursement) ;
- Résilience : **Circuit Breaker + Retry + Timeout + Fallback** sur l'appel critique Commande vers Paiement.

Point d'entrée de la documentation : [`docs/README.md`](docs/README.md).
