import tkinter
import lib
from functools import partial

# define classes


class Window(tkinter.Frame):
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        # TODO check whether other containers are running and clean up!
        # changing the title of our master widget
        self.master.title("FGO Stream Scheduler")
        # set up widgets
        lib.createTimeWidget(self)
        lib.createStatusWidget(self)
        lib.drawConfigGrid(self)
        # set up parameter variables
        self.credentials = None
        self.container = None
        self.streamActive = False
        self.imageName = "ffmpeg:1.0"
        self.schedule = None
        # allowing the widget to take the full space of the root window
        self.pack(fill="both", expand=1)
        # creating a menu instance
        menu = tkinter.Menu(self.master)
        self.master.config(menu=menu)
        # create the file object)
        file = tkinter.Menu(menu)
        # adds a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        file.add_command(label="Exit", command=self.client_exit)
        # add load config command
        file.add_command(label="Load config file", command=partial(lib.load_config, self))
        # added "file" to our menu
        menu.add_cascade(label="File", menu=file)
        # add test menu
        test = tkinter.Menu(menu)
        test.add_command(label="Test OK Stream", command=partial(lib.setStream, frame=self, color="green", rate="1000kbit/s"))
        test.add_command(label="Test BAD Stream", command=partial(lib.setStream, frame=self, color="red", rate="-/-"))
        test.add_command(label="Test Inactivate Stream", command=partial(lib.setStream, frame=self, color="yellow", rate="Inactive"))
        test.add_command(label="Start Test Containter", command=partial(lib.startTestContainer, self))
        test.add_command(label="Stop Test Containter", command=partial(lib.stopTestContainer, self))
        menu.add_cascade(label="Test", menu=test)
        # add Containers
        containers = tkinter.Menu(menu)
        containers.add_command(label="Stop all containers", command=partial(lib.stopAllContainers, imageName=self.imageName, frame=self))
        menu.add_cascade(label="Containers", menu=containers)
        # configure grid
        for i in range(2):
                self.columnconfigure(i, weight=1, minsize=25)
                self.rowconfigure(i, weight=1, minsize=25)
        # check docker
        lib.checkDocker(self.imageName)
        # initial call to put checking stream events in the queue
        lib.checkStreamEvents(self)

    def client_exit(self):
        exit()


# start of app


root = tkinter.Tk()
root.geometry("600x400")
app = Window(root)
root.mainloop()