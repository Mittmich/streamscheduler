import unittest
import lib
import pandas as pd
from pandas.testing import assert_frame_equal
from lib import checkStream
import testlib
from pathlib import Path
from functools import partial
import logging

# TestCases

# Switch off logging
logging.getLogger("lib").disabled = True


class TestCheckStream(unittest.TestCase):
    """Tests the checkStream function"""

    def test_checkStream_noContainer(self):
        # test whether nothing happens if container is none
        mockframe = testlib.mockFrame()
        # monkey patch onupdate
        lib.onUpdate = lambda x: 1
        lib.createStatusWidget(mockframe)
        lib.checkStream(mockframe)
        self.assertEqual(mockframe.status.get(), "yellow")
        self.assertEqual(mockframe.streamActive, False)

    def test_checkStream_containerRunningEarly(self):
        """Tests whether the reaction to a running container that
        has no valid bitrate output is correct."""
        # test whether nothing happens if container is none
        mockframe = testlib.mockFrame()
        mockframe.container = testlib.mockContainer(status="running", log=b"asdf")
        # monkey patch onupdate
        lib.onUpdate = lambda x: 1
        lib.createStatusWidget(mockframe)
        lib.checkStream(mockframe)
        self.assertEqual(mockframe.status.get(), "green")
        self.assertEqual(mockframe.streamActive, False)
        self.assertEqual(mockframe.lbl_StreamSpeed["text"], "-/-")

    def test_checkStream_containerRunningLate(self):
        """Tests whether the reaction to a running container that
        has no valid bitrate output is correct."""
        # test whether nothing happens if container is none
        mockframe = testlib.mockFrame()
        mockframe.container = testlib.mockContainer(status="running", log=b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                                  b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                                  b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s"
                                                                  b"\rframe 918.3kbits/s 38.8image 25 fps \frame 920.3kbits/s")
        # monkey patch onupdate
        lib.onUpdate = lambda x: 1
        lib.createStatusWidget(mockframe)
        lib.checkStream(mockframe)
        self.assertEqual(mockframe.status.get(), "green")
        self.assertEqual(mockframe.streamActive, False)
        self.assertEqual(mockframe.lbl_StreamSpeed["text"], "920.3kbits/s")

    def test_checkStream_containerCreated_inList(self):
        """Tests whether the reaction to a created container that
        is then the client.containers.list is correct"""
        mockframe = testlib.mockFrame()
        mockframe.container = testlib.mockContainer(status="created", log=b"asdf")
        # monkey patch onupdate
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda x: 1
        # monkeypatch client
        oldClient = lib.docker.from_env
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages(), containers=[mockframe.container])
        lib.createStatusWidget(mockframe)
        lib.checkStream(mockframe)
        self.assertEqual(mockframe.status.get(), "green")
        self.assertEqual(mockframe.streamActive, False)
        self.assertEqual(mockframe.lbl_StreamSpeed["text"], "-/-")
        # undo monkeypatch
        lib.onUpdate = oldOnUpdate
        lib.docker.from_env = oldClient

    def test_checkStream_containerCreated_finished(self):
        """Check whether reaction to a container that has been created and
        finished succesfully is correct."""
        mockframe = testlib.mockFrame()
        mockframe.container = testlib.mockContainer(status="created", log=b"asdf")
        # monkey patch onupdate
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda x: 1
        # monkeypatch client
        oldClient = lib.docker.from_env
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages())
        lib.createStatusWidget(mockframe)
        lib.checkStream(mockframe)
        self.assertEqual(mockframe.status.get(), "yellow")
        self.assertEqual(mockframe.streamActive, False)
        self.assertEqual(mockframe.lbl_StreamSpeed["text"], "Inactive")
        self.assertEqual(mockframe.container, None)
        # undo monkeypatch
        lib.onUpdate = oldOnUpdate
        lib.docker.from_env = oldClient

    def test_checkStream_containerCreated_crashed(self):
        """Check whether reaction to a container that has been created and
        finished succesfully is correct."""
        mockframe = testlib.mockFrame()
        mockframe.container = testlib.mockContainer(status="created", log=b"error")
        # monkey patch onupdate
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda x: 1
        # monkeypatch client
        oldClient = lib.docker.from_env
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages())
        lib.showerror = testlib.raiseAssertion
        lib.createStatusWidget(mockframe)
        badcall = partial(checkStream, mockframe)
        self.assertRaises(AssertionError, badcall)
        self.assertEqual(mockframe.status.get(), "yellow")
        self.assertEqual(mockframe.streamActive, False)
        self.assertEqual(mockframe.lbl_StreamSpeed["text"], "Inactive")
        self.assertEqual(mockframe.container, None)
        # undo monkeypatch
        lib.onUpdate = oldOnUpdate
        lib.docker.from_env = oldClient


