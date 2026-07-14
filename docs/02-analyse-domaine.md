# 2. Analyse du domaine et justification du découpage

## 2.1 Démarche

Nous avons appliqué une démarche **Domain-Driven Design (DDD)** :

1. identification des **sous-domaines** métier à partir des exigences fonctionnelles de l'énoncé ;
2. classification en sous-domaines **cœur** (différenciants), **support** et **génériques** ;
3. délimitation des **Bounded Contexts** — frontières à l'intérieur desquelles un modèle et un langage ubiquitaire sont cohérents ;
4. attribution d'**un microservice par bounded context**, en vérifiant les critères de cohésion forte / couplage faible.

## 2.2 Sous-domaines identifiés

| Sous-domaine | Type | Justification |
|--------------|------|---------------|
| Prise de commande | **Cœur** | C'est le processus qui génère la valeur : orchestration commande → paiement → préparation → livraison |
| Livraison / affectation des livreurs | **Cœur** | Différenciant métier (rapidité, optimisation des affectations) |
| Gestion des restaurants & menus | Support | Nécessaire au cœur, modèle riche mais peu différenciant |
| Catalogue & recherche | Support | Optimisé pour la lecture, alimenté par les autres contextes |
| Gestion des clients | Support | Comptes, adresses, authentification |
| Notation / avis | Support | Contribue à la confiance, faiblement couplé au reste |
| Paiement | **Générique** | Délégué à un PSP externe ; notre service n'est qu'une façade transactionnelle |
| Notification | Générique | Pur service technique, remplaçable |

## 2.3 Bounded Contexts et langage ubiquitaire

Un point clé du DDD : **le même mot désigne des concepts différents selon le contexte**, ce qui justifie des modèles séparés.

- Une **« commande »** est, pour le contexte *Commande*, un agrégat avec cycle de vie (Reçue → En préparation → En livraison → Livrée / Annulée) ; pour le contexte *Restaurant*, c'est un « ticket de préparation » à accepter/refuser ; pour le contexte *Livraison*, ce n'est qu'une « course » avec deux adresses.
- Un **« plat »** est, pour le contexte *Restaurant*, un objet riche (options, disponibilité, recette) ; pour le contexte *Commande*, une simple **ligne de commande figée** (libellé + prix au moment de l'achat — d'où la copie `libelle`/`prix_unitaire` dans `order_items`).
- Un **« client »** est un compte avec profil dans le contexte *Client*, mais seulement un `client_id` (UUID) et une adresse de livraison dans le contexte *Commande*.

Ces divergences de sens confirment que fusionner ces modèles dans une base unique créerait un modèle ambigu et fortement couplé.

## 2.4 Carte des contextes → microservices

| Bounded Context | Microservice | Exigence(s) de l'énoncé couverte(s) |
|-----------------|--------------|--------------------------------------|
| Comptes & identité | **Service Client** | Gestion des clients (inscription, profil, adresses, historique) |
| Restaurant & menu | **Service Restaurant** | Gestion des restaurants (profil, menus, horaires, acceptation) |
| Découverte | **Service Catalogue** | Catalogue & recherche (localisation, type de cuisine, plats) |
| Commande | **Service Commande** | Gestion des commandes (panier, prix total, états) |
| Paiement | **Service Paiement** | Gestion des paiements (PSP externe, remboursements) |
| Livraison & flotte | **Service Livraison** | Gestion des livreurs + gestion des livraisons |
| Réputation | **Service Notation** | Évaluations / avis |
| Notification | **Service Notification** | Notifications email / push / SMS |

## 2.5 Justification des choix de découpage

### Pourquoi fusionner « Livreurs » et « Livraisons » dans un seul service ?

L'énoncé distingue la *gestion des livreurs* et la *gestion des livraisons*. Nous les regroupons dans un unique bounded context **Livraison** car :

- l'affectation d'un livreur à une commande nécessite **en permanence** la disponibilité et la position des livreurs : séparer les deux imposerait un appel synchrone sur le chemin critique de chaque affectation (couplage temporel fort) ;
- le cycle de vie d'une livraison et le statut d'un livreur évoluent **ensemble** (livreur EN_COURSE ⇔ livraison ACCEPTEE) : c'est un invariant transactionnel local qu'il serait coûteux de garantir entre deux services ;
- le langage ubiquitaire est commun (course, prise en charge, remise au client).

C'est un compromis documenté : si la gestion de flotte devenait un domaine riche (contrats, rémunération, planification), on la scinderait.

### Pourquoi séparer « Catalogue » de « Restaurant » ?

- Les **profils d'accès sont opposés** : Restaurant est orienté écriture par les restaurateurs (mise à jour des menus), Catalogue est orienté lecture massive par les clients (recherche géographique, filtres). Les besoins d'indexation et de scalabilité diffèrent radicalement.
- Le Catalogue est un **read model dénormalisé** (pattern CQRS léger) alimenté par les événements `menu.mis-a-jour` du service Restaurant : il peut être reconstruit à tout moment et mis en cache agressivement (Redis).
- En cas de panne du service Restaurant, la **recherche reste disponible** (résilience par découplage).

### Pourquoi isoler le « Paiement » ?

- Contraintes de **sécurité/conformité (PCI-DSS)** : le périmètre manipulant les références de paiement doit être le plus petit possible.
- Dépendance à un système externe (PSP) : l'isoler permet de confiner les pannes du PSP derrière un [circuit breaker](07-resilience.md) sans polluer la logique de commande.

### Pourquoi un service « Notification » séparé et stateless ?

- Fonction purement technique et transverse : elle consomme les événements de tous les contextes.
- Aucune donnée métier propre → stateless, scalable horizontalement, remplaçable sans impact.

### Critères de validation du découpage

Pour chaque service nous avons vérifié :

- **Cohésion forte** : toutes les responsabilités d'un service partagent le même agrégat racine et le même langage ;
- **Couplage faible** : les interactions inter-services passent par des contrats (API/événements), jamais par la base de données ;
- **Autonomie de déploiement** : chaque service peut être versionné et déployé indépendamment ;
- **Propriété exclusive des données** : une seule écriture possible par donnée maîtresse (source of truth unique).
