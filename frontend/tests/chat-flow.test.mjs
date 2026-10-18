import test from "node:test";
import assert from "node:assert/strict";
import {
  addressIntent,
  confirmsOrder,
  matchChoice,
  requestedQuantity,
  reportsContext,
  preferenceCommand,
} from "../src/chat-flow.ts";

test("a confirmação exige um pedido explícito e não aceita negações ou frases genéricas", () => {
  for (const text of ["confirmar pedido", "Confirmo o pedido!", "pode confirmar o pedido"])
    assert.equal(confirmsOrder(text), true);
  for (const text of [
    "sim",
    "ok",
    "continuar",
    "não confirmar pedido",
    "quanto custa confirmar pedido?",
    "confirmar pedido se for barato",
  ])
    assert.equal(confirmsOrder(text), false);
});
test("escolhas por número e nome usam apenas opções oferecidas e recusam ambiguidades", () => {
  const options = [{ name: "Padrão" }, { name: "Rápida" }];
  assert.equal(
    matchChoice("2", options, (o) => o.name),
    options[1],
  );
  assert.equal(
    matchChoice("rápida", options, (o) => o.name),
    options[1],
  );
  assert.equal(
    matchChoice("opção 1", options, (o) => o.name),
    options[0],
  );
  assert.equal(
    matchChoice("3", options, (o) => o.name),
    undefined,
  );
  assert.equal(
    matchChoice("Rápida", [...options, { name: "Rápida" }], (o) => o.name),
    undefined,
  );
});
test("quantidade não é confundida com escolha de prato e respeita o limite do backend", () => {
  assert.equal(requestedQuantity("quero 2 unidades"), 2);
  assert.equal(requestedQuantity("quantidade 3 pratos"), 3);
  for (const value of ["2", "0 unidades", "21 unidades", "-1 unidade"])
    assert.equal(requestedQuantity(value), undefined);
});
test("relatos do dia e objetivos são tratados como contexto", () => {
  assert.equal(reportsContext("Meu objetivo é ganhar massa"), true);
  assert.equal(reportsContext("Só comi frutas hoje"), true);
  assert.equal(reportsContext("Frango grelhado"), false);
});
test("pedidos de endereço abrem cadastro ou troca sem capturar buscas de comida", () => {
  for (const text of [
    "adicionar endereço",
    "Cadastrar novo endereço",
    "novo endereço de entrega",
    "quero adicionar um endereço",
  ])
    assert.equal(addressIntent(text), "add");
  for (const text of [
    "trocar endereço",
    "Mudar o endereço",
    "entregar em outro lugar",
    "meus endereços",
    "alterar endereço de entrega",
  ])
    assert.equal(addressIntent(text), "change");
  for (const text of ["novo pedido", "quero comida perto do meu endereço", "frango grelhado", "1"])
    assert.equal(addressIntent(text), undefined);
});

test("alterações explícitas de preferências são encaminhadas sem capturar pedidos temporários", () => {
  for (const value of [
    "Salve nas minhas preferências até 600 kcal",
    "Mude meu mínimo de proteína para 30 g",
    "Adicione cebola aos ingredientes que prefiro evitar",
    "Remova meu máximo de proteína",
  ]) {
    assert.equal(preferenceCommand(value), true);
  }
  for (const value of [
    "Quero frango até 600 kcal",
    "Como alterar minhas preferências?",
    "Não salve minhas preferências",
    "Adicione queijo ao prato",
    "Prefiro frango hoje",
  ]) {
    assert.equal(preferenceCommand(value), false);
  }
});

test("frases naturais de preferências chegam ao agente durante o fluxo de compra", () => {
  for (const value of [
    "Queria que você colocasse frango nos ingredientes que gosto",
    "De agora em diante prefiro evitar cebola",
    "Meu limite de calorias agora é 600 kcal",
    "Não quero mais cebola nas minhas preferências",
    "Gosto de frango",
    "Sou alérgico a amendoim",
  ]) {
    assert.equal(preferenceCommand(value), true, value);
  }
});

test("sim e não respondem à preferência pendente sem autorizar compra", async () => {
  const { preferenceReply } = await import("../src/chat-flow.ts");
  for (const reply of [
    "sim",
    "Sim!",
    "pode salvar",
    "não",
    "não salve",
    "só hoje",
    "talvez",
    "isso",
    "ok",
    "sim, mas não salve",
  ]) {
    assert.equal(preferenceReply(reply, true), true, reply);
    assert.equal(preferenceReply(reply, false), false, reply);
    assert.equal(confirmsOrder(reply), false);
  }
  assert.equal(preferenceReply("confirmar pedido", true), false);
  assert.equal(preferenceReply("quero pizza", true), true);
});
