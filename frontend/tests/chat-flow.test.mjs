import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmsOrder, matchChoice, requestedQuantity, reportsContext } from '../src/chat-flow.ts';

test('a confirmação exige um pedido explícito e não aceita negações ou frases genéricas', () => {
  for (const text of ['confirmar pedido', 'Confirmo o pedido!', 'pode confirmar o pedido']) assert.equal(confirmsOrder(text), true);
  for (const text of ['sim', 'ok', 'continuar', 'não confirmar pedido', 'quanto custa confirmar pedido?', 'confirmar pedido se for barato']) assert.equal(confirmsOrder(text), false);
});
test('escolhas por número e nome usam apenas opções oferecidas e recusam ambiguidades', () => {
  const options = [{ name: 'Padrão' }, { name: 'Rápida' }];
  assert.equal(matchChoice('2', options, o => o.name), options[1]);
  assert.equal(matchChoice('rápida', options, o => o.name), options[1]);
  assert.equal(matchChoice('opção 1', options, o => o.name), options[0]);
  assert.equal(matchChoice('3', options, o => o.name), undefined);
  assert.equal(matchChoice('Rápida', [...options, { name: 'Rápida' }], o => o.name), undefined);
});
test('quantidade não é confundida com escolha de prato e respeita o limite do backend', () => {
  assert.equal(requestedQuantity('quero 2 unidades'), 2);
  assert.equal(requestedQuantity('quantidade 3 pratos'), 3);
  for (const value of ['2', '0 unidades', '21 unidades', '-1 unidade']) assert.equal(requestedQuantity(value), undefined);
});
test('relatos do dia e objetivos são tratados como contexto', () => {
  assert.equal(reportsContext('Meu objetivo é ganhar massa'), true);
  assert.equal(reportsContext('Só comi frutas hoje'), true);
  assert.equal(reportsContext('Frango grelhado'), false);
});
