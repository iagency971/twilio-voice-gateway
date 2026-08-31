# XAUUSD M1 — BUY US — gate Pro final E-zone score V2 R4

**Date :** 31 août 2026  
**Dépôt :** `iagency971/twilio-voice-gateway`  
**Branche :** `agent/xau-wick-zone-pro-dev`  
**Run d’autorité :** `33334031028`  
**SHA d’exécution :** `5fe152e250684e35f55236c01cc51fbc9a8fed46`  
**Périmètre :** XAUUSD BID M1, BUY, 08:00–17:00 America/New_York, zones affichées E1/E2/E3

# Décision finale

## `NO_GO_PINE_SCORE_NO_STATISTICAL_VALIDATION`

L’exécution R4 est valide, complète et conforme à la séquence autorisée. Le résultat scientifique est cependant non confirmatoire :

- les zones E pooled ne sont pas statistiquement validées contre les niveaux neutres appariés ;
- E1 n’est pas validée ;
- E2 n’est pas validée ;
- E3 n’est pas validée ;
- le score width-neutral n’est pas validé ;
- REP 2023 reste fermée conformément au gate de continuation ;
- aucun score 0–100, grading de force ou libellé Pine dérivé de V2 n’est autorisé ;
- aucune autorisation de production ou affirmation de profitabilité n’est accordée.

Il s’agit d’un **résultat négatif/non confirmatoire valide**, et non d’un échec d’exécution.

# 1. Intégrité de l’exécution

Le run `33334031028` a terminé avec succès toutes les étapes prévues :

1. reconstruction PREOUTCOME DEV/VAL/REP ;
2. vérification canonique de la sélection R4 2022 ;
3. replay déterministe ;
4. absence d’artefact outcome avant DEV ;
5. gel PREOUTCOME immuable ;
6. ouverture DEV et fit unique du modèle ;
7. gel du modèle DEV ;
8. évaluation VAL sans refit ;
9. fermeture automatique de REP lorsque le gate VAL a échoué ;
10. production du package final.

Preuves d’intégrité :

- artefact final : `9742754436` ;
- SHA-256 de l’archive : `9612fc99b1a0a61a89f580573952441ab5f0e7fc95e41d422cb20623996a501b` ;
- modèle DEV gelé : `299728a8bbb2efbb912c225a77eb2725a8cb11d14a03deb6fa6e11e33fe5c9ff` ;
- rapport zones DEV : `32495d38e2cd015610af0490ccdf0d1491356d9406344c56c6d0e7ce42ca3960` ;
- rapport score DEV : `e86cf97a3e79f39118ea2b5c7ba4fedc6ee7eb80779e6d88b6a01493714d47ad` ;
- rapport zones VAL : `22b4f5c30f5d1cff14c424e2960ca68e08dab0af80b991e5e0a5aa32a7ac1330` ;
- rapport score VAL : `746732ab896593d8cb81af4eb6499d0ce5c7b5493180a72c7bc945118327471a`.

Le package final téléchargé reproduit exactement le SHA-256 annoncé. Les hashes des rapports et du modèle correspondent aux références du freeze final. `model_refit_after_DEV = false` et `replication_outcomes_opened = false` sont confirmés.

# 2. Verdict pooled des zones E

## DEV 2020–2021

- contacts E réels : `34 144` ;
- contacts E appariés avec au moins deux contrôles contactés : `20 962` ;
- couverture : `61,3929 %`, sous le seuil gelé de `70 %` ;
- effet matched : `+0,0105826`, soit environ `+1,06 point de pourcentage` ;
- IC95 % : `[-0,0026194 ; +0,0239762]` ;
- p bootstrap unilatérale : `0,0575885` ;
- verdict : `pooled_zone_pass = false`.

DEV montre au mieux un faible signal exploratoire. La borne basse de l’intervalle est négative et la couverture des contrôles contactés ne passe pas la gate.

## VAL 2022

