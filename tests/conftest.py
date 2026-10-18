"""Os testes nunca chamam APIs reais: chaves vazias e provedor padrão antes de qualquer import do app."""
import os

import pytest

for chave in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
    os.environ[chave] = ""
os.environ["NUTRITION_PROVIDER"] = "openrouter"
os.environ["IFOOD_MODE"] = "mock"  # os testes usam o catálogo fictício, qualquer que seja o .env
os.environ["CALORIAS_LOG"] = "off"
os.environ["BUSCA_LOG_CONTEUDO"] = "false"  # o .env de desenvolvimento liga; os testes verificam o padrão privado
os.environ["BUSCA_WEB_IDENTIFICAR"] = "false"  # sem rede nos testes; os testes da pesquisa ligam e trocam a busca por um dublê
os.environ["CALORIAS_CLASSIFICAR"] = "false"  # sem chamada de rede a um provedor falso; test_classificar liga e usa dublê
os.environ["BUSCA_LOG"] = "off"


@pytest.fixture(autouse=True)
def ambiente_limpo():
    """app.run grava NUTRITION_PROVIDER no ambiente; garante que um teste não vaze isso para o seguinte."""
    yield
    os.environ["NUTRITION_PROVIDER"] = "openrouter"
    os.environ["OPENAI_API_KEY"] = ""
    from app.core.config import get_settings
    get_settings.cache_clear()
