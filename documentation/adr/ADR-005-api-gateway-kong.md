# ADR-005 — API Gateway Kong comme point d'entrée unique

**Statut** : Accepté — 2026-06-14
**Décideurs** : Groupe 14

## Contexte

Trois applications front (client, restaurateur, livreur) consomment les APIs. Sans gateway, chaque front devrait connaître l'adresse de chaque service, chaque service devrait réimplémenter l'authentification, le rate limiting et le CORS, et tous les services seraient exposés publiquement.

## Décision

Placer un **API Gateway Kong** en frontal unique : routage par préfixe (`/v1/commandes` → service Commande…), validation des JWT émis par le service Client et propagation de l'identité (`X-User-Id`), rate limiting par consommateur, terminaison TLS. Le service **Paiement n'est pas routé** par le gateway (interne uniquement, appelé par Commande).

## Options envisagées

1. **Pas de gateway (accès direct)** — rejeté : sécurité et préoccupations transverses dupliquées dans chaque service, topologie interne exposée aux fronts.
2. **BFF par type de client (3 gateways)** — pertinent à grande échelle quand les besoins des fronts divergent fortement ; prématuré ici (surcoût de 3 composants), les routes actuelles étant identiques à 90 %.
3. **Nginx en simple reverse proxy** — suffisant pour le routage mais auth JWT/rate limiting à configurer à la main ; Kong les fournit en plugins déclaratifs (`kong.yml`, mode DB-less), tout aussi simple en Docker Compose.
4. **Kong (retenu)**.

## Conséquences

**Positives** : point d'entrée et de contrôle unique ; services internes non exposés ; préoccupations transverses (auth, quotas, CORS, TLS) sorties du code métier ; configuration déclarative versionnée.

**Négatives (assumées)** : composant critique sur le chemin de toutes les requêtes — atténué par sa nature stateless (répliquable) ; un saut réseau supplémentaire (latence négligeable à notre échelle) ; ne doit jamais contenir de logique métier (règle d'équipe : uniquement du routage et des politiques).
