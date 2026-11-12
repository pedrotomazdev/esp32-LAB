from machine import ADC, Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms

DEBOUNCE_MS = 30
INATIVIDADE_MS = 60_000
QUADRO_MS = 50
LINHA_MENU_PX = 13
ROLAGEM_MENU_MS = 150
QUADRO_MENU_MS = 20
ATUALIZACAO_MS = 15_000
AMOSTRAS = 60
RGB_ATIVO_BAIXO = True  # LED de anodo comum.
CORES_LED = (
    ("AUTOMATICO", None),
    ("VERMELHO", (1, 0, 0)),
    ("VERDE", (0, 1, 0)),
    ("AZUL", (0, 0, 1)),
    ("AMARELO", (1, 1, 0)),
    ("CIANO", (0, 1, 1)),
    ("ROXO", (1, 0, 1)),
    ("BRANCO", (1, 1, 1)),
    ("APAGADO", (0, 0, 0)),
    ("ARCO-IRIS", (
        (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), (1, 0, 1),
    )),
    ("POLICIA", (
        (1, 0, 0), (0, 0, 0), (1, 0, 0), (0, 0, 0),
        (0, 0, 1), (0, 0, 0), (0, 0, 1), (0, 0, 0),
    )),
    ("BATIMENTO", (
        (1, 0, 1), (0, 0, 0), (1, 0, 1), (0, 0, 0),
        (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    )),
)
MODO_LDR = len(CORES_LED)
CORES_LED += (("BRANCO NO ESCURO", None),)
GPIO_LDR = 34
LEITURA_LDR_MS = 100
DEBUG_LDR = True
LOG_LDR_MS = 1000
LIMIAR_ESCURO = 18_000
LIMIAR_CLARO = 24_000
QUADRO_LED_MS = 150
POMODORO_MS = 25 * 60_000
TOQUE_LONGO_MS = 650
GRAFICOS = (("PING", " ms"), ("CPU", " C"), ("RAM", "%"))
historico = ()
TITULOS = ("NENZAHUB", "CPU", "MEMORIA", "REDE", "BATERIA", "DISCO")
estado = ("CONECTANDO", None)
acao_pc = (None, "")
FATO_CARREGANDO = ("BUSCANDO FATO...",)
fato_chuck = ("B2: BUSCAR",)


class Botao:
    def __init__(self, gpio):
        self.pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.pressionado = False
        self.inicio_pressao = None
        self.inicio_solto = None

    def gesto(self, agora):
        if self.clicou(agora):
            self.inicio_pressao = agora
        if self.inicio_pressao is None:
            return None
        if not self.pressionado:
            duracao_ms = ticks_diff(self.inicio_solto, self.inicio_pressao)
            self.inicio_pressao = None
            if duracao_ms >= DEBOUNCE_MS:
                return "longo" if duracao_ms >= TOQUE_LONGO_MS else "curto"
        elif self.inicio_solto is None and ticks_diff(agora, self.inicio_pressao) >= TOQUE_LONGO_MS:
            self.inicio_pressao = None
            return "longo"
        return None

    def clicou(self, agora):
        if self.pin.value() == 0:
            self.inicio_solto = None
            novo_clique = not self.pressionado
            self.pressionado = True
            return novo_clique

        if self.pressionado:
            if self.inicio_solto is None:
                self.inicio_solto = agora
            elif ticks_diff(agora, self.inicio_solto) >= DEBOUNCE_MS:
                self.pressionado = False
        return False


# Cada entrada possui um titulo e o destino. Numeros abrem telas da API.
MENU = (
    ("ULTIMATE NENZA", "abrir"),
    ("HEALTH API", 0),
    ("CPU", 1),
    ("MEMORIA", 2),
    ("REDE", 3),
    ("BATERIA", 4),
    ("DISCO", 5),
    ("MINIMIZAR NENZA", "minimizar"),
    ("TESTAR CONEXAO", "ping"),
    ("ABRIR CHROME", "chrome"),
    ("NENZAHUB", "nenzahub"),
    ("NENZAHOME", "nenzahome"),
    ("NENZALAB", "nenzalab"),
    ("ABRIR BRAVE", "brave"),
    ("ABRIR DISCORD", "discord"),
    ("MODO TRABALHO", "pc"),
    ("CONFIGURACOES", "config"),
    ("GRAFICOS", "graficos"),
    ("CHUCK NORRIS", "chuck"),
)
ACOES_FAVORITAS = tuple(
    i for i, (_, destino) in enumerate(MENU)
    if isinstance(destino, str) and destino not in ("pc", "config", "graficos", "chuck")
)
ANIMACOES = ("GATINHO", "NENZA DVD")

# Adaptacoes 8x8 de simbolos Lucide (https://lucide.dev/icons/).
# Cada byte e uma linha, com o bit mais alto a esquerda.
ICONES_MENU = {
    "abrir": b"\x18\x18\x3c\x7e\x7e\x3c\x18\x18",  # sparkles
    0: b"\x00\x08\x08\x14\xe7\x20\x20\x00",  # activity
    1: b"\x24\x7e\x42\xdb\xdb\x42\x7e\x24",  # cpu
    2: b"\x00\x7e\x42\x5a\x42\x7e\x24\x00",  # memory-stick
    3: b"\x00\x3c\x42\x00\x18\x24\x00\x18",  # wifi
    4: b"\x00\x00\x7e\x4b\x4b\x7e\x00\x00",  # battery
    5: b"\x00\x3c\x42\x81\xff\x85\xff\x00",  # hard-drive
    "minimizar": b"\x00\x00\x00\x7e\x7e\x00\x00\x00",  # minus
    "ping": b"\x00\x02\x06\x4c\x78\x30\x00\x00",  # check
    "chrome": b"\x3c\x42\x99\xa5\xa5\x99\x42\x3c",  # globe
    "nenzahub": b"\x00\x77\x55\x77\x00\x77\x55\x77",  # layout-grid
    "nenzahome": b"\x18\x24\x42\xff\x42\x5a\x5a\x7e",  # house
    "nenzalab": b"\x3c\x18\x18\x24\x24\x5a\x42\x3c",  # flask-conical
    "brave": b"\x7e\x42\x42\x42\x42\x24\x18\x00",  # shield
    "discord": b"\x7e\x81\x81\x81\x81\xfe\x40\x20",  # message-square
    "chuck": b"\x3c\x24\xff\x00\x66\x00\x3c\x18",
    "graficos": b"\x80\x80\x86\x89\xb0\xc0\x80\xff",
    "pc": b"\x18\x24\x7e\x42\x7e\x42\x7e\x00",  # briefcase-business
    "config": b"\x18\x5a\x66\xc3\xc3\x66\x5a\x18",  # settings
    "volume": b"\x08\x18\x2a\x6a\x6a\x2a\x18\x08",  # volume-2
    "animacao": b"\x00\xff\x81\x99\x91\x81\xff\x00",  # monitor-play
    "cor_led": b"\x00\x18\x3c\x7e\x7e\x3c\x18\x00",
    "musica": b"\x0c\x0a\x09\x08\x08\x38\x38\x10",
    "voltar": b"\x00\x10\x20\x7e\x20\x10\x00\x00",  # arrow-left
}


def ler_config(nvs, chave, padrao, maximo):
    try:
        valor = nvs.get_i32(chave)
    except OSError:
        return padrao
    return valor if 0 <= valor <= maximo else padrao


def salvar_config(nvs, chave, valor):
    try:
        nvs.set_i32(chave, valor)
        nvs.commit()
    except OSError as erro:
        print("Configuracoes:", erro)


MUSICAS_BOOT = ("RAINING BLOOD", "COWBOYS FROM HELL")


class Buzzer:
    # Frequencia em Hz e duracao em ms. Zero Hz indica pausa.
    # Raining Blood: riff da melody0, duas oitavas acima.
    RAINING_BLOOD = (
        (1245, 152), (0, 17), (1760, 152), (0, 17), (1865, 152), (0, 17),
        (1760, 300), (0, 34), (1397, 152), (0, 17), (1760, 152), (0, 17),
        (1661, 303), (0, 34), (1319, 152), (0, 17), (1661, 152), (0, 17),
        (1568, 301), (0, 34),
    )
    COWBOYS_FROM_HELL = (
        (659, 120), (0, 14), (784, 120), (0, 14), (659, 120), (0, 14),
        (784, 120), (0, 14), (880, 120), (0, 14), (784, 120), (0, 14),
        (880, 120), (0, 14), (784, 120), (0, 14), (932, 120), (0, 14),
        (784, 120), (0, 14), (880, 120), (0, 14), (784, 120), (0, 14),
        (880, 120), (0, 14), (988, 120), (0, 14), (1175, 120), (0, 147),
    )
    SONS_BOOT = (RAINING_BLOOD, COWBOYS_FROM_HELL)
    SOM_FOCO = ((880, 150), (0, 80), (1175, 150), (0, 80), (1568, 350))
    SONS = (
        ((1350, 35), (920, 45)),
        ((920, 35), (1350, 45)),
        ((784, 20), (1047, 20), (1319, 20), (1568, 20), (2093, 25),
         (0, 15), (1568, 20), (1976, 20), (2349, 20), (3136, 45)),
    )

    def __init__(self, gpio, volume):
        self.pwm = PWM(Pin(gpio, Pin.OUT), freq=1000, duty_u16=0)
        self.volume = volume
        self.passos = ()
        self.indice = 0
        self.prazo = ticks_ms()

    def tocar(self, passos, agora):
        self.pwm.duty_u16(0)
        self.passos = passos
        self.indice = 0
        self.prazo = agora
        self.atualizar(agora)

    def atualizar(self, agora):
        if not self.passos or ticks_diff(agora, self.prazo) < 0:
            return
        if self.indice == len(self.passos):
            self.desligar()
            return
        frequencia, duracao_ms = self.passos[self.indice]
        if frequencia:
            self.pwm.freq(frequencia)
            self.pwm.duty_u16((32768 * self.volume + 50) // 100)
        else:
            self.pwm.duty_u16(0)
        self.prazo = ticks_add(agora, duracao_ms)
        self.indice += 1

    def desligar(self):
        self.pwm.duty_u16(0)
        self.passos = ()


def deslocamento_menu(offset, inicio, agora):
    restante = max(0, ROLAGEM_MENU_MS - ticks_diff(agora, inicio))
    distancia = abs(offset) * restante * restante // (ROLAGEM_MENU_MS * ROLAGEM_MENU_MS)
    return -distancia if offset < 0 else distancia


def desenhar_item_menu(oled, item, y, cor):
    titulo, destino = item
    for dy, bits in enumerate(ICONES_MENU[destino]):
        for x in range(8):
            if bits & (0x80 >> x):
                oled.pixel(x, y + dy, cor)
    oled.text(titulo, 8, y, cor)


def desenhar_menu(oled, selecionado, rodape, itens=MENU, offset=0):
    oled.fill(0)
    linhas = range(-1, 6) if offset else range(1, min(4, len(itens)))
    for linha in linhas:
        y = 20 + (linha - 1) * LINHA_MENU_PX + offset
        if y + 8 <= 16 or y >= 54:
            continue
        desenhar_item_menu(oled, itens[(selecionado + linha) % len(itens)], y, 1)

    oled.fill_rect(0, 0, 128, 16, 1)
    desenhar_item_menu(oled, itens[selecionado], 4, 0)
    oled.fill_rect(0, 54, 128, 10, 0)
    oled.hline(0, 54, 128, 1)
    oled.text(rodape[:12], 0, 56)
    oled.text("3:OK", 96, 56)
    oled.show()


def desenhar_config(oled, item, editando, volume, animacao, cor_led, musica_boot):
    if not editando:
        itens = (("VOLUME {}%".format(volume), "volume"),
                 ("ANIMACAO", "animacao"), ("COR LED", "cor_led"),
                 ("MUSICA BOOT", "musica"), ("VOLTAR", "voltar"))
        desenhar_menu(oled, item, "1:<  2:>", itens)
        return

    oled.fill(0)
    oled.text(("VOLUME", "ANIMACAO", "COR LED", "MUSICA BOOT")[item], 0, 0)
    oled.hline(0, 11, 128, 1)
    valor = ("{}%".format(volume), ANIMACOES[animacao], CORES_LED[cor_led][0],
             MUSICAS_BOOT[musica_boot])[item]
    linhas = (valor,) if len(valor) <= 16 else valor.rsplit(" ", 1)
    for linha, texto in enumerate(linhas):
        oled.text(texto, (128 - len(texto) * 8) // 2, 23 + linha * 12)
    if item == 0:
        oled.rect(8, 38, 112, 9, 1)
        if volume:
            oled.fill_rect(10, 40, 108 * volume // 100, 5, 1)
    oled.text("1:<  2:>  3:OK", 0, 56)
    oled.show()


def desenhar_foco(oled, segundos):
    oled.fill(0)
    oled.text("MODO FOCO", 0, 0)
    oled.hline(0, 12, 128, 1)
    if segundos:
        oled.text("{:02d}:{:02d}".format(segundos // 60, segundos % 60), 44, 24)
        oled.rect(0, 40, 128, 8, 1)
        largura = 124 * segundos // (POMODORO_MS // 1000)
        if largura:
            oled.fill_rect(2, 42, largura, 4, 1)
        oled.text("3:CANCELAR", 0, 56)
    else:
        oled.text("SESSAO COMPLETA", 0, 24)
        oled.text("3:VOLTAR", 0, 56)
    oled.show()


def desenhar_grafico(oled, metrica, amostras, conexao):
    nome, unidade = GRAFICOS[metrica]
    valores = [amostra[metrica] for amostra in amostras]
    atual = valores[-1] if valores else None
    oled.fill(0)
    oled.text("{} {}".format(nome, ("--" if atual is None else "{:.1f}{}".format(atual, unidade)))[:16], 0, 0)
    oled.hline(0, 12, 128, 1)
    pontos = [valor for valor in valores if valor is not None]
    if pontos:
        minimo, maximo = min(pontos), max(pontos)
        anterior = None
        for indice, valor in enumerate(valores, AMOSTRAS - len(valores)):
            if valor is None:
                anterior = None
                continue
            x = 5 + indice * 2
            y = 34
            if maximo > minimo:
                y = 51 - int(34 * (valor - minimo) / (maximo - minimo))
            if anterior is None:
                oled.pixel(x, y, 1)
            else:
                oled.line(anterior[0], anterior[1], x, y, 1)
            anterior = (x, y)
    else:
        oled.text("Aguardando dados", 0, 28)
    oled.text("1:< 2:> 3:MENU" if conexao == "LIVE" else conexao[:16], 0, 56)
    oled.show()


def amostra_graficos(api):
    def numero(valor):
        try:
            valor = float(str(valor).strip().rstrip("%").rstrip("Cc").rstrip("\u00b0"))
        except (TypeError, ValueError, OverflowError):
            return None
        return valor if -1e9 <= valor <= 1e9 else None

    return (
        numero((api.get("latency") or {}).get("networkPingMs")),
        numero((api.get("cpu") or {}).get("temperature")),
        numero((api.get("memory") or {}).get("usagePercent")),
    )


def desenhar_acao(oled, selecionado, resultado):
    oled.fill(0)
    oled.text(MENU[selecionado][0], 0, 1)
    oled.hline(0, 12, 128, 1)
    oled.text(resultado, 0, 28)
    oled.text("3: VOLTAR", 0, 56)
    oled.show()


# Desenho procedural em 128x64, sem bitmaps na flash.
CICLO_MS = 6400
# Os eixos repetem depois de 87 e 110 quadros, respectivamente.
CICLO_DVD_MS = 87 * 110 * QUADRO_MS


def desenhar_nenza_dvd(oled, fase):
    quadro = fase // QUADRO_MS
    # Reflete a posicao nos limites de um logo de 42 por 10 pixels.
    x = (10 + 2 * quadro) % 174
    y = (10 + quadro) % 110
    x = min(x, 173 - x)
    y = min(y, 109 - y)
    oled.fill(0)
    oled.rect(x, y, 42, 10, 1)
    oled.text("NENZA", x + 1, y + 1)
    oled.show()


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


def consultar_api(endereco, requisicao, host_tls=None):
    import json
    import socket

    conexao = socket.socket()
    try:
        conexao.settimeout(8 if host_tls is not None else 3)
        conexao.connect(endereco)
        if host_tls is not None:
            import ssl
            conexao = ssl.wrap_socket(conexao, server_hostname=host_tls)
        conexao.write(requisicao)
        status = conexao.readline().split()
        if len(status) < 2 or status[1] != b"200":
            raise ValueError("Resposta HTTP: {}".format(status[1] if len(status) >= 2 else status))

        tamanho = None
        em_blocos = False
        while True:
            linha = conexao.readline()
            if linha == b"\r\n":
                break
            if not linha:
                raise ValueError("Cabecalho incompleto")
            nome, _, valor = linha.partition(b":")
            if nome.lower() == b"content-length":
                tamanho = int(valor)
            elif nome.lower() == b"transfer-encoding":
                em_blocos = b"chunked" in valor.lower()

        if em_blocos:
            corpo = bytearray()
            while True:
                cabecalho = conexao.readline()
                if not cabecalho:
                    raise ValueError("Bloco HTTP incompleto")
                tamanho_bloco = int(cabecalho.split(b";", 1)[0].strip(), 16)
                if tamanho_bloco == 0:
                    return json.loads(bytes(corpo))
                if tamanho_bloco < 0 or len(corpo) + tamanho_bloco > 16_384:
                    raise ValueError("Resposta grande demais")
                bloco = conexao.read(tamanho_bloco)
                if len(bloco) != tamanho_bloco or conexao.read(2) != b"\r\n":
                    raise ValueError("Bloco HTTP incompleto")
                corpo.extend(bloco)

        if tamanho is None and host_tls is not None:
            corpo = conexao.read(16_385)
            if len(corpo) > 16_384:
                raise ValueError("Resposta grande demais")
            return json.loads(corpo)

        if tamanho is None or not 0 < tamanho <= 16_384:
            raise ValueError("Tamanho da resposta invalido")
        corpo = conexao.read(tamanho)
        if len(corpo) != tamanho:
            raise ValueError("Resposta incompleta")
        return json.loads(corpo)
    finally:
        conexao.close()


def linhas_fato(texto):
    linhas = []
    linha = ""
    texto = texto.replace("’", "'").replace("—", "-")
    texto = "".join(c if 32 <= ord(c) <= 126 or c.isspace() else "?" for c in texto)
    for palavra in texto.split():
        if linha and len(linha) + 1 + len(palavra) > 16:
            linhas.append(linha)
            linha = ""
        while len(palavra) > 16:
            linhas.append(palavra[:16])
            palavra = palavra[16:]
        linha = linha + " " + palavra if linha else palavra
    if linha:
        linhas.append(linha)
    return tuple(linhas)


def desenhar_fato(oled, linhas, pagina):
    oled.fill(0)
    oled.fill_rect(0, 0, 128, 16, 1)
    oled.text("CHUCK NORRIS", 0, 4, 0)
    for indice, linha in enumerate(linhas[pagina * 4:pagina * 4 + 4]):
        oled.text(linha, 0, 16 + indice * 9)
    rodape = "2:PROX" if (pagina + 1) * 4 < len(linhas) else "2:NOVO"
    oled.text(rodape + " 3:VOLTAR", 0, 56)
    oled.show()


def processar_fato_chuck(wifi):
    global fato_chuck

    if fato_chuck is not FATO_CARREGANDO:
        return

    if not wifi.isconnected():
        fato_chuck = ("SEM WIFI",)
        return

    import socket

    host = "api.chucknorris.io"
    requisicao = (
        b"GET /jokes/random HTTP/1.1\r\nHost: api.chucknorris.io\r\n"
        b"Accept: application/json\r\nAccept-Encoding: identity\r\n"
        b"User-Agent: NenzaESP32/1.0\r\nConnection: close\r\n\r\n"
    )
    etapa = "DNS"
    try:
        endereco = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
        etapa = "HTTPS"
        resposta = consultar_api(endereco, requisicao, host)
        etapa = "JSON"
        texto = resposta.get("value")
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Fato vazio")
        fato_chuck = linhas_fato(texto)
    except Exception as erro:
        print("[CHUCK] {}: {!r}".format(etapa, erro))
        fato_chuck = ("FALHA " + etapa, "B2: TENTAR NOVO")


def processar_acao_pc(wifi):
    global acao_pc

    comando, _ = acao_pc
    if comando is None:
        return

    import secrets
    import socket

    host = getattr(secrets, "NENZA_HOST", "")
    token = getattr(secrets, "NENZA_TOKEN", "")
    resultado = "SEM CONFIG PC"
    if host and token:
        resultado = "SEM WIFI"
        if wifi.isconnected():
            try:
                endereco = socket.getaddrinfo(host, 8085)[0][-1]
                requisicao = (
                    "POST /nenzabuddy/commands/{} HTTP/1.0\r\nHost: {}:8085\r\n"
                    "Authorization: Bearer {}\r\nContent-Length: 0\r\n"
                    "Connection: close\r\n\r\n"
                ).format(comando, host, token).encode()
                resposta = consultar_api(endereco, requisicao)
                print("Ultimate Nenza:", resposta.get("message", "OK"))
                resultado = "COMANDO OK"
            except (OSError, ValueError, TypeError, AttributeError) as erro:
                print("Ultimate Nenza:", erro)
                resultado = "FALHA NO COMANDO"
    acao_pc = (None, resultado)


def monitorar_servidor():
    global estado, historico

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
            novas_telas = preparar_telas(api)
            amostra = amostra_graficos(api)
            telas = novas_telas
            estado = ("LIVE" if api["status"].lower() == "ok" else "ALERTA", telas)
        except (OSError, ValueError, TypeError, AttributeError) as erro:
            estado = ("API FALHOU" if wifi.isconnected() else "SEM WIFI", telas)
            print("Monitor:", erro)
            amostra = (None, None, None)

        historico = (historico + (amostra,))[-AMOSTRAS:]
        prazo = ticks_add(ticks_ms(), ATUALIZACAO_MS)
        while ticks_diff(prazo, ticks_ms()) > 0:
            processar_acao_pc(wifi)
            processar_fato_chuck(wifi)
            sleep_ms(50)


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


def ambiente_escuro(leitura, estava_escuro):
    # LDR entre 3V3 e ADC, resistor entre ADC e GND.
    if estava_escuro:
        return leitura < LIMIAR_CLARO
    return leitura <= LIMIAR_ESCURO


def atualizar_led_rgb(rgb, snapshot, cor_led, quadro, escuro):
    conexao, telas = snapshot
    cor = CORES_LED[cor_led][1]
    if cor_led == MODO_LDR:
        cor = (1, 1, 1) if escuro else (0, 0, 0)
    elif cor is None:
        if conexao == "LIVE":
            cor = (0, 1, 0)
        elif conexao == "CONECTANDO":
            cor = (0, 0, 1)
        elif telas is not None and conexao in ("SEM WIFI", "API FALHOU", "ERRO REDE"):
            cor = (1, 1, 0)
        else:
            cor = (1, 0, 0)

    if isinstance(cor[0], tuple):
        cor = cor[quadro % len(cor)]

    for pino, canal in zip(rgb, cor):
        pino.value(canal ^ RGB_ATIVO_BAIXO)


def main():
    global estado, acao_pc, fato_chuck
    from esp32 import NVS

    i2c = SoftI2C(sda=Pin(18), scl=Pin(15), freq=400_000)
    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    botoes = (Botao(27), Botao(26), Botao(25))
    nvs = NVS("nenza_menu")
    buzzer = Buzzer(19, ler_config(nvs, "volume", 70, 100))
    animacao = ler_config(nvs, "animacao", 0, len(ANIMACOES) - 1)
    rgb = tuple(
        Pin(gpio, Pin.OUT, value=int(RGB_ATIVO_BAIXO)) for gpio in (2, 4, 5)
    )
    estado_rgb = None
    cor_led = ler_config(nvs, "cor_led", 0, len(CORES_LED) - 1)
    musica_boot = ler_config(nvs, "musica_boot", 0, len(Buzzer.SONS_BOOT) - 1)
    cor_led_exibida = None
    quadro_led = 0
    ultimo_quadro_led = ticks_ms()
    ldr = None
    ultima_leitura_ldr = ultimo_quadro_led
    ultimo_log_ldr = ultimo_quadro_led
    escuro = False
    selecionado = 0
    no_menu = False
    pagina_fato = 0
    fato_exibido = None
    inicio = True
    metrica = 0
    favorito = ler_config(nvs, "favorito", 0, len(ACOES_FAVORITAS) - 1)
    acao_atalho = None
    prazo_foco = None
    segundos_foco = None
    historico_exibido = None
    aviso_menu = None
    item_config = None
    editando = False
    exibido = None
    redesenhar = True

    try:
        import _thread
        _thread.start_new_thread(atualizar_servidor, ())
    except Exception as erro:
        estado = ("ERRO REDE", None)
        print("Monitor:", erro)

    ultimo_clique = ticks_ms()
    ultimo_quadro = ultimo_clique
    inicio_rolagem = ultimo_clique
    quadro_menu = ultimo_clique
    offset_menu = 0
    descanso = False
    fase = 0
    print("Menu pronto. B1=GPIO27 B2=GPIO26 B3=GPIO25 Buzzer=GPIO19")
    acao_exibida = None

    try:
        buzzer.tocar(Buzzer.SONS_BOOT[musica_boot], ticks_ms())
        while True:
            agora = ticks_ms()
            snapshot = estado
            mudou_cor = cor_led != cor_led_exibida
            cor = CORES_LED[cor_led][1]
            animando_led = cor is not None and isinstance(cor[0], tuple)
            avancar_led = animando_led and ticks_diff(agora, ultimo_quadro_led) >= QUADRO_LED_MS
            if mudou_cor:
                quadro_led = 0
                ultimo_quadro_led = agora
            elif avancar_led:
                quadro_led = (quadro_led + 1) % len(cor)
                ultimo_quadro_led = agora
            mudou_luz = False
            if cor_led == MODO_LDR and (
                mudou_cor or ticks_diff(agora, ultima_leitura_ldr) >= LEITURA_LDR_MS
            ):
                if ldr is None:
                    ldr = ADC(Pin(GPIO_LDR), atten=ADC.ATTN_11DB)
                leitura = ldr.read_u16()
                novo_escuro = ambiente_escuro(leitura, escuro and not mudou_cor)
                mudou_luz = novo_escuro != escuro
                escuro = novo_escuro
                ultima_leitura_ldr = agora
                if DEBUG_LDR and (
                    mudou_cor or mudou_luz or ticks_diff(agora, ultimo_log_ldr) >= LOG_LDR_MS
                ):
                    print("[LDR] ADC={} | escuro<={} claro>={} | LED={}".format(
                        leitura, LIMIAR_ESCURO, LIMIAR_CLARO, "BRANCO" if escuro else "APAGADO"
                    ))
                    ultimo_log_ldr = agora
            mudou_status = cor_led == 0 and snapshot is not estado_rgb
            if mudou_cor or avancar_led or mudou_luz or mudou_status:
                atualizar_led_rgb(rgb, snapshot, cor_led, quadro_led, escuro)
                estado_rgb = snapshot
                cor_led_exibida = cor_led
            buzzer.atualizar(agora)

            amostras = historico
            if prazo_foco is not None:
                segundos = max(0, (ticks_diff(prazo_foco, agora) + 999) // 1000)
                redesenhar = redesenhar or segundos != segundos_foco
                segundos_foco = segundos
                if not segundos:
                    prazo_foco = None
                    buzzer.tocar(Buzzer.SOM_FOCO, agora)

            for indice, botao in enumerate(botoes):
                gesto = botao.gesto(agora) if indice == 2 else (
                    "curto" if botao.clicou(agora) else None
                )
                if gesto is not None:
                    print("Botao", indice + 1, "pressionado")
                    ultimo_clique = agora
                    descanso = False
                    passo = -1 if indice == 0 else 1
                    redesenhar = True
                    aviso_menu = None
                    if segundos_foco is not None:
                        if indice == 2 and gesto == "curto":
                            prazo_foco = None
                            segundos_foco = None
                            no_menu = True
                        continue
                    if gesto == "longo":
                        if inicio and acao_atalho is None and acao_pc[0] is None:
                            acao_atalho = ACOES_FAVORITAS[favorito]
                            acao_pc = (MENU[acao_atalho][1], "EXECUTANDO...")
                        elif item_config is None and no_menu and selecionado in ACOES_FAVORITAS:
                            favorito = ACOES_FAVORITAS.index(selecionado)
                            salvar_config(nvs, "favorito", favorito)
                            aviso_menu = "FAVORITO"
                        continue
                    if acao_atalho is not None:
                        if indice == 2:
                            acao_atalho = None
                        continue
                    if inicio:
                        if indice == 2:
                            inicio = False
                            no_menu = True
                        else:
                            metrica = (metrica + passo) % len(GRAFICOS)
                    elif item_config is not None:
                        if indice == 2:
                            if editando:
                                if item_config == 0:
                                    salvar_config(nvs, "volume", buzzer.volume)
                                elif item_config == 1:
                                    salvar_config(nvs, "animacao", animacao)
                                elif item_config == 2:
                                    salvar_config(nvs, "cor_led", cor_led)
                                else:
                                    salvar_config(nvs, "musica_boot", musica_boot)
                                editando = False
                            elif item_config == 4:
                                item_config = None
                            else:
                                editando = True
                                if item_config == 3:
                                    buzzer.tocar(Buzzer.SONS_BOOT[musica_boot], agora)
                                    continue
                        elif not editando:
                            item_config = (item_config + passo) % 5
                        elif item_config == 0:
                            buzzer.volume = max(0, min(100, buzzer.volume + passo * 10))
                        elif item_config == 1:
                            animacao = (animacao + passo) % len(ANIMACOES)
                        elif item_config == 2:
                            cor_led = (cor_led + passo) % len(CORES_LED)
                        else:
                            musica_boot = (musica_boot + passo) % len(Buzzer.SONS_BOOT)
                            buzzer.tocar(Buzzer.SONS_BOOT[musica_boot], agora)
                            continue
                    elif not no_menu and MENU[selecionado][1] == "chuck":
                        if indice == 2:
                            no_menu = True
                        elif indice == 0:
                            pagina_fato = max(0, pagina_fato - 1)
                        elif (pagina_fato + 1) * 4 < len(fato_chuck):
                            pagina_fato += 1
                        elif fato_chuck is not FATO_CARREGANDO:
                            pagina_fato = 0
                            fato_chuck = FATO_CARREGANDO
                    elif indice == 2:
                        destino = MENU[selecionado][1]
                        if destino == "config":
                            item_config = 0
                        elif no_menu and destino == "graficos":
                            inicio = True
                            no_menu = False
                        elif no_menu and destino == "chuck":
                            no_menu = False
                            pagina_fato = 0
                            fato_chuck = FATO_CARREGANDO
                        elif no_menu and destino == "pc":
                            prazo_foco = ticks_add(agora, POMODORO_MS)
                            segundos_foco = POMODORO_MS // 1000
                            no_menu = False
                            buzzer.desligar()
                            continue
                        elif no_menu and isinstance(destino, str):
                            if acao_pc[0] is None:
                                acao_pc = (destino, "EXECUTANDO...")
                                no_menu = False
                        else:
                            no_menu = not no_menu
                    else:
                        if no_menu:
                            atual = deslocamento_menu(offset_menu, inicio_rolagem, agora)
                            limite = 2 * LINHA_MENU_PX
                            offset_menu = max(-limite, min(limite, atual + passo * LINHA_MENU_PX))
                            inicio_rolagem = agora
                        selecionado = (selecionado + passo) % len(MENU)
                        no_menu = True
                    buzzer.tocar(Buzzer.SONS[indice], agora)
                    redesenhar = True

            menu_visivel = no_menu and item_config is None and segundos_foco is None
            if not menu_visivel:
                offset_menu = 0
            animar_menu = offset_menu and ticks_diff(agora, quadro_menu) >= QUADRO_MENU_MS

            resultado_pc = acao_pc
            fato = fato_chuck
            if segundos_foco is None and (
                descanso or ticks_diff(agora, ultimo_clique) >= INATIVIDADE_MS
            ):
                intervalo = ticks_diff(agora, ultimo_quadro)
                if not descanso or intervalo >= QUADRO_MS:
                    ciclo = CICLO_DVD_MS if animacao else CICLO_MS
                    fase = (fase + intervalo) % ciclo if descanso else 0
                    if animacao:
                        desenhar_nenza_dvd(oled, fase)
                    else:
                        desenhar_gato(oled, fase, dormindo=snapshot[0] != "LIVE")
                    ultimo_quadro = agora
                    descanso = True
            elif (
                redesenhar or animar_menu or snapshot is not exibido or resultado_pc is not acao_exibida
                or (inicio and amostras is not historico_exibido)
                or (not no_menu and MENU[selecionado][1] == "chuck" and fato is not fato_exibido)
            ):
                destino = MENU[selecionado][1]
                if segundos_foco is not None:
                    desenhar_foco(oled, segundos_foco)
                elif acao_atalho is not None:
                    desenhar_acao(oled, acao_atalho, resultado_pc[1])
                elif inicio:
                    desenhar_grafico(oled, metrica, amostras, snapshot[0])
                elif item_config is not None:
                    desenhar_config(oled, item_config, editando, buzzer.volume, animacao, cor_led, musica_boot)
                elif no_menu:
                    offset = deslocamento_menu(offset_menu, inicio_rolagem, agora)
                    desenhar_menu(oled, selecionado, aviso_menu or snapshot[0], offset=offset)
                    quadro_menu = agora
                    if offset == 0:
                        offset_menu = 0
                elif destino == "chuck":
                    desenhar_fato(oled, fato, pagina_fato)
                    fato_exibido = fato
                elif isinstance(destino, int):
                    desenhar_tela(oled, destino, snapshot)
                else:
                    desenhar_acao(oled, selecionado, resultado_pc[1])
                exibido = snapshot
                historico_exibido = amostras
                acao_exibida = resultado_pc
                redesenhar = False

            sleep_ms(5)
    finally:
        buzzer.desligar()
        buzzer.pwm.deinit()


if __name__ == "__main__":
    main()
