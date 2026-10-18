"""Alterações explícitas de preferências: interpretação opcional por LLM, validação e patch atômico."""
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from app.core.exceptions import AppError
from app.schemas.macro import Model, NutritionPreferences, PendingPreferenceUpdate, UserProfile
from app.services.nutrition_preferences import LIMIT_SPECS, NAMES, PATTERNS, extract_preferences, preference_labels
from app.services.review_processing import normalized
from app.skills import preferencias

NUMERIC = {f'nutrition_preferences.{field}' for field,_,_,_ in LIMIT_SPECS}
LISTS = {'preferences','dislikes','restrictions','nutrition_preferences.goals'}
DAILY = {'daily_calorie_goal':'calories','diet_plan.daily_protein_g':'protein_g',
         'diet_plan.daily_carbs_g':'carbs_g','diet_plan.daily_fat_g':'fat_g'}
FIELDS = NUMERIC | LISTS | set(DAILY) | {'default_budget_cents','diet_plan.goal','diet_plan.details'}
VERBS = r'salve|salvar|guarde|guardar|registre|registrar|atualize|atualizar|mude|mudar|altere|alterar|defina|definir|ajuste|ajustar|remova|remover|retire|retirar|tire|tirar|adicione|adicionar|inclua|incluir|coloque|colocar|limpe|limpar|apague|apagar|esqueca|esquecer|substitua|substituir|troque|trocar'
PREFIX = rf'^(?:por favor[, ]*)?(?:(?:quero que voce|quero|pode|voce pode|gostaria que voce|preciso que voce)\s+)?(?:{VERBS})\b'
SCOPE = r'(?:meu|minha)\s+(?:minim[oa]|maxim[oa])|preferencias?|perfil|metas?|objetivo|limites?|orcamento|restricoes|alergias|(?:ingredientes?|alimentos?|coisas) (?:que|preferidos|favoritos)|gostos?'
PERSISTENT = r'\b(?:de agora em diante|daqui (?:para|pra) frente|a partir de agora|nas proximas sugestoes|sempre|passe a evitar|passe a preferir)\b'
PERSONAL = r'\b(?:gosto de|nao como|prefiro evitar|nao quero mais|sou alergic[oa]|tenho alergia|sou intolerante)\b'
REMOVE = r'\b(?:remov\w*|retir\w*|tire|tirar|limp\w*|apag\w*|esquec\w*|desativ\w*|nao quero mais)\b'


def command_kind(text):
    value=normalized(text)
    if not (re.search(SCOPE,value) or re.search(PERSISTENT,value) or re.search(PERSONAL,value)):
        return None
    if re.match(rf'^(?:por favor[, ]*)?nao\s+(?:quero que (?:voce )?)?(?:{VERBS})\b',value):
        return 'deny'
    if re.match(r'^(?:como|onde|qual|posso)\b',value):
        return 'help'
    if re.search(PREFIX,value) and re.search(r'\b(?:se|caso|quando) (?:eu|voce)\b',value):
        return 'help'
    # O formato da frase não é autorização: os demais casos são classificados pelo agente.
    return 'edit' if re.search(PREFIX,value) else 'interpret'


class Change(Model):
    field: str = Field(description="Campo editável: "+", ".join(sorted(FIELDS)))
    action: Literal['set','add','remove','clear']
    value: str | float | list[str] | None = None
    evidence: str = Field(min_length=1,max_length=2000)

    @field_validator('field')
    @classmethod
    def allowed_field(cls,value):
        if value not in FIELDS:
            raise ValueError('Campo não editável')
        return value

    @field_validator('value',mode='before')
    @classmethod
    def not_bool(cls,value):
        if isinstance(value,bool):
            raise ValueError('Booleano não é valor nutricional')
        return value


class Proposal(Model):
    intent: Literal['update','search','clarify'] = 'update'
    changes: list[Change] = Field(default_factory=list,max_length=24)
    clarification: str = Field(default='',max_length=400)


@dataclass
class Update:
    profile: UserProfile
    message: str
    pending: PendingPreferenceUpdate | None = None


def preference_reply(message):
    value=normalized(message).strip(' .!,?')
    if re.fullmatch(r'sim|sim[, ]+(?:pode salvar|salve|quero)|pode (?:salvar|registrar|guardar)|salve(?: isso)?|confirmo(?: a preferencia)?',value):
        return 'confirm'
    if re.fullmatch(r'nao|nao[, ]+obrigad[oa]|nao (?:salve|quero salvar)|cancele|cancelar|deixa(?: pra la)?|so (?:hoje|nesta refeicao)',value):
        return 'cancel'
    return None


