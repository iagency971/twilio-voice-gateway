# XAUUSD — étude de réouverture compatible FTMO

Date de gel : 2026-08-27 / données jusqu'au 27 août 2026 inclus.

Branche : `agent/gold-reopen-stat-study-2026-08-27`

## 1. Statut des deux études

Cette étude **ne remplace pas** l'étude précédente `RESULTS_XAUUSD_REOPEN_2026-08-27.md`.

Deux objets doivent rester séparés :

1. **Étude A — broker compatible avec la réouverture native** : BUY 16:55 ET ASK, valorisation/sortie BID dès 18:00. En 2026 NORMAL, le meilleur candidat descriptif était 16:55 -> clôture de la M1 18:00 : N=132, moyenne +3.2193 $/oz, médiane +2.680, 75.76 % gagnants, PF 4.016. Ce setup n'est pas exécutable tel quel sur FTMO si XAUUSD cesse d'être tradable avant 16:55 et ne redevient tradable qu'à 18:05. Il reste conservé pour la recherche ultérieure d'un broker compatible.

2. **Étude B — compatible avec les horaires observés sur FTMO** : entrées avant la coupure, maintien de la position pendant la pause, première sortie/valorisation au premier prix tradable à 18:05.

Aucune fusion statistique entre ces deux études n'est autorisée.

## 2. Source et conventions FTMO

Source de marché : Dukascopy XAUUSD M1 BID/ASK, homogène 2020–2026, avec complément direct jusqu'au 27 août 2026.

Fuseau : `America/New_York` / ET.

Exécution LONG :
- entrée = ASK open de la minute d'entrée ;
- sortie = BID ;
- le spread historique Dukascopy est donc directement inclus ;
- 1 point dans ce mémo = 1.00 $/oz de variation XAUUSD, pas 0.01.

Entrées FTMO testées : 16:45, 16:46, 16:47, 16:48, 16:49 ET. 16:50 est uniquement diagnostique et n'est pas retenu comme minute opérationnelle afin de garder une marge avant la coupure observée.

Première sortie primaire : BID OPEN de 18:05 ET. Des sorties aux clôtures M1 de 18:05 à 18:10 sont également mesurées.

Population :
- `NORMAL` = reopens quotidiens lundi–jeudi, sans week-end ;
- `WEEKEND` = réouverture du dimanche, référence/entrée vendredi, étudiée séparément.

Le run final contient 1 649 événements valides au total. Rejets : 86 sessions inactives, 2 sessions incomplètes, 0 spread négatif. Le tail BID va jusqu'à 2026-08-27 23:58 UTC et ASK jusqu'à 23:59 UTC.

## 3. Règle FTMO à distinguer de la disponibilité du symbole

La FAQ FTMO consultée le 27 août 2026 indique que :
- durant le Processus d'Évaluation, les positions peuvent être conservées overnight et le week-end ;
- sur FTMO Account Standard, une position doit être fermée avant le week-end ou si le rollover / market break dure **plus de 2 heures** ;
- le compte Swing n'a pas cette restriction.

Source : https://ftmo.com/fr/faq/dois-je-fermer-mes-positions-pendant-la-nuit-ou-avant-le-week-end/

Une pause observée d'environ 16:50 à 18:05 ET dure environ 1 h 15, donc elle n'entre pas, en elle-même, dans le seuil `> 2 h` décrit par cette FAQ. Il faut néanmoins utiliser l'horaire et les spécifications réellement affichés sur la plateforme FTMO pour le symbole concerné.

FTMO précise aussi que les swaps rollover changent régulièrement et doivent être vérifiés dans la spécification du contrat. Source : https://ftmo.com/en/trading-updates/ et https://ftmo.com/fr/faq/quelles-sont-les-specifications-du-compte/

## 4. Résultat annuel NORMAL — BUY 16:49 ASK -> premier BID 18:05

| Année | N | Moyenne $/oz | Médiane | Gagnants | PF | Spread moyen | 16:49 -> 18:00 moyen | 18:00 -> 18:05 moyen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 201 | -0.4420 | -0.420 | 38.81 % | 0.545 | 0.579 | -1.1218 | +0.6799 |
| 2021 | 200 | -0.1906 | -0.194 | 39.00 % | 0.573 | 0.401 | -0.8235 | +0.6329 |
| 2022 | 199 | -0.4326 | -0.427 | 28.14 % | 0.303 | 0.424 | -0.7493 | +0.3168 |
| 2023 | 198 | +0.0046 | -0.157 | 40.40 % | 1.012 | 0.425 | -0.5749 | +0.5795 |
| 2024 | 198 | -0.0637 | -0.072 | 45.96 % | 0.869 | 0.364 | -0.6118 | +0.5482 |
| 2025 | 198 | -0.2275 | -0.0085 | 50.00 % | 0.849 | 0.595 | -1.1014 | +0.8739 |
| **2026** | **132** | **+2.4493** | **+1.575** | **64.39 %** | **2.209** | **0.737** | **-0.5592** | **+3.0085** |

