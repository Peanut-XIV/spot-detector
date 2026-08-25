"""Configuration fingerprint, for result traceability.

Every row of the result file carries the fingerprint of the configuration that
produced it. That fingerprint is the digest of a canonical view of the project,
reduced to the parameters that actually affect the reported value.

What is kept next to the results is not that view but a copy of the project,
openable in the application: looking up the configuration behind a result is
mostly about loading it again and re-running a processing job, which a flattened
view would not allow. The fingerprint is therefore recomputed by rebuilding the
view from the project once it has been read back.

The session directory name carries the fingerprint, but the fingerprint does not
determine the snapshot contents: two projects differing only by their name or by
the path of their reference image share the same fingerprint. A snapshot thus
documents a computation configuration, not a project; its influential fields are
exact by construction, the others are indicative only. The result column naming
the project file is what records the actual origin.

Three properties are required for a fingerprint to change only when the
configuration changes:

- floats are quantized to a fixed number of significant digits, so that a round
  trip through a widget or through NumPy does not move the last bit;
- strings are normalized to NFC, since two Unicode spellings of the same accent
  would otherwise produce two different fingerprints, which happens routinely on
  macOS;
- keys are sorted and separators are fixed, dictionary order not being a
  property of the model.

Settings neutralized by a switch are omitted: two configurations differing only
by the value of a disabled parameter yield the same fingerprint. A fingerprint
that reports inconsequential differences is a fingerprint people stop reading.

The software version does not enter the fingerprint, which would otherwise shift
every fingerprint on each release at constant configuration. It belongs in a
separate column of the result file.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator

from spot_detector.model.models import ColorAndParams, DetParams, SimpleParam
from spot_detector.model.project import Project
from spot_detector.model.processing_settings_models import (
    PreprocessingSettings,
    QualityReportingSettings,
)

# Fingerprint schema version. Bump it whenever the contents of the canonical
# view change, otherwise a change of the rules would read as a change of the
# configuration.
SCHEMA_VERSION = 2

SIGNIFICANT_DIGITS = 6
DIGEST_BITS = 48        # 12 hexadecimal digits
GROUP_SIZE = 4          # AF83-4E4D-0C71

type JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


# --- Float quantization -----------------------------------------------------

def quantize_float(value: object) -> object:
    """Reduce a float to SIGNIFICANT_DIGITS significant digits.

    Exponential notation is preferred over rounding to N decimal places, which
    would flatten very small quantities to zero: the minimum occupation of the
    signal mask sits around 1e-4 and nothing forbids a future quantity from
    going lower. Adding 0.0 turns -0.0 into 0.0, the two being equal yet
    yielding two different fingerprints.

    Non-finite values are rejected here rather than at serialization time: NaN
    equals no value at all, not even itself, and has no place in a
    configuration.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    number = float(value) + 0.0
    if not isfinite(number):
        raise ValueError("non-finite value in configuration")
    return float(f"{number:.{SIGNIFICANT_DIGITS - 1}e}")


CanonicalFloat = Annotated[float, BeforeValidator(quantize_float)]
"""Annotation to put on the float fields of the models.

Quantizing at setting time rather than at digest time puts normalization at the
entry boundary of the model, where dubious values arrive. The displayed value,
the stored value and the digested value then become the same one. Remember to
enable `validate_assignment` on the models involved: without it, an assignment
made after construction bypasses validation, and the interface writes in
exactly that way.
"""


