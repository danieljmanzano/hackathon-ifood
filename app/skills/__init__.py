"""Skills: TODOS os textos que o sistema envia a modelos de linguagem, um arquivo por skill.

Cada arquivo diz no cabeçalho quem o usa, qual modelo o recebe, o que entra e o que sai, e guarda o texto
(instruções, schema de resposta e a forma como o pedido é montado). Para mudar o que o modelo lê, mude AQUI;
o código das etapas só chama estas funções.

Para ver os textos finais, já montados com dados de exemplo:  python -m scripts.mostrar_prompts

Pipeline de calorias (ordem em que as skills entram):
  item_pedido            descreve o prato (usada por todas as de nutrição)
  nutricao_bases         juiz: o alimento da TACO é este prato?
  nutricao_web           pesquisa na web (tabela oficial ou estimativa pesquisada)
  nutricao_juiz_web      juiz: a tabela achada é do mesmo produto?
  nutricao_estimativa    estimar kcal e macros (A: texto · B: Gemini + foto)
  nutricao_ingredientes  decompor em ingredientes e casar com a TACO
Busca:
  busca_intencao         entender o pedido (com a hora local) e planejar as consultas ao iFood
  busca_replanejar       a busca não achou nada: tentar outra estratégia ou explicar ao usuário
Agente:
  agente_pedidos         papel do agente · agente_ifood_mcp  como usar o MCP do iFood
"""
from . import (agente_ifood_mcp, agente_pedidos, busca_intencao, busca_replanejar, item_pedido, nutricao_bases, nutricao_estimativa,
               nutricao_ingredientes, nutricao_juiz_web, nutricao_web)

SKILLS = {
    "item_pedido": item_pedido,
    "nutricao_bases": nutricao_bases,
    "nutricao_web": nutricao_web,
    "nutricao_juiz_web": nutricao_juiz_web,
    "nutricao_estimativa": nutricao_estimativa,
    "nutricao_ingredientes": nutricao_ingredientes,
    "busca_intencao": busca_intencao,
    "busca_replanejar": busca_replanejar,
    "agente_pedidos": agente_pedidos,
    "agente_ifood_mcp": agente_ifood_mcp,
}

# Skills que o agente pode ativar pelo nome (ask_llm(..., skills=["ifood_mcp"])).
AGENTE = {agente_ifood_mcp.NOME: agente_ifood_mcp}
