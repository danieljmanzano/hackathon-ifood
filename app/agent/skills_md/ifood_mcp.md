---
name: ifood_mcp
description: Como usar as tools do MCP do iFood (descoberta, carrinho, pedido) para montar um pedido saudável.
---
Você tem acesso a um MCP do iFood. Para usar uma tool, responda com UM bloco no formato abaixo e nada depois dele; o sistema executa e devolve o resultado.

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
4. Se uma tool falhar, explique o erro ao usuário em vez de repetir a mesma chamada.
