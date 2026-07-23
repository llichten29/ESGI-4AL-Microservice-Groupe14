# ADR-003 — REST synchrone + événements asynchrones via RabbitMQ

**Statut** : Accepté — 2026-06-14
**Décideurs** : Groupe 14

## Contexte

Les interactions du système sont de deux natures : des requêtes/réponses où l'appelant a besoin du résultat immédiatement (lectures front, autorisation de paiement) et des processus métier longs impliquant des humains (acceptation restaurant : minutes ; affectation livreur : minutes) ou plusieurs consommateurs (notifications, projections).

## Décision

- **REST/JSON (HTTP)** pour le synchrone : front ↔ gateway ↔ services, et Commande → Paiement. Contrats OpenAPI 3, versionnés par le chemin (`/v1`).
- **RabbitMQ** pour l'asynchrone : un échange **topic** `delivery.events`, routing keys `<contexte>.<evenement>`, une file durable par consommateur, messages persistants, DLQ, livraison at-least-once + idempotence des consommateurs.

## Options envisagées

1. **Tout synchrone (REST partout)** — rejeté : couplage temporel généralisé ; l'acceptation restaurant en REST bloquant est irréaliste ; disponibilité globale = produit des disponibilités.
2. **gRPC pour le synchrone** — performant et typé, mais complexité (HTTP/2, protobuf, debug) injustifiée pour nos volumes ; FastAPI fournit OpenAPI nativement.
3. **Kafka pour l'asynchrone** — excellent pour le très haut débit et le replay (event sourcing), mais opérationnellement plus lourd ; l'énoncé le classe en extension bonus. RabbitMQ suffit pour nos patterns (routage topic, files de travail) et se déploie trivialement en Docker Compose.
4. **REST + RabbitMQ (retenu)**.

## Conséquences

**Positives** : chaque interaction utilise le bon outil ; découplage temporel des processus longs ; publish/subscribe naturel pour Notification et Catalogue ; simplicité de mise en œuvre et de démonstration (RabbitMQ Management UI).

**Négatives (assumées)** : deux mécanismes à maîtriser ; l'at-least-once impose l'idempotence de tous les consommateurs ; pas de replay complet de l'historique (contrairement à Kafka) — le Catalogue se reconstruit par resynchronisation REST si besoin. Migration vers Kafka possible plus tard sans changer les contrats d'événements.
