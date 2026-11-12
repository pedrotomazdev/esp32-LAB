# Nenza ESP32 — Painel embarcado Nenza Corp

Firmware em **MicroPython** para uma **ESP32 DevKit V1** com display OLED SSD1306 de 128 × 64 pixels, três botões, buzzer, LED RGB e sensor LDR. A placa funciona como painel físico de monitoramento do **NenzaHub** e como controle remoto de ações do **Ultimate Nenza**, além de oferecer gráficos, configurações, modo foco, animações e fatos do Chuck Norris.

> **Estado desta versão:** implementação monolítica, concentrada em `main.py` (1.039 linhas). Este README documenta o código **antes da modularização**. Não representa uma versão refatorada nem certifica testes em hardware.

## Funcionalidades

### Monitoramento do NenzaHub

- Conecta-se à rede Wi-Fi configurada e consulta periodicamente a API HTTP indicada por `API_URL`.
- Atualiza os dados a cada **15 segundos**.
- Apresenta seis telas: **NenzaHub**, **CPU**, **Memória**, **Rede**, **Bateria** e **Disco**.
- Mostra estados de conexão como `CONECTANDO`, `LIVE`, `ALERTA`, `SEM WIFI`, `API FALHOU` e `ERRO REDE`.
- Preserva o último conjunto de telas recebido quando a API deixa de responder, exibindo a indicação de cache.
- Mantém até **60 amostras** para gráficos de ping, temperatura da CPU e uso de RAM.

### Controle remoto do PC

Envia comandos HTTP para o serviço **NenzaBuddy**, na porta **8085**, utilizando autenticação por token. O menu inclui ações para:

- Abrir ou minimizar o Ultimate Nenza.
- Testar a conexão.
- Abrir Chrome, Brave e Discord.
- Acionar NenzaHub, NenzaHome e NenzaLab.

Os nomes dos comandos são enviados conforme os identificadores definidos em `MENU`. A execução depende de um serviço externo que aceite `POST /nenzabuddy/commands/<comando>` e responda com JSON.

### Interface e recursos locais

- Menu OLED com ícones de 8 × 8 pixels e rolagem animada.
- Navegação por três botões físicos e suporte a pressionamento longo do terceiro botão.
- Favoritos persistentes para atalhos de comandos do PC.
- Configurações persistentes por **NVS**: volume, animação, cor do LED, música de boot e favorito.
- Controle de buzzer PWM, com sons de interface, alerta de fim do foco e duas melodias de inicialização.
- LED RGB de **ânodo comum**, com cores fixas, modo automático por status, arco-íris, polícia, batimento e modo **branco no escuro** com LDR.
- Temporizador de foco de **25 minutos**.
- Descanso de tela após **60 segundos** de inatividade, com animação de gatinho ou logotipo **Nenza DVD**.
- Consulta HTTPS à API pública `api.chucknorris.io`, com paginação de fatos adaptados à largura do OLED.

## Hardware e pinagem

A tabela reflete **os pinos efetivamente declarados no `main.py` enviado**; confira as ligações físicas antes de executar.

| Componente | GPIO | Configuração |
| --- | --- | --- |
| OLED SSD1306 — SDA | **18** | `SoftI2C`, endereço `0x3C` |
| OLED SSD1306 — SCL | **15** | `SoftI2C`, 400 kHz |
| Botão 1 | **27** | Entrada com `PULL_UP` |
| Botão 2 | **26** | Entrada com `PULL_UP` |
| Botão 3 | **25** | Entrada com `PULL_UP` |
| Buzzer | **19** | PWM |
| RGB — canal R | **2** | Saída digital, lógica invertida |
| RGB — canal G | **4** | Saída digital, lógica invertida |
| RGB — canal B | **5** | Saída digital, lógica invertida |
| LDR | **34** | ADC, atenuação de 11 dB |

**Observações elétricas:**

- Os botões usam pull-up interno; o acionamento esperado é entre o GPIO e **GND**.
- O RGB está configurado com `RGB_ATIVO_BAIXO = True`, adequado à lógica de um LED de ânodo comum **com resistores limitadores em cada canal**.
- O comentário no código especifica um divisor resistivo para o LDR: **LDR entre 3V3 e GPIO34; resistor entre GPIO34 e GND**.
- O buzzer deve estar ligado por um circuito de acionamento compatível com sua corrente e tensão. O código não especifica a topologia elétrica completa.
- **Não aplique 5 V diretamente nos GPIOs da ESP32.**
- Alguns GPIOs utilizados também participam de condições de inicialização da ESP32; conexões externas inadequadas podem impedir o boot.

