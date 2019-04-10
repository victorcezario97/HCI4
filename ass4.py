######TODo######
#Fix the location thing
    #Figure out how to get the box coordinates from the radius
#Check global variables

from twython import Twython
import requests
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import *
import threading, time
from tkinter.messagebox import askyesno
from tkinter.messagebox import askokcancel
from tkinter.messagebox import showerror
from tkinter.messagebox import showwarning
from tkinter.messagebox import showinfo
import queue
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
import traceback
import datetime
from lang import languages
from twython import TwythonStreamer
from twython import exceptions
import nltk
nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer

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
        showinfo("Credentials Edited", "The credentials were edited successfuly. Please restart the application to apply the changes.")

    def setUndoDisabled(self):
        self.procmenu.entryconfigure(1, state=tk.DISABLED)
        showinfo("Credentials Edited", "The credentials were edited successfuly. Please restart the application to apply the changes.")

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
            try:
                self.tree.insert(parent, 'end', tweet['id'], text=tweet['user']['screen_name'].encode(), values=(t))
            except tk.TclError:
                pass

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

    def clearTree(self):
        self.tree.delete(*self.tree.get_children())

    def openConversation(self):
        self.filename = filedialog.askopenfilename(initialdir = "./", title="Select file", filetypes=(("text files", "*.txt"), ("all files", "*.*")))

        if self.filemenu:
            threading.Thread(target=self.proc.openConversationProc, args=(self.filename, )).start()

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.proc = Processor()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.titleLbl = tk.Label(self, text="TWEET STREAM")
        self.titleLbl.grid(row=0, column=0, columnspan=9)

        #Comment tree and scrollbar
        self.tree = ttk.Treeview(self)
        self.tree['columns'] = ('tweet')
        self.tree.heading('tweet', text="Tweet")

        self.tree.column('#0', width=150, stretch=NO)
        self.tree.column('#1', stretch=YES, minwidth=1300)
        self.tree.heading('#0', text="User")
        self.tree.grid(row=1, column=0, columnspan=4, sticky=E+W+N+S)

        self.treesbv = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.treesbv.grid(row=1, column=4, sticky=N+S+E)
        self.treesbh = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.treesbh.grid(row=2, column=0, columnspan=4, sticky=E+W)

        self.tree.configure(yscrollcommand=self.treesbv.set, xscrollcommand=self.treesbh.set)

        #Pause/Resume button
        self.btnText = StringVar()
        self.btnText.set("PAUSE")

        #Menu bar
        self.menubar = Menu(self)

        #Create File menu, and add it to the menu bar
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command=self.openConversation)
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

        self.switch = {
            "updateUndoNormal" : self.setUndoNormal,
            "updateUndoDisable" : self.setUndoDisabled,
            "locationError" : self.showLocationError,
            "locationWarning" : self.showLocationWarning,
            "locationSuccess" : self.clearTree
        }

        ####Search Parameters####
        self.paramFrame = SearchParamFrame(self, self.proc, self)
        self.paramFrame.grid(row=1, column=7)

