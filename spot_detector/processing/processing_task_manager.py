
import numpy as np

from time import sleep
from multiprocessing import Queue, get_context, parent_process, Event
from multiprocessing.synchronize import Event as EventType
from multiprocessing.context import SpawnContext, SpawnProcess
from pathlib import Path

from spot_detector.model.config_fingerprint import ProcessingSession
from spot_detector.model.models import ColorAndParams
from spot_detector.model.result_datastructures import ImageMetaData, ImageResult, ImageTask
from spot_detector.processing.tsv_writer import TSVWriter
from spot_detector.errors import ProcessingSetupError

class ProcessingTaskManager:
    def __init__(self, session: ProcessingSession, writer: TSVWriter) -> None:
        self.session: ProcessingSession = session
        self.writer: TSVWriter = writer
        self.context: SpawnContext = get_context("spawn")

        self.workers: list[SpawnProcess] = []
        self.input_queue: Queue[ImageTask] = self.context.Queue()
        self.output_queue: Queue[ImageResult | ProcessingSetupError] = self.context.Queue()
        self.cancel: EventType = self.context.Event()

    def create_task_list(self):
        ...


    def get_ideal_process_count(self):
        # TODO: auto-detect the ideal number of parallel workers
        # For now, let's say
        worker_count = 2
        return worker_count


    def init_workers(self, worker_count: int):
        if worker_count < 1:
            return self.get_ideal_process_count()

        ctx = get_context("spawn")
        for id in range(worker_count):
            worker_args = (
                self.input_queue,
                self.output_queue,
                self.session.project_snapshot,
                self.cancel,
            )
            worker = ctx.Process(
                    target=process_runner,
                    name=f"Processing Worker {id}",
                    args=worker_args
            )
            self.workers.append(worker)

        self.session.logger.info(
          f"{worker_count} workers created and waiting for processing to begin"
        )

    def start_processing(self):
        ...

def process_runner(
    in_queue: Queue[ImageTask],
    out_queue: Queue[ImageResult | ProcessingSetupError],
    config: ColorAndParams,
    cancel: EventType,
):
    parent = parent_process()
    if parent is None:
        error = ProcessingSetupError("Parent process is None")
        out_queue.put(error)
        return

    color_table = np.array([shade.as_row() for shade in config.shades])

    while parent.is_alive() and not cancel.is_set():
        if in_queue.empty():
            sleep(1)
            continue






def get_metadata(image: Path) -> ImageMetaData:
    ...
