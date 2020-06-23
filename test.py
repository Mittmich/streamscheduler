import unittest
import lib
import pandas as pd
from pandas.testing import assert_frame_equal
import tkinter
import datetime
from pathlib import Path

# TODO make mock tkiner and docker to unify this
# helper classes


class mockContainer():
    def __init__(self, log=None):
        self.log = log
        self.index = None
        self.engine = None

    def logs(self, tail=1):
        return self.log

    def stop(self):
        self.engine.containers.containerList.pop(self.index)


class mockFrame(tkinter.Frame):
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.master = master
        self.grid = None
        self.schedule = pd.DataFrame()
        self.credentials = None
        self.container = None
        self.status = tkinter.StringVar()
        self.lbl_StreamSpeed = tkinter.Label(self)
        self.streamSpeed = tkinter.StringVar()
        self.nowDT = datetime.datetime(year=1900, month=12, day=5)
        self.streamActive = True
        self.imageName = "asdf"

    def after(*args):
        """Override after method to avoid repeated calling"""
        pass


class mockContainers():
    def __init__(self):
        self.containerList = []
        self.engine = None

    def list(self):
        return self.containerList

    def run(self, *args, **kwargs):
        newCont = mockContainer(b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s")
        self.containerList.append(newCont)
        newCont.index = self.containerList.index(newCont)
        newCont.engine = self.engine
        return newCont

    def __len__(self):
        return len(self.containerList)


class mockEngine():
    def __init__(self) -> None:
        self.containers = mockContainers()
        self.containers.engine = self


# TestCases


class TestGui(unittest.TestCase):
    def test_drawconfigGrid(self):
        mockframe = mockFrame()
        lib.drawConfigGrid(mockframe)
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
        self.goodConfig = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                 "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                 "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                        "Date/Time": [pd.Timestamp("2025-06-21 12:00:00"),
                                                      pd.Timestamp("2025-06-22 13:00:00"),
                                                      pd.Timestamp("2025-07-23 14:00:00")]})
        self.goodCredentials = {"User": 12345, "Password": 678910,
                                "rtmp-URL": "rtmp://i.amagood.server",
                                "playpath": "dclive_0_1@2345"}
        self.mockframe = mockFrame()
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
        self.engine = mockEngine()
        self.mockframe = mockFrame()
        self.mockframe.credentials = self.credentials

    def tearDown(self) -> None:
        self.engine = mockEngine()

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
