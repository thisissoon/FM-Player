import os
import spotify
import sys
import threading


class Player(object):

    def __init__(self):
        self.config = spotify.Config()
        self.config.load_application_key_file(
            os.environ.get('SPOTIFY_APP_KEY'))
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

        self.logged_in = threading.Event()
        self.end_of_track = threading.Event()
        self.logged_in.wait()

    def play(self, uri):
        print 'playing'
        track = self.session.get_track(uri).load()

        self.session.player.load(track)
        self.session.player.play()

        while not self.end_of_track.wait(0.1):
            pass

    def on_connection_state_updated(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            print 'Logged In'
            self.logged_in.set()

    def on_end_of_track(self):
        print 'End of Track'
        self.end_of_track.set()


if __name__ == '__main__':
    try:
        player = Player()
        player.play('spotify:track:6xZtSE6xaBxmRozKA0F6TA')
    except KeyboardInterrupt:
        sys.exit()
