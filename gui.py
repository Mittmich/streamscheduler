import tkinter
import lib
from functools import partial
import datetime
from pathlib import Path
import logging
import tempfile
import os

# set loggingpath

datestring = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
tempdir = tempfile.gettempdir()
logFile = Path(f"{tempdir}/{datestring}.log")
logging.basicConfig(
    format="LOGGING::%(levelname)s::%(asctime)s:    %(message)s",
    filename=logFile,
    level=logging.INFO,
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

# disable module loggers

logging.getLogger("urllib3.connectionpool").disabled = True
logging.getLogger("docker.utils.config").disabled = True
logging.getLogger("docker.auth").disabled = True

# define classes


class Window(tkinter.Frame):
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        # changing the title of our master widget
        self.master.title("FGO Stream Scheduler")
        # set up parameter variables
        self.credentials = None
        self.container = None
        self.streamActive = False
        self.imageName = "ffmpeg:1.0"
        self.schedule = None
        self.timeToStream = "".join(["-"] * 8)
        self.purged = False
        # set up widgets
        lib.createTimeWidget(self)
        lib.createStatusWidget(self)
        lib.drawConfigGrid(self)
        # allowing the widget to take the full space of the root window
        self.pack(fill="both", expand=1)
        # creating a menu instance
        menu = tkinter.Menu(self.master)
        self.master.config(menu=menu)
        # create the file object)
        file = tkinter.Menu(menu)
        # add load config command
        file.add_command(
            label="Load config file", command=partial(lib.load_config, self)
        )
        # added "file" to our menu
        menu.add_cascade(label="File", menu=file)
        # add test menu
        test = tkinter.Menu(menu)
        test.add_command(
            label="Test OK Stream",
            command=partial(
                lib.setStream, frame=self, color="green", rate="1000kbit/s"
            ),
        )
        test.add_command(
            label="Test BAD Stream",
            command=partial(lib.setStream, frame=self, color="red", rate="-/-"),
        )
        test.add_command(
            label="Test Inactivate Stream",
            command=partial(lib.setStream, frame=self, color="yellow", rate="Inactive"),
        )
        test.add_command(
            label="Start Test Containter", command=partial(lib.startTestContainer, self)
        )
        test.add_command(
            label="Stop Test Containter", command=partial(lib.stopTestContainer, self)
        )
        menu.add_cascade(label="Test", menu=test)
        # add Containers
        containers = tkinter.Menu(menu)
        containers.add_command(
            label="Stop all containers",
            command=partial(
                lib.stopAllContainers, imageName=self.imageName, frame=self
            ),
        )
        menu.add_cascade(label="Containers", menu=containers)
        # configure grid
        for i in range(2):
            self.columnconfigure(i, weight=1, minsize=25)
            self.rowconfigure(i, weight=1, minsize=25)
        # check docker
        lib.checkDocker(self.imageName)
        # initial call to put checking stream events in the queue
        lib.checkStreamEvents(self)


# start of app


root = tkinter.Tk()
root.geometry("410x400")
app = Window(root)
# close dialog
root.protocol("WM_DELETE_WINDOW", partial(lib.askExit, app, root))
# icon
iconPath = "cropped-FGHomeOffice-1.png"
root.iconphoto(False, tkinter.PhotoImage(file=iconPath))
root.mainloop()
