# 2. Analyse du domaine et justification du découpage

## 2.1 Démarche

Nous avons appliqué une démarche **Domain-Driven Design (DDD)** :

1. identification des **sous-domaines** métier à partir des exigences fonctionnelles de l'énoncé ;
2. classification en sous-domaines **cœur** (différenciants), **support** et **génériques** ;
3. délimitation des **Bounded Contexts** — frontières à l'intérieur desquelles un modèle et un langage ubiquitaire sont cohérents ;
4. attribution d'**un microservice par bounded context**, en vérifiant les critères de cohésion forte / couplage faible.

## 2.2 Sous-domaines identifiés

| Sous-domaine                         | Type          | Justification                                                                                         |
|--------------------------------------|---------------|-------------------------------------------------------------------------------------------------------|
| Prise de commande                    | **Cœur**      | C'est le processus qui génère la valeur : orchestration commande → paiement → préparation → livraison |
| Livraison (suivi des courses)        | **Cœur**      | Différenciant métier (rapidité, suivi temps réel de la course)                                        |
| Gestion des livreurs (flotte)        | **Cœur**      | Différenciant métier (disponibilité de la flotte, optimisation des affectations)                      |
| Gestion des restaurants & menus      | Support       | Nécessaire au cœur, modèle riche mais peu différenciant                                               |
| Catalogue & recherche                | Support       | Optimisé pour la lecture, alimenté par les autres contextes                                           |
| Gestion des clients                  | Support       | Comptes, adresses, authentification                                                                   |
| Notation / avis                      | Support       | Contribue à la confiance, faiblement couplé au reste                                                  |
| Paiement                             | **Générique** | Délégué à un PSP externe ; notre service n'est qu'une façade transactionnelle                         |
| Notification                         | Générique     | Pur service technique, remplaçable                                                                    |

## 2.3 Bounded Contexts et langage ubiquitaire

Un point clé du DDD : **le même mot désigne des concepts différents selon le contexte**, ce qui justifie des modèles séparés.

- Une **« commande »** est, pour le contexte *Commande*, un agrégat avec cycle de vie (Reçue → En préparation → En livraison → Livrée / Annulée) ; pour le contexte *Restaurant*, c'est un « ticket de préparation » à accepter/refuser ; pour le contexte *Livraison*, ce n'est qu'une « course » avec deux adresses.
- Un **« plat »** est, pour le contexte *Restaurant*, un objet riche (options, disponibilité, recette) ; pour le contexte *Commande*, une simple **ligne de commande figée** (libellé + prix au moment de l'achat — d'où la copie `libelle`/`prix_unitaire` dans `order_items`).
- Un **« client »** est un compte avec profil dans le contexte *Client*, mais seulement un `client_id` (UUID) et une adresse de livraison dans le contexte *Commande*.
- Un **« livreur »** est, pour le contexte *Livreurs*, un agrégat avec statut de disponibilité (`AVAILABLE / BUSY / OFFLINE`), véhicule et position ; pour le contexte *Livraison*, seulement un `deliverer_id` et un nom attachés à la course.

Ces divergences de sens confirment que fusionner ces modèles dans une base unique créerait un modèle ambigu et fortement couplé.

## 2.4 Carte des contextes → microservices

| Bounded Context    | Microservice             | Exigence(s) de l'énoncé couverte(s)                                           |
|--------------------|--------------------------|-------------------------------------------------------------------------------|
| Comptes & identité | **Service Client**       | Gestion des clients (inscription, profil, adresses, historique)               |
| Restaurant & menu  | **Service Restaurant**   | Gestion des restaurants (profil, menus, horaires, acceptation)                |
| Découverte         | **Service Catalogue**    | Catalogue & recherche (localisation, type de cuisine, plats)                  |
| Commande           | **Service Commande**     | Gestion des commandes (panier, prix total, états)                             |
| Paiement           | **Service Paiement**     | Gestion des paiements (PSP externe, remboursements)                           |
| Livraison          | **Service Livraison**    | Gestion des livraisons (création de course, suivi, confirmation de remise)    |
| Flotte de livreurs | **Service Livreur**      | Gestion des livreurs (enregistrement, disponibilité, affectation, libération) |
| Réputation         | **Service Notation**     | Évaluations / avis                                                            |
| Notification       | **Service Notification** | Notifications email / push / SMS                                              |

## 2.5 Justification des choix de découpage

### Pourquoi séparer « Livreurs » et « Livraisons » en deux services ?

L'énoncé distingue la *gestion des livreurs* et la *gestion des livraisons* ; nous conservons cette frontière avec deux bounded contexts et deux microservices (**Service Livraison** et **Service Livreur**) car :

- ce sont **deux agrégats aux cycles de vie distincts** : la course (`PENDING → ASSIGNED → PICKED_UP → DELIVERED / FAILED`) et le livreur (`AVAILABLE / BUSY / OFFLINE`, véhicule, position) n'évoluent pas au même rythme ni pour les mêmes raisons ;
- le Service Livreur est la **source de vérité unique de la disponibilité de la flotte** (propriété exclusive des données) : le statut d'un livreur n'est modifié que par son propre service, jamais par les livraisons ;
- le couplage reste **minimal et explicite** : lors d'une affectation, le Service Livraison appelle `POST /deliverers/assign` (premier livreur disponible) puis `POST /deliverers/{id}/release` en fin de course — deux appels idempotents, sans partage de base de données ;
- la gestion de flotte peut **évoluer indépendamment** (contrats, rémunération, planification, app livreur) sans toucher au suivi des courses, et chaque service se scale selon son propre profil de charge.

Le compromis assumé est un appel synchrone sur le chemin d'affectation ; il est acceptable car la dégradation est propre : si aucun livreur n'est disponible, la course reste `PENDING` et sera réaffectée, sans bloquer la SAGA de commande.

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
