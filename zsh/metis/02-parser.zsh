#!/usr/bin/env zsh
# =============================================================================
# metis/02-parser.zsh
# Parser de ferramentas XML/Bash, captura de tela Kitty e buffer de contexto.
# =============================================================================

_metis_extract_cmd() {
  local text="$1"
  [[ -z "$text" ]] && return 0

  if command -v perl >/dev/null 2>&1; then
    local res
    res="$(print -r -- "$text" | perl -0777 -ne '
      if (/<tool_call\b([^>]*)>(.*?)(?:<\/tool_call>|$)/is) {
        my $attrs = $1 || "";
        my $content = $2 || "";
        if ($attrs =~ /\bname\s*=\s*(?:"([^"]+)"|([^\s>]+))/i) {
          my $name = lc($1 || $2 || "");
          next if $name ne "bash";
        }
        $content =~ s/<!\[CDATA\[(.*?)\]\]>/$1/gis;
        $content =~ s/<!\[CDATA\[//gi;
        $content =~ s/\]\]>//g;
        $content =~ s/<\/?(?:cmd|command|bash|sh|exec|tool_call)[^>]*>//gi;
        $content =~ s/^\s*```(?:bash|sh|zsh)?\s*//i;
        $content =~ s/\s*```\s*$//;
        $content =~ s/&amp;/&/g;
        $content =~ s/&lt;/</g;
        $content =~ s/&gt;/>/g;
        $content =~ s/&quot;/"/g;
        $content =~ s/&#39;/\x27/g;
        $content =~ s/&#x27;/\x27/g;
        $content =~ s/&apos;/\x27/g;
        $content =~ s/^\s+|\s+$//g;
        print $content if $content;
      }
    ' 2>/dev/null)"
    if [[ -n "$res" ]]; then
      print -r -- "$res"
      return 0
    fi
  fi

  local py_bin="$(_metis_get_python)"
  [[ -z "$py_bin" ]] && return 1

  "$py_bin" -c '
import sys, re

text = sys.stdin.read()
if not text:
    sys.exit(0)

# Aceita somente tool_call com name="bash".
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

  if command -v perl >/dev/null 2>&1; then
    local res
    res="$(print -r -- "$text" | perl -0777 -pe '
      s/<tool_call\b[^>]*>.*?(?:<\/tool_call>|$)//gis;
      s/<\/?(?:tool_call|cmd|command|bash|sh|exec)[^>]*>//gi;
      s/^\s+|\s+$//g;
    ' 2>/dev/null)"
    print -r -- "$res"
    return 0
  fi

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

  if (( ${#context} > max_chars )); then
    {
      print '[Contexto anterior truncado]'
      print -r -- "$context" | tail -c "$max_chars"
    }
  else
    print -r -- "$context"
  fi
}
