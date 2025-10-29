import pygame, random, math

pygame.init()

# --- CONFIGURACIÓN GENERAL ---
ANCHO, ALTO = 900, 500
FPS = 60
VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Hill Drive Evo - Terreno Suave")

# --- COLORES ---
CELESTE = (135, 206, 250)
VERDE = (34, 139, 34)
CAFE = (139, 69, 19)

# --- IMAGEN DEL AUTO ---
car_img = pygame.image.load("assets/lancer.png").convert_alpha()
car_img = pygame.transform.scale(car_img, (130, 65))

# --- AUTO ---
car = {
    "x": 150,
    "y": 300,
    "vel_x": 2.0,
    "vel_y": 0.0,
    "rot": 0.0,
    "on_ground": False
}

# --- FUNCIÓN: GENERAR TERRENO SUAVE ---
def generar_terreno(largo=4000, altura_media=360, suavizado=50):
    """
    Genera un terreno suave usando interpolación entre puntos aleatorios.
    - largo: cantidad total de puntos
    - altura_media: altura base del terreno
    - suavizado: define la distancia entre puntos de control
    """
    terreno = []
    puntos_control = []

    # Crear puntos base aleatorios
    for i in range(0, largo, suavizado):
        y = altura_media + random.randint(-70, 70)
        puntos_control.append((i, y))

    # Interpolar entre los puntos de control (curvas suaves)
    for i in range(len(puntos_control) - 1):
        x1, y1 = puntos_control[i]
        x2, y2 = puntos_control[i + 1]

        for t in range(suavizado):
            # interpolación cúbica tipo “hermita”
            mu = t / suavizado
            mu2 = (1 - math.cos(mu * math.pi)) / 2
            y = (y1 * (1 - mu2) + y2 * mu2)
            terreno.append(y)

    return terreno

terreno = generar_terreno()

# --- FUNCIÓN: OBTENER ALTURA DEL TERRENO ---
def altura_terreno(x):
    if x < 0: return terreno[0]
    if x >= len(terreno): return terreno[-1]
    return terreno[int(x)]

# --- LOOP PRINCIPAL ---
clock = pygame.time.Clock()
offset_x = 0
running = True

while running:
    # --- EVENTOS ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- CONTROLES ---
    keys = pygame.key.get_pressed()
    if keys[pygame.K_d]:
        car["vel_x"] += 0.05
    if keys[pygame.K_a]:
        car["vel_x"] -= 0.05

    car["vel_x"] = max(1.5, min(5, car["vel_x"]))
    offset_x += car["vel_x"]

    # --- FÍSICA DEL AUTO ---
    terreno_y = altura_terreno(car["x"] + offset_x)
    siguiente_y = altura_terreno(car["x"] + offset_x + 5)
    pendiente = math.atan2(siguiente_y - terreno_y, 5)

    # Gravedad y salto
    if not car["on_ground"]:
        car["vel_y"] += 0.5
    if keys[pygame.K_SPACE] and car["on_ground"]:
        car["vel_y"] = -9
        car["on_ground"] = False

    car["y"] += car["vel_y"]

    # Colisión con el suelo
    if car["y"] > terreno_y - 30:
        car["y"] = terreno_y - 30
        car["vel_y"] = 0
        car["on_ground"] = True
    else:
        car["on_ground"] = False

    # Rotación del auto según la pendiente
    car["rot"] = math.degrees(-pendiente) * 0.8

    # --- DIBUJO EN PANTALLA ---
    VENTANA.fill(CELESTE)

    # Terreno
    puntos = []
    for i in range(ANCHO):
        t_y = altura_terreno(i + int(offset_x))
        puntos.append((i, t_y))
    pygame.draw.polygon(VENTANA, VERDE, puntos + [(ANCHO, ALTO), (0, ALTO)])
    pygame.draw.lines(VENTANA, CAFE, False, puntos, 2)

    # Auto
    rot_img = pygame.transform.rotate(car_img, car["rot"])
    rect = rot_img.get_rect(center=(car["x"], car["y"]))
    VENTANA.blit(rot_img, rect)

    # --- ACTUALIZAR ---
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
