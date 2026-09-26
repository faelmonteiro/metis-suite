"""Verificacao do CORPO do QSS, nao do seu tamanho.

Imprimir `len(QSS_STYLE)` nao verifica nada: uma regra deletada e outra
reescrita com o mesmo numero de caracteres produzem o mesmo tamanho. Este
arquivo le o CSS de verdade e confere o que quebra em silencio:

1. o CSS nao esta corrompido (chaves balanceadas, sem placeholder de
   f-string esquecido, sem regra sem seletor);
2. toda classe que o codigo atribui tem seletor correspondente;
3. as classes sem seletor estao numa lista explicita e datada, para que nao
   se acumule classe morta em silencio;
4. o texto do tema tem contraste suficiente, lido do CSS gerado e nao de
   constante.

O ponto (3) teve um caso e ele foi resolvido: `KeyInput` era atribuida em 5
widgets (campos de chave de API, de modelo e de servidor) sem aparecer em
nenhum seletor. Nao era bug visual — a regra generica de `QLineEdit` existe em
`agente/ui/theme_manager.py:630` e cobre esses campos. Era metadado enganoso:
a impressao digital da arvore registrava a classe, entao o teste "provava" que
o estilo do campo estava preservado sem nunca checar que ele existe. A
propriedade foi removida e a lista de classes mortas esta vazia; o teste abaixo
impede que a proxima apareca sem estilo.

Nenhum teste aqui precisa da janela: o QSS e uma string. Rodam em
milissegundos e sobrevivem a mudancas de layout.
"""

import os
import re
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = Path(__file__).resolve().parent.parent

# Classe atribuida a widgets e sem seletor no QSS, com o motivo e a data.
# Corrigir o estilo de verdade e apagar a entrada daqui: o teste falha ate voce
# apagar. Um item desta lista que ganhar seletor tambem faz o teste falhar,
# para a lista nao virar mentira.
#
# Vazia de proposito. `KeyInput` morava aqui — marcada em 5 widgets (campos de
# chave de API, de modelo e de servidor) e sem seletor nenhum. Nao era bug
# visual, porque a regra generica de `QLineEdit` cobre esses campos. Era
# metadado que enganava: a impressao digital registrava a classe e portanto
# "provava" que o estilo do campo estava preservado, sem nunca checar que o
# estilo existe. A propriedade foi removida dos 5 lugares; a lista fica vazia
# ate alguem querer um estilo proprio para campo de chave.
CLASSES_SEM_SELETOR_CONHECIDO: dict[str, str] = {}

# Conjunto de classes que o QSS de fato declara. E uma trava de queda, nao uma
#restricao de design:Classes novas podem entrar livremente, mas uma destas sumir
# significa regra apagada ou renomeada sem querer. O texto do QSS muda a cada
# tema, por isso o que fica pinado e o conjunto, nunca o conteudo.
CLASSES_DO_QSS = {
    "AIBubble", "ActionChip", "ApiCard", "CommandBox", "CommandChip", "DangerBtn",
    "HelpCard", "IconActionBtn", "ModelBtn", "ModelBtnActive", "OracleActiveBadge",
    "PrimaryBtn", "ProviderCard", "ProviderSidebarBtn", "ProviderSidebarBtnActive",
    "ProviderTag", "SecondaryBtn", "StatusPillActive", "StatusPillInactive",
    "StatusPillWarning", "ThemeCard", "ThemeCardActive", "TurnCard", "UserBubble",
}


def _qss() -> str:
    from agente.gui.theme_bridge import QSS_STYLE

    return QSS_STYLE


def _regras(qss: str) -> list[tuple[list[str], str]]:
    """Separa o CSS em (lista de seletores, corpo).

    Precisa tratar lista de seletores: `QLineEdit, QTextEdit { ... }` e uma
    regra so, com tres seletores. Um parser que para na virgula perde a
    unica regra generica de input do arquivo — foi assim que uma verificacao
    anterior concluiu, errado, que os campos estavam sem estilo.
    """
    sem_comentario = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    regras = []
    for achado in re.finditer(r"([^{}]+)\{([^{}]*)\}", sem_comentario):
        seletores = [s.strip() for s in achado.group(1).split(",") if s.strip()]
        if seletores:
            regras.append((seletores, achado.group(2)))
    return regras


def _propriedade(corpo: str, nome: str) -> str | None:
    """Le `nome: valor;` sem casar dentro de `background-color:`.

    `re.search('color: ...')` acha o `color:` de `background-color:`. O
    espaco exigido antes do nome resolve, porque `background-color` tem
    hifen grudado.
    """
    m = re.search(rf"(?:^|;|\s){re.escape(nome)}\s*:\s*([^;]+);", corpo, flags=re.M)
    return m.group(1).strip() if m else None


def _classes_no_qss(qss: str) -> set[str]:
    classes: set[str] = set()
    for seletores, _corpo in _regras(qss):
        for seletor in seletores:
            classes.update(re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)", seletor))
    return classes


