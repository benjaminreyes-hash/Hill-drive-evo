import pygame
import random
import sys
import math
from typing import Tuple, List

# ------------------------------
# CONFIGURACIÓN GLOBAL (FÁCIL AJUSTE)
# ------------------------------
SCREEN_W, SCREEN_H = 1000, 600
FPS = 60

# debug
DEBUG_SPAWN = False
DEBUG_FORCE_SPAWN = True
DEBUG_DRAW_PHYSICS = False # [MODIFICADO] Desactivado, ya no se usa la física compleja

# Tiles / estética
TILE_SIZE = 64
INITIAL_TILES = 800
TERRAIN_Y = 400

# Jugador
PLAYER_SCREEN_X = 150
# (Cerca de la línea 33)
CAR_SCALE = 0.38 
CAR_Y_OFFSET = 54 # [NUEVO] Offset vertical para alinear el coche con el terreno
PLAYER_WIDTH_SCALED = int(260 * CAR_SCALE)
PLAYER_HEIGHT_SCALED = int(90 * CAR_SCALE)
# [MODIFICADO] PLAYER_CENTER_Y_OFFSET eliminado, ya no es necesario

# Física del Coche (Simplificada a 2D Runner)
# [MODIFICADO] PLAYER_MASS eliminado
GRAVITY = 900.0
ACCEL_GROUND = 600.0 # Aceleración en el suelo
FRICTION_GROUND = 0.98 # Reducción de velocidad en el suelo
AIR_RESISTANCE = 0.995 # Reducción de velocidad en el aire


# Fuel y moneda
MAX_FUEL = 100.0
FUEL_DECAY_PER_SEC = 3.0
FUEL_PICKUP = 30.0
COIN_SPAWN_CHANCE = 0.50
FUEL_SPAWN_CHANCE = 0.05
NOS_SPAWN_CHANCE = 0.10
NOS_DURATION = 20.0
NOS_MULTIPLIER = 2.5
COLLECTIBLE_MIN_SEPARATION_TILES = 3
COIN_MIN_SEPARATION_TILES = 1
INITIAL_STREET_TILES = 20
STREET_FULL_LENGTH = True
COLLECTIBLE_VERTICAL_OFFSET = -60 # [MODIFICADO] Reducido de -100 para estar más cerca del suelo

# [NUEVO] Configuración de Decoraciones
DECORATION_SPAWN_CHANCE = 0.1 # 10% de chance por tile elegible
DECORATION_MIN_SEPARATION_TILES = 5 # Mínimo 5 tiles entre árboles
DECORATION_X_OFFSET_PX = 40 # Cuán a la derecha del inicio del tile aparece
TREE_SCALE = 0.4 # [NUEVO] Escala para los árboles (ej: 0.6 = 60%). ¡Ajusta este valor a tu gusto!
DECORATION_SPAWN_CHANCE = 0.1 
DECORATION_MIN_SEPARATION_TILES = 5
# Movimiento
CAMERA_SPEED_PX_PER_SEC = 300.0
SPAWN_AHEAD_TILES = (SCREEN_W // TILE_SIZE) + 8

# Sonidos
MUSIC_VOL = 0.25
SFX_VOL = 0.8

# ------------------------------
# UTILIDADES (carga robusta de recursos) - (Mantenidas)
# ------------------------------
# ... (load_image, load_sound, load_sound_cached, load_music sin cambios) ...

def load_image(path: str, size: Tuple[int, int] = None, alpha=True, fallback_color=(160,120,60)):
    try:
        if alpha:
            img = pygame.image.load(path).convert_alpha()
        else:
            img = pygame.image.load(path).convert()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        # fallback surface (visual pero no crashea)
        surf = pygame.Surface(size if size else (64,64), pygame.SRCALPHA if alpha else 0)
        surf.fill(fallback_color)
        pygame.draw.rect(surf, (0,0,0), surf.get_rect(), 2)
        return surf


def load_sound(path: str):
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(SFX_VOL)
        return s
    except Exception:
        # fallback: silent Sound-like object
        class Silent:
            def play(self, *args, **kwargs): pass
            def set_volume(self, *a, **k): pass
        return Silent()


_sound_cache = {}
def load_sound_cached(path: str):
    if path in _sound_cache:
        return _sound_cache[path]
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(SFX_VOL)
    except Exception:
        class Silent:
            def play(self, *a, **k): pass
            def set_volume(self, *a, **k): pass
        s = Silent()
    _sound_cache[path] = s
    return s


def load_music(path: str):
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOL)
        return True
    except Exception:
        return False

