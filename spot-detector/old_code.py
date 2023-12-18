from main import check_img_count
from process_chains import count_spots_first_method
from pathlib import Path
import numpy as np
import csv


def make_complete_csv(chemin_tableur: str, dossier_d_images: str, profondeurs: list, format_nom_image):
	# 1) Créer un tableau numpy d'[ENTIERS] à 3 dimensions de forme (n_dossiers, n_profondeurs, 2):
	sous_dossiers = sorted([e for e in Path(dossier_d_images).iterdir() if e.is_dir()])
	noms_sous_dossiers = [folder.name for folder in sous_dossiers]
	erreur, nombre_d_images = check_img_count(len(profondeurs), sous_dossiers)
	if erreur:
		print(f"Erreur : {len(profondeurs)} images étaient attendues dans chaque dossier :")
		for e in noms_sous_dossiers:
			print(e, end='\t')
			if len(e) < 4:
				print("\t", end='')
		print("")
		for e in nombre_d_images:
			print(e, end="\t\t")
		print("")
		input("Appuyez sur [Enter] pour continuer ou [ctrl] + [C] pour arrêter.")
	
	tableau_entiers = np.ndarray(shape=[len(sous_dossiers), len(profondeurs), 2])
	
	# Remplir le tableau :
	print("Début du traitement des images :")
	for i, dossier in enumerate(sous_dossiers):
		for j, prof in enumerate(profondeurs):
			print(f"dossier {i + 1}/{len(sous_dossiers)}, image {j + 1}/{len(profondeurs)}")
			images = [i for i in dossier.glob(format_nom_image(prof))]
			if len(images) == 1:
				tableau_entiers[i, j, :] =\
					count_spots_first_method(str(images[0]))
			else:
				tableau_entiers[i, j, :] = (0, 0)
	print("\nImages traitées ! calcul des pourcentages...")
	
	tableau_pourcentages = convert_tableau(tableau_entiers)
	tableau_nombres = np.ndarray(shape=tableau_pourcentages.shape)
	tableau_nombres[:, :, 0:2] = tableau_entiers
	tableau_nombres[:, :, 2] = tableau_entiers.sum(axis=2)
	
	make_csv_old(
		chemin_tableur,
		tableau_pourcentages,
		noms_sous_dossiers,
		profondeurs
	)
	make_csv_old(
		"/Users/Louis/Desktop/table_nombres.csv",
		tableau_nombres,
		noms_sous_dossiers,
		profondeurs
	)


def run_sequence(path, file_name):
	with open(Path(f'/Users/Louis/Desktop/{file_name}.csv'), 'w', newline='') as tableur:
		writer = csv.writer(tableur, dialect='unix')
		writer.writerow(['image name', 'orange count', 'green count'])
		for img_path in Path(path).glob('*.JPG'):
			path_str = str(img_path)
			orange_count, green_count = count_spots_first_method(path_str)
			writer.writerow([Path(path_str).name, orange_count, green_count])


def make_csv_old(chemin_tableur, tableau_pourcentages, noms_sous_dossiers, profondeurs):
	# À partir de ce tableau, créer un fichier CSV.
	with open(chemin_tableur, "w", newline='') as tableur:
		couleur = ["Orange", "Vert", "Orange + Vert"]
		writer = csv.writer(tableur, dialect='unix')
		# On crée 3 tableaux de [POURCENTAGES] À 2 dimensions :
		for i in range(3):
			writer.writerow([couleur[i]] + [] * (len(noms_sous_dossiers)))
			writer.writerow(["profondeur"] + noms_sous_dossiers)
			for j, prof in enumerate(profondeurs):
				writer.writerow([prof] + list(tableau_pourcentages[:, j, i]))


def convert_tableau(tab_ent):
	# Faire un tableau numpy de [POURCENTAGES] à 3 dimensions de forme (n_dossiers, n_profondeurs, 3):
	x, y, z = tab_ent.shape
	tableau_pourcentages = np.ndarray(shape=[x, y, z + 1], dtype=np.double)
	tableau_pourcentages[:, :, 0:2] = tab_ent / tab_ent.sum(axis=1, keepdims=True)
	tableau_pourcentages[:, :, 2] = (tab_ent.sum(axis=2, keepdims=True) / tab_ent.sum(axis=(1, 2), keepdims=True))[:, :, 0]
	tableau_pourcentages *= 100
	return tableau_pourcentages


def crop_zeros(array: np.ndarray, pad=0) -> np.ndarray | None:
	"""
	Only for grayscale images :/
	"""
	if len(array.shape) == 2:
		raise NotImplementedError(f"expected input array to have shape (x, y), but has shape {array.shape}")
	
	max_per_row = array.max(axis=1, initial=0)
	max_per_col = array.max(axis=0, initial=0)
	min_row = -1
	max_row = array.shape[0] - 1
	for i, val in enumerate(max_per_row):
		if val != 0:
			max_row = i
			if min_row == -1:
				min_row = i
	if min_row == -1:
		return None
	min_col = -1
	max_col = array.shape[1] - 1
	for i, val in enumerate(max_per_col):
		if val != 0:
			max_col = i
			if min_col == -1:
				min_col = i
	if min_col == -1:
		return None
	
	pad_u = pad if min_row - pad > 0 else 0
	pad_d = pad if max_row + pad < array.shape[0] - 1 else 0
	pad_l = pad if min_col - pad > 0 else 0
	pad_r = pad if max_col + pad < array.shape[1] - 1 else 0
	
	return array[min_row - pad_u: max_row + pad_d, min_col - pad_l: max_col + pad_r]
