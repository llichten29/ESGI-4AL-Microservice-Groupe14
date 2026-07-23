# ADR-007 — Choix des moteurs de persistance par service (PostgreSQL, MongoDB, Elasticsearch, Redis)

**Statut** : Accepté — 2026-07-22
**Décideurs** : Groupe 14
**Précise** : [ADR-002](ADR-002-database-per-service-polyglotte.md) (principe database-per-service et persistance polyglotte)

## Contexte

L'[ADR-002](ADR-002-database-per-service-polyglotte.md) a acté le principe « une base par service » et la persistance polyglotte, mais sans justifier moteur par moteur l'affectation retenue. Les besoins de persistance des dix services sont hétérogènes :

- transitions d'états strictes et compensations de la SAGA (commandes, paiements) ;
- agrégats documentaires à schéma évolutif (profils clients avec adresses, livreurs, courses, avis) ;
- recherche plein texte et à facettes sur le catalogue (nom, type de cuisine, prix, ouverture) ;
- données volatiles à forte fréquence de lecture (résultats de recherche, positions).

L'infrastructure est provisionnée par `docker-compose.yml` (une instance de base par service, conformément à l'ADR-002) et chaque service reçoit son URL de connexion par variable d'environnement (`DATABASE_URL`, `MONGODB_URL`, `ELASTICSEARCH_URL`).

## Décision

| Service | Moteur | Justification |
|---------|--------|---------------|
| Commande (order) | **PostgreSQL 15** | Cœur transactionnel de la SAGA : transitions d'états (`CREATED → ... → DELIVERED / CANCELLED`), lignes de commande figées (`order_items`), garanties ACID locales indispensables aux compensations |
| Paiement (payment) | **PostgreSQL 15** | Exigence d'intégrité maximale : montants, remboursements partiels, idempotence et piste d'audit ; les écritures financières ne tolèrent aucune perte ni double application |
| Restaurant | **PostgreSQL 15** | Profil structuré (horaires, statut) avec menus imbriqués portés par `jsonb` ; la décision d'acceptation d'une commande exige une lecture cohérente du menu au moment T |
| Notification | **PostgreSQL 15** | Journal append-only des notifications émises (l'API HTTP est en lecture seule, l'écriture vient des événements RabbitMQ) ; volumétrie faible, requêtage simple par destinataire |
| Client (customer) | **MongoDB 7** | Le client et ses adresses forment un agrégat documentaire naturel (1 document = 1 compte) ; schéma flexible pour profil et préférences ; pas de jointure inter-agrégats |
| Livreur (deliverer) | **MongoDB 7** | Document livreur (statut `AVAILABLE / BUSY / OFFLINE`, véhicule, position) mis à jour très fréquemment ; requête dominante « premier disponible » servie par un index simple sur le statut |
| Livraison (delivery) | **MongoDB 7** | La course est un document autoporteur (référence commande, livreur, horodatages `assigned/picked_up/delivered`, position) ; historique consulté tel quel, sans requête relationnelle |
| Notation (rating) | **MongoDB 7** | Avis = documents indépendants ; les synthèses (moyenne, volume) sont des agrégations par cible, cas d'usage natif du pipeline d'agrégation |
| Catalogue (catalog) | **Elasticsearch 8** | Read model dénormalisé (pattern CQRS léger) reconstruit depuis les événements ; recherche plein texte, filtres à facettes (cuisine, prix, ouverture) et pagination sont le cœur du service |
| API Gateway | — | Stateless : table de routage construite au démarrage depuis les contrats OpenAPI, aucun état persistant |

**Redis 7** est mutualisé comme **cache applicatif, jamais comme source de vérité** :

1. **Cache de lecture du Catalogue** : résultats de recherche mis en cache avec TTL court ; absorbe les pics de lecture et permet de servir des résultats même si l'index est indisponible (fallback du circuit breaker, [ADR-006](ADR-006-resilience-circuit-breaker.md)) ;
2. **Données volatiles de position** : positions des livreurs en cours de course avec TTL 30 s (`pos:{deliverer_id}`) ; une position périmée disparaît d'elle-même, sans purge applicative.

Toute donnée présente dans Redis peut être perdue et reconstruite : la source de vérité reste la base du service propriétaire.

### État du prototype

Le PoC applique la Clean Architecture : la persistance est isolée derrière des interfaces de repository (`infrastructure/repositories.py`). À ce stade, **customer-service et deliverer-service utilisent réellement MongoDB** (`MongoDBCustomerRepository`, `MongoDBDelivererRepository`) ; les autres services fonctionnent avec des repositories **in-memory**, l'infrastructure cible étant déjà provisionnée dans `docker-compose.yml` et les URL injectées. La migration d'un service vers son moteur cible consiste à ajouter une implémentation de repository sans toucher au domaine ni aux contrats d'API.

## Options envisagées

1. **Tout PostgreSQL** — viable et plus simple à opérer (un seul moteur), `jsonb` couvrant les besoins documentaires ; rejeté car la recherche à facettes du catalogue et l'expiration automatique des positions seraient artificielles, et l'intérêt pédagogique de la persistance polyglotte serait perdu.
2. **Tout MongoDB** — rejeté : les invariants transactionnels de la SAGA (commande, paiement) sont plus sûrs et plus lisibles avec des transactions ACID relationnelles et des contraintes de schéma.
3. **Redis comme base principale des positions et affectations** — rejeté : Redis est volatil par conception ; en faire une source de vérité imposerait persistance AOF et stratégie de reprise, disproportionnées face à un simple TTL de cache.
4. **Elasticsearch également pour les menus du Restaurant** — rejeté : le service Restaurant est orienté écriture et cohérence (décision d'acceptation) ; l'index de recherche appartient au Catalogue, alimenté par événements (séparation lecture/écriture déjà actée).
5. **Affectation polyglotte par service avec Redis en cache et Elasticsearch pour la recherche (retenu)**.

## Conséquences

**Positives** : chaque modèle de données est exprimé dans le moteur qui lui est naturel (transactions, documents, index inversé, TTL) ; le rayon d'impact d'une panne de base reste limité à un service ; le cache Redis donne un fallback de lecture démontrable pour le catalogue ; les repositories isolent le domaine des moteurs, ce qui a permis de démarrer le PoC in-memory sans bloquer le reste de l'architecture.

**Négatives (assumées)** : quatre technologies de persistance à opérer et superviser (accepté : Docker Compose les fournit clé en main pour la démo) ; l'index Elasticsearch et le cache Redis introduisent une cohérence à terme supplémentaire côté lecture (assumée : le Catalogue est un read model reconstruisible) ; l'écart entre l'infrastructure provisionnée et les repositories in-memory du prototype doit rester documenté pour ne pas induire en erreur (section « État du prototype » ci-dessus).
