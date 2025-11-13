# Hill-drive-evo
Juego inspirado en hill climb racing
Informe del Proyecto: Hill Drive Evo 9 – Profesional
1. Descripción general

Hill Drive Evo 9 es un videojuego desarrollado en Python utilizando la librería Pygame.
El juego está inspirado en títulos de conducción como Hill Climb Racing, y su objetivo principal es conducir un vehículo a través de un terreno infinito, recolectando monedas y combustible para mantener el recorrido activo.
Durante la partida, el jugador debe evitar quedarse sin gasolina y mantener la estabilidad del vehículo sobre terrenos con pendientes variables.

Este proyecto busca aplicar conocimientos de programación, física básica, manejo de imágenes y eventos dentro de un entorno de desarrollo interactivo.

2. Tecnologías utilizadas

Lenguaje: Python 3.11

Librería principal: Pygame

Módulos adicionales:

math y random: para los cálculos de movimiento y generación aleatoria

sys: para controlar la ejecución del programa

typing: para definir tipos de datos

3. Estructura general del código

El código está dividido en distintas partes que permiten un funcionamiento organizado y modular:

Sección	Función principal
Configuración global	Define las constantes como tamaño de pantalla, FPS y parámetros de física.
Sprites	Controla los objetos del juego como las monedas y los bidones de combustible.
Terreno	Genera y dibuja el terreno de manera infinita a medida que el jugador avanza.
Jugador	Maneja la posición, movimiento y estado del vehículo.
Interfaz (HUD)	Muestra en pantalla la cantidad de monedas y el nivel de combustible.
Menú y control del juego	Contiene la lógica del menú principal y las condiciones de victoria o derrota.
4. Mecánicas del juego
Movimiento del vehículo

El vehículo se mantiene centrado mientras el terreno se desplaza para simular el avance.
El jugador puede acelerar o retroceder usando las teclas D y A.

Combustible

El combustible se va agotando progresivamente con el tiempo.
Si llega a cero, el juego termina mostrando una pantalla de Game Over.
El jugador puede recolectar bidones de gasolina que restauran parte del combustible perdido.

Monedas

Las monedas aparecen de manera aleatoria a lo largo del terreno.
Al recolectarlas, el jugador incrementa su puntuación.

Terreno

El terreno se genera de forma infinita con pequeñas variaciones de altura, simulando colinas y pendientes suaves.
Se utiliza una textura tipo carretera para darle un aspecto más realista.

5. Interfaz del juego

El juego cuenta con un menú principal que permite al jugador iniciar la partida o salir.
Durante la partida, en la parte superior izquierda de la pantalla se muestra el nivel de combustible mediante una barra de color y el contador de monedas.
Cuando el jugador pierde, aparece un mensaje con la opción de reiniciar o cerrar el juego.

6. Sonido

El juego incluye música de fondo y efectos de sonido para las acciones principales:

Recolección de monedas

Recolección de combustible

Pantalla de Game Over

En caso de que los archivos de sonido no estén disponibles, el programa está diseñado para continuar sin errores.

7. Aspectos técnicos destacados

Código modular con clases bien definidas.

Generación infinita de terreno en tiempo real.

Sistema de cámara fluido que sigue el avance del jugador.

Interfaz visual clara y funcional.

Manejo robusto de recursos gráficos y sonoros.

8. Posibles mejoras

Agregar física más realista (rotación del vehículo, suspensión, gravedad avanzada).

Incluir diferentes escenarios o niveles de dificultad.

Implementar un sistema de guardado de récords o puntajes.

Añadir efectos visuales como polvo o luces.

9. Conclusión

El proyecto Hill Drive Evo 9 demuestra un manejo correcto del lenguaje Python y de la librería Pygame, combinando gráficos, física simple e interacción del usuario.
El código refleja una estructura limpia y profesional, pero también accesible para su comprensión dentro del nivel medio.
Este trabajo permitió aplicar conceptos de programación estructurada, lógica de juegos, animación 2D y control de eventos, mostrando un resultado completo y funcional.