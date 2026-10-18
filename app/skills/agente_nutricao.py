"""Skill do agente e do pipeline, carregada apenas no enriquecimento incremental."""
from pathlib import Path

NOME = 'nutrition_enrichment'
DESCRICAO = 'Estimar nutrição de produtos reais quando faltam dados reutilizáveis, com fontes e incerteza.'
CONTEUDO = Path(__file__).with_name('nutrition-enrichment').joinpath('SKILL.md').read_text(encoding='utf-8').split('---', 2)[2].strip()


def exemplo():
    return [('skill nutricional', CONTEUDO)]
