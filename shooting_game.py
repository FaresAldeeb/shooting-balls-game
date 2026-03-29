import tkinter as tk
from tkinter import ttk
import math
import random
import time

# --- Game settings ---
WIDTH, HEIGHT = 600, 400                  # Canvas size (required 600x400)
GRAVITY = 1.5                             # Gravity value (pixels added to vy each frame)


# --- Ball class ---
class Ball:
    def __init__(self, canvas):
        self.canvas = canvas
        self.r = random.randint(15, 25)   # Random radius (ball size)
        x = random.randint(250, WIDTH - self.r)     # Random start X (more to the right side)
        y = random.randint(50, HEIGHT // 2)         # Random start Y (upper half)
        COLORS = ["red", "blue", "green", "yellow"]

        self.id = canvas.create_oval(
            x - self.r, y - self.r,       # Left-top corner of oval bounding box
            x + self.r, y + self.r,       # Right-bottom corner of oval bounding box
            fill=random.choice(COLORS),
            outline="black"
        )

        # Ball Speed
        self.dx = random.choice([-3, -2, 2, 3])     # Random horizontal speed (left/right)
        self.dy = random.choice([-3, -2, 2, 3])     # Random vertical speed (up/down)

    def move(self):
        self.canvas.move(self.id, self.dx, self.dy)
        coords = self.canvas.coords(self.id)        # Get ball position [x1,y1,x2,y2]

        # If ball hits left wall (x1<=0) OR right wall (x2>=WIDTH), reverse dx (bounce)
        if coords[0] <= 0 or coords[2] >= WIDTH: self.dx = -self.dx

        # If ball hits top wall (y1<=0) OR bottom wall (y2>=HEIGHT), reverse dy (bounce)
        if coords[1] <= 0 or coords[3] >= HEIGHT: self.dy = -self.dy


# --- Bullet class ---
class Bullet:
    def __init__(self, canvas, x, y, angle, power): # Create bullet at (x,y) with angle & power
        self.canvas = canvas                         # Save canvas so bullet can move/draw
        self.id = canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="black")  # Draw bullet circle

        rad = math.radians(angle)                    # Convert degrees to radians for sin/cos

        self.vx = power * math.cos(rad)              # x velocity component (how fast it moves right)
        self.vy = -power * math.sin(rad)             # y velocity component (negative = goes up in Tkinter)

    def move(self):
        self.canvas.move(self.id, self.vx, self.vy)  # Move bullet by current vx, vy
        self.vy += GRAVITY                           # Add gravity -> bullet starts falling down over time
        coords = self.canvas.coords(self.id)         # Get bullet position [x1,y1,x2,y2]

        # Return True if bullet leaves screen (so we delete it)
        return coords[2] < 0 or coords[0] > WIDTH or coords[1] > HEIGHT


