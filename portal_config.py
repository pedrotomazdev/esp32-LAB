import json
import socket
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms

from rede_config import salvar

LIMITE_CABECALHO = 2048
LIMITE_CORPO = 4096


def responder(cliente, status, tipo, tamanho):
    cliente.write((
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
        "Connection: close\r\nCache-Control: no-store\r\n"
        "X-Content-Type-Options: nosniff\r\nX-Frame-Options: DENY\r\n\r\n"
    ).format(status, tipo, tamanho).encode())


def mensagem(cliente, status, texto):
    corpo = texto.encode()
    responder(cliente, status, "text/plain; charset=utf-8", len(corpo))
    cliente.write(corpo)


def ler_cabecalho(cliente):
    prazo = ticks_add(ticks_ms(), 4000)
    dados = bytearray()
    fim = b"\r\n\r\n"
    encontrados = 0
    while len(dados) < LIMITE_CABECALHO and ticks_diff(prazo, ticks_ms()) > 0:
        byte = cliente.read(1)
        if not byte:
            break
        dados.extend(byte)
        if byte[0] == fim[encontrados]:
            encontrados += 1
        else:
            encontrados = int(byte[0] == fim[0])
        if encontrados == len(fim):
            linhas = bytes(dados)[:-4].split(b"\r\n")
            metodo, caminho, versao = linhas[0].split()
            if versao not in (b"HTTP/1.0", b"HTTP/1.1"):
                raise ValueError
            campos = {}
            for linha in linhas[1:]:
                nome, separador, valor = linha.partition(b":")
                nome = nome.lower()
                if not separador or nome in campos:
                    raise ValueError
                campos[nome] = valor.strip()
            return metodo, caminho, campos
    raise ValueError


def atender(cliente, ip):
    try:
        metodo, caminho, campos = ler_cabecalho(cliente)
        if campos.get(b"host") not in (ip, ip + b":80"):
            raise ValueError
    except ValueError:
        mensagem(cliente, "400 Bad Request", "Abra o endereco que aparece no OLED.")
        return False

    if metodo == b"GET" and caminho in (b"/", b"/index.html"):
        with open("/index.html", "rb") as pagina:
            pagina.seek(0, 2)
            responder(cliente, "200 OK", "text/html; charset=utf-8", pagina.tell())
            pagina.seek(0)
            while True:
                bloco = pagina.read(512)
                if not bloco:
                    break
                cliente.write(bloco)
        return False

    if metodo != b"POST" or caminho != b"/config":
        mensagem(cliente, "404 Not Found", "Pagina inexistente.")
        return False

    try:
        tamanho = campos.get(b"content-length", b"")
        if (
            campos.get(b"content-type") != b"application/json"
            or b"transfer-encoding" in campos or not tamanho.isdigit()
            or len(tamanho) > 4 or not 0 < int(tamanho) <= LIMITE_CORPO
        ):
            raise ValueError
        tamanho = int(tamanho)
        corpo = cliente.read(tamanho)
        if not corpo or len(corpo) != tamanho:
            raise ValueError
        dados = json.loads(corpo)
    except ValueError:
        mensagem(cliente, "400 Bad Request", "Formulario invalido.")
        return False

    try:
        salvar(dados)
    except ValueError as erro:
        mensagem(cliente, "400 Bad Request", str(erro))
        return False
    except OSError:
        mensagem(cliente, "500 Internal Server Error", "Falha ao gravar na flash.")
        return False

    try:
        mensagem(cliente, "200 OK", "Configuracao salva. A placa vai reiniciar.")
    except OSError:
        pass
    return True


def executar(oled):
    import network
    import os
    from machine import reset

    os.stat("/index.html")
    ssid = "Nenza-Config"
    senha = "".join("%02x" % byte for byte in os.urandom(6))
    ap = network.WLAN(network.AP_IF)
    network.WLAN(network.STA_IF).active(False)
    servidor = None
    gravou = False
    try:
        ap.active(True)
        ap.config(essid=ssid, authmode=getattr(network, "AUTH_WPA2_PSK", 3), password=senha)
        ip = ap.ifconfig()[0]
        servidor = socket.socket()
        servidor.bind((ip, 80))
        servidor.listen(1)
        servidor.settimeout(1)

        oled.fill(0)
        oled.text("CONFIG WIFI", 0, 0)
        oled.text(ssid, 0, 14)
        oled.text("Senha da rede:", 0, 26)
        oled.text(senha, 0, 37)
        oled.text(ip, 0, 53)
        oled.show()

        prazo = ticks_add(ticks_ms(), 300_000)
        while ticks_diff(prazo, ticks_ms()) > 0 and not gravou:
            try:
                cliente, _ = servidor.accept()
            except OSError as erro:
                if erro.args[0] not in (11, 110, 116):
                    raise
                continue
            try:
                cliente.settimeout(2)
                gravou = atender(cliente, ip.encode())
            except OSError:
                pass
            finally:
                cliente.close()

        if gravou:
            oled.fill(0)
            oled.text("CONFIG SALVA", 0, 18)
            oled.text("Reiniciando...", 0, 36)
            oled.show()
            sleep_ms(1200)
    finally:
        if servidor is not None:
            servidor.close()
        ap.active(False)

    if gravou:
        reset()
