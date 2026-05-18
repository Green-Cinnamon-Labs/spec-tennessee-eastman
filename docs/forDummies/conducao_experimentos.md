# Como conduzir os experimentos — TEP Digital Twin Lab


## 1. Build (quando mudar código)

* 1.1. Planta — só rebuildar se `tep-plant` mudar
```bash
docker build -t te-plant:latest c:/Projetos/tep/tep-plant
```

* 1.2. IHM — rebuildar se `tep-ihm` mudar
```bash
# `poetry lock` só é necessário se `pyproject.toml` mudar
cd c:/Projetos/tep/tep-ihm && poetry lock
docker build -t tep-ihm:latest c:/Projetos/tep/tep-ihm
```

* 1.3. Operator — rebuildar se `tep-operator` mudar
```bash
docker build -t plc-operator:latest c:/Projetos/tep/tep-operator
```

* 1.4. Gerar deepcopy e CRDs — só se mudar os types do CRD
```bash
# Não funciona no Windows: usar Codespace do GitHub, depois dar pull
make generate manifests
```


## 2. Subir tudo (primeira vez ou após `kind delete`)

```bash
# 1. Subir planta + IHM
docker compose -f c:/Projetos/tep/tep-supervisor/local/docker-compose.yml up -d

# 2. Criar cluster Kind + carregar operator + deployar
#    Requer plc-operator:latest já buildada localmente
bash c:/Projetos/tep/tep-supervisor/local/setup.sh
```


## 3. Retomar após reinício do Docker

```bash
# O container do cluster parou — restartar
docker start tep-lab-control-plane

# Se `tep-lab-control-plane` não existir (cluster foi deletado), voltar ao passo 2.

# Subir planta + IHM de novo
docker compose -f c:/Projetos/tep/tep-supervisor/local/docker-compose.yml up -d
```


## 4. Atualizar imagem em cluster já existente

```bash
# Após rebuild do operator, carregar nova imagem no cluster
kind load docker-image plc-operator:latest --name tep-lab
kubectl rollout restart deployment/plc-operator
```

```bash
# Após rebuild da IHM, recriar só o container da IHM
docker compose -f c:/Projetos/tep/tep-supervisor/local/docker-compose.yml up -d --force-recreate tep-ihm
```


## 5. Parar tudo

```bash
docker compose -f c:/Projetos/tep/tep-supervisor/local/docker-compose.yml down
kind delete cluster --name tep-lab
```


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