class TestCheckRightTime(unittest.TestCase):
    """Tests the checkRightTime function."""

    def test_checkRightTime_noSchedule(self):
        mockframe = testlib.mockFrame()
        # monkeypatch dispatch stream
        oldDispatch = lib.dispatch_stream
        lib.dispatch_stream = testlib.raiseAssertion
        lib.checkRightTime(mockframe)  # should not raise AssertionError
        self.assertEqual(mockframe.container, None)
        self.assertEqual(mockframe.streamActive, False)
        # undo monkeypatch
        lib.dispatch_stream = oldDispatch

    def test_checkRightTime_StreamInFuture(self):
        mockframe = testlib.mockFrame()
        # add current time
        mockframe.nowDT = pd.Timestamp("2010-06-21 12:00:00")
        # add schedule
        mockframe.schedule = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                            "Date/Time": [pd.Timestamp("2025-06-21 12:00:00"),
                                                          pd.Timestamp("2025-06-22 13:00:00"),
                                                          pd.Timestamp("2025-07-23 14:00:00")]})
        # monkeypatch dispatch stream
        oldDispatch = lib.dispatch_stream
        lib.dispatch_stream = testlib.raiseAssertion
        lib.checkRightTime(mockframe)  # should not raise AssertionError
        self.assertEqual(mockframe.container, None)
        self.assertEqual(mockframe.streamActive, False)
        # undo monkeypatch
        lib.dispatch_stream = oldDispatch

    def test_checkRightTime_StreamInPast(self):
        mockframe = testlib.mockFrame()
        # add current time
        mockframe.nowDT = pd.Timestamp("2010-06-21 12:00:00")
        # add schedule
        mockframe.schedule = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                            "Date/Time": [pd.Timestamp("2009-06-21 12:00:00"),
                                                          pd.Timestamp("2009-06-22 13:00:00"),
                                                          pd.Timestamp("2009-07-23 14:00:00")]})
        # monkeypatch dispatch stream
        oldDispatch = lib.dispatch_stream
        lib.dispatch_stream = testlib.raiseAssertion
        lib.checkRightTime(mockframe)  # should not raise AssertionError
        self.assertEqual(mockframe.container, None)
        self.assertEqual(mockframe.streamActive, False)
        # undo monkeypatch
        lib.dispatch_stream = oldDispatch

    def test_checkRightTime_RightTime(self):
        mockframe = testlib.mockFrame()
        # add current time
        mockframe.nowDT = pd.Timestamp("2010-06-21 12:00:00")
        # add schedule
        mockframe.schedule = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                            "Date/Time": [pd.Timestamp("2010-06-21 12:00:01"),
                                                          pd.Timestamp("2009-06-22 13:00:00"),
                                                          pd.Timestamp("2009-07-23 14:00:00")]})
        # monkeypatch dispatch stream
        oldDispatch = lib.dispatch_stream
        lib.dispatch_stream = testlib.raiseAssertion
        goodCall = partial(lib.checkRightTime, mockframe)
        self.assertRaises(AssertionError, goodCall)
        # second monkeypatch to check whether events afterwards happen correctly
        lib.dispatch_stream = lambda x, y, z: None
        mockframe.after = testlib.raiseAssertion  # this is called by the error dispatching functions
        oldDrawConfig = lib.draw_config
        lib.draw_config = lambda x, y: None
        goodCall = partial(lib.checkRightTime, mockframe)
        self.assertRaises(AssertionError, goodCall)
        # call it again to see whether the effects are correct
        mockframe.after = lambda x, y, z, a: None  # this is called by the error dispatching functions
        lib.checkRightTime(mockframe)  # before the call only goes through to frame.after because assertion is raised there
        self.assertEqual(len(mockframe.schedule), 2)
        self.assertEqual(mockframe.streamActive, False)
        # undo monkeypatch
        lib.dispatch_stream = oldDispatch
        lib.draw_config = oldDrawConfig