class SearchParamFrame(tk.Frame):
    def __init__(self, parent, proc, iss):
        tk.Frame.__init__(self, parent)

        self.iss = iss
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
        if not askokcancel("Proceed?", "This will clear the tweets in the TreeView, but they can still be found in the respective file. Do you still want to continue?"):
            return

        if self.locationEnt.get():
            if not self.radiusEnt.get():
                showwarning("Radius", "Please specify the radius.")
            else:
                threading.Thread(target=self.proc.getLocation, args=(self.locationEnt.get(), self.termsEnt.get(), self.langStr.get(), self.radiusEnt.get(), )).start()
        else:
            self.iss.clearTree()
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
                self.procqueue.put("locationSuccess")
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

    def openConversationProc(self, filename):
        global tweetAnalyzeQueue
        f = open(filename, "r")
        i = 0
        j = 0
        tweetAnalyzeQueue.put("clearTree")

        self.conversations = f.read().split("&--END--&\n")
        for conv in self.conversations:
            tweets = conv.split("<----->\n")
            for t in tweets[:-1]:
                id = str(i) + str(j)
                if j == 0:
                    parent = ''
                else:
                    parent = str(i) + str(j-1)

                s = t.split('\n', 1)
                tweetAnalyzeQueue.put([parent, id, s[0], s[1]])
                j += 1
            i+=1
            j=0

        tweetAnalyzeQueue.put("setConversations")


    def getNPeople(self, conversation):
        p = []

        for tweet in conversation:
            if p.count(tweet[0]) == 0:
                p.append(tweet[0])

        return len(p)


    def filterConversationsProc(self, conversations, filterParam):
        global tweetAnalyzeQueue
        global procAnalyzeQueue
        i = 0
        j = 0

        for c in conversations:
            turns = len(c)
            if turns >= filterParam[0][0] and turns <= filterParam[0][1]:

                people = self.getNPeople(c)
                if people >= filterParam[1][0] and people <= filterParam[1][1]:

                    posFlag = False
                    negFlag = False
                    sid = SentimentIntensityAnalyzer()
                    for t in c:
                        ss = sid.polarity_scores(t[1])
                        print(t[1])
                        for k in ss:
                            print('{0}: {1}, '.format(k, ss[k]), end='')
                        if ss['pos'] >= filterParam[2][0]:
                            posFlag = True
                        if ss['neg'] >= filterParam[2][1]:
                            negFlag = True
                    #positivity
                    #negativity
                    if posFlag and negFlag:
                        for tweet in c:
                            if j == 0:
                                parent = ''
                            else:
                                parent = str(i) + str(j-1)

                            id = str(i) + str(j)
                            tweetAnalyzeQueue.put([parent, id, tweet[0], tweet[1]])
                            j += 1
            j = 0
            i += 1

        procAnalyzeQueue.put("enableButton")



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
        print("WRINTININITNTINTINTINTINT")
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
                if turns == 1:
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
                self.checkIfConversation(data, 1, people)

        f = open("data.txt", "w")

        if 'text' in data:
            f.write(str(data))

    def on_error(self, status_code, data):
        print(status_code)

######### FRAME 2 #########

