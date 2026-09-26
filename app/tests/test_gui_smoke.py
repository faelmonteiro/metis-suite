"""
Smoke test da GUI PyQt6 do Metis.

Rede de segurança das refatoracoes de `agente/ui/gui_app.py` (e do futuro
`agente/gui/`). A suite historicamente exercitava a GUI com apenas dois
testes unitarios, o que nao detecta: um metodo esquecido durante um "move",
uma pagina nao montada, um dialogo com assinatura quebrada ou um QSS que
passou a levantar no import.

Este modulo constroi a interface de verdade (offscreen) e fixa tres
invariantes:

  1. `MetisMainWindow` constroi e monta as 6 paginas.
  2. Os 8 dialogs constroem com os argumentos reais de `gui_app.py`.
  3. `MetisMainWindow` expoe exatamente o conjunto de metodos conhecido
     (snapshot) — e o que acusa um metodo perdido na modularizacao.
"""
import os
import re
import unittest
from pathlib import Path


# Precisa vir antes de qualquer import do PyQt6: sem QApplication, QPixmap e
# QWidget levantam RuntimeError. "offscreen" evita abrir janela no display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_APP = None


def _requer_qt():
    """Skip gracioso quando PyQt6 (e o modulo gui_app) nao estao disponiveis."""
    global _APP
    try:
        from PyQt6.QtWidgets import QApplication
        import agente.ui.gui_app  # noqa: F401
    except (ModuleNotFoundError, ImportError) as exc:
        raise unittest.SkipTest(f"Qt indisponivel no ambiente: {exc}") from exc

    # Uma unica QApplication por processo; pytest-pyqt nao e dependencia do projeto.
    _APP = QApplication.instance() or QApplication([])


def _janela():
    from agente.ui.gui_app import MetisMainWindow

    _requer_qt()
    return MetisMainWindow()


# Baseline da arvore de widgets. Difere de um "passa/falha" generico porque
# os metodos `setup_*_ui` estao monolithicos (100-190 linhas): um erro de
# refatoracao costuma trocar a ordem de um layout ou o texto de um label sem
# quebrar nenhuma assercao pontual. Aqui qualquer mexida na arvore aparece.
DIGITAL_BASELINE = Path(__file__).with_name("gui_impressao_digital.txt")
DIGITAL_DIALOGOS = Path(__file__).with_name("gui_dialogos")
DIGITAL_BALOES = Path(__file__).with_name("gui_baloes_chat.txt")

# O relogio e o nome da sessaoESTAMPado sao, por definicao, diferentes a cada
# execucao. Normaliza-los e o certo: o teste cobre estrutura, nao o passar do
# tempo.
_RE_TEMPO = (
    (re.compile(r"chat_\d{8}_\d{6}"), "chat_<T>"),
    (re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}"), "<data> <hora>"),
)


def _atributo(obj, nome, padrao=""):
    """Le um atributo/callable do Qt sem estourar em QObject sem esse metodo.

    Layouts e QObject genericos nao tem `isVisible`; um `getattr(x, 'isVisible')`
    direto quebrava o print no primeiro QLayout encontrado.
    """
    try:
        valor = getattr(obj, nome)
    except AttributeError:
        return padrao
    try:
        res = valor() if callable(valor) else valor
        if nome == "text" and isinstance(res, str):
            echo = getattr(obj, "echoMode", None)
            if echo is not None:
                try:
                    mode = echo() if callable(echo) else echo
                    if "Password" in str(mode):
                        return "<CHAVE_MASCARADA>" if res else ""
                except Exception:
                    pass
            if res.startswith("sk-") or "sk-" in res:
                return "<CHAVE_MASCARADA>"
        return res
    except Exception:
        return padrao


def _classe_qss(obj):
    """O `property("class")` do widget, que e o gancho do QSS do tema.

    Registrar so o `styleSheet` inline nao pegava isso: os dialogs nao estilizam
    por inline, e sim por classe. Trocar `KeyInput` por `KeyInpu` — um digito de
    typo — deixava o campo sem nenhuma formatacao e nenhum teste reclamava.
    """
    try:
        return obj.property("class") or ""
    except Exception:
        return ""


