from spot_detector.model.project import Project


class StartManagerInterface:
    def start_main_window(self, project: Project): ...