## Controles

| Contexto | Botão 1 (GPIO27) | Botão 2 (GPIO26) | Botão 3 (GPIO25) |
| --- | --- | --- | --- |
| Menu principal | Item anterior | Próximo item | Abrir/confirmar |
| Gráficos iniciais | Métrica anterior | Próxima métrica | Abrir menu |
| Tela de fato do Chuck Norris | Página anterior | Próxima página / buscar novo | Voltar ao menu |
| Configurações | Anterior / diminuir | Próximo / aumentar | Editar / confirmar / voltar |
| Modo foco | — | — | Cancelar / voltar |
| Ação remota exibida | — | — | Voltar |

**Pressionamento longo do botão 3:** na tela inicial, executa o atalho favorito configurado; no menu principal, quando o item é elegível, define esse item como favorito.

> O tratamento do botão 3 distingue gestos curtos e longos. Os botões 1 e 2 são tratados como cliques simples.

## Estrutura do menu

O código define os seguintes itens, nesta ordem:

1. ULTIMATE NENZA
2. HEALTH API
3. CPU
4. MEMORIA
5. REDE
6. BATERIA
7. DISCO
8. MINIMIZAR NENZA
9. TESTAR CONEXAO
10. ABRIR CHROME
11. NENZAHUB
12. NENZAHOME
13. NENZALAB
14. ABRIR BRAVE
15. ABRIR DISCORD
16. MODO TRABALHO
17. CONFIGURACOES
18. GRAFICOS
19. CHUCK NORRIS

**Nota:** o item `MODO TRABALHO` inicia o temporizador de foco local; não é um comando HTTP. O item `GRAFICOS` retorna à visualização inicial dos gráficos.

## Arquivos e dependências

### Arquivos locais esperados

```text
/
├── main.py       # Aplicação completa nesta versão
├── secrets.py    # Configurações privadas de rede e integração
└── ssd1306.py    # Driver MicroPython do OLED
```

O `main.py` utiliza módulos integrados ou normalmente disponíveis em builds compatíveis de MicroPython para ESP32: `machine`, `time`, `esp32`, `_thread`, `network`, `socket`, `ssl` e `json`.

O driver `ssd1306.py` deve estar disponível na placa, salvo se já estiver incluído no firmware utilizado.

### Configuração privada

Crie um arquivo `secrets.py` com os nomes de configuração esperados pelo programa:

```python
WIFI_SSID = "NOME_DA_REDE"
WIFI_PASSWORD = "SENHA_DA_REDE"
API_URL = "http://192.168.1.100:8080/api/health"

NENZA_HOST = "192.168.1.100"
NENZA_TOKEN = "TOKEN_DO_SERVICO"
```

O endereço e a rota acima são **exemplos**. Ajuste `API_URL` para o endpoint real que devolve o JSON esperado pelo painel. O código atual pressupõe URL **HTTP** com caminho e permite porta explícita; não há suporte genérico a URLs HTTPS nesse monitor local.

`NENZA_HOST` e `NENZA_TOKEN` são utilizados nos comandos remotos. Sem eles, a interface indica `SEM CONFIG PC`.

**Segurança:** não publique `secrets.py` em repositórios públicos. Inclua-o no `.gitignore` antes do primeiro commit.

```gitignore
secrets.py
__pycache__/
*.pyc
.env
```

## Formato esperado da API de monitoramento

O firmware espera um objeto JSON com `status` textual e utiliza, quando disponíveis, campos como:

```json
{
  "status": "ok",
  "latency": { "networkPingMs": 12 },
  "uptime": { "systemSeconds": 3600 },
  "cpu": { "cores": 8, "temperature": 45 },
  "thermal": { "averageTemp": 42 },
  "memory": { "usagePercent": 55, "usedMB": 2200, "totalMB": 4000 },
  "wifi": { "ip": "192.168.1.100", "signalPercent": 80, "linkSpeedMbps": 150 },
  "android": {
    "battery": { "percentage": 75, "temperature": 30, "plugged": "PLUGGED" },
    "disk": { "usagePercent": 60, "used": "60 GB", "available": "40 GB" }
  }
}
```

