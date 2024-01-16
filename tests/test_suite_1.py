# Standard Python Library
from multiprocessing import Queue
from random import randint, sample
from pathlib import Path
import unittest
# Project files
from spot_detector.config import get_color_and_params
from spot_detector.multi_core import img_processer


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

    def test_img_processer(self):
        # setup
        test_images = Path("./images").resolve()
        files = filter(lambda x: x.is_file(), test_images.iterdir())
        img_samp = map(str, sample(list(files), 5))
        for img in img_samp:
            self.in_queue.put((randint(0, 256), randint(0, 256), img))
        self.in_queue.put("STOP")
        # run
        img_processer(self.in_queue, self.out_queue, self.cap)
        outputs = []
        while not self.out_queue.empty():
            outputs.append(self.out_queue.get())
        # assertion
        print(len(outputs), "outputs")
        for _, _, numbers in outputs:
            self.assertIsInstance(numbers, list)
            for val in numbers:
                self.assertIs(type(val), int)
                print(val)


if __name__ == "__main__":
    unittest.main()
