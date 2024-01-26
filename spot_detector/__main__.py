# Project files
from spot_detector.commands import palette_editor, detector
# Other dependancies
import click


@click.group
def cli():
    pass


cli.add_command(detector)
cli.add_command(palette_editor)
