from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider: "ollama" | "openai" | "lmstudio" | "vllm" | "groq" | "together"
    # Any OpenAI-compatible API works with "openai" provider
    llm_provider: str = "ollama"

    # Model name (varies per provider)
    # Ollama:    llama3.3:70b, qwen2.5-coder:32b, deepseek-coder-v2
    # OpenAI:    gpt-4o, gpt-4o-mini
    # Groq:      llama-3.3-70b-versatile
    # Together:  meta-llama/Llama-3.3-70B-Instruct-Turbo
    # LM Studio: whatever model you loaded
    llm_model: str = "gpt-oss"

    # Base URL for the LLM API
    # Ollama:    http://localhost:11434
    # LM Studio: http://localhost:1234/v1
    # vLLM:      http://localhost:8080/v1
    # Groq:      https://api.groq.com/openai/v1
    # Together:  https://api.together.xyz/v1
    # OpenAI:    https://api.openai.com/v1
    llm_base_url: str = "http://localhost:11434"

    # API key (not needed for local Ollama/LM Studio, required for cloud)
    llm_api_key: str = ""

    # Timeout in seconds
    llm_timeout: int = 120

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Templates
    template_manifest_path: str = "../templates/TEMPLATE_MANIFEST.json"

    # Conversation limits (safety nets only — LLM decides dynamically)
    max_clarification_rounds: int = 5
    completeness_threshold: float = 0.85

    # CORS
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
