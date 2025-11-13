import pygame
import random
import sys
import math
from typing import Tuple


# ------------------------------
# CONFIGURACIÓN GLOBAL (FÁCIL AJUSTE)
# ------------------------------
SCREEN_W, SCREEN_H = 1000, 600
FPS = 60


# Tiles / estética
TILE_SIZE = 64  # tamaño del "bloque" (cambiar para más/menos "Minecraft")
INITIAL_TILES = 800
TERRAIN_Y = 420  # altura del tope del terreno (coordenada Y)


# Jugador
PLAYER_SCREEN_X = 150
# tamaño del auto (aumentado: un poco más largo)
PLAYER_WIDTH, PLAYER_HEIGHT = 240, 110


# Fuel y moneda
MAX_FUEL = 100.0
FUEL_DECAY_PER_SEC = 5.0   # consumo por segundo
FUEL_PICKUP = 40.0
COIN_SPAWN_CHANCE = 0.045
FUEL_SPAWN_CHANCE = 0.01
# Control de separación entre collectibles (en tiles)
COLLECTIBLE_MIN_SEPARATION_TILES = 4

# separación mínima específica para monedas (permite más coins que fuels)
COIN_MIN_SEPARATION_TILES = 2

# cuántos primeros tiles tendrán la textura 'calle' en su bloque superior
# aumentado para una calle más larga
INITIAL_STREET_TILES = 20
# si True, la calle cubrirá el bloque superior de TODO el terreno
STREET_FULL_LENGTH = True


# Movimiento
CAMERA_SPEED_PX_PER_SEC = 300.0

# cuantos tiles por delante de la camara intentaremos spawnear collectibles
SPAWN_AHEAD_TILES = 40

# cuántos tiles por delante de la cámara intentamos mantener spawnados
SPAWN_AHEAD_TILES = (SCREEN_W // TILE_SIZE) + 8


# Sonidos (volúmenes)
MUSIC_VOL = 0.25
SFX_VOL = 0.8


# ------------------------------
# UTILIDADES (carga robusta de recursos)
# ------------------------------
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


# small cached loader for sounds to avoid repeated disk reads
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
        self.kind = kind  # 'coin' | 'fuel'
        self.collected = False
        self._anim = 0.0


    def update_screen_pos(self, camera_x: float):
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)
        self.rect.topleft = (sx, sy)


    def animate(self, dt: float):
        if self.kind == 'coin':
            # pequeña oscilación vertical para dar vida
            self._anim += 3.5 * dt
            # keep base image (we'll offset when drawing)
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


