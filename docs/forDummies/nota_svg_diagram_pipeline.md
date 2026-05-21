# Nota: Como o diagrama da planta funciona — do Draw.io ao navegador

> Para quem nunca trabalhou com SVG dinâmico, animação de dados em tempo real, ou com a arquitetura do dashboard TEP.

---

## 1. A imagem começa no Draw.io

O diagrama da planta (reatores, separadores, válvulas, sensores, streams) é desenhado manualmente no **Draw.io** — uma ferramenta de diagramação visual, como um Visio ou Lucidchart.

O que torna esse diagrama especial não é o desenho em si, mas os **IDs semânticos** atribuídos a cada elemento. No Draw.io, ao clicar com o botão direito em qualquer forma → *Edit Data* (ou `Ctrl+M`), aparece um painel de propriedades. Ali, o campo `id` (identificador) recebe um nome com significado, como:

```
sensor-xmeas-09
actuator-xmv-03
unit-reactor
stream-09-purge
```

Esses nomes não são apenas rótulos visuais — são **endereços**. É pelo nome que o código JavaScript vai encontrar aquele elemento depois.

Quando o diagrama está pronto, você exporta pelo menu: *Extras → Edit Diagram → Export as SVG*. O resultado é um arquivo `.svg`.

---

## 2. O que é um SVG?

SVG (Scalable Vector Graphics) é um formato de imagem baseado em **XML** — o mesmo tipo de texto estruturado usado em HTML. Isso significa que um SVG não é um JPEG ou PNG opaco: ele é um documento com tags, atributos e estrutura, como este trecho:

```xml
<g data-cell-id="unit-reactor">
  <g transform="translate(420,180)">
    <path d="M 0 0 L 80 0 L 80 60 Z" fill="#dae8fc" stroke="#6c8ebf"/>
  </g>
</g>
```

O Draw.io exporta cada elemento que você criou como um grupo `<g>` com o atributo `data-cell-id` igual ao ID semântico que você definiu. Isso é o que permite o código localizar o reator, a válvula, o sensor — sem adivinhar.

Como é XML/HTML, o SVG pode ser **injetado diretamente no DOM** (a estrutura interna de uma página web). Em vez de exibir a imagem como `<img src="...">`, o servidor carrega o SVG e o cola dentro do HTML da página. A partir daí, qualquer elemento visual do diagrama pode ser manipulado por JavaScript — mudar cor, mudar espessura de linha, adicionar texto — exatamente como se fossem `<div>`s normais.

---

## 3. Os três documentos de contrato e mapeamento

Agora que você tem um SVG com IDs e um sistema de planta com variáveis (XMEAS, XMV), surge uma pergunta: **como o código sabe qual variável da planta corresponde a qual elemento do SVG?**

É aí que entram os três arquivos de contrato.

---

### 3.1 `tep_svg_semantic_contract.md`

**O que é:** um documento de especificação em linguagem natural (Markdown).

**Para que serve:** descreve as **regras e convenções** do sistema de endereçamento. É o "manual de estilo" — define que o atributo usado para buscar elementos é `data-cell-id` (não `id`), quais categorias de elementos existem (units, streams, sensors, actuators, analyzers), o que cada categoria representa no processo, e como os IDs devem ser nomeados.

**Analogia:** pense nele como a **documentação da API** antes de escrever o código. Antes de o desenvolvedor tocar em JavaScript, ele lê esse contrato para saber o que esperar encontrar no SVG.

**Quem usa:** humanos (o desenvolvedor, o AI assistente, quem faz manutenção futura). É a referência de decisões — "por que esse elemento se chama `stream-08-down` e não `stream-recycle`?". A resposta está aqui.

---

### 3.2 `tep-svg-mapping.json`

**O que é:** um arquivo de dados estruturado (JSON).

**Para que serve:** lista todos os elementos do processo TEP e vincula cada um ao seu ID no SVG, à variável de processo correspondente (XMEAS/XMV), e às unidades físicas. É a **tabela de tradução** entre o mundo do processo e o mundo visual.

Exemplo simplificado:

```json
{
  "id": "sensor-xmeas-09",
  "description": "Temperatura do reator",
  "xmeas_index": 9,
  "unit": "°C",
  "svg_cell_id": "sensor-xmeas-09"
}
```

**Analogia:** é como uma planilha Excel de "de/para". Do lado esquerdo: a variável do processo. Do lado direito: onde ela aparece no desenho. O desenvolvedor consulta esse arquivo quando precisa saber "qual XMEAS alimenta qual sensor visual?".

**Quem usa:** tanto humanos quanto potencialmente ferramentas de geração de código. Se amanhã você quiser gerar o `diagram-animator.js` automaticamente a partir desse JSON, é possível — os dados todos estão aqui.

---

### 3.3 `tep-diagram.schema.json`

**O que é:** um arquivo de schema JSON (estrutura formal de dados).

