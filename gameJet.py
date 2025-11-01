import serial
import serial.tools.list_ports
import time
import re
import pygame
import sys
import math
import random
from pygame.locals import *

# ==============================
# CONSTANTS
# ==============================
BAUD = 38400
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
BLACK = (0, 0, 20)
WHITE = (255, 255, 255)
COLOR_WHITE = (255,255,255)
# ==============================
# SERIAL COMMUNICATION
# ==============================
def find_active_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        return None

    def get_com_num(port):
        try:
            return int(''.join(filter(str.isdigit, port.device)))
        except:
            return 0
    ports.sort(key=get_com_num, reverse=True)

    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1
    ports.sort(key=port_priority)

    for port in ports:
        ser = None
        try:
            ser = serial.Serial(port.device, BAUD, timeout=0.1)
            time.sleep(0.1)
            ser.reset_input_buffer()
            valid_count = 0
            start = time.time()
            while time.time() - start < 2.0:
                raw = ser.readline()
                if not raw:
                    continue
                data = raw.decode(errors='ignore').strip()
                if data and "X:" in data and "Y:" in data:
                    x, y = parse_xy(data)
                    if x is not None:
                        valid_count +=1
                        if valid_count >=2:
                            print(f"✅ Found joystick on {port.device}")
                            return ser
            if ser:
                ser.close()
        except:
            if ser:
                try: ser.close()
                except: pass
            continue
    print("\n❌ No joystick found!")
    return None

def parse_xy(line):
    pattern = r"(?:X[:=]\s*(\d+))[^\d]*(?:Y[:=]\s*(\d+))"
    match = re.search(pattern, line)
    if match:
        return int(match.group(1)), int(match.group(2))
    numbers = re.findall(r'\b\d{2,4}\b', line)
    return (int(numbers[0]), int(numbers[1])) if len(numbers) >= 2 else (None, None)
