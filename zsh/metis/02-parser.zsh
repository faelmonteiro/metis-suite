#!/usr/bin/env zsh
# =============================================================================
# metis/02-parser.zsh
# Parser de ferramentas XML/Bash, captura de tela Kitty e buffer de contexto.
# =============================================================================

# -----------------------------------------------------------------------------
# Parser de tool_call.
#
# Havia duas implementações — Perl e Python — com a mesma lógica (~150 linhas
# duplicadas), e a de Perl era preferida sempre que o Perl existisse, o que
# tornava o Python código morto em qualquer máquina normal. Duas cópias da
# mesma regra divergem: basta um dia alguém consertar uma.
#
# Ficou só o Python, e por três motivos:
#   - Python já é dependência obrigatória. `_metis_require_deps` (00-config.zsh)
#     aborta sem `_metis_get_python`, e `api_ask.py`/`manage_models.py` já são
#     Python. O fallback de "e se não tiver Perl?" era uma garantia que o
#     projeto nunca precisou.
#   - `html.unescape` resolve a lista de entidades corretamente, contra as
#     sete substituições manuais (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;`,
#     `&#x27;`, `&apos;`) que a versão Perl mantinha à mão.
#   - `re` com `re.DOTALL` faz o `(?:</tool_call>|$)` — tag aberta, comum em
#     resposta truncada — sem o `-0777` e o `/s` do Perl.
#
# O comportamento é coberto por test_metis.zsh, que antes exercitava só o Perl
# e agora exercita o Python com os mesmos casos.
# -----------------------------------------------------------------------------

_metis_extract_cmd() {
  local text="$1"
  [[ -z "$text" ]] && return 0

  local py_bin="$(_metis_get_python)"
  [[ -z "$py_bin" ]] && return 1

  "$py_bin" -c '
import sys, re

text = sys.stdin.read()
if not text:
    sys.exit(0)

# Aceita somente tool_call com name="bash". O grupo final é `|$` e não a tag
# fechada: resposta truncada no meio do stream ainda precisa de comando
# executável, senão a rodada se perde.
m = re.search(r"<tool_call\b([^>]*)>(.*?)(?:</tool_call>|$)", text, re.DOTALL | re.IGNORECASE)
if not m:
    sys.exit(0)

attrs = m.group(1) or ""
content = m.group(2) or ""

nm = re.search(r"\bname\s*=\s*(?:\"([^\"]+)\"|([^\s>]+))", attrs, re.IGNORECASE)
name = ((nm.group(1) or nm.group(2)) if nm else "").lower()

if name != "bash":
    sys.exit(0)

content = content.strip()

# Remove tags internas acidentais, CDATA e cercas de código
content = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", content, flags=re.DOTALL)
content = re.sub(r"<!\[CDATA\[", "", content, flags=re.IGNORECASE)
content = re.sub(r"\]\]>", "", content)
content = re.sub(
    r"</?(?:cmd|command|bash|sh|exec|tool_call)[^>]*>",
    "",
    content,
    flags=re.IGNORECASE
).strip()

content = re.sub(r"^```(?:bash|sh|zsh)?\s*", "", content, flags=re.IGNORECASE)
content = re.sub(r"\s*```$", "", content).strip()

import html
content = html.unescape(content).strip()

if content:
    print(content)
' <<< "$text" 2>/dev/null
}

