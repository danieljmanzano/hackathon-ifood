# Macro: plano de construção do hackathon SEMCOMP × iFood

Plano para 4 pessoas, \~23h úteis (sáb 13h → dom 12h30), com forte uso de IA para codar.

## Princípios do plano

1. **Contratos primeiro:** com os formatos de dados combinados logo, os quatro trabalham em paralelo sem se bloquear.
2. **Fatia vertical cedo:** um fluxo completo e feio funcionando antes de qualquer refinamento.
3. **Corte planejado:** cada etapa deixa uma demo utilizável, e o time sabe o que cortar se atrasar.

## Divisão em 4 frentes

Cada frente tem um dono, mas todos usam IA para codar e revisam o trabalho uns dos outros.

| Frente | Responsabilidade | Entregáveis que cobre |
| --- | --- | --- |
| **A. Agente e MCP** | Loop do agente, integração com o MCP, guardrails, confirmação antes de fechar pedido | 05 (parte técnica) |
| **B. Dados e IA** | Mock/API de reviews, estimativa de macros com faixa e confiança, extração de atributos dos reviews, ranking | 05 (parte técnica) |
| **C. Interface e voz** | Interface mobile-first, card de refeição, barra de macros do dia, voz com fallback em texto | 04 |
| **D. Produto, qualidade e pitch** | Persona, fluxo, documentos, testes do agente, anotações sobre o MCP, roteiro e ensaio da demo | 01, 02, 03, 06 e pitch |

A pessoa D também é a **testadora oficial**: usa o agente como usuário e abre bugs para os outros. Isso evita que cada um teste só o próprio pedaço.

## Stack sugerida

Adaptem se a organização indicar algo diferente.

- **Backend:** Python com FastAPI, ou Node. Escolham o que a maioria já domina.
- **Frontend:** web mobile-first (React/Next ou algo mais simples). Evitem app nativo.
- **Voz:** comecem pelas APIs do próprio navegador (reconhecimento e síntese de fala), que não exigem conta nem custo. Só troquem por um serviço melhor se sobrar tempo.
- **Dados:** arquivos JSON ou SQLite. Nada de infraestrutura pesada.
- **Chaves de API:** em variáveis de ambiente, nunca no repositório.

## Cronograma

### Fase 0: Alinhamento (sáb 12h30 → 14h30)

**Todos juntos, no começo:**

- Conseguir **acesso ao MCP** e listar as tools reais (o que retorna, em qual formato). Perguntar aos mentores sobre a API de reviews e o ambiente de teste.
- Definir **a persona** do demo (ex.: "Lucas, 24 anos, treina 5x por semana") e **três cenários** de uso.
- Definir os **contratos de dados**, por exemplo:
  - `Prato`: id, nome, descrição, imagem, preço, restaurante.
  - `EstimativaMacros`: faixas de proteína/carbo/gordura/kcal + confiança.
  - `AtributosReview`: porção real vs. anunciada, secura, entrega fria etc.
  - `PerfilUsuario`: meta diária, consumo do dia, preferências.
- Criar o repositório e o esqueleto do projeto, pedindo à IA que gere o esqueleto a partir dos contratos.
- **Decidir o formato de submissão** com a organização.

### Fase 1: Fatia vertical em texto (sáb 14h30 → 19h)

Cada frente constrói sua parte contra os contratos:

- **A:** o loop do agente chama o MCP, busca restaurantes e pratos, monta o carrinho e pede confirmação.
- **B:** gera o mock de reviews (15 a 20 restaurantes, \~20 reviews cada, com variação realista) e a primeira versão da estimativa de macros por descrição. Ranking simples.
- **C:** tela de chat, card de refeição e barra do dia, ainda com dados falsos.
- **D:** escreve os entregáveis 01 (proposta), 02 (desenho de solução) e 03 (racional de UX). Começa o arquivo de **feedback do MCP**, anotando cada dificuldade assim que ela aparece.