- contacts E réels : `18 110` ;
- contacts E appariés : `10 282` ;
- couverture : `56,7753 %`, sous le seuil de `70 %` ;
- effet matched : `+0,0006435`, soit environ `+0,064 point de pourcentage` ;
- IC95 % : `[-0,0191901 ; +0,0193141]` ;
- p bootstrap unilatérale : `0,488902` ;
- verdict : `pooled_zone_pass = false`.

Le résultat VAL ne confirme pas le faible signal DEV. L’estimation est pratiquement nulle et l’intervalle est compatible avec un effet négatif ou positif d’environ deux points.

La conclusion ne dépend donc pas uniquement d’une gate de couverture sévère : même en mettant provisoirement cette gate de côté, le test d’effet VAL ne soutient pas une supériorité des zones E sur les témoins neutres appariés.

## Verdict pooled

`NOT_VALIDATED`

Sous l’outcome width-neutral gelé et le contrôle R4 autorisé, les zones E affichées ne peuvent pas être présentées comme de meilleurs lieux de réaction BUY que des niveaux neutres comparables.

Cette formulation ne signifie pas que toute utilisation discrétionnaire d’une zone E est impossible. Elle signifie que **l’hypothèse statistique précise étudiée ici n’est pas validée**.

# 3. Verdict E1, E2 et E3

Les verdicts individuels exigent le passage des gates gelées et une confirmation en réplication. REP n’a pas été ouverte, et aucun slot ne passe déjà ses diagnostics VAL.

## E1

- effet VAL : `-0,0050423` ;
- IC95 % : `[-0,0285321 ; +0,0175629]` ;
- p unilatérale ajustée Holm : `0,900220` ;
- AUC du score dans E1 : `0,514513`.

Verdict : `NOT_VALIDATED`.

Le signal E1 observé en DEV ne s’est pas reproduit : son effet devient légèrement négatif en validation.

## E2

- effet VAL : `+0,0020145` ;
- IC95 % : `[-0,0246892 ; +0,0282891]` ;
- p unilatérale ajustée Holm : `0,900220` ;
- AUC du score dans E2 : `0,511043`.

Verdict : `NOT_VALIDATED`.

## E3

- effet VAL : `+0,0112778` ;
- IC95 % : `[-0,0240937 ; +0,0445815]` ;
- p unilatérale ajustée Holm : `0,824235` ;
- AUC du score dans E3 : `0,485240` ;
- Q4−Q1 du score dans E3 : `-0,0532246`.

Verdict : `NOT_VALIDATED`.

L’effet ponctuel positif de E3 ne suffit pas : son intervalle est large, son test ajusté échoue et son classement par score est inversé en validation.

# 4. Verdict du score width-neutral

## DEV

- AUC affichée : `0,512725` ;
- IC95 % AUC : `[0,506112 ; 0,519304]` ;
- Q4−Q1 : `+0,0321813` ;
- IC95 % Q4−Q1 : `[+0,0154767 ; +0,0487506]` ;
- gain AUC full−nuisance : `+0,00184975` ;
- IC95 % du gain : `[-0,00040537 ; +0,00421160]` ;
- verdict : `score_pass = false`.

Le score sépare légèrement les outcomes en DEV, mais son ajout au-delà du contexte nuisance n’est pas démontré.

## VAL 2022

- AUC affichée : `0,507902` ;
- IC95 % AUC : `[0,498593 ; 0,517400]` ;
- Q4−Q1 : `+0,0183238` ;
- IC95 % Q4−Q1 : `[-0,0026080 ; +0,0401730]` ;
- gain AUC full−nuisance : `+0,00147846` ;
- IC95 % du gain : `[-0,00194148 ; +0,00496416]` ;
- quartiles monotones : `false` ;
- quintiles de largeur avec Q4−Q1 positif : `3/5`, seuil `4/5` ;
- verdict : `score_pass = false`.

Gates échouées en validation :

