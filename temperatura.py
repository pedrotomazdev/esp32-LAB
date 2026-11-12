from math import log
from machine import ADC, Pin
from time import ticks_add, ticks_diff

from config import (
    AMOSTRAS, GPIO_NTC, LEITURA_NTC_MS, NTC_ALIMENTACAO_UV, NTC_BETA_K,
    NTC_LIGADO_A_3V3, NTC_R25_OHM, NTC_RESISTOR_OHM,
)


def converter_celsius(tensao_uv):
    # Faixa aproximada de calibracao do ADC ESP32 a 11 dB.
    if not 150_000 <= tensao_uv <= 2_450_000 or tensao_uv >= NTC_ALIMENTACAO_UV:
        return None
    queda = NTC_ALIMENTACAO_UV - tensao_uv
    if NTC_LIGADO_A_3V3:
        resistencia = NTC_RESISTOR_OHM * (queda / tensao_uv)
    else:
        resistencia = NTC_RESISTOR_OHM * (tensao_uv / queda)
    return 1 / (1 / 298.15 + log(resistencia / NTC_R25_OHM) / NTC_BETA_K) - 273.15


class TemperaturaAmbiente:
    def __init__(self, agora):
        self.adc = None
        self.prazo = agora
        self.historico = [None] * AMOSTRAS
        self.revisao = 0
        self.rotulo = "-- C"

    def atualizar(self, agora):
        if ticks_diff(agora, self.prazo) < 0:
            return False
        self.prazo = ticks_add(agora, LEITURA_NTC_MS)
        try:
            if self.adc is None:
                self.adc = ADC(Pin(GPIO_NTC), atten=ADC.ATTN_11DB)
            total = 0
            for _ in range(8):
                total += self.adc.read_uv()
            celsius = converter_celsius(total // 8)
        except (AttributeError, OSError, ValueError):
            celsius = None
        self.historico[self.revisao % AMOSTRAS] = celsius
        self.revisao += 1
        self.rotulo = "-- C" if celsius is None else "{:.1f} C".format(celsius)
        return True

    def copiar(self, destino):
        quantidade = min(self.revisao, AMOSTRAS)
        inicio = self.revisao - quantidade
        for indice in range(quantidade):
            destino[indice] = self.historico[(inicio + indice) % AMOSTRAS]
        return quantidade
