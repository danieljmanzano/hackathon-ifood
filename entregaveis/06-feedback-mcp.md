# 06 · Feedback sobre os MCPs do iFood

Equipe "iFood Benefícios" · Hackathon SEMCOMP × iFood 2026

Este documento reúne as dificuldades que encontramos ao construir o Macro sobre o MCP do iFood (`consumer-mcp.ifood.com.br/marketplace`). Cada ponto traz o que aconteceu, o impacto no agente, a evidência (no código ou na documentação) e uma sugestão. A ordem vai do que mais nos custou para o que menos custou.

Fontes: uso real do MCP no modo live (`app/services/ifood_live.py`, `app/services/ifood_mcp.py`) e leitura integral das 44 páginas da documentação em 17/10/2026 (`outputs/ifood-relatorio-leitura.md`).

## Resumo

| # | Dor | Domínio | Impacto |
|---|---|---|---|
| 1 | Catálogo sem nutrição, alérgenos e texto de avaliações | Discovery | Alto |
| 2 | Busca de itens retorna pouco e sem descrição | Discovery | Médio |
| 3 | `createAddress` faz duas coisas, e não há como editar | User | Médio |

## 1. Catálogo sem nutrição, alérgenos e texto de avaliações

**O que aconteceu.** `getItem` traz nome, descrição, preço e grupos de opções. Não traz calorias, macronutrientes, alérgenos nem ingredientes estruturados. Para avaliações, existem a nota agregada (`reviewRating`, `ratingCount`) e o resumo comportamental de `getUser`. Não há leitura dos textos das avaliações.

**Impacto.** O Macro recomenda pratos por objetivo nutricional e aprende com avaliações. Sem esses dados, tivemos de construir:
- uma pipeline que estima macros a partir do nome e da descrição (tabela TACO, LLM e busca na web, em `app/services/nutrition/`), sempre mostrada como estimativa com faixa de incerteza;
- um conjunto de avaliações simuladas (`data/mocks/reviews.json`) e a coleta de avaliações dentro do próprio app.

**Sugestão.** Campos opcionais em `getItem` para informação nutricional e alérgenos declarados pelo restaurante. Uma ferramenta de leitura de avaliações por estabelecimento, mesmo que anonimizada e paginada.

## 2. Busca de itens retorna pouco e sem descrição

**O que aconteceu.** Buscas por item com `searchOffers` e `onlyOpen` frequentemente vinham vazias para termos comuns.

Os resultados também não trazem descrição: para saber a composição de um prato, é preciso um `getItem` por item. Para saber se o restaurante está aberto antes de detalhar, é preciso um `getMerchant`.

**Impacto.** Montamos uma cascata de reserva (`search_many` em `app/services/ifood_live.py`):
1. até 4 consultas em paralelo;
2. busca de restaurantes pelo termo e leitura de até 3 cardápios via `browseOffers`;
3. nova busca incluindo restaurantes fechados, para conseguir dizer "existe, mas está fechado".

Cada recomendação detalhada custa mais duas chamadas. Isso aumenta a latência da conversa.

**Sugestão.** Uma descrição curta opcional nos resultados de `searchOffers`. Uma busca semântica mais tolerante para termos genéricos ("algo leve", "proteico"). Um indicador de quantos itens existem fechados quando `onlyOpen` zera o resultado.

## 3. `createAddress` faz duas coisas, e não há como editar

**O que aconteceu.**
- A mesma ferramenta geocodifica (só com `address`) e grava (com `candidateId`). Uma chamada de consulta e uma de escrita têm o mesmo nome. Por isso a permissão não pode ser dada por ferramenta: tivemos de liberar `createAddress` à parte das ferramentas de leitura.
- O `neighborhood` do candidato pode vir vazio, e a gravação falha com `MISSING_REQUIRED_ADDRESS_FIELDS`. O formulário precisa pedir o bairro sempre.
- Não existem ferramentas para editar ou excluir endereço. Um endereço cadastrado errado pelo agente só pode ser corrigido no app do iFood.

**Sugestão.** Separar `geocodeAddress` (leitura) de `createAddress` (escrita). Adicionar `updateAddress` e `deleteAddress`. Devolver o bairro sempre que a geocodificação o conhecer.

## O que funcionou bem

- `tools/list` com `inputSchema` completo nos permitiu validar os argumentos antes de enviar.
- `candidateId` temporário e `addressId` permanente deixam a confirmação do endereço segura e idempotente.
- `refinements` estruturados (`onlyOpen`, `maxItemPrice`, `merchantId`, `sort`) evitam que preço e distância fiquem misturados no texto da busca.
- `listItemTaxonomy` é pública e independente de localização: bom para o agente planejar buscas.
