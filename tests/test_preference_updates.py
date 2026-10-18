import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings,get_settings
from app.schemas.macro import MealRequest,NutritionPreferences,UserProfile
from app.services.nutrition_preferences import extract_preferences,meets_explicit_limits
from app.services.preference_updates import Change,Proposal,command_kind,interpret_update,validate_and_apply
from tests.test_nutrition_batch_search import nutrition


@pytest.fixture
def client(tmp_path,monkeypatch):
    import app.main as main
    from fastapi.testclient import TestClient
    s=Settings(_env_file=None,ifood_mode='mock',intent_llm_enabled=False,review_llm_enabled=False,
               openai_api_key='',openrouter_api_key='',gemini_api_key='',
               database_path=tmp_path/'prefs.sqlite3',calorias_base_path=tmp_path/'nutri.json')
    monkeypatch.setattr(main,'get_settings',lambda:s)
    app=main.create_app()
    app.dependency_overrides[get_settings]=lambda:s
    with TestClient(app) as c:
        c.get('/api/session')
        yield c


def test_empty_preferences_do_not_create_numeric_targets():
    profile=UserProfile(id='u')
    assert all(v is None for k,v in profile.nutrition_preferences.model_dump().items() if k!='goals')
    assert profile.daily_calorie_goal is None
    assert profile.diet_plan.daily_protein_g is None


@pytest.mark.parametrize('text,expected',[
    ('frango pelo menos 300 kcal',{'min_calories':300}),
    ('frango até 50 g de proteína',{'max_protein_g':50}),
    ('frango no mínimo 30 g de carboidratos',{'min_carbs_g':30}),
    ('frango pelo menos 5 g de gordura',{'min_fat_g':5}),
    ('frango entre 20 e 40 g de proteína',{'min_protein_g':20,'max_protein_g':40}),
    ('frango proteína entre 20 e 40 g',{'min_protein_g':20,'max_protein_g':40}),
    ('mude meu mínimo de proteína para 35 g',{'min_protein_g':35}),
])
def test_nutrition_range_parsing(text,expected):
    _,p=extract_preferences(text)
    for key,value in expected.items():
        assert getattr(p,key)==value


def test_range_validation_and_explicit_filtering():
    for low,high in [('min_calories','max_calories'),('min_protein_g','max_protein_g'),
                     ('min_carbs_g','max_carbs_g'),('min_fat_g','max_fat_g')]:
        with pytest.raises(ValidationError):
            NutritionPreferences(**{low:50,high:20})
    assert meets_explicit_limits(nutrition(400,40),NutritionPreferences(min_calories=500)) is False
    assert meets_explicit_limits(nutrition(400,40),NutritionPreferences(max_protein_g=35)) is False
    assert meets_explicit_limits(nutrition(400,40),NutritionPreferences(min_carbs_g=40)) is False
    assert meets_explicit_limits(nutrition(400,40),NutritionPreferences(min_fat_g=15)) is False


def test_explicit_save_is_persisted_without_address_or_search(client):
    text='Salve nas minhas preferências entre 20 e 40 g de proteína e até 600 kcal'
    r=client.post('/api/chat',json={'text':text})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['last_chat_action']=='preferences'
    p=data['profile']['nutrition_preferences']
    assert p['min_protein_g']==20 and p['max_protein_g']==40 and p['max_calories']==600
    assert p['min_calories'] is None and p['min_carbs_g'] is None
    assert data['address'] is None and data['recommendations']==[] and data['order'] is None
    assert client.get('/api/session').json()['profile']['nutrition_preferences']==p
    assert 'salvas' in data['messages'][-1]['text']


def test_transient_search_does_not_persist_its_nutrition_values(client):
    client.put('/api/session/address',json={'address_id':'demo-address'})
    r=client.post('/api/chat',json={'text':'quero frango até 700 kcal'})
    assert r.status_code==200
    assert r.json()['last_chat_action']=='search'
    assert r.json()['profile']['nutrition_preferences']['max_calories'] is None
    assert r.json()['request_intent']['nutrition_preferences']['max_calories']==700


def test_ingredient_commands_add_and_remove_without_clearing_other_preferences(client):
    first=client.post('/api/chat',json={'text':'Adicione frango e legumes aos ingredientes que gosto'}).json()
    assert first['profile']['preferences']==['frango','legumes']
    second=client.post('/api/chat',json={'text':'Adicione cebola aos ingredientes que prefiro evitar'}).json()
    assert second['profile']['dislikes']==['cebola'] and second['profile']['restrictions']==[]
    third=client.post('/api/chat',json={'text':'Remova frango dos ingredientes que gosto'}).json()
    assert third['profile']['preferences']==['legumes'] and third['profile']['dislikes']==['cebola']


