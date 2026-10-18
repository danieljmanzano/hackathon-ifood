# Macro · Interface web

Interface em React, TypeScript e Vite para a conversa, recomendações e montagem de
pedidos. O backend FastAPI ativo está em `app/`, na raiz do repositório.

## Executar

Use Node.js 22.6 ou superior, com npm, e Python 3.11 ou superior para o backend.

Na raiz, instale as dependências Python e configure `.env` conforme o
[README principal](../README.md). Inicie a API:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Para testar com dados fictícios, acrescente `IFOOD_MODE=mock` antes do comando
da API. Isso altera apenas o processo iniciado, sem editar o `.env`. O modo live
usa as credenciais e a configuração salvas no backend.

Mantenha a API em execução. Em outro terminal, a partir da raiz:

```bash
cd frontend
npm ci
npm run dev
```

Abra **http://127.0.0.1:5180/**. O Vite encaminha `/api` ao backend na porta 8000,
mantendo o cookie de sessão na mesma origem. Para usar outra porta do backend:

```bash
MACRO_API_URL=http://127.0.0.1:8001 npm run dev
```

Se aparecer `No module named uvicorn`, instale as dependências com
`.venv/bin/python -m pip install -r requirements.txt` na raiz. Após mover ou
renomear a pasta do projeto, recrie o ambiente virtual no caminho atual e
reinstale as dependências. Veja também a seção de problemas de execução do
[README principal](../README.md#resolvendo-problemas-de-execução).

## Verificar e formatar

```bash
npm test
npm run build
npm run format:check
npm run format
```

Os testes dos comandos do chat exigem Node.js 22.6 ou superior. O build verifica
os tipos e gera `dist/`. Para produção, sirva esses arquivos e encaminhe `/api`
ao backend pela mesma origem. As credenciais dos provedores ficam no backend.

## Organização

- `src/App.tsx`: estado da conversa, ações e acompanhamento dos cálculos.
- `src/chat-flow.ts`: interpretação local dos comandos de compra.
- `src/chat-presentation.ts`: fases, textos e apresentação dos nutrientes.
- `src/Addresses.tsx`: seleção e cadastro de endereços.
- `src/ChatPreferences.tsx`: edição das preferências do perfil.
- `src/Reviews.tsx`: formulário, leitura e correção de avaliações.
- `src/components.tsx`: componentes visuais, seleção do prato e estados nutricionais.
- `src/api.ts`: chamadas HTTP, timeouts, preços e datas.
- `src/types.ts`: contratos correspondentes ao backend.
- `src/storage.ts`: cache local e migração de registros anteriores de consumo.
- `src/styles.css`: estilos, acessibilidade e layouts responsivos.

O Prettier define a formatação em `.prettierrc.json`. Componentes usam PascalCase;
funções e variáveis usam camelCase. Os campos dos contratos preservam os nomes
enviados pela API.

## Comportamento

O fluxo parte da conversa e inclui endereço, preferências, recomendações,
personalização do prato, entrega, pagamento, revisão e confirmação explícita.
A nutrição e a interpretação de avaliações podem terminar em segundo plano.
O diário e as avaliações persistem no backend; o cache local de consumo permite
migrar registros de versões anteriores.

O modo mock usa dados fictícios e checkout simulado. No modo live, as consultas e
o cadastro de endereço usam o iFood MCP, e a compra real continua bloqueada.
Estados de nutrição indisponível ou pendente aparecem sem inventar valores.
Veja os detalhes de configuração, limites e integrações no README principal.
