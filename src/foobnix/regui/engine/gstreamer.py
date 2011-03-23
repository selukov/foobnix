#-*- coding: utf-8 -*-
'''
Created on 28 сент. 2010

@author: ivan
'''
import os
import gst
import time
import thread
import urllib
import logging

from foobnix.regui.engine import MediaPlayerEngine
from foobnix.fc.fc import FC
from foobnix.util.const import STATE_STOP, STATE_PLAY, STATE_PAUSE, FTYPE_RADIO
from foobnix.util.plsparser import get_radio_source

class GStreamerEngine(MediaPlayerEngine):
    NANO_SECONDS = 1000000000
    def __init__(self, controls):
        MediaPlayerEngine.__init__(self, controls)

        self.player = self.gstreamer_player()
        self.position_sec = 0
        self.duration_sec = 0

        self.prev_path = None
        self.bean = None
        self.equalizer = None
        
        self.current_state = STATE_STOP
        self.remembered_seek_position = 0

    def get_state(self):
        return self.current_state
    
    def set_state(self, state):        
        self.current_state = state

    def gstreamer_player(self):
        playbin = gst.element_factory_make("playbin2", "player")
        
        
        if FC().is_eq_enable:
            self.audiobin = gst.Bin('audiobin')
            audiosink = gst.element_factory_make('autoaudiosink', 'audiosink')
    
            self.audiobin.add(audiosink)
            self.audiobin.add_pad(gst.GhostPad('sink', audiosink.get_pad('sink')))
            playbin.set_property('audio-sink', self.audiobin)
            
            self.equalizer = gst.element_factory_make('equalizer-10bands', 'equalizer')
            self.audiobin.add(self.equalizer)
    
            
            self.audiobin.get_pad('sink').set_target(self.equalizer.get_pad('sink'))
            self.equalizer.link(audiosink)
    
        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        logging.debug("LOCAL gstreamer")
        return playbin
    
    def notify_init(self, duration_int):
        logging.debug("Pre init thread" + str(duration_int))

    def notify_playing(self, position_int, duration_int, sec):
        #LOG.debug("Notify playing", position_int)
        self.position_sec = position_int / self.NANO_SECONDS
        self.duration_sec = duration_int / self.NANO_SECONDS
        self.controls.notify_playing(self.position_sec, self.duration_sec, self.bean, sec)

    def notify_eos(self):
        logging.debug("Notify eos, STOP State")
        self.controls.notify_eos()
        
        self.set_state(STATE_STOP)

    def notify_title(self, text):
        if self.bean.type == FTYPE_RADIO:
            "notify radio playing"
            self.controls.notify_title(text)

    def notify_error(self, msg):
        logging.debug("Notify error, STOP state")
        self.set_state(STATE_STOP)
        self.controls.notify_error(msg)

    def record_radio(self, bean):
        if not bean:
            return None
        path = bean.path
        
        self.state_stop()
        
        if path and path.startswith("http://"):
            path = get_radio_source(path)
            logging.debug("Try to play and record path" + path)
            
            file_name = "/tmp/" + os.path.basename(path)
            
            '''mime = subprocess.Popen("/usr/bin/file -i PATH", shell=True, \
    stdout=subprocess.PIPE).communicate()[0]'''
            self.pipeline = gst.parse_launch("""souphttpsrc location=%s ! tee name=t ! queue ! decodebin2 ! audioconvert ! audioresample ! autoaudiosink  t. ! queue ! filesink location=%s""" % (path, file_name))
            self.notify_title(path)
            self.pipeline.set_state(gst.STATE_PLAYING)
            
    
    def play(self, bean):
        self.bean = bean
        if not bean:
            return None
        path = bean.path

        if not path:
            logging.error("Can't play empty path!!!")
            return None

        
        self.state_stop()
        
        if hasattr(self, "pipeline"):
            self.pipeline.set_state(gst.STATE_NULL)
        
        self.player = self.gstreamer_player()
        
        """equlizer settings"""
        if FC().is_eq_enable:
            pre = self.controls.eq.get_preamp()
            bands = self.controls.eq.get_bands()
            self.set_all_bands(pre, bands)
        
        if path.startswith("http://"):
            path = get_radio_source(path)
            logging.debug("Try To play path" + path)
            
            if self.bean.type == FTYPE_RADIO:
                    time.sleep(2)
                    
            uri = path

            self.notify_title(uri)
        else:
            uri = 'file://' + urllib.pathname2url(path)
            if os.name == 'nt':
                uri = 'file:' + urllib.pathname2url(path)

        logging.info("Gstreamer try to play" + uri)
        self.player.set_property("uri", uri)
        
        self.state_pause()
        time.sleep(0.2)        
        self.seek_seconds(bean.start_sec)
        self.state_play()
        self.volume(FC().volume)
        
        logging.debug("current state before thread" + str(self.get_state()) + str(self.play_thread_id))
        self.play_thread_id = thread.start_new_thread(self.playing_thread, ())

    
    def set_all_bands(self, pre, values):
        if self.equalizer:
            for i, value in enumerate(values):      
                real = float(value) + pre
                if real >= 12:
                    real = 12
                if real <= -12:
                    real = -12
                self.equalizer.set_property("band%s" % i, real)
    
    def get_position_seek_ns(self):
        try:
            return self.player.query_position(gst.Format(gst.FORMAT_TIME), None)[0]
        except Exception, e:
            logging.warn("GET query_position" + str(e))
            return - 1
    
    def get_duration_seek_ns(self):
        try:
            return self.player.query_duration(gst.Format(gst.FORMAT_TIME), None)[0]
        except Exception, e:
            logging.warn("GET query_duration" + str(e))
            return - 1
    
    def playing_thread(self):
        thread_id = self.play_thread_id
        error_count = 0
        sec = 0
        
        logging.debug("current state in thread" + str(self.get_state()))
         
        while thread_id == self.play_thread_id:
            try:
                time.sleep(0.2)
                duration_int = self.get_duration_seek_ns()
                if duration_int == -1:
                    time.sleep(1)
                    continue
                self.notify_init(duration_int)
                break
            except Exception, e:
                logging.info("Init playing thread " + str(e))
                time.sleep(1)
                if error_count > 3:
                    logging.warn("shit happens")
                    self.state_stop()
                    time.sleep(1)
                    self.state_play()
                error_count += 1

        time.sleep(0.2)

        if self.bean.duration_sec > 0:
            duration_int = float(self.bean.duration_sec) * self.NANO_SECONDS
        
        logging.debug("current state before while" + str(self.get_state()))
        
        self.set_state(STATE_PLAY)
        
        while thread_id == self.play_thread_id:
            try:
                position_int = self.get_position_seek_ns()
                if position_int > 0 and self.bean.start_sec > 0:
                    position_int = position_int - float(self.bean.start_sec) * self.NANO_SECONDS
                    logging.debug(str(position_int) + str(self.bean.start_sec) + str(duration_int))
                    if position_int + self.NANO_SECONDS > duration_int:
                        self.notify_eos()
                
                if self.get_state() == STATE_PLAY:
                    sec += 1 
                    
                self.notify_playing(position_int, duration_int, sec)
            except Exception, e:
                logging.info("Playing thread error..." + str(e))

            time.sleep(1)

    def seek(self, percent, offset=0):
        if not self.bean:
            return None
        seek_ns = self.duration_sec * (percent + offset) / 100 * self.NANO_SECONDS;

        if self.bean.start_sec > 0:
            seek_ns = seek_ns + float(self.bean.start_sec) * self.NANO_SECONDS

        self.player.seek_simple(gst.Format(gst.FORMAT_TIME), gst.SEEK_FLAG_FLUSH, seek_ns)
    
    def seek_seconds(self, seconds):
        if not seconds:
            return
        logging.info("Start with seconds" + str(seconds))
        seek_ns = (float(seconds) + 0.0) * self.NANO_SECONDS
        logging.info("SEC SEEK SEC" + str(seek_ns))
        self.player.seek_simple(gst.Format(gst.FORMAT_TIME), gst.SEEK_FLAG_FLUSH, seek_ns)
    
    def seek_ns(self, ns):
        if not ns:
            return        
        logging.info("SEC ns" + str(ns))
        self.player.seek_simple(gst.Format(gst.FORMAT_TIME), gst.SEEK_FLAG_FLUSH, ns)

    def volume(self, percent):
        value = percent / 100.0
        self.player.set_property('volume', value)
        #self.player.get_by_name("volume").set_property('volume', value + 0.0)

    def state_play(self):
        self.player.set_state(gst.STATE_PLAYING)
        self.current_state = STATE_PLAY        
        self.on_chage_state()
            
    def get_current_percent(self):
        duration = self.get_duration_seek_ns()
        postion = self.get_position_seek_ns()
        return postion * 100.0 / duration 
    
    def seek_up(self, offset=3):                
        self.seek(self.get_current_percent(), offset)
        logging.debug("SEEK UP")
    
    def seek_down(self, offset= -3):
        self.seek(self.get_current_percent(), offset)
        logging.debug("SEEK DOWN")
    
    def restore_seek_ns(self):
        time.sleep(1)        
        self.player.seek_simple(gst.Format(gst.FORMAT_TIME), gst.SEEK_FLAG_FLUSH, self.remembered_seek_position)
        
    def state_stop(self, remeber_position=False):
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(gst.STATE_NULL)
        
        if remeber_position:
            self.player.set_state(gst.STATE_PAUSED)
            time.sleep(0.1)
            self.remembered_seek_position = self.get_position_seek_ns();
                        
        self.play_thread_id = None        
        self.player.set_state(gst.STATE_NULL)
        self.set_state(STATE_STOP)
        
        self.on_chage_state()
        logging.debug("state STOP")

    def state_pause(self):
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(gst.STATE_PAUSED)
        self.player.set_state(gst.STATE_PAUSED)
        self.set_state(STATE_PAUSE)
        self.on_chage_state()
        
    def state_play_pause(self):
        if self.get_state() == STATE_PLAY:
            self.state_pause()
        else:
            self.state_play()
            
    
    def on_chage_state(self):
        self.controls.on_chage_player_state(self.get_state(), self.bean)
    
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        self.controls.movie_window.draw_video(message)
        

    def on_message(self, bus, message):
        type = message.type
        
        
        if type == gst.MESSAGE_BUFFERING:
            return
        
        logging.debug("Message type %s" % type)
        logging.debug("Message %s" % message)
        
        if type in [ gst.MESSAGE_STATE_CHANGED, gst.MESSAGE_STREAM_STATUS]:            
            pass

        if type == gst.MESSAGE_TAG  and message.parse_tag():
            if message.structure.has_field("title"):
                title = message.structure['title']
                self.notify_title(title)

        elif type == gst.MESSAGE_EOS:
            logging.info("MESSAGE_EOS")
            self.notify_eos()
        elif type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            logging.warn("Error: " + str(err) + str(debug) + str(err.domain) + str(err.code))

            if err.code != 1:
                self.notify_error(str(err))

            
