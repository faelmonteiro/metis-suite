"""Janelas informativas: ajuda e status do sistema."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QDialog,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QFont

from agente import config
from agente.gui.dialogs.common import _constrain_dialog_to_parent
from agente.gui.theme_bridge import build_dynamic_qss
from agente.providers_manager import obter_servidores_customizados
from agente.services import (
    searxng_service,
    ollama_service,
)
from agente.ui.theme_manager import get_current_font_sizes

# -----------------------------------------------------------------------------
# As secoes do guia. Dado, nao logica: o `__init__` so percorre e
# chama `_add_help_card`. A ordem e a original e importa — cada card e
# um `addWidget` no scroll, e a posicao dele na tela e a ordem abaixo.
_SECOES_AJUDA = (
    ("ATALHOS GLOBAIS & NAVEGAÇÃO", "⚡", [
    ("Super + R", "Atalho global do sistema para invocar o Metis em janela flutuante no Hyprland."),
    ("Setas ↑ / ↓ / ← / →", "Navega livremente pelos cartões do Dashboard, abas de provedores e modelos."),
    ("Enter ↵", "Executa a opção selecionada no menu ou envia a mensagem no chat."),
    ("Shift + Enter", "Insere uma quebra de linha no prompt sem enviar a mensagem."),
    ("Ctrl + C", "Interrompe imediatamente a geração de resposta da IA em andamento."),
    ("ESC", "Cancela a resposta da IA, retorna à tela anterior ou fecha a janela."),
    ("1 a 6", "Digite o número da opção e pressione Enter para executar rapidamente no Dashboard."),
]),
    ("CONSULTAS, CHAT & BUSCA NA WEB", "🌐", [
    ("01 - Consultar Metis", "Chat inteligente com IA e pesquisa web integrada (chave 🌐 ativável via switch ou /web)."),
    ("03 - Buscar Conhecimento", "Pesquisa web direta sem IA (resultados e links brutos)."),
    ("/web <pergunta>", "Força a busca web em tempo real para responder sua dúvida."),
    ("/opcoes ou /avancado", "Configura ferramentas de terminal (ENABLE_COMMAND_TOOL) e extração web (FETCH_PAGE_CONTENT)."),
    ("/retry ou /repetir", "Rebobina e regenera a última resposta gerada pelo oráculo."),
]),
    ("ORÁCULOS, MODELOS & PROVEDORES", "✨", [
    ("02 - Oráculos & Modelos", "Painel completo de provedores: Ollama (local), Gemini, Groq, NVIDIA, G4F e Servidores Customizados (OpenRouter, DeepSeek, etc.)."),
    ("/modelo [nome]", "Troca rápida de provedor ativo (ex: /modelo gemini, /modelo groq, /modelo ollama) ou abre a lista."),
    ("/apis, /api ou /chaves", "Gerenciador completo de Chaves de API e variáveis de ambiente no arquivo .env."),
]),
    ("ARQUIVOS, ANEXOS & MULTIMODALIDADE", "📎", [
    ("Botão 📎 Anexar", "Abre o explorador para anexar imagens, PDFs ou arquivos de código/texto."),
    ("/arquivo <caminho>", "Carrega e analisa um arquivo, documento ou imagem do seu computador."),
]),
    ("TÁBULA DE MÉTIS (HISTÓRICO & SESSÕES)", "📜", [
    ("04 - Tábula de Métis", "Gerenciamento avançado de sessões, histórico e inspeção/exclusão cirúrgica de turnos."),
    ("05 - Purificar Memória", "Limpa com segurança todas as sessões e históricos armazenados no disco."),
    ("06 - Encerrar Sistema", "Fecha a aplicação com segurança."),
    ("/novo [nome]", "Inicia imediatamente uma nova conversa/tópico limpo sem fechar o app."),
    ("/sessao [nome]", "Lista sessões salvas ou troca/cria diretamente uma sessão pelo nome."),
    ("/exportar", "Exporta a conversa atual para arquivo Markdown (.md) na pasta exports/."),
    ("/limpar ou /clear", "Limpa a conversa da tela e reseta a memória da sessão atual."),
    ("/deletar_sessao", "Apaga a sessão atual gravada no disco e inicia uma nova."),
    ("/deletar_tudo", "Solicita confirmação para apagar todo o histórico de conversas do HD."),
    ("/status", "Abre o painel de telemetria e diagnóstico dos serviços (Ollama, Busca Web, APIs)."),
]),
)


class ModernHelpDialog(QDialog):
    def __init__(self, parent=None):
        """Monta o guia. As 6 secoes vem de `_SECOES_AJUDA`; aqui so orquestra.

        Antes as secoes eram literais dentro do `__init__` e o card era uma
        closure local. Dado em tabela deixa a ordem auditavel e a closure
        impossivel de testar de fora.
        """
        super().__init__(parent)
        self.setWindowTitle("Metis • Guia do Oráculo")
        _constrain_dialog_to_parent(self, 720, 580, parent)
        self.setStyleSheet(build_dynamic_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addLayout(self._build_header(get_current_font_sizes()))

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        root.addWidget(div)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(12)

        for titulo, icone, itens in _SECOES_AJUDA:
            self._add_help_card(c_layout, titulo, icone, itens)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        root.addLayout(self._build_footer())

    def _add_help_card(self, parent_layout: QVBoxLayout,
               title: str, icon: str, items: list):
        card = QFrame()
        card.setProperty("class", "HelpCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        c_head = QLabel(f"{icon}  {title}")
        c_head.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
        c_head.setStyleSheet("color: #f0a85d; background: transparent;")
        card_layout.addWidget(c_head)

        for cmd, desc in items:
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl_c = QLabel(cmd)
            lbl_c.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            lbl_c.setStyleSheet("color: #67e8f9; background-color: #0e1a2c; padding: 4px 8px; border-radius: 4px;")
            row.addWidget(lbl_c)

            lbl_d = QLabel(desc)
            lbl_d.setFont(QFont("Sans Serif", 9))
            lbl_d.setStyleSheet("color: #cbd5e1; background: transparent;")
            lbl_d.setWordWrap(True)
            row.addWidget(lbl_d, 1)

            card_layout.addLayout(row)

        parent_layout.addWidget(card)

    def _build_header(self, f_sz):
        """Icone, titulo e subtitulo do guia."""
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("📖")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("METIS • GUIA DO ORÁCULO")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("Manual de Operações, Comandos Rápidos e Funcionalidades")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        return h_layout

    def _build_footer(self):
        """So o botao de fechar, a direita."""
        f_layout = QHBoxLayout()
        f_layout.addStretch()

        btn_close = QPushButton("Entendido (ESC)")
        btn_close.setProperty("class", "PrimaryBtn")
        btn_close.clicked.connect(self.reject)
        f_layout.addWidget(btn_close)
        return f_layout


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        super().keyPressEvent(event)


# -----------------------------------------------------------------------------
class ModernStatusDialog(QDialog):
    def __init__(self, history_manager, current_service, parent=None):
        """Monta a telemetria: tres cartoes, um por servico.

        As linhas de cada cartao sao dado, entao ficam em `_rows_*`; aqui so
        orquestra. `obter_nome_provedor` vai por parametro para a busca porque
        o nome aparece no titulo E nas linhas, e resolver de novo dentro de
        `_rows_busca` faria uma segunda chamada ao servico.
        """
        super().__init__(parent)
        self.setWindowTitle("Metis • Telemetria do Sistema")
        _constrain_dialog_to_parent(self, 680, 520, parent)
        self.setStyleSheet(build_dynamic_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addLayout(self._build_header(get_current_font_sizes()))

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        root.addWidget(div)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        prov_name = searxng_service.obter_nome_provedor()
        c_layout.addWidget(self._make_status_card(
            "OLLAMA (LOCAL)", "\U0001F3DB\uFE0F", self._rows_ollama()))
        c_layout.addWidget(self._make_status_card(
            f"BUSCA WEB ({prov_name.upper()})", "\U0001F310", self._rows_busca(prov_name)))
        c_layout.addWidget(self._make_status_card(
            "ORÁCULOS & NUVEM", "\u2728", self._rows_apis(current_service, history_manager)))

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        root.addLayout(self._build_footer())

    def _rows_ollama(self):
        """Linhas do cartao do Ollama. O status vem do servico local."""
        ok = ollama_service.verificar_status()
        return [
            ("Status", "Online" if ok else "Offline", "#4ade80" if ok else "#f87171"),
            ("Host", config.OLLAMA_HOST, "#cbd5e1"),
            ("Modelo Ativo", config.OLLAMA_MODEL, "#67e8f9"),
            ("Contexto / Threads", f"{config.OLLAMA_NUM_CTX} tokens / {config.OLLAMA_NUM_THREADS} threads", "#94a3b8"),
        ]

    def _rows_busca(self, prov_name: str):
        """Linhas do cartao da busca web."""
        ok = searxng_service.verificar_status()
        return [
            ("Status", "Online" if ok else "Offline", "#4ade80" if ok else "#f87171"),
            ("Motor Ativo", prov_name, "#cbd5e1"),
            ("Resultados por busca", str(config.MAX_SEARCH_RESULTS), "#67e8f9"),
        ]

    def _rows_apis(self, current_service, history_manager):
        """Linhas do cartao de oraculos: chaves, customizados e a sessao atual."""
        gem_st = "Configurado" if config.GEMINI_API_KEY else "Não configurado"
        groq_st = "Configurado" if config.GROQ_API_KEY else "Não configurado"
        nvidia_st = "Configurado" if getattr(config, "NVIDIA_API_KEY", "") else "Não configurado"

        custom_srvs = obter_servidores_customizados()
        srv_nomes = ", ".join([s["nome"] for s in custom_srvs]) if custom_srvs else "Nenhum"

        return [
            ("Google Gemini", gem_st, "#4ade80" if config.GEMINI_API_KEY else "#64748b"),
            ("Groq Cloud", groq_st, "#4ade80" if config.GROQ_API_KEY else "#64748b"),
            ("NVIDIA NIM", nvidia_st, "#4ade80" if getattr(config, "NVIDIA_API_KEY", "") else "#64748b"),
            ("Servidores Custom", srv_nomes, "#67e8f9"),
            ("Oráculo Ativo Agora", getattr(current_service, "nome_provedor", "Ollama"), "#fad094"),
            ("Sessão Atual", getattr(history_manager, "sessao", "Atual"), "#67e8f9"),
        ]

    def _build_header(self, f_sz):
        """Icone, titulo e subtitulo da telemetria."""
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("\U0001F4CA")
        lbl_icon.setFont(QFont("Sans Serif", f_sz.get("icon", 16)))
        lbl_icon.setStyleSheet("background: transparent;")
        h_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("METIS • TELEMETRIA DOS SERVIÇOS")
        lbl_title.setFont(QFont("Sans Serif", f_sz.get("heading", 13), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #fad094; background: transparent;")
        t_box.addWidget(lbl_title)

        lbl_sub = QLabel("Diagnóstico, Latência e Conectividade de Provedores")
        lbl_sub.setFont(QFont("Sans Serif", f_sz.get("card_sub", 8.5)))
        lbl_sub.setStyleSheet("color: #94a3b8; background: transparent;")
        t_box.addWidget(lbl_sub)

        h_layout.addLayout(t_box)
        h_layout.addStretch()
        return h_layout

    def _build_footer(self):
        """Botao de fechar, a direita. `accept` fecha com o codigo Accepted."""
        f_layout = QHBoxLayout()
        f_layout.addStretch()

        btn_close = QPushButton("Fechar (ESC)")
        btn_close.setProperty("class", "PrimaryBtn")
        btn_close.clicked.connect(self.accept)
        f_layout.addWidget(btn_close)
        return f_layout


    def _make_status_card(self, title: str, icon: str, rows: list):
        card = QFrame()
        card.setProperty("class", "HelpCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(6)

        head = QLabel(f"{icon}  {title}")
        head.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        head.setStyleSheet("color: #f0a85d; background: transparent;")
        l.addWidget(head)

        for k, v, c in rows:
            r = QHBoxLayout()
            lk = QLabel(k)
            lk.setFont(QFont("Sans Serif", 9))
            lk.setStyleSheet("color: #94a3b8; background: transparent;")
            r.addWidget(lk)

            lv = QLabel(v)
            lv.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            lv.setStyleSheet(f"color: {c}; background: transparent;")
            r.addStretch()
            r.addWidget(lv)
            l.addLayout(r)

        return card

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        super().keyPressEvent(event)
