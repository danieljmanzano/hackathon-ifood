"""Chamadas ao MCP do iFood pedidas pelo agente de busca: validar, executar com segurança e resumir.

O modelo só PEDE (nome + argumentos em JSON). Este módulo decide se pode:
  - só as tools de leitura listadas em FERRAMENTAS (além de `READ_TOOLS` e do schema real, em ifood_live._call_in);
  - a localização vem do endereço do usuário (o modelo não informa nem altera);
  - merchantId e ids de categoria só valem se já apareceram em resultados anteriores (nada de IDs inventados);
  - páginas pequenas, no máximo 3 chamadas por passo;
  - ao modelo volta um RESUMO curto (nomes, abertos, preços, ids), nunca o JSON bruto do iFood.
"""

from typing import Callable

from app.schemas.macro import MealCandidate

FERRAMENTAS = {"listItemTaxonomy", "searchOffers", "browseOffers", "getMerchant"}
MAX_CHAMADAS = 3
MAX_PAGINA = 15
ORDENACOES = {"RELEVANCE", "PRICE", "DELIVERY_TIME"}


def _ids(dados, chaves: tuple[str, ...]) -> set[str]:
    """Todos os valores das chaves dadas, em qualquer profundidade do JSON."""
    achados: set[str] = set()
    if isinstance(dados, dict):
        for k, v in dados.items():
            if k in chaves and isinstance(v, str):
                achados.add(v)
            else:
                achados |= _ids(v, chaves)
    elif isinstance(dados, list):
        for v in dados:
            achados |= _ids(v, chaves)
    return achados


def ids_de_restaurantes(dados) -> set[str]:
    return _ids(dados, ("merchantId",))


def ids_de_categorias(dados) -> set[str]:
    """Ids de categoria vindos de listItemTaxonomy (`taxonomy`) e das facetas das buscas."""
    achados: set[str] = set()
    if isinstance(dados, dict):
        for lista in (dados.get("taxonomy"), (dados.get("facets") or {}).get("itemTaxonomy")):
            achados |= {
                c["id"] for c in lista or [] if isinstance(c, dict) and isinstance(c.get("id"), str)
            }
    return achados


def preparar(
    chamada: dict, latitude: float, longitude: float, restaurantes_vistos: set[str]
) -> tuple[tuple[str, dict] | None, str | None]:
    """(nome, argumentos prontos) ou (None, motivo da recusa). Não faz rede."""
    nome = chamada.get("ferramenta") if isinstance(chamada, dict) else None
    if nome not in FERRAMENTAS:
        return None, f"ferramenta não permitida: {nome!r}. Permitidas: {sorted(FERRAMENTAS)}"
    argumentos = chamada.get("argumentos")
    argumentos = dict(argumentos) if isinstance(argumentos, dict) else {}
    argumentos.pop("userId", None)
    argumentos.pop("userLocation", None)
    if nome != "listItemTaxonomy":
        argumentos["userLocation"] = {"latitude": latitude, "longitude": longitude}
    if nome in ("listItemTaxonomy", "searchOffers", "browseOffers"):
        argumentos["merchantType"] = "RESTAURANT"  # o app só pede comida de restaurante
    if nome == "searchOffers" and not str(argumentos.get("query", "")).strip():
        return None, "searchOffers exige 'query' (use browseOffers para navegar sem termo)"
    if nome in ("searchOffers", "browseOffers"):
        argumentos.setdefault("resultKind", "ITEM")
        if argumentos["resultKind"] not in ("ITEM", "MERCHANT"):
            return None, "resultKind deve ser ITEM ou MERCHANT"
    if "pageSize" in argumentos:
        argumentos["pageSize"] = (
            max(1, min(int(argumentos["pageSize"] or 1), MAX_PAGINA))
            if isinstance(argumentos["pageSize"], (int, float))
            else MAX_PAGINA
        )
    refinamentos = argumentos.get("refinements")
    if refinamentos is not None and not isinstance(refinamentos, dict):
        return None, "refinements deve ser um objeto"
    for merchant_id in (argumentos.get("merchantId"), (refinamentos or {}).get("merchantId")):
        if merchant_id is not None and merchant_id not in restaurantes_vistos:
            return (
                None,
                f"merchantId {merchant_id!r} não apareceu em nenhum resultado anterior (não invente ids)",
            )
    if nome == "getMerchant" and not argumentos.get("merchantId"):
        return None, "getMerchant exige merchantId de um restaurante já visto"
    return (nome, argumentos), None


