# XAUUSD — étude statistique de la réouverture après maintenance

Date de gel : 2026-08-27  
Branche : `agent/gold-reopen-stat-study-2026-08-27`  
Script reproductible : `xau-multiyear/reopen-study/gold_reopen_5m_study.py`

## 1. Objet et convention d'exécution

L'étude teste un BUY pris juste avant la coupure quotidienne du Gold, puis la trajectoire après la réouverture.

- Source : Dukascopy XAUUSD M1 BID/ASK.
- Fuseau de calcul : `America/New_York`.
- Entrées testées : OPEN ASK de 16:55, 16:56, 16:57, 16:58 et 16:59 ET.
- Sorties fixes : CLOSE BID de 18:00, 18:01, 18:02, 18:03 et 18:04, soit 1 à 5 minutes après la réouverture.
- `NORMAL` : réouvertures de lundi à jeudi à 18:00 ET, avec entrée le même jour avant la maintenance.
- `WEEKEND` : réouverture du dimanche 18:00 ET, qui ouvre la séance de trading du lundi, avec entrée le vendredi 16:55–16:59.
- Le spread est donc intégré correctement : achat à l'ASK, valorisation/sortie au BID.
- Un stop traversé pendant la coupure est exécuté au premier BID disponible à la réouverture, et non artificiellement au prix du stop.
- Le MFE/MAE inclut l'exposition depuis la minute réelle d'entrée jusqu'à 16:59, puis les cinq premières minutes de la réouverture.

Après filtres de complétude et d'activité, l'étude générale contient 1 645 événements valides : 1 324 `NORMAL` et 321 `WEEKEND`.

## 2. Résultat principal 2026 — réouvertures normales

Pour 2026 jusqu'au 27 août inclus, `NORMAL`, N=132 :

| Entrée | Sortie après 1 min : moyenne | Médiane | % gagnant | PF |
|---|---:|---:|---:|---:|
| 16:55 | +3.219 pt | +2.680 | 75.76 % | 4.02 |
| 16:57 | +3.118 pt | +2.500 | 73.48 % | 4.20 |

L'entrée 16:55 est le candidat principal : moyenne et taux de réussite supérieurs, spread légèrement inférieur. L'entrée 16:57 a un PF légèrement supérieur mais ne domine pas 16:55 sur l'ensemble des critères.

Pour l'entrée 16:55, l'allongement de la durée de détention dégrade le résultat :

| Sortie | Moyenne | Médiane | % gagnant | PF |
|---|---:|---:|---:|---:|
| après 1 min | +3.219 | +2.680 | 75.76 % | 4.02 |
| après 3 min | +2.979 | +1.787 | 67.42 % | 3.16 |
| après 5 min | +2.658 | +1.525 | 63.64 % | 2.51 |

La meilleure sortie fixe parmi 1–5 minutes est donc la clôture de la première minute de réouverture.

L'intervalle de confiance de Wilson à 95 % du taux de réussite 2026 de 100/132 est approximativement 67.8–82.3 %.

## 3. Changement de régime : 2025 vs 2026

En 2025, pour `NORMAL`, entrée 16:55, N=197 :

- sortie 1 min : moyenne -0.249 pt, médiane -0.077, 46.19 % gagnants, PF 0.77 ;
- sortie 3 min : moyenne +0.187 pt, médiane +0.113, 52.28 % gagnants, PF 1.17 ;
- sortie 5 min : moyenne +0.002 pt, médiane +0.096, 51.78 % gagnants, PF 1.00.

L'entrée 16:57 en 2025 est un peu meilleure à 3 minutes : moyenne +0.290 pt, médiane +0.133, 54.31 % gagnants, PF 1.30.

Le taux de réussite à 1 minute passe de 46.19 % en 2025 (16:55) à 75.76 % en 2026. Un test bilatéral de différence de proportions donne environ p=1.0e-7 : ce changement est trop important pour être expliqué raisonnablement par le seul bruit d'échantillonnage, mais cela ne prouve pas que le régime 2026 persistera.

Les années 2020–2024 ne montrent pas une edge exécutable stable comparable à 2026. L'effet doit donc être traité comme un phénomène de régime, et non comme une loi intemporelle du Gold.

## 4. Août 2026

Le phénomène reste présent en août 2026 jusqu'au 27 inclus. Pour `NORMAL`, entrée 16:55, N=16 :

- sortie 1 min : moyenne +1.913 pt, médiane +0.645, 68.75 % gagnants, PF 6.39 ;
- sortie 5 min : moyenne +0.679 pt, médiane +0.515, 56.25 % gagnants, PF 1.54.

Le régime est moins puissant qu'au début de 2026, mais il n'a pas disparu sur les données d'août disponibles.

## 5. MFE / MAE 2026 — entrée 16:55

Sur les 132 réouvertures normales 2026 :

### MFE total à 5 minutes

- moyenne : 8.022 pt
- médiane : 4.895 pt
- P75 : 10.630 pt
- P90 : 17.227 pt
- P95 : 24.872 pt

