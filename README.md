# Spot Detector

---

## Introduction :

Spot detector est un programme écrit en septembre et octobre 2023 dans l'objectif de compter des luminophores 
dans des boites de Pétri. Il utilise la bibliothèque OpenCV 2 ainsi que Numpy afin de manipuler des images. 

Ce programme prend en entrée un chemin de dossier de travail, un chemin de fichier csv, un ensemble
de valeurs de profondeur et un format de nom d'image. 

En retour, il produit un document CSV contenant le nombre de luminophores dans chacune des images présentes dans le 
dossier de travail, ainsi que le pourcentage par rapport au total dans un sous-dossier. Différentes colonnes 
correspondent à différentes profondeurs et couleurs de luminophores. 

Par exemple, le tableau peut prendre la forme suivante :

|                      | Nbr Orange |     |     |     | Nbr Vert |     | Nbr Orange+Vert |     | %ge Orange |     |
|:---------------------|-----------:|----:|----:|----:|---------:|----:|----------------:|----:|-----------:|----:|
| Dossier / Profondeur |        0.0 | 0.2 | ... | 2.0 |      0.0 | ... |             0.0 | ... |        0.0 | ... |
| experience1_rep10    |     11 200 | 234 | ... |   1 |      724 | ... |          11 924 | ... |  99.8753 % | ... |
| experience2_rep4     |      9 371 | 192 | ... |   0 |      338 | ... |           9 709 | ... |  98.7927 % | ... |
| experience2_rep5     |        ... | ... | ... | ... |      ... | ... |             ... | ... |        ... | ... |

---

## Installation :

Pour l'instant, l'installation du programme se fait en téléchargeant le projet
depuis github, puis en créant un environnement
virtuel dans lequel exécuter le programme.

### 1 - Télécharger

D'abord, vous devez choisir le répertoire dans lequel vous allez installer
l'application. Ça peut être votre bureau, mais je conseillerais un
répertoire qui lui est propre (ce dernier peut être dans le bureau).

Par exemple, créons  un dossier `applications-python` sur le bureau.
C'est ici que l'on installera l'application. Téléchargez ensuite le projet sur
votre ordinateur. Pour cela, cliquez sur le bouton vert en haut de la page
intitulé `code` puis sur `Download ZIP`.

Décompressez le dossier zip, copiez et collez-le dans le dossier 
`applications-python` précédamment créé. Vous devriez avoir une arborescence de
la forme suivante :

```
~/Bureau/applications-python/spot-detector-main/
                                        |- pyproject.toml
                                        |- README.md
                                        |- spot_detector
                                        |- spot_detector.egg-info
                                        |- tests
```

### 2 - Créer l'environnement virtuel (venv)

Maintenant que le projet est présent sur l'ordinateur, il faut créer
l'environnement virtuel dans lequel il sera exécuté. La création de cet
environnement nécessite Python (≥ 3.11 dans notre cas) et se fait de manière
différente sur Windows et sur MacOS / Linux.

#### Sur MacOS :

Ouvrez une fenêtre de terminal au dossier `spot-detector-main`. Pour cela,
ouvrez le dossier dans Finder, appuyez sur la touche `control` en
même temps de cliquer sur le nom de dossier et cliquez sur `Services` puis
`Nouveau terminal au dossier`. Vous êtes dans le terminal !

Maintenant, demandons quelle version de python est utilisée. Écrivez la
commande suivante et appuyez sur entrer:

```
python3 --version
```

* Si le terminal vous répond un message du genre :

```
zsh: command not found: python3
```

