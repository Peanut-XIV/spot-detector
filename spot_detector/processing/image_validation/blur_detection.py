"""Chaine de detection de flou pour Spot Detector.

Une fonction par etape. Le flou est suppose homogene sur l'image (champ plan,
denivele < 1 mm), ce qui autorise une mesure scalaire unique plutot qu'une
mesure par particule. Le test n'est declenche que si le signal est assez
peuple ; sinon il renvoie l'etat NOT_APPLICABLE.

Le seuil de reference passe a assess_blur porte sur la variance du Laplacien
NORMALISE EN CONTRASTE. Il doit etre calibre sur une serie d'images nettes de
reference traitees par ce meme code, et n'est pas transferable tel quel.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast, override

import cv2
import numpy as np
from numpy import float64, integer, uint16
from numpy.typing import NDArray

# Fonction de labellisation deja disponible dans le projet. Adapter le chemin
# d'import a l'arborescence reelle.
#   label_image_fastest_uint16(img: NDArray[np.uint16],
#                              palette: NDArray[np.uint16]) -> NDArray[np.uint8]

from spot_detector.processing.transformations import convert_mat_uint16, label_img_fastest_uint16
from spot_detector.types import CommonInt_T, ImageRGB, ShadeTable, Bool2D, Double2D, NVec


# --- Alias de types --------------------------------------------------------


class BlurState(Enum):
    SHARP = auto()
    BLURRY = auto()
    NOT_APPLICABLE = auto()

    @override
    def __str__(self) -> str:
        match self:
            case BlurState.SHARP:
                return "BlurState(SHARP)"
            case BlurState.BLURRY:
                return "BlurState(BLURRY)"
            case BlurState.NOT_APPLICABLE:
                return "BlurState(NOT_APPLICABLE)"

@dataclass
class BlurResult:
    state: BlurState
    score: float | None   # variance du Laplacien normalise, None si non applicable
    channel: int          # canal retenu (0=B, 1=G, 2=R)
    n_particles: int      # nombre de composantes connexes de signal
    occupation: float     # fraction de la ROI occupee par le signal

    @override
    def __str__(self):
        msg = (
            "BlurResult("
            + f"state:{str(self.state)},"
            + f"score:{self.score},"
            + f"channel:{["blue", "green", "red"][self.channel]},"
            + f"n_particles:{self.n_particles},"
            + f"occupation:{self.occupation}"
        )
        return msg


# --- Etape 1 : choix du canal porteur du signal ----------------------------

def select_signal_channel(hue_table: ShadeTable) -> int:
    """Retourne le canal (0=B, 1=G, 2=R) qui separe le mieux les teintes de
    signal (category != 0) du fond (category == 0). On mesure la nettete sur ce
    seul canal plutot que sur une luminance globale, ou le signal serait dilue
    dans le fond."""
    rgb, category = hue_table[:, :3].astype(np.float64), hue_table[:, 3]
    is_signal: NVec[np.bool] = cast(NVec[np.bool], category != 0)

    if not np.any(is_signal):
        raise ValueError("La table de teintes ne contient aucune teinte de signal.")

    signal_mean: NVec[float64] = rgb[is_signal].mean(axis=0, dtype=float64)

    background_mean: NDArray[float64]
    if np.any(~is_signal):
        background_mean = rgb[~is_signal].mean(axis=0)
    else:
        background_mean = np.zeros(3, dtype=np.float64)

    return int(np.argmax(signal_mean - background_mean))


# --- Etape 2 : region utile ------------------------------------------------

def get_roi_mask(img: ImageRGB[uint16], roi: Bool2D | None) -> Bool2D:
    """Renvoie le masque de la region utile. A defaut de ROI fournie, on retient
    le plus grand cercle inscrit dans l'image, afin d'exclure le rebord de la
    boite de Petri, qui est un bord franc large bande qui fausserait la mesure."""
    if roi is not None:
        return roi

    h, w, _ = img.shape
    yy, xx = np.ogrid[:h, :w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    radius = min(h, w) / 2.0
    return ((yy - cy) ** 2 + (xx - cx) ** 2) <= radius ** 2


# --- Etape 3 : masque du signal --------------------------------------------

def compute_signal_mask(img: ImageRGB[uint16], hue_table: ShadeTable, roi_mask: Bool2D) -> Bool2D:
    """Segmente les pixels de luminophores via la labellisation K-moyennes, puis
    restreint a la ROI. Une teinte est du signal si sa categorie est non nulle."""
    palette = np.ascontiguousarray(hue_table[:, :3])              # N x 3, uint16
    labels = label_img_fastest_uint16(img, palette)               # H x W, index de teinte
    is_signal_hue = cast(NDArray[np.bool], hue_table[:, 3] != 0)  # N, bool
    signal_mask = is_signal_hue[labels]                           # H x W, bool
    return signal_mask & roi_mask


# --- Etape 4 : dilatation en collier ---------------------------------------

def dilate_mask(mask: Bool2D, radius_px: int) -> Bool2D:
    """Dilate le masque d'un collier de rayon donne. L'information de nettete est
    dans le flanc de la particule, pas dans son coeur (un plateau quasi plat) :
    le collier recupere cette transition crete -> fond."""
    if radius_px <= 0:
        return mask
    ksize = 2 * radius_px + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    dilated = cv2.dilate(mask.astype(np.uint8), kernel)
    return dilated.astype(bool)


# --- Etape 5 : estimation de densite ---------------------------------------

def estimate_density(signal_mask: Bool2D, roi_mask: Bool2D) -> tuple[int, float]:
    """Renvoie (nombre de particules, taux d'occupation de la ROI). Le nombre de
    composantes connexes sert au controle de fiabilite statistique ; le taux
    d'occupation sert de proxy au risque de fusion entre voisins."""
    n_labels, _ = cv2.connectedComponents(signal_mask.astype(np.uint8), connectivity=8)
    n_particles = max(n_labels - 1, 0)  # on retire le fond
    roi_area = int(np.count_nonzero(roi_mask))
    occupation = float(np.count_nonzero(signal_mask)) / roi_area if roi_area else 0.0
    return n_particles, occupation


def is_applicable(
    n_particles: int,
    occupation: float,
    min_particles: int,
    min_occupation: float,
) -> bool:
    """Le test n'est pertinent que si le signal est assez peuple : trop peu de
    particules rend l'estimation instable, et un signal trop epars rend la
    nettete secondaire, faute de fusion possible entre voisins."""
    return n_particles >= min_particles and occupation >= min_occupation


# --- Etape 6 : normalisation de contraste ----------------------------------

def contrast_normalized_channel(
    img: ImageRGB[uint16],
    channel: int,
    signal_mask: Bool2D,
    roi_mask: Bool2D,
    bg_percentile: float = 5.0,
    peak_percentile: float = 99.0,
) -> Double2D:
    """Normalise le canal par sa dynamique robuste (fond -> crete du signal).
    Sans cette etape, la variance du Laplacien croit avec le carre du contraste,
    et une particule plus brillante paraitrait plus nette a nettete egale."""
    ch = img[:, :, channel].astype(float64)
    roi_values = ch[roi_mask]
    signal_values = ch[signal_mask]
    if signal_values.size == 0 or roi_values.size == 0:
        return np.zeros_like(ch)
    background = float(np.percentile(roi_values, bg_percentile))
    peak = float(np.percentile(signal_values, peak_percentile))
    dynamic = max(peak - background, 1.0)
    return (ch - background) / dynamic


# --- Etape 7 : operateur de nettete ----------------------------------------

def sharpness_score(norm_channel: Double2D, eval_mask: Bool2D) -> float:
    """Variance du Laplacien, restreinte au masque d'evaluation. Le Laplacien est
    calcule sur toute l'image pour eviter les artefacts de bord du masque, puis
    la variance n'est mesuree que sur les pixels retenus."""
    laplacian = cv2.Laplacian(norm_channel, cv2.CV_64F, ksize=3)
    values = laplacian[eval_mask]
    if values.size == 0:
        return 0.0
    return float(values.var(dtype=np.float64))


# --- Orchestration ---------------------------------------------------------

def assess_blur(
    img: ImageRGB[uint16],
    hue_table: ShadeTable,
    reference_threshold: float,
    roi: Bool2D | None = None,
    expected_diameter_px: int = 10,
    collar_fraction: float = 0.5,
    min_particles: int = 30,
    min_occupation: float = 1e-3,
) -> BlurResult:
    """Detecte un flou homogene sur une image RGB 16 bits.

    reference_threshold : seuil sur la variance du Laplacien normalise, calibre
        sur la serie nette de reference avec ce meme code.
    expected_diameter_px : diametre attendu de particule ; a deriver de la
        convention en fraction du cercle inscrit, non code en dur.
    collar_fraction : rayon du collier de dilatation, en fraction du diametre.
    min_particles, min_occupation : seuils de bascule vers NOT_APPLICABLE.
    """
    channel = select_signal_channel(hue_table)
    roi_mask = get_roi_mask(img, roi)
    signal_mask = compute_signal_mask(img, hue_table, roi_mask)

    n_particles, occupation = estimate_density(signal_mask, roi_mask)
    if not is_applicable(n_particles, occupation, min_particles, min_occupation):
        return BlurResult(BlurState.NOT_APPLICABLE, None, channel, n_particles, occupation)

    collar_px = max(int(round(expected_diameter_px * collar_fraction)), 1)
    eval_mask = dilate_mask(signal_mask, collar_px) & roi_mask

    norm = contrast_normalized_channel(img, channel, signal_mask, roi_mask)
    score = sharpness_score(norm, eval_mask)

    state = BlurState.SHARP if score >= reference_threshold else BlurState.BLURRY
    return BlurResult(state, score, channel, n_particles, occupation)


if __name__ == "__main__":
    import sys
    from spot_detector.model.project import Project

    img = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR_BGR | cv2.IMREAD_ANYDEPTH)

    if img is None:
        print(f"Failed reading image at: {sys.argv[1]}")
        sys.exit(0)

    if not np.isdtype(img.dtype, integer):
        print(f"Wrong image datatype: {img.dtype}")
        sys.exit(0)

    img = cast(NDArray[CommonInt_T], img)

    image_u16 = convert_mat_uint16(img)

    settings = Project.from_path(sys.argv[2])
    shades = settings.configuration.shades
    table = np.array([s.as_row() for s in shades], dtype=uint16)
    ref_th = float(sys.argv[3])
    roi = None
    expected_diameter = int(sys.argv[4])

    res = assess_blur(image_u16, table, ref_th, roi, expected_diameter)

    print(res)
