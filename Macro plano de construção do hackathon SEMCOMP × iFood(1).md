# Macro: plano de construção do hackathon SEMCOMP × iFood

O Macro é um agente que pede a refeição que fecha a meta do dia de quem treina. Este plano diz o que construir, onde cada parte vive e como fazê-la, na ordem em que as dependências pedem.

## Visão geral: o que o Macro faz

1. O usuário diz o que quer, por voz ou texto: "acabei de treinar, quero algo com proteína, até R$ 40".
2. O agente cruza a meta que ainda falta no dia, o orçamento e os pratos disponíveis.
3. Ele ranqueia as opções e explica a escolha, com macros em faixa, nível de confiança e o que os reviews dizem.
4. O usuário confirma e o carrinho é montado pelo MCP do iFood.
5. Depois da entrega, o agente pergunta "como foi?". A resposta atualiza o perfil e o consumo do dia.
6. O próximo pedido já usa o que foi aprendido.

## Onde cada coisa vive

O LLM interpreta, lê texto e conversa. O código soma, filtra e decide.

| Camada | O que faz | Onde vive |
| --- | --- | --- |
| Pedido | Buscar restaurantes, ver cardápio, montar carrinho, fechar | MCP do iFood |
| Dados de pratos e reviews | Descrição, imagem, textos de avaliação | MCP; API do iFood onde o MCP não cobre; mock em último caso |
| Estimativa de macros | Faixa + confiança por prato | LLM em pré-processamento, guardada no backend |
| Atributos dos reviews | Porção real, secura, óleo, entrega fria | LLM em pré-processamento, guardada no backend |
| Perfil e registro do dia | Meta, consumo, preferências | Código próprio (mock inicial) |
| Ranking e conta do dia | Quanto cada prato cobre do que falta | Código determinístico, nunca o LLM |
| Conversa e explicação | Entender o pedido e justificar a escolha | Agente (LLM com as tools do MCP) |
| Interface e voz | Chat, cards, barra do dia, fala | Web mobile-first; voz do navegador com fallback em texto |

Sugestão de stack: Python (FastAPI) ou Node no backend, JSON ou SQLite para dados, chaves de API em variáveis de ambiente.

## Ordem de construção

Cada etapa termina com algo que roda, e a seguinte só começa sobre isso.

1. **Fundação.** Acesso ao MCP, tools reais mapeadas, contratos de dados, dados de pratos e reviews (API ou mock), persona e três cenários de demo. Pronta quando a lista de tools está documentada e os dados de exemplo carregam.
2. **Fatia vertical.** Pedido de ponta a ponta em texto, ainda sem inteligência de macros. Pronta quando "descrição → busca → carrinho → confirmação" funciona pelo MCP.
3. **Diferencial.** Macros, reviews, perfil, ranking e explicação. Pronta quando duas pessoas com metas diferentes recebem recomendações diferentes para o mesmo pedido.
4. **Experiência.** Interface final, voz e ciclo de avaliação. Pronta quando a demo roda do começo ao fim por voz, com fallback em texto.
5. **Acabamento.** Medição de erro, documentos, vídeo de backup e ensaio do pitch. Pronta quando os seis entregáveis estão fechados.

## Features: o que, onde, como e quando

### 1. Pedido por conversa via MCP

- **Onde:** agente no backend, falando com o MCP do iFood.
- **Como:** um loop em que o LLM recebe as tools do MCP, decide qual chamar e recebe o resultado, até responder ao usuário. A ação de fechar o pedido exige confirmação explícita. Erros comuns (restaurante fechado, item indisponível) viram uma mensagem clara com alternativa.
- **Quando:** etapa 2.

### 2. Pratos e reviews

- **Onde:** camada de dados do backend.
- **Como:** uma interface única de fonte de dados com três implementações (MCP, API, mock). O resto do sistema só conhece o contrato, então trocar mock por API não quebra nada. O mock é gerado por LLM: 15 a 20 restaurantes, \~20 reviews cada, variando em porção, secura, gordura e entrega.
- **Quando:** etapa 1 com mock; trocar por MCP ou API conforme o acesso permitir.

### 3. Estimativa de macros em camadas

- **Onde:** pré-processamento no backend; o resultado fica guardado junto de cada prato.
- **Como:** hierarquia de confiança. Dado oficial vale mais que estimativa por nome, descrição e ingredientes, e a foto entra só como sinal complementar. O resultado é sempre uma faixa com nível de confiança. Os reviews corrigem a faixa: se vários dizem que a porção vem menor que a anunciada, o valor cai.
- **Quando:** versão só com texto na etapa 3; reviews e foto como refinamento dentro da mesma etapa.

### 4. Análise de reviews

- **Onde:** pré-processamento no backend.
- **Como:** o LLM lê cada review e extrai atributos fixos (porção real vs. anunciada, secura, excesso de óleo ou molho, entrega fria, saciedade) em um formato estruturado. Os atributos são agregados por restaurante e por prato. Rodar antes da demo, nunca ao vivo.
- **Quando:** etapa 3.

### 5. Perfil e registro do dia

- **Onde:** backend.
- **Como:** meta diária (kcal, proteína, carbo, gordura), restrições, consumo do dia e pesos de preferência. Todo pedido confirmado soma na conta do dia. Começar mockado, sem integrar apps externos de nutrição.
- **Quando:** modelo de dados na etapa 1; uso real na etapa 3.