**Checkpoint 1 (\~19h):** um pedido de ponta a ponta, em texto e feio, mas funcionando. Se não estiver pronto, cortar a interface e focar em fazer o fluxo rodar.

### Fase 2: O diferencial (sáb 19h → 23h30)

- **B:** extração de atributos dos reviews, perfil de gosto e ranking com macros, meta restante, orçamento e reviews. Indicador de confiança.
- **A:** guardrails (piso calórico, "estimativas, não aconselhamento", confirmação obrigatória), tratamento de erros do MCP, registro do que foi pedido no consumo do dia.
- **C:** liga a interface ao backend real, com a camada de exibição: categoria relativa à meta, número em detalhe.
- **D:** testa os 3 cenários, abre bugs e prepara a **medição de erro** das estimativas (10 a 15 pratos comparados com a Tabela TACO).

**Checkpoint 2 (\~23h30):** demo completa em texto, com macros e reviews influenciando a recomendação.

### Fase 3: Voz e ciclo de avaliação (sáb 23h30 → dom 02h)

- **C e A:** voz de entrada e saída, e o fluxo "como foi?" após a entrega, que atualiza o perfil.
- **B:** atualização do perfil a partir da avaliação falada e ajuste do ranking.
- **D:** começa o primeiro roteiro do pitch.

**Congelamento de funcionalidades (\~02h):** nada novo depois disso.

### Descanso (dom \~02h → 07h)

Dormir em dois turnos para manter alguém acordado. Quem fica acordado faz tarefas de baixo risco: testar, ajustar textos, escrever a documentação. Evitar refatorar de madrugada.

### Fase 4: Acabamento (dom 07h → 10h)

- Corrigir bugs encontrados nos testes.
- Terminar a medição de erro e escrever o **documento técnico (05)**.
- Polir a interface.
- **Gravar um vídeo de backup da demo funcionando.**
- Se (e só se) tudo estiver estável: a foto da geladeira para meal prep.

### Fase 5: Entrega e ensaio (dom 10h → 12h30)

- Fechar os seis entregáveis, incluindo o **feedback do MCP (06)**, a partir das anotações acumuladas.
- Ensaiar o pitch em voz alta, pelo menos duas vezes, com cronômetro.
- Preparar respostas para perguntas previsíveis: precisão dos macros, o que é mock, riscos de saúde, como escalar.
- **Submeter com 30 min de folga.** Problemas de upload costumam aparecer no último minuto.

## Regras de sobrevivência

1. **Se algo travar por mais de 45 minutos**, pedir ajuda aos mentores do iFood ou simplificar. Para o MCP, eles são a melhor fonte.
2. **Cada frente faz commits pequenos e frequentes**, e o ramo principal sempre roda. A integração acontece o tempo todo.
3. **Pedir à IA que gere também testes e dados de exemplo**, não só código, para detectar quebras rapidamente.
4. **Fazer cache das respostas de LLM usadas na demo**, para que ela não dependa de latência ou de queda da API. O mesmo vale para a voz: sempre manter o fallback em texto.
5. **Ser transparente sobre o que é mock** no documento técnico e no pitch.
6. **Registrar os problemas do MCP assim que aparecerem**, em um arquivo compartilhado.

## Plano de corte

Se o tempo apertar, descartar nesta ordem:

1. Foto da geladeira e meal prep.
2. Medição de erro formal (resumir com 5 pratos).
3. Voz de saída (manter só a entrada, ou só texto).
4. Atualização do perfil por avaliação falada (manter só a recomendação pelo perfil inicial).

**Nunca cortar:** pedido via MCP com confirmação, macros com faixa e confiança, reviews influenciando o ranking, os seis entregáveis e o ensaio do pitch.

## Próximos passos possíveis

- Contratos de dados em JSON.
- System prompt do agente com guardrails.
- Gerador de reviews mockados.
- Roteiro do pitch.
