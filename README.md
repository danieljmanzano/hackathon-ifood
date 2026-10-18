# Macro · Hackathon SEMCOMP × iFood

Aplicação centralizada com frontend em React/TypeScript/Vite e backend em FastAPI, integrando recomendações nutricionais e o ecossistema do iFood via MCP.

## Experiência centrada no chat

O Macro funciona como um assistente complementar ao iFood. A entrada é a conversa: recomendações, montagem do prato, escolha de entrega e pagamento, revisão do total e confirmação aparecem no próprio chat. As telas de visão geral, Meu dia, restaurantes, cardápios independentes e Meus pedidos foram retiradas, assim como o painel de metas. O endereço de entrega é escolhido no chat: clique no endereço do cabeçalho ou diga **“trocar endereço”** para escolher outro, e **“adicionar endereço”** para cadastrar um novo (no modo live ele é salvo na conta do iFood; no mock, só localmente). O iFood não oferece edição nem exclusão de endereços.

O atalho **Preferências** abre uma configuração compacta na conversa. Você também pode dizer “meu objetivo é ganhar massa e hoje só comi frutas”: o objetivo e o relato ficam salvos para as próximas sugestões. Se a mensagem contiver também um pedido de comida, a busca acontece em seguida, sem duplicar os alimentos registrados. Descrições não geram macros automaticamente.

Para comprar, escolha um prato pelo botão, nome ou número da sugestão. Ajuste complementos e quantidade e diga **“continuar”**. Selecione entrega e pagamento por nome, número ou botão. O pedido só é confirmado pelo botão com o total ou por uma mensagem explícita como **“confirmar pedido”** depois da revisão. “Sim” ou “ok” não finalizam a compra. O checkout continua simulado no modo mock; as restrições existentes para compra real via MCP continuam em vigor.

Depois da confirmação, a avaliação modificada aceita nota opcional, comentário livre e interpretação em segundo plano, com correção de nota e aspectos. Para escrever pelo chat, use **“avaliação: estava gostoso, mas a entrega demorou”**. Para outra refeição, diga **“novo pedido”**; objetivos, contexto alimentar e aprendizado das avaliações são preservados.

---

## 🚀 Como Executar

### 1. Backend (FastAPI)

Na raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Documentação interativa da API: http://127.0.0.1:8000/docs
- Verificação de saúde: http://127.0.0.1:8000/api/health

### 2. Frontend (React + Vite)

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abra **http://127.0.0.1:5180/** no navegador. O Vite encaminha automaticamente as chamadas `/api` para o backend na porta 8000 via proxy.

---

## 📁 Estrutura do Projeto

```
├── app/                      # Backend centralizado
│   ├── main.py               # Ponto de entrada FastAPI (rotas /api e /api/v1)
│   ├── domain.py             # Regras de negócio, ranqueamento e busca
│   ├── core/                 # Configurações (Settings) e tratamento de erros
│   ├── api/
│   │   ├── router.py         # Composição das rotas públicas
│   │   ├── deps.py           # Provedor iFood, sessão e atualização atômica
│   │   ├── endpoints/        # Sessões, endereços, diário, reviews, checkout e busca
│   │   └── v1/               # Rotas versionadas
│   ├── schemas/              # Modelos Pydantic (macro, health)
│   ├── services/             # Clientes externos (OpenRouter, iFood MCP, Mock)
│   ├── storage/              # Persistência SQLite local (Database)
│   └── agent/                # Orquestrador de IA e skills
├── frontend/                 # Frontend React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx           # Conversa e etapas da compra
│   │   ├── chat-presentation.ts # Textos, fases e apresentação da nutrição
│   │   ├── api.ts            # Cliente HTTP integrado com o backend
│   │   ├── components.tsx    # Componentes de UI
│   │   ├── types.ts          # Tipos TypeScript
│   │   └── styles.css        # Estilos customizados
├── requirements.txt          # Dependências do backend Python
├── requirements-dev.txt      # Dependências e ferramentas de desenvolvimento
├── pyproject.toml            # Padrão de estilo e verificação Python
└── README.md
```

---

## 🧪 Testes

```bash
# Testes do backend
pytest

# Build do frontend
cd frontend && npm run build

# Comandos do chat (Node.js 22.6+)
npm test
```

## Padrão de código

O backend segue a organização existente por camadas: `api` recebe e valida requisições,
`services` integra os fluxos e provedores, `schemas` define os contratos e `storage`
cuida da persistência. As rotas são agrupadas por responsabilidade e compartilham as
dependências de sessão e provedor em `app/api/deps.py`. Novas rotas entram em
`app/api/router.py`; a API versionada mantém seu próprio roteador.

