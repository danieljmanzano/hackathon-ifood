import asyncio
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.nutrition_budget import reserve_call
from app.schemas.macro import (Address, MealRequest, NutritionPreferences, NutritionResult,
                               NutritionSearchProgress, Recommendation, Session, UserProfile, Message)
from app.services.nutrition import service
from app.services.nutrition.pipeline import PIPELINE_VERSION
from app.services.nutrition.produtos import chave_produto, repositorio
from app.services.meal_intent import parse_intent
from app.services import nutrition_batch_search as batches
from app.storage.catalog import CatalogStore
from app.storage.database import Database
from tests.nutricao_comum import candidato


@pytest.fixture
def settings(tmp_path):
    service._cache.clear()
    service._catalog_lanes.clear()
    repositorio.cache_clear()
    return Settings(_env_file=None,ifood_mode='live',database_path=tmp_path/'db.sqlite3',
                    calorias_base_path=tmp_path/'nutrition.json',openrouter_api_key='test',
                    nutrition_provider='openrouter',intent_llm_enabled=False,busca_replanejar=False,
                    calorias_log='off',busca_log='off')


def candidates(n):
    return [candidato(item_id=f'item-{i}', name='Frango grelhado', description='Frango e arroz, 400 g',image_url=None) for i in range(n)]


def nutrition(calories=400, protein=40):
    return NutritionResult(state='ready',calories=calories,minimum=calories-10,maximum=calories+10,
                           portion_basis='prato',method='estimated',protein_g=protein,carbs_g=30,fat_g=10,
                           pipeline_version=PIPELINE_VERSION)


def setup(settings, count=15, pool=None, paging=None, text='frango até 500 kcal'):
    request = MealRequest(text=text)
    session = Session(id='user',mode='live',profile=UserProfile(id='user'),
                      address=Address(id='a',label='Casa',formatted='Endereço de teste',latitude=-23,longitude=-46),
                      messages=[Message(role='assistant',text='Avaliando')],request_intent=parse_intent(request),
                      nutrition_search=NutritionSearchProgress(id=str(uuid4())))
    db = Database(settings.database_path)
    db.save(session)
    cs = candidates(count)
    pool = cs if pool is None else pool
    recs = [Recommendation(candidate=c,reasons=[],limitations=[]) for c in pool]
    batches.enqueue(session,request,cs if paging is None else pool,recs,['frango'],paging or {},settings)
    return db,session,request


def test_batches_continue_until_three_good_and_run_in_parallel(settings,monkeypatch):
    db,session,_ = setup(settings)
    called=[]
    active=peak=0
    async def calculate(s,c,options):
        nonlocal active,peak
        active+=1
        peak=max(active,peak)
        called.append(c.item_id)
        await asyncio.sleep(.01)
        active-=1
        return nutrition(900 if int(c.item_id.split('-')[-1]) < 3 else 400)
    monkeypatch.setattr(service,'calcular',calculate)
    assert asyncio.run(batches.process_search(settings,provider=object()))
    result=db.get(session.id)
    assert result.nutrition_search.tested==6 and result.nutrition_search.batches==2
    assert result.nutrition_search.accepted==3 and result.nutrition_search.reason=='target_reached'
    assert called==[f'item-{i}' for i in range(6)]
    assert peak==3
    assert len(result.recommendations)==3
    assert all(r.nutrition.calories<=500 for r in result.recommendations)


def test_stops_after_fifteen_without_returning_bad_or_unknown_options(settings,monkeypatch):
    db,session,_=setup(settings,count=20)
    calls=[]
    async def calculate(s,c,options):
        calls.append(c.item_id)
        return nutrition(900) if len(calls)%2 else NutritionResult(state='unavailable')
    monkeypatch.setattr(service,'calcular',calculate)
    asyncio.run(batches.process_search(settings,provider=object()))
    result=db.get(session.id)
    assert len(calls)==15
    assert result.nutrition_search.tested==15 and result.nutrition_search.batches==5
    assert result.nutrition_search.reason=='limit_reached'
    assert result.recommendations==[]
    assert 'limite de 15' in result.messages[-1].text


