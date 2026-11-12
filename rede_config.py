import json

ARQUIVO = "/secrets.json"
CAMPOS = ("WIFI_SSID", "WIFI_PASSWORD", "API_URL", "NENZA_HOST", "NENZA_TOKEN")


def validar(dados):
    if not isinstance(dados, dict):
        raise ValueError("Configuracao invalida.")
    valores = []
    for campo, limite in zip(CAMPOS, (32, 64, 256, 253, 512)):
        valor = dados.get(campo)
        if not isinstance(valor, str) or len(valor.encode()) > limite:
            raise ValueError("Campo invalido: " + campo)
        if any(ord(c) < 32 or ord(c) == 127 for c in valor):
            raise ValueError("Caractere invalido: " + campo)
        valores.append(valor)

    ssid, senha, url, host_pc, token = valores
    if not ssid or (senha and not (
        8 <= len(senha.encode()) <= 63
        or len(senha) == 64 and all(c in "0123456789abcdefABCDEF" for c in senha)
    )):
        raise ValueError("Confira o nome e a senha do Wi-Fi.")
    autoridade, separador, rota = url[7:].partition("/")
    host, tem_porta, porta = autoridade.partition(":")
    if (
        not url.startswith("http://") or not separador or not host_valido(host)
        or (tem_porta and (not porta.isdigit() or not 1 <= int(porta) <= 65535))
        or any(not 33 <= ord(c) <= 126 or c == "#" for c in rota)
    ):
        raise ValueError("Use uma URL HTTP com caminho, por exemplo http://192.168.1.10:8080/api/health.")
    if bool(host_pc) != bool(token) or (host_pc and not host_valido(host_pc)):
        raise ValueError("Preencha host e token do PC juntos, ou deixe ambos vazios.")
    return tuple(valores)


def host_valido(host):
    return bool(host) and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in host)


def carregar():
    for caminho in (ARQUIVO, ARQUIVO + ".bak"):
        try:
            with open(caminho, "r") as arquivo:
                return validar(json.load(arquivo))
        except (OSError, ValueError):
            pass
    import secrets
    return (secrets.WIFI_SSID, secrets.WIFI_PASSWORD, secrets.API_URL,
            getattr(secrets, "NENZA_HOST", ""), getattr(secrets, "NENZA_TOKEN", ""))


def salvar(dados):
    import os

    valores = validar(dados)
    temporario = ARQUIVO + ".tmp"
    copia = ARQUIVO + ".bak"
    with open(temporario, "w") as arquivo:
        json.dump(dict(zip(CAMPOS, valores)), arquivo)
    # Move a versao anterior antes de promover a nova, inclusive em VFS sem overwrite.
    try:
        os.stat(ARQUIVO)
    except OSError as erro:
        if erro.args[0] != 2:
            raise
    else:
        remover_se_existe(copia)
        os.rename(ARQUIVO, copia)
    os.rename(temporario, ARQUIVO)
    try:
        remover_se_existe(copia)
    except OSError:
        # A nova configuracao ja foi promovida e tem prioridade na leitura.
        pass


def remover_se_existe(caminho):
    import os

    try:
        os.remove(caminho)
    except OSError as erro:
        if erro.args[0] != 2:
            raise
