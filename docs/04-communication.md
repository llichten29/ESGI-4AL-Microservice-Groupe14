# 4. Patterns de communication entre services

## 4.1 Règle de décision synchrone / asynchrone

Pour chaque interaction nous avons appliqué la grille suivante :

| Question | Si oui → | Si non → |
|----------|----------|----------|
| L'appelant a-t-il besoin de la réponse **maintenant** pour continuer ? | Synchrone (REST) | Asynchrone (RabbitMQ) |
| L'opération implique-t-elle un humain ou un délai imprévisible ? | Asynchrone | — |
| Plusieurs consommateurs sont-ils intéressés par le fait métier ? | Asynchrone (publish/subscribe) | — |
| L'appelant peut-il tolérer l'indisponibilité du destinataire ? | Asynchrone | Synchrone + résilience |

## 4.2 Communications synchrones (REST/JSON via HTTP)

| Interaction | Justification |
|-------------|---------------|
| Clients ↔ API Gateway ↔ services | Interactions requête/réponse classiques des applications front |
| Commande → Paiement (autorisation) | Le client attend la confirmation de sa commande : sans autorisation de paiement, la commande ne doit pas continuer. Réponse immédiate requise → REST, **protégé par timeout + retry + circuit breaker** ([détails](07-resilience.md)) |
| Commande → Paiement (capture, remboursement) | Opérations transactionnelles courtes dont l'orchestrateur doit connaître l'issue pour faire avancer/compenser la SAGA |
| Paiement → PSP externe | API du prestataire (HTTPS) |

Choix de REST plutôt que gRPC : équipes réduites, débit modeste, contrat OpenAPI natif avec FastAPI et débogage simple (curl/Swagger UI) — les gains de performance de gRPC ne justifient pas sa complexité ici ([ADR-003](adr/ADR-003-communication-rest-et-rabbitmq.md)).

## 4.3 Communications asynchrones (RabbitMQ)

**Topologie** : un échange **topic** unique `delivery.events`. Chaque service publie avec une routing key `<contexte>.<evenement>` et consomme via sa **file durable** propre, liée aux clés qui l'intéressent.

```
                        ┌──────────────────────────────┐
  order.*  ────────────►│                              │────► file notification.*  (Service Notification)
  paiement.* ──────────►│   exchange topic             │────► file restaurant.saga (Service Restaurant)
  livraison.* ─────────►│   « delivery.events »        │────► file livraison.saga  (Service Livraison)
  menu.* ──────────────►│                              │────► file commande.saga   (Service Commande)
                        └──────────────────────────────┘────► file catalogue.proj  (Service Catalogue)
```

| Interaction | Type de message | Justification |
|-------------|-----------------|---------------|
| Commande → Restaurant : `restaurant.acceptation.demandee` | **Commande** (1 destinataire attendu) | L'acceptation dépend d'un humain (délai en minutes) : un appel REST bloquant serait absurde |
| Restaurant → Commande : `order.acceptee / refusee / prete` | Événement | Fait métier ; consommé aussi par Notification |
| Commande → Livraison : `livraison.demandee` | Commande | L'affectation d'un livreur peut prendre du temps (recherche, acceptation par le livreur) |
| Livraison → * : `livraison.affectee / terminee / echec` | Événement | Suivi par Commande, Notification |
| Restaurant → Catalogue : `menu.mis-a-jour` | Événement | Projection du read model, aucune urgence |
| * → Notification | Événement | Pur consommateur ; les producteurs ignorent son existence |

### Garanties et bonnes pratiques appliquées

- **At-least-once + idempotence** : chaque message porte un `message_id` unique ; les consommateurs stockent les ids traités et ignorent les doublons.
- **Transactional Outbox** côté producteurs critiques (Commande) : l'événement est écrit en base dans la même transaction que le changement d'état, puis relayé vers RabbitMQ — pas de perte d'événement si le service crashe entre le commit et la publication.
- **Dead Letter Queue** : les messages échouant après N tentatives de consommation partent en DLQ pour analyse manuelle.
- **Files durables + messages persistants** : survivent au redémarrage du broker.

## 4.4 Rôle de l'API Gateway (Kong)

- **Point d'entrée unique** pour les trois applications front (client, restaurateur, livreur) : les services internes ne sont pas exposés ;
- **Routage** par préfixe de chemin (`/v1/commandes → service Commande`, etc.) ;
- **Authentification** : validation des JWT émis par le service Client, propagation de l'identité (`X-User-Id`) aux services ;
- **Rate limiting** et quotas par consommateur ;
- **Terminaison TLS** et CORS.

Le service **Paiement n'est volontairement pas routé** par le gateway : il n'est joignable que depuis le réseau interne (appelé par Commande), ce qui réduit la surface d'attaque.

## 4.5 Versioning et compatibilité ascendante

- **APIs REST** : version majeure dans le chemin (`/v1/...`). Une nouvelle version majeure (breaking) est déployée en parallèle (`/v2`) et l'ancienne maintenue le temps de la migration des consommateurs.
- **Changements non cassants** (ajout de champs optionnels, nouveaux endpoints) : pas de nouvelle version ; les consommateurs doivent ignorer les champs inconnus (*tolerant reader*).
- **Événements** : chaque message porte `schema_version`. Règles : on peut ajouter des champs optionnels ; on ne supprime ni ne renomme jamais un champ sans publier un nouvel événement versionné (`order.acceptee.v2`) consommable en parallèle de l'ancien.
- Les contrats OpenAPI ([docs/api/](api/)) sont versionnés avec le code et font office de source de vérité pour les tests de contrat.
