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
DEBUG_LDR = False
LOG_LDR_MS = 1000
LIMIAR_ESCURO = 18_000
LIMIAR_CLARO = 24_000
QUADRO_LED_MS = 150
POMODORO_MS = 25 * 60_000
TOQUE_LONGO_MS = 650
GRAFICOS = (("PING", " ms"), ("CPU", " C"), ("RAM", "%"), ("TEMP. AMB", " C"))
GRAFICO_AMBIENTE = len(GRAFICOS) - 1
GPIO_NTC = 35
LEITURA_NTC_MS = 15_000
NTC_R25_OHM = 10_000
NTC_RESISTOR_OHM = 10_000
NTC_BETA_K = 3950
NTC_ALIMENTACAO_UV = 3_300_000
NTC_LIGADO_A_3V3 = True  # NTC entre 3V3 e GPIO35, resistor entre GPIO35 e GND.
TITULOS = ("NENZAHUB", "CPU", "MEMORIA", "REDE", "BATERIA", "DISCO")
ANIMACOES = ("GATINHO", "NENZA DVD")
MUSICAS_BOOT = ("RAINING BLOOD", "COWBOYS FROM HELL")
DIAGNOSTICO_MEMORIA = False
