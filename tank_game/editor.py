from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line
import json
import os

class EditorCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.placed_objects = []
        self.current_tool = 'box' 
        self.selected_object = None

        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.on_object_selected = None 

        self.spawn_zones = [
            (200, 520, 200, 80),  
            (200, 0, 200, 80),    
        ]        

        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            self.design_rect = Line(rectangle=(self.x, self.y, 600, 600), width=2)

            # Vẽ spawn zones với màu bán trong suốt
            Color(1, 0, 0, 0.3) # Màu đỏ trong suốt
            self.red_zone_rect = Rectangle(pos=self._logic_to_phys_pos(self.spawn_zones[0][:2]), 
                                           size=self.spawn_zones[0][2:])
            
            Color(0, 0, 1, 0.3) # Màu xanh trong suốt
            self.blue_zone_rect = Rectangle(pos=self._logic_to_phys_pos(self.spawn_zones[1][:2]), 
                                            size=self.spawn_zones[1][2:])

        self.bind(pos=self._update_static_graphics, size=self._update_static_graphics)

    # --- Các hàm trợ giúp về tọa độ và va chạm ---
    def _logic_to_phys_pos(self, logic_pos):
        """Chuyển tọa độ logic (0-600) sang tọa độ vật lý trên màn hình."""
        logic_x, logic_y = logic_pos
        phys_x = self.x + logic_x
        phys_y = self.y + 600 - logic_y # Lật ngược Y so với khung 600x600
        return (phys_x, phys_y)

    def _phys_to_logic(self, phys_pos):
        """Chuyển tọa độ vật lý trên màn hình về tọa độ logic (0-600)."""
        logic_x = phys_pos[0] - self.x
        # Áp dụng công thức lật ngược
        logic_y = 600 - (phys_pos[1] - self.y)
        return (logic_x, logic_y)
    
    def _logic_to_phys_rect(self, logic_rect):
        """
        Chuyển một hình chữ nhật logic (x, y, w, h) sang tọa độ vật lý (Kivy)
        để có thể vẽ bằng Rectangle().
        """
        x, y, w, h = logic_rect
        phys_x = self.x + x
        # Vị trí Y của Rectangle() là góc dưới-trái, nên công thức là:
        phys_y = (self.y + 600) - y - h
        return (phys_x, phys_y)

    def check_collision(self, rect1, rect2):
        """Kiểm tra va chạm giữa hai hình chữ nhật."""
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        return not (x1 + w1 < x2 or x1 > x2 + w2 or y1 + h1 < y2 or y1 > y2 + h2)

    def _update_static_graphics(self, *args):
        """Cập nhật các hình vẽ tĩnh khi cửa sổ thay đổi."""
        self.design_rect.rectangle = (self.x, self.y, 600, 600)
        self.red_zone_rect.pos = self._logic_to_phys(self.spawn_zones[0][:2])
        self.blue_zone_rect.pos = self._logic_to_phys(self.spawn_zones[1][:2])

    # --- Các hàm xử lý sự kiện chạm ---
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
            
        logic_touch_pos = self._phys_to_logic(touch.pos)
        
        # 1. ƯU TIÊN KIỂM TRA CHỌN VÀ KÉO TRƯỚC
        for obj in reversed(self.placed_objects):
            obj_rect = (obj['x'], obj['y'], obj['width'], obj['height'])
            if obj_rect[0] < logic_touch_pos[0] < obj_rect[0] + obj_rect[2] and \
               obj_rect[1] < logic_touch_pos[1] < obj_rect[1] + obj_rect[3]:
                
                # Đã nhấp trúng một vật thể
                self.selected_object = obj
                self.is_dragging = True
                # Tính toán độ lệch để kéo mượt hơn
                self.drag_offset_x = logic_touch_pos[0] - obj['x']
                self.drag_offset_y = logic_touch_pos[1] - obj['y']
                
                if self.on_object_selected:
                    self.on_object_selected(self.selected_object)
                self.draw_objects()
                return True

        # 2. NẾU KHÔNG NHẤP TRÚNG VẬT THỂ NÀO, THÌ LÀ THÊM MỚI
        self.is_dragging = False
        # Bỏ chọn đối tượng cũ
        if self.selected_object:
            self.selected_object = None
            if self.on_object_selected:
                self.on_object_selected(None)

        # Thêm vật thể mới dựa trên công cụ hiện tại
        sizes = {'box': (50, 50), 'v_wall': (15, 200), 'h_wall': (200, 15)}
        width, height = sizes.get(self.current_tool, (50, 50))
        
        new_x = logic_touch_pos[0] - width / 2
        new_y = logic_touch_pos[1] - height / 2
        new_obj_rect = (new_x, new_y, width, height)

        # Kiểm tra xem vật thể mới có nằm trong vùng cấm không
        for zone in self.spawn_zones:
            if self.check_collision(new_obj_rect, zone):
                print("Cannot place objects in spawn zones!")
                return True # Không cho phép thêm
        
        new_obj = {'type': 'box', 'x': new_x, 'y': new_y, 'width': width, 'height': height}
        self.placed_objects.append(new_obj)
        self.draw_objects()
        return True

    def on_touch_move(self, touch):
        if self.is_dragging and self.selected_object:
            if not self.collide_point(*touch.pos):
                return False

            logic_touch_pos = self._phys_to_logic(touch.pos)
            
            # Tính vị trí mới dựa trên con trỏ và độ lệch
            new_x = logic_touch_pos[0] - self.drag_offset_x
            new_y = logic_touch_pos[1] - self.drag_offset_y
            
            # Giới hạn vị trí trong khung 600x600
            new_x = max(0, min(new_x, 600 - self.selected_object['width']))
            new_y = max(0, min(new_y, 600 - self.selected_object['height']))
            
            new_obj_rect = (new_x, new_y, self.selected_object['width'], self.selected_object['height'])
            
            # Kiểm tra va chạm với vùng cấm khi đang kéo
            is_colliding_zone = False
            for zone in self.spawn_zones:
                if self.check_collision(new_obj_rect, zone):
                    is_colliding_zone = True
                    break
            
            # Chỉ cập nhật vị trí nếu không va chạm vùng cấm
            if not is_colliding_zone:
                self.selected_object['x'] = new_x
                self.selected_object['y'] = new_y
                self.draw_objects()
            return True

    def on_touch_up(self, touch):
        # Dừng việc kéo khi nhả chuột
        if self.is_dragging:
            self.is_dragging = False
            return True

    def draw_objects(self):
        self.canvas.after.clear()
        with self.canvas.after:
            for obj in self.placed_objects:
                # Vẽ tại vị trí vật lý trên màn hình
                phys_pos = self._logic_to_phys_rect((obj['x'], obj['y'], obj['width'], obj['height']))
                Color(0.7, 0.7, 0.7, 1) # Xám
                Rectangle(pos=phys_pos, size=(obj['width'], obj['height']))

                # Nếu vật thể này đang được chọn, vẽ viền vàng
                if obj is self.selected_object:
                    Color(1, 1, 0, 1) # Vàng
                    Line(rectangle=(phys_pos[0], phys_pos[1], obj['width'], obj['height']), width=2)

        # Đặt lại màu về trắng để không ảnh hưởng đến các widget khác
        Color(1, 1, 1, 1)

    def _update_static_graphics(self, *args):
        """Cập nhật các hình vẽ tĩnh (khung viền, spawn zones)."""
        self.design_rect.rectangle = (self.x, self.y, 600, 600)
        
        # Dùng hàm trợ giúp để đặt vị trí spawn zones cho đúng
        red_zone_logic = self.spawn_zones[0]
        self.red_zone_rect.pos = self._logic_to_phys_rect(red_zone_logic)
        
        blue_zone_logic = self.spawn_zones[1]
        self.blue_zone_rect.pos = self._logic_to_phys_rect(blue_zone_logic)

    # --- Các hàm thao tác với đối tượng đã chọn ---
    def adjust_selected_object(self, prop, amount):
        if self.selected_object:
            self.selected_object[prop] += amount
            # Đảm bảo kích thước không bị âm
            if self.selected_object['width'] < 10: self.selected_object['width'] = 10
            if self.selected_object['height'] < 10: self.selected_object['height'] = 10
            self.draw_objects() # Vẽ lại

    def delete_selected_object(self):
        if self.selected_object:
            self.placed_objects.remove(self.selected_object)
            self.selected_object = None
            if self.on_object_selected:
                self.on_object_selected(None) # Thông báo đã bỏ chọn
            self.draw_objects()

    def save_map(self):
        with open('custom_map.json', 'w') as f:
            json.dump(self.placed_objects, f, indent=2)
        print("Map saved to custom_map.json")

    def load_map(self):
        if os.path.exists('custom_map.json'):
            with open('custom_map.json', 'r') as f:
                self.placed_objects = json.load(f)
            print("Loaded map from custom_map.json")
        else:
            self.placed_objects = []
            print("No custom_map.json found. Starting with a blank map.")
        self.draw_objects()

    def clear_map(self):
        self.placed_objects.clear()
        self.selected_object = None
        if self.on_object_selected:
            self.on_object_selected(None)
        self.draw_objects()

