from spot_detector.model.project import Project


# Interfaces to resolve circular references
class WelcomeWindowInterface:
    def start_window_and_hide(self, project: Project): ...