def _classes_no_codigo() -> set[str]:
    """Classes que o codigo atribui a widgets.

    Le tambem `property("class") ==`, porque um template que compara a classe
    depende dela existir para a comparacao ter efeito.
    """
    classes: set[str] = set()
    atribuicao = re.compile(r"""setProperty\(\s*["']class["']\s*,\s*["']([A-Za-z0-9_]+)["']""")
    consulta = re.compile(r"""property\(\s*["']class["']\s*\)\s*==\s*["']([A-Za-z0-9_]+)["']""")
    for caminho in sorted((RAIZ / "agente").rglob("*.py")):
        texto = caminho.read_text(encoding="utf-8")
        classes.update(atribuicao.findall(texto))
        classes.update(consulta.findall(texto))
    return classes


def _rgb(cor: str) -> tuple[int, int, int] | None:
    cor = cor.strip()
    if cor.startswith("#"):
        digitos = cor[1:]
        if len(digitos) == 3:
            digitos = "".join(c * 2 for c in digitos)
        if len(digitos) == 6:
            try:
                return tuple(int(digitos[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
            except ValueError:
                return None
    m = re.match(r"rgba?\(([^)]+)\)", cor)
    if not m:
        return None
    partes = [p.strip() for p in m.group(1).split(",")]
    if len(partes) < 3:
        return None
    try:
        return tuple(int(round(float(p) * 255)) for p in partes[:3])  # type: ignore[return-value]
    except ValueError:
        return None


def _alfa(cor: str) -> float:
    m = re.match(r"rgba\(([^)]+)\)", cor.strip())
    if not m:
        return 1.0
    partes = [p.strip() for p in m.group(1).split(",")]
    if len(partes) < 4:
        return 1.0
    try:
        return max(0.0, min(1.0, float(partes[3])))
    except ValueError:
        return 1.0


def _sobre(cor: str, alfa: float, fundo: tuple[int, int, int]) -> tuple[int, int, int]:
    """Compoe cor com alfa sobre um fundo solido."""
    base = _rgb(cor)
    if base is None:
        raise ValueError(f"nao consegui interpretar {cor!r}")
    return tuple(int(round(base[i] * alfa + fundo[i] * (1 - alfa))) for i in range(3))  # type: ignore[return-value]


def _luminancia(cor) -> float:
    if isinstance(cor, str):
        cor = _rgb(cor)
    canais = []
    for valor in cor:
        c = valor / 255
        canais.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def _contraste(a, b) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


class TestIntegridadeDoQss(unittest.TestCase):
    def test_chaves_balanceadas(self):
        """CSS corrompido nao aplica metade: o Qt descarta a folha."""
        qss = _qss()
        self.assertEqual(
            qss.count("{"), qss.count("}"),
            f"chaves desbalanceadas: {qss.count('{')} abre, {qss.count('}')} fecha",
        )

    def test_sem_placeholder_nao_resolvido(self):
        """O QSS sai de uma f-string; `{` que sobrou aparece na tela."""
        qss = _qss()
        for regra in re.findall(r"\{[^{}]*\}", qss):
            self.assertIsNone(
                re.search(r"\{[A-Za-z_][A-Za-z0-9_]*[\}\[]", regra),
                f"placeholder nao resolvido: {regra.strip()[:70]}",
            )
        for artefato in ("%s", "%d", "{0}", "None"):
            self.assertNotIn(artefato, qss, f"artefato de Python vazou para o CSS: {artefato!r}")

    def test_toda_regra_tem_seletor(self):
        """Bloco sem seletor nao estiliza nada; costuma ser regra colada errada."""
        qss = re.sub(r"/\*.*?\*/", "", _qss(), flags=re.S)
        for achado in re.finditer(r"([^{}]*)\{([^{}]*)\}", qss):
            self.assertTrue(
                achado.group(1).strip(), f"regra sem seletor: {achado.group(2).strip()[:70]}"
            )


class TestClasseDoCodigoNoQss(unittest.TestCase):
    def test_toda_classe_atribuida_tem_seletor_ou_esta_declarada(self):
        """Classe sem seletor e estilo que o autor assumiu existir e nao existe.

        Este e o teste autoritativo: ou a classe estiliza alguma coisa, ou
        alguem decidiu por escrito que ela e inerte, com motivo e data. Sem
        isso, marcar `GhostInput` em um widget passa despercebido e o
        fingerprint passa a "provar" que o estilo do campo esta preservado.
        """
        com_seletor = _classes_no_qss(_qss())
        sem_seletor = [c for c in _classes_no_codigo() if c not in com_seletor]
        nao_declaradas = [c for c in sem_seletor if c not in CLASSES_SEM_SELETOR_CONHECIDO]
        self.assertEqual(
            nao_declaradas, [],
            f"atribuidas a widgets e sem seletor: escreva a regra ou declare com "
            f"motivo e data em CLASSES_SEM_SELETOR_CONHECIDO: {nao_declaradas}",
        )

    def test_lista_de_classes_mortas_continua_valida(self):
        """Impede a lista de virar fiction, nos dois sentidos.

        Uma classe que ganhou seletor nao e mais morta e a lista passa a
        mentir; uma classe que ninguem mais atribui nunca foi um achado, so
        um comentario desatualizado.
        """
        com_seletor = _classes_no_qss(_qss())
        usadas = _classes_no_codigo()
        obsoletas = [c for c in CLASSES_SEM_SELETOR_CONHECIDO if c in com_seletor]
        self.assertEqual(
            obsoletas, [],
            f"ganhou seletor; apague de CLASSES_SEM_SELETOR_CONHECIDO: {obsoletas}",
        )
        nao_usadas = [c for c in CLASSES_SEM_SELETOR_CONHECIDO if c not in usadas]
        self.assertEqual(
            nao_usadas, [], f"declaradas como mortas mas ninguem mais atribui: {nao_usadas}"
        )

    def test_toda_classe_do_qss_continua_declarada(self):
        """Trava de queda: uma regra que existia nao pode evaporar."""
        faltando = sorted(CLASSES_DO_QSS - _classes_no_qss(_qss()))
        self.assertEqual(faltando, [], f"classes que declaravam estilo e sumiram: {faltando}")


class TestLegibilidadeDoTema(unittest.TestCase):
    def _regra_de_input(self) -> str:
        """A regra generica de input, escolhida por seletor exato.

            QLineEdit, QTextEdit, QPlainTextEdit { ... }

        Casar por substring pega `QLineEdit#PromptInput`, que sobrescreve parte
        do resultado; por isso o conjunto de seletores tem de bater inteiro.
        """
        alvo = {"QLineEdit", "QTextEdit", "QPlainTextEdit"}
        for seletores, corpo in _regras(_qss()):
            if {s.split(":")[0].split("#")[0] for s in seletores} == alvo:
                return corpo
        self.fail("a regra generica de input sumiu do QSS")

    def test_texto_do_input_contrasta_com_o_fundo(self):
        """Lido do CSS gerado, nos dois cenarios de fundo possiveis.

        A janela tem `background: transparent`, entao o dialog aparece sobre o
        que houver atras. Um tema legivel so sobre desktop escuro e um tema
        quebrado para parte dos usuarios.
        """
        corpo = self._regra_de_input()
        cor = _propriedade(corpo, "color")
        fundo = _propriedade(corpo, "background-color")
        self.assertIsNotNone(cor, "regra de input sem `color`")
        self.assertIsNotNone(fundo, "regra de input sem `background-color`")

        alfa = _alfa(fundo)
        for nome, tras in (("desktop escuro", (0, 0, 0)), ("desktop claro", (255, 255, 255))):
            razao = _contraste(cor, _sobre(fundo, alfa, tras))
            self.assertGreater(
                razao, 4.5,
                f"texto {cor} sobre {fundo} (fundo {nome}) da contraste {razao:.2f}; "
                f"WCAG AA exige 4.5",
            )

    def test_borda_do_input_contrasta_com_o_fundo(self):
        """Borda invisivel e o jeito mais comum de um campo sumir no tema.

        O campo precisa de borda perceptivel contra o dialog; sem isso o
        usuario ve um retangulo de cor quase identica e nao acha onde digitar.
        """
        corpo = self._regra_de_input()
        fundo_campo = _propriedade(corpo, "background-color")
        borda = _propriedade(corpo, "border")
        self.assertIsNotNone(borda, "regra de input sem `border`")
        cores = re.findall(r"#[0-9a-fA-F]{3,6}", borda)
        self.assertTrue(cores, f"borda sem cor: {borda!r}")

        # O fundo do campo tem alfa; contra o dialog (tambem translucido) o
        # contraste real e menor que o do hex contra o preto. Compara as
        # cores compostas sobre as duas referencias, que e o pior caso.
        dialog = "#080f1d"
        for nome, tras in (("desktop escuro", (0, 0, 0)), ("desktop claro", (255, 255, 255))):
            alvo_dialog = _sobre(dialog, 0.90, tras)
            fundo_efetivo = _sobre(fundo_campo, _alfa(fundo_campo), alvo_dialog)
            pior = max(_contraste(cor, fundo_efetivo) for cor in cores)
            self.assertGreater(
                pior, 1.25,
                f"borda {cores} some no fundo (contraste {pior:.2f} sobre {nome})",
            )

    def test_texto_do_input_tem_borda(self):
        """Sem `border`, o campo depende so do fundo; e o caminho do sumico."""
        corpo = self._regra_de_input()
        self.assertIsNotNone(_propriedade(corpo, "border"), "campo de input sem borda")
        self.assertIsNotNone(_propriedade(corpo, "border-radius"), "campo de input sem raio")
