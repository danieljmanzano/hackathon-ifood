"""Skill: as tools de LEITURA do MCP do iFood que o agente de busca pode chamar para explorar antes de decidir.

Quem usa: services/busca_agente.py, anexada ao prompt do planejador (`busca_replanejar`) quando o provedor é o
          MCP real (modo live). No catálogo fictício (mock) ela não é enviada: não há MCP.
Modelo:   o mesmo LLM de texto do planejador; ele responde com acao="usar_ferramentas" e uma lista de chamadas.
Segurança (garantida pelo código, não só pelo texto): só estas 4 tools de leitura; o código injeta a localização do
          usuário; IDs de restaurante e de categoria só valem se apareceram em resultados anteriores; nada de
          carrinho, pedido ou checkout.
"""

FERRAMENTAS = """Ferramentas do MCP do iFood (somente leitura). Para usá-las responda acao="usar_ferramentas" com até
3 chamadas em "chamadas": [{"ferramenta": "...", "argumentos": {...}}]. O sistema executa, e você recebe os resultados
em "observacoes_mcp" no próximo passo, para então decidir. Não informe userLocation (o sistema coloca).
- listItemTaxonomy {merchantType?, expandFromTaxonomyId?}: categorias existentes (id, nome). Use para descobrir ids de
  culinária ou tipo de prato ("japanese_food", "pizza"...); expandFromTaxonomyId abre as subcategorias.
- searchOffers {query, resultKind: "ITEM"|"MERCHANT", refinements?}: busca por texto. ITEM devolve pratos; MERCHANT
  devolve restaurantes (use para ver quem existe e está aberto). refinements: itemTaxonomy (lista de ids),
  maxDistanceKm, maxDeliveryTimeMinutes, onlyOpen, sort ("RELEVANCE"|"PRICE"|"DELIVERY_TIME").
- browseOffers {resultKind, refinements?}: navega sem termo. Com refinements.merchantId lista o cardápio de um restaurante
  que apareceu antes.
- getMerchant {merchantId}: horário de funcionamento (hoje), se está aberto, formas de entrega e itens em destaque.
Regras das ferramentas:
- merchantType é RESTAURANT por padrão. Nunca invente merchantId nem ids de categoria: use só os que apareceram nas
  observações ou nos resultados anteriores.
- Resultados de ITEM (searchOffers/browseOffers) abertos entram automaticamente nas opções da próxima rodada; resultados
  fechados servem só para você entender a situação.
- Use poucas chamadas: cada passo gasta tempo, e o usuário está esperando. Se já sabe o que tentar, vá direto a
  "buscar_de_novo".
- Para aplicar o que aprendeu na próxima busca, preencha "refinamentos" (itemTaxonomy com ids vistos, maxDistanceKm,
  maxDeliveryTimeMinutes). O orçamento e o filtro de abertos o sistema controla."""


def exemplo() -> list[tuple[str, str]]:
    return [("trecho anexado ao planejador (modo live)", FERRAMENTAS)]
