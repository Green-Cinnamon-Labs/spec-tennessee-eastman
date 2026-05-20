# Registro: WSL2, protobuf e rebuild do operator

Eu quis usar o WSL2 para facilitar a regeneracao dos arquivos protobuf do `tep-operator`.
O objetivo era resolver o crash do pod `plc-operator` antes de continuar os experimentos.

## Contexto

O lab subia com tres containers principais: `te-plant`, `tep-ihm` e `tep-lab-control-plane`.
A IHM recebia dados da planta, mas o painel `Operator K8S` ficava como `Unknown`.

No Kubernetes, o pod do operator aparecia em `Error`/crashloop.
O `PLCMachine` existia, mas nao recebia `PHASE`, `TIME(H)` nem `ISD`.

Os logs indicavam falha durante a inicializacao do protobuf em `plant.pb.go`.
Isso apontou para arquivos Go gerados desatualizados ou incompatíveis com o modulo atual.

## WSL2

Primeiro eu tentei entrar no WSL e cai na distro interna `docker-desktop`.
Ela nao deve ser usada para trabalho normal; e uma distro tecnica do Docker Desktop.

Pelo PowerShell, listei as distros com:

```powershell
wsl -l -v
```

Como so existia `docker-desktop`, instalei uma distro Linux real:

```powershell
wsl --install -d Ubuntu
```

Se `Ubuntu` nao aparecer como opcao, pode-se listar as opcoes e instalar uma versao explicita:

```powershell
wsl --list --online
wsl --install -d Ubuntu-24.04
```

Na primeira abertura do Ubuntu, o WSL pediu usuario e senha.
Esse usuario e local da distro Linux e nao precisa ser igual ao usuario do Windows.

## Pacotes instalados

Depois de entrar no Ubuntu, fui para o repo do operator:

```bash
cd /mnt/c/Projetos/tep/tep-operator
```

Atualizei a lista de pacotes:

```bash
sudo apt update
```

Isso nao atualiza o sistema inteiro; so baixa a lista atual de pacotes disponiveis.
E necessario antes de instalar ferramentas pelo `apt`.

Instalei o `make`:

```bash
sudo apt install -y make
```

O projeto usa `Makefile`, entao comandos como `make proto` dependem desse binario.
Sem ele, o terminal retorna `make: command not found`.

Instalei o compilador protobuf:

```bash
sudo apt install -y protobuf-compiler
```

Esse pacote fornece o comando `protoc`.
Ele le arquivos `.proto` e gera codigo em outras linguagens.

Conferi a instalacao do `protoc`:

```bash
protoc --version
```

O resultado esperado e algo parecido com `libprotoc 3.21.12`.
Isso confirma que o compilador protobuf esta no PATH.

Instalei a ferramenta Go:

```bash
sudo apt install -y golang-go
```

O operator e escrito em Go.
Tambem precisamos do `go` para instalar os plugins que geram `.pb.go`.

Instalei o plugin Go do protobuf:

```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

Esse plugin gera o arquivo Go principal a partir do `.proto`.
Sem ele, o `protoc` falha com `protoc-gen-go: program not found`.

Instalei o plugin Go do gRPC:

```bash
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

Esse plugin gera o codigo Go especifico de cliente/servidor gRPC.
Sem ele, a parte gRPC do contrato da planta nao e gerada.

Adicionei os binarios instalados pelo Go ao PATH da sessao:

```bash
export PATH="$PATH:$HOME/go/bin"
```

O `go install` coloca os plugins em `$HOME/go/bin`.
O `protoc` so encontra os plugins se esse diretorio estiver no PATH.

## Regeneracao do protobuf

Com as ferramentas instaladas, rodei:

```bash
make proto
```

Esse comando chama o `protoc` usando as regras do `Makefile`.
Ele regenera os arquivos Go em `internal/grpc/gen/tepv1`.

O primeiro problema foi falta de ferramentas: `make`, `protoc`, `go` e plugins.
Cada erro indicava uma dependencia ausente no Ubuntu recem-instalado.

