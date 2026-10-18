# 03 · Racional da Experiência

Equipe "iFood Benefícios" · Hackathon SEMCOMP × iFood 2026 · Macro

## Princípios

1. **A conversa é o produto.** A primeira versão tinha várias telas (visão geral, "Meu dia", restaurantes, pedidos, painel de metas). Removemos todas para que a decisão aconteça num só lugar: tudo é feito na conversa, com cartões de ação quando um botão é mais rápido que digitar.
2. **Complementar ao iFood, não substituto.** O Macro usa o endereço, os restaurantes e os pratos do iFood. Ele não recria cadastro, carteira ou histórico. Nosso valor é decidir melhor, não reconstruir o app.
3. **Toda escolha aceita botão ou texto.** Prato, complemento, entrega e pagamento podem ser escolhidos pelo botão, pelo número ("2") ou pelo nome ("rápida"). Se o texto for ambíguo, o Macro pergunta em vez de adivinhar.
4. **Dizer o contexto não compra nada.** "Meu objetivo é ganhar massa" salva o objetivo e responde. Não dispara uma busca que a pessoa não pediu. Se a mesma frase pedir comida, a busca acontece em seguida.

## Confiança

- **Confirmação só explícita.** "Sim", "ok" e "pode ser" não confirmam pedido. Só o botão com o total ou "confirmar pedido" depois da revisão. Também recusamos frases como "não confirmar pedido" ou "confirmar pedido se for barato". Essa regra não passa por modelo de IA: é uma regra fixa no código.
- **Estimativa é estimativa.** Calorias e macros aparecem como faixa, com origem e confiança. Quando não há dado, o card diz "indisponível" em vez de inventar.
- **Todo prato explica o porquê.** Cada sugestão traz até três motivos, como "Você tem pressa: a previsão máxima informada é de 30 minutos" ou "Vale considerar sua experiência anterior: você deu 5/5 para…".
- **Sem resultado, o motivo é específico.** Quando nada sobra, a mensagem diz se é porque está tudo fechado, se nada cabe no orçamento (e qual é o preço mais baixo) ou se os filtros cortaram tudo. Sempre sugere o que mudar.
- **Avaliação corrigível.** O Macro mostra como entendeu o comentário (nota e aspectos), e a pessoa corrige com um toque. A palavra dela vale mais que a do modelo.

## Fluidez

- **Nada trava a conversa.** A nutrição e a interpretação da avaliação rodam em segundo plano e aparecem quando prontas.
- **Até três sugestões, de restaurantes diferentes.** Poucas para decidir rápido, variadas para haver escolha real. A sessão lembra as últimas 18 sugestões para não repetir.
- **"Outra opção", "mais barato", "sem queijo"** funcionam porque o agente lê as últimas mensagens e um resumo da busca anterior.
- **Exemplos para começar.** A conversa vazia oferece frases prontas ("Treinei hoje e estou com muita fome"), que ensinam o que o Macro entende.
- **"Novo pedido" recomeça sem perder nada.** Objetivo, preferências e aprendizado das avaliações continuam.

## Acessibilidade

- A conversa é uma região `aria-live`: leitores de tela anunciam as respostas.
- Navegação completa por teclado, com foco visível e link "Ir para a conversa".
- Layout de uma coluna que funciona a partir de 320 px, sem rolagem horizontal.

