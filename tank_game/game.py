import pymunk
import json
import math
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Rectangle, Line, Color
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
import itertools
from .items import spawn_item, setup_item_collision_handler, update_active_items, COLLISION_TYPE_ITEM
from .items import log_debug
from .items import ITEM_SIZE 

def load_game_sounds():
    """Load and return all game sounds"""
    sounds = {}
    
    # Load item collection sounds
    sounds['shield'] = SoundLoader.load('sounds/shield_me.mp3')
    sounds['speedup'] = SoundLoader.load('sounds/fast_af_boi.mp3')
    sounds['billie_shot'] = SoundLoader.load('sounds/billie_eilish.mp3')
    
    # Load background music
    sounds['background'] = SoundLoader.load('sounds/bg_music.mp3')
    if sounds['background']:
        sounds['background'].loop = True  # Enable looping
    

    # Error handling - check if sounds loaded properly
    for name, sound in sounds.items():
        if sound is None:
            print(f"WARNING: Failed to load sound: {name}")
    
    return sounds

# --- Bullet Class ---
class Bullet(Widget):
    _ids = itertools.count(0)  
    
    def __init__(self, owner, pos, angle, speed, radius, space, enhanced=False, **kwargs):
        super().__init__(**kwargs)
        self.owner = owner
        self.radius = radius
        self.speed = speed
        self.bounce_count = 0
        self.max_bounce = 4
        self.id = next(Bullet._ids)
        self.size = (radius*2, radius*2)
        self.center = pos
        self.angle = angle
        self.enhanced = enhanced  # Store enhanced state in the bullet object
        
        # Pymunk body and shape
        mass = 1
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.body = pymunk.Body(mass, moment)
        self.body.position = pos
        direction = [math.sin(math.radians(angle)), math.cos(math.radians(angle))]
        self.body.velocity = (direction[0]*speed, direction[1]*speed)
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.collision_type = 3  # Bullet collision type
        self.shape.filter = pymunk.ShapeFilter(categories=0b10, mask=0b1)  # Collide with tanks/walls, not other bullets
        self.shape.bullet_id = self.id
        self.shape.bullet_owner = owner
        self.shape.enhanced = enhanced  # Store enhanced status in shape for collision handling
        self.shape.elasticity = 0.0
        self.shape.friction = 0.0
        space.add(self.body, self.shape)

        # Choose the appropriate bullet image
        bullet_image = "assets/bullet_billie.png" if enhanced else "assets/bullet.png"

        # Kivy image
        with self.canvas:
            self.img = Rectangle(source=bullet_image, size=self.size, pos=(self.center_x-radius, self.center_y-radius))
        self.bind(pos=self.update_graphics, size=self.update_graphics, center=self.update_graphics)

    def update_graphics(self, *args):
        self.size = (self.radius*2, self.radius*2)
        self.img.size = self.size
        self.img.pos = (self.center_x - self.radius, self.center_y - self.radius)

    def update(self):
        self.center = self.body.position

    def destroy(self, space):
        space.remove(self.body, self.shape)
        if self.parent:
            self.parent.remove_widget(self)