Alors c'est que vous n'avez pas Python (version 3.0 ou supérieure) d'installé.
Alternativement, si le terminal vous répond une version de Python inferieure à
3.11.7, votre version de python n'est pas assez rescente. Dans les deux cas,
il vous faudra installer Python 3.11.7, Python 3.12 ou la version la plus
rescente [ici](https://www.python.org/downloads/).

Une fois Python installé, retournez sur le terminal au dossier
`spot-detector-main` et entrez la commande suivante :

```
python3.11 -m venv venv
```

Puis

```
source venv/bin/activate
```
en



## Comment l'utiliser :


### Le dossier de travail

    Le dossier de travail doit avoir la structure suivante :

```
.../dossier_principal/
    |- test_1_replicat_1/
    |   |- image_1.jpeg
    |   |- image_2.jpeg
    |   |- image_3.jpeg
    |   |- ...
    |
    |- test_1_replicat_2/
    |   |- image_1.jpeg
    |   |- image_2.jpeg
    |   |- image_3.jpeg
    |   |- ...
    |
    |- ...
    |
    |- test_X_replicat_Y/
        |- image_1.jpeg
        |- image_2.jpeg
        |- image_3.jpeg
        |- ...
```

Les noms de dossiers, nom et formats d'images sont à but explicatif, l'important est qu'il n'y ait pas de 
sous-sous-dossier. Aussi, les images dans des arborescences supérieures ous inférieures ne seront pas traitées.
Ces sous-dossiers constituent le premier axe du tableau avec leur nom comme nom de ligne.

Par ailleurs, il est préférable que le nombre d'images soit le même dans chaque dossier. Sinon, il est possible 
d'utiliser une règle de tri que l'on verra plus tard. Dans ce cas, si une image manque, la valeur associée vaudra 0.

### Le chemin de fichier CSV

Le chemin de fichier CSV indique au programme où écrire les données qu'il vient de calculer. Il est recommandé 
d'indiquer un fichier inexistant et que l'extension soit ".csv". Cependant, si le programme a été interrompu et que 
certains dossiers n'ont pas encore été traités, il est possible de reprendre là où le programme s'est arrêté, il suffit 
d'indiquer le nom de chemin du fichier inachevé. Dans ce cas, il cherchera les noms de dossiers déjà présents et ne les 
traitera pas.

> ⚠️ **Avertissement** : Le programme ne fait pas la différence entre un fichier .csv quelconque et un fichier qu'il a 
> écrit lui-même. Pour cette raison, prenez garde à bien indiquer un fichier que vous êtes sûr de vouloir modifier !
> (Il n'y a pas de risque important en soi, le programme ne peut qu'ajouter des lignes, pas les réécrire ou les 
> supprimer.):

### Les valeurs de "profondeur"

Ces valeurs sont appelées profondeurs puisque c'est cette grandeur qui était indiquée dans l'expérience pour laquelle 
le programme a été écrit. Il s'agit du deuxième axe du tableau, les valeurs entrées serviront de noms de colonne. 
Elles sont également utilisées pour identifier les images par profondeur grâce à leur nom de fichier lors du traitement. 
Pour cela, il est important que ces valeurs soient cohérentes par rapport au nom des images et cohérent d'une image à 
l'autre.

Ces valeurs doivent être séparées par des espaces ou autres caractères similaires et peuvent contenir n'importe quel 
symbole du moment que ce n'est pas un espace, naturellement. Par ailleurs, les caractères doivent être 
compatibles avec votre système de fichiers.

### Le format de nom d'image

Le format de nom d'image est utile si les images, lorsqu'elles sont triées par profondeur, n'apparaissent pas dans 
l'ordre alphabétique. Sinon, ce format permet de prendre en compte le fait que certaines images soient manquantes. 
Ce format indique les parties invariantes, variantes ou qui contiennent la profondeur entre les noms 
de fichier des différentes images. Dans le cas pour lequel le programme a été écrit, les images avaient ce genre de nom :

`A6_1 0.4-0.6.JPG` `C30_4 0.6-0.8.JPG` `Cb2 0.0-0.2.JPG`

De manière générale, ils sont composés comme la séquence suivante :

| Caractères     | `A6_1`                                                                                            | ` `                                                                                           | `0.4`                                          | ` ` `-` ` `                                                                                                                                                                                                                                                         | `0.6`                                                                                    | `.JPG`             |
|----------------|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|--------------------|
| description    | une lettre majuscule, suivie ou non d'un chiffre, suivi ou non d'un tiret bas, suivi d'un chiffre | un espace                                                                                     | une valeur de profondeur                       | un tiret ou un tiret entouré d'espaces                                                                                                                                                                                                                              | la valeur de profondeur suivante                                                         | le nom d'extension |
| représentation | `*` permet de représenter n'importe quelle chaine de caractères                                   | À l'exception de `*` `?` `[` `]` `{` `}`, tous les caractères sont interprétés littéralement. | `{}` insert la valeur de profondeur recherchée | `[ -]` : Les symboles entre crochets indiquent un ensemble de possibilités pour un caractère. Attention, entre crochets, le tiret peut avoir un autre sens : `[a-zA-Z0-9]` indique n'importe quel caractère entre `a` et `z`, entre `A` et `Z` ou entre `0` et `9`. | `*` : on ne peut pas indiquer la valeur de profondeur de manière simple, d'où l'étoile.  | `.JPG`             |

Mis bouts-à-bouts, les éléments donnent la séquence suivante : `* {}[ -]*.JPG`.

> 📝 **Note** : La représentation de format est faite avec la méthode `str.format()` et la méthode de chemin `Path.glob()`.
Pour en savoir plus, voir la documentation de [Format String Syntax](https://docs.python.org/3/library/string.html#formatstrings) et 
[Path.glob](https://docs.python.org/3/library/pathlib.html?highlight=pathlib%20glob#pathlib.Path.glob) sur le site officiel 
du langage Python.


### Déroulement de l'exécution



---

## Le fonctionnement de la détection de point :
