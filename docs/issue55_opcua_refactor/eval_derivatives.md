# Revisão sobre `derivatives()`

A hipótese está correta: `derivatives()` acumula responsabilidades que não lhe pertencem, e é possível separar o que é dinâmica física do que é instrumentação, mas a separação exige cuidado porque algumas variáveis intermediárias cumprem as duas funções ao mesmo tempo. 

A função hoje realiza quatro coisas distintas: 
- atualiza o estado dos distúrbios como efeito colateral (Blocks 7–12), 
- calcula toda a álgebra de balanços de massa, energia e cinética necessária ao integrador (Blocks 13–34), 
- salva um subconjunto dessas variáveis em `self.xmeas` como snapshot de saída (Block 35), e 
- aplica ruído gaussiano e lógica de amostradores sobre esse snapshot (Blocks 37–39). 

Apenas o segundo grupo é dinâmica pura. Os demais são efeitos colaterais ou instrumentação acoplados ao corpo de uma função cujo contrato matemático formal é exclusivamente retornar o vetor de derivadas `yp`.

O RK4 chama `derivatives()` quatro vezes por passo de integração, passando estados intermediários diferentes a cada chamada: 
- o estado em `t`, 
- o estado em `t + dt/2` usando k1, 
- o estado em `t + dt/2` usando k2, e 
- o estado em `t + dt` usando k3. 

## Fluxo do Racional AS-IS

A ordem dos blocos dentro de `derivatives()` não é arbitrária — cada grupo depende dos resultados do anterior, formando uma cadeia de dependências que determina o que pode ser reordenado e o que não pode.

```
Blocks 1–6 — TEINIT (inicialização — fora de derivatives())
  Equivalem ao TEINIT do FORTRAN original: constantes termodinâmicas, parâmetros
  do processo, estado inicial das válvulas e distúrbios. Executam uma única vez
  na construção do modelo, distribuídos em constants.rs, initial_state.rs e
  disturbance_state.rs. derivatives() começa no Block 7 porque é onde o FORTRAN
  entrava no loop de integração a cada passo de tempo.
        │
        ▼
[yy: estado integrado]
        │
        ▼
Blocks 7–12 — Distúrbios
  Atualiza fatores externos: composições de feed (xst), temperaturas de entrada (tst),
  fatores de reação (r1f, r2f), temperaturas de água de resfriamento (tcwr, tcws).
  Entrada: self.time, self.idv
  Saída: self.xst, self.tst, self.tcwr, self.tcws, self.r1f, self.r2f
        │
        ▼
Block 13 — Desempacotamento do vetor de estado
  Separa yy nos grupos físicos: concentrações molares (ucvr, ucvs, uclr, ucls, uclc, ucvv)
  e posições de atuador (vpos[0..12]).
  → vpos é o output dos atuadores. Entra em tudo que vem depois.
        │
        ▼
Blocks 14–16 — Termodinâmica
  Frações molares → temperaturas por entalpia (tcr, tcs, tcc, tcv)
  → densidades (dlr, dls, dlc) → volumes (vlr, vls, vlc)
  → pressões parciais e totais (ptr, pts, ptv).
  Depende de: ucvr/ucvs/uclr... (estado), xst/tst (distúrbios)
        │
        ▼
Blocks 17–18 — Cinética de reação (Arrhenius)
  Depende de: ptr, ppr, tkr (temperaturas absolutas), r1f, r2f
  Saída: taxas de reação rr[4], taxas por componente crxr[8], calor de reação rh
        │
        ▼
Blocks 19–21 — Composições e entalpias dos streams
  Atualiza xst com frações de vapor/líquido calculadas. Calcula entalpias hst[13].
  Depende de: xvv, xvr, xvs, xls, xlc (frações), tst (temperaturas de stream)
        │
        ▼
Blocks 22–24 — Vazões (ftm): atuadores + pressão + compressor
  → Aqui vpos entra diretamente: ftm[i] = vpos[i] * VRNG[i] / 100
  → Vazões por pressão dependem de ptr, pts, ptv
  → Compressor depende de ptv/pts e reciclo vpos[4]
  Saída: ftm[13], cpdh (trabalho do compressor)
        │
        ▼
Block 25 — Matriz de fluxo por componente (fcm)
  fcm[componente][stream] = xst[componente][stream] * ftm[stream]
  Depende de: xst (composições), ftm (vazões totais)
        │
        ▼
Blocks 26–31 — Flash do stripper, split vapor/líquido, entalpias restantes
  Depende de: ftm, tcc, fcm, sfr
  Completa fcm e hst para todos os streams
        │
        ▼
Blocks 32–34 — Trocas de calor (qur, qus, quc)
  qur: reator ← depende de vpos[9], tcwr, tcr, uar
  qus: separador ← depende de tws, tst[7]
  quc: condensador ← depende de vpos[8], tcc
        │
        ▼
Block 35 — Snapshot XMEAS (side effect de instrumentação)
  Salva em self.xmeas os valores físicos já calculados acima.
  Não alimenta yp. É leitura, não produção.
        │
        ▼
Block 36 — Detecção de shutdown (ISD)
  Usa xmeas[6] (ptr normalizado) e volumes vlr, vls, vlc.
  Se ISD → retorna vec![0.0; 50] (bloqueia derivadas).
        │
        ▼
Blocks 37–39 — Ruído e amostradores (instrumentação — não alimenta yp)
        │
        ▼
Block 40 — Derivadas yp (o único output real da função)
  Balanços de massa:  yp[i]    = fcm (reatores, separador, stripper, compressor)
  Balanços de energia: yp[8,17,26,35] = hst * ftm ± rh ± qur/qus/quc
  Dinâmica de atuadores: yp[38+i] = (xmv[i] - vpos[i]) / VTAU[i]
```