def test_conflicting_update_is_atomic_and_clear_is_explicit(client):
    client.post('/api/chat',json={'text':'Salve nas minhas preferências entre 20 e 40 g de proteína'})
    before=client.get('/api/session').json()['profile']
    failed=client.post('/api/chat',json={'text':'Mude meu mínimo de proteína para 50 g'}).json()
    assert failed['profile']==before and 'mantidas' in failed['messages'][-1]['text']
    cleared=client.post('/api/chat',json={'text':'Remova meu máximo de proteína'}).json()
    assert cleared['profile']['nutrition_preferences']['max_protein_g'] is None
    assert cleared['profile']['nutrition_preferences']['min_protein_g']==20


@pytest.mark.parametrize('text',[
    'Não salve minhas preferências de proteína',
    'Como alterar minhas preferências de proteína?',
    'Salve minhas preferências de proteína quando eu pedir',
])
def test_denials_questions_and_conditionals_do_not_mutate_profile(client,text):
    before=client.get('/api/session').json()['profile']
    r=client.post('/api/chat',json={'text':text})
    assert r.status_code==200
    assert r.json()['profile']==before
    assert r.json()['last_chat_action']=='preferences'


def test_daily_goal_is_not_a_per_dish_limit(client):
    r=client.post('/api/chat',json={'text':'Salve minha meta diária de 140 g de proteína e 2000 kcal'}).json()
    assert r['profile']['diet_plan']['daily_protein_g']==140
    assert r['profile']['daily_calorie_goal']==2000
    assert not any(v is not None for k,v in r['profile']['nutrition_preferences'].items() if k!='goals')
    assert r['profile']['nutrition_preferences']['goals']==[]


def test_llm_proposal_is_grounded_and_cannot_invent_values(monkeypatch):
    from app.services import llm_texto
    settings=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    message='Salve nas minhas preferências até 600 kcal'
    response={'changes':[{'field':'nutrition_preferences.max_calories','action':'set','value':600,'evidence':message}], 'clarification':''}
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',AsyncMock(return_value=json.dumps(response)))
    profile=UserProfile(id='u',dislikes=['cebola'])
    result=asyncio.run(interpret_update(message,profile,settings))
    assert result.profile.nutrition_preferences.max_calories==600
    assert result.profile.dislikes==['cebola']
    response['changes'].append({'field':'nutrition_preferences.min_protein_g','action':'set','value':100,'evidence':message})
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',AsyncMock(return_value=json.dumps(response)))
    result=asyncio.run(interpret_update(message,profile,settings))
    assert result.profile==profile
    assert 'mantidas' in result.message
    with pytest.raises(ValidationError):
        Change(field='id',action='set',value='other',evidence=message)


def test_agent_is_not_called_for_ordinary_searches(monkeypatch):
    from app.services import llm_texto
    llm=AsyncMock()
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',llm)
    s=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    assert asyncio.run(interpret_update('quero frango até 500 kcal',UserProfile(id='u'),s)) is None
    llm.assert_not_called()


def test_per_meal_override_conflicts_return_422_and_do_not_mutate_profile(client):
    client.post('/api/chat',json={'text':'Salve nas minhas preferências entre 500 e 700 kcal'})
    before=client.get('/api/session').json()['profile']
    client.put('/api/session/address',json={'address_id':'demo-address'})
    r=client.post('/api/search',json={'text':'quero frango até 400 kcal'})
    assert r.status_code==422
    assert client.get('/api/session').json()['profile']==before


def test_wrong_units_and_unmentioned_changes_are_rejected():
    _,prefs=extract_preferences('proteína entre 20 e 40 kcal')
    assert prefs.min_protein_g is None and prefs.max_protein_g is None
    message='Salve nas minhas preferências até 600 kcal'
    profile=UserProfile(id='u',default_budget_cents=5000)
    bad=Proposal(changes=[Change(field='default_budget_cents',action='clear',evidence=message)])
    with pytest.raises(ValueError):
        validate_and_apply(profile,message,bad)
    bad=Proposal(changes=[Change(field='nutrition_preferences.max_calories',action='set',value=600,evidence='até 600 kcal')])
    with pytest.raises(ValueError):
        validate_and_apply(profile,'quero frango até 600 kcal',bad)
    assert profile.default_budget_cents==5000


