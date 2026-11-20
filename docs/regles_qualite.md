# Règles de qualité des données

Source : `notebooks/01_exploration.ipynb`, exécuté sur les données Open-Meteo de 5 villes marocaines, 2015 à 2024 (438 360 lignes, une par ville et par heure, heures en UTC).

## Principe

Ces règles sont des **garde-fous contre les valeurs absurdes** (erreur d'API, changement de format, panne de capteur), pas des filtres statistiques. Chaque seuil garde une marge au-delà de ce qui a été observé, pour ne pas bloquer le pipeline sur un événement météo rare mais réel.

Deux niveaux de sévérité :
- **error** : le test échoue et le pipeline s'arrête (rien n'est publié) ;
- **warn** : le test signale le problème sans bloquer.

## Règles

| ID | Règle | Seuil | Sévérité | Observé | Test dbt prévu |
|---|---|---|---|---|---|
| Q1 | Une ligne par ville et par heure | aucun doublon sur (ville, heure) | error | 0 doublon | test singulier |
| Q2 | Série continue | 24 lignes par jour et par ville | error | 18 265 jours-villes sur 18 265 | test singulier |
| Q3 | Volume par ville et par an | 8 760 lignes (8 784 si année bissextile) | error | conforme sur les 50 fichiers | test singulier |
| Q4 | Pas de valeur manquante | `not_null` sur ville, heure et les 11 variables | error | 0 manquante | `not_null` |
| Q5 | Rayonnement | 0 à 1 400 W/m² | error | 0,0 à 1 095,0 | test singulier |
| Q6 | Pas de rayonnement la nuit | au plus 1 W/m² entre 0 h et 3 h UTC | error | maximum 0,00 dans les 5 villes | test singulier |
| Q7 | Température | -15 à 55 °C | error | -5,1 à 46,8 | test singulier |
| Q8 | Humidité relative | 0 à 100 % | error | 2 à 100 | test singulier |
| Q9 | Pression de surface | 800 à 1 100 hPa | error | 872,6 à 1 033,0 | test singulier |
| Q10 | Couverture nuageuse (4 colonnes) | 0 à 100 % | error | 0 à 100 | test singulier |
| Q11 | Vitesse du vent | 0 à 150 km/h | error | 0,0 à 59,4 | test singulier |
| Q12 | Direction du vent | 0 à 360 degrés | error | 0 à 360 | test singulier |
| Q13 | Précipitation | 0 à 50 mm/h | error | 0,0 à 18,2 | test singulier |
| Q14 | Villes autorisées | Ouarzazate, Laayoune, Dakhla, Tanger, Al Hoceima | error | 5 villes | `accepted_values` |
| Q15 | Cohérence des couches de nuages | alerte si plus de 5 % des lignes ont une couverture totale inférieure à la couche la plus épaisse (tolérance 1 point) | **warn** | 1,42 % | test singulier avec sévérité `warn` |
| Q16 | Fraîcheur des données | à définir avec l'exécution quotidienne (semaine 4) | warn | non applicable pour l'instant | `source freshness` |

## Justifications à retenir

- **Pourquoi des seuils larges (ex: -15 à 55 °C) ?** 
  Les seuils sont des garde-fous contre les pannes techniques, pas des filtres météo. La température maximale observée est de 46,8 °C, mais j'ai fixé le seuil à 55 °C. Si je mettais 48 °C, une vraie canicule au Maroc bloquerait le pipeline et empêcherait la publication des prévisions. Un seuil trop serré crée de fausses alertes (faux positifs). Je garde donc une marge de sécurité physique.
  
- **Pourquoi la règle Q15 (cohérence des nuages) est un simple avertissement (`warn`) ?** 
  Dans les données d'origine, 1,42 % des lignes violent cette règle (la couverture totale est inférieure à la couche la plus épaisse). Ce n'est pas une erreur de notre code d'ingestion, mais une imperfection de la source Open-Meteo. Si je mettais cette règle en `error`, le pipeline s'arrêterait systématiquement à chaque exécution. En la passant en `warn`, je garde la donnée mais je sais qu'il faut la surveiller.
  
- **Pourquoi le rayonnement nocturne (Q6) a un seuil de 1 W/m² et non de 0 ?** 
  On tolère une infime valeur (1 W/m²) pour absorber les erreurs d'arrondi de l'API ou les effets de bord au crépuscule. En revanche, si on observait 50 W/m² à 2 h du matin, cela signifierait clairement un décalage de fuseau horaire ou une panne de capteur, et le test bloquerait.

## Limites connues des données

- **Fuseau horaire** : Les heures sont en UTC (le Maroc est en général à UTC+1).
- **Référence temporelle mixte** : Le rayonnement et la précipitation sont des moyennes (ou sommes) de l'heure *précédente*, tandis que les autres variables (température, nuages, vent) sont instantanées à l'heure indiquée. Les variables d'une même ligne n'ont donc pas la même référence de temps. (Conséquence pour la semaine 3 : l'angle du soleil avec pvlib devra être calculé au milieu de l'heure, pas à l'heure pile).
- **Résolution spatiale** : Les données viennent d'une réanalyse (ERA5 et ERA5-Land) sur une grille de 9 à 25 km. Chaque ville correspond à une "maille" (un pixel), et non à une mesure exacte sur le site de la centrale.
- **Poussière** : Les épisodes de poussière (Chergui) sont probablement mal représentés par la réanalyse (à vérifier), ce qui explique qu'aucun jour sombre sans nuages n'ait été détecté.
- **Pas de production réelle** : Il n'y a pas de mesure de production des centrales ; le rayonnement sert de proxy pour l'énergie solaire.
- **Cohérence des nuages** : Les couches de nuages sont incohérentes dans 1,42 % des lignes d'origine (règle Q15). C'est une propriété de la source, pas une erreur du pipeline.

## Règles qui ne sont pas des règles de qualité

Les variables calculées à partir du rayonnement observé (indice de clarté, enveloppe de ciel dégagé) servent à comprendre les données. Elles ne doivent pas être utilisées comme variables d'entrée du modèle : elles contiendraient la réponse.