from time import gmtime, ticks_diff
from animacoes import desenhar_logo_nenza
from config import LINHA_MENU_PX, ROLAGEM_MENU_MS, ANIMACOES, CORES_LED, MUSICAS_BOOT, GRAFICOS, AMOSTRAS, TITULOS, POMODORO_MS

# Cada entrada possui um titulo e o destino. Numeros abrem telas da API.
MENU = (
    ("ULTIMATE NENZA", "abrir"),
    ("HEALTH API", 0),
    ("CPU", 1),
    ("MEMORIA", 2),
    ("REDE", 3),
    ("BATERIA", 4),
    ("DISCO", 5),
    ("ABRIR CHROME", "chrome"),
    ("NENZAHUB", "nenzahub"),
    ("NENZAHOME", "nenzahome"),
    ("NENZALAB", "nenzalab"),
    ("ABRIR BRAVE", "brave"),
    ("ABRIR DISCORD", "discord"),
    ("MODO TRABALHO", "pc"),
    ("CONFIGURACOES", "config"),
    ("GRAFICOS", "graficos"),
    ("TEMP. AMBIENTE", "temperatura"),
    ("TELA INICIAL", "painel"),
)
ACOES_FAVORITAS = tuple(
    i for i, (_, destino) in enumerate(MENU)
    if isinstance(destino, str) and destino not in ("pc", "config", "graficos", "temperatura", "painel")
)

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
    "chrome": b"\x3c\x42\x99\xa5\xa5\x99\x42\x3c",  # globe
    "nenzahub": b"\x00\x77\x55\x77\x00\x77\x55\x77",  # layout-grid
    "nenzahome": b"\x18\x24\x42\xff\x42\x5a\x5a\x7e",  # house
    "nenzalab": b"\x3c\x18\x18\x24\x24\x5a\x42\x3c",  # flask-conical
    "brave": b"\x7e\x42\x42\x42\x42\x24\x18\x00",  # shield
    "discord": b"\x7e\x81\x81\x81\x81\xfe\x40\x20",  # message-square
    "graficos": b"\x80\x80\x86\x89\xb0\xc0\x80\xff",
    "pc": b"\x18\x24\x7e\x42\x7e\x42\x7e\x00",  # briefcase-business
    "config": b"\x18\x5a\x66\xc3\xc3\x66\x5a\x18",  # settings
    "volume": b"\x08\x18\x2a\x6a\x6a\x2a\x18\x08",  # volume-2
    "animacao": b"\x00\xff\x81\x99\x91\x81\xff\x00",  # monitor-play
    "cor_led": b"\x00\x18\x3c\x7e\x7e\x3c\x18\x00",
    "musica": b"\x0c\x0a\x09\x08\x08\x38\x38\x10",
    "voltar": b"\x00\x10\x20\x7e\x20\x10\x00\x00",  # arrow-left
    "wifi": b"\x00\x7e\x81\x3c\x42\x18\x00\x18",
    "temperatura": b"\x18\x24\x24\x24\x24\x42\x42\x3c",
    "painel": b"\x10\x28\x44\x82\x44\x54\x54\x7c",  # house
}

# Adaptacoes 8x8 de memory-stick e activity, do Lucide.
ICONE_RAM = b"\x00\x00\xff\x91\xbd\xff\x54\x00"
ICONE_PING = b"\x00\x10\x18\x28\xe7\x14\x0c\x08"


def desenhar_icone(oled, icone, x, y, cor):
    for dy, bits in enumerate(icone):
        for dx in range(8):
            if bits & (0x80 >> dx):
                oled.pixel(x + dx, y + dy, cor)


def desenhar_relogio(oled, utc):
    ano, mes, dia, hora, minuto, *_ = gmtime(max(0, utc - 3 * 3600))
    if ano < 2025:
        data, horario = "--/--/----", "--:--"
    else:
        data = "{:02d}/{:02d}/{:04d}".format(dia, mes, ano)
        horario = "{:02d}:{:02d}".format(hora, minuto)
    oled.text(horario, 44, 43)
    oled.text(data, 24, 54)