def ingredient_declaration(message):
    text=normalized(message)
    match=re.fullmatch(r'(?:eu )?(gosto de|nao gosto de|nao como|prefiro evitar)\s+([^.!?;]+)[.!?]?',text)
    if not match or re.search(r'\d|\b(?:hoje|mas|somente|apenas|nao|gosto|prefiro|salve|nas|meu|minha)\b',match[2]):
        return None
    values=[v.strip() for v in re.split(r',|\s+e\s+',match[2]) if v.strip()]
    if not values:
        return None
    field='preferences' if match[1]=='gosto de' else 'dislikes'
    return Proposal(changes=[Change(field=field,action='add',value=values,evidence=message)])


def local_proposal(message,profile):
    text=normalized(message)
    declaration=ingredient_declaration(re.sub(r'^salve nas minhas preferencias:\s*','',text))
    changes=list(declaration.changes) if declaration else []
    # Uma meta diária nunca vira um limite por prato.
    daily=bool(re.search(r'diari|por dia|/dia',text))
    clean,nutrients=extract_preferences(message) if not daily else (text,NutritionPreferences())
    if daily and not re.search(REMOVE,text):
        for field,metric in DAILY.items():
            pattern = (r'(\d+(?:[.,]\d+)?)\s*(?:kcal|calorias)' if metric=='calories' else
                       rf'(\d+(?:[.,]\d+)?)\s*g(?:ramas)?\s*(?:de\s+)?(?:{NAMES[metric]})')
            match=re.search(pattern,text)
            if match:
                changes.append(Change(field=field,action='set',value=float(match[1].replace(',','.')),evidence=message))
    from app.services.diet_context import split_daily_message
    diet_goal=split_daily_message(message)[2]
    if diet_goal and re.search(r'objetivo|meta',text) and not re.search(REMOVE,text):
        changes.append(Change(field='diet_plan.goal',action='set',value=diet_goal,evidence=message))
    # Forma local comum: "adicione frango e legumes aos ingredientes que gosto".
    ingredients=re.search(r'(?:adicione|adicionar|inclua|incluir|coloque|colocar|remova|remover|retire|retirar|tire|tirar)\s+(.+?)\s+(?:aos?|nas?|nos?|da|dos|das)\s+(?:meus? |minhas? )?((?:ingredientes?|alimentos?|coisas|restricoes|alergias).*)',text)
    if ingredients and not re.search(r'\d',ingredients[1]):
        values=[v.strip() for v in re.split(r',|\s+e\s+',ingredients[1]) if v.strip()]
        category=ingredients[2]
        field=('restrictions' if re.search(r'restricoes|alergias',category) else
               'dislikes' if re.search(r'evit|nao gosto|nao como',category) else
               'preferences' if re.search(r'gosto|favoritos|preferidos',category) else None)
        if field:
            changes.append(Change(field=field,action='remove' if re.search(REMOVE,text) else 'add',value=values,evidence=message))
    if re.search(REMOVE,text):
        removing_goals=[g for g,pattern in PATTERNS.items() if re.search(pattern,text)]
        if removing_goals and not daily and not re.search(r'\b(?:limites?|minim[oa]|maxim[oa]|metas?)\b',text):
            changes.append(Change(field='nutrition_preferences.goals',action='remove',value=removing_goals,evidence=message))
            return Proposal(changes=changes)
        for metric,pattern in NAMES.items():
            if not re.search(r'\b(?:'+pattern+r')\b',text):
                continue
            if daily:
                field=next(field for field,m in DAILY.items() if m==metric)
                changes.append(Change(field=field,action='clear',evidence=message))
                continue
            fields=[field for field,m,_,_ in LIMIT_SPECS if m==metric]
            direction='min_' if re.search(r'\bminim[oa]',text) else 'max_' if re.search(r'\bmaxim[oa]',text) else None
            chosen=[f for f in fields if (f.startswith(direction) if direction else getattr(profile.nutrition_preferences,f) is not None)]
            if len(chosen)!=1:
                return Proposal(clarification='Qual limite você quer remover: o mínimo ou o máximo?')
            changes.append(Change(field='nutrition_preferences.'+chosen[0],action='clear',evidence=message))
        for goal,pattern in PATTERNS.items():
            if not daily and re.search(pattern,text):
                changes.append(Change(field='nutrition_preferences.goals',action='remove',value=[goal],evidence=message))
    else:
        for field,_,_,_ in LIMIT_SPECS:
            value=getattr(nutrients,field)
            if value is not None:
                changes.append(Change(field='nutrition_preferences.'+field,action='set',value=value,evidence=message))
        if nutrients.goals:
            changes.append(Change(field='nutrition_preferences.goals',action='add',value=nutrients.goals,evidence=message))
    return Proposal(changes=changes)


