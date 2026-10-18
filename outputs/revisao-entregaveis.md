# Revisão dos entregáveis do Macro

Revisão em 18/10/2026, na branch `codex/clean-code`, sobre a árvore de trabalho
atual, baseada no commit `d00a1fa`. Os documentos submetidos não foram alterados.

## Parecer

Os seis entregáveis estão presentes e cobrem os assuntos pedidos na especificação
local do evento (`index-v2.html:243`). Não há exigência, nesse arquivo, de seis
arquivos separados, de vídeo ou de demo publicada. Reunir 01, 02, 03 e 05 em
`entregaveis/macro.md` atende à organização do conteúdo descrita ali.

O conjunto precisa de revisão antes da submissão: há um endereço de repositório
divergente, cinco anotações de rascunho e descrições técnicas que não correspondem
mais a algumas configurações e fluxos implementados.

## Cobertura dos seis requisitos

| Item | Exigência na especificação local | Evidência encontrada | Resultado |
| --- | --- | --- | --- |
| 01 | Problema escolhido e proposta de valor | `macro.md:20`: três problemas, proposta, benefícios e viabilidade | Presente; falta finalizar a anotação de persona e separar hipóteses de impacto de resultados medidos |
| 02 | Fluxo geral de como o agente resolve o problema | `macro.md:69`, `diagramas/fluxo-solucao.mmd` e PNG correspondente | Presente; falta representar a busca nutricional em lotes e identificar checkout simulado no próprio diagrama |
| 03 | Decisões de UX da interação | `macro.md:105`: conversa, confirmação, estimativas, feedback e acessibilidade | Presente; algumas garantias precisam ser qualificadas |
| 04 | Telas, protótipo ou interface final | `04-interface-visual.md`, 13 capturas existentes e legíveis | Presente; anotação de link opcional ainda em aberto e algumas ações cortadas nas capturas |
| 05 | Arquitetura, uso do MCP e decisões técnicas | `macro.md:138`, diagrama de arquitetura e referências ao código | Presente; corrigir provedores, fallback, reviews live e contagem dos testes |
| 06 | Dificuldades reais com o MCP | `06-feedback-mcp.md`: sete dores, impactos, soluções e sugestões | Presente; três pedidos de confirmação ainda abertos e uma descrição imprecisa do tratamento de erro |

## Correções prioritárias

### 1. Corrigir o endereço do código

`entregaveis/macro.md:16` aponta para `danieljmanzano/hackathon-ifood`.
O remoto Git configurado neste projeto é
`https://github.com/danieljmanzano/hackaton-ifood` — sem o segundo `h` em
`hackaton`. O documento deve apontar para o repositório efetivamente usado.
A acessibilidade pública do repositório não foi testada nesta revisão.

### 2. Finalizar as cinco anotações de rascunho

- `macro.md:30`: incluir a persona da demonstração ou retirar a instrução interna.
  Uma persona hipotética deve ser identificada como tal; não inventar pesquisa.
- `04-interface-visual.md:7`: incluir um link existente ou retirar a anotação.
  Vídeo/demo publicada não aparece como requisito nos seis itens locais.
- `06-feedback-mcp.md:27`: esclarecer se a equipe verificou os escopos de checkout.
- `06-feedback-mcp.md:50`: informar o tempo observado ou retirar o pedido de estimativa.
- `06-feedback-mcp.md:68`: registrar termos e horários dos casos observados ou
  limitar o relato ao que a equipe consegue comprovar.

As últimas três informações são históricas e não podem ser reconstruídas com
segurança apenas a partir do código. Não atribuir uma falha ao servidor quando
a única evidência é uma decisão preventiva da equipe.

### 3. Atualizar o fluxo nutricional e o diagrama

`macro.md:89`, `macro.md:124` e `macro.md:189` descrevem sugestões imediatas com
nutrição chegando depois. Isso descreve parte dos fluxos, mas não todo o modo live.

Em `app/api/endpoints/macro.py:418`, preferências nutricionais ativas, modo live e
enriquecimento habilitado selecionam o fluxo em lotes. A resposta inicial deixa as
recomendações vazias (`:493`) e registra o progresso (`:537`). O serviço
`app/services/nutrition_batch_search.py` avalia lotes de três, busca até três
aprovados e limita a avaliação a 15 candidatos; em certas condições pode retornar
alternativas aproximadas explicitamente sinalizadas.

Incluir esse ramo no texto e nos diagramas editável e PNG. No fluxo de compra,
identificar também que entrega, pagamento e confirmação são simulados no mock;
o checkout live é bloqueado por `app/api/endpoints/checkout.py`. O texto já declara
essa limitação, mas o diagrama isolado não a apresenta.

### 4. Explicar as avaliações simuladas também no live

