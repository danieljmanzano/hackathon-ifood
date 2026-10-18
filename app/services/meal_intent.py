"""Intenções de refeição em português por regras locais, sem alterar o contrato MCP."""
import re
from dataclasses import dataclass

from app.schemas.macro import MealCandidate, MealIntent, MealRequest
from app.services.review_processing import normalized
from app.services.nutrition_preferences import extract_preferences, merge_preferences, preference_labels

LABELS = {
    'large_portion': 'porções maiores', 'small_portion': 'porções menores',
    'light': 'refeição leve', 'cheap': 'economia', 'fast': 'entrega rápida',
    'protein': 'opções com fontes de proteína', 'comfort': 'comida caseira',
    'indulgent': 'uma refeição para sair da rotina', 'vegetarian': 'opções vegetarianas',
}
RULES = {
    'large_portion': r'muita fome|morrendo de fome|(?:to|estou) famint[oa]|fome (?:enorme|grande)|porc(?:ao|oes) (?:grande[s]?|generosa[s]?)|bem servido|comer bastante',
    'small_portion': r'pouca fome|sem (?:muita )?fome|nao (?:estou|to) com (?:muita )?fome|lanche leve|lanchinho|porc(?:ao|oes) pequena[s]?|so (?:um )?lanchinho|beliscar',
    'light': r'(?:algo|comida|refeicao|prato|lanche) leve|leve|saudavel|saudaveis|pouco oleo|sem (?:muita )?gordura|nao (?:muito )?pesad[oa]',
    'cheap': r'economizar|barat[oa]|baratinh[oa]|sem gastar muito|pouca grana|preco baixo|bom custo.beneficio|em conta',
    'fast': r'(?:estou |to )?com pressa|tenho pressa|(?:estou|to) apressad[oa]|urgente|entrega rapida|cheg(?:ue|ar) rapido|o mais rapido possivel|nao (?:posso|quero) esperar',
    'protein': r'pos.?treino|depois (?:do|de) treino|apos (?:o )?treino|proteina[s]?|protein[ao]|proteic[oa]',
    'comfort': r'comida (?:caseira|de casa|afetiva)|sabor de casa|comida que abraca',
    'indulgent': r'cheat meal|dia do lixo|sair da dieta|matar a vontade|comer uma besteira',
    'vegetarian': r'vegetarian[oa]|sem carne',
}
STOPWORDS = {
    'quero', 'pedir', 'uma', 'um', 'prato', 'refeicao', 'para', 'hoje', 'perto', 'mim', 'reais',
    'estou', 'to', 'com', 'muita', 'muito', 'fome', 'algo', 'opcao', 'opcoes', 'comer',
    'por', 'favor', 'que', 'tem', 'tenho', 'ate', 'so', 'mas', 'preciso', 'gostaria',
    'de', 'do', 'da', 'dos', 'das', 'no', 'na', 'eu', 'me', 'e', 'o', 'a', 'agora',
}


# Pedidos de novidade: o usuário quer algo que ainda não viu (não repetir os já mostrados e variar os tipos).
VARIEDADE = (r'\b(?:diferentes?|outr[oa]s?|variad[oa]s?|variedade|novidades?|mais opcoes|algo novo|'
             r'nenhum desses|nenhuma dessas|nao quero (?:esses?|essas?|isso))\b')


# Pediu para o assistente montar o pedido. Vale também quando o modelo da interpretação falha (as regras assumem).
MONTAR_PEDIDO = (r'(?:^|\b(?:pode|poderia|consegue|por favor|quero que|voce)\W+(?:voce\W+)?)\W*mont(?:e|a|ar)\b(?!\s+(?:o\s+)?(?:seu|sua)\b)'
                 r'|\b(?:faca|faz|fazer)\b.{0,30}\b(?:pedido|prato|lanche|sanduiche|combo|marmita)\b'
                 r'|\b(?:pegue|pega|escolha|escolhe)\b.{0,60}\b(?:coloque|ponha|bota|com muit[ao])\b')


