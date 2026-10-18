"""O assistente monta o pedido do cliente (complementos e quantidade) para caber nos limites que ele pediu.

    pedido base (só o obrigatório, o mais barato) -> calcula a nutrição dele (referência) ->
    base já estoura um teto (preço, kcal, carboidrato, gordura)? sim: impossível, avisa o cliente
    modelo propõe (sem pesquisar cada ingrediente) -> calcula a nutrição do que foi montado (pipeline atual) ->
    bateu os limites? sim: pronto · não: o modelo ajusta com o que o cálculo mostrou, até `montagem_max_tentativas`
    sem sucesso em todas: falhou, o cliente monta o dele.

Roda em segundo plano; cada passo vira um evento (`Assembly.events`) que a UI mostra como mensagem do assistente.
O código garante o que o modelo não pode quebrar: opções e quantidades válidas (domain.select), alimentos que o cliente
não gosta ou restrições, e a conferência dos limites. Nada é comprado: no fim a UI só preenche a tela de montagem.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from jsonschema import ValidationError as SchemaError, validate

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import AppError, MacroError
from app.domain import select
from app.schemas.macro import (Assembly, AssemblyLimits, MealCandidate, NutritionResult, SelectedItem, SelectedOption,
                               SelectionInput, UserProfile)
from app.services.nutrition_batch_search import QUALITATIVE
from app.services.llm_texto import chat_completion_fallback as chat_completion
from app.services.nutrition.entrada import extrair_json
from app.services.review_processing import normalized
from app.skills import montar_pedido

log = logging.getLogger(__name__)
TETOS = {"preço", "calorias", "carboidrato", "gordura"}  # só aumentam ao adicionar: o pedido base já os estoura = impossível
MAX_QUANTIDADE = 5
ROTULO_META = {"low_calorie": "pouco calórico", "high_protein": "muita proteína", "low_carb": "pouco carboidrato",
               "low_fat": "pouca gordura"}
# Preferências do cliente entregues ao modelo, como texto. Valor fixo por enquanto: a feature de preferências
# (gostos, aversões, restrições) vai trocar isto por um texto montado a partir do perfil.
PREFERENCIAS_DO_CLIENTE = "Sem preferências registradas."
_tarefas: dict[str, asyncio.Task] = {}


@dataclass
class Quebra:
    tipo: str
    texto: str


@dataclass
class Resultado:
    state: str  # ready | impossible | failed
    message: str
    options: list[SelectedOption] = field(default_factory=list)
    quantity: int = 1
    nutrition: NutritionResult | None = None
    attempt: int = 0


def _reais(cents: int | float) -> str:
    return f"R$ {cents / 100:.2f}".replace(".", ",")


def _proibidas(profile: UserProfile, extras: list[str]) -> list[str]:
    return [normalized(t) for t in [*profile.dislikes, *profile.restrictions, *extras] if t.strip()]


def _opcao_proibida(nome: str, proibidas: list[str]) -> bool:
    return any(p in normalized(nome) for p in proibidas)


def pedido_base(candidate: MealCandidate, proibidas: list[str]) -> list[SelectedOption] | None:
    """Só o obrigatório, com as opções mais baratas que o cliente aceita; None se não for possível montar."""
    escolhidas: list[SelectedOption] = []
    for g in candidate.option_groups:
        faltam = g.min_selections
        for o in sorted(g.options, key=lambda o: o.price_cents):
            if faltam <= 0:
                break
            if _opcao_proibida(o.name, proibidas):
                continue
            qtd = min(o.max_quantity, faltam)
            escolhidas.append(SelectedOption(group_id=g.id, option_id=o.id, quantity=qtd))
            faltam -= qtd
        if faltam > 0:
            return None
    return escolhidas


def conferir(selected: SelectedItem, nutricao: NutritionResult, limites: AssemblyLimits) -> list[Quebra]:
    """O que ficou fora dos limites do cliente, em português e com os números (a quantidade já aplicada)."""
    q, quebras = selected.quantity, []
    total = selected.unit_total_cents * q
    if limites.max_price_cents is not None and total > limites.max_price_cents:
        quebras.append(Quebra("preço", f"preço {_reais(total)} acima do limite de {_reais(limites.max_price_cents)}"))
    n = limites.nutrition
    efetivos = {"max_calories": (n.max_calories, ""), "min_protein_g": (n.min_protein_g, ""),
                "max_carbs_g": (n.max_carbs_g, ""), "max_fat_g": (n.max_fat_g, "")}
    for meta, (campo_pref, _, amplo, _) in ((g, QUALITATIVE[g]) for g in n.goals if g in QUALITATIVE):
        # "pouco calórico", "muita proteína" sem número: vale a referência ampla do motor (por prato).
        chave = {"calories": "max_calories", "protein_g": "min_protein_g", "carbs_g": "max_carbs_g",
                 "fat_g": "max_fat_g"}[campo_pref]
        if efetivos[chave][0] is None:
            efetivos[chave] = (amplo, f" (referência para “{ROTULO_META[meta]}”)")
    for tipo, campo, valor, (alvo, nota), minimo in (
        ("calorias", "calories", nutricao.calories, efetivos["max_calories"], False),
        ("proteína", "protein_g", nutricao.protein_g, efetivos["min_protein_g"], True),
        ("carboidrato", "carbs_g", nutricao.carbs_g, efetivos["max_carbs_g"], False),
        ("gordura", "fat_g", nutricao.fat_g, efetivos["max_fat_g"], False),
    ):
        if alvo is None:
            continue
        unidade = "kcal" if campo == "calories" else "g"
        if valor is None:
            quebras.append(Quebra(tipo, f"{tipo}: sem dado para conferir o limite de {alvo:g} {unidade}"))
            continue
        total_n = valor * q
        if (total_n < alvo) if minimo else (total_n > alvo):
            quebras.append(Quebra(tipo, f"{tipo} {total_n:.0f} {unidade} {'abaixo do mínimo' if minimo else 'acima do máximo'} "
                                        f"de {alvo:g} {unidade}{nota}"))
    return quebras


def _resumo(selected: SelectedItem, nutricao: NutritionResult) -> str:
    q = selected.quantity
    partes = [f"{(nutricao.calories or 0) * q:.0f} kcal"]
    for rotulo, v in (("proteína", nutricao.protein_g), ("carboidrato", nutricao.carbs_g), ("gordura", nutricao.fat_g)):
        if v is not None:
            partes.append(f"{rotulo} {v * q:.0f} g")
    return f"{_reais(selected.unit_total_cents * q)} · " + " · ".join(partes)


def _nutricao_para_o_modelo(n: NutritionResult) -> dict:
    return {"calorias": n.calories, "proteina_g": n.protein_g, "carboidrato_g": n.carbs_g, "gordura_g": n.fat_g,
            "porcao_g": n.portion_grams, "base_da_porcao": n.portion_basis, "confianca": n.confidence,
            "suposicoes": n.assumptions[:4], "evidencia": (n.evidence or "")[:300], "por_unidade": True}


def _dados(candidate: MealCandidate, limites: AssemblyLimits, base: dict, tentativas: list[dict]):
    n = limites.nutrition
    return {
        "prato": {"nome": candidate.name, "descricao": candidate.description[:300],
                  "preco_reais": candidate.price_cents / 100},
        "grupos": [{"group_id": g.id, "nome": g.name, "min_selections": g.min_selections,
                    "max_selections": g.max_selections,
                    "opcoes": [{"option_id": o.id, "nome": o.name, "preco_reais": o.price_cents / 100,
                                "max_quantity": o.max_quantity} for o in g.options]} for g in candidate.option_groups],
        "limites": {k: v for k, v in {
            "preco_maximo_reais": limites.max_price_cents / 100 if limites.max_price_cents is not None else None,
            "calorias_maximas": n.max_calories, "proteina_minima_g": n.min_protein_g,
            "carboidrato_maximo_g": n.max_carbs_g, "gordura_maxima_g": n.max_fat_g,
            "objetivos": list(n.goals) or None}.items() if v is not None},
        "preferencias": PREFERENCIAS_DO_CLIENTE,
        "quantidade_maxima": MAX_QUANTIDADE,
        "pedido_base": base,
        "tentativas": tentativas,
    }


async def propor(settings: Settings, dados: dict, erro: str | None = None) -> dict:
    """Pergunta ao modelo uma combinação. `erro`: por que a anterior foi recusada (ele corrige)."""
    dados = {**dados, "erro_da_proposta_anterior": erro} if erro else dados
    mensagens = [{"role": "system", "content": montar_pedido.INSTRUCOES},
                 {"role": "user", "content": montar_pedido.pedido(dados)}]
    texto = await chat_completion(mensagens, json_mode=True, temperature=0.2, log_content=settings.busca_log_conteudo,
                                  settings=settings)
    resposta = extrair_json(texto)
    validate(resposta, montar_pedido.SCHEMA)
    return resposta


def _montar_selecao(candidate: MealCandidate, resposta: dict, proibidas: list[str]) -> SelectedItem:
    """Valida a proposta do modelo com as mesmas regras da tela (domain.select) e com as restrições do cliente."""
    nomes = {(g.id, o.id): o.name for g in candidate.option_groups for o in g.options}
    opcoes = []
    for o in resposta["opcoes"]:
        chave = (o["group_id"], o["option_id"])
        if chave not in nomes:
            raise MacroError("Opção inexistente na proposta.", 422)
        if _opcao_proibida(nomes[chave], proibidas):
            raise MacroError(f"A opção “{nomes[chave]}” vai contra o que o cliente evita.", 422)
        opcoes.append(SelectedOption(group_id=o["group_id"], option_id=o["option_id"], quantity=max(1, o["quantity"])))
    quantidade = min(max(1, resposta["quantidade"]), MAX_QUANTIDADE)
    return select(candidate, SelectionInput(item_id=candidate.item_id, merchant_id=candidate.merchant_id,
                                            quantity=quantidade, options=opcoes))


def _chave(selected: SelectedItem) -> str:
    return json.dumps([selected.quantity, sorted((o.group_id, o.option_id, o.quantity) for o in selected.options)])


def _pronto(selecionado: SelectedItem, nutricao: NutritionResult, tentativa: int) -> Resultado:
    return Resultado("ready", f"Pronto! Montei: {', '.join(selecionado.option_labels) or 'o prato como está'}"
                              f"{f' × {selecionado.quantity} pratos' if selecionado.quantity > 1 else ''}. "
                              f"{_resumo(selecionado, nutricao)} (estimativa). Confira e diga “continuar”.",
                     options=selecionado.options, quantity=selecionado.quantity, nutrition=nutricao, attempt=tentativa)


async def montar(settings: Settings, candidate: MealCandidate, limites: AssemblyLimits, profile: UserProfile,
                 extras_proibidos: list[str], emit: Callable[[str], None],
                 calcular: Callable[[SelectedItem], Awaitable[NutritionResult]],
                 propor_fn=None) -> Resultado:
    propor_fn = propor_fn or propor  # resolvido na chamada (os testes trocam `propor`)
    proibidas = _proibidas(profile, extras_proibidos)
    base_opcoes = pedido_base(candidate, proibidas)
    if base_opcoes is None:
        return Resultado("failed", "Não consegui montar sozinho: os complementos obrigatórios deste prato têm só opções que "
                                   "você evita. Monte o seu pedido pela tela.")
    base = select(candidate, SelectionInput(item_id=candidate.item_id, merchant_id=candidate.merchant_id,
                                            quantity=1, options=base_opcoes))
    if limites.max_price_cents is not None and base.unit_total_cents > limites.max_price_cents:
        return Resultado("impossible", f"Não tem como: o pedido mais barato deste prato custa {_reais(base.unit_total_cents)}, "
                                       f"acima do seu limite de {_reais(limites.max_price_cents)}. Quer subir o limite ou escolher outro prato?")

    emit("Calculando o pedido base (só o obrigatório) para ter uma referência…")
    n_base = await calcular(base)
    if n_base.state != "ready":
        return Resultado("failed", "Não consegui calcular as calorias deste prato agora, então não dá para conferir seus limites. "
                                   "Monte o seu pedido pela tela.")
    quebras_base = conferir(base, n_base, limites)
    emit(f"Pedido base: {_resumo(base, n_base)}.")
    teto = [q for q in quebras_base if q.tipo in TETOS]
    if teto:
        return Resultado("impossible", "Não tem como com este prato: mesmo o pedido mais simples já passa do limite "
                                       f"({'; '.join(q.texto for q in teto)}). Quer relaxar o limite ou escolher outro prato?",
                         nutrition=n_base)

    ref = {"complementos": base.option_labels, "preco_reais": base.unit_total_cents / 100,
           "nutricao": _nutricao_para_o_modelo(n_base)}
    tentativas: list[dict] = []
    avaliados = {_chave(base): (base, n_base, quebras_base)}  # combinação -> (pedido, nutrição, o que quebrou)
    for tentativa in range(1, settings.montagem_max_tentativas + 1):
        emit(f"Tentativa {tentativa} de {settings.montagem_max_tentativas}: escolhendo complementos…")
        selecionado, erro = None, None
        for _ in range(2):  # uma correção se a proposta for inválida
            try:
                resposta = await propor_fn(settings, _dados(candidate, limites, ref, tentativas), erro)
                selecionado = _montar_selecao(candidate, resposta, proibidas)
                break
            except (AppError, MacroError, ValueError, SchemaError, KeyError) as e:
                erro = getattr(e, "message", None) or str(e)
        if selecionado is None:
            return Resultado("failed", "Não consegui montar uma combinação válida. Monte o seu pedido pela tela.",
                             attempt=tentativa)
        if _chave(selecionado) in avaliados:
            antigo, n_antigo, q_antigo = avaliados[_chave(selecionado)]
            if not q_antigo:  # já calculada e dentro dos limites (ex.: o próprio pedido base)
                return _pronto(antigo, n_antigo, tentativa)
            tentativas.append({"complementos": selecionado.option_labels, "quantidade": selecionado.quantity,
                               "aviso": "combinação repetida; proponha outra diferente"})
            emit("Repeti uma combinação já avaliada; vou tentar outra.")
            continue
        emit(f"{resposta['motivo']} ({', '.join(selecionado.option_labels) or 'sem complementos'}"
             f"{f', {selecionado.quantity} pratos' if selecionado.quantity > 1 else ''}). Calculando a nutrição…")
        nutricao = await calcular(selecionado)
        if nutricao.state != "ready":
            return Resultado("failed", "Não consegui calcular as calorias do que montei. Monte o seu pedido pela tela.",
                             attempt=tentativa)
        quebras = conferir(selecionado, nutricao, limites)
        avaliados[_chave(selecionado)] = (selecionado, nutricao, quebras)
        if not quebras:
            return _pronto(selecionado, nutricao, tentativa)
        emit(f"Não bateu: {'; '.join(q.texto for q in quebras)}.")
        tentativas.append({"complementos": selecionado.option_labels, "quantidade": selecionado.quantity,
                           "preco_reais": selecionado.unit_total_cents * selecionado.quantity / 100,
                           "nutricao": _nutricao_para_o_modelo(nutricao), "fora_do_limite": [q.texto for q in quebras]})
    return Resultado("failed", f"Não consegui atingir seus limites em {settings.montagem_max_tentativas} tentativas. "
                               "Monte o seu pedido pela tela; deixei o prato aberto para você.",
                     attempt=settings.montagem_max_tentativas)


# ---------- execução em segundo plano ----------

def _atualizar(db, session_id: str, assembly_id: str, operacao) -> bool:
    with db.transaction() as conexao:
        sessao = db.get(session_id, conexao)
        if sessao is None or sessao.assembly is None or sessao.assembly.id != assembly_id:
            return False  # o cliente já seguiu em frente (nova busca, escolha...)
        operacao(sessao.assembly)
        db.save(sessao, conexao)
        return True


def iniciar(db, settings: Settings, session_id: str, assembly_id: str, candidate: MealCandidate, limites: AssemblyLimits,
            profile: UserProfile, extras: list[str], calcular) -> None:
    """Cria a tarefa em segundo plano; a UI acompanha por GET /api/assembly."""
    def emit(texto: str) -> None:
        logs.info("montagem", texto)
        _atualizar(db, session_id, assembly_id, lambda a: a.events.append(texto))

    async def rodar() -> None:
        try:
            r = await asyncio.wait_for(montar(settings, candidate, limites, profile, extras, emit, calcular),
                                       settings.montagem_timeout_seconds)
        except asyncio.TimeoutError:
            r = Resultado("failed", "Demorei demais para montar. Monte o seu pedido pela tela.")
        except Exception as e:  # nada aqui pode deixar o cliente esperando para sempre
            log.exception("montagem falhou")
            logs.aviso("montagem", f"erro inesperado: {logs.curto(e)}")
            r = Resultado("failed", "Tive um problema ao montar. Monte o seu pedido pela tela.")

        def final(a: Assembly) -> None:
            a.state, a.message, a.attempt, a.nutrition = r.state, r.message, r.attempt, r.nutrition
            a.options, a.quantity = r.options, r.quantity
        _atualizar(db, session_id, assembly_id, final)
        _tarefas.pop(assembly_id, None)

    _tarefas[assembly_id] = asyncio.create_task(rodar())


def em_andamento(assembly_id: str) -> bool:
    t = _tarefas.get(assembly_id)
    return t is not None and not t.done()