Ruff padroniza o Python com indentação de quatro espaços, limite de formatação de
100 caracteres, imports ordenados e verificação de nomes e imports sem uso.
Prettier padroniza o frontend com indentação de dois espaços, aspas duplas e ponto
e vírgula. Componentes React, comandos do chat, apresentação e cliente HTTP ficam
em módulos separados. Os nomes públicos, contratos, textos dos prompts e regras
de negócio devem ser preservados em refatorações.

```bash
# Na raiz do repositório
pip install -r requirements-dev.txt
ruff check app scripts
ruff format --check app scripts

# Para aplicar a formatação Python
ruff format app scripts

# Na pasta frontend, após npm ci
npm run format:check
npm run format
```

O backend ativo fica em `app/`. O plano histórico está em
`outputs/plano-implementacao-macro.md`; os relatórios de documentação e as capturas
da interface permanecem em `outputs/` e `output/`, respectivamente. O notebook
nutricional e seus arquivos de exemplo também são mantidos.

## Mocks para recomendação por reviews

A base em `data/mocks/reviews.json` contém **24 estabelecimentos, 360 reviews e 6 avaliações do usuário `demo-user`**. Todos os dados são fictícios e determinísticos. As notas vão de 1 a 5; preços estão em centavos. Cada review inclui comentário, data, estabelecimento, item, usuário e notas de sabor (`taste`), entrega (`delivery`), custo-benefício (`value_for_money`) e tamanho da porção (`portion_size`). A nota e a contagem de cada estabelecimento são calculadas a partir das reviews da fixture.

Rotas de leitura disponíveis sem sessão, inclusive quando o iFood está no modo live, sob o prefixo explícito `/api/mock`:

- `GET /api/mock/review-dataset`: base completa, incluindo `default_user_id`.
- `GET /api/mock/establishments`: estabelecimentos e notas agregadas.
- `GET /api/mock/establishments/{merchant_id}/reviews`: reviews de um estabelecimento (404 se inexistente).
- `GET /api/mock/users/demo-user/reviews`: histórico do usuário de demonstração. Usuários sem histórico retornam `[]`, permitindo testar o cenário de início sem avaliações.

Em Python, use `from app.services.mock_reviews import review_dataset`. Relacione reviews por `merchant_id`, `item_id` e `user_id`. As avaliações do usuário fazem parte da mesma base de reviews: ao separar treino e validação ou recomendar novos estabelecimentos, exclua essas avaliações ou estabelecimentos conforme seu experimento, para evitar vazamento. Os 24 estabelecimentos e seus 121 itens em `data/mocks/menu.json` integram o catálogo mock, incluindo busca, cardápio, seleção e checkout simulado.

## Recomendação personalizada

`POST /api/search` combina busca e preferências explícitas com as avaliações do usuário da sessão. O motor é determinístico e usa notas gerais, notas por aspecto e sinais extraídos dos comentários por regras locais de português. Os textos não são enviados a um modelo externo. Dezoito restaurantes não têm avaliações do usuário de demonstração, permitindo testar descoberta por afinidade e comunidade.

- A nota mais recente do próprio usuário para o item (ou para o restaurante, quando não avaliou o item) favorece ou reduz sua posição.
- A afinidade por cozinha transfere as avaliações anteriores para restaurantes com cozinhas em comum. Notas acima de 3 são positivas; abaixo de 3 são negativas. Duas avaliações neutras de prior reduzem o peso de históricos pequenos.
- A nota da comunidade exclui as reviews do próprio usuário. Uma média com prior 3,5 e peso 3 reduz a influência de amostras pequenas.
- O sinal adicional é `comunidade + 2 × afinidade + 3 × nota pessoal centrada + afinidade textual + 0,5 × aspectos`, somado à pontuação de busca e preferências. A resposta inclui `review_signal` com componentes e `reasons` com explicações. O score é uma pontuação de ordenação, não uma probabilidade de satisfação.
- Orçamento, indisponibilidade, ingredientes rejeitados e restrições textuais continuam filtrando os candidatos antes do ranqueamento. Até três sugestões priorizam restaurantes distintos; restrições alimentares ainda exigem confirmação com o restaurante.

No modo mock, cada sessão começa com uma cópia do histórico `demo-user`; novas notas substituem a seed do mesmo item. No modo live, somente avaliações locais não simuladas entram no cálculo: ainda não há importação de reviews do iFood nem metadados de cozinha reais, então a afinidade por cozinha fica neutra. Sem histórico relacionado, o motor usa a comunidade; sem reviews, usa a busca e as preferências existentes.

