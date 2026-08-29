class ImageError(Exception):
    def __init__(self, img_path: str, msg: str = "") -> None:
        self.msg = msg
        self.img_path = img_path
        super().__init__(msg)


class FailedOpeningError(ImageError):
    def __init__(self, img_path: str, msg: str = "The image failed to open") -> None:
        super().__init__(img_path, msg)


class InvalidFormatError(ImageError):
    def __init__(
        self,
        img_path: str,
        msg: str = "The image must be RGB and have 8 or 16 bits of depth per channel",
    ) -> None:
        super().__init__(img_path, msg)


class InvalidNameError(ImageError):
    def __init__(
        self,
        img_path: str,
        msg: str = "The image name cannot start with '.'",
    ) -> None:
        super().__init__(img_path, msg)

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