def _canonical(value: object) -> JSONValue:
    """Recursively normalize a structure before serialization."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return quantize_float(value)  # pyright: ignore[reportReturnType]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _canonical(item)  # pyright: ignore[reportUnknownArgumentType]
            for key, item in value.items()  # pyright: ignore[reportUnknownVariableType]
        }
    raise TypeError(f"unserializable type in the canonical view: {type(value)!r}")


# --- Canonical view of the detection parameters -----------------------------

def _simple_param_view(param: SimpleParam) -> JSONValue:
    """A disabled filter does not affect detection: its bounds are left out.
    See DetParams.load_params, which only reads mini and maxi under the
    `enabled` condition."""
    if not param.enabled:
        return None
    return {"mini": param.mini, "maxi": param.maxi}


def _det_params_view(params: DetParams) -> JSONValue:
    # color_name enters the fingerprint: it names the count columns of the
    # result file, hence it changes how that file reads.
    view: dict[str, JSONValue] = {
        "color_name": params.color_name,
        "area": _simple_param_view(params.area),
        "circularity": _simple_param_view(params.circ),
        "convexity": _simple_param_view(params.convex),
    }
    # SimpleBlobDetector thresholding stays out of the fingerprint: since the
    # manual setting was removed, load_params derives it from the number of
    # shades, which the palette already covers.
    # load_params only applies min_dist when it is strictly positive.
    if params.min_dist is not None and params.min_dist > 0.0:
        view["min_dist"] = params.min_dist
    return view


def configuration_view(configuration: ColorAndParams) -> JSONValue:
    """Canonical view of the palette and of the detectors.

    `reference_image` is excluded: it is a path to the image used to build the
    palette, it takes no part in counting, and it changes as soon as a file is
    moved.
    """
    return {
        "shades": [[s.b, s.g, s.r, s.label_id] for s in configuration.shades],
        "detectors": [_det_params_view(params) for params in configuration.det_params],
    }


# --- Canonical view of the preprocessing ------------------------------------

def _reporting_view(reporting: QualityReportingSettings) -> JSONValue:
    blur = reporting.blur
    over = reporting.overexposure

    view: dict[str, JSONValue] = {"average_brightness": reporting.average_brightness}

    if blur.enabled:
        view["blur"] = {
            "reference_threshold": blur.reference_threshold,
            "min_particles": blur.min_particles,
            "min_occupation": blur.min_occupation,
        }
    if over.enabled:
        view["overexposure"] = {
            "area_threshold": over.area_threshold,
            "brightness_sensitivity": over.brightness_sensitivity,
        }
    # Both quantities are shared by the two checks: if neither is active they
    # have no effect and drop out of the fingerprint.
    if blur.enabled or over.enabled:
        view["expected_diameter_px"] = reporting.expected_diameter_px
        view["collar_fraction"] = reporting.collar_fraction
    return view


def preprocessing_view(
    preprocessing: PreprocessingSettings,
    dust_filter_digest: str | None = None,
) -> JSONValue:
    """Canonical view of the preprocessing.

    `dust_filter_digest` must carry the digest of the filter file contents, as
    obtained from `content_digest`. What changes the result is the contents of
    the filter, not its path: two different filters stored under the same name
    must yield two different fingerprints, and one same filter moved elsewhere
    must yield the same one. The path only serves as a fallback when the file
    could not be read, in which case the fingerprint is weaker and says so.
    """
    cropping = preprocessing.cropping
    dust = preprocessing.dust_filter

    view: dict[str, JSONValue] = {"reporting": _reporting_view(preprocessing.reporting)}

    if cropping.enabled:
        crop_view: dict[str, JSONValue] = {}
        if cropping.min_radius_enabled:
            crop_view["min_radius"] = cropping.min_radius_value
        if cropping.max_radius_enabled:
            crop_view["max_radius"] = cropping.max_radius_value
        view["cropping"] = crop_view

    if dust.enabled:
        if dust_filter_digest is not None:
            view["dust_filter"] = {"content": dust_filter_digest}
        else:
            view["dust_filter"] = {"unresolved_path": dust.path}

    return view


# --- Fingerprint ------------------------------------------------------------

def canonical_payload(
    configuration: ColorAndParams,
    preprocessing: PreprocessingSettings | None = None,
    dust_filter_digest: str | None = None,
) -> str:
    """String that gets digested to produce the fingerprint.

    It never leaves memory: what is written next to the results is a copy of the
    project, openable in the application, not this view. Verification therefore
    goes through rebuilding the view from the project read back, rather than
    through a bare digest.
    """
    document: dict[str, JSONValue] = {
        "fingerprint_schema": SCHEMA_VERSION,
        "configuration": configuration_view(configuration),
    }
    if preprocessing is not None:
        document["preprocessing"] = preprocessing_view(preprocessing, dust_filter_digest)

    return json.dumps(
        _canonical(document),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def fingerprint(payload: str) -> str:
    """Displayable fingerprint, grouped by four: AF83-4E4D-0C71.

    The digest is truncated to DIGEST_BITS bits. At 48 bits, the probability of
    a collision appearing among ten thousand distinct configurations is on the
    order of 2e-7 (n^2 / 2^(b+1)).
    """
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    text = digest[: DIGEST_BITS // 8].hex().upper()
    return "-".join(text[i : i + GROUP_SIZE] for i in range(0, len(text), GROUP_SIZE))


def normalized_fingerprint(text: str) -> str:
    """Comparison form. File names come back with a case that depends on the
    file system, and the user will sometimes copy the value without its
    dashes: every comparison goes through here."""
    return text.replace("-", "").strip().lower()


def content_digest(path: str | Path) -> str:
    """Digest of a file's contents, for the dust filter."""
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def project_fingerprint(project: Project, dust_filter_path: str | Path | None = None) -> str:
    """Fingerprint of the computation configuration of a project.

    The dust filter is identified by the digest of its contents. If the file is
    missing or unreadable, the fingerprint falls back on its path and flags that
    under a distinct key: it stays comparable, but it no longer guarantees that
    two processing runs did use the same filter.
    """
    settings = project.processing_settings
    preprocessing = settings.preprocessing if settings is not None else None

    resolved = dust_filter_path
    if resolved is None and preprocessing is not None and preprocessing.dust_filter.enabled:
        resolved = preprocessing.dust_filter.path

    digest_of_filter: str | None = None
    if resolved:
        try:
            digest_of_filter = content_digest(resolved)
        except OSError:
            digest_of_filter = None

    return fingerprint(canonical_payload(project.configuration, preprocessing, digest_of_filter))


