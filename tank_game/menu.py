from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle

class MainMenu(FloatLayout):
    """
    Game main menu with options to play, edit maps, and start the game.
    """
    def __init__(self, start_game_callback, start_custom_game_callback, open_editor_callback, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        
        # Store callback for starting the game
        self.start_game_callback = start_game_callback
        self.start_custom_game_callback = start_custom_game_callback
        self.open_editor_callback = open_editor_callback
        
        # Add background
        with self.canvas.before:
            Color(0.2, 0.2, 0.3, 1)  # Dark blue-gray
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Add game title
        self.title = Label(
            text="TANK BATTLE",
            font_size=72,
            bold=True,
            color=(1, 0.8, 0, 1),  # Gold
            size_hint=(1, 0.3),
            pos_hint={'center_x': 0.5, 'top': 0.9}
        )
        self.add_widget(self.title)
        
        # Add tank images
        self.tank1 = Image(
            source='assets/tank_r.png',
            size_hint=(0.2, 0.2),
            pos_hint={'center_x': 0.3, 'center_y': 0.6}
        )
        self.add_widget(self.tank1)
        
        self.tank2 = Image(
            source='assets/tank_b.png',
            size_hint=(0.2, 0.2),
            pos_hint={'center_x': 0.7, 'center_y': 0.6}
        )
        self.add_widget(self.tank2)
        
        # --- BỐ CỤC NÚT MỚI ---
        # Sử dụng BoxLayout để sắp xếp các nút một cách gọn gàng
        button_layout = BoxLayout(
            orientation='vertical',
            spacing=15,
            size_hint=(0.5, 0.35), # Tăng chiều cao để chứa 3 nút
            pos_hint={'center_x': 0.5, 'center_y': 0.3}
        )
        
        # Nút 1: Start Game (Chơi map mặc định)
        self.start_btn = Button(
            text="PLAY DEFAULT MAP",
            font_size=28,
            bold=True,
            background_color=(0.1, 0.7, 0.2, 1),  # Màu xanh lá cây
            background_normal=''
        )
        self.start_btn.bind(on_press=self.on_start_pressed)
        button_layout.add_widget(self.start_btn)

        # Nút 2: Start Custom Game (Chơi map tùy chỉnh)
        self.start_custom_btn = Button(
            text="PLAY CUSTOM MAP",
            font_size=28,
            bold=True,
            background_color=(0.1, 0.5, 0.8, 1),  # Màu xanh dương
            background_normal=''
        )
        self.start_custom_btn.bind(on_press=self.on_start_custom_pressed)
        button_layout.add_widget(self.start_custom_btn)

        # Nút 3: Map Editor
        self.editor_btn = Button(
            text="MAP EDITOR",
            font_size=28,
            bold=True,
            background_color=(0.8, 0.5, 0.1, 1),  # Màu cam
            background_normal=''
        )
        self.editor_btn.bind(on_press=self.on_editor_pressed)
        button_layout.add_widget(self.editor_btn)

        self.add_widget(button_layout)

        # Add controls info
        controls_text = (
            "Player 1: WASD to move, J to shoot\n"
            "Player 2: Arrow keys to move, period (.) to shoot"
        )
        self.controls = Label(
            text=controls_text,
            font_size=18,
            color=(0.8, 0.8, 0.8, 1),  # Light gray
            size_hint=(0.8, 0.1),
            pos_hint={'center_x': 0.5, 'center_y': 0.05}
        )
        self.add_widget(self.controls)
    
    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
    
    def on_start_pressed(self, instance):
        # Call the callback function to start the game
        if self.start_game_callback:
            self.start_game_callback()

    def on_start_custom_pressed(self, instance):
        # Gọi callback để bắt đầu game với map TÙY CHỈNH
        if self.start_custom_game_callback:
            self.start_custom_game_callback()

    def on_editor_pressed(self, instance):
        # Gọi callback để mở màn hình Editor
        if self.open_editor_callback:
            self.open_editor_callback()
