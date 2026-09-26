#!/usr/bin/env python3
"""
Verificacao estatica de um modulo extraido.

`py_compile` so garante que o arquivo e sintaticamente valido e NAO que todo
nome usado exista. Dois erros passam pelo py_compile e so apareceriam em
runtime:

  - `QTimer` importado de `PyQt6.QtWidgets` (e QtCore) -> ImportError no import;
  - um simbolo esquecido no cabecalho -> NameError quando o metodo roda.

Aqui o modulo e realmente importado e cada nome usado e conferido contra o
namespace do modulo. Import circular tambem aparece aqui.

O inverso tambem e checado — import morto. Um bloco de imports copiado do
modulo antigo sobrevive a uma divisao e passa despercebido: `main_window.py`
chegou a ter 115 imports dos quais so 3 eram usados, e nada acusava, porque
"todo nome usado esta importado" continua verdadeiro.

Reexports intencionais nao contam como mortos: sao os imports marcados com
`# noqa: F401` ou listados no `__all__` do modulo (o shim
`agente/ui/gui_app.py` depende de varios).

    python3 scripts/verificar_modulo.py arquivo.py [outro.py ...]
"""
import ast
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from nomes_usados import usados_no_no, definidos_no_modulo  # noqa: E402


def importados(tree, src_linhas):
    """(nome importado -> linha do import) e o conjunto de reexports."""
    mapa, reexports = {}, set()
    dunder_all = set()
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    try:
                        dunder_all = set(ast.literal_eval(n.value))
                    except (ValueError, TypeError):
                        pass
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            noqa = "noqa: F401" in src_linhas[n.lineno - 1]
            for a in n.names:
                nome = a.asname or a.name.split(".")[0]
                mapa[nome] = n.lineno
                if noqa or nome in dunder_all:
                    reexports.add(nome)
    return mapa, reexports


def main():
    ruim = False
    for caminho in sys.argv[1:]:
        p = pathlib.Path(caminho)
        mod = str(p.with_suffix("")).replace("/", ".")
        while mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]

        src = p.read_text(encoding="utf-8")
        linhas = src.splitlines()
        tree = ast.parse(src)
        definidos = definidos_no_modulo(tree)
        usados = usados_no_no(tree.body)
        mapa, reexports = importados(tree, linhas)

        try:
            m = importlib.import_module(mod)
        except Exception as e:
            print(f"FAIL  {caminho}: import -> {type(e).__name__}: {e}")
            ruim = True
            continue

        problemas = []
        faltando = sorted(x for x in usados if not hasattr(m, x))
        if faltando:
            problemas.append(f"usados e nao importados: {faltando}")

        mortos = sorted(n for n in mapa if n not in usados and n not in reexports)
        if mortos:
            problemas.append(f"imports mortos: {mortos}")

        if problemas:
            print(f"FAIL  {caminho}: " + " | ".join(problemas))
            ruim = True
        else:
            print(f"ok    {caminho}  ({len(usados)} usados, {len(mortos)} mortos, "
                  f"{len(reexports)} reexports, {len(definidos)} definidos)")
    sys.exit(1 if ruim else 0)


if __name__ == "__main__":
    main()
