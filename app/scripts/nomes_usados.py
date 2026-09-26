#!/usr/bin/env python3
"""
Lista os simbolos de nivel de modulo que um arquivo realmente usa.

Dois erros ja encontrados neste codebase, e que motivaram o script:

1. Escopo: os "locais" sao por FUNCAO. Juntar os locais de todos os metodos
   num conjunto so faz um nome parecer local em todo o arquivo (foi o que
   aconteceu na primeira versao, gerando uma lista de imports errada).

2. Poda: `ast.walk` e um gerador. Um `continue` ao encontrar uma funcao
   aninhada NAO pula os descendentes dela — eles continuam sendo emitidos e
   eram conferidos contra os locals da funcao externa. Da False positives
   como `m` (parametro de um `_repl` aninhado). Aqui a travessia e feita a mao
   e a subarvore e podada de verdade.

    python3 scripts/nomes_usados.py arquivo.py
"""
import ast
import builtins
import pathlib
import sys

BI = set(dir(builtins))
FN = (ast.FunctionDef, ast.AsyncFunctionDef)


def _args_locais(a):
    loc = set()
    for arg in [*getattr(a, "posonlyargs", []), *a.args, *a.kwonlyargs]:
        loc.add(arg.arg)
    if a.vararg:
        loc.add(a.vararg.arg)
    if a.kwarg:
        loc.add(a.kwarg.arg)
    return loc


def locais_da_funcao(fn):
    """Nomes resolvidos localmente dentro de `fn` (inclui aninhadas, lambdas e
    comprehensions)."""
    loc = _args_locais(fn.args)
    for x in ast.walk(fn):
        if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)):
            loc.add(x.id)
        elif isinstance(x, ast.Lambda):
            # args de lambda sao locais do lambda: `lambda _, f=inp: f.clear()`
            loc |= _args_locais(x.args)
        elif isinstance(x, FN) and x is not fn:
            loc.add(x.name)
            loc |= {n.id for n in ast.walk(x) if isinstance(n, ast.Name)
                    and isinstance(n.ctx, ast.Store)}
        elif isinstance(x, ast.ClassDef):
            loc.add(x.name)
        elif isinstance(x, ast.ExceptHandler) and x.name:
            loc.add(x.name)
        elif isinstance(x, (ast.Import, ast.ImportFrom)):
            for al in x.names:
                loc.add(al.asname or al.name.split(".")[0])
    return loc


def usados_dentro(no, loc):
    """Carrega `no`; desce em funcoes aninhadas com escopo = closure."""
    achados = set()
    for filho in ast.iter_child_nodes(no):
        if isinstance(filho, FN):
            # aninhada: escopo = seus locais + os da funcao que a contem (closure)
            achados |= usados_em_funcao(filho, loc)
            continue
        if isinstance(filho, ast.Name) and isinstance(filho.ctx, ast.Load):
            if filho.id not in BI and filho.id not in loc and filho.id != "self":
                achados.add(filho.id)
        achados |= usados_dentro(filho, loc)
    return achados


def usados_em_funcao(fn, externo=frozenset()):
    """`externo` = conjunto de locais das funcoes que envolvem `fn`."""
    return usados_dentro(fn, locais_da_funcao(fn) | externo)


def _metodos_diretos(cls):
    return [m for m in cls.body if isinstance(m, FN)]


