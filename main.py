import json
import os
import redis
import spotify
import sys
import threading


class Player(object):

    def __init__(self):
        self.config = spotify.Config()
        self.config.load_application_key_file(
            os.environ.get('SPOTIFY_KEY_PATH'))
        self.config.dont_save_metadata_for_playlists = True
        self.config.initially_unload_playlists = True

        self.session = spotify.Session(self.config)

        self.loop = spotify.EventLoop(self.session)
        self.loop.start()

        self.audio = spotify.PortAudioSink(self.session)

        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_updated)
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)

        self.session.login(
            os.environ.get('SPOTIFY_USER'),
            os.environ.get('SPOTIFY_PASS'))

        self.redis = redis.StrictRedis(
            host=os.environ.get('REDIS_HOST'),
            port=int(os.environ.get('REDIS_PORT')),
            db=int(os.environ.get('REDIS_DB')))

        self.logged_in = threading.Event()
        self.end_of_track = threading.Event()
        self.logged_in.wait()

        self.listen()

    def listen(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe('fm.player')

        while True:
            for item in pubsub.listen():
                if item.get('type') == 'message':
                    data = json.loads(item.get('data'))
                    if data['event'] == 'pause':
                        self.pause()
                    if data['event'] == 'resume':
                        self.resume()
                    if data['event'] == 'stop':
                        self.stop()

    def play(self, uri):
        print 'Playing {0}'.format(uri)
        track = self.session.get_track(uri).load()

        self.session.player.load(track)
        self.session.player.play()

    def pause(self):
        self.session.player.pause()

    def resume(self):
        if self.session.player.state == spotify.PlayerState.PAUSED:
            self.session.player.play()

    def stop(self):
        if self.session.player.state != spotify.PlayerState.UNLOADED:
            self.session.player.unload()

    def watch_playlist(self):
        print self.session.player.state
        if self.session.player.state == spotify.PlayerState.UNLOADED:
            print 'Watching playlist'
            while True:
                if self.redis.llen('playlist') > 0:
                    print 'Playlist not empty - stopped watching'
                    self.play(self.redis.lpop('playlist'))
                    return

    def on_connection_state_updated(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            print 'Logged In'
            self.logged_in.set()

            if self.redis.llen('playlist') > 0:
                self.play(self.redis.lpop('playlist'))
            else:
                print 'Playlist empty'
                self.watch_playlist()

    def on_end_of_track(self, *agrs, **kwargs):
        print 'End of Track'
        self.session.player.unload()
        if self.redis.llen('playlist') > 0:
            print 'playing next track'
            self.play(self.redis.lpop('playlist'))
        else:
            print 'Playlist empty'
            self.watch_playlist()


if __name__ == '__main__':
    try:
        Player()
    except KeyboardInterrupt:
        sys.exit()
