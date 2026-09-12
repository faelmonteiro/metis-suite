#!/usr/bin/env zsh
# =============================================================================
# screen/04-tool-parser.zsh
# Parser de chamadas de ferramentas (tool_call) nos formatos XML e JSON.
# =============================================================================

_parse_tool_call() {
  local raw="$1"
  [[ -z "$raw" ]] && return 1

  TOOL_NAME=""
  TOOL_PATH=""
  TOOL_CONTENT=""

  local py_clean="${PYTHON_BIN:-$HOME/Metis/.venv/bin/python}"
  if [[ ! -x "$py_clean" ]]; then
    py_clean="$(command -v python3 2>/dev/null || echo python3)"
  fi

  if _python_ok "$py_clean"; then
    local py_res
    py_res="$("$py_clean" -c '
import sys, re, html, ast, json, base64

raw = sys.stdin.read()
if not raw:
    sys.exit(1)

def clean_val(text):
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<!\[CDATA\[", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\]\]>", "", text)

    # Extrai o valor caso venha encapsulado em <parameter...>...</parameter> ou <arg...>...</arg>
    param_m = re.search(r"<parameter\b[^>]*>(.*?)(?:</parameter>|$)", text, flags=re.DOTALL | re.IGNORECASE)
    if param_m:
        text = param_m.group(1)
    arg_m = re.search(r"<arg\b[^>]*>(.*?)(?:</arg>|$)", text, flags=re.DOTALL | re.IGNORECASE)
    if arg_m:
        text = arg_m.group(1)

    # Remove quaisquer tags residuais de XML de ferramentas (ex: </parameter>, </function>, etc.)
    text = re.sub(r"</?(?:parameter|param|function|invoke|arg|arguments|cmd|command|bash|sh|exec|code|script|tool_call|call)[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*```(?:[a-zA-Z0-9_-]+)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\n?\s*```\s*$", "", text.strip(), flags=re.IGNORECASE)
    text = html.unescape(text).strip()
    # Remove qualquer fechamento de tag dangling no final (ex: </parameter>, </function>)
    text = re.sub(r"\s*</[a-zA-Z0-9_-]+>\s*$", "", text, flags=re.DOTALL | re.IGNORECASE)

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)) and parsed:
                text = str(parsed[-1]).strip()
        except Exception:
            pass
    return text.strip()

# XML tool_call ou function
m = re.search(r"<(?:tool_call|function|invoke)\b([^>]*)>(.*?)(?:</(?:tool_call|function|invoke)>|$)", raw, re.DOTALL | re.IGNORECASE)
if m:
    attrs = m.group(1) or ""
    content = m.group(2) or ""
    nm = re.search(r"\bname\s*=\s*(?:\"([^\"]+)\"|\x27([^\x27]+)\x27|([^\s>]+))", attrs, re.IGNORECASE)
    if not nm:
        nm = re.search(r"^=([a-zA-Z0-9_-]+)", attrs)
    name = (nm.group(1) or nm.group(2) or nm.group(3) if nm else "bash").lower()
    pm = re.search(r"\bpath\s*=\s*(?:\"([^\"]+)\"|\x27([^\x27]+)\x27|([^\s>]+))", attrs, re.IGNORECASE)
    path = pm.group(1) or pm.group(2) or pm.group(3) if pm else ""
    c_val = clean_val(content)
    p_val = clean_val(path)
    if name or c_val or p_val:
        print(base64.b64encode((name or "bash").encode("utf-8")).decode("utf-8"))
        print(base64.b64encode(p_val.encode("utf-8")).decode("utf-8"))
        print(base64.b64encode(c_val.encode("utf-8")).decode("utf-8"))
        sys.exit(0)

# JSON tool_call fallback
if any(k in raw for k in ["\"name\"", "\"function\"", "\"cmd\""]):
    try:
        jm = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
        if jm:
            data = json.loads(jm.group(0))
            name = (data.get("name") or data.get("function", {}).get("name") or "bash").lower()
            args = data.get("arguments") or data.get("args") or data
            if isinstance(args, str):
                try: args = json.loads(args)
                except: args = {"cmd": args}
            cmd = args.get("cmd") or args.get("command") or args.get("content") or ""
            path = args.get("path") or args.get("filepath") or ""
            c_val = clean_val(cmd)
            p_val = clean_val(path)
            if c_val or p_val:
                print(base64.b64encode((name or "bash").encode("utf-8")).decode("utf-8"))
                print(base64.b64encode(p_val.encode("utf-8")).decode("utf-8"))
                print(base64.b64encode(c_val.encode("utf-8")).decode("utf-8"))
                sys.exit(0)
    except Exception:
        pass

sys.exit(1)
' <<< "$raw" 2>/dev/null)"

    if (( $? == 0 )) && [[ -n "$py_res" ]]; then
      local -a lines=("${(@f)py_res}")
      TOOL_NAME="$(print -r -- "${lines[1]}" | base64 -d 2>/dev/null)"
      TOOL_PATH="$(print -r -- "${lines[2]}" | base64 -d 2>/dev/null)"
      TOOL_CONTENT="$(print -r -- "${lines[3]}" | base64 -d 2>/dev/null)"
      return 0
    fi
  fi

  # Fallback puro ZSH caso Python falhe
  local line="" name="" path="" content=""
  local inside=0 found=0
  local open_re=$'<tool_call[[:space:]>]'
  local name_re=$'name=[\'"]?([A-Za-z0-9_-]+)'
  local path_re=$'path=[\'"]?([^\'"<>]+)'

  while IFS= read -r line; do
    if (( inside )); then
      if [[ "$line" == *'</tool_call>'* ]]; then
        content+="${line%%</tool_call>*}"$'\n'
        found=1
        break
      fi
      content+="$line"$'\n'
    else
      if [[ "$line" =~ $open_re ]]; then
        name=""
        path=""
        [[ "$line" =~ $name_re ]] && name="${match[1]}"
        [[ "$line" =~ $path_re ]] && path="${match[1]}"

        if [[ "$line" == *'</tool_call>'* ]]; then
          content="${line#*>}"
          content="${content%%</tool_call>*}"
          found=1
          break
        else
          inside=1
          content=""
        fi
      fi
    fi
  done <<< "$raw"

  if (( inside && !found && ${#content} > 0 )); then
    found=1
  fi

  (( found )) || return 1
  [[ -z "$name" ]] && name="bash"

  # Limpeza zsh de CDATA e markdown fences
  content="${content//<!\[CDATA\[/}"
  content="${content//\]\]>/}"
  content="${content#\`\`\`*}"
  content="${content%\`\`\`*}"

  # Remove tags residuais como </parameter>, </function>, etc.
  if command -v sed >/dev/null 2>&1; then
    content="$(print -r -- "$content" | sed -E 's#</?(parameter|param|function|invoke|arg|arguments|tool_call)[^>]*>##gi')"
  fi

  TOOL_NAME="$name"
  TOOL_PATH="$(_trim "$path")"
  TOOL_CONTENT="$(_trim "$content")"

  return 0
}
