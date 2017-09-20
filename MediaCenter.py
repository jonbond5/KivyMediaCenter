from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import *
from kivy.uix.label import Label
from kivy.properties import StringProperty,ObjectProperty,NumericProperty
from kivy.core.audio import SoundLoader
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from linecache import getline
import random
from os import getcwd, chdir
from functools import partial
import time
from csv import writer,reader,QUOTE_NONE
import datetime
from tempfile import NamedTemporaryFile
import shutil
import RPi.GPIO as GPIO


directory = getcwd()
chdir(directory)

###########################################################################

class Timer(Widget):
    time = StringProperty()

    def timeUpdate(self,*args):
        t=datetime.datetime.now()
        minute=t.minute
        hour=t.hour
        maritime='AM'
        if(minute<10):
            minute='0'+str(minute)
        if(hour >= 12):
            if(hour>12):
                hour -=12
            maritime='PM'
        self.time = str(hour)+':'+str(minute)+ ' ' + maritime

    def getTime(self):
        self.timeUpdate()
        return self.time



class MainScreen(Screen):
    localTime = StringProperty()

    def __init__(self,**kwargs):
        super(MainScreen,self).__init__(**kwargs)
        Clock.schedule_interval(self.updateTime,60)
        self.updateTime()

    def updateTime(self,*args):
        self.localTime = Timer().getTime()


########################################################################################################

class Marker(Widget):

    def __init__(self,**kwargs):
        super(Marker,self).__init__(**kwargs)

    def move(self,incrementation):
        self.x = incrementation + self.x

    def reset(self):
        self.x = 335


    # if there's a song playing, stop it and update widget position
    def on_touch_down(self,touch):
        if touch.x < 685 and touch.x > 335 and touch.y > 170 and touch.y < 225:
            if self.parent.parent.get_screen('audio').song is not None:
                self.parent.parent.get_screen('audio').stopMusic()
                self.x = touch.x


    # Continue updating widget position
    def on_touch_move(self,touch):
        if touch.x < 685 and touch.x > 335 and touch.y > 170 and touch.y < 225:
            if self.parent.parent.get_screen('audio').song is not None:
                self.x = touch.x


    # When event is over, play the song
    def on_touch_up(self,touch):
        if self.parent.parent.get_screen('audio').song is not None:

            if touch.x < 685 and touch.x > 335 and touch.y > 170 and touch.y < 225:
                this = self.parent.parent.get_screen('audio')
                # Audio-equivalent position using last touch
                position = int( (self.x - 335) / 350 * this.song.length)
                this.song.play()
                this.song.seek(position)
                this.songMinutes = 0
                this.songSeconds = position
                Clock.schedule_interval(this.seekTracker,1)


