# tank_game/victory.py (NEW REUSABLE VERSION)

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader
from kivy.app import App

class VictoryScreen(FloatLayout):
    """A generic victory screen that accepts assets as parameters."""
    
    def __init__(self, winner, restart_callback, image_source, sound_source, **kwargs):
        super(VictoryScreen, self).__init__(**kwargs)
        
        self.restart_callback = restart_callback
        
        # --- THE CHANGE: Use provided assets ---
        # The image and sound are now passed in when the screen is created.
        self.sound = SoundLoader.load(sound_source)
        if self.sound:
            self.sound.play()

        # UI setup
        with self.canvas.before:
            Color(0, 0, 0, 0.8); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.title = Label(
            text=f"PLAYER {winner} WINS!", font_size=72, bold=True, color=(1, 0.8, 0, 1),
            size_hint=(1, 0.2), pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        self.add_widget(self.title)
        
        self.winner_image = Image(
            source=image_source,
            size_hint=(0.7, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.winner_image)
        
        # Buttons layout
        button_layout = FloatLayout(size_hint=(1, 0.15), pos_hint={'center_x': 0.5, 'y': 0.05})
        play_again_btn = Button(
            text="PLAY AGAIN", font_size=30, bold=True,
            background_color=(0, 0.6, 0, 1), background_normal='',
            size_hint=(0.4, 0.8), pos_hint={'x': 0.05, 'center_y': 0.5}
        )
        play_again_btn.bind(on_press=self.on_play_again_pressed)
        main_menu_btn = Button(
            text="MAIN MENU", font_size=30, bold=True,
            background_color=(0.8, 0, 0, 1), background_normal='',
            size_hint=(0.4, 0.8), pos_hint={'right': 0.95, 'center_y': 0.5}
        )
        main_menu_btn.bind(on_press=self.on_main_menu_pressed)
        button_layout.add_widget(play_again_btn)
        button_layout.add_widget(main_menu_btn)
        self.add_widget(button_layout)
    
    def on_main_menu_pressed(self, instance):
        if self.sound: self.sound.stop()
        # Go back to the game selection screen in the main app
        App.get_running_app().root.current = 'game_select'

    def on_play_again_pressed(self, instance):
        if self.sound: self.sound.stop()
        if self.restart_callback: self.restart_callback()

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size