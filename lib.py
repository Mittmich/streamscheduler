from pathlib import Path
import datetime
import docker
import re
from tkinter import filedialog
import pandas as pd
import tkinter
from tkinter.messagebox import showinfo
import pathlib
import numpy as np

# define global variables

RTMPSETTINGS_TEMPLATE = ("'{} "
                         "flashver=FMLE/3.020(compatible;20FMSc/1.0)"
                         " live=true pubUser={} pubPasswd={} playpath={}'")

FFMPEG_TEMPLATE_TEST = """ffmpeg -re\
                        -f lavfi\
                        -i testsrc\
                        -c:v libx264\
                        -b:v 1600k\
                        -preset ultrafast\
                        -b 900k\
                        -c:a libfdk_aac\
                        -b:a 128k\
                        -s 960x720\
                        -x264opts keyint=50\
                        -g 25\
                        -pix_fmt yuv420p\
                        -f flv {}"""


# misc


def currentTime():
    """Get current date and time"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# parsing realted functions


def check_config_timing(df):
    # check time difference
    diffs = pd.Series(np.diff(df["Date/Time"]))
    target = datetime.timedelta(minutes=30)
    try:
        assert not any(diff < target for diff in diffs)
    except AssertionError:
        showinfo("Error", "Stream timepoints are closer together than 30 min!")


def check_config_format(df):
    """Checks whether config entries are valid"""
    # check datatypes
    try:
        for row in df.iterrows():
                assert isinstance(row[1]["Date"], datetime.datetime)
                assert isinstance(row[1]["Time"], datetime.time)
                assert isinstance(row[1]["File"], str)
    except AssertionError:
        showinfo("Error", "Schedule does not have the right format/datatypes!")
        return False
    # check whether path to mp4 exists
    try:
        for fileP in df["File"]:
            temp = pathlib.Path(fileP)
            assert temp.exists()
    except AssertionError:
        showinfo("Error", "Video files do not exist!")
        return False
    return True


def makeQueue(df):
    """Makes a queue of videos to stream from config files
    """


def parseContainerOutput(contID):
    """Parses container output"""
    while True:
        line = contID.logs(tail=1)
        if len(line.strip().decode().split(" ")) < 10:
            yield None
        else:
            # standard out trick to parse ffmpeg output
            yield re.findall(r"\d+\.\dkbits\/s", line.strip().decode())[-1]  # yield newest bitrate


def load_config(frame, filepath=None):
    if filepath is None:
        filename = filedialog.askopenfilename(initialdir="/", title="Select file",
                                              filetypes=(("xlsx files", "*.xlsx"), ("all files", "*.*")))
    else:
        filename = filepath
    schedule = pd.read_excel(filename)
    # check format of config
    good = check_config_format(schedule)
    if good:
        # combine date and time for display
        schedule.loc[:, "Date/Time"] = schedule.apply(lambda x: pd.Timestamp.combine(x["Date"], x["Time"]), axis=1)
        schedule = schedule.drop(columns=["Date", "Time"])
        # sort by date/time
        schedule = schedule.sort_values(by="Date/Time")
        # check config
        check_config_timing(schedule)
        # load credentials
        credentials = pd.read_excel(filename, sheet_name="Credentials")
        frame.credentials = credentials.T[0].to_dict()
        frame.schedule = schedule
        draw_config(frame, schedule)


def parseFailure(container):
    """Check if container has failed.
    This is very crude!"""
    check = container.logs().decode()
    if ("error" in check) or ("failure" in check):
        return True
    return False


def draw_config(window, loadedFrame):
    # draw elements
    for index, row in enumerate(loadedFrame.head(n=10).iterrows()):
        # only show filename
        filePath = pathlib.Path(row[1]["File"])
        window.grid["grid"][index][0].set(filePath.name)
        window.grid["grid"][index][1].set(row[1]["Date/Time"])


# Streaming related functions


def checkMatch(streamQueue, currentTime):
    """Checks whether a stream needs to be started"""


def dispatch_test_stream(credentials, engine=None):
    """Starts streaming via ffmpeg.
    Returns subprocess.Popen instance."""
    # fill in credentials
    filledRTMP = RTMPSETTINGS_TEMPLATE.format(credentials["rtmp-URL"],
                                              credentials["User"], credentials["Password"],
                                              credentials["playpath"])
    # fill in ffmpeg
    ffmpegCommand = FFMPEG_TEMPLATE_TEST.format(filledRTMP)
    # connect to docker client
    if engine is None:
        client = docker.from_env()
    else:
        client = engine
    # start container
    contID = client.containers.run("ffmpeg:1.0", ffmpegCommand, detach=True)
    return contID


def startTestContainer(frame, engine=None):
    if frame.credentials is None:
        showinfo("Error", "No credentials specified!")
        return
    if frame.container is not None:
        showinfo("Error", "A stream is already running!")
    else:
        frame.container = dispatch_test_stream(frame.credentials, engine=engine)
        setStream(frame, "grey", "Waiting")


def stopTestContainer(frame):
    if frame.container is not None:
        frame.container.stop()
        frame.container = None
    else:
        showinfo("Error", "No container is running!")
        return
    client = docker.from_env()
    if len(client.containers.list()) == 0:
        setStream(frame, "yellow", "Incative")

# gui-related functions


# Set up time widget


def createTimeWidget(frame):
    frameW = tkinter.Frame(frame)
    frame.now = tkinter.StringVar()
    # Title
    frame.title = tkinter.Label(frameW, text="Current Time:", font=('Helvetica', 12))
    frame.title.pack()
    # system time
    frame.time = tkinter.Label(frameW, font=('Helvetica', 8))
    frame.time.pack()
    frame.time["textvariable"] = frame.now
    # initial time display
    onUpdate(frame)
    frameW.grid(column=1, row=1, sticky="S")


def onUpdate(frame):
    # update displayed time
    frame.now.set(currentTime())
    # schedule timer to call myself after 1 second
    frame.after(1000, onUpdate, frame)


def createStatusWidget(frame):
    # define variables
    frame.status = tkinter.StringVar()
    frame.streamSpeed = tkinter.StringVar()
    # set initial things
    frame.status.set("yellow")
    frame.streamSpeed.set("Inactive")
    # create subwindow in toplevel window
    frameS = tkinter.Frame(frame)
    # Title
    frame.status_title = tkinter.Label(frameS, text="Stream Status:", font=('Helvetica', 12))
    frame.status_title.pack()
    # status rectangle
    frame.rectl_status = tkinter.Frame(frameS, width=20, height=20)
    frame.rectl_status.pack()
    # streamingspeed
    frame.lbl_StreamSpeed = tkinter.Label(frame.rectl_status, font=('Helvetica', 8))
    frame.lbl_StreamSpeed.pack()
    frame.lbl_StreamSpeed["textvariable"] = frame.streamSpeed
    frame.lbl_StreamSpeed.configure(bg=frame.status.get())
    frameS.grid(column=0, row=1, sticky="S")


def checkStream(frame):
    """checks continuously whether
    a Stream is running and sets the
    statusWidget accordingly"""
    client = docker.from_env()
    # check whether container is running
    if frame.container is not None:
        status = frame.container.status
        if status == "created":
            # check whether stream is in client
            containers = client.containers.list()
            if frame.container not in containers:
                # check whether there is a failure
                failed = parseFailure(frame.container)
                if failed:  # failure
                    setStream(frame, "red", "-/-")
                else:  # was ok
                    setStream(frame, "yellow", "Inactivate")
            else:  # just started
                setStream(frame, "green", "-/-")
                # get bitrate
                output = next(parseContainerOutput(frame.container))
                # set stream Ok
                if output is not None:
                    setStream(frame, "green", output)
        if status == "running":
            setStream(frame, "green", "-/-")
            # get bitrate
            output = next(parseContainerOutput(frame.container))
            # set stream Ok
            if output is not None:
                setStream(frame, "green", output)
    frame.after(1000, checkStream, frame)


def setStream(frame, color, rate):
    frame.status.set(color)
    # update status to green
    frame.lbl_StreamSpeed.configure(bg=frame.status.get())
    frame.streamSpeed.set(rate)


def drawConfigGrid(window):
    # make empty grid
    grid = [[[], []] for i in range(10)]
    # setup grid parameter in window
    window.grid = {"Names": [], "grid": grid}
    frameM = tkinter.Frame(window)  # child of window
    # draw column boxes
    window.grid["Names"] = {}
    for i, name in enumerate(["File", "Date/Time"]):
        frame = tkinter.Frame(
                frameM,
                relief=tkinter.RAISED,
                borderwidth=1
            )
        frame.grid(row=0, column=i)
        label = tkinter.Label(master=frame, text=f"{name}")
        label.pack()
        frameM.columnconfigure(i, weight=1, minsize=200)
        frameM.rowconfigure(0, weight=1, minsize=20)
        window.grid["Names"][name] = label
    # draw grid elements
    for index, row in enumerate(range(10), start=1):
        for j in range(2):
            frame = tkinter.Frame(
                frameM,
                relief=tkinter.SUNKEN,
                borderwidth=1
            )
            window.grid["grid"][row][j] = tkinter.StringVar()
            window.grid["grid"][row][j].set(" ".join(["-"] * 20))
            frame.grid(row=index, column=j)
            label = tkinter.Label(master=frame, textvariable=window.grid["grid"][row][j])
            label.pack()
            frameM.columnconfigure(index, weight=1, minsize=200)
            frameM.rowconfigure(j, weight=1, minsize=20)
    frameM.grid(row=0, columnspan=2)
# Streaming related classes


class Stream():
    def __init__(self, videoFile: Path, time: datetime.datetime):
        self.videoFile = videoFile
        self.time = time
