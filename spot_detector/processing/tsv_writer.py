from logging import Logger
import os
from types import NoneType
from typing import Any, Callable

from spot_detector.model.config_fingerprint import ProcessingSession
from spot_detector.model.result_datastructures import (
    CellContent,
    CheckStatus,
    ImageResult,
    CheckID,
    Column,
    ImageTask,
)
from spot_detector.errors import AccessBeforeValidationError, ResultsCellValueError, ResultsFileContentError, ResultsShapeError
from spot_detector.misc import NFC

import csv
from datetime import datetime
from pathlib import Path


def check_status(check_id: CheckID, result: ImageResult, session: ProcessingSession) -> str | None:
    check = result.checks.get(check_id)
    if check is None:
        session.logger.warning(f"Check report with id {check_id} was not provided in the results")
        return None
    else:
        return check.check_status.name

def check_value(check_id: CheckID, result: ImageResult, _session: ProcessingSession) -> float | int | str | bool | None:
    check = result.checks.get(check_id)
    if check is None:
        return None
    else:
        return check.check_value

def get_dust_filter_path(result: ImageResult, session: ProcessingSession) -> str | None:
    check = result.checks.get(CheckID.Dust_Filter)
    if check is None:
        session.logger.warning(f"Check report with id {CheckID.Dust_Filter} was not provided in the results")
        return None

    if check.check_status != CheckStatus.Success:
        return None

    ps = session.project_snapshot.processing_settings
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
        Column("Rank", int, lambda r, s: r.rank),
        Column("Directory path", Path, lambda r, s: r.image_dir),
        Column("File name", str, lambda r, s: r.image_name),
        Column("Settings Snapshot", Path, lambda r, s: s.snapshot_save_path),
        Column("Status", str, lambda r, s: "FAILED" if r.error else "OK"),
    ]
    columns += identifiers

    counting_output: list[Column] = []
    for index, name in enumerate(session.project_snapshot.configuration.color_names):
        counting_output.append(Column(name, int, lambda r, s, i=index: r.counts[i] if r.counts else None))
    counting_output.append(Column("Total", int, lambda r, s: sum(r.counts) if r.counts else None))
    columns += counting_output

    preprocessing_info = [
        Column("Dust Filter", (Path, NoneType), get_dust_filter_path),
        Column("ROI Center X", (float, NoneType), lambda r, s: r.roi_data.center_x),
        Column("ROI Center Y", (float, NoneType), lambda r, s: r.roi_data.center_y),
        Column("ROI Radius", (float, NoneType), lambda r, s: r.roi_data.radius),
    ]
    columns += preprocessing_info

    reporting_info: list[Column] = []
    for check in CheckID: # Sorted by enum value, not by dict key order
        status = Column(
            f"{check.name.replace("_", " ")} state",
            str,
            lambda r, s, c=check: check_status(c, r, s),
        )
        value = Column(
            f"{check.name.replace("_", " ")} value",
            (bool, int, float, str, NoneType),
            lambda r, s, c=check: check_value(c, r, s),
        )
        reporting_info.append(status)
        reporting_info.append(value)
    columns += reporting_info


    extra_info = [
        Column("Width", (int, NoneType), lambda r, s: None if r.metadata is None else r.metadata.image_width),
        Column("Height", (int, NoneType), lambda r, s: None if r.metadata is None else r.metadata.image_height),
        Column("Format", (str, NoneType), lambda r, s: None if r.metadata is None else r.metadata.image_format),
        Column("Codec", (str, NoneType), lambda r, s: None if r.metadata is None else r.metadata.image_codec),
        Column("Compression", (str, NoneType), get_compression_type),
        Column("Subsampling", (str, NoneType), lambda r, s: None if r.metadata is None else r.metadata.subsampling),
        Column("Color space", (str, NoneType), lambda r, s: None if r.metadata is None else r.metadata.color_space),
        Column("Channel depth", (int, NoneType), lambda r, s: None if r.metadata is None else r.metadata.channel_depth),
        Column("Camera model", (str, NoneType), lambda r, s: None if r.metadata is None else r.metadata.camera_model),
        Column("Exposure seconds", (float, NoneType), lambda r, s: None if r.metadata is None else r.metadata.exposure_seconds),
        Column("Creation date", (datetime, NoneType), lambda r, s: None if r.metadata is None else r.metadata.creation_date),
        Column("Processing date", (datetime, NoneType), lambda r, s: r.processing_date),
        Column("Full settings digest", (str, NoneType), lambda r, s: s.config_digest),
    ]
    columns += extra_info

    diagnostics = [Column("Diagnostic Brief", str, diagnostic_brief)]
    columns += diagnostics

    return columns


