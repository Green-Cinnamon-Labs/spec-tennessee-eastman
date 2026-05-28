# TEP Analysis — Pacote de Análise

Pacote Python para visualização dos CSVs gerados pela simulação do Tennessee Eastman Digital Twin.

## Por que este pacote existe

- Separar lógica de plot e análise de dados do serviço de simulação em Rust
- Fornecer um CLI (`plot`) para geração rápida de gráficos
- Garantir isolamento de dependências via Poetry

## Pré-requisitos

Execute a partir do diretório `analysis/`:

```bash
poetry install
```

(Opcional) verificar o ambiente virtual:

```bash
poetry env info --path
```

## Comandos

### 1. Gerar plot (CSV padrão)

```bash
poetry run plot
```

Usa o entry point definido em `pyproject.toml`: `plot = "tep_analysis.plot:main"`

### 2. Gerar plot com CSV específico

```bash
poetry run plot --csv ../tennessee-eastman-service/simulation_log.csv
```

### 3. Comando equivalente via módulo Python

```bash
poetry run python -m tep_analysis.plot
```

## Verificar ambiente virtual

```bash
poetry run python -c "import sys; print(sys.executable)"
```

O caminho deve apontar para o ambiente virtual do Poetry, não para o Python global.

## Saída

A imagem do plot é salva ao lado do CSV, com extensão `.png`.

Exemplo:
- `../tennessee-eastman-service/simulation_log.csv`
- `../tennessee-eastman-service/simulation_log.png`
