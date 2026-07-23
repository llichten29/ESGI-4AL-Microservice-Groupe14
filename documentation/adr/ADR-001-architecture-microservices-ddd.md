# ADR-001 — Architecture microservices découpée selon les Bounded Contexts (DDD)

**Statut** : Accepté — 2026-06-14
**Décideurs** : Groupe 14

## Contexte

La plateforme de livraison de repas couvre huit capacités métier (clients, restaurants, catalogue, commandes, paiements, livraison, notation, notifications) portées par trois types d'acteurs aux besoins très différents. Les charges sont hétérogènes (recherche massivement lue, commandes transactionnelles, positions de livreurs à haute fréquence d'écriture) et certaines parties (paiement) ont des contraintes de sécurité spécifiques.

## Décision

Adopter une **architecture microservices**, avec **un service par bounded context** identifié par l'analyse DDD ([02-analyse-domaine.md](../02-analyse-domaine.md)) : Client, Restaurant, Catalogue, Commande, Paiement, Livraison, Notation, Notification.

## Options envisagées

1. **Monolithe modulaire** — plus simple à développer et déployer, transactions ACID globales ; mais scaling uniquement global, un déploiement unique pour toutes les équipes, et il ne répond pas à l'objectif pédagogique du projet.
2. **Microservices par bounded context (retenu)**.
3. **Microservices fins (un par entité/fonction, 15+)** — granularité excessive : explosion des appels réseau et de la complexité opérationnelle sans gain de cohésion.

## Conséquences

**Positives** : scaling indépendant par service (le Catalogue peut être répliqué sans toucher au Paiement) ; déploiements et choix techniques autonomes ; isolation des pannes ; périmètre PCI restreint au service Paiement.

**Négatives (assumées)** : complexité distribuée — cohérence à terme obligatoire (→ [ADR-004](ADR-004-saga-orchestration.md)), résilience à outiller (→ [ADR-006](ADR-006-resilience-circuit-breaker.md)), observabilité et infrastructure plus lourdes (broker, gateway, N bases). Ce coût est jugé acceptable car il est précisément l'objet du projet.
