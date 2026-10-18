# iFood MCP — relatório de leitura integral

Leitura realizada em 17/10/2026. Escopo: documentação pública em português do portal, incluindo os links adicionais do llms.txt fornecido pelo usuário. Foram lidas 44 páginas: 36 localizadas no índice público e oito páginas adicionais acessíveis pelos links do llms.txt. Algumas são apenas páginas de agrupamento. Glossário e Changelog contêm exemplos genéricos, sem conteúdo técnico substantivo. Também foram inspecionadas as quatro imagens referenciadas nos guias.

A leitura incluiu texto, tabelas, parâmetros, exemplos, respostas, tratamento de erros, cartões, FAQs e termos de uso. Não equivale a testar as APIs ou confirmar em produção as afirmações da documentação. As páginas externas de fornecedores e as traduções que repetem o conteúdo em outros idiomas não integram este escopo.

## O que o contrato detalhado oferece

O endpoint de conexão indicado pelo guia de instalação é `https://consumer-mcp.ifood.com.br/marketplace`. Um gateway reúne quatro domínios, com 24 ferramentas documentadas:

| Domínio | Ferramentas |
| --- | --- |
| User — 3 | getUser, listAddresses, createAddress |
| Offer Discovery — 6 | searchOffers, browseOffers, getRecommendations, listItemTaxonomy, getMerchant, getItem |
| Cart — 13 | createCart, getCart, getCartDeliveryMethods, addItemToCart, updateCartItem, removeItemFromCart, removeVoucher, listVouchers, setVoucher, setCartDelivery, setCartPayment, listPaymentMethods, submitOrder |
| Order Tracking — 2 | trackOrder, getOrder |

### Cadastro, permissões e autenticação

O agente é registrado com identificação, callback e links públicos de termos e privacidade. Os três grupos de acesso são dados de usuário, descoberta e criação de pedidos; a seleção é cumulativa. Credenciais e escopos técnicos dependem de aprovação. O Client Secret é exibido uma única vez quando gerado. A conta do desenvolvedor e a conta de teste do consumidor são diferentes.

O guia indexado de implementação descreve Authorization Code com PKCE/S256, validação de state e troca de tokens no backend. Os endpoints indicados são `id.ifood.com.br/authorize`, `id.ifood.com.br/token` e `id.ifood.com.br/revoke`; a entrada mobile usa `app.ifood.com.br/F4X4/authorize`. Tokens são rotacionados na renovação. Solicitar somente os escopos efetivamente liberados ao agente.

Contas de teste têm OTP gerado manualmente no portal, limite de dez por usuário e exclusão após quinze dias. A documentação avisa para não fazer pedidos reais e informa que pagamentos reais feitos em testes não são reembolsados.

### Identidade e endereço

A identidade é injetada pelo gateway; o agente não fornece userId no payload. getUser retorna dados conforme o tier e os escopos. O tier comportamental pode incluir `profileData.userBehaviorDescription`, um resumo em Markdown produzido pelo LCM. O texto pode descrever hábitos, preferências e avaliações; não constitui uma API de comentários individuais.

Em fluxos de entrega, listar endereços antes da descoberta. Um endereço pode ser utilizado informando o usuário; múltiplos exigem escolha ou confirmação da inferência. Sem dados comportamentais, não inferir a preferência. Contagens comportamentais são strings.

createAddress oferece geocodificação seguida de confirmação, ou criação direta quando endereço, complemento e correspondência única permitem. Bairro precisa ser resolvido em campo próprio. candidateId é temporário e serve à confirmação/idempotência; addressId é permanente.

### Descoberta e recomendações

searchOffers recebe conteúdo descritivo; qualificadores de preço, distância e prazo vão em refinements. browseOffers exige merchantType. Há seis verticais documentadas: restaurante, mercado, bebidas, farmácia, pet e shopping. listItemTaxonomy é pública e independente de localização. IDs de taxonomia e tokens de paginação devem vir das respostas.

getRecommendations oferece RECOMMENDED, RECENT_ORDERS, FAVORITE_MERCHANTS, BEST_DEALS e FEATURED_LOCAL. Favoritos e destaques locais aceitam apenas MERCHANT. Os outros modos também podem retornar ITEM. Pedidos recentes podem incluir lastOrderedAt, timesOrdered e lastOrderId. Não há parâmetro para fornecer um algoritmo próprio de ranking.

