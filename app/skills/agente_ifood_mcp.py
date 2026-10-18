"""Skill do agente: como usar as tools do MCP do iFood (descoberta, carrinho e pedido).

Ensina o modelo a pedir uma tool com um bloco ```mcp_call {...}``` e lista as tools com suas regras
(ordem do carrinho, confirmação antes de submitOrder, nunca inventar IDs).
Ativada pelo nome: ask_llm("...", skills=["ifood_mcp"]).
"""

NOME = """ifood_mcp"""
DESCRICAO = """Como usar as tools do MCP do iFood (descoberta, carrinho, pedido) para montar um pedido saudável."""
CONTEUDO = """Você tem acesso a um MCP do iFood. Para usar uma tool, responda com UM bloco no formato abaixo e nada depois dele; o sistema executa e devolve o resultado.

```mcp_call
{"tool": "searchOffers", "arguments": {"query": "frango grelhado"}}
```

Se não precisar do MCP, responda normalmente em texto, sem bloco.

## Tools

Usuário
- `listAddresses`: endereços salvos. Sempre o primeiro passo em fluxos de entrega.
- `getUser`: perfil do usuário autenticado.
- `createAddress`: salva um endereço novo.

Descoberta
- `searchOffers`: busca por termo descritivo (ex.: "marmita fit").
- `browseOffers`: navega por localização, sem termo.
- `getRecommendations`: ofertas personalizadas.
- `getMerchant`: detalhes do restaurante (cardápio, horários, entrega).
- `getItem`: detalhes do item, customizações e alérgenos.
- `listItemTaxonomy`: categorias por tipo de estabelecimento.

Carrinho (ordem obrigatória)
`createCart` → `addItemToCart` → `getCartDeliveryMethods` → `setCartDelivery` → `listPaymentMethods` → `setCartPayment` → `submitOrder`.
- `updateCartItem` usa `cartItemId`, não `itemId`.
- `setVoucher` exige `code` e `campaignId` vindos de `listVouchers`.
- Outras: `getCart`, `removeItemFromCart`, `removeVoucher`.

Pedido
- `trackOrder`: status e histórico. Respeite `agentHints.pollingStop`.
- `getOrder`: detalhes estáticos do pedido.

## Regras
1. Chame uma tool por vez e espere o resultado antes da próxima.
2. `submitOrder` cobra de verdade: só chame após o usuário confirmar explicitamente o pedido, e envie `userConsent: true`.
3. Não invente IDs. Use apenas IDs devolvidos por tools anteriores.
4. Se uma tool falhar, explique o erro ao usuário em vez de repetir a mesma chamada."""


def exemplo() -> list[tuple[str, str]]:
    from .agente_pedidos import montar_system
    return [("sistema com esta skill", montar_system([(NOME, DESCRICAO, CONTEUDO)]))]
