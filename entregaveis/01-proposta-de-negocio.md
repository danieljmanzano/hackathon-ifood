# 01 · Proposta de Negócio

Equipe "iFood Benefícios" · Hackathon SEMCOMP × iFood 2026 · Macro

## O problema

Quem tem um objetivo com a alimentação (ganhar massa, emagrecer, comer melhor depois do treino) também pede delivery. Na hora de pedir, essa pessoa enfrenta três dificuldades:

1. **O cardápio não diz o que importa para ela.** O iFood mostra nome, foto, descrição e preço. Calorias e proteína quase nunca aparecem. A pessoa estima de cabeça ou desiste do delivery.
2. **Decidir cansa.** Ela precisa cruzar o que já comeu no dia, o objetivo, a fome do momento, o orçamento e o que está aberto. Rolar o app fazendo essa conta mental leva tempo e termina, muitas vezes, no pedido de sempre.
3. **As avaliações não respondem à pergunta dela.** Uma nota 4,6 não diz se a porção é grande, se o frango é seco ou se a comida chega fria. Isso está espalhado em comentários que ninguém lê antes de pedir.

> ⚠️ Equipe: incluir aqui a persona do demo (ex.: "Lucas, 24 anos, treina 5x por semana") e, se houver, algum dado ou relato que sustente o problema.

## A proposta

O **Macro** é um agente de conversa que funciona como complemento do iFood. A pessoa conta, do jeito dela, como está:

> "Treinei hoje, estou com muita fome e só comi frutas. Quero algo até R$ 35."

O Macro entende o objetivo, a fome, o orçamento e o que já foi consumido. Ele busca pratos reais abertos perto do endereço, pelo MCP do iFood. Depois sugere até três opções e explica cada escolha:
- a **estimativa de calorias e macros**, com faixa e nível de confiança;
- o que **as avaliações** dizem sobre porção, sabor e entrega;
- **por que** aquele prato combina com o pedido.

A pessoa escolhe, monta o prato, revisa o total e confirma, tudo na conversa. Depois da entrega, avalia com um comentário livre, e o Macro aprende com isso para as próximas sugestões.

## Proposta de valor

| Para quem pede | Para o iFood e os restaurantes |
|---|---|
| Decide mais rápido, sem conta mental | Mais conversão de quem hoje desiste por não saber o que pedir |
| Vê calorias e macros estimados, sem precisar procurar | Um público com objetivo de saúde, que pede com frequência |
| Recebe sugestões que respeitam restrições e aversões | Avaliações mais ricas (aspectos estruturados, não só nota) |
| Entende o porquê de cada sugestão | Pratos bons, mas pouco descobertos, ganham visibilidade |

## Diferenciais

- **Nutrição como estimativa honesta.** Os números vêm de uma pipeline com tabela TACO, busca na web e modelos de IA. Sempre aparecem como faixa e com nível de confiança, nunca como verdade.
- **Avaliações como sinal, não só nota.** Comentários viram aspectos (porção, oleosidade, entrega, custo-benefício) que influenciam o ranking e as justificativas.
- **A conversa é a interface.** Contexto, escolha, ajustes, pagamento e avaliação acontecem num só lugar.
- **Segurança por desenho.** O agente nunca confirma um pedido sozinho. "Sim" ou "ok" não finalizam a compra.

## Viabilidade

- Funciona sobre o MCP do iFood que já existe: busca, cardápio, detalhes do item e endereços.
- A estimativa nutricional usa fontes públicas (TACO) e modelos gratuitos ou baratos. Em produção, ela seria calculada uma vez, quando o restaurante cadastra o prato, e não a cada acesso (ver [Documento Técnico Resumido](05-documento-tecnico-resumido.md)).
- Os pontos que dependem do iFood para produção estão no entregável 06: checkout sem cobrança para testes, dados nutricionais declarados e leitura de avaliações.