- borne basse AUC > 0,5 ;
- borne basse Q4−Q1 > 0 ;
- monotonie Q1 ≤ Q2 ≤ Q3 ≤ Q4 ;
- Q4−Q1 positif dans au moins quatre quintiles de largeur ;
- borne basse du gain full−nuisance > 0.

## Ce que le résultat établit sur la largeur

Les contraintes de décorrélation à la largeur passent : la corrélation score-largeur globale reste dans le seuil et les corrélations intra-famille restent acceptables. La construction V2 a donc bien réduit le défaut mécanique du V1.

Mais après retrait de cette dépendance, le signal de force restant n’est pas suffisamment stable ni incrémental pour être validé. Les résultats sont compatibles avec l’idée que la forte performance apparente du score V1 provenait largement de la largeur et du contexte, sans que V2 puisse démontrer une qualité intrinsèque exploitable des zones.

Cette dernière phrase est une interprétation soutenue par les résultats, pas une preuve que tout signal intrinsèque est exactement nul.

## Verdict score

`NOT_VALIDATED`

Aucun score 0–100, couleur de force, grade faible/moyen/fort ou filtre de qualité fondé sur V2 ne doit être transposé dans Pine.

# 5. Application de l’arbre de décision pré-enregistré

L’arbre de décision gelé dit :

- si les zones pooled échouent, aucune validation statistique des zones E ;
- aucun score de qualité ne doit être créé ou affiché ;
- REP ne s’ouvre que si le gate complet VAL passe.

Application :

- `validation_continuation_pass = false` ;
- `replication_outcomes_opened = false` ;
- REP 2023 reste scellée ;
- aucune modification adaptative de seuil, feature, modèle, matching ou gate n’est permise dans V2 ;
- aucun rescue E1, E2, E3 ou famille n’est permis ;
- aucune formule Pine n’est autorisée.

# 6. Claims autorisés et interdits

## Autorisé

Il est exact de dire :

- l’étude V2 R4 a été exécutée conformément au protocole ;
- le résultat est non confirmatoire ;
- le faible signal DEV ne s’est pas confirmé en VAL 2022 ;
- le score width-neutral n’a pas passé ses gates ;
- aucune zone E1/E2/E3 n’est statistiquement validée ;
- REP a été correctement laissée fermée.

## Interdit

Il n’est pas exact de dire :

- que les zones E sont statistiquement meilleures que les contrôles neutres ;
- que E1, E2 ou E3 est validée ;
- que le score 0–100 mesure une force réelle validée ;
- que le classement est prêt pour Pine ;
- que cette étude prouve une expectancy ou une profitabilité de trading ;
- qu’un sous-groupe observé après coup sauve l’étude.

Les zones visuelles existantes peuvent rester un outil **exploratoire**, mais elles ne disposent pas d’une validation statistique issue de V2.

# 7. Clôture et frontière des travaux futurs

V2 est désormais `CLOSED` comme étude non confirmatoire valide.

Il est interdit de modifier V2 après lecture de DEV/VAL pour obtenir un meilleur résultat. Les artefacts et hashes doivent rester immuables.

REP 2023 conserve une valeur scientifique précisément parce que ses outcomes n’ont pas été ouverts. Elle ne peut plus être ouverte comme rescue de V2. Une éventuelle V3 devra être :

- matériellement distincte ;
- explicitement pré-enregistrée ;
- approuvée outcome-blind avant toute ouverture de 2023 ;
- présentée comme une nouvelle étude, jamais comme une réussite rétroactive de V2.

# Conclusion finale

Le travail n’est pas « pour rien » : il a empêché la mise en production d’un score séduisant mais non confirmé et a séparé le signal de largeur du signal de force propre aux zones.

Le verdict opérationnel est néanmoins sans ambiguïté :

## zones E non validées, E1/E2/E3 non validées, score non validé, aucun Pine score, aucune production.

Référence machine-readable : `E_ZONE_SCORE_BUY_US_V2_FINAL_PRO_GATE.json`.