def impressao_digital(janela, normalizar_tempo=True):
    """Descreve cada QObject da janela: tipo, nome, pai, geometria e estado."""
    from PyQt6.QtCore import QObject

    linhas = []
    for obj in janela.findChildren(QObject):
        try:
            pai = obj.parent()
            campos = [
                type(obj).__name__,
                _atributo(obj, "objectName"),
                f"{type(pai).__name__}:{_atributo(pai, 'objectName')}" if pai else "",
                _atributo(obj, "geometry", ""),
                _atributo(obj, "isVisible", ""),
                _atributo(obj, "isEnabled", ""),
                _atributo(obj, "text"),
                _atributo(obj, "styleSheet"),
                _atributo(obj, "toolTip"),
                # `placeholderText` e o que orienta o usuario ("Cole sua chave
                # ou URL para..."), e nao tinha cobertura nenhuma.
                _atributo(obj, "placeholderText", ""),
                _classe_qss(obj),
                # `echoMode` so no QLineEdit, mas e o que garante que a chave de
                # API fique mascarada; trocar por Normal nao acusava nada.
                _atributo(obj, "echoMode", ""),
                # `sizeHint` e `minimumSizeHint` sao deliberadamente fora da
                # impressao digital. Eles dependem da metrica da fonte, e o
                # QSS pede `sans-serif` — um nome generico que o Qt resolve
                # pelo que houver instalado. Aqui resolve para Noto Sans com
                # `exactMatch() == False`; a baseline tinha sido gravada onde
                # resolveu para outra fonte e dava 2px de diferenca nos dois
                # eixos, num widget cujo codigo nao tinha mudado nada.
                #
                # Ou seja: o teste nao conseguia passar em duas maquinas, e
                # ja falhava no commit. `geometry` continua no lugar e cobre
                # o que importa de layout — e o QSS tem teste proprio agora,
                # em `test_gui_qss.py`, que le a folha de estilo gerada.
            ]
        except RuntimeError:
            # Destruido no meio da varredura. `deleteLater` e usado bastante
            # nesta GUI (oracles, chips de comando), e o `QTextFrame` interno de
            # um QLabel com HTML morre quando o texto e redefinido. Registrar
            # mantem o baseline diffavel; estourar aqui esconderia o resto.
            linhas.append(f"<deletado:{type(obj).__name__}>")
            continue
        linha = "|".join(str(c) for c in campos)
        if normalizar_tempo:
            for padrao, troca in _RE_TEMPO:
                linha = padrao.sub(troca, linha)
        linhas.append(linha)
    return "\n".join(linhas)


