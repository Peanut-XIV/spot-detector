import click
import numpy as np
import cv2
from pathlib import Path

@click.command()
@click.argument(
        "reference",
        type=click.Path(file_okay=True, dir_okay=False, exists=True)
)
@click.argument(
        "source",
        type=click.Path(file_okay=False, dir_okay=True, exists=True)
)
@click.option(
        "-d",
        "--destination",
        type=click.Path(file_okay=False, dir_okay=True, exists=False),
        default=None,
)
@click.option(
        "-n",
        "--name",
        type=click.types.STRING,
        default=None,
)
def remove_hot_pixels(
        reference: str,
        source: str,
        destination: str | None,
        name: str | None,
):
    try:
        ref_img = cv2.imread(reference, cv2.IMREAD_ANYDEPTH + cv2.IMREAD_COLOR)
    except RuntimeError:
        raise click.FileError("Could not open reference image")
    if ref_img is None:
        raise click.FileError("Could not open reference image")
    
    source_path = Path(source)
    source_directories = [dir for dir in source_path.iterdir() if dir.is_dir()]
    destination_path = validate_destination_path(source_path, destination, name)
    destination_path.mkdir()
    wheel_count = 0
    for source_dir in source_directories:
        dest_dir = destination_path.joinpath(source_dir.name)
        dest_dir.mkdir()
        image_paths = [img for img in source_dir.iterdir() if img.is_file()]
        for im_path in image_paths:
            img = cv2.imread(str(im_path), cv2.IMREAD_ANYDEPTH + cv2.IMREAD_COLOR)
            if img is None:
                print(f"{im_path} could not be opened")
                continue
            loading_list = ""
            print(f"{loading_list[wheel_count % 6]}", end="\r")
            wheel_count += 1
            diff = img.astype(np.int32) - ref_img.astype(np.int32)
            out_img = np.clip(diff, 0, 65535).astype(np.uint16)
            out_img_path = dest_dir.joinpath(im_path.name)
            cv2.imwrite(str(out_img_path), out_img)
    print("\nFinished!!!")



def validate_destination_path(
        source_path: Path,
        destination: str | None,
        name: str | None
) -> Path:
    destination_path: Path
    if name is not None:
        if destination is not None:
            raise click.BadOptionUsage(
                    "destination",
                    "destination and name options are mutually exclusive"
            )
        if len(name) == 0:
            raise click.BadOptionUsage(
                    "name",
                    "name can't be an empty string"
            )
        for char in name:
            if not char.isalnum and char not in "-_":
                raise click.BadOptionUsage(
                        "name",
                        "name must only contain letters, numbers, - and _"
                )
        destination_path = source_path.joinpath(name)
        if destination_path.exists():
            raise IsADirectoryError(f"{destination_path} already exists")
    elif destination is None:
        counter = 0
        destination_path = source_path.joinpath(f"modified_{counter}")
        while destination_path.exists() and counter < 100:
            counter += 1
            destination_path = source_path.joinpath(f"modified_{counter}")
        if destination_path.exists():
            raise IsADirectoryError(
                "to many directories named \"modified_xx\","
                "please set the destination path manually"
            )
    else:
        destination_path = Path(destination)
        if destination_path.exists():
            raise IsADirectoryError(
                    f"{destination_path} already exists"
            )
    return destination_path

