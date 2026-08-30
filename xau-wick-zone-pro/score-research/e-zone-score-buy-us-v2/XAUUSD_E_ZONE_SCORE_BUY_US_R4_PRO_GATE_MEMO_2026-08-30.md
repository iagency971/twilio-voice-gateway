# XAUUSD M1 — BUY US — mémo Pro de validation méthodologique ciblée R4

**Date :** 30 août 2026  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Périmètre :** contrôle neutre de l'étude E-zone score BUY-US V2  
**Statut outcome :** strictement outcome-blind

# Décision

## `GO_R4`

Le contrôle `R4_D5_MINIMAL_DENSE` est **scientifiquement acceptable et autorisé**, sous réserve d'un rebuild PREOUTCOME R4 complet et du passage de tous les garde-fous figés dans `E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json`.

Il n'existe pas de blocker méthodologique justifiant `NO_GO_R4`. Les blockers restants sont des blockers d'implémentation et de preuve pré-outcome : le pipeline courant exécute encore R2, son QA contient encore les anciens calipers, et aucun package R4 complet DEV/VAL/REP n'a encore été construit.

Si le package PREOUTCOME R4 satisfait mécaniquement toutes les conditions du présent gate, **aucun nouveau passage Pro n'est requis avant l'ouverture de DEV 2020-2021**. Si une seule condition échoue, le workflow doit s'arrêter avant DEV et revenir en Pro.

# 1. Intégrité outcome-blind de l'audit

Aucun outcome futur V2 DEV 2020-2021, VAL 2022 ou REP 2023 n'a été ouvert ou utilisé. Le run R2 s'est arrêté dans la construction PREOUTCOME. Les étapes d'ouverture DEV, de fit du modèle, de validation et de réplication ont été sautées.

R4 n'a lu que les géométries causales, les snapshots de contexte, le pool causal E/Z4 et les chemins de display. Le code de ladder refuse les colonnes désignant des outcomes, et les manifests R4 déclarent `future_price_outcomes_used = false`.

Le diagnostic Pro complémentaire a lui aussi été limité aux contrôles, à la balance, aux distributions et aux longueurs de chemin. Aucun label de réaction, matched-contact result, AUC, coefficient ou score n'a été produit.

# 2. Nécessité du remplacement de R2

La correction R2 supprimant l'exigence erronée d'un vrai slot E receveur était méthodologiquement correcte mais insuffisante. Le contrôle exact restait inexécutable :

- DEV : 550 / 67 200 donneurs avec au moins deux contrôles, soit 0,81845 % ;
- VAL 2022 : 153 / 35 466, soit 0,43140 % ;
- REP 2023 : 228 / 36 014, soit 0,63309 %.

Cette densité ne pouvait pas soutenir l'estimand primaire et ses seuils de taille d'échantillon.

R3 a exploré une ladder pré-outcome sans outcome. Son meilleur palier D4 a atteint 74,8689 % de donneurs avec au moins deux contrôles, avec un maximum absolu de SMD égal à 0,08812. Le seuil de sélection avait été figé à 80 % ; D4 n'a donc pas été accepté après coup.

R4 a conservé le même gate 80 % / SMD max 0,10 et a pré-déclaré D5 à D8. D5 a été le premier palier testé et le premier palier passant. D6-D8 n'ont pas été utilisés et sont désormais interdits.

# 3. Adjudication de `R4_D5_MINIMAL_DENSE`

Le design autorisé conserve :

- le même créneau de cinq minutes au départ ;
- une séparation minimale de dix sessions représentées ;
- les cinq variables numériques déjà gelées ;
- la transplantation du chemin géométrique normalisé du donneur ;
- la famille et le slot comme labels donneurs uniquement ;
- la neutralité causale vis-à-vis du pool complet E/Z4 ;
- la troncature avant le premier conflit ou snapshot indisponible ;
- cinq contrôles maximum ;
- un départage SHA-256 déterministe.

Les seules modifications de matching par rapport au contrôle R2 sont :

- `abs(delta log(v)) <= 0,65` ;
- `abs(delta nearest_upper_z4_dist_v) <= 1,25` ;
- weekday non exact, pénalité 0,10 ;
- bucket du nombre de Z4 supérieures non exact, pénalité 0,25.

Ces valeurs ne sont pas déclarées « optimales ». Elles sont acceptées parce qu'elles ont été définies sans outcome, qu'elles constituent le premier palier R4 passant, qu'aucun palier plus large n'a été consulté pour la sélection, et que les diagnostics de support et de balance passent. Elles doivent maintenant rester inchangées.

# 4. Résultats pré-outcome du design

Sur la population outcome-blind 2022 :

