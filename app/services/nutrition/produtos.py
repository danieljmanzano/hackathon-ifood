"""Base local de produtos já calculados (JSON). Produto na base não é recalculado."""
import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.schemas.macro import MealCandidate, NutritionResult, SelectedItem

log = logging.getLogger(__name__)
VERSAO_ARQUIVO = 1
_lock = threading.Lock()


def chave_produto(item: MealCandidate | SelectedItem) -> str:
    """Item do restaurante + opções escolhidas. A ordem das opções não muda a chave."""
    if isinstance(item, SelectedItem):
        candidate = item.candidate
        opcoes = sorted(o.option_id for o in item.options) or sorted(item.option_labels)
    else:
        candidate, opcoes = item, None
    # Preço/disponibilidade/imagem com URL temporária não alteram a composição.
    # Nomes de adicionais e quantidades fazem parte da receita, inclusive para um ID já conhecido.
    grupos = [(g.id, [(o.id, o.name) for o in g.options]) for g in candidate.option_groups]
    quantidades = sorted((o.option_id, o.quantity) for o in item.options) if isinstance(item, SelectedItem) else None
    base = [candidate.merchant_id, candidate.item_id or candidate.name, candidate.simulated,
            candidate.name, candidate.description,
            [candidate.features.portion_size, candidate.features.serves, candidate.features.weight_grams],
            grupos, opcoes, quantidades]
    return hashlib.sha256(json.dumps(base, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


class RepositorioProdutos:
    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)

    def _ler(self) -> dict:
        if not self.caminho.exists():
            return {"versao": VERSAO_ARQUIVO, "produtos": {}}
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            if isinstance(dados.get("produtos"), dict):
                return dados
        except (json.JSONDecodeError, OSError, AttributeError):
            pass
        backup = self.caminho.with_suffix(".bak")
        log.warning("Base de produtos ilegível; guardada em %s e recomeçada.", backup)
        try:
            os.replace(self.caminho, backup)
        except OSError:
            pass
        return {"versao": VERSAO_ARQUIVO, "produtos": {}}

    def get(self, chave: str, versao_pipeline: str) -> NutritionResult | None:
        """Resultado salvo, ou None se não há ou foi calculado por outra versão do pipeline (e não é manual)."""
        return self.get_many([chave], versao_pipeline).get(chave)

    def get_many(self, chaves: list[str], versao_pipeline: str) -> dict[str, NutritionResult]:
        """Lê a base uma vez para consultar um catálogo inteiro, sem chamadas externas."""
        registros = self._ler()["produtos"]
        return {chave: resultado for chave in chaves
                if (resultado := self._validar(registros.get(chave), versao_pipeline)) is not None}

    @staticmethod
    def _validar(registro, versao_pipeline: str) -> NutritionResult | None:
        if not registro:
            return None
        if registro.get("origem") != "manual" and registro.get("versao_pipeline") != versao_pipeline:
            return None
        try:
            return NutritionResult.model_validate(registro["resultado"])
        except (ValueError, KeyError):
            return None

    def put(self, chave: str, resultado: NutritionResult, candidate: MealCandidate) -> None:
        """Grava resultados prontos. Registros marcados "manual" nunca são sobrescritos."""
        if resultado.state != "ready":
            return
        with _lock:
            dados = self._ler()
            atual = dados["produtos"].get(chave)
            if atual and atual.get("origem") == "manual":
                return
            dados["produtos"][chave] = {
                "nome": candidate.name,
                "restaurante": candidate.merchant_name,
                "origem": resultado.method,
                "versao_pipeline": resultado.pipeline_version,
                "calculado_em": datetime.now(timezone.utc).isoformat(),
                "resultado": resultado.model_dump(mode="json"),
            }
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.caminho.with_suffix(".tmp")
            temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(temporario, self.caminho)


@lru_cache(maxsize=8)
def repositorio(caminho: str) -> RepositorioProdutos:
    return RepositorioProdutos(Path(caminho))
