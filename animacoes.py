from config import QUADRO_MS

# Desenho procedural em 128x64, sem bitmaps na flash.
CICLO_MS = 6400
# Os eixos repetem depois de 87 e 110 quadros, respectivamente.
CICLO_DVD_MS = 87 * 110 * QUADRO_MS


def desenhar_logo_nenza(oled, x, y):
    oled.rect(x, y, 42, 10, 1)
    oled.text("NENZA", x + 1, y + 1)


def desenhar_nenza_dvd(oled, fase, temperatura=None):
    quadro = fase // QUADRO_MS
    # Reflete a posicao nos limites de um logo de 42 por 10 pixels.
    x = (10 + 2 * quadro) % 174
    y = (10 + quadro) % 110
    x = min(x, 173 - x)
    y = min(y, 109 - y)
    oled.fill(0)
    desenhar_logo_nenza(oled, x, y)
    if temperatura is not None:
        oled.text(temperatura, 0, 56 if y < 8 else 0)
    oled.show()


def desenhar_gato(oled, fase, dormindo, temperatura=None):
    if fase < 1500:
        olhar = 0
    elif fase < 3000:
        olhar = min(9, (fase - 1500) // 35)
    elif fase < 4650:
        olhar = max(-9, 9 - (fase - 3000) // 35)
    else:
        olhar = min(0, -9 + (fase - 4650) // 35)

    raio_y = 1 if dormindo else 13
    if not dormindo:
        for piscada in (1140, 3810, 4100, 5680):
            distancia = abs(fase - piscada)
            raio_y = min(raio_y, max(1, (distancia - 20) // 6))

    oled.fill(0)

    # Orelhas e interior das orelhas.
    for x, lado in ((17, 1), (110, -1)):
        oled.line(x, 22, x + lado * 3, 4, 1)
        oled.line(x + lado * 3, 4, x + lado * 22, 16, 1)
        oled.line(x + lado * 6, 10, x + lado * 13, 16, 1)

    for x in (35, 92):
        if raio_y <= 2:
            oled.line(x - 19, 33, x - 8, 37, 1)
            oled.hline(x - 8, 37, 17, 1)
            oled.line(x + 8, 37, x + 19, 33, 1)
        else:
            oled.ellipse(x, 33, 22, raio_y, 1, True)
            pupila = x + olhar
            oled.ellipse(pupila, 33, 4, raio_y - 1, 0, True)
            if raio_y >= 7:
                oled.fill_rect(pupila - 2, 28, 3, 3, 1)
                oled.pixel(pupila + 2, 35, 1)

    # Nariz, boca e bigodes.
    oled.hline(60, 47, 7, 1)
    oled.hline(61, 48, 5, 1)
    oled.hline(62, 49, 3, 1)
    oled.vline(63, 50, 4, 1)
    oled.line(63, 53, 59, 56, 1)
    oled.line(63, 53, 67, 56, 1)
    oled.line(59, 56, 55, 54, 1)
    oled.line(67, 56, 71, 54, 1)

    for ponta, bochecha in ((3, 25), (124, 102)):
        oled.line(ponta, 47, bochecha, 49, 1)
        oled.line(ponta + (4 if ponta < bochecha else -4), 57, bochecha, 52, 1)

    if dormindo:
        subida = fase % 1600 // 100
        oled.text("Z", 67 + subida // 2, 23 - subida, 1)

    if temperatura is not None:
        oled.text(temperatura, (128 - len(temperatura) * 8) // 2, 0)
    oled.show()
