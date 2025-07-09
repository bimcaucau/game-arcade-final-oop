from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.core.audio import SoundLoader
import pymunk

from .ui import GameArea  # Use relative import
from .menu import MainMenu # Use relative import
from .editor import MapEditorScreen

class TankMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # MainMenu được khởi tạo với các hàm callback để điều khiển ScreenManager cha
        self.add_widget(MainMenu(
            start_game_callback=lambda: self.manager.switch_to_game('default_map.json'),
            start_custom_game_callback=lambda: self.manager.switch_to_game('custom_map.json'),
            open_editor_callback=lambda: setattr(self.manager, 'current', 'editor')
        ))

class TankGamePlayScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_area = GameArea()
        self.add_widget(self.game_area)

        self.notification_label = Label(
            text="", 
            font_size=48, 
            bold=True, 
            color=(1, 0, 0, 1),
            size_hint=(None, None), 
            size=(600, 100), # Đặt size trực tiếp ở đây
            halign='center',
            valign='middle', 
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            opacity=0
        )

        self.notification_label.text_size = self.notification_label.size
        self.add_widget(self.notification_label)

        # Liên kết GamePanel với màn hình này
        self.game_area.middle_panel.root_widget = self

    def start_game(self, map_filename):
        self.game_area.middle_panel.reset_game(map_filename)
        Clock.schedule_once(self.start_countdown, 0.5)

        
    def show_notification(self, text, duration=1.0, color=(1, 0, 0, 1)):
        self.notification_label.text = text
        self.notification_label.color = color
        Animation.cancel_all(self.notification_label)
        anim = Animation(opacity=1, duration=0.3)
        anim += Animation(opacity=1, duration=duration - 0.6)
        anim += Animation(opacity=0, duration=0.3)
        anim.start(self.notification_label)
    
    def start_countdown(self, dt):
        Clock.schedule_once(lambda dt: self.show_notification("Game will start in 3 seconds", 0.8), 0)
        Clock.schedule_once(lambda dt: self.show_notification("Game will start in 2 seconds", 0.8), 1)
        Clock.schedule_once(lambda dt: self.show_notification("Game will start in 1 second", 0.8), 2)
        Clock.schedule_once(lambda dt: self.show_notification("START!", 1, color=(0, 1, 0, 1)), 3)
        Clock.schedule_once(self.game_area.middle_panel.teleport_tanks_to_center, 4)
    
    def show_victory_screen(self, winner):
        # Tell the main app to show the screen, specifying the game type
        App.get_running_app().show_victory_screen(winner, 'tank')

    def update_scale(self, scale_factor):
        """Nhận tỉ lệ từ RootWidget và truyền xuống GameArea."""
        if hasattr(self, 'game_area'):
            self.game_area.set_scale(scale_factor)



class TankGameRootWidget(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.BASE_WINDOW_SIZE = (1280, 720) # Kích thước thiết kế chuẩn
        self.scale_factor = 1.0
        Window.bind(on_resize=self.on_window_resize)
        self.on_window_resize(Window, Window.width, Window.height) # Gọi lần đầu
      
        self.transition = FadeTransition(duration=0.2)

        # Tạo và thêm các màn hình con
        self.add_widget(TankMenuScreen(name='tank_menu'))
        self.game_play_screen = TankGamePlayScreen(name='tank_gameplay')
        self.add_widget(self.game_play_screen)
        
        # Màn hình Editor
        self.add_widget(MapEditorScreen(name='editor'))

        self.current = 'tank_menu'

    def switch_to_game(self, map_filename):
        # Khi bắt đầu game, cũng phải cập nhật tỉ lệ
        if hasattr(self, 'game_play_screen'):
            self.game_play_screen.update_scale(self.scale_factor)
        self.current = 'tank_gameplay'
        self.game_play_screen.start_game(map_filename)

    
    def on_window_resize(self, window, width, height):
        # Tính tỉ lệ dựa trên chiều rộng
        self.scale_factor = width / self.BASE_WINDOW_SIZE[0]
        print(f"Window resized. New scale factor: {self.scale_factor}")
        # Truyền tỉ lệ này xuống các thành phần con nếu cần
        if hasattr(self, 'game_play_screen'):
            self.game_play_screen.game_area.set_scale(self.scale_factor)

