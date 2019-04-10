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

#Subclass of the Entry widget with placeholder text when empty
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

##### FRAME 1 #####

#Frame with the stream of tweets according to the specified parameters
class IncomingTweets(tk.Frame):

    #Function that sets the state of the 'undo' option in the menu to normal
    def setUndoNormal(self):
        self.procmenu.entryconfigure(1, state=tk.NORMAL)
        showinfo("Credentials Edited", "The credentials were edited successfuly. Please restart the application to apply the changes.")

    #Function that sets the state of the 'undo' option in the menu to disabled
    def setUndoDisabled(self):
        self.procmenu.entryconfigure(1, state=tk.DISABLED)
        showinfo("Credentials Edited", "The credentials were edited successfuly. Please restart the application to apply the changes.")

    #Function that displays an error when a location specified cannot be found by geopy
    def showLocationError(self):
        showerror("Location Error", "No location could be found from the address provided")

    #Function that displays a warning when an internal geopy warning occurs
    def showLocationWarning(self):
        showwarning("Location Warning", "There was problem fetching the location data. More information can be found in the log file.")

    #Function that displays a warning when the rate limit is reached in the Twython API
    def rateLimitWarning(self):
        showwarning("Rate Limit", "The rate limit for retrieving tweets has been exceeded. Please try again later.")

    #Function that periodically checks a queue for a new action
    def checkProcQueue(self):
        global close
        if close:
            return

        try:
            message = procqueue.get(block=False)
            if message is not None:
                if "Error code:" in message:
                    showerror("Tweet Streamer Error", "An error has occurred with the Tweet Streamer. " + message)
                else:
                    self.switch[message]()

        except queue.Empty: pass
        self.after(100, self.checkProcQueue)

    #Function that inserts a new tweet into the treeview widget
    def insertTweet(self, tweet):
        if self.tree.exists(tweet['id']):
            return
        else:
            t = tweet['text'].replace("\n", ". ").replace(" ", "\ ").encode()

            if tweet['in_reply_to_status_id']:
                parent = tweet['in_reply_to_status_id_str']
            else:
                parent = ''
            try:
                self.tree.insert(parent, 'end', tweet['id'], text=tweet['user']['screen_name'].encode(), values=(t))
            except tk.TclError:
                pass

    #Function that periodically checks a queue for new tweets to be added to the treeview
    def checkTweetQueue(self):
        global close

        if close:
            return

        try:
            tweet = tweetQueue.get(block=False)
            if tweet:
                if tweet == 'clearTree':
                    self.clearTree()
                else:
                    self.insertTweet(tweet)

        except queue.Empty: pass
        self.after(50, self.checkTweetQueue)

    #Function called when the option to 'edit credentials' is selected
    def editCred(self):

        #Function to confirm the action
        def apply():
            if askyesno("Confirm", "Are you sure you want to overwrite the credentials?"):
                s = []
                for i in range(4):
                    s.append(self.e[i].get())

                threading.Thread(target=self.proc.editCredProc, args=(s,)).start()
                win.destroy()

        #Pop up window to get the new credentials
        win = tk.Toplevel()
        win.wm_title("Window")

        l = tk.Label(win, text="Credentials")
        l.grid(row=0, column=0)

        self.e = []

        win.grid_columnconfigure(1, weight=1)

        #API Key
        self.l1 = tk.Label(win, text="API key: ")
        self.l1.grid(row=1, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, placeholder="(Unchanged)"))
        self.e[0].grid(row=1, column=1, sticky=E+W+N+S, padx="5px")

        #API Key Secret
        self.l2 = tk.Label(win, text="API secret key: ")
        self.l2.grid(row=2, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[1].grid(row=2, column=1, sticky=E+W+N+S, padx="5px")

        #Access token
        self.l3 = tk.Label(win, text="Access token: ")
        self.l3.grid(row=3, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[2].grid(row=3, column=1, sticky=E+W+N+S, padx="5px")

        #Access token secret
        self.l4 = tk.Label(win, text="Access token secret: ")
        self.l4.grid(row=4, column=0, sticky=W)
        self.e.append(EntryWithPlaceholder(win, "(Unchanged)"))
        self.e[3].grid(row=4, column=1, sticky=E+W+N+S, padx="5px")

        okBtn = ttk.Button(win, text="OK", command=apply)
        okBtn.grid(row=5, column=0)

        cancelBtn = ttk.Button(win, text="Cancel", command=win.destroy)
        cancelBtn.grid(row=5, column=1)

    #Function called when the 'undo last edit' option is selected
    def undo(self):
        if askyesno("Confirm", "Are you sure you want to undo the last edit?"):
            threading.Thread(target=self.proc.undoProc).start()

    #Function that clears the treeview widget
    def clearTree(self):
        self.tree.delete(*self.tree.get_children())

    #Function that opens the dialog for a file to be selected
    def openConversation(self):
        self.filename = filedialog.askopenfilename(initialdir = "./", title="Select file", filetypes=(("text files", "*.txt"), ("all files", "*.*")))

        if self.filemenu:
            threading.Thread(target=self.proc.openConversationProc, args=(self.filename, )).start()

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        #Processor instance
        self.proc = Processor()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.titleLbl = tk.Label(self, text="TWEET STREAM")
        self.titleLbl.grid(row=0, column=0, columnspan=9)

        #Treeview with the tweets and scrollbars
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

        #Menu bar
        self.menubar = Menu(self)

        #Create File menu, and add it to the menu bar
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command=self.openConversation)
        self.filemenu.add_command(label="Exit", command=callback)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        #Create Edit menu
        self.procmenu = Menu(self.menubar, tearoff=0)
        self.procmenu.add_command(label="Edit Credentials", command=self.editCred)
        self.procmenu.add_command(label="Undo last edit", command=self.undo)
        self.procmenu.entryconfigure(1, state=tk.DISABLED)
        self.menubar.add_cascade(label="Edit", menu=self.procmenu)

        # display the menu
        parent.config(menu=self.menubar)

        #Queues to be monitored
        global procqueue
        global tweetQueue

        #Dictionary with the actions to be taken for each option found in the 'procqueue'
        self.switch = {
            "updateUndoNormal" : self.setUndoNormal,
            "updateUndoDisable" : self.setUndoDisabled,
            "locationError" : self.showLocationError,
            "locationWarning" : self.showLocationWarning,
            "locationSuccess" : self.clearTree,
            "rateLimit" : self.rateLimitWarning
        }

        #Search parameters
        self.paramFrame = SearchParamFrame(self, self.proc, self)
        self.paramFrame.grid(row=1, column=7)

#Frame with the tweet search parameters
class SearchParamFrame(tk.Frame):
    def __init__(self, parent, proc, iss):
        tk.Frame.__init__(self, parent)

        self.iss = iss
        self.proc = proc

        #Labels
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

        #Entries
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


    #Function that starts a new search based on the search parameters specified
    def startSearch(self):
        if not self.termsEnt.get():
            showwarning("Missing Terms", "Please input the search terms.")
            return

        if not askokcancel("Proceed?", "This will clear the tweets in the TreeView, but they can still be found in the respective file. Do you still want to continue?"):
            return

        if self.locationEnt.get():
            if not self.radiusEnt.get():
                showwarning("Radius", "Please specify the radius.")
            else:
                #Getting the location from geopy
                threading.Thread(target=self.proc.getLocation, args=(self.locationEnt.get(), self.termsEnt.get(), self.langStr.get(), self.radiusEnt.get(), )).start()
        else:
            #Search with only terms and language since no location was specified
            self.iss.clearTree()
            threading.Thread(target=self.proc.search, args=(self.termsEnt.get(), self.langStr.get(), None, None,)).start()

#Class responsible for the general processing
class Processor():

    def __init__(self):
        #Queue for comunication with the GUI
        global procqueue
        #Twitter instance for searching
        global twitter
        #Flag for stopping
        global close
        #Previous credentials for the undo option
        self.edits = []

    #Function for editing the credentials file
    def editCredProc(self, s):

        f = open("credentials.txt", "r")
        lines = f.readlines()

        #Backing up the previous credentials
        backup = []
        for i in range(4):
            backup.append(lines[i])
            if s[i] == "(Unchanged)":
                continue
            else:
                lines[i] = s[i] + "\n"

        self.edits.append(backup)
        f.close()

        #Rewriting the file
        f = open("credentials.txt", "w")
        f.writelines(lines)
        f.close()

        #Sending the GUI the signal to enable the undo button
        procqueue.put("updateUndoNormal")

    #Function that undos the last edit of the credentials file
    def undoProc(self):

        f = open("credentials.txt", "w")
        f.writelines(self.edits.pop())
        if not self.edits:
            #If there are no more edits backed up, sends the signal to disable the undo button
            procqueue.put("updateUndoDisable")
        f.close()

    #Function that gets the location from the addres provided with geopy
    def getLocation(self, address, q, lang, radius):
        geolocator = Nominatim(user_agent="TwitterAnalyzer")
        try:
            location = geolocator.geocode(address)

            #If no location is found, sends the signal to display an error
            if not location:
                procqueue.put("locationError")

            else:
                #If the location is found, calls the search function with all the parameters
                procqueue.put("locationSuccess")
                self.search(q, lang, location, radius)
        except GeopyError as err:
            #If a geopy error occurs, write the traceback in a log file and send the signal to warn the user
            f = open("log.txt", "a")
            f.write(str(datetime.datetime.now()) + ":\n")
            f.write(traceback.format_exc() + "\n")
            f.close()

            procqueue.put("locationWarning")


    def startLocationSearch(self, q, lang, geocode):
        #twitter instance for searching
        global twitter
        #Flag for closing the application
        global stopSearch
        #Streamer instance
        global streamer
        #Processor queue instance
        global procqueue
        #Flag that states if the twitter instance is in use
        global search

        streamer.setParameters(lang, q, geocode)
        try:
            tweets = twitter.cursor(twitter.search, q=q, lang=lang, geocode=geocode)

            #Checking if the tweets found are part of conversations
            for t in tweets:
                check = streamer.checkIfConversation(t, 1, [], True)
                if check == None:
                    return

        #Sends the signal to display a warning in case of rate limit error
        except exceptions.TwythonRateLimitError:
            procqueue.put("rateLimit")
            search = False
            return

        #Keep searching until another search is made or the application is closed
        if not stopSearch:
            time.sleep(1)
            self.startLocationSearch(q, lang, geocode)

    #Function that starts a search for tweets, either with a streamer or a twitter instance
    def search(self, q, lang, location, radius):
        #Flag to tell if a twitter instance was being used
        global search
        #Streamer instance
        global streamer
        #Queue to communicate with the streamer instace
        global qu
        #Queue to receive signals from the streamer instance
        global done
        #Language code (ISO 639-1)
        langCode = dict(languages)[lang]

        try:
            streamer.disconnect()
        except exceptions.TwythonError:
            pass
        time.sleep(5)

        if location:
            #If the twitter instance was executing a search, send a signal for it to stop and wait for the response
            if search:
                qu.put('stop')
                a = done.get(block=True)
            else:
                #Set the flag that the twitter instance is executing a search
                search = True
            geocode = str(location.latitude) + "," + str(location.longitude) + "," + radius + "km"
            threading.Thread(target=self.startLocationSearch, args=(q, langCode, geocode,  )).start()
        else:
            #If the twitter instance was executing a search, send a signal for it to stop and wait for the response
            if search:
                qu.put('stop')
                a = done.get(block=True)
                search = False
            #Start the stream
            threading.Thread(target=startStream, args=(q, langCode, None,  )).start()

    #Function that gets conversations from a file
    def openConversationProc(self, filename):
        global tweetAnalyzeQueue
        f = open(filename, "r")
        #Variables used as indexes for the treeview
        i = 0
        j = 0
        #Clears the treeview and disables the button until it's finished
        tweetAnalyzeQueue.put("clearTree")
        tweetAnalyzeQueue.put("disableButton")

        #Splits the string by the delimiters
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
                #Sends the tweet to be inserted into the treeview
                tweetAnalyzeQueue.put([parent, id, s[0], s[1]])
                j += 1
            i+=1
            j=0

        #Send signals to store the conversations locally and to re-enable the button
        tweetAnalyzeQueue.put("setConversations")
        tweetAnalyzeQueue.put("enableButton")

    #Function that returns the amount of different participants in a conversation
    def getNPeople(self, conversation):
        p = []

        for tweet in conversation:
            if p.count(tweet[0]) == 0:
                p.append(tweet[0])

        return len(p)

    #Function the returns the 'flow' of a conversation (positive, negative or neutral)
    def getConversationFlow(self, c):
        posFlag = True
        negFlag = True
        sid = SentimentIntensityAnalyzer()

        lastPos = sid.polarity_scores(c[0][1])['pos']
        lastNeg = sid.polarity_scores(c[0][1])['neg']

        for t in c:
            ss = sid.polarity_scores(t[1])
            #If the positivity is not increasing and the negativity is not decreasing it's not positive
            if ss['pos'] < lastPos and ss['neg'] > lastNeg:
                posFlag = False
            #If the negativity is not increasing and the positivity is not decreasing it's not negative
            if ss['pos'] > lastPos and ss['neg'] < lastNeg:
                negFlag = False
            lastPos = ss['pos']
            lastNeg = ss['neg']

        #If it's not positive or negative, returns 'neutral'
        if lastPos:
            return 'pos'
        elif lastNeg:
            return 'neg'
        else:
            return 'neu'

    #Function that filters the conversations according to the parameters specified
    def filterConversationsProc(self, conversations, filterParam):
        #Queue to send signals to the GUI
        global tweetAnalyzeQueue

        #Sends signal to disable button while the conversation is processed
        tweetAnalyzeQueue.put('disableButton')
        #Variables used as indexes for the treeview
        i = 0
        j = 0

        for c in conversations:
            turns = len(c)
            #Checking number of turns
            if turns >= filterParam[0][0] and turns <= filterParam[0][1]:

                people = self.getNPeople(c)
                #Checking the number of unique participants
                if people >= filterParam[1][0] and people <= filterParam[1][1]:

                    flow = self.getConversationFlow(c)

                    #Checking if the flow of the conversation matches what was specified
                    if flow == filterParam[2]:
                        for tweet in c:
                            if j == 0:
                                parent = ''
                            else:
                                parent = str(i) + str(j-1)

                            id = str(i) + str(j)
                            #Sends the tweets to be added to the treeview
                            tweetAnalyzeQueue.put([parent, id, tweet[0], tweet[1]])
                            j += 1
            j = 0
            i += 1

        #Re-enables the button
        tweetAnalyzeQueue.put("enableButton")

#Class that streams tweets
class TweetStreamer(TwythonStreamer):

    #Function that sets the search parameters
    def setParameters(self, lang, track, geocode):
        self.lang = lang
        self.track = track
        self.geocode = geocode

    #Function that builds a conversation from a tweet object
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

    #Function that writes a tweet to a file specified by the searc parameters
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

    #Function that checks if a tweet is part of a conversation
    def checkIfConversation(self, data, turns, people, search):
        #Twitter instance
        global twitter
        #Queue to communicate with the GUI
        global tweetQueue
        #Queue to get signals from the processor class
        global qu
        #Queue to send signals to the processor class
        global done

        try:
            a = qu.get(block=False)
            if a == 'stop':
                tweetQueue.put('clearTree')
                done.put('done')
                return None
        except queue.Empty:
            pass

        if turns > 10:
            return False

        #Checking if there's a new unique participant
        if people.count(data['user']['id_str']) == 0:
            people.append(data['user']['id_str'])

        if data['in_reply_to_status_id']:
            #Try to find the tweet that was responded and call the function recursively
            try:
                next = twitter.show_status(id=data['in_reply_to_status_id'])
            except exceptions.TwythonError:
                return False
            if self.checkIfConversation(next, turns+1, people, search):
                if turns == 1:
                    self.writeConversation(data)
                tweetQueue.put(data)
                return True
            else:
                return False
        else:
            #If it's the first tweet in the conversation and it meets the requirements, returns true and sends it to the queue
            if turns >= 3 and len(people) >= 2:
                tweetQueue.put(data)
                return True
            else:
                return False

    #Function called when a tweet is found by the streamer
    def on_success(self, data):

        if 'in_reply_to_status_id' in data:
            if data['in_reply_to_status_id']:
                people = []
                people.append(data['user']['id_str'])
                self.checkIfConversation(data, 1, people, False)

    #Function called when an error occurs with the streamer
    def on_error(self, status_code, data):
        global procqueue
        procqueue.put('Error code: ' + str(status_code))
        self.disconnect()


######### FRAME 2 #########

#Frame with filter parameters
class FilterParamFrame(tk.Frame):

    #functions that restrict the Minimum and Maximum turns/people
    def minPeopleTraceCallback(self, *args):
        self.maxPeopleScl.config(from_=self.minPeopleVar.get())

    def maxPeopleTraceCallback(self, *args):
        self.minPeopleScl.config(to=self.maxPeopleVar.get())

    def minTurnsTraceCallback(self, *args):
        self.maxTurnsScl.config(from_=self.minTurnsVar.get())

    def maxTurnsTraceCallback(self, *args):
        self.minTurnsScl.config(to=self.maxTurnsVar.get())

    #Function that recursively returns all the children of a tweet in the treeview widget
    def getTweetChildren(self, conversation, tweetId):
        child = self.parent.tree.get_children(tweetId)

        if not child:
            return conversation
        else:
            conversation.append(child[0])
            return self.getTweetChildren(conversation, child[0])

    #Function that formats a conversation in a list of tuples ("user", "text")
    def formatConversation(self, conversation):
        newC = []
        for c in conversation:
            newC.append((self.parent.tree.item(c, option="text").decode(), self.parent.tree.item(c, option="values")[0]))

        return newC

    #Function that returns the filter parameters as a list
    def getFilterParam(self):
        filterParam = []

        filterParam.append((self.minTurnsScl.get(), self.maxTurnsScl.get()))
        filterParam.append((self.minPeopleScl.get(), self.maxPeopleScl.get()))
        filterParam.append(self.posNegVar.get())

        return filterParam

    #Function that returns all the tweets from the TreeView widget
    def getTweets(self):
        tweets = self.parent.tree.get_children()
        conversations = []

        for t in tweets:
            conv = self.getTweetChildren([t],t)
            conversations.append(self.formatConversation(conv))

        return conversations

    #Function that starts the thread to apply the filters on the conversations
    def applyFilters(self):
        conversations = self.parent.getConversations()

        self.applyBtn.config(state=tk.DISABLED)
        self.parent.clearTree()
        threading.Thread(target=Processor().filterConversationsProc, args=(conversations, self.getFilterParam())).start()

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.parent = parent

        #Top label
        self.searchLbl = tk.Label(self, text="Filter Parameters")
        self.searchLbl.grid(row=0, column=0, columnspan=2, pady="7px")

        #Minimum participants scale
        self.minPeopleLbl = tk.Label(self, text="Minimum participants")
        self.minPeopleLbl.grid(row=1, column=0, pady="7px")
        self.minPeopleVar = IntVar()
        self.minPeopleScl = tk.Scale(self, variable=self.minPeopleVar, from_=2, to=10, orient=HORIZONTAL)
        self.minPeopleScl.grid(row=1, column=1)

        #Maximum participants scale
        self.maxPeopleLbl = tk.Label(self, text="Maximum participants")
        self.maxPeopleLbl.grid(row=2, column=0, pady="7px")
        self.maxPeopleVar = IntVar()
        self.maxPeopleScl = tk.Scale(self, variable=self.maxPeopleVar, from_=2, to=10, orient=HORIZONTAL)
        self.maxPeopleScl.grid(row=2, column=1)

        self.minPeopleVar.trace("w", self.minPeopleTraceCallback)
        self.maxPeopleVar.trace("w", self.maxPeopleTraceCallback)

        #Minimum turns scale
        self.minTurnsLbl = tk.Label(self, text="Minimum turns")
        self.minTurnsLbl.grid(row=3, column=0, pady="7px")
        self.minTurnsVar = IntVar()
        self.minTurnsScl = tk.Scale(self, variable=self.minTurnsVar, from_=3, to=10, orient=HORIZONTAL)
        self.minTurnsScl.grid(row=3, column=1)

        #Maximum turns scale
        self.maxTurnsLbl = tk.Label(self, text="Maximum turns")
        self.maxTurnsLbl.grid(row=4, column=0, pady="7px")
        self.maxTurnsVar = IntVar()
        self.maxTurnsScl = tk.Scale(self, variable=self.maxTurnsVar, from_=3, to=10, orient=HORIZONTAL)
        self.maxTurnsScl.grid(row=4, column=1)

        self.minTurnsVar.trace("w", self.minTurnsTraceCallback)
        self.maxTurnsVar.trace("w", self.maxTurnsTraceCallback)

        #Frame with radiobuttons
        self.posNegFrame = tk.Frame(self)
        self.posNegFrame.grid(row=5, column=0, rowspan=2, columnspan=2)

        #Label
        self.posNegLbl = tk.Label(self.posNegFrame, text="Conversation Flow:")
        self.posNegLbl.grid(row=0, column=0, columnspan=3)

        #Text and values of radiobuttons
        self.modes = [
            ("Negative", "neg"),
            ("Neutral", "neu"),
            ("Positive", "pos")
        ]
        self.posNegVar = StringVar()
        self.posNegVar.set("neu")

        #Radiobuttons
        i=0
        for text, mode in self.modes:
            rb = tk.Radiobutton(self.posNegFrame, text=text, variable=self.posNegVar, value=mode)
            rb.grid(row=1, column=i)
            i += 1

        #Apply button
        self.applyBtn = tk.Button(self, text="Apply", command=self.applyFilters)
        self.applyBtn.grid(row=7, column=0, columnspan=2, pady="7px")

#Frame with the conversations and filter parameters
class ConversationDisplayer(tk.Frame):

    #Function that adds a tweet to the TreeView widget
    def insertTweetAnalyze(self, tweet):
        if self.tree.exists(tweet[1]):
            return
        else:
            t = tweet[3].replace("\n", ". ").replace(" ", "\ ").encode()

            try:
                self.tree.insert(tweet[0], 'end', tweet[1], text=tweet[2].encode(), values=(t))
            except tk.TclError:
                pass

    #Function that periodically checks the TweetAnalyzeQueue
    def checkTweetAnalyzeQueue(self):
        global close

        if close:
            return

        try:
            tweet = tweetAnalyzeQueue.get(block=False)
            #Check if any action should be taken or inserts a tweet
            if tweet:
                if tweet == "clearTree":
                    self.clearTree()
                elif tweet == "setConversations":
                    self.setConversations()
                elif tweet == "disableButton":
                    self.paramFrame.applyBtn.config(state=tk.DISABLED)
                elif tweet == "enableButton":
                    self.paramFrame.applyBtn.config(state=tk.NORMAL)
                else:
                    self.insertTweetAnalyze(tweet)

        except queue.Empty: pass
        self.after(50, self.checkTweetAnalyzeQueue)

    #Clears the TreeView widget
    def clearTree(self):
        self.tree.delete(*self.tree.get_children())

    #Enables the Apply Button
    def enableButton(self):
        self.paramFrame.applyBtn.config(state=tk.NORMAL)

    #Set the local conversations variable
    def setConversations(self):
        self.conversations = self.paramFrame.getTweets()

    #Returns the local conversations variable
    def getConversations(self):
        return self.conversations

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        #Top label
        self.titleLbl = tk.Label(self, text="TWEET ANALYZER")
        self.titleLbl.grid(row=0, column=0, columnspan=9)

        #Conversations tree and scrollbar
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

        #Processor instance
        self.proc = Processor()

        #Filter parameters frame
        self.paramFrame = FilterParamFrame(self)
        self.paramFrame.grid(row=1, column=7, sticky=E)

        #Local conversations variable
        self.conversations = []

#Function that starts the streamer with the specified parameters
def startStream(q, lang, geocode):

    if geocode:
        streamer.setParameters(lang, q, geocode)
        streamer.statuses.filter(language=lang, track=q, locations=geocode)
    else:
        streamer.setParameters(lang, q, None)
        streamer.statuses.filter(language=lang, track=q)

#Function that returns the credentials from the file
def getCredentials():
    f = open("credentials.txt", "r")
    cred = f.readlines()

    return cred;

#Callback function called when the application is closed
def callback():
    #Sets the flags, stops the streamer and send the stop signals to the queue
    close = True
    stopSearch = True
    streamer.disconnect()
    if search:
        qu.put('stop')
        a = done.get(block=True)
    root.destroy()

#Global queues
procqueue = queue.Queue()
tweetQueue = queue.Queue()
tweetAnalyzeQueue = queue.Queue()
qu = queue.Queue()
done = queue.Queue()

#Global flags
close = False
search = False
stopSearch = False

#Initializing the streamer a twitter instances with the credentials
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

#Initializing the root
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", callback)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
root.rowconfigure(3, weight=1)

#Initializing frame 1
mainFrame = tk.Frame(root)
iss = IncomingTweets(root)
iss.grid(row=0, column=0, sticky=N+S+E+W)
iss.checkProcQueue()
threading.Thread(target=iss.checkTweetQueue).start()

#Initializing frame 2
cd = ConversationDisplayer(root)
cd.grid(row=3, column=0, sticky=N+S+E+W)
threading.Thread(target=cd.checkTweetAnalyzeQueue).start()

root.mainloop()
