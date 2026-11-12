from machine import Pin, PWM
from time import ticks_add, ticks_diff, ticks_ms
from config import DEBOUNCE_MS, TOQUE_LONGO_MS, LIMIAR_CLARO, LIMIAR_ESCURO, CORES_LED, MODO_LDR, RGB_ATIVO_BAIXO

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
