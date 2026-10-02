# Diagnostic d’une utilisation CPU élevée sous Linux

## Symptômes

Une utilisation CPU durablement élevée peut ralentir les applications, augmenter le temps de réponse et provoquer une accumulation de tâches. Une pointe courte n’indique pas forcément un incident.

## Vérifications initiales

Utiliser `uptime` pour consulter la charge moyenne de la machine.

Utiliser `top` ou `htop` pour observer l’utilisation globale du CPU et identifier les processus actifs.

La commande suivante classe les processus selon leur consommation CPU :

    ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head

## Interprétation de la charge

La charge moyenne doit être comparée au nombre de processeurs logiques.

Une charge de 4 sur une machine possédant 8 processeurs logiques n’a pas la même signification qu’une charge de 4 sur une machine possédant 2 processeurs logiques.

La commande `nproc` affiche le nombre de processeurs logiques disponibles.

## Questions à examiner

Vérifier si la consommation vient d’un seul processus ou de plusieurs processus.

Vérifier si l’augmentation est ponctuelle ou durable.

Vérifier si le processus concerné effectue un traitement attendu, une compilation, une sauvegarde ou une boucle anormale.

## Précautions

Ne pas arrêter un processus uniquement parce que son utilisation CPU est élevée.

Identifier son rôle, son propriétaire et son impact avant toute action.

Conserver les observations et l’heure de l’incident avant une intervention.
