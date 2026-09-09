"""Entry point of the graphical application.

Everything must stay inside `main()`, behind the `__main__` guard. Worker
processes are started with the "spawn" method, and `multiprocessing` rebuilds
their `__main__` by running this very file again through
`runpy.run_path(main_path, run_name="__mp_main__")`. Any statement left at
module level would therefore run once per worker: with the window creation
outside the guard, each worker opened its own copy of Spot Detector instead of
processing images.
"""

import multiprocessing as mp
import sys


def main() -> int:
    # Must come first: a frozen executable relaunches itself to spawn a worker,
    # and this is what makes that relaunch run the worker instead of the app.
    mp.freeze_support()

    from PySide6.QtWidgets import QApplication

    from spot_detector.controller.entry_point import AppStartManager

    app = QApplication(sys.argv)
    app.setApplicationName("Spot Detector")
    app.setApplicationDisplayName("Spot Detector")

    start_manager = AppStartManager()
    start_manager.start_from_welcome()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