class AudioScreen(Screen):
    # Constructor
    localTime = StringProperty()
    currentlyPlaying = StringProperty()
    song = ObjectProperty(None)
    songList=[]
    played=[]
    songVolume = 0.2
    songSeconds=NumericProperty()
    songMinutes=NumericProperty()
    songPositionString = StringProperty()
    songIncrementation=NumericProperty()
    songLengthNum = NumericProperty()
    songLength = StringProperty()
    marker=ObjectProperty(None)
    layout=GridLayout(cols=1, spacing=0, size_hint_y=None)
    scroll = ScrollView(size_hint=(None, None), size=(300, 350),pos=(0,80))
    localPlaylist = StringProperty()
    # END CONSTRUCTOR



    # This function loads the selected song into memory and plays it and unloads any currently playing song

    def stopMusic(self):
        if self.song is not None:
            self.song.stop()
            Clock.unschedule(self.seekTracker)

    def playMusic(self,*args):
        if self.song is None:
            self.ffMusic()
        if self.song.state is not 'play':
            if self.song is not None:
                self.song.seek(60*self.songMinutes+self.songSeconds)
                self.song.play()

                # Free up mem for pi, use a greater time interval for clock interval
                Clock.schedule_interval(self.seekTracker,1)

    def seekTracker(self,*args):
        if self.songMinutes*60 + self.songSeconds >= self.song.length:
            self.audioUnpack(random.choice(self.songList))

        self.songSeconds += 1
        # Time logic

        while self.songSeconds >= 60:
            self.songMinutes += 1
            self.songSeconds -= 60
        # Add a 0 in front of seconds for proper time
        if self.songSeconds < 10:
            self.songPositionString = str(self.songMinutes)+':0'+str(self.songSeconds)
        else:
            self.songPositionString = str(self.songMinutes)+':'+str(self.songSeconds)

        self.marker.move(self.songIncrementation)


    def audioUnpack(self,songToPlay,isrw=False,*args):
        # Check if a song is playing and stop it
        if self.song is not None:
            self.song.stop()
            self.song.unload()
            Clock.unschedule(self.seekTracker)
        # Build path and load
        soundString = getcwd() + '/Songs/' + songToPlay
        self.song = SoundLoader.load(soundString)

        # Build string for song label
        self.currentlyPlaying = songToPlay[:-4]

        # Add to played list for RW
        self.played+=[songToPlay]
        self.songSeconds = 0
        self.songMinutes = 0
        self.songPositionString = '0:00'

        # Calc length string
        minutes = 0
        self.songLengthNum = self.song.length
        while(self.songLengthNum - 60.0 >= 1.0):
            self.songLengthNum -= 60
            minutes += 1
        if self.songLengthNum < 10:
            self.songLength = str(minutes) + ':0' + str(int(self.songLengthNum))
        else:
            self.songLength = str(minutes)+ ':' + str(int(self.songLengthNum))

        # Track the seek bar
        self.marker.reset()
        self.songIncrementation = 325 / self.song.length
        Clock.schedule_interval(self.seekTracker,1)

        # If calld by RW, pop off last song (prevent RW func from duplicating songs)
        if isrw:
            self.played.pop()
        self.song.volume = self.songVolume
        self.song.play()



    def rwMusic(self):
        if self.song is not None:
            if self.song.get_pos() < 1:
                self.song.stop()
                self.song.play()
            elif(len(self.played)>1):
                self.played.pop()
                self.audioUnpack(self.played[-1],True)
            else:
                self.audioUnpack(random.choice(self.songList))

    def ffMusic(self):
        self.audioUnpack(random.choice(self.songList),False)

    #adjust volume
    def volumeAdjust(self,*args):
        if self.song is not None:
            self.song.volume=args[1]
            self.songVolume=args[1]


#####################################################

    def __init__(self,**kwargs):
        super(AudioScreen,self).__init__(**kwargs)
        self.add_widget(AudioButton())
        self.add_widget(UtilButton())
        self.add_widget(MainButton())
        playlistPos = getline('util.txt',1)[6:-1]
        self.localPlaylist = playlistPos[:-4]

        self.layout.bind(minimum_height=self.layout.setter('height'))
        with open(playlistPos,'r') as file:
            for row in file:
                self.songList+=[row[:-1]]
                btn = Button(text=row[:-5],id=row, size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=partial(self.audioUnpack,row[:-1],False))
                self.layout.add_widget(btn)
            file.close()
        self.scroll.add_widget(self.layout)
        self.add_widget(self.scroll)

        volumeSlider = Slider(orientation='vertical',max=1,min=0,
                              pos=(715,85),value=0.2,
                              size_hint=(None,None),size=(50,175))
        volumeSlider.bind(value=self.volumeAdjust)
        self.add_widget(volumeSlider)
        Clock.schedule_interval(self.updateTime,60)
        self.updateTime()

    def updatePlaylist(self,plist,*args):
        self.layout.clear_widgets()
        self.scroll.clear_widgets()
        self.songList = []
        self.localPlaylist = plist[:-4]
        with open(plist,'r') as file:
            for row in file:
                self.songList += [row[:-1]]
                btn = Button(text=row[:-5],id=row, size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=partial(self.audioUnpack,row[:-1],False))
                self.layout.add_widget(btn)
            file.close()
        self.scroll.add_widget(self.layout)



    def updateTime(self,*args):
        self.localTime = Timer().getTime()

##################################################################################################################



