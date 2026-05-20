# Nota: FastAPI, Uvicorn e o modelo assíncrono do Python

Eu vinha do Spring Boot e não entendia direito o que acontecia quando o FastAPI recebia uma requisição.
No Spring existe um modelo mental claro: Tomcat tem um pool de threads, cada requisição ganha uma thread, a thread vive até a resposta sair.
No Python eu via o código rodar, não criava threads explicitamente, mas o servidor atendia múltiplas coisas ao mesmo tempo.
Esse arquivo explica o que de fato acontece, passo a passo, usando o `tep-ihm` como exemplo concreto.

---

## O problema central do Python: o GIL

O Python tem um mecanismo chamado GIL (Global Interpreter Lock).
Ele garante que apenas uma thread Python execute bytecode de cada vez, mesmo em máquinas com múltiplos núcleos.

Isso significa que threads em Python **não são paralelas para código CPU-bound**.
Dois loops Python rodando em threads diferentes não executam literalmente ao mesmo tempo: eles se revezam no GIL.

A consequência prática: usar threads da mesma forma que no Java para obter paralelismo real não funciona no Python puro.
A comunidade Python respondeu a isso com um modelo diferente: **event loop + coroutines**.

---

## O event loop: a alma do asyncio

O `asyncio` é a biblioteca padrão do Python para código assíncrono.
A ideia central é um **event loop**: uma única thread fica em loop infinito verificando o que está pronto para executar.

O event loop é **cooperativo**: quando uma coroutine chega num `await`, ela pausa voluntariamente e devolve o controle ao event loop.
O event loop então verifica se outra coroutine está pronta para continuar e a executa.
Nenhuma thread nova é criada nesse processo.

Comparando com o Spring:

| Spring Boot                      | asyncio (Python)                             |
| -------------------------------- | -------------------------------------------- |
| Pool de threads (Tomcat)         | Event loop (thread única)                    |
| Cada requisição = uma thread     | Cada requisição = uma coroutine              |
| Thread bloqueia esperando I/O    | Coroutine pausa no `await` e libera o loop   |
| `@Async` cria task em outro pool | `asyncio.create_task()` agenda no mesmo loop |
| Threads rodam em paralelo real   | Coroutines revezam cooperativamente          |

---

## Uvicorn: o servidor ASGI

O Uvicorn é o servidor HTTP que roda embaixo do FastAPI.
No mundo Spring o equivalente seria o Tomcat ou o Jetty.

O Uvicorn inicia o event loop do `asyncio` e fica nele para sempre.
Quando chega uma requisição HTTP, o Uvicorn a transforma num evento e entrega para o FastAPI processar como uma coroutine.

Ele também inicia alguns **worker threads** do AnyIO (a biblioteca que o FastAPI usa internamente como abstração de async).
Essas threads existem para executar código síncrono bloqueante sem travar o event loop.
Elas **não são threads de requisição** como no Tomcat: são um pool de propósito geral para quando você precisa rodar código blocking.

É por isso que o debugger do VS Code mostra isso ao pausar o `tep-ihm`:

```
MainThread         RUNNING   ← event loop do asyncio
AnyIO worker thread RUNNING  ← pool para código bloqueante
AnyIO worker thread RUNNING
AnyIO worker thread RUNNING
```

São normais. Não indicam problema.

---

## FastAPI: dois mundos dentro do mesmo processo

O FastAPI entende dois tipos de endpoint: `async def` e `def`.
Eles se comportam de forma completamente diferente.

### Endpoint com `async def`

```python
@app.get("/status")
async def get_status():
    data = await alguma_io_assincrona()
    return {"ok": True}
```

O FastAPI executa essa função **diretamente no event loop**.
Não cria thread nenhuma.
Quando chega em `await alguma_io_assincrona()`, a coroutine pausa, o event loop atende outra coisa, e quando a I/O termina a coroutine retoma de onde parou.

Regra: tudo que for chamado aqui precisa ser `async`. Se você chamar uma função bloqueante (`time.sleep`, leitura de arquivo síncrona, chamada gRPC síncrona), você **trava o event loop inteiro** e o servidor para de atender qualquer coisa enquanto aquilo não termina.

### Endpoint com `def` (síncrono)

```python
@app.get("/config")
def get_config():
    return {"valor": 42}
```

Aqui o FastAPI percebe que não é `async` e automaticamente envia a função para rodar em uma **thread do pool do AnyIO**.
O event loop não bloqueia.
É como se o FastAPI fizesse por baixo dos panos:

```python
await asyncio.to_thread(get_config)
```

Isso resolve o problema de código legado ou de bibliotecas que não têm versão async.
No Spring você não precisa pensar nisso porque toda requisição já tem uma thread própria.

