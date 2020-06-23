"""Classes for mock testing"""
import tkinter
import datetime
import pandas as pd

# 


class RootDestroyedException(BaseException):
    pass

# mock tkinter

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
        self.streamActive = False
        self.imageName = "asdf"

    def after(*args):
        """Override after method to avoid repeated calling"""
        pass


class mockRoot():
    def destroy(self):
        raise RootDestroyedException

# mock docker


class mockContainer():
    def __init__(self, log=None):
        self.log = log
        self.index = None
        self.engine = None

    def logs(self, tail=1):
        return self.log

    def stop(self):
        self.engine.containers.containerList.pop(self.index)


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

# misc functions


def raiseAssertion(*args, **kwargs):
    raise AssertionError


def yessayer(*args, **kwargs):
    return True