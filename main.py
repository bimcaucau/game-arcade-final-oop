import sys 
import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.resources import resource_add_path
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import StringProperty

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Add the resource paths for the assets
resource_add_path(resource_path('.'))
resource_add_path(resource_path('tank_game'))
resource_add_path(resource_path('pingpong_new'))
# Load the KV file for the main app
Builder.load_file('main.kv')

# --- Import Game Root Widgets ---
from tank_game.main import TankGameRootWidget
from pingpong_new.main import GameWidget as PongGameWidget
from tank_game.victory import VictoryScreen

# --- Define ALL Screens ---
class MasterMenuScreen(Screen): pass
class GameSelectScreen(Screen): pass
class HelpSelectScreen(Screen): pass

class HelpDisplayScreen(Screen):
    image_source = StringProperty('')

class TankGameScreen(Screen):
    def on_enter(self, *args):
        App.get_running_app().stop_menu_music()
        self.clear_widgets()
        self.add_widget(TankGameRootWidget())

    def on_leave(self, *args):
        for child in self.walk():
            if hasattr(child, 'sounds'):
                for sound in child.sounds.values():
                    if sound and sound.state == 'play': sound.stop()
            if hasattr(child, 'update'): Clock.unschedule(child.update)
        self.clear_widgets()

class PingPongScreen(Screen):
    def on_enter(self, *args):
        App.get_running_app().stop_menu_music()
        self.clear_widgets()
        self.add_widget(PongGameWidget())

    def on_leave(self, *args):
        for child in self.walk():
            if hasattr(child, 'update'): Clock.unschedule(child.update)
            if hasattr(child, 'music') and child.music: child.music.stop()
        self.clear_widgets()

# --- The Main App Class ---
class GameArcadeApp(App):
    def build(self):
        self.menu_music = None

        self.menu_music = SoundLoader.load('assets/menu_music.mp3')
        if self.menu_music:
            self.menu_music.loop = True
            self.menu_music.play()

        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(MasterMenuScreen(name='master_menu'))
        sm.add_widget(GameSelectScreen(name='game_select'))
        sm.add_widget(HelpSelectScreen(name='help_select'))
        sm.add_widget(HelpDisplayScreen(name='help_display'))
        sm.add_widget(TankGameScreen(name='tank_game_screen'))
        sm.add_widget(PingPongScreen(name='pingpong_screen'))

        Window.bind(on_key_down=self.on_global_key_down)
        
        return sm
        
    def play_menu_music(self):
        if self.menu_music and self.menu_music.state != 'play':
            self.menu_music.play()

    def stop_menu_music(self):
        if self.menu_music and self.menu_music.state == 'play':
            self.menu_music.stop()

    def go_to_main_menu(self):
        if self.root:
            current_screen = self.root.current_screen
            if hasattr(current_screen, 'on_leave'):
                 current_screen.dispatch('on_leave')
            self.root.current = 'master_menu'
            self.play_menu_music()
            
    def on_global_key_down(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            current_screen_name = self.root.current
            game_screens = ['tank_game_screen', 'pingpong_screen']
            if current_screen_name in game_screens:
                self.go_to_main_menu()
                return True
        return False

    def show_help_for(self, game_name):
        help_screen = self.root.get_screen('help_display')
        if game_name == 'tank':
            help_screen.image_source = 'assets/help_tank.png'
        elif game_name == 'pong':
            help_screen.image_source = 'assets/help_pong.png'
        self.root.current = 'help_display'

    def show_victory_screen(self, winner_number, game_type):
        current_game_screen = self.root.current_screen
        if game_type == 'tank':
            image_source = f"assets/xxxtentacion.png" if winner_number == 1 else f"assets/kingvon.png"
            sound_source = f"sounds/xxxtentacion.mp3" if winner_number == 1 else f"sounds/kingvon.mp3"
        elif game_type == 'pong':
            image_source = f"assets/pong_winner{winner_number}.png"
            sound_source = f"sounds/pong_winner{winner_number}.mp3"
        else: image_source, sound_source = "", ""
        victory_widget = VictoryScreen(
            winner=winner_number,
            restart_callback=lambda: self.restart_game(current_game_screen),
            image_source=image_source, sound_source=sound_source)
        current_game_screen.add_widget(victory_widget)
        
    def restart_game(self, screen_instance):
        screen_instance.dispatch('on_leave'); screen_instance.dispatch('on_enter')

if __name__ == '__main__':
    GameArcadeApp().run()