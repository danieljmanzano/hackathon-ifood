# Macro · Interface web

Interface em React, TypeScript e Vite, conectada ao backend FastAPI existente. Todo o conteúdo está em português. Esta entrega é local: nenhum site foi publicado e nenhuma compra real é permitida.

## Executar

Na raiz do repositório, use o ambiente Python do projeto:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

Abra **http://127.0.0.1:5180/**. A porta 5180 foi escolhida porque 5173 e 5174 já estavam ocupadas no ambiente. O Vite encaminha `/api` ao FastAPI na porta 8000, mantendo o cookie de sessão HttpOnly na mesma origem. Para outro backend:

```bash
MACRO_API_URL=http://127.0.0.1:8001 npm run dev
```

O modo padrão do backend é `mock`. O ambiente virtual e as dependências Python já existentes foram preservados. Se necessário, o setup do backend está definido em `backend/requirements.txt` e `.env.example`, na raiz.

```bash
npm run build
```

O comando verifica os tipos e gera `dist/`. Para produção, sirva esses arquivos e encaminhe `/api` ao backend pela mesma origem. Nenhum token do iFood deve ser colocado no frontend.

## Fluxos implementados

- Visão geral com atalhos de busca e inspirações fotográficas identificadas como ilustrativas.
- Barra de conversa fixa em todas as telas e dentro dos diálogos, acima da navegação no celular. O rascunho é mantido ao navegar; Enter envia e Shift + Enter quebra a linha. A barra usa a busca existente do backend e abre os resultados na tela de conversa.
- É possível continuar digitando durante uma consulta, sem perder o novo rascunho ao receber o resultado. Envios ficam bloqueados durante o processamento; confirmar pedidos continua sendo uma ação separada no checkout.
- Sessão, endereço, conversa, recomendações e perfil carregados do backend. Quando existe apenas um endereço, ele é selecionado e informado no cabeçalho.
- Até três recomendações, com preço do prato, motivo, limitações e estados nutricionais explícitos.
- Detalhes do prato com opções obrigatórias e opcionais, limites, quantidades e preço atualizado.
- Carrinho, entrega, pagamento, total e confirmação explícita vinculada à versão do resumo do backend.
- Trocar entrega/pagamento exige atualizar o resumo e confirmar novamente. Editar o prato invalida o resumo no backend.
- Alerta quando entrega e adicionais ultrapassam o orçamento da busca.
- Confirmação de demonstração com identificador retornado pelo backend; comprar nunca registra consumo automaticamente.
- Meu dia com confirmação de 25%, 50%, 75% ou 100% do pedido, feedback opcional, edição e exclusão.
- Registros de dias anteriores continuam disponíveis para edição e exclusão no Meu dia, com data original e informação nutricional preservadas. O resumo diário contabiliza apenas os registros de hoje.
- Preferências, aversões e restrições separadas; orçamento e meta calórica opcionais.
- Layout responsivo, navegação inferior no celular, diálogos nativos com foco, labels, link para pular navegação, foco visível e respeito a movimento reduzido.
- Tratamento de indisponibilidade do servidor, sessão, endereço e busca; operações com bloqueio contra cliques repetidos.

## Limites e próximas integrações

O backend atual possui catálogo e checkout simulados. O modo `live` oferece apenas consultas, depende das credenciais e bloqueia compras reais. A interface respeita esse bloqueio e não inventa pagamentos ou endereços.

A conversa atual usa a busca por termos do backend; não há um LLM conversacional conectado. A pipeline nutricional ainda não está conectada. A interface suporta `pending`, `ready`, `unavailable` e `error`, faixa, base da porção, método, origem e confiança qualitativa. Não apresenta porcentagem de confiança ou macros inventados. Ao personalizar um prato com estimativa, informa que o valor anterior está desatualizado; o recálculo ainda precisa ser integrado.

**Consumo e feedback são locais ao navegador**, na chave `macro:consumption:v1:<session-id>`. O backend ainda não possui esses endpoints. Apenas perfil, sessão e pedido têm persistência no servidor existente. O snapshot nutricional de prato personalizado não reutiliza silenciosamente a estimativa do prato original. Esses registros locais podem ser perdidos ao limpar os dados do navegador e não sincronizam entre dispositivos. O feedback não altera automaticamente o ranking ou os nutrientes.

O backend permite um pedido por sessão. A tela de pedidos mostra esse pedido, sem simular histórico completo, rastreamento ou criação de outra sessão. Voz e metas de proteína/carboidrato/gordura ficam fora desta entrega.

## Organização

- `src/App.tsx`: telas e transições do fluxo, consumindo os endpoints existentes.
- `src/components.tsx`: componentes visuais, cards, diálogos, seleção de quantidade e estados nutricionais.
- `src/ChatBar.tsx`: campo de conversa compartilhado por todas as telas e diálogos, sem bibliotecas adicionais.
- `src/api.ts`: cliente HTTP, timeout, formatação de preços, URLs HTTPS e data local de São Paulo.
- `src/types.ts`: contratos TypeScript correspondentes ao backend.
- `src/storage.ts`: armazenamento e validação dos registros locais de consumo.
- `src/styles.css`: identidade visual, estados, acessibilidade e layouts responsivos.

Manrope para a interface, Sora para títulos e marca, ícones Lucide. As fontes são carregadas do Google Fonts, com fallback local. Fotos ilustrativas são carregadas do Unsplash; uma falha de imagem não bloqueia o pedido.
