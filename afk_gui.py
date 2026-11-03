import os
import sys
import json
import time
import random
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox, filedialog

import pyautogui
import keyboard
from PIL import Image

# ---------- CAMINHOS / ARQUIVOS ----------
BASE = os.path.dirname(os.path.abspath(sys.argv[0]))
ARQUIVO_CFG = os.path.join(BASE, "config.json")
PASTA_IMAGENS = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "AFK-Fortnite", "imagens")

# Quantas tentativas seguidas sem achar o lobby antes de sugerir trocar a imagem.
FALHAS_ATE_SUGERIR = 5

IMAGENS = {
    "lobby.png": "Lobby (botão Jogar)",
    "partida.png": "Partida (HUD)",
    "menu.png": "Ícone das 3 listras",
    "voltar_lobby.png": "Botão Voltar ao lobby",
}

TECLA_MENU = "esc"
TECLA_PARAR = "f8"
TECLA_INICIAR = "f9"

PADRAO = {
    "tempo_partida_min": 10,
    "tecla_jogar": "p",
    "confianca": 0.8,
    "intervalo": 3,
    "timeout_fila_min": 10,
    "overlay": True,
}

pyautogui.FAILSAFE = True

# ---------- CORES ----------
BG = "#14161c"
CARD = "#1e212b"
BORDA = "#2b2f3c"
TEXTO = "#e8eaf0"
CINZA = "#8b90a0"
ROXO = "#7c5cff"
VERDE = "#2ecc71"
VERMELHO = "#ff5c6c"
AMARELO = "#f5c542"


def garantir_pasta_imagens():
    os.makedirs(PASTA_IMAGENS, exist_ok=True)
    return PASTA_IMAGENS


def caminho_imagem(arq):
    return os.path.join(PASTA_IMAGENS, arq)