| Critère | Gate figé | Résultat | Verdict |
|---|---:|---:|---|
| Donneurs avec ≥2 contrôles | ≥80 % | 82,2393 % | PASS |
| Minimum parmi E1/E2/E3 | ≥70 % | 80,4101 % | PASS |
| SMD donor-equal maximal | ≤0,10 | 0,08228 | PASS |
| KS donor-equal maximal | ≤0,10 | 0,08052 | PASS |
| TVD weekday | ≤0,10 | 0,02408 | PASS |
| TVD bucket Z4 | ≤0,10 | 0,04331 | PASS |
| Écart catégoriel maximal weekday | ≤0,10 | 0,02408 | PASS |
| Écart catégoriel maximal bucket Z4 | ≤0,10 | 0,04331 | PASS |
| Donneurs éligibles avec deux contrôles couvrant ≥50 % du chemin | ≥70 % | 97,0000 % | PASS |

Les trois slots passent séparément la gate de couverture pré-outcome :

- E1 : 11 333 / 14 094 = 80,4101 % ;
- E2 : 10 775 / 13 011 = 82,8145 % ;
- E3 : 7 059 / 8 361 = 84,4277 %.

La balance donor-equal est cohérente avec l'estimand final où chaque vraie E pèse un :

- `trend15_v` : SMD -0,08228 ; KS 0,07956 ;
- `trend60_v` : SMD +0,02906 ; KS 0,06486 ;
- `trend240_v` : SMD +0,06001 ; KS 0,08052 ;
- `nearest_upper_z4_dist_v` : SMD +0,00681 ; KS 0,01307 ;
- `log_v_snapshot` : SMD +0,02198 ; KS 0,01502.

La famille `ES_M1_8H_R2_T0.50` a la couverture la plus faible, 70,3044 %. Cette information reste un diagnostic de support, pas un motif de modification ou de rescue par famille. Aucun modèle ou seuil spécifique à une famille n'est autorisé.

# 5. Utilisation de 2022 pour le design

L'utilisation de la géométrie et des covariables 2022 pour choisir un matching, avec les outcomes masqués, ne contamine pas la validation future de l'effet de réaction. La règle R4 est fixée avant lecture de tout outcome et ne dépend d'aucune réussite ou défaillance future.

La formulation scientifique doit toutefois rester exacte : 2022 est une **validation forward des outcomes sous un design de matching conçu outcome-blind sur les covariables 2022**. Ce n'est plus un holdout totalement intact au niveau du design. Les chiffres de couverture et de balance 2022 sont des preuves de design, pas des preuves de réaction.

Pour contrôler le transport du matching, le même R4 doit passer les garde-fous pré-outcome séparément dans DEV, VAL et REP avant l'ouverture de DEV. REP 2023 conserve ensuite son rôle de seconde validation d'outcome sans refit, mais reste fermé si le gate complet de continuation VAL 2022 échoue.

# 6. Médiane de chemin placebo égale à un snapshot

Cette médiane n'est pas un blocker.

Le diagnostic montre que la médiane du chemin réel donneur est elle-même égale à un snapshot : 75 % des épisodes donneurs ont un seul snapshot et le percentile 90 est de deux snapshots. La médiane placebo égale à un reflète donc principalement la structure réelle des épisodes, pas une destruction générale par la règle de neutralité.

De plus :

- 84,6460 % des contrôles sélectionnés conservent le chemin complet ;
- 86,1762 % des donneurs éligibles ont au moins deux contrôles conservant le chemin complet ;
- 97,0000 % ont au moins deux contrôles conservant au moins la moitié du chemin donneur.

Le labeler autorise techniquement un épisode d'un snapshot : après disponibilité de la feature, une M1 peut armer l'épisode, puis une M1 ultérieure peut le contacter pendant la validité du snapshot. Une fois le contact établi, la classification sur les trente M1 suivantes ne dépend plus de la persistance ultérieure du chemin.

Il serait donc méthodologiquement incorrect d'imposer maintenant une longueur absolue minimale de deux snapshots à tous les donneurs : cela changerait la population E réelle. Le garde-fou approprié est relatif à la longueur du donneur, tel que figé dans le gate R4.

# 7. SMD seul et diagnostics supplémentaires

Le SMD global publié par la ladder R4 était nécessaire mais non suffisant pour deux raisons :

1. il pondérait chaque ligne contrôle, alors que l'estimand final donne un poids total de un à chaque donneur ;
2. weekday et bucket Z4 sont devenus des appariements souples, alors qu'ils étaient auparavant exacts.

Le gate Pro ajoute donc, avant outcome et sans modifier le matching :

- une balance donor-equal ;
- une distance KS pondérée sur les cinq variables numériques ;
- une TVD et un écart maximal de proportions sur weekday et bucket Z4 ;
- une couverture séparée par slot ;
- un support relatif des chemins.