# ==============================
# STARFIELD EFFECT
# ==============================
class StarSimulation:
    def __init__(self, count, width, height):
        self.width = width
        self.height = height
        self.star_cache = {}
        self.stars = []
        self._init_stars(count)

    def _init_stars(self, count):
        for _ in range(count):
            size = random.choices([1, 2, 3], weights=[5,3,2])[0]
            x = random.randint(0, self.width)
            y = random.randint(-self.height*2, self.height)
            speed = random.uniform(40,120)*(1+size*0.25)
            brightness = random.uniform(0.5,1.0)
            color_type = random.choice(['white','blue','pink','lightyellow'])
            self.stars.append((x,y,speed,size,brightness,color_type))

    def move_stars(self, factor, dt):
        for i, (x,y,speed,size,bright,color_type) in enumerate(self.stars):
            y += speed*(1+size*0.25)*dt*factor
            bright += random.uniform(-0.02,0.02)
            bright = max(0.5,min(1.0,bright))
            if y>self.height+20:
                y = random.randint(-50,-10)
                x = random.randint(0,self.width)
                size = random.choices([1,2,3],weights=[5,3,2])[0]
                bright = random.uniform(0.5,1.0)
                color_type = random.choice(['white','blue','pink','lightyellow'])
            self.stars[i]=(x,y,speed,size,bright,color_type)

    def draw(self, surf):
        for x,y,_,size,bright,color_type in self.stars:
            key=(size,int(bright*10),color_type)
            if key not in self.star_cache:
                self.star_cache[key]=self._create_star(size,bright,color_type)
            surf.blit(self.star_cache[key],(x-self.star_cache[key].get_width()//2,
                                            y-self.star_cache[key].get_height()//2))
    def _create_star(self,size,bright,color_type):
        s=size*2+2
        star_surf = pygame.Surface((s,s),pygame.SRCALPHA)
        if color_type=='white':
            color=(int(255*bright),int(255*bright),int(255*bright))
        elif color_type=='blue':
            color=(int(80*bright),int(150*bright),int(255*bright))
        elif color_type=='pink':
            color=(int(255*bright),int(150*bright),int(200*bright))
        else:
            color=(int(255*bright),int(255*bright),int(180*bright))
        if size>1:
            pygame.draw.circle(star_surf,color+(120,),(s//2,s//2),size+1)
        pygame.draw.circle(star_surf,color,(s//2,s//2),size)
        return star_surf
# ==============================
# JET DRAWING
# ==============================
def render_jet(surface,x,y,angle,scale=30):
    if not hasattr(render_jet,'cache'):
        render_jet.cache={}
    angle_deg=int(math.degrees(angle)/5)*5
    key=(scale,angle_deg)
    if key not in render_jet.cache:
        jet_surf = pygame.Surface((scale*2,scale*2),pygame.SRCALPHA)
        points=[(scale,0),(scale*1.2,scale*0.5),(scale*1.1,scale*1.5),(scale,scale*2),
                (scale*0.9,scale*1.5),(scale*0.8,scale*0.5)]
        pygame.draw.polygon(jet_surf,(180,180,200),points)
        pygame.draw.ellipse(jet_surf,(80,200,255),(scale*0.85,scale*0.5,scale*0.3,scale*0.5))
        flame_surf=pygame.Surface((scale//2,scale//2),pygame.SRCALPHA)
        pygame.draw.polygon(flame_surf,(255,140,0,200),[(0,0),(scale//2,scale//4),(0,scale//2)])
        jet_surf.blit(flame_surf,(scale*0.6,scale*1.2),special_flags=pygame.BLEND_ADD)
        rotated=pygame.transform.rotate(jet_surf,angle_deg)
        render_jet.cache[key]=rotated
    rect=render_jet.cache[key].get_rect(center=(x,y))
    surface.blit(render_jet.cache[key],rect.topleft)
    return rect
# ==============================
# HUD + Joystick
# ==============================
class HUDDisplay:
    def __init__(self,width,height):
        self.width=width
        self.height=height
        self.font=pygame.font.SysFont('Arial',24,bold=True)
        self.speed_lbl=self.font.render("Speed:",True,COLOR_WHITE)
        self.score_lbl=self.font.render("Score:",True,COLOR_WHITE)
        self.bg=pygame.Surface((width,50),pygame.SRCALPHA)
        pygame.draw.rect(self.bg,(0,0,0,160),(0,0,width,50),border_radius=10)
    def render(self,surf,speed,score):
        surf.blit(self.bg,(10,10))
        spd_text=self.font.render(f"{abs(speed):.1f}",True,(180,220,255))
        scr_text=self.font.render(f"{int(score)}",True,(255,220,180))
        shadow_color=(0,0,0)
        surf.blit(self.font.render(f"{abs(speed):.1f}",True,shadow_color),(101,21))
        surf.blit(self.font.render(f"{int(score)}",True,shadow_color),(self.width-79,21))
        surf.blit(self.speed_lbl,(20,20))
        surf.blit(spd_text,(100,20))
        surf.blit(self.score_lbl,(self.width-150,20))
        surf.blit(scr_text,(self.width-80,20))

def draw_joystick(surface,center,x_val,y_val,prev_pos=None):
    max_radius=40
    joy_range=20
    joy_x=int(center[0]+((x_val-512)/512.0)*joy_range)
    joy_y=int(center[1]+((y_val-512)/512.0)*joy_range)
    if prev_pos:
        joy_x=int(prev_pos[0]*0.8+joy_x*0.2)
        joy_y=int(prev_pos[1]*0.8+joy_y*0.2)
    for angle in range(0,360,15):
        rad=math.radians(angle)
        x=int(center[0]+max_radius*math.cos(rad))
        y=int(center[1]+max_radius*math.sin(rad))
        pygame.draw.circle(surface,(100,100,100),(x,y),2)
    dot_surf=pygame.Surface((20,20),pygame.SRCALPHA)
    for i in range(10,0,-1):
        color=(255,255,255,int(25*i))
        pygame.draw.circle(dot_surf,color,(10,10),i)
    surface.blit(dot_surf,(joy_x-10,joy_y-10))
    return (joy_x,joy_y)
# ==============================
# GAME LOOP
# ==============================
def start_sim(serial_port):
    pygame.init()
    screen=pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.DOUBLEBUF|pygame.HWSURFACE)
    pygame.display.set_caption("Jet Fighter Simulator")
    pygame.event.set_allowed([QUIT,KEYDOWN])
    stars=StarSimulation(200,WINDOW_WIDTH,WINDOW_HEIGHT)
    hud=HUDDisplay(WINDOW_WIDTH,WINDOW_HEIGHT)
    clock=pygame.time.Clock()
    jet_state={'x':WINDOW_WIDTH//2,'y':WINDOW_HEIGHT*2//3,'roll':0.0,'pitch':0.0,'velocity_x':0.0,'velocity_y':0.0,'speed':0.0,'size':30,'roll_max':45.0,'pitch_max':30.0,'max_speed':500.0}
    game_state={'score':0,'x_val':512,'y_val':512,'running':True}
    joy_center=(80,WINDOW_HEIGHT-80)
    last_time=time.time()
    frame_count=0
    fps_update_time=last_time
    print("🎮 Jet Fighter Simulator started")
    while game_state['running']:
        current_time=time.time()
        dt=min(current_time-last_time,0.1)
        last_time=current_time
        frame_count+=1
        if current_time-fps_update_time>=1.0:
            fps=frame_count/(current_time-fps_update_time)
            if fps<55: print(f"Performance: {fps:.1f} FPS")
            frame_count=0
            fps_update_time=current_time
        game_state['running']=handle_events(game_state,jet_state)
        update_game_state(serial_port,game_state,jet_state,dt)
        render_frame(screen,stars,hud,game_state,jet_state,joy_center,dt)
        clock.tick(60)
    serial_port.close()
    pygame
