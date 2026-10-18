# Documentação iFood MCP — extração dos guias

Data: 17/10/2026. Conteúdo obtido dos dados públicos das páginas do portal. Extração de texto, cartões, FAQs e exemplos. Os quatro diagramas/imagens foram inspecionados na leitura; descrição registrada no relatório de leitura.

## Visão geral — Visão geral

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides

Bem-vindo ao iFood MCP
Developer Portal
Permite que LLMs cuidem de buscas, carrinhos, pagamentos e entregas de forma autônoma e conversacional.
Comece em 5 min
Ver referência de MCPs

OAuth 2.1 com escopos
Plug-and-play em SDK e MCP
4 servidores compostos

Tudo o que seu agente precisa, exposto como tools.
Sessão
Carrinho
Busca
Restaurantes
Cardápios
Entregas
Notificações
Pagamento
Status

## Casos de uso de quem já está construindo

Assistente pessoal

**"Alexa, pede almoço para a equipe de engenharia."**

Agentes de uso doméstico que entendem contexto familiar, preferências e horários — e fecham o pedido sem fricção.

Automação corporativa

**"Agende o almoço da equipe toda segunda às 12h."**

Fluxos corporativos que repetem pedidos, respeitam políticas da empresa e integram com calendários.

Concierge empresarial

**"Peça o jantar do escritório com o budget do time."**

Assistentes que conhecem limites de gasto, preferências do time e fecham pedidos em nome da empresa.

Acessibilidade por voz

**"Quero uma marmita sem glúten perto de mim."**

Interfaces por voz que tornam pedidos acessíveis, com confirmação clara antes de finalizar.

Do zero ao primeiro pedido autônomo
Crie sua conta de desenvolvedor
Acesso ao sandbox em segundos.
Registre seu agente
Obtenha credenciais OAuth 2.1 com escopos.
Conecte ao MCP server
Apontamento HTTPS direto, sem proxy.
Faça seu primeiro pedido
End-to-end em ambiente de homologação.

```
// 1. Instale o SDK MCP
npm install @ifood/mcp-sdk

// 2. Conecte ao MCP server de Catálogo
import { connect } from "@ifood/mcp-sdk";
const catalog = await connect("https://mcp.ifood.dev/catalog");

// 3. Sua LLM já pode buscar pratos
await catalog.search({ query: "pizza marguerita perto de mim" });
```

Assine o MCP do iFood e delivery direto hoje
Construa o próximo agente que pede comida de verdade.
Criar conta de desenvolvedor

---

## Autenticação — /authentication

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication

# Autenticação

---

## MCPs — /mcps

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps

# Model Context Protocol APIs

Referência técnica completa das MCPs do iFood. Cada MCP expõe um conjunto de tools para seu agente realizar operações autonomamente.

## MCPs disponíveis

User MCP

Gerenciar dados de usuário, endereços de entrega e preferências pessoais.

Offer Discovery MCP

Buscar e descobrir restaurantes e itens, navegar por categoria, ver detalhes e customizações.

Cart MCP

Adicionar itens, modificar quantidade e gerenciar carrinho.

Order MCP

Criar pedidos, rastrear entregas e consultar histórico.

---

## Primeiros passos — /first-steps

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps

# Primeiros passos

Em 4 passos simples, você estará pronto para criar e testar seu primeiro agente.

Criar conta

Crie sua conta no MCP Portal

Instalar MCP

Configure seu MCP localmente e prepare o ambiente

Registrar agente

Crie e registre seu agente na plataforma

Criar conta de teste

Crie uma conta de teste para validar sua integração sem telefone real

---

## Erros — /authentication/erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/erros

# Erros

Erros de autenticação podem ocorrer em 3 pontos do fluxo. Cada um tem formato e estratégia de recuperação diferentes.

## Formato de erro

Todas as respostas de erro seguem o mesmo formato:

| Campo | Obrigatório | Descrição |
| --- | --- | --- |
| `error` | Sim | Código de erro padronizado |
| `error_description` | Não | Descrição do erro em linguagem natural |
| `error_uri` | Não | URI com documentação adicional sobre o erro |


## Erros ao redirecionar o usuário

Erros que ocorrem durante o redirecionamento para o fluxo de autorização são retornados via **query string** no `redirect_uri`.

**Exemplo:**

```
GET https://seu-app.example/callback?
  error=invalid_scope
  &error_description=The+requested+scope+is+invalid%2C+unknown%2C+or+malformed.
  &state=abcd1234
```

Erros que não redirecionam
Se o client_id não for informado ou for desconhecido, ou se o redirect_uri não for informado, estiver malformado ou não corresponder aos endereços registrados, o iFood informa o erro diretamente ao usuário e não redireciona de volta ao seu aplicativo.

### Tabela de erros

| Erro | Descrição | Solução |
| --- | --- | --- |
| `invalid_request` | Faltam parâmetros obrigatórios, valor inválido, parâmetro duplicado ou requisição malformada | Revise os parâmetros fornecidos. Garanta que não haja duplicatas. |
| `unauthorized_client` | O cliente não está autorizado a usar este `response_type` | Revise o `response_type` fornecido. Verifique a configuração do seu cliente OAuth. |
| `unsupported_response_type` | O servidor não suporta este `response_type` globalmente | Use `response_type=code`. |
| `invalid_scope` | Escopo inválido, desconhecido, malformado ou excede o permitido | Revise o `scope` fornecido. Verifique a configuração do seu cliente OAuth. |
| `access_denied` | O usuário recusou o consentimento ou a política do servidor rejeitou a requisição | Informe ao usuário que não é possível prosseguir sem autorização. |
| `server_error` | Erro interno inesperado do servidor de autorização | Use backoff exponencial e tente novamente. |
| `temporarily_unavailable` | Servidor indisponível por sobrecarga ou manutenção | Use backoff exponencial e tente novamente. |


## Erros ao obter ou renovar tokens

Erros que ocorrem durante a obtenção ou renovação de tokens são retornados diretamente no **corpo da resposta**, em formato JSON.

**Exemplo:**

```
{
  "error": "invalid_request",
  "error_description": "The request is missing a required parameter, includes an invalid parameter value, includes a parameter more than once, or is otherwise malformed."
}
```

### Tabela de erros

| Erro | HTTP | Descrição | Solução |
| --- | --- | --- | --- |
| `invalid_request` | 400 | Faltam parâmetros obrigatórios, valor inválido, parâmetro duplicado ou requisição malformada | Revise os parâmetros fornecidos. Garanta que não haja duplicatas. |
| `invalid_client` | 401 | Cliente desconhecido, sem autenticação ou método não suportado | Revise o `client_id` e `client_secret` informados. |
| `invalid_grant` | 400 | O authorization code ou refresh token é inválido, está expirado, já foi usado, foi revogado, não corresponde ao `redirect_uri` ou foi emitido para outro cliente | Obtenha um novo código de autorização e repita o fluxo. Garanta que o `redirect_uri` seja idêntico ao usado na requisição de autorização. |
| `unauthorized_client` | 400 | O cliente não está autorizado a usar este `grant_type` | Revise o `grant_type` fornecido. Verifique a configuração do seu cliente OAuth. |
| `unsupported_grant_type` | 400 | O servidor não suporta este `grant_type` globalmente | Use `authorization_code` ou `refresh_token`. |
| `invalid_scope` | 400 | Escopo inválido, desconhecido, malformado ou excede o concedido na requisição de autorização | Use exatamente os escopos aprovados na requisição de autorização. Não solicite escopos adicionais. |


HTTP 401 vs 400
O erro invalid_client retorna HTTP 401 (Unauthorized) e pode incluir o header WWW-Authenticate. Os demais erros retornam HTTP 400 (Bad Request).

## Erros ao revogar tokens

Erros que ocorrem durante a revogação de tokens são retornados diretamente no **corpo da resposta**, em formato JSON.

**Exemplo:**

```
{
  "error": "invalid_request",
  "error_description": "The request is missing a required parameter, includes an invalid parameter value, includes a parameter more than once, or is otherwise malformed."
}
```

### Tabela de erros

| Erro | HTTP | Descrição | Solução |
| --- | --- | --- | --- |
| `invalid_request` | 400 | Faltam parâmetros obrigatórios, valor inválido, parâmetro duplicado ou requisição malformada | Revise os parâmetros fornecidos. Garanta que não haja duplicatas. |
| `invalid_client` | 401 | Cliente desconhecido, sem autenticação ou método não suportado | Revise o `client_id` e `client_secret` informados. |
| `unsupported_token_type` | 400 | O servidor não suporta revogação do tipo de token informado | Revise o `token` ou `token_type_hint` informados. |


## Estratégia de retry

Para erros temporários (`server_error`, `temporarily_unavailable`), use backoff exponencial. Para erros permanentes (`invalid_client`, `unauthorized_client`), não faça retry — corrija a configuração primeiro. O número de tentativas fica a seu critério — o exemplo abaixo usa 3.

```
// Número de tentativas é configurável — 3 é apenas um exemplo.
async function retryWithBackoff(fn, maxAttempts = 3) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const errorCode = error.response?.data?.error;

      // Erros permanentes: não retentar
      const permanent = ['invalid_client', 'unauthorized_client', 'unsupported_token_type'];
      if (permanent.includes(errorCode)) {
        throw error;
      }

      // Erros temporários: backoff exponencial
      if (attempt < maxAttempts) {
        const delay = Math.pow(2, attempt) * 1000; // 2s, 4s, 8s
        console.warn(`Tentativa ${attempt}/${maxAttempts} falhou (${errorCode}). Retry em ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
}
```

## Matriz de decisão

```
Recebeu erro?
│
├─ O erro veio na query string? (redirect)
│  └─ Valide os parâmetros da requisição de autorização
│
├─ O erro veio no corpo JSON? (token / revoke)
│  ├─ invalid_client (HTTP 401) → client_id ou client_secret incorreto
│  ├─ invalid_grant → código expirou, redirecione para novo login
│  ├─ invalid_request → revise os parâmetros enviados
│  └─ server_error / temporarily_unavailable → retry com backoff
│
└─ O erro é permanente?
   ├─ Sim (invalid_client, unauthorized_client, unsupported_*) → corrija a configuração
   └─ Não (server_error, temporarily_unavailable) → retry com backoff
```

---

## Escopos — /authentication/escopos

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/escopos

# Escopos

Escopos definem quais dados seu agente pode acessar. Todos os escopos dos MCPs seguem o prefixo `mcp.*` e controlam o acesso a dados de usuário, descoberta e pedidos.

O acesso aos dados ocorre em duas etapas:

- Na criação do agente, você seleciona os **escopos de acesso** desejados.
- Após a homologação, você recebe os **escopos técnicos** liberados para aquele agente. São esses escopos que você usa nas requisições.

## Escopos de acesso (na criação do agente)

| Escopo de acesso | O que permite |
| --- | --- |
| **Dados de usuário** | Identificar o usuário, obter dados básicos de perfil e gerenciar dados de endereço. |
| **Descoberta de conteúdo** | Acessar feeds de restaurantes, recomendações de cardápios, busca de itens e avaliações de estabelecimento. |
| **Criação de pedidos** | Gerenciar o carrinho do usuário, efetuar pagamentos simulados e acompanhar o status de entrega do pedido. |


Seleção em cascata
Permissões avançadas incluem automaticamente as anteriores. Por exemplo, Descoberta de conteúdo ativa Dados de usuário, e Criação de pedidos ativa todas as opções.

## Escopos técnicos (após a homologação)

Após a homologação, o portal lista os escopos técnicos liberados para o seu agente, agrupados por escopo de acesso:

### `mcp.user` — Dados de usuário

| Escopo | Descrição |
| --- | --- |
| `mcp.user.basic.read` | Dados básicos do usuário: nome, e-mail e telefone |
| `mcp.user.advanced.read` | Dados avançados do usuário: CPF/CNPJ |
| `mcp.user.addresses.read` | Consulta de endereços salvos |
| `mcp.user.behavior.read` | Dados comportamentais do usuário |
| `mcp.user.addresses.write` | Criação de endereços |


### `mcp.discovery` — Descoberta de conteúdo

| Escopo | Descrição |
| --- | --- |
| `mcp.discovery.search.read` | Busca textual por merchants e itens |
| `mcp.discovery.browse.read` | Navegação por catálogo e taxonomia de merchants e itens |
| `mcp.discovery.recommendation.read` | Listas curadas (recomendados, favoritos, pedidos recentes, ofertas) |
| `mcp.discovery.details.read` | Detalhe operacional de um merchant ou item específico |


### `mcp.cart` — Criação de pedidos

| Escopo | Descrição |
| --- | --- |
| `mcp.cart.read` | Leitura do carrinho de compras |
| `mcp.cart.write` | Criação e modificação do carrinho |
| `mcp.cart.checkout` | Finalização do pedido |
| `mcp.cart.payment` | Consulta de meios de pagamento |
| `mcp.orders.read` | Consulta de pedidos e status |


## Exemplo de requisição

Um agente homologado com acesso aos três escopos de acesso informa, no parâmetro `scope`, todos os escopos técnicos liberados para ele:

```
scope=mcp.user.basic.read mcp.user.advanced.read mcp.user.addresses.read mcp.user.behavior.read mcp.user.addresses.write mcp.discovery.search.read mcp.discovery.browse.read mcp.discovery.recommendation.read mcp.discovery.details.read mcp.cart.read mcp.cart.write mcp.cart.checkout mcp.cart.payment mcp.orders.read
```

Use somente os escopos liberados para o seu agente
Você não escolhe escopos técnicos individualmente. Solicitar um escopo não liberado retorna invalid_scope.

## Boas práticas

- Solicite o mínimo: na criação, peça apenas os escopos de acesso necessários.
- Use os escopos liberados: na requisição, use somente os escopos técnicos liberados para o agente.
- Verifique a aprovação: valide quais escopos foram concedidos antes de chamar os MCPs.
- Respeite a revogação: se o usuário revogar um escopo, não tente usá-lo.

---

## Implementação — /authentication/implementacao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementacao

# Implementação

O fluxo de autenticação é **agnóstico de linguagem** — os passos abaixo funcionam em qualquer stack. Os exemplos de código estão em cURL, JavaScript, Python, Java e Go.

## Passo 1: Solicite autorização

Gere os parâmetros PKCE e redirecione o usuário.

**Gere o `code_verifier` e o `code_challenge`:**

JavaScript

```
const crypto = require('crypto');

// String criptograficamente aleatória (32 bytes)
const codeVerifier = crypto.randomBytes(32).toString('base64url');

// SHA256 + base64url
const codeChallenge = crypto
  .createHash('sha256')
  .update(codeVerifier)
  .digest('base64url');
```

Python

```
import base64
import hashlib
import secrets

# String criptograficamente aleatória
code_verifier = secrets.token_urlsafe(32)

# SHA256 + base64url
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
```

Java

```
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

// String criptograficamente aleatória (32 bytes)
byte[] verifierBytes = new byte[32];
new SecureRandom().nextBytes(verifierBytes);
String codeVerifier = Base64.getUrlEncoder()
    .withoutPadding()
    .encodeToString(verifierBytes);

// SHA256 + base64url
MessageDigest digest = MessageDigest.getInstance("SHA-256");
byte[] challengeBytes = digest.digest(codeVerifier.getBytes(StandardCharsets.US_ASCII));
String codeChallenge = Base64.getUrlEncoder()
    .withoutPadding()
    .encodeToString(challengeBytes);
```

Go

```
import (
    "crypto/rand"
    "crypto/sha256"
    "encoding/base64"
)

// String criptograficamente aleatória (32 bytes)
verifierBytes := make([]byte, 32)
rand.Read(verifierBytes)
codeVerifier := base64.RawURLEncoding.EncodeToString(verifierBytes)

// SHA256 + base64url
hash := sha256.Sum256([]byte(codeVerifier))
codeChallenge := base64.RawURLEncoding.EncodeToString(hash[:])
```

**Redirecione o usuário:**

```
GET https://app.ifood.com.br/F4X4/authorize?
  response_type=code
  &client_id=seu-client-id
  &redirect_uri=https://seu-app.example/callback
  &scope=mcp.cart+mcp.cart.read+mcp.cart.write
  &state=wxyz6789
  &code_challenge=abcd_-0123
  &code_challenge_method=S256
```

| Parâmetro | Descrição |
| --- | --- |
| `response_type` | Sempre `code` |
| `client_id` | ID do seu cliente OAuth registrado no iFood |
| `redirect_uri` | URL para onde o usuário volta após autenticar. O valor deve corresponder exatamente ao cadastrado. Use HTTPS em todas as URLs — a única exceção é `localhost`. Em dispositivos móveis, você pode configurar um Universal Link (iOS) ou App Link (Android) para retornar diretamente ao seu app. |
| `scope` | Escopos solicitados, separados por espaço — escopos amplos (`mcp.cart`) para roteamento e granulares (`mcp.cart.write`) para autorização. Consulte a referência de [Escopos](/docs/guides/authentication/escopos). |
| `state` | String opaca e aleatória com no mínimo 8 caracteres. Protege contra CSRF e permite correlacionar o estado antes e depois do redirecionamento. |
| `code_challenge` | SHA256 do `code_verifier` codificado em base64url |
| `code_challenge_method` | Sempre `S256` |


Nunca envie o code_verifier no redirecionamento
Ele é usado apenas no Passo 3, na troca por tokens.

## Passo 2: Processe o callback

Após o usuário se autenticar e consentir, o iFood redireciona para o `redirect_uri` com o `authorization_code` e o `state` na query string:

```
GET https://seu-app.example/callback?
  code=AUTHORIZATION_CODE
  &state=wxyz6789
```

**Sempre valide o `state` antes de prosseguir:**

```
app.get('/callback', (req, res) => {
  const { code, state } = req.query;

  // Validação obrigatória contra CSRF
  if (state !== req.session.oauthState) {
    return res.status(403).send('State inválido. Possível ataque CSRF.');
  }

  // State válido — prossiga para a troca de tokens
  exchangeCodeForTokens(code);
});
```

Valide o state antes de prosseguir
Rejeite a requisição se o state não coincidir com o valor enviado no Passo 1. Essa validação previne ataques CSRF.

## Passo 3: Troque o código por tokens

Envie o `authorization_code` para o endpoint de token. **Essa chamada parte do seu backend** — nunca exponha o `client_secret` no frontend ou em aplicativos nativos.

cURL

```
curl -X POST https://id.ifood.com.br/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=https://seu-app.example/callback" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "code_verifier=$CODE_VERIFIER"
```

JavaScript

```
const params = new URLSearchParams({
  grant_type: 'authorization_code',
  code: 'AUTHORIZATION_CODE',
  redirect_uri: 'https://seu-app.example/callback',
  client_id: process.env.CLIENT_ID,
  client_secret: process.env.CLIENT_SECRET,
  code_verifier: codeVerifier
});

const response = await fetch('https://id.ifood.com.br/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: params
});

const tokens = await response.json();
```

Python

```
import os
import requests

response = requests.post(
    "https://id.ifood.com.br/token",
    data={
        "grant_type": "authorization_code",
        "code": "AUTHORIZATION_CODE",
        "redirect_uri": "https://seu-app.example/callback",
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "code_verifier": code_verifier,
    },
)

tokens = response.json()
```

Java

```
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.stream.Collectors;

Map<String, String> form = Map.of(
    "grant_type", "authorization_code",
    "code", "AUTHORIZATION_CODE",
    "redirect_uri", "https://seu-app.example/callback",
    "client_id", System.getenv("CLIENT_ID"),
    "client_secret", System.getenv("CLIENT_SECRET"),
    "code_verifier", codeVerifier
);

String body = form.entrySet().stream()
    .map(e -> URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8) + "=" +
              URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8))
    .collect(Collectors.joining("&"));

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://id.ifood.com.br/token"))
    .header("Content-Type", "application/x-www-form-urlencoded")
    .POST(HttpRequest.BodyPublishers.ofString(body))
    .build();

HttpResponse<String> response = HttpClient.newHttpClient()
    .send(request, HttpResponse.BodyHandlers.ofString());
```

Go

```
import (
    "log"
    "net/http"
    "net/url"
    "os"
    "strings"
)

form := url.Values{
    "grant_type":    {"authorization_code"},
    "code":          {"AUTHORIZATION_CODE"},
    "redirect_uri":  {"https://seu-app.example/callback"},
    "client_id":     {os.Getenv("CLIENT_ID")},
    "client_secret": {os.Getenv("CLIENT_SECRET")},
    "code_verifier": {codeVerifier},
}

resp, err := http.Post(
    "https://id.ifood.com.br/token",
    "application/x-www-form-urlencoded",
    strings.NewReader(form.Encode()),
)
if err != nil {
    log.Fatal(err)
}
defer resp.Body.Close()
```

| Parâmetro | Descrição |
| --- | --- |
| `grant_type` | Sempre `authorization_code` |
| `code` | Código recebido no Passo 2 |
| `redirect_uri` | O mesmo `redirect_uri` enviado no Passo 1 |
| `client_id` | ID do seu cliente OAuth |
| `client_secret` | Senha do seu cliente OAuth |
| `code_verifier` | String aleatória gerada no Passo 1 |


**Resposta de sucesso (200 OK):**

```
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Nunca exponha o client_secret
A troca de código por tokens sempre acontece no backend. Se o client_secret vazar, qualquer pessoa pode se passar pela sua aplicação.

## Passo 4: Renove os tokens

Quando o `access_token` expirar, use o `refresh_token` para obter um novo par — sem exigir nova interação do usuário. Assim como no Passo 3, essa chamada parte do seu backend. A única diferença é o corpo da requisição.

cURL

```
curl -X POST https://id.ifood.com.br/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET"
```

JavaScript

```
const params = new URLSearchParams({
  grant_type: 'refresh_token',
  refresh_token: refreshToken,
  client_id: process.env.CLIENT_ID,
  client_secret: process.env.CLIENT_SECRET
});

const response = await fetch('https://id.ifood.com.br/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: params
});

const tokens = await response.json();
```

Python

```
import os
import requests

response = requests.post(
    "https://id.ifood.com.br/token",
    data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
    },
)

tokens = response.json()
```

Java

```
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.stream.Collectors;

Map<String, String> form = Map.of(
    "grant_type", "refresh_token",
    "refresh_token", refreshToken,
    "client_id", System.getenv("CLIENT_ID"),
    "client_secret", System.getenv("CLIENT_SECRET")
);

String body = form.entrySet().stream()
    .map(e -> URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8) + "=" +
              URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8))
    .collect(Collectors.joining("&"));

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://id.ifood.com.br/token"))
    .header("Content-Type", "application/x-www-form-urlencoded")
    .POST(HttpRequest.BodyPublishers.ofString(body))
    .build();

HttpResponse<String> response = HttpClient.newHttpClient()
    .send(request, HttpResponse.BodyHandlers.ofString());
```

Go

```
import (
    "log"
    "net/http"
    "net/url"
    "os"
    "strings"
)

form := url.Values{
    "grant_type":    {"refresh_token"},
    "refresh_token": {refreshToken},
    "client_id":     {os.Getenv("CLIENT_ID")},
    "client_secret": {os.Getenv("CLIENT_SECRET")},
}

resp, err := http.Post(
    "https://id.ifood.com.br/token",
    "application/x-www-form-urlencoded",
    strings.NewReader(form.Encode()),
)
if err != nil {
    log.Fatal(err)
}
defer resp.Body.Close()
```

| Parâmetro | Descrição |
| --- | --- |
| `grant_type` | Sempre `refresh_token` |
| `refresh_token` | Token obtido no Passo 3 ou na última renovação |
| `client_id` | ID do seu cliente OAuth |
| `client_secret` | Senha do seu cliente OAuth |


**Resposta (200 OK):**

```
{
  "access_token": "NOVO_ACCESS_TOKEN",
  "id_token": "NOVO_ID_TOKEN",
  "refresh_token": "NOVO_REFRESH_TOKEN",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Os tokens são rotacionados a cada renovação
Descarte o access_token e o refresh_token anteriores e armazene apenas os novos tokens retornados.

## Passo 5: Revogue os tokens

Quando o usuário se desconectar da sua aplicação, revogue os tokens ativos para invalidá-los no iFood. A revogação parte do seu backend.

```
POST https://id.ifood.com.br/revoke
Content-Type: application/x-www-form-urlencoded

token=REFRESH_TOKEN
&client_id=seu-client-id
&client_secret=seu-client-secret
```

| Parâmetro | Descrição |
| --- | --- |
| `token` | `refresh_token` ou `access_token` a ser revogado |
| `client_id` | ID do seu cliente OAuth |
| `client_secret` | Senha do seu cliente OAuth |


**Resposta de sucesso:** `200 OK`

A revogação é imediata e irreversível
Revogar um refresh_token invalida também todos os access_tokens derivados dele. Após revogar, remova os tokens do seu armazenamento. Para obter acesso novamente, o usuário precisa refazer o fluxo desde o Passo 1.

## Endpoints

| Endpoint | Método | Descrição |
| --- | --- | --- |
| `https://id.ifood.com.br/authorize` | `GET` | Iniciar autenticação (via navegador) |
| `https://app.ifood.com.br/F4X4/authorize` | `GET` | Iniciar autenticação (via aplicativo — OneLink) |
| `https://id.ifood.com.br/token` | `POST` | Trocar código por tokens / Renovar tokens |
| `https://id.ifood.com.br/revoke` | `POST` | Revogar tokens (logout) |


## Segurança

### Checklist de produção

-  **HTTPS em todas as URLs** — a única exceção é `localhost`
-  **`client_secret` apenas no backend** — nunca no frontend, app mobile ou repositório
-  **Valide o `state` no callback** — proteção obrigatória contra CSRF
-  **Refresque antes de expirar** — mantenha um buffer de 5 minutos
-  **Revogue ao fazer logout** — chame `/revoke`, depois remova os tokens locais
-  **Armazene tokens com segurança** — HttpOnly cookies no backend, Keychain/Keystore no mobile
-  **Respeite os escopos concedidos** — não acesse dados além do que o usuário consentiu

---

## Introdução — /authentication/introducao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/introducao

# Introdução

Este guia explica como funciona o processo de autenticação para usar os MCPs do iFood Marketplace.

O fluxo é baseado em [OAuth 2.1](https://oauth.net/2.1/) e [OpenID Connect (OIDC)](https://openid.net/connect/). Nesse modelo, o iFood atua como [Identity Provider (IdP)](https://en.wikipedia.org/wiki/Identity_provider) e [Single Sign-On (SSO)](https://en.wikipedia.org/wiki/Single_sign-on). O usuário entra com a conta iFood — e, se ainda não tiver uma, cria no próprio fluxo.

## Como funciona

O fluxo segue o **Authorization Code com PKCE** e tem 5 passos:

Solicite autorização
Redirecione o usuário para /authorize.
Processe o callback
Receba o authorization_code e valide o state.
Troque o código por tokens
POST /token → access_token + refresh_token.
Renove os tokens
POST /token com o refresh_token.
Revogue os tokens
POST /revoke no logout.

A integração é a mesma para qualquer aplicação. O que muda é como o usuário autentica e consente — no navegador ou no app — e é essa etapa que diferencia as jornadas.

## Jornadas de autenticação

A experiência do usuário varia conforme o dispositivo. O iFood oferece **2 jornadas**:

Via app iFood (Any2App)

App mobile com o app iFood instalado.

Login WEB

Qualquer dispositivo, sem app iFood — fallback universal.

A integração não muda
Você implementa os mesmos 5 passos em qualquer jornada. A diferença está em como o usuário autentica e consente — o que acontece entre o Passo 1 e o Passo 2.

## Consentimento

O consentimento é a assinatura do usuário para o compartilhamento de dados — e a base de governança da autenticação.

- **Obrigatório** para qualquer integração com aplicações terceiras.
- **Exibição padronizada** das informações compartilhadas (scopes), garantindo clareza e previsibilidade.
- **Solicitado uma única vez** — não se repete a cada login.
- **Interface modular**, com personalização de marca (título, imagem e termos de privacidade) por cliente.

O usuário gerencia e revoga consentimentos a qualquer momento em **"Contas Conectadas"**, no app iFood. Ao revogar, o compartilhamento de dados é interrompido imediatamente e a sessão ativa na sua aplicação é encerrada. Seu agente deve respeitar a revogação e parar de usar o escopo imediatamente.

A tela de consentimento exibe os escopos que sua aplicação solicita. Solicite apenas o essencial — veja a referência de [Escopos](/docs/guides/authentication/escopos).

---

## Jornadas de autenticação — /authentication/jornadas

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/jornadas

# Jornadas de autenticação

O iFood seleciona a jornada com base no dispositivo e no contexto do usuário. Em todas elas, o **fluxo de autorização é o mesmo** (OAuth 2.1 + OIDC) — o que muda é como o usuário comprova a identidade.

## Escolha a jornada

Via app iFood (Any2App)

Mobile (Android/iOS). Requer app iFood, com fallback WEB.

Login WEB

Qualquer dispositivo, sem app iFood.

Login WEB é o fallback universal
Quando o app iFood não está disponível — no dispositivo (Any2App) ou no celular do usuário (Pending Action) — o sistema redireciona para a web (id.ifood.com.br), cobrindo 100% dos usuários sem interrupção na jornada.

## Via app iFood (Any2App)

A jornada **Any2App** usa a sessão do app iFood para autenticar o usuário sem digitar credenciais. É a jornada com menor fricção.

### Quando usar

Use quando sua aplicação é mobile (Android ou iOS) e o usuário tem o app iFood instalado.

### Ponto de entrada

Use o **OneLink** como ponto de entrada único: `https://app.ifood.com.br/F4X4/authorize`.

O OneLink é uma página web que detecta se o app iFood está instalado:

- **Instalado:** abre o app iFood para autenticação e consentimento.
- **Não instalado:** redireciona para a [jornada Login WEB](#login-web) (fallback automático).

Interação com o OneLink
A depender do dispositivo, o usuário pode precisar interagir com a página do OneLink para prosseguir ao destino.

### Experiência do usuário

Toque em "Logar com iFood"
O usuário inicia o login na sua aplicação.
Redirecione ao app
Sua aplicação redireciona para o app iFood, via deep link.
Autentique e consinta
Logado, o usuário vê o consentimento; senão, autentica no app antes de consentir.
Receba o código
Após aprovar, o usuário retorna à sua aplicação com o authorization_code.
Troque por tokens
Sua aplicação troca o código por Access Token e ID Token.

A troca de tokens segue o mesmo fluxo da [Implementação](/docs/guides/authentication/implementacao).

### Cenário alternativo

**App iFood não instalado:** o sistema redireciona automaticamente para a [jornada Login WEB](#login-web). O usuário continua o fluxo sem interrupção.

### Implementação

#### Configure o `redirect_uri`

Use uma URL **HTTPS** como `redirect_uri`. Para retornar diretamente ao seu app, configure um **Universal Link** (iOS) ou **App Link** (Android). Ambos usam HTTPS e são configurados no seu app e no seu domínio, sem envolvimento do iFood.

Custom schemes não são suportados
Esquemas customizados (scheme://) exigem registro individual no app iFood a cada novo scheme, o que não é escalável. Use sempre HTTPS.

#### Abra o OneLink

```
const state = Math.random().toString(36).substring(7);
const params = new URLSearchParams({
  client_id: 'YOUR_CLIENT_ID',
  response_type: 'code',
  redirect_uri: 'https://seuapp.com/callback',
  scope: 'mcp.cart mcp.cart.read mcp.cart.write',
  state
});

const oneLink = `https://app.ifood.com.br/F4X4/authorize?${params}`;
await Linking.openURL(oneLink);
```

#### Capture o callback

O callback chega em `https://seuapp.com/callback?code=...&state=...` — direto no seu app, via Universal Link ou App Link. Valide o `state` e envie o `code` para o backend trocar por tokens. Veja os [Passos 2 e 3 da Implementação](/docs/guides/authentication/implementacao#passo-2-processe-o-callback).

## Login WEB

A jornada **Login WEB** é a solução universal: funciona em qualquer dispositivo e não requer o app iFood. O usuário é redirecionado para `id.ifood.com.br`, onde insere seus dados e valida a identidade.

O Login WEB tem duas variações:

- **[Login WEB no navegador](#login-web-no-navegador)** — a autenticação começa e termina na web.
- **[Login WEB: Pending Action](#login-web-pending-action)** — a autenticação começa na web e termina no app iFood.

### Login WEB no navegador

#### Quando usar

Use quando o app iFood não está disponível — no dispositivo ou no celular do usuário. É o fallback das outras jornadas.

#### Ponto de entrada

`https://id.ifood.com.br/authorize`

#### Experiência do usuário

Toque em "Logar com iFood"
O usuário inicia o login na sua aplicação.
Redirecione ao navegador
O usuário é redirecionado para id.ifood.com.br.
Valide a identidade
O usuário informa um identificador (telefone ou e-mail) e completa a validação, conforme o perfil de segurança aplicável.
Consinta
O usuário vê a tela de consentimento e aprova o compartilhamento dos dados.
Receba o código
O iFood retorna o authorization_code para sua aplicação.
Troque por tokens
Sua aplicação troca o código por Access Token e ID Token.

A troca de tokens segue o mesmo fluxo da [Implementação](/docs/guides/authentication/implementacao).

#### Diferenciais

- Não requer o app iFood — acesso universal (Android, iOS, desktop).
- O usuário escolhe o identificador (telefone ou e-mail).
- Usa o navegador nativo (system webview), sem instalar nada.

### Login WEB: Pending Action

A **Pending Action** é a variação do Login WEB que começa na web e termina no app. O usuário inicia o fluxo no navegador de um dispositivo não-móvel (desktop, totem ou agente) e autoriza no app iFood do celular, via push notification ou abrindo o app diretamente.

#### Quando usar

Use quando o usuário inicia o fluxo em desktop, totem ou agente, e confirma a autorização no celular.

#### Experiência do usuário

Toque em "Logar com iFood"
O usuário inicia o login na sua aplicação (desktop, totem etc.).
Identifique o dispositivo
A plataforma identifica o dispositivo como out-of-band e seleciona a Pending Action.
Envie a notificação
O sistema envia uma notificação para o app iFood no celular do usuário.
Abra o app iFood
O usuário abre o app (via notificação ou diretamente) e vê as telas de inserção numérica e consentimento antes da home.
Autentique e consinta
Logado, as telas aparecem diretamente; senão, o usuário autentica no app antes de consentir.
Aprove ou recuse
O usuário aprova ou recusa a solicitação.
Receba os tokens
Se aprovado, o iFood emite os tokens e notifica sua aplicação.

#### Onde o usuário vê a solicitação

- **Push notification:** recebida automaticamente ao iniciar o fluxo.
- **Abertura do app:** a tela de consentimento aparece antes da home do iFood.

#### Cenários alternativos

- **Sem app iFood no celular:** fallback automático para o [Login WEB no navegador](#login-web-no-navegador). O usuário toca em "tentar de outra forma".
- **Recusa pelo usuário:** o iFood notifica sua aplicação com erro de negação (`access_denied`). Veja [Erros](/docs/guides/authentication/erros).
- **Sem conta iFood:** o usuário é redirecionado para o [cadastro](#cadastro), no dispositivo inicial.

O consentimento é salvo e pode ser revogado a qualquer momento em **"Contas Conectadas"**. Veja [Introdução](/docs/guides/authentication/introducao#consentimento).

#### Cadastro

Quando o usuário ainda não tem conta iFood, a jornada continua em `id.ifood.com.br` com o cadastro. O cadastro usa o mesmo fluxo de autorização e retorna as mesmas informações do login.

O usuário fornece:

- **Telefone** — validado para comprovar posse.
- **E-mail** — validado para comprovar posse.
- **Nome completo**.

Após criar a conta, o fluxo continua automaticamente: o consentimento é solicitado e os tokens são emitidos, retornando o usuário para a sua aplicação — sem novo login.

#### Desafios de segurança

Os desafios variam conforme as políticas de segurança do iFood e o dispositivo.
Código de verificação
Disponível em qualquer dispositivo. É o desafio mais comum:

- O usuário fornece seu e-mail ou telefone.
- O iFood envia um código para o e-mail ou telefone informado.
- O usuário digita o código recebido.

No desktop, o usuário também pode aprovar o acesso pelo smartphone. Veja a subseção [Login WEB: Pending Action](#login-web-pending-action).

#### Implementação

```
const state = Math.random().toString(36).substring(7);
const params = new URLSearchParams({
  client_id: 'YOUR_CLIENT_ID',
  response_type: 'code',
  redirect_uri: 'https://seuapp.com/callback',
  scope: 'mcp.cart mcp.cart.read mcp.cart.write',
  state
});

window.location.href = `https://id.ifood.com.br/authorize?${params}`;
```

O callback chega em `https://seuapp.com/callback?code=...&state=...`. Valide o `state` e envie o `code` para o backend. Veja os [Passos 2 e 3 da Implementação](/docs/guides/authentication/implementacao#passo-2-processe-o-callback).

---

## User MCP — /mcps/account

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account

# User MCP

---

## Offer Discovery MCP — /mcps/discovery

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery

# Offer Discovery MCP

---

## Order Tracking — /mcps/order

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order

# Order Tracking MCP

---

## Cart — /mcps/cart

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart



---

## Criar agente — /first-steps/agent

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/agent

# Criar agente

Crie um agente para solicitar acesso aos MCPs no sandbox.

## Informações do agente

| Campo | Formato | Notas |
| --- | --- | --- |
| Logo | PNG, SVG, JPG (1 MB) | Quadrado |
| Nome | String | "Pizza Concierge" |
| Descrição | String | Uma frase |
| Redirect URL (Callback URL) | URL (http:// ou https://) | Recebe `authorization_code` no fluxo OAuth 2.1 |
| Termos de Uso (URL) | URL | Link público para os termos de uso do agente |
| Política de Privacidade (URL) | URL | Link público para a política de privacidade do agente |


## Escopos de acesso

Nesta etapa você seleciona os **escopos de acesso** que o agente poderá solicitar. Escolha apenas o que for necessário.

| Escopo de acesso | O que permite |
| --- | --- |
| **Dados de usuário** | Permite ao agente identificar o usuário, obter dados básicos de perfil e gerenciar dados de endereço. |
| **Descoberta de conteúdo** | Acesso a feeds de restaurantes, recomendações de cardápios, busca de itens e avaliações de estabelecimento. |
| **Criação de pedidos** | Permite gerenciar o carrinho do usuário, efetuar pagamentos simulados e acompanhar o status de entrega do pedido. |


Seleção em cascata
Permissões avançadas incluem automaticamente as anteriores. Por exemplo, Descoberta de conteúdo ativa Dados de usuário, e Criação de pedidos ativa todas as opções.

Escopos técnicos chegam após a homologação
Nesta tela você seleciona apenas os 3 escopos de acesso. Os escopos técnicos exatos (por exemplo, `mcp.user.basic.read` e `mcp.cart.write`) só são liberados depois que o agente é homologado.

Veja a referência de [Escopos](/docs/guides/authentication/escopos) para a lista completa e o uso na requisição.

## Após a criação

Ao criar o agente, ele entra em **análise de segurança** do iFood. As credenciais são liberadas somente após a aprovação.

Acompanhe o status do agente no portal, na listagem **Meus agents**. A aprovação não gera notificação por e-mail.

Com o agente aprovado, a seção **Credenciais de acesso** aparece na página do agente:

- **Client ID** — exibido diretamente.
- **Client Secret** — gerado sob demanda. Clique no ícone de gerar e copie o valor na primeira exibição; ele é mostrado uma única vez.

Use as duas credenciais para trocar o `authorization_code` por um `access_token` na Redirect URL (Callback URL).

Com o agente homologado, você pode [criar uma conta de teste](/docs/guides/first-steps/test-account) para validar sua integração de ponta a ponta, sem telefone real.

---

## Criar conta — /first-steps/account

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/account

# Criar conta

Leva 5 minutos. Crie sua conta no MCP Portal: escolha seu perfil, insira e-mail e senha e faça as validações por e-mail.

## Qual tipo de perfil você precisa?

Pessoal / Estudante
Testar integrações localmente
Estudar como os MCPs funcionam
Desenvolver em ambiente sandbox
Validação: Nenhuma
Acesso: Sandbox (grátis)
Profissional
Validação de documentação (CNPJ/registro comercial)
Aprovação do time de conformidade (24-48h)
Acesso simultâneo: sandbox + produção
Validação: Documentação (24-48h)
Acesso: Sandbox + Produção

## Fluxo de criação

Dados de login
E-mail e senha. A senha deve ter pelo menos 8 caracteres, 1 número, 1 letra maiúscula e 1 letra minúscula.
Qual é seu objetivo?
Escolha entre Estudante ou Profissional. Você pode mudar depois.
Dados cadastrais
Nome completo e CPF.
Sobre a empresa
CNPJ, razão social, nome fantasia e CNAE. Apenas para conta Profissional.
Confirme seu telefone
País e número.
Enviamos um e-mail de verificação pra você
Veja a caixa de entrada ou pasta de spam do seu e-mail e continue.

Tudo pronto! O que esperar agora?

Assim que o 2FA for configurado com sucesso, sua conta estará ativa no ambiente Sandbox. Após verificar seu e-mail e fazer login no MCP Portal, você poderá acessar o ambiente Sandbox. Para obter credenciais de teste (`Client ID` e `Client Secret`), registre um agente. [Crie sua conta agora](https://mcp-developer.ifood-sandbox.com.br/pt-BR/sign-up).

## Depois da criação

Após verificar seu e-mail e fazer login, você terá acesso ao sandbox para testar. Se escolheu Profissional, receberá e-mail quando a validação de documentação terminar (normalmente 24-48h). Enquanto isso, o sandbox fica disponível para experimentar.

Quando estiver pronto para integrar MCPs, consulte:

- [Gerenciar tokens](/docs/guides/authentication/implementacao#passo-4-renove-os-tokens)
- [Entender OAuth 2.1 e PKCE](/docs/guides/authentication/)

## Problemas comuns ao criar conta

Não recebi o e-mail de verificação de conta
Verifique a caixa de entrada ou a pasta de spam do e-mail informado. O e-mail de confirmação é enviado após a criação da conta.
A senha não atende aos requisitos de segurança exigidos
A senha deve ter pelo menos 8 caracteres, 1 número, 1 letra maiúscula e 1 letra minúscula. Evite usar informações pessoais óbvias como nome, e-mail ou datas.
Não consigo ler o código QR do 2FA
Tente usar a opção de inserir o código manualmente (em vez de escanear o código QR). Certifique-se de que a câmera do seu telefone está funcionando. Se o problema persistir, tente usar outro aplicativo autenticador como Google Authenticator, Microsoft Authenticator ou Authy.
O que fazer se eu perder meus códigos de backup do 2FA?
Entre em contato com o suporte de segurança imediatamente. Você pode solicitar a desabilitação temporária do 2FA para recuperar o acesso, mediante comprovação de identidade. Após recuperar o acesso, configure um novo 2FA e armazene os novos códigos de backup em local seguro.

Aviso: boas práticas de segurança
Proteger sua conta de desenvolvedor é vital para a integridade dos seus agentes. Nunca compartilhe suas chaves ou tokens de agente em canais públicos. Use senhas exclusivas para o portal de desenvolvimento. Sempre regenere e descarte credenciais antigas de agente.

---

## Instalar MCP — /first-steps/install-mcp

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/install-mcp

# Instalar MCP

## O que é MCP?

O **Model Context Protocol (MCP)** é um protocolo aberto que permite conectar aplicações de IA com ferramentas e dados externos. Um MCP atua como um "servidor" que roda localmente ou remotamente, fornecendo funcionalidades específicas (como buscar ofertas, gerenciar carrinho, rastrear pedidos) que o Claude, Gemini, ChatGPT ou qualquer cliente de IA pode acessar durante conversas.

**Na prática:** Quando você instala o MCP do iFood, o Claude ganha a capacidade de buscar ofertas, promoções e restaurantes em tempo real. Tudo isso sem deixar a conversa.

## Por que instalar um MCP?

- Acesso a dados em tempo real (sem dados desatualizados)
- Integração nativa com seus sistemas iFood
- Sem necessidade de fazer chamadas manuais à API
- Segurança: tokens configurados uma vez, usados automaticamente
- Funciona offline se o servidor MCP rodar localmente

## Pré-requisitos

Você precisa de **apenas um** desses:

| Ambiente | Requisito | Comando para verificar |
| --- | --- | --- |
| **Claude Code (VS Code)** | VS Code + extensão Claude | `code --version` |
| **Cursor IDE** | Cursor instalado | `cursor --version` |
| **Claude Desktop** | App Claude Desktop | Procure "Claude" no seu sistema |
| **Google Gemini CLI** | Node.js 18+ ou Python 3.8+ | `node --version` ou `python --version` |
| **ChatGPT** | ChatGPT Plus, Pro, Team, Enterprise ou Edu | Acesse [chat.openai.com](https://chat.openai.com) |


Não tem nada instalado?

Comece com **Claude Desktop** (mais simples) ou **Cursor IDE** (se já usa Cursor).

## Instalação por plataforma

Antes de conectar, tenha em mãos o **Client ID** e o **Client Secret** do seu agente. Essas credenciais aparecem na página do agente, na seção **Credenciais de acesso**, após a aprovação (veja [Criar agente](/docs/guides/first-steps/agent)). Nos comandos abaixo, substitua `CLIENT_ID` e `CLIENT_SECRET` pelos seus valores.

### Claude Code (VS Code)

**Tempo estimado: 2 minutos**

- 
Instale a extensão Claude

- Abra VS Code
- Vá para Extensions (`Cmd+Shift+X`)
- Procure "Claude" e instale a versão oficial da Anthropic

- 
Configure seu token API

- Abra Command Palette (`Cmd+Shift+P`)
- Digite `Claude: Set API Token`
- Copie seu token em [claude.ai/settings/api](https://claude.ai/settings/api)

- 
Adicione o MCP do iFood

Bash (macOS/Linux)

```
claude mcp add --transport http iFood https://consumer-mcp.ifood.com.br/marketplace --client-id CLIENT_ID --client-secret
```

PowerShell (Windows)

```
claude mcp add --transport http iFood https://consumer-mcp.ifood.com.br/marketplace --client-id CLIENT_ID --client-secret
```

O `--client-secret` pede o segredo de forma mascarada — não passe o valor na própria linha. Alternativamente, defina a variável `MCP_CLIENT_SECRET`.

- 
Autorize no navegador

Abra o Claude Code e execute `/mcp` para seguir o fluxo de login (OAuth) no navegador.

- 
Reinicie VS Code

Pronto! O Claude no seu VS Code pode acessar ofertas do iFood.

### Cursor IDE

**Tempo estimado: 2 minutos**

**Método recomendado: Interface Visual**

- Abra Settings (`Cmd+,` ou `Ctrl+,`)
- Procure por "MCP"
- Clique em **Add new MCP server**
- Preencha os campos:

- **Name:** `iFood`
- **Type:** `HTTP`
- **URL:** `https://consumer-mcp.ifood.com.br/marketplace`
- **Client ID:** `CLIENT_ID`
- **Client Secret:** `CLIENT_SECRET`

- Reinicie Cursor

Alternativa: Editar o arquivo `~/.cursor/mcp.json`

```
{
  "mcpServers": {
    "ifood": {
      "url": "https://consumer-mcp.ifood.com.br/marketplace",
      "auth": {
        "CLIENT_ID": "client-id",
        "CLIENT_SECRET": "client-secret"
      }
    }
  }
}
```

Salve o arquivo e reinicie Cursor.

### Claude Desktop

**Tempo estimado: 3 minutos**

- 
Baixe e instale [claude.ai/download](https://claude.ai/download)

- 
Adicione o MCP do iFood

O Claude Desktop usa os mesmos servidores MCP do Claude Code. Rode no seu terminal o mesmo comando da seção anterior:

```
claude mcp add --transport http iFood https://consumer-mcp.ifood.com.br/marketplace --client-id CLIENT_ID --client-secret
```

- 
Autorize no navegador

Abra o app e execute `/mcp` para seguir o fluxo de login (OAuth) no navegador.

Pronto! O MCP está conectado.

### Google Gemini CLI

**Tempo estimado: 3 minutos**

- 
Instale a CLI

npm

```
npm install -g @google/gemini-cli
gemini --version
```

Homebrew (macOS)

```
brew install gemini-cli
gemini --version
```

- 
Configure seu API key

```
gemini config set api-key YOUR_API_KEY
```

Obtenha a chave em [ai.google.dev/api/keys](https://ai.google.dev/api/keys)

- 
Adicione o MCP do iFood

```
gemini mcp add -s user --transport http iFood https://consumer-mcp.ifood.com.br/marketplace
```

- 
Abra `~/.gemini/settings.json` e adicione o bloco `oauth` com as credenciais (o arquivo deve ficar assim):

```
{
  "mcpServers": {
    "ifood": {
      "httpUrl": "https://consumer-mcp.ifood.com.br/marketplace",
      "oauth": {
        "clientId": "CLIENT_ID",
        "clientSecret": "CLIENT_SECRET"
      }
    }
  }
}
```

- 
Inicie o Gemini e autentique

```
gemini
# No chat, execute: /mcp auth iFood
```

- 
Verifique com `/mcp list` — o iFood deve aparecer conectado.

### ChatGPT (OpenAI)

**Requer:** ChatGPT Plus, Pro, Team, Enterprise ou Edu

- Ative o **Developer Mode**: Configurações → Apps/Connectors → Advanced Settings → ative **Developer Mode**
- Vá em Settings → Connectors → **Add app**
- Informe a URL do MCP (`https://consumer-mcp.ifood.com.br/marketplace`) e o **Client ID** do seu agente
- Selecione **OAuth** como autenticação e clique em Connect para autorizar

Sem Client Secret

O ChatGPT usa OAuth 2.1 com PKCE (fluxo authorization code), então normalmente só é preciso o **Client ID** — clientes públicos não usam Client Secret.

## Verificar se está funcionando

Após instalar, teste a conexão:

### Claude Code / VS Code

- Abra Command Palette (`Cmd+Shift+P`)
- Digite `Claude: View MCP Servers`
- Procure por "iFood"
- Status deve ser **Connected** (verde)

### Cursor IDE

- Settings (`Cmd+,`)
- Procure "MCP"
- Veja **Tools & MCP → Installed MCP Servers**
- Status deve ser **Connected**

### Claude Desktop

- Abra o app e execute `/mcp`
- "iFood" deve aparecer **Connected**

### Google Gemini CLI

```
gemini
# No chat, execute: /mcp list
```

O MCP do iFood deve aparecer como ativo.

### Teste prático

Abra uma conversa e tente:

```
"Busque as melhores ofertas de restaurantes italianos em São Paulo"
```

Se o MCP está funcionando, receberá dados reais do iFood em tempo real.

Primeira vez?

Comece com **Cursor IDE** se prefere uma interface visual, ou **Claude Code** se já usa o terminal.

## Instalação de múltiplos MCPs

O marketplace do iFood é um **único MCP** (gateway) que reúne os quatro domínios disponíveis. Você não precisa instalar cada domínio separadamente — ao conectar a URL do marketplace, todos os domínios ficam disponíveis automaticamente:

- **User** - Gerenciar conta do usuário
- **Offer Discovery** - Buscar ofertas e restaurantes
- **Cart** - Gerenciar carrinho de compras
- **Order Tracking** - Rastrear pedidos

Se você já tem outros MCPs configurados no cliente, basta adicionar a entrada do iFood (com vírgula) sem remover os demais.

## Troubleshooting

### "MCP Server Not Found"

**Sintoma:** O servidor não aparece na lista de MCPs

**Causa:** URL incorreta ou sem conectividade com o marketplace

**Solução:**

- 
Confira se a URL está exatamente como a seguir (sem barra final):
`https://consumer-mcp.ifood.com.br/marketplace`

- 
Teste a conectividade:

```
curl -I https://consumer-mcp.ifood.com.br/marketplace
```

   Se o comando retornar uma resposta HTTP (como `200` ou `401`), o endpoint está acessível. Erros de conexão (`Could not resolve host` ou `Connection refused`) indicam problema de rede ou proxy.

### "Server Shows Disconnected"

**Sintoma:** MCP aparece mas com status "Disconnected"

**Causa:** Processo do servidor morreu ou não consegue se comunicar

**Solução:**

- Saia **completamente** do cliente (não minimize)
- Aguarde 10 segundos
- Abra o cliente novamente
- Se ainda estiver desconectado, teste o endpoint manualmente:

```
curl -I https://consumer-mcp.ifood.com.br/marketplace
```

Se o `curl` responder mas o cliente ainda mostrar desconectado, pode ser um problema de firewall ou proxy.

Firewall corporativo?

Configure proxy nas suas variáveis de ambiente:

```
export HTTP_PROXY="http://seu-proxy:porta"
export HTTPS_PROXY="http://seu-proxy:porta"
```

### "JSON Syntax Error"

**Sintoma:** Nenhum MCP funciona após editar config

**Causa:** Erro na sintaxe JSON (vírgula, aspas, chaves faltando)

**Solução:**

- Abra [jsonlint.com](https://jsonlint.com)
- Cole o conteúdo do arquivo de configuração (por exemplo, `~/.cursor/mcp.json`)
- Procure por:

- Vírgulas faltando entre objetos
- Aspas simples (`'`) em vez de duplas (`"`)
- Chaves `}` ou colchetes `]` não fechados

**Exemplo de erro comum:**

```
// ERRADO - falta vírgula entre os dois MCPs
{
  "mcpServers": {
    "ifood": {
      "type": "http",
      "url": "https://consumer-mcp.ifood.com.br/marketplace"
    }    // Falta vírgula aqui!
    "outro-mcp": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}

// CORRETO
{
  "mcpServers": {
    "ifood": {
      "type": "http",
      "url": "https://consumer-mcp.ifood.com.br/marketplace"
    },   // Vírgula adicionada
    "outro-mcp": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

### "Permission Denied" (macOS/Linux)

**Sintoma:** Erro ao tentar acessar config ou executar MCP

**Causa:** Permissões de arquivo incorretas

**Solução:**

```
# Corrigir permissões do arquivo de configuração
chmod 600 ~/.cursor/mcp.json

# Verificar se ficou correto (deve mostrar: -rw-------)
ls -l ~/.cursor/mcp.json
```

### "Connection Refused" / "Port Already in Use"

**Sintoma:** Erro de conexão, porta bloqueada

**Causa:** Outra instância do MCP está rodando, ou firewall bloqueando

**Solução (macOS/Linux):**

```
# Ver qual processo está usando a porta (ex: 3000)
lsof -i :3000

# Matar o processo
kill -9 <PID>

# Depois reiniciar o cliente
```

**Solução (Windows):**

- Abra Resource Monitor (`Ctrl+Shift+Esc`)
- Clique na aba **Network**
- Procure pela porta do MCP
- Clique direito → **End Process**
- Reinicie Claude Desktop

## Próximas etapas

Com o MCP funcionando, você pode criar ou registrar um agente iFood para começar a usar.

Consulte a documentação de cada MCP para entender quais ações você pode executar:

- **Offer Discovery MCP** - Buscar ofertas e restaurantes
- **User MCP** - Gerenciar dados da conta
- **Cart MCP** - Adicionar/remover itens do carrinho
- **Order Tracking MCP** - Acompanhar status de pedidos

## Referências

- [MCP Protocol Official Docs](https://modelcontextprotocol.io/)
- [Anthropic Claude Integration](https://claude.ai/docs/mcp)

---

## Criar conta de teste — /first-steps/test-account

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/test-account

# Criar conta de teste

Crie uma conta de teste para validar sua integração de ponta a ponta, sem telefone real nem SMS de verdade.

## O que é OTP

**One-Time Password (OTP)** é um código de verificação de uso único, usado no login. Na conta de teste, o código aparece direto no MCP Portal, em vez de ser enviado por SMS ou e-mail.

## O que é uma conta de teste

Uma conta de teste é uma conta iFood dedicada exclusivamente a testes, identificada pelo escopo `ONLY_TEST_AGENT`. Ela nasce para teste e nunca se transforma em conta real.

Com ela, você valida fluxos completos no ambiente sandbox:

- Login via web e app
- Validação de OTP por e-mail e telefone
- Integração dos MCPs (carrinho, busca, pedidos)

Tudo sem depender de um número de telefone real.

## Diferença para a sua conta do MCP Portal

Não confunda os dois tipos de conta:

| Conta | Para que serve | Onde você cria |
| --- | --- | --- |
| Conta do MCP Portal | Acessar o portal, criar agentes e gerenciar credenciais | Página de [criação de conta](https://mcp-developer.ifood-sandbox.com.br/pt-BR/sign-up) |
| Conta de teste | Simular o consumidor final e testar sua integração | Dentro do MCP Portal |


A conta de teste é uma conta iFood de consumidor. Ela serve para validar o que o seu agente fará em nome do usuário.

## Pré-requisitos

Para criar uma conta de teste, você precisa de:

- Uma conta ativa no MCP Portal
- Um agente **ativo**, **aprovado** ou **parcialmente aprovado**

A criação de contas de teste só fica disponível depois que o seu agente é aprovado ou parcialmente aprovado.

## Como funciona

Cada conta de teste tem estas características:

- **E-mail automático** no domínio `@test.ifood.com.br`, gerado a partir do seu nome de usuário.
- **Telefone inválido** com DDD terminado em zero (por exemplo, `20`, `30` ou `40`) e prefixo que não começa com `9`. O número passa na validação de formato sem disparar SMS real.
- **OTP exibido no portal** — os códigos de e-mail e telefone aparecem na tela quando você gera, sem envio real.
- **Regeneração manual** — você gera um novo código quando precisar.

Telefone fictício
O telefone de teste não é seu e não recebe SMS, WhatsApp nem ligação. Os códigos de verificação aparecem apenas no portal.

## Criar uma conta de teste

Abra a área de contas de teste
No MCP Portal, acesse a seção de contas de teste. Ela aparece depois que o seu agente é aprovado ou parcialmente aprovado.
Crie uma nova conta
O portal gera automaticamente o e-mail e o telefone inválido da conta.
Gere e copie o OTP
No modal de detalhes da conta, clique em **Gerar código**. Os códigos de e-mail e telefone aparecem na tela para você copiar.
Use o OTP no login
Faça login no id.ifood com o OTP exibido, em web ou app.

O login não muda

A experiência de login no id.ifood permanece igual. O sistema trata o OTP de teste como um OTP comum, em web e app.

## Regenerar o OTP

O código não é gerado por tempo, como um autenticador. Quando precisar de um novo código, clique em **Gerar novamente** no MCP Portal.

Código expirou?
Regenere o OTP e use o novo código na tentativa de login.

## Limites e ciclo de vida

- Cada usuário do MCP Portal pode ter até 10 contas de teste.
- As contas de teste são **excluídas 15 dias** após a criação.

## O que você pode e não pode fazer

**Pode:**

- Testar login, OTP e integrações no sandbox
- Criar contas para validar fluxos em web e app

**Não pode:**

- Fazer pedidos reais
- Acessar funcionalidades não lançadas

Pedidos de teste pagos não são reembolsados
Evite concluir pagamentos reais em pedidos de teste — por exemplo, via PIX. Se um pedido de teste for pago, o valor não será devolvido.

## Problemas comuns

Qual a diferença entre conta de teste e can_test?
A conta de teste nasce exclusivamente para teste e nunca vira conta real. O `can_test` dá acesso a funcionalidades não lançadas e não deve ser usado para desenvolvimento.
Por que o telefone é inválido?
O DDD terminado em zero não existe no Brasil. Isso mantém o formato válido para o sistema e garante que nenhum SMS ou WhatsApp real seja enviado.
Preciso regenerar o OTP manualmente?
Sim. O código não é gerado por tempo. Clique em **Gerar novamente** no portal sempre que precisar de um novo código.
Não vejo a opção de criar conta de teste
A criação de contas de teste exige um agente ativo, aprovado ou parcialmente aprovado. Verifique o status do seu agente em **Meus agents**.
Quantas contas de teste posso criar?
Até 10 contas por usuário do MCP Portal. As contas são excluídas 15 dias após a criação.

## Próximos passos

- [Autenticação](/docs/guides/authentication/) para entender OAuth 2.1 e PKCE
- [Escopos](/docs/guides/authentication/escopos) para saber o que seu agente pode solicitar

---

## Erros — /mcps/account/erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/erros

# Erros

O User MCP retorna erros estruturados via JSON-RPC 2.0. Entender os tipos de erro e as estratégias de retry ajuda a construir fluxos robustos.

## Protocolo de erro

Todas as respostas usam `HTTP 200 OK`, mesmo em erro. Os erros vêm no corpo com esta estrutura:

```
{
  "errors": {
    "mcpCode": -32301,
    "code": "PLACE_NOT_FOUND",
    "message": "The address 'Avenida Paulista, 99999, São Paulo, SP' could not be geocoded. The number may be invalid or the street may not exist. Ask the user to verify the address and try again.",
    "suggestedAction": "Tell the user: 'I couldn't find that address. Could you double-check it and try again?'",
    "retryable": true
  }
}
```

**Campos importantes:**

- **`mcpCode`**: código de erro JSON-RPC (inteiros negativos)
- **`code`**: tipo do erro (ex. `PLACE_NOT_FOUND`, `MISSING_NEIGHBORHOOD`)
- **`retryable`**: se vale a pena tentar de novo
- **`suggestedAction`**: o que dizer ao usuário

## Taxonomia de erros

| Código | `mcpCode` | Retry? | Causas | O que fazer |
| --- | --- | --- | --- | --- |
| `AUTHENTICATION_REQUIRED` | -32302 | Não | Usuário não autenticado; problema de config do gateway | Dizer ao usuário para reautenticar; não tentar de novo |
| `PLACE_NOT_FOUND` | -32301 | Sim | Endereço não existe / número inválido | Pedir ao usuário para verificar o endereço |
| `MISSING_ADDRESS` | -32303 | Sim | Campo `address` vazio | Pedir o endereço ao usuário |
| `MISSING_NEIGHBORHOOD` | -32301 | Sim | Bairro não pôde ser resolvido | Pedir o bairro e reenviar |
| `MISSING_CANDIDATE_ID` | -32304 | Sim | Tentou confirmar sem `candidateId` | Chamar `createAddress` com `address` primeiro, ou single-shot |
| `CANDIDATE_ID_CONFLICT` | -32305 | Sim | `candidateId` reutilizado com parâmetros diferentes | Re-geocodificar para obter novo `candidateId` |
| `SERVICE_UNAVAILABLE` | -32502 | Sim | Serviço de endereço temporariamente fora | Informar o usuário; tentar de novo em alguns minutos |


`PLACE_NOT_FOUND` e `MISSING_NEIGHBORHOOD` usam o mesmo `mcpCode -32301` — são erros de escopo de geocodificação.

## Exemplos completos de erro

### `AUTHENTICATION_REQUIRED`

```
{
  "errors": {
    "mcpCode": -32302,
    "code": "AUTHENTICATION_REQUIRED",
    "message": "The user is not authenticated. This is a gateway configuration issue — the external agent cannot resolve it. Do not retry. Inform the user that their session may have expired and they should re-authenticate.",
    "suggestedAction": "Tell the user: 'I couldn't verify your identity. Please make sure you're logged into iFood.' Do not attempt any other identity or address operations until this is resolved.",
    "retryable": false
  }
}
```

### `PLACE_NOT_FOUND`

```
{
  "errors": {
    "mcpCode": -32301,
    "code": "PLACE_NOT_FOUND",
    "message": "The address 'Avenida Paulista, 99999, São Paulo, SP' could not be geocoded. The number may be invalid or the street may not exist. Ask the user to verify the address and try again.",
    "suggestedAction": "Tell the user: 'I couldn't find that address. Could you double-check it and try again?'",
    "retryable": true
  }
}
```

### `MISSING_ADDRESS`

```
{
  "errors": {
    "mcpCode": -32303,
    "code": "MISSING_ADDRESS",
    "message": "The address field is required and was empty. Ask the user for their delivery address.",
    "suggestedAction": "Ask the user: 'What's your delivery address?'",
    "retryable": true
  }
}
```

### `MISSING_NEIGHBORHOOD`

```
{
  "errors": {
    "mcpCode": -32301,
    "code": "MISSING_NEIGHBORHOOD",
    "message": "Geocoding did not return a neighborhood (bairro) and none could be resolved from the request. Ask the user for the neighborhood and re-submit with the neighborhood parameter.",
    "suggestedAction": "Ask the user: 'Qual é o bairro do endereço?' Then call createAddress again with candidateId and neighborhood.",
    "retryable": true
  }
}
```

### `MISSING_CANDIDATE_ID`

```
{
  "errors": {
    "mcpCode": -32304,
    "code": "MISSING_CANDIDATE_ID",
    "message": "A candidateId is required to create an address but none was provided. This error occurs when the agent attempts to create an address without first obtaining candidates via a geocoding call, or without using the single-shot flow.",
    "suggestedAction": "Either: (1) Call createAddress with the address string first to get candidates, confirm with the user, then re-submit with the chosen candidateId. Or (2) if the user provided address (street + number) + complement upfront, call createAddress with both to trigger single-shot creation.",
    "retryable": true
  }
}
```

### `CANDIDATE_ID_CONFLICT`

```
{
  "errors": {
    "mcpCode": -32305,
    "code": "CANDIDATE_ID_CONFLICT",
    "message": "This candidateId was already used to create an address with different parameters (address, neighborhood, alias, complement, or reference). The existing address was not modified.",
    "suggestedAction": "If the user changed their mind about the neighborhood, alias, complement, or reference, re-geocode the address to get a new candidateId and retry. If this was a genuine retry, verify the parameters match the original call.",
    "retryable": true
  }
}
```

### `SERVICE_UNAVAILABLE`

```
{
  "errors": {
    "mcpCode": -32502,
    "code": "SERVICE_UNAVAILABLE",
    "message": "The address service is temporarily unavailable. Do not retry immediately. Inform the user that address lookup is down and suggest they try again in a few minutes. You can proceed to Offer Discovery with a user-provided location if available.",
    "suggestedAction": "Tell the user: 'I'm having trouble accessing your saved addresses. You can tell me your delivery address directly if you know it, or we can wait a moment and try again.'",
    "retryable": true
  }
}
```

## Anti-padrões comuns

### Anti-padrão 1: Não chamar `listAddresses()` primeiro

**Problema**: começar a criação de endereço sem saber se o usuário já tem um.

```
// ERRADO - Pulou listAddresses()!
async function createNewAddress() {
  const newAddr = await userClient.createAddress({
    address: "Avenida Paulista, 100"
  });
  // Resultado: pode criar um endereço duplicado
}
```

**Solução**:

```
// CORRETO - Sempre listar primeiro
async function orderFlow() {
  const list = await userClient.listAddresses();

  if (list.results.length === 0) {
    const newAddr = await userClient.createAddress({ address: "Avenida Paulista, 100" });
  } else {
    // Usar existente
  }
}
```

### Anti-padrão 2: Confundir `candidateId` com `addressId`

**Problema**: armazenar `candidateId` e tentar usá-lo em pedidos futuros.

```
// ERRADO
const geocoding = await userClient.createAddress({ address: "Avenida Paulista, 100" });
const candidateId = geocoding.candidates[0].candidateId;

// Bem depois...
const cart = await cartClient.createCart({
  addressId: candidateId  // Isso é candidateId, não addressId!
});
```

**Solução**: `candidateId` é só para confirmação; `addressId` é permanente.

```
const geocoding = await userClient.createAddress({ address: "Avenida Paulista, 100" });

const created = await userClient.createAddress({
  candidateId: geocoding.candidates[0].candidateId,
  complement: "Apto 72",
  alias: "Casa"
});

const addressId = created.addressId;  // ESTE é permanente
```

### Anti-padrão 3: Confirmar sem geocodificar primeiro

**Problema**: tentar criar com um `candidateId` que nunca foi obtido da geocodificação.

```
// ERRADO
const candidateId = "cand-001";  // Inventado

const newAddr = await userClient.createAddress({
  candidateId: candidateId,  // Sem chamar createAddress(address) primeiro!
  complement: "Apto 72"
});
// Resultado: erro MISSING_CANDIDATE_ID
```

**Solução**:

```
// CORRETO - Sempre two-step
const geocoding = await userClient.createAddress({ address: "Avenida Paulista, 100" });

const newAddr = await userClient.createAddress({
  candidateId: geocoding.candidates[0].candidateId,
  complement: "Apto 72"
});
```

### Anti-padrão 4: Colocar bairro em `complement` ou `reference`

**Problema**: quando a geocodificação omite o bairro, codificar o bairro no campo errado.

```
// ERRADO
const newAddr = await userClient.createAddress({
  candidateId: "cand-002",
  complement: "Apto 10, Centro"  // bairro pertence a neighborhood!
});
// Resultado: validação pode falhar ou corromper a semântica de entrega
```

**Solução**:

```
// CORRETO - Use o parâmetro neighborhood
const newAddr = await userClient.createAddress({
  candidateId: "cand-002",
  complement: "Apto 10",
  neighborhood: "Centro"
});
```

## Estratégia de retry

### Fluxograma

```
Erro recebido?
  │
  ├─ retryable: false
  │  └─ Não tentar de novo. Corrigir a entrada e tentar com novos parâmetros.
  │
  └─ retryable: true
     ├─ PLACE_NOT_FOUND / MISSING_NEIGHBORHOOD / MISSING_ADDRESS
     │  └─ Pedir ao usuário para corrigir ou completar a entrada
     │
     ├─ MISSING_CANDIDATE_ID / CANDIDATE_ID_CONFLICT
     │  └─ Corrigir o fluxo (geocodificar primeiro, ou re-geocodificar para novo candidateId)
     │
     └─ SERVICE_UNAVAILABLE
        └─ Aguardar alguns minutos e tentar de novo (backoff limitado)
```

### Exemplo: retry com backoff

```
async function createAddressWithRetry(address, maxAttempts = 3) {
  let attempt = 0;

  while (attempt < maxAttempts) {
    const result = await userClient.createAddress({ address });

    if (result.errors && result.errors.code === "SERVICE_UNAVAILABLE") {
      attempt++;
      const backoffSeconds = Math.pow(2, attempt) * 1000;  // evite loops curtos de retry
      console.log(`Serviço indisponível. Tentando de novo em ${backoffSeconds / 1000}s...`);
      await new Promise(resolve => setTimeout(resolve, backoffSeconds));
      continue;
    }

    if (result.errors) {
      return result;  // Erro não-serviço: trate conforme a taxonomia
    }

    return result;  // Sucesso
  }

  throw new Error("Máximo de tentativas excedido");
}
```

## O que NÃO fazer

- Não tentar de novo erros com `retryable: false`
- Não armazenar `candidateId` para uso futuro
- Não tentar confirmar sem geocodificar primeiro
- Não ignorar `suggestedAction` — use-o para orientar o usuário
- Não colocar bairro em `complement` ou `reference`
- Não tentar `SERVICE_UNAVAILABLE` em loop curto — espere minutos, não segundos

## O que FAZER

- Tentar de novo apenas quando `retryable: true`
- Armazenar apenas `addressId` (permanente)
- Sempre confirmar após geocodificar (two-step)
- Usar `suggestedAction` para mensagens ao usuário
- Usar o parâmetro `neighborhood` quando a geocodificação omitir o bairro

---

## Casos de uso — /mcps/account/casos-de-uso

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/casos-de-uso

# Casos de uso

Explore cenários completos e reais de implementação do User MCP. Cada caso mostra como lidar com diferentes situações de endereço.

## Caso 1: Sem endereço (Two-Step com confirmação)

**Objetivo**: usuário sem endereço. O agente geocodifica, apresenta candidatos e cria após confirmação.

**Fluxo**:

- `listAddresses()` → vazio
- Coletar endereço do usuário
- `createAddress(address)` → retorna candidatos
- Confirmar com o usuário
- `createAddress(candidateId, ...)` → criar endereço

**JavaScript:**

```
async function createAddressWithConfirmation() {
  try {
    console.log("1. Verificando endereços...");
    const listResult = await userClient.listAddresses();

    if (listResult.results.length > 0) {
      console.log("Usuário já tem endereços");
      return;
    }

    // Passo 1: Geocodificar
    console.log("2. Geocodificando endereço...");
    const geocodingResult = await userClient.createAddress({
      address: "Avenida Paulista, 100"
    });

    console.log(`Candidatos encontrados: ${geocodingResult.candidates.length}`);
    geocodingResult.candidates.forEach((c, i) => {
      console.log(`  ${i + 1}. ${c.formattedAddress}`);
    });

    // Usuário escolhe o primeiro candidato
    const chosen = geocodingResult.candidates[0];
    console.log(`\nUsuário confirmou: ${chosen.formattedAddress}`);

    // Passo 2: Criar com confirmação
    console.log("3. Salvando endereço...");
    const newAddress = await userClient.createAddress({
      candidateId: chosen.candidateId,
      address: "Avenida Paulista, 100",
      complement: "Apto 72",
      alias: "Casa",
      reference: "Portão azul"
    });

    console.log("Endereço salvo!");
    console.log(`   Alias: ${newAddress.alias}`);
    console.log(`   addressId: ${newAddress.addressId}`);

    return newAddress.addressId;

  } catch (error) {
    console.error(`ERRO: ${error.message}`);
    throw error;
  }
}
```

**Python:**

```
async def create_address_with_confirmation():
    try:
        print("1. Verificando endereços...")
        list_result = await user_client.list_addresses()

        if len(list_result['results']) > 0:
            print("Usuário já tem endereços")
            return

        # Passo 1: Geocodificar
        print("2. Geocodificando 'Avenida Paulista, 100'...")
        geocoding = await user_client.create_address(
            address="Avenida Paulista, 100"
        )

        print(f"Candidatos: {len(geocoding['candidates'])}")
        for i, cand in enumerate(geocoding['candidates']):
            print(f"  {i + 1}. {cand['formattedAddress']}")

        # Usuário escolhe o primeiro candidato
        chosen = geocoding['candidates'][0]
        print(f"\nUsuário confirmou: {chosen['formattedAddress']}")

        # Passo 2: Criar
        new_addr = await user_client.create_address(
            candidate_id=chosen['candidateId'],
            address="Avenida Paulista, 100",
            complement="Apto 72",
            alias="Casa"
        )

        print(f"Salvo com addressId: {new_addr['addressId']}")
        return new_addr['addressId']

    except Exception as error:
        print(f"ERRO: {str(error)}")
        raise
```

## Caso 2: Um endereço (usar direto, sem confirmação)

**Objetivo**: usuário com 1 endereço. O agente usa imediatamente — informa o usuário, sem confirmação.

**Fluxo**:

- `listAddresses()` → 1 endereço
- Informar: "Entregando na Casa" (preferir alias)
- Usar `addressId` / coordenadas direto

**JavaScript:**

```
async function useExistingAddressIfOne() {
  try {
    console.log("1. Listando endereços...");
    const listResult = await userClient.listAddresses();

    if (listResult.results.length !== 1) {
      console.log(`Não se aplica (${listResult.results.length} endereços)`);
      return null;
    }

    const address = listResult.results[0];
    const label = address.alias || address.formattedAddress;

    // Sem confirmação — informar o usuário
    console.log(`Usando ${label} para entrega.`);
    console.log(`   addressId: ${address.addressId}`);
    console.log("   (usuário pode fornecer um novo se não estiver correto)");

    return address.addressId;

  } catch (error) {
    console.error(`ERRO: ${error.message}`);
    throw error;
  }
}
```

**Python:**

```
async def use_existing_address_if_one():
    try:
        print("1. Listando endereços...")
        list_result = await user_client.list_addresses()

        if len(list_result['results']) != 1:
            print(f"Não se aplica ({len(list_result['results'])} endereços)")
            return None

        address = list_result['results'][0]
        label = address.get('alias') or address['formattedAddress']

        # Sem confirmação — informar o usuário
        print(f"Usando {label} para entrega.")
        print(f"   addressId: {address['addressId']}")

        return address['addressId']

    except Exception as error:
        print(f"ERRO: {str(error)}")
        raise
```

## Caso 3: Múltiplos endereços com inferência comportamental

**Objetivo**: usuário com vários endereços. O agente usa os campos comportamentais para inferir o mais provável, confirma brevemente, ou apresenta opções quando não há dados.

**Fluxo**:

- `listAddresses()` → N endereços
- Sem `dataWarning` → inferir o mais provável; confirmar por alias
- Com `dataWarning` → apresentar opções por alias
- Usar o `addressId` escolhido

**JavaScript:**

```
async function smartAddressSelection() {
  try {
    console.log("1. Listando endereços...");
    const listResult = await userClient.listAddresses();
    const addresses = listResult.results;

    if (addresses.length < 2) {
      console.log("Não se aplica (menos de 2 endereços)");
      return null;
    }

    const hints = listResult.agentHints;

    if (hints.dataWarning) {
      // Sem dados comportamentais: apresentar opções por alias
      console.log("2. Apresentando opções...");
      addresses.forEach((addr, i) => {
        console.log(`   ${i + 1}. ${addr.alias || addr.formattedAddress}`);
      });
      // Usuário escolhe → retornar addresses[choice].addressId
      const choice = 0; // simulado
      return addresses[choice].addressId;
    }

    // Com dados comportamentais: inferir o endereço mais provável
    // (1) isLastUsedAddress, (2) isMostUsedAddress30d
    let inferred =
      addresses.find(a => a.isLastUsedAddress) ||
      addresses.find(a => a.isMostUsedAddress30d) ||
      addresses[0];

    // (Opcional) casar a intenção (categoria + dia/turno) com
    // ordersByMerchantTypeWeekdayAndShift quando a intenção é conhecida.
    const alias = inferred.alias || inferred.formattedAddress;
    console.log(`2. Sugerindo: ${alias}`);

    // Confirmar brevemente — nunca assumir em silêncio
    // ex.: "Entregar na Casa?"
    const userAccepts = true; // simulado
    if (userAccepts) {
      console.log(`Confirmado: ${alias}`);
      return inferred.addressId;
    }

    // Usuário rejeitou → apresentar lista completa ou coletar novo
    addresses.forEach((addr, i) => {
      console.log(`   ${i + 1}. ${addr.alias || addr.formattedAddress}`);
    });
    const choice = 0; // simulado
    return addresses[choice].addressId;

  } catch (error) {
    console.error(`ERRO: ${error.message}`);
    throw error;
  }
}
```

**Python:**

```
async def smart_address_selection():
    try:
        print("1. Listando endereços...")
        list_result = await user_client.list_addresses()
        addresses = list_result['results']

        if len(addresses) < 2:
            print("Não se aplica")
            return None

        hints = list_result.get('agentHints', {})

        if hints.get('dataWarning'):
            # Sem dados comportamentais: apresentar opções por alias
            print("2. Apresentando opções...")
            for i, addr in enumerate(addresses):
                label = addr.get('alias') or addr.get('formattedAddress')
                print(f"   {i + 1}. {label}")
            return addresses[0]['addressId']  # escolha do usuário

        # Com dados comportamentais: inferir o endereço mais provável
        inferred = next(
            (a for a in addresses if a.get('isLastUsedAddress')), None
        ) or next(
            (a for a in addresses if a.get('isMostUsedAddress30d')), None
        ) or addresses[0]

        alias = inferred.get('alias') or inferred.get('formattedAddress')
        print(f"2. Sugerindo: {alias}")

        # Confirmar brevemente — nunca assumir em silêncio
        user_accepts = True  # simulado
        if user_accepts:
            print(f"Confirmado: addressId={inferred['addressId']}")
            return inferred['addressId']

        # Usuário rejeitou → apresentar opções
        for i, addr in enumerate(addresses):
            label = addr.get('alias') or addr.get('formattedAddress')
            print(f"   {i + 1}. {label}")
        return addresses[0]['addressId']  # escolha do usuário

    except Exception as error:
        print(f"ERRO: {str(error)}")
        raise
```

## Caso 4: Single-Shot (otimizado)

**Objetivo**: usuário forneceu endereço completo com complemento. O agente cria direto, sem confirmação extra.

**Fluxo**:

- `listAddresses()` → vazio
- Usuário: "Avenida Paulista, 100, Apto 72, chamar de Casa"
- `createAddress(address, complement, alias)` → `createdDirectly: true`
- Usar `addressId`

**JavaScript:**

```
async function createAddressSingleShot() {
  try {
    console.log("1. Listando endereços...");
    const listResult = await userClient.listAddresses();

    if (listResult.results.length > 0) {
      console.log("Usuário já tem endereços");
      return null;
    }

    console.log("Usuário forneceu: 'Avenida Paulista, 100, Apto 72'");

    // Criar direto (sem confirmação)
    console.log("2. Criando endereço (single-shot)...");
    const newAddress = await userClient.createAddress({
      address: "Avenida Paulista, 100",
      complement: "Apto 72",
      alias: "Casa"
    });

    if (newAddress.agentHints.createdDirectly) {
      console.log("Criado direto (single-shot)!");
      console.log(`   Alias: ${newAddress.alias}`);
      console.log(`   addressId: ${newAddress.addressId}`);
      return newAddress.addressId;
    } else {
      // Servidor degradou para candidatos → fallback two-step
      console.log("Requer confirmação (não foi single-shot)");
      return null;
    }

  } catch (error) {
    console.error(`ERRO: ${error.message}`);
    throw error;
  }
}
```

**Python:**

```
async def create_address_single_shot():
    try:
        print("1. Listando endereços...")
        list_result = await user_client.list_addresses()

        if len(list_result['results']) > 0:
            print("Usuário já tem endereços")
            return None

        # Criar direto
        new_addr = await user_client.create_address(
            address="Avenida Paulista, 100",
            complement="Apto 72",
            alias="Casa"
        )

        if new_addr.get('agentHints', {}).get('createdDirectly'):
            print(f"Criado direto! addressId: {new_addr['addressId']}")
            return new_addr['addressId']
        else:
            # Servidor degradou para candidatos → fallback two-step
            print("Requer confirmação")
            return None

    except Exception as error:
        print(f"ERRO: {str(error)}")
        raise
```

## Caso 5: Geocodificação omitiu o bairro

**Objetivo**: o endereço teve match único, mas a geocodificação retornou `neighborhood` vazio. O agente pergunta o bairro e reenvia.

**Fluxo**:

- `createAddress(address)` → match SINGLE, `neighborhood: ""`
- Perguntar: "Qual é o bairro?"
- `createAddress(candidateId, neighborhood, complement, ...)` → criar

**JavaScript:**

```
async function createAddressWithNeighborhood() {
  try {
    // Passo 1: Geocodificar
    const geocoding = await userClient.createAddress({
      address: "Rua Rio Grande do Sul, 44, Sonora, MS"
    });

    const candidate = geocoding.candidates[0];

    if (!candidate.location.neighborhood) {
      // Geocodificação omitiu o bairro — perguntar ao usuário
      console.log("Geocodificação omitiu o bairro. Perguntando ao usuário...");
      const bairro = "Centro"; // coletado do usuário

      // Passo 2: Reenviar com neighborhood
      const newAddress = await userClient.createAddress({
        candidateId: candidate.candidateId,
        address: "Rua Rio Grande do Sul, 44, Sonora, MS",
        neighborhood: bairro,
        complement: "Casa"
      });

      console.log(`Salvo com bairro ${bairro}: ${newAddress.addressId}`);
      return newAddress.addressId;
    }

    return null; // bairro presente — seguir normalmente

  } catch (error) {
    console.error(`ERRO: ${error.message}`);
    throw error;
  }
}
```

**Python:**

```
async def create_address_with_neighborhood():
    try:
        # Passo 1: Geocodificar
        geocoding = await user_client.create_address(
            address="Rua Rio Grande do Sul, 44, Sonora, MS"
        )

        candidate = geocoding['candidates'][0]

        if not candidate['location'].get('neighborhood'):
            print("Geocodificação omitiu o bairro. Perguntando ao usuário...")
            bairro = "Centro"  # coletado do usuário

            # Passo 2: Reenviar com neighborhood
            new_addr = await user_client.create_address(
                candidate_id=candidate['candidateId'],
                address="Rua Rio Grande do Sul, 44, Sonora, MS",
                neighborhood=bairro,
                complement="Casa"
            )

            print(f"Salvo com bairro {bairro}: {new_addr['addressId']}")
            return new_addr['addressId']

        return None

    except Exception as error:
        print(f"ERRO: {str(error)}")
        raise
```

## Boas práticas

Ao implementar fluxos do User MCP:

- **`listAddresses` sempre primeiro**: 0, 1 ou N endereços determina todo o fluxo.
- **Um endereço = usar direto**: informe o usuário, não espere confirmação.
- **Múltiplos endereços = inferir + confirmar**: use os campos comportamentais (`ordersByMerchantTypeWeekdayAndShift`, `isLastUsedAddress`, `isMostUsedAddress30d`); confirme brevemente pelo alias.
- **Sem dados comportamentais = apresentar opções**: quando `dataWarning` está presente, liste aliases e deixe o usuário escolher.
- **Armazene `addressId`, descarte `candidateId`**: `addressId` é permanente; `candidateId` é só para confirmação (e idempotência).
- **Use `alias` quando há múltiplos**: "Casa — Avenida Paulista, 100" é melhor do que só coordenadas.
- **Trate bairro ausente**: pergunte o bairro e reenvie via parâmetro `neighborhood` — nunca em `complement` ou `reference`.
- **Single-shot quando possível**: quando o usuário já deu `address + complement`, pule a confirmação extra.
- **Passe `addressId` / coordenadas aos próximos MCPs**: Offer Discovery e Cart os usam a jusante.

---

## Tools — /mcps/account/tools

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/tools

# User MCP - Tools

O User MCP oferece 3 tools atômicas para gerenciar identidade e endereços de entrega. Este guia documenta cada tool, seus parâmetros, respostas e exemplos de código.

## Visão geral

| Tool | Descrição | Quando usar |
| --- | --- | --- |
| [`getUser`](#getuser) | Obter nome, email, telefone, formas de pagamento e dados comportamentais | Personalização, saudações, descoberta de tiers |
| [`listAddresses`](#listaddresses) | Listar endereços de entrega salvos com padrões de uso | **SEMPRE primeiro** em qualquer fluxo de entrega |
| [`createAddress`](#createaddress) | Geocodificar e salvar um novo endereço de entrega | Após `listAddresses` retornar vazio ou usuário escolher "novo" |


## Índice rápido

- [`getUser`](#getuser) — Identidade do usuário com tiers baseados em escopos OAuth
- [`listAddresses`](#listaddresses) — Descoberta de endereços com inferência comportamental
- [`createAddress`](#createaddress) — Geocodificação two-step com confirmação, ou single-shot

## Convenções transversais

Todas as tools seguem estas convenções:

- **Chaves JSON**: `lowerCamelCase`
- **Identificadores**: UUID v4 para `addressId`; string opaca para `candidateId` (ex.: `cand-001`)
- **HTTP Status**: Sempre `200 OK` (JSON-RPC 2.0); erros vêm no corpo
- **Identidade**: o gateway injeta via header HTTP; o agente nunca fornece nem vê `userId`
- **Envelopes de resposta**: tools de leitura retornam `data`/`results`; erros retornam um objeto `errors`
- **agentHints**: Sempre presentes; orientam a próxima ação
- **Leitura vs Escrita**: `getUser` e `listAddresses` não têm efeitos colaterais; `createAddress` persiste

## Obter identidade e perfil do usuário

### `getUser`

Retorna o perfil do usuário autenticado — nome, email, telefone e, opcionalmente, formas de pagamento e dados comportamentais, conforme o tier de escopo OAuth (BASIC → ADVANCED → BEHAVIOR). Use para personalização, saudações e para validar quais escopos foram concedidos.

**Quando usar:**

- Saudar o usuário pelo nome (ponto de entrada da personalização)
- Entender o tier do perfil e a segmentação
- Obter formas de pagamento (tier ADVANCED+)
- Obter `taxPayerIdentificationNumber` (tier ADVANCED+)
- Acessar dados comportamentais para personalização (tier BEHAVIOR)

**Quando NÃO usar:**

- Para obter endereços, pedidos ou histórico de pagamento (use `listAddresses` ou outros domínios)
- Para descobrir quais formas de pagamento um estabelecimento aceita (use `listPaymentMethods` no Cart)
- Para fabricar ou adivinhar um `userId` (a identidade é injetada via header e invisível ao agente)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: Usuário autenticado via OAuth; o gateway injeta a identidade via header.

#### Tiers de resposta (baseados nos escopos OAuth)

O gateway determina qual tier retornar conforme os escopos concedidos ao agente:

| Tier | Escopos necessários | Campos retornados |
| --- | --- | --- |
| **BASIC** | `mcp.user.basic.read`, `mcp.user.addresses.read`, `mcp.user.addresses.write` | `fullName`, `email`, `phone` |
| **ADVANCED** | BASIC + `mcp.user.advanced.read` | BASIC + `taxPayerIdentificationNumber`, `paymentMethods` |
| **BEHAVIOR** | ADVANCED + `mcp.user.behavior.read` | ADVANCED + `profileData` (`hasClub`, `userBehaviorDescription`) |


#### Parâmetros

Nenhum — a identidade é injetada pelo gateway.

#### Resposta (Tier 1: BASIC)

```
{
  "success": true,
  "data": {
    "fullName": "João Silva",
    "email": "foodlover@ifood.com.br",
    "phone": "55119999999"
  },
  "agentHints": {
    "suggestedNextAction": "Use the user's name for personalization. Check if the user has saved delivery addresses before searching for restaurants or items."
  }
}
```

#### Resposta (Tier 2: ADVANCED)

```
{
  "success": true,
  "data": {
    "fullName": "João Silva",
    "email": "foodlover@ifood.com.br",
    "phone": "55119999999",
    "taxPayerIdentificationNumber": "11111111111",
    "paymentMethods": ["Cartão de Crédito", "Vale Refeição", "Pix"]
  },
  "agentHints": {
    "suggestedNextAction": "Use the user's name for personalization. Check if the user has saved delivery addresses before searching for restaurants or items."
  }
}
```

#### Resposta (Tier 3: BEHAVIOR)

```
{
  "success": true,
  "data": {
    "fullName": "João Silva",
    "email": "foodlover@ifood.com.br",
    "phone": "55119999999",
    "taxPayerIdentificationNumber": "11111111111",
    "paymentMethods": ["Cartão de Crédito", "Vale Refeição", "Pix"],
    "profileData": {
      "hasClub": true,
      "userBehaviorDescription": "## 1) User Profile & Persona\n\n### User Persona\nPizza lover who orders primarily on weekends. Prefers mid-range restaurants and occasionally browses premium options. Club iFood subscriber.\n\n### Motivation\nConvenience-driven — orders when cooking isn't an option. Weekend dinner is the primary use case.\n\n[...]"
    }
  },
  "agentHints": {
    "suggestedNextAction": "Use the user's name for personalization. Check if the user has saved delivery addresses before searching for restaurants or items."
  }
}
```

**Campos de resposta (Tier 1 — BASIC):**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `success` | boolean | `true` quando a operação foi concluída com sucesso. |
| `data` | object | Os dados do perfil do usuário, aninhados em `data`. |
| `data.fullName` | string | Nome completo do usuário, adequado para tratamento direto ("João Silva"). |
| `data.email` | string | Email do usuário autenticado. |
| `data.phone` | string | Telefone com código do país (ex.: `"55119999999"`). |
| `agentHints` | object | `suggestedNextAction` — orienta o agente a personalizar com o nome e verificar endereços salvos. |


**Campos de resposta (Tier 2 — ADVANCED, soma ao BASIC):**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `data.taxPayerIdentificationNumber` | string | CPF, ex.: `"11111111111"`. |
| `data.paymentMethods` | array de strings | Formas de pagamento salvas na conta, ordenadas pela mais usada recentemente. |


**Campos de resposta (Tier 3 — BEHAVIOR, soma ao ADVANCED):**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `data.profileData` | object | Dados de perfil e segmentação. |
| `data.profileData.hasClub` | boolean | Se o usuário é assinante do Club iFood. |
| `data.profileData.userBehaviorDescription` | string | String em Markdown com a saída do LCM (Large Commerce Model): persona, localização, padrões temporais, preferências alimentares, promoções, descoberta, social, avaliações, insights-chave e sinais de segmentação. |


#### Saída (Erro — falha de autenticação)

```
{
  "errors": {
    "mcpCode": -32302,
    "code": "AUTHENTICATION_REQUIRED",
    "message": "The user is not authenticated. This is a gateway configuration issue — the external agent cannot resolve it. Do not retry. Inform the user that their session may have expired and they should re-authenticate.",
    "suggestedAction": "Tell the user: 'I couldn't verify your identity. Please make sure you're logged into iFood.' Do not attempt any other identity or address operations until this is resolved.",
    "retryable": false
  }
}
```

## Descobrir endereços salvos

### `listAddresses`

Retorna todos os endereços de entrega ativos da conta com análises de uso — contagem de pedidos por dia e turno, afinidade de categoria, flags de último usado e mais usado. **PRIMEIRA chamada obrigatória em todo fluxo de compra.** O número de resultados (0, 1 ou N) determina toda a jornada.

**Quando usar:**

- **PRIMEIRO passo obrigatório** em qualquer fluxo de compra/entrega
- Para descobrir locais de entrega disponíveis
- Para decidir se cria um novo endereço (lista vazia) ou deixa o usuário escolher um existente
- Para obter coordenadas para consultas de Offer Discovery
- Para entender os padrões de entrega do usuário

**Quando NÃO usar:**

- Após etapas de descoberta/carrinho (o endereço DEVE vir primeiro)
- Para listar endereços arquivados ou excluídos (somente endereços ativos)
- Para salvar um novo endereço (use `createAddress`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: Usuário autenticado via gateway; sem parâmetros de entrada.

**Regra de ordenação:** Endereços com `alias` vêm primeiro, seguidos dos sem alias ordenados pelo mais recentemente criado/editado (até 20). Lista vazia quando não há endereços salvos.

#### Parâmetros

Nenhum — retorna todos os endereços ativos em uma única resposta.

#### Resposta (com endereços)

```
{
  "results": [
    {
      "addressId": "28e8f7e5-7970-46b0-9ab3-f93d155bbf47",
      "formattedAddress": "R. Anésio Lafayette Raizer, 157, Casa 14, Vila José Iório, Campinas, SP",
      "alias": "Casa",
      "location": {
        "street": "R. Anésio Lafayette Raizer",
        "number": "157",
        "neighborhood": "Vila José Iório",
        "city": "Campinas",
        "state": "SP"
      },
      "postalCode": "13105532",
      "complement": "Casa 14",
      "reference": "Próximo ao Platz Mall",
      "coordinates": {
        "latitude": -22.882708,
        "longitude": -46.970348
      },
      "isLastUsedAddress": true,
      "isMostUsedAddress30d": true,
      "topMerchantTypes": {
        "DRUGSTORE": "1",
        "GROCERIES": "1",
        "RESTAURANT": "10"
      },
      "topWeekDayShift": {
        "Friday dinner": "3",
        "Friday snack": "1",
        "Monday dinner": "2",
        "Sunday lunch": "2",
        "Sunday snack": "1",
        "Tuesday dinner": "1",
        "Wednesday dinner": "2"
      },
      "ordersByMerchantTypeWeekdayAndShift": {
        "DRUGSTORE": {
          "Sunday": { "lunch": "1" }
        },
        "GROCERIES": {
          "Sunday": { "snack": "1" }
        },
        "RESTAURANT": {
          "Friday": { "dinner": "3", "snack": "1" },
          "Monday": { "dinner": "2" },
          "Sunday": { "lunch": "1" },
          "Tuesday": { "dinner": "1" },
          "Wednesday": { "dinner": "2" }
        }
      }
    }
  ],
  "agentHints": {
    "addressCount": 1,
    "suggestedNextAction": "Single saved address — use it as the delivery address without waiting for confirmation. Inform the user which address is being used (prefer the alias when available). Let them know they can provide a new address if it is not correct.",
    "nextStepWhenUserPicksAddress": "Use the coordinates (latitude/longitude) from this address immediately to find nearby restaurants and items. Inform the user which address is being used (prefer the alias). Tell them they can provide a new address if it is not correct."
  }
}
```

**Campos de resposta:**

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `results` | array | Todos os endereços ativos, com alias primeiro, depois os mais recentemente criados/editados (até 20). |
| `addressId` | string | Identificador persistente da conta. Use nas tools de Offer Discovery e Cart. |
| `formattedAddress` | string | String de exibição completa, formato `{street}, {number}, {complement}, {neighborhood}, {city}, {state}`. NÃO inclui CEP nem `reference`. |
| `alias` | string | null | Rótulo amigável ("Casa", "Trabalho"). Prefira este sobre `formattedAddress` ao apresentar opções. |
| `location` | object | Componentes normalizados: `street`, `number`, `neighborhood`, `city`, `state`. `number` pode estar ausente. |
| `postalCode` | string | CEP sem máscara (ex.: `"13105532"`). |
| `complement` | string | null | Apartamento, bloco ou outro complemento. |
| `reference` | string | null | Ponto de referência para entrega ("Próximo ao Platz Mall", "Portão azul"). |
| `coordinates` | object | `latitude` e `longitude` para raio de entrega e roteamento. |
| `isLastUsedAddress` | boolean | True se foi o endereço usado no pedido mais recente. |
| `isMostUsedAddress30d` | boolean | True se tem a maior contagem de uso nos últimos 30 dias. |
| `topMerchantTypes` | map | Tipos de estabelecimento mais pedidos neste endereço. Chaves são valores do enum `merchantType` (`RESTAURANT`, `DRUGSTORE`, `GROCERIES`, `PETSTORE`, `LIQUORSTORE`, `SHOPPING`); valores são contagens em string. |
| `topWeekDayShift` | map | Combinações dia+turno mais pedidas. Chaves são `"{Weekday} {shift}"` (ex.: `"Friday dinner"`); valores são contagens em string. |
| `ordersByMerchantTypeWeekdayAndShift` | map | Tabela cruzada por tipo de estabelecimento × dia da semana × turno. Sinal primário para casar a intenção do usuário a um endereço. |


**Nota sobre formato das contagens:** Todas as contagens nos três mapas comportamentais são **strings** (ex.: `"10"`), não inteiros — converta antes de fazer aritmética. Chaves de dia são capitalizadas (`"Friday"`); chaves de turno são minúsculas (`"dinner"`).

#### Inferência comportamental (múltiplos endereços)

Quando o usuário tem vários endereços e há dados comportamentais, `agentHints.suggestedNextAction` instrui o agente a **inferir** o endereço mais provável em vez de listar todas as opções. Os campos usados na inferência são:

| Campo | Uso na inferência |
| --- | --- |
| `ordersByMerchantTypeWeekdayAndShift` | Sinal primário — casar a intenção (categoria + dia/turno) |
| `isLastUsedAddress` | Desempate — endereço do pedido mais recente |
| `isMostUsedAddress30d` | Desempate — maior uso nos últimos 30 dias |
| `topMerchantTypes` | Afinidade de categoria neste endereço |
| `topWeekDayShift` | Padrões de dia+turno |


**Prioridade da inferência:** (1) casar a intenção com `ordersByMerchantTypeWeekdayAndShift`; (2) `isLastUsedAddress`; (3) `isMostUsedAddress30d`. Confirme brevemente pelo alias (ex.: "Entregar na Casa?") — nunca assuma em silêncio.

#### agentHints — seleção de endereço

| Cenário | `addressCount` | Hints retornados | Comportamento do agente |
| --- | --- | --- | --- |
| Sem endereços | — (omitido) | `noResultsGuidance` | Pedir endereço; salvar na conta |
| Endereço único | `1` | `suggestedNextAction`, `nextStepWhenUserPicksAddress` | Usar imediatamente; informar; sem confirmação |
| Múltiplos + dados comportamentais | `N` | `addressCount`, `suggestedNextAction`, `nextStepWhenUserPicksAddress` | Inferir o mais provável; confirmar em uma pergunta; listar só se rejeitar |
| Múltiplos, sem dados comportamentais | `N` | `addressCount`, `suggestedNextAction`, `dataWarning`, `nextStepWhenUserPicksAddress` | Apresentar opções por alias; não inferir |


#### Resposta (lista vazia)

```
{
  "results": [],
  "agentHints": {
    "noResultsGuidance": "No saved addresses found. Ask the user for their delivery address as a free-form string (e.g., 'Avenida Paulista, 100, São Paulo, SP'), then save it on the user's account."
  }
}
```

#### Resposta (múltiplos endereços, sem dados comportamentais)

```
{
  "results": [
    { "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2", "alias": "Casa", "formattedAddress": "Avenida Paulista, 100, Bela Vista, São Paulo, SP" },
    { "addressId": "ca2b81f4-d4a8-5f31-88b2-64e7771d28g3", "alias": "Trabalho", "formattedAddress": "Rua Canário, 981, Moema, São Paulo, SP" }
  ],
  "agentHints": {
    "addressCount": 2,
    "suggestedNextAction": "Multiple saved addresses and behavioral data is unavailable. Present options to the user by alias when available (Casa, Trabalho) and ask which one to use for delivery.",
    "dataWarning": "Behavioral data is unavailable for this call. Do not infer a preferred address — present saved options and ask the user to choose.",
    "nextStepWhenUserPicksAddress": "After the user confirms the delivery address (whether inferred or explicitly chosen), use its coordinates (latitude/longitude) to find nearby restaurants and items. If you inferred the address from behavioral data, you must get confirmation before proceeding. If the user wants a different address, collect it as a free-form string and save it on the user's account."
  }
}
```

#### Saída (Erro — serviço indisponível)

```
{
  "errors": {
    "mcpCode": -32502,
    "code": "SERVICE_UNAVAILABLE",
    "message": "The address service is temporarily unavailable. Do not retry immediately. Inform the user that address lookup is down and suggest they try again in a few minutes. You can proceed to Offer Discovery with a user-provided location if available.",
    "suggestedAction": "Tell the user: 'I'm having trouble accessing your saved addresses. You can tell me your delivery address directly if you know it, or we can wait a moment and try again.'",
    "retryable": true
  }
}
```

## Geocodificar e persistir novo endereço

### `createAddress`

Geocodifica uma string de endereço livre, retorna candidatos para confirmação do usuário e então persiste o endereço escolhido. Suporta dois fluxos: (1) **two-step** — geocodificar → confirmar → criar, e (2) **single-shot** — quando o usuário fornece endereço + complemento de uma vez e o match é SINGLE, cria diretamente. A geocodificação é encapsulada — o agente nunca chama uma tool de geocodificação separada.

**Quando usar:**

- Após `listAddresses` retornar vazio (usuário sem endereços salvos)
- Quando o usuário escolhe adicionar um novo endereço (após ver os salvos)
- Two-step: geocodificar, confirmar com o usuário e criar (inclua `neighborhood` quando a geocodificação omitir)
- Single-shot: criar diretamente quando o usuário forneceu todos os essenciais e o bairro é resolvível

**Quando NÃO usar:**

- Antes de chamar `listAddresses` (descoberta de endereço primeiro)
- Fabricando strings de endereço (colete do usuário)
- Sem `address` (mínimo obrigatório)
- Adivinhando `candidateId` (obtenha de uma resposta de geocodificação)
- Colocando bairro em `complement` ou `reference` (use `neighborhood`)

**Efeitos colaterais:** Cria um novo endereço na conta. Two-step: apenas na confirmação com `candidateId`. Single-shot: na primeira chamada se SINGLE e bairro resolvível. Idempotente via `candidateId`.

#### Resolução de bairro

A validação de endereço brasileira exige `neighborhood` (bairro). Provedores de geocodificação podem omiti-lo — especialmente em municípios pequenos. O servidor resolve o bairro nesta ordem antes de persistir:

- **Parâmetro explícito `neighborhood`** — maior prioridade; use quando a geocodificação omitir ou o usuário corrigir.
- **Valor geocodificado** — `candidates[].location.neighborhood`.
- **Fallback da consulta de endereço** — extração best-effort do token entre número e cidade (ex.: `"Rua X, 44, Centro, Sonora, MS"` → `"Centro"`).

Se nada resolver, a persistência é bloqueada com `MISSING_NEIGHBORHOOD` (two-step) ou o servidor retorna candidatos com orientação para coletar o bairro (degradação do single-shot).

**Regras do agente:**

- Verifique `candidates[].location.neighborhood` após geocodificar. Se vazio, pergunte: "Qual é o bairro?"
- Reenvie com `candidateId` + `neighborhood` na confirmação.
- Nunca codifique o bairro em `complement` ou `reference`.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `address` | string | sim | String de endereço livre (ex.: `"Avenida Paulista, 100, São Paulo, SP"`). |
| `neighborhood` | string | condicional | Bairro. Obrigatório quando a geocodificação não retornar e o fallback não resolver. Envie na confirmação (com `candidateId`) ou no single-shot. Sobrescreve o bairro geocodificado. |
| `alias` | string | não | Rótulo amigável ("Casa", "Trabalho"). Fortemente recomendado quando o usuário tem outros endereços. |
| `complement` | string | não | Apartamento, bloco ou outro complemento (ex.: `"Apto 72"`). |
| `reference` | string | não | Ponto de referência ("Portão azul", "Perto do mercado"). |
| `candidateId` | string | condicional | Obrigatório para confirmar e criar. Vem do candidato escolhido em uma resposta `candidates[]`. Também é a chave de idempotência. |


#### Passo 1: Geocodificação (sem efeitos colaterais)

Chame `createAddress(address)` para geocodificar. Retorna `matchConfidence` com candidatos:

**Candidato único:**

```
{
  "matchConfidence": "SINGLE",
  "candidates": [
    {
      "candidateId": "cand-001",
      "formattedAddress": "Avenida Paulista, 100, Bela Vista, São Paulo, SP, CEP 01310-100",
      "location": {
        "street": "Avenida Paulista",
        "number": "100",
        "neighborhood": "Bela Vista",
        "city": "São Paulo",
        "state": "SP"
      },
      "postalCode": "01310-100",
      "coordinates": {
        "latitude": -23.561414,
        "longitude": -46.656139
      }
    }
  ],
  "agentHints": {
    "confirmAddressGuidance": "The address 'Avenida Paulista, 100' matched a single location. Confirm with the user and ask together: 'Avenida Paulista, 100, Bela Vista, São Paulo, SP, CEP 01310-100 — confirm? What's the complement and a nickname, like Casa or Trabalho? A delivery reference?' Then re-submit with the same address, plus alias, complement, reference, neighborhood (if geocoding omitted it), and the candidateId."
  }
}
```

**Candidato único — geocodificação omitiu o bairro:**

```
{
  "matchConfidence": "SINGLE",
  "candidates": [
    {
      "candidateId": "cand-002",
      "formattedAddress": "Rua Rio Grande do Sul, 44, Sonora, MS, CEP 79400-000",
      "location": {
        "street": "Rua Rio Grande do Sul",
        "number": "44",
        "neighborhood": "",
        "city": "Sonora",
        "state": "MS"
      },
      "postalCode": "79400-000",
      "coordinates": {
        "latitude": -17.57,
        "longitude": -54.75
      }
    }
  ],
  "agentHints": {
    "confirmAddressGuidance": "The address matched a single location. Geocoding did not return neighborhood (bairro). Ask the user explicitly for the neighborhood, then re-submit with the same address, candidateId, neighborhood, and optional complement, alias, and reference to create the address."
  }
}
```

**Múltiplos candidatos:**

```
{
  "matchConfidence": "MULTIPLE",
  "candidates": [
    {
      "candidateId": "cand-001",
      "formattedAddress": "Avenida Paulista, 100, Bela Vista, São Paulo, SP, CEP 01310-100",
      "location": { "street": "Avenida Paulista", "number": "100", "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP" },
      "postalCode": "01310-100",
      "coordinates": { "latitude": -23.561414, "longitude": -46.656139 }
    },
    {
      "candidateId": "cand-002",
      "formattedAddress": "Avenida Paulista, 100, Paraíso, São Paulo, SP, CEP 01310-101",
      "location": { "street": "Avenida Paulista", "number": "100", "neighborhood": "Paraíso", "city": "São Paulo", "state": "SP" },
      "postalCode": "01310-101",
      "coordinates": { "latitude": -23.573254, "longitude": -46.645012 }
    }
  ],
  "agentHints": {
    "confirmAddressGuidance": "The address 'Avenida Paulista, 100' matched multiple locations in São Paulo. Present the candidates to the user by formattedAddress and ask for confirmation, together with: '[formattedAddress] — confirm? What's the complement and a nickname, like Casa or Trabalho? A delivery reference?' If any candidate has an empty neighborhood, ask for bairro and include neighborhood on re-submit."
  }
}
```

#### Criação single-shot

Quando o usuário fornece `address` (rua + número) e `complement` em uma única interação, a geocodificação retorna um match SINGLE e o bairro é resolvível, o agente pode pular a confirmação e criar diretamente em uma chamada.

**Pré-condições do single-shot:** match SINGLE; usuário forneceu `address` + `complement`; bairro resolvível. Retorna `createdDirectly: true` em `agentHints`.

```
{
  "matchConfidence": "SINGLE",
  "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  "formattedAddress": "Avenida Paulista, 100, Apto 72, Bela Vista, São Paulo, SP, CEP 01310-100",
  "alias": null,
  "location": { "street": "Avenida Paulista", "number": "100", "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP" },
  "postalCode": "01310-100",
  "complement": "Apto 72",
  "reference": null,
  "coordinates": { "latitude": -23.561414, "longitude": -46.656139 },
  "agentHints": {
    "nextStepWhenUserPicksAddress": "Address created and saved. Use the coordinates (latitude/longitude) from this address to find nearby restaurants and items.",
    "createdDirectly": true
  }
}
```

**Quando NÃO usar single-shot:**

- `matchConfidence` é `"MULTIPLE"` → sempre confirme com o usuário
- Usuário NÃO forneceu `complement` → colete antes de criar
- Bairro não resolvível → colete o bairro primeiro (o servidor degrada para candidatos)
- O agente está inseguro sobre qualquer campo → confirme antes de criar

#### Passo 2: Confirmação e criação

Após o usuário confirmar, chame `createAddress` com `candidateId` + `complement`, `alias`, `reference` (e `neighborhood` quando necessário):

```
{
  "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  "formattedAddress": "Avenida Paulista, 100, Bela Vista, São Paulo, SP, CEP 01310-100",
  "alias": "Casa",
  "location": { "street": "Avenida Paulista", "number": "100", "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP" },
  "postalCode": "01310-100",
  "complement": "Apto 72",
  "reference": "Portão azul",
  "coordinates": { "latitude": -23.561414, "longitude": -46.656139 },
  "agentHints": {
    "nextStepWhenUserPicksAddress": "Address saved. Use the coordinates (latitude/longitude) from this address to find nearby restaurants and items."
  }
}
```

**Idempotência:** `candidateId` é a chave de idempotência. Chamadas duplicadas de confirmação com o mesmo `candidateId` e mesmos parâmetros retornam `agentHints.alreadyExists: true` (não é erro). Chamadas duplicadas com o mesmo `candidateId` mas parâmetros diferentes retornam `CANDIDATE_ID_CONFLICT`.

```
{
  "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  "formattedAddress": "Avenida Paulista, 100, Bela Vista, São Paulo, SP, CEP 01310-100",
  "alias": "Casa",
  "location": { "street": "Avenida Paulista", "number": "100", "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP" },
  "postalCode": "01310-100",
  "complement": "Apto 72",
  "reference": "Portão azul",
  "coordinates": { "latitude": -23.561414, "longitude": -46.656139 },
  "agentHints": {
    "nextStepWhenUserPicksAddress": "This address was already created (idempotent response). Use the coordinates to find nearby restaurants — no need to create it again.",
    "alreadyExists": true
  }
}
```

#### Campos de resposta (endereço criado)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `addressId` | string | Identificador persistente da conta. Use nas tools de Offer Discovery e Cart. |
| `formattedAddress` | string | String completa incluindo CEP. Two-step: `{street}, {number}, {neighborhood}, {city}, {state}, CEP {postalCode}`. Single-shot: inclui `complement` antes do `neighborhood`. |
| `alias` | string | null | Rótulo amigável ("Casa", "Trabalho"). |
| `location` | object | Componentes normalizados: `street`, `number`, `neighborhood`, `city`, `state`. |
| `postalCode` | string | CEP do endereço validado. |
| `complement` | string | null | Apartamento, bloco ou outro complemento. |
| `reference` | string | null | Ponto de referência ("Portão azul", "Perto do mercado"). |
| `coordinates` | object | `latitude` e `longitude` para raio de entrega e roteamento. |


## Erros comuns dos agentes

- **Pular `listAddresses`:** pular para a criação de endereço antes de verificar os salvos faz o usuário reinserir informações que já forneceu. Sempre liste primeiro.
- **Listar todos os endereços quando há dados comportamentais:** quando `agentHints.suggestedNextAction` instrui inferência, não apresente todos os endereços por padrão. Infira o mais provável, confirme brevemente e liste todas as opções só se o usuário rejeitar ou pedir.
- **Inferir sem confirmação (múltiplos endereços):** obtenha uma breve confirmação do usuário antes de prosseguir — nunca assuma em silêncio. Não se aplica quando há só um endereço salvo.
- **Esperar campos de endereço explícitos:** `createAddress` aceita uma única string `address`. Não divida em rua/número/cidade/estado — exceto `neighborhood`, que tem um parâmetro dedicado.
- **Ignorar bairro ausente:** quando `candidates[].location.neighborhood` estiver vazio ou a orientação pedir bairro, pergunte ao usuário e reenvie com `neighborhood`. Não coloque bairro em `complement` ou `reference`.
- **Não pedir `alias` em novos endereços:** quando o usuário já tem 1+ endereços salvos, sempre sugira um alias para o novo.

## Segurança e identidade

Todas as tools do User MCP recebem a identidade do usuário **automaticamente via header HTTP do gateway**:

- O agente externo **nunca** fornece nem vê `userId`
- O gateway injeta a identidade de forma transparente a partir do token OAuth
- Apenas o usuário autenticado acessa seus próprios dados

`getUser` retorna `fullName` para personalização; as tools de endereço retornam identificadores de domínio (`addressId`). O `userId` subjacente nunca é exposto.

## Fluxo completo: entrada para saída

```
1. getUser()
   └─ Saudar o usuário pelo nome (personalização)

2. listAddresses()  ← SEMPRE primeiro
   ├─ vazio          → coletar novo endereço (passo 3)
   ├─ 1 endereço     → usar direto; informar (sem confirmação)
   └─ N endereços    → inferir (com dados comportamentais) e confirmar, ou apresentar opções

3. createAddress()
   ├─ Passo 1: geocodificar → matchConfidence + candidates[]
   ├─ (single-shot se aplica) → criar direto
   ├─ (caso contrário) confirmar com o usuário
   └─ Passo 2: confirmar e criar → addressId permanente

4. Usar addressId / coordenadas nos próximos MCPs
   ├─ Offer Discovery: encontrar restaurantes e itens
   ├─ Cart: criar carrinho e definir entrega
   └─ Order Tracking: rastrear pedido
```

**Regra crítica**: `listAddresses` é SEMPRE o ponto de entrada. Nunca comece com `createAddress`.

---

## Introdução — /mcps/account/introducao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/account/introducao

# O que é o User MCP?

O User MCP gerencia identidade do usuário e endereços de entrega. Ele responde a três perguntas que todo agente faz em cada fluxo de compra:

- **"Quem é este usuário?"** — `getUser` retorna nome, email, telefone e dados comportamentais opcionais
- **"Onde posso entregar?"** — `listAddresses` lista endereços salvos com análises de uso
- **"Como salvo um novo endereço?"** — `createAddress` geocodifica e persiste endereços na conta

## Problemas que resolve

- **Identidade sem vazamento**: o agente externo aprende o nome do usuário, mas nunca vê `userId`. A identidade é injetada pelo gateway via header HTTP.
- **Descoberta de endereço antes da busca**: agentes que pulam `listAddresses` gastam tokens geocodificando endereços que o usuário já tem salvos.
- **Geocodificação encapsulada**: `createAddress` aceita uma string de endereço crua e trata a geocodificação internamente — sem tool de geocodificação separada.
- **Aliases para conversa natural**: endereços têm um `alias` opcional ("Casa", "Trabalho") para o agente usar linguagem natural em vez de recitar endereços completos.

## Fora do escopo

- **Autenticação e login**: domínio upstream; o User MCP assume um usuário já autenticado
- **Histórico e status de pedidos**: Order Tracking MCP
- **Processamento de pagamento**: domínio de Payments
- **Catálogo de estabelecimentos e itens**: Offer Discovery MCP

## Responsabilidades

| Responsabilidade | Quem | Descrição |
| --- | --- | --- |
| Mapear intenção → tool; sequência de operações | Agente externo (LLM) | O agente interpreta o que o usuário quer e orquestra as chamadas na ordem correta |
| Coletar localização e preferências do usuário | Agente externo (LLM) | Alias, complemento, referência, rua, número, cidade, estado, bairro |
| Apresentar opções de endereço com aliases | Agente externo (LLM) | O agente mostra "Casa", "Trabalho" e deixa o usuário escolher |
| Injetar identidade (via header HTTP) do token autenticado | Gateway agêntico | Transparente ao agente externo |
| Validar entrada e executar apenas a operação invocada | Servidor User MCP | O servidor valida e executa exatamente a operação solicitada |
| Retornar estado do endereço e erros acionáveis | Servidor User MCP | Respostas incluem `agentHints` para orientar o agente |


## Três tools atômicas

O User MCP expõe 3 operações, cada uma com um propósito específico:

| Tool | Quando usar | Retorna |
| --- | --- | --- |
| `getUser` | Personalização, saudações, descoberta de tiers | Nome, email, telefone, formas de pagamento, dados comportamentais (por tier) |
| `listAddresses` | **SEMPRE primeiro** em qualquer fluxo de entrega | Endereços salvos com análises comportamentais |
| `createAddress` | Após `listAddresses` retornar vazio ou usuário escolher "novo" | `addressId` permanente + coordenadas |


## Fluxo por cenário

A escolha de qual tool chamar é determinada pela resposta de `listAddresses()` — que é **sempre** a primeira chamada:

```
┌─ listAddresses()
│
├─ results: [] (vazio)
│  └─ Sem endereço salvo
│     ├─ Agente pergunta o endereço (ex. "Avenida Paulista, 100, São Paulo, SP")
│     ├─ createAddress(address) → geocodificar → confirmar → criar
│     │     (ou single-shot quando endereço + complemento fornecidos)
│     └─ addressId pronto para Offer Discovery
│
├─ results: [1] (um endereço)
│  └─ Um endereço encontrado
│     ├─ Usar direto — informar o usuário, sem confirmação
│     ├─ Preferir alias sobre formattedAddress ("Entregando na Casa")
│     └─ Usuário pode fornecer um novo se não estiver correto
│
└─ results: [2+] (múltiplos)
   └─ Múltiplos endereços encontrados
      ├─ Dados comportamentais disponíveis? (sem dataWarning)
      │  ├─ SIM → inferir o mais provável; confirmar brevemente pelo alias
      │  └─ NÃO  → apresentar opções por alias; pedir para o usuário escolher
      ├─ Usuário confirma → usar addressId / coordenadas
      └─ Usuário quer novo → fluxo createAddress
```

### Por que `listAddresses()` é SEMPRE primeiro?

- **Evita trabalho redundante**: o usuário com 3 endereços salvos não precisa de um 4º geocodificado.
- **Permite conversa natural**: "Entregar na Casa?" é melhor do que recitar um endereço completo.
- **Ponto de bifurcação determinístico**: o resultado (vazio, 1 ou N) determina toda a interação.
- **Checagem de custo zero**: sem parâmetros, retorna instantaneamente.

### Fluxo de criação: Two-Step + Single-Shot

Quando o usuário não tem endereço ou quer um novo, `createAddress()` oferece dois caminhos:

**Caminho A: Two-Step (padrão)**

```
Usuário: "Rua Augusta, 500"
  ↓
createAddress(address="Rua Augusta, 500")
  → matchConfidence: "SINGLE" ou "MULTIPLE"
  → candidates[] com formattedAddress + candidateId
  ↓
Agente confirma: "Rua Augusta, 500, São Paulo — confirma? Complemento, alias, referência?"
  (se o bairro foi omitido: perguntar "Qual é o bairro?")
  ↓
createAddress(candidateId, complement, alias, reference, neighborhood)
  → addressId permanente
```

**Caminho B: Single-Shot (otimizado)**

```
Usuário: "Avenida Paulista, 100, Apto 72 — chamar de Casa"
  ↓
createAddress(address="Avenida Paulista, 100", complement="Apto 72", alias="Casa")
  → match SINGLE + bairro resolvível
  → createdDirectly: true
  → addressId permanente (sem confirmação extra)
```

## Guia de decisão: qual tool chamar

| Você quer... | Use esta tool | Quando |
| --- | --- | --- |
| Saudar pelo nome; acessar perfil e dados comportamentais | `getUser` | Início de qualquer conversa |
| Descobrir endereços salvos | `listAddresses` | **SEMPRE PRIMEIRO** em qualquer fluxo de entrega |
| Criar novo endereço; geocodificar | `createAddress` | Após `listAddresses` retornar vazio OU usuário escolher "novo" |


## Conceitos essenciais

### `addressId` é permanente; `candidateId` é descartável

- **`candidateId`**: identificador temporário de um candidato retornado pelo `createAddress` passo 1. Usado apenas para confirmar e criar. **Não armazene.** Também é a chave de idempotência.
- **`addressId`**: identificador permanente do endereço SALVO na conta. Armazene e reutilize em pedidos futuros (Offer Discovery, Cart, etc.).

### `alias` melhora muito a UX

- Quando o usuário tem 1 endereço: alias é opcional.
- Quando tem 2+: **sempre recomende um alias** ("Casa", "Trabalho", "Casa da mãe").
- Ao apresentar múltiplos endereços: mostre o alias primeiro ("Casa — Avenida Paulista, 100").

### Mapas comportamentais permitem sugestões inteligentes

Cada endereço em `listAddresses` inclui análises comportamentais usadas para inferir o endereço mais provável:

- **`ordersByMerchantTypeWeekdayAndShift`**: sinal primário — cruzamento tipo de estabelecimento × dia × turno. Case a intenção ("pizza na sexta à noite") a um endereço.
- **`topMerchantTypes`** e **`topWeekDayShift`**: afinidade de categoria e dia+turno.
- **`isLastUsedAddress`** / **`isMostUsedAddress30d`**: critérios de desempate.

Todas as contagens são strings (ex.: `"10"`). Converta antes de fazer aritmética.

### Convenções

- **Chaves JSON**: `lowerCamelCase`
- **Identificadores**: UUID v4 para `addressId`; string opaca para `candidateId`
- **HTTP Status**: Sempre `200 OK` (JSON-RPC 2.0); erros vêm no corpo
- **Identidade**: gateway injeta via header; o agente nunca vê `userId`

---

## Erros — /mcps/discovery/erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/erros

# Erros

O Offer Discovery MCP retorna erros estruturados inline no corpo da resposta. Entender os tipos de erro e as estratégias de retry ajuda a construir fluxos robustos.

## Protocolo de erro

Todas as tools retornam erros no corpo, com esta estrutura:

```
{
  "errors": {
    "message": "The search query is empty or contains only qualifiers ('cheap', 'near', 'fast'). Move qualifiers to refinements (maxItemPrice, maxDistanceKm, maxDeliveryTimeMinutes) and put descriptive terms in query.",
    "code": "INVALID_QUERY",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user to describe what kind of food or item they want. Use a descriptive term like 'pizza', 'sushi', 'vegan burger'.",
    "retryable": true
  }
}
```

**Campos importantes:**

- **`message`**: descrição do que deu errado e por quê
- **`code`**: tipo do erro (ex. `INVALID_QUERY`, `MERCHANT_NOT_FOUND`)
- **`mcpCode`**: código JSON-RPC (inteiro negativo). Todas as tools de Offer Discovery usam `-32301`
- **`suggestedAction`**: o que o agente deve dizer/fazer em seguida
- **`retryable`**: se vale a pena repetir a chamada com os mesmos parâmetros

## Taxonomia de erros

| Código | Tool | Retry? | Causas | O que fazer |
| --- | --- | --- | --- | --- |
| `INVALID_QUERY` | `searchOffers` | Sim | `query` vazia ou só com qualificadores ("barato", "perto") | Pedir ao usuário um termo descritivo; mover qualificadores para `refinements` |
| `MISSING_LOCATION` | `searchOffers` | Sim | `userLocation` ausente | Perguntar o endereço de entrega |
| `MISSING_MERCHANT_VERTICAL` | `browseOffers` | Sim | `merchantType` ausente | Perguntar que tipo de loja o usuário quer navegar |
| `INCOMPATIBLE_RESULT_KIND` | `getRecommendations` | Sim | `resultKind` incompatível com `contentMode` | Trocar `resultKind` ou `contentMode` |
| `UNKNOWN_TAXONOMY_ID` | `listItemTaxonomy` | Não | ID de taxonomia não existe ou não tem sub-categorias | Voltar ao nível raiz e apresentar categorias válidas |
| `INVALID_MERCHANT_VERTICAL` | `listItemTaxonomy` | Sim | `merchantType` inválido | Usar um dos 6 valores válidos |
| `MERCHANT_NOT_FOUND` | `getMerchant` | Não | ID de parceiro não existe ou indisponível na área | Voltar aos resultados e oferecer alternativas |
| `MERCHANT_CLOSED` | `getMerchant` | Não | Parceiro fechado no momento | Informar quando abre; oferecer outros parceiros abertos |
| `ITEM_NOT_FOUND` | `getItem` | Não | ID de item não existe ou foi removido do cardápio | Voltar ao catálogo e oferecer alternativas |
| `ITEM_MERCHANT_MISMATCH` | `getItem` | Sim | `itemId` não pertence ao `merchantId` informado | Usar o `merchantId` que veio junto do `itemId` |


Todos os códigos usam `mcpCode -32301`. A distinção entre cenários é feita pelo campo `code`, não pelo `mcpCode`.

## Exemplos completos de erro

### `INVALID_QUERY`

```
{
  "errors": {
    "message": "The search query is empty or contains only qualifiers ('cheap', 'near', 'fast'). Move qualifiers to refinements (maxItemPrice, maxDistanceKm, maxDeliveryTimeMinutes) and put descriptive terms in query.",
    "code": "INVALID_QUERY",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user to describe what kind of food or item they want. Use a descriptive term like 'pizza', 'sushi', 'vegan burger'.",
    "retryable": true
  }
}
```

### `MISSING_LOCATION`

```
{
  "errors": {
    "message": "No delivery location provided. The user's location is required to search for nearby options.",
    "code": "MISSING_LOCATION",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user where they want delivery. Check the user's saved delivery addresses, or ask for a street address.",
    "retryable": true
  }
}
```

### `MISSING_MERCHANT_VERTICAL`

```
{
  "errors": {
    "message": "merchantType is required for browseOffers. Choose from: RESTAURANT, GROCERIES, LIQUORSTORE, DRUGSTORE, PETSTORE, SHOPPING.",
    "code": "MISSING_MERCHANT_VERTICAL",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user what kind of store or category they want to browse.",
    "retryable": true
  }
}
```

### `INCOMPATIBLE_RESULT_KIND`

```
{
  "errors": {
    "message": "FAVORITE_MERCHANTS only supports resultKind=MERCHANT. Change resultKind to MERCHANT or select a different contentMode.",
    "code": "INCOMPATIBLE_RESULT_KIND",
    "mcpCode": -32301,
    "suggestedAction": "Set resultKind to MERCHANT or use contentMode RECOMMENDED for item results.",
    "retryable": true
  }
}
```

### `UNKNOWN_TAXONOMY_ID`

```
{
  "errors": {
    "message": "The taxonomy ID 'id_inventado' does not exist in the RESTAURANT vertical or has no sub-categories. Use the root level or try a valid ID from the taxonomy response.",
    "code": "UNKNOWN_TAXONOMY_ID",
    "mcpCode": -32301,
    "suggestedAction": "Retrieve the root categories for this vertical and present them to the user.",
    "retryable": false
  }
}
```

### `INVALID_MERCHANT_VERTICAL`

```
{
  "errors": {
    "message": "Invalid merchantType 'INVALID_VERTICAL'. Valid values: RESTAURANT, GROCERIES, LIQUORSTORE, DRUGSTORE, PETSTORE, SHOPPING.",
    "code": "INVALID_MERCHANT_VERTICAL",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user which type of store they're interested in.",
    "retryable": true
  }
}
```

### `MERCHANT_NOT_FOUND`

```
{
  "errors": {
    "message": "The merchant ID 'ffffffff-eeee-dddd-cccc-bbbbaaaa9999' was not found or is not available in your area. Do not retry this ID.",
    "code": "MERCHANT_NOT_FOUND",
    "mcpCode": -32301,
    "suggestedAction": "Return to the previous search results and present the user with alternative merchants.",
    "retryable": false
  }
}
```

### `MERCHANT_CLOSED`

```
{
  "errors": {
    "message": "Pizza Express is currently closed. It opens today at 17:00.",
    "code": "MERCHANT_CLOSED",
    "mcpCode": -32301,
    "suggestedAction": "Tell the user the merchant is closed and when it opens. Offer to browse other open merchants from the previous search.",
    "retryable": false
  }
}
```

### `ITEM_NOT_FOUND`

```
{
  "errors": {
    "message": "The item ID 'a1b2c3d4-0001-4000-8000-000000009999' was not found at merchant 'b8f3c1e2-a456-7890-1234-567890abcdef'. It may have been removed from the menu.",
    "code": "ITEM_NOT_FOUND",
    "mcpCode": -32301,
    "suggestedAction": "Return to the merchant's catalog and present alternative items to the user.",
    "retryable": false
  }
}
```

### `ITEM_MERCHANT_MISMATCH`

```
{
  "errors": {
    "message": "Item 'a1b2c3d4-0001-4000-8000-000000004592' does not belong to merchant 'ffffffff-eeee-dddd-cccc-bbbbaaaa9999'. Verify the merchantId — it should match the merchant from the search result where this item was found.",
    "code": "ITEM_MERCHANT_MISMATCH",
    "mcpCode": -32301,
    "suggestedAction": "Use the merchantId that was returned alongside this itemId in the search or inventory response.",
    "retryable": true
  }
}
```

## Anti-padrões comuns

### Anti-padrão 1: Qualificadores em `query`

**Problema**: colocar qualificadores de preço/distância na string de busca.

```
// ERRADO
const results = await discoveryClient.searchOffers({
  userLocation,
  query: "pizza barata perto de mim"  // qualificadores na query
});
```

**Solução**:

```
// CORRETO
const results = await discoveryClient.searchOffers({
  userLocation,
  query: "pizza",
  refinements: {
    maxItemPrice: 30.0,
    maxDistanceKm: 3
  }
});
```

### Anti-padrão 2: Inventar IDs de taxonomia

**Problema**: adivinhar IDs de categoria em `refinements.itemTaxonomy`.

```
// ERRADO
refinements: { itemTaxonomy: ["pizza-margherita"] }  // adivinhado
```

**Solução**: copie IDs de `listItemTaxonomy` ou `facets.itemTaxonomy`.

```
// CORRETO
const taxonomy = await discoveryClient.listItemTaxonomy({ merchantType: "RESTAURANT" });
const pizzaId = taxonomy.taxonomy.find(t => t.name === "Pizza")?.id;

const results = await discoveryClient.searchOffers({
  query: "pizza",
  refinements: { itemTaxonomy: [pizzaId] }
});
```

### Anti-padrão 3: `userId` ou `userLocation` em `listItemTaxonomy`

**Problema**: enviar identidade ou geo para uma tool pública.

```
// ERRADO
const taxonomy = await discoveryClient.listItemTaxonomy({
  merchantType: "RESTAURANT",
  userLocation: { latitude: -23.5505, longitude: -46.6333 }
});
```

**Solução**: `listItemTaxonomy` é pública — sem `userId`, sem `userLocation`.

```
// CORRETO
const taxonomy = await discoveryClient.listItemTaxonomy({ merchantType: "RESTAURANT" });
```

### Anti-padrão 4: Construir `nextPageToken`

**Problema**: fabricar o token de paginação.

```
// ERRADO
nextPageToken: "page-" + (page + 1)  // fabricado
```

**Solução**: reutilize exatamente o token retornado.

```
// CORRETO
const firstPage = await discoveryClient.searchOffers({ ... });
if (firstPage.hasMore) {
  const secondPage = await discoveryClient.searchOffers({
    ...params,
    nextPageToken: firstPage.nextPageToken  // reutilize exatamente
  });
}
```

### Anti-padrão 5: `merchantType` ausente em `browseOffers`

**Problema**: chamar `browseOffers` sem vertical.

```
// ERRADO
const nearby = await discoveryClient.browseOffers({ userLocation });  // sem merchantType
// → MISSING_MERCHANT_VERTICAL
```

**Solução**: `merchantType` é obrigatório.

```
// CORRETO
const nearby = await discoveryClient.browseOffers({
  userLocation,
  merchantType: "RESTAURANT"
});
```

## Estratégia de retry

### Fluxograma

```
Erro recebido?
  │
  ├─ retryable: false
  │  └─ Não repetir com os mesmos parâmetros. Corrigir a entrada ou oferecer alternativas.
  │
  └─ retryable: true
     ├─ INVALID_QUERY / MISSING_LOCATION / MISSING_MERCHANT_VERTICAL
     │  └─ Completar/corrigir a entrada e chamar de novo
     │
     ├─ INCOMPATIBLE_RESULT_KIND
     │  └─ Trocar resultKind ou contentMode
     │
     └─ INVALID_MERCHANT_VERTICAL / ITEM_MERCHANT_MISMATCH
        └─ Corrigir o valor do parâmetro e reenviar
```

### O que NÃO fazer

- Não repetir erros com `retryable: false` usando os mesmos parâmetros
- Não inventar IDs de taxonomia, parceiro ou item
- Não construir `nextPageToken`
- Não enviar `userId` no payload
- Não enviar geo para `listItemTaxonomy`

### O que FAZER

- Repetir apenas quando `retryable: true` e com a entrada corrigida
- Usar `suggestedAction` para orientar a mensagem ao usuário
- Copiar IDs exatamente das respostas anteriores
- Oferecer alternativas quando um recurso não for encontrado

---

## Casos de uso — /mcps/discovery/casos-de-uso

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/casos-de-uso

# Casos de uso

Explore cenários reais e completos de implementação do Offer Discovery MCP com código executável. Em todos os exemplos, a identidade (`userId`) é injetada pelo gateway via header — o agente **nunca** a envia no payload.

## Caso 1: Buscar pizza por menos de R$30

**Objetivo:** Usuário quer encontrar pizzas com filtro de preço e tempo de entrega.

**Fluxo:**

- Usuário diz: "Encontre pizza entregue em até 30 min por menos de R$30"
- Agente decompõe: `query: "pizza"` + `refinements: { maxItemPrice, maxDeliveryTimeMinutes }`
- Chama `searchOffers` com `resultKind: "ITEM"`
- Processa resultados e pagina se necessário

**JavaScript:**

```
const discoveryClient = require('@ifood/discovery-sdk');

async function searchPizzaUnder30(userLocation) {
  const results = await discoveryClient.searchOffers({
    userLocation: userLocation,          // { latitude, longitude }
    query: "pizza",                     // apenas conteúdo descritivo
    resultKind: "ITEM",
    refinements: {
      maxItemPrice: 30.0,               // R$30
      maxDeliveryTimeMinutes: 30,
      requiredDeliveryMethod: "DELIVERY",
      onlyOpen: true,
      sort: "RELEVANCE"
    },
    pageSize: 10
  });

  console.log(`${results.results.length} pizzas encontradas:`);
  results.results.forEach((item, index) => {
    console.log(`${index + 1}. ${item.itemName}`);
    console.log(`   Preço: R$${item.unitPrice}`);
    console.log(`   Parceiro: ${item.merchant.merchantName}`);
    console.log(`   Entrega: ${item.merchant.deliveryMethod.estimatedMinutes.min}-${item.merchant.deliveryMethod.estimatedMinutes.max}min (R$${item.merchant.deliveryMethod.fee})`);

    if (item.promotionalUnitPrice) {
      console.log(`   Promoção: R$${item.promotionalUnitPrice}`);
    }
  });

  // Paginação: reutilize exatamente o nextPageToken retornado
  if (results.hasMore) {
    const nextPage = await discoveryClient.searchOffers({
      userLocation,
      query: "pizza",
      resultKind: "ITEM",
      refinements: { maxItemPrice: 30.0, maxDeliveryTimeMinutes: 30 },
      nextPageToken: results.nextPageToken
    });
  }

  return results;
}

const userLocation = { latitude: -23.5505, longitude: -46.6333 };
searchPizzaUnder30(userLocation);
```

**Python:**

```
import discovery_client

def search_pizza_under_30(user_location):
    results = discovery_client.search_offers(
        user_location=user_location,           # {"latitude", "longitude"}
        query="pizza",                         # apenas conteúdo descritivo
        result_kind="ITEM",
        refinements={
            "maxItemPrice": 30.0,              # R$30
            "maxDeliveryTimeMinutes": 30,
            "requiredDeliveryMethod": "DELIVERY",
            "onlyOpen": True,
            "sort": "RELEVANCE"
        },
        page_size=10
    )

    print(f"{len(results['results'])} pizzas encontradas:")
    for i, item in enumerate(results['results'], 1):
        print(f"{i}. {item['itemName']}")
        print(f"   Preço: R${item['unitPrice']}")
        print(f"   Parceiro: {item['merchant']['merchantName']}")

        delivery = item['merchant']['deliveryMethod']
        print(f"   Entrega: {delivery['estimatedMinutes']['min']}-{delivery['estimatedMinutes']['max']}min (R${delivery['fee']})")

        if item.get('promotionalUnitPrice'):
            print(f"   Promoção: R${item['promotionalUnitPrice']}")

    return results
```

## Caso 2: Mostrar restaurantes favoritos do usuário

**Objetivo:** Recuperar a lista pré-curada de restaurantes favoritos salvos.

**Fluxo:**

- Usuário diz: "Mostre meus favoritos"
- Agente chama `getRecommendations` com `contentMode: "FAVORITE_MERCHANTS"`
- Exibe nome, avaliação e distância
- Usuário pode escolher um para explorar itens

**JavaScript:**

```
async function showUserFavorites(userLocation) {
  const favorites = await discoveryClient.getRecommendations({
    userLocation: userLocation,
    contentMode: "FAVORITE_MERCHANTS",   // suporta apenas resultKind MERCHANT
    resultKind: "MERCHANT"
  });

  if (favorites.results.length === 0) {
    console.log("Você ainda não tem restaurantes favoritos");
    return;
  }

  console.log(`Seus ${favorites.results.length} restaurantes favoritos:`);
  favorites.results.forEach((merchant, idx) => {
    console.log(`${idx + 1}. ${merchant.merchantName}`);
    console.log(`   Avaliação: ${merchant.reviewRating} | ${merchant.straightLineDistanceKm}km`);

    if (merchant.isOpen) {
      const delivery = merchant.deliveryMethod;
      console.log(`   Entrega: ${delivery.estimatedMinutes.min}-${delivery.estimatedMinutes.max}min (R$${delivery.fee})`);
    } else {
      console.log(`   Fechado`);
    }
  });
}

showUserFavorites({ latitude: -23.5505, longitude: -46.6333 });
```

**Python:**

```
def show_user_favorites(user_location):
    favorites = discovery_client.get_recommendations(
        user_location=user_location,
        content_mode="FAVORITE_MERCHANTS",
        result_kind="MERCHANT"
    )

    if not favorites['results']:
        print("Você ainda não tem restaurantes favoritos")
        return

    print(f"Seus {len(favorites['results'])} restaurantes favoritos:")
    for idx, merchant in enumerate(favorites['results'], 1):
        print(f"{idx}. {merchant['merchantName']}")
        print(f"   Avaliação: {merchant['reviewRating']} | {merchant['straightLineDistanceKm']}km")

        if merchant['isOpen']:
            delivery = merchant['deliveryMethod']
            print(f"   Entrega: {delivery['estimatedMinutes']['min']}-{delivery['estimatedMinutes']['max']}min (R${delivery['fee']})")
        else:
            print("   Fechado")
```

## Caso 3: Explorar restaurantes abertos perto de você

**Objetivo:** Usuário quer saber "O que está aberto perto de mim?"

**Fluxo:**

- Obter a localização do usuário
- Chamar `browseOffers` com `merchantType: "RESTAURANT"`
- Filtrar por abertos
- Mostrar os próximos restaurantes

**JavaScript:**

```
async function showNearbyOpen(userLocation) {
  const nearby = await discoveryClient.browseOffers({
    userLocation: userLocation,
    resultKind: "MERCHANT",
    merchantType: "RESTAURANT",           // obrigatório — sem vertical padrão
    refinements: {
      onlyOpen: true,
      maxDeliveryFee: 15.0
    },
    pageSize: 10
  });

  console.log(`${nearby.results.length} restaurantes abertos perto de você:`);
  nearby.results.forEach((merchant, idx) => {
    console.log(`${idx + 1}. ${merchant.merchantName}`);
    console.log(`   ${merchant.straightLineDistanceKm}km | ${merchant.reviewRating} estrelas`);
    console.log(`   Entrega: ${merchant.deliveryMethod.estimatedMinutes.min}min (R$${merchant.deliveryMethod.fee})`);
  });

  // Drill-down por categoria usando facets.itemTaxonomy
  const facetId = nearby.facets.itemTaxonomy[0]?.id;
  if (facetId) {
    const byCategory = await discoveryClient.browseOffers({
      userLocation,
      resultKind: "MERCHANT",
      merchantType: "RESTAURANT",
      refinements: { itemTaxonomy: [facetId] }
    });
  }
}

showNearbyOpen({ latitude: -23.5505, longitude: -46.6333 });
```

**Python:**

```
def show_nearby_open(user_location):
    nearby = discovery_client.browse_offers(
        user_location=user_location,
        result_kind="MERCHANT",
        merchant_type="RESTAURANT",          # obrigatório
        refinements={
            "onlyOpen": True,
            "maxDeliveryFee": 15.0
        },
        page_size=10
    )

    print(f"{len(nearby['results'])} restaurantes abertos perto de você:")
    for idx, merchant in enumerate(nearby['results'], 1):
        print(f"{idx}. {merchant['merchantName']}")
        print(f"   {merchant['straightLineDistanceKm']}km | {merchant['reviewRating']} estrelas")

        delivery = merchant['deliveryMethod']
        print(f"   Entrega: {delivery['estimatedMinutes']['min']}min (R${delivery['fee']})")
```

## Caso 4: Customizar item antes de adicionar ao carrinho

**Objetivo:** Usuário selecionou um item e quer ver os grupos de opções disponíveis.

**Fluxo:**

- Usuário escolhe Pizza Margherita da Pizza Express
- Agente chama `getItem` com `merchantId` e `itemId`
- Processa `optionGroups` com `minSelections`/`maxSelections`
- Renderiza a UI de customização
- Usuário seleciona opções; `optionId`/`customizationId` são exigidos por `addItemToCart`

**JavaScript:**

```
async function showItemOptions(merchantId, itemId) {
  const detail = await discoveryClient.getItem({
    merchantId: merchantId,
    itemId: itemId,
    userLocation: { latitude: -23.5505, longitude: -46.6333 }
  });

  console.log(`${detail.itemName}`);
  console.log(`Preço base: R$${detail.unitPrice}`);
  if (detail.promotionalUnitPrice) {
    console.log(`Preço promocional: R$${detail.promotionalUnitPrice}`);
  }
  console.log(detail.itemDescription);

  detail.optionGroups.forEach(group => {
    const required = group.minSelections > 0
      ? ` (obrigatório: selecione pelo menos ${group.minSelections})`
      : " (opcional)";
    console.log(`\n${group.name} — máx ${group.maxSelections}${required}`);

    group.options.forEach(option => {
      const price = option.additionalPrice > 0 ? ` +R$${option.additionalPrice}` : "";
      console.log(`  - ${option.name}${price}`);
    });
  });
}

showItemOptions(
  "b8f3c1e2-a456-7890-1234-567890abcdef",
  "a1b2c3d4-0001-4000-8000-000000004592"
);
```

**Python:**

```
def show_item_options(merchant_id, item_id):
    detail = discovery_client.get_item(
        merchant_id=merchant_id,
        item_id=item_id,
        user_location={"latitude": -23.5505, "longitude": -46.6333}
    )

    print(detail['itemName'])
    print(f"Preço base: R${detail['unitPrice']}")
    if detail.get('promotionalUnitPrice'):
        print(f"Preço promocional: R${detail['promotionalUnitPrice']}")
    print(detail['itemDescription'])

    for group in detail['optionGroups']:
        required = " (obrigatório)" if group['minSelections'] > 0 else " (opcional)"
        print(f"\n{group['name']} — máx {group['maxSelections']}{required}")

        for option in group['options']:
            price = f" +R${option['additionalPrice']}" if option['additionalPrice'] > 0 else ""
            print(f"  - {option['name']}{price}")

show_item_options(
    "b8f3c1e2-a456-7890-1234-567890abcdef",
    "a1b2c3d4-0001-4000-8000-000000004592"
)
```

## Caso 5: Navegar por categorias de restaurantes

**Objetivo:** Mostrar todas as categorias de restaurantes disponíveis globalmente e usá-las para filtrar.

**Fluxo:**

- UI quer exibir um menu de categorias
- Agente chama `listItemTaxonomy` com `merchantType: "RESTAURANT"`
- Renderiza o seletor
- Quando o usuário escolhe, usa o ID em `searchOffers` ou `browseOffers`

**JavaScript:**

```
async function showRestaurantCategories() {
  // Tool pública: sem userId, sem userLocation
  const taxonomy = await discoveryClient.listItemTaxonomy({
    merchantType: "RESTAURANT",
    pageSize: 50
  });

  console.log("Categorias de restaurantes:");
  taxonomy.taxonomy.forEach((category, idx) => {
    console.log(`${idx + 1}. ${category.name} (ID: ${category.id})`);
  });

  // Usuário escolhe "Pizza" → use o ID em uma busca geo-localizada
  const pizzaId = taxonomy.taxonomy.find(c => c.name === "Pizza")?.id;
  if (pizzaId) {
    const results = await discoveryClient.searchOffers({
      userLocation: { latitude: -23.5505, longitude: -46.6333 },
      query: "pizza",
      resultKind: "MERCHANT",
      refinements: { itemTaxonomy: [pizzaId] }   // ID vindo da taxonomia
    });

    console.log(`Encontradas ${results.results.length} pizzarias na sua área`);
  }
}

showRestaurantCategories();
```

**Python:**

```
def show_restaurant_categories():
    # Tool pública: sem userId, sem userLocation
    taxonomy = discovery_client.list_item_taxonomy(
        merchant_type="RESTAURANT",
        page_size=50
    )

    print("Categorias de restaurantes:")
    for idx, category in enumerate(taxonomy['taxonomy'], 1):
        print(f"{idx}. {category['name']} (ID: {category['id']})")

    pizza_id = next((c['id'] for c in taxonomy['taxonomy'] if c['name'] == 'Pizza'), None)
    if pizza_id:
        results = discovery_client.search_offers(
            user_location={"latitude": -23.5505, "longitude": -46.6333},
            query="pizza",
            result_kind="MERCHANT",
            refinements={"itemTaxonomy": [pizza_id]}
        )

        print(f"Encontradas {len(results['results'])} pizzarias na sua área")

show_restaurant_categories()
```

## Boas práticas

Nestes exemplos, observe:

- **Nunca envie `userId` no payload** — o gateway injeta via header
- **Obtenha a localização** antes de chamadas geo-aware
- **Use `refinements` para filtros** — não coloque "barato" em `query`
- **Copie IDs literalmente** de `listItemTaxonomy` ou `facets.itemTaxonomy`
- **Processe `optionGroups`** com `minSelections`/`maxSelections` (`minSelections > 0` = obrigatório)
- **Pagine** usando `nextPageToken` exatamente como retornado
- **Use `promotionalUnitPrice`** (escalar) para comunicar preço promocional — não existe array `promotions`
- **Respeite quando a tool é geo-aware** (`listItemTaxonomy` é pública)

---

## Introdução — /mcps/discovery/introducao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/introducao

# O que é o Offer Discovery MCP?

O Offer Discovery MCP é a lente do agente para o marketplace do iFood. Ele responde a seis perguntas em todo fluxo de compra:

| Tool | Pergunta |
| --- | --- |
| `searchOffers` | "Estou procurando algo específico — encontre." |
| `browseOffers` | "O que está disponível perto de mim nesta categoria?" |
| `getRecommendations` | "O que devo repedir / o que é recomendado / o que está em promoção?" |
| `listItemTaxonomy` | "Que tipos de coisa posso navegar neste vertical?" |
| `getMerchant` | "Conte tudo sobre este restaurante antes de eu me comprometer." |
| `getItem` | "Mostre os detalhes completos, grupos de opções e preços promocionais deste item." |


## Por que 6 tools (e não 4, nem 12)

Seis tools é a cobertura mínima para a jornada agêntica de descoberta:

- **4 seriam poucas:** juntar busca + inventário forçaria uma tool única sobrecarregada com um "modo" implícito — exatamente o padrão de enum de operação que rejeitamos. Juntar as tools de detalhe forçaria resultados de lista a carregar payloads completos de detalhe, inflando toda resposta.
- **12 seriam muitas:** dividir `searchOffers` em uma tool por `resultKind`, ou criar tools dedicadas de "drill-down", forçaria o agente a rotear por uma árvore de decisão que duplica o parâmetro `refinements`. O agente já expressa intenção de drill-down via `refinements.itemTaxonomy` — não há tool por nível de taxonomia.
- **6 dá fronteiras limpas:** 3 tools de lista (busca, inventário, curado) + 1 tool de taxonomia (global, sem geo) + 2 tools de detalhe (parceiro, item). Cada tool de lista suporta os dois tipos de resultado (`MERCHANT` e `ITEM`) via um único parâmetro `resultKind` — mesmo mecanismo, sem duplicação.

## Problemas que resolve

- **Busca por texto com qualificadores estruturados:** o agente expressa "ache comida japonesa barata perto de mim" como `query: "comida japonesa"` + `refinements: { maxItemPrice: 40, maxDistanceKm: 3 }`. Qualificadores nunca poluem a string de query.
- **Navegação sem termo de busca:** `browseOffers` permite explorar o que existe em um vertical quando o usuário não tem termo específico — "o que posso pedir?" mapeia diretamente para esta tool.
- **Reengajamento curado:** `getRecommendations` traz favoritos, pedidos recentes, recomendações, ofertas e destaques — todos os fluxos de "não me faça buscar de novo".
- **Taxonomia global sem geo:** `listItemTaxonomy` fornece IDs canônicos de taxonomia para um vertical inteiro, independente do endereço de entrega. O agente usa para popular seletores de categoria ou preparar `refinements.itemTaxonomy` antes de consultas com geo.
- **Detalhe sem inchaço:** resultados de lista carregam apenas campos de resumo. `getMerchant` e `getItem` fornecem dados operacionais exaustivos só quando o usuário se compromete com uma escolha — mantendo os payloads de lista enxutos.
- **Mecanismo único de roteamento:** `resultKind` (`MERCHANT` | `ITEM`) é o único discriminador nas tools de lista. O agente não escolhe entre 6 tools para a mesma intenção — escolhe 1 tool e define 1 enum.

## Fora do escopo

- **Carrinho, pagamentos, pedidos:** domínios downstream. O `orderId` de `getRecommendations` (modo `RECENT_ORDERS`) é opaco — usado apenas para "pedir de novo" no Cart, não para consultar status.
- **Autenticação / OAuth / webview:** domínio upstream.
- **Tool dedicada de cardápio:** navegar itens dentro de um parceiro usa `browseOffers` ou `searchOffers` com `refinements.merchantId`. Não existe tool "menu" separada.
- **Escritas / efeitos colaterais:** Offer Discovery é somente leitura. Sem chaves de idempotência, sem preview de checkout.

## Modelo de identidade

- O `userId` é injetado pelo gateway via header HTTP para as tools que exigem contexto de usuário. O agente **nunca** envia `userId` no payload.
- **Exceção:** `listItemTaxonomy` não recebe `userId` nem `userLocation` — é um catálogo público e global, independente de qualquer usuário.
- As outras 5 tools recebem `userId` via header (não no payload) e exigem `userLocation` no payload.

## As seis tools atômicas

O Offer Discovery resolve cada intenção de descoberta com uma tool específica:

| Tool | Quando usar | Retorna |
| --- | --- | --- |
| `searchOffers` | Usuário descreve o que procura ("pizza", "sushi", "hambúrguer vegano") | Merchants ou itens com `query` + `refinements`, com facets para drill-down |
| `browseOffers` | Usuário quer explorar sem termo ("o que tem perto?", "mostre restaurantes") | Inventário geo-filtrado por vertical com facets de taxonomia |
| `getRecommendations` | Usuário quer repedir, ver favoritos, ofertas ou destaques | Listas pré-curadas por `contentMode` |
| `listItemTaxonomy` | Descobrir IDs canônicos de categoria para um vertical | Taxonomia global, sem geo (pública) |
| `getMerchant` | Usuário escolheu um parceiro e precisa de contexto operacional | Horários, métodos de entrega, mínimo de pedido, itens em destaque |
| `getItem` | Usuário escolheu um item e precisa de grupos de opções | Detalhe completo com `optionGroups` e preço promocional |


## Guia de decisão: qual tool chamar

| Você quer... | Use esta tool | Parâmetro-chave |
| --- | --- | --- |
| Buscar com um termo específico | `searchOffers` | `query` + `resultKind` |
| Navegar um vertical perto do usuário | `browseOffers` | `merchantType` + `resultKind` |
| Ver favoritos, repedidos, ofertas, destaques | `getRecommendations` | `contentMode` + `resultKind` |
| Obter IDs canônicos de taxonomia de um vertical | `listItemTaxonomy` | `merchantType` |
| Ver horários e métodos de entrega | `getMerchant` | `merchantId` |
| Ver grupos de opções e preço promocional de um item | `getItem` | `merchantId` + `itemId` |


## Conceitos essenciais

### Separação entre `query` e `refinements`

`query` carrega **apenas conteúdo descritivo**. Qualificadores estruturados (distância, tempo, dieta, preço) ficam em `refinements`.

```
❌ Errado:  query: "pizza barata perto de mim"
✅ Correto: query: "pizza", refinements: { maxItemPrice: 30, maxDistanceKm: 3 }
```

Por quê: o agente decompõe a intenção naturalmente, e o motor de busca funciona melhor quando a query não carrega ruído como "barata" ou "perto".

### `resultKind` como discriminador único

As 3 tools de lista usam o mesmo parâmetro `resultKind` para alternar entre merchants e itens:

```
{ "resultKind": "MERCHANT" }  // retorna MerchantResult[]
{ "resultKind": "ITEM" }      // retorna ItemResult[]
```

Quando `resultKind` é `MERCHANT`, os resultados carregam `merchantId`, `merchantName`, `reviewRating` e dados de entrega. Quando é `ITEM`, carregam `itemId`, `itemName`, `unitPrice` e um resumo `merchant` embutido.

### Taxonomia não é um enum fixo

`refinements.itemTaxonomy` aceita IDs de string vindos de respostas em runtime (`facets.itemTaxonomy` ou `listItemTaxonomy`) — não um enum gravado no descritor. A taxonomia muda independentemente do contrato, e o agente descobre as categorias válidas em runtime. IDs vêm de exatamente duas fontes: `listItemTaxonomy` (global) ou `facets.itemTaxonomy` (contextual). **Nunca invente.**

### Preços promocionais são campos escalares

Informação promocional é carregada por dois campos escalares — `promotionalUnitPrice` (preço com desconto do item) e `promotionalFee` (taxa de entrega com desconto) — em vez de um array `promotions[]` estruturado. O backend já resolve empilhamento, prioridade e elegibilidade; o agente só precisa do número resolvido.

## Convenções transversais

| Convenção | Padrão |
| --- | --- |
| **Chaves JSON** | `lowerCamelCase` (`merchantId`, `userLocation`, `itemTaxonomy`) |
| **Valores de enum** | `SCREAMING_SNAKE_CASE` (`MERCHANT`, `ITEM`, `RESTAURANT`, `DELIVERY`) |
| **Paginação** | `pageSize` (padrão 10, máx 25) + `nextPageToken` (opaco, nunca construa) + `hasMore` (boolean) |
| **Verticais (`merchantType`)** | `RESTAURANT`, `GROCERIES`, `LIQUORSTORE`, `DRUGSTORE`, `PETSTORE`, `SHOPPING` |
| **Identidade** | Gateway injeta `userId` via header; o agente nunca envia no payload |
| **Erros** | Inline no corpo, com `errors` → `message`, `code`, `mcpCode`, `suggestedAction`, `retryable` |
| **Guidance** | Respostas incluem `agentHints` orientando a próxima ação |


## Próximos passos

- **[Referência de tools](/docs/guides/mcps/discovery/tools)** — Especificação detalhada de cada uma das 6 tools
- **[Tratamento de erros](/docs/guides/mcps/discovery/erros)** — Códigos de erro e estratégias de retry
- **[Casos de uso](/docs/guides/mcps/discovery/casos-de-uso)** — Cenários reais com código completo

---

## Casos de uso — /mcps/order/casos-de-uso

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/casos-de-uso

# Casos de uso

Cenários reais e completos de implementação do Order Tracking MCP com código executável. Em todos os exemplos, a identidade (`userId`) é injetada pelo gateway via header — o agente **nunca** a envia no payload. `orderId` sempre vem de `submitOrder`.

## Caso 1: "Cadê meu pedido?" — reportar o status atual

**Objetivo:** O usuário pergunta onde está o pedido. O agente chama `trackOrder` e repassa o `status.description` legível.

**Fluxo:**

- Receber `orderId` de `submitOrder`
- Chamar `trackOrder(orderId)`
- Repassar `status.description` verbatim — nunca exibir `status.code`
- Ler `retryMessage` e agendar o próximo poll
- Se `pollingStop: true`, parar e reportar o status final

**JavaScript:**

```
async function reportOrderStatus(orderId) {
  const response = await orderClient.trackOrder({ orderId });

  // Repasse a descrição legível — nunca o código bruto
  const { code, description } = response.status;

  if (response.agentHints.pollingStop) {
    return `Status final: ${description}`;
  }

  // Agende o próximo poll a partir da cadência controlada pelo servidor
  scheduleNextPoll(orderId, parseSeconds(response.agentHints.retryMessage)); // ex.: 60

  return `Status: ${description}`;
}
```

**Python:**

```
def report_order_status(order_id):
    response = order_client.track_order(order_id=order_id)

    code = response["status"]["code"]
    description = response["status"]["description"]

    if response["agentHints"].get("pollingStop"):
        return f"Status final: {description}"

    schedule_next_poll(order_id, parse_seconds(response["agentHints"]["retryMessage"]))
    return f"Status: {description}"
```

## Caso 2: "A entrega é iminente?" — notificação de chegada iminente

**Objetivo:** Detectar quando o pedido está prestes a chegar e enviar uma notificação urgente.

**Fluxo:**

- Chamar `trackOrder(orderId)`
- Ler `status.code` para determinar o estado (ex.: `DELIVERY_ARRIVED_AT_DESTINATION`)
- Repassar `status.description` — ela já carrega o contexto de ETA
- Enfatizar a proximidade quando `code` indicar chegada iminente
- Continuar o polling seguindo `retryMessage` até `pollingStop`

**JavaScript:**

```
async function notifyImminentArrival(orderId) {
  const response = await orderClient.trackOrder({ orderId });
  const { code, description } = response.status;

  if (code === "DELIVERY_ARRIVED_AT_DESTINATION") {
    notifyUser(`Seu pedido está quase chegando: ${description}`);
    return true;
  }

  if (code === "ON_THE_WAY") {
    notifyUser(`Saiu para entrega: ${description}`);
  }

  return false;
}
```

**Python:**

```
def notify_imminent_arrival(order_id):
    response = order_client.track_order(order_id=order_id)
    code = response["status"]["code"]
    description = response["status"]["description"]

    if code == "DELIVERY_ARRIVED_AT_DESTINATION":
        notify_user(f"Seu pedido está quase chegando: {description}")
        return True

    if code == "ON_THE_WAY":
        notify_user(f"Saiu para entrega: {description}")

    return False
```

## Caso 3: "Qual foi o endereço de entrega?" — confirmar o endereço

**Objetivo:** O usuário pergunta para qual endereço o pedido foi. O agente lê de `getOrder`.

**Fluxo:**

- Chamar `getOrder(orderId)` uma vez (cache é seguro — dados imutáveis após o checkout)
- Extrair `delivery.address` (uma string formatada, pronta para exibir)
- Se o usuário perguntar sobre custo ou pagamento, usar o campo `payment`
- Não chamar de novo a menos que o usuário pergunte sobre outro pedido

**JavaScript:**

```
async function showDeliveryAddress(orderId) {
  const order = await orderClient.getOrder({ orderId });

  // delivery.address já vem formatado — sem necessidade de parsear campos
  return {
    address: order.delivery.address,
    verificationCode: order.delivery.verificationCode,
    payment: order.payment
  };
}
```

**Python:**

```
def show_delivery_address(order_id):
    order = order_client.get_order(order_id=order_id)
    return {
        "address": order["delivery"]["address"],
        "verification_code": order["delivery"]["verificationCode"],
        "payment": order["payment"],
    }
```

## Caso 4: "O que eu pedi?" — resumo completo do pedido

**Objetivo:** O usuário quer revisar o pedido. O agente usa `getOrder` para mostrar itens, total e merchant.

**Fluxo:**

- Chamar `getOrder(orderId)` uma vez
- Formatar os itens e o pagamento para exibição
- Não chamar de novo (dados são estáticos)

**JavaScript:**

```
async function showOrderSummary(orderId) {
  const order = await orderClient.getOrder({ orderId });

  let summary = `Pedido ${order.shortCode} — ${order.merchant}\n`;
  order.items.forEach(item => { summary += `  • ${item}\n`; });
  summary += `\n${order.payment}`;

  return summary;
}
```

**Python:**

```
def show_order_summary(order_id):
    order = order_client.get_order(order_id=order_id)

    lines = [f"Pedido {order['shortCode']} — {order['merchant']}"]
    for item in order["items"]:
        lines.append(f"  • {item}")
    lines.append(f"\n{order['payment']}")

    return "\n".join(lines)
```

## Caso 5: Monitorar até a entrega — loop de polling controlado pelo servidor

**Objetivo:** Monitorar continuamente um pedido ativo e parar no momento em que o servidor sinalizar um estado terminal.

**Fluxo:**

- Chamar `trackOrder(orderId)`
- Detectar mudanças de status e notificar o usuário
- Se `pollingStop: true`, parar imediatamente e reportar o status final
- Caso contrário, esperar o intervalo em `retryMessage` e fazer polling de novo

**JavaScript:**

```
async function monitorUntilDelivered(orderId) {
  let previousCode = null;

  while (true) {
    const response = await orderClient.trackOrder({ orderId });
    const { code, description } = response.status;
    const hints = response.agentHints;

    if (code !== previousCode) {
      notifyUser(`Atualização: ${description}`);
      previousCode = code;
    }

    if (hints.pollingStop) {
      notifyUser(hints.stopMessage || description);
      break; // não faça polling deste pedido novamente
    }

    await sleep(parseSeconds(hints.retryMessage) * 1000); // ex.: 60s
  }
}
```

**Python:**

```
def monitor_until_delivered(order_id):
    previous_code = None

    while True:
        response = order_client.track_order(order_id=order_id)
        code = response["status"]["code"]
        description = response["status"]["description"]
        hints = response["agentHints"]

        if code != previous_code:
            notify_user(f"Atualização: {description}")
            previous_code = code

        if hints.get("pollingStop"):
            notify_user(hints.get("stopMessage") or description)
            break

        time.sleep(parse_seconds(hints["retryMessage"]))
```

## Boas práticas

- **Nunca exiba `status.code`** — compare-o, repasse `status.description` verbatim
- **Siga `retryMessage`** — o servidor controla a cadência de polling; não faça polling em intervalo fixo
- **Pare em `pollingStop: true`** — nunca refaça polling de um pedido terminal
- **Faça cache dos resultados de `getOrder`** — os dados são imutáveis após o checkout
- **Nunca fabrique `orderId`** — ele sempre vem de `submitOrder`
- **Verifique por `null`, não pela ausência da chave** — `agentHints` sempre retorna os quatro campos

---

## Erros — /mcps/order/erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/erros

# Erros

O Order Tracking MCP retorna erros com os campos diretamente na raiz da resposta (sem aninhamento). Entender os tipos de erro e as estratégias de retry ajuda a construir fluxos robustos.

## Protocolo de erro

Todas as tools retornam erros no corpo, com esta estrutura:

```
{
  "errorType": "ResourceNotFoundError",
  "code": "ORDER_NOT_FOUND",
  "message": "Order ID 'f47ac10b-58cc-4372-a567-0e02b2c3d479' not found",
  "retryable": false,
  "suggestion": "Do not attempt to look up this Order ID again. Tell the user to verify the order reference."
}
```

**Campos importantes:**

- **`errorType`**: categoria de erro de alto nível (ex.: `ResourceNotFoundError`, `AccessDeniedError`)
- **`code`**: código de erro legível por máquina (ex.: `ORDER_NOT_FOUND`)
- **`message`**: descrição técnica do que aconteceu
- **`retryable`**: se vale a pena repetir a chamada
- **`suggestion`**: instrução imperativa sobre o que o agente deve fazer em seguida

**Desvio em relação ao schema canônico de erro:** o contrato de Order Tracking retorna os campos diretamente na raiz da resposta, em vez do formato canônico `{ "errors": { "mcpCode", "message", "code", "suggestedAction", "retryable" } }`. Os agentes devem ler `response.errorType`, não `response.errors.message`. Veja o mapeamento de campos abaixo.

### Mapeamento de campos para o schema canônico

| Campo canônico | Equivalente no Order Tracking |
| --- | --- |
| `errors` (chave wrapper) | Não presente — campos diretamente na raiz |
| `mcpCode` (inteiro) | Não presente — use `errorType` e `code` |
| `message` | `message` (igual) |
| `code` | `code` (igual) |
| `suggestedAction` | `suggestion` (renomeado) |
| `retryable` | `retryable` (igual) |


## Taxonomia de erros

| Código | Tool | Retry? | Causas | O que fazer |
| --- | --- | --- | --- | --- |
| `ORDER_NOT_FOUND` | `trackOrder` | Não | O `orderId` não existe ou foi digitado incorretamente | Diga ao usuário para verificar a referência do pedido; não faça retry |
| `ORDER_NOT_FOUND` | `getOrder` | Sim | Pedido recém-criado (consistência eventual) ou pedido mais antigo arquivado | Aguarde alguns segundos e tente de novo |
| `ORDER_ACCESS_DENIED` | `getOrder` | Não | O pedido não pertence ao usuário autenticado | Verifique se o `orderId` veio do checkout deste usuário |


Nota: o mesmo código `ORDER_NOT_FOUND` tem valores de `retryable` diferentes conforme a tool. `trackOrder` o trata como terminal; `getOrder` pode ter sucesso após uma breve espera.

## Exemplos completos de erro

### `ORDER_NOT_FOUND` (`trackOrder`)

```
{
  "errorType": "ResourceNotFoundError",
  "code": "ORDER_NOT_FOUND",
  "message": "Order ID 'f47ac10b-58cc-4372-a567-0e02b2c3d479' not found",
  "retryable": false,
  "suggestion": "Do not attempt to look up this Order ID again. Tell the user to verify the order reference."
}
```

### `ORDER_NOT_FOUND` (`getOrder`)

```
{
  "errorType": "ResourceNotFoundError",
  "code": "ORDER_NOT_FOUND",
  "message": "Order ID 'f47ac10b-58cc-4372-a567-0e02b2c3d479' not found",
  "retryable": true,
  "suggestion": "If the order was just created, wait a few seconds and retry. For older orders, the data may have been archived."
}
```

### `ORDER_ACCESS_DENIED` (`getOrder`)

```
{
  "errorType": "AccessDeniedError",
  "code": "ORDER_ACCESS_DENIED",
  "message": "Access denied. The requested order does not belong to the authenticated user.",
  "retryable": false,
  "suggestion": "Only query orders that belong to the current user. Verify the orderId came from this user's checkout."
}
```

## Anti-padrões comuns

### Anti-padrão 1: Fazer polling em intervalo fixo

**Problema:** ignorar `agentHints.retryMessage` e fazer polling a cada 5 segundos.

```
// ERRADO
setInterval(async () => {
  await orderClient.trackOrder({ orderId });
}, 5000); // intervalo fixo, ignora a cadência do servidor
```

**Solução:** seguir a cadência controlada pelo servidor.

```
// CORRETO
const response = await orderClient.trackOrder({ orderId });
const seconds = parseSeconds(response.agentHints.retryMessage); // vinda do servidor
setTimeout(async () => {
  await orderClient.trackOrder({ orderId });
}, seconds * 1000);
```

### Anti-padrão 2: Fazer polling após um estado terminal

**Problema:** continuar fazendo polling depois de `pollingStop: true`.

```
// ERRADO
while (true) {
  const r = await orderClient.trackOrder({ orderId });
  // nunca verifica pollingStop
}
```

**Solução:** parar imediatamente em `pollingStop: true`.

```
// CORRETO
const r = await orderClient.trackOrder({ orderId });
if (r.agentHints.pollingStop) {
  return; // não faça polling deste pedido novamente
}
```

### Anti-padrão 3: Exibir `status.code` ao usuário

**Problema:** mostrar o enum de máquina bruto ao usuário.

```
// ERRADO
tellUser(`Status: ${response.status.code}`); // "DELIVERY_ARRIVED_AT_DESTINATION"
```

**Solução:** repassar `status.description` verbatim.

```
// CORRETO
tellUser(response.status.description); // "Delivery person arrived at order delivery address."
```

### Anti-padrão 4: Fabricar `orderId`

**Problema:** adivinhar ou enumerar IDs de pedido.

```
// ERRADO
await orderClient.getOrder({ orderId: "00000000-0000-0000-0000-000000000001" }); // inventado
```

**Solução:** usar o `orderId` retornado por `submitOrder`.

```
// CORRETO
const { orderId } = await cartClient.submitOrder({ ... });
await orderClient.trackOrder({ orderId });
```

## Estratégia de retry

### Fluxograma

```
Erro recebido?
  │
  ├─ retryable: false
  │  └─ Não faça retry. Siga a suggestion e informe o usuário.
  │
  └─ retryable: true
     └─ ORDER_NOT_FOUND (getOrder)
        └─ Aguarde alguns segundos e tente uma vez
```

### O que NÃO fazer

- Não faça retry de erros com `retryable: false`
- Não faça polling em intervalo fixo — siga `retryMessage`
- Não faça polling depois de `pollingStop: true`
- Não exiba `status.code` ao usuário
- Não fabrique `orderId`

### O que fazer

- Faça retry apenas quando `retryable: true` (e, para `getOrder`, só após uma breve espera)
- Use `suggestion` para guiar a mensagem ao usuário
- Repasse `status.description` verbatim
- Compare `status.code` para lógica programática
- Pare o polling imediatamente em `pollingStop: true`

---

## Tools — /mcps/discovery/tools

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/discovery/tools

# Offer Discovery MCP - Tools

O Offer Discovery MCP expõe 6 tools atômicas para pesquisar, navegar, explorar listas curadas, navegar taxonomia e recuperar detalhes de parceiros e itens. Este guia documenta cada tool, seus parâmetros, respostas e erros.

## Visão geral

| Tool | Descrição | Quando usar |
| --- | --- | --- |
| [`searchOffers`](#searchoffers) | Busca por texto com refinamentos estruturados | Usuário descreve o que procura ("pizza", "sushi") |
| [`browseOffers`](#browseoffers) | Navega inventário geo-localizado por vertical | Usuário quer explorar ("o que tem perto?") |
| [`getRecommendations`](#getrecommendations) | Listas pré-curadas (favoritos, repedidos, ofertas) | Reengajamento sem busca |
| [`listItemTaxonomy`](#listitemtaxonomy) | Taxonomia global de categorias por vertical | Descobrir IDs válidos de categoria |
| [`getMerchant`](#getmerchant) | Detalhes operacionais completos do parceiro | Após usuário escolher um parceiro |
| [`getItem`](#getitem) | Detalhe completo do item com grupos de opções | Após usuário escolher um item |


## Índice rápido

- [`searchOffers`](#searchoffers) — Busca por texto
- [`browseOffers`](#browseoffers) — Navegação por vertical
- [`getRecommendations`](#getrecommendations) — Listas pré-curadas
- [`listItemTaxonomy`](#listitemtaxonomy) — Taxonomia global
- [`getMerchant`](#getmerchant) — Detalhes do parceiro
- [`getItem`](#getitem) — Detalhes do item

## Convenções transversais

Todas as tools seguem estas convenções:

- **Chaves JSON**: `lowerCamelCase`
- **Identificadores**: UUID v4 (ex.: `b8f3c1e2-a456-7890-1234-567890abcdef`)
- **Verticais (`merchantType`)**: `RESTAURANT`, `GROCERIES`, `LIQUORSTORE`, `DRUGSTORE`, `PETSTORE`, `SHOPPING`
- **`resultKind`**: `MERCHANT` (lojas) ou `ITEM` (produtos específicos) — nas 3 tools de lista
- **Paginação**: `pageSize` (padrão 10, máx 25; taxonomia padrão 50, máx 100) + `nextPageToken` (opaco, nunca construa) + `hasMore` (boolean)
- **Identidade**: gateway injeta `userId` via header; o agente nunca envia `userId` no payload
- **Localização**: `userLocation` = `{ "latitude": number, "longitude": number }` — obrigatório em 5 das 6 tools (`listItemTaxonomy` é pública)
- **Preços**: escalares em BRL — `promotionalUnitPrice` (item com desconto) e `promotionalFee` (entrega com desconto); não existe array `promotions`
- **Erros**: inline no corpo, com `errors` → `message`, `code`, `mcpCode`, `suggestedAction`, `retryable`
- **Guidance**: respostas incluem `agentHints` orientando a próxima ação

## Busca por texto com refinamentos

### `searchOffers`

Busca no marketplace por merchants ou itens usando uma query em linguagem natural com refinamentos estruturados (preço, distância, tempo de entrega, dieta). Use quando o usuário tem um termo descritivo ("pizza", "sushi", "hambúrguer vegano"). Qualificadores ("barato", "rápido", "perto") vão em `refinements`, **não** em `query`.

**Quando usar:**

- Usuário expressa intenção de busca com termos descritivos ("pizza", "sobremesa vegana", "paracetamol 500mg")
- Usuário quer refinar resultados com qualificadores estruturados (preço, distância, tempo de entrega)
- Busca por texto como ponto de entrada principal da descoberta

**Quando NÃO usar:**

- Usuário quer navegar sem um termo específico (use `browseOffers`)
- Usuário quer favoritos, repedidos ou ofertas (use `getRecommendations`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: O agente deve ter um `userLocation` válido. O gateway injeta `userId` via header. `query` contém **apenas** conteúdo descritivo — qualificadores ficam em `refinements`.

**Dependências**: Use coordenadas de `listAddresses` ou `createAddress` como `userLocation`. Use `merchantId` ou `itemId` retornados para `getMerchant` ou `getItem`.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `query` | string | Sim | — | Termo em linguagem natural. Apenas conteúdo descritivo — use `refinements` para qualificadores. Ex.: `"pizza margherita"`, não `"pizza barata rápida perto de mim"`. |
| `resultKind` | string | Não | `"MERCHANT"` | O que buscar: `"MERCHANT"` (encontrar lojas) ou `"ITEM"` (encontrar produtos específicos). |
| `userLocation` | object | Sim | — | `{ "latitude": number, "longitude": number }`. Ponto de entrega/consulta. |
| `merchantType` | string | Não | — | Filtro de vertical: `"RESTAURANT"`, `"GROCERIES"`, `"LIQUORSTORE"`, `"DRUGSTORE"`, `"PETSTORE"`, `"SHOPPING"`. |
| `refinements` | object | Não | — | Filtros estruturados (ver subtabela abaixo). |
| `pageSize` | integer | Não | 10 | Resultados por página (máx 25). |
| `nextPageToken` | string | Não | — | Token opaco da resposta anterior (nunca construa). |


**`refinements`:**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `itemTaxonomy` | array de strings | IDs de taxonomia de `listItemTaxonomy` ou `facets.itemTaxonomy`. Lógica OR — vários IDs ampliam os resultados. |
| `merchantId` | string | UUID v4. Restringe a um único parceiro. |
| `maxItemPrice` | number | Preço unitário máximo em BRL. |
| `minItemPrice` | number | Preço unitário mínimo em BRL. |
| `maxDeliveryFee` | number | Taxa de entrega máxima em BRL. |
| `maxDistanceKm` | number | Distância máxima em linha reta a partir de `userLocation`. |
| `maxDeliveryTimeMinutes` | integer | Tempo máximo estimado de entrega. |
| `onlyOpen` | boolean | Filtrar apenas parceiros abertos no momento. |
| `sort` | string | Ordenação: `"RELEVANCE"`, `"PRICE"`, `"DELIVERY_TIME"`. Padrão `"RELEVANCE"`. |
| `dietary` | array de strings | Filtros dietéticos: `"VEGETARIAN"`, `"VEGAN"`, `"GLUTEN_FREE"`. |
| `requiredDeliveryMethod` | string | `"DELIVERY"`, `"TAKEOUT"` ou `"ANY"`. |


#### Resposta (sucesso — busca por merchant)

```
{
  "resultKind": "MERCHANT",
  "interpretedQuery": "pizza margherita",
  "results": [
    {
      "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
      "merchantName": "Pizza Express",
      "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
      "reviewRating": 4.7,
      "isOpen": true,
      "deliveryMethod": {
        "deliveryMethodMode": "DELIVERY",
        "fee": 0.00,
        "promotionalFee": null,
        "estimatedMinutes": { "min": 25, "max": 35 }
      },
      "straightLineDistanceKm": 1.2,
      "nextOpenAt": null,
      "matchScore": 0.95,
      "whyRecommended": "Matches Italian preference, within budget, free delivery today",
      "concerns": "Slightly higher minimum order than your average"
    }
  ],
  "facets": {
    "itemTaxonomy": [
      { "id": "pizza", "name": "Pizza", "availability": "PLENTIFUL" },
      { "id": "pasta", "name": "Pasta", "availability": "ADEQUATE" }
    ]
  },
  "nextPageToken": "eyJvZm...EwfQ",
  "hasMore": true,
  "agentHints": {
    "nextStepWhenUserPicksMerchant": "Retrieve detailed information about this merchant — operating hours, full address, delivery methods, payment options, and featured items before presenting it to the user.",
    "nextStepForDrillingDown": "Narrow results by applying taxonomy filters from the available facets to refine the search to a specific category."
  }
}
```

#### Resposta (sucesso — busca por item)

```
{
  "resultKind": "ITEM",
  "interpretedQuery": "hambúrguer artesanal",
  "results": [
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000004592",
      "itemName": "Cheesebúrguer Artesanal",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 32.00,
      "merchant": {
        "merchantId": "c9a4d2f3-b567-8901-2345-678901bcdefa",
        "merchantName": "Burger House",
        "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
        "reviewRating": 4.7,
        "isOpen": true,
        "deliveryMethod": {
          "deliveryMethodMode": "DELIVERY",
          "fee": 6.50,
          "promotionalFee": null,
          "estimatedMinutes": { "min": 30, "max": 45 }
        },
        "straightLineDistanceKm": 2.1,
        "nextOpenAt": null
      },
      "matchScore": 0.92,
      "promotionalUnitPrice": 29.00
    }
  ],
  "facets": {},
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksItem": "Retrieve full item details — option groups, and applicable promotional prices — before presenting it to the user."
  }
}
```

#### Saída (Erro — query vazia ou só com qualificadores)

```
{
  "errors": {
    "message": "The search query is empty or contains only qualifiers ('cheap', 'near', 'fast'). Move qualifiers to refinements (maxItemPrice, maxDistanceKm, maxDeliveryTimeMinutes) and put descriptive terms in query.",
    "code": "INVALID_QUERY",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user to describe what kind of food or item they want. Use a descriptive term like 'pizza', 'sushi', 'vegan burger'.",
    "retryable": true
  }
}
```

#### Saída (Erro — userLocation ausente)

```
{
  "errors": {
    "message": "No delivery location provided. The user's location is required to search for nearby options.",
    "code": "MISSING_LOCATION",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user where they want delivery. Check the user's saved delivery addresses, or ask for a street address.",
    "retryable": true
  }
}
```

#### Saída (resultados vazios)

```
{
  "resultKind": "MERCHANT",
  "interpretedQuery": "sushi premium",
  "results": [],
  "facets": {},
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "noResultsGuidance": "No results found for 'sushi premium' in this area. Suggest the user try a broader term like 'Japanese food', remove price or distance filters, or try a different neighborhood."
  }
}
```

**Resposta contém:**

- `resultKind`: enum `"MERCHANT"` ou `"ITEM"` — determina o tipo de resultado
- `results[]`: array paginado (até 25 itens, padrão 10). Se `MERCHANT`: `merchantId`, `merchantName`, `merchantLogoUrl`, `reviewRating`, `isOpen`, `deliveryMethod`, `straightLineDistanceKm`. Se `ITEM`: `itemId`, `itemName`, `itemImageUrl`, `unitPrice`, `promotionalUnitPrice`, `merchant` (resumo)
- `facets.itemTaxonomy`: taxonomias disponíveis para drill-down — use os IDs em `refinements.itemTaxonomy`
- `nextPageToken`: opaco (nunca construa); `hasMore`: boolean; `agentHints`: orientação contextual

## Navegação por vertical

### `browseOffers`

Navega o inventário geo-localizado por vertical sem termo de busca, retornando merchants ou itens com facets de taxonomia para drill-down. É a tool de "mostre o que está disponível".

**Quando usar:**

- Usuário pergunta "o que está disponível perto de mim?", "mostre restaurantes", "que supermercados existem?"
- Exploração genérica quando o usuário não tem termo específico
- Navegar dentro do catálogo de um parceiro específico (use `refinements.merchantId`)
- Descobrir categorias disponíveis em um vertical geográfico

**Quando NÃO usar:**

- Usuário tem um termo de busca específico (use `searchOffers`)
- Usuário quer conteúdo curado: favoritos, repedidos, ofertas (use `getRecommendations`)
- Buscar taxonomia global sem geo (use `listItemTaxonomy`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: `merchantType` é OBRIGATÓRIO (sem padrão). O agente deve ter um `userLocation` válido. O gateway injeta `userId` via header.

**Dependências**: Use coordenadas de `listAddresses` ou `createAddress` como `userLocation`. Use `merchantId` ou `itemId` retornados para `getMerchant` ou `getItem`. Use IDs de `facets.itemTaxonomy` na próxima chamada com `refinements.itemTaxonomy`.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `merchantType` | string | Sim | — | Vertical: `"RESTAURANT"`, `"GROCERIES"`, `"LIQUORSTORE"`, `"DRUGSTORE"`, `"PETSTORE"`, `"SHOPPING"`. |
| `resultKind` | string | Não | `"MERCHANT"` | `"MERCHANT"` ou `"ITEM"`. |
| `userLocation` | object | Sim | — | `{ "latitude": number, "longitude": number }`. |
| `refinements` | object | Não | — | Subconjunto dos refinements de `searchOffers`: `itemTaxonomy`, `merchantId` (UUID v4), `maxItemPrice` (BRL), `maxDeliveryFee` (BRL), `maxDistanceKm`, `maxDeliveryTimeMinutes`, `onlyOpen`, `sort`, `dietary`. |
| `pageSize` | integer | Não | 10 | Resultados por página (máx 25). |
| `nextPageToken` | string | Não | — | Token opaco. |


#### Resposta (sucesso — exploração aberta, MERCHANT)

```
{
  "resultKind": "MERCHANT",
  "merchantType": "GROCERIES",
  "results": [
    {
      "merchantId": "d0b5e3a4-c678-9012-3456-789012cdefab",
      "merchantName": "Mercado do Bairro",
      "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
      "reviewRating": 4.6,
      "isOpen": true,
      "deliveryMethod": {
        "deliveryMethodMode": "DELIVERY",
        "fee": 8.00,
        "promotionalFee": null,
        "estimatedMinutes": { "min": 35, "max": 55 }
      },
      "straightLineDistanceKm": 0.9,
      "nextOpenAt": null
    }
  ],
  "facets": {
    "itemTaxonomy": [
      { "id": "produce", "name": "Hortifrúti", "availability": "PLENTIFUL" },
      { "id": "dairy", "name": "Laticínios", "availability": "PLENTIFUL" }
    ]
  },
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksMerchant": "Retrieve detailed information about this merchant — operating hours, delivery methods, and payment options — before presenting it to the user.",
    "nextStepForDrillingDown": "Narrow results by applying taxonomy filters from the available facets to browse a specific category within this vertical."
  }
}
```

#### Resposta (sucesso — drill-down com taxonomia, ITEM)

```
{
  "resultKind": "ITEM",
  "merchantType": "RESTAURANT",
  "results": [
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000008301",
      "itemName": "Combinado 12 peças",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 54.90,
      "merchant": {
        "merchantId": "e1c6f4b5-d789-0123-4567-890123defabc",
        "merchantName": "Sushi Norte",
        "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
        "reviewRating": 4.8,
        "isOpen": true,
        "deliveryMethod": {
          "deliveryMethodMode": "DELIVERY",
          "fee": 7.00,
          "promotionalFee": null,
          "estimatedMinutes": { "min": 40, "max": 55 }
        },
        "straightLineDistanceKm": 2.4,
        "nextOpenAt": null
      }
    }
  ],
  "facets": {
    "itemTaxonomy": [
      { "id": "sashimi", "name": "Sashimi", "availability": "ADEQUATE" }
    ]
  },
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksItem": "Retrieve full item details — option groups and applicable promotional prices — before presenting it to the user."
  }
}
```

#### Saída (Erro — merchantType ausente)

```
{
  "errors": {
    "message": "merchantType is required for browseOffers. Choose from: RESTAURANT, GROCERIES, LIQUORSTORE, DRUGSTORE, PETSTORE, SHOPPING.",
    "code": "MISSING_MERCHANT_VERTICAL",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user what kind of store or category they want to browse.",
    "retryable": true
  }
}
```

#### Saída (resultados vazios)

```
{
  "resultKind": "MERCHANT",
  "merchantType": "DRUGSTORE",
  "results": [],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "noResultsGuidance": "No pharmacies found in your area. Suggest trying a different neighborhood or checking if the address is correct."
  }
}
```

**Resposta contém:**

- `merchantType`: string enum retornado (o vertical consultado)
- `resultKind`: enum `"MERCHANT"` (padrão) ou `"ITEM"`
- `results[]`: mesma estrutura de `searchOffers`
- `facets.itemTaxonomy`: taxonomias disponíveis neste vertical geográfico (subconjunto contextual)

## Listas pré-curadas

### `getRecommendations`

Retorna listas pré-curadas com base no histórico do usuário, recomendações ou seleção editorial, com contexto geográfico. É o ponto de entrada de "não me faça buscar de novo" — favoritos, repedidos, ofertas, recomendações personalizadas.

**Quando usar:**

- Usuário quer repedir algo que já pediu antes
- Usuário quer ver parceiros ou itens favoritos
- Usuário quer ver ofertas ativas e preços promocionais
- Usuário quer recomendações personalizadas ou destaques locais
- Reengajamento ("veja o que você pediu")

**Quando NÃO usar:**

- Usuário tem um termo de busca específico (use `searchOffers`)
- Navegação genérica sem termo (use `browseOffers`)
- Listar todas as categorias (use `listItemTaxonomy`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: `contentMode` deve ser compatível com `resultKind` (ver matriz abaixo). O gateway injeta `userId` via header. O agente deve ter `userLocation`.

**Dependências**: Use coordenadas de `listAddresses` ou `createAddress` como `userLocation`. Use `merchantId` ou `itemId` retornados para `getMerchant` ou `getItem`. Para `RECENT_ORDERS`: `lastOrderId` é opaco (apenas contexto).

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `contentMode` | string | Sim | — | `"RECOMMENDED"`, `"RECENT_ORDERS"`, `"FAVORITE_MERCHANTS"`, `"BEST_DEALS"` ou `"FEATURED_LOCAL"`. |
| `resultKind` | string | Não | `"MERCHANT"` | Deve ser compatível com `contentMode` (ver tabela). |
| `userLocation` | object | Sim | — | `{ "latitude": number, "longitude": number }`. |
| `merchantType` | string | Não | — | Filtro opcional de vertical. |
| `refinements` | object | Não | — | Subconjunto: `itemTaxonomy`, `priceRange`, `maxDistanceKm`, `maxDeliveryTimeMinutes`, `onlyOpen`, `sort`, `dietary`. |
| `pageSize` | integer | Não | 10 | Resultados por página (máx 25). |
| `nextPageToken` | string | Não | — | Token opaco. |


**Matriz de compatibilidade `contentMode` × `resultKind`:**

| `contentMode` | MERCHANT | ITEM | Notas |
| --- | --- | --- | --- |
| `RECOMMENDED` | ✓ | ✓ | Recomendações personalizadas com base no histórico |
| `RECENT_ORDERS` | ✓ | ✓ | Pedidos recentes com `lastOrderedAt`, `timesOrdered`, `lastOrderId` |
| `FAVORITE_MERCHANTS` | ✓ only | ✗ | Parceiros favoritos do usuário |
| `BEST_DEALS` | ✓ | ✓ | Ofertas ativas e preços promocionais |
| `FEATURED_LOCAL` | ✓ only | ✗ | Destaques locais selecionados editorialmente |


#### Resposta (sucesso — RECOMMENDED, MERCHANT)

```
{
  "contentMode": "RECOMMENDED",
  "resultKind": "MERCHANT",
  "results": [
    {
      "merchantId": "f2d7a5c6-e890-1234-5678-901234efabcd",
      "merchantName": "Cantinho Caseiro",
      "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
      "reviewRating": 4.9,
      "isOpen": true,
      "deliveryMethod": {
        "deliveryMethodMode": "DELIVERY",
        "fee": 0.00,
        "promotionalFee": null,
        "estimatedMinutes": { "min": 20, "max": 35 }
      },
      "straightLineDistanceKm": 1.0,
      "nextOpenAt": null,
      "whyRecommended": "Aligned with your recent orders of home-style meals"
    }
  ],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksMerchant": "Retrieve detailed information about this merchant — operating hours, delivery methods, and payment options — before presenting it to the user."
  }
}
```

#### Resposta (sucesso — RECENT_ORDERS, ITEM)

```
{
  "contentMode": "RECENT_ORDERS",
  "resultKind": "ITEM",
  "results": [
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000001204",
      "itemName": "Prato executivo frango",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 28.00,
      "lastOrderedAt": "2026-05-20T12:10:00Z",
      "timesOrdered": 4,
      "lastOrderId": "e5f6a7b8-0001-4000-d000-000000000001",
      "merchant": {
        "merchantId": "a3e8b6d7-f901-2345-6789-012345fabce0",
        "merchantName": "Marmita Express",
        "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
        "reviewRating": 4.4,
        "isOpen": true,
        "deliveryMethod": {
          "deliveryMethodMode": "DELIVERY",
          "fee": 5.50,
          "promotionalFee": null,
          "estimatedMinutes": { "min": 25, "max": 40 }
        },
        "straightLineDistanceKm": 3.0,
        "nextOpenAt": null
      }
    }
  ],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksItem": "Retrieve full item details — option groups and applicable promotional prices — before presenting it to the user."
  }
}
```

#### Resposta (sucesso — BEST_DEALS, ITEM com promoção)

```
{
  "contentMode": "BEST_DEALS",
  "resultKind": "ITEM",
  "results": [
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000005601",
      "itemName": "Combo almoço",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 35.00,
      "promotionalUnitPrice": 28.00,
      "merchant": {
        "merchantId": "b4f9c7e8-a012-3456-7890-123456abcdef",
        "merchantName": "Almoço Rápido",
        "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
        "reviewRating": 4.3,
        "isOpen": true,
        "deliveryMethod": {
          "deliveryMethodMode": "DELIVERY",
          "fee": 4.00,
          "promotionalFee": null,
          "estimatedMinutes": { "min": 15, "max": 30 }
        },
        "straightLineDistanceKm": 0.6,
        "nextOpenAt": null
      }
    }
  ],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepWhenUserPicksItem": "Retrieve full item details — option groups and applicable promotional prices — before presenting it to the user."
  }
}
```

#### Saída (Erro — resultKind incompatível)

```
{
  "errors": {
    "message": "FAVORITE_MERCHANTS only supports resultKind=MERCHANT. Change resultKind to MERCHANT or select a different contentMode.",
    "code": "INCOMPATIBLE_RESULT_KIND",
    "mcpCode": -32301,
    "suggestedAction": "Set resultKind to MERCHANT or use contentMode RECOMMENDED for item results.",
    "retryable": true
  }
}
```

#### Saída (resultados vazios)

```
{
  "contentMode": "BEST_DEALS",
  "resultKind": "MERCHANT",
  "results": [],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "noResultsGuidance": "No active deals found in your area right now. Try browsing available inventory in this vertical, or try RECOMMENDED for personalized suggestions."
  }
}
```

**Resposta contém:**

- `contentMode`: string enum do modo consultado
- `resultKind`: enum `"MERCHANT"` (padrão) ou `"ITEM"` — compatível com `contentMode`
- `results[]`: mesma estrutura de `searchOffers`/`browseOffers`. Se `RECENT_ORDERS`: adiciona `lastOrderedAt` (ISO 8601), `timesOrdered` (int), `lastOrderId` (opaco). Se `BEST_DEALS`: adiciona `promotionalUnitPrice` (BRL) quando há desconto

## Taxonomia global por vertical

### `listItemTaxonomy`

Retorna a árvore de taxonomia GLOBAL de um vertical — IDs canônicos de categoria independentes de localização ou geografia. Tool pública, sem autenticação ou geo.

**Quando usar:**

- O agente precisa validar IDs de taxonomia antes de montar `refinements.itemTaxonomy`
- Mostrar ao usuário que TIPOS de coisa existem em um vertical
- Popular um seletor de categoria ou menu de drill-down (árvore de categorias)
- Antes de consultas com geo, para aprender as categorias disponíveis globalmente

**Quando NÃO usar:**

- Descobrir o subconjunto contextual de categorias (use `facets.itemTaxonomy` de search/browse)
- Buscar produtos (use `searchOffers` ou `browseOffers`)
- Quando você já tem facets de uma resposta anterior (reutilize IDs de `facets.itemTaxonomy`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: `merchantType` é OBRIGATÓRIO (sem padrão). A tool é PÚBLICA — não recebe `userId` nem exige `userLocation`. O gateway não injeta identidade.

**Dependências**: Nenhuma — tool de descoberta autônoma. Retorna IDs para uso em `refinements.itemTaxonomy` de `searchOffers`, `browseOffers` e `getRecommendations`.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `merchantType` | string | Sim | — | Vertical: `"RESTAURANT"`, `"GROCERIES"`, `"LIQUORSTORE"`, `"DRUGSTORE"`, `"PETSTORE"`, `"SHOPPING"`. |
| `expandFromTaxonomyId` | string | Não | — | ID de taxonomia a expandir em sub-categorias. Omitir para o nível raiz. |
| `pageSize` | integer | Não | 50 | Resultados por página (máx 100 — árvores de taxonomia podem ser grandes). |
| `nextPageToken` | string | Não | — | Token opaco. |


#### Resposta (sucesso — nível raiz)

```
{
  "merchantType": "RESTAURANT",
  "taxonomy": [
    { "id": "italian_food", "name": "Italiana", "availability": "PLENTIFUL" },
    { "id": "japanese_food", "name": "Japonesa", "availability": "PLENTIFUL" },
    { "id": "brazilian_food", "name": "Brasileira", "availability": "PLENTIFUL" },
    { "id": "arabic_food", "name": "Árabe", "availability": "PLENTIFUL" },
    { "id": "bakery", "name": "Padaria", "availability": "PLENTIFUL" }
  ],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepForDrillingDown": "Browse inventory near the user using one or more of these taxonomy IDs as category filters.",
    "nextStepForExpand": "Expand a taxonomy entry into its sub-categories to let the user drill deeper into a specific category."
  }
}
```

#### Resposta (sucesso — sub-categoria expandida)

```
{
  "merchantType": "RESTAURANT",
  "expandedFrom": "italian_food",
  "taxonomy": [
    { "id": "pizza", "name": "Pizza", "availability": "PLENTIFUL" },
    { "id": "pasta", "name": "Massas", "availability": "PLENTIFUL" },
    { "id": "risotto", "name": "Risotos", "availability": "ADEQUATE" }
  ],
  "nextPageToken": null,
  "hasMore": false,
  "agentHints": {
    "nextStepForDrillingDown": "Browse inventory near the user using one of these sub-category IDs as a category filter."
  }
}
```

#### Saída (Erro — ID de taxonomia desconhecido)

```
{
  "errors": {
    "message": "The taxonomy ID 'id_inventado' does not exist in the RESTAURANT vertical or has no sub-categories. Use the root level or try a valid ID from the taxonomy response.",
    "code": "UNKNOWN_TAXONOMY_ID",
    "mcpCode": -32301,
    "suggestedAction": "Retrieve the root categories for this vertical and present them to the user.",
    "retryable": false
  }
}
```

#### Saída (Erro — vertical inválido)

```
{
  "errors": {
    "message": "Invalid merchantType 'INVALID_VERTICAL'. Valid values: RESTAURANT, GROCERIES, LIQUORSTORE, DRUGSTORE, PETSTORE, SHOPPING.",
    "code": "INVALID_MERCHANT_VERTICAL",
    "mcpCode": -32301,
    "suggestedAction": "Ask the user which type of store they're interested in.",
    "retryable": true
  }
}
```

**Resposta contém:**

- `merchantType`: string enum retornado (o vertical consultado)
- `expandedFrom`: string (presente se chamado com `expandFromTaxonomyId`)
- `taxonomy[]`: categorias com `id` (use em `refinements.itemTaxonomy`), `name` (nome em português) e `availability` (enum `"PLENTIFUL"`, `"ADEQUATE"`, `"SCARCE"`)
- `nextPageToken` / `hasMore`: paginação (máx 100 itens)

## Detalhes do parceiro

### `getMerchant`

Retorna os detalhes operacionais completos de um parceiro — horário de funcionamento, todos os métodos de entrega com taxas e ETAs, mínimo de pedido, resumo do catálogo, itens em destaque e deeplink do app. Chame ANTES de apresentar um parceiro ao usuário.

**Quando usar:**

- SEMPRE após o usuário escolher um parceiro de qualquer resultado de lista
- Para exibir horários, métodos de entrega
- Para validar que o parceiro está aberto e atende o endereço do usuário
- Antes de navegar o cardápio (catalogar itens)

**Quando NÃO usar:**

- Listar parceiros (use `searchOffers`, `browseOffers`, `getRecommendations`)
- Detalhes de um item específico (use `getItem`)
- Sem antes ter `merchantId` de um resultado de lista

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: `merchantId` de resultado anterior (`searchOffers`, `browseOffers`, `getRecommendations`). O agente deve ter um `userLocation` válido. O gateway injeta `userId` via header.

**Dependências**: `merchantId` vem de `searchOffers`, `browseOffers` ou `getRecommendations`. Antes de navegar itens: use `browseOffers(merchantId)` ou `searchOffers(merchantId)`.

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `merchantId` | string | Sim | UUID v4 (ex.: `"b8f3c1e2-a456-7890-1234-567890abcdef"`) de um resultado de lista anterior. |
| `userLocation` | object | Sim | `{ "latitude": number, "longitude": number }`. |


#### Resposta (sucesso — restaurante com detalhe completo)

```
{
  "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
  "merchantName": "Pizza Express",
  "merchantLogoUrl": "https://cdn.ifood.com.br/merchants/abc123-logo.jpg",
  "merchantType": "RESTAURANT",
  "isOpen": true,
  "operatingHours": {
    "today": {
      "openLocal": "11:00",
      "closeLocal": "23:00"
    },
    "weekly": {
      "mon": { "openLocal": "11:00", "closeLocal": "23:00" },
      "tue": { "openLocal": "11:00", "closeLocal": "23:00" },
      "wed": { "openLocal": "11:00", "closeLocal": "23:00" },
      "thu": { "openLocal": "11:00", "closeLocal": "23:00" },
      "fri": { "openLocal": "11:00", "closeLocal": "00:00" },
      "sat": { "openLocal": "11:00", "closeLocal": "00:00" },
      "sun": { "openLocal": "17:00", "closeLocal": "23:00" }
    }
  },
  "deliveryMethods": [
    {
      "deliveryMethodId": "ECONOMIC",
      "deliveryMethodMode": "DELIVERY",
      "fee": 0.00,
      "promotionalFee": null,
      "estimatedMinutes": { "min": 25, "max": 35 }
    },
    {
      "deliveryMethodId": "EXPRESS",
      "deliveryMethodMode": "DELIVERY",
      "fee": 12.00,
      "promotionalFee": null,
      "estimatedMinutes": { "min": 15, "max": 25 }
    }
  ],
  "minimumOrderAmount": 15.00,
  "appDeeplink": "ifood://catalog-hub/70c62455-bd12-4011-9463-de6279210d0a/RESTAURANT",
  "catalogSummary": {
    "totalItems": 87,
    "navigationHint": "Browse this merchant's full catalog by taxonomy to explore their offerings."
  },
  "featuredItems": [
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000000100",
      "itemName": "Pizza Margherita",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 32.90,
      "promotionalUnitPrice": null,
      "menuSection": "Pizzas",
      "featuredReason": "Mais pedida"
    },
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000000101",
      "itemName": "Pizza Calabresa",
      "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
      "unitPrice": 34.90,
      "promotionalUnitPrice": 29.90,
      "menuSection": "Combos Lanche +maionese + Batata + Coca",
      "featuredReason": "Promoção do dia"
    }
  ],
  "agentHints": {
    "nextStepWhenUserPicksItem": "Retrieve full item details — option groups, and applicable promotional prices — for the chosen item before adding it to the cart."
  }
}
```

#### Saída (Erro — parceiro não encontrado)

```
{
  "errors": {
    "message": "The merchant ID 'ffffffff-eeee-dddd-cccc-bbbbaaaa9999' was not found or is not available in your area. Do not retry this ID.",
    "code": "MERCHANT_NOT_FOUND",
    "mcpCode": -32301,
    "suggestedAction": "Return to the previous search results and present the user with alternative merchants.",
    "retryable": false
  }
}
```

#### Saída (Erro — parceiro fechado, com orientação)

```
{
  "errors": {
    "message": "Pizza Express is currently closed. It opens today at 17:00.",
    "code": "MERCHANT_CLOSED",
    "mcpCode": -32301,
    "suggestedAction": "Tell the user the merchant is closed and when it opens. Offer to browse other open merchants from the previous search.",
    "retryable": false
  }
}
```

**Resposta contém:**

- `merchantId`: UUID v4 (confirmação); `merchantName`: nome exato; `merchantType`: enum
- `isOpen`: boolean; `operatingHours`: objeto com `today` (hoje) e `weekly` (seg–dom). Formato `{ "openLocal": "HH:mm", "closeLocal": "HH:mm" }` em horário local (não UTC)
- `deliveryMethods[]`: `deliveryMethodId` (enum de backend, ex.: `"ECONOMIC"`, `"EXPRESS"`), `deliveryMethodMode`, `fee` (BRL), `promotionalFee` (BRL | null), `estimatedMinutes` ({min, max})
- `minimumOrderAmount`: number BRL; `featuredItems[]`: `itemId`, `itemName`, `unitPrice`, `promotionalUnitPrice`, `menuSection`, `featuredReason`
- `appDeeplink`: URL para abrir no app iFood; `agentHints`: orientação de navegação do catálogo

## Detalhes do item

### `getItem`

Retorna o detalhe EXAUSTIVO de um item — descrição, grupos de opções, preço promocional, imagem e deeplink. Última etapa da descoberta antes de adicionar ao carrinho.

**Quando usar:**

- SEMPRE após o usuário escolher um item de qualquer lista ou de `getMerchant.featuredItems`
- Antes de adicionar ao carrinho — exibir opções, preço promocional, valores finais
- Para resolver grupos de opções obrigatórios/opcionais
- Para entender o preço final após preço promocional

**Quando NÃO usar:**

- Listar itens (use `searchOffers`, `browseOffers`, `getRecommendations`)
- Sem ter validado `merchantId` E `itemId`
- Listar ofertas do parceiro (use `getMerchant` ou `getRecommendations(BEST_DEALS)`)

**Efeitos colaterais**: Nenhum (somente leitura).

**Pré-condições**: `merchantId` E `itemId` de resultado anterior (search/browse/getMerchant). Ambos OBRIGATÓRIOS. O agente deve ter `userLocation`. O gateway injeta `userId` via header.

**Dependências**: `merchantId` + `itemId` vêm juntos de `searchOffers(ITEM)`, `browseOffers(ITEM)`, `getRecommendations(ITEM)` ou `getMerchant.featuredItems`. Nunca adivinhe IDs. Os valores `optionId` e `customizationId` desta resposta são exigidos por `addItemToCart` (Cart MCP).

#### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `merchantId` | string | Sim | UUID v4 (ex.: `"b8f3c1e2-a456-7890-1234-567890abcdef"`) do parceiro que vende este item. |
| `itemId` | string | Sim | UUID v4 (ex.: `"a1b2c3d4-0001-4000-8000-000000004592"`) do item de um resultado de lista anterior. |
| `userLocation` | object | Sim | `{ "latitude": number, "longitude": number }`. |


#### Resposta (sucesso — item com grupos de opções e promoção)

```
{
  "itemId": "a1b2c3d4-0001-4000-8000-000000004592",
  "itemName": "Pizza Margherita",
  "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
  "merchantName": "Pizza Express",
  "unitPrice": 32.90,
  "itemDescription": "Classic margherita with fresh mozzarella, San Marzano tomato sauce, and basil. 35cm, serves 1-2.",
  "itemImageUrl": "https://cdn.ifood.com.br/items/4592.jpg",
  "appDeeplink": "ifood://dish-details/98aa765a-11f3-481b-b595-7b1b5f93a35c/9341b742-270c-4d26-bd37-41875b65f722",
  "optionGroups": [
    {
      "optionGroupId": "c8a1f3d2-4e5f-4000-8a00-000000000001",
      "name": "Borda",
      "minSelections": 0,
      "maxSelections": 1,
      "options": [
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000001", "name": "Catupiry", "description": "Borda recheada com catupiry", "additionalPrice": 5.00 },
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000002", "name": "Cheddar", "description": "Borda recheada com cheddar", "additionalPrice": 5.00 },
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000003", "name": "Sem borda", "description": "Sem recheio na borda", "additionalPrice": 0.00 }
      ]
    },
    {
      "optionGroupId": "c8a1f3d2-4e5f-4000-8a00-000000000002",
      "name": "Ingredientes extras",
      "minSelections": 0,
      "maxSelections": 3,
      "options": [
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000010", "name": "Pepperoni", "description": "Fatias de pepperoni", "additionalPrice": 6.00 },
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000011", "name": "Cebola caramelizada", "description": "Cebola caramelizada na brasa", "additionalPrice": 4.00 },
        { "optionId": "f6a7b8c9-0001-4000-e000-000000000012", "name": "Azeitona preta", "description": "Azeitonas pretas fatiadas", "additionalPrice": 3.00 }
      ]
    }
  ],
  "promotionalUnitPrice": 27.97,
  "agentHints": {
    "nextStep": "Add this item to the active cart with the chosen quantity and any selected options."
  }
}
```

#### Saída (Erro — item não encontrado)

```
{
  "errors": {
    "message": "The item ID 'a1b2c3d4-0001-4000-8000-000000009999' was not found at merchant 'b8f3c1e2-a456-7890-1234-567890abcdef'. It may have been removed from the menu.",
    "code": "ITEM_NOT_FOUND",
    "mcpCode": -32301,
    "suggestedAction": "Return to the merchant's catalog and present alternative items to the user.",
    "retryable": false
  }
}
```

#### Saída (Erro — incompatibilidade merchant/item)

```
{
  "errors": {
    "message": "Item 'a1b2c3d4-0001-4000-8000-000000004592' does not belong to merchant 'ffffffff-eeee-dddd-cccc-bbbbaaaa9999'. Verify the merchantId — it should match the merchant from the search result where this item was found.",
    "code": "ITEM_MERCHANT_MISMATCH",
    "mcpCode": -32301,
    "suggestedAction": "Use the merchantId that was returned alongside this itemId in the search or inventory response.",
    "retryable": true
  }
}
```

**Resposta contém:**

- `itemId`: UUID v4 (confirmação); `itemName`: nome exato; `merchantId`: UUID v4 (confirmação); `merchantName`: resumo
- `unitPrice`: number BRL (preço base antes do preço promocional); `promotionalUnitPrice`: number BRL (presente quando há preço promocional ativo)
- `itemDescription`: texto descritivo completo; `itemImageUrl`: URL da imagem
- `optionGroups[]`: grupos de customização com `optionGroupId` (UUID), `name`, `minSelections` (int; `0` = opcional, `> 0` = obrigatório), `maxSelections` (int), `options[]` com `optionId` (UUID), `name`, `description`, `additionalPrice` (BRL, pode ser 0)
- `appDeeplink`: URL para abrir no app; `agentHints.nextStep`: orientação para adicionar ao carrinho

## Erros comuns dos agentes

Veja a página de **[Tratamento de erros](/docs/guides/mcps/discovery/erros)** para a taxonomia completa de códigos e estratégias de retry. Os anti-padrões mais frequentes são:

- **Qualificadores em `query`**: "pizza barata perto de mim" pertence a `query: "pizza"` + `refinements: { maxItemPrice: 35, maxDistanceKm: 3 }`.
- **Inventar IDs de taxonomia**: IDs vêm apenas de `listItemTaxonomy` (global) ou `facets.itemTaxonomy` (contextual).
- **Pular o detalhe do parceiro**: chame `getMerchant` antes de apresentar o cardápio.
- **Enviar `userId` a `listItemTaxonomy`**: esta tool é pública — sem identidade, sem geo.
- **Esquecer `merchantType` em `browseOffers`**: é obrigatório — a tool não tem vertical padrão.
- **Construir `nextPageToken`**: reutilize exatamente o token da resposta anterior.

---

## Introdução — /mcps/order/introducao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/introducao

# O que é o Order Tracking MCP?

O Order Tracking MCP é o conjunto de tools do agente para a fase pós-checkout. Depois que `submitOrder` retorna um `orderId`, o agente passa a responder aqui duas perguntas recorrentes do usuário:

| Tool | Pergunta |
| --- | --- |
| `trackOrder` | "Cadê meu pedido? Quando vai chegar?" |
| `getOrder` | "O que eu pedi? Para qual endereço? Quanto custou?" |


## Por que 2 tools (o contrato mais enxuto)

Order Tracking é um domínio de consumo puramente read-only — sem mutações, sem máquinas de estado complexas, sem orquestração entre domínios. Exatamente duas tools cobrem toda pergunta pós-checkout:

- **2 tools são suficientes:** toda pergunta pós-checkout cai em uma de duas categorias: "o que está acontecendo agora?" (`trackOrder`) ou "o que havia neste pedido?" (`getOrder`).
- **3+ tools dividiriam o polling desnecessariamente:** separar em `getTracking`, `getHistory`, `getStatus` forçaria o agente a chamar 3 tools onde 1 basta. A resposta de status já inclui um histórico resumido e o estado atual em uma única chamada.
- **1 tool sobrecarregaria a semântica:** um único `getOrderInfo` combinando rastreamento ao vivo, histórico e detalhes estáticos produziria respostas enormes que inundariam a janela de contexto do agente. Separar ao vivo vs. estático mantém cada resposta focada e proporcional.

## Problemas que resolve

- **Polling, não push:** agentes fazem polling em `trackOrder` numa cadência controlada pelo servidor (via `agentHints.retryMessage`). O servidor dita o intervalo com base no status atual — o agente nunca adivinha o tempo.
- **Detecção de estado terminal:** `agentHints.pollingStop` diz ao agente de forma definitiva quando parar de fazer polling. Nenhuma lista interna de status terminais é necessária.
- **Histórico resumido, não log bruto de eventos:** `statusHistory` retorna uma lista curada (3–5 entradas) de transições recentes, da mais nova para a mais antiga. O log bruto de eventos Kafka fica no backend; a paginação via `moreStatusEvents` permite acessar entradas mais antigas se necessário.
- **Status estruturado — código de máquina + descrição humana:** `status` é um objeto `{ code, description }`. O agente usa `code` para lógica programática e repassa `description` verbatim ao usuário — sem tabela de mapeamento de enums.
- **`getOrder` mínimo, sem payloads inchados:** `getOrder` retorna apenas campos essenciais em formato legível — exatamente o que o agente precisa para responder "o que eu pedi?".
- **Handoff transparente a partir do Cart:** `orderId` vem diretamente de `submitOrder`. O agente nunca fabrica um ID de pedido.
- **Identidade via header HTTP:** ambas as tools validam que o `orderId` pertence ao usuário autenticado (injetado pelo gateway). O agente nunca passa `userId`.

## Fora do escopo

- **Cart, Checkout, Pagamento:** domínios upstream (User, Offer Discovery, Cart).
- **Reembolsos e cancelamentos:** operações do ciclo de vida pós-pedido — ainda não contratadas.
- **Pedir de novo ("o de sempre"):** tratado por um futuro domínio de Order Placement, não pelo Order Tracking.
- **Gestão do pedido do lado do merchant:** aceite de pedido e painel de preparo do restaurante — fora do escopo do MCP voltado ao agente.

## Modelo de identidade

Ambas as tools validam que o `orderId` pertence ao usuário autenticado. A identidade é injetada pelo gateway via header HTTP — o agente nunca passa `userId`, portanto não consegue consultar acidentalmente pedidos de outra pessoa.

## As duas tools atômicas

| Tool | Quando usar | Retorna |
| --- | --- | --- |
| `trackOrder` | Status ao vivo, rastreamento e histórico de eventos | Status atual (`{ code, description }`) + histórico resumido + orientação de polling |
| `getOrder` | Detalhes estáticos do pedido (imutáveis após o checkout) | Merchant, itens, pagamento, endereço de entrega, código de verificação |


## Guia de decisão: qual tool chamar

| Você quer... | Use esta tool | Parâmetro-chave |
| --- | --- | --- |
| "Cadê meu pedido?" / "Quando vai chegar?" | `trackOrder` | `orderId` |
| "O que eu pedi?" | `getOrder` | `orderId` |
| "Qual endereço?" | `getOrder` | `orderId` |
| "Quanto custou?" | `getOrder` | `orderId` |
| "Como paguei?" | `getOrder` | `orderId` |


## Árvore de decisão do agente

```
submitOrder tem sucesso → retorna orderId
                         │
                         ▼
              agente chama trackOrder(orderId)
                         │
                    ┌────┴────┐
                    ▼         ▼
              status é    status é
              ativo       terminal
                    │         │
                    ▼         ▼
            agente lê    agente lê
            retryMessage pollingStop
                    │         │
                    ▼         ▼
            agente espera  agente para
            e faz polling  o polling e
            de novo        reporta o estado
                           final ao usuário
```

O agente também chama `getOrder(orderId)` a qualquer momento para detalhes estáticos ("o que eu pedi?", "quanto custou?") — isso é independente do polling de status.

## Conceitos essenciais

### `status` é um objeto `{ code, description }`

`code` é um enum `SCREAMING_SNAKE_CASE` legível por máquina (ex.: `DELIVERY_ARRIVED_AT_DESTINATION`); `description` é uma frase legível por humanos que o agente repassa verbatim. Compare `code` — nunca o exiba. `description` já carrega ETA e demais contextos.

### `agentHints` sempre retorna os quatro campos

`retryMessage`, `moreStatusEvents`, `pollingStop` e `stopMessage` estão sempre presentes. Campos inativos são `null` em vez de ausentes — verifique por `null`, não pela ausência da chave.

### `statusHistory` é resumido, com o timestamp embutido em `description`

Cada entrada é um objeto `{ code, description }`; o timestamp da transição fica embutido em `description` (ex.: `"...address. (2026-07-13T19:50:21.053283818Z)"`). Isso mantém a contagem de entradas baixa e o payload plano.

### `orderId` vem de `submitOrder` — nunca o fabrique

`orderId` sempre se origina de `submitOrder.response.orderId`. O agente nunca inventa, adivinha ou enumera IDs de pedido.

## Convenções transversais

| Convenção | Padrão |
| --- | --- |
| **Chaves JSON** | `lowerCamelCase` (`orderId`, `shortCode`, `statusHistory`, `agentHints`) |
| **Valores de enum** | `SCREAMING_SNAKE_CASE` (`DELIVERED`, `ON_THE_WAY`, `DELIVERY_ARRIVED_AT_DESTINATION`) |
| **Erros** | Campos na raiz da resposta (sem aninhamento): `errorType`, `code`, `message`, `retryable`, `suggestion` (desvio documentado em relação ao schema canônico `errors`) |
| **Guidance** | `agentHints` presente no sucesso, orientando o comportamento de polling |
| **Identidade** | Gateway injeta identidade via header HTTP; o agente nunca envia `userId` |
| **Moeda** | Sempre BRL |


## Jornada de conexão — como o Order Tracking se conecta aos outros MCPs

Order Tracking é o **consumidor downstream** do Cart. A única entrada é o `orderId` de `submitOrder`:

```
Cart                              Order Tracking
────                              ──────────────
submitOrder ──────────→ orderId ──→ trackOrder
                                    getOrder
```

**Ponto de transição chave:**

- **Cart → Order Tracking:** `orderId` de `submitOrder` é a entrada obrigatória para `trackOrder` e `getOrder`. Sem um checkout concluído, não há o que rastrear.

## Próximos passos

- **[Referência de tools](/docs/guides/mcps/order/tools)** — Especificação detalhada das 2 tools
- **[Tratamento de erros](/docs/guides/mcps/order/erros)** — Códigos de erro e estratégias de recuperação
- **[Casos de uso](/docs/guides/mcps/order/casos-de-uso)** — Cenários reais com código completo

---

## Tratamento de Erros — /mcps/cart/erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/erros

# Tratamento de Erros — Cart MCP

O gateway MCP normaliza todas as respostas HTTP para `200 OK` (exceto `submitOrder`, que retorna `201 Created`). Para saber se houve sucesso ou falha, verifique a presença de `error` na raiz da resposta.

## Protocolo de erro

Todos os erros usam a chave **`"error"`** (singular) — **não** `"errors"` (plural). Essa é uma divergência conhecida do schema canônico das diretrizes unificadas.

```
{
  "error": {
    "code": "CART_NOT_FOUND",
    "message": "O carrinho 'a1b2c3d4-...' não foi encontrado. Ele pode ter expirado ou sido excluído. Crie um novo carrinho.",
    "details": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [
      { "tool": "createCart", "displayName": "Criar novo carrinho", "payload": {} }
    ],
    "userFriendlyMessage": "Carrinho não encontrado. Crie um novo carrinho."
  },
  "agentHints": { "nextStep": "Crie um novo carrinho com addressId, merchantId e itens do usuário." }
}
```

### Campos do `AgentDetail` (o objeto `error`)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `code` | string | null | Código legível do erro (ex.: `"CART_NOT_FOUND"`, `"MERCHANT_CLOSED"`). |
| `message` | string | Instrução para o agente — o que falhou e o que fazer. |
| `details` | object | Contexto estruturado. Valores podem ser strings, arrays ou inteiros — verifique o tipo antes de usar. Pode ser `{}`. |
| `impact` | Impact | null | `canProceedToCheckout: false` bloqueia o checkout. |
| `suggestedActions` | array de SuggestedAction | Ações concretas de recuperação (`tool`, `displayName`, `payload`). |
| `userFriendlyMessage` | string | Mensagem em português para relatar ao usuário final. |


### Tabela de decisão

```
 Recebi response com "error"

 error.impact.canProceedToCheckout?
   false → Erro BLOQUEIA checkout
      NÃO retry com os mesmos parâmetros
      Leia error.code e error.suggestedActions
      Execute a ação de recuperação indicada

   true (ou impact null) → Aviso consultivo
      Pode tentar retry com ajuste ou prosseguir

 Sempre relate error.userFriendlyMessage ao usuário
```

## `AIAgentToolFailureBody` vs. códigos MCP

O contrato do Cart usa `{ "error": AgentDetail, "agentHints": {...} }`. O formato canônico das diretrizes (`{ "errors": { "mcpCode", "message", "code", "suggestedAction", "retryable" } }`) **não** é usado no Cart.

| Campo das diretrizes | Equivalente no Cart | Notas |
| --- | --- | --- |
| `errors` (plural) | `error` (singular) | Diferença direta de chave — leia `response.error`, não `response.errors` |
| `mcpCode` (integer) | Não presente | Use `error.code` para classificar (ex.: `"CART_NOT_FOUND"`) |
| `message` (string) | `error.message` | Mesmo propósito — instrução ao agente |
| `code` (string) | `error.code` (string | null) | Código legível no `AgentDetail` |
| `suggestedAction` (string) | `error.suggestedActions` (array) | Mais rico: cada ação tem `tool`, `displayName` e `payload` pré-preenchido |
| `retryable` (boolean) | Não presente como campo | Infira de `error.impact.canProceedToCheckout`: `false` = os parâmetros atuais nunca terão sucesso |


## Taxonomia de erros

| Código | Retryable? | Quando aparece | Estratégia de recuperação |
| --- | --- | --- | --- |
| `CART_NOT_FOUND` | Não | Qualquer tool com `cartId` inválido/expirado/excluído | Criar novo carrinho com `createCart()`. |
| `CART_EMPTY` | Não | `createCart()` com `items` vazio; `removeItemFromCart` do último item | Adicionar ≥1 item; se o carrinho foi excluído, criar novo. |
| `CART_ITEM_NOT_FOUND` | Não | `updateCartItem()` / `removeItemFromCart()` com `cartItemId` errado (provavelmente `itemId`) | Chamar `getCart()` e usar o `cartItemId` correto. |
| `CART_NOT_READY` | Não | `submitOrder()` sem itens, entrega ou pagamento | Verificar `details.missingRequirements`; configurar o que falta e reenviar. |
| `ITEM_NOT_AVAILABLE` | Não | `addItemToCart()` / `createCart()` com item fora do cardápio | Chamar `getMerchant()` para ver o cardápio atual e usar um `itemId` válido. |
| `MERCHANT_CLOSED` | Não | `createCart()` / `submitOrder()` com estabelecimento fechado | Não retry. Voltar à descoberta e sugerir outro estabelecimento. |
| `MERCHANT_NOT_FOUND` | Não | `listPaymentMethods()` com `merchantId` inválido | Buscar estabelecimento válido via `searchOffers` e tentar de novo. |
| `DELIVERY_OPTIONS_UNAVAILABLE` | Não | `getCartDeliveryMethods()` sem endereço ou sem cobertura | Verificar endereço via `listAddresses`; tentar outro endereço/estabelecimento. |
| `DELIVERY_METHOD_UNAVAILABLE` | Sim | `setCartDelivery()` / `submitOrder()` com método indisponível | `getCartDeliveryMethods()` → apresentar novas opções → `setCartDelivery()` → retry. |
| `PAYMENT_METHOD_UNAVAILABLE` | Sim | `setCartPayment()` com método não aceito | `listPaymentMethods()` → apresentar novas opções → `setCartPayment()` → retry. |
| `CARD_TOKEN_REQUIRED` | Sim | `setCartPayment()` com CREDIT_CARD/DEBIT_CARD sem `cardTokenId` | Pedir dados do cartão ou sugerir PIX/vale. |
| `VOUCHER_INVALID` | Sim | `setVoucher()` com `code`/`campaignId` inválido ou expirado | `listVouchers()` → apresentar vouchers válidos → `setVoucher()` com `code` + `campaignId` corretos. |
| `CONSENT_REQUIRED` | Sim | `submitOrder()` sem `userConsent: true` | Apresentar o resumo, obter confirmação explícita e reenviar. |


**Regra de ouro**: quando `error.impact.canProceedToCheckout` é `false`, o retry com os **mesmos parâmetros** nunca terá sucesso. Uma ação diferente é necessária. A presença de `suggestedActions` não-vazio confirma isso.

## Estratégia de retry

```
async function handleError(response) {
  if (!response.error) {
    return { action: "proceed", data: response };
  }

  const { error } = response;
  const canProceed = error.impact?.canProceedToCheckout ?? true;

  // Erros que NUNCA devem retry
  if (error.code === "MERCHANT_CLOSED" || error.code === "ITEM_NOT_AVAILABLE") {
    return { action: "fail", message: `${error.code}: ${error.userFriendlyMessage}` };
  }

  // Erros que BLOQUEIAM checkout — executar ação de recuperação
  if (canProceed === false) {
    return {
      action: "recover",
      nextStep: response.agentHints.nextStepBeforeCheckout ?? response.agentHints.nextStep,
      suggestedTool: error.suggestedActions[0]?.tool
    };
  }

  // Avisos consultivos — backoff + retry com os mesmos parâmetros
  return { action: "retry", backoffSeconds: Math.pow(2, attemptCount) };
}
```

### Backoff exponencial (máx 3 tentativas)

```
async function submitOrderWithRetry(cartId, maxAttempts = 3) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const order = await cartClient.submitOrder({
      cartId, userConsent: true, document: "123.456.789-00"
    });

    if (!order.error) return order; // Sucesso

    // Não-retryable? Parar.
    if (order.error.impact?.canProceedToCheckout === false) {
      throw new Error(`Erro fatal: ${order.error.code}`);
    }

    // Retryable — backoff
    const backoffSeconds = Math.pow(2, attempt);
    console.log(`Aguardando ${backoffSeconds}s antes de retry...`);
    await new Promise(r => setTimeout(r, backoffSeconds * 1000));
  }
  throw new Error(`Máximo de tentativas excedido (${maxAttempts})`);
}
```

## Anti-padrões comuns

### 1. Ler `response.errors` em vez de `response.error`

```
// ERRADO
if (response.errors) { ... }
// CORRETO — a chave é singular
if (response.error) { ... }
```

### 2. Confundir `cartItemId` com `itemId`

```
// ERRADO — usar itemId onde cartItemId esperado
await cartClient.updateCartItem({ cartId, cartItemId: catalogItemId, quantity: 3 });
// Resultado: CART_ITEM_NOT_FOUND

// CORRETO — salvar cartItemId de addItemToCart/getCart e usá-lo
```

### 3. Omitir `options` array

```
// ERRADO
await cartClient.addItemToCart({ cartId, itemId, quantity: 1 });
// CORRETO
await cartClient.addItemToCart({ cartId, itemId, quantity: 1, options: [] });
```

### 4. Submeter sem entrega/pagamento

```
// ERRADO — createCart direto para submitOrder
// Resultado: CART_NOT_READY (faltando deliveryMethod/paymentMethod)

// CORRETO — getCartDeliveryMethods → setCartDelivery; listPaymentMethods → setCartPayment
```

### 5. Retry infinito em erro não-retryable

```
// ERRADO — loop sem validar canProceedToCheckout
// CORRETO — verificar error.impact.canProceedToCheckout antes de retry
```

### 6. Ignorar `suggestedActions`

Quando o erro é recuperável, `suggestedActions[0]` indica a tool e o `payload` a usar. Avalie sempre se outra tool atende melhor — o `tool` é sugestão forte, não comando.

## Mapeamento de campos: guidelines vs Cart

| Campo Cart | Finalidade | Notas |
| --- | --- | --- |
| `error.code` | Classificação do erro | Use para rotear a recuperação (ex.: `"CART_NOT_READY"`) |
| `error.message` | Instrução ao agente | Explica o que falhou e o que fazer |
| `error.details` | Contexto estruturado | Ex.: `missingRequirements`, `availableCartItemIds` |
| `error.impact.canProceedToCheckout` | Bloqueia checkout? | `false` = não retry com mesmos parâmetros |
| `error.suggestedActions` | Ações de recuperação | Cada item tem `tool`, `displayName`, `payload` |
| `error.userFriendlyMessage` | Mensagem ao usuário | Em português |
| `agentHints` | Próximo passo | `nextStep` (sucesso) / `nextStepBeforeCheckout` (erro) |


## Checklist de segurança

-  Verificar `response.error` (singular) depois de cada chamada
-  Ler `error.code` para classificar o erro
-  Validar `error.impact.canProceedToCheckout` antes de qualquer retry
-  Seguir `suggestedActions` / `agentHints` para a ação de recuperação
-  Aplicar backoff exponencial (máx 3 tentativas)
-  Nunca retry em `MERCHANT_CLOSED` ou `ITEM_NOT_AVAILABLE`
-  Distinguir `cartItemId` vs `itemId`; sempre incluir `options`; `userConsent: true`

---

## Introdução — /mcps/cart/introducao

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/introducao

# O que é o Cart MCP?

O Cart MCP é o conjunto de tools do agente para montar e confirmar um pedido. Ele responde a treze perguntas em todo fluxo de compra:

| Tool | Pergunta |
| --- | --- |
| `createCart` | "Começar um novo carrinho para este estabelecimento, endereço e itens." |
| `getCart` | "O que há no meu carrinho e quanto vai custar?" |
| `getCartDeliveryMethods` | "Quais métodos de entrega e horários estão disponíveis para este carrinho?" |
| `addItemToCart` | "Adicionar este item (com suas opções e customizações) ao carrinho." |
| `updateCartItem` | "Alterar a quantidade, opções ou notas deste item do carrinho." |
| `removeItemFromCart` | "Remover este item do carrinho." |
| `removeVoucher` | "Limpar o voucher aplicado no momento." |
| `listVouchers` | "Quais vouchers e cupons posso aplicar a este carrinho?" |
| `setVoucher` | "Aplicar este voucher ou cupom ao carrinho." |
| `setCartDelivery` | "Escolher como e quando o pedido será entregue." |
| `setCartPayment` | "Escolher como o pedido será pago." |
| `listPaymentMethods` | "Quais formas de pagamento este estabelecimento aceita?" |
| `submitOrder` | "Enviar o pedido — estou pronto." |


## Por que 13 tools atômicas

Cada tool tem uma intenção única e plana — sem `operation` enums e sem despacho condicional de parâmetros. Isso segue o mandato de conformidade Google MCP (G1) e as diretrizes do contrato unificado:

- **`getCartDeliveryMethods`** é uma tool dedicada de leitura — o agente descobre métodos de entrega e horários válidos antes de chamar `setCartDelivery`.
- **`listVouchers`** é uma tool dedicada de leitura — o agente descobre quais vouchers/cupons são aplicáveis ao carrinho antes de chamar `setVoucher`.
- **`setVoucher`** e **`removeVoucher`** são mutações separadas — aplicar e remover um voucher são intenções distintas do usuário, cada uma com sua própria tool.
- **`addItemToCart`**, **`updateCartItem`** e **`removeItemFromCart`** são três operações atômicas separadas, não três valores de um `operation` enum.

**Sem `operation` enum em lugar nenhum.** O nome de cada tool é autoexplicativo.

## O modelo Option / Customization

A API de Cart representa a configuração de um item como uma hierarquia de dois níveis:

```
Item
 └── Option
      └── Customization
```

- **`Option`** representa um grupo de escolha de nível superior (tamanho, tipo de massa, acompanhamento). Cada opção tem um `optionId`, um `name`, uma `quantity`, um `customerNote` opcional e um array de `customizations` aninhadas.
- **`Customization`** representa uma sub-escolha dentro de uma opção (ingredientes extras, remoções, instruções de preparo). Cada customização tem um `customizationId`, um `name`, uma `quantity` e um `customerNote` opcional.

Ambas são passadas no array `options` ao adicionar ou atualizar itens. A resposta de `getItem` (Offer Discovery) fornece as opções e customizações disponíveis para um item de catálogo — o agente deve selecionar valores válidos de `optionId` e `customizationId` a partir dessa resposta.

## Fora do escopo

- **Offer Discovery:** busca de itens, detalhe de estabelecimento, taxonomia — domínio upstream (`02-offer-discovery-mcp.md`).
- **Account:** gestão de endereços e identidade — domínio upstream (`01-user-mcp.md`).
- **Order tracking:** consulta de status pós-checkout e rastreamento — domínio downstream (`04-order-tracking-mcp.md`).
- **Reembolsos e cancelamentos:** operações pós-pedido — ainda não contratadas.
- **OAuth, webview, registro de integrador:** tratados de forma transparente pelo gateway MCP — o agente não gerencia tokens de autenticação, abre web views nem se registra como integrador.

## Comportamento do gateway: status HTTP e erros

O gateway MCP normaliza todas as respostas HTTP para status 200 do ponto de vista do agente. A API Cart Integration Hub pode usar códigos HTTP distintos internamente (400 para falhas recuperáveis com `AIAgentToolFailureBody`; 404/500 para não-encontrado e erros de servidor com `CartErrorResponse`), mas o agente vê apenas o corpo JSON. Para saber se houve sucesso ou falha, verifique a presença de `error`:

- **Sucesso:** `error` está ausente. A resposta corresponde ao schema de sucesso da tool (ex.: `CartDetailsResponse`, `CheckoutSuccessBody`, `PaymentListPayload`, `VoucherListPayload`, `CartDeliveryOptionsResponse`).
- **Falha:** `error` está presente como um objeto `AgentDetail`. Leia `error.message` para instruções, `error.suggestedActions` para caminhos de recuperação e `agentHints` para orientação do próximo passo.

Todos os erros usam a chave `"error"` (singular) na raiz da resposta — **não** `"errors"` (plural). Essa é uma divergência conhecida do schema de erro canônico das diretrizes unificadas. Veja a página de [Tratamento de erros](/docs/guides/mcps/cart/erros) para o mapeamento completo.

## As treze tools atômicas

| Tool | Quando usar | Retorna |
| --- | --- | --- |
| `createCart` | Iniciar um carrinho novo (do zero ou a partir de um pedido anterior) | `CartDetailsResponse` com o novo `cartId` |
| `getCart` | Consultar o estado completo do carrinho | `CartDetailsResponse` |
| `getCartDeliveryMethods` | Descobrir métodos de entrega e horários antes de definir a entrega | `CartDeliveryOptionsResponse` |
| `addItemToCart` | Adicionar um item do catálogo com opções | `CartDetailsResponse` (salve o `cartItemId`) |
| `updateCartItem` | Alterar quantidade, opções ou notas de um item já no carrinho | `CartDetailsResponse` |
| `removeItemFromCart` | Remover um item do carrinho | `CartDetailsResponse` |
| `removeVoucher` | Limpar o voucher aplicado | `CartDetailsResponse` |
| `listVouchers` | Descobrir vouchers/cupons aplicáveis ao carrinho | `VoucherListPayload` |
| `setVoucher` | Aplicar um voucher (`code` + `campaignId`) | `CartDetailsResponse` |
| `setCartDelivery` | Definir método de entrega e, opcionalmente, horário | `CartDetailsResponse` |
| `setCartPayment` | Definir forma de pagamento | `CartDetailsResponse` |
| `listPaymentMethods` | Listar formas de pagamento aceitas pelo estabelecimento | `PaymentListPayload` |
| `submitOrder` | Enviar o pedido | `CheckoutSuccessBody` com `orderId` |


## Guia de decisão: qual tool chamar

| Você quer... | Use esta tool | Entradas necessárias |
| --- | --- | --- |
| Começar um carrinho novo | `createCart` | Caminho A: `addressId` + `merchantId` + `items[]` (do zero). Caminho B: `orderId` sozinho (reordenar). Opcionais: `deliveryMethod`, `paymentMethod` |
| Ver o que há no carrinho | `getCart` | `cartId` |
| Descobrir métodos de entrega e horários | `getCartDeliveryMethods` | `cartId` |
| Adicionar um item com opções | `addItemToCart` | `cartId`, `itemId`, `quantity`, `options[]`, `customerNote` opcional |
| Alterar quantidade/opções de um item | `updateCartItem` | `cartId`, `cartItemId`, `itemId`, `quantity`, `options[]`, `customerNote` opcional |
| Remover um item | `removeItemFromCart` | `cartId`, `cartItemId` |
| Limpar voucher aplicado | `removeVoucher` | `cartId` |
| Descobrir vouchers aplicáveis | `listVouchers` | `cartId` |
| Aplicar um voucher | `setVoucher` | `cartId`, `code`, `campaignId` |
| Definir método de entrega e horário | `setCartDelivery` | `cartId`, `deliveryMethodId`, `selectedTimeSlotId` opcional |
| Definir forma de pagamento | `setCartPayment` | `cartId`, `paymentMethodId`, `cardTokenId` opcional |
| Ver formas de pagamento disponíveis | `listPaymentMethods` | `merchantId` |
| Enviar o pedido | `submitOrder` | `cartId`, `userConsent`, `document` opcional |


## Árvore de decisão do agente

Antes de chamar qualquer tool do Cart, o agente deve ter resolvido, a partir dos domínios upstream:

```
Do User MCP:
  └── addressId (de listAddresses ou createAddress)

Do Offer Discovery MCP:
  ├── merchantId (de qualquer tool de lista ou detalhe)
  └── itemId (para cada item a adicionar — de searchOffers, browseOffers, getRecommendations ou getItem)
      └── options (da resposta de getItem — valores de optionId e customizationId)

Do Order Tracking MCP:
  └── orderId (para fluxos de reordenar — opcional)
```

```
START: o agente tem addressId + merchantId + pelo menos um itemId com options (do zero) OU orderId (reordenar)
│
├── createCart(merchantId?, addressId?, items?, orderId?, deliveryMethod?, paymentMethod?)
│   │   NOTA: dois caminhos mutuamente exclusivos:
│   │   - Caminho A (do zero): merchantId + addressId + items[] (todos obrigatórios)
│   │   - Caminho B (reordenar): orderId sozinho (merchantId, addressId, items derivados automaticamente)
│   │
│   ├── Sucesso → cartId retornado, carrinho ativo
│   │   │
│   │   ├── Precisa ver o estado do carrinho?
│   │   │   └── getCart(cartId)
│   │   │
│   │   ├── Precisa adicionar mais itens?
│   │   │   └── addItemToCart(cartId, itemId, quantity, customerNote?, options[])
│   │   │       └── Salve o cartItemId retornado para updates futuros
│   │   │
│   │   ├── Precisa alterar um item?
│   │   │   ├── updateCartItem(cartId, cartItemId, itemId, quantity, customerNote?, options[])
│   │   │   └── removeItemFromCart(cartId, cartItemId)
│   │   │
│   │   ├── Precisa descobrir opções de entrega?
│   │   │   └── getCartDeliveryMethods(cartId) → depois setCartDelivery com o método escolhido
│   │   │
│   │   ├── Precisa descobrir formas de pagamento?
│   │   │   └── listPaymentMethods(merchantId) → depois setCartPayment com a forma escolhida
│   │   │
│   │   ├── Precisa descobrir vouchers disponíveis?
│   │   │   └── listVouchers(cartId) → depois setVoucher com code + campaignId escolhidos
│   │   │
│   │   ├── Precisa remover um voucher?
│   │   │   └── removeVoucher(cartId)
│   │   │
│   │   └── Pronto para enviar?
│   │       └── submitOrder(cartId, userConsent: true, document?)
│   │           ├── Sucesso → orderId → Order Tracking MCP
│   │           └── Erro → leia error.message e suggestedActions → corrija → tente de novo
│   │
│   └── Erro → trate (veja cenários de erro do createCart: estabelecimento fechado, carrinho vazio, endereço inválido)
```

## Erros comuns de agentes

- **Usar `itemId` onde `cartItemId` é exigido:** `updateCartItem` e `removeItemFromCart` exigem `cartItemId` — o identificador atribuído quando o item entrou no carrinho. `addItemToCart` exige `itemId` — o identificador de catálogo do Offer Discovery. São escopos diferentes.
- **Pular `getCartDeliveryMethods` antes de `setCartDelivery`:** o agente deve obter métodos e horários válidos de `getCartDeliveryMethods` antes de chamar `setCartDelivery`. Hardcodar IDs de método de entrega falha.
- **Omitir `options` em `addItemToCart` e `updateCartItem`:** ambas as tools exigem o array `options` (mesmo que vazio). Itens sem `options` são rejeitados.
- **Pular a configuração do pagamento:** chamar `submitOrder` antes de definir a forma de pagamento falha. Sempre `listPaymentMethods` → apresentar opções → `setCartPayment` → `submitOrder`.
- **Hardcodar `code`/`campaignId` de voucher em vez de usar `listVouchers`:** `setVoucher` exige o `code` e o `campaignId` exatos retornados por `listVouchers` para o carrinho atual. Vouchers são dinâmicos e escopados ao carrinho — não invente nem reutilize códigos.
- **Confundir `setVoucher` com `removeVoucher`:** aplicar e remover são intenções distintas, com tools distintas.
- **Não salvar `cartItemId`:** após `addItemToCart`, o array `items[]` da resposta contém o novo `cartItemId`. Salve-o — você precisará dele para `updateCartItem` e `removeItemFromCart`.
- **Recriar um carrinho quando já existe um:** `createCart` sempre cria um carrinho novo. Se já há um carrinho ativo, retome com `getCart`.
- **Omitir `userConsent` em `submitOrder`:** o boolean `userConsent` é obrigatório. Defina como `true` somente depois de o usuário confirmar explicitamente.
- **Seguir cegamente `suggestedActions[].tool`:** o campo `tool` é uma sugestão de conveniência, não um comando. Avalie sempre se outra tool atende melhor à intenção do usuário.
- **Esquecer o documento de identificação antes de `submitOrder`:** a regulação brasileira exige CPF (pessoa física) ou CNPJ (empresa). Contas estrangeiras precisam de número de passaporte. Peça o documento antes de enviar; se o usuário não fornecer, omita o parâmetro `document` — ele é opcional.
- **Informar `orderId` junto com `merchantId`/`addressId`/`items` em `createCart`:** são caminhos mutuamente exclusivos. Com `orderId`, os demais campos são ignorados.

## Conceitos essenciais

### Três IDs distintos — não confunda

| ID | Vem de | Escopo | Usa em | NÃO usa em |
| --- | --- | --- | --- | --- |
| **`itemId`** | Offer Discovery (catálogo do estabelecimento) | Válido em qualquer carrinho do estabelecimento | `addItemToCart`, `createCart`, `updateCartItem` (para validação) | `updateCartItem` (parâmetro `cartItemId`), `removeItemFromCart` |
| **`cartItemId`** | Retornado por `createCart`, `addItemToCart` ou `getCart` | Válido apenas neste carrinho específico | `updateCartItem`, `removeItemFromCart` | `addItemToCart`, `createCart` |
| **`cartId`** | Retornado por `createCart` | Válido para operações neste carrinho | Quase todas as tools (exceto `listPaymentMethods`, que usa `merchantId`) | Parâmetro em `createCart` |


### O array `options` é obrigatório

Em `addItemToCart` e `updateCartItem`, o array `options` é obrigatório — mesmo que vazio (`[]`). Um `options: []` significa "o agente confirmou que este item não tem opções a selecionar", em oposição a omitir o campo, que poderia significar "o agente esqueceu de verificar".

### `code` + `campaignId` de voucher

`setVoucher` exige o par `code` + `campaignId` retornado por `listVouchers` — não um código solto. O `campaignId` desambigua o contexto da campanha: o mesmo `code` pode existir em campanhas diferentes e mapear efeitos diferentes.

### `userConsent` e `document` em `submitOrder`

`userConsent` é um gate de comportamento explícito: o agente deve confirmar com o usuário antes do checkout. `document` carrega CPF, CNPJ ou passaporte — coletado antes de enviar, mas opcional se o usuário não fornecer.

## Convenções transversais

| Convenção | Padrão |
| --- | --- |
| **Chaves JSON** | `lowerCamelCase` |
| **Identificadores** | UUID v4 para `cartId`, `itemId`, `cartItemId`, `merchantId`, `addressId`, `paymentMethodId`, `campaignId` |
| **HTTP Status** | Gateway normaliza para `200 OK`; `submitOrder` retorna `201 Created` |
| **Erros** | Chave `"error"` (singular) na raiz, com `code`, `message`, `details`, `impact`, `suggestedActions`, `userFriendlyMessage` |
| **Guidance** | `agentHints` presente em sucesso e erro, orientando a próxima ação |
| **Moeda** | BRL sempre, em decimal (ex.: `32.90`, não `3290`) |
| **Método HTTP** | `listPaymentMethods` usa GET com `merchantId` como query param; as demais tools usam POST |


## Connection Journey — como o Cart se conecta aos outros MCPs

O Cart MCP é a **ponte entre o Offer Discovery e o Order Tracking** — transforma as seleções do usuário em um pedido confirmado.

```
Offer Discovery                 Cart                              Order Tracking
─────────                       ────                              ──────────────
searchOffers              ──→ merchantId ──→ createCart
browseOffers                  itemId          addItemToCart
getRecommendations            options         updateCartItem
getMerchant                                    removeItemFromCart
getItem                                        removeVoucher
                                               listVouchers
                                               setVoucher
                                               getCartDeliveryMethods
                                               setCartDelivery
                                ┌────────── listPaymentMethods
                                │
                                ▼
listAddresses ──→ addressId ──→ createCart (addressId)
createAddress

                                ┌────────── submitOrder ──→ orderId ──→ trackOrder
                                │                                        getOrder
                                ▼
                           (pedido confirmado)
```

**Pontos de transição:**

- **Offer Discovery → Cart:** `merchantId`, `itemId` e `options` (de `getItem`) são as entradas de `createCart` e `addItemToCart`.
- **Account → Cart:** `addressId` do User MCP é a entrada de `createCart`.
- **Cart → Order Tracking:** `orderId` de `submitOrder` é a entrada de `trackOrder` e `getOrder`.

Cada tool do domínio Cart serve a um propósito único e bem definido. O agente avança linearmente: criar carrinho → descobrir entrega → definir entrega → descobrir pagamento → definir pagamento → (opcional) descobrir voucher → aplicar voucher → confirmar → enviar.

## Próximos passos

- **[Referência de tools](/docs/guides/mcps/cart/tools)** — Especificação detalhada de cada uma das 13 tools
- **[Tratamento de erros](/docs/guides/mcps/cart/erros)** — Códigos de erro e estratégias de recuperação
- **[Casos de uso](/docs/guides/mcps/cart/casos-de-uso)** — Cenários reais com código completo

---

## Tools — /mcps/order/tools

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/order/tools

# Order Tracking MCP — As 2 Tools

O Order Tracking MCP expõe 2 tools read-only para monitorar e inspecionar pedidos. Este guia documenta cada uma: quando usar, parâmetros, respostas e orientações.

## Visão geral das 2 tools

| Tool | Descrição | Quando usar |
| --- | --- | --- |
| [`trackOrder`](#trackorder) | Status atual (`{ code, description }`), histórico resumido de eventos e orientação de polling | Status ao vivo: "cadê meu pedido?", "quando vai chegar?" |
| [`getOrder`](#getorder) | Detalhes estáticos do pedido: merchant, itens, pagamento, endereço | Referência: "o que eu pedi?", "qual endereço?", "quanto custou?" |


## Índice rápido

- [trackOrder](#trackorder) — Status ao vivo e polling
- [getOrder](#getorder) — Detalhes estáticos do pedido

## Convenções transversais

Todas as tools seguem estas convenções:

- **Chaves JSON**: `lowerCamelCase` (`orderId`, `statusHistory`, `agentHints`)
- **Identificadores**: UUID v4 para `orderId`
- **Valores de enum**: `SCREAMING_SNAKE_CASE` (`DELIVERED`, `ON_THE_WAY`, `DELIVERY_ARRIVED_AT_DESTINATION`)
- **Erros**: campos na raiz da resposta (sem aninhamento) — `errorType`, `code`, `message`, `retryable`, `suggestion`
- **`agentHints`**: sempre retorna os quatro campos (`retryMessage`, `moreStatusEvents`, `pollingStop`, `stopMessage`); os inativos são `null`
- **Identidade**: o gateway injeta identidade via header HTTP; o agente nunca envia `userId`
- **Efeitos colaterais**: nenhum — ambas as tools são read-only

## trackOrder

Recupera o status atual de um pedido como um objeto `{ code, description }`, além de um histórico resumido de eventos (3–5 transições recentes) e orientação de polling. Use para monitorar pedidos desde `submitOrder` até o estado terminal. **O servidor controla a cadência de polling** — siga `retryMessage`, não um intervalo fixo.

**Quando usar:**

- DEPOIS que `submitOrder` retornar `orderId` (ponto de entrada do Order Tracking)
- Quando o usuário perguntar "cadê meu pedido?", "quando vai chegar?", "já saiu para entrega?"
- Para todas as consultas de status ao vivo
- Chamar repetidamente seguindo a cadência controlada pelo servidor (`retryMessage`)

**Quando NÃO usar:**

- Para listar o histórico de pedidos passados (read-only; use `getOrder` para detalhes)
- Sem um `orderId` válido de `submitOrder` (nunca adivinhe ou fabrique IDs)
- Ignorando `agentHints.pollingStop` (DEVE parar no estado terminal)
- Ignorando `retryMessage` — polling agressivo sem respeitar a cadência (rate limit)

**Efeitos colaterais:** Nenhum (read-only). Polling puro — sem mutações.

**Precondições:**

- `orderId` válido de `submitOrder.response.orderId`
- Usuário autenticado (gateway injeta identidade via header)
- Servidor valida que o pedido pertence ao usuário autenticado

**Dependências:** Chamar após `submitOrder` (→ `orderId`). `orderId` é um UUID v4 — nunca o fabrique. Rastreabilidade: `orderId` ← `submitOrder.response.orderId` (Cart MCP).

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `orderId` | string | sim | Identificador do pedido (UUID v4), obtido de `submitOrder.response.orderId`. |


### Resposta (sucesso — pedido ativo, a caminho)

```
{
  "status": {
    "code": "DELIVERY_ARRIVED_AT_DESTINATION",
    "description": "Delivery person arrived at order delivery address."
  },
  "statusHistory": [
    {
      "code": "DELIVERY_ARRIVED_AT_DESTINATION",
      "description": "Delivery person arrived at order delivery address. (2026-07-13T19:50:21.053283818Z)"
    },
    {
      "code": "ORDER_LATE",
      "description": "Order exceeded estimated delivery time. (2026-06-26T21:44:55.446846514Z)"
    },
    {
      "code": "DISPATCHED",
      "description": "Merchant released order for delivery. (2026-06-18T00:05:39.350Z)"
    }
  ],
  "agentHints": {
    "retryMessage": "Please call again in 60 seconds for updates",
    "moreStatusEvents": "Call trackOrder(order_id='316eecf7-9902-4bab-8499-82436edf7d19') with next_page_token=eyJvIjozfQ== to fetch older events",
    "pollingStop": null,
    "stopMessage": null
  }
}
```

### Resposta (sucesso — estado terminal)

```
{
  "status": {
    "code": "DELIVERED",
    "description": "Order delivered to the customer."
  },
  "statusHistory": [
    {
      "code": "DELIVERED",
      "description": "Order delivered to the customer. (2026-07-13T20:02:11.120931044Z)"
    },
    {
      "code": "DELIVERY_ARRIVED_AT_DESTINATION",
      "description": "Delivery person arrived at order delivery address. (2026-07-13T19:50:21.053283818Z)"
    },
    {
      "code": "DISPATCHED",
      "description": "Merchant released order for delivery. (2026-06-18T00:05:39.350Z)"
    }
  ],
  "agentHints": {
    "retryMessage": null,
    "moreStatusEvents": null,
    "pollingStop": true,
    "stopMessage": "Do not call this tool for this order."
  }
}
```

### Resposta (sucesso — pagamento recusado)

```
{
  "status": {
    "code": "PAYMENT_DECLINED",
    "description": "Couldn't process your payment."
  },
  "statusHistory": [
    {
      "code": "PAYMENT_DECLINED",
      "description": "Payment declined. (2026-06-18T00:05:06.120Z)"
    },
    {
      "code": "ORDER_CREATED",
      "description": "Order created. (2026-06-18T00:04:58.891Z)"
    }
  ],
  "agentHints": {
    "retryMessage": "Please check your card details or try using a different payment method",
    "moreStatusEvents": null,
    "pollingStop": true,
    "stopMessage": null
  }
}
```

### Resposta (erro — pedido não encontrado)

```
{
  "errorType": "ResourceNotFoundError",
  "code": "ORDER_NOT_FOUND",
  "message": "Order ID 'f47ac10b-58cc-4372-a567-0e02b2c3d479' not found",
  "retryable": false,
  "suggestion": "Do not attempt to look up this Order ID again. Tell the user to verify the order reference."
}
```

### Campos de `agentHints`

O objeto `agentHints` **sempre retorna os quatro campos**. Campos inativos são `null` em vez de ausentes — verifique por `null`, não pela ausência da chave.

| Campo | Quando presente | Significado |
| --- | --- | --- |
| `retryMessage` | Pedidos ativos (não terminais) | Instrução: "Please call again in N seconds for updates". Parseie o intervalo e agende o próximo poll de acordo. `null` para pedidos terminais. |
| `moreStatusEvents` | Quando há histórico de eventos mais antigo | Instrução: "Call trackOrder(order_id='...') with next_page_token=...". Busque entradas mais antigas além das 3–5 mais recentes. `null` quando não há eventos mais antigos. |
| `pollingStop` | Estados terminais (Entregue, Cancelado, Pagamento Recusado, etc.) | `true` significa parar o polling imediatamente — o pedido não mudará de estado. `false` ou `null` para pedidos ativos. |
| `stopMessage` | Estados terminais | Confirmação legível: "Do not call this tool for this order." `null` para pedidos ativos. |


## getOrder

Recupera detalhes estáticos do pedido — merchant, itens, preços (BRL), endereço de entrega com código de verificação e resumo de pagamento. Os dados são imutáveis após o checkout e seguros para cache. Retorna um payload mínimo e legível, otimizado para interpretação do agente.

**Quando usar:**

- Usuário pergunta "o que eu pedi?", "quanto custou?", "qual endereço?" ou "como paguei?"
- Para detalhar o desdobramento de itens com personalizações
- Para exibir o desdobramento de preços (subtotal, taxas, descontos, total)
- Para confirmar endereço e formas de entrega/pagamento
- A qualquer momento após o checkout para referência de pedidos passados

**Quando NÃO usar:**

- Para rastreamento/status ao vivo (use `trackOrder`)
- Para listar múltiplos pedidos (não há tool de listagem disponível)
- Sem um `orderId` válido (nunca adivinhe)
- Esperando que os dados mudem após o checkout (eles são imutáveis)

**Efeitos colaterais:** Nenhum (read-only). Consumo puro — dados estáticos.

**Precondições:**

- `orderId` válido de `submitOrder.response.orderId`
- Usuário autenticado (gateway injeta identidade via header)
- Servidor valida que o pedido pertence ao usuário autenticado

**Dependências:** Chamar após `submitOrder` (→ `orderId`). `orderId` é um UUID v4 — nunca o fabrique. Rastreabilidade: `orderId` ← `submitOrder.response.orderId` (Cart MCP).

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `orderId` | string | sim | Identificador do pedido (UUID v4), obtido de `submitOrder.response.orderId`. |


### Resposta (sucesso)

```
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "shortCode": "ABCD",
  "merchant": "Pizza Express",
  "items": [
    "Margherita Pizza (x2, R$ 65.80 + R$ 5.00 extra cheese)",
    "Coca-Cola 350ml (x1, R$ 6.50)"
  ],
  "payment": "Credit Card - Total R$ 72.30",
  "delivery": {
    "address": "Av. Paulista, 1000, Bela Vista, São Paulo - SP",
    "verificationCode": "ABCD"
  }
}
```

### Resposta (erro — pedido não encontrado)

```
{
  "errorType": "ResourceNotFoundError",
  "code": "ORDER_NOT_FOUND",
  "message": "Order ID 'f47ac10b-58cc-4372-a567-0e02b2c3d479' not found",
  "retryable": true,
  "suggestion": "If the order was just created, wait a few seconds and retry. For older orders, the data may have been archived."
}
```

### Resposta (erro — acesso negado)

```
{
  "errorType": "AccessDeniedError",
  "code": "ORDER_ACCESS_DENIED",
  "message": "Access denied. The requested order does not belong to the authenticated user.",
  "retryable": false,
  "suggestion": "Only query orders that belong to the current user. Verify the orderId came from this user's checkout."
}
```

### Notas sobre a saída

- `id` é o UUID do pedido (igual ao `orderId` de entrada)
- `shortCode` é a referência do pedido voltada ao usuário (ex.: exibida em recibos)
- `merchant` é o nome do estabelecimento (string)
- `items` é um array de descrições legíveis de itens, combinando nome + quantidade + personalizações + preço
- `payment` é um resumo de pagamento legível (forma + total em BRL)
- `delivery.address` é o endereço de entrega formatado (string)
- `delivery.verificationCode` é o código exibido na entrega (para verificação do pedido pelo entregador)
- **Sem campo de status:** use `trackOrder` para status ao vivo. `getOrder` é puramente estático.

## Exemplos de códigos de status

`status.code` e `statusHistory[].code` são enums `SCREAMING_SNAKE_CASE` legíveis por máquina. Estes são os valores que aparecem neste contrato — compare `code`, nunca o exiba ao usuário.

| Código | Significado |
| --- | --- |
| `ORDER_CREATED` | Pedido criado. |
| `PAYMENT_DECLINED` | Não foi possível processar o pagamento. |
| `CONFIRMED` | Merchant confirmou o pedido. |
| `PREPARING` | Merchant está preparando o pedido. |
| `DISPATCHED` | Merchant liberou o pedido para entrega. |
| `ON_THE_WAY` | O entregador está em trânsito. |
| `ORDER_LATE` | Pedido excedeu o tempo estimado de entrega. |
| `DELIVERY_ARRIVED_AT_DESTINATION` | Entregador chegou ao endereço. |
| `DELIVERED` | Pedido entregue ao cliente. |


## Erros comuns do agente

- **Fazer polling sem ler `agentHints.retryMessage`:** o servidor diz quanto tempo esperar. Se `retryMessage` disser "Please call again in 60 seconds for updates", espere 60 segundos — não 5. Polling agressivo pode disparar rate limits.
- **Ignorar `agentHints.pollingStop`:** quando `pollingStop` é `true`, o pedido atingiu um estado terminal. Pare imediatamente. Continuar fazendo polling em um pedido entregue é um bug.
- **Fabricar `orderId`:** `orderId` sempre vem de `submitOrder` ou do histórico de pedidos do usuário. Nunca invente, adivinhe ou enumere IDs de pedido.
- **Confundir `status.code` com `status.description`:** compare `code`, nunca o exiba. Repasse `description` verbatim ao usuário.
- **Ignorar `moreStatusEvents` quando disponível:** se for necessário histórico mais antigo além das 3–5 mais recentes, use o `next_page_token` fornecido para buscar entradas adicionais.

---

## Tools — /mcps/cart/tools

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/tools

# Cart MCP — As 13 Tools

O Cart MCP oferece 13 tools atômicas para gerenciar carrinhos de compras. Este guia documenta cada uma: quando usar, parâmetros, respostas e exemplos.

## Visão geral das 13 tools

| Tool | Descrição | Quando usar |
| --- | --- | --- |
| [`createCart`](#createcart) | Criar novo carrinho com estabelecimento, endereço e itens | Entrada no fluxo Cart; ou reordenação via `orderId` |
| [`getCart`](#getcart) | Retornar o estado completo do carrinho | Revisar, validar ou resumir antes de qualquer mutação |
| [`getCartDeliveryMethods`](#getcartdeliverymethods) | Listar métodos de entrega e horários disponíveis | Descobrir antes de `setCartDelivery` |
| [`addItemToCart`](#additemtocart) | Adicionar um item do catálogo com opções | Adicionar item novo |
| [`updateCartItem`](#updatecartitem) | Alterar quantidade, opções ou notas de um item | Modificar item já no carrinho |
| [`removeItemFromCart`](#removeitemfromcart) | Remover um item do carrinho | Remover item |
| [`removeVoucher`](#removevoucher) | Limpar o voucher aplicado | Remover cupom/desconto |
| [`listVouchers`](#listvouchers) | Listar vouchers aplicáveis ao carrinho | Descobrir antes de `setVoucher` |
| [`setVoucher`](#setvoucher) | Aplicar um voucher (`code` + `campaignId`) | Aplicar cupom escolhido |
| [`setCartDelivery`](#setcartdelivery) | Definir método de entrega e horário | Configurar entrega antes de `submitOrder` |
| [`setCartPayment`](#setcartpayment) | Definir forma de pagamento | Configurar pagamento antes de `submitOrder` |
| [`listPaymentMethods`](#listpaymentmethods) | Listar formas de pagamento aceitas | Descobrir antes de `setCartPayment` |
| [`submitOrder`](#submitorder) | Enviar o pedido e gerar `orderId` | Checkout após confirmação explícita |


## Índice rápido

- [createCart](#createcart) — Iniciar o fluxo
- [getCart](#getcart) — Consultar estado
- [getCartDeliveryMethods](#getcartdeliverymethods) — Descobrir entrega
- [addItemToCart](#additemtocart) — Adicionar item
- [updateCartItem](#updatecartitem) — Atualizar item
- [removeItemFromCart](#removeitemfromcart) — Remover item
- [removeVoucher](#removevoucher) — Limpar voucher
- [listVouchers](#listvouchers) — Descobrir vouchers
- [setVoucher](#setvoucher) — Aplicar voucher
- [setCartDelivery](#setcartdelivery) — Definir entrega
- [setCartPayment](#setcartpayment) — Definir pagamento
- [listPaymentMethods](#listpaymentmethods) — Listar pagamentos
- [submitOrder](#submitorder) — Checkout

## Convenções transversais

Todas as tools seguem estas convenções:

- **Chaves JSON**: `lowerCamelCase`
- **UUIDs v4**: `cartId`, `itemId`, `cartItemId`, `merchantId`, `addressId`, `paymentMethodId`, `campaignId`
- **HTTP Status**: o gateway normaliza para `200 OK`; `submitOrder` retorna `201 Created`
- **Erros**: chave `"error"` (singular) na raiz, com `code`, `message`, `details`, `impact`, `suggestedActions`, `userFriendlyMessage`
- **`agentHints`**: presente em sucesso e erro, orientando a próxima ação
- **Sem `operation` enum**: cada tool é atômica
- **Método HTTP**: `listPaymentMethods` usa GET (query param); as demais usam POST

## createCart

Cria um novo carrinho. Dois caminhos mutuamente exclusivos: **Caminho A** — do zero, com `merchantId` + `addressId` + `items[]` (todos obrigatórios). **Caminho B** — reordenação, com `orderId` sozinho (`merchantId`, `addressId`, `items` derivados automaticamente do pedido original). Pode também pré-configurar entrega e pagamento na criação.

**Quando usar:**

- Usuário selecionou um estabelecimento e ≥1 item (entrada no domínio Cart)
- Nova intenção de compra no estabelecimento
- Fluxo de reordenação: passe `orderId` para semear os itens (demais campos derivados automaticamente)
- Quer pré-configurar entrega/pagamento no momento da criação (otimização)

**Quando NÃO usar:**

- Sem `merchantId` válido quando não usa `orderId` (use `browseOffers` ou `searchOffers` antes)
- Sem `addressId` quando não usa `orderId` (use `listAddresses` ou `createAddress` antes)
- Com `items` vazio ou nulo quando não usa `orderId` (mínimo 1 para carrinhos do zero)
- Informando `merchantId`, `addressId` ou `items` junto com `orderId` (são ignorados)

**Efeitos colaterais:** Cria um recurso de carrinho no backend. **Não idempotente** — cada chamada cria um carrinho novo.

**Precondições:**

- Ou: `orderId` sozinho (reordenação) OU `merchantId` + `addressId` + mínimo 1 item (do zero)
- `merchantId` do Offer Discovery; `addressId` do User MCP; mínimo 1 item com `itemId`, `quantity` (≥ 1), `options` (array, vazio permitido)

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `merchantId` | string (UUID) | condicional | Estabelecimento (do Offer Discovery). Obrigatório apenas quando não usa `orderId`. |
| `addressId` | string (UUID) | condicional | Endereço de entrega (do User MCP). Obrigatório apenas quando não usa `orderId`. |
| `items` | array de AgentToolCartItem | condicional | Itens a adicionar. Mínimo 1 quando não usa `orderId`. |
| `items[].itemId` | string (UUID) | sim | Item do catálogo (do Offer Discovery). |
| `items[].quantity` | integer | sim | Quantidade (≥ 1). |
| `items[].options` | array de Option | sim | Opções selecionadas. Obrigatório mesmo se vazio (`[]`). |
| `items[].customerNote` | string | não | Instrução livre para o item (ex.: "sem cebola"). |
| `orderId` | string (UUID) | não | Para reordenação. Com ele, `merchantId`, `addressId` e `items` não são necessários. Sempre chame `getCart` depois para verificar os itens semeados a preços atuais. |
| `deliveryMethod` | AgentToolDeliveryMethod | não | Método de entrega a definir na criação. |
| `deliveryMethod.deliveryMethodId` | string | sim (se deliveryMethod presente) | Ex.: `DEFAULT`, `EXPRESS`. |
| `deliveryMethod.selectedTimeSlotId` | string (UUID) | não | Horário de `getCartDeliveryMethods`. |
| `paymentMethod` | AgentToolPaymentMethod | não | Forma de pagamento a definir na criação. |
| `paymentMethod.paymentMethodId` | string (UUID) | sim (se paymentMethod presente) | UUID exato de `listPaymentMethods`. **Não use o valor `kind` (ex.: `"PIX"`) como ID.** |
| `paymentMethod.cardTokenId` | string | não | Token do cartão para crédito/débito. |


### Exemplo de requisição

```
{
  "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
  "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  "items": [
    {
      "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
      "quantity": 1,
      "customerNote": "sem cebola",
      "options": [
        {
          "optionId": "b7e6d5c4-0001-4000-8000-000000000001",
          "quantity": 1,
          "customizations": [
            { "customizationId": "c1d2e3f4-0001-4000-8000-000000000101", "quantity": 1 }
          ]
        }
      ]
    }
  ],
  "deliveryMethod": { "deliveryMethodId": "DEFAULT" },
  "paymentMethod": { "paymentMethodId": "550e8400-e29b-41d4-a716-446655440000" }
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** — o estado completo do carrinho.

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "merchant": {
    "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
    "merchantName": "Pizza Express",
    "orderMinimumPrice": 15.00,
    "formattedAddress": "Rua Augusta, 1500 - Consolação, São Paulo"
  },
  "items": [
    {
      "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
      "cartItemId": "d4e5f6a7-0001-4000-c000-000000000001",
      "name": "Margherita Pizza",
      "quantity": 1,
      "unitPrice": 32.90,
      "customerNote": "sem cebola",
      "options": [
        {
          "optionId": "b7e6d5c4-0001-4000-8000-000000000001",
          "name": "Tamanho",
          "quantity": 1,
          "customerNote": null,
          "customizations": [
            {
              "customizationId": "c1d2e3f4-0001-4000-8000-000000000101",
              "name": "Queijo extra",
              "quantity": 1,
              "customerNote": null
            }
          ]
        }
      ]
    }
  ],
  "deliveryAddress": { "streetName": "Rua Augusta", "streetNumber": "1234", "neighborhood": "Consolação" },
  "deliveryMethod": null,
  "paymentMethod": null,
  "fees": [{ "name": "Taxa de serviço", "description": null, "amount": 0.00 }],
  "summary": {
    "totalName": "Total", "totalAmount": 32.90,
    "subtotalName": "Subtotal", "subtotalAmount": 32.90,
    "deliveryFeeName": "Taxa de entrega", "deliveryFeeAmount": 0.00,
    "feeTotalName": "Taxas", "feeTotalAmount": 0.00,
    "benefitsTotalName": "Benefícios", "benefitsTotalAmount": 0.00,
    "voucherTotalName": "Cupom", "voucherTotalAmount": 0.00
  },
  "warning": null,
  "appDeeplink": "ifoodapp://cart/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "agentHints": { "nextStep": "Carrinho criado. Revise itens, totais e status de entrega/pagamento. Configure entrega e pagamento antes de enviar o pedido." }
}
```

### Resposta (erro — estabelecimento fechado)

```
{
  "error": {
    "code": "MERCHANT_CLOSED",
    "message": "O estabelecimento 'ffffffff-eeee-dddd-cccc-bbbbaaaa0000' não está aceitando pedidos agora. Peça ao usuário para escolher outro estabelecimento.",
    "details": { "merchantId": "ffffffff-eeee-dddd-cccc-bbbbaaaa0000", "reason": "MERCHANT_CLOSED" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [
      { "tool": "searchOffers", "displayName": "Buscar restaurantes alternativos", "payload": { "query": "restaurantes próximos", "userLocation": "{localização atual}" } }
    ],
    "userFriendlyMessage": "Este restaurante não está aceitando pedidos no momento. Tente outro restaurante."
  },
  "agentHints": { "nextStep": "Apresente estabelecimentos alternativos da descoberta anterior ou busque novas opções." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/createCart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
    "addressId": "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
    "items": [
      {
        "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
        "quantity": 1,
        "customerNote": "sem cebola",
        "options": []
      }
    ]
  }'
```

**TypeScript:**

```
const cart = await cartClient.createCart({
  merchantId: "b8f3c1e2-a456-7890-1234-567890abcdef",
  addressId: "fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  items: [{ itemId: "f7e6d5c4-b3a2-9180-7654-321fedcba098", quantity: 1, options: [] }]
});
console.log("Carrinho criado:", cart.cartId);
```

**Python:**

```
cart = cart_client.create_cart(
  merchant_id="b8f3c1e2-a456-7890-1234-567890abcdef",
  address_id="fb7fbc80-9520-47fa-b7ac-83d6662c97f2",
  items=[{"itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098", "quantity": 1, "options": []}]
)
print(f"Carrinho criado: {cart['cartId']}")
```

## getCart

Retorna o estado completo de um carrinho: itens com `cartItemId`, resumo de preços, configuração de entrega/pagamento, endereço, avisos e deeplink. Chame antes de qualquer modificação do carrinho ou para apresentá-lo ao usuário.

**Quando usar:**

- Apresentar o carrinho ao usuário (revisão completa)
- Obter o `cartItemId` de um item recém-adicionado
- Validar estado antes de modificar (entrega/pagamento configurados?)
- Revisar totais e avisos antes do checkout
- Após `addItemToCart`, `updateCartItem`, `removeItemFromCart`

**Quando NÃO usar:**

- Para listar endereços (use `listAddresses`)
- Para descobrir métodos de entrega (use `getCartDeliveryMethods`)
- Para listar formas de pagamento (use `listPaymentMethods`)
- Para descobrir vouchers aplicáveis (use `listVouchers`)

**Efeitos colaterais:** Nenhum (somente leitura).

**Precondições:** `cartId` válido de `createCart` ou tools anteriores.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |


### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)**.

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "merchant": {
    "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef",
    "merchantName": "Pizza Express",
    "orderMinimumPrice": 15.00,
    "formattedAddress": "Rua Augusta, 1500 - Consolação, São Paulo"
  },
  "items": [
    {
      "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
      "cartItemId": "d4e5f6a7-0001-4000-c000-000000000001",
      "name": "Margherita Pizza",
      "quantity": 2,
      "unitPrice": 32.90,
      "customerNote": "sem cebola",
      "options": []
    },
    {
      "itemId": "a1b2c3d4-0001-4000-8000-000000005103",
      "cartItemId": "d4e5f6a7-0001-4000-c000-000000000002",
      "name": "Coca-Cola 350ml",
      "quantity": 1,
      "unitPrice": 6.50,
      "customerNote": null,
      "options": []
    }
  ],
  "deliveryAddress": { "streetName": "Rua Augusta", "streetNumber": "1234", "neighborhood": "Consolação" },
  "deliveryMethod": {
    "deliveryMethodMode": "DELIVERY",
    "deliveryMethodName": "Entrega Padrão",
    "fee": 5.90,
    "estimatedMinutes": { "min": 30, "max": 45 },
    "timeSlot": null
  },
  "paymentMethod": {
    "paymentMethodId": "550e8400-e29b-41d4-a716-446655440001",
    "kind": "CREDIT_CARD",
    "displayName": "Cartão de Crédito",
    "cardTokenId": "ct-abc123",
    "brand": "Visa",
    "issuerBank": "Nubank"
  },
  "fees": [{ "name": "Taxa de serviço", "description": null, "amount": 0.00 }],
  "summary": {
    "totalName": "Total", "totalAmount": 78.20,
    "subtotalName": "Subtotal", "subtotalAmount": 72.30,
    "deliveryFeeName": "Taxa de entrega", "deliveryFeeAmount": 5.90,
    "feeTotalName": "Taxas", "feeTotalAmount": 0.00,
    "benefitsTotalName": "Benefícios", "benefitsTotalAmount": 0.00,
    "voucherTotalName": "Cupom", "voucherTotalAmount": 0.00
  },
  "warning": null,
  "appDeeplink": "ifoodapp://cart/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "agentHints": {
    "nextStep": "O carrinho tem 2 itens totalizando R$78,20. Entrega e pagamento configurados. Revise com o usuário e envie quando confirmado.",
    "nextStepWhenUserAddsItem": "Adicione o item selecionado ao carrinho ativo.",
    "nextStepWhenUserRemovesItem": "Remova o item usando seu cartItemId."
  }
}
```

### Resposta (erro — carrinho não encontrado)

```
{
  "error": {
    "code": "CART_NOT_FOUND",
    "message": "O carrinho 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' não foi encontrado. Ele pode ter expirado ou sido excluído. Crie um novo carrinho.",
    "details": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "createCart", "displayName": "Criar novo carrinho", "payload": {} }],
    "userFriendlyMessage": "Carrinho não encontrado. Crie um novo carrinho."
  },
  "agentHints": { "nextStep": "Crie um novo carrinho com addressId, merchantId e itens do usuário." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/getCart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }'
```

**TypeScript:**

```
const cart = await cartClient.getCart({ cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" });
console.log(`Total: R$ ${cart.summary.totalAmount}`);
```

**Python:**

```
cart = cart_client.get_cart(cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
print(f"Total: R$ {cart['summary']['totalAmount']}")
```

## getCartDeliveryMethods

Lista as opções de entrega disponíveis para o carrinho (Padrão, Expressa, Turbo, Retirada, etc.) com taxas, tempos estimados e horários para entrega agendada. **Sempre chame ANTES de `setCartDelivery`** — nunca hardcode IDs de método de entrega.

**Quando usar:**

- Usuário quer ver opções de entrega
- Antes de configurar entrega (descoberta sempre antes da ação)
- Para entender tempos e taxas de cada opção
- Para apresentar horários (entrega agendada)
- Após `createCart` ou quando o usuário muda a preferência de entrega

**Quando NÃO usar:**

- Para configurar entrega (use `setCartDelivery`)
- Se o carrinho não tem itens ou endereço (erro: "Delivery Options Unavailable")
- Para listar opções de outro estabelecimento (acoplado ao `cartId`)

**Efeitos colaterais:** Nenhum (somente leitura).

**Precondições:** `cartId` válido; carrinho com ≥1 item; carrinho com `deliveryAddress`.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho (deve ter endereço definido). |


### Resposta (sucesso)

Retorna **[CartDeliveryOptionsResponse](#cartdeliveryoptionsresponse)**.

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "deliveryMethods": [
    {
      "deliveryMethodId": "DEFAULT",
      "deliveryMethodMode": "DELIVERY",
      "deliveryMethodName": "Entrega Padrão",
      "fee": 5.90,
      "estimatedMinutes": { "min": 30, "max": 45 },
      "timeslots": null
    },
    {
      "deliveryMethodId": "EXPRESS",
      "deliveryMethodMode": "DELIVERY",
      "deliveryMethodName": "Entrega Expressa",
      "fee": 12.90,
      "estimatedMinutes": { "min": 15, "max": 25 },
      "timeslots": null
    },
    {
      "deliveryMethodId": "SCHEDULED",
      "deliveryMethodMode": "DELIVERY",
      "deliveryMethodName": "Entrega Agendada",
      "fee": 5.90,
      "estimatedMinutes": { "min": 120, "max": 180 },
      "timeslots": [
        { "from": "2026-06-25T18:00:00Z", "to": "2026-06-25T18:30:00Z" },
        { "from": "2026-06-25T19:00:00Z", "to": "2026-06-25T19:30:00Z" }
      ]
    },
    {
      "deliveryMethodId": "TAKEOUT",
      "deliveryMethodMode": "TAKEOUT",
      "deliveryMethodName": "Retirada no local",
      "fee": 0.00,
      "estimatedMinutes": { "min": 15, "max": 25 },
      "timeslots": null
    }
  ],
  "warning": null,
  "agentHints": {
    "nextStep": "Apresente estas opções ao usuário. Uma vez escolhida, configure a entrega com o deliveryMethodId selecionado.",
    "noResultsGuidance": "Um array deliveryMethods vazio geralmente significa que não há opções para este estabelecimento/endereço. Não invente métodos. Sugira outro endereço ou estabelecimento."
  }
}
```

### Resposta (erro)

```
{
  "error": {
    "code": "DELIVERY_OPTIONS_UNAVAILABLE",
    "message": "Não foi possível obter opções de entrega. O carrinho pode não ter endereço definido ou o estabelecimento pode não entregar nesta localização.",
    "details": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "listAddresses", "displayName": "Verificar endereços", "payload": {} }],
    "userFriendlyMessage": "Não foi possível obter as opções de entrega para este carrinho."
  },
  "agentHints": { "nextStep": "Verifique se o carrinho tem um endereço de entrega válido." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/getCartDeliveryMethods" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }'
```

**TypeScript:**

```
const options = await cartClient.getCartDeliveryMethods({ cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" });
options.deliveryMethods.forEach(m => console.log(`- ${m.deliveryMethodName}: R$ ${m.fee}`));
```

**Python:**

```
options = cart_client.get_cart_delivery_methods(cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
for m in options['deliveryMethods']:
  print(f"- {m['deliveryMethodName']}: R$ {m['fee']}")
```

## addItemToCart

Adiciona um item do catálogo com opções e customizações selecionadas ao carrinho. O array `options` é OBRIGATÓRIO mesmo se vazio (`[]`). Após chamar, salve o `cartItemId` retornado para atualizações futuras.

**Quando usar:**

- Usuário quer adicionar um novo item
- Após busca em `getMerchant` ou `searchOffers`
- Com `itemId` de catálogo e `options` selecionadas
- Para aumentar quantidade (alternativa: `updateCartItem` se já existe)

**Quando NÃO usar:**

- Para modificar item já no carrinho (use `updateCartItem` com `cartItemId`)
- Sem `itemId` válido do estabelecimento (use `getMerchant` antes)
- Sem o array `options` (obrigatório, mesmo vazio)
- Se o item não pertence ao estabelecimento do carrinho (erro: "Item Not Available")

**Efeitos colaterais:** Adiciona item ao carrinho, recalcula preços; servidor atribui `cartItemId`.

**Precondições:** `cartId` válido; `itemId` do catálogo do estabelecimento (NÃO `cartItemId`); `options` obrigatório; `quantity` ≥ 1.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `itemId` | string (UUID) | sim | Item do catálogo (do Offer Discovery). **É o `itemId`, não `cartItemId`.** |
| `quantity` | integer | sim | Quantidade (≥ 1). |
| `options` | array de Option | sim | Opções selecionadas. Vazio (`[]`) se o item não tem opções. |
| `customerNote` | string | não | Instruções especiais (ex.: "sem cebola"). |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "itemId": "a1b2c3d4-0001-4000-8000-000000005103",
  "quantity": 1,
  "customerNote": "gelada",
  "options": []
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** — o estado atualizado do carrinho. O array `items[]` contém o novo `cartItemId`; **salve-o**.

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/addItemToCart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "itemId": "a1b2c3d4-0001-4000-8000-000000005103",
    "quantity": 1,
    "customerNote": "gelada",
    "options": []
  }'
```

**TypeScript:**

```
const result = await cartClient.addItemToCart({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  itemId: "a1b2c3d4-0001-4000-8000-000000005103",
  quantity: 1,
  customerNote: "gelada",
  options: [] // Obrigatório!
});
const cartItemId = result.items[result.items.length - 1].cartItemId;
console.log(`Item adicionado. cartItemId: ${cartItemId}`);
```

**Python:**

```
result = cart_client.add_item_to_cart(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  item_id="a1b2c3d4-0001-4000-8000-000000005103",
  quantity=1, customer_note="gelada", options=[]
)
cart_item_id = result['items'][-1]['cartItemId']
print(f"Item adicionado. cartItemId: {cart_item_id}")
```

## updateCartItem

Atualiza quantidade, opções ou notas de um item já no carrinho. Envie o estado novo COMPLETO (quantidade, opções e notas) — não apenas os campos alterados. TANTO `cartItemId` QUANTO `itemId` são obrigatórios.

**Quando usar:**

- Mudar quantidade de item existente
- Mudar opções (tamanho, sabor, etc.)
- Adicionar/remover customizações
- Atualizar a nota do item

**Quando NÃO usar:**

- Sem `cartItemId` (use `getCart` para obter)
- Se o item não está no carrinho (use `addItemToCart`)
- Confundindo `cartItemId` com `itemId` (ambos obrigatórios, diferentes!)

**Efeitos colaterais:** Modifica o item; preços recalculados.

**Precondições:** `cartId` válido; `cartItemId` do item no carrinho; `itemId` do catálogo; `quantity` ≥ 1.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `cartItemId` | string (UUID) | sim | Identificador do item NO carrinho. **Não é o `itemId` do Offer Discovery.** |
| `itemId` | string (UUID) | sim | Item do catálogo, para validação cruzada. |
| `quantity` | integer | sim | Nova quantidade. |
| `options` | array de Option | sim | Opções atualizadas. Obrigatório mesmo se vazio (`[]`). |
| `customerNote` | string | não | Instrução livre. Omita para manter a nota existente. |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "cartItemId": "d4e5f6a7-0001-4000-c000-000000000001",
  "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
  "quantity": 3,
  "customerNote": "sem cebola, borda recheada",
  "options": [
    {
      "optionId": "b7e6d5c4-0001-4000-8000-000000000002",
      "quantity": 1,
      "customizations": [
        { "customizationId": "c1d2e3f4-0001-4000-8000-000000000102", "quantity": 1 }
      ]
    }
  ]
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)**.

### Resposta (erro — `cartItemId` não encontrado)

```
{
  "error": {
    "code": "CART_ITEM_NOT_FOUND",
    "message": "O cartItemId 'd4e5f6a7-0001-4000-c000-000000000999' não foi encontrado neste carrinho. Você pode estar usando um itemId do Offer Discovery em vez de um cartItemId. Revise o carrinho para ver os cartItemId válidos.",
    "details": {
      "cartItemId": "d4e5f6a7-0001-4000-c000-000000000999",
      "availableCartItemIds": ["d4e5f6a7-0001-4000-c000-000000000001", "d4e5f6a7-0001-4000-c000-000000000002"]
    },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "getCart", "displayName": "Revisar estado do carrinho", "payload": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" } }],
    "userFriendlyMessage": "Item não encontrado no carrinho."
  },
  "agentHints": { "nextStep": "Revise o estado atual do carrinho para obter o cartItemId correto." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/updateCartItem" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "cartItemId": "d4e5f6a7-0001-4000-c000-000000000001",
    "itemId": "f7e6d5c4-b3a2-9180-7654-321fedcba098",
    "quantity": 3,
    "customerNote": "sem cebola, borda recheada",
    "options": []
  }'
```

**TypeScript:**

```
await cartClient.updateCartItem({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  cartItemId: "d4e5f6a7-0001-4000-c000-000000000001", // do addItemToCart
  itemId: "f7e6d5c4-b3a2-9180-7654-321fedcba098",     // do catálogo
  quantity: 3,
  options: []
});
```

**Python:**

```
cart_client.update_cart_item(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  cart_item_id="d4e5f6a7-0001-4000-c000-000000000001",
  item_id="f7e6d5c4-b3a2-9180-7654-321fedcba098",
  quantity=3, customer_note="sem cebola, borda recheada", options=[]
)
```

## removeItemFromCart

Remove um item específico do carrinho. O `cartItemId` deve corresponder a um item da resposta de `getCart` — é o ID escopado ao carrinho, NÃO o `itemId` de catálogo.

**Quando usar:**

- Usuário pede para remover um item
- Item adicionado por engano
- Após `getCart` obter o `cartItemId`

**Quando NÃO usar:**

- Sem `cartItemId` válido (use `getCart`)
- Confundindo `cartItemId` com `itemId`
- Para zerar quantidade (remoção é sempre completa)

**Efeitos colaterais:** Remove o item e recalcula preços. Se era o último item, o carrinho é excluído automaticamente.

**Precondições:** `cartId` válido; `cartItemId` de `getCart`/`addItemToCart`/`createCart`.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `cartItemId` | string (UUID) | sim | Identificador do item NO carrinho. |


### Resposta (sucesso — itens permanecem)

Retorna **[CartDetailsResponse](#cartdetailsresponse)**.

### Resposta (sucesso — último item removido)

Quando o item removido era o **último** do carrinho, o servidor exclui o carrinho por completo e a resposta pode conter apenas `agentHints.cartDeletedAfterLastItemRemoved`:

```
{
  "agentHints": {
    "cartDeletedAfterLastItemRemoved": "O último item foi removido e o carrinho foi excluído automaticamente. Não há carrinho para modificar — crie um novo se o usuário quiser pedir de novo."
  }
}
```

Não tente novas mutações contra um carrinho excluído — chame `createCart` para recomeçar.

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/removeItemFromCart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "cartItemId": "d4e5f6a7-0001-4000-c000-000000000001" }'
```

**TypeScript:**

```
await cartClient.removeItemFromCart({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  cartItemId: "d4e5f6a7-0001-4000-c000-000000000001"
});
```

**Python:**

```
cart_client.remove_item_from_cart(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  cart_item_id="d4e5f6a7-0001-4000-c000-000000000001"
)
```

## removeVoucher

Remove o voucher/cupom aplicado atualmente ao carrinho. Se nenhum voucher estiver aplicado, retorna sucesso silencioso (no-op).

**Quando usar:**

- Usuário pede explicitamente para remover cupom
- Usuário quer ver o preço sem desconto
- Após aplicar um voucher, mudou de ideia

**Quando NÃO usar:**

- Para aplicar um novo voucher (use `setVoucher`)
- Para listar vouchers disponíveis (use `listVouchers`)

**Efeitos colaterais:** Limpa o voucher; recalcula preços para cima.

**Precondições:** `cartId` válido.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |


### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** com o voucher limpo e `summary.voucherTotalAmount` igual a `0.00`.

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/removeVoucher" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }'
```

**TypeScript:**

```
await cartClient.removeVoucher({ cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" });
```

**Python:**

```
cart_client.remove_voucher(cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
```

## listVouchers

Lista os vouchers/cupons disponíveis e aplicáveis ao carrinho atual. Cada entrada expõe o `code` e o `campaignId` exigidos por `setVoucher`, além de uma descrição legível e o efeito do desconto.

**Quando usar:**

- Antes de configurar um voucher (descoberta sempre antes de `setVoucher`)
- Usuário pergunta quais cupons se aplicam a este pedido
- Para apresentar opções com o efeito do desconto (FIXED ou PERCENTAGE)
- Após `createCart`, `addItemToCart`, ou quando o usuário pergunta sobre descontos

**Quando NÃO usar:**

- Para aplicar um voucher (use `setVoucher`)
- Para remover um voucher (use `removeVoucher`)
- Para listar a carteira global de vouchers não usados do usuário (fora de escopo — retorna apenas o que é aplicável ao carrinho)

**Efeitos colaterais:** Nenhum (somente leitura).

**Precondições:** `cartId` válido.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |


### Resposta (sucesso)

Retorna **[VoucherListPayload](#voucherlistpayload)**.

```
{
  "vouchers": [
    {
      "code": "VCH-10",
      "campaignId": "b8f3c1e2-0001-4000-8000-00000000abcd",
      "effectType": "FIXED",
      "effectValue": 10.0,
      "maxDiscountValue": null,
      "description": "R$10 de desconto em pedidos acima de R$50",
      "available": true
    },
    {
      "code": "PROMO20",
      "campaignId": "b8f3c1e2-0001-4000-8000-00000000ef01",
      "effectType": "PERCENTAGE",
      "effectValue": 20.0,
      "maxDiscountValue": 15.0,
      "description": "20% de desconto, limitado a R$15",
      "available": true
    }
  ],
  "agentHints": {
    "nextStep": "Apresente estes vouchers ao usuário. Cada voucher tem code e campaignId — salve ambos. Uma vez escolhido, aplique com setVoucher usando o code e campaignId exatos.",
    "noResultsGuidance": "Um array vouchers vazio significa que nenhum voucher se aplica a este carrinho. Não invente vouchers. Diga ao usuário que nenhum cupom se aplica."
  }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/listVouchers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }'
```

**TypeScript:**

```
const result = await cartClient.listVouchers({ cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" });
result.vouchers.forEach(v => console.log(`- ${v.code}: ${v.description}`));
```

**Python:**

```
result = cart_client.list_vouchers(cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
for v in result['vouchers']:
  print(f"- {v['code']}: {v['description']}")
```

## setVoucher

Aplica um voucher ou cupom ao carrinho. Chame após o usuário escolher entre os vouchers retornados por `listVouchers`. Use o par exato `code` + `campaignId` dessa resposta — nunca invente nem reutilize códigos.

**Quando usar:**

- Após apresentar as opções de `listVouchers` ao usuário
- Usuário escolheu um voucher específico
- Para aplicar um desconto antes de revisar totais e enviar

**Quando NÃO usar:**

- Sem chamar `listVouchers` antes
- Com `code`/`campaignId` não retornado por `listVouchers` (erro: "Invalid Voucher")
- Para remover um voucher (use `removeVoucher`)
- Para navegar pelos vouchers disponíveis (use `listVouchers`)

**Efeitos colaterais:** Aplica o voucher; recalcula `summary.voucherTotalAmount` e `summary.totalAmount` para baixo.

**Precondições:** `cartId` válido; par `code` + `campaignId` válido (de `listVouchers`).

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `code` | string | sim | Código do voucher, como retornado por `listVouchers`. |
| `campaignId` | string (UUID) | sim | ID da campanha do voucher, como retornado por `listVouchers`. |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "code": "VCH-10",
  "campaignId": "b8f3c1e2-0001-4000-8000-00000000abcd"
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** com o voucher aplicado (`summary.voucherTotalAmount` > 0 e `summary.totalAmount` reduzido).

### Resposta (erro — voucher inválido)

```
{
  "error": {
    "code": "VOUCHER_INVALID",
    "message": "O voucher 'VCH-XXX' não pôde ser aplicado a este carrinho. O código pode ser inválido, expirado ou não aplicável aos itens. Peça ao usuário para escolher um voucher da resposta de listVouchers.",
    "details": { "code": "VCH-XXX", "campaignId": "b8f3c1e2-0001-4000-8000-00000000ffff" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "listVouchers", "displayName": "Ver vouchers disponíveis", "payload": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" } }],
    "userFriendlyMessage": "Este cupom não pode ser aplicado a este carrinho."
  },
  "agentHints": { "nextStep": "Obtenha os vouchers aplicáveis atuais, apresente ao usuário e tente de novo com code e campaignId válidos." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/setVoucher" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "code": "VCH-10",
    "campaignId": "b8f3c1e2-0001-4000-8000-00000000abcd"
  }'
```

**TypeScript:**

```
await cartClient.setVoucher({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  code: "VCH-10",
  campaignId: "b8f3c1e2-0001-4000-8000-00000000abcd"
});
```

**Python:**

```
cart_client.set_voucher(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  code="VCH-10",
  campaign_id="b8f3c1e2-0001-4000-8000-00000000abcd"
)
```

## setCartDelivery

Seleciona um método de entrega e, opcionalmente, um horário para o carrinho. Chame após o usuário escolher entre as opções de `getCartDeliveryMethods`. Inclua `selectedTimeSlotId` para entrega agendada, ou omita para entrega imediata.

**Quando usar:**

- Após apresentar as opções de `getCartDeliveryMethods` ao usuário
- Usuário escolheu um método de entrega
- Para entrega agendada: com `selectedTimeSlotId` da resposta anterior
- Antes de finalizar o pedido (entrega é obrigatória em `submitOrder`)

**Quando NÃO usar:**

- Sem chamar `getCartDeliveryMethods` antes
- Com `deliveryMethodId` não retornado por `getCartDeliveryMethods` (erro: "Delivery Method Unavailable")
- Sem `selectedTimeSlotId` para entrega agendada (obrigatório quando `timeslots` não é nulo)
- Se o carrinho não tem itens ou endereço

**Efeitos colaterais:** Atualiza `deliveryMethod`; recalcula `summary.deliveryFeeAmount` e `summary.totalAmount`.

**Precondições:** `cartId` válido; `deliveryMethodId` válido; `selectedTimeSlotId` se entrega agendada; carrinho com ≥1 item e endereço.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `deliveryMethodId` | string | sim | ID do método escolhido (ex.: `"DEFAULT"`, `"EXPRESS"`). Use o ID exato de `getCartDeliveryMethods`. |
| `selectedTimeSlotId` | string (UUID) | não | ID do horário, se o método suporta agendamento. |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "deliveryMethodId": "EXPRESS"
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** com `deliveryMethod` atualizado.

### Resposta (erro)

```
{
  "error": {
    "code": "DELIVERY_METHOD_UNAVAILABLE",
    "message": "O método 'EXPRESS' não está disponível para este carrinho. Métodos disponíveis: DEFAULT, ECONOMIC. Apresente essas opções e tente de novo com um deliveryMethodId válido.",
    "details": { "requestedMethodId": "EXPRESS", "availableMethodIds": ["DEFAULT", "ECONOMIC"] },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "getCartDeliveryMethods", "displayName": "Ver métodos disponíveis", "payload": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" } }],
    "userFriendlyMessage": "Esta modalidade de entrega não está disponível. Escolha entre as opções disponíveis."
  },
  "agentHints": { "nextStep": "Obtenha as opções de entrega atuais, apresente ao usuário e tente de novo com um deliveryMethodId válido." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/setCartDelivery" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{ "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "deliveryMethodId": "EXPRESS" }'
```

**TypeScript:**

```
await cartClient.setCartDelivery({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  deliveryMethodId: "EXPRESS"
});
```

**Python:**

```
cart_client.set_cart_delivery(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  delivery_method_id="EXPRESS"
)
```

## setCartPayment

Seleciona uma forma de pagamento para o carrinho. Chame após o usuário escolher uma opção de `listPaymentMethods`. Use o ID exato dessa resposta. Inclua `cardTokenId` apenas ao pagar com cartão de crédito/débito salvo — omita para PIX ou outros métodos não-cartão.

**Quando usar:**

- Após apresentar as opções de `listPaymentMethods` ao usuário
- Usuário escolheu uma forma de pagamento
- Para cartões (CREDIT_CARD, DEBIT_CARD): com `cardTokenId` tokenizado
- Antes de finalizar (pagamento é obrigatório em `submitOrder`)

**Quando NÃO usar:**

- Sem chamar `listPaymentMethods` antes
- Com `paymentMethodId` não retornado por `listPaymentMethods` (erro: "Payment Method Unavailable")
- Sem `cardTokenId` para CREDIT_CARD/DEBIT_CARD (erro: "Card Token Required")

**Efeitos colaterais:** Atualiza `paymentMethod`. Sem recálculo de preço.

**Precondições:** `cartId` válido; `paymentMethodId` válido; `cardTokenId` se o `kind` for CREDIT_CARD/DEBIT_CARD.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `paymentMethodId` | string (UUID) | sim | UUID exato de `listPaymentMethods`. **Não use o valor `kind` (ex.: `"PIX"`) como ID.** |
| `cardTokenId` | string | não | Obrigatório quando o método é cartão (CREDIT_CARD/DEBIT_CARD). Copie de `listPaymentMethods`. Omita para PIX. |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "paymentMethodId": "550e8400-e29b-41d4-a716-446655440001",
  "cardTokenId": "660e8400-e29b-41d4-a716-446655440002"
}
```

### Resposta (sucesso)

Retorna **[CartDetailsResponse](#cartdetailsresponse)** com `paymentMethod` atualizado.

### Resposta (erro — método não aceito)

```
{
  "error": {
    "code": "PAYMENT_METHOD_UNAVAILABLE",
    "message": "A forma de pagamento '75354fd8-e916-41db-9286-93be2232efe2' não é aceita por este estabelecimento. Verifique a lista atual e apresente as opções ao usuário.",
    "details": {
      "requestedMethodId": "75354fd8-e916-41db-9286-93be2232efe2",
      "availableMethodIds": ["550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002", "550e8400-e29b-41d4-a716-446655440004"]
    },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "listPaymentMethods", "displayName": "Ver formas de pagamento", "payload": { "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef" } }],
    "userFriendlyMessage": "Esta forma de pagamento não é aceita por este restaurante. Escolha outra opção."
  },
  "agentHints": { "nextStep": "Obtenha as formas de pagamento atuais, apresente ao usuário e tente de novo com um paymentMethodId válido." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/setCartPayment" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "paymentMethodId": "550e8400-e29b-41d4-a716-446655440001",
    "cardTokenId": "660e8400-e29b-41d4-a716-446655440002"
  }'
```

**TypeScript:**

```
await cartClient.setCartPayment({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  paymentMethodId: "550e8400-e29b-41d4-a716-446655440001",
  cardTokenId: "660e8400-e29b-41d4-a716-446655440002" // se for cartão
});
```

**Python:**

```
cart_client.set_cart_payment(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  payment_method_id="550e8400-e29b-41d4-a716-446655440001",
  card_token_id="660e8400-e29b-41d4-a716-446655440002"
)
```

## listPaymentMethods

Recupera todas as formas de pagamento disponíveis (PIX, cartão de crédito, cartão de débito, etc.) e tokens de cartão salvos de um estabelecimento. Use o `merchantId` dos detalhes do carrinho. **Sempre chame ANTES de `setCartPayment`** — nunca hardcode IDs de forma de pagamento.

**Quando usar:**

- Antes de configurar o pagamento (descoberta de opções)
- Usuário pergunta quais formas de pagamento o restaurante aceita
- Para validar se uma forma é suportada antes de `setCartPayment`

**Quando NÃO usar:**

- Para configurar o pagamento (use `setCartPayment`)
- Sem `merchantId` válido (use `browseOffers`, `searchOffers` ou `getMerchant` antes)
- Para listar as formas de pagamento globais do usuário (fora de escopo do Cart)

**Efeitos colaterais:** Nenhum (somente leitura).

**Precondições:** `merchantId` válido do Offer Discovery.

### Parâmetros (query parameter)

`listPaymentMethods` é um endpoint **GET** — `merchantId` vai como query parameter, não no corpo:

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `merchantId` | string (UUID) | sim | Estabelecimento do Offer Discovery. |


```
GET /ai-agents/v1/list-payment-methods?merchantId=b8f3c1e2-a456-7890-1234-567890abcdef
```

### Resposta (sucesso)

Retorna **[PaymentListPayload](#paymentlistpayload)**.

```
{
  "paymentMethods": [
    { "paymentMethodId": "550e8400-e29b-41d4-a716-446655440001", "kind": "CREDIT_CARD", "displayName": "Cartão de Crédito", "cardTokenId": null, "brand": null, "issuerBank": null },
    { "paymentMethodId": "550e8400-e29b-41d4-a716-446655440002", "kind": "DEBIT_CARD", "displayName": "Cartão de Débito", "cardTokenId": null, "brand": null, "issuerBank": null },
    { "paymentMethodId": "75354fd8-e916-41db-9286-93be2232efe2", "kind": "PIX", "displayName": "PIX", "cardTokenId": null, "brand": null, "issuerBank": null },
    { "paymentMethodId": "550e8400-e29b-41d4-a716-446655440004", "kind": "MEAL_VOUCHER", "displayName": "Vale Refeição", "cardTokenId": null, "brand": null, "issuerBank": null }
  ],
  "agentHints": {
    "nextStep": "Apresente estas formas de pagamento ao usuário. Para CREDIT_CARD e DEBIT_CARD, um cardTokenId será necessário ao configurar o pagamento.",
    "noResultsGuidance": "Um array paymentMethods vazio significa que o estabelecimento não tem formas de pagamento ativas. Não invente formas. Sugira outro estabelecimento."
  }
}
```

### Resposta (erro — estabelecimento não encontrado)

```
{
  "error": {
    "code": "MERCHANT_NOT_FOUND",
    "message": "O estabelecimento 'ffffffff-eeee-dddd-cccc-bbbbaaaa0000' não foi encontrado. Verifique se o merchantId veio de uma resposta do Offer Discovery.",
    "details": { "merchantId": "ffffffff-eeee-dddd-cccc-bbbbaaaa0000" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "searchOffers", "displayName": "Buscar estabelecimentos", "payload": { "query": "{última busca do usuário}" } }],
    "userFriendlyMessage": "Restaurante não encontrado."
  },
  "agentHints": { "nextStep": "Busque estabelecimentos para obter um merchantId válido e tente de novo." }
}
```

### Exemplos

**cURL:**

```
curl -X GET "https://cart.api.ifood.com/v1/list-payment-methods?merchantId=b8f3c1e2-a456-7890-1234-567890abcdef" \
  -H "Authorization: Bearer seu_token_aqui"
```

**TypeScript:**

```
const methods = await cartClient.listPaymentMethods({ merchantId: "b8f3c1e2-a456-7890-1234-567890abcdef" });
console.log(`${methods.paymentMethods.length} métodos disponíveis`);
```

**Python:**

```
methods = cart_client.list_payment_methods(merchant_id="b8f3c1e2-a456-7890-1234-567890abcdef")
print(f"{len(methods['paymentMethods'])} métodos disponíveis")
```

## submitOrder

Envia o pedido do carrinho. Chame `getCart` primeiro para mostrar o carrinho ao usuário e peça confirmação explícita. Só chame esta tool após a confirmação. Defina `userConsent` como `true` apenas quando o usuário concordar explicitamente. Se o usuário fornecer um documento de identificação, passe no campo `document`. Documentos aceitos: CPF (pessoa física), CNPJ (empresa) ou Passaporte (contas estrangeiras).

**Quando usar (APENAS com todos estes critérios):**

- Carrinho com ≥1 item (verifique com `getCart`)
- Método de entrega configurado (não-nulo em `getCart`)
- Forma de pagamento configurada (não-nula em `getCart`)
- Usuário confirmou explicitamente que quer finalizar

**Quando NÃO usar:**

- Sem ≥1 item (erro: "Cart Not Ready")
- Sem entrega configurada (erro: "Missing: deliveryMethod")
- Sem pagamento configurado (erro: "Missing: paymentMethod")
- SEM consentimento explícito (`userConsent: false` ou omitido)

**Efeitos colaterais:** Cria um pedido persistente. Fecha o carrinho. Pode iniciar a transação de pagamento. **Este é o ponto sem retorno.**

**Precondições:** `cartId` válido; ≥1 item; `deliveryMethod` e `paymentMethod` não-nulos; consentimento explícito do usuário.

### Parâmetros

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | ID do carrinho. |
| `userConsent` | boolean | sim | `true` apenas após o usuário confirmar explicitamente. |
| `document` | string | não | Documento de identificação: CPF, CNPJ ou Passaporte. Omita se o usuário não fornecer. |


### Exemplo de requisição

```
{
  "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "userConsent": true,
  "document": "123.456.789-00"
}
```

### Resposta (sucesso)

Retorna **[CheckoutSuccessBody](#checkoutsuccessbody)** com HTTP `201 Created`.

```
{
  "orderId": "7f3a2b1c-9d4e-5f6a-8b7c-0d1e2f3a4b5c",
  "agentHints": { "nextStep": "Pedido enviado com sucesso! Comece a rastrear o status do pedido em tempo real com trackOrder." }
}
```

### Resposta (erro — carrinho não pronto)

```
{
  "error": {
    "code": "CART_NOT_READY",
    "message": "O carrinho não está pronto para checkout. Faltando: forma de pagamento. O carrinho deve ter itens, entrega e pagamento configurados antes do checkout.",
    "details": { "missingRequirements": ["paymentMethod"], "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" },
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "listPaymentMethods", "displayName": "Ver formas de pagamento", "payload": { "merchantId": "b8f3c1e2-a456-7890-1234-567890abcdef" } }],
    "userFriendlyMessage": "Seu carrinho não está pronto. Configure a forma de pagamento antes de finalizar."
  },
  "agentHints": { "nextStepBeforeCheckout": "Verifique: (1) ≥1 item, (2) entrega definida, (3) pagamento definido, (4) apresente o resumo e obtenha confirmação. Só então envie de novo." }
}
```

### Resposta (erro — consentimento ausente)

```
{
  "error": {
    "code": "CONSENT_REQUIRED",
    "message": "O usuário não deu consentimento para enviar este pedido. O campo userConsent deve ser explicitamente true após a confirmação.",
    "details": {},
    "impact": { "canProceedToCheckout": false },
    "suggestedActions": [{ "tool": "getCart", "displayName": "Mostrar resumo ao usuário", "payload": { "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" } }],
    "userFriendlyMessage": "Você precisa confirmar que deseja finalizar o pedido."
  },
  "agentHints": { "nextStepBeforeCheckout": "Apresente o resumo completo e peça confirmação explícita antes de definir userConsent como true." }
}
```

### Exemplos

**cURL:**

```
curl -X POST "https://cart.api.ifood.com/v1/submitOrder" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '{
    "cartId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "userConsent": true,
    "document": "123.456.789-00"
  }'
```

**TypeScript:**

```
const order = await cartClient.submitOrder({
  cartId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  userConsent: true, // Obrigatório!
  document: "123.456.789-00"
});
console.log(`Pedido confirmado: ${order.orderId}`);
```

**Python:**

```
order = cart_client.submit_order(
  cart_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  user_consent=True,
  document="123.456.789-00"
)
print(f"Pedido confirmado: {order['orderId']}")
```

## Shared Schema Reference

Estas estruturas aparecem em múltiplas respostas. Definição completa de cada uma.

### CartDetailsResponse

Retornado por: `createCart`, `getCart`, `addItemToCart`, `updateCartItem`, `removeItemFromCart`, `removeVoucher`, `setVoucher`, `setCartDelivery`, `setCartPayment`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | Identificador do carrinho. |
| `merchant` | object | sim | `merchantId`, `merchantName` (string | null), `orderMinimumPrice` (number | null), `formattedAddress` (string | null). |
| `items` | array de Item | sim | Itens no carrinho. |
| `deliveryAddress` | DeliveryAddress | null | não | Resumo do endereço de entrega. |
| `deliveryMethod` | DeliveryMethod | null | não | Entrega configurada (`null` se ainda não definida). |
| `paymentMethod` | PaymentMethod | null | não | Pagamento configurado (`null` se ainda não definido). |
| `fees` | array de Fee | sim | Taxas por linha (embalagem, serviço, etc.). |
| `summary` | Summary | sim | Detalhamento de preços em BRL. |
| `warning` | AgentDetail | null | não | Aviso ou recomendação ao agente. |
| `appDeeplink` | string | null | não | Deeplink para abrir o carrinho no app iFood. |
| `agentHints` | object | null | não | Orientação para o próximo passo. |


### Item

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `itemId` | string (UUID) | sim | Item do catálogo (Offer Discovery). |
| `cartItemId` | string (UUID) | null | não | ID escopado ao carrinho. `null` quando ainda não persistido. |
| `name` | string | sim | Nome legível (ex.: "Margherita Pizza"). |
| `quantity` | integer | sim | Quantidade atual. |
| `unitPrice` | number | sim | Preço unitário (BRL). |
| `customerNote` | string | null | não | Nota livre do item. |
| `options` | array de Option | sim | Opções e customizações. Presente mesmo se vazio (`[]`). |


### Option

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `optionId` | string (UUID) | sim | Opção do `getItem` (Offer Discovery). |
| `name` | string | null | não | Nome legível (ex.: "Tamanho", "Massa"). |
| `quantity` | integer | sim | Quantidade desta escolha. |
| `customerNote` | string | null | não | Nota livre desta opção. |
| `customizations` | array de Customization | sim | Customizações aninhadas. Presente mesmo se vazio (`[]`). |


### Customization

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `customizationId` | string (UUID) | sim | Customização do `getItem` (Offer Discovery). |
| `name` | string | null | não | Nome legível (ex.: "Queijo extra", "Sem cebola"). |
| `quantity` | integer | sim | Quantidade desta escolha. |
| `customerNote` | string | null | não | Nota livre desta customização. |


### DeliveryAddress

Resumo do endereço de entrega. Todos os campos são anuláveis.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `streetName` | string | null | não | Rua (ex.: "Rua Augusta"). |
| `streetNumber` | string | null | não | Número (ex.: "1234"). |
| `neighborhood` | string | null | não | Bairro (ex.: "Consolação"). |


### DeliveryMethod

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `deliveryMethodMode` | string | sim | `DELIVERY`, `TAKEOUT` ou `PICKUP`. |
| `deliveryMethodName` | string | sim | Nome legível (ex.: "Entrega Padrão"). |
| `fee` | number | sim | Taxa de entrega (BRL). `0.00` para entrega grátis. |
| `estimatedMinutes` | object | sim | `{ "min": integer, "max": integer }`. |
| `timeSlot` | Timeslot | null | sim | Horário selecionado (pode ser `null`). |


### PaymentMethod

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `paymentMethodId` | string | sim | Identificador da forma de pagamento. |
| `kind` | string | sim | `CREDIT_CARD`, `DEBIT_CARD`, `PIX`, `MEAL_VOUCHER`, `FOOD_VOUCHER`. |
| `displayName` | string | sim | Nome em português (ex.: "Cartão de Crédito"). |
| `cardTokenId` | string | null | não | Token do cartão. Sempre `null` em `listPaymentMethods`; preenchido após `setCartPayment`. |
| `brand` | string | null | não | Bandeira (ex.: "Visa"). |
| `issuerBank` | string | null | não | Banco emissor (ex.: "Nubank"). |


### Fee

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `name` | string | sim | Rótulo da taxa (ex.: "Taxa de serviço"). |
| `description` | string | null | não | Descrição opcional. |
| `amount` | number | sim | Valor (BRL). |


### AgentToolCartItem

Schema somente de entrada em `createCart.items[]`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `itemId` | string (UUID) | sim | Item do catálogo. |
| `quantity` | integer | sim | Quantidade (≥ 1). |
| `options` | array de Option | sim | Obrigatório mesmo se vazio (`[]`). |
| `customerNote` | string | null | não | Instrução livre. |


### AgentToolDeliveryMethod

Schema somente de entrada em `createCart.deliveryMethod`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `deliveryMethodId` | string | sim (se presente) | Ex.: `DEFAULT`, `EXPRESS`. |
| `selectedTimeSlotId` | string (UUID) | null | não | Horário de `getCartDeliveryMethods`. |


### AgentToolPaymentMethod

Schema somente de entrada em `createCart.paymentMethod`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `paymentMethodId` | string (UUID) | sim (se presente) | UUID exato de `listPaymentMethods`. **Não use `kind` como ID.** |
| `cardTokenId` | string | null | não | Token do cartão. |


### Summary

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `totalName` | string | sim | Rótulo do total (ex.: "Total"). |
| `totalAmount` | number | sim | Total final (BRL). |
| `subtotalName` | string | sim | Rótulo do subtotal (ex.: "Subtotal"). |
| `subtotalAmount` | number | sim | Soma dos preços dos itens (BRL). |
| `deliveryFeeName` | string | sim | Rótulo da entrega (ex.: "Taxa de entrega"). |
| `deliveryFeeAmount` | number | sim | Taxa de entrega (BRL). |
| `feeTotalName` | string | sim | Rótulo das taxas (ex.: "Taxas"). |
| `feeTotalAmount` | number | sim | Total de taxas adicionais (BRL). |
| `benefitsTotalName` | string | sim | Rótulo dos benefícios (ex.: "Benefícios"). |
| `benefitsTotalAmount` | number | sim | Total de benefícios (BRL). |
| `voucherTotalName` | string | sim | Rótulo do cupom (ex.: "Cupom"). |
| `voucherTotalAmount` | number | sim | Total do desconto de voucher (BRL). |


### CartDeliveryOptionsResponse

Retornado por: `getCartDeliveryMethods`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `cartId` | string (UUID) | sim | Identificador do carrinho. |
| `deliveryMethods` | array de DeliveryOption | sim | Métodos disponíveis. |
| `warning` | AgentDetail | null | não | Aviso se opções limitadas. |
| `agentHints` | object | null | não | Orientação (pode incluir `noResultsGuidance`). |


### DeliveryOption

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `deliveryMethodId` | string | sim | ID para `setCartDelivery`. |
| `deliveryMethodMode` | string | sim | `DELIVERY`, `TAKEOUT` ou `PICKUP`. |
| `deliveryMethodName` | string | sim | Nome legível. |
| `fee` | number | sim | Taxa (BRL). |
| `estimatedMinutes` | object | sim | `{ "min": integer, "max": integer }`. |
| `timeslots` | array de Timeslot | null | não | Horários para agendamento. `null` para métodos não agendáveis. |


### Timeslot

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `from` | string (date-time) | sim | Início da janela (ISO 8601). |
| `to` | string (date-time) | sim | Fim da janela (ISO 8601). |


### PaymentListPayload

Retornado por: `listPaymentMethods`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `paymentMethods` | array de PaymentMethod | sim | Formas aceitas pelo estabelecimento. |
| `agentHints` | object | null | não | Orientação (pode incluir `noResultsGuidance`). |


### VoucherListPayload

Retornado por: `listVouchers`.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `vouchers` | array de VoucherListItem | sim | Vouchers aplicáveis ao carrinho. |
| `agentHints` | object | null | não | Orientação (pode incluir `noResultsGuidance`). |


### VoucherListItem

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `code` | string | sim | Código para `setVoucher.code`. |
| `campaignId` | string (UUID) | sim | Campanha para `setVoucher.campaignId`. |
| `effectType` | string | null | não | `FIXED` (valor em BRL) ou `PERCENTAGE` (% do subtotal). |
| `effectValue` | number | null | não | Magnitude do efeito. |
| `maxDiscountValue` | number | null | não | Teto do desconto em BRL (ex.: % limitada a R$15). |
| `description` | string | null | não | Descrição legível da promo. |
| `available` | boolean | sim | Se aplicável ao carrinho (sempre `true` em `listVouchers`). |


### CheckoutSuccessBody

Retornado por: `submitOrder` no sucesso.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `orderId` | string (UUID) | sim | UUID v4 do pedido criado. Entrada do Order Tracking MCP. |
| `agentHints` | object | null | não | Orientação (ex.: começar a rastrear). |


### CartErrorResponse

Schema da API subjacente para 404 (Not Found) e 500 (Internal Server Error). Em operação normal, o gateway normaliza para 200 e o agente vê o corpo diretamente. A ausência de `agentHints` e `suggestedActions` indica condição inesperada de servidor — reporte ao usuário e, se `code` indicar condição transitória, tente uma vez.

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `code` | string | sim | Código legível (ex.: `"CART_NOT_FOUND"`). |
| `message` | string | sim | Mensagem legível. |


### AgentDetail

Usado em erros (`AIAgentToolFailureBody.error`) e avisos (`CartDetailsResponse.warning`, `CartDeliveryOptionsResponse.warning`).

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `code` | string | null | não | Código do erro (ex.: `"MERCHANT_CLOSED"`). |
| `message` | string | sim | Instrução para o agente. |
| `details` | object | sim | Contexto estruturado. Pode conter strings, arrays ou inteiros — verifique o tipo antes de usar. Pode ser `{}`. |
| `impact` | Impact | null | não | Se o problema bloqueia o checkout. |
| `suggestedActions` | array de SuggestedAction | sim | Ações concretas de recuperação. |
| `userFriendlyMessage` | string | sim | Mensagem em português para o usuário final. |


### Impact

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `canProceedToCheckout` | boolean | sim | `false` quando bloqueia o checkout; `true` quando é aviso consultivo. |


### SuggestedAction

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `tool` | string | sim | Nome de uma tool sugerida. Trate como sugestão forte, não comando. |
| `displayName` | string | sim | Rótulo legível (ex.: "Buscar restaurantes alternativos"). |
| `payload` | object | sim | Parâmetros pré-preenchidos. Revise e adapte antes de usar. |


### AIAgentToolFailureBody

Retornado por todas as tools do Cart em erros 400 (normalizados para HTTP 200 pelo gateway).

| Campo | Tipo | Obr. | Descrição |
| --- | --- | --- | --- |
| `error` | AgentDetail | sim | Detalhes do erro com instruções e ações de recuperação. |
| `agentHints` | object | sim | Mapa string→string com orientação para o próximo passo. |


## Constantes de enum

### deliveryMethodMode

```
"DELIVERY"  — Entrega em casa
"TAKEOUT"   — Retirada no local
"PICKUP"    — Retirada
```

### paymentMethodKind

```
"CREDIT_CARD"   — Cartão de Crédito
"DEBIT_CARD"    — Cartão de Débito
"PIX"           — PIX instantâneo
"MEAL_VOUCHER"  — Vale Refeição
"FOOD_VOUCHER"  — Vale Alimentação
```

### Valores de `deliveryMethodId`

```
"DEFAULT"   — Entrega padrão
"EXPRESS"   — Entrega expressa
"SCHEDULED" — Entrega agendada (com timeslots)
"TAKEOUT"   — Retirada
```

Os valores válidos são dinâmicos por carrinho — sempre use o `deliveryMethodId` retornado por `getCartDeliveryMethods`.

## Distinções críticas

### `cartItemId` vs `itemId`

- **`itemId`** = ID do item no **catálogo** (do Offer Discovery; usado em `addItemToCart` e `createCart`)
- **`cartItemId`** = ID do item no **carrinho específico** (retornado por `addItemToCart`/`getCart`; obrigatório em `updateCartItem` e `removeItemFromCart`)

### `options` é obrigatório

```
// CORRETO
{ itemId: "...", quantity: 1, options: [] }
// ERRADO — omitir options causa erro
{ itemId: "...", quantity: 1 }
```

### Ordem de chamadas

- `createCart()` (ou retomar com `getCart()`)
- `getCartDeliveryMethods()` → `setCartDelivery()`
- `listPaymentMethods()` → `setCartPayment()`
- (opcional) `listVouchers()` → `setVoucher()`
- `getCart()` (confirmar estado final)
- `submitOrder()`

---

## Casos de Uso — /mcps/cart/casos-de-uso

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/mcps/cart/casos-de-uso

# Casos de Uso — Cart MCP v3.2

Explore cenários reais com código completo usando as 13 tools atômicas.

## Decisão a decisão: raciocínio do agente

Este exemplo mostra cada decisão e raciocínio de um agente real durante o fluxo de compra, agora com vouchers e documento de identificação.

### Cenário: usuário quer "2 pizzas e uma coca"

```
 USUÁRIO: "Quero 2 Margherita Pizza e uma Coca 2L"

 AGENTE PENSA:
   1. [PARSE INTENÇÃO]
      Ação: COMPRAR
      Itens: Pizza (qty=2) + Coca (qty=1)

   2. [DISCOVERY]
      → searchOffers / getItem
      ← merchantId + itemId + options (optionId, customizationId)

   3. [USER CONTEXT]
      → listAddresses
      ← addressId

   4. [CRIAR CARRINHO]
      → createCart(merchantId, addressId, items)
      ← cartId

   5. [DESCOBRIR ENTREGA]
      → getCartDeliveryMethods(cartId)
      ← DEFAULT (R$5,90, 30-45 min), EXPRESS (R$12,90, 15-25 min)

 USUÁRIO: "Entrega padrão está bom"
      → setCartDelivery(cartId, deliveryMethodId="DEFAULT")

   6. [DESCOBRIR PAGAMENTO]
      → listPaymentMethods(merchantId)
      ← CREDIT_CARD, DEBIT_CARD, PIX

 USUÁRIO: "Pago com PIX"
      → setCartPayment(cartId, paymentMethodId="75354fd8-...")

   7. [DESCOBRIR VOUCHERS]
      → listVouchers(cartId)
      ← VCH-10 (R$10 off), PROMO20 (20% até R$15)

 USUÁRIO: "Aplica o VCH-10"
      → setVoucher(cartId, code="VCH-10", campaignId="b8f3c1e2-...")

   8. [RESUMIR E COLETAR DOCUMENTO]
      → getCart(cartId)
      ← itens, totais, entrega, pagamento, voucher aplicado
      Agente pergunta: "CPF ou CNPJ para nota fiscal?"

 USUÁRIO: "Meu CPF é 123.456.789-00. Confirma!"

   9. [CHECKOUT]
      → submitOrder(cartId, userConsent=true, document="123.456.789-00")
      ← orderId

  10. [PÓS-COMPRA]
      → trackOrder(orderId)
```

### Insights críticos neste fluxo

| Decisão | Racional | Erro comum |
| --- | --- | --- |
| **Sempre chamar Discovery ANTES de `createCart()`** | Cart precisa de `itemId` e `options` do catálogo. | Hardcodar `itemId` ou usar `options` inválidos |
| **Salvar `cartItemId` de cada resposta** | Necessário para update/remove. | Confundir `itemId` vs `cartItemId` |
| **Descobrir antes de aplicar** | `getCartDeliveryMethods` → `setCartDelivery`; `listPaymentMethods` → `setCartPayment`; `listVouchers` → `setVoucher` | Hardcodar IDs de entrega/pagamento ou `code`/`campaignId` |
| **Pedir consentimento E documento antes de `submitOrder()`** | `userConsent: true` é obrigatório; `document` (CPF/CNPJ/Passaporte) é exigido por regulação. | Submeter sem confirmar ou sem documento |
| **Validar `error.impact.canProceedToCheckout`** | Indica se pode retry com ajuste. | Retry infinito em `MERCHANT_CLOSED` |


## Caso 1: Fluxo completo (happy path)

**Objetivo**: Usuário seleciona carrinho, entrega, pagamento, aplica voucher e faz checkout.

**Sequência**:

- `createCart()` — criar carrinho
- `getCartDeliveryMethods()` → `setCartDelivery()` — entrega
- `listPaymentMethods()` → `setCartPayment()` — pagamento
- `listVouchers()` → `setVoucher()` — voucher (opcional)
- `getCart()` — confirmar estado final
- `submitOrder()` — enviar pedido

### JavaScript

```
const cartClient = new iFood.CartClient({ token: YOUR_TOKEN });

async function completeCheckoutFlow(merchantId, addressId, itemsToAdd) {
  // 1. Criar carrinho
  const cart = await cartClient.createCart({
    merchantId, addressId, items: itemsToAdd
  });

  // 2. Descobrir e definir entrega
  const deliveryOptions = await cartClient.getCartDeliveryMethods({ cartId: cart.cartId });
  const firstMethod = deliveryOptions.deliveryMethods[0];
  await cartClient.setCartDelivery({
    cartId: cart.cartId,
    deliveryMethodId: firstMethod.deliveryMethodId
  });

  // 3. Descobrir e definir pagamento
  const paymentMethods = await cartClient.listPaymentMethods({ merchantId });
  const pix = paymentMethods.paymentMethods.find(m => m.kind === "PIX");
  await cartClient.setCartPayment({
    cartId: cart.cartId,
    paymentMethodId: pix.paymentMethodId // UUID, NÃO "PIX"
  });

  // 4. (Opcional) descobrir e aplicar voucher
  const vouchers = await cartClient.listVouchers({ cartId: cart.cartId });
  if (vouchers.vouchers.length > 0) {
    const chosen = vouchers.vouchers[0];
    await cartClient.setVoucher({
      cartId: cart.cartId,
      code: chosen.code,
      campaignId: chosen.campaignId
    });
  }

  // 5. Confirmar estado final
  const finalCart = await cartClient.getCart({ cartId: cart.cartId });
  console.log(`Total: R$ ${finalCart.summary.totalAmount}`);

  // 6. Submeter pedido (com documento)
  const order = await cartClient.submitOrder({
    cartId: cart.cartId,
    userConsent: true,          // Obrigatório!
    document: "123.456.789-00"  // CPF/CNPJ/Passaporte
  });

  console.log(`Pedido confirmado: ${order.orderId}`);
  return order;
}
```

### Python

```
cart_client = iFood.CartClient(token=YOUR_TOKEN)

def complete_checkout_flow(merchant_id, address_id, items_to_add):
  # 1. Criar carrinho
  cart = cart_client.create_cart(merchant_id=merchant_id, address_id=address_id, items=items_to_add)

  # 2. Descobrir e definir entrega
  delivery_options = cart_client.get_cart_delivery_methods(cart_id=cart['cartId'])
  first_method = delivery_options['deliveryMethods'][0]
  cart_client.set_cart_delivery(cart_id=cart['cartId'], delivery_method_id=first_method['deliveryMethodId'])

  # 3. Descobrir e definir pagamento
  payment_methods = cart_client.list_payment_methods(merchant_id=merchant_id)
  pix = next(m for m in payment_methods['paymentMethods'] if m['kind'] == 'PIX')
  cart_client.set_cart_payment(cart_id=cart['cartId'], payment_method_id=pix['paymentMethodId'])

  # 4. (Opcional) descobrir e aplicar voucher
  vouchers = cart_client.list_vouchers(cart_id=cart['cartId'])
  if vouchers['vouchers']:
    chosen = vouchers['vouchers'][0]
    cart_client.set_voucher(cart_id=cart['cartId'], code=chosen['code'], campaign_id=chosen['campaignId'])

  # 5. Confirmar estado final
  final_cart = cart_client.get_cart(cart_id=cart['cartId'])
  print(f"Total: R$ {final_cart['summary']['totalAmount']}")

  # 6. Submeter pedido
  order = cart_client.submit_order(cart_id=cart['cartId'], user_consent=True, document="123.456.789-00")
  print(f"Pedido confirmado: {order['orderId']}")
  return order
```

## Caso 2: Reordenação (createCart com `orderId`)

**Objetivo**: Usuário quer repetir um pedido anterior. Em vez de montar do zero, passe apenas `orderId` — o servidor deriva `merchantId`, `addressId` e `items` do pedido original.

**Sequência**:

- `createCart(orderId)` — semear o carrinho com os itens do pedido anterior
- `getCart()` — verificar itens semeados a preços atuais (itens podem ter saído do cardápio)
- `submitOrder()` — após reconfigurar entrega/pagamento se necessário

### JavaScript

```
async function reorderFlow(orderId) {
  // 1. Criar carrinho a partir do pedido anterior (Caminho B)
  const cart = await cartClient.createCart({ orderId });

  // 2. SEMPRE verificar os itens semeados — preços são recalculados
  const state = await cartClient.getCart({ cartId: cart.cartId });
  state.items.forEach(i => console.log(`- ${i.quantity}x ${i.name} (R$ ${i.unitPrice})`));

  if (state.items.length === 0) {
    console.warn("Nenhum item disponível para reordenação — monte um carrinho novo.");
    return null;
  }

  // 3. Entrega e pagamento podem precisar ser reconfirmados
  // ... getCartDeliveryMethods → setCartDelivery, listPaymentMethods → setCartPayment

  const order = await cartClient.submitOrder({
    cartId: cart.cartId,
    userConsent: true,
    document: "123.456.789-00"
  });
  return order;
}
```

**Importante**: não misture `orderId` com `merchantId`/`addressId`/`items` — são caminhos mutuamente exclusivos. Com `orderId`, os demais campos são ignorados.

## Caso 3: Adicionar e atualizar itens

**Objetivo**: Criar carrinho, adicionar um item novo e alterar quantidade. Demonstra `cartItemId` vs `itemId`.

### JavaScript

```
async function modifyItemsFlow(cartId, newItemId) {
  // 1. Adicionar novo item (itemId = catálogo)
  const addResult = await cartClient.addItemToCart({
    cartId, itemId: newItemId, quantity: 1, options: []
  });

  // SALVAR cartItemId — você precisa dele para updates!
  const cartItemId = addResult.items[addResult.items.length - 1].cartItemId;

  // 2. Atualizar quantidade (cartItemId = carrinho; itemId = validação)
  await cartClient.updateCartItem({
    cartId,
    cartItemId,        // Use cartItemId, NÃO itemId!
    itemId: newItemId, // Obrigatório para validação
    quantity: 3,
    options: []
  });

  // 3. Confirmar estado
  const cart = await cartClient.getCart({ cartId });
  console.log(`Novo total: R$ ${cart.summary.totalAmount}`);
}
```

## Caso 4: Remover item

**Objetivo**: Remover um item do carrinho — e tratar o caso do último item (carrinho auto-excluído).

### JavaScript

```
async function removeItemFlow(cartId, cartItemId) {
  const result = await cartClient.removeItemFromCart({ cartId, cartItemId });

  if (result.agentHints?.cartDeletedAfterLastItemRemoved) {
    console.warn("Carrinho excluído — último item removido. Crie um novo se precisar.");
    return null;
  }

  console.log(`${result.items.length} item(ns) restante(s) no carrinho`);
  return result;
}
```

## Caso 5: Aplicar e remover voucher

**Objetivo**: Descobrir vouchers aplicáveis, aplicar um e, depois, removê-lo.

### JavaScript

```
async function voucherFlow(cartId) {
  // 1. Descobrir vouchers aplicáveis
  const result = await cartClient.listVouchers({ cartId });
  if (result.vouchers.length === 0) {
    console.log("Nenhum cupom aplicável a este carrinho.");
    return;
  }

  // 2. Aplicar o escolhido (code + campaignId exatos)
  const chosen = result.vouchers[0];
  await cartClient.setVoucher({
    cartId,
    code: chosen.code,
    campaignId: chosen.campaignId
  });

  const withVoucher = await cartClient.getCart({ cartId });
  console.log(`Desconto: R$ ${withVoucher.summary.voucherTotalAmount}`);
  console.log(`Total: R$ ${withVoucher.summary.totalAmount}`);

  // 3. Remover o voucher (se o usuário mudar de ideia)
  await cartClient.removeVoucher({ cartId });
  const withoutVoucher = await cartClient.getCart({ cartId });
  console.log(`Total sem cupom: R$ ${withoutVoucher.summary.totalAmount}`);
}
```

## Caso 6: Tratamento de erro retryable

**Objetivo**: Quando o método de entrega virar indisponível no checkout, recuperar oferecendo alternativa.

### JavaScript

```
async function checkoutWithRetry(cartId, merchantId) {
  const order = await cartClient.submitOrder({ cartId, userConsent: true });

  if (!order.error) {
    return order; // Sucesso
  }

  // Ler o código de erro e as ações sugeridas
  console.log(`${order.error.message}`);
  console.log(`Próxima ação: ${order.agentHints.nextStepBeforeCheckout}`);

  if (order.error.code === "DELIVERY_METHOD_UNAVAILABLE") {
    // 1. Obter novas opções
    const newOptions = await cartClient.getCartDeliveryMethods({ cartId });

    // 2. Escolher e aplicar
    const selected = newOptions.deliveryMethods[0];
    await cartClient.setCartDelivery({
      cartId,
      deliveryMethodId: selected.deliveryMethodId
    });

    // 3. Retry checkout
    const retryOrder = await cartClient.submitOrder({
      cartId, userConsent: true, document: "123.456.789-00"
    });
    return retryOrder;
  }

  if (order.error.code === "CART_NOT_READY") {
    // Falta entrega ou pagamento — configurar antes de retry
    console.log(`Faltando: ${order.error.details.missingRequirements.join(", ")}`);
    return null;
  }

  throw new Error(`Erro não tratado: ${order.error.code}`);
}
```

## Boas práticas & erros comuns de agentes

### 1. Sempre salvar `cartItemId`

```
const result = await cartClient.addItemToCart({ ... });
const cartItemId = result.items[result.items.length - 1].cartItemId;
// SALVE cartItemId para usar em updateCartItem() e removeItemFromCart()
```

### 2. Nunca omita `options`

```
// CORRETO
{ itemId: "...", quantity: 1, options: [] }
// ERRADO
{ itemId: "...", quantity: 1 }  // Causa erro!
```

### 3. Sempre validar a resposta (`error` vs sucesso)

```
if (response.error) {
  // Trata erro — leia error.code, error.message, suggestedActions
} else {
  // Sucesso
}
```

### 4. Descobrir antes de aplicar (entrega, pagamento, voucher)

```
getCartDeliveryMethods → setCartDelivery
listPaymentMethods      → setCartPayment
listVouchers            → setVoucher
```

Nunca hardcode `deliveryMethodId`, `paymentMethodId` ou `code`/`campaignId`.

### 5. `userConsent` e `document` em `submitOrder`

```
// Após usuário confirmar explicitamente
const order = await cartClient.submitOrder({
  cartId,
  userConsent: true,           // Obrigatório!
  document: "123.456.789-00"   // CPF/CNPJ/Passaporte (opcional se não fornecido)
});
```

### 6. Distinção: `cartItemId` vs `itemId`

- **`itemId`** = ID do catálogo (use em `addItemToCart`, `createCart`)
- **`cartItemId`** = ID no carrinho (use em `updateCartItem`, `removeItemFromCart`)

### 7. Não confundir `setVoucher` com `removeVoucher`

- Aplicar voucher → `setVoucher(cartId, code, campaignId)`
- Remover voucher → `removeVoucher(cartId)`

## Erros comuns de agentes — o que NÃO fazer

### Erro #1: Confundir IDs em `updateCartItem`

```
// ERRADO — usar itemId onde cartItemId esperado
await cartClient.updateCartItem({
  cartId,
  cartItemId: catalogItemId, // ← é itemId!
  quantity: 3
});
// Resultado: CART_ITEM_NOT_FOUND
```

**Correto**: salve o `cartItemId` de `addItemToCart`/`getCart` e use-o aqui.

### Erro #2: Hardcodar `paymentMethodId` com o valor `kind`

```
// ERRADO — usar "PIX" como ID
await cartClient.setCartPayment({ cartId, paymentMethodId: "PIX" });
// Resultado: 422 — paymentMethodId deve ser o UUID de listPaymentMethods

// CORRETO
await cartClient.setCartPayment({ cartId, paymentMethodId: "75354fd8-e916-41db-9286-93be2232efe2" });
```

### Erro #3: Retry infinito em erro não-retryable

```
// ERRADO — loop sem validar canProceedToCheckout
while (true) {
  const order = await cartClient.submitOrder({ cartId, userConsent: true });
  if (!order.error) break;
  // Nunca sai do loop para MERCHANT_CLOSED!
}

// CORRETO — validar antes de retry
if (response.error && !response.error.impact.canProceedToCheckout) {
  throw new Error(`Erro fatal: ${response.error.code}`); // PARAR!
}
```

### Erro #4: Omitir `userConsent` ou `document`

```
// ERRADO
await cartClient.submitOrder({ cartId, userConsent: false });
// Resultado: CONSENT_REQUIRED

// CORRETO
await cartClient.submitOrder({
  cartId,
  userConsent: true,          // após confirmação explícita
  document: "123.456.789-00"
});
```

## Checklist final

Antes de chamar cada tool, validar:

-  **IDs**: `cartItemId` em update/remove; `itemId` em add/create; `paymentMethodId` como UUID
-  **`options`**: array incluído (mesmo que `[]`)
-  **Descoberta**: `getCartDeliveryMethods`/`listPaymentMethods`/`listVouchers` antes de `set*`
-  **Voucher**: `code` + `campaignId` exatos de `listVouchers`
-  **Erros**: validar `error.code` e `error.impact.canProceedToCheckout` antes de retry
-  **Consentimento**: confirmação explícita antes de `submitOrder()` com `userConsent: true`
-  **Documento**: CPF/CNPJ/Passaporte coletado antes do checkout
-  **Backoff**: delay entre retries; nunca retry infinito

---

## Glossário — https://mcp-developer.ifood.com.br/pt-BR/docs/glossary

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/glossary

# E

## Example

Exemplo de glossário

---

## Changelog — https://mcp-developer.ifood.com.br/pt-BR/docs/changelog

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/changelog

# Exemplo

Exemplo

# Mudanças Recentes

## 2025/01/01

- Exemplo

## 2024/01/01

- Exemplo

## 2023/01/01

- Exemplo

---

## Condições Gerais de Uso - MCP Developer Portal iFood — https://mcp-developer.ifood.com.br/pt-BR/docs/terms-of-use

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/terms-of-use

# Condições Gerais de Uso — MCP Developer Portal iFood

## 1. Identificação e aceite

**1.1.** Estas Condições Gerais de Uso — MCP Developer Portal iFood ("Condições") disciplinam o acesso e o uso do Portal e dos recursos de MCP disponibilizados pelo iFood ou por terceiros autorizados no ecossistema, conforme o escopo efetivamente habilitado ao usuário.

**1.2.** Para acessar funcionalidades que exigem aceite, a pessoa física deverá se identificar com dados verdadeiros e, quando atuar por uma organização, declarar que possui poderes ou autorização suficientes para vinculá-la.

**1.3.** O aceite eletrônico ocorrerá mediante marcação da caixa de seleção, clique ou mecanismo equivalente na jornada do Portal.

**1.4.** Ao aceitar, o usuário declara ter lido estas Condições.

**1.5.** Se o usuário não concordar com as Condições aplicáveis, não deverá utilizar as funcionalidades que dependam de aceite.

## 2. Definições

Para fins destas Condições:

- **"MCP"** significa "Model Context Protocol" ou "Protocolo de Contexto de Modelo". É um padrão de código aberto criado para conectar aplicações de inteligência artificial.
- **"Agente"** significa aplicação ou sistema baseado em IA capaz de interpretar instruções e, conforme suas permissões, produzir conteúdo, recomendações ou executar ações por meio de ferramentas ou integrações.
- **"Servidor MCP"** significa componente que implementa o MCP e expõe ferramentas, recursos ou contexto para consumo por um agente ou cliente autorizado.
- **"Ferramenta"** significa função, ação, API, recurso ou capacidade exposta por um servidor MCP, agente, integração ou outro componente conectado ao Portal.
- **"Integradora"** ou **"empresa integradora"** significa pessoa jurídica ou pessoa desenvolvedora que cria, conecta, publica, registra, opera ou disponibiliza componente ou integração no ecossistema, em nome próprio ou autorizado por terceiro.
- **"Desenvolvedora"** significa pessoa física ou jurídica que cria, mantém ou publica agente, servidor MCP, ferramenta ou integração.
- **"Credenciais"** significa qualquer segredo, token, chave, certificado, senha, IDs ou mecanismo de autenticação/autorização associado ao Portal ou a uma integração.
- **"Ecossistema MCP"** significa o conjunto de Portal, APIs, servidores MCP, agentes, ferramentas, integrações, ambientes, catálogos, documentação e serviços habilitados ou relacionados.
- **"Owner"** significa a pessoa ou organização responsável pelo propósito, segurança, manutenção, acessos, ciclo de vida, resposta a incidentes e conformidade do componente registrado.
- **"Portal"** significa o MCP Developer Portal iFood, incluindo interfaces, áreas de cadastro, catálogo, documentação e funções que venham a ser disponibilizadas em [https://mcp-developer.ifood.com.br/](https://mcp-developer.ifood.com.br/).
- **"Produção"** significa ambiente ou operação com usuários, sistemas, dados ou processos reais, em contraste com sandbox/homologação.
- **"Sandbox"** significa ambiente segregado e controlado destinado a testes e experimentação, sem dados reais, salvo autorização expressa e documentada.
- **"Propriedade Intelectual"** significa todos os direitos de propriedade intelectual, incluindo, sem limitação, patentes, marcas, direitos autorais, segredos de negócio, know-how, desenhos, software, APIs, código-fonte, bases de dados e demais direitos correlatos, reconhecidos no Brasil ou no exterior, registrados ou não.
- **"Informações Confidenciais"** significam informações sobre a existência destas Condições Gerais, o objeto e os Serviços e qualquer negociação envolvendo as Partes, verbais ou escritas, identificadas ou não como confidenciais, sobre negócios (atuais ou futuros), planos de negócio, projetos, estratégias da Parte Divulgadora e/ou de suas afiliadas, incluindo, mas não se limitando, documentos pertencentes ou relacionados às Partes e/ou suas Afiliadas, know-how, segredos comerciais e/ou industriais, especificações, produtos, operações, processos, dados, previsões, gráficos, demonstrações financeiras e/ou contábeis, documentos gerenciais, informações comerciais, administrativas, sobre produtos e/ou informações, publicadas ou não, relacionadas aos direitos de propriedade intelectual de titularidade das Partes e/ou de suas afiliadas, e/ou a elas licenciados, bem como qualquer outra informação comercial, financeira, administrativa, operacional ou técnica relacionada aos Serviços. Serão também consideradas Informações Confidenciais todas as informações e resultados provenientes dos Serviços.

## 3. Objeto e escopo

**3.1.** O objeto destas Condições é estabelecer regras para cadastro, autenticação, desenvolvimento, registro, publicação, conexão e consumo de agentes, servidores MCP, ferramentas e integrações por meio do Portal.

**3.2.** O acesso é limitado às funcionalidades habilitadas ao usuário, à organização e ao ambiente correspondente. Uma autorização para testar ou registrar um componente não implica autorização para publicá-lo ou operá-lo em Produção.

## 4. Elegibilidade, cadastro e informações

**4.1.** Poderão se cadastrar pessoas desenvolvedoras e empresas integradoras que atendam aos requisitos técnicos, comerciais, de segurança e de conformidade definidos para o Portal.

**4.2.** O usuário deverá fornecer informações completas, exatas, atuais e verificáveis, manter o cadastro atualizado e corrigir informações incorretas. É proibido criar identidade falsa.

## 5. Regras de uso do Portal e do Ecossistema MCP

**5.1.** O usuário deverá utilizar o Portal de acordo com estas Condições, a documentação vigente e as instruções de segurança, somente para finalidade legítima, autorizada e compatível com o cadastro.

**5.2.** O usuário deverá documentar finalidade, owner, arquitetura, dados, ferramentas, permissões, dependências, ambientes e classificação de risco do componente. Alterações relevantes poderão exigir nova análise ou homologação.

**5.3.** Componentes destinados à produção deverão ter origem confiável, registro no catálogo ou inventário aplicável e homologação técnica e de segurança, quando exigidos pelo fluxo vigente. Componentes não homologados deverão ficar restritos a Sandbox segregado, sem dados reais, credenciais corporativas válidas ou propriedade intelectual estratégica, salvo aprovação específica documentada.

**5.4.** O usuário não deverá contornar limites técnicos, controles de acesso, validações, filtros, rate limiting, quotas, mecanismos de auditoria ou kill switch.

**5.5.** Não há autorização implícita para acessar dados, APIs, contas, ambientes ou funcionalidades não indicados na configuração aprovada.

## 6. Segurança, IA, dados, ambiente e homologação

**6.1.** O componente deverá seguir o princípio do menor privilégio: somente ferramentas, escopos, dados e operações estritamente necessários poderão ser habilitados. Credenciais genéricas, compartilhadas ou com privilégios superiores aos necessários são proibidas.

**6.2.** O uso de dados pessoais deverá ser minimizado, justificado pela finalidade e previamente avaliado/autorizado quando exigido. Sempre que possível, devem ser empregados anonimização, mascaramento, desidentificação, agregação e filtros de dados pessoais. Dados pessoais sensíveis não deverão ser utilizados em prompts, contexto, memória, treinamento, logs ou outputs, salvo exceção.

## 7. Privacidade e Proteção de dados

**7.1.** Ao cumprir as obrigações previstas nestas Condições Gerais, as partes, por si e por seus sócios, administradores, diretores, agentes, representantes, funcionários e colaboradores, obrigam-se a respeitar, fielmente, a legislação aplicável à proteção de dados pessoais, como a Lei Geral de Proteção de Dados (Lei federal nº 13.709/2018), o Marco Civil da Internet (Lei federal nº 12.965/2014) e seu Decreto regulamentador nº 8.771/2016, e a garantir a privacidade dos usuários, entregadores, colaboradores e demais dados acessados ou de qualquer forma disponibilizados para a execução do objeto destas Condições Gerais.

**7.2.** Para fins destas Condições Gerais, as Partes obrigam-se a conduzir as suas atividades em boa-fé e de acordo com os princípios que regem a proteção de dados pessoais, como a finalidade, adequação e necessidade.

**7.3.** As Integradoras e Desenvolvedoras declaram que receberam cópias (via link) das Declarações de Privacidade do iFood e que tomaram ciência de seu conteúdo disponível em: [https://privacidade.ifood.com.br/pt-BR/home/](https://privacidade.ifood.com.br/pt-BR/home/).

**7.4.** Em conformidade com o objeto previsto nas Condições Gerais, as Integradoras e Desenvolvedoras poderão ter acesso a dados enviados pelo iFood que identifiquem ou permitam a identificação de indivíduos ("Dados Pessoais").

**7.5.** As atividades de acesso, utilização, coleta, produção, recepção, classificação, reprodução, transmissão, distribuição, processamento, arquivamento, armazenamento, eliminação, avaliação ou controle da informação, modificação, comunicação, transferência, difusão ou extração e a transferência a terceiro de Dados Pessoais compartilhados pelo iFood ("Tratamento de Dados Pessoais") serão autorizadas às Integradoras e Desenvolvedoras desde que limitadas ao estritamente necessário para a execução dos Serviços e tão somente durante a vigência das Condições Gerais. Fica vedada a utilização dos Dados Pessoais para atender quaisquer outras finalidades além daquelas necessárias para a execução do objeto das Condições Gerais.

**7.6.** Caso as Integradoras e Desenvolvedoras necessitem ter acesso a quaisquer banco de dados, sejam estes pessoais ou não, e/ou à infraestrutura de tecnologia da informação do iFood para execução do Projeto, esta deverá seguir as regras e direcionamentos do time de Segurança do iFood e comprometer-se com a preservação de seu ambiente seguro e estável.

**7.7.** Fica vedado às Integradoras e Desenvolvedoras transferir, no todo ou em parte, os Dados Pessoais compartilhados pelo iFood para quaisquer terceiros que não estejam diretamente relacionados com a execução dos Serviços, ainda que de forma agregada e/ou anônima. Fica vedado às Integradoras e Desenvolvedoras subcontratar terceiro, sem autorização por escrito do iFood, para realizar atividade de tratamento relacionada aos Dados Pessoais compartilhados pelo iFood e/ou acessados em razão das Condições Gerais.

**7.8.** De acordo com as orientações do iFood, as Integradoras e Desenvolvedoras deverão promover a exclusão definitiva de quaisquer Dados Pessoais que lhe foram transmitidos por força deste instrumento, durante ou após finda a sua vigência.

**7.9.** As partes deverão acordar sobre a forma mais segura para envio ou transmissão dos Dados Pessoais necessários para execução dos Serviços, sendo que as Integradoras e Desenvolvedoras se comprometem a assegurar a segurança, privacidade e a adequada gestão dos Dados Pessoais compartilhados pelo iFood. As Integradoras e Desenvolvedoras deverão valer-se de técnicas de segurança como criptografia, hardening, controle de acesso, dupla autenticação, monitoramento e testes de segurança frequentes, dentre outros métodos de proteção condizentes com as melhores práticas do setor para a segurança e a proteção de dados.

**7.10.** As Integradoras e Desenvolvedoras obrigam-se a notificar o iFood, em até 24 (vinte e quatro) horas, por meio do Suporte do Developer Portal, clicando em "Chamados" e, em seguida, enviar mensagem sobre "Dúvidas/Incidentes/Requisições", acerca de qualquer incidente de segurança, como o vazamento ou comprometimento de suas bases de dados relacionadas a este instrumento, bem como acerca de qualquer violação da legislação de privacidade e de proteção de dados pessoais sobre a qual tiver ciência com relação aos dados em sua custódia, inclusive violação acidental ou culposa. Na ocorrência de incidente de segurança, as Integradoras e Desenvolvedoras devem informar as seguintes informações básicas ao iFood, dentro do prazo indicado e sem se limitar a: (i) data e hora do incidente, (ii) tipos e volume de Dados Pessoais envolvidos, (iii) volume de titulares afetados, (iv) medidas de segurança e mitigação já implementadas. Demais medidas mitigadoras, como a comunicação às autoridades competentes e/ou aos titulares dos Dados Pessoais, devem ser tomadas estritamente de acordo com as orientações do iFood.

**7.11.** Caso o iFood sofra quaisquer danos ou prejuízos decorrentes do descumprimento, ocasionado por ação ou omissão por parte das Integradoras e Desenvolvedoras e/ou por seus respectivos subcontratados, das obrigações e/ou cláusulas de proteção de dados pessoais previstas neste instrumento, ficarão as Integradoras e Desenvolvedoras obrigados a ressarcir integralmente o iFood de quaisquer perdas, danos, prejuízos e lucros cessantes, incluindo quaisquer custas judiciais, administrativas e honorários advocatícios.

**7.12.** Caso as Integradoras e Desenvolvedoras sejam obrigados a transferir e/ou divulgar qualquer Dado Pessoal em razão de ordem administrativa ou judicial de qualquer natureza, deverão informar ao iFood em até 24 (vinte e quatro) horas, a fim de que este possa tomar as medidas judiciais que entender necessárias. Além disso, as Integradoras e Desenvolvedoras comprometem-se a cooperar com o iFood para limitar a extensão e o âmbito de tal transferência e/ou divulgação de dados respeitando qualquer conteúdo que faça referência a segredos de negócio do iFood.

**7.13.** Na hipótese de as Integradoras e Desenvolvedoras serem questionados por autoridades públicas competentes ou envolvida em ação judicial relacionada ao cumprimento da legislação, as Integradoras e Desenvolvedoras obrigam-se a informar ao iFood no prazo de até 24 (vinte e quatro) horas tão logo tenha ciência e a assumir a defesa relacionada a esses questionamentos por sua própria conta e custos, comprometendo-se a indenizar iFood com relação a quaisquer prejuízos havidos, inclusive com relação a custas judiciais, administrativas e honorários advocatícios.

## 8. Credenciais

**8.1.** O iFood poderá bloquear, rotacionar ou revogar Credenciais quando houver risco, violação, ausência de necessidade, alteração de escopo ou exigência de segurança, observados os procedimentos e comunicações aplicáveis.

## 9. Usos proibidos

Sem prejuízo de outras restrições legais ou contratuais, é proibido:

- usar o Portal para finalidade ilegal, fraudulenta, discriminatória, ofensiva, enganosa ou que viole direitos de terceiros;
- criar ou operar componente sem owner, inventário/registro ou homologação exigida;
- utilizar componentes, ferramentas, conectores, bases ou integrações não homologados;
- contornar autenticação, autorização, controles corporativos, auditoria, quotas ou limites;
- exfiltrar, revelar ou tentar obter dados pessoais, segredos, tokens, propriedade intelectual ou informações confidenciais sem autorização;
- induzir agente a ignorar instruções de segurança, revelar contexto protegido, executar ação indevida ou burlar salvaguardas;
- executar ação destrutiva, financeira ou crítica sem autorização e supervisão exigidas;
- inserir conteúdo político, discriminatório, ilegal ou que infrinja propriedade intelectual;
- testar ou operar com credenciais corporativas válidas em Sandbox sem autorização;
- revender, sublicenciar ou compartilhar acesso ao Portal ou Credenciais sem autorização expressa; ou
- interferir na disponibilidade, integridade, segurança ou operação do Portal ou de terceiros.

## 10. Confidencialidade

**10.1.** As Partes reconhecem que, em razão destas Condições Gerais, poderão disponibilizar ("Parte Divulgadora") informações confidenciais sobre as suas atividades ou estratégicas de negócio à outra ("Parte Receptora") para a realização do objeto destas Condições Gerais.

**10.2.** A Parte Receptora não divulgará Informações Confidenciais a terceiros, concedendo acesso apenas aos seus empregados, funcionários ou prepostos diretamente envolvidos no cumprimento destas Condições Gerais. Cada Parte será responsável por eventuais violações de confidencialidade cometidas por seus empregados, funcionários, prepostos e/ou subcontratados.

**10.3.** É vedado às Partes, seus sócios, funcionários ou prepostos, usar as Informações Confidenciais em benefício próprio ou de terceiros para desenvolver atividade igual ou similar à da outra Parte.

**10.4.** Não são Informações Confidenciais as informações cuja revelação seja autorizada prévia e expressamente por qualquer uma das Partes ou que se tornaram ou venham a se tornar de domínio público, sem que tenha ocorrido violação de qualquer obrigação de confidencialidade.

**10.5.** Qualquer violação ao compromisso de confidencialidade será passível de multa no valor total do Contrato, além dos danos ou prejuízos sofridos. A Parte afetada pela violação poderá tomar as medidas que julgar adequadas para defender seus interesses.

**10.6.** A obrigação de confidencialidade estabelecida nesta seção perdurará por 3 (três) anos após o término ou extinção destas Condições Gerais.

## 11. Propriedade Intelectual

**11.1.** O iFood é e permanece titular de todos os direitos de propriedade intelectual relacionados ao Portal, ao Ecossistema MCP, às APIs, documentação, marcas, interfaces e demais recursos por ele disponibilizados, incluindo, sem limitações, suas marcas, registradas ou não, nomes de domínio, slogans, trade dress, layouts, expressões publicitárias e demais sinais distintivos, estejam protegidos ou não.

**11.2.** As ferramentas, agentes, servidores MCP e integrações desenvolvidos pela Desenvolvedora ou Integradora ("Componentes Desenvolvidos") permanecem de titularidade da respectiva Desenvolvedora ou Integradora, ressalvadas as licenças de software livre ou de terceiros incorporados. A Desenvolvedora ou Integradora deverá apresentar, quando solicitado, documentação que comprove sua titularidade ou licença válida de todos os componentes utilizados.

**11.3.** Ao publicar ou registrar Componente Desenvolvido no Portal, a Desenvolvedora ou Integradora concede ao iFood uma licença não exclusiva, mundial, gratuita, transferível e sublicenciável para usar, reproduzir, modificar, adaptar, executar, distribuir e operar tal Componente, na medida necessária para o funcionamento, manutenção, evolução e segurança do Portal e do Ecossistema MCP.

**11.4.** A Desenvolvedora ou Integradora garante ao iFood que os Componentes Desenvolvidos e as informações fornecidas não infringem quaisquer direitos de propriedade intelectual próprios ou de terceiros, ou segredos comerciais e/ou industriais, assumindo a obrigação de manter o iFood a todo o tempo, mesmo após o término do prazo de vigência destas Condições Gerais, livre de qualquer ação, reclamação ou indenização por parte de terceiros, por violação de direitos de imagem, autorais ou de propriedade industrial, comprometendo-se a indenizar o iFood por quaisquer perdas, danos, custas judiciais e honorários advocatícios decorrentes de reivindicação em contrário.

**11.5.** A Desenvolvedora ou Integradora não utilizará as marcas e os nomes do iFood de forma a diminuir seu valor ou prejudicar a sua reputação.

**11.6.** A Desenvolvedora ou Integradora não poderá registrar ou requerer o registro, em qualquer país, em seu próprio nome ou em nome de terceiros, de qualquer nome, marca, nome de domínio, direito autoral, segredo de negócio, símbolo, designação, indício, slogan ou sinal que possa induzir, causar confusão ou gerar associação com as propriedades do iFood.

**11.7.** A Desenvolvedora ou Integradora não poderá, sem a prévia e expressa aprovação do iFood, realizar qualquer das seguintes atividades: (i) divulgar a existência destas Condições Gerais e/ou sua relação contratual com o iFood; (ii) listar e/ou divulgar o iFood como seu cliente, parceiro ou figura similar; e/ou (iii) realizar qualquer tipo de divulgação pública, entrevista, por qualquer meio em que mencione a existência destas Condições Gerais, da relação contratual entre as Partes ou utilize a marca iFood.

**11.8.** Após o término ou a rescisão destas Condições Gerais por quaisquer motivos, a Desenvolvedora ou Integradora deverá imediatamente cessar o uso de quaisquer direitos de propriedade intelectual ou industrial do iFood.

**11.9.** O iFood poderá remover ou desativar qualquer Componente Desenvolvido que, a seu critério razoável, seja suspeito de violar direitos de propriedade intelectual de terceiros, sem prejuízo das demais medidas cabíveis.

## 12. Terceiros e serviços externos

**12.1.** Componentes podem depender de serviços externos, provedores de modelos, bibliotecas, APIs ou infraestrutura de terceiros. O usuário deverá avaliar segurança, privacidade, retenção, treinamento, localização, disponibilidade, licenças, subcontratados e riscos antes de habilitar a dependência.

**12.2.** Termos e políticas do terceiro podem se aplicar diretamente ao usuário. O iFood não assume, por estas Condições, responsabilidade pelo serviço externo, seu conteúdo, disponibilidade, tratamento de dados ou alterações.

## 13. Logs, monitoramento, auditoria e cooperação

**13.1.** Podemos manter a observabilidade proporcional ao risco, incluindo logs de autenticação, interações, chamadas de ferramentas, decisões ou aprovações relevantes, erros, alterações e eventos de segurança, quando aplicável.

**13.2.** Logs deverão evitar segredos e dados pessoais desnecessários, ter controles de acesso e ser mantidos pelo período definido na política aplicável.

**13.3.** O iFood poderá monitorar o uso do Portal e realizar verificações técnicas, de segurança, privacidade, risco ou conformidade, observados os limites legais e contratuais. O usuário deverá cooperar com solicitações razoáveis e fornecer evidências de controle, testes, arquitetura, owner e permissões.

## 14. Compliance

**14.1.** As partes comprometem-se a cumprir todas as leis anticorrupção aplicáveis, incluindo a Lei Federal nº 12.846/2013 (Lei Anticorrupção), a Lei nº 8.429/1992 (Lei de Improbidade Administrativa), bem como a Foreign Corrupt Practices Act (FCPA) e a UK Bribery Act, quando aplicáveis.

**14.2.** Fica expressamente proibido à Desenvolvedora, Integradora e seus respectivos sócios, administradores, funcionários e representantes oferecer, prometer, pagar, autorizar ou aceitar, direta ou indiretamente, qualquer vantagem indevida, pagamento ou benefício a agente público, parte interessada ou terceiro, com o objetivo de obter, reter ou direcionar negócio ou vantagem indevida.

**14.3.** O descumprimento das obrigações desta seção constitui violação grave destas Condições Gerais, sujeitando a parte infratora à suspensão ou encerramento imediato, sem prejuízo das medidas judiciais e administrativas cabíveis.

## 15. Disponibilidade, alterações, suspensão e encerramento

**15.1.** O Portal e seus recursos poderão ser alterados, descontinuados, limitados ou temporariamente indisponibilizados por manutenção, segurança, evolução técnica, risco, exigência legal ou outra razão legítima, conforme comunicações e compromissos que venham a ser definidos.

**15.2.** O iFood poderá suspender ou restringir acesso, componente, Credencial ou publicação quando necessário para proteger pessoas, dados, sistemas, terceiros ou o ecossistema, ou diante de suspeita de violação. Salvo em hipóteses de urgência ou risco iminente, o iFood notificará previamente a Desenvolvedora ou Integradora, por meio do Portal ou por e-mail cadastrado, concedendo prazo razoável — não inferior a 5 (cinco) dias úteis — para correção da irregularidade. A notificação conterá descrição sumária do motivo e, quando aplicável, das medidas corretivas esperadas. Na hipótese de risco iminente de dano a pessoas, dados, sistemas ou terceiros, fraude ou violação grave de segurança, o iFood poderá suspender o acesso imediatamente, sem aviso prévio, comunicando o ocorrido em até 48 (quarenta e oito) horas. Os efeitos da suspensão incluem o bloqueio de Credenciais, a indisponibilização de componentes publicados e a restrição de acessos ao ambiente correspondente.

**15.3.** O usuário poderá encerrar cadastro ou componente, devendo revogar acessos, remover dependências, tratar dados e cumprir obrigações de transição, incidentes e auditoria aplicáveis.

**15.4.** O encerramento implicará: (i) revogação imediata de todas as Credenciais; (ii) exclusão ou indisponibilização dos componentes publicados pelo usuário no Portal; (iii) devolução ou exclusão definitiva de Dados Pessoais compartilhados pelo iFood, conforme orientação do iFood e na forma do item 7.8; (iv) manutenção dos logs e registros pelo período definido na política de retenção aplicável; (v) cancelamento de licenças de uso concedidas; e (vi) quitação de eventuais cobranças pendentes. O encerramento não gera direito a indenização, ressarcimento de investimentos ou compensação de qualquer natureza ao usuário, salvo disposição legal em contrário.

**15.5.** Fica desde já certo e ajustado que estas Condições Gerais serão automaticamente rescindidas, sem necessidade de comunicação, nas hipóteses a seguir descritas, sem prejuízo da indenização por perdas e danos: (a) falência ou pedido de recuperação judicial por qualquer das partes; e (b) encerramento das operações de qualquer das partes.

## 16. Responsabilidades, limitações e ausência de garantia

**16.1.** O usuário é responsável por seu cadastro, componentes, conteúdo, ferramentas, Credenciais, dados, dependências, conformidade, segurança, manutenção e atos de seus usuários e contratados, conforme limites da lei e dos contratos aplicáveis.

**16.2.** O iFood não será responsável por danos indiretos, consequenciais, lucros cessantes, perda de dados, interrupção de negócios ou perda de oportunidade decorrentes do uso ou da indisponibilidade do Portal, salvo nos casos de dolo ou culpa grave.

**16.3.** A Desenvolvedora ou Integradora indenizará e manterá o iFood indenizado de quaisquer reclamações, perdas, danos, custas judiciais e administrativas, honorários advocatícios e despesas decorrentes de: (i) descumprimento destas Condições Gerais; (ii) atos ou omissões de seus usuários, funcionários, representantes ou subcontratados; (iii) violação de direitos de terceiros, incluindo Propriedade Intelectual e dados pessoais; e (iv) defeitos, falhas ou inadequações dos Componentes Desenvolvidos.

**16.4.** Salvo nos casos de dolo, culpa grave ou violação de direitos de propriedade intelectual, a responsabilidade do iFood perante o usuário, por eventos decorrentes destas Condições Gerais, será limitada aos danos diretos e comprovados.

**16.5.** Nada nesta seção deverá ser interpretado como renúncia a direitos indisponíveis, exclusão de responsabilidade não permitida ou limitação inválida.

**16.6.** Nenhuma das partes será responsável por descumprimento decorrente de caso fortuito ou força maior, conforme definido na legislação civil aplicável. A parte afetada deverá comunicar a outra por escrito no prazo máximo de 5 (cinco) dias, justificando suas alegações, e manter a outra parte informada diariamente enquanto perdurar o evento. Caso o motivo de força maior ou caso fortuito perdure por mais de 30 (trinta) dias, estas Condições Gerais estarão automaticamente rescindidas de pleno direito.

---



# Páginas adicionais referenciadas pelo llms.txt

Estas páginas estão acessíveis, mas não aparecem no índice atual. Há divergências entre elas e os guias indexados; consulte o relatório de leitura.

## Métodos de Autenticação

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods

# Métodos de Autenticação

Escolha o método correto para seu tipo de aplicação.

---

## Autenticação Nativa (Any2App)

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/any2app

# Autenticação Nativa (Any2App)

Use este método quando seu app nativo (Android/iOS) precisa autenticar usuários que **já têm o app iFood instalado**.

## Quando usar Any2App

**Use Any2App se:**

- Seu app é **nativo** (Android ou iOS)
- Usuário **já tem o app iFood instalado**
- Quer a melhor experiência: uma tela, sem redirecionamento, rápido
- Busca altas taxas de conversão (70-80%)

**Não use se:**

- Usuário pode não ter app iFood instalado
- Seu app é web/híbrido
- Precisa de fallback universal → use [Web Login](/docs/guides/authentication/authentication-methods/web-login)

## Como funciona

O Any2App usa **deep linking** para abrir o app iFood, autenticar, e retornar ao seu app com um código.

```
┌─────────────┐
│ Seu App     │
│ (nativo)    │
└──────┬──────┘
       │
       ├─ 1. Abre deep link
       │   ifood://auth/authorize?...
       │
       ▼
┌─────────────────────────┐
│ App iFood               │
│ (já logado)             │
└──────┬──────────────────┘
       │
       ├─ 2. Usuário confirma
       │   permissões
       │
       ▼
┌─────────────┐
│ Seu App     │
│ (retorno)   │
└──────┬──────┘
       │
       ├─ 3. Recebe
       │   authorization_code
       │
       ▼
┌─────────────┐
│ Seu Backend │
└──────┬──────┘
       │
       ├─ 4. Troca code
       │   por access_token
       │
       ▼
┌─────────────────────────┐
│ iFood Auth Server       │
└─────────────────────────┘
```

## Passo 1: Registrar Custom URL Scheme

### Android

No `AndroidManifest.xml`, registre seu custom scheme:

```
<activity android:name=".AuthCallbackActivity">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />

    <!-- Seu custom scheme -->
    <data android:scheme="meuapp" android:host="callback" />
  </intent-filter>
</activity>
```

Quando iFood retorna, chama: `meuapp://callback?code=AUTH_CODE&state=...`

### iOS

No `Info.plist`, registre seu URL scheme:

```
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>meuapp</string>
    </array>
    <key>CFBundleURLName</key>
    <string>com.meuapp.auth</string>
  </dict>
</array>
```

No `AppDelegate`, capture o callback:

```
func application(
  _ app: UIApplication,
  open url: URL,
  options: [UIApplication.OpenURLOptionsKey: Any] = [:]
) -> Bool {
  // url = meuapp://callback?code=AUTH_CODE&state=...
  if let components = URLComponents(url: url, resolvingAgainstBaseURL: true) {
    if let code = components.queryItems?.first(where: { $0.name == "code" })?.value {
      // Trocar code por token
      exchangeCodeForToken(code: code)
    }
  }
  return true
}
```

## Passo 2: Abrir Deep Link

Construa e abra o deep link do iFood com seus parâmetros:

```
// React Native (Expo)
import * as Linking from 'expo-linking';

const openAny2AppAuth = async () => {
  const state = Math.random().toString(36).substring(7);
  const params = new URLSearchParams({
    client_id: 'YOUR_CLIENT_ID',
    response_type: 'code',
    redirect_uri: 'meuapp://callback',
    scope: 'openid profile email phone',
    state: state
  });

  const deepLink = `ifood://auth/authorize?${params.toString()}`;

  try {
    const canOpen = await Linking.canOpenURL(deepLink);
    if (canOpen) {
      await Linking.openURL(deepLink);
    } else {
      // iFood não instalado → fallback para web login
      console.warn('iFood app not installed, fallback to web login');
    }
  } catch (error) {
    console.error('Failed to open iFood auth:', error);
  }
};
```

**Parâmetros:**

- **`client_id`**: ID da sua aplicação
- **`response_type=code`**: Sempre `code`
- **`redirect_uri=meuapp://callback`**: Custom scheme registrado
- **`scope`**: Escopos solicitados (`openid profile email phone`)
- **`state`**: String aleatória para proteção CSRF

## Passo 3: Capturar Retorno

Quando o usuário confirma no app iFood, retorna para seu app com:

```
meuapp://callback?code=AUTH_CODE_HERE&state=SAME_STATE
```

Capture e valide:

```
// React Native
import { useEffect } from 'react';
import * as Linking from 'expo-linking';

const AuthCallback = () => {
  useEffect(() => {
    const handleDeepLink = async (event) => {
      const url = event.url;
      const parsed = Linking.parse(url);

      const code = parsed.queryParams?.code;
      const state = parsed.queryParams?.state;

      if (code && state) {
        // Validar state (compare com salvo antes)
        const savedState = await getStoredState();
        if (state !== savedState) {
          console.error('State mismatch — CSRF attack?');
          return;
        }

        // Trocar code por token (via seu backend)
        await exchangeCodeForToken(code);
      }
    };

    // Listener para deep links enquanto app está aberto
    const subscription = Linking.addEventListener('url', handleDeepLink);

    // Se app foi aberto por deep link
    const initialUrl = await Linking.getInitialURL();
    if (initialUrl != null) {
      handleDeepLink({ url: initialUrl });
    }

    return () => subscription.remove();
  }, []);

  return <Text>Autenticando...</Text>;
};
```

## Passo 4: Trocar Code por Token

Seu **backend** faz a troca (confira [Token Management](/docs/guides/authentication/implementation/token-management) para mais detalhes):

```
curl -X POST https://auth.ifood.com.br/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE_HERE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=meuapp://callback"
```

## Fallback: O que fazer se iFood não estiver instalado?

Se `Linking.canOpenURL(deepLink)` retorna `false`, o app iFood não está disponível. Implemente fallback:

```
const authenticate = async () => {
  const deepLink = buildAny2AppDeepLink();

  try {
    const canOpen = await Linking.canOpenURL(deepLink);

    if (canOpen) {
      // Any2App: sucesso esperado
      await Linking.openURL(deepLink);
    } else {
      // iFood não instalado → fallback para web login
      console.warn('iFood app not installed, using web login fallback');

      // Abrir webview com web login (veja Web Login docs)
      navigateToWebLogin();
    }
  } catch (error) {
    // Erro ao abrir → fallback
    console.error('Any2App failed:', error);
    navigateToWebLogin();
  }
};
```

## Taxa de Conversão & Performance

| Métrica | Valor |
| --- | --- |
| Taxa de sucesso | 70-80% (app iFood instalado) |
| Tempo de autenticação | < 5 segundos |
| Experiência do usuário | Uma tela, sem redirecionamento |
| Requisito | App iFood instalado |


## Casos de Uso Comuns

### Caso 1: Integração básica em React Native Expo

```
import * as Linking from 'expo-linking';
import AsyncStorage from '@react-native-async-storage/async-storage';

const useAny2AppAuth = () => {
  const authenticate = async () => {
    // Gerar state aleatório
    const state = Math.random().toString(36).substring(7);
    await AsyncStorage.setItem('auth_state', state);

    // Construir deep link
    const params = new URLSearchParams({
      client_id: 'YOUR_CLIENT_ID',
      response_type: 'code',
      redirect_uri: 'meuapp://callback',
      scope: 'openid profile email phone',
      state
    });

    const deepLink = `ifood://auth/authorize?${params.toString()}`;

    try {
      const canOpen = await Linking.canOpenURL(deepLink);
      if (!canOpen) {
        throw new Error('iFood app not installed');
      }
      await Linking.openURL(deepLink);
    } catch (error) {
      console.error('Failed to open iFood auth:', error);
      // Fallback para web login
    }
  };

  return { authenticate };
};
```

### Caso 2: Validar state e trocar code (backend)

```
// Node.js + Express
app.post('/api/auth/callback', async (req, res) => {
  const { code, state } = req.body;

  // Validar state
  const savedState = req.session.state;
  if (state !== savedState) {
    return res.status(400).json({ error: 'Invalid state' });
  }

  try {
    // Trocar code por token
    const tokenResponse = await axios.post('https://auth.ifood.com.br/token', {
      grant_type: 'authorization_code',
      code,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET,
      redirect_uri: 'meuapp://callback'
    });

    const { access_token, refresh_token } = tokenResponse.data;

    // Salvar na sessão
    req.session.accessToken = access_token;
    req.session.refreshToken = refresh_token;

    return res.json({ success: true });
  } catch (error) {
    console.error('Token exchange failed:', error);
    return res.status(500).json({ error: 'Authentication failed' });
  }
});
```

## iOS App Store Risk

attention

**Deep linking deve ter fallback**

Ao usar deep linking com `ifood://`, o app iFood deve estar instalado. Se não estiver, o deep link falha silenciosamente. Sempre implemente fallback para [Web Login](/docs/guides/authentication/authentication-methods/web-login).

Além disso, a App Store pode questionar por que você abre outro app. Explique na revisão:

"Nosso app oferece login com iFood. Se o usuário tem iFood instalado, abrimos para autenticação rápida (sem sair do device). Se não tiver, usamos web login via webview."

Isso geralmente é aprovado sem problemas.

## Anti-Padrões Comuns

### Anti-padrão 1: Não registrar custom scheme

```
// ERRADO
const deepLink = 'ifood://auth/authorize?...';
await Linking.openURL(deepLink); // Retorno fica perdido!
```

**Solução**: Registre `meuapp://callback` no `AndroidManifest.xml` e `Info.plist`.

### Anti-padrão 2: Não validar state

```
// ERRADO
const { code } = parsed.queryParams; // Não checou state!
await exchangeCodeForToken(code); // Vulnerável a CSRF
```

**Solução**: Sempre compare `state` retornado com o salvo antes.

### Anti-padrão 3: Não implementar fallback

```
// ERRADO
await Linking.openURL(deepLink); // E se iFood não tiver instalado?
```

**Solução**: Sempre verifique `canOpenURL()` e implemente fallback para web login.

## Suporte

Dúvidas? Veja [Error Handling](/docs/guides/authentication/implementation/error-handling) ou entre em contato.

---

## Autenticação Aprovada Remotamente (Pending Action)

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/pending-action

# Autenticação Aprovada Remotamente (Pending Action)

Use este método quando a aprovação vem de **outro dispositivo** (out-of-band): TV, totem, kiosk, servidor, AI agent.

## Quando usar Pending Action

**[X] Use Pending Action se:**

- Dispositivo **sem navegador** ou teclado limitado (TV, totem, kiosk)
- Usuário aprova em **outro dispositivo** (smartphone)
- Precisa de **push notification** para pedir confirmação
- Servidor/AI agent precisa de acesso autenticado
- Quer fluxo **sem redirecionamento**

**[ ] Não use se:**

- Usuário autenticando no mesmo dispositivo → use [Web Login](/docs/guides/authentication/authentication-methods/web-login) ou [Any2App](/docs/guides/authentication/authentication-methods/any2app)

## Como funciona

- Seu dispositivo **gera um code** e mostra na tela
- Usuário vê um **QR code ou número**
- Abre app iFood no smartphone e **aprova**
- Seu dispositivo **recebe aprovação** via polling ou webhook
- Troca code por token

```
┌──────────────────┐         ┌────────────────┐
│ TV / Totem       │         │ Smartphone     │
│ (seu app)        │         │ (app iFood)    │
└────────┬─────────┘         └────────┬───────┘
         │                            │
         ├─ 1. Gera code             │
         │   (mostra QR code)        │
         │                            │
         │        ◄─── 2. Lê QR ─────┤
         │                            │
         │                            ├─ 3. Mostra permissões
         │                            │
         │        ◄─── 4. Aprova ─────┤
         │                            │
         ├─ 5. Polling: "aprovado?" │
         │                            │
         ▼                            ▼
Troca code por token
```

## Passo 1: Gerar Pending Action Code

Seu dispositivo solicita um `device_code` e `user_code`:

```
curl -X POST https://auth.ifood.com.br/device/authorize \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "scope=openid profile email"
```

**Resposta:**

```
{
  "device_code": "AH-2a4f-6e9c",
  "user_code": "ABCD-1234",
  "verification_uri": "https://auth.ifood.com.br/device",
  "verification_uri_complete": "https://auth.ifood.com.br/device?user_code=ABCD-1234",
  "expires_in": 1800,
  "interval": 5,
  "qr_code": "data:image/png;base64,iVBORw0KGgo..."
}
```

**Campos importantes:**

- **`device_code`**: Código gerado. Use para polling ou webhook.
- **`user_code`**: Código exibido na tela (ex: "ABCD-1234"). Usuário digita ou escaneia QR.
- **`verification_uri_complete`**: URL com QR code já incluso (para gerar QR dinamicamente).
- **`qr_code`**: QR code em base64 (pronto para exibir na tela).
- **`interval`**: Segundos **mínimos** entre polling requests (5 segundos).
- **`expires_in`**: Tempo até code expirar (1800 segundos = 30 min).

## Passo 2: Exibir QR Code ou User Code

Na tela, exiba **ambos** para máxima usabilidade:

```
┌──────────────────────┐
│  Conecte sua Conta   │
├──────────────────────┤
│                      │
│  ┌────────────────┐  │
│  │                │  │
│  │   [QR CODE]    │  │
│  │                │  │
│  └────────────────┘  │
│                      │
│  OU DIGITE:          │
│  ABCD-1234           │
│                      │
│  Abrindo app iFood...│
│  Aguardando      │
│                      │
└──────────────────────┘
```

## Passo 3: Usuário Aprova no Smartphone

Usuário abre app iFood e:

- 
Lê QR code **OU** digita user code (ABCD-1234)

- 
Vê tela de consentimento:

```
Conecte com TotemApp?

Permissões solicitadas:
[X] Identidade
[X] Email
[X] Perfil

[Aprovar] [Cancelar]
```

- 
Clica **Aprovar** (ou **Cancelar** para rejeitar)

## Passo 4: Polling para Verificar Aprovação

Seu dispositivo faz **polling** a cada `interval` segundos para verificar se foi aprovado:

```
curl -X POST https://auth.ifood.com.br/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
  -d "device_code=AH-2a4f-6e9c" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

**Respostas possíveis:**

**1. Ainda aguardando (código `authorization_pending`):**

```
{
  "error": "authorization_pending",
  "error_description": "Aguardando aprovação do usuário..."
}
```

→ Espere `interval` segundos e tente novamente.

**2. Usuário expirou o code (código `expired_token`):**

```
{
  "error": "expired_token",
  "error_description": "O código expirou. Solicite um novo."
}
```

→ Volte ao Passo 1 e gere um novo code.

**3. Usuário rejeitou (código `access_denied`):**

```
{
  "error": "access_denied",
  "error_description": "Usuário rejeitou a solicitação."
}
```

→ Peça ao usuário para tentar novamente.

**4. Aprovado! (sucesso):**

```
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "REFRESH_TOKEN_HERE"
}
```

→ Use `access_token` para chamar APIs.

## Passo 5: Usar Access Token

Agora você tem acesso:

```
curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
  https://api.ifood.com.br/v1/user
```

## Exemplo: Fluxo Completo (Node.js)

```
const axios = require('axios');

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;

async function authenticateWithPendingAction() {
  try {
    // Passo 1: Gerar device code
    console.log('Gerando device code...');
    const deviceResponse = await axios.post(
      'https://auth.ifood.com.br/device/authorize',
      new URLSearchParams({
        client_id: CLIENT_ID,
        scope: 'openid profile email'
      })
    );

    const { device_code, user_code, qr_code, expires_in, interval } = deviceResponse.data;

    console.log(`[X] Device code gerado`);
    console.log(`  User code: ${user_code}`);
    console.log(`  QR code: ${qr_code.substring(0, 50)}...`);
    console.log(`  Expira em: ${expires_in}s`);

    // Passo 2: Exibir QR code (simulado)
    displayQRCode(qr_code);
    displayUserCode(user_code);

    // Passo 3 & 4: Polling
    console.log('\nAguardando aprovação do usuário...');

    let approved = false;
    let attempts = 0;
    const maxAttempts = Math.floor(expires_in / interval);

    while (!approved && attempts < maxAttempts) {
      // Esperar `interval` segundos
      await new Promise(resolve => setTimeout(resolve, interval * 1000));
      attempts++;

      console.log(`[${attempts}/${maxAttempts}] Verificando...`);

      try {
        const tokenResponse = await axios.post(
          'https://auth.ifood.com.br/token',
          new URLSearchParams({
            grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
            device_code,
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET
          })
        );

        // Aprovado!
        const { access_token, refresh_token } = tokenResponse.data;
        console.log(`[X] Aprovado! Access token obtido.`);

        return { access_token, refresh_token };

      } catch (error) {
        const errorCode = error.response?.data?.error;

        if (errorCode === 'authorization_pending') {
          // Continua polling
          continue;
        } else if (errorCode === 'access_denied') {
          console.error('[ ] Usuário rejeitou a solicitação');
          throw new Error('User denied access');
        } else if (errorCode === 'expired_token') {
          console.error('[ ] Code expirou. Gerando novo...');
          throw new Error('Device code expired');
        } else {
          throw error;
        }
      }
    }

    throw new Error('Polling timeout: usuário não aprovou a tempo');

  } catch (error) {
    console.error('Erro na autenticação:', error.message);
    throw error;
  }
}

function displayQRCode(qrCode) {
  // Em produção: renderizar QR code na tela (TV, totem, etc)
  console.log('QR Code:', qrCode);
}

function displayUserCode(userCode) {
  // Exibir código para digitar manualmente
  console.log(`Código para digitar: ${userCode}`);
}

// Uso
(async () => {
  try {
    const { access_token } = await authenticateWithPendingAction();
    console.log('\n[X] Acesso concedido. Token:', access_token.substring(0, 20) + '...');
  } catch (error) {
    console.error('Falha na autenticação:', error.message);
  }
})();
```

## Otimizações & Boas Práticas

### 1. Webhook em vez de Polling (Opcional)

Se prefere não fazer polling continuado, registre um **webhook**:

```
curl -X POST https://auth.ifood.com.br/device/authorize \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "scope=openid profile email" \
  -d "webhook_uri=https://seuapp.com/auth/callback"
```

Quando aprovado, iFood envia `POST`:

```
{
  "device_code": "AH-2a4f-6e9c",
  "access_token": "eyJ..."
}
```

### 2. Exibir Timer de Expiração

Mostre ao usuário quanto tempo falta:

```
const expiresIn = 1800; // 30 minutos
const startTime = Date.now();

setInterval(() => {
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const remaining = expiresIn - elapsed;

  if (remaining <= 0) {
    console.log('Code expirou');
  } else {
    console.log(`⏱️  Expira em: ${remaining}s`);
  }
}, 1000);
```

### 3. Permitir Rescan de QR Code

Usuário pode escanear novamente se tiver errado:

```
const rescanQRCode = async () => {
  // Gerar novo device code
  const newDeviceResponse = await axios.post(
    'https://auth.ifood.com.br/device/authorize',
    { client_id: CLIENT_ID, scope: 'openid profile email' }
  );

  // Exibir novo QR code
  displayQRCode(newDeviceResponse.data.qr_code);
};
```

## Casos de Uso Reais

### Caso 1: Totem de Pedidos

```
class OrderKiosk {
  async authenticate() {
    const { device_code, qr_code, user_code } = await this.generateDeviceCode();

    // Exibir na tela do totem
    this.screen.displayQRCode(qr_code);
    this.screen.displayUserCode(user_code);
    this.screen.showMessage('Escaneie com seu smartphone iFood');

    // Aguardar aprovação
    const { access_token } = await this.pollForApproval(device_code);

    // Usuário autenticado
    this.screen.showMessage('[X] Bem-vindo!');
    return access_token;
  }
}
```

### Caso 2: Servidor/CLI Integrado

```
# Seu servidor precisa de acesso como aplicação

./auth-cli --device-auth \
  --client-id "APP_ID" \
  --client-secret "APP_SECRET"

# Output:
# Abra no app iFood e aprove:
# ABCD-1234
#
# Aguardando...
# [X] Acesso obtido!
```

### Caso 3: AI Agent Solicitando Permissão

```
# Python: seu AI agent precisa de acesso autenticado

from auth_client import PendingActionAuth

auth = PendingActionAuth(
  client_id="YOUR_CLIENT_ID",
  client_secret="YOUR_CLIENT_SECRET"
)

# Gerar code
device_info = auth.generate_device_code()

# Notificar usuário (ex: via email, push)
notify_user(
  message=f"AI agent pediu acesso. Aprove em: {device_info.verification_uri_complete}"
)

# Aguardar aprovação
token = auth.wait_for_approval(
  device_code=device_info.device_code,
  timeout=1800  # 30 minutos
)

print(f"[X] Acesso concedido ao AI agent: {token.access_token}")
```

## Taxas & Performance

| Métrica | Valor |
| --- | --- |
| Taxa de sucesso | 60-70% (depende de notificação ao usuário) |
| Tempo até aprovação | 30 segundos - 5 minutos (depende do usuário) |
| Timeout máximo | 30 minutos (customizável) |
| Intervalo de polling | Mínimo 5 segundos |


## Anti-Padrões Comuns

### Anti-padrão 1: Não respeitar intervalo mínimo

```
// [ ] ERRADO
while (!approved) {
  checkApproval();  // Polling a cada frame (muito rápido)
}
```

**Solução**: Espere pelo menos `interval` segundos entre requests.

### Anti-padrão 2: Não lidar com expiração

```
// [ ] ERRADO
while (!approved) {
  await checkApproval(device_code);  // Nunca sai do loop se expirou
}
```

**Solução**: Implemente timeout ou máximo de tentativas.

### Anti-padrão 3: Expor device_code no frontend

```
// [ ] ERRADO (React)
const TokenDisplay = ({ device_code }) => (
  <div>Device code: {device_code}</div>  // Expõe no browser!
);
```

**Solução**: Mantenha `device_code` seguro no backend. Envie apenas `user_code` e `qr_code` ao frontend.

## Suporte

Dúvidas? Veja [Error Handling](/docs/guides/authentication/implementation/error-handling) ou entre em contato.

---

## Autenticação Web (Web Login)

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/authentication-methods/web-login

# Autenticação Web (Web Login)

Use este método quando você precisa de um **fallback que funciona em todos os dispositivos**: sem dependência de outros apps, sem deep linking complexo.

## Quando usar Web Login

**[X] Use Web Login se:**

- Seu app é **web/híbrido** (não nativo)
- Precisa de **fallback universal** (sempre funciona)
- Usuário pode **não ter app iFood instalado**
- Quer **máxima compatibilidade** (desktop, tablet, mobile)
- Necessita de **OTP** (autenticação por código)

**[ ] Não use se:**

- App nativo Android/iOS com iFood instalado → use [Any2App](/docs/guides/authentication/authentication-methods/any2app) para melhor UX
- Dispositivo sem navegador → use [Pending Action](/docs/guides/authentication/authentication-methods/pending-action)

## Como funciona

Web Login usa o **fluxo OAuth 2.0 tradicional** com redirecionamento de navegador:

- Usuário clica **"Login com iFood"**
- Redireciona para tela de login iFood
- Escolhe entre **CPF** ou **email**
- Recebe **código de confirmação** (SMS ou email)
- Digita código (OTP)
- Autoriza permissões
- Retorna ao seu app com `access_token`

```
┌─────────────┐
│ Seu App     │
└──────┬──────┘
       │
       ├─ 1. Redireciona
       │   para /authorize
       │
       ▼
┌─────────────────────┐
│ iFood Login Page    │
└──────┬──────────────┘
       │
       ├─ 2. Usuário escolhe
       │   CPF ou email
       │
       ├─ 3. Recebe OTP
       │   (SMS ou email)
       │
       ├─ 4. Digita código
       │
       ├─ 5. Autoriza
       │   permissões
       │
       ▼
┌──────────────────┐
│ Seu App          │
│ (com token)      │
└──────────────────┘
```

## Passo 1: Redirecionar para Authorization Endpoint

Seu frontend constrói e redireciona para o `authorize` endpoint:

```
const redirectToLogin = () => {
  const params = new URLSearchParams({
    client_id: 'YOUR_CLIENT_ID',
    response_type: 'code',
    redirect_uri: 'https://seuapp.com/callback',
    scope: 'openid profile email phone',
    state: Math.random().toString(36).substring(7)
  });

  window.location.href = `https://auth.ifood.com.br/authorize?${params.toString()}`;
};
```

**URL destino:**

```
https://auth.ifood.com.br/authorize?
  client_id=YOUR_CLIENT_ID
  &response_type=code
  &redirect_uri=https://seuapp.com/callback
  &scope=openid%20profile%20email%20phone
  &state=abc123xyz
```

## Passo 2: Usuário Escolhe OTP Method

Na tela de iFood, usuário vê:

```
┌─────────────────────────┐
│ Conecte com iFood       │
├─────────────────────────┤
│                         │
│ Qual sua conta?         │
│                         │
│ [Celular (SMS)]      │
│ [Email]              │
│                         │
│ Insira seu CPF/Email:   │
│ [_______________]       │
│                         │
│ [Continuar]             │
└─────────────────────────┘
```

Usuário escolhe:

- **SMS**: Recebe código no celular (mais rápido)
- **Email**: Recebe código no inbox (mais seguro)

## Passo 3: Receber e Digitar OTP

Após digitar CPF/email, recebe código (exemplo: "256341"):

```
┌─────────────────────────┐
│ Código de Confirmação   │
├─────────────────────────┤
│                         │
│ Enviamos um código para │
│ seu celular: ***7890    │
│                         │
│ Insira o código:        │
│ [_ _ _ _ _ _]           │
│                         │
│ Não recebeu?            │
│ [Reenviar] [Trocar]     │
│                         │
└─────────────────────────┘
```

Digita código de 6 dígitos.

## Passo 4: Autorizar Permissões

Após validar OTP, usuário vê tela de consentimento:

```
┌─────────────────────────┐
│ Sua Conta iFood         │
├─────────────────────────┤
│                         │
│ SeuApp solicita:        │
│ [X] Sua identidade        │
│ [X] Email                 │
│ [X] Telefone              │
│ [X] Endereço              │
│                         │
│ [Autorizar] [Cancelar]  │
│                         │
└─────────────────────────┘
```

Clica **Autorizar** para prosseguir.

## Passo 5: Voltar para Seu App

iFood redireciona para seu `redirect_uri` com `code`:

```
https://seuapp.com/callback?
  code=AUTH_CODE_HERE
  &state=abc123xyz
```

Seu frontend captura e envia o `code` para seu backend.

## Passo 6: Backend Troca Code por Token

Seu **backend** faz a troca (mesmo que outros fluxos):

```
curl -X POST https://auth.ifood.com.br/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE_HERE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://seuapp.com/callback"
```

**Resposta:**

```
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "REFRESH_TOKEN_HERE"
}
```

## Exemplo: Implementação Completa (React)

### Frontend

```
import React from 'react';
import axios from 'axios';

const LoginPage = () => {
  const handleLoginClick = () => {
    // Gerar state aleatório
    const state = Math.random().toString(36).substring(7);
    sessionStorage.setItem('auth_state', state);

    // Construir authorization URL
    const params = new URLSearchParams({
      client_id: process.env.REACT_APP_CLIENT_ID,
      response_type: 'code',
      redirect_uri: `${window.location.origin}/callback`,
      scope: 'openid profile email phone',
      state
    });

    // Redirecionar
    window.location.href = `https://auth.ifood.com.br/authorize?${params.toString()}`;
  };

  return (
    <div>
      <h1>Bem-vindo</h1>
      <button onClick={handleLoginClick}>
        Login com iFood
      </button>
    </div>
  );
};

export default LoginPage;
```

### Callback Handler

```
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const CallbackPage = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      // Extrair parâmetros da URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const state = params.get('state');

      // Validar state
      const savedState = sessionStorage.getItem('auth_state');
      if (state !== savedState) {
        console.error('State mismatch — CSRF attack?');
        navigate('/login');
        return;
      }

      try {
        // Enviar code para backend
        const response = await axios.post('/api/auth/callback', { code });

        // Backend retorna tokens
        const { accessToken, refreshToken } = response.data;

        // Salvar tokens
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        // Redirecionar para dashboard
        navigate('/dashboard');
      } catch (error) {
        console.error('Authentication failed:', error);
        navigate('/login');
      }
    };

    handleCallback();
  }, [navigate]);

  return <div>Autenticando...</div>;
};

export default CallbackPage;
```

### Backend (Node.js)

```
const express = require('express');
const axios = require('axios');
const app = express();

app.post('/api/auth/callback', async (req, res) => {
  const { code } = req.body;

  try {
    // Trocar code por tokens
    const tokenResponse = await axios.post('https://auth.ifood.com.br/token', {
      grant_type: 'authorization_code',
      code,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET,
      redirect_uri: `${process.env.FRONTEND_URL}/callback`
    });

    const { access_token, refresh_token } = tokenResponse.data;

    // Retornar tokens ao frontend
    // (Em produção: usar HttpOnly cookies em vez de retornar ao frontend)
    res.json({
      accessToken: access_token,
      refreshToken: refresh_token
    });
  } catch (error) {
    console.error('Token exchange failed:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

app.listen(3000);
```

## OTP: SMS vs Email

### SMS (Padrão, mais rápido)

**Vantagens:**

- Código recebido em segundos
- Não depende de acesso a email
- Melhor UX para mobile

**Desvantagens:**

- Pode não funcionar em alguns países
- Pode ter custo para o usuário
- Vulnerável a SIM swap

```
Codigo de confirmação enviado para: ***7890
Validade: 5 minutos
```

### Email (Mais seguro)

**Vantagens:**

- Funciona em qualquer país
- Sem custos
- Histórico no inbox

**Desvantagens:**

- Mais lento (inbox pode estar cheio)
- Requer acesso a email

```
Código de confirmação enviado para: u***@gmail.com
Validade: 15 minutos
```

## Anti-Fraude: Proteção Adicional

Se detectar atividade suspeita, iFood pode solicitar verificação adicional:

```
┌──────────────────────────┐
│ Verificação de Segurança │
├──────────────────────────┤
│                          │
│ Detectamos uma tentativa │
│ de acesso incomum.       │
│                          │
│ Confirme sua identidade: │
│ [CPF: ___________]       │
│ [Data nasc: ____]        │
│                          │
│ [Verificar]              │
│                          │
└──────────────────────────┘
```

Isso é **normal** — parte da proteção contra fraudes.

## Casos de Uso Reais

### Caso 1: Web App com React Router

```
// routes.js
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import CallbackPage from './pages/CallbackPage';
import DashboardPage from './pages/DashboardPage';
import ProtectedRoute from './components/ProtectedRoute';

export const AppRoutes = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<CallbackPage />} />
      <Route
        path="/dashboard"
        element={<ProtectedRoute component={DashboardPage} />}
      />
    </Routes>
  </BrowserRouter>
);
```

### Caso 2: Webview em App Híbrido

```
// React Native WebView com Web Login

import { WebView } from 'react-native-webview';

const HybridAuthScreen = ({ onAuthSuccess }) => {
  const handleMessage = (event) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'AUTH_SUCCESS') {
        // Webview enviou token
        onAuthSuccess(data.accessToken);
      }
    } catch (error) {
      console.error('Message parsing failed:', error);
    }
  };

  return (
    <WebView
      source={{ uri: 'https://seuapp.com/login' }}
      onMessage={handleMessage}
    />
  );
};
```

### Caso 3: SPA (Single Page App) com Redirect Storage

```
// Para SPA com redirecionamento, preserve o estado

const handleCallback = async () => {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const returnTo = sessionStorage.getItem('return_to') || '/dashboard';

  try {
    const { accessToken } = await exchange(code);
    localStorage.setItem('access_token', accessToken);

    // Voltar para página original
    navigate(returnTo);
  } catch (error) {
    navigate('/login');
  }
};

const handleLoginClick = (returnTo) => {
  sessionStorage.setItem('return_to', returnTo);
  redirectToAuthorize();
};
```

## Taxa de Conversão & Performance

| Métrica | Valor |
| --- | --- |
| Taxa de sucesso | 80-90% (máxima compatibilidade) |
| Tempo até código OTP | < 10 segundos |
| Tempo total de autenticação | 1-3 minutos |
| Requisito | Navegador + internet |
| Dispositivos suportados | Desktop, tablet, mobile, TV |


## Anti-Padrões Comuns

### Anti-padrão 1: Não validar state

```
// [ ] ERRADO
const code = new URLSearchParams(window.location.search).get('code');
await exchangeCodeForToken(code);  // State não validado!
```

**Solução**: Sempre compare `state` retornado com o salvo.

### Anti-padrão 2: Armazenar tokens no localStorage sem HTTPS

```
// [ ] ERRADO (em produção)
localStorage.setItem('access_token', token);  // HTTP → XSS risk
```

**Solução**: Use HTTPS em produção. Ou use HttpOnly cookies.

### Anti-padrão 3: Não refrescar tokens expirados

```
// [ ] ERRADO
const token = localStorage.getItem('access_token');
await callAPI(token);  // Token pode ter expirado
```

**Solução**: Verifique expiração ou use `refresh_token` (veja [Token Management](/docs/guides/authentication/implementation/token-management)).

## Suporte

Dúvidas sobre OTP, anti-fraude ou callback? Veja [Error Handling](/docs/guides/authentication/implementation/error-handling) ou entre em contato.

---

## Implementação

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation

# Implementação

Gerenciar tokens, lidar com erros e implementar boas práticas de segurança.

---

## Tratamento de Erros

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation/error-handling

# Tratamento de Erros — Diagnóstico e Recuperação

Identifique, diagnostique e recupere-se de erros de autenticação comuns.

## Taxonomia de Erros

Erros podem ocorrer em 3 pontos:

- **No Authorize Endpoint** — Ao redirecionar para login
- **No Token Endpoint** — Ao trocar code por token
- **Na API** — Ao chamar endpoints com access_token

```
┌──────────────────────────────────────────────┐
│ Seu App                                      │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
    AUTHORIZE   TOKEN     API
    ENDPOINT    ENDPOINT  CALL
    (errors)    (errors)  (errors)
```

## Erros no Authorize Endpoint

Quando redireciona o usuário, pode voltar com erro **na URL**:

```
https://seuapp.com/callback?
  error=invalid_scope
  &error_description=Escopo+não+registrado
  &state=abc123
```

### Tabela: Erros de Authorize

| Erro | Causa | Recuperação |
| --- | --- | --- |
| `invalid_scope` | Escopo não registrado | Verificar documentação de escopos válidos |
| `invalid_client` | `client_id` errado | Conferir `client_id` na variável de ambiente |
| `invalid_redirect_uri` | `redirect_uri` não registrada | Registrar URI exata em console do parceiro |
| `access_denied` | Usuário clicou "Cancelar" | Ofertar novo login (link "Tentar novamente") |
| `server_error` | Servidor indisponível | Retry com backoff exponencial |
| `unauthorized_client` | App não autorizada | Contatar suporte |


### Exemplo: Tratamento de Authorize Error

```
// Frontend
const handleCallback = () => {
  const params = new URLSearchParams(window.location.search);

  const error = params.get('error');
  const errorDescription = params.get('error_description');

  if (error) {
    // Houve erro no authorization
    switch (error) {
      case 'invalid_scope':
        showError(`Escopo inválido: ${errorDescription}`);
        console.error('Invalid scope registered in app config');
        break;

      case 'access_denied':
        showError('Você cancelou o login. Tente novamente.');
        setTimeout(() => navigateToLogin(), 2000);
        break;

      case 'server_error':
        showError('Servidor temporariamente indisponível. Tente em alguns segundos.');
        break;

      default:
        showError(`Erro de autenticação: ${errorDescription}`);
        navigateToLogin();
    }
    return;
  }

  // Se chegou aqui, não houve erro
  const code = params.get('code');
  const state = params.get('state');

  // Continuar com troca de token...
};
```

## Erros no Token Endpoint

Quando seu **backend** chama `POST /token`, pode receber erro no JSON:

```
{
  "error": "invalid_code",
  "error_description": "Authorization code has expired"
}
```

### Tabela: Erros de Token

| Erro | Causa | Recuperação |
| --- | --- | --- |
| `invalid_code` | Code expirou ou já foi usado | Redirecionar para novo login |
| `invalid_client` | `client_secret` incorreto | Verificar variável de ambiente |
| `invalid_grant` | Code inválido | Redirecionar para login |
| `unauthorized_client` | App não autorizada para este flow | Contatar suporte |
| `server_error` | Servidor indisponível | Retry com backoff |
| `invalid_request` | Parâmetro faltando | Verificar se enviou `code`, `client_id`, `redirect_uri` |


### Exemplo: Tratamento de Token Error

```
// Backend (Node.js)
app.post('/api/auth/callback', async (req, res) => {
  const { code } = req.body;

  if (!code) {
    return res.status(400).json({
      error: 'missing_code',
      message: 'Authorization code not provided'
    });
  }

  try {
    const tokenResponse = await axios.post(
      'https://auth.ifood.com.br/token',
      {
        grant_type: 'authorization_code',
        code,
        client_id: process.env.CLIENT_ID,
        client_secret: process.env.CLIENT_SECRET,
        redirect_uri: process.env.REDIRECT_URI
      }
    );

    const { access_token, refresh_token } = tokenResponse.data;

    return res.json({
      success: true,
      accessToken: access_token,
      refreshToken: refresh_token
    });

  } catch (error) {
    const errorCode = error.response?.data?.error;
    const errorDescription = error.response?.data?.error_description;

    console.error(`Token error: ${errorCode} — ${errorDescription}`);

    switch (errorCode) {
      case 'invalid_code':
        // Code expirou (após ~10 minutos) ou já foi usado
        return res.status(400).json({
          error: 'invalid_code',
          message: 'Authorization code expired or already used. Please login again.',
          userMessage: 'Sessão expirada. Por favor, faça login novamente.'
        });

      case 'invalid_client':
        // Credenciais erradas — problema na configuração
        return res.status(500).json({
          error: 'invalid_client',
          message: 'Application credentials are incorrect. Contact support.',
          userMessage: 'Erro de configuração. Contate suporte.'
        });

      case 'server_error':
        // Servidor iFood está down
        return res.status(503).json({
          error: 'service_unavailable',
          message: 'Authentication service temporarily unavailable. Retry later.',
          userMessage: 'Serviço temporariamente indisponível. Tente novamente em alguns segundos.'
        });

      default:
        return res.status(500).json({
          error: errorCode,
          message: errorDescription,
          userMessage: 'Erro ao autenticar. Tente novamente.'
        });
    }
  }
});
```

## Erros na Chamada de API

Quando chama uma API protegida com `access_token`, pode falhar:

```
const response = await fetch('https://api.ifood.com.br/v1/user', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});

if (!response.ok) {
  // Erro na API
  const error = await response.json();
  console.error(error);
}
```

### Tabela: Erros de API

| Status | Erro | Causa | Recuperação |
| --- | --- | --- | --- |
| `401` | `invalid_token` | Token expirou | Refrescar com `refresh_token` |
| `401` | `insufficient_scope` | Escopo insuficiente | Solicitar novo login com más escopos |
| `403` | `insufficient_scope` | Não tem permissão | Informar usuário que não tem permissão |
| `404` | `resource_not_found` | Recurso não existe | Verificar ID e retry |
| `429` | `rate_limit_exceeded` | Muitas requisições | Esperar e retry com backoff |
| `500` | `server_error` | Servidor com erro | Retry com backoff |


### Exemplo: Tratamento de API Error

```
// Função auxiliar para chamadas protegidas
const callProtectedAPI = async (endpoint, accessToken, options = {}) => {
  try {
    const response = await fetch(`https://api.ifood.com.br${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      const error = await response.json();
      const statusCode = response.status;

      switch (statusCode) {
        case 401:
          // Token inválido ou expirou
          if (error.error === 'invalid_token') {
            console.log('Token expired, attempting refresh...');
            throw new TokenExpiredError('Token needs refresh');
          }

          if (error.error === 'insufficient_scope') {
            console.log('Insufficient scope for this endpoint');
            throw new InsufficientScopeError(error.error_description);
          }
          break;

        case 403:
          // Não tem permissão
          throw new ForbiddenError(error.error_description);

        case 429:
          // Rate limit
          const retryAfter = response.headers.get('Retry-After') || 60;
          console.warn(`Rate limited. Retry after ${retryAfter}s`);
          throw new RateLimitError(`Retry after ${retryAfter}s`);

        case 500:
          // Server error — retry com backoff
          throw new ServerError('Server error, retry later');

        default:
          throw new APIError(error.error, error.error_description);
      }
    }

    return await response.json();

  } catch (error) {
    // Re-throw com contexto
    console.error(`API call failed: ${error.message}`);
    throw error;
  }
};

// Uso com tratamento de erro
try {
  const user = await callProtectedAPI('/v1/user', accessToken);
} catch (error) {
  if (error instanceof TokenExpiredError) {
    // Refrescar token
    const newToken = await refreshToken();
    // Retry
    const user = await callProtectedAPI('/v1/user', newToken);
  } else if (error instanceof RateLimitError) {
    // Esperar e retry
    await sleep(60000);
    const user = await callProtectedAPI('/v1/user', accessToken);
  } else {
    // Outro erro
    showError(error.message);
  }
}
```

## Padrão: Refresh Token Quando Token Expira

O erro mais comum: **token expirado**. Solução: usar `refresh_token`.

```
// Interceptor para refrescar token automaticamente
class AuthInterceptor {
  constructor(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  async request(endpoint, options) {
    try {
      // Tentar com token atual
      return await this.callAPI(endpoint, this.accessToken, options);
    } catch (error) {
      if (error.status === 401 && error.code === 'invalid_token') {
        // Token expirou — refrescar
        console.log('Token expired, refreshing...');
        await this.refreshAccessToken();

        // Retry com novo token
        return await this.callAPI(endpoint, this.accessToken, options);
      }

      throw error;
    }
  }

  async refreshAccessToken() {
    const response = await axios.post('https://auth.ifood.com.br/token', {
      grant_type: 'refresh_token',
      refresh_token: this.refreshToken,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET
    });

    // Atualizar tokens
    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token || this.refreshToken;

    // Salvar para próximas requisições
    localStorage.setItem('access_token', this.accessToken);
    localStorage.setItem('refresh_token', this.refreshToken);

    console.log('Token refreshed successfully');
  }

  async callAPI(endpoint, token, options) {
    const response = await fetch(`https://api.ifood.com.br${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        ...options.headers
      }
    });

    if (!response.ok) {
      throw {
        status: response.status,
        code: (await response.json()).error,
        message: (await response.json()).error_description
      };
    }

    return await response.json();
  }
}

// Uso
const auth = new AuthInterceptor(accessToken, refreshToken);
const user = await auth.request('/v1/user', {});
// Automáticamete refrescará se token expirou
```

## Stratégia: Backoff Exponencial para Retry

Para erros temporários (rate limit, server error), use backoff:

```
const retryWithBackoff = async (fn, maxAttempts = 3) => {
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Não retry para erros permanentes
      if ([400, 401, 403, 404].includes(error.status)) {
        throw error;
      }

      // Retry para erros temporários
      if (attempt < maxAttempts) {
        const delayMs = Math.pow(2, attempt) * 1000;  // 2s, 4s, 8s
        console.log(`Retry ${attempt}/${maxAttempts} in ${delayMs}ms...`);
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }

  throw lastError;
};

// Uso
const user = await retryWithBackoff(
  () => callAPI('/v1/user', accessToken),
  3  // Máximo 3 tentativas
);
```

## Matrix de Decisão: Qual Ação Tomar?

```
┌─ Recebi resposta de erro
│
├─ Status 4xx (client error)?
│  ├─ 400 (invalid_request) → Verificar parâmetros
│  ├─ 401 (unauthorized/token_expired) → Refrescar token
│  ├─ 403 (insufficient_scope) → Solicitar novo login
│  └─ 404 (not_found) → Verificar ID do recurso
│
├─ Status 429 (rate_limit)? → Backoff exponencial + retry
│
├─ Status 5xx (server error)? → Backoff + retry (máx 3x)
│
└─ Erro genérico? → Log + informar usuário
```

## Checklist: Antes de Produção

Antes de fazer deploy, verificar se:

-  Todos os erros são capturados (try/catch)
-  Não expõe `client_secret` em logs/console
-  Implementou refresh de token
-  Implementou backoff para retry
-  Mensagens de erro são legíveis para usuário
-  Logs contêm suficiente contexto para diagnóstico
-  Testes cobrem casos de erro comuns
-  Validação de parâmetros antes de fazer requisições

## Anti-Padrões Comuns

### Anti-padrão 1: Ignorar erros

```
// [ ] ERRADO
const token = await exchangeCode(code);
// E se deu erro? Silenciosamente falhou!
```

**Solução**: Sempre tratar erros.

```
// [X] CORRETO
try {
  const token = await exchangeCode(code);
} catch (error) {
  console.error('Token exchange failed:', error);
  showError('Erro de autenticação. Tente novamente.');
}
```

### Anti-padrão 2: Retry infinito

```
// [ ] ERRADO
while (true) {
  try {
    await callAPI(endpoint, token);
    break;
  } catch (error) {
    // Retry sem limite!
  }
}
```

**Solução**: Limitar tentativas.

```
// [X] CORRETO
const maxAttempts = 3;
for (let i = 0; i < maxAttempts; i++) {
  try {
    return await callAPI(endpoint, token);
  } catch (error) {
    if (i === maxAttempts - 1) throw error;
    await sleep(Math.pow(2, i) * 1000);
  }
}
```

### Anti-padrão 3: Expor credenciais em erro

```
// [ ] ERRADO
catch (error) {
  console.error(error);  // Pode conter client_secret!
  sendToSentry(error);   // Expõe em logs remotos
}
```

**Solução**: Sanitizar logs.

```
// [X] CORRETO
catch (error) {
  const sanitized = {
    message: error.message,
    code: error.code,
    // NÃO incluir: error.client_secret, etc
  };
  console.error(sanitized);
}
```

## Referência Rápida

| Erro | Ação Imediata | Longo Prazo |
| --- | --- | --- |
| `invalid_code` | Redirecionar para login | — |
| `invalid_client` | Log + contatar suporte | Verificar credenciais |
| `server_error` | Backoff + retry | Monitorar servidor |
| `rate_limit` | Backoff exponencial | Aumentar limite ou cache |
| `invalid_token` | Refrescar token | — |
| `insufficient_scope` | Solicitar novo login | Ajustar escopos |


## Próximos Passos

- [Token Management](/docs/guides/authentication/implementation/token-management) — Refrescar tokens

## Suporte

Erro não listado? Entre em contato conosco com detalhes.

---

## Gerenciamento de Tokens

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/authentication/implementation/token-management

# Gerenciamento de Tokens — Obter, Refrescar e Revogar

Saiba como gerenciar o ciclo de vida dos seus tokens de autenticação.

## Ciclo de Vida do Token

```
┌─ Obter token (via authorization code)
│
├─ Usar em requisições (HTTP header)
│
├─ Token expira (30 min - 1 hora)
│
├─ Refrescar (usando refresh_token)
│
└─ Revogar (fazer logout)
```

## Tipos de Token

### Access Token

- **Propósito**: Autorizar requisições à API
- **Duração**: 1 hora (customizável)
- **Uso**: Header `Authorization: Bearer ACCESS_TOKEN`
- **Segurança**: Guarde com cuidado, expiração curta

```
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Refresh Token

- **Propósito**: Obter novo access_token quando expirar
- **Duração**: Até 30 dias (ou indefinido)
- **Uso**: Apenas no token endpoint (`POST /token`)
- **Segurança**: **NUNCA** exponha ao frontend

```
{
  "refresh_token": "REFRESH_TOKEN_HERE",
  "token_type": "Bearer",
  "expires_in": 2592000
}
```

### ID Token

- **Propósito**: Informações do usuário (JWT decodificável)
- **Duração**: Até 1 hora
- **Uso**: Decodificar para obter claims (`sub`, `name`, `email`)
- **Segurança**: Pode ser armazenado, contém informações públicas

```
// Decodificado, contém:
{
  "sub": "user-uuid",
  "name": "José Silva",
  "email": "jose@example.com",
  "iat": 1234567890,
  "exp": 1234571490
}
```

## Passo 1: Obter Access Token Inicial

### Via Authorization Code (Standard OAuth)

```
POST https://auth.ifood.com.br/token

Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=AUTH_CODE_HERE
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&redirect_uri=https://seuapp.com/callback
```

**Resposta:**

```
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "REFRESH_TOKEN_HERE",
  "id_token": "eyJ..."
}
```

### Exemplo: Node.js

```
const axios = require('axios');

const getInitialToken = async (authorizationCode) => {
  try {
    const response = await axios.post('https://auth.ifood.com.br/token', {
      grant_type: 'authorization_code',
      code: authorizationCode,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET,
      redirect_uri: process.env.REDIRECT_URI
    });

    const { access_token, refresh_token, expires_in } = response.data;

    return {
      accessToken: access_token,
      refreshToken: refresh_token,
      expiresAt: Date.now() + (expires_in * 1000)  // Quando expira
    };
  } catch (error) {
    console.error('Failed to get token:', error.response?.data);
    throw error;
  }
};
```

## Passo 2: Usar Access Token

### No Header da Requisição

```
GET https://api.ifood.com.br/v1/user

Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Exemplo: JavaScript (Fetch)

```
const callProtectedAPI = async (endpoint, accessToken) => {
  const response = await fetch(`https://api.ifood.com.br${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
};

// Uso
const user = await callProtectedAPI('/v1/user', accessToken);
```

### Exemplo: Axios Interceptor

```
const axiosInstance = axios.create({
  baseURL: 'https://api.ifood.com.br'
});

axiosInstance.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem('access_token');
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Uso
const user = await axiosInstance.get('/v1/user');
```

## Passo 3: Refrescar Token Quando Expirar

Quando `access_token` expirar, use `refresh_token` para obter novo:

```
POST https://auth.ifood.com.br/token

Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=REFRESH_TOKEN_HERE
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
```

**Resposta:**

```
{
  "access_token": "NEW_ACCESS_TOKEN_HERE",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "NEW_REFRESH_TOKEN_HERE"
}
```

### Exemplo: Detectar Token Expirado

```
const isTokenExpired = (expiresAt) => {
  // Consideramos expirado 5 minutos antes de fato expirar
  const bufferMs = 5 * 60 * 1000;
  return Date.now() > (expiresAt - bufferMs);
};

const getValidAccessToken = async () => {
  const expiresAt = localStorage.getItem('token_expires_at');

  // Token ainda válido
  if (!isTokenExpired(expiresAt)) {
    return localStorage.getItem('access_token');
  }

  // Token expirou — refrescar
  console.log('Token expired, refreshing...');
  const newToken = await refreshAccessToken();
  return newToken;
};

const refreshAccessToken = async () => {
  try {
    const response = await axios.post('https://auth.ifood.com.br/token', {
      grant_type: 'refresh_token',
      refresh_token: localStorage.getItem('refresh_token'),
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET
    });

    const { access_token, refresh_token, expires_in } = response.data;

    // Salvar novos tokens
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('token_expires_at', Date.now() + (expires_in * 1000));

    console.log('Token refreshed successfully');
    return access_token;

  } catch (error) {
    console.error('Failed to refresh token:', error.response?.data);
    // Refresh falhou — fazer logout
    logout();
    throw error;
  }
};
```

### Exemplo: Automático com Interceptor

```
const createAuthenticatedClient = (initialAccessToken, initialRefreshToken) => {
  let accessToken = initialAccessToken;
  let refreshToken = initialRefreshToken;
  let tokenExpiresAt = Date.now() + (3600 * 1000);

  const refreshAccessToken = async () => {
    try {
      const response = await axios.post('https://auth.ifood.com.br/token', {
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: process.env.CLIENT_ID,
        client_secret: process.env.CLIENT_SECRET
      });

      accessToken = response.data.access_token;
      refreshToken = response.data.refresh_token;
      tokenExpiresAt = Date.now() + (response.data.expires_in * 1000);

      return accessToken;
    } catch (error) {
      console.error('Refresh failed:', error);
      throw error;
    }
  };

  const client = axios.create({
    baseURL: 'https://api.ifood.com.br'
  });

  // Interceptor: verificar token antes de cada request
  client.interceptors.request.use(async (config) => {
    // Refrescar se expirou
    if (Date.now() > (tokenExpiresAt - 5 * 60 * 1000)) {
      accessToken = await refreshAccessToken();
    }

    config.headers.Authorization = `Bearer ${accessToken}`;
    return config;
  });

  // Interceptor de erro: retry se 401
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const config = error.config;

      // Se 401 e não tentou refresh ainda
      if (error.response?.status === 401 && !config._retry) {
        config._retry = true;

        try {
          accessToken = await refreshAccessToken();
          config.headers.Authorization = `Bearer ${accessToken}`;
          return client(config);
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );

  return client;
};

// Uso
const client = createAuthenticatedClient(accessToken, refreshToken);
const user = await client.get('/v1/user');
// Automáticamente refrescará se token expirou
```

## Passo 4: Revogar Token (Logout)

Para fazer logout e invalidar tokens:

```
POST https://auth.ifood.com.br/logout

Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&refresh_token=REFRESH_TOKEN_HERE
```

**Resposta (sucesso):**

```
{
  "success": true
}
```

### Exemplo: Logout Completo

```
const logout = async () => {
  const refreshToken = localStorage.getItem('refresh_token');

  try {
    // Revogar token no servidor
    await axios.post('https://auth.ifood.com.br/logout', {
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET,
      refresh_token: refreshToken
    });

    console.log('Logout successful');
  } catch (error) {
    console.error('Logout failed:', error);
    // Continuar mesmo se falhar (limpar local anyway)
  } finally {
    // Limpar tokens localmente
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expires_at');

    // Redirecionar para home
    window.location.href = '/';
  }
};
```

## Armazenamento Seguro de Tokens

### Frontend: Opção 1 — SessionStorage (Mais Seguro)

```
// Tokens expiram quando fecha navegador
sessionStorage.setItem('access_token', token);
const token = sessionStorage.getItem('access_token');
```

**Vantagens:**

- Limpo automaticamente ao fechar aba
- Não persiste entre sessões
- Protegido contra XSS (HTMLOnly flags ajudam)

**Desvantagens:**

- Usuário faz logout ao fechar navegador

### Frontend: Opção 2 — Memory (Máximo Seguro)

```
let accessToken = null;

const setToken = (token) => {
  accessToken = token;
};

const getToken = () => {
  return accessToken;
};
```

**Vantagens:**

- Nunca persiste em disco
- Máxima proteção contra XSS
- Máxima proteção contra CSRF

**Desvantagens:**

- Perdido ao recarregar página

### Frontend: NÃO use localStorage (Menos Seguro)

```
// [ ] ERRADO
localStorage.setItem('access_token', token);  // Persiste em disco!
// Vulnerável a XSS: script roubando token
```

### Backend: HttpOnly Cookies (Padrão Ouro)

```
// Salvar token em HttpOnly cookie
res.cookie('access_token', accessToken, {
  httpOnly: true,      // JS não pode acessar
  secure: true,        // Apenas HTTPS
  sameSite: 'strict'   // Proteção contra CSRF
});
```

**Vantagens:**

- Automático em cada requisição
- Protegido contra XSS (JS não consegue ler)
- Protegido contra CSRF (SameSite flag)

**Desvantagens:**

- Requer backend setup
- Menos flexível para casos especiais

## Checklist de Segurança

-  **Access token**: Duração curta (1 hora máx)
-  **Refresh token**: Armazenado com segurança (backend cookie ou criptografado)
-  **Nunca exponha `client_secret`** no frontend
-  **HTTPS em produção**: Sem exceção
-  **Refrescar antes de expirar**: Buffer de 5 minutos
-  **Revogar ao logout**: Invalidar tokens no servidor
-  **Validar token no servidor**: Nunca confiar apenas em claims locais
-  **Rotação de refresh token**: Novo refresh_token a cada uso

## Exemplo Completo: Sistema de Autenticação

```
// auth-service.js

class AuthService {
  constructor() {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpiresAt = null;
  }

  async login(authorizationCode) {
    try {
      const response = await axios.post('/api/auth/token', {
        code: authorizationCode
      });

      this.setTokens(response.data);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }

  setTokens(data) {
    this.accessToken = data.accessToken;
    this.refreshToken = data.refreshToken;
    this.tokenExpiresAt = Date.now() + (data.expiresIn * 1000);

    // Salvar para persistência entre recarregos
    sessionStorage.setItem('access_token', this.accessToken);
    sessionStorage.setItem('refresh_token', this.refreshToken);
    sessionStorage.setItem('token_expires_at', this.tokenExpiresAt);
  }

  getAccessToken() {
    if (this.isTokenExpired()) {
      return this.refresh().then(() => this.accessToken);
    }
    return Promise.resolve(this.accessToken);
  }

  isTokenExpired() {
    const buffer = 5 * 60 * 1000;  // 5 minutos
    return Date.now() > (this.tokenExpiresAt - buffer);
  }

  async refresh() {
    try {
      const response = await axios.post('/api/auth/refresh', {
        refreshToken: this.refreshToken
      });

      this.setTokens(response.data);
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  async logout() {
    try {
      await axios.post('/api/auth/logout', {
        refreshToken: this.refreshToken
      });
    } finally {
      this.accessToken = null;
      this.refreshToken = null;
      this.tokenExpiresAt = null;

      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('refresh_token');
      sessionStorage.removeItem('token_expires_at');
    }
  }

  isAuthenticated() {
    return !!this.accessToken && !this.isTokenExpired();
  }
}

// Singleton
export const authService = new AuthService();
```

## Anti-Padrões Comuns

### Anti-padrão 1: Armazenar access_token no localStorage

```
// [ ] ERRADO
localStorage.setItem('access_token', token);
// Vulnerável a XSS — qualquer script rouba o token
```

**Solução**: Usar sessionStorage ou HttpOnly cookies.

### Anti-padrão 2: Não refrescar antes de expirar

```
// [ ] ERRADO
await callAPI(token);  // Token pode ter expirado!
```

**Solução**: Verificar e refrescar antes.

```
// [X] CORRETO
const token = await authService.getAccessToken();
await callAPI(token);  // getAccessToken() automáticamente refrescaif
```

### Anti-padrão 3: Ignorar erro de refresh

```
// [ ] ERRADO
try {
  const newToken = await refreshToken();
} catch (error) {
  // Ignorou erro — vai falhar na próxima API call
  continue;
}
```

**Solução**: Fazer logout ao falhar refresh.

```
// [X] CORRETO
try {
  const newToken = await refreshToken();
} catch (error) {
  logout();  // Refresh falhou — fazer logout
}
```

## Próximos Passos

- [Error Handling](/docs/guides/authentication/implementation/error-handling) — Lidar com erros de token
- [Autenticação](/docs/guides/authentication) — Visão geral e configuração de escopos

## Suporte

Dúvidas sobre tokens? Entre em contato com o time de autenticação.

---

## Homologação e produção

Fonte: https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/validate-publish

# Homologação e produção

Teste seu agente em homologação antes de ativar em produção. Quatro fases: conformidade técnica, testes funcionais, segurança e aprovação final.

## Pré-validação

Certifique-se antes de submeter:

**Código**
[ ] Sem credenciais hardcoded
[ ] Variáveis de ambiente para secrets
[ ] HTTPS em todas as conexões
[ ] Sem código comentado

**Funcionalidade**
[ ] MCPs configurados corretamente
[ ] Tratamento de erros implementado
[ ] Logs apropriados (sem dados sensíveis)
[ ] Performance aceitável

**Testes**
[ ] Testes unitários passando
[ ] Testes de integração passando
[ ] Sucesso em sandbox
[ ] Cobertura adequada

**Documentação**
[ ] README com instruções
[ ] Exemplos funcionando
[ ] APIs documentadas
[ ] Changelog atualizado

## Fases de validação

| Fase | Escopo | Tempo |
| --- | --- | --- |
| Conformidade técnica | Automático, lint, vulnerabilidades | 1-2 dias |
| Testes funcionais | Manual em sandbox, fluxos principais | 2-3 dias |
| Segurança | Análise de código, credenciais, dados | 2-3 dias |
| Aprovação final | iFood interno, ativação em produção | 1 dia |


## Submissão

No Dashboard: **Agentes** > Seu agente > **Submeter para Validação**

Preencha:

- Descrição das mudanças
- Changelog
- Notas para revisor

## Resultados

**Aprovado** — Ativado automaticamente em produção.

**Aprovado com observações** — Aprovado, mas com recomendações futuras.

**Rejeição** — Relatório detalhado fornecido. Corrija e resubmita.

Você recebe email de confirmação e acompanha status no Dashboard.

---

