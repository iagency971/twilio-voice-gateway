# XAUUSD Z4 / E-BUY — Dukascopy Native Recovery v0.3 — Erratum A (transport host)

Date : 2026-08-25

## Incident

Le premier run v0.3 `32918836611` s'est arrêté dans **Stage A acquisition**, avant décodage complet, avant agrégation M1, avant QA native-vs-mirror et avant tout Stage B.

Erreur : HTTP `503 Service Unavailable` sur `https://datafeed.dukascopy.com/datafeed/XAUUSD/2026/07/19/03h_ticks.bi5` après retries.

Aucun résultat de parité Stage A n'a donc été observé et aucun résultat E-BUY/trigger/score n'a été calculé dans ce run.

## Réparation autorisée

Réparation d'ingénierie transport uniquement :

- conserver le même path Dukascopy `.bi5`, le même symbole XAUUSD, les mêmes dates, le même month zero-indexed et le même format `>IIIff` ;
- essayer le host `https://datafeed.dukascopy.com/datafeed` ;
- en cas de 5xx/timeout après retries, essayer `https://www.dukascopy.com/datafeed` pour le **même fichier** ;
- ne jamais synthétiser une heure absente ;
- si les deux hosts échouent, l'heure est manquante et la QA Stage A de couverture décidera ;
- aucune modification des gates v0.3.

## Invariants

Aucun changement de :
- reconstruction tick→M1 ;
- diviseur XAUUSD ;
- fenêtre QA 19–20 août ;
- seuils BID/ASK Stage A ;
- architecture E-BUY ;
- trigger `BULL_REJECTION` ;
- modèle/CDF `E_BUY_US` ;
- comparator Stage B ;
- seuils entry-transfer.

Cette réparation ne peut pas transformer un FAIL de QA en PASS par changement de seuil ; elle permet seulement d'obtenir les bytes natifs nécessaires pour que la QA puisse s'exécuter.
