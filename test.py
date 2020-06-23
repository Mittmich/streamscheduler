import unittest
import lib
import pandas as pd
from pandas.testing import assert_frame_equal
import testlib
from pathlib import Path


# TestCases


class TestGui(unittest.TestCase):
    def test_drawconfigGrid(self):
        mockframe = testlib.mockFrame()
        lib.drawConfigGrid(mockframe)
        self.assertEqual(list(mockframe.grid["Names"].keys()), ["File", "Date/Time"])
        self.assertEqual(len(mockframe.grid["grid"]), 10)
        for i in range(10):
            self.assertEqual(len(mockframe.grid["grid"][i]), 2)


class TestParse(unittest.TestCase):
    def setUp(self) -> None:
        self.GoodContainer = testlib.mockContainer(b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                   b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                   b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                   b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s")
        self.badContainer = testlib.mockContainer(b"press [q] press [h]")
        self.goodConfig = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                 "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                 "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                        "Date/Time": [pd.Timestamp("2025-06-21 12:00:00"),
                                                      pd.Timestamp("2025-06-22 13:00:00"),
                                                      pd.Timestamp("2025-07-23 14:00:00")]})
        self.goodCredentials = {"User": 12345, "Password": 678910,
                                "rtmp-URL": "rtmp://i.amagood.server",
                                "playpath": "dclive_0_1@2345"}
        self.mockframe = testlib.mockFrame()
        # draw grid onto mockFrame
        lib.drawConfigGrid(self.mockframe)

    def test_parseContainerOutput(self):
        # test no bitrate
        result = next(lib.parseContainerOutput(self.badContainer))
        self.assertIsNone(result)
        # test bitrate
        result = next(lib.parseContainerOutput(self.GoodContainer))
        self.assertEqual(result, "920.3kbits/s")

    def test_loadconfig(self):
        # TODO: find a way to not prune past events in these tests
        lib.load_config(self.mockframe, filepath="./test_files/test_schedule_1_mock_good.xlsx")
        assert_frame_equal(self.mockframe.schedule, self.goodConfig)
        self.assertEqual(self.mockframe.credentials, self.goodCredentials)

    def test_drawconfig(self):
        lib.load_config(self.mockframe, filepath="./test_files/test_schedule_1_mock_good.xlsx")
        for i in range(len(self.mockframe.schedule)):
            tempFile = self.mockframe.grid["grid"][i][0].get()
            self.assertEqual(Path(self.mockframe.schedule.iloc[i, 0]).name, tempFile)
            tempDateTime = pd.Timestamp(self.mockframe.grid["grid"][i][1].get())
            self.assertEqual(self.mockframe.schedule.iloc[i, 1], tempDateTime)


class TestStream(unittest.TestCase):
    def setUp(self):
        self.credentials = {"User": 12345, "Password": 678910,
                            "rtmp-URL": "rtmp://i.amagood.server",
                            "playpath": "dclive_0_1@2345"}
        self.engine = testlib.mockEngine()
        self.mockframe = testlib.mockFrame()
        self.mockframe.credentials = self.credentials

    def tearDown(self) -> None:
        self.engine = testlib.mockEngine()

    def test_dispatch_test_stream(self):
        cont = lib.dispatch_test_stream(self.credentials, self.engine)
        self.assertEqual(len(self.engine.containers), 1)

    def test_startTestContainer(self):
        lib.startTestContainer(self.mockframe, self.engine)
        self.assertEqual(len(self.engine.containers), 1)

    def test_start_stopTestContainer(self):
        lib.startTestContainer(self.mockframe, self.engine)
        self.assertEqual(len(self.engine.containers), 1)
        lib.stopTestContainer(self.mockframe)
        self.assertEqual(len(self.engine.containers), 0)


if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
