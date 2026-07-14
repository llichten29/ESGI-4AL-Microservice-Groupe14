# ADR-004 — SAGA orchestrée pour le passage de commande

**Statut** : Accepté — 2026-07-14
**Décideurs** : Groupe 14

## Contexte

Le passage de commande traverse quatre services (Commande, Paiement, Restaurant, Livraison), chacun avec sa propre base ([ADR-002](ADR-002-database-per-service-polyglotte.md)). Sans transaction distribuée possible, il faut garantir qu'une commande ne reste jamais dans un état incohérent (payée mais jamais préparée, préparée mais jamais livrée) : chaque étape doit être compensable.

## Décision

Implémenter une **SAGA orchestrée** : le service Commande héberge l'orchestrateur, persiste l'état d'avancement (`saga_state`) et pilote les étapes — autorisation de paiement (REST sync), acceptation restaurant (message async), affectation livreur (message async), capture du paiement (REST sync). En cas d'échec, il exécute les compensations en ordre inverse (remboursement, annulation). Détail complet : [06-coherence-saga.md](../06-coherence-saga.md).

## Options envisagées

1. **Transaction distribuée (2PC/XA)** — rejetée : verrous bloquants, coordinateur SPOF, non supporté par MongoDB/RabbitMQ/PSP, anti-pattern microservices.
2. **SAGA chorégraphiée** — chaque service réagit aux événements des autres, couplage minimal ; mais avec 5 étapes et 3 scénarios de compensation, la logique du processus serait éparpillée dans 4 services : difficile à comprendre, à tester et à déboguer ; risque de dépendances cycliques d'événements.
3. **SAGA orchestrée (retenu)** — logique du processus centralisée et observable, compensations explicites.

## Conséquences

**Positives** : le processus critique est lisible en un seul endroit ; état d'avancement requêtable (suivi de commande, débogage, démo) ; timeouts métier (5 min acceptation, 10 min affectation) et compensations gérés systématiquement ; ajout d'une étape localisé.

**Négatives (assumées)** : le service Commande concentre plus de logique (risque de « god service » — contenu en n'y mettant que la coordination, jamais les règles métier des participants) ; l'orchestrateur doit être hautement disponible — son état étant persisté, un redémarrage reprend les SAGAs en cours ; couplage de connaissance de l'orchestrateur vers les APIs/messages publics des participants (acceptable : contrats versionnés).
