"""
Modelos de dados e validação para config_models.json.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class CustomServer:
    """Servidor de API customizado (OpenRouter, DeepSeek, etc.)."""
    id: str
    nome: str
    base_url: str
    api_key_env: str = ""
    modelos: List[str] = field(default_factory=list)
    modelo_atual: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomServer":
        return cls(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            base_url=data.get("base_url", ""),
            api_key_env=data.get("api_key_env", ""),
            modelos=data.get("modelos", []),
            modelo_atual=data.get("modelo_atual", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "modelos": self.modelos,
            "modelo_atual": self.modelo_atual,
        }


@dataclass
class Preferences:
    """Preferências do usuário."""
    active_model: str = ""
    active_models: Dict[str, str] = field(default_factory=dict)
    theme_id: str = "metis_oracle"
    font_size: str = "medium"
    font_family: str = "default"
    window_opacity: int = 95
    neon_glow: bool = True
    copy_btn: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Preferences":
        return cls(
            active_model=data.get("active_model", ""),
            active_models=data.get("active_models", {}),
            theme_id=data.get("theme_id", "metis_oracle"),
            font_size=data.get("font_size", "medium"),
            font_family=data.get("font_family", "default"),
            window_opacity=int(data.get("window_opacity", 95)),
            neon_glow=bool(data.get("neon_glow", True)),
            copy_btn=bool(data.get("copy_btn", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_model": self.active_model,
            "active_models": self.active_models,
            "theme_id": self.theme_id,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "window_opacity": self.window_opacity,
            "neon_glow": self.neon_glow,
            "copy_btn": self.copy_btn,
        }


@dataclass
class ConfigModel:
    """Configuração completa do arquivo config_models.json."""
    schema_version: int = 2
    builtin_models: Dict[str, List[str]] = field(default_factory=dict)
    custom_servers: List[CustomServer] = field(default_factory=list)
    preferences: Preferences = field(default_factory=Preferences)
    removed_servers: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigModel":
        return cls(
            schema_version=data.get("schema_version", 2),
            builtin_models=data.get("builtin_models", {}),
            custom_servers=[CustomServer.from_dict(s) for s in data.get("custom_servers", [])],
            preferences=Preferences.from_dict(data.get("preferences", {})),
            removed_servers=[str(s).strip().lower() for s in data.get("removed_servers", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "builtin_models": self.builtin_models,
            "custom_servers": [s.to_dict() for s in self.custom_servers],
            "preferences": self.preferences.to_dict(),
            "removed_servers": self.removed_servers,
        }


def validate_provider_name(name: str) -> str:
    """Normaliza nome do provedor para canonical form."""
    return name.strip()


def validate_model_id(model_id: str) -> str:
    """Valida e normaliza ID do modelo."""
    return model_id.strip()


def is_server_removed(config: ConfigModel, server_id: str) -> bool:
    """Verifica se um servidor foi marcado como removido."""
    server_lower = server_id.strip().lower()
    return server_lower in config.removed_servers