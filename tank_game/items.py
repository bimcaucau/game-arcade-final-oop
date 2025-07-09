import pymunk
import random
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.clock import Clock
import time

# Constants
COLLISION_TYPE_ITEM = 8  # Unique collision type for items
ITEM_SIZE = (24, 24)  # Default size for items

class Item(Widget):
    def __init__(self, position, item_type="basic", **kwargs):
        super().__init__(**kwargs)
        self.pos = position
        self.size = ITEM_SIZE
        self.collected = False
        self.item_type = item_type
        
        # Set properties based on item type
        if item_type == "shield":
            self.duration = 3.0    # 3 seconds
            self.image_path = "assets/shield.png"
        elif item_type == "speedup":
            self.duration = 2.0    # 2 seconds
            self.image_path = "assets/speedup.png"
        elif item_type == "billie":  # New Billie Eilish item
            self.duration = None   # No duration - lasts until used
            self.image_path = "assets/billie_eilish.png"
        else:
            self.duration = 5.0    # Default duration
            self.image_path = "assets/shield.png"  # Default fallback image
        
        # Visual representation using image
        with self.canvas:
            self.rect = Rectangle(source=self.image_path, pos=self.pos, size=self.size)
        
        self.bind(pos=self.update_graphics)
    
    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def apply_effect(self, tank):
        """Apply the item effect to the tank"""
        if self.item_type == "shield":
            # Apply shield effect
            log_debug(f"Applying shield effect to tank {tank.source}")
            tank.shield_active = True
            tank.shield_expire_time = time.time() + self.duration
        
        elif self.item_type == "speedup":
            # Apply speed up effect
            log_debug(f"Applying speed up effect to tank {tank.source}")
            # Store original speed if not already stored
            if not hasattr(tank, "original_speed"):
                tank.original_speed = tank.move_speed
            
            # Double the speed
            tank.move_speed = tank.original_speed * 2
            tank.speedup_expire_time = time.time() + self.duration
            
        elif self.item_type == "billie":
            # Apply Billie Eilish bullet enhancement
            log_debug(f"Applying Billie Eilish bullet effect to tank {tank.source}")
            tank.billie_bullet_active = True
            # No expiration time - lasts until used
    
    def remove_effect(self, tank):
        """Remove the item effect from the tank"""
        if self.item_type == "shield":
            log_debug(f"Removing shield effect from tank {tank.source}")
            tank.shield_active = False
            tank.shield_expire_time = None
        
        elif self.item_type == "speedup":
            log_debug(f"Removing speed up effect from tank {tank.source}")
            # Restore original speed
            if hasattr(tank, "original_speed"):
                tank.move_speed = tank.original_speed
            tank.speedup_expire_time = None
            
        elif self.item_type == "billie":
            log_debug(f"Removing Billie Eilish bullet effect from tank {tank.source}")
            tank.billie_bullet_active = False
        
    def destroy(self):
        """Remove the item from the game"""
        if self.parent:
            self.parent.remove_widget(self)


def log_debug(msg):
    """Debug logging function"""
    print(f"DEBUG: {msg}")


def spawn_item(space, map_rect, obstacles, tanks):
    """Spawn a random item at a valid location"""
    map_x, map_y, map_w, map_h = map_rect
    
    # Define margin from edges
    margin = 40
    
    # Choose a random item type
    item_types = ["shield", "speedup", "billie"]  # Add billie to possible items
    item_type = random.choice(item_types)
    
    # Try several random positions until a valid one is found
    max_attempts = 50
    for attempt in range(max_attempts):
        # Generate random position within map bounds with margin
        x = random.uniform(map_x + margin, map_x + map_w - margin - ITEM_SIZE[0])
        y = random.uniform(map_y + margin, map_y + map_h - margin - ITEM_SIZE[1])
        
        # Create a test body and shape
        test_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        test_body.position = (x + ITEM_SIZE[0]/2, y + ITEM_SIZE[1]/2)
        test_shape = pymunk.Circle(test_body, ITEM_SIZE[0]/2)
        
        # Check for collisions with ANY existing shape in the space
        collisions = space.shape_query(test_shape)
        
        if collisions:
            continue
            
        # Check if too close to any tank
        too_close = False
        for tank in tanks:
            dist = ((tank.center_x - (x + ITEM_SIZE[0]/2))**2 + 
                   (tank.center_y - (y + ITEM_SIZE[1]/2))**2)**0.5
            if dist < 50:  # Minimum distance from tanks
                too_close = True
                break
                
        if too_close:
            continue
                
        # Valid position found!
        item = Item((x, y), item_type=item_type)
        
        # Create a pymunk body for the item (as a sensor)
        item_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        item_body.position = (x + ITEM_SIZE[0]/2, y + ITEM_SIZE[1]/2)
        item_shape = pymunk.Circle(item_body, ITEM_SIZE[0]/2)
        item_shape.sensor = True  # Make it non-blocking
        item_shape.collision_type = COLLISION_TYPE_ITEM
        
        # Add to space
        space.add(item_body, item_shape)
        
        # Store references
        item.body = item_body
        item.shape = item_shape
        item_shape.item = item  # Reference back to the item
        
        log_debug(f"Successfully spawned {item_type} item at {item.pos}")
        return item
            
    # If we got here, couldn't find a valid position
    return None


