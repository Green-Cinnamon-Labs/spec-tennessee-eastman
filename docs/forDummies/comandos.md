# Comandos — TEP Digital Twin Lab

---

## 1. Build (quando mudar código)

> Planta — só rebuildar se `tep-plant` mudar
```bash
docker build -t te-plant:latest c:/Projetos/projetos-estrategicos/tep-plant
```

> IHM — rebuildar se `tep-ihm` mudar
> `poetry lock` só é necessário se `pyproject.toml` mudar
```bash
cd c:/Projetos/projetos-estrategicos/tep-ihm && poetry lock
docker build -t tep-ihm:latest c:/Projetos/projetos-estrategicos/tep-ihm
```

> Operator — rebuildar se `tep-operator` mudar
```bash
docker build -t plc-operator:latest c:/Projetos/projetos-estrategicos/tep-operator
```

> Gerar deepcopy e CRDs — só se mudar os types do CRD
> Não funciona no Windows: usar Codespace do GitHub, depois dar pull
```bash
make generate manifests
```

---

## 2. Subir tudo (primeira vez ou após `kind delete`)

```bash
# 1. Subir planta + IHM
docker compose -f c:/Projetos/projetos-estrategicos/tep-supervisor/local/docker-compose.yml up -d

# 2. Criar cluster Kind + carregar operator + deployar
#    Requer plc-operator:latest já buildada localmente
bash c:/Projetos/projetos-estrategicos/tep-supervisor/local/setup.sh
```

---

## 3. Retomar após reinício do Docker

```bash
# O container do cluster parou — restartar
docker start tep-lab-control-plane

# Subir planta + IHM de novo
docker compose -f c:/Projetos/projetos-estrategicos/tep-supervisor/local/docker-compose.yml up -d
```

> Se `tep-lab-control-plane` não existir (cluster foi deletado), voltar ao passo 2.

---

## 4. Atualizar imagem em cluster já existente

> Após rebuild do operator, carregar nova imagem no cluster
```bash
kind load docker-image plc-operator:latest --name tep-lab
kubectl rollout restart deployment/plc-operator
```

> Após rebuild da IHM, recriar só o container da IHM
```bash
docker compose -f c:/Projetos/projetos-estrategicos/tep-supervisor/local/docker-compose.yml up -d --force-recreate tep-ihm
```

---

## 5. Parar tudo

```bash
docker compose -f c:/Projetos/projetos-estrategicos/tep-supervisor/local/docker-compose.yml down
kind delete cluster --name tep-lab
```

---

## 6. Diagnóstico

```bash
# Ver containers rodando (deve ter: te-plant, tep-ihm, tep-lab-control-plane)
docker ps

# Ver pods do operator no cluster
kubectl get pods

# Ver estado do PLCMachine
kubectl get plcmachine tep-baseline

# Logs do operator
kubectl logs -f deploy/plc-operator

# Estado completo do PLCMachine (XMEAS, XMV, policy)
kubectl get plcmachine tep-baseline -o jsonpath='{.status}' | python -m json.tool
```