# Snapshot dos metodos de MetisMainWindow. Atualizar SOMENTE em refatoracoes
# que removem/renomeiam metodos de proposito — nunca para "fazer passar".
METODOS_ESPERADOS = frozenset({
    # `AiMixin.start_ai_query`: decisoes e corpos dos sinais do worker.
    "_atualizar_cronometro",
    "_criar_buffer_de_render",
    "_criar_cronometro",
    "_criar_worker",
    # `stop_ai_generation` foi de 75 para 17 linhas. Estas sao as pecas que
    # ele chamava inline: a tabela de sinais, os dois timers, o aviso do balao,
    # o cronometro congelado e o foco. `_desligar_sinais_do_worker` le a mesma
    # tabela de `_ligar_sinais_do_worker` — antes eram duas listas e o
    # `search_started` ficava conectado apos o cancelamento.
    "_congelar_cronometro_interrompido",
    "_desligar_sinais_do_worker",
    "_devolver_foco_ao_chat",
    "_fechar_cronometro",
    "_ia_ocupada",
    "_enfileirar",
    "_flush_render",
    "_ligar_sinais_do_worker",
    "_marcar_balao_interrompido",
    "_on_chunk",
    "_on_error",
    "_on_finished",
    "_on_search_started",
    "_on_tool_finished",
    "_on_tool_started",
    "_parar_timers_de_render",
    "_rotulo_do_cronometro",
    "_texto_do_usuario",
    "start_ai_query",
    "__init__", "_build_body", "_build_command_bar", "_build_header",
    "_build_info_panel", "_build_menu_column", "_build_prompt",
    "_atalho_do_dashboard",
    "_build_appearance_header", "_build_appearance_right",
    "_build_chat_features_card", "_build_memory_actions_card",
    "_build_attachment_bar", "_build_ai_actions", "_build_ai_bubble",
    "_build_ai_header", "_build_chip_row", "_build_chips_header",
    "_build_chat_header", "_build_chat_input_bar",
    "_build_message_area", "_build_user_bubble", "_make_content_label",
    "_build_opacity_card", "_build_oracles_header", "_build_provider_detail",
    "_build_provider_sidebar", "_build_session_manager_card",
    "_build_sidebar_buttons", "_build_sessions_header", "_build_theme_list_panel",
    "_build_timeline_label", "_build_timeline_scroll", "_build_typography_card",
    "_cmd_arquivo", "_cmd_deletar_sessao", "_cmd_executar", "_cmd_modelo",
    "_cmd_novo", "_cmd_sessao", "_cmd_web", "_copiar_comando_extraido",
    "_detalhe_g4f", "_detalhe_nuvem", "_detalhe_ollama",
    "_provider_list", "_render_selected_provider", "_reset_oracle_panels",
    "_resolver_provedor",
    "_create_info_item", "_exec_menu_aligned", "_on_command_error",
    "_on_command_finished", "_on_page_changed", "_process_next_in_queue",
    "_render_command_chips_for_bubble", "_render_custom_server_detail",
    "_render_provider_detail", "_set_bubble_content", "_populate_models_grid",
    "activate_custom_server",
    "activate_g4f", "activate_gemini", "activate_groq", "activate_nvidia",
    "activate_ollama", "add_chat_bubble", "apply_theme", "carregar_servico_padrao",
    "centralizar_janela", "clear_attachment", "clear_chat_view", "closeEvent",
    "create_new_session", "delete_builtin_server", "delete_current_session_file",
    "delete_custom_server", "delete_last_turn", "delete_n_turns",
    "ensure_active_provider_valid", "eventFilter", "execute_direct_search",
    "export_current_session", "focus_active_oracle_btn", "get_active_oracle_info",
    "get_active_provider_key", "handle_menu_action", "handle_prompt_submit",
    "init_ui", "keyPressEvent", "mover_para_canto_superior_direito",
    "navigate_menu", "navigate_oracles", "on_agent_options_updated",
    "on_apis_updated", "on_font_family_selected", "on_font_size_selected",
    "on_glow_toggled", "on_opacity_slider_changed", "on_server_restored",
    "on_session_selected", "open_appearance_page", "open_file_dialog",
    "open_oracles_page", "open_sessions_page", "prefill_prompt", "prompt_add_model",
    "prompt_edit_custom_server", "prompt_remove_model", "rebuild_oracle_buttons",
    "refresh_sessions_dropdown", "refresh_telemetry", "rename_current_session",
    "render_appearance_themes", "render_current_turns", "reset_appearance_defaults",
    "resizeEvent", "retry_last_query", "scroll_chat_to_bottom",
    "select_card", "select_oracle_btn",
    "select_provider_tab", "select_theme", "send_chat_message",
    "set_attachment", "setup_appearance_ui", "setup_chat_ui",
    "setup_dashboard_ui", "setup_oracles_ui", "setup_search_ui",
    "setup_sessions_ui",     "show_add_server_dialog", "show_agent_options_dialog", "show_apis_dialog",
    "show_chat_options_menu", "show_custom_server_options_menu",
    "show_help_dialog", "show_provider_options_menu", "show_restore_server_dialog",
    "show_status_dialog", "showEvent", "show_oracle_settings_menu",
    "start_ai_query", "stop_ai_generation", "sync_window_opacity",
    "toggle_or_focus", "process_text_command_or_query",
})


# (classe, argumentos) = assinatura real em gui_app.py. Os dialogs sao
# construtos sob demanda, entao so o smoke test os exercita.
DIALOGOS = [
    ("ModernApisDialog", lambda w: (w,)),
    ("ModernAgentOptionsDialog", lambda w: (w,)),
    ("CustomServerDialog", lambda w: (w,)),
    ("ModernAddModelDialog", lambda w: ("Groq",)),
    ("ModernRemoveModelDialog", lambda w: ("Groq", None, "modelo-teste")),
    ("ModernRestoreServerDialog", lambda w: (w,)),
    ("ModernHelpDialog", lambda w: (w,)),
    ("ModernStatusDialog", lambda w: (w.history_manager, w.current_service, w)),
]


