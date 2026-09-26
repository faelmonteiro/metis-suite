import json
import os
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from agente import config
from agente.utils import sanitizar_nome_sessao


class HistoryManager:
    def __init__(self, sessao: str = None):
        if sessao is None:
            from datetime import datetime
            sessao = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.sessao = sanitizar_nome_sessao(sessao)
        self.dir_path = Path(config.HISTORICO_DIR)
        self.dir_path.mkdir(parents=True, exist_ok=True)
        self.file_path = self.dir_path / f"{self.sessao}.json"
        self.historico = []
        self.saved_model = None
        self.carregar()

    def carregar(self):
        if not self.file_path.exists():
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if isinstance(dados, list):
                self.historico = dados
            elif isinstance(dados, dict):
                self.historico = dados.get("historico", [])
                self.saved_model = dados.get("OLLAMA_MODEL")
            else:
                self.historico = []

            self._validar_consistencia()

        except json.JSONDecodeError:
            print("[Aviso] Histórico corrompido. Criando backup.")
            backup = self.file_path.with_suffix(".json.bak")
            try:
                self.file_path.replace(backup)
            except Exception as _silent_e:
                logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
            self.historico = []
        except Exception:
            logger.exception("Falha ao carregar histórico")
            self.historico = []

    def salvar(self):
        try:
            dados = {
                "historico": self.historico,
                "OLLAMA_MODEL": config.OLLAMA_MODEL,
            }

            dir_name = str(self.file_path.parent)
            fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_name)

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(self.file_path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError as _silent_e:
                    logger.debug("Exceção silenciosa tratada: %s", _silent_e, exc_info=True)
                raise

        except Exception:
            logger.exception("Falha ao salvar histórico")

    def adicionar_mensagem(self, role: str, content: str, media_paths: list = None):
        if role == "assistant" and not str(content or "").strip():
            content = "⚠️ [Não foi possível obter uma resposta para esta consulta no momento.]"

        if role == "user" and self.sessao.startswith("chat_"):
            novo_nome = sanitizar_nome_sessao(content)[:30].strip("_")
            if novo_nome and novo_nome != "sessao":
                self.renomear_sessao(novo_nome)

        msg = {"role": role, "content": content}
        if media_paths:
            msg["media_paths"] = media_paths

        self.historico.append(msg)
        self.salvar()

    def limpar(self):
        self.historico = []
        self.salvar()

    def obter_contexto(self):
        max_msgs = config.MAX_HISTORY_MESSAGES

        if max_msgs <= 0:
            contexto = self.historico[:]
        else:
            contexto = self.historico[-max_msgs:]

        idx = 0
        while idx < len(contexto) and contexto[idx].get("role") != "user":
            idx += 1

        return contexto[idx:]

    def contagem_conversas(self):
        return len([m for m in self.historico if m.get("role") == "user"])

    def listar_turnos(self):
        turnos = []
        turno_atual = {}

        for m in self.historico:
            if m.get("role") == "user":
                if turno_atual:
                    turnos.append(turno_atual)
                turno_atual = {
                    "user": m.get("content", ""),
                    "assistant": ""
                }
            elif m.get("role") == "assistant":
                if turno_atual:
                    turno_atual["assistant"] = m.get("content", "")

        if turno_atual:
            turnos.append(turno_atual)

        return turnos

    def _reconstruir_historico_por_turnos(self, turnos):
        novo_hist = []

        for t in turnos:
            novo_hist.append({
                "role": "user",
                "content": t.get("user", "")
            })

            if t.get("assistant"):
                novo_hist.append({
                    "role": "assistant",
                    "content": t.get("assistant", "")
                })

        self.historico = novo_hist
        self.salvar()

    def truncar_ate(self, indice_turno: int) -> bool:
        turnos = self.listar_turnos()
        if 0 <= indice_turno < len(turnos):
            self._reconstruir_historico_por_turnos(turnos[:indice_turno + 1])
            return True
        return False

    def remover_turno(self, indice_turno: int) -> bool:
        turnos = self.listar_turnos()
        if 0 <= indice_turno < len(turnos):
            turnos.pop(indice_turno)
            self._reconstruir_historico_por_turnos(turnos)
            return True
        return False

    def deletar_ultimos(self, qtd: int) -> bool:
        if qtd <= 0:
            return True

        turnos = self.listar_turnos()
        if not turnos:
            return False

        if qtd >= len(turnos):
            self.limpar()
            return True

        self._reconstruir_historico_por_turnos(turnos[:-qtd])
        return True

    def _validar_consistencia(self):
        tamanho_original = len(self.historico)

        self.historico = [
            m for m in self.historico
            if isinstance(m, dict)
            and m.get("role") in {"user", "assistant", "system", "tool", "functionCall", "functionResponse"}
            and (
                isinstance(m.get("content"), (str, dict, list))
                or "functionCall" in m
                or m.get("role") in {"functionCall", "functionResponse"}
            )
        ]

        while self.historico and self.historico[0].get("role") not in {"user", "system"}:
            self.historico.pop(0)

        if len(self.historico) != tamanho_original:
            self.salvar()

    @staticmethod
    def listar_sessoes() -> list:
        dir_path = Path(config.HISTORICO_DIR)
        if not dir_path.exists():
            return []
        return sorted([
            f.stem
            for f in dir_path.glob("*.json")
            if not f.name.startswith(".")
        ])

    def trocar_sessao(self, nova_sessao: str) -> "HistoryManager":
        return HistoryManager(nova_sessao)

    def deletar_sessao(self) -> bool:
        try:
            if self.file_path.exists():
                self.file_path.unlink()
            self.historico = []
            return True
        except Exception:
            return False

    def renomear_sessao(self, novo_nome: str) -> bool:
        novo_nome = sanitizar_nome_sessao(novo_nome)
        nova_path = self.dir_path / f"{novo_nome}.json"

        if not self.file_path.exists():
            return False

        try:
            # Renomeação atômica sem sobrescrita: os.rename no Linux substitui
            # arquivos existentes em silêncio. Criar o link rígido do novo nome
            # (O_EXCL implícito) falha com FileExistsError se o alvo existir,
            # eliminando a janela de corrida do antigo check-then-rename.
            os.link(self.file_path, nova_path)
            self.file_path.unlink()
        except FileExistsError:
            return False
        except OSError:
            # Filesystem sem suporte a hard link: cai no rename com checagem.
            try:
                if nova_path.exists():
                    return False
                self.file_path.rename(nova_path)
            except OSError:
                return False

        self.sessao = novo_nome
        self.file_path = nova_path
        return True
