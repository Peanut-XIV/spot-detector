import csv
from process_chains import count_spots_first_method, count_spots_second_method
import numpy as np
from file_utils import (
    check_img_count,
    get_unprocessed_directories,
    match_dir_items,
    get_color_table_array
)


def make_progressive_csv(dossier_principal,
                         chemin_tableur,
                         profondeurs,
                         format_nom_image,
                         counting_algorithm,
                         color_table_path):
    # Vérifier l'existence de dossiers déjà traités
    csv_exists, dossiers =\
        get_unprocessed_directories(chemin_tableur, dossier_principal)
    if csv_exists:
        input(f"Avertissement : Le document {chemin_tableur} existe déjà.\n"
              "Appuyez sur [Enter] pour traiter les dossiers manquants ou "
              "[ctrl] + [C] pour arrêter.")
    # Vérifier la correspondence entre le nombre d'images à traiter et
    # le nombre d'images présentes dans chaque dossier
    doesnt_match, image_counts = check_img_count(len(profondeurs), dossiers)
    if doesnt_match:
        print(f"Avertissement : {len(profondeurs)} "
              "images étaient attendues dans chaque dossier :")
        for dossier in dossiers:
            nom = dossier.name
            print(nom, end='\t')
            if len(nom) < 4:
                print("\t", end='')
        print("")
        for n in image_counts:
            print(n, end="\t\t")
        print("")
        input("Appuyez sur [Enter] pour continuer "
              "ou [ctrl] + [C] pour arrêter.")
    
    # On ouvre le fichier csv où les données seront inscrites
    with open(chemin_tableur, "a", newline='') as tableur:
        writer = csv.writer(tableur)
        
        if not csv_exists:
            # On ajoute les noms de colonne
            liste_vide = [""] * (len(profondeurs) - 1)
            label_row_1 = ["", "Nbr Orange"] + liste_vide\
                + ["Nbr Vert"] + liste_vide\
                + ["Nbr Orange+Vert"] + liste_vide\
                + ["%ge Orange"] + liste_vide\
                + ["%ge Vert"] + liste_vide\
                + ["%ge Orange+Vert"] + liste_vide
            label_row_2 = ["Nom de dossier\\Profondeur"] + 6 * profondeurs
            writer.writerows((label_row_1, label_row_2))
            
        color_table = get_color_table_array(color_table_path)
        print("Début du traitement des images :")
        for i, dossier in enumerate(dossiers):
            tableau = np.ndarray(shape=(6, len(profondeurs)))
            images = sorted([i for i in dossier.iterdir() if i.is_file()])
            for j, prof in enumerate(profondeurs):
                print(f"\rdossier {i + 1}/{len(dossiers)},"
                      f"image {j + 1}/{len(profondeurs)}", end='')

                if format_nom_image == "" or format_nom_image == "*":
                    try:
                        resultats_recherche = [images[j]]
                    except IndexError:
                        resultats_recherche = []
                else:
                    resultats_recherche =\
                        match_dir_items(dossier, format_nom_image, prof)
                
                if len(resultats_recherche) >= 1:
                    output = str(resultats_recherche[0])
                    tableau[0:2, j] = counting_algorithm(output, color_table)
                else:
                    tableau[0:2, j] = (0, 0)
            # complétion du reste des lignes du tableau
            tableau[2, :] = tableau[0:2, :].sum(axis=0)
            total = tableau[0:3, :].sum(axis=1, keepdims=True)
            tableau[3:, :] = tableau[0:3, :] / total

            # écriture de la ligne dans le fichier
            writer.writerow([dossiers[i].name] + list(tableau.flat))
    print("\nTerminé !")


def main():
    chemin_dossier = input(
        "Chemin du dossier contenant les sous-dossiers d'image:\n"
        "/Users/Louis/Desktop/detection_de_points/data/"
        "par défaut\n"
    )
    chemin_tableur = input(
        "Chemin du document csv :\n"
        "/Users/Louis/Desktop/tableur/detection_de_points/tableur.csv "
        "par défaut\n"
    )
    profondeurs = input(
        "Liste de valeurs de profondeur "
        "(chaines de caractères séparées par un espace):\n"
        "'0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8 2.0' par défaut\n"
    )
    motif_nom_images = input(
        "Format du nom d'image en fonction de la profondeur:\n"
        r"((\w+)(_| )?)?$value( - |-)\d(\.\d)?(-\d)?\.(JPE?G|jpe?g|PNG|png)""\n"
        "par défaut pour correspondre à 'A15_3 0.2-0.4.JPG' ou une variation.\n"
        "'$value' est remplacé par la valeur de profondeur recherchée\n"
    )
    color_table_path = input(
        "chemin de la palette :\n"
    )
    if chemin_dossier == "":
        chemin_dossier = "/Users/Louis/Desktop/detection_de_points/data/"
    if chemin_tableur == "":
        chemin_tableur = "/Users/Louis/Desktop/detection_de_points/tableur.csv"
    if profondeurs == "":
        # [f"{i/10:1.1f}" for i in range(0, 22, 2)]
        liste_profondeurs = '0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8 2.0'.split(' ')
    else:
        liste_profondeurs = profondeurs.split(' ')
    if motif_nom_images == "":
        motif_nom_images =\
            r"((\w+)(_| )?)?$value( - |-)\d(\.\d)?(-\d)?\.(JPE?G|jpe?g|PNG|png)"
    if color_table_path == "":
        color_table_path = "palette_exp_manon.csv"
    make_progressive_csv(chemin_dossier,
                         chemin_tableur,
                         liste_profondeurs,
                         motif_nom_images,
                         count_spots_second_method,
                         color_table_path)


if __name__ == '__main__':
    main()