def test_fetches_more_pages_only_when_needed_and_deduplicates(settings,monkeypatch):
    cs=candidates(9)
    db,session,_=setup(settings,pool=cs[:3],paging={'cursor':{'page':1}})
    class Provider:
        calls=[]
        async def search_page(self,*args,cursor):
            self.calls.append(cursor)
            if cursor['page']==1:
                return {'candidates':cs[:3],'cursor':{'page':2}}
            return {'candidates':cs[3:6],'cursor':{'page':3}}
    p=Provider()
    calls=[]
    async def calculate(s,c,options):
        calls.append(c.item_id)
        return nutrition(900 if int(c.item_id.split('-')[-1])<3 else 400)
    monkeypatch.setattr(service,'calcular',calculate)
    asyncio.run(batches.process_search(settings,provider=p))
    assert p.calls==[{'page':1},{'page':2}]
    assert len(set(calls))==6 and len(calls)==6
    assert db.get(session.id).nutrition_search.reason=='target_reached'


def test_catalog_exhaustion_returns_only_approved_fewer_than_three(settings,monkeypatch):
    db,session,_=setup(settings,count=5)
    async def calculate(s,c,options):
        return nutrition(400 if c.item_id=='item-0' else 900)
    monkeypatch.setattr(service,'calcular',calculate)
    asyncio.run(batches.process_search(settings,provider=object()))
    result=db.get(session.id)
    assert result.nutrition_search.tested==5
    assert result.nutrition_search.reason=='catalog_exhausted'
    assert len(result.recommendations)==1


def test_daily_budget_is_shared_across_parallel_estimates_and_stops_search(settings,monkeypatch):
    settings=settings.model_copy(update={'catalog_calls_per_day':1})
    db,session,_=setup(settings)
    sent=[]
    async def calculate(s,c,options):
        reserve_call('test')
        sent.append(c.item_id)
        return nutrition()
    monkeypatch.setattr(service,'calcular',calculate)
    asyncio.run(batches.process_search(settings,provider=object()))
    result=db.get(session.id)
    assert len(sent)==1 and len(result.recommendations)==1
    assert result.nutrition_search.reason=='usage_limit' and result.nutrition_search.tested==3
    assert CatalogStore(settings.database_path).status()['calls']==1


def test_old_search_cannot_overwrite_new_search(settings,monkeypatch):
    db,session,_=setup(settings)
    async def run():
        started=asyncio.Event()
        release=asyncio.Event()
        async def calculate(*args):
            started.set()
            await release.wait()
            return nutrition()
        monkeypatch.setattr(service,'calcular',calculate)
        task=asyncio.create_task(batches.process_search(settings,provider=object()))
        await started.wait()
        new=db.get(session.id)
        new.nutrition_search=NutritionSearchProgress(id='new-search')
        new.messages[-1].text='Nova busca'
        db.save(new)
        release.set()
        await task
    asyncio.run(run())
    result=db.get(session.id)
    assert result.nutrition_search.id=='new-search'
    assert result.recommendations==[] and result.messages[-1].text=='Nova busca'


def test_cache_reuse_and_qualitative_missing_data(settings,monkeypatch):
    db,session,_=setup(settings,count=3,text='frango com mais proteína')
    for c in candidates(3):
        repositorio(str(settings.calorias_base_path)).put(chave_produto(c),nutrition(protein=40),c)
    async def unexpected(*args):
        pytest.fail('Cache pronto não deve chamar a IA')
    monkeypatch.setattr(service,'calcular',unexpected)
    asyncio.run(batches.process_search(settings,provider=object()))
    assert db.get(session.id).nutrition_search.reason=='target_reached'
    prefs=NutritionPreferences(goals=['high_protein'])
    assert not batches.qualifies(nutrition(protein=None),prefs)
    assert not batches.qualifies(nutrition(protein=20),prefs)
    assert batches.qualifies(nutrition(protein=40),prefs)


def test_resumes_persisted_in_flight_batch(settings,monkeypatch):
    db,session,_=setup(settings,count=3)
    store=CatalogStore(settings.database_path)
    job=store.claim_search(60)
    job['in_flight'],job['pool']=job['pool'],[]
    store.save_search(job['id'],job)
    store.recover_searches()
    async def calculate(*args):
        return nutrition()
    monkeypatch.setattr(service,'calcular',calculate)
    asyncio.run(batches.process_search(settings,provider=object()))
    assert db.get(session.id).nutrition_search.tested==3
    assert db.get(session.id).nutrition_search.reason=='target_reached'


