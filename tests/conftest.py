"""Os testes nunca chamam APIs reais: chaves vazias antes de qualquer import do app."""
import os

for chave in ("GEMINI_API_KEY", "OPENROUTER_API_KEY"):
    os.environ[chave] = ""