Este JSON é **ilustrativo**, elaborado a partir dos campos acessados pelo código; não é uma especificação oficial do servidor. Valores ausentes são tratados de maneiras diferentes conforme a tela. O campo `status` é obrigatório para que a resposta seja considerada válida.

## Instalação e execução

1. Instale uma versão de MicroPython compatível com sua ESP32.
2. Conecte a placa ao computador e abra o Thonny ou ferramenta equivalente.
3. Envie `ssd1306.py` e `secrets.py` para o sistema de arquivos da ESP32.
4. Envie `main.py` para a raiz do sistema de arquivos.
5. Reinicie a placa. O bloco `if __name__ == "__main__": main()` inicia a aplicação.
6. Confira no terminal a mensagem de inicialização e os logs de rede.

**Importante:** esta versão pode exigir memória livre suficiente para compilar/carregar o `main.py`. Se houver `MemoryError` ou erro de armazenamento, registre a mensagem exata antes de apagar arquivos ou firmware.

## Funcionamento interno

A aplicação combina dois fluxos principais:

- **Loop de interface (`main`)**: inicializa OLED, botões, NVS, buzzer, RGB e LDR; lê entradas, atualiza estados e redesenha telas conforme necessário.
- **Thread de monitoramento (`atualizar_servidor` / `monitorar_servidor`)**: conecta ao Wi-Fi, consulta periodicamente a API local, atualiza telas e histórico, processa comandos remotos e busca fatos do Chuck Norris quando solicitados.

As duas partes compartilham estados globais, incluindo `estado`, `historico`, `acao_pc` e `fato_chuck`.

O cliente HTTP implementado em `consultar_api()` aceita respostas JSON com `Content-Length` e também transferência `chunked`, com limite de corpo de **16.384 bytes**. Para a API do Chuck Norris, usa HTTPS e resolve `api.chucknorris.io` na porta 443.

## Configurações e valores padrão

| Parâmetro | Valor no código |
| --- | --- |
| Debounce | 30 ms |
| Pressionamento longo | 650 ms |
| Atualização da API | 15 s |
| Histórico de gráficos | 60 amostras |
| Inatividade até descanso de tela | 60 s |
| Temporizador de foco | 25 min |
| Volume inicial do buzzer | 70% |
| Animação inicial | Gatinho |
| Cor RGB inicial | Automático |
| Música de boot inicial | Raining Blood |
| Intervalo de leitura do LDR | 100 ms |
| Limiares LDR | Escuro: 18.000 / claro: 24.000 (leitura de 16 bits) |

Configurações salvas em NVS podem substituir os valores iniciais.

## Limitações conhecidas e pontos de atenção

- **Código monolítico:** interface, rede, hardware, estado e regras de negócio estão no mesmo arquivo, o que dificulta manutenção e pode aumentar a exigência de RAM durante a compilação.
- **Memória:** a quantidade de flash livre e a RAM disponível precisam ser medidas na placa. O tamanho do arquivo, isoladamente, não demonstra qual recurso está esgotado.
- **Concorrência:** o monitoramento usa `_thread` e compartilha variáveis com a interface; futuras mudanças devem preservar consistência e responsividade.
- **Rede bloqueante:** DNS, conexões e leitura de respostas podem bloquear a thread de monitoramento até o timeout configurado.
- **Limite de JSON:** respostas maiores que 16 KB são rejeitadas.
- **Dependência externa:** comandos de PC exigem o serviço NenzaBuddy; monitoramento exige API compatível; fatos do Chuck Norris exigem acesso à internet e suporte TLS no firmware.
- **Logs:** `DEBUG_LDR = True` habilita mensagens periódicas no terminal quando o modo LDR está ativo.
- **Atualização segura:** mantenha uma cópia funcional antes de refatorar ou substituir arquivos.

## Próximos passos sugeridos

A próxima evolução planejada é separar o firmware em módulos de hardware, interface e serviços, preservando comportamento, pinagem e funcionalidades. A otimização deve ser acompanhada por medições reais de **RAM livre**, **RAM utilizada** e **espaço livre na flash** antes e depois das mudanças.

---

**Nenza Corp**  
*𝕾𝖔 𝖞𝖔𝖚 𝖐𝖓𝖔𝖜 𝖎𝖙'𝖘 𝖌𝖔𝖔𝖉 👌*