def _locais_de_bloco(corpo, extra=frozenset(), incluir_imports=False):
    """Locais de um corpo de classe ou de modulo: tudo que e atribuido ali.

    `incluir_imports` fica False quando o objetivo e saber quais nomes *sao
    usados*: se o proprio import contasse como local, `import logging` +
    `logger = logging.getLogger(__name__)` se cancelariam e o `logging`
    pareceria nao usado.
    """
    loc = set(extra)
    for x in corpo:
        if isinstance(x, FN):
            loc.add(x.name)
            loc |= {n.id for n in ast.walk(x)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        elif isinstance(x, ast.ClassDef):
            loc.add(x.name)
        elif isinstance(x, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            alvos = x.targets if isinstance(x, ast.Assign) else [x.target]
            loc |= {t.id for t in alvos if isinstance(t, ast.Name)}
        elif isinstance(x, (ast.Import, ast.ImportFrom)) and incluir_imports:
            loc |= {a.asname or a.name.split(".")[0] for a in x.names}
        elif isinstance(x, (ast.For, ast.AsyncFor, ast.comprehension)):
            loc |= {n.id for n in ast.walk(x.target)
                    if isinstance(n, ast.Name)}
        elif isinstance(x, ast.ExceptHandler) and x.name:
            loc.add(x.name)
    return loc


_NOVO_ESCOPO = (FN, ast.ClassDef)


def _nomes_do_corpo(corpo, loc):
    """Nomes carregados em expressoes de nivel de classe/modulo.

    Faltava essa passagem, e o resultado saia errado nos dois sentidos:
    `import logging` + `logger = logging.getLogger(__name__)` marcava `logging`
    como morto, e `sinal = pyqtSignal()` dentro de uma classe marcava
    `pyqtSignal` como morto. Ambos estao em uso.

    Percorre com DFS explicito, e nao com `ast.walk`, porque `ast.walk` nao
    deixa podar: ele enfileira os descendentes antes de o laço ver o no. Num
    lambda, `continue` pulava o no mas os filhos ja vinham na fila, e o corpo
    do lambda era contado duas vezes — uma no escopo de dentro, outra no de
    fora, onde seus parametros sao nomes livres. Em `lambda: (lambda y: y)()`
    isso acusava `y` como "usado e nao importado".
    """
    achados = set()
    for stmt in corpo:
        achados |= _nomes_do_no(stmt, loc)
    return achados


def _nomes_do_no(no, loc):
    achados = set()
    if isinstance(no, ast.Lambda):
        # escopo proprio: corpo com os params do lambda como locais
        return _nomes_do_corpo([no.body], _args_locais(no.args))
    if isinstance(no, _NOVO_ESCOPO):
        return achados  # corpos tratados a parte, com escopo proprio
    if isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load):
        if no.id not in BI and no.id not in loc and no.id != "self":
            achados.add(no.id)
    for filho in ast.iter_child_nodes(no):
        achados |= _nomes_do_no(filho, loc)
    return achados


def _nomes_da_bases(cls):
    """Nomes carregados na declaracao `class X(A, B, metaclass=M)`.

    Precisa ser explicito: `bases` e `keywords` ficam no no ClassDef, e o
    percurso por metodos nao passa por eles. Sem isso, `class
    MetisMainWindow(PlatformMixin, ..., QMainWindow)` nao registraria nenhuma
    das 9 bases, e um header gerado a partir daqui ficaria sem elas —
    NameError no import, que o py_compile nao acusa.
    """
    achados = set()
    for b in list(cls.bases) + [k.value for k in cls.keywords]:
        for x in ast.walk(b):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load):
                achados.add(x.id)
    return achados


def usados_no_no(alvo):
    """
    Percorre APENAS as funcoes de topo. As aninhadas sao visitadas pela
    recursao de `usados_dentro`, que passa os locais da funcao que as contem
    (closure). Visitar aninhadas tambem pelo topo — sem escopo externo — faz
    os valores default (`def f(x=VAR)`) parecerem nomes externos: eles sao
    avaliados no escopo de quem define, nao no de quem recebe.
    """
    if isinstance(alvo, list):
        alvo = ast.Module(body=alvo, type_ignores=[])
    externo = set()
    # 1. codigo de nivel de modulo (constantes, `logger = logging.getLogger`)
    externo |= _nomes_do_corpo(alvo.body, _locais_de_bloco(alvo.body))
    # 2. classes e funcoes de topo
    for n in ast.iter_child_nodes(alvo):
        if isinstance(n, FN):
            externo |= usados_em_funcao(n)
        elif isinstance(n, ast.ClassDef):
            externo |= _nomes_da_bases(n)
            # `sinal = pyqtSignal()` e afim vivem no corpo da classe
            externo |= _nomes_do_corpo(n.body, _locais_de_bloco(n.body))
            for m in _metodos_diretos(n):
                externo |= usados_em_funcao(m)
    return externo


def definidos_no_modulo(tree):
    defs = set()
    for n in tree.body:
        if isinstance(n, (ast.ClassDef, ast.FunctionDef)):
            defs.add(n.name)
        elif isinstance(n, ast.Assign):
            defs.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            defs.update(a.asname or a.name.split(".")[0] for a in n.names)
    return defs


def main():
    caminho = sys.argv[1]
    tree = ast.parse(pathlib.Path(caminho).read_text(encoding="utf-8"))
    externos = sorted(n for n in usados_no_no(tree.body)
                      if n not in definidos_no_modulo(tree) and n not in BI)
    print(" ".join(externos))


if __name__ == "__main__":
    main()
