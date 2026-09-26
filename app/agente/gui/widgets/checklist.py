"""Card de checklist: mostra o plano e as ferramentas do agente em tempo real."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from PyQt6.QtGui import QFont

# -----------------------------------------------------------------------------
class AgentChecklistWidget(QFrame):
    """
    Card dinâmico de Checklist e Execução de Tarefas do Agente em tempo real.
    Mostra o plano de ação, ferramentas acionadas, progresso e detalhes recolhíveis.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgentChecklistCard")
        self.setStyleSheet("""
            QFrame#AgentChecklistCard {
                background-color: #0b1320;
                border: 1px solid #1e293b;
                border-left: 3px solid #f0a85d;
                border-radius: 8px;
                margin: 4px 0px 8px 0px;
                padding: 6px 10px;
            }
        """)

        self.items_data = []
        self.is_collapsed = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(6)

        # Header
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)

        self.lbl_header_title = QLabel("🤖  PLANO & AÇÕES DO AGENTE")
        self.lbl_header_title.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        self.lbl_header_title.setStyleSheet("color: #fad094; background: transparent;")
        self.header_layout.addWidget(self.lbl_header_title)

        self.lbl_badge = QLabel("0 passos")
        self.lbl_badge.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        self.lbl_badge.setStyleSheet("color: #94a3b8; background: #162234; border-radius: 4px; padding: 2px 6px;")
        self.header_layout.addWidget(self.lbl_badge)

        self.header_layout.addStretch()

        self.btn_toggle = QPushButton("▾ Ocultar")
        self.btn_toggle.setProperty("class", "ActionChip")
        self.btn_toggle.setFixedWidth(70)
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        self.header_layout.addWidget(self.btn_toggle)

        self.main_layout.addLayout(self.header_layout)

        # Container dos Itens
        self.items_container = QWidget()
        self.items_container.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(2, 2, 2, 2)
        self.items_layout.setSpacing(4)
        self.main_layout.addWidget(self.items_container)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.items_container.setVisible(not self.is_collapsed)
        self.btn_toggle.setText("▸ Detalhes" if self.is_collapsed else "▾ Ocultar")

    def _friendly_tool_info(self, name: str, args: dict) -> tuple[str, str]:
        """Retorna (titulo_formatado, detalhe_amigavel) para a ferramenta."""
        if name == "buscar_web":
            q = str(args.get("query", "")).strip()
            return "🌐 Pesquisa Web", f"Buscar: \"{q[:45]}\""
        elif name == "executar_comando":
            cmd = str(args.get("comando", "")).strip()
            return "⚡ Executar no Terminal", f"$ {cmd[:50]}"
        elif name == "ler_arquivo":
            c = str(args.get("caminho", "")).strip()
            return "📄 Ler Arquivo", f"Arquivo: {c}"
        elif name == "listar_diretorio":
            c = str(args.get("caminho", ".")).strip()
            return "📁 Listar Diretório", f"Pasta: {c}"
        elif name == "escrever_arquivo":
            c = str(args.get("caminho", "")).strip()
            return "✍️ Criar Arquivo", f"Gravar em: {c}"
        elif name == "editar_arquivo":
            c = str(args.get("caminho", "")).strip()
            return "📝 Editar Arquivo", f"Diff em: {c}"
        elif name == "gerar_pdf":
            c = str(args.get("caminho_destino", "")).strip()
            return "📑 Gerar PDF", f"Destino: {c}"
        return f"🛠️ {name}", str(args)[:45]

    def add_or_update_started(self, data: dict):
        name = data.get("name", "")
        args = data.get("args", {})
        title, detail = self._friendly_tool_info(name, args)

        row = QFrame()
        row.setStyleSheet("background: #0f1a2a; border-radius: 6px; padding: 4px 6px;")
        r_layout = QVBoxLayout(row)
        r_layout.setContentsMargins(6, 4, 6, 4)
        r_layout.setSpacing(2)

        top_h = QHBoxLayout()
        lbl_status = QLabel("⏳")
        lbl_status.setFont(QFont("Sans Serif", 9))
        top_h.addWidget(lbl_status)

        lbl_desc = QLabel(f"<b>{title}</b> — <span style='color: #94a3b8;'>{detail}</span>")
        lbl_desc.setFont(QFont("Sans Serif", 9))
        lbl_desc.setStyleSheet("color: #e2e8f0; background: transparent;")
        top_h.addWidget(lbl_desc, 1)

        lbl_time = QLabel("executando...")
        lbl_time.setFont(QFont("Sans Serif", 8))
        lbl_time.setStyleSheet("color: #67e8f9; background: transparent; font-style: italic;")
        top_h.addWidget(lbl_time)
        r_layout.addLayout(top_h)

        self.items_layout.addWidget(row)
        item_entry = {
            "name": name,
            "args": args,
            "row": row,
            "lbl_status": lbl_status,
            "lbl_desc": lbl_desc,
            "lbl_time": lbl_time,
            "r_layout": r_layout,
            "finished": False
        }
        self.items_data.append(item_entry)
        self._update_badge()

    def add_or_update_finished(self, data: dict):
        name = data.get("name", "")
        duration = data.get("duration", 0.0)
        success = data.get("success", True)
        result = data.get("result", "")

        target_item = None
        for item in reversed(self.items_data):
            if item["name"] == name and not item["finished"]:
                target_item = item
                break

        if not target_item:
            self.add_or_update_started(data)
            target_item = self.items_data[-1]

        target_item["finished"] = True
        if success:
            target_item["lbl_status"].setText("✅")
            target_item["lbl_time"].setText(f"{duration:.2f}s")
            target_item["lbl_time"].setStyleSheet("color: #4ade80; background: transparent; font-weight: bold;")
        else:
            target_item["lbl_status"].setText("❌")
            target_item["lbl_time"].setText(f"falha ({duration:.2f}s)")
            target_item["lbl_time"].setStyleSheet("color: #f87171; background: transparent; font-weight: bold;")

        if result and len(str(result).strip()) > 0:
            res_preview = str(result).strip()
            lines = res_preview.split("\n")
            short_res = "\n".join(lines[:3])
            if len(lines) > 3 or len(short_res) > 150:
                short_res = short_res[:150] + "..."

            lbl_detail = QLabel(f"↳ <i>{short_res}</i>")
            lbl_detail.setFont(QFont("Sans Serif", 8))
            lbl_detail.setStyleSheet("color: #64748b; background: transparent; padding-left: 18px;")
            lbl_detail.setWordWrap(True)
            target_item["r_layout"].addWidget(lbl_detail)

        self._update_badge()

    def _update_badge(self):
        total = len(self.items_data)
        done = sum(1 for i in self.items_data if i["finished"])
        if done == total and total > 0:
            self.lbl_badge.setText(f"{done}/{total} concluídos")
            self.lbl_badge.setStyleSheet("color: #4ade80; background: #14532d; border-radius: 4px; padding: 2px 6px;")
            self.lbl_header_title.setText("🤖  AÇÕES DO AGENTE CONCLUÍDAS")
        else:
            self.lbl_badge.setText(f"{done}/{total} passos")
            self.lbl_badge.setStyleSheet("color: #fad094; background: #162234; border-radius: 4px; padding: 2px 6px;")
            self.lbl_header_title.setText("🤖  AGENTE EM EXECUÇÃO...")