class Tank(Widget):
    def __init__(self, source, controller, space=None, **kwargs):
        super().__init__(**kwargs)
        self.opacity = 0  # Start invisible
        self.controller = controller
        self.move_speed = 60  # pixels per second
        self.rotate_speed = 90  # degrees per second
        self.angle = 0  # 0 degrees is north (up)
        self.direction = [0, 1]  # Facing north (up)
        self.center_pos = [0, 0]
        self.moving_forward = False
        self.moving_backward = False
        self.rotating_left = False
        self.rotating_right = False
        self.size = (32, 32)
        self.source = source
        self.shield_active = False
        self.shield_expire_time = None
        self.speedup_expire_time = None
        self.active_items = {}
        self.original_speed = self.move_speed
        self.billie_bullet_active = False
        self.space = space

        self.BASE_SIZE = (32, 32)
        self.BASE_MOVE_SPEED = 60
        self.BASE_ROTATE_SPEED = 90
        self.scale_factor = 1.0

        # --- Pymunk body and shape ---
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.body.position = (0, 0)
        # Circle hitbox
        radius = self.BASE_SIZE[0] / 2 # Default 32x32 tank, so radius is 16
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.sensor = False
        self.shape.collision_type = 1
        self.shape.filter = pymunk.ShapeFilter(categories=0b0001, mask=0b1111)  # Collide with everything
        self.shape.tank = self  # Reference back to the tank object
        if space is not None:
            space.add(self.body, self.shape)

        with self.canvas:
            self.push = PushMatrix()
            self.rot = Rotate(angle=0, origin=self.center)
            self.rect = Rectangle(source=self.source, size=(32, 32), pos=self.pos)
            self.pop = PopMatrix()
        self.bind(pos=self.update_graphics, size=self.update_graphics, center=self.update_graphics)

        # Health system
        self.max_health = 3
        self.health = self.max_health
        
        # Ammo and cooldown system
        self.max_ammo = 3
        self.ammo = self.max_ammo
        self.can_shoot = True
        self.cooldown_timer = 0
        self.cooldown_duration = 1.0  # 1 second between shots
        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 2.0  # 2 seconds to reload

        self.update_scale(1.0) # Khởi tạo với tỉ lệ 1

    def update_scale(self, scale_factor):
        self.scale_factor = scale_factor
        # Cập nhật kích thước đồ họa Kivy
        new_size = (self.BASE_SIZE[0] * scale_factor, self.BASE_SIZE[1] * scale_factor)
        self.size = new_size

        self.move_speed = self.BASE_MOVE_SPEED * scale_factor
        self.rotate_speed = self.BASE_ROTATE_SPEED # Tốc độ xoay có thể giữ nguyên
       
        # --- LOGIC "THÁO RA, LẮP MỚI" ---
        # Chỉ thực hiện nếu shape và space đã tồn tại
        if hasattr(self, 'shape') and self.shape in self.space.shapes:
            # 1. Tháo shape cũ ra khỏi space
            self.space.remove(self.shape)

            # 2. Tạo shape mới với bán kính đã được scale
            new_radius = new_size[0] / 2
            new_shape = pymunk.Circle(self.body, new_radius)

            # 3. SAO CHÉP TẤT CẢ các thuộc tính quan trọng từ shape cũ sang shape mới
            new_shape.sensor = self.shape.sensor
            new_shape.collision_type = self.shape.collision_type
            new_shape.filter = self.shape.filter
            new_shape.elasticity = self.shape.elasticity
            new_shape.friction = self.shape.friction
            new_shape.tank = self # Đừng quên tham chiếu ngược này!

            # 4. Lắp shape mới vào space
            self.space.add(new_shape)

            # 5. Cập nhật lại tham chiếu shape của Tank
            self.shape = new_shape

    def update_graphics(self, *args):
        self.size = (32, 32)
        self.rect.size = (32, 32)
        self.rect.pos = (self.center_x - 16, self.center_y - 16)
        self.rot.origin = self.center

    def update(self, dt, map_center, map_size, space=None, collision_enabled=True):
        # Handle rotation
        if self.rotating_left:
            self.angle -= self.rotate_speed * dt
        if self.rotating_right:
            self.angle += self.rotate_speed * dt
        self.angle %= 360

        # Update direction vector based on angle
        rad = math.radians(self.angle)
        self.direction = [math.sin(rad), math.cos(rad)]  # y axis up

        # Calculate intended move
        move = 0
        if self.moving_forward:
            move += self.move_speed * dt
        if self.moving_backward:
            move -= self.move_speed * dt

        # Predict new position
        new_pos = self.center_pos[:]
        if move != 0:
            new_pos[0] += self.direction[0] * move
            new_pos[1] += self.direction[1] * move

        # Clamp to map bounds
        map_half_w = map_size[0] / 2
        map_half_h = map_size[1] / 2
        min_x = map_center[0] - map_half_w + self.width / 2
        max_x = map_center[0] + map_half_w - self.width / 2
        min_y = map_center[1] - map_half_h + self.height / 2
        max_y = map_center[1] + map_half_h - self.height / 2
        new_pos[0] = max(min_x, min(max_x, new_pos[0]))
        new_pos[1] = max(min_y, min(max_y, new_pos[1]))

        # --- Collision check ---
        can_move = True
        if space is not None and move != 0 and collision_enabled:
            # Temporarily move the shape to the new position and check for collisions
            old_pos = self.body.position
            old_angle = self.body.angle
            self.body.position = new_pos
            self.body.angle = -math.radians(self.angle)
            collisions = space.shape_query(self.shape)
            self.body.position = old_pos
            self.body.angle = old_angle
            # if collisions:
            #     can_move = False
            blocking_collisions = False
            for collision in collisions:
                if not collision.shape.sensor:
                    blocking_collisions = True
                    break
            
            if blocking_collisions:
                can_move = False

        # Only move if no collision
        if can_move:
            self.center_pos = new_pos

        # --- Sync Kivy and Pymunk ---
        self.center = self.center_pos
        self.rot.angle = -self.angle
        self.rot.origin = self.center
        self.body.position = self.center_pos
        self.body.angle = -math.radians(self.angle)

        # Update cooldown and reload timers
        if not self.can_shoot:
            self.cooldown_timer += dt
            if self.cooldown_timer >= self.cooldown_duration:
                self.cooldown_timer = 0
                self.can_shoot = True
        
        if self.is_reloading:
            self.reload_timer += dt
            if self.reload_timer >= self.reload_duration:
                self.reload_timer = 0
                self.is_reloading = False
                self.ammo = self.max_ammo
                print(f"Tank {self.source} reloaded! Ammo: {self.ammo}")