Pooled 2020–2025, 16:49 : N=1 194, moyenne -0.22594, 482/1 194 = 40.37 % gagnants, PF agrégé ≈0.694.

Comparaison du taux de gains 2026 (85/132 = 64.39 %) au pooled 2020–2025 (482/1 194 = 40.37 %) : z ≈5.294, p bilatéral ≈1.19e-7. Le changement de régime est statistiquement très net, mais ne prouve pas sa persistance future.

Conclusion historique : **ce n'est pas une loi structurelle stable depuis 2020 ; c'est un phénomène de régime 2026.**

## 5. Robustesse au choix de la minute d'entrée

Première sortie BID 18:05 OPEN, population NORMAL.

| Entrée | 2025 mean | 2025 gagnants | 2025 PF | 2026 mean | 2026 gagnants | 2026 PF |
|---|---:|---:|---:|---:|---:|---:|
| 16:45 | -0.1447 | 49.49 % | 0.906 | +2.7360 | 65.15 % | 2.282 |
| 16:46 | -0.2390 | 50.00 % | 0.850 | +2.5286 | 63.64 % | 2.186 |
| 16:47 | -0.2687 | 49.49 % | 0.831 | +2.6635 | 63.64 % | 2.276 |
| 16:48 | -0.2143 | 47.98 % | 0.858 | **+2.7694** | 63.64 % | **2.357** |
| 16:49 | -0.2275 | 50.00 % | 0.849 | +2.4493 | **64.39 %** | 2.209 |

Les cinq minutes racontent la même histoire. Le signal 2026 n'est donc pas créé par le choix opportuniste d'une minute précise.

16:48 donne la meilleure moyenne brute et le meilleur PF de cette grille en 2026, mais la différence avec 16:45–16:49 est faible et **16:48 ne doit pas être qualifiée d'“optimale”** sur cet échantillon in-sample. Son intérêt opérationnel est aussi de garder environ deux minutes de marge avant une coupure observée vers 16:50.

## 6. Où se produit réellement le mouvement FTMO 2026 ?

Pour 16:49 en 2026 :
- 16:49 ASK -> 18:00 BID open : moyenne **-0.5592** ;
- 18:00 BID open -> 18:05 BID open : moyenne **+3.0085** ;
- total 16:49 ASK -> 18:05 BID open : moyenne **+2.4493**.

Le résultat FTMO-compatible 2026 vient donc essentiellement du repricing pendant la fenêtre 18:00–18:05, inaccessible à de nouvelles opérations FTMO mais capturable par une position déjà ouverte si elle reste effectivement en portefeuille durant la pause.

## 7. Sortir dès 18:05 ou attendre ?

Pour 16:49, NORMAL 2026, N=132 :

| Sortie | Mean $/oz | Gagnants | PF |
|---|---:|---:|---:|
| 18:05 OPEN | **+2.4493** | 64.39 % | **2.209** |
| 18:05 CLOSE | +2.3957 | 64.39 % | 2.151 |
| 18:06 CLOSE | +2.4798 | 65.15 % | 2.156 |
| 18:08 CLOSE | +2.0985 | 61.36 % | 1.813 |
| 18:10 CLOSE | +1.9233 | 59.09 % | 1.745 |

Il n'y a pas de preuve suffisante justifiant d'attendre plusieurs minutes après la réouverture. La sortie primaire non optimisée reste donc **le premier prix réellement exécutable vers 18:05**.

## 8. Le point critique : le signal 2026 s'affaiblit fortement

16:49 -> 18:05 OPEN par mois en 2026 :

| Mois | N | Mean $/oz | Médiane | Gagnants | PF |
|---|---:|---:|---:|---:|---:|
| Jan | 15 | +6.1967 | +2.523 | 86.67 % | 4.105 |
| Fév | 15 | +3.7153 | +5.846 | 60.00 % | 1.799 |
| Mar | 18 | +2.6294 | +2.300 | 66.67 % | 1.668 |
| Avr | 17 | +6.3527 | +6.240 | 88.24 % | 10.686 |
| Mai | 15 | +0.4617 | +1.360 | 66.67 % | 1.363 |
| Juin | 18 | **-0.4477** | -0.5585 | 44.44 % | 0.720 |
| Juil | 18 | +0.1644 | +0.685 | 55.56 % | 1.130 |
| Août* | 16 | +1.0925 | **-0.080** | **50.00 %** | 2.163 |

*Août jusqu'au 27 inclus.

Agrégé :
- janvier–avril : N=65, moyenne **+4.6770**, 49/65 = **75.38 %** gagnants ;
- mai–août : N=67, moyenne seulement **+0.2882**, 36/67 = **53.73 %** gagnants.

C'est un avertissement majeur : la statistique annuelle 2026 est fortement portée par janvier–avril. Le setup ne doit pas être considéré comme prêt pour la production uniquement à partir du résultat YTD.

## 9. Coût de swap : non inventé, traité par sensibilité