class TestGui(unittest.TestCase):

    def test_createTimeWidget(self):
        mockframe = testlib.mockFrame()
        # monkey patch onupdate
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda x: 1
        lib.createTimeWidget(mockframe)
        # check whether it is there
        self.assertTrue(hasattr(mockframe, "time_label"))
        self.assertTrue(hasattr(mockframe, "time_title"))
        self.assertTrue(hasattr(mockframe, "now"))
        # undo monkey patch
        lib.onUpdate = oldOnUpdate

    def test_createStatusWidget(self):
        mockframe = testlib.mockFrame()
        # monkey patch onupdate
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda x: 1
        lib.createStatusWidget(mockframe)
        # check whether it is there
        self.assertTrue(hasattr(mockframe, "status"))
        self.assertTrue(hasattr(mockframe, "streamSpeed"))
        self.assertTrue(hasattr(mockframe, "status_title"))
        self.assertTrue(hasattr(mockframe, "rectl_status"))
        self.assertTrue(hasattr(mockframe, "lbl_StreamSpeed"))
        # undo monkey patch
        lib.onUpdate = oldOnUpdate

    def test_setStream(self):
        mockframe = testlib.mockFrame()
        lib.createStatusWidget(mockframe)
        lib.setStream(mockframe, "green", "1234")
        self.assertEqual(mockframe.status.get(), "green")
        self.assertEqual(mockframe.streamSpeed.get(), "1234")

    def test_checkPastStream(self):
        mockframe = testlib.mockFrame()
        mockframe.streamActive = True
        mockframe.nowDT = pd.Timestamp("2009-07-23 14:00:00")
        # monkey patch draw config and on update
        oldDrawConfig = lib.draw_config
        lib.draw_config = lambda x, y: None
        oldOnUpdate = lib.onUpdate
        lib.onUpdate = lambda: None
        # only present/future events
        goodDf = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                                    "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                            "Date/Time": [pd.Timestamp("2015-06-21 12:00:01"),
                                                          pd.Timestamp("2015-06-22 13:00:00"),
                                                          pd.Timestamp("2015-07-23 14:00:00")]})
        mockframe.schedule = goodDf
        lib.checkPastStream(mockframe)
        assert_frame_equal(mockframe.schedule, goodDf)
        # one past event
        badDf = pd.DataFrame({"File": ["C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test.mp4",
                                        "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test2.mp4",
                                        "C:\\Users\\michael.mitter\\Documents\\streamscheduler\\test_files\\vids\\test4.mp4"],
                                    "Date/Time": [pd.Timestamp("2008-06-21 12:00:01"),
                                                  pd.Timestamp("2012-06-22 13:00:00"),
                                                  pd.Timestamp("2012-07-23 14:00:00")]})
        mockframe.schedule = badDf
        lib.checkPastStream(mockframe)
        assert_frame_equal(mockframe.schedule, badDf.iloc[1:, :])
        # restore old draw config
        lib.draw_config = oldDrawConfig
        lib.onUpdate = oldOnUpdate

    def test_drawconfigGrid(self):
        mockframe = testlib.mockFrame()
        lib.drawConfigGrid(mockframe)
        self.assertEqual(list(mockframe.grid["Names"].keys()), ["File", "Date/Time"])
        self.assertEqual(len(mockframe.grid["grid"]), 10)
        for i in range(10):
            self.assertEqual(len(mockframe.grid["grid"][i]), 2)

    def test_askExit(self):
        # make mockfraem
        mockframe = testlib.mockFrame()
        mockroot = testlib.mockRoot()
        # save old askyesno
        oldAskYesNo = lib.askyesno
        # monkey patch in alwasy true
        lib.askyesno = lambda x, y: True
        # set stream to active
        mockframe.streamActive = True
        destroyCall = partial(lib.askExit, frame=mockframe, root=mockroot)
        self.assertRaises(testlib.RootDestroyedException, destroyCall)
        # set stream to inactive
        lib.askyesno = lambda x, y: False
        # set stream to active
        mockframe.streamActive = True
        destroyCall = partial(lib.askExit, frame=mockframe, root=mockroot)
        # restore old function
        lib.askyesno = oldAskYesNo


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
        # monkey patch lib.showerror so that I can catch to result
        lib.showerror = testlib.raiseAssertion

    def test_parseContainerOutput(self):
        # test no bitrate
        result = next(lib.parseContainerOutput(self.badContainer))
        self.assertIsNone(result)
        # test bitrate
        result = next(lib.parseContainerOutput(self.GoodContainer))
        self.assertEqual(result, "920.3kbits/s")

    def test_loadconfig(self):
        lib.load_config(self.mockframe, filepath="./test_files/test_schedule_1_mock_good.xlsx")
        assert_frame_equal(self.mockframe.schedule, self.goodConfig)
        self.assertEqual(self.mockframe.credentials, self.goodCredentials)

    def test_drawconfig(self):
        lib.load_config(self.mockframe, filepath="./test_files/test_schedule_1_mock_good.xlsx")
        i = 0
        for i in range(len(self.mockframe.schedule)):
            tempFile = self.mockframe.grid["grid"][i][0].get()
            self.assertEqual(Path(self.mockframe.schedule.iloc[i, 0]).name, tempFile)
            tempDateTime = pd.Timestamp(self.mockframe.grid["grid"][i][1].get())
            self.assertEqual(self.mockframe.schedule.iloc[i, 1], tempDateTime)
        # Test that the other lines contain ----
        for index in range(i + 1, 10):
            temp = self.mockframe.grid["grid"][index][0].get()
            self.assertEqual(temp, " ".join(["-"] * 20))

    def test_checkConfigTiming(self):
        # bad example
        badCall = partial(lib.load_config, frame=self.mockframe, filepath="./test_files/test_schedule_1_mock_badTiming.xlsx")
        self.assertRaises(AssertionError, badCall)
        # good example
        goodCall = partial(lib.load_config, frame=self.mockframe, filepath="./test_files/test_schedule_1_mock_good.xlsx")
        goodCall()

    def test_config_format(self):
        # bad example - bad datatypes
        badCall = partial(lib.load_config, frame=self.mockframe, filepath="./test_files/test_schedule_1_mock_badDtypes.xlsx")
        self.assertRaises(AssertionError, badCall)
        # bad example - badfiles
        badCall = partial(lib.load_config, frame=self.mockframe, filepath="./test_files/test_schedule_1_mock_badfiles.xlsx")
        self.assertRaises(AssertionError, badCall)
        # bad example - bad videodirs
        badCall = partial(lib.load_config, frame=self.mockframe, filepath="./test_files/test_schedule_1_mock_badVideoDir.xlsx")
        self.assertRaises(AssertionError, badCall)

    def test_parseFailure(self):
        badContainer1 = testlib.mockContainer(b"I am a failure!")
        self.assertTrue(lib.parseFailure(badContainer1))
        badContainer2 = testlib.mockContainer(b"Everything is an error..")
        self.assertTrue(lib.parseFailure(badContainer2))
        badContainer3 = testlib.mockContainer(b"Not found...")
        self.assertTrue(lib.parseFailure(badContainer3))