# --- Processing session -----------------------------------------------------

SESSION_PREFIX = "results_"
RESULTS_NAME = "results.tsv"
SNAPSHOT_NAME = "snapshot.spot"
LOG_NAME = "log.txt"

# The colons of ISO 8601 are forbidden in a file name under Windows. The rest of
# the format is kept, which lets chronological order coincide with the
# lexicographic order of directory names.
TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"


@dataclass(frozen=True)
class ProcessingSession:
    """Directory of one processing session.

    A session gathers what must stay together: the result table, the snapshot of
    the settings that produced it, and the processing log. Moving the directory
    breaks nothing, since none of the three refers to the others by a path.
    """
    directory: Path
    results_path: Path
    snapshot_path: Path
    log_path: Path
    config_digest: str


def _session_paths(directory: Path, digest: str) -> ProcessingSession:
    return ProcessingSession(
        directory=directory,
        results_path=directory / RESULTS_NAME,
        snapshot_path=directory / SNAPSHOT_NAME,
        log_path=directory / LOG_NAME,
        config_digest=digest,
    )


def session_directory_name(started_at: datetime, digest: str) -> str:
    return f"{SESSION_PREFIX}{started_at.strftime(TIMESTAMP_FORMAT)}_{digest}"


def write_snapshot(path: str | Path, project: Project) -> None:
    """Write the snapshot of the settings.

    What gets serialized is the in-memory model, never the project file present
    on disk: the user may start a processing run after changing settings without
    saving them, in which case the file would describe something other than what
    ran. `save_as` is not used either, as it would rewrite `latest_save_path`
    and list the snapshot among the recent projects.
    """
    snapshot = project.model_copy(deep=True)
    _ = Path(path).write_text(snapshot.model_dump_json(indent=2), encoding="UTF-8")


def append_log(session: ProcessingSession, message: str) -> None:
    """Append a timestamped line to the log.

    The file is opened and closed on every line: a log that would not survive
    the program being interrupted would miss exactly the case it serves. The
    timestamp carries the UTC offset, unlike the directory name, which stays
    readable at the cost of that ambiguity.
    """
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with open(session.log_path, "a", encoding="UTF-8") as handle:
        _ = handle.write(f"{stamp}  {message}\n")


def create_session(
    parent_directory: str | Path,
    project: Project,
    dust_filter_path: str | Path | None = None,
    started_at: datetime | None = None,
) -> ProcessingSession:
    """Create the session directory, write the snapshot and open the log.

    The directory name carries the fingerprint of the configuration at launch
    time. Should a run be resumed with modified settings, that name only
    describes the first session: what counts is the fingerprint written on each
    row of the table, which allows a heterogeneous file without making it
    misleading.
    """
    started = started_at or datetime.now()
    digest = project_fingerprint(project, dust_filter_path)

    parent = Path(parent_directory)
    name = session_directory_name(started, digest)

    directory = parent / name
    attempt = 1
    while True:
        try:
            directory.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            # Two runs launched within the same second with the same config.
            attempt += 1
            directory = parent / f"{name}_{attempt}"

    session = _session_paths(directory, digest)
    write_snapshot(session.snapshot_path, project)
    append_log(session, f"session opened, configuration fingerprint {digest}")
    return session


def open_session(directory: str | Path) -> ProcessingSession:
    """Reopen an existing session, to resume an interrupted processing run.

    The fingerprint is recomputed from the snapshot rather than read from the
    directory name: the name may have been changed or carry a disambiguation
    suffix, whereas the snapshot is authoritative.
    """
    path = Path(directory)
    snapshot_path = path / SNAPSHOT_NAME
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"no settings snapshot in {path}")

    snapshot = Project.from_path(snapshot_path)
    return _session_paths(path, project_fingerprint(snapshot))


def verify_session(session: ProcessingSession) -> bool:
    """Check that the snapshot matches the fingerprint of the session.

    A negative result does not necessarily point to tampering: if the dust
    filter has been moved or modified since the run, its digest has changed and
    the fingerprint with it.
    """
    snapshot = Project.from_path(session.snapshot_path)
    return normalized_fingerprint(project_fingerprint(snapshot)) == normalized_fingerprint(
        session.config_digest
    )