class GamePanel(FloatLayout):
    """Middle panel where the game occurs"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale_factor = 1.0

        self.bullets = []
        self.bullets_by_shape = {}
        self.tanks = []
        self.items = []
        self.item_spawn_timer = -5  # Start negative to delay first spawn
        self.item_spawn_interval = 5  # seconds
        self.status_panel = {}
        with self.canvas.before:
            Color(1, 1, 0, 1)  # Yellow
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.is_on_custom_map = False # Mặc định là không phải map tùy chỉnh

        self.map_image = Image(
            source='assets/map.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.map_image)

        # Tạo một Widget trống để vẽ bản đồ tùy chỉnh LÊN TRÊN map_image
        self.custom_map_drawer = Widget()
        self.add_widget(self.custom_map_drawer)

        # --- Pymunk space ---
        self.space = pymunk.Space()
        #self.log_debug(f"Space type:, {type(self.space)}")
        self.setup_bullet_collision()
        setup_item_collision_handler(self.space, self)

        self.space.gravity = (0, 0)

        self.wall_shapes = []
        self.wall_thickness = 11  # Reduced from 11

        # Tank 1: WASD
        tank1 = Tank(
            source='assets/tank_r.png',
            controller={
                'forward': 'w',
                'backward': 's',
                'left': 'a',
                'right': 'd'
            },
            space=self.space
        )
        self.tanks.append(tank1)
        self.add_widget(tank1)

        # Tank 2: Arrow keys
        tank2 = Tank(
            source='assets/tank_b.png',
            controller={
                'forward': 'up',
                'backward': 'down',
                'left': 'left',
                'right': 'right'
            },
            space=self.space
        )
        self.tanks.append(tank2)
        self.add_widget(tank2)

        self.bind(size=self.update_map)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)

        self.tanks_enabled = False  # Movement disabled at start
        self.collision_enabled = False  # Add this line

        # Schedule teleport after 3 seconds
        # Clock.schedule_once(self.teleport_tanks_to_center, 6)
        self.sounds = load_game_sounds()
        if hasattr(self, "sounds") and "background" in self.sounds:
            if self.sounds["background"].state != 'play':
                self.sounds["background"].play()
                print("Background music continued")

        # self.game_loop_event = None
        Clock.schedule_interval(self.update, 1/60)

        # self.bind(size=self.update_custom_map_graphics, pos=self.update_custom_map_graphics)

    def set_scale(self, scale_factor):
        self.scale_factor = scale_factor
        # Cập nhật kích thước và tốc độ cho các xe tăng hiện có
        for tank in self.tanks:
            tank.update_scale(self.scale_factor)
        # Cập nhật cho TẤT CẢ các vật phẩm
        for item in self.items:
            # Giả sử Item có hàm update_scale tương tự Tank
            item.update_scale(scale_factor)

    def spawn_new_item(self):
        """Spawn a new item on the map"""
        #log_debug("\n--- Attempting to spawn item ---")
        if not self.tanks_enabled:
            #log_debug("Tanks not enabled, skipping item spawn")
            return

        # Get map dimensions
        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        map_rect = (map_x, map_y, map_w, map_h)
        
        # Get obstacle shapes
        obstacles = self.wall_shapes
        
        # Spawn the item
        new_item = spawn_item(self.space, map_rect, obstacles, self.tanks)
        if new_item:
            self.items.append(new_item)
            self.add_widget(new_item)

    # def create_walls(self):
    def load_map_from_file(self, map_filename):
        # Remove old walls if they exist
        for wall in self.wall_shapes:
            self.space.remove(wall)
        self.wall_shapes.clear()
        self.custom_map_drawer.canvas.clear() # Xóa sạch mọi thứ đã vẽ trước đó

        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        
        border_thickness = self.wall_thickness 

        # Walls at the very edge of the map
        walls = [
            # Left
            ((map_x, map_y), (map_x, map_y + map_h)),
            # Right
            ((map_x + map_w, map_y), (map_x + map_w, map_y + map_h)),
            # Bottom
            ((map_x, map_y), (map_x + map_w, map_y)),
            # Top
            ((map_x, map_y + map_h), (map_x + map_w, map_y + map_h)),
        ]
        for a, b in walls:
            seg = pymunk.Segment(self.space.static_body, a, b, self.wall_thickness / 2)
            seg.sensor = False  # Enable collision
            seg.collision_type = 2
            self.space.add(seg)
            self.wall_shapes.append(seg)

        # --- KIỂM TRA ĐỂ VẼ NỀN VÀ VẬT THỂ ---
        # Nếu đây là bản đồ tùy chỉnh, chúng ta sẽ vẽ
        self.is_on_custom_map = "custom" in map_filename

        # Nếu là map tùy chỉnh, làm cho ảnh nền cũ vô hình
        if self.is_on_custom_map:
            self.map_image.opacity = 0
        else: # Nếu là map mặc định, hiện lại ảnh nền
            self.map_image.opacity = 1

        with self.custom_map_drawer.canvas:
            # 1. Vẽ nền trắng nếu là bản đồ tùy chỉnh
            if self.is_on_custom_map:
                Color(1, 1, 1, 1) # Màu trắng
                # Lấy kích thước và vị trí của map_image để vẽ nền cho đúng
                self.custom_map_bg = Rectangle(pos=self.map_image.pos, size=self.map_image.size)
                Color(0, 0, 0, 1) # Đen
                self.custom_map_border = Line(
                    rectangle=(self.map_image.x, self.map_image.y, 
                    self.map_image.width, self.map_image.height), 
                    width=2
                )
                spawn_zones_logic = [
                    (200, 520, 200, 80),  # Đỏ dưới
                    (200, 0, 200, 80),    # Xanh trên
                ]
                # Hàm trợ giúp để chuyển đổi (có thể đưa nó ra ngoài nếu dùng nhiều lần)
                def logic_rect_to_phys(logic_rect):
                    map_w, map_h = self.map_image.size
                    map_x, map_y = self.map_image.pos
                    scale_x = map_w / 600.0
                    scale_y = map_h / 600.0
                    
                    lx, ly, lw, lh = logic_rect
                    px = map_x + lx * scale_x
                    py = map_y + map_h - (ly * scale_y) - (lh * scale_y) # Dưới-trái
                    pw = lw * scale_x
                    ph = lh * scale_y
                    return (px, py, pw, ph)
                # Vẽ vùng màu đỏ
                rect_r = logic_rect_to_phys(spawn_zones_logic[0])
                Color(1, 0, 0, 0.2) # Đỏ, trong suốt hơn một chút
                Rectangle(pos=(rect_r[0], rect_r[1]), size=(rect_r[2], rect_r[3]))
                Color(0, 0, 0, 1) # Viền đen
                Line(rectangle=rect_r, width=2)
                
                # Vẽ vùng màu xanh
                rect_b = logic_rect_to_phys(spawn_zones_logic[1])
                Color(0, 0, 1, 0.2) # Xanh, trong suốt
                Rectangle(pos=(rect_b[0], rect_b[1]), size=(rect_b[2], rect_b[3]))
                Color(0, 0, 0, 1) # Viền đen
                Line(rectangle=rect_b, width=2)              

            # --- BƯỚC 3: ĐỌC VÀ XỬ LÝ FILE JSON ---
            # Tải dữ liệu các chướng ngại vật từ file
            try:
                with open(map_filename, 'r') as f:
                    map_data = json.load(f)
            except FileNotFoundError:
                print(f"WARNING: Map file '{map_filename}' not found. Loading an empty map.")
                map_data = [] # Nếu không tìm thấy file, tạo một danh sách rỗng
            except json.JSONDecodeError:
                print(f"ERROR: Map file '{map_filename}' is not a valid JSON. Loading an empty map.")
                map_data = [] # Nếu file JSON bị lỗi, tạo một danh sách rỗng

            def to_pymunk_coords(orig_x, orig_y):
                scaled_x = orig_x * (map_w / 600)
                scaled_y = orig_y * (map_h / 600)
                return (map_x + scaled_x, map_y + (map_h - scaled_y))

            # Lặp qua từng đối tượng chướng ngại vật trong dữ liệu đã đọc
            for obj_data in map_data:
                # Lấy các thông số từ đối tượng JSON
                logic_x1 = obj_data.get('x', 0)
                logic_y1 = obj_data.get('y', 0)
                logic_w = obj_data.get('width', 0)
                logic_h = obj_data.get('height', 0)
                
                # Tính tọa độ của góc dưới-phải trong hệ logic
                logic_x2 = logic_x1 + logic_w
                logic_y2 = logic_y1 + logic_h
                
                # Tạo danh sách 4 đỉnh của hình chữ nhật bằng cách chuyển đổi từng điểm
                # theo thứ tự: trên-trái, trên-phải, dưới-phải, dưới-trái
                # Đây là thứ tự mà Pymunk yêu cầu để tính toán đúng
                verts = [
                    to_pymunk_coords(logic_x1, logic_y1), # Trên-trái
                    to_pymunk_coords(logic_x2, logic_y1), # Trên-phải
                    to_pymunk_coords(logic_x2, logic_y2), # Dưới-phải
                    to_pymunk_coords(logic_x1, logic_y2)  # Dưới-trái
                ]
                
                # Tạo một vật thể đa giác (polygon) tĩnh
                poly = pymunk.Poly(self.space.static_body, verts)
                poly.sensor = False
                poly.collision_type = 2 # Gán loại va chạm là "tường"
                
                # Thêm vào không gian vật lý và danh sách quản lý
                self.space.add(poly)
                self.wall_shapes.append(poly)
            
                # --- BÂY GIỜ, VẼ VẬT THỂ ĐỒ HỌA ---
                # Chúng ta chỉ vẽ đồ họa cho các vật thể nếu là map tùy chỉnh
                # (vì map mặc định đã có sẵn hình ảnh)
                if self.is_on_custom_map:
                    # Lấy tọa độ và kích thước từ các đỉnh đã được chuyển đổi
                    # để đảm bảo đồ họa khớp chính xác với vật lý
                    verts = poly.get_vertices()
                    
                    # Tìm điểm dưới-trái (min_x, min_y) và kích thước
                    min_x = min(v.x for v in verts)
                    min_y = min(v.y for v in verts)
                    max_x = max(v.x for v in verts)
                    max_y = max(v.y for v in verts)
                    
                    width = max_x - min_x
                    height = max_y - min_y

                    Color(0.5, 0.5, 0.5, 1) # Màu xám cho vật thể
                    Rectangle(pos=(min_x, min_y), size=(width, height))
                    
                    # Vẽ viền đen cho vật thể
                    Color(0, 0, 0, 1) # Đen
                    Line(rectangle=(min_x, min_y, width, height), width=2)

        with self.custom_map_drawer.canvas:
            Color(1, 1, 1, 1) # Trả lại bút màu trắng (màu trung tính)

        print(f"Map loading complete. Total wall objects: {len(self.wall_shapes)}")

    def teleport_tanks_to_center(self, dt):
        """Teleport tanks to start positions"""
        self._teleport_scheduled = False
        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        border_thickness = self.wall_thickness
        # Tính toán offset dựa trên tỉ lệ
        tank_radius = (16 * self.scale_factor)

        # Một khoảng đệm nhỏ để xe tăng không bị "dính" vào tường
        padding = 5 * self.scale_factor
        # Tổng khoảng cách an toàn từ mép bản đồ
        tank_offset = border_thickness + tank_radius + padding


        # Bottom-middle for tank 1
        tank1_x = map_x + map_w / 2
        tank1_y = map_y + tank_offset
        self.tanks[0].center_pos = [tank1_x, tank1_y]
        self.tanks[0].angle = 0
        self.tanks[0].opacity = 1  # Make tank visible
        
        # Top-middle for tank 2
        tank2_x = map_x + map_w / 2
        tank2_y = map_y + map_h - tank_offset
        self.tanks[1].center_pos = [tank2_x, tank2_y]
        self.tanks[1].angle = 180
        self.tanks[1].opacity = 1  # Make tank visible

        for tank in self.tanks:
            tank.center = tank.center_pos
            tank.body.position = tank.center_pos
            # Cập nhật lại scale lần cuối để đảm bảo kích thước vật lý khớp
            tank.update_scale(self.scale_factor)


        # NOW enable tanks and collisions (after countdown)
        self.tanks_enabled = True
        self.collision_enabled = True

        # Now create the walls (after tanks are in place)
        self.load_map_from_file(self.current_map_filename)
        # self.create_walls()

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def update_map(self, *args):
        width = self.width
        height = width
        if height > self.height:
            height = self.height
            width = height
        pos_x = (self.width - width) / 2
        pos_y = (self.height - height) / 2

        self.map_image.size = (width, height)
        self.map_image.pos = (pos_x, pos_y)

        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        border = self.wall_thickness

        # Remove old walls if they exist
        for wall in self.wall_shapes:
            self.space.remove(wall)
        self.wall_shapes.clear()

        # Walls at the very edge of the map
        walls = [
            # Left
            ((map_x, map_y), (map_x, map_y + map_h)),
            # Right
            ((map_x + map_w, map_y), (map_x + map_w, map_y + map_h)),
            # Bottom
            ((map_x, map_y), (map_x + map_w, map_y)),
            # Top
            ((map_x, map_y + map_h), (map_x + map_w, map_y + map_h)),
        ]
        for a, b in walls:
            seg = pymunk.Segment(self.space.static_body, a, b, border / 2)
            seg.sensor = False  # Enable collision
            seg.collision_type = 2
            self.space.add(seg)
            self.wall_shapes.append(seg)

        # Center all tanks on the map (if not moved yet)
        map_center = [
            self.map_image.x + self.map_image.width / 2,
            self.map_image.y + self.map_image.height / 2
        ]
        for tank in self.tanks:
            if tank.center_pos == [0, 0] or tank.center_pos == [self.width/2, self.height/2]:
                tank.center_pos = map_center[:]
            tank.center = tank.center_pos
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard.unbind(on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]

        print(f"Key pressed: {key}")  # Debug print

        if self.tanks_enabled:
            # Handle tank movement
            for tank in self.tanks:
                ctrl = tank.controller
                if key == ctrl['forward']:
                    tank.moving_forward = True
                elif key == ctrl['backward']:
                    tank.moving_backward = True
                elif key == ctrl['left']:
                    tank.rotating_left = True
                elif key == ctrl['right']:
                    tank.rotating_right = True

            # Add shooting keys:
            if key == 'j':
                print("Tank 1 shoots!")  # Debug print
                self.shoot_bullet(self.tanks[0])
            elif key == '.':
                print("Tank 2 shoots!")  # Debug print
                self.shoot_bullet(self.tanks[1])
        return True

    def _on_key_up(self, keyboard, keycode):
        if not self.tanks_enabled:
            return True
        key = keycode[1]
        for tank in self.tanks:
            ctrl = tank.controller
            if key == ctrl['forward']:
                tank.moving_forward = False
            elif key == ctrl['backward']:
                tank.moving_backward = False
            elif key == ctrl['left']:
                tank.rotating_left = False
            elif key == ctrl['right']:
                tank.rotating_right = False
        return True

    def draw_debug(self):
        self.canvas.after.clear()
        # Draw tank collision circles
        for tank in self.tanks:
            with self.canvas.after:
                Color(0, 1, 0, 0.5)
                Line(circle=(tank.center_pos[0], tank.center_pos[1], 16), width=2)
        # Draw wall shapes
        for wall in self.wall_shapes:
            with self.canvas.after:
                Color(1, 0, 0, 0.7)
                if isinstance(wall, pymunk.Poly):
                    pts = [p for v in wall.get_vertices() for p in (v.x, v.y)]
                    pts += pts[:2]  # close the rectangle
                    Line(points=pts, width=2)
                elif isinstance(wall, pymunk.Segment):
                    a = wall.a
                    b = wall.b
                    Line(points=[a[0], a[1], b[0], b[1]], width=wall.radius * 2)
                elif isinstance(wall, pymunk.Circle):
                    center = wall.offset
                    Line(circle=(center[0], center[1], wall.radius), width=2)

    def update(self, dt):
        map_center = [self.map_image.x + self.map_image.width / 2,
                      self.map_image.y + self.map_image.height / 2]
        map_size = self.map_image.size # Lấy kích thước động
        for tank in self.tanks:
            tank.update(dt, map_center, map_size, space=self.space, collision_enabled=self.collision_enabled)
        for bullet in self.bullets[:]:
            bullet.update()
        self.space.step(dt)  # Step the physics
        #self.check_item_collection()
        self.item_spawn_timer += dt
        if self.item_spawn_timer >= self.item_spawn_interval and len(self.items) <= 6:
            self.item_spawn_timer = 0
            self.spawn_new_item()

        # Update active items
        for tank in self.tanks:
            update_active_items(tank, self)
        #self.draw_debug()

    def clear_all_items(self):
        """Remove all items from the game"""
        for item in self.items[:]:
            if hasattr(item, "body") and hasattr(item, "shape"):
                self.space.remove(item.body, item.shape)
            item.destroy()
        self.items.clear()
        
        # Clear all status panels
        if hasattr(self, 'parent'):
            for panel in [self.parent.left_panel, self.parent.right_panel]:
                if hasattr(panel, 'active_items'):
                    for item_type in list(panel.active_items.keys()):
                        icon = panel.active_items[item_type]
                        if hasattr(panel, 'items_container'):
                            panel.items_container.remove_widget(icon)
                    panel.active_items.clear()

    # Add this method to the GamePanel class
    def check_item_collection(self):
        """Manual item collection check for debugging"""
        for tank in self.tanks:
            for item in self.items[:]:
                # Calculate distance between tank and item centers
                tank_x, tank_y = tank.center
                item_x = item.pos[0] + item.size[0]/2
                item_y = item.pos[1] + item.size[1]/2
                
                # Debug log the positions
                #log_debug(f"Tank at {tank_x}, {tank_y}, Item at {item_x}, {item_y}")
                
                dist = ((tank_x - item_x)**2 + (tank_y - item_y)**2)**0.5
                #log_debug(f"Distance: {dist}")
                
                # Check if close enough for collection (adjust radius as needed)
                if dist < 25:  # Collection radius
                    #log_debug(f"COLLECTING ITEM")
                    # Mark as collected
                    item.collected = True
                    
                    # Remove from game
                    self.items.remove(item)
                    
                    # Remove physics body
                    if hasattr(item, "body") and hasattr(item, "shape"):
                        self.space.remove(item.body, item.shape)
                    
                    # Remove widget
                    item.destroy()
                    
                    print(f"Item collected by tank!")

    def setup_bullet_collision(self):
        def bullet_wall(arbiter, space, data):
            bullet_shape = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 3 else arbiter.shapes[1]
            bullet = self.bullets_by_shape.get(bullet_shape)
            if bullet:
                #self.log_debug(f"DEBUG: Bullet {bullet.id} hit a wall (bounce {bullet.bounce_count + 1})")
                bullet.bounce_count += 1
                if bullet.bounce_count > bullet.max_bounce:
                    bullet.destroy(self.space)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    if bullet_shape in self.bullets_by_shape:
                        del self.bullets_by_shape[bullet_shape]
                else:
                    normal = arbiter.contact_point_set.normal
                    vx, vy = bullet.body.velocity
                    speed = bullet.speed
                    dot = vx * normal.x + vy * normal.y
                    rvx = vx - 2 * dot * normal.x
                    rvy = vy - 2 * dot * normal.y
                    norm = math.hypot(rvx, rvy)
                    if norm != 0:
                        bullet.body.velocity = (rvx / norm * speed, rvy / norm * speed)
            return False

        def bullet_tank(arbiter, space, data):
            bullet_shape = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 3 else arbiter.shapes[1]
            tank_shape = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 1 else arbiter.shapes[1]
            bullet = self.bullets_by_shape.get(bullet_shape)
            
            # Find which tank was hit
            hit_tank = None
            hit_tank_index = -1
            for i, tank in enumerate(self.tanks):
                if tank.shape == tank_shape:
                    hit_tank = tank
                    hit_tank_index = i
                    break
            
            if bullet and hit_tank:
                # Check if bullet is enhanced (Billie Eilish power)
                is_enhanced = hasattr(bullet, 'enhanced') and bullet.enhanced
                
                # Check if tank has shield and bullet is NOT enhanced
                if (hasattr(hit_tank, 'shield_active') and hit_tank.shield_active and not is_enhanced):
                    print(f"Tank shielded from bullet!")
                    
                    # Remove shield effect
                    if hasattr(hit_tank, 'active_items') and 'shield' in hit_tank.active_items:
                        item = hit_tank.active_items['shield']
                        item.remove_effect(hit_tank)
                        self.remove_item_from_status_panel(hit_tank, 'shield')
                        del hit_tank.active_items['shield']
                    
                    # Destroy bullet
                    bullet.destroy(self.space)
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    if bullet_shape in self.bullets_by_shape:
                        del self.bullets_by_shape[bullet_shape]
                        
                    return False  # No damage taken
                
                # If bullet is enhanced, print a special message
                if is_enhanced:
                    print(f"ENHANCED BULLET HIT: Billie Eilish power penetrates shield!")
                
                # Reduce tank health
                hit_tank.health -= 1
                print(f"Tank hit! Health reduced to {hit_tank.health}")
                
                # Stop all tank movement immediately
                self.stop_all_tank_movement()
                
                # Disable tanks during restart
                self.tanks_enabled = False
                self.collision_enabled = False
                
                # Destroy bullet
                bullet.destroy(self.space)
                if bullet in self.bullets:
                    self.bullets.remove(bullet)
                if bullet_shape in self.bullets_by_shape:
                    del self.bullets_by_shape[bullet_shape]
                
                # If tank still has health, schedule restart
                if hit_tank.health > 0:
                    # Clear all bullets
                    self.clear_all_bullets()
                    
                    # Schedule restart after 3 seconds
                    Clock.schedule_once(self.restart_game, 3)
                else:
                    # Game over - tank is destroyed
                    print(f"Tank destroyed! Game over!")

                    # Stop background music
                    if hasattr(self, "sounds") and "background" in self.sounds:
                        self.sounds["background"].stop()
                        print("Background music stopped")
                    
                    # Determine winner (opposite of hit tank)
                    winner = 1 if hit_tank_index == 1 else 2
                    
                    # Show victory screen
                    if self.root_widget:
                        self.root_widget.show_victory_screen(winner)
        
            return False
        
        handler1 = self.space.add_collision_handler(3, 2)
        handler1.begin = bullet_wall
        handler2 = self.space.add_collision_handler(3, 1)
        handler2.begin = bullet_tank

# Replace or update the existing shoot_bullet method

    def shoot_bullet(self, tank):
        # Check if tank can shoot
        if not tank.can_shoot or tank.ammo <= 0:
            if tank.ammo <= 0 and not tank.is_reloading:
                print(f"Tank out of ammo! Reloading...")
                tank.is_reloading = True
                tank.reload_timer = 0
            elif not tank.can_shoot:
                print(f"Tank on cooldown! {tank.cooldown_timer:.1f}s left")
            return
        
        # Tank can shoot, reduce ammo and start cooldown
        tank.ammo -= 1
        tank.can_shoot = False
        tank.cooldown_timer = 0
        
        print(f"Tank shoots! Ammo remaining: {tank.ammo}")
        
        # Check for Billie Eilish bullet enhancement
        is_enhanced = False
        if hasattr(tank, "billie_bullet_active") and tank.billie_bullet_active:
            is_enhanced = True
            print(f"ENHANCED BULLET: Billie Eilish power activated!")
            # Play Billie Eilish sound
            if hasattr(self, "sounds") and "billie_shot" in self.sounds:
                self.sounds["billie_shot"].play()
                log_debug("Playing Billie Eilish sound")
            # Remove the effect after use
            tank.billie_bullet_active = False
            
            # Remove from status panel and active items
            if hasattr(tank, "active_items") and "billie" in tank.active_items:
                item = tank.active_items["billie"]
                item.remove_effect(tank)
                self.remove_item_from_status_panel(tank, "billie")
                del tank.active_items["billie"]
        
        scale = tank.scale_factor # Lấy tỉ lệ từ xe tăng

        # Create bullet with appropriate parameters
        radius = 8 * scale
        if is_enhanced:
            radius = 24 * scale  # 3x bigger for enhanced bullet
            
        speed = 140 * scale # Bullet speed
        angle_rad = math.radians(tank.angle)
        direction = [math.sin(angle_rad), math.cos(angle_rad)]
        offset = 16 + radius * scale
        pos = (
            tank.center_pos[0] + direction[0] * offset,
            tank.center_pos[1] + direction[1] * offset
        )
        
        # Create the bullet with appropriate image and size
        bullet = Bullet(
            owner=tank, 
            pos=pos, 
            angle=tank.angle, 
            speed=speed, 
            radius=radius, 
            space=self.space,
            enhanced=is_enhanced  # Pass the enhanced flag to Bullet
        )
        
        self.add_widget(bullet)
        self.bullets.append(bullet)
        self.bullets_by_shape[bullet.shape] = bullet

    def clear_all_bullets(self):
        """Remove all bullets from the game"""
        for bullet in self.bullets[:]:
            bullet.destroy(self.space)
        self.bullets.clear()
        self.bullets_by_shape.clear()

    def restart_game(self, dt):
        """Restart the game after a hit"""
        print("Restarting game...")
        
        # Ensure background music is playing
        if hasattr(self, "sounds") and "background" in self.sounds:
            if self.sounds["background"].state != 'play':
                self.sounds["background"].play()
                print("Background music continued")

        # Stop any lingering movement
        self.stop_all_tank_movement()

        self.clear_all_items()

        # Keep tanks disabled during countdown
        self.tanks_enabled = False
        self.collision_enabled = False
        
        # Reset tank positions
        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        border = self.wall_thickness
        tank_radius = 16
        tank_offset = border + tank_radius + 4

        # Bottom-middle for tank 1
        tank1_x = map_x + map_w / 2
        tank1_y = map_y + tank_offset
        self.tanks[0].center_pos = [tank1_x, tank1_y]
        self.tanks[0].angle = 0

        # Top-middle for tank 2
        tank2_x = map_x + map_w / 2
        tank2_y = map_y + map_h - tank_offset
        self.tanks[1].center_pos = [tank2_x, tank2_y]
        self.tanks[1].angle = 180

        for tank in self.tanks:
            # Reset position
            tank.center = tank.center_pos
            
            # Reset ammo (but NOT health)
            tank.ammo = tank.max_ammo
            tank.can_shoot = True
            tank.is_reloading = False
    
        # Start countdown for restart from root widget
        if self.root_widget:
            self.root_widget.start_countdown(0)
    
        # Note: tanks_enabled will be set to True by teleport_tanks_to_center
        # which is called after the countdown

    def reset_tanks_full(self):
        """Reset tanks with full health and ammo (for new game)"""
        for tank in self.tanks:
            tank.health = tank.max_health
            tank.ammo = tank.max_ammo
            tank.can_shoot = True
            tank.is_reloading = False

    def reset_game(self, map_filename="default_map.json"):
        """Reset the entire game state for a new game"""
        # Lưu lại tên file map để dùng sau
        self.current_map_filename = map_filename    
        # Reset tank health and ammo
        for tank in self.tanks:
            tank.health = tank.max_health
            tank.ammo = tank.max_ammo
            tank.can_shoot = True
            tank.is_reloading = False
            tank.opacity = 0  # Hide tanks initially
    
        # Clear all bullets
        self.clear_all_bullets()

        self.clear_all_items()

        # Gọi hàm load map mới này. Nó sẽ tự động dọn dẹp và tạo lại tường.
        # self.load_map_from_file(map_filename)

        # Reset game state
        self.tanks_enabled = False
        self.collision_enabled = False

    def debug_print_rectangles(self):
        map_x, map_y = self.map_image.pos
        map_w, map_h = self.map_image.size
        print("---- Rectangle Collide Boxes (relative to map) ----")
        for wall in self.wall_shapes:
            if isinstance(wall, pymunk.Poly):
                coords = []
                for v in wall.get_vertices():
                    # Convert to map-local coordinates
                    local_x = v.x - map_x
                    local_y = v.y - map_y
                    coords.append((round(local_x, 2), round(local_y, 2)))
                print(coords)
        print("---------------------------------------------------")

    def stop_all_tank_movement(self):
        """Reset all movement flags for all tanks"""
        for tank in self.tanks:
            tank.moving_forward = False
            tank.moving_backward = False
            tank.rotating_left = False
            tank.rotating_right = False
    def add_item_to_status_panel(self, tank, item):
        """Add item to status panel"""
        tank_index = self.tanks.index(tank)
        
        # Initialize the status panel for this tank if needed
        if tank_index not in self.status_panel:
            self.status_panel[tank_index] = {}
        
        # Use the game area to access the correct panel
        if hasattr(self, 'parent') and hasattr(self.parent, 'left_panel') and hasattr(self.parent, 'right_panel'):
            # Access the appropriate panel through the GameArea
            if tank_index == 0:
                panel = self.parent.left_panel
            else:
                panel = self.parent.right_panel
                
            # Add item to the panel - create a simple container if needed
            from kivy.uix.boxlayout import BoxLayout
            
            # Create or get items container
            if not hasattr(panel, 'items_container'):
                items_container = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=0.15,
                    pos_hint={'center_x': 0.5, 'y': 0.15},  # Position near the bottom
                    spacing=5
                )
                panel.add_widget(items_container)
                panel.items_container = items_container
            
            # Check if this item type already exists
            if hasattr(panel, 'active_items') and item.item_type in panel.active_items:
                # Remove existing icon
                existing_icon = panel.active_items[item.item_type]
                panel.items_container.remove_widget(existing_icon)
            
            # Create icon
            from kivy.uix.image import Image
            icon = Image(source=item.image_path, size_hint=(None, None), size=(72, 72))
            
            # Add to panel's items container
            panel.items_container.add_widget(icon)
            
            # Track the item for removal later
            if not hasattr(panel, 'active_items'):
                panel.active_items = {}
            panel.active_items[item.item_type] = icon
            
            # Also store in status_panel for consistency
            self.status_panel[tank_index][item.item_type] = icon
            
            print(f"Added {item.item_type} to status panel for tank {tank_index}")
        else:
            print("Cannot access status panels! Make sure GamePanel is properly connected to GameArea.")

    def remove_item_from_status_panel(self, tank, item_type):
        """Remove item from status panel"""
        tank_index = self.tanks.index(tank)
    
        # Access the correct panel
        if hasattr(self, 'parent') and hasattr(self.parent, 'left_panel') and hasattr(self.parent, 'right_panel'):
            panel = self.parent.left_panel if tank_index == 0 else self.parent.right_panel
        
            # Remove icon if it exists
            if hasattr(panel, 'active_items') and item_type in panel.active_items:
                icon = panel.active_items[item_type]
                if hasattr(panel, 'items_container'):
                    panel.items_container.remove_widget(icon)
                del panel.active_items[item_type]
                print(f"Removed {item_type} from status panel for tank {tank_index}")