def sanear_refinamentos(refinamentos, categorias_vistas: set[str]) -> dict:
    """O que o modelo pode aplicar na próxima busca. Descarta o que não é seguro ou não foi visto."""
    if not isinstance(refinamentos, dict):
        return {}
    saida: dict = {}
    categorias = [
        c
        for c in refinamentos.get("itemTaxonomy") or []
        if isinstance(c, str) and c in categorias_vistas
    ]
    if categorias:
        saida["itemTaxonomy"] = categorias[:5]
    distancia = refinamentos.get("maxDistanceKm")
    if (
        isinstance(distancia, (int, float))
        and not isinstance(distancia, bool)
        and 0 < distancia <= 30
    ):
        saida["maxDistanceKm"] = float(distancia)
    minutos = refinamentos.get("maxDeliveryTimeMinutes")
    if isinstance(minutos, (int, float)) and not isinstance(minutos, bool) and 0 < minutos <= 180:
        saida["maxDeliveryTimeMinutes"] = int(minutos)
    return saida


def _reais(v):
    return v if isinstance(v, (int, float)) else None


def resumir(nome: str, argumentos: dict, dados: dict) -> dict:
    """Resumo curto para o modelo: o suficiente para decidir, sem despejar o JSON do iFood."""
    erro = dados.get("errors") if isinstance(dados, dict) else None
    if erro:
        return {
            "erro": {
                "codigo": erro.get("code"),
                "mensagem": str(erro.get("message", ""))[:160],
                "tentar_de_novo": erro.get("retryable"),
            }
        }
    if nome == "listItemTaxonomy":
        return {
            "categorias": [
                {"id": c.get("id"), "nome": c.get("name"), "disponibilidade": c.get("availability")}
                for c in (dados.get("taxonomy") or [])[:40]
            ]
        }
    if nome == "getMerchant":
        hoje = (dados.get("operatingHours") or {}).get("today") or {}
        return {
            "restaurante": dados.get("merchantName"),
            "aberto": dados.get("isOpen"),
            "hoje_abre_fecha": [hoje.get("openLocal"), hoje.get("closeLocal")],
            "entrega": [
                {
                    "modo": m.get("deliveryMethodMode"),
                    "taxa": _reais(m.get("fee")),
                    "minutos": m.get("estimatedMinutes"),
                }
                for m in (dados.get("deliveryMethods") or [])[:3]
            ],
            "pedido_minimo": _reais(dados.get("minimumOrderAmount")),
            "itens_em_destaque": [
                {"nome": i.get("itemName"), "preco": _reais(i.get("unitPrice"))}
                for i in (dados.get("featuredItems") or [])[:8]
            ],
        }
    resultados = dados.get("results") or []
    resumo: dict = {"quantidade": len(resultados)}
    if argumentos.get("resultKind") == "MERCHANT":
        resumo["restaurantes"] = [
            {
                "merchantId": m.get("merchantId"),
                "nome": m.get("merchantName"),
                "aberto": m.get("isOpen"),
                "nota": m.get("reviewRating"),
                "distancia_km": m.get("straightLineDistanceKm"),
                "proxima_abertura": m.get("nextOpenAt"),
            }
            for m in resultados[:10]
        ]
    else:
        resumo["itens"] = [
            {
                "nome": i.get("itemName"),
                "preco": _reais(i.get("promotionalUnitPrice") or i.get("unitPrice")),
                "restaurante": (i.get("merchant") or {}).get("merchantName"),
                "merchantId": (i.get("merchant") or {}).get("merchantId"),
                "aberto": (i.get("merchant") or {}).get("isOpen"),
            }
            for i in resultados[:10]
        ]
    categorias = (dados.get("facets") or {}).get("itemTaxonomy") or []
    if categorias:
        resumo["categorias_relacionadas"] = [
            {"id": c.get("id"), "nome": c.get("name")} for c in categorias[:10]
        ]
    return resumo


def candidatos_abertos(
    argumentos: dict, dados: dict, converter: Callable[[dict], list[MealCandidate]]
) -> list[MealCandidate]:
    """Pratos ABERTOS achados por uma chamada de itens: entram nas opções da próxima rodada."""
    if (
        not isinstance(dados, dict)
        or dados.get("errors")
        or argumentos.get("resultKind", "ITEM") != "ITEM"
    ):
        return []
    try:
        return [c for c in converter(dados) if c.available]
    except Exception:  # resposta fora do contrato: é só informativa, não deve derrubar a busca
        return []
