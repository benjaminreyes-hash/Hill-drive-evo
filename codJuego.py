import pygame
import math
import random

pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hill Drive Evo 9")

# Colores
SKY = (135, 206, 235)

# Auto
car_img = pygame.image.load("assets/lancer.png").convert_alpha()  # Auto con transparencia real
car_img = pygame.transform.scale(car_img, (120, 60))
car_x, car_y = 100, 400
car_speed_y = 0
gravity = 0.6
lift = -12
on_ground = False

# Terreno
terrain = [450 + math.sin(i / 40) * 50 + random.randint(-5, 5) for i in range(3000)]
camera_x = 0

# Textura del terreno
ground_texture = pygame.image.load("assets/ground.png").convert()
ground_texture = pygame.transform.scale(ground_texture, (20, 20))  # Ajusta tamaño de bloque

clock = pygame.time.Clock()
running = True

while running:
    clock.tick(60)
    screen.fill(SKY)

    # Eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_d]:
        camera_x += 4
    if keys[pygame.K_a]:
        camera_x -= 4
    if keys[pygame.K_w] and on_ground:
        car_speed_y = lift
        on_ground = False

    # Física del auto
    car_y += car_speed_y
    car_speed_y += gravity

    # Limitar cámara
    camera_x = max(0, min(len(terrain) - WIDTH, camera_x))

    # Detección de terreno
    terrain_index = int(car_x + camera_x)
    if terrain_index >= len(terrain):
        terrain_index = len(terrain) - 1
    terrain_y = terrain[terrain_index]
    if car_y >= terrain_y - car_img.get_height()//2:
        car_y = terrain_y - car_img.get_height()//2
        car_speed_y = 0
        on_ground = True

    # Dibujar terreno con textura
    for i in range(WIDTH):
        idx = i + int(camera_x)
        if idx >= len(terrain):
            break
        ty = terrain[idx]
        y = ty
        while y < HEIGHT:
            screen.blit(ground_texture, (i, y))
            y += ground_texture.get_height()

    # Dibujar auto
    screen.blit(car_img, (car_x, car_y - car_img.get_height()//2))

    pygame.display.flip()

pygame.quit()
