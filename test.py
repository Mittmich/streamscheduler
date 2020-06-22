import unittest
from lib import parseContainerOutput

# helper classes


class mockContainer():
    def __init__(self, log):
        self.log = log

    def logs(self, tail=1):
        return self.log

# TestCases


class TestParse(unittest.TestCase):
    def setUp(self) -> None:
        self.GoodContainer = mockContainer(b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s")
        self.badContainer = mockContainer(b"press [q] press [h]")

    def test_parseContainerOutput(self):
        # test no bitrate
        result = next(parseContainerOutput(self.badContainer))
        self.assertIsNone(result)
        # test bitrate
        result = next(parseContainerOutput(self.GoodContainer))
        self.assertEqual(result, "920.3kbits/s")


if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