class PlaylistScreen(Screen):
    # Set currentPlaylist to playlist attr of util.txt
    localTime = StringProperty()
    playlistTitle = StringProperty('Playlists')
    currentPlaylist = StringProperty()
    editingActive = False
    songs=GridLayout(cols=1, spacing=0, size_hint_y=None)
    playlists=GridLayout(cols=1, spacing=0, size_hint_y=None)
    songsToAdd=GridLayout(cols=1,spacing=0, size_hint_y=None)
    scroll = ScrollView(size_hint=(None, None), size=(250, 350),pos=(250,80))
    scroll1 = ScrollView(size_hint=(None, None), size=(260, 350),pos=(10,80))

    ############
    def __init__(self,**kwargs):
        super(PlaylistScreen,self).__init__(**kwargs)
        # Store line 1 in playlistPos, and set it equal to currentP.
        playlistPos = getline('util.txt',1)[6:-1]
        self.currentPlaylist = str(playlistPos)

        self.songs.bind(minimum_height=self.songs.setter('height'))
        self.playlists.bind(minimum_height=self.playlists.setter('height'))
        self.songsToAdd.bind(minimum_height=self.songsToAdd.setter('height'))

        # Make buttons for all playlists
        with open('playlistLog.csv','r') as file:
            for row in file:
                btn = Button(text=row[:-1],id=row, size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=partial(self.buildSongsList,row[:-1]))
                self.playlists.add_widget(btn)
            file.close()

        # Make buttons for those songs in playlist
        with open(self.currentPlaylist,'r') as file:
            for row in file:
                btn = Button(text=row[:-5],size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=
                             partial(self.audioUnpackTerminal,row[:-1],self.currentPlaylist))
                self.songs.add_widget(btn)
            file.close()

        # Creates list of all songs
        with open('rootList.csv','r') as file:
            for row in file:
                btn=Button(text=row[:-5],size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=partial(self.addButton,row[:-1]))
                self.songsToAdd.add_widget(btn)
            file.close()

        self.scroll.add_widget(self.songs)
        self.add_widget(self.scroll)

        self.scroll1.add_widget(self.playlists)
        self.add_widget(self.scroll1)

        Clock.schedule_interval(self.updateTime,60)
        self.updateTime()

    ##############

    # Builds songs layout with buttons that run audio terminal
    def buildSongsList(self,filename,*args):
        print(filename,len(filename))
        filename = filename[:-1]
        self.songs.clear_widgets()
        self.scroll.clear_widgets()
        if filename[-3:-1] != 'csv':
            filename += '.csv'
        with open(filename,'r') as file:
            for row in file:
                btn = Button(text=row[:-6],size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                             on_release=partial(self.audioUnpackTerminal,row[:-1],filename))
                self.songs.add_widget(btn)
            file.close()
        self.scroll.add_widget(self.songs)
        self.currentPlaylist = filename
        self.parent.get_screen('audio').updatePlaylist(filename)
        self.updateCurrentList('/list')

    # Helper function: plays song from playlist
    ##########################################
    def audioUnpackTerminal(self,*args):
        if self.editingActive == False:
            this = self.parent.get_screen('audio')
            this.audioUnpack(args[0])
            this.localPlaylist = args[1][:-3]
            self.parent.current='audio'
        else:
            self.removeButton(args[0])


    def editPlaylist(self,*args):
        if self.playlistTitle != 'Add songs':
            self.playlistTitle = 'Add songs'
            self.remove_widget(self.scroll1)
            self.scroll1.remove_widget(self.playlists)
            self.scroll1.add_widget(self.songsToAdd)
            self.add_widget(self.scroll1)
            self.editingActive = True

    def addButton(self,name,*args):
        with open(self.currentPlaylist,'a',newline='') as file:
            self.songs.add_widget(
                Button(text=name[:-4],size_hint_y=None,
                             height=35,color=(0,1,1,0.9),
                             background_color=(1,1,1,0),
                        on_release=partial(self.removeButton,name)))
            a = writer(file,delimiter='\n')
            a.writerow([name])

            file.close()


    def removeButton(self,name,*args):
        # Prevents deleting all songs of name 'name', deletes first time 'name' occurs, faulty
        notFound = True
        filename = self.currentPlaylist
        tempfile = NamedTemporaryFile(
            delete=False,
            dir=directory)
        with open(filename,'r+') as file:
            with open(tempfile.name,'w+') as tempfile:
                w = writer(tempfile,lineterminator='\n')
                for row in file:
                    if row[:-1] != name or notFound == False:
                        w.writerow([row[:-1]])
                    elif notFound:
                        notFound = False
        shutil.move(tempfile.name,filename)
        self.buildSongsList(filename[:-4])
    def cancelEditing(self,*args):
        if self.playlistTitle != 'Playlists':
            self.scroll1.remove_widget(self.songsToAdd)
            self.scroll1.add_widget(self.playlists)
            self.playlistTitle = 'Playlists'
            self.editingActive = False

    # finder is a 5 character decorator that determines the right row
    # e.g.: to change the list, finder = '/list'
    # check 'util.txt' for the list of finders
    # Function writes current list to file for later reference
    def updateCurrentList(self,finder,*args):
        name = self.currentPlaylist
        tempfile = NamedTemporaryFile(
            delete=False,
            dir=directory)
        with open('util.txt','r+') as f:
            with open(tempfile.name,'w+') as tempfile:
                for row in f:
                    if row[0:5] == finder:
                        tempfile.write(finder+','+name+'\n')
                    else:
                        tempfile.write(row+'\n')
        shutil.move(tempfile.name,'util.txt')


    def updateTime(self,*args):
        self.localTime = Timer().getTime()


        ################################


