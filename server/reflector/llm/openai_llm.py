import httpx
from transformers import AutoTokenizer
from reflector.settings import settings


class OpenAILLM:
    def __init__(self, config_prefix: str):
        self.config_prefix = config_prefix
        self.model_name = getattr(settings, f"{config_prefix}_MODEL")
        self.url = getattr(settings, f"{config_prefix}_LLM_URL")
        self.api_key = getattr(settings, f"{config_prefix}_LLM_API_KEY")
        
        self.client = httpx.AsyncClient(timeout=300)
        
        # Use a tokenizer that approximates OpenAI token counting
        tokenizer_name = getattr(settings, f"{config_prefix}_TOKENIZER", "gpt2")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        except:
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")


    async def generate(self, prompt: str, gen_schema=None, gen_cfg=None, logger=None, **kwargs) -> str:
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self.url.rstrip('/')}/chat/completions"
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def completion(self, messages: list, **kwargs) -> dict:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self.url.rstrip('/')}/chat/completions"
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()