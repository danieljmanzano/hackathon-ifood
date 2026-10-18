# Macro · Hackathon SEMCOMP × iFood

Aplicação centralizada com frontend em React/TypeScript/Vite e backend em FastAPI, integrando recomendações nutricionais e o ecossistema do iFood via MCP.

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
│   │   ├── endpoints/        # Rotas da API (macro, health)
│   │   └── v1/               # Rotas versionadas
│   ├── schemas/              # Modelos Pydantic (macro, health)
│   ├── services/             # Clientes externos (OpenRouter, iFood MCP, Mock)
│   ├── storage/              # Persistência SQLite local (Database)
│   └── agent/                # Orquestrador de IA e skills
├── frontend/                 # Frontend React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx           # Telas e fluxo do usuário
│   │   ├── api.ts            # Cliente HTTP integrado com o backend
│   │   ├── components.tsx    # Componentes de UI
│   │   ├── types.ts          # Tipos TypeScript
│   │   └── styles.css        # Estilos customizados
├── requirements.txt          # Dependências do backend Python
└── README.md
```

---

## 🧪 Testes

```bash
# Testes do backend
pytest

# Build do frontend
cd frontend && npm run build
```

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

Na interface, abra um prato e expanda **“Já provou?”** para registrar ou atualizar sua avaliação. O histórico aparece em **Preferências → Suas avaliações**. A próxima busca já utiliza a nova nota.

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

`GET /api/profile/tastes` consulta o perfil de gostos da sessão. A interface mostra **Preferências → Gostos aprendidos e salvos**, separando as inferências das preferências informadas. O armazenamento sobrevive a reinícios, mas continua vinculado ao cookie da sessão; ainda não existe identidade de conta para recuperar o perfil em outro navegador.

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

Em **Preferências → Qual é seu objetivo de dieta?**, cadastre ganhar massa muscular, perder peso, manter o peso, desempenho nos treinos ou alimentação equilibrada. É possível acrescentar orientações em texto e metas diárias de proteína, carboidratos e gordura que você já utiliza. A meta diária de calorias continua no campo existente. O perfil é persistido em `diet_plan`; nenhuma meta numérica é criada automaticamente a partir do objetivo.

Em **Meu dia → O que você já comeu hoje?**, registre refeições de casa ou de outros lugares. Calorias e macros são opcionais, relativos à quantidade efetivamente consumida. Descrever “banana e maçã” não gera números nutricionais. Os consumos confirmados dos pedidos são sincronizados com o backend, incluindo quantidade e fração consumida, e os registros antigos do navegador são migrados na primeira abertura da versão atualizada. Evite registrar a mesma refeição nos dois lugares.

O backend considera apenas o dia no fuso `TIMEZONE` (padrão `America/Sao_Paulo`). Registros de ontem continuam salvos, mas não influenciam o contexto de hoje. A soma aplica quantidade e fração dos pedidos; campos ausentes permanecem desconhecidos. A diferença para a meta só é calculada quando todos os registros daquele dia têm o nutriente informado, e sempre se refere ao que está registrado, não a uma garantia de que todas as refeições foram relatadas.

Exemplos de comportamento:

- Objetivo de ganhar massa + registros apenas de frutas: favorece uma refeição mais reforçada, variada e com fontes de proteína.
- Pouca fome ou pré-treino leve explícitos: mantêm a porção menor/leve, mesmo no cenário anterior.
- Proteína registrada já alcançando a meta informada: não presume que seja necessário aumentar a proteína.
- Perder peso ou calorias registradas já alcançando a meta: favorece opções leves, sem recomendar pular refeições nem criar limite de zero calorias para o próximo prato.
- Sem registros: não presume jejum ou ausência de alimentação.

Também é possível escrever **“meu objetivo é ganhar massa muscular, só comi frutas hoje, quero frango até R$ 30”** na busca. O contexto é usado somente nessa busca; os alimentos já consumidos não viram termos da refeição procurada. Para guardar o objetivo e o consumo, use os formulários do perfil e do diário.

O LLM interpreta o contexto quando está disponível; regras locais preservam os principais comportamentos sem ele. O cache da interpretação inclui a data, o objetivo e os registros/totais do dia. Mudanças nesses dados geram uma nova interpretação. `request_intent.diet_context` guarda o contexto usado e os cards explicam como ele influenciou as sugestões. Logs `diet.ready` contêm somente presença de objetivo e contagens, sem descrições dos alimentos ou orientações da dieta.

Endpoints locais: `GET /api/daily-context`, `POST /api/food-diary`, `DELETE /api/food-diary/{id}` e `GET/PUT /api/consumption`. Os dados são isolados pelo perfil da sessão e sobrevivem a reinícios do servidor, mas continuam vinculados ao cookie, sem conta autenticada. Nenhuma ferramenta MCP foi alterada.