def parse_intent(request: MealRequest) -> MealIntent:
    text = normalized(request.text)
    pede_variedade = bool(re.search(VARIEDADE, text))
    working, nutritional = extract_preferences(text)
    nutritional = merge_preferences(nutritional, request.nutrition_preferences)
    budget = request.budget_cents
    money = r'(?:ate\s*(?:r\$\s*)?|r\$\s*|(?:tenho|gastar)\s+)(\d+)(?:[,.](\d{1,2}))?(?:\s*reais)?|(\d+)(?:[,.](\d{1,2}))?\s*reais'
    money_text = working
    for match in list(re.finditer(money, money_text)):
        # "até 30 minutos" e "para 2 pessoas" não são valores em reais.
        if re.match(r'\s*(?:minutos?|min\b|pessoas?|kcal|calorias|g\b|gramas)', money_text[match.end():]):
            continue
        if budget is None:
            budget = int(match[1] or match[3]) * 100 + int((match[2] or match[4] or '0').ljust(2, '0'))
        working = working.replace(match[0], ' ')
    goals = []
    inferred_goals = []
    inferences = []
    hits = []
    for goal, pattern in RULES.items():
        for match in re.finditer(r'\b(?:' + pattern + r')\b', working):
            prefix = re.split(r'[.,;!?]', working[:match.start()])[-1]
            negated = re.search(r'\b(?:nao|sem)(?:\s+\w+){0,2}\s+$', prefix)
            if not negated:
                hits.append((goal, match.start(), match[0]))
    # A última indicação explícita de apetite prevalece; "pouca fome" não vira "muita fome".
    appetite = [h for h in hits if h[0] in ('large_portion', 'small_portion')]
    if appetite:
        goals.append(max(appetite, key=lambda h: h[1])[0])
    for goal, _, phrase in hits:
        if goal not in ('large_portion', 'small_portion') and goal not in goals:
            goals.append(goal)
    for _, _, phrase in sorted(hits, key=lambda h: -len(h[2])):
        working = working.replace(phrase, ' ')
    # Remover negações conhecidas sem deixar "pressa" virar um alimento na busca.
    working = re.sub(r'\b(?:nao (?:estou|to) com pressa|sem pressa|nao quero (?:algo |comida |refeicao )?leve)\b', ' ', working)
    delivery = re.search(r'\b(?:em |entrega em |cheg(?:ue|ar) em )?(?:ate )?(\d+)\s*(?:minutos?|min\b)', working)
    max_delivery = None
    activity_timing = bool(re.search(r'\b(?:treinar|treino|academia|musculacao)\b', text)) and not bool(re.search(r'\b(?:entrega|chegue|chegar|pressa)\b', text))
    if delivery and activity_timing:
        working = working.replace(delivery[0], ' ')
    if delivery and not activity_timing and 0 < int(delivery[1]) <= 240:
        max_delivery = int(delivery[1])
        if 'fast' not in goals:
            goals.append('fast')
        working = working.replace(delivery[0], ' ')
    party_size = None
    party = re.search(r'\b(?:para|pra)\s+(\d+|duas|dois|tres|quatro)\s*(?:pessoas?)?\b', working)
    if party:
        value = {'duas': 2, 'dois': 2, 'tres': 3, 'quatro': 4}.get(party[1])
        party_size = value if value is not None else int(party[1])
        if not 1 <= party_size <= 20:
            party_size = None
        working = working.replace(party[0], ' ')
    sharing = re.search(r'\b(?:para|pra) (?:dividir|compartilhar)\b', working)
    if sharing:
        party_size = party_size or 2
        working = working.replace(sharing[0], ' ')
    pre_training = bool(re.search(r'\b(?:pre.?treino|vou treinar|antes de treinar)\b', text))
    post_training = bool(re.search(r'\b(?:treinei(?: musculacao)?(?: hoje)?|acabei de treinar|saindo da academia)\b', text))
    explicit_appetite = any(g in goals for g in ('large_portion', 'small_portion'))
    suggested = ['light'] + ([] if explicit_appetite else ['small_portion']) if pre_training else ['protein'] + ([] if explicit_appetite else ['large_portion']) if post_training else []
    for goal in suggested:
        if goal not in goals:
            goals.append(goal)
            inferred_goals.append(goal)
    if suggested:
        inferences.append('O contexto de treino foi usado para sugerir o estilo e o tamanho da refeição, sem assumir uma necessidade nutricional.')
        working = re.sub(r'\b(?:pre.?treino|vou treinar|antes de treinar|treinei(?: musculacao)?(?: hoje)?|acabei de treinar|saindo da academia|daqui|pouco)\b', ' ', working)
    if pede_variedade:  # "diferente", "variadas"... descrevem o pedido, não a comida
        working = re.sub(VARIEDADE + r'|\b(?:mostre|mostra|me)\b', ' ', working)
    words = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', working)
    food_query = ' '.join(w for w in words if w not in STOPWORDS and len(w) > 1)
    labels = [LABELS[goal] for goal in goals] + preference_labels(nutritional)
    if party_size:
        labels.append(f'comida para {party_size} pessoas')
    if max_delivery:
        labels.append(f'previsão de entrega de até {max_delivery} minutos')
    defaults = {'large_portion': 'refeição porção grande', 'small_portion': 'lanche',
                'light': 'salada grelhado', 'cheap': 'marmita', 'fast': 'refeição',
                'protein': 'frango grelhado', 'comfort': 'comida caseira',
                'indulgent': 'hambúrguer pizza', 'vegetarian': 'vegetariano'}
    return MealIntent(goals=goals, party_size=party_size, max_delivery_minutes=max_delivery,
                      food_query=food_query, provider_query=food_query or defaults.get(goals[0] if goals else '', 'refeição'),
                      budget_cents=budget, labels=labels, inferred_goals=inferred_goals, inferences=inferences,
                      nutrition_preferences=nutritional, avoid_repeats=pede_variedade,
                      montar_pedido=bool(re.search(MONTAR_PEDIDO, text)))