Na interface, avalie pela conversa depois de confirmar o pedido. A interpretação mostra nota e aspectos e permite corrigir o resultado. O histórico continua no backend para personalização, sem uma tela paralela de avaliações.

- `GET /api/reviews/me`: histórico da sessão atual, incluindo seed apenas no modo mock.
- `PUT /api/reviews`: cria ou atualiza a avaliação de um item apresentado na busca, no cardápio, selecionado ou previamente avaliado pela sessão. A identidade vem do cookie, sem aceitar `user_id` enviado pelo cliente.

Exemplo de corpo para `PUT /api/reviews`:

```json
{
  "merchant_id": "demo-cozinha",
  "item_id": "demo-frango",
  "rating": 5,
  "comment": "Frango suculento e boa porção.",
  "aspects": { "taste": 5, "delivery": 4, "value_for_money": 5, "portion_size": 5 }
}
```

As avaliações ficam no SQLite configurado por `DATABASE_PATH`, com uma nota por usuário, modo, restaurante e item. O perfil pertence à sessão do navegador, sem conta autenticada; perder o cookie cria outro histórico. A avaliação local não implica compra verificada. Em mock, as notas dos outros usuários continuam fictícias.

Validação sem serviços externos:

```bash
IFOOD_MODE=mock OPENAI_API_KEY='' .venv/bin/python -m pytest tests -q
cd frontend && npm run build
```


## Pré-processamento e gostos persistidos

Na inicialização, o backend normaliza as reviews locais (e as fixtures em mock), centra as notas e extrai menções a frescor, pouco óleo, porção, entrega e custo-benefício. Regras simples de negação distinguem, por exemplo, “oleoso” de “nada oleoso”. Isso é uma heurística limitada, sem compreensão semântica geral, sarcasmo ou garantia sobre o prato.

A tabela `processed_reviews` guarda o resultado por hash do conteúdo e versão da pipeline. Reviews iguais reutilizam o processamento após reiniciar o servidor; edição de comentário, nota, aspectos ou versão gera outro hash. Caches antigos não participam do ranqueamento se não corresponderem às reviews atuais.

A tabela `user_tastes` guarda preferências, rejeições e restrições explícitas, afinidades por cozinha, aspectos mencionados, pesos de aspectos, contagem de reviews e data de atualização. Cada perfil é separado por usuário e modo. O hash inclui histórico, metadados de cozinha e perfil explícito: mudanças recalculam os gostos. Salvar avaliação ou perfil atualiza esses dados; consultas verificam se estão atuais.

Menções textuais indicam aspectos relevantes, sem inferir alergias nem transformar críticas em restrições. O ranqueamento cruza esses aspectos com elogios/críticas da comunidade e usa as notas estruturadas com maior peso nos aspectos em que o usuário já teve experiências ruins. A explicação distingue observações sobre o restaurante de características garantidas do prato.

`GET /api/profile/tastes` consulta o perfil de gostos da sessão. Esses sinais alimentam as justificativas dos pratos na conversa, separados das preferências explícitas. O armazenamento sobrevive a reinícios, mas continua vinculado ao cookie da sessão; ainda não existe identidade de conta para recuperar o perfil em outro navegador.

A pipeline é local e não altera ferramentas, argumentos ou autenticação do MCP. O adaptador atual não importa textos de reviews do iFood: em live, processamos apenas avaliações locais não simuladas. Os dados fictícios não entram no perfil live.


### Variedade entre buscas

O catálogo mock contém 24 restaurantes, 121 pratos e 360 reviews. O histórico inicial do usuário continua com seis avaliações; 18 restaurantes têm apenas reviews da comunidade. Há pratos de diferentes preços e cozinhas, incluindo mexicana, árabe, tailandesa, nordestina, japonesa, italiana e comida caseira.

A busca prioriza a quantidade de termos específicos encontrados no nome, descrição ou cozinha. Quando há resultados correspondentes, opções sem esses termos ficam fora das sugestões. Pedidos genéricos como “almoço” usam o catálogo completo. A sessão guarda as últimas 18 sugestões e reduz a pontuação dos pratos e restaurantes exibidos recentemente; isso varia as opções sem sorteio. Os filtros de orçamento, restrições e disponibilidade continuam obrigatórios. Em catálogos muito restritos, pratos podem se repetir. O histórico de exposição não altera os gostos aprendidos nem envia novos argumentos ao MCP.


## Interpretação da intenção da mensagem