def test_daily_removal_and_subjective_removal_do_not_clear_other_fields(client):
    client.post('/api/chat',json={'text':'Salve minha meta diária de 140 g de proteína'})
    client.post('/api/chat',json={'text':'Salve nas minhas preferências pelo menos 30 g de proteína e pouca gordura'})
    changed=client.post('/api/chat',json={'text':'Remova minha meta diária de proteína'}).json()
    assert changed['profile']['diet_plan']['daily_protein_g'] is None
    assert changed['profile']['nutrition_preferences']['min_protein_g']==30
    changed=client.post('/api/chat',json={'text':'Remova minha preferência por pouca gordura'}).json()
    assert changed['profile']['nutrition_preferences']['goals']==[]
    assert changed['profile']['nutrition_preferences']['min_protein_g']==30


def test_profile_update_survives_application_restart(client):
    response=client.post('/api/chat',json={'text':'Salve nas minhas preferências entre 20 e 40 g de proteína'}).json()
    from app.storage.database import Database
    db=Database(client.app.state.settings.database_path)
    restored=db.get(response['id'])
    assert restored.profile.nutrition_preferences.min_protein_g==20
    assert restored.profile.nutrition_preferences.max_protein_g==40


def test_existing_purchase_state_is_preserved_when_preferences_change(client):
    from tests.test_review_endpoint import checkout,confirm
    _,version=checkout(client)
    confirm(client,version)
    before=client.get('/api/session').json()
    after=client.post('/api/chat',json={'text':'Salve nas minhas preferências até 600 kcal'}).json()
    assert after['order']==before['order'] and after['summary']==before['summary']
    assert after['profile']['nutrition_preferences']['max_calories']==600


@pytest.mark.parametrize('message,field,action,value',[
    ('Queria que você colocasse frango nos ingredientes que gosto','preferences','add',['frango']),
    ('De agora em diante prefiro evitar cebola','dislikes','add',['cebola']),
    ('Meu limite de calorias agora é 600 kcal','nutrition_preferences.max_calories','set',600),
    ('Não quero mais cebola nas minhas preferências','preferences','remove',['cebola']),
])
def test_agent_understands_natural_profile_edits(monkeypatch,message,field,action,value):
    from app.services import llm_texto
    profile=UserProfile(id='u',preferences=['cebola','legumes'])
    response={'intent':'update','changes':[{'field':field,'action':action,'value':value,'evidence':message}]}
    llm=AsyncMock(return_value=json.dumps(response))
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',llm)
    settings=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    result=asyncio.run(interpret_update(message,profile,settings))
    assert result is not None and 'salvas' in result.message
    data=result.profile.model_dump()
    actual=data[field] if '.' not in field else data[field.split('.')[0]][field.split('.')[1]]
    if action=='add':
        assert all(v in actual for v in value)
    elif action=='remove':
        assert actual==['legumes']
    else:
        assert actual==value
    sent=json.loads(llm.call_args.args[0][1]['content'])
    assert sent['current_preferences']['preferences']==['cebola','legumes']
    assert 'id' not in sent['current_preferences']


@pytest.mark.parametrize('intent,message',[
    ('search','Prefiro evitar cebola hoje'),
    ('clarify','Gosto de frango'),
])
def test_semantic_classification_never_saves_transient_or_ambiguous_preferences(monkeypatch,intent,message):
    from app.services import llm_texto
    # Mesmo com operações indevidas na resposta, a classificação não autoriza persistência.
    response={'intent':intent,'clarification':'Quer salvar para as próximas sugestões?',
              'changes':[{'field':'preferences','action':'add','value':['frango'],'evidence':message}]}
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',AsyncMock(return_value=json.dumps(response)))
    settings=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    profile=UserProfile(id='u')
    result=asyncio.run(interpret_update(message,profile,settings))
    assert result is None if intent=='search' else result.profile==profile
    assert profile.preferences==[]


def test_natural_edit_requires_semantic_authorization_and_grounded_numbers(monkeypatch):
    from app.services import llm_texto
    message='Meu limite de calorias agora é 600 kcal'
    change=Change(field='nutrition_preferences.max_calories',action='set',value=600,evidence=message)
    profile=UserProfile(id='u')
    with pytest.raises(ValueError):
        validate_and_apply(profile,message,Proposal(changes=[change]))
    settings=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    for response in [
        {'changes':[change.model_dump()]},
        {'intent':'update','changes':[{**change.model_dump(),'value':900}]},
    ]:
        monkeypatch.setattr(llm_texto,'chat_completion_fallback',AsyncMock(return_value=json.dumps(response)))
        result=asyncio.run(interpret_update(message,profile,settings))
        assert result.profile==profile


