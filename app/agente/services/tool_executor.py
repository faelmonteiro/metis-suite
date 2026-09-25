"""
Executor centralizado de ferramentas (tools).

Evita a duplicação do loop de busca e execução de ferramentas
entre os diferentes serviços de LLM (Ollama, Groq, Gemini).
"""
import logging

logger = logging.getLogger(__name__)


def executar_tool(name: str, args: dict) -> str:
    """
    Executa uma ferramenta registrada pelo nome passando os argumentos fornecidos.
    Retorna o resultado da execução como string.
    """
    from agente.services.tools_defs import AVAILABLE_TOOLS_CALLABLE

    if not isinstance(args, dict):
        args = {}

    if name not in AVAILABLE_TOOLS_CALLABLE:
        logger.warning(f"Ferramenta solicitada não encontrada: {name}")
        return f"Erro: Ferramenta '{name}' não encontrada no catálogo de ferramentas disponíveis."

    func = AVAILABLE_TOOLS_CALLABLE[name]

    # Valida a assinatura ANTES de executar: se os argumentos nao correspondem
    # aos parametros esperados, devolvemos erro explicito em vez de executar a
    # funcao com args invalidos (o que podia produzir "resultado-lixo" que a LLM
    # interpretava como sucesso).
    import inspect
    try:
        sig = inspect.signature(func)
        sig.bind(**args)
    except (TypeError, ValueError) as se:
        logger.warning(f"Args invalidos para ferramenta {name}: {se}")
        return (f"Erro: argumentos invalidos para a ferramenta '{name}'. "
                f"Assinatura esperada: {sig}. Recebido: {args}")

    try:
        resultado = func(**args)
        return str(resultado)
    except Exception as e:
        logger.error(f"Exceção durante execução da ferramenta {name}: {e}")
        return f"Erro na execução de {name}: {e}"
