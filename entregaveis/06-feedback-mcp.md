# 06 · Feedback sobre os MCPs do iFood

Equipe "iFood Benefícios" · Hackathon SEMCOMP × iFood 2026

Este documento reúne as dificuldades que encontramos ao construir o Macro sobre o MCP do iFood (`consumer-mcp.ifood.com.br/marketplace`). Cada ponto traz o que aconteceu, o impacto no agente, a evidência (no código ou na documentação) e uma sugestão. A ordem vai do que mais nos custou para o que menos custou.

Fontes: uso real do MCP no modo live (`app/services/ifood_live.py`, `app/services/ifood_mcp.py`) e leitura integral das 44 páginas da documentação em 17/10/2026 (`outputs/ifood-relatorio-leitura.md`).

## Resumo

| # | Dor | Domínio | Impacto |
|---|---|---|---|
| 1 | Sem ambiente seguro para testar o checkout | Cart | Alto |
| 2 | Catálogo sem nutrição, alérgenos e texto de avaliações | Discovery | Alto |
| 3 | Login OAuth difícil de rodar num servidor | Auth | Alto |
| 4 | Um envelope de erro diferente por domínio | Todos | Médio |
| 5 | Busca de itens retorna pouco e sem descrição | Discovery | Médio |
| 6 | `createAddress` faz duas coisas, e não há como editar | User | Médio |
| 7 | Documentação com exemplos que contradizem o contrato | Docs | Médio |

## 1. Sem ambiente seguro para testar o checkout

**O que aconteceu.** A documentação avisa para não fazer pedidos reais com a conta de teste e informa que pagamentos reais feitos em testes não são reembolsados. `submitOrder` pode iniciar um pagamento e não existe ferramenta de cancelamento ou reembolso. Não encontramos um modo sandbox em que o pedido seja aceito sem cobrança.

**Impacto.** Bloqueamos carrinho e checkout no modo live (`READ_TOOLS` em `app/services/ifood_live.py`). O fechamento do pedido roda só no modo de demonstração. O fluxo que o desafio pede, "da escolha do restaurante ao fechamento do carrinho", não pôde ser validado de ponta a ponta contra o iFood.

> ⚠️ Confirmar: o bloqueio foi só escolha da equipe pelo risco de cobrança, ou os escopos de carrinho e pedido também não foram liberados para o agente?

**Sugestão.** Um ambiente de homologação com restaurantes e pagamentos fictícios, ou uma flag `dryRun` em `submitOrder` que valide tudo e devolva o pedido simulado.

## 2. Catálogo sem nutrição, alérgenos e texto de avaliações

**O que aconteceu.** `getItem` traz nome, descrição, preço e grupos de opções. Não traz calorias, macronutrientes, alérgenos nem ingredientes estruturados. Para avaliações, existem a nota agregada (`reviewRating`, `ratingCount`) e o resumo comportamental de `getUser`. Não há leitura dos textos das avaliações.

**Impacto.** O Macro recomenda pratos por objetivo nutricional e aprende com avaliações. Sem esses dados, tivemos de construir:
- uma pipeline que estima macros a partir do nome e da descrição (tabela TACO, LLM e busca na web, em `app/services/nutrition/`), sempre mostrada como estimativa com faixa de incerteza;
- um conjunto de avaliações simuladas (`data/mocks/reviews.json`) e a coleta de avaliações dentro do próprio app.

**Sugestão.** Campos opcionais em `getItem` para informação nutricional e alérgenos declarados pelo restaurante. Uma ferramenta de leitura de avaliações por estabelecimento, mesmo que anonimizada e paginada.

## 3. Login OAuth difícil de rodar num servidor

**O que aconteceu.**
- **Issuer divergente.** O recurso protegido aponta para `https://id.ifood.com.br`, mas os metadados do servidor de login anunciam o issuer `https://id.ifood.com.br/3p`. O SDK oficial do MCP para Python rejeita essa diferença. Tivemos de substituir a validação do SDK para aceitar exatamente esse par (`app/services/ifood_mcp.py`).
- **Renovação de token.** Quando os tokens salvos vencem, o SDK recebe 401 e tenta abrir o navegador para um novo login, sem usar o refresh token. Num backend não há navegador. Tivemos de descobrir o endpoint de token pelos metadados públicos e renovar manualmente antes de cada conexão (`refresh_if_expired`).
- **Endereços divergentes na documentação.** As páginas citam `id.ifood.com.br`, `auth.ifood.com.br` e `api.ifood.com.br`, e falam em revogar por `/revoke` e por `/logout`.

**Impacto.** A autenticação atrasou a primeira chamada útil ao MCP.

> ⚠️ Confirmar: quanto tempo isso custou à equipe.

A solução depende de um ajuste no SDK que pode quebrar em atualizações.

**Sugestão.** Alinhar o `issuer` anunciado com o `authorization_servers` do recurso. Publicar um exemplo oficial de agente server-side (sem navegador) com renovação de token. Manter uma única tabela de endpoints de autenticação.