def test_generic_ingredient_removal_does_not_guess_between_lists():
    profile=UserProfile(id='u',preferences=['cebola'],dislikes=['cebola'])
    message='Não quero mais cebola nas minhas preferências'
    proposal=Proposal(intent='update',changes=[Change(field='preferences',action='remove',value=['cebola'],evidence=message)])
    with pytest.raises(ValueError):
        validate_and_apply(profile,message,proposal,interpreted_update=True)


def test_semantic_update_is_persisted_by_chat_without_search(client,monkeypatch):
    from app.services import llm_texto
    message='De agora em diante prefiro evitar cebola'
    settings=client.app.state.settings.model_copy(update={'intent_llm_enabled':True,'openrouter_api_key':'test'})
    client.app.dependency_overrides[get_settings]=lambda:settings
    response={'intent':'update','changes':[{'field':'dislikes','action':'add','value':['cebola'],'evidence':message}]}
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',AsyncMock(return_value=json.dumps(response)))
    result=client.post('/api/chat',json={'text':message})
    assert result.status_code==200
    data=result.json()
    assert data['last_chat_action']=='preferences'
    assert data['profile']['dislikes']==['cebola'] and data['profile']['restrictions']==[]
    assert data['recommendations']==[] and data['order'] is None
    assert client.get('/api/session').json()['profile']['dislikes']==['cebola']


def test_confirmation_saves_pending_ingredient_without_search(client):
    before=client.get('/api/session').json()
    question=client.post('/api/chat',json={'text':'gosto de frango'}).json()
    assert question['profile']==before['profile']
    assert question['pending_preference_update']['source_message']=='gosto de frango'
    confirmed=client.post('/api/chat',json={'text':'sim'}).json()
    assert confirmed['last_chat_action']=='preferences'
    assert confirmed['profile']['preferences']==['frango']
    assert confirmed['pending_preference_update'] is None
    assert confirmed['recommendations']==[] and confirmed['request_intent'] is None
    assert confirmed['messages'][-2]['text']=='sim'
    assert 'salvas' in confirmed['messages'][-1]['text']
    assert client.get('/api/session').json()['profile']['preferences']==['frango']


@pytest.mark.parametrize('reply',['não','não salve','cancele','só hoje'])
def test_negative_reply_cancels_pending_preference_without_search(client,reply):
    client.post('/api/chat',json={'text':'gosto de frango'})
    result=client.post('/api/chat',json={'text':reply}).json()
    assert result['last_chat_action']=='preferences'
    assert result['profile']['preferences']==[]
    assert result['pending_preference_update'] is None
    assert result['recommendations']==[] and result['request_intent'] is None


def test_unconfirmed_message_keeps_pending_and_panel_save_discards_it(client):
    client.post('/api/chat',json={'text':'gosto de frango'})
    result=client.post('/api/chat',json={'text':'só comi frutas hoje'}).json()
    assert result['last_chat_action']=='preferences'
    assert result['pending_preference_update'] is not None
    assert result['profile']['preferences']==[]
    profile=client.get('/api/session').json()['profile']
    profile['preferences']=['legumes']
    updated=client.put('/api/profile',json=profile).json()
    assert updated['pending_preference_update'] is None
    assert updated['profile']['preferences']==['legumes']


def test_pending_confirmation_survives_reload_and_preserves_purchase(client):
    from tests.test_review_endpoint import checkout,confirm
    _,version=checkout(client)
    confirm(client,version)
    before=client.get('/api/session').json()
    client.post('/api/chat',json={'text':'gosto de frango'})
    from app.storage.database import Database
    restored=Database(client.app.state.settings.database_path).get(before['id'])
    assert restored.pending_preference_update.source_message=='gosto de frango'
    confirmed=client.post('/api/chat',json={'text':'pode salvar'}).json()
    assert confirmed['order']==before['order'] and confirmed['summary']==before['summary']
    assert confirmed['profile']['preferences']==['frango']
    assert confirmed['last_chat_action']=='preferences'


