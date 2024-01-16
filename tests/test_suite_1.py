# Standard Python Library
from multiprocessing import Queue, Process
from pathlib import Path
from random import randint
from time import sleep
import unittest
# Project files
from spot_detector.config import get_color_and_params
from spot_detector.multi_core import img_processer, init_workers


class Test_img_processer(unittest.TestCase):
    def setUp(self):
        self.in_queue = Queue()
        self.out_queue = Queue()
        self.cap = get_color_and_params(
                    Path("./color_and_detection.toml").resolve()
                )

    def tearDown(self):
        self.in_queue.close()
        self.out_queue.close()

    def test_img_processer_single(self):
        # setup
        test_image = str(Path("./images/A6_2 0.0-0.2.JPG").resolve())
        x1, y1 = randint(0, 256), randint(0, 256)
        self.in_queue.put((x1, y1, test_image))
        self.in_queue.put("STOP")
        # run
        img_processer(self.in_queue, self.out_queue, self.cap)
        x2, y2, values = self.out_queue.get()
        # assertion
        self.assertEqual(x1, x2)
        self.assertEqual(y1, y2)
        self.assertIsInstance(values, list)
        for num in values:
            self.assertIs(type(num), int)

    def test_img_processer_multi(self):
        images = list(map(str, Path("./images").resolve().iterdir()))
        for img in images:
            self.in_queue.put((randint(0, 256), randint(0, 256), img))
        cap_path = Path("./color_and_detection.toml").resolve()
        cap = get_color_and_params(cap_path)
        workers = init_workers(10, cap, self.in_queue, self.out_queue)
        for worker in workers:
            self.in_queue.put("STOP")
            worker.run()
        output_list = []
        while (any_alive(workers)):
            if self.out_queue.empty():
                sleep(1)
            else:
                output_list.append(self.out_queue.get())
        print("HEY")
        for output in output_list:
            x, y, values = output
            print(values)
            self.assertIs(type(x), int)
            self.assertIs(type(y), int)
            self.assertIsInstance(values, list, msg=f"{values}")
            for val in values:
                self.assertIs(type(val), int)


def any_alive(worker_list: list[Process]):
    status_list = map(lambda x: x.is_alive(), worker_list)
    return any(status_list)


if __name__ == "__main__":
    unittest.main()