getMerchant fornece contexto operacional e itens em destaque, sem representar sozinho todo o cardápio. Para navegar itens de um estabelecimento, usar searchOffers/browseOffers com refinements.merchantId. getItem detalha o produto e seus grupos de opções. O contrato mostrado não oferece textos de reviews nem campos estruturados de nutrição/alérgenos.

### Carrinho e checkout

createCart exige merchantId, addressId e pelo menos um item com options; alternativamente, orderId semeia um pedido anterior. A criação não é idempotente. Revisar itens e preços atuais na reordenação.

itemId identifica o catálogo; cartItemId identifica o item dentro daquele carrinho. updateCartItem exige ambos, quantidade e options. O array options é obrigatório mesmo vazio. Remover o último item exclui o carrinho.

Descobrir antes de configurar: getCartDeliveryMethods → setCartDelivery; listPaymentMethods → setCartPayment; listVouchers → setVoucher. paymentMethodId é o identificador retornado, não o enum PIX. Voucher exige code e campaignId do carrinho atual.

Antes do checkout, revisar estado e total com getCart e obter confirmação explícita. submitOrder exige userConsent e pode iniciar pagamento. document é opcional no schema, embora trechos narrativos o descrevam como obrigatório. Não há ferramenta documentada de cancelamento ou reembolso.

### Pós-compra e erros

trackOrder consulta status ao vivo; getOrder fornece detalhes estáticos. Não há ferramenta de listagem geral de pedidos no Order Tracking. Respeitar a cadência indicada e parar quando pollingStop for true. Os quatro campos de agentHints do rastreamento podem vir nulos.

Os erros não têm envelope único: User e Discovery usam errors; Cart usa error e impact/suggestedActions; Order Tracking coloca errorType, code e demais campos na raiz. HTTP de sucesso, isoladamente, não garante operação bem-sucedida. Retry precisa considerar o domínio, o erro e se a entrada foi corrigida.

## Inconsistências e lacunas observadas

| Ponto | Evidência e implicação |
| --- | --- |
| Endpoints | Visão geral exemplifica mcp.ifood.dev/catalog; instalação indica consumer-mcp.ifood.com.br/marketplace. As páginas adicionais usam auth.ifood.com.br e api.ifood.com.br, enquanto o guia indexado usa id.ifood.com.br. Não assumir equivalência. |
| Any2App | Página adicional ensina callback com custom scheme; o guia indexado de jornadas diz que custom schemes não são suportados e orienta HTTPS com Universal/App Links. |
| PKCE e state | Vários exemplos omitem PKCE e geram state com Math.random, apesar do fluxo exigido pelo guia principal. Não copiar esses exemplos literalmente. |
| Tokens no navegador | Páginas adicionais guardam refresh tokens em localStorage/sessionStorage, contrariando suas próprias recomendações de proteção. SessionStorage não possui HttpOnly nem impede acesso por scripts da página. |
| Revogação | Página adicional de tokens usa /logout; guia indexado usa /revoke. |
| Escopos | llms.txt inclui user:read, cart:write e outros nomes que divergem da referência indexada mcp.*. Usar os escopos liberados no cadastro. |
| Homologação | Página adicional descreve fases, prazos e e-mail; página indexada de criação informa que aprovação do agente não gera e-mail. Podem ser etapas diferentes; não prometer prazo ou notificação sem confirmação do portal. |
| Opções de produto | Discovery mostra optionGroups/options, sem demonstrar customizationId; Cart exige uma hierarquia que pode conter customizations. Falta esclarecer o mapeamento completo. |
| Entrega agendada | setCartDelivery pede selectedTimeSlotId, mas Timeslot e os exemplos de descoberta mostram apenas from/to. Falta o identificador no exemplo. |
| Cartão | setCartPayment orienta copiar cardTokenId de listPaymentMethods, mas a referência de PaymentMethod diz que ele é sempre nulo nessa lista. Não há fluxo completo de tokenização documentado. |
| Histórico de rastreamento | moreStatusEvents menciona next_page_token e order_id, mas a tabela de parâmetros expõe somente orderId. |
| Documento | Narrativas chamam CPF/CNPJ/passaporte de obrigatório; schema de submitOrder permite omitir document. |
| Sequenciamento | Caso de uso do Cart inicia Discovery antes de endereço, contrariando a regra de listar endereços primeiro no User MCP. |
| Retry | Há código de exemplo aguardando segundos para SERVICE_UNAVAILABLE no User, embora o texto recomende minutos. Não adotar um retry genérico para todas as chamadas. |
| Métricas | Percentuais de conversão e tempos das páginas adicionais não apresentam método ou fonte; tratá-los como afirmações da documentação, não como resultados comprovados. |
| Exemplos executáveis | Há SDKs e hosts em exemplos sem confirmação operacional, escolhas simuladas e trechos incompletos. Leitura integral não confirma execução. |