Depois apareceu um erro de modulo antigo:

```text
generated file does not match prefix "github.com/Green-Cinnamon-Labs/tep-operator"
```

O `.proto` ainda apontava para o modulo antigo `cluster-api-provider-plc`.
Por isso o codigo gerado nao batia com o modulo atual `tep-operator`.

A correcao foi ajustar o `option go_package` em `tep-operator/proto/tep/v1/plant.proto`:

```proto
option go_package = "github.com/Green-Cinnamon-Labs/tep-operator/internal/grpc/gen/tepv1;tepv1";
```

Depois disso, `make proto` terminou sem erro.
Quando o `make` volta ao prompt sem `Error`, a geracao foi concluida.

## Rebuild do operator

Depois de regenerar os arquivos `.pb.go`, a imagem Docker do operator precisa ser reconstruida.
So mudar arquivos locais nao altera o container que ja esta rodando.

No Windows/PowerShell, o build usado foi:

```powershell
docker build -t plc-operator:latest c:/Projetos/tep/tep-operator
```

Esse comando cria uma nova imagem `plc-operator:latest` no Docker Desktop.
Mas o cluster Kind nao usa automaticamente essa imagem nova.

## Por que subir a imagem de novo no Kind

O Kind roda como um container separado, com cache de imagens proprio.
Entao a imagem nova precisa ser carregada para dentro do cluster.

O comando direto para isso e:

```bash
kind load docker-image plc-operator:latest --name tep-lab
```

Mesmo depois do `kind load`, um pod antigo nao troca de imagem sozinho.
E preciso reiniciar o Deployment para criar um pod novo.

O reinicio direto e:

```bash
kubectl rollout restart deployment/plc-operator
kubectl rollout status deployment/plc-operator --timeout=60s
```

O primeiro comando recria o pod do operator.
O segundo espera o rollout terminar ou falha se o operator continuar quebrando.

## Ajuste no setup.sh

O script `tep-supervisor/local/setup.sh` ja criava/validava o Kind, carregava a imagem e aplicava os manifests.
Mas ele nao garantia que o pod existente seria recriado apos carregar uma imagem nova.

Por isso foi adicionado ao final do script:

```bash
# A imagem plc-operator:latest foi carregada no Kind, mas pods existentes
# nao sao recriados automaticamente. Reinicia apenas o Deployment do operator
# para garantir que o novo pod use a imagem recem-carregada.
kubectl rollout restart deployment/plc-operator

# Aguarda o rollout terminar. Se o operator entrar em CrashLoop ou nao ficar
# pronto dentro do timeout, o setup falha aqui e o problema fica visivel.
kubectl rollout status deployment/plc-operator --timeout=60s
```

Isso reinicia apenas o operator.
Nao derruba `te-plant`, `tep-ihm` nem outros containers do Docker.

## Fluxo final esperado

Quando o protobuf do operator mudar:

```bash
cd /mnt/c/Projetos/tep/tep-operator
make proto
```

Depois, reconstruir a imagem:

```powershell
docker build -t plc-operator:latest c:/Projetos/tep/tep-operator
```

Depois, rodar o setup local:

```bash
bash c:/Projetos/tep/tep-supervisor/local/setup.sh
```

Com o ajuste no `setup.sh`, ele carrega a imagem no Kind e reinicia o operator.
Assim o pod novo deve usar a imagem recem-buildada.

## Validacao

Verificar se o pod ficou vivo:

```bash
kubectl get pods
```

Verificar se o CR recebeu status:

```bash
kubectl get plcmachine tep-baseline
```

Se ainda falhar, olhar os logs atuais e anteriores:

```bash
kubectl logs deploy/plc-operator
kubectl logs deploy/plc-operator --previous
```

Se o pod estiver `Running` e o `PLCMachine` tiver `PHASE`, o bloqueio do Exp 1 foi removido.
A partir dai da para documentar a conectividade e seguir para o baseline da issue #43.