---

## `asyncio.create_task()`: o equivalente do `@Async`

No Spring, quando você quer que algo rode em background sem bloquear a resposta:

```java
@Async
public void processarAlgo() {
    // roda em outra thread do pool
}
```

No Python com asyncio:

```python
asyncio.create_task(minha_coroutine())
```

Isso **não cria uma thread nova**. Cria uma coroutine e a agenda no event loop para rodar na primeira oportunidade.
A diferença conceitual é importante: no Spring você tem paralelismo real (threads diferentes em núcleos diferentes).
No Python você tem **concorrência cooperativa**: o event loop alterna entre as tarefas quando cada uma faz `await`.

Para I/O (rede, disco, banco de dados), isso é suficiente e muito eficiente.
Para CPU-bound (cálculo pesado), isso não ajuda — para isso você usaria `multiprocessing` ou `concurrent.futures.ProcessPoolExecutor`.

---

## `asyncio.to_thread()`: rodando código bloqueante sem travar

Às vezes você precisa chamar uma biblioteca que não tem versão async.
Por exemplo, o watch do Kubernetes no `tep-ihm` usa o cliente Python oficial do K8s, que é síncrono.

Se você simplesmente chamar no event loop:

```python
async def operator_watch_loop():
    while True:
        w.watch(...)  # BLOQUEANTE — trava o event loop inteiro!
```

O servidor para de responder enquanto o watch estiver bloqueado.

A solução é `asyncio.to_thread()`, que envia a função bloqueante para um worker thread do AnyIO:

```python
async def operator_watch_loop():
    while True:
        await asyncio.to_thread(_k8s_watch_sync, custom, w)
        await asyncio.sleep(10)
```

Agora `_k8s_watch_sync` roda em uma das AnyIO worker threads que o Uvicorn criou.
O event loop fica livre para continuar atendendo WebSockets, requisições HTTP e o stream gRPC.

---

## Como o `tep-ihm` usa tudo isso na prática

Quando o servidor sobe, o `lifespan` do FastAPI agenda as tasks:

```python
@asynccontextmanager
async def lifespan(app):
    tasks = []
    tasks.append(asyncio.create_task(plant_stream_loop()))    # task 1
    tasks.append(asyncio.create_task(operator_watch_loop()))  # task 2
    yield
    for t in tasks:
        t.cancel()
```

O event loop passa a ter três coisas rodando concorrentemente:

```
event loop
├── plant_stream_loop()       ← coroutine: abre canal gRPC, faz `async for` no stream
├── operator_watch_loop()     ← coroutine: chama `asyncio.to_thread(...)` para K8s watch
└── uvicorn HTTP handler      ← atende GET, POST, WebSocket /ws
```

Quando um browser abre o WebSocket `/ws`, o FastAPI aceita e o handler fica suspenso em:

```python
while True:
    await ws.receive_text()  # pausa aqui, libera o event loop
```

Quando `plant_stream_loop` recebe um metric do gRPC, ele chama `broadcast(snapshot)`, que itera sobre `connected_clients` e faz `await ws.send_text(msg)` para cada um.
O event loop entrega a mensagem para cada WebSocket aberto sem criar thread nenhuma.

Quando o front faz `POST /api/reconnect`, o event loop entrega para o handler, que faz:

```python
_plant_task = asyncio.create_task(plant_stream_loop())
```

Uma nova coroutine entra no pool do event loop e começa a tentar reconectar.

---

## Resumo: o que acontece em cada cenário

| Cenário                                    | O que o FastAPI faz                                                    |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| `GET /status` com `async def`              | Roda no event loop, sem thread nova                                    |
| `GET /config` com `def`                    | Envia para worker thread via `asyncio.to_thread`                       |
| `WebSocket /ws` com `async def`            | Coroutine fica viva no event loop enquanto o cliente estiver conectado |
| `asyncio.create_task(loop())`              | Agenda coroutine no event loop, sem thread nova                        |
| `await asyncio.to_thread(func_bloqueante)` | Roda `func_bloqueante` em worker thread do AnyIO                       |
| Chamada bloqueante dentro de `async def`   | **Erro silencioso**: trava o event loop inteiro                        |

---

## Por que não vejo minhas "threads" no debugger?

Porque a maior parte do trabalho acontece como coroutines no event loop, não como threads.
As AnyIO worker threads aparecem porque o Uvicorn as cria preventivamente para o pool.
No `tep-ihm`, só `_k8s_watch_sync` realmente usa uma delas.
Todo o resto — gRPC, WebSocket, HTTP — roda como coroutines na MainThread.