class FilterParamFrame(tk.Frame):

    def minPeopleTraceCallback(self, *args):
        self.maxPeopleScl.config(from_=self.minPeopleVar.get())

    def maxPeopleTraceCallback(self, *args):
        self.minPeopleScl.config(to=self.maxPeopleVar.get())
        #print(self.minPeopleVar.get())

    def minTurnsTraceCallback(self, *args):
        self.maxTurnsScl.config(from_=self.minTurnsVar.get())

    def maxTurnsTraceCallback(self, *args):
        self.minTurnsScl.config(to=self.maxTurnsVar.get())

    def getTweetChildren(self, conversation, tweetId):
        child = self.parent.tree.get_children(tweetId)

        if not child:
            return conversation
        else:
            conversation.append(child[0])
            return self.getTweetChildren(conversation, child[0])

    def formatConversation(self, conversation):
        newC = []
        for c in conversation:
            newC.append((self.parent.tree.item(c, option="text").decode(), self.parent.tree.item(c, option="values")[0]))

        return newC

    def getFilterParam(self):
        filterParam = []

        filterParam.append((self.minTurnsScl.get(), self.maxTurnsScl.get()))
        filterParam.append((self.minPeopleScl.get(), self.maxPeopleScl.get()))
        filterParam.append((self.positiveScl.get(), self.negativeScl.get()))

        return filterParam

    def getTweets(self):
        tweets = self.parent.tree.get_children()
        conversations = []
        #print(self.parent.tree.get_children(tweets[0]))

        for t in tweets:
            conv = self.getTweetChildren([t],t)
            conversations.append(self.formatConversation(conv))

        print(conversations)
        return conversations

    def applyFilters(self):
        conversations = self.parent.getConversations()
        print("__________")
        print(conversations)

        self.applyBtn.config(state=tk.DISABLED)
        self.parent.clearTree()
        threading.Thread(target=Processor().filterConversationsProc, args=(conversations, self.getFilterParam())).start()


        #print(conversations)

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.parent = parent
        #self.iss = iss
        #self.proc = proc

        self.searchLbl = tk.Label(self, text="Filter Parameters")
        self.searchLbl.grid(row=0, column=0, columnspan=2, pady="7px")

        self.minPeopleLbl = tk.Label(self, text="Minimum participants")
        self.minPeopleLbl.grid(row=1, column=0, pady="7px")
        self.minPeopleVar = IntVar()
        self.minPeopleScl = tk.Scale(self, variable=self.minPeopleVar, from_=2, to=10, orient=HORIZONTAL)
        self.minPeopleScl.grid(row=1, column=1)

        self.maxPeopleLbl = tk.Label(self, text="Maximum participants")
        self.maxPeopleLbl.grid(row=2, column=0, pady="7px")
        self.maxPeopleVar = IntVar()
        self.maxPeopleScl = tk.Scale(self, variable=self.maxPeopleVar, from_=2, to=10, orient=HORIZONTAL)
        self.maxPeopleScl.grid(row=2, column=1)

        self.minPeopleVar.trace("w", self.minPeopleTraceCallback)
        self.maxPeopleVar.trace("w", self.maxPeopleTraceCallback)


        self.minTurnsLbl = tk.Label(self, text="Minimum turns")
        self.minTurnsLbl.grid(row=3, column=0, pady="7px")
        self.minTurnsVar = IntVar()
        self.minTurnsScl = tk.Scale(self, variable=self.minTurnsVar, from_=3, to=10, orient=HORIZONTAL)
        self.minTurnsScl.grid(row=3, column=1)

        self.maxTurnsLbl = tk.Label(self, text="Maximum turns")
        self.maxTurnsLbl.grid(row=4, column=0, pady="7px")
        self.maxTurnsVar = IntVar()
        self.maxTurnsScl = tk.Scale(self, variable=self.maxTurnsVar, from_=3, to=10, orient=HORIZONTAL)
        self.maxTurnsScl.grid(row=4, column=1)

        self.minTurnsVar.trace("w", self.minTurnsTraceCallback)
        self.maxTurnsVar.trace("w", self.maxTurnsTraceCallback)

        self.positiveLbl = tk.Label(self, text="Positive threshold")
        self.positiveLbl.grid(row=5, column=0, pady="7px")
        self.positiveScl = tk.Scale(self, from_=0, to=1, orient=HORIZONTAL, resolution=0.01)
        self.positiveScl.grid(row=5, column=1)

        self.negativeLbl = tk.Label(self, text="Negative threshold")
        self.negativeLbl.grid(row=6, column=0, pady="7px")
        self.negativeScl = tk.Scale(self, from_=0, to=1, orient=HORIZONTAL, resolution=0.01)
        self.negativeScl.grid(row=6, column=1)


        self.applyBtn = tk.Button(self, text="Apply", command=self.applyFilters)
        self.applyBtn.grid(row=7, column=0, columnspan=2, pady="7px")


    def startSearch(self):
        if not askokcancel("Proceed?", "This will clear the tweets in the TreeView, but they can still be found in the respective file. Do you still want to continue?"):
            return

        if self.locationEnt.get():
            if not self.radiusEnt.get():
                showwarning("Radius", "Please specify the radius.")
            else:
                threading.Thread(target=self.proc.getLocation, args=(self.locationEnt.get(), self.termsEnt.get(), self.langStr.get(), self.radiusEnt.get(), )).start()
        else:
            self.iss.clearTree()
            threading.Thread(target=self.proc.search, args=(self.termsEnt.get(), self.langStr.get(), None, None,)).start()

