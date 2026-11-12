from machine import ADC, Pin
from time import sleep_ms


def main():
    adc = ADC(Pin(35), atten=ADC.ATTN_11DB)
    print("GPIO 35 | 16 amostras por leitura | Ctrl+C para parar")
    try:
        while True:
            total = 0
            minimo = 65535
            maximo = 0
            for _ in range(16):
                valor = adc.read_u16()
                total += valor
                minimo = min(minimo, valor)
                maximo = max(maximo, valor)
                sleep_ms(5)

            print("GPIO35 ADC | media={} min={} max={}".format(total // 16, minimo, maximo))
            sleep_ms(920)
    except KeyboardInterrupt:
        print("Teste encerrado.")


if __name__ == "__main__":
    main()