# ------------------------------
# TERRAIN (tiles planos con generación infinita)
# ------------------------------
class Terrain:
    def __init__(self, tile_size:int, initial_tiles:int, base_y:int, ground_img:pygame.Surface):
        self.tile_size = tile_size
        self.base_y = base_y
        self.tiles = [self.base_y for _ in range(initial_tiles)]
        self.ground_img = ground_img


    def ensure_tiles(self, idx: int):
        if idx < len(self.tiles):
            return
        # generar en chunks para eficiencia
        while len(self.tiles) <= idx:
            # terreno plano con micro variaciones opcionales
            jitter = random.randint(-2, 2)
            self.tiles.append(self.base_y + jitter)


    def tile_y_at_pixel_x(self, world_x_px:int) -> int:
        tile_idx = max(0, world_x_px // self.tile_size)
        if tile_idx >= len(self.tiles):
            self.ensure_tiles(tile_idx)
        return self.tiles[tile_idx]


    def generate_chunk(self, count:int):
        for _ in range(count):
            jitter = random.randint(-2, 2)
            self.tiles.append(self.base_y + jitter)


    def draw(self, surf:pygame.Surface, camera_x:float, player_tile: int = None, street_img: pygame.Surface = None):
        """Draw terrain tiles. If player_tile and street_img are provided, the top cell of that tile
        will be drawn using street_img so the 'calle' appears as part of the terrain.
        """
        screen_tile_start = int(camera_x) // self.tile_size
        offset_x = int(camera_x) % self.tile_size
        tiles_on_screen = surf.get_width() // self.tile_size + 3
        for i in range(tiles_on_screen):
            tile_idx = screen_tile_start + i
            if tile_idx >= len(self.tiles):
                self.generate_chunk(200)
            world_x = tile_idx * self.tile_size
            ty = self.tiles[tile_idx]
            screen_x = i * self.tile_size - offset_x
            # dibujar la parte superior del tile:
            # - si STREET_FULL_LENGTH está activado y street_img existe, usar street_img en todos los tiles
            # - sino, usar la lógica previa (primeros INITIAL_STREET_TILES o player_tile)
            used_top_img = None
            if street_img is not None and STREET_FULL_LENGTH:
                used_top_img = street_img
            else:
                if tile_idx < INITIAL_STREET_TILES and street_img is not None:
                    used_top_img = street_img
                elif tile_idx == player_tile and street_img is not None:
                    used_top_img = street_img

            if used_top_img is not None:
                try:
                    surf.blit(used_top_img, (screen_x, ty))
                except Exception:
                    surf.blit(self.ground_img, (screen_x, ty))
            else:
                surf.blit(self.ground_img, (screen_x, ty))

            y = ty + self.tile_size

            # dibujar el resto del terreno por debajo
            while y < surf.get_height():
                surf.blit(self.ground_img, (screen_x, y))
                y += self.tile_size


# ------------------------------
# PLAYER (jugador)
# ------------------------------
class Player:
    def __init__(self, screen_x:int, image:pygame.Surface):
        self.screen_x = screen_x
        self.image = image
        self.rect = self.image.get_rect()
        self.world_x = 0.0
        self.world_y = TERRAIN_Y
        self.coins = 0
        self.fuel = MAX_FUEL


    def place_on_terrain(self, terrain:Terrain, camera_x:float):
        world_x = camera_x + self.screen_x
        ty = terrain.tile_y_at_pixel_x(int(world_x))
        self.world_x = world_x
        # colocar la mitad inferior del auto sobre el tile top
        self.world_y = ty - (self.image.get_height() // 2)
        self.rect.topleft = (self.screen_x, int(self.world_y))


    def draw(self, surf:pygame.Surface):
        surf.blit(self.image, self.rect.topleft)


# ------------------------------
# HUD y Menú (UI simple y profesional)
# ------------------------------
class HUD:
    def __init__(self, font:pygame.font.Font):
        self.font = font


    def draw(self, surf:pygame.Surface, player:Player):
        # Monedas
        txt = self.font.render(f"Monedas: {player.coins}", True, (255,215,0))
        surf.blit(txt, (20, 20))
        # Barra de fuel
        bx, by, bw, bh = 20, 60, 220, 20
        pygame.draw.rect(surf, (0,0,0), (bx, by, bw, bh), 2)
        fill = int((player.fuel / MAX_FUEL) * (bw - 4))
        col = (255, 60, 60) if player.fuel < 30 else (0,160,0)
        pygame.draw.rect(surf, col, (bx + 2, by + 2, fill, bh - 4))
        # Porcentaje
        perc = self.font.render(f"{int(player.fuel)}%", True, (255,255,255))
        surf.blit(perc, (bx + bw + 10, by - 1))


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
# GAME (control principal)
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
        # imagen de la calle (solo el bloque que toca el auto)
        self.street_img = load_image("assets/calle.png", (TILE_SIZE, TILE_SIZE), alpha=False, fallback_color=(120,120,120))
        self.car_img = load_image("assets/lancer.png", (PLAYER_WIDTH, PLAYER_HEIGHT), alpha=True, fallback_color=(220,220,220))
        self.coin_img = load_image("assets/coin.png", (36,36), alpha=True, fallback_color=(240,220,20))
        self.fuel_img = load_image("assets/fuel.png", (40,40), alpha=True, fallback_color=(200,0,0))


        # sonidos: usar cache loader o load_sound según disponibilidad
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
        self.player = Player(PLAYER_SCREEN_X, self.car_img)
        self.hud = HUD(self.font)
        self.camera_x = 0.0


        # collectibles
        self.collectibles = pygame.sprite.Group()
        self.collectible_tiles = set()  # tiles que ya tienen un collectible
        self.last_collectible_tile = -999
        self.last_coin_tile = -999
        # ajustar probabilidades un poco más altas para más apariciones (más coins)
        global COIN_SPAWN_CHANCE, FUEL_SPAWN_CHANCE
        COIN_SPAWN_CHANCE = max(COIN_SPAWN_CHANCE, 0.12)
        FUEL_SPAWN_CHANCE = max(FUEL_SPAWN_CHANCE, 0.02)
        self.spawn_initial_collectibles()


        # UI: menu buttons
        btn_w, btn_h = 220, 52
        self.btn_play = Button(pygame.Rect((SCREEN_W//2 - btn_w//2, SCREEN_H//2 - 70, btn_w, btn_h)), "JUGAR", self.font)
        self.btn_quit = Button(pygame.Rect((SCREEN_W//2 - btn_w//2, SCREEN_H//2 + 0, btn_w, btn_h)), "SALIR", self.font)


        # estado
        self.running = True
        self.in_menu = True
        self.game_over = False


    # spawn collectibles distributed within first chunk so they appear at start
    def spawn_initial_collectibles(self):
        self.collectibles.empty()
        # spawn coins/fuel across first N tiles aligned with player, but bias to more coins
        end = min(len(self.terrain.tiles), 300)
        # ensure last counters exist
        last_collect = getattr(self, 'last_collectible_tile', -999)
        last_coin = getattr(self, 'last_coin_tile', -999)
        for tile_idx in range(10, end):
            spawned = False
            # intentar spawn de coin si cumple separación específica de coins
            if tile_idx - last_coin >= COIN_MIN_SEPARATION_TILES and random.random() < COIN_SPAWN_CHANCE:
                wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
                wy = self.player.world_y
                coin = Collectible(wx, wy, self.coin_img, 'coin')
                self.collectibles.add(coin)
                # marcar tile como ocupado
                self.collectible_tiles.add(tile_idx)
                last_coin = tile_idx
                last_collect = tile_idx
                spawned = True
            else:
                # intentar spawn de fuel respetando la separación general
                if tile_idx - last_collect >= COLLECTIBLE_MIN_SEPARATION_TILES and random.random() < FUEL_SPAWN_CHANCE:
                    wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
                    wy = self.player.world_y
                    fuel = Collectible(wx, wy, self.fuel_img, 'fuel')
                    self.collectibles.add(fuel)
                    # marcar tile como ocupado
                    self.collectible_tiles.add(tile_idx)
                    last_collect = tile_idx
                    spawned = True
            if spawned:
                # actualizar los atributos de seguimiento
                self.last_collectible_tile = last_collect
                self.last_coin_tile = last_coin


    def spawn_collectible_at_tile(self, tile_idx:int):
        # no crear si ya existe collectible en ese tile
        if tile_idx in getattr(self, 'collectible_tiles', set()):
            return
        # intentar spawn con preferencia por coins pero respetando separaciones
        last_collect = getattr(self, 'last_collectible_tile', -999)
        last_coin = getattr(self, 'last_coin_tile', -999)
        # intentar coin primero si distancia suficiente desde última coin
        if tile_idx - last_coin >= COIN_MIN_SEPARATION_TILES and random.random() < COIN_SPAWN_CHANCE:
            wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
            wy = self.player.world_y
            coin = Collectible(wx, wy, self.coin_img, 'coin')
            self.collectibles.add(coin)
            # marcar tile
            self.collectible_tiles.add(tile_idx)
            self.last_coin_tile = tile_idx
            self.last_collectible_tile = tile_idx
            return
        # si no salió coin, intentar fuel (respetando separación general)
        if tile_idx - last_collect < COLLECTIBLE_MIN_SEPARATION_TILES:
            return
        if random.random() < FUEL_SPAWN_CHANCE:
            wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
            wy = self.player.world_y
            fuel = Collectible(wx, wy, self.fuel_img, 'fuel')
            self.collectibles.add(fuel)
            # marcar tile
            self.collectible_tiles.add(tile_idx)
            self.last_collectible_tile = tile_idx


    def run(self):
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
        pygame.quit()
        sys.exit()


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


    def start_game(self):
        self.in_menu = False
        self.game_over = False
        self.camera_x = 0.0
        self.player.coins = 0
        self.player.fuel = MAX_FUEL
        self.spawn_initial_collectibles()


    def process_input(self, dt:float):
        keys = pygame.key.get_pressed()
        if self.player.fuel > 0:
            if keys[pygame.K_d]:
                self.camera_x += CAMERA_SPEED_PX_PER_SEC * dt
            if keys[pygame.K_a]:
                self.camera_x -= CAMERA_SPEED_PX_PER_SEC * dt
            if self.camera_x < 0:
                self.camera_x = 0.0


    def update(self, dt:float):
        # generar tiles y collectibles cuando sea necesario
        needed_px = int(self.camera_x) + SCREEN_W + (TILE_SIZE * 200)
        needed_tile_index = needed_px // TILE_SIZE
        if needed_tile_index >= len(self.terrain.tiles):
            old_len = len(self.terrain.tiles)
            self.terrain.generate_chunk(300)
            for t in range(old_len, len(self.terrain.tiles)):
                self.spawn_collectible_at_tile(t)

        # asegurarnos de tener spawn constante en la ventana por delante de la cámara
        try:
            camera_tile = int(self.camera_x) // TILE_SIZE
            for t in range(camera_tile, camera_tile + SPAWN_AHEAD_TILES):
                # asegurarnos de que el tile existe
                if t >= len(self.terrain.tiles):
                    self.terrain.ensure_tiles(t)
                # intentar spawn en cada tile (función evita duplicados)
                self.spawn_collectible_at_tile(t)
        except Exception:
            pass


        # colocar jugador
        self.player.place_on_terrain(self.terrain, self.camera_x)


        # actualizar collectibles y colisiones
        for c in list(self.collectibles):
            c.animate(dt)
            c.update_screen_pos(self.camera_x)
            # eliminar si muy atrasado
            if c.world_x + 300 < self.camera_x:
                # limpiar marca de tile
                try:
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.kill()
                continue
            # colisión
            if self.player.rect.colliderect(c.rect):
                if c.kind == 'coin':
                    self.player.coins += 1
                    # play sound safely
                    try:
                        self.sfx_pick.play()
                    except Exception:
                        pass
                elif c.kind == 'fuel':
                    self.player.fuel = min(MAX_FUEL, self.player.fuel + FUEL_PICKUP)
                    try:
                        self.sfx_pick.play()
                    except Exception:
                        pass
                # limpiar marca de tile antes de eliminar
                try:
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.collect()


        # fuel decay
        if not self.game_over:
            self.player.fuel -= FUEL_DECAY_PER_SEC * dt
            if self.player.fuel <= 0:
                self.player.fuel = 0
                self.game_over = True
                try:
                    self.sfx_gameover.play()
                except Exception:
                    pass


    def draw_menu(self):
        self.screen.fill((40, 40, 60))
        title = pygame.font.SysFont("consolas", 48).render("HILL DRIVE EVO 9", True, (255,255,255))
        subtitle = pygame.font.SysFont("consolas", 18).render("Presiona JUGAR o Q para salir", True, (200,200,200))
        self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 80))
        self.screen.blit(subtitle, (SCREEN_W//2 - subtitle.get_width()//2, 140))
        self.btn_play.draw(self.screen)
        self.btn_quit.draw(self.screen)


    def draw_game(self):
        # fondo cielo parallax
        sky_x = -self.camera_x * 0.25
        self.screen.blit(self.sky, (sky_x, 0))
        self.screen.blit(self.sky, (sky_x + self.sky.get_width(), 0))


        # terreno: dibujar la 'calle' como parte del terreno al final del mapa
        try:
            # elegir el último índice de tile disponible como tile de la calle
            street_tile = len(self.terrain.tiles) - 1
            if street_tile < 0:
                street_tile = None
        except Exception:
            street_tile = None
        # pasamos street_tile como player_tile param (no sigue al coche ahora)
        self.terrain.draw(self.screen, self.camera_x, player_tile=street_tile, street_img=self.street_img)


        # collectibles
        for c in self.collectibles:
            if -300 < c.rect.x < SCREEN_W + 300:
                c.draw(self.screen, self.camera_x)


        # player
        self.player.draw(self.screen)


        # hud
        self.hud.draw(self.screen, self.player)


        # game over overlay + instrucciones
        if self.game_over:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,170))
            self.screen.blit(overlay, (0,0))
            big = pygame.font.SysFont("consolas", 44).render("GAME OVER - SIN GASOLINA", True, (255,80,80))
            small = pygame.font.SysFont("consolas", 20).render("Presiona R para reintentar o Q para salir", True, (255,255,255))
            self.screen.blit(big, (SCREEN_W//2 - big.get_width()//2, SCREEN_H//2 - 50))
            self.screen.blit(small, (SCREEN_W//2 - small.get_width()//2, SCREEN_H//2 + 10))


    def restart(self):
        self.camera_x = 0.0
        self.player.coins = 0
        self.player.fuel = MAX_FUEL
        self.collectibles.empty()
        self.terrain = Terrain(TILE_SIZE, INITIAL_TILES, TERRAIN_Y, self.ground)
        self.spawn_initial_collectibles()
        self.game_over = False


# ------------------------------
# Ejecutar
# ------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()



