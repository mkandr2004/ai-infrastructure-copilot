# Diagnostic de l’espace disque sous Linux

## Symptômes

Un disque presque plein peut empêcher l’écriture de fichiers, perturber les bases de données et provoquer l’échec de services.

Les messages « No space left on device » peuvent être causés par un manque d’espace ou par un épuisement des inodes.

## Vérification de l’espace

La commande suivante affiche l’utilisation des systèmes de fichiers :

    df -h

La colonne `Use%` indique le pourcentage d’espace utilisé.

Pour vérifier les inodes :

    df -i

## Recherche des répertoires volumineux

La commande suivante affiche la taille des principaux répertoires d’un emplacement :

    du -xhd1 /var 2>/dev/null | sort -h

L’option `-x` évite de traverser d’autres systèmes de fichiers.

Il faut ensuite examiner progressivement les répertoires les plus volumineux.

## Causes fréquentes

Les causes possibles comprennent des logs volumineux, des fichiers temporaires, des sauvegardes oubliées, des caches ou des données applicatives en croissance.

Un fichier supprimé peut encore occuper de l’espace s’il reste ouvert par un processus. La commande `lsof +L1` aide à détecter cette situation.

## Précautions

Ne pas supprimer arbitrairement des fichiers système ou des journaux.

Vérifier l’utilité, le propriétaire et la politique de conservation avant toute suppression.

Pour une base de données, utiliser les procédures propres au moteur plutôt que supprimer directement ses fichiers.
