import pymunk
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.window import Window
from random import choice, uniform
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
# --- Constants ---
PADDLE_WIDTH, PADDLE_HEIGHT = 20, 240
BALL_RADIUS = 12
ORB_RADIUS = 10
BALL_INITIAL_SPEED = 440
PADDLE_SPEED = 300
WINNING_SCORE = 4

# --- Pymunk Collision Types ---
COLLISION_TYPE_BALL = 1
COLLISION_TYPE_PADDLE = 2
COLLISION_TYPE_GOAL = 3
COLLISION_TYPE_ORB = 4

class Particle(Widget):
    """A simple visual particle for effects."""
    def __init__(self, pos, velocity, color, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        self.size = (4,4)
        self.velocity = velocity
        with self.canvas:
            self.color = Color(rgba=color)
            self.rect = Rectangle(pos=self.pos, size=self.size)

        # Animate the 'a' (alpha) channel of the Color instruction to 0
        anim = Animation(a=0, duration=0.4)
        # When the animation is complete, remove the particle widget
        anim.bind(on_complete=self.self_destruct)
        anim.start(self.color)

    def move(self, dt):
        self.pos = Vector(*self.velocity) * dt + self.pos
        self.rect.pos = self.pos # Update the rectangle's position

    def self_destruct(self, *args):
        # The parent of this widget is the GameWidget that created it.
        if self.parent:
            self.parent.remove_widget(self)

class GameWidget(Widget):
    score1 = NumericProperty(0)
    score2 = NumericProperty(0)
    hp1 = NumericProperty(3)
    hp2 = NumericProperty(3)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.music = None
        self.hit_count = 0
        self.game_over = False
        self.health_orb = None # To store the orb's physics body
        self.particles = [] # To store active particles
        self.orb_spawn_timer = 0.0
        with self.canvas.before:
            Color(1, 1, 0.8, 1); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.score_label1 = Label(text=str(self.score1), font_size='80sp', color=(0.7,0.7,0.7,1), font_name='fonts/VCR_OSD_MONO_1.001.ttf')
        self.hp_label1 = Label(text=f"{self.hp1}/3", font_size='40sp', color=(0.7,0.7,0.7,1), font_name='fonts/VCR_OSD_MONO_1.001.ttf')
        self.score_label2 = Label(text=str(self.score2), font_size='80sp', color=(0.7,0.7,0.7,1), font_name='fonts/VCR_OSD_MONO_1.001.ttf')
        self.hp_label2 = Label(text=f"{self.hp2}/3", font_size='40sp', color=(0.7,0.7,0.7,1), font_name='fonts/VCR_OSD_MONO_1.001.ttf')
        
        for label in [self.score_label1, self.hp_label1, self.score_label2, self.hp_label2]:
            self.add_widget(label)

        with self.canvas.after:
            self.ball_color_gfx = Color(1,1,1,1)
            self.ball_gfx = Ellipse(size=(BALL_RADIUS*2, BALL_RADIUS*2))
            Color(0,0,0,1); self.ball_outline_gfx = Line(circle=(0,0,BALL_RADIUS), width=1.5)
            self.paddle1_color_gfx = Color(1,0,0,1)
            self.paddle1_gfx = Rectangle(size=(PADDLE_WIDTH, PADDLE_HEIGHT))
            Color(0,0,0,1); self.paddle1_outline_gfx = Line(rectangle=(0,0,PADDLE_WIDTH,PADDLE_HEIGHT), width=2.0)
            self.paddle2_color_gfx = Color(0,0,1,1)
            self.paddle2_gfx = Rectangle(size=(PADDLE_WIDTH, PADDLE_HEIGHT))
            Color(0,0,0,1); self.paddle2_outline_gfx = Line(rectangle=(0,0,PADDLE_WIDTH,PADDLE_HEIGHT), width=2.0)
            self.orb_color_gfx = Color(0.2, 1, 0.2, 0) # Green, but invisible initially
            self.orb_gfx = Ellipse(size=(ORB_RADIUS*2, ORB_RADIUS*2))
        
        self.bind(score1=self.update_labels, hp1=self.update_labels, score2=self.update_labels, hp2=self.update_labels)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
        Clock.schedule_once(self.setup_physics)

    def setup_physics(self, dt):
        # --- ADD MUSIC ---
        self.music = SoundLoader.load('sounds/pong_bgm.mp3') # Make sure this is the correct filename
        if self.music:
            self.music.loop = True
            self.music.play()

        self.space = pymunk.Space()
        self.ball = self.create_physics_ball()
        self.player1 = self.create_physics_paddle(is_player1=True)
        self.player2 = self.create_physics_paddle(is_player1=False)
        self.create_walls_and_goals()
        paddle_handler = self.space.add_collision_handler(COLLISION_TYPE_BALL, COLLISION_TYPE_PADDLE)
        paddle_handler.post_solve = self.on_paddle_hit
        # NEW: Collision handler for orb collection
        orb_handler = self.space.add_collision_handler(COLLISION_TYPE_PADDLE, COLLISION_TYPE_ORB)
        orb_handler.begin = self.on_orb_collect
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self.p1_movement = self.p2_movement = 0

        Clock.schedule_interval(self.update, 1.0 / 60.0)
        self.reset_round()

    def on_paddle_hit(self, arbiter, space, data):
        if self.game_over: return
        self.hit_count += 1
        speed_multiplier = 1.0 + min(self.hit_count, 12) * 0.05
        new_speed = BALL_INITIAL_SPEED * speed_multiplier
        self.ball.velocity = self.ball.velocity.normalized() * new_speed
        paddle_shape = arbiter.shapes[1]
        self.resize_paddle_for_hit(paddle_shape)

        # --- PARTICLE EFFECT ---
        impact_point = arbiter.contact_point_set.points[0].point_a
        self.create_particle_burst(impact_point)
        
        if self.hit_count >= 12:
            if paddle_shape.body == self.player1: 
                self.hp1 -= 1
            elif paddle_shape.body == self.player2: 
                self.hp2 -= 1
            self.check_for_hp_loss()
        if self.hit_count >= 12:
            if paddle_shape.body == self.player1:
                self.spawn_health_orb(side=1) # Spawn a health orb if conditions are met
            else:
                self.spawn_health_orb(side=2)

    def create_particle_burst(self, pos):
        ratio = min(self.hit_count / 12.0, 1.0)
        particle_color = [1, 1 - (ratio * 0.5), 1 - ratio, 1] # Color with full alpha
        
        # We no longer need the 'with self.canvas.after' block here
        for _ in range(10):
            velocity = Vector(uniform(-150, 150), uniform(-150, 150))
            # Create the particle and add it as a child widget
            p = Particle(pos=pos, velocity=velocity, color=particle_color)
            self.add_widget(p) # Add to the GameWidget
            self.particles.append(p)

    def spawn_health_orb(self, side, dt=None):
        self.remove_health_orb()
        if self.game_over or self.hit_count < 12: 
            return
        if side == 1:
            # Spawn on Player 1's (left) side
            x = self.player1.position.x
        else:
            # Spawn on Player 2's (right) side
            x = self.player2.position.x

        # Generate a random Y position along the paddle's path
        y = uniform(self.y + PADDLE_HEIGHT / 2, self.top - PADDLE_HEIGHT / 2)
        
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = x, y
        shape = pymunk.Circle(body, ORB_RADIUS)
        shape.sensor = True
        shape.collision_type = COLLISION_TYPE_ORB
        self.space.add(body, shape)
        self.health_orb = body
        self.orb_color_gfx.a = 1 # Make it visible

    def remove_health_orb(self):
        if self.health_orb:
            self.space.remove(self.health_orb, *self.health_orb.shapes)
            self.health_orb = None
            self.orb_color_gfx.a = 0 # Make it invisible

    def on_orb_collect(self, arbiter, space, data):
        paddle_shape, orb_shape = arbiter.shapes
        # Figure out which player collected it
        if paddle_shape.body == self.player1:
            if self.hp1 < 3: 
                self.hp1 += 1
        elif paddle_shape.body == self.player2:
            if self.hp2 < 3: 
                self.hp2 += 1
        
        self.remove_health_orb()
        return False

    def check_for_winner(self):
        winner = None
        if self.score1 >= WINNING_SCORE: winner = 1
        elif self.score2 >= WINNING_SCORE: winner = 2
        
        if winner:
            self.game_over = True
            self.ball.velocity = (0,0)
            self.remove_health_orb() # Clean up orb on game over
            # --- FINAL INTEGRATION ---
            # Call the main app's victory screen function
            App.get_running_app().show_victory_screen(winner, 'pong')
            return True
        return False

    def reset_round(self, side=None):
        self.hp1 = 3
        self.hp2 = 3
        self.hit_count = 0
        self.orb_spawn_timer = 0.0
        self.remove_health_orb() # Remove orb at the start of a new round
        for shape in list(self.player1.shapes):
            shape.shrink_hits = 0
            self.resize_paddle(shape)
        for shape in list(self.player2.shapes):
            shape.shrink_hits = 0
            self.resize_paddle(shape)
        self.serve_ball(side)

    def update(self, dt):
        if self.game_over: return
        self.player1.velocity = (0, self.p1_movement * PADDLE_SPEED)
        self.player2.velocity = (0, self.p2_movement * PADDLE_SPEED)

        for shape in self.player1.shapes:
            p1_height = shape.bb.top - shape.bb.bottom
            min_y1, max_y1 = p1_height / 2, self.height - p1_height / 2
            self.player1.position = (self.player1.position.x, max(min_y1, min(self.player1.position.y, max_y1)))
        for shape in self.player2.shapes:
            p2_height = shape.bb.top - shape.bb.bottom
            min_y2, max_y2 = p2_height / 2, self.height - p2_height / 2
            self.player2.position = (self.player2.position.x, max(min_y2, min(self.player2.position.y, max_y2)))

        self.space.step(dt)
            
        # --- Update Particles ---
        for p in self.particles[:]:
            p.move(dt)
            # The self_destruct now handles removal, but we need to remove from our list
            if p.parent is None:
                self.particles.remove(p)
        
        ratio = min(self.hit_count / 12.0, 1.0)
        self.ball_color_gfx.rgb = (1, 1 - (ratio * 0.5), 1 - ratio)
        ball_x, ball_y = self.ball.position
        p1_x, p1_y = self.player1.position
        p2_x, p2_y = self.player2.position
        self.ball_gfx.pos = (ball_x - BALL_RADIUS, ball_y - BALL_RADIUS)
        self.ball_outline_gfx.circle = (ball_x, ball_y, BALL_RADIUS)
        if self.health_orb: 
            self.orb_gfx.pos = (self.health_orb.position.x - ORB_RADIUS, self.health_orb.position.y - ORB_RADIUS)
        for shape in self.player1.shapes:
            p1_height = shape.bb.top - shape.bb.bottom
            self.paddle1_gfx.pos = (p1_x - PADDLE_WIDTH/2, p1_y - p1_height/2); self.paddle1_gfx.size = (PADDLE_WIDTH, p1_height)
            self.paddle1_outline_gfx.rectangle = (*self.paddle1_gfx.pos, *self.paddle1_gfx.size)
        for shape in self.player2.shapes:
            p2_height = shape.bb.top - shape.bb.bottom
            self.paddle2_gfx.pos = (p2_x - PADDLE_WIDTH/2, p2_y - p2_height/2); self.paddle2_gfx.size = (PADDLE_WIDTH, p2_height)
            self.paddle2_outline_gfx.rectangle = (*self.paddle2_gfx.pos, *self.paddle2_gfx.size)


    def resize_paddle_for_hit(self, p_shape):
        s_hits = getattr(p_shape, 'shrink_hits', 0)
        if s_hits < 6: s_hits += 1; p_shape.shrink_hits = s_hits; self.resize_paddle(p_shape)

    def resize_paddle(self, p_shape):
        body = p_shape.body; self.space.remove(p_shape)
        s_hits = getattr(p_shape, 'shrink_hits', 0)
        s_mult = 1.0 - (min(s_hits, 6) * 0.065); n_height = PADDLE_HEIGHT * s_mult
        n_shape = pymunk.Poly.create_box(body, (PADDLE_WIDTH, n_height))
        n_shape.elasticity = 1.0; n_shape.collision_type = COLLISION_TYPE_PADDLE; n_shape.shrink_hits = s_hits
        self.space.add(n_shape)

    def process_goal(self, arbiter, space, data):
        if self.game_over: return False
        
        # Determine who scored and who the serve should go to
        # If player 1 scores, serve to player 2.
        # If player 2 scores, serve to player 1.
        serve_to_side = arbiter.shapes[1].player_who_scores 
        
        if serve_to_side == 1: 
            self.score1 += 1
            serve_direction = 2 # Serve to the other side
        else: 
            self.score2 += 1
            serve_direction = 1 # Serve to the other side
            
        if not self.check_for_winner(): 
            self.reset_round(serve_direction)
        return False
    

    def check_for_hp_loss(self):
        if self.game_over: return
        point_awarded, serve_direction = False, None
        if self.hp1 <= 0: 
            self.score2 += 1
            point_awarded, serve_direction = True, 1 # Serve to P1 who lost
        elif self.hp2 <= 0: 
            self.score1 += 1
            point_awarded, serve_direction = True, 2 # Serve to P2 who lost
            
        if point_awarded and not self.check_for_winner(): 
            self.reset_round(serve_direction)

    def serve_ball(self, side=None):
        if self.game_over: return
        self.ball.position = self.center; self.ball.velocity = (0, 0)
        self.player1.position = self.player1.position.x, self.center_y
        self.player2.position = self.player2.position.x, self.center_y
        
        # --- THE DEFINITIVE SERVE LOGIC ---
        
        # 1. Determine the horizontal direction
        if side == 1: 
            direction_x = 1 # Serve towards Player 2
        elif side == 2: 
            direction_x = -1  # Serve towards Player 1
        else: 
            direction_x = choice([-1, 1]) # Random for the first serve

        # 2. Get a random vertical component for the angle
        # We use a smaller range here because it's just for the direction vector
        direction_y = uniform(-0.5, 0.5) 

        # 3. Create, normalize, and scale the final impulse vector
        # This ensures the final speed is always exactly BALL_INITIAL_SPEED
        direction_vector = Vector(direction_x, direction_y).normalize()
        impulse = direction_vector * BALL_INITIAL_SPEED
            
        Clock.schedule_once(lambda dt: setattr(self.ball, 'velocity', impulse), 0.5)
        
    def update_canvas(self, *args):
        self.bg.pos, self.bg.size = self.pos, self.size; self.update_labels()
        
    def update_labels(self, *args):
        self.score_label1.text, self.hp_label1.text = str(self.score1), f"{self.hp1}/3"
        self.score_label2.text, self.hp_label2.text = str(self.score2), f"{self.hp2}/3"
        self.score_label1.center_x, self.score_label1.top = self.width/4, self.top - 20
        self.hp_label1.center_x, self.hp_label1.y = self.width/4, self.y + 20
        self.score_label2.center_x, self.score_label2.top = self.width*3/4, self.top - 20
        self.hp_label2.center_x, self.hp_label2.y = self.width*3/4, self.y + 20

    def create_physics_ball(self):
        body = pymunk.Body(1, pymunk.moment_for_circle(1, 0, BALL_RADIUS))
        body.position, shape = self.center, pymunk.Circle(body, BALL_RADIUS)
        shape.elasticity, shape.collision_type = 1.0, COLLISION_TYPE_BALL
        self.space.add(body, shape)
        return body
    
    def create_physics_paddle(self, is_player1):
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        margin = 5
        if is_player1: body.position = (margin + PADDLE_WIDTH / 2, self.center_y)
        else: body.position = (self.width - margin - PADDLE_WIDTH / 2, self.center_y)
        shape = pymunk.Poly.create_box(body, (PADDLE_WIDTH, PADDLE_HEIGHT))
        shape.elasticity = 1.0; shape.collision_type = COLLISION_TYPE_PADDLE
        self.space.add(body, shape)
        return body
    
    def create_walls_and_goals(self):
        static_body = self.space.static_body
        walls = [pymunk.Segment(static_body, (0,0), (self.width,0), 1),
                 pymunk.Segment(static_body, (0,self.height), (self.width,self.height), 1)]
        for w in walls: w.elasticity = 1.0; self.space.add(w)
        goal1 = pymunk.Segment(static_body, (0,0), (0,self.height), 1)
        goal2 = pymunk.Segment(static_body, (self.width,0), (self.width,self.height), 1)
        goal1.sensor = goal2.sensor = True
        goal1.collision_type = goal2.collision_type = COLLISION_TYPE_GOAL
        goal1.player_who_scores, goal2.player_who_scores = 2, 1
        self.space.add(goal1, goal2)
        handler = self.space.add_collision_handler(COLLISION_TYPE_BALL, COLLISION_TYPE_GOAL)
        handler.begin = self.process_goal

    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key == 'w': self.p1_movement = 1
        elif key == 's': self.p1_movement = -1
        if key == 'up': self.p2_movement = 1
        elif key == 'down': self.p2_movement = -1
        return True
    
    def _on_key_up(self, keyboard, keycode):
        key = keycode[1]
        
        if key in ('w', 's'): self.p1_movement = 0
        if key in ('up', 'down'): self.p2_movement = 0
        return True
    
