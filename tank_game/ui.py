from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label
from .game import GamePanel
class StatusPanel(BoxLayout):
    """Left and right panels for player status (light yellow)"""
    def __init__(self, tank=None, tank_image=None, **kwargs):
        super(StatusPanel, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.tank = tank
        self.tank_image = tank_image
        
        # Add light yellow background
        with self.canvas.before:
            Color(1, 1, 0.8, 1)  # Light yellow
            self.bg = Rectangle(pos=self.pos, size=self.size)
        
        # Update background when panel size changes
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Add top padding to shift everything down
        self.add_widget(Widget(size_hint_y=0.1))  # Top padding
        
        # Add tank image below the padding
        if self.tank_image:
            # Create an image with appropriate size (600x600 original)
            # Increase size by 25% (from 150 to 188)
            tank_img = Image(
                source=self.tank_image,
                size_hint=(None, None),
                size=(188, 188),  # 25% larger than before
                pos_hint={'center_x': 0.5}
            )
            self.add_widget(tank_img)
        
        # Add spacing between image and stats
        self.add_widget(Widget(size_hint_y=0.05))
        
        # Schedule updates if tank is provided
        if self.tank:
            self.update_status(0)  # Initial update
            Clock.schedule_interval(self.update_status, 1/10)
    
    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
    
    def update_status(self, dt):
        if self.tank:
            # Clear only status widgets, not the image
            # We'll use a container for status info
            if hasattr(self, 'status_container'):
                self.remove_widget(self.status_container)
            
            # Create container for status info
            self.status_container = BoxLayout(orientation='vertical', size_hint_y=0.5)
            
            # Display health info with red color
            health_label = Label(
                text=f"Health: {self.tank.health}/{self.tank.max_health}",
                font_size=24,
                color=(1, 0, 0, 1),  # Red
                bold=True,
                size_hint_y=0.5
            )
            self.status_container.add_widget(health_label)
            
            # Display ammo info with blue color
            ammo_label = Label(
                text=f"Ammo: {self.tank.ammo}/{self.tank.max_ammo}",
                font_size=24,
                color=(0, 0, 1, 1),  # Blue
                bold=True,
                size_hint_y=0.5
            )
            self.status_container.add_widget(ammo_label)
            
            # Add the status container to the panel
            self.add_widget(self.status_container)

class GameArea(BoxLayout):
    """Main layout of the game with three panels"""
    def __init__(self, **kwargs):
        super(GameArea, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        
        # Import GamePanel here to avoid circular imports

        # Create game panel first
        self.middle_panel = GamePanel(size_hint_x=0.5)
        
        # Create the status panels with references to tanks and tank images
        self.left_panel = StatusPanel(
            tank=self.middle_panel.tanks[0], 
            tank_image='assets/tank_r.png',
            size_hint_x=0.25
        )
        
        self.right_panel = StatusPanel(
            tank=self.middle_panel.tanks[1], 
            tank_image='assets/tank_b.png',
            size_hint_x=0.25
        )
        
        # Add panels to the layout
        self.add_widget(self.left_panel)
        self.add_widget(self.middle_panel)
        self.add_widget(self.right_panel)

    def set_scale(self, scale_factor):
        # Truyền tỉ lệ xuống cho GamePanel
        self.middle_panel.set_scale(scale_factor)