_metis_clean_final_msg() {
  local text="$1"
  [[ -z "$text" ]] && return 0

  local py_bin="$(_metis_get_python)"
  [[ -z "$py_bin" ]] && return 1

  "$py_bin" -c '
import sys, re

text = sys.stdin.read()
if not text:
    sys.exit(0)

# Remove tool_call fechado ou mal fechado.
text = re.sub(r"<tool_call\b[^>]*>.*?(?:</tool_call>|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
text = re.sub(r"</?(?:tool_call|cmd|command|bash|sh|exec)[^>]*>", "", text, flags=re.IGNORECASE)

# Remove blocos de raciocínio: <think>...</think>, <think> sem fechamento
# (o modelo foi cortado) e tags </think> soltas. Sem isso, uma resposta que
# contém só pensamento passava pelo teste de "mensagem final clara" e era
# impressa literal no terminal.
text = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
text = re.sub(r"</?think[^>]*>", "", text, flags=re.IGNORECASE)

print(text.strip())
' <<< "$text" 2>/dev/null
}

_metis_capture_screen() {
  local num_lines="${1:-30}"
  local target=""
  local listen_sock=""

  command -v kitty >/dev/null 2>&1 || return 0

  if [[ -n "${KITTY_LISTEN_ON:-}" ]]; then
    target="$KITTY_LISTEN_ON"
    [[ "$target" != *:* ]] && target="unix:$target"
  fi

  if [[ -z "$target" ]]; then
    local -a kitty_socks
    kitty_socks=(/tmp/mykitty*(N))

    if [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
      kitty_socks+=("${XDG_RUNTIME_DIR}"/mykitty*(N))
    fi

    if (( ${#kitty_socks} )); then
      listen_sock="$(ls -t -- "${kitty_socks[@]}" 2>/dev/null | head -n 1)"
      if [[ -S "$listen_sock" && ! -L "$listen_sock" && -O "$listen_sock" ]]; then
        target="unix:$listen_sock"
      fi
    fi
  fi

  if [[ -n "$target" ]]; then
    kitty @ --to "$target" get-text --extent=screen 2>/dev/null | tail -n "$num_lines"
  fi
}

_metis_summarize_output() {
  local file="$1"
  local max_chars="${2:-20000}"

  [[ -f "$file" ]] || return 0

  local lines
  lines="$(wc -l < "$file" 2>/dev/null | tr -d ' ')"
  [[ -z "$lines" ]] && lines=0

  if (( lines > 80 )); then
    {
      head -n 30 "$file"
      print '[... saída truncada ...]'
      tail -n 50 "$file"
    } 2>/dev/null | head -c "$max_chars"
  else
    cat "$file" 2>/dev/null | head -c "$max_chars"
  fi
}

_metis_trim_context() {
  local context="$1"
  local max_chars="${2:-60000}"

  if (( ${#context} <= max_chars )); then
    print -r -- "$context"
    return 0
  fi

  # O corte é por turno, não por byte, e é do MEIO para fora.
  #
  # A versão antiga fazia `tail -c`: guardava o fim e descartava o começo. Só
  # que o system prompt — as DIRETRIZES com a sintaxe obrigatória
  # <tool_call name="bash"> — é justamente o PRIMEIRO bloco. Com 3 passos de
  # saída grande ele saía pela janela, e do passo 4 em diante o modelo já não
  # recebia instrução de formato: respondia texto puro, o loop caía no ramo
  # "respondeu sem comando executável" e encerrava com passos sobrando.
  #
  # O extremo oposto também é erro: cortar no meio de um <tool_result> deixa a
  # tag aberta no histórico, e o modelo copia o padrão. Turno entra inteiro ou
  # não entra.

  # Por LINHAS, e não por separador. Duas surpresas do zsh 5.9, ambas
  # custaram uma tentativa cada:
  #   - `s` exige argumento aqui; `${(@ps)x}` é erro, apesar de a doc prometer
  #     que sem argumento ele quebra em newlines.
  #   - o argumento é delimitado por ponto: `${(@ps.\n.)x}` quebra em newline.
  #     `${(@ps:$sep)x}` — separador de variável — é erro de sintaxe.
  local -a linhas
  linhas=("${(@ps.\n.)context}")
  local total=${#linhas[@]}

  # Onde começam os turnos do assistente. O `\[` é escapado de propósito: sem
  # isso o zsh lê [Assistente] como classe de caracteres e casa com qualquer
  # letra isolada, esterlando o corte.
  local -a inicios
  local i j
  for (( i = 1; i <= total; i++ )); do
    [[ "${linhas[i]}" == \[Assistente\]:* ]] && inicios+=($i)
  done

  # Cabeça: tudo antes do primeiro turno. São as DIRETRIZES — a parte que o
  # corte antigo comia primeiro. Sem turnos ainda, devolve como está.
  if (( ${#inicios[@]} == 0 )); then
    print -r -- "$context"
    return 0
  fi

  local -a cabeca=("${(@)linhas[1,$inicios[1]-1]}")
  local usado=0
  for (( i = 1; i <= ${#cabeca[@]}; i++ )); do
    usado=$(( usado + ${#cabeca[i]} + 1 ))
  done

  # Do turno mais novo para o mais antigo, enquanto couber.
  local -a mantidos
  local tam linha
  for (( i = ${#inicios[@]}; i >= 1; i-- )); do
    j=$total
    (( i < ${#inicios[@]} )) && j=$(( inicios[i+1] - 1 ))

    # Um turno que não fecha </tool_result> é saída de comando que parecia
    # cabeçalho de turno, partida ao meio. Descarta em vez de carregar tag
    # aberta para o histórico.
    [[ "${linhas[j]}" == *'</tool_result>' ]] || continue

    tam=0
    for (( linha = inicios[i]; linha <= j; linha++ )); do
      tam=$(( tam + ${#linhas[linha]} + 1 ))
    done

    # O turno corrente nunca é descartado: sem ele o modelo perde o estado do
    # que acabou de rodar. Estourar o teto em alguns milhares é melhor.
    (( usado + tam > max_chars && ${#mantidos[@]} > 0 )) && break

    usado=$(( usado + tam ))
    mantidos=("$i" "${mantidos[@]}")
  done

  local novo="${(pj:\n:)cabeca}"
  if (( ${#mantidos[@]} < ${#inicios[@]} )); then
    novo="$novo"$'\n'"[Contexto anterior truncado]"
  fi
  for (( i = 1; i <= ${#mantidos[@]}; i++ )); do
    j=$total
    (( mantidos[i] < ${#inicios[@]} )) && j=$(( inicios[mantidos[i]+1] - 1 ))
    novo="$novo"$'\n'"${(pj:\n:)linhas[inicios[mantidos[i]],j]}"
  done

  print -r -- "$novo"
}