A posição de `vpos` no início da cadeia (Block 13) é a decisão estrutural central: os atuadores determinam as vazões, as vazões determinam os balanços, os balanços determinam as derivadas. Qualquer separação de atuadores em objetos próprios precisa respeitar esse ponto de entrada — `vpos` precisa estar disponível antes de Block 22.

## Sensores AS-IS

O modelo TEP expõe 41 variáveis medidas, agrupadas em `self.xmeas[0..41]`. As primeiras 22 (`XMEAS(1–22)`) são medições contínuas de processo — vazões de alimentação e produto, pressões, níveis e temperaturas dos equipamentos principais (reator, separador, stripper, compressor). As 19 restantes (`XMEAS(23–41)`) são analisadores de composição: 14 medem frações molares no purge e no reciclo gasoso, 5 medem composição do produto líquido do stripper. 

Esses dois grupos têm comportamentos distintos: 
- as medições contínuas são recalculadas a cada passo de integração e recebem ruído gaussiano a cada step; 
- os analisadores são amostrados em intervalos fixos (`tgas = 0.1 h` para gasosos, `tprod = 0.25 h` para produto), introduzem um atraso de transporte via `self.xdel`, e recebem ruído apenas no momento do disparo do sampler. 

Na prática, isso significa que as 22 primeiras variáveis correspondem a transmissores online e as 19 seguintes correspondem a cromatógrafos — instrumentos com dinâmica de amostragem completamente diferente. Isso tem consequências diretas sobre tudo que é efeito colateral dentro da função. O Block 35 usa atribuição simples (`=`), então a cada chamada do RK4 ele sobrescreve `self.xmeas[0..22]` com os valores físicos computados a partir do estado intermediário corrente, e logo depois o Block 37 adiciona ruído sobre esses valores. 

O resultado final em `self.xmeas` após os quatro estágios é o valor físico da quarta chamada (com estado `t + dt*k3`) somado ao ruído gerado nessa quarta chamada — os ruídos das chamadas anteriores são sobrescritos. Isto significa que, por acidente de implementação, o ruído para medições contínuas é aplicado corretamente uma única vez ao final do ciclo RK4, mas não por design: é uma propriedade emergente da sobrescrita em Block 35 e não seria garantida se a ordem ou a estrutura do bloco mudasse.

Para os analisadores amostrados (Blocks 38–39), a situação é diferente e mais delicada. O disparo do sampler é controlado por comparações com `self.tgas` e `self.tprod`, variáveis de estado interno do modelo. Quando a condição `time >= self.tgas` é verdadeira na primeira chamada do RK4, o código executa o disparo, avança `self.tgas += 0.1` e salva a composição do estado intermediário k1 em `self.xdel`. 

Nas três chamadas seguintes do mesmo passo de integração, `self.tgas` já foi avançado, de modo que a condição não dispara novamente — o que evita quatro disparos por passo. Entretanto, a composição `xcmp` salva em `self.xdel` na primeira chamada reflete o estado intermediário k1, não o estado final do passo. O valor que o analisador amostra é, portanto, o estado da planta em `t + dt/2 * k1_valves`, não o estado consolidado ao fim do passo. Para dt da ordem de 0.001 h isso é numericamente insignificante, mas é um acoplamento oculto entre o método de integração e a lógica de instrumentação — um acoplamento que não existiria se os analisadores fossem aplicados após a integração completar.

