# SolarOps Maroc : analyse exploratoire des données (jour 3)

Données : Open-Meteo Archive, 5 villes (Ouarzazate, Laayoune, Dakhla, Tanger, Al Hoceima), 2015 à 2024, 438 360 lignes (une par ville et par heure, heures en UTC).
Source : `notebooks/01_exploration.ipynb`.

## 1. Qualité des données

Les données sont propres : sur 438 360 lignes, il n'y a **aucun doublon, aucune heure manquante, aucune valeur manquante et aucune valeur hors plage physique**. Chaque ville a exactement 87 672 lignes, et chaque jour a 24 lignes (18 265 jours-villes sur 18 265).

Valeurs observées : rayonnement de 0 à 1 095 W/m², température de -5,1 à 46,8 °C, humidité de 2 à 100 %, pression de 872,6 à 1 033 hPa, vent jusqu'à 59,4 km/h, précipitation jusqu'à 18,2 mm/h. Le rayonnement est exactement nul entre 0 h et 3 h UTC dans les 5 villes.

Ce qui m'a surpris : l'absence totale de défaut. Les tests de qualité ne vont donc pas détecter de problème sur ces données ; leur rôle est de protéger le pipeline contre les futures ingestions (changement de format, panne de l'API).

## 2. Saisonnalité et journée

- **Forme de la journée** : une cloche centrée vers 13 h UTC, nulle la nuit. Elle est plus haute et plus large en été. À Tanger, le pic moyen est d'environ 910 W/m² en été contre environ 490 W/m² en hiver. Le jour commence vers 6 h UTC en été et vers 8 h UTC en hiver.
- **Décalage est-ouest** : plus on va vers l'ouest, plus le pic arrive tard en UTC. Dakhla culmine à 14 h (environ 865 W/m²), Tanger et Al Hoceima à 13 h (environ 705 W/m²).
- **Écart été-hiver** : plus marqué au nord. À Tanger, le rayonnement mensuel moyen passe d'environ 105 W/m² (décembre) à environ 317 W/m² (juillet), soit un facteur 3. À Dakhla, il passe d'environ 184 à environ 323 W/m² (mai), soit un facteur 1,75.
- **Durée du jour** : de 11 h en hiver à 14 ou 15 h en été (heures où le rayonnement moyen dépasse 5 W/m²).
- **Stabilité d'une année à l'autre** : très forte. Les moyennes annuelles varient de moins de 0,2 kWh/m²/jour autour de leur niveau et aucune année ne ressort. La dérive naturelle est donc faible : la démonstration de dérive du projet devra être **simulée**, et clairement présentée comme telle.
- **Distribution de l'énergie journalière** : elle n'est pas simplement asymétrique, elle a deux bosses. Au nord, un pic vers 3 kWh/m²/jour et une queue de jours très sombres. Au sud, deux pics (vers 4 à 4,7 et vers 7 à 7,5). La bosse basse vient en partie de l'hiver (jours courts), pas seulement des nuages. Conséquence : évaluer le modèle aussi par saison et par ville, pas seulement avec une moyenne globale.

## 3. Nuages

Plus il y a de nuages, moins il y a de rayonnement, pour les quatre colonnes (mesure à midi, 11 h à 13 h UTC).

| Variable | Rayonnement avec peu de nuages | Avec 90 à 100 % de nuages | Baisse |
|---|---|---|---|
| Couverture totale | environ 780 W/m² | environ 545 W/m² | environ -30 % |
| Couche basse | environ 750 W/m² | environ 435 W/m² | environ -42 % |
| Couche moyenne | environ 750 W/m² | environ 350 W/m² | environ -53 % |
| Couche haute | environ 745 W/m² | environ 580 W/m² | environ -22 % |

La couche **moyenne** pèse le plus, puis la basse, puis la haute. La baisse est globalement régulière, avec une chute plus forte dans la dernière tranche (90 à 100 %). Les pentes étant très différentes d'une couche à l'autre, il faut garder les trois couches comme variables séparées.

*(Note : les valeurs lues sur les graphiques sont approximatives, les chiffres exacts sont dans le notebook).*

## 4. Comparaison des villes

| Ville | Énergie (kWh/m²/jour) | Indice de clarté moyen | Jours dégagés | Pluie par an |
|---|---|---|---|---|
| Dakhla | 6,20 | 0,87 | 67,5 % | 37 mm |
| Laayoune | 5,88 | 0,84 | 55,3 % | 38 mm |
| Ouarzazate | 5,85 | 0,82 | 45,7 % | 102 mm |
| Al Hoceima | 5,11 | 0,79 | 42,4 % | 302 mm |
| Tanger | 5,11 | 0,78 | 42,5 % | 627 mm |

Les sites du sud reçoivent plus d'énergie et ont un ciel plus régulier. Le nord est plus nuageux (40 % de nuages à Tanger, 25 % à Dakhla) et plus variable, avec plus de jours très couverts (environ 8 % à Tanger contre moins de 1 % à Dakhla et Laayoune).

Hypothèse à vérifier : Ouarzazate reçoit plus d'énergie que son pourcentage de jours dégagés ne le laisse penser, ce qui s'explique peut-être par son altitude (pression moyenne de 892 hPa contre environ 1 010 ailleurs).

Autre point à creuser : à Dakhla, le rayonnement baisse en juin et juillet alors que Tanger continue de monter. Les graphiques ne l'expliquent pas.

## 5. Température, humidité, vent (boîtes à moustaches)

| Ville | Température médiane | Humidité médiane | Vent médian |
|---|---|---|---|
| Al Hoceima | environ 18 °C | environ 72 % | environ 8 km/h |
| Dakhla | environ 20,5 °C | environ 71 % | environ 24 km/h |
| Laayoune | environ 20 °C | environ 66 % | environ 20,5 km/h |
| Ouarzazate | environ 19 °C | environ 30 % | environ 7,5 km/h |
| Tanger | environ 18 °C | environ 79 % | environ 13,5 km/h |

- **Ouarzazate** (intérieur) a l'écart de température le plus large : la boîte va d'environ 12 à 26 °C, et elle a la valeur la plus froide (-5,1 °C). Son humidité est bien plus faible que celle des autres villes (médiane autour de 30 % contre 66 à 79 %).
- **Les températures les plus élevées ne sont pas à Ouarzazate** : les valeurs extrêmes (jusqu'à 46,8 °C) viennent de Laayoune, puis de Dakhla (environ 44 °C). Ouarzazate monte seulement vers 42 °C. Ces pics isolés sont peut-être liés aux épisodes de vent chaud et sec (Chergui), mais c'est une hypothèse que les données ne prouvent pas.
- **Vent** : plus fort sur la côte atlantique du sud (Dakhla et Laayoune) que sur la côte nord (Tanger, Al Hoceima) et à Ouarzazate. Al Hoceima et Ouarzazate ont une médiane faible mais beaucoup de valeurs extrêmes (jusqu'à environ 57 et 51 km/h). Le maximum global est de 59,4 km/h, loin du seuil de 150 km/h prévu dans la règle Q11.
- **Conséquence pour les règles de qualité** : les points isolés sont nombreux (température, humidité basse et vent), ce qui confirme qu'un seuil serré donnerait de fausses alertes. D'où des seuils larges (par exemple -15 à 55 °C pour la température, alors que l'observé va de -5,1 à 46,8 °C).

## 6. Jours sombres sans nuages (piste poussière)

Aucun jour ne correspond aux critères (clarté journalière inférieure à 0,6 et nuages moyens inférieurs à 20 %). Les données ne montrent donc pas d'épisode de poussière : la source (une réanalyse météo ERA5) les représente probablement mal. Avant de conclure, on peut assouplir les seuils (par exemple clarté inférieure à 0,7 et nuages inférieurs à 30 %). La vraie piste est l'API de qualité de l'air d'Open-Meteo, prévue en semaine 4.

## 7. Corrélations

Les heures de jour (9 h à 15 h UTC), corrélation avec le rayonnement : `clear_sky_p95` 0,90, `clearness` 0,62, température 0,61, heure 0,53, humidité -0,43, couverture nuageuse -0,36. La température suit surtout l'heure et la saison, elle ne cause pas le rayonnement.

**Attention :** `clear_sky_p95` et `clearness` sont calculés à partir du rayonnement observé, donc elles contiennent la réponse. Elles servent à comprendre les données, mais ne doivent **pas** être des variables d'entrée du modèle. Pour le modèle, il faudra une enveloppe de ciel clair calculée à partir de la position du soleil (pvlib).

## 8. Baselines : les chiffres à battre (heures de jour 7 h à 17 h UTC)

| Ville | nMAE persistance J-1 | nMAE climatologie | MAE persistance (W/m²) |
|---|---|---|---|
| Dakhla | 6,4 % | 6,7 % | 33,8 |
| Laayoune | 8,9 % | 9,2 % | 45,0 |
| Ouarzazate | 9,8 % | 10,4 % | 50,7 |
| Tanger | 13,7 % | 14,0 % | 61,4 |
| Al Hoceima | 14,6 % | 14,7 % | 65,8 |

La persistance est mauvaise quand le ciel change d'un jour à l'autre (nord) et meilleure dans les zones très dégagées (sud). La climatologie ne fait pas mieux que la persistance, alors qu'elle est calculée sur toutes les années (donc légèrement optimiste).

Pour un skill score de 0,20 par rapport à la persistance, il faudrait une MAE d'environ 27 W/m² à Dakhla et d'environ 53 W/m² à Al Hoceima.

## 9. Variables à créer (jour 4 et semaine 3)

- Heure et jour de l'année en sinus et cosinus (encodage cyclique).
- Angle du soleil et enveloppe de ciel clair calculés avec pvlib (pas à partir du rayonnement observé).
- Interactions entre l'heure et les nuages, et entre les couches de nuages.

## 10. Règles de qualité à implémenter dans dbt (jour 4)

Voir `docs/regles_qualite.md` (règles Q1 à Q16). Principe : ce sont des garde-fous contre les valeurs absurdes, avec une marge au-delà du maximum observé pour ne pas bloquer le pipeline sur un événement météo rare mais réel. Exemple : température maximale observée 46,8 °C, seuil à 55 °C.

## Limites connues des données

- **Fuseau horaire** : Les heures sont en UTC (le Maroc est en général à UTC+1).
- **Référence temporelle mixte** : Le rayonnement et la précipitation sont des moyennes (ou sommes) de l'heure *précédente*, tandis que les autres variables (température, nuages, vent) sont instantanées à l'heure indiquée. Les variables d'une même ligne n'ont donc pas la même référence de temps. (Conséquence pour la semaine 3 : l'angle du soleil avec pvlib devra être calculé au milieu de l'heure, pas à l'heure pile).
- **Résolution spatiale** : Les données viennent d'une réanalyse (ERA5 et ERA5-Land) sur une grille de 9 à 25 km. Chaque ville correspond à une "maille" (un pixel), et non à une mesure exacte sur le site de la centrale.
- **Poussière** : Les épisodes de poussière (Chergui) sont probablement mal représentés par la réanalyse (à vérifier), ce qui explique qu'aucun jour sombre sans nuages n'ait été détecté.
- **Pas de production réelle** : Il n'y a pas de mesure de production des centrales ; le rayonnement sert de proxy pour l'énergie solaire.
- **Cohérence des nuages** : Les couches de nuages sont incohérentes dans 1,42 % des lignes d'origine (règle Q15). C'est une propriété de la source, pas une erreur du pipeline.