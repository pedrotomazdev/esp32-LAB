from config import DIAGNOSTICO_MEMORIA

if DIAGNOSTICO_MEMORIA:
    from diagnostico import medir_memoria
    medir_memoria("Inicializacao", flash=True)

from machine import ADC, Pin, SoftI2C
from ssd1306 import SSD1306_I2C
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms
from config import (
    AMOSTRAS, ANIMACOES, CORES_LED, DEBUG_LDR, GPIO_LDR, GRAFICOS, INATIVIDADE_MS,
    LEITURA_LDR_MS, LIMIAR_CLARO, LIMIAR_ESCURO, LINHA_MENU_PX, LOG_LDR_MS,
    MODO_LDR, POMODORO_MS, QUADRO_LED_MS, QUADRO_MENU_MS, QUADRO_MS, RGB_ATIVO_BAIXO,
    TOQUE_LONGO_MS,
)
from animacoes import CICLO_MS, CICLO_DVD_MS, desenhar_gato, desenhar_nenza_dvd
from perifericos import Botao, Buzzer, ambiente_escuro, atualizar_led_rgb, ler_config, salvar_config
from telas import (
    ACOES_FAVORITAS, MENU, deslocamento_menu, desenhar_acao, desenhar_config,
    desenhar_foco, desenhar_grafico, desenhar_menu, desenhar_tela,
)
import monitor

if DIAGNOSTICO_MEMORIA:
    medir_memoria("Modulos carregados")


def main():
    from esp32 import NVS

    i2c = SoftI2C(sda=Pin(18), scl=Pin(15), freq=400_000)
    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    botoes = (Botao(27), Botao(26), Botao(25))
    if botoes[2].pin.value() == 0:
        sleep_ms(TOQUE_LONGO_MS)
        if botoes[2].pin.value() == 0:
            try:
                from portal_config import executar
                executar(oled)
            except (ImportError, OSError, ValueError, MemoryError) as erro:
                print("[CONFIG] Falha no portal:", erro)
                oled.fill(0)
                oled.text("ERRO NO PORTAL", 0, 24)
                oled.show()
                sleep_ms(1500)
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
    inicio = True
    metrica = 0
    anterior = ler_config(nvs, "favorito", 0, len(ACOES_FAVORITAS))
    # Na lista anterior, "Testar conexao" ocupava o indice 2.
    padrao_favorito = 0 if anterior == 2 else anterior - int(anterior > 2)
    favorito = ler_config(nvs, "favorito_v2", padrao_favorito, len(ACOES_FAVORITAS) - 1)
    acao_atalho = None
    prazo_foco = None
    segundos_foco = None
    historico_exibido = None
    valores_grafico = [None] * AMOSTRAS
    aviso_menu = None
    item_config = None
    editando = False
    exibido = None
    redesenhar = True

    try:
        import _thread
        monitor.trava_historico = _thread.allocate_lock()
        _thread.start_new_thread(monitor.atualizar_servidor, ())
    except Exception as erro:
        monitor.estado = ("ERRO REDE", None)
        print("Monitor:", erro)

    ultimo_clique = ticks_ms()
    ultimo_diagnostico = ultimo_clique
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
            snapshot = monitor.estado
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
                        if inicio and acao_atalho is None and monitor.acao_pc[0] is None:
                            acao_atalho = ACOES_FAVORITAS[favorito]
                            monitor.acao_pc = (MENU[acao_atalho][1], "EXECUTANDO...")
                        elif item_config is None and no_menu and selecionado in ACOES_FAVORITAS:
                            favorito = ACOES_FAVORITAS.index(selecionado)
                            salvar_config(nvs, "favorito_v2", favorito)
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
                    elif indice == 2:
                        destino = MENU[selecionado][1]
                        if destino == "config":
                            item_config = 0
                        elif no_menu and destino == "graficos":
                            inicio = True
                            no_menu = False
                        elif no_menu and destino == "pc":
                            prazo_foco = ticks_add(agora, POMODORO_MS)
                            segundos_foco = POMODORO_MS // 1000
                            no_menu = False
                            buzzer.desligar()
                            continue
                        elif no_menu and isinstance(destino, str):
                            if monitor.acao_pc[0] is None:
                                monitor.acao_pc = (destino, "EXECUTANDO...")
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

            resultado_pc = monitor.acao_pc
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
                or (inicio and monitor.revisao_historico != historico_exibido)
            ):
                destino = MENU[selecionado][1]
                if segundos_foco is not None:
                    desenhar_foco(oled, segundos_foco)
                elif acao_atalho is not None:
                    desenhar_acao(oled, acao_atalho, resultado_pc[1])
                elif inicio:
                    historico_exibido, quantidade = monitor.copiar_metrica(metrica, valores_grafico)
                    desenhar_grafico(oled, metrica, valores_grafico, quantidade, snapshot[0])
                elif item_config is not None:
                    desenhar_config(oled, item_config, editando, buzzer.volume, animacao, cor_led, musica_boot)
                elif no_menu:
                    offset = deslocamento_menu(offset_menu, inicio_rolagem, agora)
                    desenhar_menu(oled, selecionado, aviso_menu or snapshot[0], offset=offset)
                    quadro_menu = agora
                    if offset == 0:
                        offset_menu = 0
                elif isinstance(destino, int):
                    desenhar_tela(oled, destino, snapshot)
                else:
                    desenhar_acao(oled, selecionado, resultado_pc[1])
                exibido = snapshot
                acao_exibida = resultado_pc
                redesenhar = False

            if DIAGNOSTICO_MEMORIA and ticks_diff(agora, ultimo_diagnostico) >= 60_000:
                medir_memoria("Operacao", coletar=False)
                ultimo_diagnostico = agora
            sleep_ms(5)
    finally:
        buzzer.desligar()
        buzzer.pwm.deinit()


if __name__ == "__main__":
    main()
