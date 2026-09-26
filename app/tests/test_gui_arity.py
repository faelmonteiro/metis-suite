"""Os slots locais nao podem engolir o argumento do sinal.

`clicked` emite um `bool`. Quando um slot local e escrito para "capturar" as
variaveis do escopo por parametro default, o primeiro parametro posicional
deixa de ser o default e passa a receber o bool:

    def toggle_echo(field=inp):      # field = False
        field.setEchoMode(...)

Nao e um erro de logica, e um erro de processo: excecao levantada dentro de um
slot que o C++ chamou aborta o aplicativo inteiro. Isso ja esteve em cinco
slots deste projeto — dois abortavam o app, e "Excluir Turno" apagava o turno 0
em vez do turno da linha, porque `False == 0` em Python.

Este teste nao roda a GUI: le a AST e proibe o padrao. E a unica forma de
segurar os slots que ainda vao ser escritos, ja que a impressao digital nao
distingue um handler que funciona de um que aborta.
"""

import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = Path(__file__).resolve().parent.parent

# Sinais cujo primeiro argumento e um `bool` de "o botao esta marcado?".
# Qualquer slot local conectado a um destes precisa de um parametro posicional
# antes dos defaults.
SINAIS_COM_BOOL = {"clicked", "toggled", "pressed", "released"}


def _slots_locais(raiz: Path):
    """(arquivo, linha, sinal, funcao, primeiro_parametro_tem_default)."""
    achados = []
    for caminho in sorted(raiz.rglob("*.py")):
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        # Funcoes locais por nome. O padrao so aparece em `def` aninhado,
        # porque e onde se usa captura por parametro default.
        locais = {}
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.args.args:
                if len(no.args.defaults) == len(no.args.args):
                    locais[no.name] = True
        for no in ast.walk(arvore):
            if not (isinstance(no, ast.Call) and no.args):
                continue
            f = no.func
            if not (isinstance(f, ast.Attribute) and f.attr == "connect"):
                continue
            if not isinstance(f.value, ast.Attribute):
                continue
            if f.value.attr not in SINAIS_COM_BOOL:
                continue
            alvo = no.args[0]
            if isinstance(alvo, ast.Name) and locais.get(alvo.id):
                achados.append((caminho, no.lineno, f.value.attr, alvo.id))
    return achados


class TestAridadeDeSlot(unittest.TestCase):
    def test_nenhum_slot_local_engole_o_argumento_do_sinal(self):
        achados = _slots_locais(RAIZ / "agente")
        if achados:
            detalhe = "\n".join(
                f"  {c.relative_to(RAIZ)}:{ln}  {sinal}.connect({nome})  "
                f"— {nome}() comecava em parametro default"
                for c, ln, sinal, nome in achados
            )
            self.fail(
                "slot local conectado a um sinal que emite bool, comecando em "
                "parametro default. O PyQt entrega o bool nesse parametro:\n"
                f"{detalhe}\n"
                "  Use `def handler(_checked, x=capturado):` — explicito, e a "
                "prova de que o bool foi considerado."
            )

    def test_o_detector_encontra_o_caso_conhecido(self):
        """Confere que o detector funciona, com um arquivo sintético.

        Sem isto, um `ast` quebrado aqui transformaria o teste em um passa
        sempre silencioso — que e o pior formato de teste possível.
        """
        import tempfile

        exemplo = (
            "def externo():\n"
            "    widget = None\n"
            "    alvo = 'x'\n"
            "    def bom(_checked, x=alvo):\n"
            "        return x\n"
            "    def ruim(x=alvo):\n"
            "        return x\n"
            "    widget.clicked.connect(bom)\n"
            "    widget.clicked.connect(ruim)\n"
        )
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "exemplo.py"
            destino.write_text(exemplo, encoding="utf-8")
            achados = _slots_locais(Path(pasta))
        nomes = sorted(nome for _, _, _, nome in achados)
        self.assertEqual(nomes, ["ruim"], "o detector acusou o caso errado")


if __name__ == "__main__":
    unittest.main()
