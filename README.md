# AFK Fortnite

Programa para Windows que fica no lobby, entra na partida, espera o tempo configurado e volta ao lobby, repetindo até você parar. Ele reconhece a tela comparando prints que você mesmo importa.

> Usar automação no Fortnite viola os termos de uso da Epic Games e pode levar a banimento da conta. Use por sua conta e risco.

## Como usar

1. Baixe `AFK Fortnite.exe` e coloque numa pasta qualquer. Não precisa instalar Python.
2. Abra o executável. Se o Windows SmartScreen avisar, clique em **Mais informações → Executar assim mesmo**.
3. Importe as 4 imagens de referência (veja abaixo).
4. Ajuste as configurações e clique em **Salvar**.
5. Abra o Fortnite no lobby, clique em **INICIAR (F9)** e, durante a contagem de 5 segundos, clique na janela do jogo.

Para parar, use **PARAR (F8)** ou leve o mouse para um canto da tela (proteção do pyautogui).

## Imagens de referência

O bot só funciona com prints tirados **na sua resolução e com a sua escala de tela**. Prints de outro computador quase sempre falham.

| Arquivo | O que capturar |
| --- | --- |
| `lobby.png` | Botão **Jogar** no lobby |
| `partida.png` | Um pedaço fixo do HUD durante a partida |
| `menu.png` | Ícone das 3 listras do menu |
| `voltar_lobby.png` | Botão **Voltar ao lobby** |

Como fazer:

1. No jogo, use `Win + Shift + S` e recorte só o elemento, com pouca sobra em volta.
2. Salve o recorte (png, jpg ou bmp).
3. No programa, clique em **Importar** na linha da imagem e escolha o arquivo.

As imagens ficam salvas em `%LOCALAPPDATA%\AFK-Fortnite\imagens`. A pasta é criada automaticamente, e o botão **Abrir pasta** leva até ela.

Se faltar alguma imagem, o programa pede ao clicar em Iniciar. Se o lobby não for reconhecido várias vezes seguidas, a linha fica marcada como **não reconhecida** e aparece um aviso: tire um print novo e importe de novo. Baixar um pouco a **Confiança da imagem** (por exemplo 0.7) também ajuda.

## Configurações

| Campo | Para que serve |
| --- | --- |
| Tempo na partida (min) | Quanto tempo fica na partida antes de sair |
| Tecla de jogar | Tecla que inicia a busca no lobby (padrão `p`) |
| Confiança da imagem | De 0.1 a 1; quanto maior, mais exata precisa ser a imagem |
| Intervalo de verificação (s) | De quanto em quanto tempo a tela é conferida |
| Timeout da fila (min) | Tempo máximo na fila antes de voltar ao lobby |
| Mostrar popup de tempo | Mostra um contador pequeno no canto da tela |

As configurações ficam em `config.json`, na mesma pasta do executável.

## Gerar o executável a partir do código

Precisa de Python 3.12 instalado.

```bat
build.bat
```

O script instala as dependências de `requirements.txt` e gera `publish\AFK Fortnite.exe`.

Para rodar sem gerar o executável:

```bat
python -m pip install -r requirements.txt
python afk_gui.py
```