def test_agent_receives_recent_history_and_confirmation_context(monkeypatch):
    from app.services import llm_texto
    from app.schemas.macro import Message
    profile=UserProfile(id='u')
    message='Minha preferência é até 600 kcal'
    responses=[
        json.dumps({'intent':'clarify','changes':[],'clarification':'Quer salvar até 600 kcal por prato?'}),
        json.dumps({'intent':'update','changes':[{'field':'nutrition_preferences.max_calories','action':'set','value':600,
                    'evidence':'até 600 kcal'}]}),
    ]
    llm=AsyncMock(side_effect=responses)
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',llm)
    settings=Settings(_env_file=None,intent_llm_enabled=True,openrouter_api_key='test')
    first=asyncio.run(interpret_update(message,profile,settings))
    assert first.pending is not None and first.profile==profile
    history=[Message(role='user',text=message),Message(role='assistant',text=first.message)]
    second=asyncio.run(interpret_update('sim',profile,settings,pending=first.pending,messages=history))
    assert second.profile.nutrition_preferences.max_calories==600 and second.pending is None
    sent=json.loads(llm.call_args.args[0][1]['content'])
    assert sent['recent_messages'][0]['text']==message
    assert 'Salve nas minhas preferências:' in sent['message']


def test_confirmation_uses_only_pending_nutritional_values(client):
    first=client.post('/api/chat',json={'text':'Minha preferência é até 600 kcal'}).json()
    assert first['profile']['nutrition_preferences']['max_calories'] is None
    assert first['pending_preference_update'] is not None
    confirmed=client.post('/api/chat',json={'text':'sim'}).json()
    assert confirmed['last_chat_action']=='preferences'
    assert confirmed['profile']['nutrition_preferences']['max_calories']==600
    assert confirmed['profile']['nutrition_preferences']['min_protein_g'] is None
    assert confirmed['request_intent'] is None


@pytest.mark.parametrize('reply',[
    'talvez','ok','isso','isso mesmo','acho que sim','sim, mas não salve',
    'não sei','quero emagrecer','salve nas minhas preferências até 400 kcal',
])
def test_pending_preference_requires_affirmative_reply_even_if_agent_would_save(client,monkeypatch,reply):
    from app.services import llm_texto
    client.post('/api/chat',json={'text':'gosto de frango'})
    before=client.get('/api/session').json()
    settings=client.app.state.settings.model_copy(update={'intent_llm_enabled':True,'openrouter_api_key':'test'})
    client.app.dependency_overrides[get_settings]=lambda:settings
    llm=AsyncMock(side_effect=AssertionError('Não consultar o agente sem confirmação'))
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',llm)
    response=client.post('/api/chat',json={'text':reply})
    assert response.status_code==200
    result=response.json()
    assert result['profile']==before['profile']
    assert result['pending_preference_update']==before['pending_preference_update']
    assert result['request_intent']==before['request_intent']
    assert result['order']==before['order']
    assert result['last_chat_action']=='preferences'
    llm.assert_not_called()


@pytest.mark.parametrize('message,expected',[
    ('nao gosto de peixe',['peixe']),
    ('Não gosto de peixe e camarão.',['peixe','camarao']),
    ('Eu não como peixe',['peixe']),
    ('Prefiro evitar peixe',['peixe']),
])
def test_confirmed_dislike_is_saved_without_reinterpreting_as_removal_or_allergy(client,monkeypatch,message,expected):
    from app.services import llm_texto
    before=client.get('/api/session').json()['profile']
    question=client.post('/api/chat',json={'text':message}).json()
    assert question['profile']==before
    assert question['pending_preference_update']['source_message']==message
    # A confirmação funciona inclusive com LLM configurado, mas indisponível.
    settings=client.app.state.settings.model_copy(update={'intent_llm_enabled':True,'openrouter_api_key':'test'})
    client.app.dependency_overrides[get_settings]=lambda:settings
    llm=AsyncMock(side_effect=AssertionError('Declaração confirmada não precisa ser reinterpretada'))
    monkeypatch.setattr(llm_texto,'chat_completion_fallback',llm)
    confirmed=client.post('/api/chat',json={'text':'sim'}).json()
    assert confirmed['profile']['dislikes']==expected
    assert confirmed['profile']['preferences']==before['preferences']
    assert confirmed['profile']['restrictions']==before['restrictions']
    assert confirmed['pending_preference_update'] is None
    assert confirmed['last_chat_action']=='preferences'
    assert confirmed['request_intent'] is None and confirmed['recommendations']==[]
    assert client.get('/api/session').json()['profile']['dislikes']==expected
    llm.assert_not_called()


def test_dislike_is_not_saved_without_affirmative_confirmation(client):
    client.post('/api/chat',json={'text':'nao gosto de peixe'})
    for reply in ['talvez','isso','sim, mas não salve']:
        result=client.post('/api/chat',json={'text':reply}).json()
        assert result['profile']['dislikes']==[] and result['profile']['restrictions']==[]
        assert result['pending_preference_update'] is not None
    canceled=client.post('/api/chat',json={'text':'não'}).json()
    assert canceled['profile']['dislikes']==[]
    assert canceled['pending_preference_update'] is None