## 4. Um envelope de erro diferente por domínio

**O que aconteceu.** User e Discovery devolvem `errors`. Cart devolve `error` com `impact` e `suggestedActions`. Order Tracking coloca `errorType` e `code` na raiz. Além disso, o protocolo permite devolver o resultado em `structuredContent` ou como texto JSON em `content`, e a documentação não diz qual esperar. Uma resposta HTTP de sucesso não garante sucesso da operação.

**Impacto.** O adaptador precisa aceitar todos esses formatos (`unpack_result`). Também tratamos campos de texto como `message` e `suggestedAction` como dado, nunca como instrução ao modelo. Fizemos isso para evitar que um texto externo mude o comportamento do agente: mostramos ao usuário só o código do erro.

**Sugestão.** Um envelope único (`success`, `data`, `error: {code, message, retryable}`) em todos os domínios, sempre em `structuredContent`. Separar a orientação para agentes (`suggestedAction`) num campo documentado como texto não confiável.

## 5. Busca de itens retorna pouco e sem descrição

**O que aconteceu.** Buscas por item com `searchOffers` e `onlyOpen` frequentemente vinham vazias para termos comuns.

> ⚠️ Confirmar: termos e horários em que isso aconteceu.

Os resultados também não trazem descrição: para saber a composição de um prato, é preciso um `getItem` por item. Para saber se o restaurante está aberto antes de detalhar, é preciso um `getMerchant`.

**Impacto.** Montamos uma cascata de reserva (`search_many` em `app/services/ifood_live.py`):
1. até 4 consultas em paralelo;
2. busca de restaurantes pelo termo e leitura de até 3 cardápios via `browseOffers`;
3. nova busca incluindo restaurantes fechados, para conseguir dizer "existe, mas está fechado".

Cada recomendação detalhada custa mais duas chamadas. Isso aumenta a latência da conversa.

**Sugestão.** Uma descrição curta opcional nos resultados de `searchOffers`. Uma busca semântica mais tolerante para termos genéricos ("algo leve", "proteico"). Um indicador de quantos itens existem fechados quando `onlyOpen` zera o resultado.

## 6. `createAddress` faz duas coisas, e não há como editar

**O que aconteceu.**
- A mesma ferramenta geocodifica (só com `address`) e grava (com `candidateId`). Uma chamada de consulta e uma de escrita têm o mesmo nome. Por isso a permissão não pode ser dada por ferramenta: tivemos de liberar `createAddress` à parte das ferramentas de leitura.
- O `neighborhood` do candidato pode vir vazio, e a gravação falha com `MISSING_REQUIRED_ADDRESS_FIELDS`. O formulário precisa pedir o bairro sempre.
- Não existem ferramentas para editar ou excluir endereço. Um endereço cadastrado errado pelo agente só pode ser corrigido no app do iFood.

**Sugestão.** Separar `geocodeAddress` (leitura) de `createAddress` (escrita). Adicionar `updateAddress` e `deleteAddress`. Devolver o bairro sempre que a geocodificação o conhecer.

## 7. Documentação com exemplos que contradizem o contrato

Na leitura integral encontramos divergências que fazem um agente gerado a partir dos exemplos falhar:

- **Escopos:** o `llms.txt` usa nomes como `user:read` e `cart:write`, mas a referência usa `mcp.*`.
- **Cartão:** `setCartPayment` manda copiar o `cardTokenId` de `listPaymentMethods`, mas a referência diz que o campo é sempre nulo nessa lista.
- **Entrega agendada:** `setCartDelivery` exige `selectedTimeSlotId`, mas os exemplos de horários só mostram `from` e `to`.
- **Documento:** as narrativas dizem que CPF/CNPJ é obrigatório, mas o schema de `submitOrder` permite omitir `document`.
- **Ordem das chamadas:** o caso de uso do Cart começa pela descoberta, mas o User MCP orienta listar endereços antes.
- **Exemplos de segurança:** vários exemplos omitem PKCE, geram `state` com `Math.random` e guardam refresh token em `localStorage`, contrariando o próprio guia de autenticação.
- **Opções de produto:** Discovery mostra `optionGroups`/`options`, mas o Cart pede `customizations`. Falta o mapeamento entre os dois.

**Impacto.** Para não depender dos exemplos, validamos cada chamada contra o `inputSchema` real devolvido por `tools/list` antes de enviá-la. Se o schema divergir, a chamada é recusada com erro claro.

**Sugestão.** Gerar os exemplos a partir dos schemas publicados e testá-los em CI. Publicar um changelog dos contratos.

## O que funcionou bem

- `tools/list` com `inputSchema` completo nos permitiu validar os argumentos antes de enviar.
- `candidateId` temporário e `addressId` permanente deixam a confirmação do endereço segura e idempotente.
- `refinements` estruturados (`onlyOpen`, `maxItemPrice`, `merchantId`, `sort`) evitam que preço e distância fiquem misturados no texto da busca.
- `listItemTaxonomy` é pública e independente de localização: bom para o agente planejar buscas.
