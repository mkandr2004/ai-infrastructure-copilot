# Diagnostic d’une utilisation mémoire élevée sous Linux

## Symptômes

Une utilisation mémoire élevée peut ralentir les applications, provoquer une utilisation importante du swap ou déclencher le mécanisme OOM Killer de Linux.

Une valeur élevée n’indique pas toujours un incident, car Linux utilise volontairement une partie de la mémoire disponible pour les caches.

## Vérifications initiales

La commande suivante affiche la mémoire totale, utilisée, disponible et le swap :

    free -h

La colonne `available` est généralement plus utile que la colonne `free` pour estimer la mémoire réellement encore utilisable.

Pour observer l’évolution de la mémoire :

    vmstat 1 5

## Recherche des processus consommateurs

La commande suivante classe les processus selon leur consommation mémoire :

    ps -eo pid,comm,%mem,rss --sort=-%mem | head

La colonne `RSS` représente approximativement la mémoire physique actuellement utilisée par chaque processus.

Il faut vérifier si la consommation augmente continuellement ou reste stable.

## Causes fréquentes

Les causes possibles comprennent une charge applicative importante, une fuite mémoire, un cache applicatif trop grand, un nombre excessif de processus ou une configuration insuffisante.

Une utilisation croissante du swap peut indiquer une pression mémoire, mais doit être interprétée avec l’activité réelle de la machine.

## Vérification du OOM Killer

Le noyau Linux peut arrêter un processus lorsque la mémoire devient insuffisante.

Les événements récents peuvent être recherchés avec :

    journalctl -k --since "1 hour ago" | grep -i -E "out of memory|killed process"

La présence d’un événement OOM doit être rapprochée de l’heure de l’incident et du processus concerné.

## Précautions

Ne pas arrêter un processus uniquement parce qu’il utilise beaucoup de mémoire.

Identifier son rôle et observer l’évolution de sa consommation avant une intervention.

Ne pas vider les caches Linux automatiquement sans comprendre l’origine du problème.
