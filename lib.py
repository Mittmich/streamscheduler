from pathlib import Path
import datetime
import docker
import re
from tkinter import filedialog
import pandas as pd
import tkinter
from tkinter.messagebox import showerror, showinfo, askyesno
import pathlib
import numpy as np
import shutil
import logging
import requests
import json
import time


# define global variables

RTMPSETTINGS_TEMPLATE = (
    "'{} "
    "flashver=FMLE/3.020(compatible;20FMSc/1.0)"
    " live=true pubUser={} pubPasswd={} playpath={}'"
)

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

FFMPEG_TEMPLATE = """ffmpeg -re\
                        -i {}\
                        -c:v libx264\
                        -b:v 1600k\
                        -preset ultrafast\
                        -b 900k\
                        -c:a libfdk_aac\
                        -b:a 128k\
                        -s 1280x720\
                        -x264opts keyint=50\
                        -g 25\
                        -pix_fmt yuv420p\
                        -f flv {}"""

# set loggingpath

datestring = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
logFile = Path(f"C:/temp/{datestring}.log")
logger = logging.getLogger("lib")

# misc


def currentTime():
    """Get current date and time"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def askExit(frame, root):
    if askyesno("Exit", "Do you really want to exit? All containers will be killed!"):
        stopAllContainers(frame, frame.imageName)
        root.destroy()


# parsing related functions


def check_config_timing(df):
    # check time difference
    diffs = pd.Series(np.diff(df["Date/Time"]))
    # LOGGING
    logger.debug(f"Time differences: {diffs}")
    target = datetime.timedelta(minutes=30)
    try:
        assert not any(diff < target for diff in diffs)
    except AssertionError:
        showerror("Error", "Stream timepoints are closer together than 30 min!")
        logger.error("Stream timepoints are closer together than 30 min!")


def check_config_format(df):
    """Checks whether config entries are valid"""
    if "Package" not in df.columns:
        showerror("Error", "Package ID needs to be provided!")
        logger.error("Video files are not all in the same directory!")
    try:
        dirs = []
        for row in df.iterrows():
            dirs.append(Path(row[1]["File"]).parent)
        assert all([x == dirs[0] for x in dirs])
    except AssertionError:
        showerror("Error", "Video files are not all in the same directory!")
        logger.error("Video files are not all in the same directory!")
        return False
    # check datatypes
    try:
        for row in df.iterrows():
            assert isinstance(row[1]["Date"], datetime.datetime)
            assert isinstance(row[1]["Time"], datetime.time)
            assert isinstance(row[1]["File"], str)
    except AssertionError:
        showerror("Error", "Schedule does not have the right format/datatypes!")
        logger.error("Schedule does not have the right format/datatypes!")
        return False
    # check whether path to mp4 exists
    try:
        for fileP in df["File"]:
            temp = pathlib.Path(fileP)
            assert temp.exists()
    except AssertionError:
        showerror("Error", "Video files do not exist!")
        logger.error("Video files do not exist!")
        return False
    return True


def parseContainerOutput(contID):
    """Parses container output"""
    while True:
        line = contID.logs(tail=1)
        # logger
        logger.debug(f"Container Output is: {line}")
        if len(line.strip().decode().split(" ")) < 10:
            yield None
        else:
            # standard out trick to parse ffmpeg output
            matched = re.findall(r"\d+\.\dkbits\/s", line.strip().decode())
            if len(matched) > 0:
                yield re.findall(r"\d+\.\dkbits\/s", line.strip().decode())[
                    -1
                ]  # yield newest bitrate
            else:
                yield None


def load_config(frame, filepath=None):
    if filepath is None:
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Select file",
            filetypes=(("xlsx files", "*.xlsx"), ("all files", "*.*")),
        )
    else:
        filename = filepath
    schedule = pd.read_excel(filename)
    # check format of config
    good = check_config_format(schedule)
    if good:
        # combine date and time for display
        schedule.loc[:, "Date/Time"] = schedule.apply(
            lambda x: pd.Timestamp.combine(x["Date"], x["Time"]), axis=1
        )
        schedule = schedule.drop(columns=["Date", "Time"])
        # sort by date/time
        schedule = schedule.sort_values(by="Date/Time")
        # check config
        check_config_timing(schedule)
        # prune out past events
        schedule = schedule.loc[schedule["Date/Time"] > frame.nowDT, :]
        if len(schedule) == 0:
            showerror("Error", "Only past events provided!")
            logger.error("Only past events provided!")
        else:
            # load credentials
            credentials = pd.read_excel(filename, sheet_name="Credentials")
            frame.credentials = credentials.T[0].to_dict()
            # add pathmap for docker mapping
            tempBase = pathlib.Path(schedule["File"].values[0]).parent
            frame.pathMap = {tempBase: {"bind": "/vids"}}
            frame.schedule = schedule
            draw_config(frame, schedule)
            checkRightTime(frame)
            # logger
            logger.info("Config loaded succesfully")


def parseFailure(container):
    """Check if container has failed.
    This is very crude!"""
    check = container.logs().decode()
    if (
        ("error" in check.lower())
        or ("failure" in check.lower())
        or ("not found" in check.lower())
    ):
        # logger
        logger.error(f"Stream Failed! With the following line {check}")
        return True
    return False


def draw_config(window, loadedFrame):
    # draw elements
    index = None
    for index, row in enumerate(loadedFrame.head(n=10).iterrows()):
        # only show filename
        filePath = pathlib.Path(row[1]["File"])
        window.grid["grid"][index][0].set(filePath.name)
        window.grid["grid"][index][1].set(row[1]["Date/Time"])
    if index is None:
        for i in range(0, 10):
            window.grid["grid"][i][0].set(" ".join(["-"] * 20))
            window.grid["grid"][i][1].set(" ".join(["-"] * 20))
    elif index < 9:  # Redraw blanks if less entries
        for i in range(index + 1, 10):
            window.grid["grid"][i][0].set(" ".join(["-"] * 20))
            window.grid["grid"][i][1].set(" ".join(["-"] * 20))


def checkDocker(imageName):
    """Checks if docker is installed and
    whether the right container is available"""
    result = shutil.which("docker")
    if result is None:
        showerror("error", "Docker is not installed!")
        logger.error("Docker is not installed!")
        return
    # checker whether docker client is reachable
    client = docker.from_env()
    try:
        client.version()
    except BaseException:
        showerror("error", "Docker is not running!")
        logger.error("Docker is not running!")
        return
    # check whether image is installed
    try:
        client.images.get(imageName)
    except docker.errors.ImageNotFound:
        showerror("Error", f"{imageName} not found in docker.images!")
        logger.error(f"{imageName} not found in docker.images!")
    # check whether curlimages/curl:latest is installed
    try:
        client.images.get("curlimages/curl:latest")
    except docker.errors.ImageNotFound:
        showerror("Error", "curlimages/curl:latestnot found in docker.images!")
        logger.error("curlimages/curl:latest not found in docker.images!")
    if countImages(imageName) != 0:
        showerror(
            "Error",
            "Other containers with the same image are running!\n Please stop the containers.",
        )
        logger.error(
            "Other containers with the same image are running!\n Please stop the containers."
        )


def countImages(imageName):
    client = docker.from_env()
    containerList = client.containers.list()
    count = 0
    for cont in containerList:
        if imageName in str(cont.image):
            count += 1
    return count


# Streaming related functions


def dispatch_test_stream(credentials, engine=None):
    """Starts streaming via ffmpeg.
    Returns subprocess.Popen instance."""
    # fill in credentials
    filledRTMP = RTMPSETTINGS_TEMPLATE.format(
        credentials["rtmp-URL"],
        credentials["User"],
        credentials["Password"],
        credentials["playpath"],
    )
    # fill in ffmpeg
    ffmpegCommand = FFMPEG_TEMPLATE_TEST.format(filledRTMP)
    # connect to docker client
    if engine is None:
        client = docker.from_env()
    else:
        client = engine
    # start container
    try:
        contID = client.containers.run("ffmpeg:1.0", ffmpegCommand, detach=True)
    except docker.errors.APIError:
        showerror("Erro", "Docker is not ready/installed!")
        logger.error("Docker is not ready/installed!")
        return None
    else:
        return contID


def dispatch_stream(videofile, credentials, pathmap, engine=None):
    """Starts streaming via ffmpeg.
    Returns docker container object."""
    # fill in credentials
    filledRTMP = RTMPSETTINGS_TEMPLATE.format(
        credentials["rtmp-URL"],
        credentials["User"],
        credentials["Password"],
        credentials["playpath"],
    )
    # fill in ffmpeg
    ffmpegCommand = FFMPEG_TEMPLATE.format(videofile, filledRTMP)
    # connect to docker client
    if engine is None:
        client = docker.from_env()
    else:
        client = engine
    try:
        contID = client.containers.run(
            "ffmpeg:1.0", ffmpegCommand, detach=True, volumes=pathmap
        )
    except docker.errors.APIError:
        showerror("Erro", "Docker is not ready/installed!")
        logger.error("Docker is not ready/installed")
        return None
    else:
        logger.debug(f"Stream dispatched with contID {contID}")
        return contID


def startTestContainer(frame, engine=None):
    if frame.credentials is None:
        showerror("Error", "No credentials specified!")
        logger.error("No credentials specified!")
        return
    if frame.container is not None:
        showerror("Error", "A stream is already running!")
        logger.error("A stream is already running!")
    else:
        frame.container = dispatch_test_stream(frame.credentials, engine=engine)
        if frame.container is not None:
            setStream(frame, "grey", "Waiting")
            frame.streamActive = True


def stopTestContainer(frame):
    if frame.container is not None:
        frame.container.stop()
        frame.container = None
        frame.streamActive = False
    else:
        showerror("Error", "No container is running!")
        logger.error("No container is running!")
        return
    if countImages(frame.imageName) == 0:
        setStream(frame, "yellow", "Inactive")


def stopAllContainers(frame, imageName):
    """stops all running docker containers
    with the specified image name."""
    frame.streamActive = False
    client = docker.from_env()
    containers = client.containers.list()
    if len(containers) == 0:
        logger.info("No containers are running!")
    else:
        for cont in containers:
            if imageName in str(cont.image):
                cont.stop()
        showinfo("Stopped", "All containers stopped!")
        logger.info("All containers stopped!")
        frame.purged = False  # channel may be dirty, set purged to False


# gui-related functions


# Set up time widget


def createTimeWidget(frame):
    frameW = tkinter.Frame(frame)
    frame.now = tkinter.StringVar()
    # Title
    frame.time_title = tkinter.Label(
        frameW, text="Current Time | Time to stream:", font=("Helvetica", 12)
    )
    frame.time_title.pack()
    # system time
    frame.time_label = tkinter.Label(frameW, font=("Helvetica", 12))
    frame.time_label.pack()
    frame.time_label["textvariable"] = frame.now
    # initial time display
    onUpdate(frame)
    frameW.grid(column=1, row=1, sticky="S")
    logger.debug("Time widget created")


def onUpdate(frame):
    # update displayed time
    if isinstance(frame.timeToStream, datetime.timedelta):
        deltaString = str(frame.timeToStream).split(".")[0]
    else:
        deltaString = frame.timeToStream
    setString = currentTime() + f" | {deltaString}"
    frame.now.set(setString)
    # update internal time
    frame.nowDT = datetime.datetime.now()
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
    frame.status_title = tkinter.Label(
        frameS, text="Stream Status:", font=("Helvetica", 12)
    )
    frame.status_title.pack()
    # status rectangle
    frame.rectl_status = tkinter.Frame(frameS, width=20, height=20)
    frame.rectl_status.pack()
    # streamingspeed
    frame.lbl_StreamSpeed = tkinter.Label(frame.rectl_status, font=("Helvetica", 12))
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
                    setStream(frame, "yellow", "Inactive")
                    frame.streamActive = False  # reset stream active flag
                    frame.container = None  # reset container
                    frame.purged = False
                    # logger
                    logger.error("Stream Failed!")
                    showerror("Error", "Stream failed!")
                else:  # was ok and stopped normally
                    setStream(frame, "yellow", "Inactive")
                    frame.streamActive = False  # reset stream active flag
                    logger.info("Stream ended successfully!")
                    frame.container = None
                    frame.purged = False
                    startUpload(frame)  # trigger upload sequence
            else:  # just started
                setStream(frame, "green", "Active")
                logger.debug(frame.container.logs())
                # get bitrate
                output = next(parseContainerOutput(frame.container))
                # set stream Ok
                if output is not None:
                    setStream(frame, "green", output)
        if status == "running":
            setStream(frame, "green", "Active")
            # get bitrate
            output = next(parseContainerOutput(frame.container))
            # set stream Ok
            if output is not None:
                setStream(frame, "green", output)


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
        frame = tkinter.Frame(frameM, relief=tkinter.RAISED, borderwidth=1)
        frame.grid(row=0, column=i)
        label = tkinter.Label(master=frame, text=f"{name}")
        label.pack()
        frameM.columnconfigure(i, weight=1, minsize=200)
        frameM.rowconfigure(0, weight=1, minsize=20)
        window.grid["Names"][name] = label
    # draw grid elements
    for index, row in enumerate(range(10), start=1):
        for j in range(2):
            frame = tkinter.Frame(frameM, relief=tkinter.SUNKEN, borderwidth=1)
            window.grid["grid"][row][j] = tkinter.StringVar()
            window.grid["grid"][row][j].set(" ".join(["-"] * 20))
            frame.grid(row=index, column=j)
            label = tkinter.Label(
                master=frame, textvariable=window.grid["grid"][row][j]
            )
            label.pack()
            frameM.columnconfigure(index, weight=1, minsize=200)
            frameM.rowconfigure(j, weight=1, minsize=20)
    frameM.grid(row=0, columnspan=2)


def checkRightTime(frame):
    """checks whether it is time to stream."""
    if frame.schedule is None:  # no schedule loaded
        return
    if len(frame.schedule) == 0:  # no more streams to stream
        return
    if not frame.streamActive:
        # check the next stream to start and add it to next upload
        nextRow = next(frame.schedule.iterrows())[1]
        if frame.nextupload is None:
            frame.nextupload = nextRow
        time = nextRow["Date/Time"]
        videoFile = nextRow["File"]
        # convert to target path in container
        targetPath = f"/vids/{Path(videoFile).name}"
        # check whether it is time to start
        now = frame.nowDT
        differenceStream = datetime.timedelta(seconds=20)
        differencePurge = datetime.timedelta(minutes=10)
        frame.timeToStream = np.abs(now - time)
        logger.debug(f"Time to stream is: {frame.timeToStream}")
        logger.debug(
            f"Next stream is: {frame.schedule['File'].values[0]} - {frame.schedule['Date/Time'].values[0]}"
        )
        if ((now - time) < differencePurge) and (not frame.purged):
            frame.purged = True  # make sure the stream starts even if purging failed
            frame.after(0, purgeChannel, frame)
        if np.abs(now - time) < differenceStream:
            frame.container = dispatch_stream(
                targetPath, frame.credentials, frame.pathMap
            )
            if frame.container is not None:
                logger.info(f"Stream started! {Path(videoFile).name} at {time}")
                # set stream activate to true
                frame.streamActive = True
            else:
                frame.after(
                    10,
                    showerror,
                    "Error",
                    "Error starting stream. Docker is not ready/installed.",
                )
                logger.error("Error starting stream. Docker is not ready/installed.")
            # pluck the row from the schedule. Even if there was an error, otherwise streams in the future will not run
            frame.schedule = frame.schedule.iloc[1:, :]
            # redraw config
            draw_config(frame, frame.schedule)


def checkPastStream(frame):
    """Gets rid of streams that are in the past.
    This can happen if two streams are scheduled
    right after each after and the first one takes longer
    than the difference."""
    if frame.streamActive:
        oldLength = len(frame.schedule)
        frame.schedule = frame.schedule.loc[
            frame.schedule["Date/Time"] > frame.nowDT, :
        ]
        if oldLength != len(frame.schedule):
            draw_config(frame, frame.schedule)


def checkStreamEvents(frame):
    """Main event that checks all
    stream related things"""
    # check whether stream needs to be started
    checkRightTime(frame)
    # check stream status
    checkStream(frame)
    # check past stream
    checkPastStream(frame)
    # schedule next stream
    frame.after(1000, checkStreamEvents, frame)


def purgeChannel(frame):
    if "API_KEY" not in frame.credentials:
        logger.error("No api key for purging provided!")
        return
    if "CHANNEL_ID" not in frame.credentials:
        logger.error("No channel for purging provided!")
        return
    apiKey = frame.credentials["API_KEY"]
    channelID = frame.credentials["CHANNEL_ID"]
    request = "http://api.dacast.com/v2/channel/{}/webdvr/purge?apikey={}".format(
        channelID, apiKey
    )
    r = requests.put(request)
    if not (200 <= r.status_code < 300) :
        logger.error("Purging did not work!")
        logger.error(f"Command was: {request}")
        logger.error(f"{r.text}")
    else:
        logger.info("Purging of channel successful!")


def startUpload(frame):
    """Takes a pandas.Series object stored at
    frame.nextupload and uploads the file field to dacast
    VOD."""
    # unpack arguments
    if frame.nextupload is None:
        return
    fileName = frame.nextupload["File"]
    apiKey = frame.credentials["API_KEY"]
    # convert path to target path in container
    targetPath = f"/vids/{Path(fileName).name}"
    # get the AWS key
    data = {"source": targetPath,
            "callback_url": "https://fitnessgoesoffice.com/",
            "upload_type": "curl",
            "auto_encoding": False}
    awsKeyResponse = requests.post(f"http://api.dacast.com/v2/vod?apikey={apiKey}", data=data)
    # check if respone was successful
    if not (200 <= awsKeyResponse.status_code < 300):
        logger.error("Getting aws key did not work!")
        logger.error(f"Command was: {awsKeyResponse}")
        logger.error(f"{awsKeyResponse.text}")
        frame.nextupload = None
        return
    logger.info("Successfully got aws key!")
    awsKeyParsed = json.loads(awsKeyResponse.text)
    # construct curl command
    curlCommand = awsKeyParsed["curl-command"].split("curl")[1]
    # dispatch curl command
    client = docker.from_env()
    logger.info("Starting upload!")
    contID = client.containers.run("curlimages/curl:latest", curlCommand, detach=True, volumes=frame.pathMap)
    frame.uploadContainer = contID
    checkUpload(frame)  # start checking of upload


def checkUpload(frame, retries=0):
    """Checks whether a started upload was finished"""
    # unpack arguments
    fileName = frame.nextupload["File"]
    apiKey = frame.credentials["API_KEY"]
    # check if container has finished
    client = docker.from_env()
    runningContainers = client.containers.list()
    if not (frame.uploadContainer in runningContainers):  # container is not in running container list anymore
        # initialize idVids that will fail the check
        idVid = []
        # check whether file exists on VOD DACAST
        if retries < 5:
            logger.info(f"Retry: {retries}")
            videos = requests.get(f"http://api.dacast.com/v2/vod?apikey={apiKey}&_format=JSON")
            # check whether apicall worked
            if not (200 <= videos.status_code < 300):
                logger.error("Enumerating vod videos did not work!")
                logger.error(f"Command was: {videos}")
                logger.error(f"{videos.text}")
                frame.nextupload = None
                frame.uploadContainer = None
                return
            logger.info("   Enumerating vod videos worked!")
            # parse videos
            vidsJson = json.loads(videos.text)
            # get ID by name
            data = vidsJson["data"]
            idVid = [i["id"] for i in data if i["title"] == Path(fileName).name.split(".mp4")[0]]
            logger.info(f"idVid: {idVid}")
            if len(idVid) == 0:
                # go into another retry
                frame.after(10000, checkUpload, frame, retries + 1)
                return
        # check if after 5 retries you have the id
        if len(idVid) == 0:
            # upload failed
            logger.error("Upload failed!")
            logger.error(frame.uploadContainer.logs())
            frame.uploadContainer = None
            frame.nextupload = None
            return
        # upload succeeded, add to package
        logging.info("Upload succeeded!")
        addToPackage(frame, idVid)
        return
    else:
        frame.after(10, checkUpload, frame)  # continue checking for upload


def addToPackage(frame, idVid):
    # unpack arguments
    apiKey = frame.credentials["API_KEY"]
    packageID = frame.nextupload["Package"]
    # get current content of package
    result = requests.get(f"http://api.dacast.com/v2/package/{packageID}?apikey={apiKey}&_format=JSON")
    # check whether apicall worked
    if not (200 <= result.status_code < 300):
        logger.error("Getting package contents did not work!")
        logger.error(f"Command was: {result}")
        logger.error(f"{result.text}")
        frame.nextupload = None
        frame.uploadContainer = None
        return
    logger.info("Getting package contents was successful")
    # fix content_id vs id issue
    content = json.loads(result.text)["content"]["data"]
    oldContent = []
    for contentDict in content:
        newContentDict = {}
        newContentDict["id"] = contentDict.pop("content_id")
        newContentDict.update(contentDict)
        oldContent.append(newContentDict)
    # add new content
    newContent = [{"type": "vod", "position": len(oldContent), "id": str(idVid[0])}]
    postContent = oldContent + newContent
    # make request
    data = {"content": json.dumps(postContent)}
    postRequest = requests.put(f"http://api.dacast.com/v2/package/{packageID}/content?apikey={apiKey}", data=data)
    # check if respone was successful
    if not (200 <= postRequest.status_code < 300):
        logger.error("Updating package contents did not work!")
        logger.error(f"Command was: {postRequest}")
        logger.error(f"{postRequest.text}")
        frame.nextupload = None
        frame.uploadContainer = None
        return
    logger.info("Updating package contents was succesful!")
    frame.nextupload = None
