from collections.abc import Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from spot_detector.types import Array2D, ImageRGB, Bool2D

Color = tuple[int, int, int]

CYAN: Color = (0, 255, 255)
MAGENTA: Color = (255, 0, 255)

def visualize_detection(
    image_rgb: ImageRGB[np.uint16],
    image_quantized: Array2D[np.uint8],
    key_points: Sequence[cv2.KeyPoint],
    *,
    contour_thickness: int = 1,
    contour_opacity: float = 0.5,
    blob_opacity: float = 0.5,
    radius_factor: float = 0.8,
    fit_to_mask: bool = False,
    stretch_percentile: tuple[float, float] | None = None,
) -> ImageRGB[np.uint8]:
    _check_input_shapes(image_rgb, image_quantized)
    _check_bounds(contour_opacity, "contour_opacity")
    _check_bounds(blob_opacity, "blob_opacity")

    output = _rgb8_background(image_rgb, stretch_percentile)

    contours = _level_contours_mask(image_quantized, contour_thickness)
    _apply_color(output, contours, CYAN, contour_opacity)

    blobs = _mask_blobs(
        image_quantized,
        key_points,
        radius_factor=radius_factor,
        fit_to_mask=fit_to_mask,
    )
    _apply_color(output, blobs, MAGENTA, blob_opacity)

    keypoint_diagnostic(image_quantized, key_points)
    localize(image_quantized, key_points)

    return output


def _check_input_shapes(image_rgb: ImageRGB[np.uint16], image_quantized: Array2D[np.uint8]) -> None:
    if image_quantized.shape != image_rgb.shape[:2]:
        raise ValueError(f"Incompatible input shapes, got {image_rgb.shape[:2]} and {image_quantized.shape}")


def _check_bounds(valeur: float, name: str) -> None:
    if not 0.0 <= valeur <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {valeur}")