O backend interpreta expressões em português antes da busca e combina os objetivos com o prato solicitado, orçamento, perfil e reviews. A interpretação usa regras locais, sem depender de chave de IA ou enviar o texto a outro serviço. A resposta de `/api/search` inclui `request_intent` e a interface mostra o entendimento e as justificativas.

| Exemplos | Prioridade |
| --- | --- |
| “muita fome”, “morrendo de fome” | Porções grandes ou para compartilhar |
| “pouca fome”, “não estou com muita fome” | Porções pequenas |
| “algo leve”, “pouco óleo”, “saudável” | Pratos identificados como leves |
| “economizar”, “sem gastar muito” | Faixas de menor preço, preservando variedade |
| “estou com pressa”, “em até 30 minutos” | Prazo de entrega informado |
| “depois do treino”, “proteína” | Pratos com fontes de proteína indicadas, sem inventar macros |
| “comida caseira”, “sabor de casa” | Comida caseira |
| “cheat meal”, “sair da rotina” | Pratos como pizza e hambúrguer |
| “sem carne”, “vegetariano” | Identificação vegetariana no catálogo |
| “para duas pessoas”, “para compartilhar” | Número de pessoas atendidas |

Objetivos podem ser combinados: “muita fome, mas quero algo leve” procura porções grandes com identificação leve. A indicação mais recente de apetite prevalece quando a mensagem é contraditória. Negações conhecidas, como “sem pressa”, não ativam o objetivo contrário. “Até 30 minutos” não é interpretado como orçamento de R$ 30.

Os candidatos passam pelos filtros de disponibilidade, orçamento e ingredientes; em seguida, a ordem considera correspondência com o alimento pedido, atendimento às intenções e pontuação de preferências/reviews com diversidade. Uma intenção pontual não é salva como gosto permanente. As 18 últimas sugestões continuam sendo usadas para variar opções com atendimento semelhante ao pedido.

Os mocks incluem `features` com porção, peso, pessoas atendidas, estilo e prazo máximo de entrega. Esses dados são inteiramente fictícios para a demonstração. Sem metadados de porção/entrega, especialmente em live, a resposta informa a ausência e não inventa quantidades ou prazo. Se não houver opções que atendam a todos os objetivos, a sugestão informa as limitações. O fallback local é limitado às regras implementadas; o LLM interpreta situações mais amplas, mantendo os filtros e a validação no servidor. O contrato MCP permanece igual; apenas o texto de busca é traduzido para termos de comida quando a mensagem contém somente uma intenção.


### Contexto interpretado por LLM

`app/services/llm_meal_intent.py` chama o cliente OpenRouter existente antes da busca. O modelo recebe a mensagem atual e o contrato de saída. Quando existem objetivos de dieta ou registros do dia, recebe também esse contexto: objetivo, orientações informadas, até 12 descrições resumidas de alimentos, metas diárias e totais conhecidos. Não recebe endereço, identidade, cookie ou reviews. Retorna objetivos do catálogo, termos de comida, resumo e inferências em JSON validado pelo Pydantic. Ele não recebe ferramentas para comprar, alterar perfil ou executar ações MCP.

Exemplos: “treinei musculação hoje” pode favorecer uma refeição mais substanciosa com fontes de proteína; “vou treinar em breve” pode favorecer algo leve e menor. O usuário pode corrigir o contexto com preferências explícitas, como “treinei, mas estou com pouca fome”. Essas inferências são hipóteses de preferência para a busca, sem concluir necessidades médicas, calorias ou macros. Não viram gostos permanentes. Sem alimento explícito, palavras de situação não são usadas como nome de prato.

Apetite, orçamento, quantidade de pessoas e prazo extraídos explicitamente pelas regras são preservados. Inferências que contradizem apetite explícito ou negações conhecidas são recusadas e ativam o fallback. A resposta inclui `interpretation_source`, `context_summary`, `inferences`, `inferred_goals` e `fallback_reason` em `request_intent`; a interface mostra o entendimento e as inferências.

Configuração adicional (valores padrão):

```dotenv
INTENT_LLM_ENABLED=true
INTENT_LLM_TIMEOUT_SECONDS=18
```

A seleção usa `OPENROUTER_MODEL` e os fallbacks já configurados. Um identificador de modelo inválido com HTTP 400 agora permite tentar os alternativos; outros erros 400 continuam sendo recusados. O timeout envolve todas as tentativas da interpretação. O cache da interpretação dura cinco minutos, tem limite de 128 entradas em memória e não guarda o ranqueamento: a rotação de pratos continua por busca. Respostas inválidas, timeout e falhas do provedor voltam para regras locais sem interromper a busca. Logs dessa camada não registram mensagens do usuário nem credenciais.

