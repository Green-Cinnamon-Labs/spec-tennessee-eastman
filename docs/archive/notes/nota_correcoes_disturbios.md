# Nota: Correções do Sistema de Distúrbios (IDV)

Registro das correções encontradas durante a preparação do Exp 14 (IDV(4): Reactor CW inlet +5°C).

---

## Correção 1 — Botão IDV não respondia visualmente

**Sintoma:** clicar no ▶ de qualquer IDV não mudava o estado do botão.

**Causa:** `toggleIdv` em `app.js` enviava o POST com sucesso, mas a atualização visual dependia exclusivamente do próximo tick do WebSocket. A 1× (3.6 s/tick) o botão parecia congelado. Se a planta não estivesse streamando, o botão nunca mudava.

**Correção (`app.js`):** após `resp.ok`, atualizar `_currentActiveIdv` e chamar `renderIdv` imediatamente, sem esperar o WebSocket.

---

## Correção 2 — Desativar IDV não limpava o distúrbio na planta

**Sintoma:** ao clicar ⏹ para desativar um IDV, a planta continuava com o distúrbio ativo.

**Causa:** `runtime.rs` só entrava no bloco de sync de `dv[]` se `!state.active_idv.is_empty()`. Com lista vazia (todos desativados), o bloco era pulado e `dv[]` nunca era zerado.

**Correção (`runtime.rs`):** remover a guarda `!state.active_idv.is_empty()` — o sync de `dv[]` ocorre sempre que `disturbances_restored = true`, independente da lista estar vazia.

---

## Correção 3 — Fechar painel IDV (✕) não funcionava

**Sintoma:** clicar no ✕ do painel flutuante não fechava o painel.

**Causa:** `makeDraggable` adiciona `e.preventDefault()` no `pointerdown` do header inteiro, cancelando o `click` subsequente em qualquer botão filho — incluindo o ✕.

**Correção (`app.js`):** adicionar `if (e.target.closest('button')) return;` no início do handler de `pointerdown`, pulando o drag quando o alvo é um botão.

---

## Correção 4 — IDV estado perdido após reiniciar a planta

**Sintoma:** após Stop + F5 na planta, o botão IDV continuava amarelo na IHM, mas a planta não recebia o distúrbio.

**Causa:** o IHM mantém `ACTIVE_IDV` como estado local. Quando a planta reinicia, ela começa com `state.active_idv = []`. A IHM não reenviava automaticamente o estado ao reconectar.

**Correção (`server.py`):** no primeiro tick da stream gRPC após conexão (`_connected = False → True`), reenviar `UpdateDisturbances` com o `ACTIVE_IDV` e `IDV_MAGNITUDES` atuais.

---

## Correção 5 — IDV(4) ativo, temperatura do reator não mudava

**Sintoma:** IDV(4) aparecia ativo (botão amarelo, gRPC confirmado), mas XMEAS(9) e XMV(10) não se alteravam em nada.

**Causa (em duas camadas):**

**Camada A — `self.tcwr` nunca chegava na física.**
`self.tcwr` é calculado corretamente em `derivatives()`:
```rust
self.tcwr = eval_disturbance(4, time, ds) + idv[3] as f64 * self.idv_step_mag[3];
```
Mas a ODE do estado `twr` (`yy[36]`) estava zerada:
```rust
// ERRADO — yp[36] sempre zero:
yp[36] = 0.0;
```
Com `yp[36] = 0`, `twr` nunca mudava. O calor trocado `qur = uar * (twr - tcr)` dependia só de `twr` (constante) e `tcr` — `tcwr` não aparecia em lugar nenhum na equação de energia.

**Camada B — ODE ausente no modelo.**
O comentário original dizia _"Cooling water temperatures: kept constant (YP(37)/YP(38) never set in FORTRAN TEFUNC)"_ — interpretação incorreta. No FORTRAN original de Downs & Vogel (1993), as temperaturas do fluido de resfriamento SÃO estados dinâmicos:

```
dTWR/dt = [FCWR·CpCW·(TCWR − TWR) + UAR·(TR − TWR)] / (VCR·CpCW)
```

**Por que a ODE falhou:** a fórmula `(-qur + fcwr * cpcw * (tcwr - twr)) / cpcw` cancela o `cpcw`, deixando `yp[36] ≈ -11500 °C/h` no instante t=0, travando o ISD em t=0.168h. A causa é que `fcwr` está em unidades de fluxo normalizadas (~41 u.a.) enquanto `qur` está em unidades de energia compatíveis com o balanço do reator (~21 u.a.) — as escalas são ~530× diferentes.

**Correção (`core/src/dynamics/tep/model.rs`):** solução quasi-estática — calcular `twr` algebricamente do balanço de calor em cada passo, sem ODE:

```rust
// Na Block 32, após calcular uar:
let fcwr = vpos[9] * VRNG[9] * 0.001;
let cw_cap_r = fcwr * 0.00942_f64 + uar;
let twr = (fcwr * 0.00942_f64 * self.tcwr + uar * tcr) / cw_cap_r;
let qur = uar * (twr - tcr) * (...);

// No bloco de ODE:
yp[36] = 0.0;  // twr não é estado ODE; resolvido acima
```

`cpcw_eff = 0.00942` foi calibrado para reproduzir `twr = 94.6°C` no ponto nominal (`tcwr = 38.5`, `tcr = 120`, `fcwr = 41.1`, `uar = 0.856`). IDV(4) agora propaga: `tcwr` ↑ → `twr` ↑ (quasi-estático, sem lag) → `qur` menos negativo → menos calor removido do reator → XMEAS(9) ↑ → controlador abre XMV(10).

---

## Arquivos modificados

| Arquivo                                    | Correção                             |
| ------------------------------------------ | ------------------------------------ |
| `tep-ihm/static/app.js`                    | #1 visual imediato, #3 fechar painel |
| `tep-plant/service/src/runtime.rs`         | #2 desativar IDV, #4 magnitude sync  |
| `tep-ihm/src/server.py`                    | #4 reenvio ao reconectar             |
| `tep-plant/core/src/dynamics/tep/model.rs` | #5 ODE de twr/tws                    |

---

## Lição

IDV(4)–(5) dependem da temperatura da água de resfriamento (`twr`/`tws`) como variável de estado intermediária. Qualquer distúrbio de temperatura de CW só tem efeito se essa ODE estiver ativa. Verificar o mesmo para IDV(3) (D feed temperature) se `tst[0]` também for estado com derivada zerada.
