import os

from spot_detector.model.config_fingerprint import ProcessingSession
from spot_detector.model.result_datastructures import (
    CellContent,
    CheckStatus,
    ImageResult,
    CheckID,
    Column,
)

from pathlib import Path
import csv
from datetime import datetime

def check_status(check_id: CheckID, result: ImageResult, session: ProcessingSession) -> str | None:
    check = result.checks.get(check_id)
    if check is None:
        session.logger.warning(f"Check report with id {check_id} was not provided in the results")
        return None
    else:
        return check.check_status.name

def check_value(check_id: CheckID, result: ImageResult, session: ProcessingSession) -> float | int | str | bool | None:
    check = result.checks.get(check_id)
    if check is None:
        return None
    else:
        return check.check_value

# def check_message(check_id: CheckID, result: ImageResult, session: ProcessingSession) -> str | None:
#     check = result.checks.get(check_id)
#     if check is None:
#         session.logger.warning(f"Check report with id {check_id} was not provided in the results")
#         return "Not Provided"
#     else:
#         return check.check_message

def get_dust_filter_path(result: ImageResult, session: ProcessingSession) -> str | None:
    check = result.checks.get(CheckID.Dust_Filter)
    if check is None:
        session.logger.warning(f"Check report with id {CheckID.Dust_Filter} was not provided in the results")
        return "Not Provided"

    if check.check_status != CheckStatus.Success:
        return None

    ps = session.project.processing_settings
    if ps is None:
        session.logger.warning("Divergence between ImageResult and project settings: check successful yet None in the settings")
        return None

    dfs = ps.preprocessing.dust_filter
    if not dfs.enabled:
        session.logger.warning("Divergence between ImageResult and project settings: check successful yet disabled in the settings")
        return None

    return dfs.path


def get_compression_type(result: ImageResult, _session: ProcessingSession) -> str | None:
    if result.metadata is None:
        return None
    return "Lossy" if result.metadata.has_lossy_compression else "LossLess"

def diagnostic_brief(result: ImageResult, _session: ProcessingSession) -> str:
    diags: list[str] = []

    if result.error:
        diags.append("Processing Error: " + result.error)

    for id, report in result.checks.items():
        if report.check_status != CheckStatus.Fail:
            continue
        diags.append(f"{id.name.replace("_"," ")} Warning: {report.check_message}")

    if len(diags):
        return " ; ".join(diags)
    else:
        return "No issue found"


def build_columns(session: ProcessingSession) -> list[Column]:
    columns: list[Column] = []

    identifiers = [
        Column("Rank", lambda r, s: r.rank),
        Column("Directory path", lambda r, s: r.directory),
        Column("File name", lambda r, s: r.file_name),
        Column("Settings Snapshot", lambda r, s: s.project_snapshot_path),
        Column("Status", lambda r, s: "FAILED" if r.error else "OK"),
    ]
    columns += identifiers

    counting_output: list[Column] = []
    for index, name in enumerate(session.project.configuration.color_names):
        counting_output.append(Column(name, lambda r, s, i=index: r.counts[i] if r.counts else None))
    counting_output.append(Column("Total", lambda r, s: sum(r.counts) if r.counts else None))
    columns += counting_output

    preprocessing_info = [
        Column("Dust Filter", get_dust_filter_path),
        Column("ROI Center X", lambda r, s: r.roi_data.center_x),
        Column("ROI Center Y", lambda r, s: r.roi_data.center_y),
        Column("ROI Radius", lambda r, s: r.roi_data.radius),
    ]
    columns += preprocessing_info

    reporting_info: list[Column] = []
    for check in CheckID: # Sorted by enum value, not by dict key order
        status = Column(
            f"{check.name.replace("_", " ")} state",
            lambda r, s, c=check: check_status(c, r, s),
        )
        value = Column(
            f"{check.name.replace("_", " ")} value",
            lambda r, s, c=check: check_value(c, r, s),
        )
        reporting_info.append(status)
        reporting_info.append(value)
    columns += reporting_info

    extra_info = [
        Column("Width", lambda r, s: None if r.metadata is None else r.metadata.image_width),
        Column("Height", lambda r, s: None if r.metadata is None else r.metadata.image_height),
        Column("Format", lambda r, s: None if r.metadata is None else r.metadata.image_format),
        Column("Codec", lambda r, s: None if r.metadata is None else r.metadata.image_codec),
        Column("Compression", get_compression_type),
        Column("Subsampling", lambda r, s: None if r.metadata is None else r.metadata.subsampling),
        Column("Color space", lambda r, s: None if r.metadata is None else r.metadata.color_space),
        Column("Channel depth", lambda r, s: None if r.metadata is None else r.metadata.channel_depth),
        Column("Camera model", lambda r, s: None if r.metadata is None else r.metadata.camera_model),
        Column("Exposure seconds", lambda r, s: None if r.metadata is None else r.metadata.exposure_seconds),
        Column("Creation date", lambda r, s: None if r.metadata is None else r.metadata.creation_date),
        Column("Processing date", lambda r, s: r.processing_date),
        Column("Full settings digest", lambda r, s: s.config_digest),
    ]
    columns += extra_info

    diagnostics = [Column("Diagnostic Brief", diagnostic_brief)]
    columns += diagnostics

    return columns




def has_header(file: Path) -> bool:
    file_size = os.stat(file).st_size

    return file_size > 0



class TSVWriter:
    def __init__(self, session: ProcessingSession):
        self.session: ProcessingSession = session
        self.columns: list[Column] = build_columns(self.session)
        self.file_unchecked: bool = True

    def format_cell(self, content: CellContent) -> str:
        match content:
            case bool():
                return "True" if content else "False"
            case int():
                return str(content)
            case float():
                return f"{content:z.6g}"
            case str():
                return content
            case datetime():
                return content.isoformat(timespec="seconds")
            case Path():
                return str(content)
            case None:
                return ""
            case other:  # pyright: ignore[reportUnnecessaryComparison]
                self.session.logger.warning(f"unexpected type {type(other).__name__}")
                return str(other)  # pyright: ignore[reportUnreachable]

    def write_result(self, result: ImageResult):

        if result.metadata is None:
            self.session.logger.warning(f"Metadata for entry {result.rank} was not provided")

        need_header = False
        if self.file_unchecked:
            self.file_unchecked = False
            fp = Path(self.session.results_path)
            if not fp.exists():
                need_header = True
            elif not has_header(fp):
                need_header = True

        row = [self.format_cell(col.extract(result, self.session)) for col in self.columns]

        with open(self.session.results_path, "a", newline="", encoding="utf-8") as result_file:
            writer = csv.writer(result_file, dialect="excel-tab")

            if need_header:
                header = [col.name for col in self.columns]
                writer.writerow(header)
            writer.writerow(row)