`/api/health` informa `intent_interpretation=llm_configured` quando há configuração; isso não garante que o provedor esteja disponível. O resultado de cada busca informa a fonte realmente utilizada. O frontend permite até 60 segundos na busca para acomodar interpretação, consulta ao catálogo e enriquecimento nutricional. O contrato das ferramentas MCP permanece igual.

## Logs de busca e recomendação

Os eventos ficam no terminal do backend e usam um identificador aleatório por busca. O header **`X-Search-Id`** de `POST /api/search` permite relacionar a resposta com todas as etapas no log. Esse identificador não é o ID do usuário nem o cookie da sessão.

Configure na `.env` e reinicie o backend:

```dotenv
BUSCA_LOG=resumo
```

- `resumo` (padrão): origem da interpretação, objetivos reconhecidos, cache/fallback do LLM, tempo de consulta ao catálogo, quantidade de candidatos/reviews, descartes por motivo, pratos selecionados com pontuação, estados da nutrição e duração total.
- `detalhe`: acrescenta pontuação de cada candidato e motivo de cada descarte.
- `off`: mantém somente falhas e avisos de busca.

Exemplo para iniciar diretamente com detalhes:

```bash
BUSCA_LOG=detalhe .venv/bin/python -m uvicorn app.main:app --port 8000
```

A sequência principal é `search.started → intent.ready → catalog.completed → reviews.ready → ranking.completed → nutrition.prepared → search.completed`. Falhas geram `search.failed` com etapa, classe do erro, status quando disponível e tempo decorrido. Cache da interpretação aparece em `intent.cache_hit`; sua indisponibilidade aparece em `intent.fallback` com motivo (`disabled`, `not_configured`, `timeout`, `invalid_response` ou `unavailable`). Uma falha do LLM que permite fallback não interrompe a busca.

`ranking.completed` registra contagens por motivo de exclusão (`unavailable`, `vegetarian`, `dislike`, `restriction`, `budget`, `search_mismatch`). Para os selecionados, mostra IDs do restaurante/item, posição, relevância, aderência à intenção, pontos por preferências/busca/orçamento/reviews, penalidade de repetição e pontuação resultante. A ordenação continua usando relevância, intenção e pontuação nessa ordem; os logs não alteram as recomendações.

A configuração é independente de `CALORIAS_LOG`. Não são registrados texto integral da mensagem, endereço, identidade/cookie do usuário, conteúdo das reviews ou credenciais. As chamadas de interpretação também omitem conteúdo retornado pelo modelo e corpos de erro do provedor, mesmo em nível detalhado. Os logs existentes da pipeline nutricional continuam sendo controlados separadamente por `CALORIAS_LOG`.

## Preferências nutricionais na busca

Em **Preferências**, salve objetivos como mais proteína, menos carboidratos, menos gordura ou menos calorias. Também é possível informar máximo de kcal, mínimo de proteína e máximos de carboidratos/gordura **por prato**. Esses campos são persistidos em `profile.nutrition_preferences`, junto ao perfil na sessão SQLite. Sessões anteriores recebem valores vazios por padrão.

Na busca, por exemplo: **“frango até R$ 35, até 600 kcal e pelo menos 30 g de proteína”** ou **“quero algo low carb”**. O LLM extrai as preferências em JSON validado; as regras locais reconhecem os exemplos mesmo sem LLM. Valores da mensagem prevalecem sobre os padrões do perfil somente naquela busca; campos estruturados de `MealRequest.nutrition_preferences` prevalecem sobre os extraídos da mensagem. Objetivos qualitativos são combinados. A meta diária de calorias continua sendo usada pelo acompanhamento diário e não é convertida em limite por prato.

A busca consulta os resultados nutricionais já calculados em memória e na base local para todo o catálogo recebido. Depois, estima no máximo **12 candidatos elegíveis** dentro do prazo `NUTRITION_SEARCH_BUDGET_SECONDS` e faz o ranking final dos três pratos. Cálculos pendentes continuam em segundo plano. Os resultados passam a ser aproveitados nas próximas buscas; a atualização dos cards troca os dados e as justificativas sem mudar os pratos durante a leitura.

A adequação nutricional gera um sinal entre 0 e 3, multiplicado por 4 e somado aos pontos de gostos, orçamento, reviews e rotação. Limites numéricos recebem pontuação proporcional à proximidade com o valor pedido, limitada ao atendimento completo. Objetivos qualitativos usam comparações graduais dos valores disponíveis. A relevância do alimento e o atendimento às intenções de porção/estilo continuam sendo critérios anteriores à pontuação; alternativas de restaurantes diferentes continuam sendo priorizadas.

