# Experimento #82 — J sob distúrbio, observado pelo Kubernetes

**Issue:** https://github.com/Green-Cinnamon-Labs/spec-tennessee-eastman/issues/82
**Epic:** #77
**Data:** 2026-10-07 (não iniciado)

---

A epic #77 montou a cadeia planta → historian → `plant-supervisor` → `Plant.status` e mostrou que ela funciona em operação nominal: J ≈ 166 $/h, `Compliant`. Também mostrou o veredito virando, mas só *mudando a regra* (baixando o `maxCost` para 150 com `kubectl patch`). O que ainda não foi mostrado é o caso que importa para a tese: a **própria planta** se degradando enquanto as regras ficam fixas, e o Kubernetes percebendo. O experimento #82 é esse teste — é a evidência de que a camada supervisória realmente observa o estado econômico da planta, e não apenas os números que alguém digitou numa política.

O procedimento é simples de enunciar. Com a planta rodando no caso base do Modo 1 e a política do Modo 1 ativa, primeiro registra-se um trecho de operação nominal (J, metas e limites todos ok). Depois liga-se um distúrbio do TEP escrevendo no seu node OPC-UA — por exemplo `disturbance.idv6 = 1`, perda da alimentação de A, o mesmo comando já testado em 2026-10-02 — sem mexer na política. A partir daí, acompanha-se o `Plant.status` ao longo do tempo: J deve se afastar do valor nominal, alguma meta ou limite deve eventualmente falhar e, depois de `persistenceEvaluations` (3) avaliações ruins seguidas, `PolicyCompliant` deve virar `False` e a fase, `NonCompliant`.

O que se mede é a *observação*, não o distúrbio em si (caracterizar cada IDV é a #47). As perguntas são: como J evolui depois do distúrbio e quais dos seus 12 termos se mexem; qual condição falha primeiro — custo (`CostWithinBudget`), produto (`TargetsMet`) ou envelope de operação (`ConstraintsSatisfied`); quanto tempo passa entre ligar o distúrbio e o veredito virar, separando o tempo de resposta da própria planta do atraso que o supervisor acrescenta (janela de média de 60 s, intervalo de avaliação de 30 s, persistência de 3); e se o veredito volta a `Compliant` quando o distúrbio é desligado. Um segundo distúrbio com assinatura diferente (por exemplo IDV1, um degrau na razão A/C da alimentação) mostraria se o veredito distingue um problema econômico de um problema de limite.

O principal obstáculo é o tempo. O IDV6 é um distúrbio lento e severo: no TEP original ele leva horas de tempo *simulado* para levar a planta aos seus limites, e a planta simulada roda hoje a cerca de 2× o tempo real, então uma rodada completa pode levar horas de relógio — e a janela de 60 s do supervisor também é em tempo de relógio, cobrindo só uns 2 minutos simulados. Antes de rodar, é preciso decidir alguns pontos, listados abaixo. O resultado deve entrar em `experimentos.md` como um novo experimento e na monografia como a principal evidência da camada supervisória.

## Decisões antes de rodar

- **Velocidade da simulação** — rodar a planta mais rápido que 2× o tempo real (tornar o `tick_interval` configurável é a #69), ou aceitar uma rodada longa.
- **Janela e intervalo** — manter 60 s / 30 s, ou alongar a janela para que J seja julgada sobre um trecho relevante de tempo simulado (ou passar a janela para tempo simulado, usando o sinal `clock.t_h` da planta).
- **Orçamento** — com `maxCost: 179` e J ≈ 166, J precisa subir cerca de 8 % antes de a condição de custo falhar; decidir se essa é a sensibilidade desejada (ver [operating_policy_mode1.md](operating_policy_mode1.md), "Decisions to revisit").
- **Registro** — o `Plant.status` guarda só o veredito mais recente, então a rodada precisa de uma série temporal: um script consultando `kubectl get plant tep -o json` (junto com o `clock.t_h` da planta), o log do próprio supervisor (uma linha por avaliação), ou as sessões SQLite da IHM.
- **Quais distúrbios** — só o IDV6, ou o IDV6 mais um mais rápido (IDV1) para contraste; e se a planta deve chegar aos limites de shutdown (o shutdown da planta hoje é só diagnóstico, #70).
