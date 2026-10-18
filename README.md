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