Tous ces contrôles passent sur 2022. Ils deviennent maintenant des conditions mécaniques du rebuild PREOUTCOME dans chaque fenêtre. Les quantiles de distance de matching et la couverture par famille restent report-only : ils doivent être conservés, mais ne peuvent servir à une exclusion post-hoc ou à un nouveau tuning.

# 8. Parité V0.4

La reproduction fraîche obtient :

- 88 557 lignes de référence ;
- 88 557 lignes instrumentées ;
- égalité float64 exacte ;
- zéro mismatch ;
- delta absolu maximal égal à zéro.

Le précédent constat ponctuel de trois différences `zlo` et quatre différences `zhi` n'est pas reproduit et sa cause n'est pas démontrée. Il ne justifie ni correction de géométrie ni relâchement de tolérance.

La gate reste donc une égalité exacte fail-closed. Elle doit être rejouée dans le workflow PREOUTCOME R4 immédiatement avant le gel. Toute divergence arrête le workflow avant DEV.

# 9. Blockers avant l'ouverture de DEV

## Blocker 1 — générateur R4 absent du pipeline canonique

Le code R4 actuel est une ladder de faisabilité. Le pipeline canonique appelle toujours le générateur placebo R2. Un générateur R4 unique doit matérialiser les placebos et la matching table avec parité exacte vis-à-vis de la sélection canonique R4 2022.

## Blocker 2 — QA encore codé pour R2

Le QA vérifie encore `0,20` et `0,25`. Il doit vérifier les paramètres R4, les pénalités souples, l'écart minimal de sessions, la pondération donor-equal, les diagnostics distributionnels et le support relatif des chemins.

## Blocker 3 — autorisation technique R2 à superséder

Le runner et le token R2 ne doivent pas pouvoir ouvrir une nouvelle séquence d'outcomes. Le runner R4 doit vérifier `E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json` et utiliser le nouveau token :

`GO_E_ZONE_SCORE_BUY_US_V2_R4_SEQUENTIAL_HISTORICAL_EXECUTION`

## Blocker 4 — package PREOUTCOME R4 complet non encore gelé

DEV, VAL et REP doivent être reconstruits en R4, testés, hashés et archivés avant toute génération de label. Les onze exigences détaillées dans le JSON de gate sont obligatoires.

Ces blockers empêchent l'ouverture immédiate de DEV, mais ils ne constituent pas un défaut scientifique de `R4_D5_MINIMAL_DENSE`.

# 10. Éléments qui restent inchangés

Le présent gate ne modifie pas :

- la définition des vraies zones E ;
- le moteur v0.4 sticky ;
- les slots originaux E1/E2/E3 ;
- le périmètre BUY / US / M1 ;
- l'outcome width-neutral ;
- les règles d'armement et de contact ;
- les features et nuisances ;
- la régression logistique L2 et ses hyperparamètres ;
- le fit unique sur DEV ;
- l'absence de refit en VAL et REP ;
- les gates de validation des zones et du score ;
- la condition d'ouverture de REP ;
- l'interdiction Pine avant le gate Pro final ;
- l'absence d'autorisation de production ou de claim de profitabilité.

Les diagnostics supplémentaires R4 sont des gates de support et de comparabilité pré-outcome rendues nécessaires par le passage d'exact à souple pour weekday et bucket Z4. Ils ne redéfinissent ni l'outcome ni le modèle ni le seuil final d'effet.

# 11. Séquence autorisée après ce gate

1. Implémenter le générateur, le runner et le QA R4 exacts.
2. Construire DEV, VAL et REP entièrement outcome-blind.
3. Rejouer parité exacte, invariance de préfixe, déterminisme, neutralité et diagnostics R4.
4. Geler et hasher le package PREOUTCOME complet.
5. Si toutes les conditions passent, ouvrir DEV sans nouveau passage Pro.
6. Fitter une seule fois le modèle DEV et le geler.
7. Ouvrir VAL 2022 sans refit.
8. Ouvrir REP 2023 uniquement si le gate complet de continuation VAL passe.
9. Produire le package final et revenir en Pro au checkpoint final déjà gelé.

# Verdict final

## `GO_R4`

- Design R4 autorisé : **oui**.
- Calipers et pénalités gelés tels quels : **oui**.
- Outcome 2022 encore valide comme validation forward : **oui**, avec la qualification design-only obligatoire.
- Médiane d'un snapshot : **non bloquante**.
- Diagnostic supplémentaire au SMD : **requis et passé**.
- Parité exacte : **requise et passée**, fail-closed à chaque rebuild.
- Nouveau gate Pro après PREOUTCOME : **non**, si tous les contrôles mécaniques passent.
- Gates downstream originales : **inchangées**.
- REP 2023 : **toujours conditionnelle au gate VAL 2022**.