Valores ausentes não contam como zero calorias/macros nem como atendimento da preferência. A resposta explica quais valores estão disponíveis, quais preferências não foram atendidas ou não puderam ser verificadas. São estimativas por prato antes dos adicionais, usadas como preferência de ordenação; não são um filtro rígido nem garantia dos limites. Os logs incluem `nutrition_score`, `nutrition_points` e `nutrition_state` por candidato e `nutrition.ranking` com o tamanho do conjunto comparado. O contrato das ferramentas MCP permanece igual.

## Objetivos de dieta e alimentação do dia

No chat, informe seu objetivo ou use **Preferências → Objetivo de dieta**: ganhar massa muscular, perder peso, manter o peso, desempenho nos treinos ou alimentação equilibrada. As configurações opcionais permitem informar orientações e metas que você já utiliza. O perfil é persistido em `diet_plan`; nenhuma meta numérica é criada automaticamente a partir do objetivo.

Relate na conversa refeições de casa ou de outros lugares: **“hoje só comi banana e maçã”**. O chat salva esse relato, sem estimar números a partir da descrição. Consumos anteriores com calorias e macros continuam sendo considerados pelo backend e os registros antigos do navegador são migrados na primeira abertura. A tela de diário e a confirmação separada de consumo foram removidas. Comprar continua sem significar que o prato foi consumido.

O backend considera apenas o dia no fuso `TIMEZONE` (padrão `America/Sao_Paulo`). Registros de ontem continuam salvos, mas não influenciam o contexto de hoje. A soma aplica quantidade e fração dos pedidos; campos ausentes permanecem desconhecidos. A diferença para a meta só é calculada quando todos os registros daquele dia têm o nutriente informado, e sempre se refere ao que está registrado, não a uma garantia de que todas as refeições foram relatadas.

Exemplos de comportamento:

- Objetivo de ganhar massa + registros apenas de frutas: favorece uma refeição mais reforçada, variada e com fontes de proteína.
- Pouca fome ou pré-treino leve explícitos: mantêm a porção menor/leve, mesmo no cenário anterior.
- Proteína registrada já alcançando a meta informada: não presume que seja necessário aumentar a proteína.
- Perder peso ou calorias registradas já alcançando a meta: favorece opções leves, sem recomendar pular refeições nem criar limite de zero calorias para o próximo prato.
- Sem registros: não presume jejum ou ausência de alimentação.

Escreva **“meu objetivo é ganhar massa muscular, só comi frutas hoje, quero frango até R$ 30”** no chat para salvar o contexto e buscar em uma mensagem. Os alimentos já consumidos não viram termos da refeição procurada. Clientes de `POST /api/search` mantêm o comportamento anterior de contexto temporário; `POST /api/chat` salva objetivos e relatos e distingue `last_chat_action=context` de `search`.

O LLM interpreta o contexto quando está disponível; regras locais preservam os principais comportamentos sem ele. O cache da interpretação inclui a data, o objetivo e os registros/totais do dia. Mudanças nesses dados geram uma nova interpretação. `request_intent.diet_context` guarda o contexto usado e os cards explicam como ele influenciou as sugestões. Logs `diet.ready` contêm somente presença de objetivo e contagens, sem descrições dos alimentos ou orientações da dieta.

Endpoints locais: `GET /api/daily-context`, `POST /api/food-diary`, `DELETE /api/food-diary/{id}` e `GET/PUT /api/consumption`. Os dados são isolados pelo perfil da sessão e sobrevivem a reinícios do servidor, mas continuam vinculados ao cookie, sem conta autenticada. Nenhuma ferramenta MCP foi alterada.

### Catálogo real com reviews de demonstração e nutrição incremental

Configure `IFOOD_MODE=live`, as credenciais MCP e faça o login pelo comando
`python -m app.services.ifood_mcp`. O catálogo usa os produtos devolvidos pelo MCP
para o endereço atual. Não há importação global nem fallback silencioso para
restaurantes fictícios. O checkout real continua bloqueado.

`LIVE_MOCK_REVIEWS=true` permite reviews **simuladas**, estáveis e persistidas,
ligadas aos IDs reais observados. O card identifica a demonstração, e as reviews
não servem como fonte de macros. `false` remove esse overlay da recomendação,
preservando as reviews reais e seu aprendizado. A origem do produto continua real.

