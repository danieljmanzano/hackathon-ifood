# Macro — entrega da interface visual

Implementação local realizada na branch `artur`, preservando o backend, `.gitignore`, arquivos de pesquisa e alterações que já estavam no diretório. Nenhuma compra real, troca de branch, commit ou publicação foi executada.

## Direção visual

Interface de refeições com linguagem próxima de quem treina, sem prescrever dieta. O ponto de partida é a escolha da refeição; o painel do dia fornece contexto sem inventar metas ou nutrientes.

| Elemento | Decisão |
| --- | --- |
| Fundo | `#fafbf9`, branco `#ffffff` |
| Texto principal | `#28352f` |
| Ação principal | Laranja `#f3663b` |
| Destaque de boas-vindas | Pêssego `#fceadf` |
| Apoio | Verde `#4b795d` |
| Tipografia | Sora em títulos e marca; Manrope na interface |
| Desktop | Navegação à esquerda, tarefa ao centro e contexto do dia à direita |
| Celular | Uma coluna, navegação inferior e diálogos de seleção/revisão |
| Imagens | Fotografias ilustrativas, sem representar porção ou nutrientes reais |

A decisão inicial foi reduzir elementos de dashboard sem dados: o painel apresenta traços para nutrientes ausentes, meta opcional e apenas consumo confirmado. Em vez de rankings numéricos fictícios, as recomendações mostram os motivos reais retornados pelo backend.

## Entrega

- Visão geral com busca por texto, sugestões rápidas e inspirações.
- Conversa persistida e até três recomendações consultadas no backend.
- Seleção de endereço, detalhes, complementos, quantidade e subtotal.
- Entrega e pagamento disponíveis, atualização do resumo e confirmação explícita de sua versão.
- Pedido confirmado com identificador retornado pelo servidor.
- Perfil editável, com preferências, aversões, restrições, orçamento e meta calórica opcional.
- Meu dia com confirmação de consumo, fração, feedback, edição e exclusão.
- Estados de conexão, processamento, erro, vazio e nutrição indisponível.
- Foco visível, labels, diálogos nativos, navegação por teclado, redução de movimento e adaptação a telas pequenas.

Código e setup: `frontend/README.md`.

## Validação executada

Build de produção (`npm run build`): verificação estrita de TypeScript, incluindo símbolos e parâmetros não utilizados, e geração dos arquivos estáticos concluídas.

Verificação no Chromium, usando o backend FastAPI existente em modo `mock`:

| Cenário | Resultado observado |
| --- | --- |
| Endereço único | Selecionado e informado no cabeçalho |
| Busca | Retornou três pratos, com preços e limitações |
| Complemento obrigatório ausente | Botão de adicionar bloqueado |
| Frango + purê + legumes | Subtotal de R$ 33,90 |
| Entrega padrão | Total de R$ 39,80 |
| Confirmação antes de marcar a revisão | Botão de confirmar bloqueado |
| Trocar entrega após marcar a revisão | Confirmação removida; exigida nova revisão |
| Entrega expressa | Total de R$ 43,80; aviso de R$ 3,80 acima do orçamento |
| Pedido de demonstração | Identificador `demo-order-…` retornado pelo backend |
| Pedido confirmado antes do consumo | Meu dia continuou com zero registros |
| Confirmar metade do pedido | Um registro de 50%; calorias permaneceram indisponíveis |
| Repetir confirmação de consumo | Continuou com um registro |
| Recarregar página | Perfil, pedido e registro local recuperados |
| Excluir consumo | Meu dia retornou a zero registros |
| Editar perfil | Preferência por grão-de-bico, aversão a carne, orçamento e meta persistidos após reload |
| Nova busca com perfil personalizado | Grão-de-bico passou à primeira posição; carne foi excluída por aversão |
| Falha de rede simulada | Erro visível e texto da busca preservado; nenhuma recomendação falsa |
| 390 px e 320 px | Largura do conteúdo igual à viewport, sem rolagem horizontal |

Capturas em `output/playwright/`:

- `macro-desktop.png`: visão geral em 1440 × 1080.
- `macro-mobile.png`: visão geral em celular, página completa.
- `macro-checkout-mobile.png`: revisão do checkout no celular.
- `macro-recomendacoes.png`: resultados personalizados.

A inspeção visual levou a ajustes no contraste e no tamanho dos textos secundários, na composição da imagem no celular e no acesso ao início pelo logotipo.

## O que continua pendente

Esta entrega implementa a interface e a conecta ao serviço existente; não encerra as etapas de integração real do plano principal.

- Autenticação e validação de contratos do MCP real; o checkout real permanece bloqueado.
- LLM para interpretação de conversa e integração da pipeline nutricional. O fluxo atual usa a busca por termos do backend.
- Endpoints de consumo e feedback. Por enquanto, esses registros ficam somente no navegador, com aviso na tela.
- Recálculo nutricional de opções, sincronização entre dispositivos, histórico completo e novos pedidos na mesma sessão.
- Aprendizado a partir do feedback, rastreamento e voz.

O modo de demonstração não comprova acesso autenticado ao iFood. Estados nutricionais disponíveis são suportados visualmente, mas a pipeline real não foi executada nesta entrega.