class ConversationDisplayer(tk.Frame):

    def checkProcQueue(self):
        global close
        if close:
            return

        try:
            message = procAnalyzeQueue.get(block=False)
            if message is not None:
                self.switch[message]()

        except queue.Empty: pass
        self.after(100, self.checkProcQueue)

    def insertTweetAnalyze(self, tweet):
        if self.tree.exists(tweet[1]):
            return
        else:
            t = tweet[3].replace("\n", ". ").replace(" ", "\ ").encode()
            #print(tweet['text'])
            #print(t)
            #print(tweet['in_reply_to_status_id'])
            #if tweet['in_reply_to_status_id']:
        #        parent = tweet['in_reply_to_status_id_str']
        #    else:
        #        parent = ''
            try:
                self.tree.insert(tweet[0], 'end', tweet[1], text=tweet[2].encode(), values=(t))
            except tk.TclError:
                pass

    def checkTweetAnalyzeQueue(self):
        global close

        if close:
            return

        try:
            tweet = tweetAnalyzeQueue.get(block=False)
            if tweet:
                if tweet == "clearTree":
                    self.clearTree()
                elif tweet == "setConversations":
                    self.setConversations()
                else:
                    self.insertTweetAnalyze(tweet)

        except queue.Empty: pass
        self.after(50, self.checkTweetAnalyzeQueue)


    def clearTree(self):
        self.tree.delete(*self.tree.get_children())

    def enableButton(self):
        self.paramFrame.applyBtn.config(state=tk.NORMAL)

    def setConversations(self):
        self.conversations = self.paramFrame.getTweets()
        print(self.conversations)

    def getConversations(self):
        return self.conversations

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.titleLbl = tk.Label(self, text="TWEET ANALYZER")
        self.titleLbl.grid(row=0, column=0, columnspan=9)

        #Comment tree and scrollbar
        self.tree = ttk.Treeview(self)
        self.tree['columns'] = ('tweet')
        self.tree.heading('tweet', text="Tweet")

        self.tree.column('#0', width=150, stretch=NO)
        self.tree.column('#1', stretch=YES, minwidth=1300)
        self.tree.heading('#0', text="User")
        self.tree.grid(row=1, column=0, columnspan=4, sticky=E+W+N+S)

        self.treesbv = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.treesbv.grid(row=1, column=4, sticky=N+S+E)
        self.treesbh = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.treesbh.grid(row=2, column=0, columnspan=4, sticky=E+W)

        self.tree.configure(yscrollcommand=self.treesbv.set, xscrollcommand=self.treesbh.set)

        global procAnalyzeQueue
        global tweetQueue

        self.proc = Processor()

        self.switch = {
            "locationSuccess" : self.clearTree,
            "enableButton" : self.enableButton,
            "setConversations" : self.setConversations
        }

        ####Search Parameters####
        self.paramFrame = FilterParamFrame(self)
        self.paramFrame.grid(row=1, column=7)

        self.conversations = []



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
procAnalyzeQueue = queue.Queue()
tweetAnalyzeQueue = queue.Queue()

close = False

edits = []

cred = getCredentials()

APP_KEY = cred[0][:-1]
APP_SECRET = cred[1][:-1]
ACCESS_TOKEN = cred[2][:-1]
ACCESS_SECRET = cred[3][:-1]

try:
    streamer = TweetStreamer(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET)

    twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    ACCESS_TOKEN = twitter.obtain_access_token()
    twitter = Twython(APP_KEY, access_token=ACCESS_TOKEN)

    t1 = threading.Thread(target=startStream, args=("twitter", "en", None, ))
    t1.start()
except exceptions.TwythonError:
    showerror("Authentication Error", "There was an error authenticating the application. Please check the credentials and try again.")

root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", callback)

mainFrame = tk.Frame(root)
iss = IncomingSubmissions(root)
iss.grid(row=0, column=0, sticky=N+S+E+W)
iss.checkProcQueue()
threading.Thread(target=iss.checkTweetQueue).start()

cd = ConversationDisplayer(root)
cd.grid(row=3, column=0)
cd.checkProcQueue()
threading.Thread(target=cd.checkTweetAnalyzeQueue).start()
root.mainloop()