def test_mcp_fetches_exactly_three_and_uses_returned_pagination_token():
    from tests.test_busca_multiplas_consultas import IFoodFalso, ENDERECO, item_json
    def response(name,args):
        if args.get('nextPageToken')=='actual-token':
            return {'results':[item_json('b','Frango')], 'hasMore':False}
        return {'results':[item_json('a','Frango')], 'hasMore':True,'nextPageToken':'actual-token'}
    provider=IFoodFalso(response)
    async def run():
        first=await provider.search_page(['frango'],ENDERECO,3500,refinamentos={'maxDeliveryTimeMinutes':30})
        second=await provider.search_page(['frango'],ENDERECO,3500,refinamentos={'maxDeliveryTimeMinutes':30},cursor=first['cursor'])
        assert second['cursor'] is None
    asyncio.run(run())
    assert len(provider.chamadas)==2
    for _,args in provider.chamadas:
        assert args['pageSize']==3
        assert args['refinements']=={'onlyOpen':True,'maxItemPrice':35,'maxDeliveryTimeMinutes':30}
    assert provider.chamadas[1][1]['nextPageToken']=='actual-token'


def test_mcp_repeated_token_stops_and_preserves_next_query():
    from tests.test_busca_multiplas_consultas import IFoodFalso, ENDERECO, item_json
    provider=IFoodFalso(lambda name,args:{'results':[item_json('a','Frango')], 'hasMore':True,'nextPageToken':'same-token'})
    async def run():
        first=await provider.search_page(['frango','carne'],ENDERECO,None)
        second=await provider.search_page(['frango','carne'],ENDERECO,None,cursor=first['cursor'])
        assert second['cursor']=={'query_index':1}
        await provider.search_page(['frango','carne'],ENDERECO,None,cursor=second['cursor'])
    asyncio.run(run())
    assert [a['query'] for _,a in provider.chamadas]==['frango','frango','carne']
    assert 'nextPageToken' not in provider.chamadas[-1][1]


def test_chat_api_returns_progress_then_three_verified_candidates(settings,monkeypatch):
    import app.main as main
    from app.api.endpoints import macro
    from app.core.config import get_settings
    from fastapi.testclient import TestClient
    cs=candidates(6)
    class Provider:
        pages=[]
        details=[]
        async def addresses(self):
            return [Address(id='a',label='Casa',formatted='Endereço de teste',latitude=-23,longitude=-46)]
        async def search_page(self,*args,cursor=None):
            self.pages.append(cursor)
            return {'candidates':cs[:3] if cursor is None else cs[3:],
                    'cursor':{'page':2} if cursor is None else None}
        async def item(self,merchant_id,item_id,address):
            self.details.append(item_id)
            return next(c for c in cs if c.item_id==item_id)
    provider=Provider()
    async def calculate(s,c,options):
        return nutrition(900 if int(c.item_id.split('-')[-1])<3 else 400)
    monkeypatch.setattr(service,'calcular',calculate)
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    app=main.create_app()
    app.dependency_overrides[get_settings]=lambda:settings
    app.dependency_overrides[macro.get_provider]=lambda:provider
    client=TestClient(app)
    client.get('/api/session')
    client.put('/api/session/address',json={'address_id':'a'})
    response=client.post('/api/chat',json={'text':'frango até 500 kcal até R$ 40'})
    assert response.status_code==200
    initial=response.json()
    assert initial['last_chat_action']=='search'
    assert initial['nutrition_search']['state']=='pending'
    assert initial['recommendations']==[]
    assert provider.pages==[None]
    asyncio.run(batches.process_search(settings,provider=provider))
    result=client.get('/api/recommendations/nutrition').json()
    assert result['nutrition_search']['reason']=='target_reached'
    assert result['nutrition_search']['tested']==6
    assert len(result['recommendations'])==3
    assert all(r['nutrition']['calories']<=500 for r in result['recommendations'])
    assert all(r['review_signal']['simulated'] for r in result['recommendations'])
    assert provider.pages==[None,{'page':2}] and len(provider.details)==6
    # Consultar progresso não reinicia estimativas nem novas páginas.
    assert client.get('/api/recommendations/nutrition').json()['nutrition_search']['tested']==6
    assert len(provider.pages)==2
    client.close()


def test_restart_after_saved_success_does_not_estimate_another_batch(settings,monkeypatch):
    db,session,_=setup(settings,count=6)
    store=CatalogStore(settings.database_path)
    job=store.claim_search(60)
    job['results']=[{'candidate':c,'nutrition':nutrition().model_dump(mode='json'),'reason':None} for c in job['pool'][:3]]
    job['pool']=job['pool'][3:]
    store.save_search(job['id'],job)
    store.recover_searches()
    async def unexpected(*args):
        pytest.fail('Busca já tem três aprovados no snapshot; não deve estimar mais')
    monkeypatch.setattr(service,'calcular',unexpected)
    asyncio.run(batches.process_search(settings,provider=object()))
    result=db.get(session.id)
    assert result.nutrition_search.tested==3 and result.nutrition_search.reason=='target_reached'
    assert len(result.recommendations)==3