def validate_and_apply(profile,message,proposal,*,interpreted_update=False):
    kind=command_kind(message)
    if kind != 'edit' and not (kind=='interpret' and interpreted_update and proposal.intent=='update'):
        raise ValueError('Pedido explícito de alteração necessário')
    data=profile.model_dump()
    text=normalized(message)
    _,grounded=extract_preferences(message)
    descriptions=[]
    for change in proposal.changes:
        evidence=normalized(change.evidence)
        if evidence not in text:
            raise ValueError('Alteração sem evidência na mensagem')
        field,action,value=change.field,change.action,change.value
        if action in ('clear','remove') and not re.search(REMOVE,text):
            raise ValueError('Remoção não solicitada')
        if field in NUMERIC:
            if re.search(r'diari|por dia|/dia',evidence) and not re.search(r'por prato|por refeicao',evidence):
                raise ValueError('Meta diária não é limite por prato')
            name=field.split('.')[-1]
            if action=='set':
                if not isinstance(value,(float,int)) or getattr(grounded,name)!=value:
                    raise ValueError('Limite não informado explicitamente')
            elif action=='clear':
                metric=next(m for f,m,_,_ in LIMIT_SPECS if f==name)
                if not re.search(NAMES[metric],evidence):
                    raise ValueError('Remoção sem nutriente identificado')
                lower='min_' if re.search(r'\bminim[oa]',evidence) else 'max_' if re.search(r'\bmaxim[oa]',evidence) else None
                candidates=[f for f,m,_,_ in LIMIT_SPECS if m==metric and getattr(profile.nutrition_preferences,f) is not None]
                if (lower and not name.startswith(lower)) or (not lower and candidates!=[name]):
                    raise ValueError('Limite ambíguo')
            else:
                raise ValueError('Operação nutricional inválida')
        elif field in DAILY:
            metric=DAILY[field]
            if not re.search(NAMES[metric],evidence):
                raise ValueError('Nutriente diário não identificado')
            unit=r'(?:kcal|calorias)' if metric=='calories' else r'g(?:ramas)?'
            if 'diari' not in evidence and not re.search(r'por dia|/dia',evidence):
                raise ValueError('Meta diária não explícita')
            if action=='set':
                if not isinstance(value,(float,int)) or not re.search(NAMES[metric],evidence):
                    raise ValueError('Meta não fundamentada')
                number=re.escape(f'{value:g}').replace(r'\.',r'[.,]')
                if not re.search(r'(?<![\d.,])'+number+r'\s*'+unit+r'\b',evidence):
                    raise ValueError('Valor da meta não informado')
        elif field=='default_budget_cents':
            if not re.search(r'orcamento|preco|gastar|gasto',evidence):
                raise ValueError('Orçamento não solicitado')
            if action=='set':
                from app.services.meal_intent import parse_intent
                from app.schemas.macro import MealRequest
                if not isinstance(value,(int,float)) or value!=parse_intent(MealRequest(text=message)).budget_cents:
                    raise ValueError('Orçamento não informado')
                value=int(value)
        elif field=='diet_plan.goal':
            if not re.search(r'objetivo|meta',evidence):
                raise ValueError('Objetivo não solicitado')
            if action=='set':
                from app.services.diet_context import split_daily_message
                if split_daily_message(message)[2]!=value:
                    raise ValueError('Objetivo não informado')
        elif field=='diet_plan.details':
            if not re.search(r'orientac|detalhes|plano|dieta',evidence):
                raise ValueError('Orientação não solicitada')
            if action=='set':
                if not isinstance(value,str) or normalized(value) not in text:
                    raise ValueError('Orientação não informada')
        if field in LISTS:
            categories={'preferences':r'(?<!nao )\bgosto\b|gostar|preferidos|favoritos',
                        'dislikes':r'evit|nao gosto|nao como|prefiro sem',
                        'restrictions':r'restricoes|alergi|intoleran'}
            if field in categories and not re.search(categories[field],evidence):
                # Remoção genérica do perfil só resolve uma categoria já cadastrada, sem adivinhar.
                unique_removal = action=='remove' and isinstance(value,list) and bool(value) and re.search(r'preferencias?|perfil',evidence)
                if not unique_removal or any(
                    [key for key in categories if normalized(v) in {normalized(x) for x in getattr(profile,key)}] != [field]
                    for v in value
                ):
                    raise ValueError('Categoria de ingrediente não solicitada')
            if action!='clear' and (not isinstance(value,list) or not all(isinstance(v,str) for v in value)):
                raise ValueError('Lista inválida')
            if field=='nutrition_preferences.goals':
                if action!='clear' and any(v not in PATTERNS or not re.search(PATTERNS[v],text) for v in value):
                    raise ValueError('Preferência não mencionada')
            elif action!='clear' and any(not v.strip() or normalized(v) not in text for v in value):
                raise ValueError('Ingrediente não mencionado')
            if action=='clear':
                # Limpar todas as listas não é inferido de um pedido genérico.
                labels={'preferences':r'ingredientes? (?:que (?:eu )?gosto|preferidos|favoritos)',
                        'dislikes':r'(?:ingredientes?|alimentos?).*(?:evit|nao gosto)',
                        'restrictions':r'restricoes|alergias','nutrition_preferences.goals':r'preferencias nutricionais'}
                if not re.search(labels[field],evidence):
                    raise ValueError('Lista a limpar não identificada')
        parts=field.split('.')
        container=data if len(parts)==1 else data[parts[0]]
        key=parts[-1]
        if field in LISTS:
            current=container[key]
            if action=='set' and not re.search(r'\b(?:substitu\w*|troqu\w*|somente|apenas|so)\b',text):
                action='add'
            if action=='clear':
                container[key]=[]
            elif action=='remove':
                container[key]=[v for v in current if normalized(v) not in {normalized(v) for v in value}]
            elif action=='add':
                for v in value:
                    if normalized(v) not in {normalized(x) for x in current}:
                        current.append(v)
            else:
                container[key]=value
        elif action=='clear':
            container[key]='' if field=='diet_plan.details' else None
        elif action=='set':
            container[key]=value
        else:
            raise ValueError('Operação inválida')
        descriptions.append(field)
    return UserProfile.model_validate(data),descriptions