### 6. Ranking e explicação

- **Onde:** código determinístico para decidir; LLM só para redigir a explicação.
- **Como:** o score combina quanto o prato cobre do que falta, o orçamento e os sinais dos reviews, pesados pelo perfil. O agente recebe o resultado com o motivo e apenas o explica, sempre dizendo por que descartou a alternativa.
- **Quando:** etapa 3.

### 7. Exibição honesta dos macros

- **Onde:** regra no backend, visual no frontend.
- **Como:** o destaque é uma categoria relativa à meta ("cobre \~30–40% do que falta de proteína") e o número fica como detalhe. Confiança média mostra faixa larga com rótulo de estimativa. Confiança baixa mostra só a categoria e admite que não conseguiu estimar.
- **Quando:** regra na etapa 3; visual na etapa 4.

### 8. Guardrails

- **Onde:** agente, com validação em código (nunca só no prompt).
- **Como:** o agente não prescreve dieta, recusa metas calóricas abaixo de um piso de segurança, apresenta macros sempre como estimativas e exige confirmação antes de fechar qualquer pedido.
- **Quando:** confirmação na etapa 2; o conjunto completo na etapa 3.

### 9. Interface

- **Onde:** frontend web mobile-first.
- **Como:** chat, card de refeição com categoria e macros, barra do dia ("faltam 65 g de proteína") e um resumo antes de confirmar.
- **Quando:** protótipo com dados falsos na etapa 2; ligada ao backend real na etapa 3; polimento na etapa 4.

### 10. Voz

- **Onde:** frontend e agente.
- **Como:** reconhecimento e síntese de fala do navegador. O texto transcrito entra no mesmo fluxo do chat, ou seja, a voz é só outra entrada. O fallback em texto fica sempre disponível.
- **Quando:** etapa 4.

### 11. Ciclo de avaliação

- **Onde:** agente e perfil.
- **Como:** após o pedido, o agente pergunta "como foi?". O LLM transforma a resposta falada em uma avaliação estruturada, com os mesmos atributos dos reviews. Isso atualiza os pesos do perfil e a nota do restaurante para aquele usuário, e a mudança aparece na tela.
- **Quando:** etapa 4.

### 12. Extra: foto da geladeira e meal prep

- **Onde:** agente com entrada de imagem.
- **Como:** o LLM lista os itens vistos com um nível de confiança por item. Antes de comprar, o agente pede confirmação dos itens incertos ("não tenho certeza se vi uma maçã").
- **Quando:** só depois que a etapa 4 estiver estável.

Ficam só para o pitch, como roadmap: smartwatch, print de vídeo do TikTok e integração com apps de nutrição.

## Entregáveis: quando e de onde sai o conteúdo

| Entregável | Quando | De onde sai o conteúdo |
| --- | --- | --- |
| 01 Proposta de Negócio | Etapa 1 | Persona e problema: apps não mostram macros, a descrição não bate com o prato, o pedido ignora o dia |
| 02 Desenho de Solução | Etapa 1, ajustado na 3 | Seções "Visão geral" e "Onde cada coisa vive" deste doc |
| 03 Racional da Experiência | Etapas 2 e 3 | Decisões de interface, voz e exibição honesta dos macros |
| 04 Interface Visual | Etapas 2 a 4 | A própria interface e capturas de tela |
| 05 Documento Técnico | Rascunho desde a 3, fechado na 5 | Arquitetura, o que é MCP, API ou mock, e a medição de erro |
| 06 Feedback sobre os MCPs | Anotar o tempo todo, fechar na 5 | Arquivo compartilhado com cada dificuldade registrada quando aparece |

## Como validar as estimativas

Na etapa 5, comparar 10 a 15 pratos comuns (arroz, feijão, frango grelhado, salada) com a Tabela TACO e reportar o quanto o agente acerta a categoria e a faixa. Mesmo um resultado imperfeito vale no pitch, porque mostra que o erro é conhecido.

## Regras de engenharia

- Contratos de dados primeiro; depois cada parte avança sem esperar a outra.
- Fatia vertical antes de refinamentos, e o ramo principal sempre roda.
- LLM só onde há linguagem. Somar, filtrar e ranquear é código.
- Pré-processar o que é pesado e guardar em cache as respostas de LLM usadas na demo.
- Pedir à IA testes e dados de exemplo junto com o código.
- Dizer claramente, no documento técnico e no pitch, o que é mock.
- Registrar os problemas do MCP assim que aparecerem.

## Se o escopo apertar

Cortar nesta ordem: foto da geladeira, medição de erro formal (resumir em 5 pratos), voz de saída, atualização do perfil por avaliação falada.

Nunca cortar: pedido via MCP com confirmação, macros com faixa e confiança, reviews influenciando o ranking, os seis entregáveis e o ensaio do pitch.

## Em aberto: confirmar com a organização

- Formato de submissão (plataforma, repositório, PDF).
- Se o MCP retorna a descrição dos pratos; se não, qual API do iFood entrega.
- Se o MCP roda em ambiente de teste ou faz pedidos reais.
- Qual API do iFood fornece os textos de reviews.
