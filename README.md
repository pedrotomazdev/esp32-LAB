# Nenza ESP32 — Painel embarcado Nenza Corp

Firmware em **MicroPython** para uma **ESP32 DevKit V1** com display OLED SSD1306 de 128 × 64 pixels, três botões, buzzer, LED RGB e sensor LDR. A placa funciona como painel físico de monitoramento do **NenzaHub** e como controle remoto de ações do **Ultimate Nenza**, além de oferecer gráficos, configurações, modo foco, e animações.

> **Estado desta versão** — Firmware modular com validação em computador. Os testes na ESP32 e as medições de memória estão pendentes.

## Alterações desta versão

- Firmware dividido em módulos de configuração, periféricos, telas, animações, monitoramento e transporte HTTP. A thread de rede continua separada do loop do OLED.
- Gráficos com buffer circular de 60 amostras e reutilização do buffer de desenho. O cliente HTTP fecha o socket antes de decodificar o JSON. O diagnóstico de memória pode ser ativado em `config.py`.
- Portal Wi-Fi ativado pelo B3 na inicialização. O OLED mostra a rede, a senha temporária e o IP. O formulário salva a configuração em `secrets.json`, com `secrets.py` como reserva.
- Remoção das opções **Chuck Norris** e **Testar conexão**. Os demais favoritos salvos mantêm a ação original. Se **Testar conexão** era o favorito, o atalho passa a abrir **Ultimate Nenza**. O gráfico de ping do NenzaHub continua disponível.

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

## Hardware e pinagem

A tabela reflete **os pinos usados pelo firmware**; confira as ligações físicas antes de executar.

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
9. ABRIR CHROME
10. NENZAHUB
11. NENZAHOME
12. NENZALAB
13. ABRIR BRAVE
14. ABRIR DISCORD
15. MODO TRABALHO
16. CONFIGURACOES
17. GRAFICOS

**Nota:** o item `MODO TRABALHO` inicia o temporizador de foco local; não é um comando HTTP. O item `GRAFICOS` retorna à visualização inicial dos gráficos.

## Arquivos e dependências

### Arquivos locais esperados

```text
/
├── main.py          # Entrada, inicialização e loop de interface
├── config.py        # Constantes e chave de diagnóstico
├── perifericos.py   # Botões, buzzer, NVS e controle do RGB/LDR
├── telas.py         # Menu, telas e gráficos
├── animacoes.py     # Gatinho e Nenza DVD
├── monitor.py       # Wi-Fi, API, comandos e histórico
├── http_json.py     # Transporte HTTP e decodificação JSON
├── rede_config.py   # Leitura e gravação da configuração de rede
├── portal_config.py # Ponto de acesso e servidor temporários
├── index.html       # Formulário de configuração
├── diagnostico.py   # Medições opcionais
├── secrets.py       # Configurações privadas de rede e integração
└── ssd1306.py       # Driver MicroPython do OLED
```

O `main.py` utiliza módulos integrados ou normalmente disponíveis em builds compatíveis de MicroPython para ESP32: `machine`, `time`, `esp32`, `_thread`, `network`, `socket` e `json`.

O driver `ssd1306.py` deve estar disponível na placa, salvo se já estiver incluído no firmware utilizado.

### Configuração privada

#### Pelo navegador

1. Envie `rede_config.py`, `portal_config.py` e `index.html` para a raiz da placa junto com o firmware.
2. Segure o botão B3 ao ligar ou reiniciar a ESP32. Solte quando o OLED mostrar `CONFIG WIFI`.
3. Conecte-se à rede `Nenza-Config` com a senha temporária exibida no OLED. Mantenha a conexão se o celular avisar que a rede está sem internet.
4. Abra no navegador `http://` seguido do IP exibido no OLED. Preencha o Wi-Fi e a URL HTTP do NenzaHub. Para habilitar comandos do PC, preencha o host e o token juntos.
5. Toque em **Salvar e reiniciar**. A placa grava `/secrets.json` e reinicia. Se a nova configuração falhar, repita o acesso com B3 e corrija os campos.

O portal abre antes da thread de monitoramento e fecha ao salvar ou após cinco minutos. A página usa HTTP dentro da rede temporária protegida por WPA2. Os campos começam vazios. Cada envio substitui os cinco valores, e as credenciais ficam armazenadas em texto no sistema de arquivos da placa.

#### Pelo arquivo Python

Na ausência de uma configuração JSON válida, o firmware usa o `secrets.py` existente. Para configurar manualmente por esse arquivo, use estes campos:

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