def _rgb8_background(
    image_rgb: ImageRGB[np.uint16],
    etirement_percentile: tuple[float, float] | None,
) -> ImageRGB[np.uint8]:
    """Convertit l'image source en 8 bits, avec etirement optionnel."""
    if etirement_percentile is None:
        return (image_rgb // 257).astype(np.uint8)

    bas, haut = etirement_percentile
    if not 0.0 <= bas < haut <= 100.0:
        raise ValueError(f"etirement_percentile doit verifier 0 <= bas < haut <= 100, recu {etirement_percentile}")

    low_bound: np.float64
    high_bound: np.float64
    low_bound, high_bound = np.percentile(image_rgb, (bas, haut))  # pyright: ignore[reportAny]
    if high_bound <= low_bound:
        return (image_rgb // 257).astype(np.uint8)

    etendue = float(high_bound - low_bound)
    normalise = (image_rgb.astype(np.float32) - float(low_bound)) / etendue
    return (np.clip(normalise, 0.0, 1.0) * 255.0).round().astype(np.uint8)


def _level_contours_mask(
    image_quantized: Array2D[np.uint8],
    thickness: int,
) -> Bool2D:
    """Trace le contour de chaque palier non nul de l'image quantifiee."""
    if thickness < 1:
        raise ValueError(f"epaisseur_contours doit valoir au moins 1, recu {thickness}")

    acc = np.zeros(image_quantized.shape, dtype=np.uint8)
    for value in np.unique(image_quantized):  # pyright: ignore[reportAny]
        if value == 0:
            continue
        level: Array2D[np.uint8] = (image_quantized == value).astype(np.uint8)  # pyright: ignore[reportAny]
        contours, _ = cv2.findContours(
            level, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        _ = cv2.drawContours(acc, contours, -1, color=1, thickness=thickness)
    return acc.astype(bool)


def _mask_blobs(
    image_quantized: Array2D[np.uint8],
    key_points: Sequence[cv2.KeyPoint],
    *,
    radius_factor: float,
    fit_to_mask: bool,
) -> Bool2D:
    """Remplit le disque associe a chaque point cle retenu."""
    if radius_factor <= 0.0:
        raise ValueError(
            f"facteur_rayon doit etre strictement positif, recu {radius_factor}"
        )

    acc = np.zeros(image_quantized.shape, dtype=np.uint8)
    for point in key_points:
        x_axis, y_axis = point.pt
        rayon = max(1, int(round(point.size * radius_factor / 2.0)))
        _ = cv2.circle(
            acc,
            (int(round(x_axis)), int(round(y_axis))),
            rayon,
            color=1,
            thickness=-1,
        )

    mask = acc.astype(bool)
    if fit_to_mask:
        mask &= image_quantized > 0
    return mask


def _apply_color(
    image: ImageRGB[np.uint8],
    mask: Bool2D,
    color: Color,
    opacity: float,
) -> None:
    if opacity == 0.0 or not mask.any():
        return
    if opacity == 1.0:
        image[mask] = color
        return

    hue = np.asarray(color, dtype=np.float32)
    zone = image[mask].astype(np.float32)
    blend = (1.0 - opacity) * zone + opacity * hue
    image[mask] = blend.round().clip(0, 255).astype(np.uint8)


def keypoint_diagnostic(image_quantized: Array2D[np.uint8], key_points: Sequence[cv2.KeyPoint]):
    _n, _, _stats, centroids = cv2.connectedComponentsWithStats(
        (image_quantized > 0).astype(np.uint8), connectivity=8
    )
    refs = centroids[1:]
    pts = np.array([p.pt for p in key_points])
    print("forme du masque :", image_quantized.shape[::-1], "(largeur, hauteur)")
    print(f"{len(refs)} composantes, {len(pts)} points détectés")
    for name, try_ in (
        ("brut", pts),
        ("axes échangés", pts[:, ::-1]),
    ):
        d: NDArray[np.float64] = np.linalg.norm(try_[:, None, :] - refs[None, :, :], axis=2)  # pyright: ignore[reportAny]
        candidates = d.min(axis=1)
        vectors = try_ - refs[d.argmin(axis=1)]
        print(f"{name:15} median offset {np.median(candidates):7.1f} px  "
              + f"average offset ({vectors[:,0].mean():+.1f}, {vectors[:,1].mean():+.1f})  "
              + f"spread ({vectors[:,0].std():.1f}, {vectors[:,1].std():.1f})")
        d = np.linalg.norm(pts[:, None, :] - refs[None, :, :], axis=2)
        plus_proche = d.argmin(axis=1)
        _, effectifs = np.unique(plus_proche, return_counts=True)
        seuls = np.isin(plus_proche, np.flatnonzero(effectifs == 1))
        print(f"{seuls.sum()} points isolés, écart médian {np.median(d.min(axis=1)[seuls]):.2f} px")

def localize(image_quantized: Array2D[np.uint8], key_points: Sequence[cv2.KeyPoint]):
    h, w = image_quantized.shape
    pts = np.array([p.pt for p in key_points])
    n, _, _, _ = cv2.connectedComponentsWithStats(
        (image_quantized > 0).astype(np.uint8), connectivity=8
    )
    ys, xs = np.nonzero(image_quantized)
    in_frame = ((pts[:, 0] >= 0) & (pts[:, 0] < w)
                  & (pts[:, 1] >= 0) & (pts[:, 1] < h))
    pi = np.clip(pts.astype(int), [0, 0], [w - 1, h - 1])
    on_signal = image_quantized[pi[:, 1], pi[:, 0]] > 0

    print(f"masque {w}x{h}, {n - 1} composantes, {len(pts)} points")
    print(f"signal    x {xs.min()}..{xs.max()}"
        + f"   y {ys.min()}..{ys.max()}")
    print(f"points    x {pts[:,0].min():.0f}..{pts[:,0].max():.0f}"
        + f"   y {pts[:,1].min():.0f}..{pts[:,1].max():.0f}")
    print(f"dans le cadre : {in_frame.mean():.0%}   sur un pixel de signal : {on_signal.mean():.0%}")