class TSVWriter:
    def __init__(self, session: ProcessingSession):
        self.session: ProcessingSession = session
        self.columns: list[Column] = build_columns(self.session)
        self._result_file_valid: bool = False

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
                return NFC(content)
            case None:
                return ""
            case other:  # pyright: ignore[reportUnnecessaryComparison]
                # When used in a non type-safe way
                self.session.logger.warning(f"unexpected type {type(other).__name__}")
                return str(other)  # pyright: ignore[reportUnreachable]

    def reset_file_validity(self):
        self._result_file_valid = False

    def result_file_valid(self) -> bool:
        return self._result_file_valid

    def write_result(self, result: ImageResult):
        if not self._result_file_valid:
            raise AccessBeforeValidationError(
                "Results file must be validated with TSVWriter.prepare_results_file before writing to it"
            )

        self.session.logger.info(f"Writing row {result.rank} for image {result}")
        if result.metadata is None:
            self.session.logger.warning(f"Metadata for entry {result.rank} was not provided")

        row = [self.format_cell(col.extract(result, self.session)) for col in self.columns]
        with open(self.session.results_path, "a", newline="", encoding="utf-8") as result_file:
            writer = csv.writer(result_file, dialect="excel-tab")
            writer.writerow(row)


    def get_processed_rows(self) -> tuple[list[ImageTask], list[ImageTask]]:
        """
        Only call if prepare_results_file has been called without error beforehand.
        """
        if not self._result_file_valid:
            raise AccessBeforeValidationError(
                "Results file must be validated with TSVWriter.prepare_results_file before reading from it"
            )

        self.session.logger.info("Getting already processed rows")
        rows: list[list[str]]
        with open(self.session.results_path, "r", encoding="utf-8", newline="") as handle:
            rows = [row for row in csv.reader(handle, dialect="excel-tab")]

        self.session.logger.info(f"Found {len(rows) - 1} data rows in file `{NFC(self.session.results_path)}`")

        processed_rows: list[ImageTask] = []
        failed_rows: list[ImageTask] = []
        for row in rows[1:]:
            rank = int(row[0])
            image_path = Path(NFC((Path(row[1]) / row[2]).expanduser().resolve()))
            if row[4] == "OK":
                processed_rows.append(ImageTask(rank, image_path))
            else:
                failed_rows.append(ImageTask(rank, image_path))

        return processed_rows, failed_rows

    def prepare_results_file(self, *, check_data_type: bool = True, strict_paths: bool = False) -> None:
        """
        Conditions the result file so that new rows can be simply appended
        afterwards. Raises an error if the file contains column headers that
        are different to those generated from the project snapshot.

        If the function is successful, sets `self.result_file_valid` to `True`.

        The check will not be shortcut if the file is already validated, and
        may invalidate it if it fails.
        """
        self._result_file_valid = False
        self._prepare_results_file(check_data_type=check_data_type, strict_paths=strict_paths)
        self._result_file_valid = True


    def _prepare_results_file(self, *, check_data_type: bool = True, strict_paths: bool = False) -> None:
        """
        Conditions the result file so that new rows can be simply appended
        afterwards. Raises an error if the file contains column headers that
        are different to those generated from the project snapshot.
        """
        self.session.logger.info("Preparing results file for writing")
        if not self.session.results_path.exists():
            self.session.logger.info(f"File `{NFC(self.session.results_path)}` doesn't exist yet, creating")
            self.session.results_path.touch()

        if not self.session.results_path.is_file():
            raise FileNotFoundError(f"Provided path `{NFC(self.session.results_path)}` does not point to a file")

        # check for truncated row and remove it if found, empties the file if the header is truncated
        data = self.session.results_path.read_bytes()
        if data and not data.endswith(b"\r\n"):
            self.session.logger.warning("Integrity check found a truncated final row. The row will be removed.")
            cut = data.rfind(b"\r\n")
            with open(self.session.results_path, "rb+") as handle:
                _ = handle.truncate(cut + 2 if cut >= 0 else 0)

        # add header if missing
        data = self.session.results_path.read_bytes()
        if not data:
            self.session.logger.info("Results file is empty : adding header")
            with open(self.session.results_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, "excel-tab")
                writer.writerow([col.name for col in self.columns])
            return

        # ATP at least the header is there
        rows = []
        with open(self.session.results_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, dialect="excel-tab")
            rows = [row for row in reader]
        row_count = len(rows)

        # Unreachable but let's check anyway. 
        if row_count == 0:
            self.session.logger.error(f"file `{NFC(self.session.results_path)}` is non-empty but parses to nothing")
            # I can't see how this could be reached. A bunch of invalid unicode?
            raise ResultsFileContentError(f"file `{NFC(self.session.results_path)}` is non-empty but parses to nothing")

        header = rows[0]
        col_count = len(header)
        self.session.logger.info(f"Header has {col_count} columns")

        if col_count != len(self.columns):
            self.session.logger.warning(f"file `{NFC(self.session.results_path)}` has the wrong number of columns. Maybe a different config.")
            raise ResultsShapeError(f"File header has an unexpected number of columns, expected {len(self.columns)}, got {col_count}")

        # we are now sure that the header has the correct size but it may still contain bad names,
        # which would corrupt the meaning of some of the data, especially color names in count values
        bad_columns: list[dict[str, int | str]] = []
        for i, found_name, ref_column in zip(range(col_count), rows[0], self.columns):
            if found_name != ref_column.name:
                message = (
                    f"Unexpected column name in position {i}:"
                    + f" got `{found_name}`,"
                    + f" expected `{ref_column.name}`"
                )
                self.session.logger.warning(message)

                bad_columns.append({
                    "position":i,
                    "current name":found_name,
                    "expected name":ref_column.name
                })

        if bad_columns:
            raise ResultsCellValueError(f"Unexpected column names : {bad_columns}")

        if row_count == 1:
            # no data row to check now
            self.session.logger.info(f"file `{NFC(self.session.results_path)}` contains only one row")
            return

        # at least one row besides the header
        table_shape = list_2D_shape(rows)
        if table_shape is None:
            lengths = [len(row) for row in rows]
            message = (
              f"Rows in file `{NFC(self.session.results_path)}` have an inconsistent length: "
              + f"header = {lengths[0]} ; rows = {lengths[1:]}"
            )
            self.session.logger.warning(message)
            raise ResultsShapeError(message)

        bad_rows: list[tuple[int, str]] = []
        for position, row in enumerate(rows[1:], start=2):
            try:
                _rank = int(row[0])
            except ValueError:
                self.session.logger.warning(f"Bad rank value on row {position}: {row}")
                bad_rows.append((position, row[0]))
        if bad_rows:
            raise ResultsCellValueError(f"Results file has invalid cell values on first column: {bad_rows}")

        # all the rows have the correct shape
        if not check_data_type:
            self.session.logger.info("Results file preparation successful, type checking skipped")
            return

        self.session.logger.info("Results file preparation successful, type_checking in progress")

        def bool_test(string: str):
            if string.casefold() not in ("true", "false"):
                raise ValueError(f"Expected a string simplifying to `true` or `false`, got {string}")

        def none_test(string: str):
            if string.casefold() not in ("", "none"):
                raise ValueError(f"Expected a string simplifying to an empty string or `none`, got {string}")

        def dt_test(string: str):
            _ = datetime.fromisoformat(string)


        path_checker = PathChecker(self.session.logger)

        def path_test(string: str) -> None:
            if not path_checker.path_exists(Path(NFC(string))):
                self.session.logger.warning(f"Expected a valid path, got {string}")
                if strict_paths:
                    raise ValueError(f"Expected a valid path, got {string}")

        custom_tests = {
                bool: bool_test,
            NoneType: none_test,
            datetime: dt_test,
                Path: path_test,
        }

        failing_rows: dict[int, dict[int, tuple[str, tuple[type,...]]]] = {}
        for i, row in enumerate(rows[1:], start=2):
            failing_cells: dict[int, tuple[str, tuple[type, ...]]] = {}

            # check if the string in each field can be cast back to one of the cell's expected types, if not fails
            for j, (cell, column) in enumerate(zip(row, self.columns)):
                if not castable(cell, column.data_types, custom_cast=custom_tests, logger=self.session.logger):
                    failing_cells[j] = (cell, column.data_types)

            if failing_cells:
                count = len(failing_cells.keys())
                self.session.logger.warning(
                    f"In file `{NFC(self.session.results_path)}`, on row {i}, {count} "
                    + f"cells failed to convert to their expected type : {failing_cells}",
                )
                failing_rows[i] = failing_cells

        if failing_rows:

            total_rows = row_count - 1
            total_cells = total_rows * col_count
            total_failed_rows = len(failing_rows.keys())
            total_failed_cells = sum(len(row.keys()) for row in failing_rows.values())

            self.session.logger.warning(
                f"In total, on file `{NFC(self.session.results_path)}`, {total_failed_cells}/{total_cells}"
              + f" cells over {total_failed_rows}/{total_rows} rows failed to convert to the correct type"
            )

            raise ResultsCellValueError(
                f"In total, on file `{NFC(self.session.results_path)}`, {total_failed_cells}/{total_cells}"
              + f" cells over {total_failed_rows}/{total_rows} rows failed to convert to the correct type"
            )

        self.session.logger.info("Results file preparation and checking successful")