## Implicação para o recomendador baseado em reviews

O MCP documenta nota agregada, resumo comportamental e recomendações/pedidos recentes. Não foi localizada uma ferramenta de leitura dos textos das avaliações dos estabelecimentos ou das avaliações individuais escritas pelo usuário. A análise de aspectos desejada exige uma fonte adicional autorizada ou feedback coletado no próprio produto. Um resumo comportamental pode ajudar, mas não substitui acesso às evidências originais.

## Imagens inspecionadas

- Any2App: entrada do cliente → app iFood → consentimento.
- Login web: entrada → telefone → OTP de telefone → OTP de e-mail → consentimento.
- Pending Action: entrada do cliente → app iFood → confirmação numérica → consentimento.
- Seleção de escopos: três grupos de acesso e aviso de seleção em cascata.

## Termos de uso

Foram lidos integralmente, incluindo regras de cadastro, homologação, segurança, privacidade, confidencialidade, propriedade intelectual, terceiros, logs, suspensão e responsabilidades. O texto distingue autorização para sandbox de autorização para produção, exige minimização de acesso/dados, contém obrigações relativas a terceiros e prevê comunicação de incidentes em 24 horas. Este registro descreve o texto publicado; não é validação jurídica da sua aplicabilidade.

## Inventário de páginas lidas

1. [Visão geral](https://mcp-developer.ifood.com.br/pt-BR/docs/guides)
2. [Autenticação](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication)
3. [MCPs](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps)
4. [Primeiros passos](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps)
5. [Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/erros)
6. [Escopos](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/escopos)
7. [Implementação](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementacao)
8. [Introdução](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/introducao)
9. [Jornadas de autenticação](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/jornadas)
10. [User MCP](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account)
11. [Offer Discovery MCP](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery)
12. [Order Tracking](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order)
13. [Cart](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart)
14. [Criar agente](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/agent)
15. [Criar conta](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/account)
16. [Instalar MCP](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/install-mcp)
17. [Criar conta de teste](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/test-account)
18. [Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/erros)
19. [Casos de uso](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/casos-de-uso)
20. [Tools](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/tools)
21. [Introdução](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/introducao)
22. [Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/erros)
23. [Casos de uso](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/casos-de-uso)
24. [Introdução](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/introducao)
25. [Casos de uso](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/casos-de-uso)
26. [Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/erros)
27. [Tools](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/tools)
28. [Introdução](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/introducao)
29. [Tratamento de Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/erros)
30. [Introdução](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/introducao)
31. [Tools](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/tools)
32. [Tools](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/tools)
33. [Casos de Uso](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/casos-de-uso)
34. [Glossário](https://mcp-developer.ifood.com.br/pt-BR/docs/glossary)
35. [Changelog](https://mcp-developer.ifood.com.br/pt-BR/docs/changelog)
36. [Condições Gerais de Uso - MCP Developer Portal iFood](https://mcp-developer.ifood.com.br/pt-BR/docs/terms-of-use)
37. [Métodos de Autenticação](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods) — fora do índice atual; acessível pelo llms.txt.
38. [Autenticação Nativa (Any2App)](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/any2app) — fora do índice atual; acessível pelo llms.txt.
39. [Autenticação Aprovada Remotamente (Pending Action)](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/pending-action) — fora do índice atual; acessível pelo llms.txt.
40. [Autenticação Web (Web Login)](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/web-login) — fora do índice atual; acessível pelo llms.txt.
41. [Implementação](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation) — fora do índice atual; acessível pelo llms.txt.
42. [Tratamento de Erros](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation/error-handling) — fora do índice atual; acessível pelo llms.txt.
43. [Gerenciamento de Tokens](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation/token-management) — fora do índice atual; acessível pelo llms.txt.
44. [Homologação e produção](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/validate-publish) — fora do índice atual; acessível pelo llms.txt.