`macro.md:234` diz que o ranking live usa apenas avaliações feitas no Macro.
Entretanto, `live_mock_reviews` é `True` por padrão em `app/core/config.py:132`.
`app/api/endpoints/macro.py:452` chama `attach_reviews`, que acrescenta avaliações
simuladas aos produtos reais observados. A interface as identifica como simulação.

Atualizar a tabela de modos e as limitações: não há importação dos textos das
reviews do iFood; avaliações locais são usadas e, com `LIVE_MOCK_REVIEWS=true`,
há uma camada adicional de avaliações fictícias. Desligar essa opção remove essa
camada. Não apresentar as reviews simuladas como evidência real da comunidade.

### 5. Corrigir os detalhes técnicos dos modelos e skills

- `macro.md:200` atribui a estimativa por imagem ao Gemini. A função executada,
  `estimar_b`, chama `app.services.openai_client.responder` e identifica a fonte
  como `openai-imagem` (`app/services/nutrition/etapas/estimar.py:134`). Gemini
  continua previsto para a busca web na configuração correspondente; não deve ser
  retirado de toda a arquitetura por causa dessa correção.
- `macro.md:188` promete fallback entre provedores para toda chamada. Esse fallback
  depende de `LLM_FALLBACK`, que é `False` por padrão (`app/core/config.py:70`),
  das chaves e do caminho executado. Distinguir reservas de modelos dentro de um
  provedor, fallback entre provedores e regras locais após falha.
- `macro.md:151` descreve as skills do agente de busca como Markdown. Os prompts
  de busca em `app/skills/` são módulos Python; existe separadamente a skill
  Markdown de enriquecimento nutricional.
- A referência da API em `macro.md:149` pode ser atualizada para `app/api/router.py`,
  `app/api/deps.py` e `app/api/endpoints/`, acompanhando a separação das rotas.

### 6. Atualizar a evidência de qualidade

`macro.md:227` informa 426 testes. A execução atual de
`.venv/bin/python -m pytest tests -q --tb=short` executou **574 testes: 572 passaram
e dois falharam**, em 31,93 segundos. As falhas são as mesmas já observadas antes
da limpeza, relacionadas à captura de logs:

- `tests/test_montagem.py::test_log_da_decisao_explica_se_monta_a_sugestao_ou_busca`
- `tests/test_montagem.py::test_alvo_escolhido_pelo_modelo_vale_mais_que_o_casamento_de_palavras`

Não declarar a suíte integralmente verde. `npm test` passou nos oito testes do
frontend, e `npm run build` também passou.

## Ajustes de precisão e apresentação

- `macro.md:125`: restaurantes diferentes são uma prioridade, não uma garantia.
  `app/domain.py` completa as sugestões pela ordem quando falta variedade.
- `macro.md:206`: o cache pode ser invalidado por composição, porção, opções,
  quantidades e versão. Qualificar “não é recalculado” como reutilização enquanto
  a chave e o resultado forem válidos; falhas e dados alterados podem ser recalculados.
- `06-feedback-mcp.md:60`: `unpack_result` devolve uma mensagem local genérica ao
  usuário; não mostra apenas o código de erro retornado pelo iFood.
- As capturas `04-montar-prato.png`, `05-entrega.png` e `06-revisao.png` mostram a
  jornada, mas não evidenciam todos os controles citados. A montagem escolhida não
  tem grupos de complementos; não há uma captura específica da escolha do
  pagamento, e a confirmação fica abaixo do recorte de revisão. Capturas adicionais
  tornariam a demonstração mais verificável.
- Conversão, rapidez de decisão e frequência de compra são hipóteses de valor;
  a documentação não apresenta medição desses resultados.
- `aria-live`, link para a conversa e estilos de foco existem no código. A alegação
  de navegação completa por teclado e ausência de rolagem horizontal em 320 px
  exige uma validação interativa específica; as capturas existentes não a provam.

## Verificações realizadas

- Leitura dos três documentos de entrega, dos dois Mermaid e da especificação local.
- Inspeção visual das 13 capturas e dos dois diagramas PNG.
- Validação de 20 referências locais e das âncoras internas: nenhuma quebrada.
- Conferência das fixtures: 24 restaurantes, 121 pratos, 360 avaliações e seis
  avaliações do usuário `demo-user`.
- Conferência dos pontos técnicos com o código atual, inclusive lista de
  permissões, validação de schema, localização, confirmação explícita e OAuth.
- Teste local da etapa de geocodificação mock: resposta 200 com candidato fictício.
- Execução da suíte Python, testes do frontend e build.

Não foram feitas chamadas autenticadas ao iFood, compras, novas chamadas pagas de
IA nem validação do portal de submissão. As observações históricas sobre o MCP
foram confrontadas com o relatório e a documentação arquivados no projeto; isso
não equivale a reproduzir os incidentes ou confirmar o contrato externo atual.