class TestDockers(unittest.TestCase):
    def makeGood(self):
        # setup things in a way that all tests of checkDocker will pass
        lib.shutil.which = lambda x: "asdf"  # this will make the call return something
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages())
        lib.countImages = lambda x: 0

    def test_checkDocker(self):
        # save all functions that will be monkey patched here
        oldWhich = lib.shutil.which
        oldClient = lib.docker.from_env
        oldCountImages = lib.countImages
        oldShowerror = lib.showerror
        # check if everything passes
        lib.showerror = testlib.raiseAssertion
        self.makeGood()
        lib.checkDocker("ffmpeg:1.0")
        # simulate docker not installed
        lib.shutil.which = lambda x: None
        badCall = partial(lib.checkDocker, "asdf")
        self.assertRaises(AssertionError, badCall)
        # reset to good version
        self.makeGood()
        # simulate version is not ok
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages(), version="Bad")
        badCall = partial(lib.checkDocker, "asdf")
        self.assertRaises(AssertionError, badCall)
        # reset to good version
        self.makeGood()
        # simulate image is not installed
        lib.docker.from_env = lambda: testlib.mockEngine(testlib.mockImages(good=False))
        badCall = partial(lib.checkDocker, "asdf")
        self.assertRaises(AssertionError, badCall)
        # simulate count of image is not right
        self.makeGood()
        lib.countImages = lambda x: 1
        badCall = partial(lib.checkDocker, "asdf")
        self.assertRaises(AssertionError, badCall)
        # restore old funcitons
        lib.countImages = oldCountImages
        lib.docker.from_env = oldClient
        lib.shutil.which = oldWhich
        lib.showerror = oldShowerror

    def test_countImages(self):
        rightContainer = testlib.mockContainer(name="asdf")
        # 0 images
        oldClient = lib.docker.from_env
        lib.docker.from_env = lambda: testlib.mockEngine(containers=[])
        self.assertEqual(lib.countImages("asdf"), 0)
        # 2 images
        lib.docker.from_env = lambda: testlib.mockEngine(containers=[rightContainer, rightContainer])
        self.assertEqual(lib.countImages("asdf"), 2)
        # restore old client
        lib.docker.from_env = oldClient


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
        lib.dispatch_test_stream(self.credentials, self.engine)
        self.assertEqual(len(self.engine.containers), 1)

    def test_dispatch_Stream(self):
        # test whether container is dispatched
        lib.dispatch_stream("mockfile", credentials=self.credentials, pathmap="dummy", engine=self.engine)
        self.assertEqual(len(self.engine.containers), 1)


if __name__ == '__main__':
    res = unittest.main(verbosity=3, exit=False)