# ------------------------------
# SPRITES
# ------------------------------
class Collectible(pygame.sprite.Sprite):
    def __init__(self, world_x: float, world_y: float, image: pygame.Surface, kind: str):
        super().__init__()
        self.base_image = image
        self.image = image
        self.rect = self.image.get_rect()
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.kind = kind  # 'coin' | 'fuel' | 'nos'
        self.collected = False
        self._anim = 0.0

    def update_screen_pos(self, camera_x: float):
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)
        self.rect.topleft = (sx, sy)

    def animate(self, dt: float):
        if self.kind == 'coin':
            self._anim += 3.5 * dt
            self.image = self.base_image
            self.rect = self.image.get_rect()

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)
        if self.kind == 'coin':
            offset = int(6 * (0.5 + 0.5 * math.sin(self._anim)))
            surface.blit(self.image, (sx, sy - offset))
        else:
            surface.blit(self.image, (sx, sy))

    def collect(self):
        self.collected = True
        self.kill()


# [NUEVO] Clase para las decoraciones (árboles)
class Decoration(pygame.sprite.Sprite):
    def __init__(self, world_x: float, world_y_base: float, image: pygame.Surface):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.world_x = float(world_x) # Posición X (topleft)
        self.world_y_base = float(world_y_base) # Posición Y (base)
        # Colocamos la base del sprite en la Y del terreno
        self.rect.bottomleft = (int(self.world_x), int(self.world_y_base))

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = int(self.world_x - camera_x)
        # El top Y es la base Y menos la altura de la imagen
        sy = int(self.world_y_base - self.rect.height) 
        surface.blit(self.image, (sx, sy))

    def update_screen_pos(self, camera_x: float):
        # Actualiza el rect en pantalla (para culling/limpieza)
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y_base - self.rect.height)
        self.rect.topleft = (sx, sy)


