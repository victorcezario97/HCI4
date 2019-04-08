######TODo######
#Fix the location thing
    #Figure out how to get the box coordinates from the radius
#Edit credentials -> Update when changed?
    #handle errors
#Clear treeview when changing the search parameters?
#Check global variables



from twython import Twython
import requests
import tkinter as tk
from tkinter import ttk
from tkinter import *
import threading, time
from tkinter.messagebox import askyesno
from tkinter.messagebox import showerror
from tkinter.messagebox import showwarning
import queue
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
import traceback
import datetime
from lang import languages
from twython import TwythonStreamer
from twython import exceptions

class EntryWithPlaceholder(tk.Entry):
    def __init__(self, master, placeholder="PLACEHOLDER", color='grey'):
        super().__init__(master)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_placeholder()


#Top level widget class that contains all other widgets
class IncomingSubmissions(tk.Frame):

    def setUndoNormal(self):
        self.procmenu.entryconfigure(1, state=tk.NORMAL)

    def setUndoDisabled(self):
        self.procmenu.entryconfigure(1, state=tk.DISABLED)

    def showLocationError(self):
        showerror("Location Error", "No location could be found from the address provided")

    def showLocationWarning(self):
        showwarning("Location Warning", "There was problem fetching the location data. More information can be found in the log file.")

    def checkProcQueue(self):
        global close
        if close:
            return

        try:
            message = procqueue.get(block=False)
            if message is not None:
                self.switch[message]()

        except queue.Empty: pass
        self.after(100, self.checkProcQueue)

    def insertTweet(self, tweet):
        if self.tree.exists(tweet['id']):
            return
        else:
            t = tweet['text'].replace("\n", ". ").replace(" ", "\ ").encode()
            print(tweet['text'])
            print(t)
            print(tweet['in_reply_to_status_id'])
            if tweet['in_reply_to_status_id']:
                parent = tweet['in_reply_to_status_id_str']
            else:
                parent = ''
            self.tree.insert(parent, 'end', tweet['id'], text=tweet['user']['screen_name'].encode(), values=(t))

    def checkTweetQueue(self):
        global close

        if close:
            return

        try:
            tweet = tweetQueue.get(block=False)
            if tweet:
                self.insertTweet(tweet)

        except queue.Empty: pass
        self.after(50, self.checkTweetQueue)

    def editCred(self):

        def apply():
            if askyesno("Confirm", "Are you sure you want to overwrite the credentials?"):
                s = []
                for i in range(4):
                    s.append(self.e[i].get())

                threading.Thread(target=self.proc.editCredProc, args=(s,)).start()
                win.destroy()

        #Pop up window to get the URL
        win = tk.Toplevel()
        win.wm_title("Window")

        l = tk.Label(win, text="Credentials")
        l.grid(row=0, column=0)

        self.e = []

        win.grid_columnconfigure(1, weight=1)

        self.l1 = tk.Label(win, text="API key: ")
        self.l1.grid(row=1, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, placeholder="(Unchanged)"))
        self.e[0].grid(row=1, column=1, sticky=E+W+N+S, padx="5px")

        self.l2 = tk.Label(win, text="API secret key: ")
        self.l2.grid(row=2, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[1].grid(row=2, column=1, sticky=E+W+N+S, padx="5px")

        self.l3 = tk.Label(win, text="Access token: ")
        self.l3.grid(row=3, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[2].grid(row=3, column=1, sticky=E+W+N+S, padx="5px")

        self.l4 = tk.Label(win, text="Access token secret: ")
        self.l4.grid(row=4, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[3].grid(row=4, column=1, sticky=E+W+N+S, padx="5px")

        okBtn = ttk.Button(win, text="OK", command=apply)
        okBtn.grid(row=5, column=0)

        cancelBtn = ttk.Button(win, text="Cancel", command=win.destroy)
        cancelBtn.grid(row=5, column=1)

    def undo(self):
        if askyesno("Confirm", "Are you sure you want to undo the last edit?"):
            threading.Thread(target=self.proc.undoProc).start()

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        #Comment tree and scrollbar
        self.tree = ttk.Treeview(parent)
        self.tree['columns'] = ('tweet')
        self.tree.heading('tweet', text="Tweet")

        self.tree.column('#0', width=150, stretch=NO)
        self.tree.column('#1', stretch=YES, minwidth=1300)
        self.tree.heading('#0', text="User")
        self.tree.grid(row=0, column=0, columnspan=4, sticky=E+W+N+S)

        self.treesbv = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.treesbv.grid(row=0, column=4, sticky=N+S+E)
        self.treesbh = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.treesbh.grid(row=1, column=0, columnspan=4, sticky=E+W)

        self.tree.configure(yscrollcommand=self.treesbv.set, xscrollcommand=self.treesbh.set)

        #Pause/Resume button
        self.btnText = StringVar()
        self.btnText.set("PAUSE")

        #Menu bar
        self.menubar = Menu(parent)

        #Create File menu, and add it to the menu bar
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Exit", command=callback)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        #Create Edit menu
        self.edits = []
        self.procmenu = Menu(self.menubar, tearoff=0)
        self.procmenu.add_command(label="Edit Credentials", command=self.editCred)
        self.procmenu.add_command(label="Undo last edit", command=self.undo)
        self.procmenu.entryconfigure(1, state=tk.DISABLED)
        self.menubar.add_cascade(label="Edit", menu=self.procmenu)

        # display the menu
        parent.config(menu=self.menubar)

        global procqueue
        global tweetQueue

        self.proc = Processor()

        self.switch = {
            "updateUndoNormal" : self.setUndoNormal,
            "updateUndoDisable" : self.setUndoDisabled,
            "locationError" : self.showLocationError,
            "locationWarning" : self.showLocationWarning
        }

        ####Search Parameters####
        self.paramFrame = SearchParamFrame(parent, self.proc)
        self.paramFrame.grid(row=0, column=7)

class SearchParamFrame(tk.Frame):
    def __init__(self, parent, proc):
        tk.Frame.__init__(self, parent)

        self.proc = proc

        self.searchLbl = tk.Label(self, text="Search Parameters")
        self.searchLbl.grid(row=0, column=0, columnspan=2, pady="7px")
        self.termsLbl = tk.Label(self, text="Search terms: ")
        self.termsLbl.grid(row=1, column=0)
        self.langLbl = tk.Label(self, text="Language: ")
        self.langLbl.grid(row=2, column=0)
        self.locationLbl = tk.Label(self, text="Location: ")
        self.locationLbl.grid(row=3, column=0)
        self.radiusLbl = tk.Label(self, text="Radius(km): ")
        self.radiusLbl.grid(row=4, column=0)

        self.termsEnt = tk.Entry(self)
        self.termsEnt.grid(row=1, column=1, padx="7px", pady="2px")
        self.langStr = StringVar()
        self.langStr.set("English")
        self.langOpt = tk.OptionMenu(self, self.langStr, *[x[0] for x in languages])
        self.langOpt.grid(row=2, column=1, padx="7px", pady="2px")
        self.locationEnt = tk.Entry(self)
        self.locationEnt.grid(row=3, column=1, padx="7px", pady="2px")
        self.radiusEnt = tk.Entry(self)
        self.radiusEnt.grid(row=4, column=1, padx="7px", pady="2px")

        self.searchBtn = tk.Button(self, text="Search", command=self.startSearch)
        self.searchBtn.grid(row=5, column=0, columnspan=2, pady="7px")


    def startSearch(self):
        if self.locationEnt.get():
            if not self.radiusEnt.get():
                showwarning("Radius", "Please specify the radius.")
            else:
                threading.Thread(target=self.proc.getLocation, args=(self.locationEnt.get(), self.termsEnt.get(), self.langStr.get(), self.radiusEnt.get(), )).start()
        else:
            threading.Thread(target=self.proc.search, args=(self.termsEnt.get(), self.langStr.get(), None, None,)).start()


class Processor():

    def __init__(self):
        global procqueue
        global twitter
        global close

    def editCredProc(self, s):
        global edits
        #Checks if the submission exists, and if so, starts the CommentGetter thread

        f = open("credentials.txt", "r")
        lines = f.readlines()

        backup = []
        for i in range(4):
            backup.append(lines[i])
            if s[i] == "(Unchanged)":
                continue
            else:
                lines[i] = s[i] + "\n"

        edits.append(backup)
        f.close()

        f = open("credentials.txt", "w")
        f.writelines(lines)
        f.close()

        procqueue.put("updateUndoNormal")


    def undoProc(self):
        global edits

        f = open("credentials.txt", "w")
        f.writelines(edits.pop())
        if not edits:
            procqueue.put("updateUndoDisable")
        f.close()


    def getLocation(self, address, q, lang, radius):
        geolocator = Nominatim(user_agent="TwitterAnalyzer")
        try:
            location = geolocator.geocode(address)

            if not location:
                procqueue.put("locationError")

            else:
                self.search(q, lang, location, radius)
        except GeopyError as err:
            f = open("log.txt", "a")
            f.write(str(datetime.datetime.now()) + ":\n")
            f.write(traceback.format_exc() + "\n")
            f.close()

            procqueue.put("locationWarning")


    def search(self, q, lang, location, radius):
        global streamer
        langCode = dict(languages)[lang]
        print(langCode)
        streamer.disconnect()
        time.sleep(5)
        if location:
            geocode = str(location.latitude) + "," + str(location.longitude) + "," + radius + "km"
            threading.Thread(target=startStream, args=(q, langCode, geocode,  )).start()
        else:
            threading.Thread(target=startStream, args=(q, langCode, None,  )).start()

class TweetStreamer(TwythonStreamer):

    def setParameters(self, lang, track, geocode):
        self.lang = lang
        self.track = track
        self.geocode = geocode

    def buildConversation(self, tweet, conversation):
        global twitter

        if tweet['in_reply_to_status_id']:
            try:
                next = twitter.show_status(id=tweet['in_reply_to_status_id'])
                self.buildConversation(next, conversation)
                conversation.append((tweet['user']['screen_name'],tweet['text']))
            except exceptions.TwythonError:
                return None
        else:
            conversation.append((tweet['user']['screen_name'],tweet['text']))


    def writeConversation(self, tweet):
        self.conversation = []
        filename = "conv_" + self.track + "_" + self.lang + "_" + str(self.geocode) + ".txt"
        f = open(filename, "a")

        self.buildConversation(tweet, self.conversation)
        for t in self.conversation:
            f.write(t[0] + "\n")
            f.write(t[1] + "\n")
            f.write("<----->\n")

        f.write("&--END--&\n")
        f.close()


    def checkIfConversation(self, data, turns, people):
        global twitter
        global tweetQueue

        if turns > 10:
            return False

        if people.count(data['user']['id_str']) == 0:
            people.append(data['user']['id_str'])

        if data['in_reply_to_status_id']:
            try:
                next = twitter.show_status(id=data['in_reply_to_status_id'])
            except exceptions.TwythonError:
                return False
            if self.checkIfConversation(next, turns+1, people):
                if turns == 0:
                    self.writeConversation(data)
                tweetQueue.put(data)
                return True
        else:
            print("Turns: " + str(turns) + " People: " + str(len(people)))

            if turns >= 3 and len(people) >= 2:
                tweetQueue.put(data)
                return True
            else:
                return False

    def on_success(self, data):

        if 'in_reply_to_status_id' in data:
            if data['in_reply_to_status_id']:
                people = []
                people.append(data['user']['id_str'])
                self.checkIfConversation(data, 0, people)

        f = open("data.txt", "w")

        if 'text' in data:
            f.write(str(data))

    def on_error(self, status_code, data):
        print(status_code)


def startStream(q, lang, geocode):

    if geocode:
        streamer.setParameters(lang, q, geocode)
        streamer.statuses.filter(language=lang, track=q, locations=geocode)
    else:
        streamer.setParameters(lang, q, None)
        streamer.statuses.filter(language=lang, track=q)


def getCredentials():
    f = open("credentials.txt", "r")
    cred = f.readlines()

    return cred;

def callback():
    close = True
    streamer.disconnect()
    root.destroy()

def getClose():
    return close

procqueue = queue.Queue()
tweetQueue = queue.Queue()
close = False

edits = []

cred = getCredentials()

APP_KEY = cred[0][:-1]
APP_SECRET = cred[1][:-1]
ACCESS_TOKEN = cred[2][:-1]
ACCESS_SECRET = cred[3][:-1]

streamer = TweetStreamer(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET)

twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
ACCESS_TOKEN = twitter.obtain_access_token()
twitter = Twython(APP_KEY, access_token=ACCESS_TOKEN)

t1 = threading.Thread(target=startStream, args=("twitter", "en", None, ))
t1.start()

root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", callback)
iss = IncomingSubmissions(root)
iss.checkProcQueue()
threading.Thread(target=iss.checkTweetQueue).start()
root.mainloop()