A questão central sobre o que pode sair de `derivatives()` é a seguinte: as variáveis físicas `tcr`, `ptr`, `vlr`, `ftm`, `tcs`, `tcc`, `cpdh`, `quc` e demais que aparecem em Block 35 são locais à função — elas são calculadas em Blocks 13–34 e são necessárias para o cálculo de `yp` em Block 40. Não são calculadas para instrumentação; são calculadas para a dinâmica e depois salvas como subproduto. O Block 35 é, portanto, um snapshot de variáveis que já precisariam existir no escopo da função. 

O que pode e deve sair são os Blocks 37, 38 e 39 integralmente: nenhum deles contribui para `yp`, todos eles mutam `self.xmeas` como efeito colateral de instrumentação, e todos deveriam ser invocados uma única vez após o passo de integração ser concluído, em um método separado — seja `observe()`, `instrument()` ou equivalente — que o `Plant::step()` chama explicitamente depois de `integrator.step()` e `advance_time()`.

## Atuadores AS-IS

O modelo TEP expõe 12 variáveis manipuladas (`XMV`), todas representadas no vetor de estado `yy[38..50]` como posições de atuador integradas pelo RK4. Das 12, onze são válvulas de controle de fluxo — alimentação de D, E, A, A/C, reciclo do compressor, purga, underflow do separador, produto do stripper, vapor do stripper, água de resfriamento do reator e água de resfriamento do condensador. 

A décima segunda (`XMV(12)` / `vpos[11]`) é a velocidade do agitador do reator, tratada pelo modelo com a mesma equação de primeira ordem das válvulas mas com semântica diferente: não controla vazão de fluido, controla mistura no reator via `agsp`, que por sua vez afeta o coeficiente de troca térmica `uar` em Block 32. São, portanto, dois tipos físicos de atuador embutidos sob a mesma abstração numérica.

Além desses 12, existem elementos que num processo real seriam atuadores mas que o benchmark TEP simplifica como curvas fixas ou parâmetros algébricos. O compressor não tem velocidade como variável manipulada: sua vazão (`ftm[8]`) é determinada em Block 24 pela razão de pressão `ptv/pts` e pela curva característica fixada em `CPFLMX` e `CPPRMX`. O único controle indireto sobre ele é pela válvula de reciclo `XMV(5)`. 

Bombas também não existem como entidades separadas — os fluxos líquidos são inteiramente dirigidos pelas válvulas sobre gradientes de pressão entre equipamentos. Isso significa que, do ponto de vista de instrumentação e OPC-UA, os 12 `XMV` são os únicos atuadores explícitos do modelo, e o agitador merece uma classe própria distinta das válvulas de fluxo quando os objetos `Actuator` forem tipados.

A dinâmica de válvulas (Block 40, `yp[i+38] = (self.xmv[i] - vpos[i]) / VTAU[i]`) pertence às EDOs: as posições de válvula são variáveis de estado em `yy[38..50]`, integradas pelo RK4, e `VTAU` é o parâmetro físico da constante de tempo de primeira ordem. Esse bloco não pode sair de `derivatives()` sem reimplementar integração para os atuadores fora do RK4, o que quebraria a consistência numérica.

O que pode ser feito é parametrizar `VTAU[i]` a partir de objetos `Actuator` injetados — o ODE continua igual, mas o valor da constante de tempo passa a vir do objeto em vez de uma constante hardcoded. Isso permite trocar `IdealActuator` (tau→0, resposta instantânea) por outros tipos sem alterar a estrutura do integrador. O `xmv` recebido como comando pelo modelo é já o sinal de entrada do atuador; a posição de válvula `vpos` integrada é a resposta dinâmica desse atuador. A separação conceitual já existe implicitamente — falta apenas torná-la explícita nos tipos.

# Conclusão

- `derivatives()` deve ser reduzida a Blocks 7–35 mais Block 40.
- Block 35 permanece mas muda de semântica: deixa de ser "escrita para instrumentação" e passa a ser "snapshot do estado físico observável após álgebra do passo", acessível como `self.xmeas` bruto sem ruído. 
- Os Blocks 37–39 migram para um método `apply_sensors()` invocado em `Plant::step()` após `integrator.step()`, recebendo os objetos `Sensor` injetados e produzindo `bus.outputs.xmeas` como o vetor de medições já processadas. 
- O `bus.outputs.xmeas` passa a ser o process image instrumentado; `self.xmeas` interno ao modelo passa a ser o process image físico bruto. 

Essa é a fronteira correta: de um lado a dinâmica, do outro a instrumentação — e os objetos `Sensor` vivem exatamente nessa fronteira.
