from pathlib import Path

from spot_detector.misc import canonical_path


class ImageError(Exception):
    def __init__(self, img_path: Path | str, msg: str = "") -> None:
        self.msg: str = msg
        self.img_path: Path = canonical_path(img_path)
        super().__init__(msg)


class FailedOpeningError(ImageError):
    def __init__(self, img_path: Path | str, msg: str = "The image failed to open") -> None:
        super().__init__(img_path, msg)


class InvalidFormatError(ImageError):
    def __init__(
        self,
        img_path: str | Path,
        msg: str = "Image has an invalid datatype (floating or integer over 64 bits) or an unexpected channel count (1 or 3 only)",
    ) -> None:
        super().__init__(img_path, msg)


class InvalidNameError(ImageError):
    def __init__(
        self,
        img_path: str | Path,
        msg: str = "The image name cannot start with '.'",
    ) -> None:
        super().__init__(img_path, msg)


class InvalidProjectError(Exception):
    """
    An error raised when the project has an invalid status.
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class UnsetCriticalSettingsError(InvalidProjectError):
    """
    An error raised when the project misses some critical attributes without
    which the program cannot continue.
    """

class ResultsFileContentError(Exception):
    """
    A generic error raised when the internal structure of the results file is inconsistent
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ResultsShapeError(ResultsFileContentError):
    """
    An error raised when the shape of the results table is inconsistent
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ResultsCellValueError(ResultsFileContentError):
    """
    An error raised when a cell of the results table could not be parsed
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class AccessBeforeValidationError(Exception):
    """
    Error raised when a critical file is accessed (read from or written to) before validation
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class WorkerError(Exception):
    """
    Error transmitted (NOT raised) when a reasonable error occurs
    in the processing worker's run function
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ProcessingSetupError(WorkerError):
    """
    Error transmitted (not raised) when a an error occurs
    before any processing starts.
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class UncaughtExceptionError(WorkerError):
    """
    Error transmitted (not raised) when a an error occurs
    during the processing of an image.
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

