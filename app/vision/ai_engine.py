"""
Motor de Inteligência Artificial para Análise Visual.
Suporta múltiplos provedores (NVIDIA NIM, Google Gemini, OpenRouter e Ollama) com streaming em tempo real.
"""

import base64
import json
import os
import sys
from typing import Any, Generator, Optional
import httpx
import config

# Timeout padrão para requisições HTTP (com 120s de leitura para modelos vision)
_DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
DEFAULT_VISION_MAX_TOKENS = int(getattr(config, "MAX_VISION_TOKENS", 1500))

_vision_client: Optional[httpx.Client] = None

def _get_vision_client() -> httpx.Client:
    global _vision_client
    if _vision_client is None or _vision_client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=25, keepalive_expiry=60.0)
        _vision_client = httpx.Client(timeout=_DEFAULT_TIMEOUT, limits=limits, follow_redirects=True)
    return _vision_client

class VisionAIEngine:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or config.DEFAULT_PROVIDER
        self.model = model or config.DEFAULT_MODELS.get(self.provider)

    @staticmethod
    def _parse_openai_sse_stream(response: httpx.Response) -> Generator[str, None, None]:
        """Parseia stream SSE no padrão OpenAI (data: {...}) e gera chunks de conteúdo."""
        for line in response.iter_lines():
            line = line.strip()
            if not line or line == "data: [DONE]":
                continue
            if line.startswith("data: "):
                try:
                    chunk = json.loads(line[6:])
                    choices = chunk.get("choices", [])
                    if choices and "delta" in choices[0]:
                        content = choices[0]["delta"].get("content", "")
                        if content:
                            yield content
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"[ai_engine] Erro ao parsear SSE: {e}", file=sys.stderr)

    def chat_multiturn_stream(
        self,
        messages: list[dict[str, Any]],
        image_bytes: Optional[bytes] = None,
        system_instruction: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Permite conversação contínua (perguntas de acompanhamento) mantendo o contexto da tela.
        messages: Lista de dicionários [{'role': 'user'|'assistant', 'content': '...'}]
        """
        sys_prompt = system_instruction or config.SYSTEM_PROMPT
        b64_image = base64.b64encode(image_bytes).decode("utf-8") if image_bytes else None

        # Monta lista de mensagens no padrão OpenAI/NVIDIA/OpenRouter
        formatted_messages = [{"role": "system", "content": sys_prompt}]
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            text_content = msg.get("content", "")
            
            # Se for a primeira mensagem do usuário e houver imagem, anexa a imagem nela
            if i == 0 and role == "user" and b64_image:
                formatted_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_content},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                })
            else:
                formatted_messages.append({
                    "role": role,
                    "content": text_content
                })

        prov = self.provider.lower()
        base_url = None
        api_key = None
        model = self.model

        if prov == "nvidia":
            base_url = "https://integrate.api.nvidia.com/v1"
            api_key = config.NVIDIA_API_KEY
            model = self.model or "meta/llama-3.2-11b-vision-instruct"
        elif prov == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
            api_key = config.OPENROUTER_API_KEY
            model = self.model or "google/gemini-2.0-flash-exp:free"
        elif prov == "groq":
            base_url = "https://api.groq.com/openai/v1"
            api_key = config.GROQ_API_KEY
            model = self.model or "llama-3.3-70b-versatile"
        elif prov == "gemini" and config.GEMINI_API_KEY.startswith("AIzaSy"):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=config.GEMINI_API_KEY)
                contents = []
                for i, msg in enumerate(messages):
                    role = "user" if msg.get("role") == "user" else "model"
                    text_content = msg.get("content", "")
                    if i == 0 and role == "user" and image_bytes:
                        contents.append(types.Content(role=role, parts=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), types.Part.from_text(text=text_content)]))
                    else:
                        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text_content)]))

                response = client.models.generate_content_stream(
                    model=self.model or "gemini-2.0-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                yield f"⚠️ Erro no Gemini Multi-turn: {str(e)}"
                return
        elif prov == "ollama":
            url = f"{config.OLLAMA_HOST}/api/chat"
            ollama_messages = [{"role": "system", "content": sys_prompt}]
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                text_content = msg.get("content", "")
                if i == 0 and role == "user" and b64_image:
                    ollama_messages.append({"role": "user", "content": text_content, "images": [b64_image]})
                else:
                    ollama_messages.append({"role": role, "content": text_content})

            payload = {
                "model": self.model or config.OLLAMA_VISION_MODEL,
                "stream": True,
                "messages": ollama_messages
            }
            try:
                with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
                    with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            yield f"⚠️ Erro no Ollama ({response.status_code}): Verifique se o modelo está baixado."
                            return
                        for line in response.iter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except Exception:
                                    pass
                return
            except Exception as e:
                yield f"⚠️ Erro ao conectar ao Ollama: {str(e)}"
                return
        else:
            # Resolução dinâmica de Servidores Customizados cadastrados no Metis
            import model_manager
            cfg = model_manager.load_models_config()
            custom_srv = next((s for s in cfg.get("custom_servers", []) if s.get("id", "").lower() == prov or s.get("nome", "").lower() == prov), None)
            if custom_srv:
                b_url = custom_srv.get("base_url", "").rstrip("/")
                if b_url.endswith("/chat/completions"):
                    b_url = b_url[:-len("/chat/completions")]
                base_url = b_url
                k_env = custom_srv.get("api_key_env", f"{custom_srv.get('id', 'custom').upper()}_API_KEY")
                api_key = os.getenv(k_env, "").strip() or custom_srv.get("api_key", "").strip()
                model = self.model or custom_srv.get("modelo_atual", "")

        # Padrão OpenAI / NVIDIA / OpenRouter / Groq / Servidores Customizados
        if api_key and base_url:
            url = f"{base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "stream": True,
                "max_tokens": DEFAULT_VISION_MAX_TOKENS,
                "temperature": 0.2,
                "messages": formatted_messages
            }
            try:
                client = _get_vision_client()
                with client.stream("POST", url, headers=headers, json=payload) as response:
                        if response.status_code == 429:
                            yield "⚠️ Limite de requisições (Rate Limit) atingido no modelo atual. Experimente selecionar outro modelo no topo!"
                            return
                        if response.status_code != 200:
                            yield f"⚠️ Erro na API ({response.status_code})"
                            return
                        yield from self._parse_openai_sse_stream(response)
            except Exception as e:
                yield f"⚠️ Erro de conexão com {prov.upper()}: {str(e)}"
        else:
            yield from self.analyze_text_stream(messages[-1]["content"])

    def analyze_stream(
        self,
        image_bytes: bytes,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Analisa a imagem e faz streaming dos blocos de texto gerados.
        """
        sys_prompt = system_instruction or config.SYSTEM_PROMPT
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        prov = self.provider.lower()

        if prov == "gemini" and config.GEMINI_API_KEY.startswith("AIzaSy"):
            yield from self._stream_gemini(image_bytes, prompt, sys_prompt)
        elif prov == "nvidia":
            yield from self._stream_openai_compatible(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=config.NVIDIA_API_KEY,
                model=self.model or "meta/llama-3.2-11b-vision-instruct",
                b64_image=b64_image,
                prompt=prompt,
                system_prompt=sys_prompt
            )
        elif prov == "openrouter":
            yield from self._stream_openai_compatible(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.OPENROUTER_API_KEY,
                model=self.model or "google/gemini-2.0-flash-exp:free",
                b64_image=b64_image,
                prompt=prompt,
                system_prompt=sys_prompt
            )
        elif prov == "groq":
            yield from self._stream_openai_compatible(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.GROQ_API_KEY,
                model=self.model or "llama-3.3-70b-versatile",
                b64_image=b64_image,
                prompt=prompt,
                system_prompt=sys_prompt
            )
        elif prov == "ollama":
            yield from self._stream_ollama(b64_image, prompt, sys_prompt)
        else:
            # Verifica servidores customizados
            import model_manager
            cfg = model_manager.load_models_config()
            custom_srv = next((s for s in cfg.get("custom_servers", []) if s.get("id", "").lower() == prov or s.get("nome", "").lower() == prov), None)
            if custom_srv:
                b_url = custom_srv.get("base_url", "").rstrip("/")
                if b_url.endswith("/chat/completions"):
                    b_url = b_url[:-len("/chat/completions")]
                k_env = custom_srv.get("api_key_env", f"{custom_srv.get('id', 'custom').upper()}_API_KEY")
                k_val = os.getenv(k_env, "").strip() or custom_srv.get("api_key", "").strip()
                mod_val = self.model or custom_srv.get("modelo_atual", "")
                yield from self._stream_openai_compatible(
                    base_url=b_url,
                    api_key=k_val,
                    model=mod_val,
                    b64_image=b64_image,
                    prompt=prompt,
                    system_prompt=sys_prompt
                )
            else:
                # Fallback para NVIDIA ou OpenRouter
                if config.NVIDIA_API_KEY:
                    yield from self._stream_openai_compatible(
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=config.NVIDIA_API_KEY,
                        model="meta/llama-3.2-11b-vision-instruct",
                        b64_image=b64_image,
                        prompt=prompt,
                        system_prompt=sys_prompt
                    )
                elif config.OPENROUTER_API_KEY:
                    yield from self._stream_openai_compatible(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=config.OPENROUTER_API_KEY,
                        model="google/gemini-2.0-flash-exp:free",
                        b64_image=b64_image,
                        prompt=prompt,
                        system_prompt=sys_prompt
                    )
                else:
                    yield "⚠️ Nenhuma chave de API válida encontrada. Configure GEMINI_API_KEY, NVIDIA_API_KEY ou OPENROUTER_API_KEY no arquivo .env."

    def analyze_text_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_instruction: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Processa texto puro ou contexto de arquivos/pastas com streaming.
        """
        sys_prompt = system_instruction or config.SYSTEM_PROMPT
        full_user_prompt = f"{context}\n\n[SOLICITAÇÃO DO USUÁRIO]: {prompt}" if context else prompt
        prov = self.provider.lower()

        if prov == "nvidia":
            yield from self._stream_openai_compatible_text(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=config.NVIDIA_API_KEY,
                model=self.model or "meta/llama-3.2-11b-vision-instruct",
                prompt=full_user_prompt,
                system_prompt=sys_prompt
            )
        elif prov == "openrouter":
            yield from self._stream_openai_compatible_text(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.OPENROUTER_API_KEY,
                model=self.model or "google/gemini-2.0-flash-exp:free",
                prompt=full_user_prompt,
                system_prompt=sys_prompt
            )
        elif prov == "groq":
            yield from self._stream_openai_compatible_text(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.GROQ_API_KEY,
                model=self.model or "llama-3.3-70b-versatile",
                prompt=full_user_prompt,
                system_prompt=sys_prompt
            )
        elif prov == "gemini" and config.GEMINI_API_KEY.startswith("AIzaSy"):
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                response = client.models.generate_content_stream(
                    model=self.model or "gemini-2.0-flash",
                    contents=[full_user_prompt],
                    config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.2)
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                yield f"⚠️ Erro no Gemini API: {str(e)}"
        elif prov == "ollama":
            url = f"{config.OLLAMA_HOST}/api/chat"
            payload = {
                "model": self.model or config.OLLAMA_VISION_MODEL,
                "stream": True,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": full_user_prompt}
                ]
            }
            try:
                with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
                    with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            yield f"⚠️ Erro no Ollama ({response.status_code}): Verifique se o modelo está baixado."
                            return
                        for line in response.iter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except Exception:
                                    pass
            except Exception as e:
                yield f"⚠️ Erro ao conectar ao Ollama: {str(e)}"
        else:
            # Verifica servidores customizados
            import model_manager
            cfg = model_manager.load_models_config()
            custom_srv = next((s for s in cfg.get("custom_servers", []) if s.get("id", "").lower() == prov or s.get("nome", "").lower() == prov), None)
            if custom_srv:
                b_url = custom_srv.get("base_url", "").rstrip("/")
                if b_url.endswith("/chat/completions"):
                    b_url = b_url[:-len("/chat/completions")]
                k_env = custom_srv.get("api_key_env", f"{custom_srv.get('id', 'custom').upper()}_API_KEY")
                k_val = os.getenv(k_env, "").strip() or custom_srv.get("api_key", "").strip()
                mod_val = self.model or custom_srv.get("modelo_atual", "")
                yield from self._stream_openai_compatible_text(
                    base_url=b_url,
                    api_key=k_val,
                    model=mod_val,
                    prompt=full_user_prompt,
                    system_prompt=sys_prompt
                )
            elif config.NVIDIA_API_KEY:
                yield from self._stream_openai_compatible_text(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=config.NVIDIA_API_KEY,
                    model="meta/llama-3.2-11b-vision-instruct",
                    prompt=full_user_prompt,
                    system_prompt=sys_prompt
                )

    def _stream_openai_compatible_text(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str
    ) -> Generator[str, None, None]:
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "stream": True,
            "max_tokens": DEFAULT_VISION_MAX_TOKENS,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            client = _get_vision_client()
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    yield f"⚠️ Erro na API ({response.status_code})"
                    return
                yield from self._parse_openai_sse_stream(response)
        except Exception as e:
            yield f"⚠️ Erro de conexão: {str(e)}"


    def _stream_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        b64_image: str,
        prompt: str,
        system_prompt: str
    ) -> Generator[str, None, None]:
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "stream": True,
            "max_tokens": DEFAULT_VISION_MAX_TOKENS,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                        }
                    ]
                }
            ]
        }

        try:
            client = _get_vision_client()
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    yield f"⚠️ Erro na API ({response.status_code})"
                    return
                yield from self._parse_openai_sse_stream(response)
        except Exception as e:
            yield f"⚠️ Erro de conexão com o modelo: {str(e)}"

    def _stream_gemini(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str
    ) -> Generator[str, None, None]:
        try:
            from google import genai
            from google.genai import types
            from PIL import Image
            import io

            client = genai.Client(api_key=config.GEMINI_API_KEY)
            img = Image.open(io.BytesIO(image_bytes))
            
            response = client.models.generate_content_stream(
                model=self.model or "gemini-2.0-flash",
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2
                )
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"⚠️ Erro no Gemini API: {str(e)}"

    def _stream_ollama(
        self,
        b64_image: str,
        prompt: str,
        system_prompt: str
    ) -> Generator[str, None, None]:
        url = f"{config.OLLAMA_HOST}/api/chat"
        payload = {
            "model": self.model or config.OLLAMA_VISION_MODEL,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_image]
                }
            ]
        }
        try:
            client = _get_vision_client()
            with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield f"⚠️ Erro no Ollama ({response.status_code}): Verifique se o Ollama está rodando e o modelo baixado."
                        return
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                msg = data.get("message", {})
                                content = msg.get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                pass
        except Exception as e:
            yield f"⚠️ Erro ao conectar ao Ollama: {str(e)}"

if __name__ == "__main__":
    from capture import capture_screen
    print("Testando motor de IA com captura...")
    engine = VisionAIEngine()
    print(f"Provedor ativo: {engine.provider} | Modelo: {engine.model}")
    img_data = capture_screen("fullscreen")
    
    print("\nResposta em tempo real:")
    for chunk in engine.analyze_stream(img_data, config.QUICK_ACTIONS["resumo"]):
        print(chunk, end="", flush=True)
    print("\n\n--- Teste concluído com sucesso ---")
