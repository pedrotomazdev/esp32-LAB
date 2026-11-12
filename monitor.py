from time import sleep_ms, ticks_add, ticks_diff, ticks_ms
from config import AMOSTRAS, ATUALIZACAO_MS, DIAGNOSTICO_MEMORIA
from http_json import consultar_api

if DIAGNOSTICO_MEMORIA:
    from diagnostico import medir_memoria


estado = ("CONECTANDO", None)
acao_pc = (None, "")

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

def processar_acao_pc(wifi, host, token):
    global acao_pc

    comando, _ = acao_pc
    if comando is None:
        return

    import socket

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
            except (OSError, ValueError, TypeError, AttributeError, MemoryError) as erro:
                print("Ultimate Nenza:", erro)
                resultado = "FALHA NO COMANDO"
    acao_pc = (None, resultado)


def monitorar_servidor():
    global estado

    import network
    import socket
    from rede_config import carregar

    ssid, senha, api_url, host_pc, token = carregar()
    host_porta, rota = api_url[len("http://"):].split("/", 1)
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
                wifi.connect(ssid, senha)
                inicio = ticks_ms()
                while not wifi.isconnected() and ticks_diff(ticks_ms(), inicio) < 12_000:
                    sleep_ms(250)
                if not wifi.isconnected():
                    wifi.disconnect()
                    raise OSError("Wi-Fi indisponivel")
                if DIAGNOSTICO_MEMORIA:
                    medir_memoria("Wi-Fi conectado")

            endereco = socket.getaddrinfo(host, int(porta or "80"))[0][-1]
            estado, amostra = ler_snapshot(endereco, requisicao)
            telas = estado[1]
            if DIAGNOSTICO_MEMORIA:
                medir_memoria("API local")
        except (OSError, ValueError, TypeError, AttributeError, MemoryError) as erro:
            estado = ("API FALHOU" if wifi.isconnected() else "SEM WIFI", telas)
            print("[NENZAHUB]", erro)
            amostra = (None, None, None)

        registrar_amostra(amostra)
        prazo = ticks_add(ticks_ms(), ATUALIZACAO_MS)
        while ticks_diff(prazo, ticks_ms()) > 0:
            processar_acao_pc(wifi, host_pc, token)
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

historico = [None] * AMOSTRAS
revisao_historico = 0
trava_historico = None


def registrar_amostra(amostra):
    global revisao_historico

    with trava_historico:
        historico[revisao_historico % AMOSTRAS] = amostra
        revisao_historico += 1


def copiar_metrica(metrica, destino):
    if trava_historico is None:
        return 0, 0
    # A trava protege a copia da serie, sem abranger operacoes no OLED.
    with trava_historico:
        revisao = revisao_historico
        quantidade = min(revisao, AMOSTRAS)
        primeiro = revisao - quantidade
        for indice in range(quantidade):
            destino[indice] = historico[(primeiro + indice) % AMOSTRAS][metrica]
    return revisao, quantidade


def ler_snapshot(endereco, requisicao):
    api = consultar_api(endereco, requisicao)
    telas = preparar_telas(api)
    conexao = "LIVE" if api["status"].lower() == "ok" else "ALERTA"
    return (conexao, telas), amostra_graficos(api)
