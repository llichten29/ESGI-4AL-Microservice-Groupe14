# ADR-006 — Circuit Breaker (+ Retry, Timeout, Fallback) sur les appels synchrones critiques

**Statut** : Accepté — 2026-07-14
**Décideurs** : Groupe 14

## Contexte

L'appel synchrone Commande → Paiement est sur le chemin critique de chaque commande. Si le service Paiement (ou le PSP derrière lui) tombe ou ralentit, les requêtes s'accumulent dans le service Commande (threads/connexions bloqués), qui finit par tomber à son tour : **panne en cascade**. C'est le principal risque de disponibilité identifié ([07-resilience.md](../07-resilience.md)).

## Décision

Protéger tous les appels HTTP sortants critiques par la combinaison :

1. **Timeout** de 2 s sur chaque tentative ;
2. **Retry** ×3 avec backoff exponentiel (200/400 ms + jitter), uniquement sur opérations idempotentes (`Idempotency-Key`) ;
3. **Circuit Breaker** : ouverture après 3 échecs consécutifs, fenêtre de 30 s, état semi-ouvert avec requête d'essai ;
4. **Fallback** : commande sauvegardée `EN_ATTENTE_PAIEMENT` + 503 explicite avec `Retry-After` (et, pour le Catalogue, service des résultats depuis le cache Redis).

Implémentation prototype : `tenacity` (retry/backoff) + `pybreaker` (circuit breaker) autour d'un client `httpx` avec timeouts.

## Options envisagées

1. **Retry + timeout seuls** — rejeté : les retries sur une panne durable *aggravent* la charge du service en difficulté et n'empêchent pas l'accumulation de latence.
2. **Circuit breaker combiné aux quatre patterns (retenu)**.
3. **Service mesh (Istio/Linkerd)** — fournit ces patterns sans code, mais exige Kubernetes : disproportionné pour un prototype Docker Compose.

## Conséquences

**Positives** : pas de panne en cascade ; échec rapide et réponse claire au client ; le service en panne récupère à l'abri du trafic ; comportement démontrable (il suffit d'arrêter le conteneur Paiement pendant la démo).

**Négatives (assumées)** : cinq paramètres à calibrer (documentés et centralisés en configuration) ; le fallback introduit un état supplémentaire (`EN_ATTENTE_PAIEMENT`) à gérer dans le cycle de vie ; le circuit breaker étant local à chaque instance, ses compteurs ne sont pas partagés entre réplicas (acceptable : chaque instance converge en quelques secondes).