class TestGuiSmoke(unittest.TestCase):
    """Constroi a GUI de verdade e fixa as invariantes acima."""

    @classmethod
    def setUpClass(cls):
        _requer_qt()
        cls.win = _janela()

    @classmethod
    def tearDownClass(cls):
        if cls.win is not None:
            cls.win.close()
            cls.win.deleteLater()
            cls.win = None

    def test_janela_constroi_com_6_paginas(self):
        """init_ui() monta as 6 pagas dentro do QStackedWidget."""
        self.assertEqual(self.win.stack.count(), 6)
        for attr in (
            "page_dashboard", "page_chat", "page_search",
            "page_oracles", "page_sessions", "page_appearance",
        ):
            self.assertTrue(hasattr(self.win, attr), f"pagina ausente: {attr}")

    def test_janela_monta_arvore_de_widgets(self):
        """A construcao real gera a arvore de widgets esperada (baseline 296)."""
        self.assertGreaterEqual(len(self.win.findChildren(object)), 250)

    def test_impressao_digital_da_arvore(self):
        """A arvore inteira bate com o baseline, linha a linha.

        Constroi uma janela SO para este teste: os demais testes criam dialogs
        e assimilaram widgets, e medir a `cls.win` compartilhada dava 4088
        objetos em vez de 348 — o teste media o estado deixado por outros.

        Para revisar o baseline de proposito (refatoracao que mude a arvore):
            METIS_ATUALIZAR_DIGITAL=1 python -m pytest tests/test_gui_smoke.py

        O diff no git mostra exatamente o que mudou na arvore.
        """
        from agente.ui.gui_app import MetisMainWindow

        limpa = MetisMainWindow()
        limpa.resize(860, 550)
        limpa.show()
        _APP.processEvents()
        try:
            obtido = impressao_digital(limpa)
        finally:
            limpa.close()
            limpa.deleteLater()

        if os.environ.get("METIS_ATUALIZAR_DIGITAL"):
            DIGITAL_BASELINE.write_text(obtido + "\n", encoding="utf-8")
            self.skipTest("baseline atualizado de proposito")

        self.assertTrue(
            DIGITAL_BASELINE.exists(),
            f"baseline ausente: {DIGITAL_BASELINE}. Gere com METIS_ATUALIZAR_DIGITAL=1",
        )
        esperado = DIGITAL_BASELINE.read_text(encoding="utf-8").rstrip("\n")
        if obtido == esperado:
            return

        dif = [
            f"  {i}: esperado={e!r}\n       obtido  ={o!r}"
            for i, (e, o) in enumerate(
                zip(esperado.splitlines(), obtido.splitlines()), start=1
            )
            if e != o
        ]
        self.fail(
            f"arvore de widgets mudou ({len(esperado.splitlines())} -> "
            f"{len(obtido.splitlines())} objetos)\n" + "\n".join(dif[:15])
        )

    def test_impressao_digital_dos_dialogs(self):
        """Cada dialog tambem bate com o baseline, objeto a objeto.

        A impressao da janela so cobre o que `init_ui` monta. Os dialogs sao
        top-level e nao entram nela — e sao justamente os `__init__` mais
        longos do projeto (267 linhas no de Opcoes do Agente), entao sem isso
        a divisao deles estaria sem prova nenhuma.

        Deliberadamente NAO fixa `isChecked`/`value`/`currentIndex`: esses
        valores vem de `config_models.json`, e o baseline passaria a depender
        da maquina de quem roda o teste.
        """
        import agente.ui.gui_app as g

        falhas = []
        for nome, montar_args in DIALOGOS:
            with self.subTest(dialogo=nome):
                dlg = getattr(g, nome)(*montar_args(self.win))
                try:
                    dlg.resize(dlg.width(), dlg.height())
                    dlg.show()
                    _APP.processEvents()
                    obtido = impressao_digital(dlg)
                finally:
                    dlg.close()
                    dlg.deleteLater()

                caminho = DIGITAL_DIALOGOS / f"{nome}.txt"
                if os.environ.get("METIS_ATUALIZAR_DIGITAL"):
                    caminho.write_text(obtido + "\n", encoding="utf-8")
                    continue

                if not caminho.exists():
                    falhas.append(f"  {nome}: baseline ausente ({caminho})")
                    continue
                esperado = caminho.read_text(encoding="utf-8").rstrip("\n")
                if esperado == obtido:
                    continue
                dif = [
                    f"    {i}: esperado={e!r}\n         obtido  ={o!r}"
                    for i, (e, o) in enumerate(
                        zip(esperado.splitlines(), obtido.splitlines()), start=1
                    )
                    if e != o
                ]
                if len(esperado.splitlines()) != len(obtido.splitlines()):
                    dif.insert(0, f"    contagem: {len(esperado.splitlines())}"
                                  f" -> {len(obtido.splitlines())}")
                falhas.append(f"  {nome}:\n" + "\n".join(dif[:10]))

        if falhas and not os.environ.get("METIS_ATUALIZAR_DIGITAL"):
            self.fail("arvore de um dialog mudou:\n" + "\n".join(falhas))

    def test_impressao_digital_dos_baloes(self):
        """Os baloes do chat batem com o baseline, objeto a objeto.

        A impressao da janela mede o que `init_ui` monta, e o chat NASCE VAZIO:
        `add_chat_bubble` (129 linhas) e `_render_command_chips_for_bubble`
        (102) nunca eram chamados por nenhum teste. Quatro mutacoes diferentes
        no `add_chat_bubble` — trocar `max_limit`, o nome do QSS `UserBubble`,
        a fonte e o glifo do botao de copiar — passaram sem que nada
        reclamasse. A divisao desses metodos estava sem prova nenhuma.

        Meço o `chat_container`, e nao cada balão, porque `impressao_digital`
        começa em `findChildren`, que exclui a raiz: passando a `bubble` o
        `setFixedWidth` da linha 641 ficaria de fora — e e a logica de
        largura que vale verificar.
        """
        from agente.ui.gui_app import MetisMainWindow

        # (rotulo, role, texto, is_queued) — cobre os caminhos que se
        # diferenciam: badge de fila, largura acima do limite, chips de
        # comando, e "Pensando...", que suprime os chips.
        casos = [
            ("user_simples", "user", "Qual o clima de hoje?", False),
            ("user_na_fila", "user", "segunda pergunta", True),
            ("user_largo", "user", "p" * 200, False),
            ("ai_simples", "assistant", "Resposta qualquer.", False),
            ("ai_com_chip", "assistant", "```\nls -la\n```", False),
            ("ai_pensando", "assistant", "Pensando...", False),
        ]

        limpa = MetisMainWindow()
        try:
            for _rotulo, role, texto, is_queued in casos:
                limpa.add_chat_bubble(role, texto, is_queued)
            _APP.processEvents()
            # Uma unica leitura, depois que os 6 baloes estao no container. Ler
            # uma vez por caso repetiria 6x a mesma arvore final sob 6 rotulos
            # diferentes — os rotulos mentiriam e o baseline incharia 6x.
            obtido = impressao_digital(limpa.chat_container)
        finally:
            limpa.close()
            limpa.deleteLater()

        if os.environ.get("METIS_ATUALIZAR_DIGITAL"):
            DIGITAL_BALOES.write_text(obtido + "\n", encoding="utf-8")
            self.skipTest("baseline atualizado de proposito")

        self.assertTrue(
            DIGITAL_BALOES.exists(),
            f"baseline ausente: {DIGITAL_BALOES}. Gere com METIS_ATUALIZAR_DIGITAL=1",
        )
        esperado = DIGITAL_BALOES.read_text(encoding="utf-8").rstrip("\n")
        if obtido == esperado:
            return

        dif = [
            f"  {i}: esperado={e!r}\n       obtido  ={o!r}"
            for i, (e, o) in enumerate(
                zip(esperado.splitlines(), obtido.splitlines()), start=1
            )
            if e != o
        ]
        self.fail(
            f"arvore de um balao mudou ({len(esperado.splitlines())} -> "
            f"{len(obtido.splitlines())} linhas)\n" + "\n".join(dif[:15])
        )

    def test_estado_inicial_da_janela(self):
        """Atributos de estado que a classe principal precisa continuar tendo."""
        for attr in (
            "history_manager", "current_service", "cards", "oracle_buttons",
            "chat_input", "prompt_input", "telemetry_timer",
        ):
            self.assertTrue(hasattr(self.win, attr), f"estado ausente: {attr}")

    def test_metodos_publicos_nao_perdidos(self):
        """Snapshot bidirecional: acusa metodo esquecido E snapshot defasado.

        Verificar so um lado deixa o snapshot derivar em silencio (metodo
        removido de proposito continuaria "faltando" para sempre). Exigir
        igualdade nos dois sentidos forcsa a atualizacao consciente.

        A coleta percorre a MRO ate a classe Qt, e nao so `vars()`: os metodos
        de `MetisMainWindow` estao divididos em mixins (`agente/gui/*`) e
        passam a ser herdados. `vars()` sozinho so veria o resto, e o teste
        acusaria perda onde nao houve.
        """
        from PyQt6.QtWidgets import QMainWindow
        from agente.ui.gui_app import MetisMainWindow

        metodos = set()
        for cls in MetisMainWindow.__mro__:
            if cls is QMainWindow:
                break
            metodos |= {nome for nome, val in vars(cls).items() if callable(val)}

        self.assertEqual(
            METODOS_ESPERADOS - metodos, set(),
            f"metodos ausentes em MetisMainWindow: {sorted(METODOS_ESPERADOS - metodos)}",
        )
        self.assertEqual(
            metodos - METODOS_ESPERADOS, set(),
            f"metodos novos nao registrados no snapshot: {sorted(metodos - METODOS_ESPERADOS)}",
        )

    def test_toggle_or_focus_presente(self):
        """Contrato usado pelo launcher de instancia unica."""
        from agente.ui.gui_app import MetisMainWindow

        self.assertTrue(callable(getattr(MetisMainWindow, "toggle_or_focus", None)))

    def test_contratos_de_importacao(self):
        """Os 5 pontos de entrada externos ao modulo."""
        import agente.ui.gui_app as g

        self.assertTrue(callable(g.main))
        self.assertTrue(callable(g.build_dynamic_qss))
        self.assertTrue(callable(g.get_system_theme_colors))
        self.assertTrue(callable(g.format_markdown_to_html))
        # QSS_STYLE e avaliado no import: se build_dynamic_qss levantar,
        # "import agente.ui.gui_app" quebra para todo mundo.
        self.assertIsInstance(g.QSS_STYLE, str)
        self.assertTrue(g.QSS_STYLE.strip())

    def test_dialogs_constroem(self):
        """Os 8 dialogs, cada um com a assinatura real de gui_app.py."""
        import agente.ui.gui_app as g

        for nome, montar_args in DIALOGOS:
            with self.subTest(dialogo=nome):
                cls = getattr(g, nome, None)
                self.assertIsNotNone(cls, f"dialogo ausente: {nome}")
                dlg = cls(*montar_args(self.win))
                try:
                    self.assertFalse(dlg.findChildren(object) == [])
                finally:
                    dlg.close()
                    dlg.deleteLater()

    def test_nenhum_modulo_gui_tem_import_morto(self):
        """Import morto nao quebra nada hoje, mas mascara o que quebrara amanha.

        `main_window.py` chegou a ter 115 imports dos quais 3 eram usados, sem
        que nenhum teste reclamasse: o codigo continuava funcionando e o
        arquivo dizia mentira sobre as dependencias. Aqui cada modulo de
        `agente/gui/` e conferido contra `scripts/verificar_modulo.py`.

        Reexports sao ignorados de proposito: o shim precisa de nomes que nao
        usa localmente.
        """
        import subprocess
        import sys
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        modulos = sorted(
            p for p in (raiz / "agente/gui").rglob("*.py") if p.name != "__init__.py"
        )
        self.assertTrue(modulos, "nenhum modulo encontrado em agente/gui/")
        r = subprocess.run(
            [sys.executable, "scripts/verificar_modulo.py",
             *[str(p.relative_to(raiz)) for p in modulos]],
            cwd=raiz, capture_output=True, text=True,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        self.assertEqual(
            r.returncode, 0,
            f"verificar_modulo reprovou:\n{r.stdout}{r.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