# ------------------------------
# TERRAIN (tiles planos con generación infinita)
# ------------------------------
class Terrain:
    def __init__(self, tile_size:int, initial_tiles:int, base_y:int, ground_img:pygame.Surface):
        self.tile_size = tile_size
        self.base_y = base_y
        self.tiles = [self.base_y for _ in range(initial_tiles)]
        self.ground_img = ground_img
        self.add_random_ramps(0, initial_tiles, chance=0.04)

    def tile_y_at_pixel_x(self, world_x_px:int) -> int:
        tile_idx = max(0, world_x_px // self.tile_size)
        if tile_idx >= len(self.tiles):
            self.ensure_tiles(tile_idx)
        return self.tiles[tile_idx]

    # [MODIFICADO] Eliminado terrain_angle_at_pixel_x, ya no se usa
    
    # [MODIFICADO] Mantenido, es crucial para la física suave en Y
    def terrain_interpolated_y(self, world_x_px: int) -> int:
        tile_idx = max(0, world_x_px // self.tile_size)
        if tile_idx + 1 >= len(self.tiles):
            self.ensure_tiles(tile_idx + 1)

        y0 = self.tiles[tile_idx]
        y1 = self.tiles[tile_idx + 1]
        
        # Posición relativa dentro del tile (0 a 1)
        t = (world_x_px % self.tile_size) / self.tile_size
        
        interpolated_y = y0 + (y1 - y0) * t
        return int(interpolated_y)

    def ensure_tiles(self, idx: int):
        if idx < len(self.tiles):
            return
        
        # generar en chunks para eficiencia
        while len(self.tiles) <= idx:
            # Generar el terreno faltante usando la lógica de chunks (rampas)
            self.generate_chunk(100)
    
    def generate_chunk(self, count:int):
        i = 0
        while i < count:
            if random.random() < 0.08: # Aumento la chance de rampas
                length = random.randint(6, 18) # Rampas más largas
                height_change = random.choice([
                    random.randint(-150, -48), # Subida significativa
                    random.randint(48, 150) # Bajada significativa
                ])
                for r in range(length):
                    if i >= count:
                        break
                    
                    frac = r / length
                    slope = int(frac * height_change)
                    
                    base_y = self.tiles[-1] if self.tiles else self.base_y
                    
                    new_y = base_y + slope
                    
                    if r > 0:
                        prev_y = self.tiles[-1]
                        max_change = 10
                        if abs(new_y - prev_y) > max_change:
                            new_y = prev_y + math.copysign(max_change, new_y - prev_y)
                    
                    jitter = random.randint(-2, 2)
                    self.tiles.append(new_y + jitter)
                    i += 1
                continue
            
            # normal tile
            base_y = self.tiles[-1] if self.tiles else self.base_y
            jitter = random.randint(-2, 2)
            max_flat_change = 4
            if abs(base_y + jitter - self.tiles[-1]) > max_flat_change:
                jitter = math.copysign(max_flat_change - 1, base_y + jitter - self.tiles[-1])
            
            self.tiles.append(base_y + jitter)
            i += 1
            
    def add_random_ramps(self, start_idx:int = 0, end_idx: int = None, chance: float = 0.02):
        if end_idx is None:
            end_idx = len(self.tiles)
        i = start_idx
        while i < end_idx - 1:
            if random.random() < chance:
                length = random.randint(4, 12)
                height_change = random.randint(-48, -12) # Solo subidas
                for r in range(length):
                    idx = i + r
                    if idx >= end_idx:
                        break
                    
                    frac = (r + 1) / length
                    slope = int(frac * height_change)
                    jitter = random.randint(-2, 2)
                    
                    base_y = self.tiles[i-1] if i > 0 else self.base_y 
                    
                    self.tiles[idx] = base_y + slope + jitter
                i += length
            else:
                i += 1
    
    def draw(self, surf:pygame.Surface, camera_x:float, player_tile: int = None, street_img: pygame.Surface = None):
        screen_tile_start = int(camera_x) // self.tile_size
        offset_x = int(camera_x) % self.tile_size
        tiles_on_screen = surf.get_width() // self.tile_size + 3
        
        for i in range(tiles_on_screen):
            tile_idx = screen_tile_start + i
            if tile_idx >= len(self.tiles):
                self.generate_chunk(50) 
            
            ty = self.tiles[tile_idx]
            screen_x = i * self.tile_size - offset_x
            
            # [MODIFICADO] Lógica de dibujado mantenida, pero STREET_FULL_LENGTH = True
            # asegura que 'calle.png' (street_img) se use siempre arriba.
            used_top_img = None
            if street_img is not None and STREET_FULL_LENGTH:
                used_top_img = street_img
            elif tile_idx < INITIAL_STREET_TILES and street_img is not None:
                used_top_img = street_img
            
            top_img = used_top_img if used_top_img else self.ground_img
            surf.blit(top_img, (screen_x, ty))

            # Dibujar el resto del terreno por debajo (ground.png)
            y = ty + self.tile_size
            while y < surf.get_height():
                surf.blit(self.ground_img, (screen_x, y))
                y += self.tile_size


# ------------------------------
# PLAYER CAR BODY (Simplificado, sin rotación)
# ------------------------------
# [MODIFICADO] Clase CarBody simplificada
class CarBody:
    """Maneja el sprite visual del coche (sin rotación)."""
    def __init__(self, base_image: pygame.Surface):
        self.base_image = base_image
        self.image = base_image
        self.rect = self.image.get_rect()
        # self.angle ya no es necesario
        
    def set_position(self, screen_x: int, screen_y_bottom: int):
        """Establece la posición (base) del coche en la pantalla."""
        # screen_x es el centro, screen_y_bottom es la base (ruedas)
        self.rect.midbottom = (screen_x, screen_y_bottom)


# ------------------------------
# PLAYER (jugador - con física simplificada)
# ------------------------------
class Player:
    def __init__(self, screen_x:int, car_body:CarBody):
        # Propiedades Físicas
        self.world_x = 0.0
        # [MODIFICADO] world_y ahora representa la BASE del coche (ruedas)
        self.world_y = TERRAIN_Y 
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.on_ground = True
        
        # Propiedades de Juego
        self.screen_x = screen_x # X fija en la pantalla
        self.car_body = car_body
        self.rect = self.car_body.rect # Usamos el rect del cuerpo para colisiones
        self.coins = 0
        self.fuel = MAX_FUEL
        self.speed_multiplier = 1.0
        self.nos_time_left = 0.0
        
        # Posición inicial
        self.world_x = self.screen_x
        # [MODIFICADO] Pasa la Y (base) a set_position
        self.car_body.set_position(self.screen_x, int(self.world_y))

    # [MODIFICADO] Método place_on_terrain eliminado.
    # La física ahora se maneja completamente en update().

    # [MODIFICADO] Método update reescrito para física 2D simple
    def update(self, dt: float, keys: List[bool], terrain: 'Terrain'):
        
        # --- Lógica de NOS
        if self.nos_time_left > 0:
            self.nos_time_left -= dt
            self.speed_multiplier = NOS_MULTIPLIER
        else:
            self.speed_multiplier = 1.0

        # --- Obtener Y del terreno
        # El punto de contacto es el centro X del coche
        contact_x = int(self.world_x)
        terrain_y = terrain.terrain_interpolated_y(contact_x)
        
        # --- Física Vertical (Gravedad y Colisión con Suelo)
        
        # Si estamos en el aire (nuestra base Y está por encima de la Y del terreno)
        if self.world_y < terrain_y - 1: # 1px de umbral
            self.on_ground = False
            self.velocity_y += GRAVITY * dt
        else:
            # Estamos en el suelo o hundiéndonos
            self.world_y = terrain_y # Ajustar exactamente al suelo
            self.velocity_y = 0.0
            self.on_ground = True

        # Actualizar posición Y basada en velocidad vertical
        self.world_y += self.velocity_y * dt
        
        # Segunda comprobación (si la velocidad nos hundió este frame)
        if self.world_y > terrain_y:
            self.world_y = terrain_y
            self.velocity_y = 0.0
            self.on_ground = True
            
        # --- Física Horizontal (Aceleración de conducción)
        accel_dir = 0
        if keys[pygame.K_d]:
            accel_dir = 1
        elif keys[pygame.K_a]:
            accel_dir = -1
        
        # Solo se puede acelerar si hay combustible
        if self.fuel > 0 and accel_dir != 0:
            force_x = 0.0
            if self.on_ground:
                # Aceleración normal o reversa
                force_x = ACCEL_GROUND * accel_dir * self.speed_multiplier
                if accel_dir < 0:
                    force_x *= 0.5 # Menos fuerza en reversa
                
                # Consumo de combustible (solo al acelerar hacia adelante)
                if accel_dir > 0:
                    self.fuel -= FUEL_DECAY_PER_SEC * dt * 0.5 * self.speed_multiplier
            
            self.velocity_x += force_x * dt

        # Aplicar fricción/resistencia
        if self.on_ground:
            self.velocity_x *= FRICTION_GROUND
        else:
            self.velocity_x *= AIR_RESISTANCE
            
        # Actualizar posición X
        self.world_x += self.velocity_x * dt
        
        # --- Actualizar el CarBody (Visual)
        visual_y = int(self.world_y + CAR_Y_OFFSET)
        self.car_body.set_position(self.screen_x, visual_y)
        
        # --- Actualizar el self.rect para colisiones
        # (El rect de CarBody está en coordenadas de pantalla,
        # lo cual es correcto para colisionar con Collectibles)
        self.rect = self.car_body.rect


    def draw(self, surf:pygame.Surface):
        # El CarBody ya dibuja el sprite en la posición correcta (midbottom)
        surf.blit(self.car_body.image, self.car_body.rect.topleft)
        
        # [MODIFICADO] Dibujo de debug eliminado
        # if DEBUG_DRAW_PHYSICS: ...


# ------------------------------
# HUD y Menú (UI simple y profesional) - (Mantenidas)
# ------------------------------
# ... (HUD, Button sin cambios) ...

class HUD:
    def __init__(self, font:pygame.font.Font):
        self.font = font

    def draw(self, surf:pygame.Surface, player:Player):
        # Monedas
        txt = self.font.render(f"Monedas: {player.coins}", True, (255,215,0))
        surf.blit(txt, (20, 20))
        # Distancia
        dist_txt = self.font.render(f"Distancia: {int(player.world_x / 100)}m", True, (255, 255, 255))
        surf.blit(dist_txt, (SCREEN_W - dist_txt.get_width() - 20, 20))
        
        # Barra de fuel
        bx, by, bw, bh = 20, 60, 220, 20
        pygame.draw.rect(surf, (0,0,0), (bx, by, bw, bh), 2)
        fill = int((player.fuel / MAX_FUEL) * (bw - 4))
        col = (255, 60, 60) if player.fuel < 30 else (0,160,0)
        pygame.draw.rect(surf, col, (bx + 2, by + 2, fill, bh - 4))
        # Porcentaje
        perc = self.font.render(f"{int(player.fuel)}%", True, (255,255,255))
        surf.blit(perc, (bx + bw + 10, by - 1))
        # NOS status
        if getattr(player, 'nos_time_left', 0.0) > 0:
            nos_txt = self.font.render(f"NOS: {int(player.nos_time_left)}s", True, (120,200,255))
            surf.blit(nos_txt, (20, 90))


class Button:
    def __init__(self, rect:pygame.Rect, text:str, font:pygame.font.Font, bg=(40,40,40), fg=(255,255,255)):
        self.rect = rect
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg

    def draw(self, surf:pygame.Surface):
        pygame.draw.rect(surf, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, (0,0,0), self.rect, 2, border_radius=8)
        txt = self.font.render(self.text, True, self.fg)
        surf.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# ------------------------------
# GAME (control principal) - (Ajustada para la nueva física)
# ------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Hill Drive Evo 9 - Profesional")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)

        # assets (carga con fallback)
        self.sky = load_image("assets/sky.png", (SCREEN_W * 2, SCREEN_H), alpha=False, fallback_color=(120,200,255))
        self.ground = load_image("assets/ground.png", (TILE_SIZE, TILE_SIZE), alpha=False, fallback_color=(160,100,50))
        self.street_img = load_image("assets/calle.png", (TILE_SIZE, TILE_SIZE), alpha=False, fallback_color=(120,120,120))
        
        # Coche: cargado y escalado
        car_original_img = load_image("assets/lancer.png", size=None, alpha=True, fallback_color=(220,220,220))
        try:
            ow, oh = car_original_img.get_size()
            # [MODIFICADO] Usa la constante CAR_SCALE actualizada (0.45)
            tw = max(1, int(ow * CAR_SCALE))
            th = max(1, int(oh * CAR_SCALE))
            self.car_img = pygame.transform.scale(car_original_img, (tw, th))
        except Exception:
            self.car_img = car_original_img
            
        self.coin_img = load_image("assets/coin.png", (36,36), alpha=True, fallback_color=(240,220,20))
        self.nos_img = load_image("assets/nos.png", (40,40), alpha=True, fallback_color=(120,200,255))
        self.fuel_img = load_image("assets/fuel.png", (40,40), alpha=True, fallback_color=(200,0,0))
        
        # [NUEVO] Carga de assets de decoración
        # (Línea ~548)
        self.fuel_img = load_image("assets/fuel.png", (40,40), alpha=True, fallback_color=(200,0,0))
        
        # [NUEVO] Carga de assets de decoración (MODIFICADO para escalar)
        try:
            tree1_original = load_image("assets/arbol1.png", size=None, alpha=True, fallback_color=(40, 100, 40))
            ow, oh = tree1_original.get_size()
            tw, th = max(1, int(ow * TREE_SCALE)), max(1, int(oh * TREE_SCALE))
            self.tree1_img = pygame.transform.scale(tree1_original, (tw, th))
        except Exception:
            # Fallback con un tamaño fijo razonable si falla
            self.tree1_img = load_image("assets/arbol1.png", size=(80, 160), alpha=True, fallback_color=(40, 100, 40)) 

        try:
            tree2_original = load_image("assets/arbol2.png", size=None, alpha=True, fallback_color=(60, 120, 60))
            ow, oh = tree2_original.get_size()
            tw, th = max(1, int(ow * TREE_SCALE)), max(1, int(oh * TREE_SCALE))
            self.tree2_img = pygame.transform.scale(tree2_original, (tw, th))
        except Exception:
            # Fallback con un tamaño fijo razonable si falla
            self.tree2_img = load_image("assets/arbol2.png", size=(80, 160), alpha=True, fallback_color=(60, 120, 60))


        # sonidos
        self.sfx_pick = load_sound_cached("assets/sfx_pickup.wav")
        self.sfx_gameover = load_sound_cached("assets/sfx_gameover.wav")
        music_loaded = load_music("assets/music.ogg")
        if music_loaded:
            try:
                pygame.mixer.music.play(-1)
            except Exception:
                pass

        # instancias
        self.terrain = Terrain(TILE_SIZE, INITIAL_TILES, TERRAIN_Y, self.ground)
        self.car_body = CarBody(self.car_img)
        self.player = Player(PLAYER_SCREEN_X, self.car_body)
        self.hud = HUD(self.font)
        self.camera_x = 0.0
        
        # [NUEVO] Grupos para decoraciones
        self.decorations = pygame.sprite.Group()
        self.decoration_tiles = set()
        self.last_decoration_tile = -999
        self.tree_toggle = False # Para alternar arbol1/arbol2

        # collectibles
        self.collectibles = pygame.sprite.Group()
        self.collectible_tiles = set()
        self.last_collectible_tile = -999
        self.last_coin_tile = -999

        self.spawn_initial_collectibles()
        
        

        # UI: menu buttons
        btn_w, btn_h = 220, 52
        self.btn_play = Button(pygame.Rect((SCREEN_W//2 - btn_w//2, SCREEN_H//2 - 70, btn_w, btn_h)), "JUGAR", self.font)
        self.btn_quit = Button(pygame.Rect((SCREEN_W//2 - btn_w//2, SCREEN_H//2 + 0, btn_w, btn_h)), "SALIR", self.font)

        # estado
        self.running = True
        self.in_menu = True
        self.game_over = False

    def spawn_initial_collectibles(self):
        # Resetear el estado de los coleccionables
        self.collectibles.empty()
        self.collectible_tiles.clear()
        self.last_collectible_tile = -999
        self.last_coin_tile = -999
        
        # [MODIFICADO] La altura Y se calcula dinámicamente en spawn_collectible_at_tile
        # por lo que aquí solo iteramos
        
        end = min(len(self.terrain.tiles), 300)
        
        for tile_idx in range(10, end):
            self.spawn_collectible_at_tile(tile_idx)
            # [NUEVO] También spawnear decoraciones iniciales
            self.spawn_decoration_at_tile(tile_idx)


    def force_spawn_near_player(self):
        camera_tile = int(self.camera_x) // TILE_SIZE
        start = camera_tile + 3
        
        for i, t in enumerate(range(start, start + 16)):
            if t in self.collectible_tiles:
                continue
            
            kind = None
            if i % 11 == 0:
                kind = 'nos'
            elif i % 5 == 0:
                kind = 'fuel'
            elif i % 2 == 0:
                kind = 'coin'
            
            if kind is None:
                continue
            
            wx = t * TILE_SIZE + TILE_SIZE // 2
            
            # [MODIFICADO] Usar la Y interpolada del terreno + offset
            terrain_y_at_tile = self.terrain.terrain_interpolated_y(wx)
            wy = int(terrain_y_at_tile + COLLECTIBLE_VERTICAL_OFFSET)
            
            img = self.coin_img
            if kind == 'fuel':
                img = self.fuel_img
            elif kind == 'nos':
                img = self.nos_img
                
            c = Collectible(wx, wy, img, kind)
            self.collectibles.add(c)
            self.collectible_tiles.add(t)
            self.last_collectible_tile = t
            if kind == 'coin':
                self.last_coin_tile = t

    def spawn_collectible_at_tile(self, tile_idx:int):
        # [MODIFICADO] Esta función ahora calcula la Y correcta basada en el terreno
        
        if tile_idx in getattr(self, 'collectible_tiles', set()):
            return
        
        last_collect = getattr(self, 'last_collectible_tile', -999)
        last_coin = getattr(self, 'last_coin_tile', -999)
        
        # Calcular la altura de spawn sobre el terreno en ese tile
        wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
        
        # Aseguramos que el tile exista antes de pedir la Y interpolada
        if tile_idx + 1 >= len(self.terrain.tiles):
             self.terrain.ensure_tiles(tile_idx + 1)
             
        terrain_y_at_tile = self.terrain.terrain_interpolated_y(wx)
        # [MODIFICADO] Usa el offset global
        wy = int(terrain_y_at_tile + COLLECTIBLE_VERTICAL_OFFSET)

        spawned = False
        kind = None

        # Intentar coin
        if tile_idx - last_coin >= COIN_MIN_SEPARATION_TILES and random.random() < COIN_SPAWN_CHANCE:
            kind = 'coin'
            self.last_coin_tile = tile_idx
            self.last_collectible_tile = tile_idx
            spawned = True
        # Intentar fuel/nos
        elif tile_idx - last_collect >= COLLECTIBLE_MIN_SEPARATION_TILES:
            if random.random() < NOS_SPAWN_CHANCE:
                kind = 'nos'
                self.last_collectible_tile = tile_idx
                spawned = True
            elif random.random() < FUEL_SPAWN_CHANCE:
                kind = 'fuel'
                self.last_collectible_tile = tile_idx
                spawned = True

        if spawned:
            img = self.coin_img
            if kind == 'fuel':
                img = self.fuel_img
            elif kind == 'nos':
                img = self.nos_img
            
            c = Collectible(wx, wy, img, kind)
            self.collectibles.add(c)
            self.collectible_tiles.add(tile_idx)

    # [NUEVO] Método para spawnear árboles
    def spawn_decoration_at_tile(self, tile_idx: int):
        if tile_idx in self.decoration_tiles:
            return
        if tile_idx - self.last_decoration_tile < DECORATION_MIN_SEPARATION_TILES:
            return
        if random.random() > DECORATION_SPAWN_CHANCE:
            return

        # Calcular Posición X: inicio del tile + offset
        wx = (tile_idx * TILE_SIZE) + DECORATION_X_OFFSET_PX
        
        # Asegurar que el terreno exista
        if tile_idx + 1 >= len(self.terrain.tiles):
             self.terrain.ensure_tiles(tile_idx + 1)
        
        # Obtener la Y del terreno en ese punto X
        terrain_y_at_tile = self.terrain.terrain_interpolated_y(wx)
        
        # Alternar imagen de árbol
        img = self.tree1_img if self.tree_toggle else self.tree2_img
        self.tree_toggle = not self.tree_toggle
        
        # Crear la decoración (la Y es la base)
        deco = Decoration(wx, terrain_y_at_tile, img)
        self.decorations.add(deco)
        self.decoration_tiles.add(tile_idx)
        self.last_decoration_tile = tile_idx


    def run(self):
        try:
            while self.running:
                dt_ms = self.clock.tick(FPS)
                dt = dt_ms / 1000.0
                self.handle_events()
                
                if self.in_menu:
                    self.draw_menu()
                else:
                    if not self.game_over:
                        self.process_input(dt) 
                        self.update(dt)
                    self.draw_game()
                    
                pygame.display.flip()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("Unhandled exception in game loop:\n", tb)
            try:
                showing = True
                while showing:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            showing = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                            showing = False
                    
                    overlay = pygame.Surface((SCREEN_W, SCREEN_H))
                    overlay.fill((20,20,30))
                    font = pygame.font.SysFont('consolas', 16)
                    lines = tb.splitlines()
                    y = 10
                    for line in lines[-30:]:
                        surf = font.render(line, True, (255,200,200))
                        overlay.blit(surf, (10, y))
                        y += surf.get_height() + 2
                    small = font.render('Presiona Q o cierra la ventana para salir', True, (200,200,200))
                    overlay.blit(small, (10, SCREEN_H - 30))
                    
                    try:
                        self.screen.blit(overlay, (0,0))
                        pygame.display.flip()
                    except Exception:
                        pass
                    self.clock.tick(10)
            except Exception:
                pass
        finally:
            try:
                pygame.quit()
            except Exception:
                pass
            try:
                sys.exit()
            except Exception:
                pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.in_menu and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.btn_play.is_clicked(pos):
                    self.start_game()
                elif self.btn_quit.is_clicked(pos):
                    self.running = False
            elif self.game_over and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.restart()
                elif event.key == pygame.K_q:
                    self.running = False
                    
    def restart(self):
        self.game_over = False
        self.camera_x = 0.0
        self.player.world_x = self.player.screen_x
        self.player.world_y = TERRAIN_Y # Reinicia la base Y
        self.player.velocity_x = 0.0
        self.player.velocity_y = 0.0
        # self.player.angle = 0.0 -> ya no existe
        self.player.coins = 0
        self.player.fuel = MAX_FUEL
        self.player.nos_time_left = 0.0
        self.player.speed_multiplier = 1.0
        
        # [NUEVO] Limpiar decoraciones
        self.decorations.empty()
        self.decoration_tiles.clear()
        self.last_decoration_tile = -999
        
        self.spawn_initial_collectibles()
        if DEBUG_FORCE_SPAWN:
            self.force_spawn_near_player()

    def start_game(self):
        self.in_menu = False
        self.restart() # Usamos restart para inicializar todo

    def process_input(self, dt:float):
        # La entrada se procesa en player.update()
        pass

    def update(self, dt:float):
        # --- Actualización del jugador (física incluida)
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.terrain)
        
        # --- Actualización de la cámara
        self.camera_x = self.player.world_x - self.player.screen_x
        if self.camera_x < 0:
            self.camera_x = 0.0
            self.player.world_x = self.player.screen_x 
            self.player.velocity_x = max(0, self.player.velocity_x) # Evita seguir yendo a la izquierda

        # [MODIFICADO] Eliminada la llamada a self.player.place_on_terrain

        # --- Generación de terreno, coleccionables y decoraciones
        camera_tile = int(self.camera_x) // TILE_SIZE
        desired_ahead = SPAWN_AHEAD_TILES + 400
        desired_len = camera_tile + desired_ahead
        if len(self.terrain.tiles) < desired_len:
            old_len = len(self.terrain.tiles)
            to_gen = desired_len - old_len
            self.terrain.generate_chunk(to_gen)
            # Intentar spawn en los nuevos tiles
            for t in range(old_len, len(self.terrain.tiles)):
                self.spawn_collectible_at_tile(t)
                self.spawn_decoration_at_tile(t) # [NUEVO]

        # --- Limpieza (Culling) y Animación de Coleccionables
        for c in list(self.collectibles):
            c.animate(dt)
            c.update_screen_pos(self.camera_x)
            
            # Eliminar si está muy atrasado
            if c.world_x + 300 < self.camera_x:
                try:
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.kill()
                continue
            
            # Colisión
            if self.player.rect.colliderect(c.rect):
                if c.kind == 'coin':
                    self.player.coins += 1
                elif c.kind == 'fuel':
                    self.player.fuel = min(MAX_FUEL, self.player.fuel + FUEL_PICKUP)
                elif c.kind == 'nos':
                    self.player.nos_time_left = NOS_DURATION
                
                try:
                    self.sfx_pick.play()
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.collect()

        # [NUEVO] Limpieza (Culling) de Decoraciones
        for d in list(self.decorations):
            d.update_screen_pos(self.camera_x) # Actualiza el rect
            # Eliminar si está muy atrasado
            if d.world_x + d.rect.width < self.camera_x:
                try:
                    tidx = int(d.world_x) // TILE_SIZE
                    self.decoration_tiles.discard(tidx)
                except Exception:
                    pass
                d.kill()

        # --- Game Over
        if self.player.fuel <= 0:
            if not self.game_over:
                try:
                    self.sfx_gameover.play()
                except Exception:
                    pass
            self.game_over = True
            self.player.velocity_x *= 0.8 # Frenar suavemente

    def draw_menu(self):
        # Fondo
        self.screen.blit(self.sky, (0, 0))
        # Overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Título
        title_font = pygame.font.SysFont("consolas", 48, bold=True)
        title_txt = title_font.render("HILL DRIVE EVO 9", True, (255, 255, 255))
        self.screen.blit(title_txt, (SCREEN_W // 2 - title_txt.get_width() // 2, SCREEN_H // 2 - 180))

        # Botones
        self.btn_play.draw(self.screen)
        self.btn_quit.draw(self.screen)

    def draw_game(self):
        # Dibujar cielo (Parallax)
        sky_scroll = int(-self.camera_x * 0.1) % self.sky.get_width()
        self.screen.blit(self.sky, (sky_scroll, 0))
        self.screen.blit(self.sky, (sky_scroll - self.sky.get_width(), 0))

        # Dibujar terreno (calle.png arriba, ground.png abajo)
        self.terrain.draw(self.screen, self.camera_x, self.player.world_x // TILE_SIZE, self.street_img)
        
        # [NUEVO] Dibujar decoraciones (árboles)
        # Se dibujan después del terreno pero antes del jugador
        for d in self.decorations:
            d.draw(self.screen, self.camera_x)

        # Dibujar coleccionables
        for c in self.collectibles:
            c.draw(self.screen, self.camera_x)

        # Dibujar jugador
        self.player.draw(self.screen)
        
        # Dibujar HUD
        self.hud.draw(self.screen, self.player)

        # Pantalla de Game Over
        if self.game_over:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            go_font = pygame.font.SysFont("consolas", 60, bold=True)
            go_txt = go_font.render("GAME OVER", True, (255, 60, 60))
            self.screen.blit(go_txt, (SCREEN_W // 2 - go_txt.get_width() // 2, SCREEN_H // 2 - 80))

            score_txt = self.font.render(f"Distancia: {int(self.player.world_x / 100)}m | Monedas: {self.player.coins}", True, (255, 255, 255))
            self.screen.blit(score_txt, (SCREEN_W // 2 - score_txt.get_width() // 2, SCREEN_H // 2 + 10))

            restart_txt = self.font.render("Presiona R para Reiniciar o Q para Salir", True, (180, 180, 180))
            self.screen.blit(restart_txt, (SCREEN_W // 2 - restart_txt.get_width() // 2, SCREEN_H // 2 + 60))

# ------------------------------
# INICIO
# ------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()