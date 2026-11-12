from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
from time import sleep_ms, ticks_diff, ticks_ms

DEBOUNCE_MS = 30
INATIVIDADE_MS = 60_000
ATUALIZACAO_MS = 15_000
QUADRO_MS = 50
TITULOS = ("NENZAHUB", "CPU", "MEMORIA", "REDE", "BATERIA", "DISCO")
estado = ("CONECTANDO", None)


class Botao:
    def __init__(self, gpio):
        self.pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.pressionado = self.pin.value() == 0
        self.leitura = self.pressionado
        self.ultima_mudanca = ticks_ms()

    def clicou(self, agora):
        leitura = self.pin.value() == 0
        if leitura != self.leitura:
            self.leitura = leitura
            self.ultima_mudanca = agora

        if leitura == self.pressionado:
            return False
        if ticks_diff(agora, self.ultima_mudanca) < DEBOUNCE_MS:
            return False

        self.pressionado = leitura
        return leitura


# Desenho procedural em 128x64, sem bitmaps na flash.
CICLO_MS = 6400


def desenhar_gato(oled, fase, dormindo):
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

    oled.show()


def consultar_api(endereco, requisicao):
    import json
    import socket

    conexao = socket.socket()
    try:
        conexao.settimeout(3)
        conexao.connect(endereco)
        conexao.write(requisicao)
        status = conexao.readline().split()
        if len(status) < 2 or status[1] != b"200":
            raise ValueError("Resposta HTTP invalida")

        tamanho = None
        while True:
            linha = conexao.readline()
            if linha == b"\r\n":
                break
            if not linha:
                raise ValueError("Cabecalho incompleto")
            if linha.lower().startswith(b"content-length:"):
                tamanho = int(linha.split(b":", 1)[1])

        if tamanho is None or not 0 < tamanho <= 16_384:
            raise ValueError("Tamanho da resposta invalido")
        corpo = conexao.read(tamanho)
        if len(corpo) != tamanho:
            raise ValueError("Resposta incompleta")
        return json.loads(corpo)
    finally:
        conexao.close()


def monitorar_servidor():
    global estado

    import network
    import socket
    from secrets import API_URL, WIFI_PASSWORD, WIFI_SSID

    host_porta, rota = API_URL[len("http://"):].split("/", 1)
    host, _, porta = host_porta.partition(":")
    requisicao = (
        "GET /{} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n"
        .format(rota, host_porta).encode()
    )
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    telas = None

    while True:
        try:
            if not wifi.isconnected():
                estado = ("SEM WIFI" if telas else "CONECTANDO", telas)
                wifi.connect(WIFI_SSID, WIFI_PASSWORD)
                inicio = ticks_ms()
                while not wifi.isconnected() and ticks_diff(ticks_ms(), inicio) < 12_000:
                    sleep_ms(250)
                if not wifi.isconnected():
                    wifi.disconnect()
                    raise OSError("Wi-Fi indisponivel")

            endereco = socket.getaddrinfo(host, int(porta or "80"))[0][-1]
            api = consultar_api(endereco, requisicao)
            telas = preparar_telas(api)
            estado = ("LIVE" if api["status"].lower() == "ok" else "ALERTA", telas)
        except (OSError, ValueError, TypeError, AttributeError) as erro:
            estado = ("API FALHOU" if wifi.isconnected() else "SEM WIFI", telas)
            print("Monitor:", erro)

        sleep_ms(ATUALIZACAO_MS)


def atualizar_servidor():
    global estado

    try:
        monitorar_servidor()
    except Exception as erro:
        estado = ("ERRO REDE", estado[1])
        print("Monitor:", erro)


def medida(valor, unidade=""):
    if valor is None or valor == "":
        return "--"
    return str(valor).replace("\u00b0", "") + unidade


