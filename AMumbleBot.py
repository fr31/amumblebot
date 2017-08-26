#!/usr/bin/env python3

import pymumble.pymumble_py3 as pymumble
import random
import time
import audioop
import signal
import sys
import subprocess
import configparser
import html5lib
import os
import pafy

def html_to_text(body):
    doc = html5lib.parse(body, treebuilder="lxml")
    return(doc.xpath("string()"))

class MumbleBot(object):
    def __init__(self):
        signal.signal(signal.SIGINT, self.kill)

        self.playing = False
        self.stop_playing = False
        self.exit = False
        self.thread = None

        self.playlist = []
        self.skip = False
        self.remove = False
        self.playlist_playing = False

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.ini"))

        if self.config.get('bot', 'certfile').lower() == "none":
            self.mumblecert = None
        else:
            self.mumblecert = self.config.get('bot', 'certfile')

        if self.config.get('bot', 'keyfile').lower() == "none":
            self.mumblekey = None
        else:
            self.mumblekey = self.config.get('bot', 'keyfile')

        self.mumblecomment = self.config.get('bot', 'comment')
        self.volume = self.config.getfloat('bot', 'volume')

        self.playcmd = self.config.get('commands', 'play')
        self.stopcmd = self.config.get('commands', 'stop')
        self.addcmd = self.config.get('commands', 'add')
        self.removecmd = self.config.get('commands', 'remove')
        self.skipcmd = self.config.get('commands', 'skip')
        self.shufflecmd = self.config.get('commands', 'shuffle')
        self.volumecmd = self.config.get('commands', 'volume')
        self.mutecmd = self.config.get('commands', 'mute')
        self.unmutecmd = self.config.get('commands', 'unmute')
        self.joincmd = self.config.get('commands', 'join')
        self.helpcmd = self.config.get('commands', 'help')
        self.killcmd = self.config.get('commands', 'kill')
        self.flipcmd = self.config.get('commands', 'flip')
        self.rollcmd = self.config.get('commands', 'roll')
        self.customonecmd = self.config.get('commands', 'customcmdone')
        self.customtwocmd = self.config.get('commands', 'customcmdtwo')

        self.notices = self.config.getboolean('notifications', 'notices')
        self.playingnownotice = self.config.get('notifications', 'playingnow')
        self.invalidcommandnotice = self.config.get('notifications', 'invalidcommand')
        self.emptyplaylistnotice = self.config.get('notifications', 'emptyplaylist')
        self.invalidurlnotice = self.config.get('notifications', 'invalidurl')
        self.volumesetnotice = self.config.get('notifications', 'volumeset')
        self.volumehighnotice = self.config.get('notifications', 'volumehigh')
        self.volumeerrornotice = self.config.get('notifications', 'volumeerror')
        self.volumemutednotice = self.config.get('notifications', 'volumemuted')
        self.botmutednotice = self.config.get('notifications', 'botmuted')
        self.botunmutednotice = self.config.get('notifications', 'botunmuted')
        self.addedsongnotice = self.config.get('notifications', 'addedsong')
        self.skipsongnotice = self.config.get('notifications', 'skipsong')
        self.rfpnotice = self.config.get('notifications', 'removefromplaylist')
        self.shufflenotice = self.config.get('notifications', 'shuffleplaylist')
        self.nowplayingnotice = self.config.get('notifications', 'nowplaying')
        self.stoppedplayingnotice = self.config.get('notifications', 'stoppedplaying')
        self.reqadminnotice = self.config.get('notifications', 'permission')
        self.helpnotice = self.config.get('notifications', 'help')
        self.customonenotice = self.config.get('notifications', 'custommsgone')
        self.customtwonotice = self.config.get('notifications', 'custommsgtwo')

        self.admins = self.config.get('other', 'admins').split(";")
        self.urlwhitelist = self.config.getboolean('other', 'urlwhitelist')
        self.whitelistedurls = self.config.get('other', 'whitelistedurls').split(";")
        self.blacklistedurls = self.config.get('other', 'blacklistedurls').split(";")
        self.filetypes = self.config.get('other', 'allowedfiletypes').split(";")

        self.mumble = pymumble.Mumble(self.config.get('server', 'server'), user=self.config.get('bot', 'username'), port=self.config.getint('server', 'port'),
                                      reconnect=self.config.getboolean('bot', 'autoreconnect'), certfile=self.mumblecert, keyfile=self.mumblekey)
        self.mumble.callbacks.set_callback("text_received", self.message_received)
        self.mumble.set_codec_profile("audio")
        self.mumble.start()
        self.mumble.is_ready()
        self.mumble.users.myself.unmute()
        self.mumble.set_bandwidth(200000)
        self.mumble.users.myself.comment(self.mumblecomment)

        self.mainloop()

    def mainloop(self):
        while not self.exit:
            try:
                if self.playing:
                    while self.mumble.sound_output.get_buffer_size() > 0.5 and self.playing:
                        time.sleep(0.01)
                    raw_music = self.thread.stdout.read(480)
                    if raw_music:
                        self.mumble.sound_output.add_sound(audioop.mul(raw_music, 2, self.volume))
                    else:
                        time.sleep(0.1)
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1)
        while self.mumble.sound_output.get_buffer_size() > 0:
            time.sleep(0.01)
        time.sleep(0.5)

    def message_received(self, raw):
        text = html_to_text(raw.message)
        user = raw.actor
        passwhitelist = False
        blacklisted = False
        reqadmin = False
        if self.mumble.users[user]['name'] in self.admins:
            admin = True
        else:
            admin = False
        if text.startswith("!"):
            for item in self.blacklistedurls:
                if item.lower() in text.lower():
                    blacklisted = True
                    break
            if self.urlwhitelist:
                for item in self.whitelistedurls:
                    if item.lower() in text.lower():
                        passwhitelist = True
                        break
                    else:
                        pass
            else:
                passwhitelist = True
            if not blacklisted:
                if "youtube.com" in text.lower() or "youtu.be" in text.lower():
                    pass
                elif text.lower() == "!play":
                    pass
                else:
                    for x in self.filetypes:
                        if text.lower().endswith(x):
                            blacklisted = False
                            break
                        else:
                            blacklisted = True
            if text[1:].lower().startswith(self.joincmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.joincmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.mumble.users.myself.move_in(self.mumble.users[user]['channel_id'])
            elif text[1:].lower().startswith(self.playcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.playcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    if passwhitelist and not blacklisted:
                        if text[1:].lower() == self.playcmd.split(";")[0]:
                            if self.playlist == []:
                                self.send_msg(self.emptyplaylistnotice, user, text)
                            else:
                                self.send_msg(self.nowplayingnotice, user, text)
                                self.play_playlist()
                        elif "http" in text.lower():
                            url = text[1:].split(' ', 1)
                            self.send_msg(self.nowplayingnotice, user, text)
                            self.play_url(url[1])
                        else:
                            self.send_msg(self.invalidurlnotice, user, text)
                    else:
                        self.send_msg(self.invalidurlnotice, user, text)
            elif text[1:].lower().startswith(self.stopcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.stopcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.send_msg(self.stoppedplayingnotice, user, text)
                    self.stop()
            elif text[1:].lower().startswith(self.addcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.addcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    if passwhitelist and not blacklisted:
                        if "http" in text.lower():
                            url = text[1:].split(' ', 1)
                            self.playlist.append(url[1])
                            if self.addedsongnotice == "None":
                                success = "None"
                            else:
                                success = "%s <a href=\"%s\">%s</a>" % (self.addedsongnotice, url[1], url[1])
                            self.send_msg(success, user, text)
                        else:
                            self.send_msg(self.invalidurlnotice, user, text)
                    else:
                        self.send_msg(self.invalidurlnotice, user, text)
            elif text[1:].lower().startswith(self.volumecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.volumecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    try:
                        vol = text[1:].split(' ', 1)[1]
                        vol = int(vol)/2 * 0.1
                        if vol > 0.5:
                            self.send_msg(self.volumehighnotice, user, text)
                        elif vol < 0.01:
                            self.send_msg(self.volumemutednotice, user, text)
                            self.volume = vol
                        else:
                            self.send_msg(self.volumesetnotice, user, text)
                            self.volume = vol
                    except Exception:
                        self.send_msg(self.volumeerrornotice, user, text)
            elif text[1:].lower().startswith(self.mutecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.mutecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.mumble.users.myself.mute()
                    self.send_msg(self.botmutednotice, user, text)
            elif text[1:].lower().startswith(self.unmutecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.unmutecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.mumble.users.myself.unmute()
                    self.send_msg(self.botunmutednotice, user, text)
            elif text[1:].lower().startswith(self.skipcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.skipcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.skip = True
                    self.send_msg(self.skipsongnotice, user, text)
            elif text[1:].lower().startswith(self.removecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.removecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.remove = True
                    self.send_msg(self.rfpnotice, user, text)
            elif text[1:].lower().startswith(self.shufflecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.shufflecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    random.shuffle(self.playlist)
                    if self.playlist_playing:
                        self.stop()
                        self.play_playlist()
                    else:
                        pass
                    self.send_msg(self.shufflenotice, user, text)
            elif text[1:].lower().startswith(self.helpcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.helpcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.send_msg(self.helpnotice, user, text)
            elif text[1:].lower().startswith(self.flipcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.flipcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    if random.randint(0,1) == 0:
                        result = "HEADS"
                    else:
                        result = "TAILS"
                    message = self.config.get('notifications', 'flip') % (self.mumble.users[user]['name'], result)
                    self.send_msg(message, user, text, True)
            elif text[1:].lower().startswith(self.rollcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.rollcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    result = random.randint(1,6)
                    message = self.config.get('notifications', 'roll') % (self.mumble.users[user]['name'], result)
                    self.send_msg(message, user, text, True)
            elif text[1:].lower().startswith(self.customonecmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.customonecmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.send_msg(self.customonenotice, user, text)
            elif text[1:].lower().startswith(self.customtwocmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.customtwocmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.send_msg(self.customtwonotice, user, text)
            elif text[1:].lower().startswith(self.killcmd.split(";")[0]):
                if "admin" in (a.lower() for a in self.killcmd.split(";")):
                    reqadmin = True
                if reqadmin and not admin:
                    self.send_msg(self.reqadminnotice, user, text)
                else:
                    self.send_msg("None", user, text)
                    self.stop()
                    print("\nExiting...")
                    self.exit = True
            else:
                self.send_msg(self.invalidcommandnotice, user, text)
        else:
            self.send_msg(self.invalidcommandnotice, user, text)

    def stop(self):
        if self.thread:
            self.playing = False
            time.sleep(0.5)
            self.thread.kill()
            self.thread = None
            self.stop_playing = True
            self.now_playing_comment(status=False)

    def play_url(self, url):
        self.stop()
        self.stop_playing = False
        if "youtu" in url:
            video = pafy.new(url)
            url = video.getbestaudio().url
            self.now_playing_comment(title=video.title, status=True)
            self.play(url)
            for x in range(video.length):
                if self.stop_playing:
                    break
                time.sleep(1)
            self.now_playing_comment(status=False)
        else:
            self.play(url)

    def play_playlist(self):
        self.stop()
        self.stop_playing = False
        self.playlist_playing = True
        while not self.stop_playing:
            for x in self.playlist:
                currentvideo = x
                self.skip = False
                video = pafy.new(currentvideo)
                bestaudio = video.getbestaudio().url
                self.play(bestaudio)
                self.stop_playing = False
                self.now_playing_comment(title=video.title,status=True)
                for x in range(video.length):
                    if self.stop_playing:
                        break
                    if self.skip:
                        break
                    if self.remove:
                        if currentvideo in self.playlist:
                            self.playlist.remove(currentvideo)
                        self.remove = False
                        self.skip = True
                    time.sleep(1)
                self.now_playing_comment(status=False)
                if self.stop_playing:
                    break
            self.stop()
        self.playlist_playing = False

    def play(self,url):
        self.stop()
        command = ["ffmpeg", '-v', 'warning', '-nostdin', '-i', url, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=480)
        self.playing = True

    def send_msg(self,msg,user,cmd,sendchannel=False):
        print("\n" + self.mumble.users[user]['name'] + ":", cmd + "\n" + html_to_text(msg))
        if self.notices and msg.lower() != "none":
            if not sendchannel:
                self.mumble.users[user].send_message(msg)
            else:
                self.mumble.channels[self.mumble.users.myself['channel_id']].send_text_message(msg)


    def now_playing_comment(self, title=None, status=False):
        if status:
            comment = "<b>%s</b><br /><i>%s</i><br /><br />%s" % (self.playingnownotice, title, self.mumblecomment)
            self.mumble.users.myself.comment(comment)
        else:
            self.mumble.users.myself.comment(self.config.get('bot', 'comment'))

    def kill(self,a,b):
        self.stop()
        self.exit = True
        print("\nExiting...")
        sys.exit()


if __name__ == '__main__':
    mumblebot = MumbleBot()