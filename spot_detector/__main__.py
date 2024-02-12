import click

from spot_detector.commands import detector, palette_editor


@click.group
def cli():
    pass


cli.add_command(detector)
cli.add_command(palette_editor)