# --- Game class ---
class ShootingGame:
    def __init__(self, root):
        self.root = root
        self.root.title("HCI 418 Project: Shooting Balls Game")

        self.balls = []
        self.bullets = []
        self.score = 0
        self.level = 0
        self.running = False
        self.last_shot = 0

        # Time tracking
        self.start_time = None
        self.elapsed_time = 0

        self.setup_gui()
        self.update_cannon()
        self.loop()

    def setup_gui(self):
        tk.Label(
            self.root,
            text="HCI 418 Project: Shooting Balls Game",
            font=("Arial", 16, "bold"),
            bg="#333",
            fg="white"
        ).pack(fill=tk.X)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        panel = tk.Frame(main_frame, width=220, bg="#b5c7ff", padx=10)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            panel,
            text="Control Panel",
            bg="#b5c7ff",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Button(panel, text="Start / Resume", command=self.start).pack(fill=tk.X, pady=3)
        ttk.Button(panel, text="Pause", command=lambda: setattr(self, 'running', False)).pack(fill=tk.X, pady=3)
        ttk.Button(                                  # Reset button (reset then start again)
            panel,
            text="Reset",
            command=lambda: (self.reset(), self.start())
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            panel,
            text="Stop",
            command=lambda: setattr(self, 'running', False, self.reset())
        ).pack(fill=tk.X, pady=3)

        tk.Label(panel, text="Angle", bg="#b5c7ff").pack()          # Angle label
        self.angle = tk.DoubleVar(value=45)                         # Default angle = 45 degrees
        tk.Scale(                                                   # Angle slider
            panel,
            from_=10,
            to=80,
            orient=tk.HORIZONTAL,
            variable=self.angle,
            command=self.update_cannon
        ).pack(fill=tk.X)

        tk.Label(panel, text="Strength", bg="#b5c7ff").pack()       # Strength label
        self.power = tk.DoubleVar(value=30)                         # Default power = 30
        tk.Scale(                                                   # Strength slider
            panel,
            from_=10,
            to=60,
            orient=tk.HORIZONTAL,
            variable=self.power,
            command=self.update_cannon
        ).pack(fill=tk.X)

        tk.Label(panel, text="Cannon Height", bg="#b5c7ff").pack(pady=(10, 0))  # Cannon height label
        self.cannon_height = tk.DoubleVar(value=HEIGHT - 40)        # Default cannon y position

        tk.Scale(
            panel,
            from_=HEIGHT - 40,                                      # lowest position (near bottom)
            to=HEIGHT - 300,                                        # highest position
            orient=tk.VERTICAL,
            variable=self.cannon_height,
            command=self.update_cannon
        ).pack(pady=5)

        ttk.Button(panel, text="Shooting!", command=self.shoot).pack(fill=tk.X, pady=15)  # Shoot button

        self.canvas = tk.Canvas(main_frame, width=WIDTH, height=HEIGHT, bg="#b5c7ff")  # Game area canvas
        self.canvas.pack(side=tk.RIGHT, padx=10, pady=10)            # Put canvas on right with padding

        self.hud = tk.Label(self.root, bg="#222", fg="white", font=("Arial", 12))  # Bottom status bar
        self.hud.pack(fill=tk.X)                                     # Stretch across bottom

    def start(self):
        if self.running:                             # If already running, this acts like "next level"
            self.level += 1                          # Increase level
            self.spawn_balls()                       # Spawn more balls
        else:
            self.running = True                      # Start running

            if self.start_time is None:              # If time not started yet
                self.start_time = time.time()        # Save current time

            if not self.balls:                       # If there are no balls yet
                if self.level == 0: self.level = 1   # Start at level 1
                self.spawn_balls()                   # Create balls

    def restart(self):
        self.reset()                                 # Reset game
        self.start()                                 # Start game again

    def reset(self):
        self.running = False                         # Stop movement
        self.level = 0                               # Reset level
        self.score = 0                               # Reset score
        self.balls.clear()                           # Remove all balls from list
        self.bullets.clear()                         # Remove all bullets from list
        self.canvas.delete("all")                    # Remove everything drawn on canvas

        self.start_time = None                       # Reset timer start time
        self.elapsed_time = 0                        # Reset shown time to 0

        self.update_cannon()                         # Redraw the cannon after clearing canvas

    def spawn_balls(self):
        for _ in range(3 + self.level):              # Number of balls = 3 + level
            self.balls.append(Ball(self.canvas))     # Create a Ball and store it

    def update_cannon(self, _=None):
        self.pivot = (10, self.cannon_height.get())  # Pivot point (x fixed, y from slider)

        rad = math.radians(self.angle.get())         # Convert current angle to radians
        length = self.power.get()                    # Use power also as cannon length

        x2 = self.pivot[0] + length * math.cos(rad)  # End x of cannon line
        y2 = self.pivot[1] - length * math.sin(rad)  # End y of cannon line (minus = up)

        self.canvas.delete("gun")                    # Delete old cannon drawings (tag "gun")
        self.canvas.create_line(                     # Draw cannon line
            self.pivot[0], self.pivot[1], x2, y2,
            width=6,
            tag="gun"
        )
        self.canvas.create_oval(                     # Draw cannon base circle at pivot
            self.pivot[0] - 8, self.pivot[1] - 8,
            self.pivot[0] + 8, self.pivot[1] + 8,
            fill="black",
            tag="gun"
        )

    def shoot(self):
        # If game not running OR cooldown not finished -> do nothing
        if not self.running or time.time() - self.last_shot < 0.5: return

        self.last_shot = time.time()                 # Save current time as last shot

        rad = math.radians(self.angle.get())         # Angle in radians
        p = self.power.get()                         # Power value

        x = self.pivot[0] + p * math.cos(rad)        # Bullet starts at cannon tip x
        y = self.pivot[1] - p * math.sin(rad)        # Bullet starts at cannon tip y

        self.bullets.append(Bullet(self.canvas, x, y, self.angle.get(), p))  # Create and store bullet

    def loop(self):
        if self.running:                             # Only update game if running
            if self.start_time:                      # If timer started
                self.elapsed_time = int(time.time() - self.start_time)  # seconds since start

            self.check_ball_collision()              # Handle ball-ball collisions

            for b in self.balls:                     # Move each ball
                b.move()

            for b in self.bullets[:]:                # Loop over a copy so we can remove bullets safely
                if b.move() or self.check_hit(b):    # If bullet left screen or hit a ball
                    self.canvas.delete(b.id)         # Delete bullet drawing
                    self.bullets.remove(b)           # Remove bullet from list

            if not self.balls:                       # If all balls destroyed
                self.start()                         # Go to next level (spawn again)

        self.hud.config(                             # Update bottom HUD text
            text=f"Score: {self.score}    Level: {self.level}    Time: {self.elapsed_time}s"
        )

        self.root.after(30, self.loop)               # Call loop again after 30 ms (~33 FPS)

    def check_ball_collision(self):
        for i in range(len(self.balls)):             # For each ball i
            for j in range(i + 1, len(self.balls)):  # Compare with ball j after i (avoid duplicates)
                b1, b2 = self.balls[i], self.balls[j]  # Two balls
                c1, c2 = self.canvas.coords(b1.id), self.canvas.coords(b2.id)  # Their coords

                dist = math.hypot(                   # Distance between the two centers
                    (c1[0] + c1[2]) / 2 - (c2[0] + c2[2]) / 2,
                    (c1[1] + c1[3]) / 2 - (c2[1] + c2[3]) / 2
                )

                if dist < (b1.r + b2.r):             # If centers are closer than radii sum -> collision
                    # Ball 1 takes Ball 2 speed (swap velocities)
                    b1.dx, b2.dx = b2.dx, b1.dx
                    b1.dy, b2.dy = b2.dy, b1.dy

    def check_hit(self, bullet):
        b_c = self.canvas.coords(bullet.id)          # Bullet coords
        bx, by = (b_c[0] + b_c[2]) / 2, (b_c[1] + b_c[3]) / 2  # Bullet center point

        for ball in self.balls:                      # Check bullet against each ball
            c = self.canvas.coords(ball.id)          # Ball coords

            # If bullet center is inside the ball bounding box -> hit
            if c[0] < bx < c[2] and c[1] < by < c[3]:
                self.canvas.delete(ball.id)          # Remove ball drawing
                self.balls.remove(ball)              # Remove ball from list
                self.score += 10                     # Add score for hit
                return True                          # Tell loop bullet should be removed

        return False                                 # No hit


if __name__ == "__main__":
    root = tk.Tk()                                   # Create main Tk window
    ShootingGame(root)                               # Create the game inside the window
    root.mainloop()                                  # Start GUI event loop (keeps window running)