Le spread est déjà inclus. En revanche, il n'existe pas dans cette étude de série historique exacte des swaps FTMO XAUUSD pour chaque date. FTMO indique que ces swaps sont régulièrement modifiés et doivent être contrôlés dans les spécifications de la plateforme. Nous ne remplaçons donc pas cette donnée manquante par un faux taux fixe.

Convention de sensibilité : un coût de swap de base `S` en $/oz est appliqué une fois les jours ordinaires et trois fois le mercredi pour modéliser le triple swap. En 2026, le multiplicateur moyen est 1.51515.

Pour 16:49 -> 18:05 OPEN en 2026, brut spread inclus = +2.4493 :

| Swap de base simulé | Mean nette* | Gagnants | PF |
|---|---:|---:|---:|
| 0.25 | +2.0706 | 60.61 % | 1.952 |
| 0.50 | +1.6918 | 56.82 % | 1.723 |
| 1.00 | +0.9342 | 51.52 % | 1.344 |
| 2.00 | -0.5810 | 42.42 % | 0.837 |

*Hors slippage additionnel de réouverture.

Le coût de swap de base break-even de cet échantillon 2026 est ≈ **1.6166 $/oz** pour 16:49. Pour 16:48, il est ≈ **1.8278 $/oz**.

## 10. Sensibilité à un coût/slippage supplémentaire à la réouverture

Pour 16:49 -> 18:05 OPEN en 2026 :

| Coût supplémentaire plat | Mean nette | Gagnants | PF |
|---|---:|---:|---:|
| 0.25 | +2.1993 | 61.36 % | 2.038 |
| 0.50 | +1.9493 | 59.09 % | 1.878 |
| 1.00 | +1.4493 | 53.79 % | 1.595 |
| 2.00 | +0.4493 | 46.21 % | 1.153 |

Approximation combinée du mean 2026 16:49 :

`net ≈ 2.44934 - 1.51515 × swap_base - slippage_supplémentaire`

Exemples :
- swap_base 0.50 + slippage 0.50 -> ≈ +1.192 $/oz ;
- swap_base 1.00 + slippage 0.50 -> ≈ +0.434 $/oz ;
- swap_base 1.00 + slippage 1.00 -> ≈ -0.066 $/oz.

La valeur réelle du swap FTMO est donc décisive. Il faut la relever sur la plateforme avant toute décision d'exploitation.

## 11. WEEKEND : hors candidat

La réouverture du dimanche reste séparée. À 16:49 -> 18:05 :
- 2025 WEEKEND : N=49, mean -0.3557, 46.94 % gagnants, PF0.888 ;
- 2026 WEEKEND : N=31, mean +5.0822, 54.84 % gagnants, PF1.472, spread moyen 1.129.

Les analyses précédentes ont en plus montré une distribution weekend très heavy-tail avec de grandes excursions adverses. **Le weekend n'entre pas dans le candidat FTMO.**

## 12. Candidat FTMO provisoire à valider, pas stratégie de production

Pour la prochaine phase de validation :
- population : `NORMAL` uniquement ;
- direction : LONG ;
- entrée pratique candidate : ASK vers **16:48 ET** ;
- conserver la robustesse 16:45–16:49 comme preuve que le résultat ne dépend pas d'une minute unique ;
- maintien pendant la pause de marché ;
- sortie primaire : **premier BID réellement exécutable vers 18:05** ;
- weekend exclu ;
- coût de swap FTMO réel à intégrer ;
- slippage de réouverture à mesurer en live/forward ;
- aucun SL/TP “optimal” n'est encore figé ;
- tenir compte de l'affaiblissement mai–août avant toute décision de taille/risque.

Le bon statut méthodologique est : **edge de régime 2026 intéressant, FTMO-compatible en brut, mais non validé net de swap réel et non suffisamment stable récemment pour être déclaré production-ready.**

## 13. Prochaine gate

Avant de risquer du capital réel :
1. relever le swap LONG XAUUSD exact sur le compte FTMO/TradingView utilisé ;
2. confirmer par observation que la position reste ouverte de 16:48 à 18:05 sur le type de compte concerné ;
3. collecter un forward sample des fills réels 16:48 et de la première liquidation possible après 18:05, afin de mesurer spread/slippage réellement subi ;
4. étudier un filtre de régime défini **ex ante** (volatilité/ATR, range du jour, tendance, jour de semaine, contexte macro) en évitant de sélectionner le filtre sur les résultats futurs ;
5. conserver l'étude 16:55 -> 18:00 séparément pour rechercher un broker capable de l'exécuter.

## 14. Fichiers de reproduction

- Étude broker-compatible : `gold_reopen_5m_study.py`
- Mémo broker-compatible : `RESULTS_XAUUSD_REOPEN_2026-08-27.md`
- Étude FTMO-compatible : `gold_reopen_ftmo_study.py`
- Résultat annuel détaillé FTMO : `FTMO_YEARLY_2020_2026_2026-08-27.json`
- Résumé annuel FTMO : `FTMO_YEAR_SUMMARY_2020_2026_2026-08-27.json`

Aucun merge vers `main` n'est effectué dans cette étude.
