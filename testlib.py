"""Classes for mock testing"""
import tkinter
import datetime
import pandas as pd
import docker

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
        self.call_ = None

    def logs(self, tail=1):
        return self.log

    def stop(self):
        self.engine.containers.containerList.pop(self.index)


class mockContainers():
    def __init__(self, name="asdf"):
        self.containerList = []
        self.engine = None
        self.image = name

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


class mockImages():
    def __init__(self, good=True, imageList=None) -> None:
        self.good = good
        self.imageList = None

    def get(self, imageName):
        if not self.good:
            raise docker.errors.ImageNotFound("asdf")
        else:
            return self.imageList


class mockEngine():
    def __init__(self, images="Good", version="Good") -> None:
        self.containers = mockContainers()
        self.containers.engine = self
        self.imagesInst = images
        self.versionInt = version

    def version(self):
        """Dummy call for version"""
        if self.versionInt != "Good":
            raise AssertionError

    @property
    def images(self):
            return self.imagesInst

# misc functions


def raiseAssertion(*args, **kwargs):
    raise AssertionError