**Para que serve:** descreve a **ontologia do processo** — não o SVG, mas o que os elementos *representam* no processo TEP. Define os tipos de equipamentos (reator, condensador, separador), as variáveis medidas, os atuadores, os analisadores — com todas as suas propriedades, faixas de operação, e relações entre si. É uma representação formal do conhecimento de processo.

**Analogia:** se o contrato `.md` é o manual de estilo e o `.json` de mapeamento é a tabela de tradução, o schema é a **enciclopédia do processo**. Ele responde: "O que é um analisador de composição? Quais variáveis ele mede? Em que faixa?".

**Quem usa:** ferramentas que precisam entender o domínio (AI assistentes, validators, geradores de documentação). Também serve como referência para garantir que o mapeamento está consistente com o que o processo realmente é.

---

## 4. Os dois arquivos JavaScript do IHM

Com o SVG no DOM e os documentos de contrato escritos, o JavaScript entra em cena para fazer o diagrama *viver*. Ele é dividido em duas camadas.

---

### 4.1 `diagram-adapter.js` — a camada de primitivas

**O que é:** uma biblioteca de funções baixo nível para interagir com o SVG do Draw.io.

**Problema que resolve:** o Draw.io exporta SVGs com uma estrutura interna peculiar — elementos aninhados em múltiplos grupos `<g>`, com `data-cell-id` em vez de `id`. Funções padrão do JavaScript como `getElementById()` não funcionam aqui. O adapter encapsula essa complexidade.

**Funções principais:**

```
getSemanticElement(id)      → encontra o <g> pelo data-cell-id
getDrawablePath(id)         → dentro do <g>, acha o <path> ou <rect> desenhável
getOrCreateValueText(id)    → cria (ou reutiliza) um <text> SVG ao lado do elemento
updateStream(id, valor)     → muda espessura e opacidade de um stream
updateActuator(id, valor)   → muda cor de uma válvula (cinza=fechada, verde=aberta)
updateSensor(id, valor)     → exibe o valor numérico ao lado do sensor
updateUnit(id, tempC)       → colore um vaso por faixa de temperatura
```

**Analogia:** pense nele como os **drivers de hardware**. Você não precisa saber como o SVG está estruturado internamente — chama `updateActuator('actuator-xmv-03', 62)` e a válvula fica laranja.

---

### 4.2 `diagram-animator.js` — a camada de lógica de animação

**O que é:** a camada de alto nível que recebe os dados da planta e decide o que atualizar no diagrama.

**Problema que resolve:** o adapter sabe *como* colorir um vaso, mas não sabe *qual* XMEAS alimenta *qual* vaso. O animator tem esse conhecimento de negócio — ele é o "maestro".

**Função principal:**

```javascript
function updateDiagram(xmeas, xmv) {
    // recebe os 41 XMEAS e 12 XMV do WebSocket
    // e chama as funções do adapter com os valores corretos

    colorizeVessel('unit-reactor', xmeas[8]);        // XMEAS(9) = temperatura do reator
    updateStreamWidth('stream-09-purge', xmeas[9]);  // XMEAS(10) = vazão da purga
    updateSensorValue('sensor-xmeas-09', xmeas[8], '°C');
    updateActuator('actuator-xmv-03', xmv[2]);
    // ... e assim por diante para os 41+12 sinais
}
```

Além disso, o animator gerencia:
- **Zoom e pan** do diagrama (scroll do mouse, Ctrl+drag)
- **Analisadores de composição** (XMEAS 23–41), que mostram os percentuais ao lado de cada sensor do analisador
- **Carregamento inicial** do SVG via `fetch('/static/plant-diagram.svg')` e injeção no DOM

---

## 5. Como tudo entra no navegador

O fluxo completo, do servidor ao pixel na tela:

```
1. Usuário abre o navegador → http://localhost:8080

2. FastAPI serve o index.html
   └─ index.html carrega:
       ├─ diagram-adapter.js  (primitivas SVG)
       └─ diagram-animator.js (lógica de animação)

3. DOMContentLoaded dispara no animator:
   └─ fetch('/static/plant-diagram.svg')
       └─ SVG é injetado como innerHTML no <div id="diagram-container">
       └─ initDiagramInteraction() ativa zoom/pan

4. WebSocket conecta em ws://localhost:8080/ws
   └─ A cada mensagem, chega um JSON com xmeas[41] e xmv[12]
       └─ updateDiagram(xmeas, xmv) é chamado
           ├─ adapter coloriza vasos
           ├─ adapter escala streams
           ├─ adapter atualiza labels de sensores
           ├─ adapter colore atuadores
           └─ animator atualiza displays de analisadores
```

O diagrama não é uma imagem estática — é um documento XML vivo, manipulado frame a frame pelo JavaScript conforme os dados chegam da planta via WebSocket.

---

## Resumo em uma frase

Você desenha no Draw.io, atribui IDs semânticos, exporta como SVG → o SVG vira parte do HTML → o JavaScript usa os IDs para encontrar cada elemento → quando chegam dados da planta pelo WebSocket, o código atualiza cores, espessuras e labels em tempo real.

Os três documentos de contrato garantem que o desenho, o processo, e o código falem a mesma língua.
