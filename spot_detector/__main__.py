import click

from spot_detector.commands import detector, palette_editor
from spot_detector.subtract_base_image import remove_hot_pixels


@click.group
def cli():
    pass


cli.add_command(detector)
cli.add_command(palette_editor)
cli.add_command(remove_hot_pixels)
