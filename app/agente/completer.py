"""Autocomplete para comandos do agente."""

try:
    import readline
except ImportError:
    readline = None

COMANDOS = [
    "/novo", "/new", "/nova", "/web ", "/executar ", "/arquivo ",
    "/oraculo", "/oraculos", "/modelo ", "/tema", "/temas", "/iris", "/manto", "/aparencia",
    "/retry", "/repetir", "/limpar", "/clear", "/sessao", "/sessoes",
    "/exportar", "/status", "/ajuda", "/help", "/apis", "/api", "/chaves",
    "/automode", "/deletar_sessao", "/deletar_tudo",
    "/menu", "/sair", "/voltar",
]

def _completer(text, state):
    opcoes = [c for c in dict.fromkeys(COMANDOS) if c.startswith(text)]
    if state < len(opcoes):
        return opcoes[state]
    return None

def configurar_readline():
    if readline is None:
        return
    readline.set_completer(_completer)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims("")

# Integração com prompt_toolkit
try:
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    
    class ChatCompleterClass(Completer):
        def __init__(self):
            self.comandos = list(dict.fromkeys([c.strip() for c in COMANDOS]))
            self.path_completer = PathCompleter(expanduser=True)
            
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            
            # Se for comando que pede arquivo (/arquivo)
            if text.startswith('/arquivo ') and ' ' in text:
                from prompt_toolkit.document import Document
                path_text = text.split(' ', 1)[1]
                doc_path = Document(path_text, cursor_position=len(path_text))
                yield from self.path_completer.get_completions(doc_path, complete_event)
                return
            # Autocompleta comandos iniciais (que começam com /)
            # Como get_word_before_cursor ignora a barra '/', extraímos nós mesmos
            word = text.split(' ')[-1]
            if word.startswith('/'):
                for cmd in self.comandos:
                    if cmd.startswith(word):
                        yield Completion(cmd, start_position=-len(word))

    ChatCompleter = ChatCompleterClass()

except ImportError:
    ChatCompleter = None
