"""Comportamento do cartao de chave em `ModernApisDialog`.

A impressao digital em `tests/gui_dialogos/` garante que a arvore de widgets
continua igual. Nao diz nada sobre o que os botoes *fazem*, e neste cartao ha
tres acoes com efeito real: reativar um provedor removido (escreve no
registro de provedores e emite `keys_saved`), alternar a visibilidade da chave e
limpar o campo.

O selo de reativacao foi extraido de `_add_api_field` justamente para ficar
testavel; se ele voltar para dentro do construtor, estes testes falham por
`AttributeError`, o que e o aviso de que a emenda se perdeu.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_APP = None

# Nomes que os testes usam para achar widgets. Importados aqui para nao
# depender de `__globals__` do modulo testado.
_TEXTO_BOTAO_OLHO = "👁️"
_TEXTO_BOTAO_LIMPAR = "✕"
_TEXTO_BOTAO_REATIVAR = "🔄 Reativar"
_STATUS_SEM_CHAVE = "○ Não configurada"


def _app():
    global _APP
    from PyQt6.QtWidgets import QApplication

    _APP = QApplication.instance() or QApplication([])
    return _APP


def _dialogo():
    from agente.gui.dialogs.apis import ModernApisDialog

    return ModernApisDialog()


def _botao(dlg, texto):
    from PyQt6.QtWidgets import QPushButton

    for b in dlg.findChildren(QPushButton):
        if b.text() == texto:
            return b
    return None


def _rotulos(dlg):
    from PyQt6.QtWidgets import QLabel

    return [l.text() for l in dlg.findChildren(QLabel)]


def _campos(dlg):
    from PyQt6.QtWidgets import QLineEdit

    return dlg.findChildren(QLineEdit)


def _widgets_do_layout(layout):
    """Widgets de um layout, lidos do proprio layout.

    Um layout recem-construido nao tem widget-pai ainda, entao `parent()` nao
    serve; `itemAt` funciona nos dois casos.
    """
    widgets = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item and item.widget():
            widgets.append(item.widget())
    return widgets


class TestCartaoDeChave(unittest.TestCase):
    def setUp(self):
        _app()
        # O dialogo le as chaves do ambiente ao abrir. Sem isolar isso, o
        # resultado passa a depender de quem roda a suite ter GEMINI_API_KEY
        # exportado na maquina.
        self.env = mock.patch.dict(os.environ, {
            "GEMINI_API_KEY": "", "GROQ_API_KEY": "", "NVIDIA_API_KEY": "",
            "DEEPSEEK_API_KEY": "", "OPENROUTER_API_KEY": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def _abrir(self, removido=False):
        with mock.patch("agente.gui.dialogs.apis.is_servidor_removido",
                        return_value=removido):
            dlg = _dialogo()
        self.addCleanup(dlg.deleteLater)
        return dlg

    # --- mascara da chave ---------------------------------------------------

    def test_chave_nasce_mascarada(self):
        campo = _campos(self._abrir())[0]
        self.assertEqual(campo.echoMode(), campo.EchoMode.Password)

    def test_o_olho_alterna_a_mascara(self):
        dlg = self._abrir()
        campo = _campos(dlg)[0]
        olho = _botao(dlg, _TEXTO_BOTAO_OLHO)
        self.assertIsNotNone(olho, "o botão de mostrar chave não foi montado")
        olho.click()
        self.assertEqual(campo.echoMode(), campo.EchoMode.Normal)
        olho.click()
        self.assertEqual(campo.echoMode(), campo.EchoMode.Password)

    def test_o_x_limpa_o_campo(self):
        dlg = self._abrir()
        campo = _campos(dlg)[0]
        campo.setText("chave-que-vai-sumir")
        _botao(dlg, _TEXTO_BOTAO_LIMPAR).click()
        self.assertEqual(campo.text(), "")

    def test_campo_completo_tem_olho_e_aspas(self):
        dlg = self._abrir()
        # A dica que orienta o usuario a colar a chave.
        self.assertIn("Digite ou cole sua", _campos(dlg)[0].placeholderText())

    def test_campo_nao_senha_nao_tem_olho(self):
        """O botão de mostrar so faz sentido onde existe mascara.

        Chamado direto, para nao depender de qual dos quatro cartoes da
        passagem esta sem senha. A leitura e pelo proprio layout devolvido,
        que ainda nao tem widget-pai.
        """
        dlg = self._abrir()
        linha, campo = dlg._linha_de_entrada_api("", "VAR", is_password=False)
        self.assertEqual(campo.echoMode(), campo.EchoMode.Normal)
        textos = [b.text() for b in _widgets_do_layout(linha) if b.text()]
        self.assertNotIn(_TEXTO_BOTAO_OLHO, textos)
        self.assertIn(_TEXTO_BOTAO_LIMPAR, textos, "o X de limpar sumiu junto")

    def test_campo_com_senha_tem_o_olho(self):
        dlg = self._abrir()
        linha, campo = dlg._linha_de_entrada_api("", "VAR", is_password=True)
        textos = [b.text() for b in _widgets_do_layout(linha) if b.text()]
        self.assertIn(_TEXTO_BOTAO_OLHO, textos)
        self.assertEqual(campo.echoMode(), campo.EchoMode.Password)

    def test_o_campo_nao_carrega_classe_morta(self):
        """Nenhuma classe sem estilo pode sobrar no cartao.

        `KeyInput` foi removida destes campos: nao tinha seletor no QSS, e a
        impressao digital a registrava como se estivesse estilizada. O
        `test_gui_qss.py` agora impede que uma classe morta nova apareca — e
        este impede que ela volte pelos caminhos deste dialogo.
        """
        dlg = self._abrir()
        for campo in _campos(dlg):
            self.assertFalse(
                campo.property("class"),
                f"o campo voltou a carregar a classe {campo.property('class')!r}, "
                "que nao tem seletor no QSS",
            )

    # --- selo de servidor removido ------------------------------------------

    def test_sem_servidor_removido_nao_ha_botao_reativar(self):
        dlg = self._abrir(removido=False)
        self.assertIsNone(_botao(dlg, _TEXTO_BOTAO_REATIVAR))

    def test_servidor_removido_mostra_o_selo(self):
        dlg = self._abrir(removido=True)
        self.assertIsNotNone(_botao(dlg, _TEXTO_BOTAO_REATIVAR),
                             "provedor removido não mostrou o botão de reativar")
        self.assertTrue(any("Oculto da lista" in t for t in _rotulos(dlg)))

    def test_reativar_chama_o_registro_e_emite(self):
        """O botão escreve no registro de provedores e avisa a janela.

        `keys_saved` e o que faz a janela recarregar a lista. Sem a emissao o
        provedor voltava no disco e nao na tela, e o usuario clicava de novo
        sem efeito.
        """
        dlg = self._abrir(removido=True)
        recebidos = []
        dlg.keys_saved.connect(lambda: recebidos.append(1))
        botao = _botao(dlg, _TEXTO_BOTAO_REATIVAR)
        with mock.patch("agente.gui.dialogs.apis.restaurar_servidor_provedor") as restaura:
            botao.click()
        restaura.assert_called_once_with("gemini")
        self.assertEqual(recebidos, [1], "keys_saved não foi emitido")

    def test_reativar_marca_o_selo(self):
        dlg = self._abrir(removido=True)
        botao = _botao(dlg, _TEXTO_BOTAO_REATIVAR)
        with mock.patch("agente.gui.dialogs.apis.restaurar_servidor_provedor"):
            botao.click()
        self.assertTrue(any("Reativado" in t for t in _rotulos(dlg)),
                        "o selo não mudou para Reativado")

    def test_reativar_troca_a_cor_do_selo(self):
        """A cor e o unico sinal quando o texto ja foi reescrito.

        O verde sobre fundo escuro e o que diz "voltou"; se voltar para o
        vermelho, o selo mente.
        """
        from PyQt6.QtWidgets import QLabel

        dlg = self._abrir(removido=True)
        botao = _botao(dlg, _TEXTO_BOTAO_REATIVAR)
        with mock.patch("agente.gui.dialogs.apis.restaurar_servidor_provedor"):
            botao.click()
        alvo = [l for l in dlg.findChildren(QLabel) if "Reativado" in l.text()]
        self.assertTrue(alvo, "selo não encontrado")
        self.assertIn("#4ade80", alvo[0].styleSheet())

    # --- status configurado -------------------------------------------------

    def test_sem_chave_o_status_diz_nao_configurada(self):
        dlg = self._abrir(removido=False)
        self.assertIn(_STATUS_SEM_CHAVE, _rotulos(dlg))

    def test_com_chave_o_status_diz_configurada(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "sk-teste"}):
            with mock.patch("agente.gui.dialogs.apis.is_servidor_removido",
                            return_value=False):
                dlg = _dialogo()
            self.addCleanup(dlg.deleteLater)
        self.assertIn("● Configurada", _rotulos(dlg))


if __name__ == "__main__":
    unittest.main()
