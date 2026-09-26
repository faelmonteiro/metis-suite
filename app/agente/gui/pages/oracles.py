"""Pagina 3, o painel de oraculos, provedores e servidores customizados.

Estado compartilhado com os outros mixins: ver `pages/__init__.py`."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QDialog,
    QMessageBox,
    QGridLayout,
)

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QFont

from typing import (
    Optional,
    List,
)

import os

from agente import config
from agente.gui.dialogs.providers import (
    CustomServerDialog,
    ModernAddModelDialog,
    ModernRemoveModelDialog,
    ModernRestoreServerDialog,
)
from agente.gui.theme_bridge import get_system_theme_colors
from agente.providers_manager import (
    load_config,
    obter_modelos_provedor,
    adicionar_modelo_provedor,
    obter_servidores_customizados,
    obter_servidor_customizado,
    remover_servidor_customizado,
    atualizar_modelo_ativo_servidor,
    salvar_variavel_env,
    obter_preferencia,
    salvar_preferencia,
    obter_servidores_removidos,
    remover_servidor_provedor,
)
from agente.services import ollama_service
from agente.services.custom_openai_service import CustomOpenAIService
from agente.services.g4f_service import G4FService
from agente.services.gemini_service import GeminiService
from agente.services.groq_service import GroqService
from agente.services.nvidia_service import NvidiaService
from agente.services.ollama_service import OllamaService

# Provedor de nuvem -> metodo `activate_*`. Nao guardamos os metodos aqui:
# o binding aconteceria na importacao e a tabela passaria a diter metodos.
_ATIVA_POR_PROVEDOR = {
    "gemini": "activate_gemini",
    "groq": "activate_groq",
    "nvidia": "activate_nvidia",
}

# Os 4 nativos, na ordem da sidebar.
_PROVIDERS_NATIVOS = (
    ("ollama", "🏛️ Ollama Local"),
    ("gemini", "✨ Google Gemini"),
    ("groq", "⚡ Groq Cloud"),
    ("nvidia", "🟢 NVIDIA NIM"),
)

# Os 3 de nuvem, que compartilham o mesmo formato de detalhe. `attr_chave` e o
# atributo lido de `config` para o status; `modelo_cfg`, o comparado com o modelo
# ativo. Os titulos tem espaco duplo antes porque viravam layout.
_PROVIDERS_NUVEM = {
    "gemini": {
        "titulo": "✨  GOOGLE GEMINI",
        "tag": "NUVEM / GOOGLE",
        "descricao": "Modelos do Google de alto desempenho com suporte multimodal a imagens e janela de contexto de 1M+ tokens.",
        "provider_key": "Gemini",
        "servico": "GeminiService",
        "attr_chave": "GEMINI_API_KEY",
        "modelo_cfg": "GEMINI_MODEL",
        "env": "GEMINI_API_KEY",
        "icone": "✨",
    },
    "groq": {
        "titulo": "⚡  GROQ CLOUD",
        "tag": "INFERÊNCIA ULTRA-RÁPIDA",
        "descricao": "Inferência ultra-rápida em hardware customizado LPU com Llama 3.3 70B, Qwen 3.8 e DeepSeek R1 Distill.",
        "provider_key": "Groq",
        "servico": "GroqService",
        "attr_chave": "GROQ_API_KEY",
        "modelo_cfg": "GROQ_MODEL",
        "env": "GROQ_API_KEY",
        "icone": "⚡",
    },
    "nvidia": {
        "titulo": "🟢  NVIDIA NIM API",
        "tag": "GPU MICROSSERVIÇOS",
        "descricao": "Microsserviços de inferência acelerada em GPU NVIDIA (Llama 3.1 70B, Mistral Large 2, Vision multimodal).",
        "provider_key": "NVIDIA",
        "servico": "NvidiaService",
        "attr_chave": "NVIDIA_API_KEY",
        "modelo_cfg": "NVIDIA_MODEL",
        "env": "NVIDIA_API_KEY",
        "icone": "🟢",
    },
}

class OraclesMixin:
    """Painel de oraculos: provedores, modelos e servidores customizados.

    Escolha do provedor ativo, listagem e grade de modelos, edicao de servidores
    customizados, remocao/restauracao, e os dialogos de adicionar/remover
    modelo. E o dominio que mais cresce: cada provedor novo entra aqui.

    Os metodos sao os mesmos de `MetisMainWindow` de antes: a divisao em
    mixins nao moveu nenhum corpo, so mudou onde cada um mora.
    """

    def setup_oracles_ui(self, parent: QWidget):
        """Monta a pagina. So orquestra; cada painel tem seu builder.

        A ordem das chamadas NAO e cosmetics: `tests/gui_impressao_digital.txt`
        fixa a ordem de criacao dos objetos, e quem define a geometria final e
        a ordem de insercao no layout, nao a ordem do codigo.
        """
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addLayout(self._build_oracles_header())

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #162234;")
        layout.addWidget(div)

        # Master-Detail Layout sem scroll vertical
        body_split = QHBoxLayout()
        body_split.setSpacing(12)
        body_split.addWidget(self._build_provider_sidebar())
        body_split.addWidget(self._build_provider_detail(), 1)
        layout.addLayout(body_split, 1)

        self.selected_provider_tab = "ollama"

    def _build_oracles_header(self):
        """Voltar, titulo, o badge do provider ativo e os atalhos."""
        header = QHBoxLayout()
        header.setSpacing(10)

        btn_back = QPushButton("← Voltar")
        btn_back.setProperty("class", "SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_back)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_t = QLabel("CONFIGURAÇÃO DE ORÁCULOS")
        lbl_t.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: #fad094;")
        t_box.addWidget(lbl_t)

        lbl_s = QLabel("Selecione um provedor na barra lateral para ver seus modelos e gerenciar chaves")
        lbl_s.setFont(QFont("Sans Serif", 8))
        lbl_s.setStyleSheet("color: #94a3b8;")
        t_box.addWidget(lbl_s)
        header.addLayout(t_box)

        header.addStretch()

        icone, prov_tipo, modelo_nome = self.get_active_oracle_info()
        self.lbl_oracle_badge = QLabel(f"{icone} Ativo: {prov_tipo} ({modelo_nome})")
        self.lbl_oracle_badge.setObjectName("OracleActiveBadge")
        self.lbl_oracle_badge.setProperty("class", "OracleActiveBadge")
        header.addWidget(self.lbl_oracle_badge)

        self.btn_oracle_settings = QPushButton("⚙️ Opções ▾")
        self.btn_oracle_settings.setProperty("class", "SecondaryBtn")
        self.btn_oracle_settings.setToolTip("Cadastrar novo servidor, gerenciar chaves de API e diagnóstico")
        self.btn_oracle_settings.clicked.connect(self.show_oracle_settings_menu)
        header.addWidget(self.btn_oracle_settings)

        btn_go_chat = QPushButton("💬 Chat ↵")
        btn_go_chat.setProperty("class", "PrimaryBtn")
        btn_go_chat.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        header.addWidget(btn_go_chat)

        return header

    def _build_provider_sidebar(self):
        """Painel lateral esquerdo: a lista de providers.

        `sidebar_content_widget` e `detail_content_widget` nascem None porque
        quem os cria depois e `rebuild_oracle_buttons` /
        `_render_provider_detail`, em tempo de execucao. O `addStretch` entre o
        cabecalho e o botao empurra a lista para o topo e o botao para baixo.
        """
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("ProviderSidebar")
        self.sidebar_frame.setFixedWidth(230)
        self.sidebar_vbox = QVBoxLayout(self.sidebar_frame)
        self.sidebar_vbox.setContentsMargins(10, 10, 10, 10)
        self.sidebar_vbox.setSpacing(6)

        lbl_side_title = QLabel("PROVEDORES DE IA")
        lbl_side_title.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        lbl_side_title.setStyleSheet("color: #f0a85d; padding: 2px 4px;")
        self.sidebar_vbox.addWidget(lbl_side_title)

        self.sidebar_content_widget = None
        self.detail_content_widget = None

        self.sidebar_vbox.addStretch()

        btn_new_srv = QPushButton("➕ Novo Servidor API")
        btn_new_srv.setProperty("class", "SecondaryBtn")
        btn_new_srv.clicked.connect(self.show_add_server_dialog)
        self.sidebar_vbox.addWidget(btn_new_srv)

        return self.sidebar_frame

    def _build_provider_detail(self):
        """Painel direito: o container vazio onde os detalhes sao injetados.

        Fica em metodo proprio (e nao embutido no orquestrador) para manter o
        par `sidebar_frame` / `detail_container` legivel: os dois nascem
        vazios aqui e sao preenchidos em tempo de execucao.
        """
        self.detail_container = QFrame()
        self.detail_container.setProperty("class", "ProviderCard")
        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(18, 14, 18, 14)
        self.detail_layout.setSpacing(10)
        return self.detail_container

    def get_active_provider_key(self) -> str:
        """Retorna a chave do provedor correspondente ao oráculo atualmente ativo."""
        if isinstance(self.current_service, GeminiService):
            return "gemini"
        elif isinstance(self.current_service, GroqService):
            return "groq"
        elif isinstance(self.current_service, NvidiaService):
            return "nvidia"
        elif isinstance(self.current_service, G4FService):
            return "g4f"
        elif isinstance(self.current_service, CustomOpenAIService):
            srv_id = getattr(self.current_service, "server_info", {}).get("id", "")
            return f"custom_{srv_id}" if srv_id else "custom"
        else:
            return "ollama"

    def select_provider_tab(self, prov_key: str):
        """Alterna o provedor selecionado na sidebar e renderiza seus modelos."""
        self.selected_provider_tab = prov_key
        self.rebuild_oracle_buttons()

    def open_oracles_page(self):
        self.selected_provider_tab = self.get_active_provider_key()
        self.rebuild_oracle_buttons()
        self.refresh_telemetry()
        self.stack.setCurrentIndex(3)
        self.focus_active_oracle_btn()

    def rebuild_oracle_buttons(self):
        """Recria sidebar e painel de detalhes do provedor selecionado.

        Orquestra: `_reset_oracle_panels` limpa os dois containers,
        `_build_sidebar_buttons` monta a lista de provedores, e
        `_render_selected_provider` pinta o detalhe.
        """
        self.oracle_buttons = []
        self._reset_oracle_panels()
        self._build_sidebar_buttons()
        self._render_selected_provider()

    def _reset_oracle_panels(self):
        """Joga fora os dois containers e cria os vazios no lugar.

        `deleteLater` nao destroi agora: os widgets antigos ficam vivos ate o
        event loop, entao sao recriados em containers novos em vez de
        esvaziados - esvaziar reaproveitaria o objeto e a ordem de `addWidget`.
        """
        if getattr(self, "sidebar_content_widget", None) is not None:
            self.sidebar_content_widget.deleteLater()
        self.sidebar_content_widget = None

        self.sidebar_content_widget = QWidget()
        self.sidebar_content_layout = QVBoxLayout(self.sidebar_content_widget)
        self.sidebar_content_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_content_layout.setSpacing(6)
        self.sidebar_vbox.insertWidget(1, self.sidebar_content_widget)

        if getattr(self, "detail_content_widget", None) is not None:
            self.detail_content_widget.deleteLater()
        self.detail_content_widget = None

        self.detail_content_widget = QWidget(self.detail_container)
        self.detail_content_layout = QVBoxLayout(self.detail_content_widget)
        self.detail_content_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_content_layout.setSpacing(10)
        self.detail_layout.addWidget(self.detail_content_widget)

    def _provider_list(self):
        """Os provedores a listar, na ordem: nativos, customizados, g4f.

        Um nativo so entra se constar de `builtin_models` no config E nao
        estiver na lista de removidos. A ordem e fixa porque a posicao na
        sidebar e a ordem daqui.
        """
        cfg_builtin = load_config().get("builtin_models", {})
        builtin_keys_lower = [k.lower() for k in cfg_builtin.keys()]
        removed_servers = obter_servidores_removidos()

        lista = [
            p for p in _PROVIDERS_NATIVOS
            if p[0].lower() in builtin_keys_lower and p[0].lower() not in removed_servers
        ]

        for srv in obter_servidores_customizados():
            s_id = srv.get("id", "custom")
            lista.append((f"custom_{s_id}", f"🌐 {srv.get('nome', 'Custom')}"))

        if "g4f" in builtin_keys_lower and "g4f" not in removed_servers:
            lista.append(("g4f", "🌍 IA Web (G4F)"))
        return lista

    def _build_sidebar_buttons(self):
        """Um botao por provedor, na ordem de `_provider_list`."""
        providers_list = self._provider_list()

        # Aba selecionada removida do config? Cai para a primeira que sobrou.
        available_keys = [p[0] for p in providers_list]
        if self.selected_provider_tab not in available_keys:
            self.selected_provider_tab = available_keys[0] if available_keys else "ollama"

        for p_key, p_label in providers_list:
            is_selected = (self.selected_provider_tab == p_key)
            btn_prov = QPushButton(p_label)
            btn_prov.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_prov.setProperty("class", "ProviderSidebarBtnActive" if is_selected else "ProviderSidebarBtn")
            btn_prov.setFixedHeight(40)
            # `k=p_key` amarra o valor agora: sem isso os 4 lambdas fechariam
            # sobre a mesma variavel de laco e todos responderiam pelo ultimo.
            btn_prov.clicked.connect(lambda _, k=p_key: self.select_provider_tab(k))
            self.sidebar_content_layout.addWidget(btn_prov)

    def _render_selected_provider(self):
        """Pinta o painel direito conforme `selected_provider_tab`."""
        sel = self.selected_provider_tab

        if sel == "ollama":
            self._render_provider_detail(
                **self._detalhe_ollama(),
                activate_callback=self.activate_ollama,
            )
        elif sel in _PROVIDERS_NUVEM:
            self._render_provider_detail(
                **self._detalhe_nuvem(sel),
                activate_callback=getattr(self, _ATIVA_POR_PROVEDOR[sel]),
            )
        elif sel == "g4f":
            self._render_provider_detail(
                **self._detalhe_g4f(),
                activate_callback=self.activate_g4f,
            )
        elif sel.startswith("custom_"):
            target_id = sel.split("custom_", 1)[1]
            srv = obter_servidor_customizado(target_id)
            if srv:
                self._render_custom_server_detail(srv)
            else:
                self.selected_provider_tab = "ollama"
                self.rebuild_oracle_buttons()

    def _detalhe_ollama(self):
        """Detalhe do Ollama. Unico que lista do servico local."""
        return {
            "titulo": "🏛️  OLLAMA LOCAL",
            "category_tag": "LOCAL / OFFLINE",
            "status_text": "● Offline & Privado",
            "status_type": "active",
            "descricao": "Executa modelos open-source diretamente na sua máquina local com total privacidade e sem limites de requisições.",
            "provider_key": "Ollama",
            "modelos": ollama_service.listar_modelos() or [getattr(config, "OLLAMA_MODEL", "llama3.2:3b")],
            "is_active_callback": lambda mod: (isinstance(self.current_service, OllamaService) and config.OLLAMA_MODEL == mod),
            "icon": "🏛️",
        }

    def _detalhe_nuvem(self, sel):
        """Detalhe dos provedores de nuvem: so muda rotulo, chave e servico.

        O status ("Chave Configurada" vs "Requer <ENV>") e derivado da config,
        entao fica aqui em vez de na tabela.
        """
        meta = _PROVIDERS_NUVEM[sel]
        tem_chave = bool(getattr(config, meta["attr_chave"], ""))
        servico = meta["servico"]
        modelo_cfg = meta["modelo_cfg"]
        return {
            "titulo": meta["titulo"],
            "category_tag": meta["tag"],
            "status_text": ("● Chave Configurada" if tem_chave
                            else "○ Requer " + meta["env"]),
            "status_type": "active" if tem_chave else "warning",
            "descricao": meta["descricao"],
            "provider_key": meta["provider_key"],
            "modelos": obter_modelos_provedor(meta["provider_key"]),
            "is_active_callback": lambda mod: (
                type(self.current_service).__name__ == servico
                and getattr(config, modelo_cfg, "") == mod
            ),
            "icon": meta["icone"],
        }

    def _detalhe_g4f(self):
        """Detalhe do G4F: sem chave, e o modelo mora no servico, nao na config."""
        return {
            "titulo": "🌍  IA WEB GRATUITA (G4F)",
            "category_tag": "COMUNITÁRIO / FREE",
            "status_text": "● Gratuito & Sem Chave",
            "status_type": "active",
            "descricao": "Provedor comunitário para consultas diretas em múltiplos modelos na nuvem sem necessidade de chaves pagas.",
            "provider_key": "G4F",
            "modelos": obter_modelos_provedor("G4F"),
            "is_active_callback": lambda mod: (type(self.current_service).__name__ == "G4FService" and getattr(self.current_service, "model", "") == mod),
            "icon": "🌍",
        }


    def _render_provider_detail(self, titulo: str, category_tag: str, status_text: str, status_type: str, descricao: str, provider_key: str, modelos: List[str], activate_callback, is_active_callback, icon: str):
        l = self.detail_content_layout

        # Header do Card
        c = get_system_theme_colors()
        h_row = QHBoxLayout()
        lbl_t = QLabel(titulo)
        lbl_t.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {c['accent_gold']}; background: transparent;")
        h_row.addWidget(lbl_t)

        lbl_cat = QLabel(category_tag)
        lbl_cat.setProperty("class", "ProviderTag")
        h_row.addWidget(lbl_cat)

        lbl_st = QLabel(status_text)
        if status_type == "active":
            lbl_st.setProperty("class", "StatusPillActive")
        elif status_type == "warning":
            lbl_st.setProperty("class", "StatusPillWarning")
        else:
            lbl_st.setProperty("class", "StatusPillInactive")
        h_row.addWidget(lbl_st)

        h_row.addStretch()

        if provider_key in ["Gemini", "Groq", "NVIDIA", "Ollama", "G4F"]:
            btn_gear = QPushButton("⚙️")
            btn_gear.setProperty("class", "ActionChip")
            btn_gear.setToolTip("Configurações do Provedor (Adicionar, Gerenciar/Excluir Modelos)")
            btn_gear.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_gear.clicked.connect(lambda _, b=btn_gear, p=provider_key: self.show_provider_options_menu(b, p))
            h_row.addWidget(btn_gear)

        l.addLayout(h_row)

        lbl_desc = QLabel(descricao)
        lbl_desc.setFont(QFont("Sans Serif", 9))
        lbl_desc.setStyleSheet(f"color: {c['fg_sub']}; background: transparent;")
        lbl_desc.setWordWrap(True)
        l.addWidget(lbl_desc)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c['border']};")
        l.addWidget(div)

        lbl_sec = QLabel(f"🤖 MODELOS SALVOS NESTE PERFIL ({len(modelos)}):")
        lbl_sec.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec.setStyleSheet(f"color: {c['accent_cyan']}; margin-top: 2px; background: transparent;")
        l.addWidget(lbl_sec)

        self._populate_models_grid(
            l, modelos,
            activate_callback=activate_callback,
            is_active_callback=is_active_callback,
            icon=icon,
            cols=2
        )

    def _render_custom_server_detail(self, srv: dict):
        srv_id = srv.get("id")
        l = self.detail_content_layout
        c = get_system_theme_colors()

        h_row = QHBoxLayout()
        lbl_t = QLabel(f"🌐  SERVIDOR: {srv.get('nome', 'Custom API').upper()}")
        lbl_t.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {c['accent_gold']}; background: transparent;")
        h_row.addWidget(lbl_t)

        lbl_cat = QLabel("OPENAI COMPATÍVEL")
        lbl_cat.setProperty("class", "ProviderTag")
        h_row.addWidget(lbl_cat)

        api_key_env = srv.get("api_key_env", f"{srv_id.upper()}_API_KEY")
        has_key = bool(os.getenv(api_key_env, "").strip() or srv.get("api_key", "").strip())
        lbl_st = QLabel("● Conexão Ativa" if has_key else "○ Sem Chave (ou Local)")
        lbl_st.setProperty("class", "StatusPillActive" if has_key else "StatusPillInactive")
        h_row.addWidget(lbl_st)
        h_row.addStretch()

        btn_gear = QPushButton("⚙️")
        btn_gear.setProperty("class", "ActionChip")
        btn_gear.setToolTip("Configurações do Servidor (Adicionar, Gerenciar Modelos, Editar, Excluir)")
        btn_gear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gear.clicked.connect(lambda _, b=btn_gear, s=srv: self.show_custom_server_options_menu(b, s))
        h_row.addWidget(btn_gear)

        l.addLayout(h_row)

        lbl_desc = QLabel(f"Endpoint: {srv.get('base_url')}  •  Variável de Chave: {api_key_env}")
        lbl_desc.setFont(QFont("Monospace", 8))
        lbl_desc.setStyleSheet(f"color: {c['fg_sub']}; background: transparent;")
        l.addWidget(lbl_desc)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {c['border']};")
        l.addWidget(div)

        modelos = srv.get("modelos", [])
        if not modelos and srv.get("modelo_atual"):
            modelos = [srv.get("modelo_atual")]

        lbl_sec = QLabel(f"🤖 MODELOS CADASTRADOS ({len(modelos)}):")
        lbl_sec.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        lbl_sec.setStyleSheet(f"color: {c['accent_cyan']}; margin-top: 2px; background: transparent;")
        l.addWidget(lbl_sec)

        self._populate_models_grid(
            l, modelos,
            activate_callback=lambda mod, s=srv: self.activate_custom_server(s, mod),
            is_active_callback=lambda mod, sid=srv_id: (
                getattr(self.current_service, "__class__", None).__name__ == "CustomOpenAIService"
                and getattr(self.current_service, "server_info", {}).get("id") == sid
                and getattr(self.current_service, "modelo", "") == mod
            ),
            icon="🔗",
            cols=2
        )

    def _populate_models_grid(self, parent_layout: QVBoxLayout, modelos: List[str], activate_callback, is_active_callback, icon: str = "🤖", cols: int = 2):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(scroll_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 4, 0, 4)

        for idx, m in enumerate(modelos):
            is_active = is_active_callback(m)
            
            # Formatação inteligente de badges e ícones por tipo de modelo
            m_lower = m.lower()
            if is_active:
                display_label = f"✓  {m}  ★ (Ativo)"
            elif ":free" in m_lower or "/free" in m_lower:
                display_label = f"🆓  {m}"
            elif "vision" in m_lower:
                display_label = f"👁️  {m}"
            elif "coder" in m_lower or "code" in m_lower:
                display_label = f"💻  {m}"
            elif "deepseek-r1" in m_lower or "r1" in m_lower or "reasoning" in m_lower:
                display_label = f"🧠  {m}"
            else:
                display_label = f"{icon}  {m}"

            btn = QPushButton(display_label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Modelo: {m}\nClique para selecionar e ativar")
            btn.setProperty("class", "ModelBtnActive" if is_active else "ModelBtn")
            btn.setFixedHeight(42)
            btn.clicked.connect(lambda _, mod=m: activate_callback(mod))

            row = idx // cols
            col = idx % cols
            grid.addWidget(btn, row, col)
            self.oracle_buttons.append(btn)

        num_rows = (len(modelos) + cols - 1) // cols
        grid.setRowStretch(num_rows, 1)

        scroll.setWidget(scroll_widget)
        parent_layout.addWidget(scroll, 1)

    def prompt_edit_custom_server(self, server_to_edit: dict):
        """Abre o diálogo para editar um servidor customizado existente."""
        dlg = CustomServerDialog(self, server_to_edit=server_to_edit)
        dlg.server_saved.connect(self.rebuild_oracle_buttons)
        dlg.exec()

    def focus_active_oracle_btn(self):
        if not self.oracle_buttons:
            return
        target_idx = 0
        for i, btn in enumerate(self.oracle_buttons):
            if btn.property("class") == "ModelBtnActive":
                target_idx = i
                break
        self.select_oracle_btn(target_idx)

    def select_oracle_btn(self, index: int):
        if not self.oracle_buttons:
            return
        self.selected_oracle_index = max(0, min(index, len(self.oracle_buttons) - 1))
        btn = self.oracle_buttons[self.selected_oracle_index]
        btn.setFocus()

    def navigate_oracles(self, delta: int):
        if not self.oracle_buttons:
            return
        new_idx = (self.selected_oracle_index + delta) % len(self.oracle_buttons)
        self.select_oracle_btn(new_idx)

    def get_active_oracle_info(self) -> tuple[str, str, str]:
        """Retorna (icone, nome_provedor, nome_modelo) do oráculo ativo no momento."""
        if isinstance(self.current_service, GeminiService):
            return "✨", "Gemini", getattr(config, "GEMINI_MODEL", "gemini-2.0-flash")
        elif isinstance(self.current_service, GroqService):
            return "⚡", "Groq", config.GROQ_MODEL
        elif isinstance(self.current_service, NvidiaService):
            return "🟢", "NVIDIA", getattr(config, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
        elif isinstance(self.current_service, G4FService):
            return "🌍", "G4F", getattr(self.current_service, "model", getattr(config, "G4F_MODEL", "gpt-4o-mini"))
        elif isinstance(self.current_service, CustomOpenAIService):
            nome_srv = getattr(self.current_service, "nome", "Custom API")
            modelo = getattr(self.current_service, "modelo", "default")
            return "🌐", nome_srv, modelo
        else:
            return "🧠", "Ollama", getattr(config, "OLLAMA_MODEL", "qwen2.5:latest")

    def carregar_servico_padrao(self):
        saved_prov = obter_preferencia("last_active_provider")
        saved_model = obter_preferencia("last_active_model")

        prov = saved_prov or getattr(config, "DEFAULT_PROVIDER", "ollama") or "ollama"
        prov = prov.strip().lower()

        if prov == "gemini" and config.GEMINI_API_KEY:
            if saved_model:
                config.GEMINI_MODEL = saved_model
            return GeminiService()
        elif prov == "groq" and config.GROQ_API_KEY:
            if saved_model:
                config.GROQ_MODEL = saved_model
            return GroqService()
        elif prov == "nvidia" and getattr(config, "NVIDIA_API_KEY", ""):
            if saved_model:
                config.NVIDIA_MODEL = saved_model
            return NvidiaService()
        elif prov == "g4f":
            m = saved_model or getattr(config, "G4F_MODEL", "gpt-4o-mini")
            config.G4F_MODEL = m
            return G4FService(model=m)
        elif prov.startswith("custom:"):
            srv_id = prov.split(":", 1)[1]
            srv = obter_servidor_customizado(srv_id)
            if srv:
                if saved_model:
                    srv["modelo_atual"] = saved_model
                return CustomOpenAIService(srv)
        elif prov == "ollama":
            if saved_model:
                config.OLLAMA_MODEL = saved_model
            return OllamaService()

        return OllamaService()

    def activate_ollama(self, model_name: str = ""):
        if not model_name:
            model_name = getattr(config, "OLLAMA_MODEL", "llama3.2:3b")
        config.OLLAMA_MODEL = model_name
        config.DEFAULT_PROVIDER = "ollama"
        salvar_variavel_env("OLLAMA_MODEL", model_name)
        salvar_variavel_env("DEFAULT_PROVIDER", "ollama")
        salvar_preferencia("last_active_provider", "ollama")
        salvar_preferencia("last_active_model", model_name)
        self.current_service = OllamaService()
        self.lbl_oracle_badge.setText(f"🧠 Ativo: Ollama ({model_name})")
        self.rebuild_oracle_buttons()
        self.refresh_telemetry()

    def activate_gemini(self, model_name: str = "gemini-2.0-flash"):
        if not config.GEMINI_API_KEY:
            res = QMessageBox.question(
                self,
                "Gemini API Key",
                "A chave GEMINI_API_KEY não está configurada no seu .env.\nDeseja configurá-la agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.show_apis_dialog()
                if not config.GEMINI_API_KEY:
                    return
            else:
                return

        try:
            config.GEMINI_MODEL = model_name
            config.DEFAULT_PROVIDER = "gemini"
            salvar_variavel_env("GEMINI_MODEL", model_name)
            salvar_variavel_env("DEFAULT_PROVIDER", "gemini")
            salvar_preferencia("last_active_provider", "gemini")
            salvar_preferencia("last_active_model", model_name)
            self.current_service = GeminiService()
            self.lbl_oracle_badge.setText(f"✨ Ativo: Gemini ({model_name})")
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
        except Exception as e:
            QMessageBox.warning(self, "Gemini", f"Erro ao ativar Gemini: {e}")

    def activate_groq(self, model_name: str = None):
        # Sem argumento, mantém o default do config (não sobrescreve GROQ_MODEL).
        model_name = (model_name or "").strip() or config.GROQ_MODEL
        if not config.GROQ_API_KEY:
            res = QMessageBox.question(
                self,
                "Groq API Key",
                "A chave GROQ_API_KEY não está configurada no seu .env.\nDeseja configurá-la agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.show_apis_dialog()
                if not config.GROQ_API_KEY:
                    return
            else:
                return

        try:
            config.GROQ_MODEL = model_name
            config.DEFAULT_PROVIDER = "groq"
            salvar_variavel_env("GROQ_MODEL", model_name)
            salvar_variavel_env("DEFAULT_PROVIDER", "groq")
            salvar_preferencia("last_active_provider", "groq")
            salvar_preferencia("last_active_model", model_name)
            self.current_service = GroqService()
            self.lbl_oracle_badge.setText(f"⚡ Ativo: Groq ({model_name})")
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
        except Exception as e:
            QMessageBox.warning(self, "Groq", f"Erro ao ativar Groq: {e}")

    def activate_nvidia(self, model_name: str = "meta/llama-3.1-70b-instruct"):
        if not getattr(config, "NVIDIA_API_KEY", ""):
            res = QMessageBox.question(
                self,
                "NVIDIA API Key",
                "A chave NVIDIA_API_KEY não está configurada no seu .env.\nDeseja configurá-la agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.show_apis_dialog()
                if not getattr(config, "NVIDIA_API_KEY", ""):
                    return
            else:
                return

        try:
            config.NVIDIA_MODEL = model_name
            config.DEFAULT_PROVIDER = "nvidia"
            salvar_variavel_env("NVIDIA_MODEL", model_name)
            salvar_variavel_env("DEFAULT_PROVIDER", "nvidia")
            salvar_preferencia("last_active_provider", "nvidia")
            salvar_preferencia("last_active_model", model_name)
            self.current_service = NvidiaService()
            self.lbl_oracle_badge.setText(f"🟢 Ativo: NVIDIA ({model_name})")
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
        except Exception as e:
            QMessageBox.warning(self, "NVIDIA", f"Erro ao ativar NVIDIA: {e}")

    def activate_g4f(self, model_name: str = "gpt-4o-mini"):
        try:
            config.G4F_MODEL = model_name
            config.DEFAULT_PROVIDER = "g4f"
            salvar_variavel_env("G4F_MODEL", model_name)
            salvar_variavel_env("DEFAULT_PROVIDER", "g4f")
            salvar_preferencia("last_active_provider", "g4f")
            salvar_preferencia("last_active_model", model_name)
            self.current_service = G4FService(model=model_name)
            self.lbl_oracle_badge.setText(f"🌍 Ativo: G4F ({model_name})")
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
        except Exception as e:
            QMessageBox.warning(self, "G4F", f"Erro ao ativar G4F: {e}")

    def activate_custom_server(self, server_info: dict, model_name: str):
        srv_copy = dict(server_info)
        srv_copy["modelo_atual"] = model_name
        atualizar_modelo_ativo_servidor(server_info["id"], model_name)
        config.DEFAULT_PROVIDER = f"custom:{server_info['id']}"
        salvar_variavel_env("DEFAULT_PROVIDER", f"custom:{server_info['id']}")
        salvar_preferencia("last_active_provider", f"custom:{server_info['id']}")
        salvar_preferencia("last_active_model", model_name)

        try:
            self.current_service = CustomOpenAIService(srv_copy)
            self.lbl_oracle_badge.setText(f"🌐 Ativo: {server_info.get('nome')} ({model_name})")
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
        except Exception as e:
            QMessageBox.warning(self, "Servidor Customizado", f"Erro ao conectar ao servidor: {e}")

    def prompt_add_model(self, provider_key: str, server_id: Optional[str] = None):
        dlg = ModernAddModelDialog(provider_name=provider_key, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_model_name:
            adicionar_modelo_provedor(provider_key, dlg.result_model_name, server_id=server_id)
            self.rebuild_oracle_buttons()

    def prompt_remove_model(self, provider_key: str, server_id: Optional[str] = None):
        active_model = ""
        if provider_key == "Gemini":
            active_model = config.GEMINI_MODEL
        elif provider_key == "Groq":
            active_model = config.GROQ_MODEL
        elif provider_key == "NVIDIA":
            active_model = getattr(config, "NVIDIA_MODEL", "")
        elif provider_key == "G4F":
            active_model = getattr(self.current_service, "model", "")
        elif server_id:
            srv = obter_servidor_customizado(server_id)
            active_model = srv.get("modelo_atual", "") if srv else ""

        dlg = ModernRemoveModelDialog(
            provider_name=provider_key,
            server_id=server_id,
            current_active_model=active_model,
            parent=self
        )
        dlg.models_updated.connect(self.rebuild_oracle_buttons)
        dlg.exec()

    def show_add_server_dialog(self):
        dlg = CustomServerDialog(self)
        dlg.server_saved.connect(self.rebuild_oracle_buttons)
        dlg.exec()

    def delete_custom_server(self, server_id: str):
        srv = obter_servidor_customizado(server_id)
        nome = srv.get("nome", server_id) if srv else server_id
        res = QMessageBox.warning(
            self,
            "Excluir Servidor Definitivamente",
            f"Deseja realmente excluir permanentemente o servidor '{nome}' dos arquivos de configuração?\n\n"
            "Ele será apagado definitivamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            remover_servidor_customizado(server_id)
            self.ensure_active_provider_valid()
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
            QMessageBox.information(
                self,
                "Servidor Excluído",
                f"O servidor '{nome}' foi excluído permanentemente dos arquivos de configuração."
            )

    def delete_builtin_server(self, provider_key: str):
        removed = obter_servidores_removidos()
        all_builtin = ["ollama", "gemini", "groq", "nvidia", "g4f"]
        custom_s = obter_servidores_customizados()
        remaining_count = sum(1 for p in all_builtin if p not in removed) + len(custom_s)
        if remaining_count <= 1:
            QMessageBox.warning(
                self,
                "Aviso",
                "Não é possível excluir o único servidor restante. Mantenha ao menos um servidor ativo."
            )
            return

        res = QMessageBox.warning(
            self,
            "Excluir Servidor Definitivamente",
            f"Deseja realmente excluir permanentemente o servidor '{provider_key}' dos arquivos de configuração?\n\n"
            "Ele será apagado definitivamente e não ficará oculto para restaurar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            remover_servidor_provedor(provider_key)
            self.ensure_active_provider_valid()
            self.rebuild_oracle_buttons()
            self.refresh_telemetry()
            QMessageBox.information(
                self,
                "Servidor Excluído",
                f"O servidor '{provider_key}' foi excluído permanentemente dos arquivos de configuração."
            )

    def show_restore_server_dialog(self):
        dlg = ModernRestoreServerDialog(self)
        dlg.server_restored.connect(self.on_server_restored)
        dlg.exec()

    def on_server_restored(self):
        self.rebuild_oracle_buttons()
        self.refresh_telemetry()

    def ensure_active_provider_valid(self):
        removed = obter_servidores_removidos()
        curr_prov = getattr(config, "DEFAULT_PROVIDER", "ollama").lower()
        prov_clean = curr_prov.replace("custom:", "")
        if prov_clean in removed or curr_prov in removed:
            if "ollama" not in removed:
                self.activate_ollama()
            elif "gemini" not in removed and config.GEMINI_API_KEY:
                self.activate_gemini()
            elif "groq" not in removed and config.GROQ_API_KEY:
                self.activate_groq()
            elif "nvidia" not in removed and getattr(config, "NVIDIA_API_KEY", ""):
                self.activate_nvidia()
            elif "g4f" not in removed:
                self.activate_g4f()
            else:
                for srv in obter_servidores_customizados():
                    if srv.get("id", "").lower() not in removed:
                        mod = srv.get("modelo_atual") or (srv.get("modelos") or ["default"])[0]
                        self.activate_custom_server(srv, mod)
                        break
