# XAUUSD Z4 / E-BUY — Dukascopy Native Recovery v0.3 — Erratum B (transport order/concurrency)

Date : 2026-08-25

Au moment de ce gel, le rerun v0.3 après Erratum A est encore dans `Stage A acquire native Dukascopy 19-20 Aug`. Aucune QA native-vs-mirror Stage A n'a été exécutée/observée et Stage B n'a pas été ouvert.

## Problème d'ingénierie

Le host `datafeed.dukascopy.com` consomme ses timeouts avant fallback `www.dukascopy.com`, rendant les 24 fichiers horaires inutilement lents. Il s'agit d'un problème de transport, pas de définition de données.

## Réparation autorisée avant QA

- pour chaque **même path BI5 exact**, essayer `https://www.dukascopy.com/datafeed` en premier, puis `https://datafeed.dukascopy.com/datafeed` en fallback ;
- télécharger les 24 heures d'un jour avec une concurrence bornée (maximum 6 workers) ;
- aucun autre host/source ;
- aucune fusion entre hosts pour un même fichier : le premier HTTP 200 du path est utilisé ;
- aucune interpolation/forward-fill ;
- les heures réellement indisponibles restent absentes ;
- reconstruction BI5 et tick→M1 inchangée ;
- la QA Stage A 99 % + erreurs/rendements reste seule juge de l'équivalence.

Tous les seuils et objets du prereg v0.3 restent strictement inchangés.