@dataclass
class IntentFit:
    score: float
    reasons: list[str]
    limitations: list[str]


def assess_intent(candidate: MealCandidate, intent: MealIntent) -> IntentFit:
    f = candidate.features
    score, reasons, limitations = 0.0, [], []
    for goal in intent.goals:
        if goal in ('large_portion', 'small_portion'):
            size = f.portion_size
            large = goal == 'large_portion'
            matches = size in ('large', 'sharing') if large else size == 'small'
            if matches:
                score += 2
                detail = f' ({f.weight_grams} g no catálogo)' if f.weight_grams else ''
                introduction = ('Pelo contexto que você descreveu, priorizamos este tamanho de porção' if goal in intent.inferred_goals
                                else f'Você disse que está com {"muita" if large else "pouca"} fome')
                reasons.append(f'{introduction}: esta opção tem porção {"grande" if large else "pequena"}{detail}.')
            elif size is None:
                limitations.append('O tamanho da porção não foi informado; confirme com o restaurante.')
            else:
                score -= 1
                limitations.append('O tamanho desta porção não corresponde ao apetite informado.')
        elif goal == 'cheap':
            # Faixas de preço permitem variar pratos econômicos sem prender a busca ao mesmo mais barato.
            score += 1 if candidate.price_cents <= 2500 else 0.5 if candidate.price_cents <= 3500 else -0.5
            reasons.append('Você quer economizar: demos mais peso às opções de menor preço.')
        elif goal == 'fast':
            if f.eta_max_minutes is not None:
                target = intent.max_delivery_minutes or 30
                score += 1 if f.eta_max_minutes <= target else max(-1, (target - f.eta_max_minutes) / 30)
                reasons.append(f'Você tem pressa: a previsão máxima informada é de {f.eta_max_minutes} minutos.')
                if f.eta_max_minutes > target:
                    limitations.append('A previsão informada ultrapassa o prazo desejado.')
            else:
                limitations.append('A previsão de entrega não está disponível para comparar a rapidez.')
        else:
            if goal in f.tags:
                score += 1
                reasons.append({
                    'light': 'Você pediu algo leve: esta opção está marcada como leve no catálogo.',
                    'protein': 'Para seu pedido, priorizamos opções com fontes de proteína indicadas no catálogo.',
                    'comfort': 'Você quer comida caseira: esta opção corresponde a esse estilo.',
                    'indulgent': 'Você quer sair da rotina: esta opção corresponde a esse tipo de refeição.',
                    'vegetarian': 'Você pediu uma opção vegetariana: este prato está identificado assim no catálogo. Confirme os ingredientes com o restaurante.',
                }[goal])
            else:
                limitations.append(f'Não há indicação no catálogo de que esta opção atenda a: {LABELS[goal]}.')
    if intent.party_size:
        if f.serves is not None:
            if f.serves >= intent.party_size:
                score += 2
                reasons.append(f'O catálogo informa que esta opção serve {f.serves} pessoas; você pediu para {intent.party_size}.')
            else:
                score -= 2
                limitations.append(f'Esta opção serve {f.serves} pessoa(s), abaixo das {intent.party_size} solicitadas.')
        else:
            limitations.append('O número de pessoas atendidas por esta porção não foi informado.')
    return IntentFit(score, reasons, list(dict.fromkeys(limitations)))