class SettingsScreen(Screen):
    
    localTime = StringProperty()
    
    def __init__(self,**kwargs):
        super(SettingsScreen,self).__init__(**kwargs)
        Clock.schedule_interval(self.updateTime,60)
        self.updateTime()

    
    def updateTime(self,*args):
        self.localTime = Timer().getTime()


class MainMenu(Widget):
    pass

class AudioButton(Button):
    pass

class MainButton(Button):
    pass

class UtilButton(Button):
    pass


Builder.load_string("""
<AudioButton>:
    size_hint:None,None
    size:250,80
    background_color:0,0,0,0
    color:1,0,0,1
    font_name:'Fonts/KenneySpace.ttf'
    font_size:24
    text:'Audio'
    pos:0,0
    on_release:app.sm.current='audio'

<MainButton>:
    size_hint:None,None
    size:250,80
    background_color:0,0,0,0
    color:1,0,0,1
    font_name:'Fonts/KenneySpace.ttf'
    font_size:24
    text:'Home'
    pos:275,0
    on_release:app.sm.current='main'

<UtilButton>:
    size_hint:None,None
    size:250,80
    background_color:0,0,0,0
    color:1,0,0,1
    font_name:'Fonts/KenneySpace.ttf'
    font_size:24
    text:'Settings'
    pos:550,0
    on_release:app.sm.current='settings'


<MainMenu>:
    canvas:
        Rectangle:
            size:self.size
            source:'Acura_Logo.jpg'
        Color:
            rgba: 0,0,0,1
        Rectangle:
            size:800,80
            pos:0,0
        Ellipse:
            pos:510,400
            size:100,100
        Rectangle:
            pos:560,400
            size:250,100

    AudioButton:
    MainButton:
    UtilButton:

####################################################

<MainScreen>:
    canvas:
        Rectangle:
            size:self.size
            source:'Acura_Logo.jpg'
        Color:
            rgba: 0,0,0,1
        Rectangle:
            size:800,80
            pos:0,0
        Ellipse:
            pos:510,400
            size:100,100
        Rectangle:
            pos:560,400
            size:250,100

    AudioButton:
    MainButton:
    UtilButton:
   
    Label:
        size_hint:None,None
        size:50,50
        pos:650,420
        font_name:'Fonts/DAGGERSQUARE.otf'
        font_size:58
        text:root.localTime

<Marker>:
    size_hint:None,None
    size:5,30
    pos:810,177
    canvas:
        Color:
            rgb:1,0,1
        Rectangle:
            pos:self.pos
            size:self.size


<AudioScreen>:
    marker:marker_id
    canvas:
        Rectangle:
            size:self.size
            source:'Acura_Logo.jpg'
        Color:
            rgba: 0,0,0,1
        Rectangle:
            size:800,80
            pos:0,0
        Ellipse:
            pos:510,400
            size:100,100
        Rectangle:
            pos:560,400
            size:250,100
        Color:
            rgba:0,0,0,.75
        Rectangle:
            pos:0,80
            size:800,400
        Color:
            rgba:0,0,0,1
        Rectangle:
            pos:300,80
            size:500,175
        Color:
            rgba:.3,.3,.3,1
        Rectangle:
            pos:335,190
            size:350,5


    Marker:
        id:marker_id



    Label:
        size_hint:None,None
        size:50,50
        pos:650,420
        font_name:'Fonts/DAGGERSQUARE.otf'
        font_size:58
        text:root.localTime

    Label:
        size_hint:None,None
        font_size:24
        pos:400,190
        text:root.currentlyPlaying
    Label:
        size_hint:None,None
        pos:265,143
        text:root.songPositionString
    Label:
        size_hint:None,None
        pos:655,143
        text:root.songLength

    Label:
        size_hint:None,None
        pos:100,400
        font_size:24
        font_name:'Fonts/KenneySpace.ttf'
        color:1,0,0,.65
        text:root.localPlaylist

    Button:
        size_hint:None,None
        size:75,75
        pos:600,90
        background_normal:'Icons/FF_button.png'
        background_down:'Icons/FF_button_active.png'
        on_release:root.ffMusic()


    Button:
        size_hint:None,None
        size:75,75
        pos:300,90
        background_normal:'Icons/RW_button.png'
        background_down:'Icons/RW_button_active.png'
        on_release:root.rwMusic()



    Button:
        size_hint:None,None
        size:65,65
        pos:405,95
        background_normal:'Icons/pause_button.png'
        background_down:'Icons/pause_button_active.png'
        on_release:root.stopMusic()


    Button:
        size_hint:None,None
        size:75,75
        pos:500,90
        background_normal:'Icons/play_button.png'
        background_down:'Icons/play_button_active.png'
        on_release:root.playMusic()

    Button:
        size_hint:None,None
        size:50,50
        pos:715,260
        background_normal:'Icons/add-to-playlist.png'
        background_down:'Icons/add-to-playlist.png'
        on_release:app.sm.current='playlist'


<PlaylistScreen>:

    canvas:
        Rectangle:
            size:self.size
            source:'Acura_Logo.jpg'
        Color:
            rgba: 0,0,0,1
        Rectangle:
            size:800,80
            pos:0,0
        Ellipse:
            pos:510,400
            size:100,100
        Rectangle:
            pos:560,400
            size:250,100
        Color:
            rgba:0,0,0,.75
        Rectangle:
            pos:0,80
            size:800,400
    AudioButton:
    MainButton:
    UtilButton:

    Label:
        size_hint:None,None
        size:50,50
        pos:650,420
        font_name:'Fonts/DAGGERSQUARE.otf'
        font_size:58
        text:root.localTime

    Label:
        size_hint:None,None
        pos:100,400
        font_size:18
        text:root.playlistTitle
        font_name:'Fonts/KenneySpace.ttf'
        color:1,0,0,.8

    Label:
        font_name:'Fonts/KenneySpace.ttf'
        size_hint:None,None
        pos:325,400
        font_size:18
        text:root.currentPlaylist[:-4]
        color: 1,0,0,.8

    Button:
        pos:555,300
        size_hint:None,None
        size:200,50
        text:'Edit active playlist'
        background_color:0,0,0,0
        color:0,1,0,.9
        font_size:24
        on_release:root.editPlaylist()

    Button:
        pos:555,240
        size_hint:None,None
        size:200,50
        text:'Done editing'
        background_color:0,0,0,0
        color:0,1,0,.9
        font_size:24
        on_release:root.cancelEditing()


<SettingsScreen>:
    canvas:
        Rectangle:
            size:self.size
            source:'Acura_Logo.jpg'
        Color:
            rgba:0,0,0,1
        Rectangle:
            size:800,80
            pos:0,0
        Ellipse:
            pos:510,400
            size:100,100
        Rectangle:
            pos:560,400
            size:250,100

    Button:
        size_hint:None,None
        size:400,100
        pos:100,100
        font_size:58
        text:"Change Lights"
        background_color:0,0,0,0
        color:0,.75,.75,1
        on_release:app.turnOnLights()
    Button:
        size_hint:None,None
        size:100,100
        pos:400,250
        on_press:app.quit()


    Label:
        size_hint:None,None
        size:50,50
        pos:650,420
        font_name:'Fonts/DAGGERSQUARE.otf'
        font_size:56
        text:root.localTime

    AudioButton:
    MainButton:
    UtilButton:

""")


class MediaCenterApp(App):

    def turnOnLights(self):
        GPIO.output(18,True)

    def quit(self):
        GPIO.output(18,False)
        GPIO.cleanup()
        self.stop()

    sm = ScreenManager()
    sm.add_widget(MainScreen(name='main'))
    sm.add_widget(AudioScreen(name='audio'))
    sm.add_widget(SettingsScreen(name='settings'))
    sm.add_widget(PlaylistScreen(name='playlist'))

    #Constructor
    #Window.size = (800,480) #Adjusts window size and removes border

    #Window.size = (480,360)
    #Window.borderless = True

    def build(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18,GPIO.OUT)
        return self.sm

MediaCenterApp().run()