def desenhar_painel(oled, amostra, temperatura, utc):
    ping, _, ram = amostra
    ram_texto = "--%" if ram is None or not 0 <= ram <= 100 else "{:.0f}%".format(ram)
    ping_texto = "--ms" if ping is None or ping < 0 else "{:.0f}ms".format(ping)
    if len(ping_texto) > 6:
        ping_texto = ">999ms"
    temperatura = temperatura.replace(" ", "")
    if len(temperatura) > 5:
        temperatura = temperatura.split(".", 1)[0] + "C"
    oled.fill(0)
    desenhar_icone(oled, ICONE_RAM, 0, 0, 1)
    desenhar_icone(oled, ICONE_PING, 60, 0, 1)
    desenhar_icone(oled, ICONES_MENU["temperatura"], 120, 0, 1)
    oled.text(ram_texto, 0, 9)
    oled.text(ping_texto, (128 - len(ping_texto) * 8) // 2, 9)
    oled.text(temperatura, 128 - len(temperatura) * 8, 9)
    desenhar_logo_nenza(oled, 43, 27)
    desenhar_relogio(oled, utc)
    oled.show()


def deslocamento_menu(offset, inicio, agora):
    restante = max(0, ROLAGEM_MENU_MS - ticks_diff(agora, inicio))
    distancia = abs(offset) * restante * restante // (ROLAGEM_MENU_MS * ROLAGEM_MENU_MS)
    return -distancia if offset < 0 else distancia


def desenhar_item_menu(oled, item, y, cor):
    titulo, destino = item
    desenhar_icone(oled, ICONES_MENU[destino], 0, y, cor)
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


CONFIG_WIFI = 4
CONFIG_VOLTAR = 5


def desenhar_config(oled, item, editando, volume, animacao, cor_led, musica_boot):
    if not editando:
        itens = (("VOLUME {}%".format(volume), "volume"),
                 ("ANIMACAO", "animacao"), ("COR LED", "cor_led"),
                 ("MUSICA BOOT", "musica"), ("CONFIGURAR WIFI", "wifi"),
                 ("VOLTAR", "voltar"))
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


def desenhar_grafico(oled, metrica, valores, quantidade, conexao):
    nome, unidade = GRAFICOS[metrica]
    atual = valores[quantidade - 1] if quantidade else None
    oled.fill(0)
    oled.text("{} {}".format(nome, ("--" if atual is None else "{:.1f}{}".format(atual, unidade)))[:16], 0, 0)
    oled.hline(0, 12, 128, 1)
    minimo = maximo = None
    for indice in range(quantidade):
        valor = valores[indice]
        if valor is not None:
            if minimo is None or valor < minimo:
                minimo = valor
            if maximo is None or valor > maximo:
                maximo = valor
    if minimo is not None:
        anterior_x = None
        for indice in range(quantidade):
            valor = valores[indice]
            if valor is None:
                anterior_x = None
                continue
            x = 5 + (AMOSTRAS - quantidade + indice) * 2
            y = 34
            if maximo > minimo:
                y = 51 - int(34 * (valor - minimo) / (maximo - minimo))
            if anterior_x is None:
                oled.pixel(x, y, 1)
            else:
                oled.line(anterior_x, anterior_y, x, y, 1)
            anterior_x, anterior_y = x, y
    else:
        oled.text("Aguardando dados", 0, 28)
    oled.text("1:< 2:> 3:MENU" if conexao == "LIVE" else conexao[:16], 0, 56)
    oled.show()

def desenhar_acao(oled, selecionado, resultado):
    oled.fill(0)
    oled.text(MENU[selecionado][0], 0, 1)
    oled.hline(0, 12, 128, 1)
    oled.text(resultado, 0, 28)
    oled.text("3: VOLTAR", 0, 56)
    oled.show()



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
