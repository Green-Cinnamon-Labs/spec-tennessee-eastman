# Nota: Painel Analytics — Séries Temporais TEP

**Onde fica:** `http://localhost:8080/analytics` (link "📈 Analytics" no header do IHM)  
**Arquivos:** `tep-ihm/src/persistence.py`, `tep-ihm/static/analytics.{html,js}`

---

## O que é

O painel Analytics é uma tela separada do IHM operacional. Enquanto o IHM mostra o estado **agora**, o Analytics mostra o que aconteceu **ao longo do tempo** — séries temporais das 41 variáveis medidas (XMEAS) e das 12 variáveis manipuladas (XMV).

Os dados são gravados em SQLite (`/data/sessions.db`) a ~1 ponto por segundo, mas **somente quando você inicia uma sessão de captura manualmente**.

---

## Fluxo básico

### 1. Iniciar uma captura

No header da tela:

```
[● verde]  [Session name…]  [▶ Start]  [■ Stop]  |  recording: …
```

1. Digite um nome descritivo no campo `Session name…` (ex: `IDV-5 teste 2`)
2. Clique **▶ Start**
3. O ponto fica verde piscando e o status muda para `recording: <nome>`
4. Deixe a simulação rodar pelo tempo que quiser
5. Clique **■ Stop** para encerrar a captura

> A captura pode ser feita em paralelo enquanto você usa o IHM normalmente — você não precisa ficar na tela de Analytics.

---

### 2. Selecionar e visualizar uma sessão gravada

Na sidebar esquerda:

1. **SESSION → dropdown**: selecione a sessão que quer analisar
   - O dropdown mostra nome, data e quantidade de pontos gravados
   - Sessões com `●` no nome ainda estão sendo gravadas
2. Os metadados aparecem abaixo: intervalo de tempo (`t_h`) e horário real

---

### 3. Definir janela temporal (opcional)

Em **TIME RANGE (T_H)**:

- `From` e `To` aceitam valores em horas de simulação (ex: `0.5` a `2.0`)
- Deixe em branco para ver a sessão inteira
- Útil quando a sessão é longa e você só quer analisar um trecho (ex: durante um IDV)

---

### 4. Selecionar variáveis

Em **VARIABLES**, há três grupos colapsáveis:

| Grupo                     | Conteúdo                            |
| ------------------------- | ----------------------------------- |
| XMEAS — Process (1–22)    | Pressão, temperatura, nível, fluxos |
| XMEAS — Analysers (23–41) | Composição de correntes (mol%)      |
| XMV — Actuators (1–12)    | Abertura de válvulas (%)            |

Clique no triângulo `▶` para expandir um grupo e marque as variáveis desejadas.

**Dica:** misture XMEAS + XMV relacionados para ver a malha de controle (ex: XMEAS(9) Temperatura do Reator + XMV(10) Fluxo de CWS).

---

### 5. Consultar o gráfico

Clique **Query selected chart** (botão azul no fundo da sidebar).

O gráfico ECharts carrega com:
- Linhas **sólidas** para XMEAS (eixo Y esquerdo, escala automática)
- Linhas **tracejadas** para XMV (eixo Y direito, escala %)
- Eixo X = t_h (horas de simulação)

**Interações nativas do ECharts:**
- Scroll do mouse → zoom no eixo X
- Arraste sobre o slider abaixo do gráfico → seleciona janela
- Botão 🔲 no canto superior direito do gráfico → zoom por área
- Botão 🖼 → salva imagem PNG

---

### 6. Múltiplos gráficos

- Clique **+ Add chart** para adicionar um novo slot
- Cada slot é independente: pode ter variáveis e janelas temporais diferentes
- Clique **◎ Focus** em um slot para torná-lo o alvo do próximo Query
- Clique **✕** no slot para limpar os dados
- Clique **—** para remover o slot

---

### 7. Exportar para CSV

Com uma sessão selecionada, clique **↓ CSV** na sidebar.  
O download contém: `t_h`, `xmeas_1..41`, `xmv_1..12` — pronto para pandas/Excel.

```python
import pandas as pd
df = pd.read_csv("tep_session_1.csv")
df.plot(x="t_h", y=["xmeas_7", "xmeas_9"])
```

---

### 8. Deletar uma sessão

Clique **✕ Delete** (vermelho) — remove a sessão e todos os pontos do banco. Irreversível.

---

## Onde os dados ficam

```
tep-ihm container
└── /data/sessions.db        ← SQLite com todas as sessões
```

Se você quer persistir entre restarts do container, o volume `/data` precisa estar mapeado no `docker-compose.yml` (já configurado no `tep-supervisor`).

---

## Limitações conhecidas

- **Sem auto-captura**: dados só são gravados durante uma sessão ativa. Se o IHM reiniciar, a sessão ativa é encerrada automaticamente.
- **1 sessão ativa por vez**: não é possível gravar duas sessões em paralelo.
- **ECharts via CDN**: a tela de Analytics requer acesso à internet (`cdn.jsdelivr.net`) para carregar o ECharts. Em ambiente sem internet, é preciso servir o bundle localmente.
