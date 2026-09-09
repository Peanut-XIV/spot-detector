"""Calibration des parametres de detection de flou a partir d'une serie
d'images de reference nettes, si possible reparties sur la gamme de
concentration. Le collier est choisi pour minimiser la dependance a la densite ;
le seuil est place entre le signal net et un flou tout juste inacceptable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from math import sqrt

import cv2
import numpy as np
from numpy import uint16

import spot_detector.processing.image_validation.blur_detection as bd
from spot_detector.custom_types import Double2D, ImageRGB, ShadeTable, Bool2D
from typing import cast


# Champs de valeur plausibles : (min, max, defaut, unite, description).
PARAMETER_RANGES: dict[str, tuple[int | float, int | float, int | float, str, str]] = {
    "expected_diameter_px": (2, 30, 6, "px", "diametre attendu de particule"),
    "collar_fraction":      (0.3, 1.0, 0.5, "-", "rayon du collier en fraction du diametre"),
    "reference_threshold":  (0.02, 0.30, 0.10, "-", "variance Laplacien normalise, seuil net/flou"),
    "min_particles":        (10, 100, 30, "count", "nombre minimal de particules pour evaluer"),
    "min_occupation":       (1e-4, 1e-2, 1e-3, "fraction ROI", "occupation minimale du signal"),
}


@dataclass
class BlurCalibration:
    channel: int
    expected_diameter_px: int
    collar_fraction: float
    reference_threshold: float
    min_particles: int
    min_occupation: float
    chosen_collar_px: int
    dispersion_ratio: float                # max/min des scores nets au collier retenu
    sharp_scores: list[float] = field(default_factory=list)
    blurred_scores: list[float] = field(default_factory=list)
    occupations: list[float] = field(default_factory=list)
    n_particles: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def calibrate_blur(
    reference_images: Sequence[ImageRGB[uint16]],
    hue_table: ShadeTable,
    roi_masks: Sequence[Bool2D | None] | None = None,
    candidate_diameters_px: Sequence[int] = (2, 4, 6, 8, 10, 14, 20),
    collar_fraction: float = 0.5,
    reject_sigma: float = 1.5,
    min_particles: int = 30,
    occupation_safety: float = 0.5,
) -> BlurCalibration:
    """Derive expected_diameter_px, reference_threshold et le plancher
    d'applicabilite depuis une serie d'images nettes de reference."""
    if roi_masks is None:
        roi_masks = [None] * len(reference_images)
    channel = bd.select_signal_channel(hue_table)
    warnings: list[str] = []

    # Pre-calcul par image : ROI, masque signal, canal normalise, densite.
    rois : list[Bool2D] = []
    masks: list[Bool2D] = []
    norms: list[Double2D] = []
    occ: list[float] = []
    npart: list[int] = []

    for img, roi_in in zip(reference_images, roi_masks):
        roi = bd.get_roi_mask(img, roi_in)
        sm = bd.compute_signal_mask(img, hue_table, roi)
        n, o = bd.estimate_density(sm, roi)
        rois.append(roi)
        masks.append(sm)
        norms.append(bd.contrast_normalized_channel(img, channel, sm, roi))
        occ.append(o)
        npart.append(n)

    applicable = [i for i, n in enumerate(npart) if n >= min_particles]
    if not applicable:
        raise ValueError("Aucune image de reference assez peuplée pour calibrer.")
    if len(applicable) == 1:
        warnings.append("Une seule image exploitable : l'invariance en densité "
                        + "n'est pas vérifiable, collier laissé au defaut.")

    def collar_of(diam: int) -> int:
        return max(int(round(diam * collar_fraction)), 1)

    def score_at(i: int, collar: int) -> float:
        ev = bd.dilate_mask(masks[i], collar) & rois[i]
        return bd.sharpness_score(norms[i], ev)

    # Choix du collier : minimise le rapport max/min des scores nets.
    if len(applicable) >= 2:
        best: tuple[float, int, int] | None  = None
        for diam in candidate_diameters_px:
            c = collar_of(diam)
            s = [score_at(i, c) for i in applicable]
            lo = min(s)
            ratio = (max(s) / lo) if lo > 0 else float("inf")
            if best is None or ratio < best[0]:
                best = (ratio, diam, c)

        assert best is not None
        dispersion_ratio, exp_diam, collar = best

    else:
        exp_diam = int(PARAMETER_RANGES["expected_diameter_px"][2])
        collar = collar_of(exp_diam)
        dispersion_ratio = float("nan")

    # Scores nets au collier retenu, sur toutes les images applicables.
    sharp = [score_at(i, collar) for i in applicable]
    min_sharp = min(sharp)

    # Flou de reference : on floute chaque image et on recompte tout.
    blurred: list[float] = []
    for i in applicable:
        im = cast(ImageRGB[uint16], cv2.GaussianBlur(reference_images[i], (0, 0), reject_sigma))
        roi = rois[i]
        sm_b = bd.compute_signal_mask(im, hue_table, roi)
        norm_b = bd.contrast_normalized_channel(im, channel, sm_b, roi)
        ev_b = bd.dilate_mask(sm_b, collar) & roi
        blurred.append(bd.sharpness_score(norm_b, ev_b))
    max_blurred = max(blurred)

    # Seuil : moyenne geometrique entre net et flou de rejet.
    if max_blurred >= min_sharp:
        warnings.append("Recouvrement net/flou au sigma de rejet : seuil de "
                        + "repli a min_sharp/3, a valider sur du flou reel.")
        threshold = min_sharp / 3.0
    else:
        threshold = sqrt(min_sharp * max_blurred)

    # Plancher d'occupation : sous la moins peuplee des references valides.
    min_occ = occupation_safety * min(occ[i] for i in applicable)
    min_occ = float(np.clip(min_occ, *PARAMETER_RANGES["min_occupation"][:2]))  # pyright: ignore[reportAny]

    return BlurCalibration(
        # user input:
        collar_fraction=collar_fraction,
        min_particles=min_particles,

        # calibrated values:
        expected_diameter_px=int(exp_diam),
        reference_threshold=float(threshold),
        min_occupation=min_occ,
        chosen_collar_px=int(collar),

        # debug info:
        channel=channel,
        dispersion_ratio=float(dispersion_ratio),
        sharp_scores=[float(x) for x in sharp],
        blurred_scores=[float(x) for x in blurred],
        occupations=[float(occ[i]) for i in applicable],
        n_particles=[int(npart[i]) for i in applicable],
        warnings=warnings,
    )
