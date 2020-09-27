import json
from datetime import datetime
import time 
from flask import Flask, render_template
from flask_socketio import SocketIO
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import spotipy
import spotipy.util as util
import os

username = <YOUR USERNAME>
clientid = <YOUR CLIENTID>
clientsecret = <YOUR CLIENT SECRET>

scope = "user-read-playback-state,user-modify-playback-state,user-library-read"

app = Flask(__name__)

def convertMillis(millis):
     seconds=(millis/1000)%60
     minutes=(millis/(1000*60))%60
     hours=(millis/(1000*60*60))%24
     return seconds, minutes, hours

def buildJson(res):
     status = dict()
     status['updates'] = updates
     status['is_playing'] = res['is_playing']
     status['artistname'] = res['item']['artists'][0]['name']
     status['coverimage'] = res['item']['album']['images'][1]['url']
     status['albumname'] = res['item']['album']['name']
     status['trackname'] = res['item']['name']
     status['releasedate'] = res['item']['album']['release_date']
     duration = int(res['item']['duration_ms'])
     context = res['context']
     if (context != None) and ('type' in context):
          status['contexttype'] = res['context']['type']
     else:
          status['contexttype'] = ''
     progress = int(res['progress_ms'])
     lengthsecs, lengthmins, lengthhours = convertMillis(duration)
     status['tracklength'] = '{}:{}'.format(lengthmins, lengthsecs)
     status['percentcomplete'] = int(progress / duration * 100)
     if status['contexttype'] == 'playlist':
          playlist = sp.playlist(playlist_id=res['context']['uri'],market='GB', fields='name')
          status['playlistname'] = playlist['name']
     else:
          status['playlistname'] = ''
     strstatus = json.dumps(status)
     return strstatus

def tick():
     global token
     global sp
     global exceptions
     
     if updates == True:
          try:
               res = sp.current_playback(market='GB')
          except spotipy.client.SpotifyException:
               print('Exception - attempting to renew token')
               exceptions = exceptions + 1
               token = util.prompt_for_user_token(username,
                           scope,
                           client_id = clientid,
                           client_secret = clientsecret,
                           redirect_uri = 'http://localhost:5011')
               if token:
                    sp = spotipy.Spotify(auth=token)

          if res != None:
               strstatus = buildJson(res)
               socketio.emit('spotify_status', data=strstatus)
          else:
               print("none")

# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: scheduler.shutdown())

socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('shutdown')
def handle_shutdown():
     os.system("sudo shutdown /s /t 1")
     
@socketio.on('playpause')
def handle_playpause():
     print('playpause')
     res = sp.current_playback(market='GB')
     if res != None:
          device = res['device']['id']
          if res['is_playing'] == True:
               sp.pause_playback(device)
          else:
               sp.start_playback(device)
          if res['is_playing'] == True:
               res['is_playing'] = False
          else:
               res['is_playing'] = True
          strstatus = buildJson(res)
          socketio.emit('spotify_status', data=strstatus)

@socketio.on('back')
def handle_back():
     print('back')
     res = sp.current_playback(market='GB')
     if res != None:
          device = res['device']['id']          
          sp.previous_track(device)
          res = sp.current_playback(market='GB')
          strstatus = buildJson(res)
          socketio.emit('spotify_status', data=strstatus)

@socketio.on('fwd')
def handle_fwd():
     print('fwd')
     res = sp.current_playback(market='GB')
     if res != None:
          device = res['device']['id']          
          sp.next_track(device)
          res = sp.current_playback(market='GB')
          strstatus = buildJson(res)          
          socketio.emit('spotify_status', data=strstatus)

@socketio.on('updates')
def handle_kill():
     global updates
     if updates == True:
          updates = False
     else:
          updates = True
     res = sp.current_playback(market='GB')
     strstatus = buildJson(res)          
     socketio.emit('spotify_status', data=strstatus)


if __name__ == '__main__':
     updates = True
     exceptions = 0
     token = util.prompt_for_user_token(username,
                           scope,
                           client_id = clientid,
                           client_secret = clientsecret,
                           redirect_uri = 'http://localhost:5011')
     if token:
          sp = spotipy.Spotify(auth=token)
          scheduler = BackgroundScheduler()
          scheduler.add_job(tick, 'interval', seconds=10, max_instances=1)
          scheduler.start()

          socketio.run(app, host='0.0.0.0', port=5000, use_reloader=True, debug=True)
     else:
          print("ERROR RUNNING SPOTIPY. EXITING....")