### MAE total à 5 minutes

- moyenne : 5.360 pt
- médiane : 3.466 pt
- P75 : 6.238 pt
- P90 : 12.237 pt
- P95 : 14.327 pt

Parmi les trades qui sont encore gagnants à la sortie 5 minutes (N=84), leur MAE total est : médiane 2.315 pt, P75 4.575, P90 6.137, P95 9.776.

Cela montre qu'une partie importante des futurs gagnants subit d'abord une excursion négative. Un stop très serré transforme donc le profil du setup.

## 6. Simulation de stops — 2026 NORMAL, BUY 16:55, sortie 1 minute

Simulation stop-only + sortie temporelle, gap-aware :

| SL fixe | % stoppé | Gain moyen | % gagnant | PF |
|---|---:|---:|---:|---:|
| 1 pt | 90.91 % | -0.570 | 9.09 % | 0.43 |
| 2 pt | 66.67 % | +0.153 | 32.58 % | 1.10 |
| 3 pt | 49.24 % | +0.533 | 47.73 % | 1.30 |
| 5 pt | 21.21 % | +2.080 | 68.94 % | 2.51 |
| 7.5 pt | 12.12 % | +2.312 | 71.21 % | 2.70 |
| 10 pt | 7.58 % | +2.716 | 73.48 % | 3.16 |
| 15 pt | 2.27 % | +3.233 | 75.76 % | 4.07 |
| 20 pt | 0.76 % | +3.234 | 75.76 % | 4.07 |

Ce tableau ne signifie pas que 15 ou 20 points est un « stop optimal ». Il montre surtout que le Gold 2026 est beaucoup plus volatil et qu'un SL fixe en points doit être normalisé par la volatilité avant toute règle de risque. L'optimisation naïve du SL sur 2026 serait in-sample et conduirait à une fausse précision.

## 7. Potentiel de TP — descriptif uniquement

Pour 2026 `NORMAL`, entrée 16:55, proportion atteignant au moins le niveau positif indiqué pendant les cinq premières minutes après la réouverture, mesuré au BID par rapport à l'ASK d'entrée :

| Niveau | Atteint |
|---|---:|
| +0.5 pt | 88.64 % |
| +1 pt | 87.88 % |
| +2 pt | 81.82 % |
| +3 pt | 71.21 % |
| +4 pt | 62.12 % |
| +5 pt | 47.73 % |
| +7.5 pt | 33.33 % |
| +10 pt | 28.03 % |
| +15 pt | 12.12 % |
| +20 pt | 6.82 % |

Ces fréquences ne constituent pas un backtest TP+SL : en M1, si un TP et un SL se trouvent dans la même bougie, leur ordre intraminute est inconnu. Un test de bracket exact nécessiterait du tick ou au minimum une granularité inférieure à M1.

## 8. Week-end : population à exclure du candidat principal

Le week-end est structurellement différent et extrêmement dispersé.

En 2026, `WEEKEND`, entrée 16:55, N=30 :

- sortie 1 min : moyenne +1.550 pt, médiane +2.393, 53.33 % gagnants, PF 1.16 ;
- sortie 5 min : moyenne +2.331 pt, médiane +0.358, 50.00 % gagnants, PF 1.20 ;
- MAE 5 min : médiane 11.112 pt, P90 39.020, P95 64.860 ;
- spread d'entrée médian : 1.358 pt.

En 2025, les résultats week-end sont nettement négatifs. Les très grosses queues de distribution peuvent donner des moyennes trompeuses avec certains stops. La réouverture du dimanche doit donc rester séparée et est exclue du setup candidat.

## 9. Candidat provisoire à geler pour validation hors échantillon

Le candidat le plus défendable à ce stade est :

- population : `NORMAL` uniquement ; exclure la réouverture après week-end ;
- direction : LONG ;
- entrée : 16:55 ET, au prix ASK ;
- sortie primaire : clôture BID de la bougie M1 18:00, donc après la première minute de réouverture ;
- aucune optimisation de TP proposée à ce stade ;
- aucun SL fixe « optimal » proposé à ce stade ; le risque doit être normalisé par la volatilité et validé séparément.

Ce candidat est fort en 2026 mais n'est pas une stratégie historiquement stable sur 2020–2025. La question de recherche devient donc : quels états de marché expliquent et identifient ex ante le régime 2026, sans utiliser l'issue du trade ?

## 10. Étape méthodologique suivante

Avant toute conclusion tradable, il faut tester des variables pré-existantes et outcome-blind : volatilité/ATR avant 16:55, niveau du spread, amplitude de la séance, direction/tendance de la journée, jour de semaine, proximité d'événements macro et éventuellement variables de structure. Les seuils doivent être définis sur une période de développement puis évalués en walk-forward/OOS.

Pour le money management, la prochaine simulation prioritaire est un risque normalisé par ATR/volatilité avec sizing constant en dollars, puis un contrôle FTMO incluant spread/commission/slippage réalistes.