def castable(
    data: str,
    types: type | tuple[type, ...],
    /,
    *,
    custom_cast: dict[type, Callable[[str], None]] | None = None,
    logger: Logger | None = None
) -> bool:
    _custom_cast = custom_cast or {}
    type_collection: tuple[type] | tuple[type, ...]
    if isinstance(types, tuple):
        type_collection = types
    else:
        type_collection = (types, )

    if str in type_collection:
        return True

    for _type in type_collection:
        cast_function = _custom_cast.get(_type) or _type
        try:
            _cast = cast_function(data)
            success = True
        except ValueError:
            if logger is not None:
                logger.info(f"data of type str and of value {data} cannot be converted to type {_type.__name__}")
            success = False
        except TypeError as e:
            if logger is not None:
                logger.info(e)
                logger.info(f"provided type {_type.__name__} in argument `types` must accept str as input for casting.")
            raise
        if success:
            return True
    return False




def list_2D_shape(seq: list[list[Any]]) -> tuple[int, int] | None:  # pyright: ignore[reportExplicitAny]
    """
    Returns the 2D shape of a list of lists or None if rows have varying lengths.
    An empty list in input returns a shape of (0, 0) and a list of empty lists
    returns a shape of (n, 0).
    """
    row_count = len(seq)
    if row_count == 0:
        return (0,0)

    cols = [len(row) for row in seq]
    col_count = cols[0]
    for col in cols:
        if col != col_count:
            return None

    return (row_count, col_count)


class PathChecker:
    def __init__(self, logger: Logger | None = None):
        self.memoized_path_exists: dict[str, bool] = {}
        self.logger: Logger | None = logger

    def path_exists(self, path: Path) -> bool:
        path_str = NFC(path)
        exists = self.memoized_path_exists.get(path_str)

        if exists is None:
            if self.logger:
                self.logger.info(f"Path `{path_str}` was not met before.")
            exists = path.exists()
            self.memoized_path_exists[path_str] = exists

        return exists