def duracao(segundos):
    if segundos is None:
        return "--"
    minutos = int(segundos) // 60
    return "{}d {:02d}h {:02d}m".format(minutos // 1440, minutos // 60 % 24, minutos % 60)


def barra(valor):
    try:
        return max(0, min(100, float(str(valor).rstrip("%"))))
    except (ValueError, TypeError):
        return None


def preparar_telas(api):
    status = api.get("status")
    if not isinstance(status, str):
        raise ValueError("Resposta sem status")
    latencia = api.get("latency") or {}
    uptime = api.get("uptime") or {}
    memoria = api.get("memory") or {}
    cpu = api.get("cpu") or {}
    termica = api.get("thermal") or {}
    wifi = api.get("wifi") or {}
    android = api.get("android") or {}
    bateria = android.get("battery") or {}
    disco = android.get("disk") or {}
    ram_pct = memoria.get("usagePercent")
    sinal = wifi.get("signalPercent")
    carga = bateria.get("percentage")
    disco_pct = disco.get("usagePercent")
    tomada = bateria.get("plugged")
    tomada_texto = "--"
    if tomada is not None:
        tomada_texto = "NAO" if tomada == "UNPLUGGED" else "SIM"

    return (
        (("Status: " + status.upper(), "Ping: " + medida(latencia.get("networkPingMs"), " ms"),
          "Up: " + duracao(uptime.get("systemSeconds"))), None),
        (("Nucleos: " + medida(cpu.get("cores")), "CPU: " + medida(cpu.get("temperature")),
          "Media: " + medida(termica.get("averageTemp"), "C")), None),
        (("Uso: " + medida(ram_pct, "%"), "Usada: " + medida(memoria.get("usedMB"), " MB"),
          "Total: " + medida(memoria.get("totalMB"), " MB")), barra(ram_pct)),
        ((medida(wifi.get("ip")), "Sinal: " + medida(sinal, "%"),
          "Link: " + medida(wifi.get("linkSpeedMbps"), " Mbps")), barra(sinal)),
        (("Carga: " + medida(carga, "%"), "Temp: " + medida(bateria.get("temperature"), "C"),
          "Tomada: " + tomada_texto), barra(carga)),
        (("Uso: " + medida(disco_pct), "Usado: " + medida(disco.get("used")),
          "Livre: " + medida(disco.get("available"))), barra(disco_pct)),
    )


def desenhar_tela(oled, tela, snapshot):
    conexao, telas = snapshot
    oled.fill(0)
    oled.text(TITULOS[tela], 0, 1)
    oled.text("{}/{}".format(tela + 1, len(TITULOS)), 104, 1)
    oled.hline(0, 12, 128, 1)

    if telas is None:
        oled.text("Aguardando dados", 0, 28)
        oled.text(conexao, 0, 47)
    else:
        linhas, percentual = telas[tela]
        for i, linha in enumerate(linhas):
            oled.text(linha[:16], 0, 16 + i * 10)
        if conexao in ("SEM WIFI", "API FALHOU", "ERRO REDE"):
            oled.text("CACHE " + conexao, 0, 54)
        elif conexao == "ALERTA":
            oled.text("NENZA / ALERTA", 0, 54)
        elif percentual is not None:
            oled.rect(0, 51, 128, 10, 1)
            largura = int(percentual * 124 / 100)
            if largura:
                oled.fill_rect(2, 53, largura, 6, 1)
        else:
            oled.text("NENZA / LIVE", 0, 54)
    oled.show()


def atualizar_led(led, agora, conexao):
    if conexao == "LIVE":
        led.value(1)
    else:
        meio_periodo = 500 if conexao in ("CONECTANDO", "SEM WIFI") else 125
        led.value((agora // meio_periodo) % 2)


def main():
    global estado

    # Mesmos pinos e frequencia do teste de botoes que funciona na placa.
    i2c = SoftI2C(sda=Pin(18), scl=Pin(15), freq=400_000)
    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    tela = 0
    exibido = estado
    desenhar_tela(oled, tela, exibido)

    botao = Botao(4)
    led = Pin(2, Pin.OUT)
    try:
        import _thread
        _thread.start_new_thread(atualizar_servidor, ())
    except Exception as erro:
        estado = ("ERRO REDE", None)
        print("Monitor:", erro)

    ultimo_clique = ticks_ms()
    ultimo_quadro = ultimo_clique
    dormindo = False
    fase = 0

    while True:
        agora = ticks_ms()
        snapshot = estado
        atualizar_led(led, agora, snapshot[0])
        if botao.clicou(agora):
            if not dormindo:
                tela = (tela + 1) % len(TITULOS)
            dormindo = False
            ultimo_clique = agora
            exibido = None

        if dormindo or ticks_diff(agora, ultimo_clique) >= INATIVIDADE_MS:
            intervalo = ticks_diff(agora, ultimo_quadro)
            if not dormindo or intervalo >= QUADRO_MS:
                fase = (fase + intervalo) % CICLO_MS if dormindo else 0
                desenhar_gato(oled, fase, dormindo=snapshot[0] != "LIVE")
                ultimo_quadro = agora
                dormindo = True
        elif snapshot is not exibido:
            desenhar_tela(oled, tela, snapshot)
            exibido = snapshot

        sleep_ms(5)


if __name__ == "__main__":
    main()