class MapEditorScreen(Screen):
    def on_enter(self, *args):
        # Tự động load map cũ mỗi khi vào màn hình này
        self.canvas_widget.load_map()
            
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root_layout = FloatLayout()
        self.canvas_widget = EditorCanvas(size_hint=(None, None), size=(600, 600),
                                          pos_hint={'center_x': 0.45, 'center_y': 0.5})
        root_layout.add_widget(self.canvas_widget)
        
        # Kết nối callback từ canvas về màn hình này
        self.canvas_widget.on_object_selected = self.toggle_adjustment_controls

        # Toolbox bên phải
        toolbox = BoxLayout(orientation='vertical', size_hint=(0.2, 1), 
                            pos_hint={'right': 1, 'top': 1}, spacing=10, padding=10)
        
        # --- Phần Công cụ (Tools) ---
        toolbox.add_widget(Label(text="Tools", font_size='20sp', size_hint_y=None, height=40))

        # Hàm callback cho các nút công cụ
        def set_current_tool(instance):
            self.canvas_widget.current_tool = instance.tool_type
            # Bỏ chọn đối tượng khi đổi công cụ
            if self.canvas_widget.selected_object:
                self.canvas_widget.selected_object = None
                self.toggle_adjustment_controls(None)
                self.canvas_widget.draw_objects()

        tool_buttons_config = [
            ("Add Box", 'box'),
            ("Add Vertical Wall", 'v_wall'),
            ("Add Horizontal Wall", 'h_wall'),
        ]
        for text, tool_type in tool_buttons_config:
            btn = Button(text=text, size_hint_y=None, height=40)
            btn.tool_type = tool_type
            btn.bind(on_press=set_current_tool)
            toolbox.add_widget(btn)

        # --- Phần Điều chỉnh (Adjustments) ---
        self.adjustment_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        
        # Tạo các nút điều chỉnh
        self.adjustment_box.add_widget(Label(text="Adjust Selected", font_size='18sp'))
        
        # Width controls
        w_layout = BoxLayout(size_hint_y=None, height=40)
        btn_w_minus = Button(text="W -")
        btn_w_minus.bind(on_press=lambda x: self.canvas_widget.adjust_selected_object('width', -5))
        btn_w_plus = Button(text="W +")
        btn_w_plus.bind(on_press=lambda x: self.canvas_widget.adjust_selected_object('width', 5))
        w_layout.add_widget(btn_w_minus)
        w_layout.add_widget(btn_w_plus)
        self.adjustment_box.add_widget(w_layout)

        # Height controls
        h_layout = BoxLayout(size_hint_y=None, height=40)
        btn_h_minus = Button(text="H -")
        btn_h_minus.bind(on_press=lambda x: self.canvas_widget.adjust_selected_object('height', -5))
        btn_h_plus = Button(text="H +")
        btn_h_plus.bind(on_press=lambda x: self.canvas_widget.adjust_selected_object('height', 5))
        h_layout.add_widget(btn_h_minus)
        h_layout.add_widget(btn_h_plus)
        self.adjustment_box.add_widget(h_layout)

        btn_delete = Button(text="Delete Selected", background_color=(1,0,0,1), size_hint_y=None, height=40)
        btn_delete.bind(on_press=lambda x: self.canvas_widget.delete_selected_object())
        self.adjustment_box.add_widget(btn_delete)
        
        toolbox.add_widget(self.adjustment_box)
        # Ẩn đi ban đầu
        self.toggle_adjustment_controls(None) 

        # --- Phần Hành động (Actions) ---
        toolbox.add_widget(Label(text="Map Actions", font_size='20sp', size_hint_y=None, height=40))
        btn_save = Button(text='Save Map', size_hint_y=None, height=40)
        btn_save.bind(on_press=lambda x: self.canvas_widget.save_map())
        
        btn_clear = Button(text='Clear All', size_hint_y=None, height=40)
        btn_clear.bind(on_press=lambda x: self.canvas_widget.clear_map())

        btn_back = Button(text='Back to Tank Menu', size_hint_y=None, height=40)
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'tank_menu'))

        toolbox.add_widget(btn_save)
        toolbox.add_widget(btn_clear)
        toolbox.add_widget(btn_back)

        root_layout.add_widget(toolbox)
        self.add_widget(root_layout)

    def toggle_adjustment_controls(self, selected_object):
        """Hàm này được gọi bởi EditorCanvas khi có đối tượng được chọn/bỏ chọn."""
        if selected_object:
            # Hiện ra
            self.adjustment_box.height = self.adjustment_box.minimum_height
            self.adjustment_box.opacity = 1
            # Kích hoạt các nút
            for child in self.adjustment_box.walk(restrict=True):
                if isinstance(child, Button):
                    child.disabled = False
        else:
            # Ẩn đi
            self.adjustment_box.height = 0
            self.adjustment_box.opacity = 0
            # Vô hiệu hóa các nút
            for child in self.adjustment_box.walk(restrict=True):
                if isinstance(child, Button):
                    child.disabled = True