1. Conecte a placa via USB, interrompa o firmware com Ctrl+C e confirme que o REPL está acessível. Use o Thonny ou uma ferramenta equivalente.
2. Copie para o computador o `main.py` funcional, o driver e os demais arquivos da placa. Guarde a cópia de `secrets.py` em local privado. Registre a versão do MicroPython e confira o espaço com `os.statvfs("/")`.
3. Envie primeiro os novos módulos listados acima. Mantenha as cópias de `secrets.py` e `ssd1306.py` já instaladas, se funcionais. Envie o novo ponto de entrada como `main_novo.py`.
4. No REPL, execute `import main_novo; main_novo.main()` e faça os testes abaixo. Após o teste, interrompa a aplicação e faça um reset para encerrar a thread de teste antes de executar novamente. O reset ainda inicializará o firmware anterior.
5. Com a nova versão validada, interrompa o firmware anterior, renomeie `main.py` para `main_anterior.py` e `main_novo.py` para `main.py`. Reinicie a placa e valide a inicialização automática.
6. Para restaurar, interrompa o novo firmware pelo REPL, renomeie o novo `main.py` e devolva `main_anterior.py` ao nome `main.py`. Reinicie. O procedimento usa o sistema de arquivos e preserva o firmware MicroPython e a NVS.

### Validação na placa

- Inicialize a frio e confira OLED, música, botões, toques longos, favoritos, menu e rolagem.
- Percorra as telas e os gráficos. Deixe o histórico ultrapassar 60 amostras e confira a ordem, lacunas em falhas e a reconexão Wi-Fi.
- Teste os comandos remotos em um PC autorizado. Verifique a resposta dos controles durante uma consulta lenta.
- Teste Pomodoro, animações, RGB e LDR. Reinicie para confirmar a persistência das configurações NVS.

### Memória e compatibilidade

- **Flash** — `os.statvfs("/")` mede o espaço do sistema de arquivos. Confira-o antes de transferir a versão de teste e manter a cópia anterior na placa.
- **Compilação no boot** — Cada arquivo fonte é compilado separadamente no import. Módulos menores podem diminuir o pico do compilador. O heap necessário para manter todos os módulos depende do build e do carregamento. Se o pico ocorrer antes da primeira linha de `main.py`, use uma medição no REPL antes de importar o ponto de entrada.
- **Execução** — Pilha da thread, corpo HTTP, árvore JSON e snapshots coexistentes são candidatos a picos. O limite do corpo continua em 16 KiB. Uma linha de cabeçalho ainda usa `readline()`, e o caminho chunked ainda converte o buffer para bytes antes do parse.
- **Medição** — Ative `DIAGNOSTICO_MEMORIA` em `config.py` para registrar heap e flash na inicialização, heap após imports, Wi-Fi, API local e a cada minuto no loop. Os pontos durante o loop amostram o heap sem coleta. Compare a versão original e a nova na mesma placa, com o mesmo build, endpoints e ações. Registre heap antes/depois dos mesmos eventos e falhas observadas. Os logs são amostras do heap MicroPython e podem perder o pico durante compilação. Também não medem diretamente a pilha nativa ou o heap do ESP-IDF.
- **Pré-compilação** — Se o gargalo for a compilação no dispositivo, confira `sys.implementation._mpy` e use o `mpy-cross` compatível com o build da placa. Valide os módulos `.mpy` separadamente e mantenha `main.py` como ponto de entrada. A entrega usa fonte. As constantes continuam em um módulo compartilhado. A aplicação de `const()` merece medição no build alvo, especialmente para valores importados por vários módulos.

## Funcionamento interno

A aplicação combina dois fluxos principais:

- **Loop de interface (`main`)**: inicializa OLED, botões, NVS, buzzer, RGB e LDR; lê entradas, atualiza estados e redesenha telas conforme necessário.
- **Thread de monitoramento (`atualizar_servidor` / `monitorar_servidor`)**: conecta ao Wi-Fi, consulta periodicamente a API local, atualiza telas e histórico, e processa comandos remotos.

O monitor publica snapshots e mensagens como tuplas. O histórico tem 60 posições em um buffer circular, e a interface copia somente a série exibida para uma lista reutilizada. A trava cobre a escrita e a cópia do histórico. A renderização ocorre após a liberação da trava. O JSON bruto da API fica limitado à função que prepara o snapshot.

A thread mantém as operações bloqueantes de Wi-Fi, DNS, e HTTP fora do loop do OLED. Uma migração para `uasyncio` exigiria operações de rede cooperativas para preservar essa separação. O custo da pilha da thread continua presente.

O cliente HTTP implementado em `consultar_api()` aceita respostas JSON com `Content-Length` e também transferência `chunked`, com limite de corpo de **16.384 bytes**.

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
- **Dependência externa:** comandos de PC exigem o serviço NenzaBuddy; monitoramento exige API compatível.
- **Logs:** `DEBUG_LDR = True` habilita mensagens periódicas no terminal quando o modo LDR está ativo.
- **Atualização segura:** mantenha uma cópia funcional antes de refatorar ou substituir arquivos.

## Próximos passos sugeridos

A próxima evolução planejada é separar o firmware em módulos de hardware, interface e serviços, preservando comportamento, pinagem e funcionalidades. A otimização deve ser acompanhada por medições reais de **RAM livre**, **RAM utilizada** e **espaço livre na flash** antes e depois das mudanças.

---

**Nenza Corp**  
*𝕾𝖔 𝖞𝖔𝖚 𝖐𝖓𝖔𝖜 𝖎𝖙'𝖘 𝖌𝖔𝖔𝖉 👌*
