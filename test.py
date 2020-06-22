import unittest
from lib import drawConfigGrid, parseContainerOutput, load_config
import pandas as pd
from pandas.testing import assert_frame_equal
import tkinter
# helper classes


class mockContainer():
    def __init__(self, log):
        self.log = log

    def logs(self, tail=1):
        return self.log


class mockFrame(tkinter.Frame):
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.master = master
        self.grid = None
        self.schedule = None

# TestCases


class TestGui(unittest.TestCase):
    def test_drawconfigGrid(self):
        mockframe = mockFrame()
        drawConfigGrid(mockframe)
        self.assertEqual(list(mockframe.grid["Names"].keys()), ["File", "Date/Time"])
        self.assertEqual(len(mockframe.grid["grid"]), 10)
        for i in range(10):
            self.assertEqual(len(mockframe.grid["grid"][i]), 2)


class TestParse(unittest.TestCase):
    def setUp(self) -> None:
        self.GoodContainer = mockContainer(b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                           b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s")
        self.badContainer = mockContainer(b"press [q] press [h]")
        self.goodConfig = pd.DataFrame({"File": ["test.mp4", "test2.mp4", "test4.mp4"],
                                        "Date/Time": [pd.Timestamp("2020-06-21 12:00:00"),
                                                      pd.Timestamp("2020-06-22 13:00:00"),
                                                      pd.Timestamp("2021-07-23 14:00:00")]})
        self.mockframe = mockFrame()
        # draw grid onto mockFrame
        drawConfigGrid(self.mockframe)

    def test_parseContainerOutput(self):
        # test no bitrate
        result = next(parseContainerOutput(self.badContainer))
        self.assertIsNone(result)
        # test bitrate
        result = next(parseContainerOutput(self.GoodContainer))
        self.assertEqual(result, "920.3kbits/s")

    def test_loadconfig(self):
        load_config(self.mockframe, filepath="./test_files/test_schedule_1_mock.xlsx")
        assert_frame_equal(self.mockframe.schedule, self.goodConfig)

if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
