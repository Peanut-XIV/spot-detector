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
