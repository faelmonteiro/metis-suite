import os
import subprocess
from pathlib import Path

def ler_arquivo(caminho: str, max_chars: int = 25000) -> str:
    """
    Lê o conteúdo de um arquivo (texto puro ou PDF).
    Retorna o texto ou uma mensagem de erro começando com [Erro].
    """
    try:
        from agente.utils import caminho_leitura_seguro
        caminho_path = caminho_leitura_seguro(str(caminho))
    except Exception as e:
        return f"[Erro] Acesso negado: {e}"
    
    if not caminho_path.exists():
        return f"[Erro] Arquivo não encontrado: {caminho}"
        
    if not caminho_path.is_file():
        return f"[Erro] O caminho fornecido não é um arquivo: {caminho}"

    extensao = caminho_path.suffix.lower()

    try:
        # Se for PDF, tenta usar pdftotext
        if extensao == ".pdf":
            result = subprocess.run(
                ["pdftotext", str(caminho_path), "-"], 
                capture_output=True, text=True, check=True
            )
            texto = result.stdout
        else:
            # Tenta ler como texto puro (com limite na leitura para evitar OOM em arquivos gigantes)
            with open(caminho_path, "r", encoding="utf-8", errors="replace") as f:
                texto = f.read(max_chars + 1)

        # Truncamento de segurança para não explodir o contexto
        if len(texto) > max_chars:
            texto = texto[:max_chars] + f"\n... [Texto truncado após {max_chars} caracteres devido ao limite de contexto]"
            
        return texto.strip()
    except subprocess.CalledProcessError:
        return "[Erro] Falha ao extrair PDF. Certifique-se de que o pacote 'poppler-utils' está instalado (tem o pdftotext)."
    except FileNotFoundError:
        if extensao == ".pdf":
            return "[Erro] Comando 'pdftotext' não encontrado. Instale o pacote 'poppler-utils'."
        return f"[Erro] Arquivo não encontrado: {caminho}"
    except UnicodeDecodeError:
        return f"[Erro] O arquivo {caminho} parece ser um binário não suportado ou possui codificação inválida."
    except Exception as e:
        return f"[Erro] Falha desconhecida ao ler o arquivo: {e}"
