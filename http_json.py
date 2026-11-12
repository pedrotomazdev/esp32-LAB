def consultar_api(endereco, requisicao):
    import json
    import socket

    conexao = socket.socket()
    try:
        conexao.settimeout(3)
        conexao.connect(endereco)
        corpo = ler_corpo(conexao, requisicao)
    finally:
        conexao.close()
    if isinstance(corpo, bytearray):
        corpo = bytes(corpo)
    return json.loads(corpo)


def ler_corpo(conexao, requisicao):
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
                return corpo
            if tamanho_bloco < 0 or len(corpo) + tamanho_bloco > 16_384:
                raise ValueError("Resposta grande demais")
            bloco = conexao.read(tamanho_bloco)
            if not bloco or len(bloco) != tamanho_bloco or conexao.read(2) != b"\r\n":
                raise ValueError("Bloco HTTP incompleto")
            corpo.extend(bloco)
            del bloco

    if tamanho is None or not 0 < tamanho <= 16_384:
        raise ValueError("Tamanho da resposta invalido")
    corpo = conexao.read(tamanho)
    if not corpo or len(corpo) != tamanho:
        raise ValueError("Resposta incompleta")
    return corpo