Com `CATALOG_ENRICHMENT_ENABLED=true`, a busca responde com o que há no cache e
coloca até `CATALOG_PRODUCTS_PER_SEARCH=3` produtos novos na fila, priorizados pelo
ranking (até dez candidatos para buscas nutricionais). O worker do ciclo de vida
da API usa o agente nutricional existente em modo econômico, uma amostra e até três
estimativas simultâneas por processo. Seleções personalizadas compartilham a mesma
faixa de execução e o mesmo orçamento. Use um processo da API para esse limite de
concorrência global no protótipo.

Produtos observados, fila, leases, tentativas, reviews simuladas e reservas de uso
ficam no SQLite de `DATABASE_PATH`. A nutrição pronta continua em
`CALORIAS_BASE_PATH`. Reinícios retomam tarefas; falhas têm intervalo
`CATALOG_RETRY_SECONDS=900` e no máximo `CATALOG_MAX_ATTEMPTS=2` tentativas.
A cota diária esgotada adia tarefas até o próximo dia UTC, sem gastar tentativas.

Limites padrão do agente nutricional real:

- `CATALOG_PRODUCTS_PER_DAY=20`: produtos/variantes distintos que iniciaram chamadas no dia.
- `CATALOG_CALLS_PER_DAY=60`: requisições de IA, contando erros, retries e fallback.
- `CATALOG_CALLS_PER_PRODUCT=8`: requisições por produto/variante no dia.
- `CATALOG_MAX_OUTPUT_TOKENS=1800`: limite de saída enviado a cada provedor.
- `CATALOG_MAX_INPUT_CHARS=24000`: entradas textuais maiores não são enviadas.

Essas cotas são reservadas atomicamente **antes** do HTTP. Elas limitam volume,
não representam um teto exato em reais: preços por modelo, imagens e ferramentas
internas de busca têm cobrança própria. Intenção do chat e interpretação de
reviews ficam fora desse orçamento nutricional. A busca web respeita
`CALORIAS_BUSCA_WEB`; desligue para evitar seu custo adicional.

O cache é identificado por composição, porção, opções e quantidades de adicionais,
além do produto/restaurante e versão do pipeline. Preço, disponibilidade e URL
temporária da foto não invalidam a nutrição. Alterações de composição geram uma
nova chave; registros antigos não são apresentados como atuais.

A skill [nutrition-enrichment](app/skills/nutrition-enrichment/SKILL.md) é injetada
nas etapas de estimativa quando o agente precisa enriquecer dados sem cache e pode
ser carregada por `load_skill("nutrition_enrichment")`. Ela orienta fontes,
porções, incerteza e insuficiência; cache, orçamento e fila são controles do backend.

Limites numéricos explícitos excluem pratos cujos valores conhecidos os violam.
Dados ausentes aparecem como não verificados; preferências qualitativas afetam a
ordenação. Ao chegar uma estimativa incompatível, o polling remove a opção e
explica quando não sobra nenhuma. Estimativas não são garantias nutricionais.

Inspecione contagens e limites (sem dados pessoais) em
`GET /api/catalog/enrichment/status`.


### Busca nutricional em lotes de três

No modo real, buscas com preferências nutricionais usam um fluxo específico:

1. `searchOffers` retorna páginas de **3 itens**, com os filtros de localização,
   preço, disponibilidade e outros critérios mantidos. A continuação usa somente
   `nextPageToken` devolvido pelo MCP; tokens repetidos encerram a paginação.
2. Os candidatos são priorizados pelos demais critérios (intenção, reviews,
   gostos, preço), sem pontuação nutricional nessa seleção inicial.
3. Os detalhes atuais de cada produto são lidos e até **3 estimativas rodam em
   paralelo**, respeitando `NUTRITION_CONCURRENCY` (limitado a três nesse fluxo).
   Resultados prontos em cache não geram novas chamadas de IA.
4. Só entram nas recomendações resultados suficientes que atendam às restrições.
   Com menos de três aprovados, o motor passa ao próximo lote. Para em **3
   aprovados ou 15 candidatos avaliados**, ou antes por esgotamento do catálogo,
   indisponibilidade do estimador ou limite diário de uso. Pode retornar menos de
   três opções aprovadas. Sem nenhum aprovado, pode oferecer alternativas
   aproximadas com aviso de baixa certeza, preservando limites numéricos.

Preferências qualitativas usam as referências de comparação já adotadas no motor:
mais proteína: >=20 g (referência central 30 g); menos carboidratos: <=65 g
(central 40 g); menos gordura: <=30 g (central 20 g); menos calorias: <=700 kcal
(central 500 kcal), sempre por prato. São critérios internos de seleção, não
metas de dieta atribuídas ao usuário. Limites numéricos explícitos também precisam
ser atendidos. Cada card mantém fonte, confiança e limitações da estimativa.