async def interpret_update(message,profile,settings,*,pending=None,messages=()):
    confirmed=bool(pending and preference_reply(message)=='confirm')
    confirmed_declaration=ingredient_declaration(pending.source_message) if confirmed else None
    if pending and preference_reply(message)=='cancel':
        return Update(profile,'Alteração de preferências cancelada. Suas preferências foram mantidas.')
    if confirmed:
        # A autorização vem da resposta atual; os valores vêm apenas do pedido pendente.
        message='Salve nas minhas preferências: '+pending.source_message
    elif pending:
        # A decisão é do backend: o LLM nunca pode transformar uma resposta ambígua em consentimento.
        return Update(profile,'Não recebi uma confirmação afirmativa. Suas preferências foram mantidas. Responda “sim” para salvar a alteração pendente ou “não” para cancelar.',pending)
    kind=command_kind(message)
    if kind is None:
        return None
    if kind=='deny':
        return Update(profile,'Suas preferências foram mantidas. Pedidos de uma refeição não alteram seu perfil.')
    if kind=='help':
        return Update(profile,'Você pode abrir Preferências ou pedir: “salve nas minhas preferências pelo menos 30 g de proteína”. Os limites e ingredientes são opcionais.')
    declaration=ingredient_declaration(message) if kind=='interpret' else None
    if declaration:
        change=declaration.changes[0]
        category='gosta' if change.field=='preferences' else 'prefere evitar'
        return Update(profile,f'Você gostaria de salvar {", ".join(change.value)} como ingrediente(s) que {category}? Responda “sim” para salvar ou “não” para cancelar.',PendingPreferenceUpdate(source_message=message))
    try:
        proposal=confirmed_declaration or local_proposal(message,profile)
        # O agente interpreta ingredientes, metas e pedidos mais variados. Não recebe IDs nem dados de compra.
        if confirmed_declaration is None and settings.intent_llm_enabled and (settings.llm_api_key or settings.openrouter_api_key):
            from app.services.llm_texto import chat_completion_fallback
            from app.services.nutrition.entrada import extrair_json
            raw=await asyncio.wait_for(chat_completion_fallback(
                [{'role':'system','content':preferencias.CONTEUDO+'\nSchema JSON:\n'+json.dumps(Proposal.model_json_schema(),ensure_ascii=False)},
                 {'role':'user','content':json.dumps({'message':message,'current_preferences':{
                     key:value for key,value in profile.model_dump().items()
                     if key in {'preferences','dislikes','restrictions','nutrition_preferences','diet_plan','daily_calorie_goal','default_budget_cents'}
                 },'recent_messages':[{'role':m.role,'text':m.text[:300]} for m in messages[-6:]]},ensure_ascii=False)}],
                settings=settings,preferido=settings.nutrition_provider,json_mode=True,temperature=0,max_tokens=800,
                prazo_primeiro=4,log_content=False),timeout=10)
            # A intenção é obrigatória para frases que não eram comandos locais explícitos.
            parsed=extrair_json(raw)
            if kind=='interpret' and 'intent' not in parsed:
                return Update(profile,'Você quer salvar essa mudança nas suas preferências ou usá-la apenas nesta refeição? Nada foi alterado.',PendingPreferenceUpdate(source_message=message))
            proposal=Proposal.model_validate(parsed)
        elif kind=='interpret':
            # Relatos de objetivo/consumo continuam no fluxo existente de contexto diário.
            if re.search(r'\bobjetivo\b',normalized(message)) and not re.search(
                r'preferencias?|perfil|limites?|minim[oa]|maxim[oa]|'+PERSISTENT,normalized(message)
            ):
                return None
            return Update(profile,'Você quer salvar essa mudança nas suas preferências? Nada foi alterado.',PendingPreferenceUpdate(source_message=message))
        if proposal.intent=='search':
            if confirmed:
                return Update(profile,'Não consegui resolver a alteração pendente. Suas preferências foram mantidas; informe novamente o ingrediente ou limite que deseja salvar.',pending)
            return None
        if proposal.intent=='clarify':
            return Update(profile,proposal.clarification or 'Você quer salvar essa mudança nas suas preferências ou usá-la apenas nesta refeição? Nada foi alterado.',PendingPreferenceUpdate(source_message=message))
        if proposal.clarification or not proposal.changes:
            return Update(profile,proposal.clarification or 'Qual preferência você quer salvar? Informe o ingrediente ou o limite, com mínimo/máximo e unidade. Nada foi alterado.',PendingPreferenceUpdate(source_message=message))
        updated,fields=validate_and_apply(profile,message,proposal,interpreted_update=kind=='interpret')
        nutrient_labels=preference_labels(updated.nutrition_preferences)
        other=[]
        labels={'daily_calorie_goal':('Meta diária de calorias','kcal'),
                'diet_plan.daily_protein_g':('Meta diária de proteína','g'),
                'diet_plan.daily_carbs_g':('Meta diária de carboidratos','g'),
                'diet_plan.daily_fat_g':('Meta diária de gordura','g')}
        for field in fields:
            if field=='diet_plan.goal':
                from app.services.diet_context import GOAL_LABELS
                other.append('Objetivo: '+(GOAL_LABELS.get(updated.diet_plan.goal) or 'não definido'))
            if field=='default_budget_cents':
                other.append('Orçamento: '+(f'R$ {updated.default_budget_cents/100:.2f}' if updated.default_budget_cents is not None else 'não definido'))
            if field in labels:
                label,unit=labels[field]
                value=getattr(updated,field) if '.' not in field else getattr(updated.diet_plan,field.split('.')[-1])
                other.append(f'{label}: {value:g} {unit}' if value is not None else f'{label}: não definida')
        summary=' Preferências nutricionais atuais: '+', '.join(nutrient_labels)+'.' if nutrient_labels else ''
        lists=[]
        if any(f in fields for f in ('preferences','dislikes','restrictions')):
            for field,label in [('preferences','Ingredientes que gosta'),('dislikes','Prefere evitar'),('restrictions','Restrições')]:
                if field in fields:
                    lists.append(label+': '+(', '.join(getattr(updated,field)) or 'nenhum'))
        return Update(updated,'Preferências salvas para as próximas sugestões.'+summary+(' '+'. '.join([*lists,*other])+'.' if lists or other else ''))
    except (ValueError,ValidationError,AppError,asyncio.TimeoutError):
        return Update(profile,'Não consegui aplicar essa alteração com segurança: confira mínimo/máximo, unidades e ingredientes. Suas preferências foram mantidas; você também pode usar o painel Preferências.',pending if confirmed else None)