def setup_item_collision_handler(space, game_panel):
    """Setup collision handling for items"""
    def begin_tank_item_collision(arbiter, space, data):
        log_debug("!!! Tank-item collision handler called !!!")
        shapes = arbiter.shapes
        item_shape = shapes[0] if shapes[0].collision_type == COLLISION_TYPE_ITEM else shapes[1]
        tank_shape = shapes[0] if shapes[0].collision_type == 1 else shapes[1]
        
        # Get the item and tank objects
        item = getattr(item_shape, "item", None)
        tank = None
        for t in game_panel.tanks:
            if t.shape == tank_shape:
                tank = t
                break
                
        if item and tank:
            log_debug(f"Tank {tank.source} collected item")
            
            # Mark item as collected
            item.collected = True
            
            # Apply effect
            item.apply_effect(tank)
            
            # Play sound effect based on item type
            if item.item_type == "shield" and hasattr(game_panel, "sounds") and "shield" in game_panel.sounds:
                game_panel.sounds["shield"].play()
                log_debug("Playing shield sound")
                
            elif item.item_type == "speedup" and hasattr(game_panel, "sounds") and "speedup" in game_panel.sounds:
                game_panel.sounds["speedup"].play()
                log_debug("Playing speed up sound")
                
            # Add to tank's active items
            if not hasattr(tank, 'active_items'):
                tank.active_items = {}
            tank.active_items[item.item_type] = item
            
            # Update status panel
            game_panel.add_item_to_status_panel(tank, item)
            
            # Remove from game
            if item in game_panel.items:
                game_panel.items.remove(item)
            
            # Remove physics body
            space.remove(item.body, item.shape)
            
            # Remove widget
            item.destroy()
            
            print(f"Item collected by tank!")
            
        # Return False to allow tanks to pass through
        return False
        
    # Add the collision handler
    handler = space.add_collision_handler(1, COLLISION_TYPE_ITEM)  # Tank and item
    handler.begin = begin_tank_item_collision
    log_debug(f"Item collision handler set up")


def update_active_items(tank, game_panel):
    """Update any active item effects on a tank"""
    current_time = time.time()
    
    # Check shield expiration
    if hasattr(tank, "shield_active") and tank.shield_active:
        if tank.shield_expire_time and current_time > tank.shield_expire_time:
            print(f"Shield expired for tank {tank.source}")
            # Remove shield effect
            tank.shield_active = False
            
            # Remove from active items
            if hasattr(tank, "active_items") and "shield" in tank.active_items:
                item = tank.active_items["shield"]
                item.remove_effect(tank)
                game_panel.remove_item_from_status_panel(tank, "shield")
                del tank.active_items["shield"]
    
    # Check speed up expiration
    if hasattr(tank, "speedup_expire_time") and tank.speedup_expire_time:
        if current_time > tank.speedup_expire_time:
            print(f"Speed up expired for tank {tank.source}")
            # Restore original speed
            if hasattr(tank, "original_speed"):
                tank.move_speed = tank.original_speed
            tank.speedup_expire_time = None
            
            # Remove from active items
            if hasattr(tank, "active_items") and "speedup" in tank.active_items:
                item = tank.active_items["speedup"]
                item.remove_effect(tank)
                game_panel.remove_item_from_status_panel(tank, "speedup")
                del tank.active_items["speedup"]
    
    # No need to check billie bullet effect - it's used when shooting