O fluxo roda em segundo plano para não exceder o timeout HTTP. O chat consulta
`/api/recommendations/nutrition`, recebe `nutrition_search` com contagens/estado e
mostra os aprovados e o progresso. O snapshot do lote fica no SQLite; um reinício
retoma a busca, e uma nova busca impede a anterior de sobrescrever seus resultados.

`CATALOG_PRODUCTS_PER_SEARCH` segue controlando o enriquecimento oportunista de
buscas **sem preferência nutricional**. Nas buscas nutricionais, o limite é de 15
candidatos, em lotes fixos de três. Cotas diárias de produtos e chamadas continuam
valendo e podem interromper a avaliação antes desse máximo. O modo mock mantém o
fluxo de demonstração anterior.


### Preferências subjetivas e alternativas aproximadas

"Bastante" e "pouco" usam as faixas amplas acima, sem converter essas referências
em metas prescritas. Se nenhum candidato for aprovado ao encerrar a busca, são
oferecidas até três alternativas próximas dentre os candidatos já avaliados.
A proximidade usa os nutrientes conhecidos e preserva os demais critérios nos
empates; não é uma probabilidade calibrada. Dados conhecidos têm prioridade sobre
inferências sem macros disponíveis. Não há chamadas extras de IA para esse fallback.

Cards aproximados têm `approximate_match=true` e `match_confidence=low`, aviso
visível e explicação das lacunas; a confiança nutricional original é preservada.
O progresso separa `accepted` (aprovados) de `approximate` (alternativas).
Orçamento, disponibilidade, restrições e limites numéricos continuam sendo
aplicados. Se um limite numérico não puder ser verificado, essa opção não entra
nas alternativas. Com um ou dois aprovados, retornam apenas os aprovados.

### Preferências opcionais e edição explícita pelo chat

O painel Preferências permite definir, por prato, mínimo e máximo de calorias,
proteína, carboidratos e gordura. Todos os limites são opcionais e começam vazios;
o sistema não preenche números a partir do objetivo, treino ou histórico.
Metas diárias continuam separadas dos intervalos por prato. Intervalos com mínimo
maior que máximo são recusados pelo frontend e pelo backend.

O agente pode salvar alterações quando o usuário pedir explicitamente, por exemplo:

- “Salve nas minhas preferências entre 20 e 40 g de proteína e até 600 kcal”.
- “Adicione frango e legumes aos ingredientes que gosto”.
- “Adicione cebola aos ingredientes que prefiro evitar”.
- “Remova meu máximo de proteína”.
- “De agora em diante prefiro evitar cebola”.
- “Meu limite de calorias agora é 600 kcal”.
- “Não quero mais cebola nas minhas preferências”.

“Quero frango até 600 kcal hoje” aplica o limite à busca atual e não muda o perfil.
Perguntas, negativas e pedidos condicionais não autorizam alterações. O comando
pode ser enviado antes de selecionar endereço e durante um pedido; não cria busca,
não altera carrinho e não confirma compra. A resposta confirma a alteração salva.

A skill do agente `user_preferences` em `app/skills/preferencias.py` interpreta o
pedido em operações tipadas quando o LLM está habilitado; comandos comuns de
limites e ingredientes também têm interpretação local. O backend exige evidência
na mensagem, números/unidades explícitos, campos permitidos e validação do perfil
completo antes de persistir. Uma proposta inválida mantém todas as preferências.
O agente também classifica frases naturais relacionadas ao perfil como alteração,
pedido da refeição atual ou dúvida que precisa de esclarecimento. Não é necessário
começar com um verbo específico. Ele recebe as preferências atuais para resolver
remoções; se houver mais de uma categoria possível, pede esclarecimento. Sem LLM,
comandos locais continuam funcionando e frases ambíguas pedem um comando explícito.
Quando o agente pergunta se deve salvar uma preferência, o pedido fica pendente
na sessão. “Sim” ou “pode salvar” confirma esse pedido, e “não” o cancela, sem
disparar busca ou confirmar compra. Enquanto houver uma pergunta pendente, qualquer
resposta sem confirmação afirmativa mantém o perfil intacto e pede “sim” ou “não”.
“Isso”, “talvez” e negativas não contam como consentimento. Uma edição pelo painel
descarta a pendência. O agente de preferências também recebe as seis
mensagens recentes; o histórico ajuda na interpretação, mas não autoriza mudanças
sozinho. As confirmações continuam sujeitas à validação de ingredientes e valores.
Mudanças são gravadas no SQLite da sessão, reaparecem no painel e valem para as
próximas buscas. Campos omitidos e dados de compra são preservados.
