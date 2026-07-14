# ADR-002 — Une base de données par service, persistance polyglotte

**Statut** : Accepté — 2026-07-14
**Décideurs** : Groupe 14

## Contexte

Chaque microservice doit pouvoir évoluer et se déployer indépendamment. Une base partagée créerait un couplage par le schéma : toute migration impacterait tous les services, et les invariants métier fuiteraient hors de leur contexte. Par ailleurs, les besoins de persistance diffèrent : transactions strictes (commandes, paiements), documents flexibles (menus), lectures géo/texte massives (catalogue), données volatiles à haute fréquence (positions des livreurs).

## Décision

1. **Database per service** : chaque service est l'unique propriétaire de sa base ; aucun autre service n'y accède directement (accès uniquement via API ou événements).
2. **Persistance polyglotte** :
   - **PostgreSQL** pour Commande, Paiement, Client, Livraison — ACID, contraintes, jsonb ;
   - **MongoDB** pour Restaurant, Catalogue, Notation — agrégats documentaires (menu complet = 1 document), schéma flexible, index géospatiaux/texte ;
   - **Redis** pour le cache du Catalogue et les positions temps réel des livreurs (TTL 30 s, `GEOADD`).

## Options envisagées

1. Base PostgreSQL unique partagée — rejetée : couplage fort, single point of failure, migrations globales.
2. Database per service, tout PostgreSQL — viable et plus simple à opérer, mais perd l'adéquation modèle/usage (menus, géo, TTL) et l'intérêt pédagogique.
3. **Database per service polyglotte (retenu)**.

## Conséquences

**Positives** : autonomie des schémas et des déploiements ; technologie adaptée à chaque usage ; rayon d'impact d'une panne de base limité à un service.

**Négatives (assumées)** : plus de jointures inter-contextes → duplication contrôlée de données (ex. `libelle`/`prix_unitaire` copiés dans `order_items`) et références par UUID sans clé étrangère ; cohérence inter-services à terme, gérée par événements + SAGA ([ADR-004](ADR-004-saga-orchestration.md)) et Transactional Outbox ; trois moteurs à opérer (accepté : Docker Compose les fournit clé en main).
