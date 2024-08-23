import click

from spot_detector.commands.detector import detector
from spot_detector.commands.palette_editor import palette_editor
from spot_detector.subtract_base_image import remove_hot_pixels


@click.group
def cli():
    pass


cli.add_command(detector)
cli.add_command(palette_editor)
cli.add_command(remove_hot_pixels)