def carregar_cfg():
    cfg = dict(PADRAO)
    if os.path.exists(ARQUIVO_CFG):
        try:
            with open(ARQUIVO_CFG, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def salvar_cfg(cfg):
    with open(ARQUIVO_CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


class Overlay:
    """Popup pequeno, sempre no topo, que não rouba o foco nem recebe cliques."""

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.85)
        self.win.configure(bg="#0b0d12")

        self.l1 = tk.Label(self.win, text="", bg="#0b0d12", fg=CINZA,
                           font=("Segoe UI", 10, "bold"), width=22)
        self.l1.pack(padx=14, pady=(8, 0))
        self.l2 = tk.Label(self.win, text="", bg="#0b0d12", fg=VERDE,
                           font=("Consolas", 24, "bold"), width=8)
        self.l2.pack(padx=14, pady=(0, 8))
        self.visivel = False

    def _flags(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.win.winfo_id())
            estilo = user32.GetWindowLongW(hwnd, -20)
            # NOACTIVATE | TRANSPARENT (clique atravessa) | TOOLWINDOW | LAYERED
            estilo |= 0x08000000 | 0x00000020 | 0x00000080 | 0x00080000
            user32.SetWindowLongW(hwnd, -20, estilo)
        except Exception:
            pass

    def mostrar(self):
        self.win.deiconify()
        self.win.update_idletasks()
        w = self.win.winfo_reqwidth()
        sw = self.win.winfo_screenwidth()
        self.win.geometry(f"+{sw - w - 24}+24")
        self._flags()
        self.visivel = True

    def esconder(self):
        self.win.withdraw()
        self.visivel = False

    def atualizar(self, estado, tempo, cor):
        self.l1.config(text=estado)
        self.l2.config(text=tempo, fg=cor)

    def destruir(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = carregar_cfg()
        self.parar_evt = threading.Event()
        self.thread = None
        self.rodando = False
        garantir_pasta_imagens()

        root.title("AFK Fortnite")
        root.configure(bg=BG)
        root.geometry("600x780")
        root.minsize(560, 740)

        self.overlay = Overlay(root)
        self.ov_estado, self.ov_tempo, self.ov_cor = "", "", TEXTO
        self.montar_ui()
        self.atualizar_imagens()
        keyboard.add_hotkey(TECLA_PARAR, self.parar_via_hotkey)
        keyboard.add_hotkey(TECLA_INICIAR, self.iniciar_via_hotkey)
        root.protocol("WM_DELETE_WINDOW", self.fechar)

    # ---------- UI ----------
    def card(self, parent, titulo):
        frame = tk.Frame(parent, bg=CARD, highlightbackground=BORDA,
                         highlightthickness=1)
        frame.pack(fill="x", padx=18, pady=6)
        tk.Label(frame, text=titulo, bg=CARD, fg=CINZA,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        return frame

    def montar_ui(self):
        # Cabeçalho
        topo = tk.Frame(self.root, bg=BG)
        topo.pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(topo, text="AFK Fortnite", bg=BG, fg=TEXTO,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        self.lbl_status = tk.Label(topo, text="● PARADO", bg=BG, fg=CINZA,
                                   font=("Segoe UI", 11, "bold"))
        self.lbl_status.pack(side="right")

        # Estado atual
        c = self.card(self.root, "ESTADO ATUAL")
        self.lbl_estado = tk.Label(c, text="Aguardando início", bg=CARD, fg=TEXTO,
                                   font=("Segoe UI", 14, "bold"))
        self.lbl_estado.pack(anchor="w", padx=14)
        self.lbl_tempo = tk.Label(c, text="", bg=CARD, fg=CINZA,
                                  font=("Segoe UI", 10))
        self.lbl_tempo.pack(anchor="w", padx=14, pady=(0, 12))

        # Configurações
        c = self.card(self.root, "CONFIGURAÇÕES")
        grade = tk.Frame(c, bg=CARD)
        grade.pack(fill="x", padx=14, pady=(0, 12))
        self.campos = {}
        itens = [
            ("tempo_partida_min", "Tempo na partida (min)"),
            ("tecla_jogar", "Tecla de jogar"),
            ("confianca", "Confiança da imagem (0.1 a 1)"),
            ("intervalo", "Intervalo de verificação (s)"),
            ("timeout_fila_min", "Timeout da fila (min)"),
        ]
        for i, (chave, rotulo) in enumerate(itens):
            tk.Label(grade, text=rotulo, bg=CARD, fg=TEXTO,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w", pady=4)
            e = tk.Entry(grade, width=9, bg=BG, fg=TEXTO, insertbackground=TEXTO,
                         relief="flat", font=("Segoe UI", 11), justify="center",
                         highlightbackground=BORDA, highlightthickness=1)
            e.grid(row=i, column=1, sticky="e", pady=4, ipady=4)
            e.insert(0, str(self.cfg[chave]))
            self.campos[chave] = e
        self.var_overlay = tk.BooleanVar(value=self.cfg.get("overlay", True))
        tk.Checkbutton(grade, text="Mostrar popup de tempo na tela",
                       variable=self.var_overlay, bg=CARD, fg=TEXTO,
                       selectcolor=BG, activebackground=CARD,
                       activeforeground=TEXTO, font=("Segoe UI", 10),
                       highlightthickness=0).grid(row=len(itens), column=0,
                                                  columnspan=2, sticky="w", pady=(6, 0))
        grade.columnconfigure(0, weight=1)

        botoes_cfg = tk.Frame(c, bg=CARD)
        botoes_cfg.pack(fill="x", padx=14, pady=(0, 12))
        self.botao(botoes_cfg, "Salvar", self.salvar, ROXO).pack(side="left")
        self.botao(botoes_cfg, "Restaurar padrão", self.restaurar, BORDA,
                   fg=TEXTO).pack(side="left", padx=8)

        # Imagens
        c = self.card(self.root, "IMAGENS DE REFERÊNCIA")
        tk.Label(c, text="Tire os prints na sua resolução e importe cada um.",
                 bg=CARD, fg=CINZA, font=("Segoe UI", 9)).pack(anchor="w", padx=14)
        self.lbls_img = {}
        for arq, desc in IMAGENS.items():
            linha = tk.Frame(c, bg=CARD)
            linha.pack(fill="x", padx=14, pady=1)
            tk.Label(linha, text=f"{arq}  ·  {desc}", bg=CARD, fg=TEXTO,
                     font=("Segoe UI", 9)).pack(side="left")
            self.botao(linha, "Importar", lambda a=arq: self.importar_imagem(a),
                       BORDA, fg=TEXTO, pequeno=True).pack(side="right", padx=(8, 0))
            lbl = tk.Label(linha, text="", bg=CARD, font=("Segoe UI", 10, "bold"))
            lbl.pack(side="right")
            self.lbls_img[arq] = lbl
        botoes_img = tk.Frame(c, bg=CARD)
        botoes_img.pack(fill="x", padx=14, pady=(8, 12))
        self.botao(botoes_img, "Verificar de novo", self.atualizar_imagens, BORDA,
                   fg=TEXTO).pack(side="left")
        self.botao(botoes_img, "Abrir pasta", self.abrir_pasta_imagens, BORDA,
                   fg=TEXTO).pack(side="left", padx=8)

        # Controles
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(fill="x", padx=18, pady=8)
        self.btn_iniciar = self.botao(ctrl, "▶  INICIAR (F9)", self.iniciar, VERDE,
                                      fg="#0b0d12", grande=True)
        self.btn_iniciar.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.btn_parar = self.botao(ctrl, "■  PARAR (F8)", self.parar, VERMELHO,
                                    fg="#0b0d12", grande=True)
        self.btn_parar.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.btn_parar.config(state="disabled")

        # Log
        c = self.card(self.root, "LOG")
        self.log = tk.Text(c, height=8, bg=BG, fg=TEXTO, relief="flat",
                           font=("Consolas", 9), state="disabled", wrap="word",
                           highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def botao(self, parent, texto, comando, cor, fg="white", grande=False,
              pequeno=False):
        tamanho = 12 if grande else 8 if pequeno else 10
        b = tk.Button(parent, text=texto, command=comando, bg=cor, fg=fg,
                      activebackground=cor, activeforeground=fg, relief="flat",
                      bd=0, cursor="hand2",
                      font=("Segoe UI", tamanho, "bold"),
                      padx=8 if pequeno else 14,
                      pady=10 if grande else 2 if pequeno else 6)
        return b

    # ---------- AÇÕES DA UI ----------
    def escrever_log(self, msg):
        def _f():
            self.log.config(state="normal")
            self.log.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.root.after(0, _f)

    def set_estado(self, estado, cor=TEXTO):
        def _f():
            self.lbl_estado.config(text=estado, fg=cor)
            self.ov_estado, self.ov_cor = estado, cor
            self.overlay.atualizar(self.ov_estado, self.ov_tempo, self.ov_cor)
        self.root.after(0, _f)

    def set_tempo(self, texto, curto=None):
        def _f():
            self.lbl_tempo.config(text=texto)
            self.ov_tempo = curto if curto is not None else ""
            self.overlay.atualizar(self.ov_estado, self.ov_tempo, self.ov_cor)
        self.root.after(0, _f)

    def atualizar_imagens(self):
        garantir_pasta_imagens()
        todas_ok = True
        for arq, lbl in self.lbls_img.items():
            if os.path.exists(caminho_imagem(arq)):
                lbl.config(text="✔ OK", fg=VERDE)
            else:
                lbl.config(text="✘ faltando", fg=VERMELHO)
                todas_ok = False
        return todas_ok

    def imagens_faltando(self):
        return [a for a in IMAGENS if not os.path.exists(caminho_imagem(a))]

    def importar_imagem(self, arq):
        origem = filedialog.askopenfilename(
            parent=self.root,
            title=f"Importar {arq} — {IMAGENS[arq]}",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")])
        if not origem:
            return False
        destino = caminho_imagem(arq)
        try:
            garantir_pasta_imagens()
            with Image.open(origem) as img:
                img.convert("RGB").save(destino, "PNG")
        except Exception as e:
            messagebox.showerror("Erro ao importar", f"Não deu para abrir a imagem:\n{e}")
            return False
        self.escrever_log(f"{arq} importada para {PASTA_IMAGENS}")
        self.atualizar_imagens()
        return True

    def pedir_imagens_faltando(self):
        for arq in self.imagens_faltando():
            if not messagebox.askyesno(
                    "Imagem faltando",
                    f"Falta a imagem \"{IMAGENS[arq]}\" ({arq}).\n\n"
                    "Tire um print desse elemento na sua resolução e importe agora?"):
                return False
            if not self.importar_imagem(arq):
                return False
        return not self.imagens_faltando()

    def sugerir_reimportar(self, arq):
        def _f():
            self.lbls_img[arq].config(text="⚠ não reconhecida", fg=AMARELO)
            messagebox.showwarning(
                "Imagem não reconhecida",
                f"A imagem \"{IMAGENS[arq]}\" ({arq}) não está sendo achada na tela.\n\n"
                "Isso costuma acontecer quando a resolução é diferente. "
                "Pare o bot, tire um print novo e clique em Importar nessa linha.")
        self.root.after(0, _f)

    def abrir_pasta_imagens(self):
        os.startfile(garantir_pasta_imagens())

    def ler_campos(self):
        try:
            novo = {
                "tempo_partida_min": float(self.campos["tempo_partida_min"].get().replace(",", ".")),
                "tecla_jogar": self.campos["tecla_jogar"].get().strip().lower(),
                "confianca": float(self.campos["confianca"].get().replace(",", ".")),
                "intervalo": float(self.campos["intervalo"].get().replace(",", ".")),
                "timeout_fila_min": float(self.campos["timeout_fila_min"].get().replace(",", ".")),
                "overlay": bool(self.var_overlay.get()),
            }
        except ValueError:
            messagebox.showerror("Erro", "Confira os números digitados.")
            return None
        if (not novo["tecla_jogar"] or novo["tempo_partida_min"] <= 0
                or not (0.1 <= novo["confianca"] <= 1)
                or novo["intervalo"] <= 0 or novo["timeout_fila_min"] <= 0):
            messagebox.showerror("Erro", "Algum valor está fora do permitido.")
            return None
        return novo

    def salvar(self):
        novo = self.ler_campos()
        if novo:
            self.cfg.update(novo)
            salvar_cfg(self.cfg)
            self.escrever_log("Configurações salvas.")

    def restaurar(self):
        self.cfg = dict(PADRAO)
        salvar_cfg(self.cfg)
        for chave, e in self.campos.items():
            e.delete(0, "end")
            e.insert(0, str(self.cfg[chave]))
        self.var_overlay.set(True)
        self.escrever_log("Configurações restauradas.")

    def iniciar(self):
        if self.rodando:
            return
        if not self.atualizar_imagens() and not self.pedir_imagens_faltando():
            messagebox.showwarning("Imagens faltando",
                                   "Importe as 4 imagens de referência antes de iniciar.")
            return
        novo = self.ler_campos()
        if not novo:
            return
        self.cfg.update(novo)
        salvar_cfg(self.cfg)

        self.parar_evt.clear()
        self.rodando = True
        self.btn_iniciar.config(state="disabled")
        self.btn_parar.config(state="normal")
        self.lbl_status.config(text="● RODANDO", fg=VERDE)
        self.ov_estado, self.ov_tempo, self.ov_cor = "Iniciando...", "", AMARELO
        self.overlay.atualizar(self.ov_estado, self.ov_tempo, self.ov_cor)
        if self.cfg.get("overlay", True):
            self.overlay.mostrar()
        self.thread = threading.Thread(target=self.rodar, daemon=True)
        self.thread.start()

    def parar(self):
        if self.rodando:
            self.parar_evt.set()
            self.escrever_log("Parando...")

    def iniciar_via_hotkey(self):
        self.root.after(0, self.iniciar)

    def parar_via_hotkey(self):
        self.root.after(0, self.parar)

    def finalizado(self):
        def _f():
            self.rodando = False
            self.btn_iniciar.config(state="normal")
            self.btn_parar.config(state="disabled")
            self.lbl_status.config(text="● PARADO", fg=CINZA)
            self.lbl_estado.config(text="Aguardando início", fg=TEXTO)
            self.lbl_tempo.config(text="")
            self.overlay.esconder()
        self.root.after(0, _f)

    def fechar(self):
        self.parar_evt.set()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.overlay.destruir()
        self.root.destroy()

    # ---------- LÓGICA DO BOT (thread) ----------
    def ver(self, arq):
        try:
            return pyautogui.locateCenterOnScreen(
                caminho_imagem(arq), confidence=self.cfg["confianca"])
        except (pyautogui.ImageNotFoundException, FileNotFoundError):
            return None

    def clicar(self, arq):
        pos = self.ver(arq)
        if pos:
            pyautogui.moveTo(pos.x, pos.y, duration=random.uniform(0.3, 0.7))
            pyautogui.click()
            return True
        return False

    def esperar(self, segundos):
        """Retorna False se foi pedido para parar."""
        fim = time.time() + segundos
        while time.time() < fim:
            if self.parar_evt.is_set():
                return False
            time.sleep(0.2)
        return True

    def rodar(self):
        try:
            self._loop()
        except pyautogui.FailSafeException:
            self.escrever_log("Parado pelo canto da tela (failsafe).")
        except Exception as e:
            self.escrever_log(f"Erro: {e}")
        finally:
            self.escrever_log("Encerrado.")
            self.finalizado()

    def _loop(self):
        cfg = self.cfg
        tempo_partida = cfg["tempo_partida_min"] * 60
        timeout_fila = cfg["timeout_fila_min"] * 60
        TIMEOUT_CARREGANDO = 5 * 60
        ESPERA_MENU_ABERTO = 20

        for i in range(5, 0, -1):
            self.set_estado("Começando em", AMARELO)
            self.set_tempo(f"Começando em {i}s", f"00:0{i}")
            if i == 5:
                self.escrever_log("Clique na janela do Fortnite!")
            if not self.esperar(1):
                return

        self.escrever_log("Rodando.")
        estado = "LOBBY"
        inicio = time.time()
        falhas_lobby = 0
        avisou_lobby = False

        while not self.parar_evt.is_set():
            decorrido = time.time() - inicio

            if estado == "LOBBY":
                self.set_estado("No lobby", ROXO)
                self.set_tempo("")
                if self.ver("lobby.png"):
                    falhas_lobby = 0
                    self.escrever_log(f"Lobby detectado -> {cfg['tecla_jogar'].upper()}")
                    pyautogui.press(cfg["tecla_jogar"])
                    estado, inicio = "FILA", time.time()
                    if not self.esperar(random.uniform(5, 8)):
                        break
                elif decorrido > ESPERA_MENU_ABERTO:
                    self.escrever_log("Lobby não visível, talvez menu aberto -> Esc")
                    pyautogui.press(TECLA_MENU)
                    inicio = time.time()
                    falhas_lobby += 1
                    if falhas_lobby >= FALHAS_ATE_SUGERIR and not avisou_lobby:
                        avisou_lobby = True
                        self.escrever_log("lobby.png não reconhecida, importe um print novo")
                        self.sugerir_reimportar("lobby.png")
                    if not self.esperar(1.5):
                        break

            elif estado == "FILA":
                self.set_estado("Na fila / carregando partida", AMARELO)
                self.set_tempo(f"Esperando há {int(decorrido)}s",
                               f"{int(decorrido) // 60:02d}:{int(decorrido) % 60:02d}")
                if self.ver("partida.png"):
                    self.escrever_log(f"Entrou na partida! Contando {cfg['tempo_partida_min']} min")
                    estado, inicio = "PARTIDA", time.time()
                elif decorrido > timeout_fila and self.ver("lobby.png"):
                    self.escrever_log("Fila demorou demais, voltando ao lobby")
                    estado, inicio = "LOBBY", time.time()

            elif estado == "PARTIDA":
                restante = max(0, int(tempo_partida - decorrido))
                self.set_estado("Em partida", VERDE)
                self.set_tempo(f"Saindo em {restante // 60:02d}:{restante % 60:02d}",
                               f"{restante // 60:02d}:{restante % 60:02d}")
                if decorrido >= tempo_partida:
                    self.escrever_log("Tempo completo -> saindo")
                    estado, inicio = "SAINDO", time.time()
                elif self.ver("lobby.png"):
                    self.escrever_log("Voltou ao lobby antes do tempo")
                    estado, inicio = "LOBBY", time.time()

            elif estado == "SAINDO":
                self.set_estado("Saindo da partida", AMARELO)
                self.set_tempo("")
                if self.ver("lobby.png"):
                    estado, inicio = "LOBBY", time.time()
                elif self.ver("voltar_lobby.png"):
                    self.escrever_log("Clicando em Voltar ao lobby")
                    self.clicar("voltar_lobby.png")
                    estado, inicio = "CARREGANDO", time.time()
                    if not self.esperar(5):
                        break
                elif self.ver("menu.png"):
                    self.escrever_log("Clicando nas três listras")
                    self.clicar("menu.png")
                    if not self.esperar(1.5):
                        break
                else:
                    self.escrever_log("Menu fechado -> Esc")
                    pyautogui.press(TECLA_MENU)
                    if not self.esperar(1.5):
                        break

            elif estado == "CARREGANDO":
                self.set_estado("Carregando o lobby", AMARELO)
                self.set_tempo(f"Esperando há {int(decorrido)}s",
                               f"{int(decorrido) // 60:02d}:{int(decorrido) % 60:02d}")
                if self.ver("lobby.png"):
                    self.escrever_log("Lobby apareceu")
                    estado, inicio = "LOBBY", time.time()
                elif decorrido > TIMEOUT_CARREGANDO:
                    self.escrever_log("Carregamento demorou demais, verificando")
                    estado, inicio = "LOBBY", time.time()

            if not self.esperar(cfg["intervalo"]):
                break


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
