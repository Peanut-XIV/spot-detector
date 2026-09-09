from datetime import datetime
from time import monotonic
from multiprocessing import get_context, parent_process
from multiprocessing.synchronize import Event as EventType
from multiprocessing.context import SpawnContext, SpawnProcess
from multiprocessing.queues import Queue as QueueType
from queue import Empty
from pathlib import Path
from traceback import format_exc
from natsort import natsorted

from spot_detector.model.config_fingerprint import ProcessingSession
from spot_detector.model.models import ColorAndParams
from spot_detector.model.processing_settings_models import PreprocessingSettings
from spot_detector.model.result_datastructures import CheckStatus, ImageResult, ImageTask, ROIData
from spot_detector.processing.process_chains import process_image
from spot_detector.processing.tsv_writer import TSVWriter
from spot_detector.errors import ProcessingSetupError
from spot_detector.misc import canonical_path

class ProcessingTaskManager:
    """
    """
    def __init__(self, session: ProcessingSession, writer: TSVWriter) -> None:
        self.session: ProcessingSession = session
        self.writer: TSVWriter = writer

        self.context: SpawnContext = get_context("spawn")
        self.workers: list[SpawnProcess] = []
        self.input_queue: QueueType[ImageTask | None] = self.context.Queue()
        self.output_queue: QueueType[ImageResult | ProcessingSetupError] = self.context.Queue()
        self.cancel: EventType = self.context.Event()
        self.expected: int = 0
        self.received: int = 0

        self.task_list: list[ImageTask] = []


    def create_task_list(self):
        self.task_list = []
        successes, fails = self.writer.get_processed_paths()
        # for now, no distinction between fails and successes
        processed_tasks_list = successes + fails
        processed_tasks = set(processed_tasks_list)

        proc_total = len(processed_tasks_list)
        proc_unique = len(processed_tasks)


        project_entries = self.session.processing_settings.entries
        snapshot_tasks: set[Path] = set()
        snapshot_total = 0
        for entry in project_entries:
            if isinstance(entry, str):
                snapshot_tasks.add(canonical_path(entry))
                snapshot_total += 1
            else:
                for file in entry.files:
                    snapshot_tasks.add(canonical_path(file))
                    snapshot_total += 1

        snapshot_tasks_list = natsorted(list(snapshot_tasks), key= lambda x: str(x))
        snapshot_unique = len(snapshot_tasks)

        for rank, path in enumerate(snapshot_tasks_list):
            if path not in processed_tasks:
                self.task_list.append(ImageTask(rank, path))

        final = len(self.task_list)

        if len(processed_tasks):
            self.session.logger.info(
              f"Selected files:  {snapshot_unique} unique / {snapshot_total} total ; "
            + f"Already processed files: {proc_unique} unique / {proc_total} total ; "
            + f"Selected and unprocessed files: {final}"
            )
        else:
            self.session.logger.info(
              f"Selected files:  {snapshot_unique} unique / {snapshot_total} total",
            )


    def get_ideal_process_count(self):
        # TODO: auto-detect the ideal number of parallel workers
        # For now, let's say
        worker_count = 2
        return worker_count

    def init_workers(self, worker_count: int):
        if worker_count < 1:
            worker_count = self.get_ideal_process_count()

        for id in range(worker_count):
            worker_name = f"Processing Worker {id}"
            worker_args = (
                self.input_queue,
                self.output_queue,
                self.session.project_snapshot.configuration,
                self.session.processing_settings.preprocessing,
                self.cancel,
                worker_name,
            )
            worker = self.context.Process(
                    target=process_runner,
                    name=worker_name,
                    args=worker_args
            )
            self.workers.append(worker)

        self.session.logger.info(f"{worker_count} workers created and waiting for processing to begin")


    def start_processing(self):
        for task in self.task_list:
            self.input_queue.put(task)
        for _worker in self.workers:
            self.input_queue.put(None)

        self.expected = len(self.task_list)
        self.received = 0
        for worker in self.workers:
            worker.start()


    def update_results_file(self):
        while True:
            try:
                result = self.output_queue.get_nowait()
            except Empty:
                return
            if isinstance(result, ImageResult):
                self.writer.write_result(result)
                self.received += 1
            else:
                self.session.logger.error(result)


    def poll(self) -> bool:
        """One tick of the coordinator. Returns True when nothing more will come."""
        self.update_results_file()

        if self.received >= self.expected:
            return True

        if any(worker.is_alive() for worker in self.workers):
            return False

        # tous sortis : leurs fils d'alimentation sont joints, ce qui reste est le dernier lot
        self.update_results_file()
        if self.received >= self.expected:
            return True

        for worker in self.workers:
            if worker.exitcode not in (0, None):
                self.session.logger.error(
                    f"{worker.name} exited with code {worker.exitcode}"
                )
        self.session.logger.error(
            f"{self.expected - self.received} images produced no result"
        )
        return True


    def request_cancel(self) -> None:
        """Ask the workers to stop once they are done with their current image."""
        self.cancel.set()
        self.session.logger.info("cancellation requested by the user")

    def shutdown(self, grace_seconds: float = 10.0) -> None:
        """Join every worker, killing the ones that do not come back.

        Only call once `poll` has returned True, or after `request_cancel`: a
        worker terminated while writing on the output queue can leave a partial
        object in the pipe and poison it for every later read.
        """
        deadline = monotonic() + grace_seconds
        for worker in self.workers:
            if worker.is_alive():
                worker.join(max(0.0, deadline - monotonic()))

        for worker in self.workers:
            if worker.is_alive():
                self.session.logger.warning(f"{worker.name} ignored the cancellation, terminating")
                worker.terminate()
                worker.join(1.0)
            if worker.is_alive():
                self.session.logger.error(f"{worker.name} ignored terminate, killing")
                worker.kill()
                worker.join()

        # The tasks still queued will never be delivered, and the parent would
        # otherwise block at exit waiting for its feeder thread to empty a pipe
        # nobody reads any more.
        self.input_queue.cancel_join_thread()
        self.session.logger.info(
            f"processing ended: {self.received} results collected out of {self.expected} expected"
        )



def process_runner(
    in_queue: QueueType[ImageTask | None],
    out_queue: QueueType[ImageResult | ProcessingSetupError],
    config: ColorAndParams,
    preproc_settings: PreprocessingSettings,
    cancel: EventType,
    worker_name: str,
):
    parent = parent_process()
    if parent is None:
        error = ProcessingSetupError(f"Parent process of worker {worker_name} is None")
        out_queue.put(error)
        return

    while True:
        if cancel.is_set() or not parent.is_alive():
            return
        try:
            task = in_queue.get(timeout=0.5)
        except Empty:
            continue
        if task is None:
            return

        try:
            result = process_image(task, config, preproc_settings)
        except Exception:
            err_detail = format_exc()
            result = ImageResult(
                task, None,
                ROIData(CheckStatus.NotApplicable, None, None, None),
                {}, datetime.now(), None, "An error occurred during processing", err_detail
            )

        out_queue.put(result)
