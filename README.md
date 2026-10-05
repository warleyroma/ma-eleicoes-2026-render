# MA Eleições 2026 — Mapa de votação por candidato

Aplicação web independente para visualizar a votação de **um candidato a Deputado Federal no Maranhão**, por município e por seção/local de votação.

## Fontes

Os resultados são obtidos diretamente da infraestrutura pública de divulgação do TSE. O TSE informa que entidades podem criar soluções próprias de divulgação, observadas as regras técnicas, limites de acesso e legislação. A documentação de 2026 define EA11/EA12/EA16/EA18/EA20 e o acesso público aos resultados. 

- TSE — resultados: https://resultados.tse.jus.br
- TSE — documentação 2026: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados
- TSE — Eleições 2026: https://www.tse.jus.br/eleicoes/eleicoes-2026
- GeoJSON municipal: IBGE, via dataset público usado apenas para desenho dos municípios.

## O que esta versão faz

1. identifica automaticamente os códigos de eleição/pleito no `ele-c.json`;
2. consulta Deputado Federal no Maranhão;
3. permite fixar um candidato por `CANDIDATO_NUMERO` ou `CANDIDATO_NOME`;
4. mostra total de votos;
5. mostra mapa dos municípios;
6. mostra votação municipal;
7. ao clicar em município, consulta as zonas/seções;
8. ao clicar em uma seção, consulta o EA18 e o arquivo `imgbu` do TSE;
9. extrai a votação nominal do candidato daquela urna;
10. mostra local/endereço quando disponível;
11. tenta geocodificar o local para posicionar o marcador;
12. mantém cache em memória para reduzir chamadas ao TSE;
13. não grava dados pessoais de eleitores.

O TSE explica que o BU contém a votação individual das candidaturas e identifica município, zona, local e seção. citehttps://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026

## Importante sobre a seção

A documentação do TSE estabelece a hierarquia:

```text
EA11
  ↓
EA12
  ↓
EA16
  ↓
EA18
  ↓
arquivos da urna
  ↓
BU / IMGBU
```

O EA18 informa os hashes e nomes dos arquivos disponíveis para uma seção. O TSE orienta que, para chegar a um arquivo de urna, deve-se consultar EA16, depois EA18 e então montar a URL do arquivo. citeturn1search17

A aplicação usa preferencialmente o `imgbu`, porque ele é o espelho textual do boletim e evita colocar um parser ASN.1 grande dentro do serviço web. Se o `imgbu` não estiver disponível, a interface informa que a seção não pôde ser detalhada.

## Render

A configuração já está em `render.yaml`.

### Deploy

1. Crie um repositório no GitHub.
2. Envie todo o conteúdo desta pasta.
3. No Render, escolha **New → Blueprint**.
4. Selecione o repositório.
5. O Render lerá `render.yaml`.

O serviço utiliza:

```text
Build:
pip install -r requirements.txt

Start:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Esse é o formato recomendado pela documentação do Render para FastAPI. citeturn0search8

## Variáveis de ambiente

### Obrigatórias

```text
CANDIDATO_NUMERO
```

ou

```text
CANDIDATO_NOME
```

Exemplo:

```text
CANDIDATO_NUMERO=12345
```

Você pode deixar ambos vazios para a aplicação listar os candidatos disponíveis na tela de configuração.

### Opcionais

```text
TSE_UF=ma
TSE_CARGO=0006
TSE_TURNO=1
CACHE_TTL=300
GEOCODE_ENABLED=true
```

## Desenvolvimento local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra:

```text
http://127.0.0.1:8000
```

## Estrutura

```text
ma-eleicoes-2026-render/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── cache.py
│   └── tse.py
│
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── scripts/
│   └── smoke_test.py
│
├── tests/
│   └── test_parser.py
│
├── requirements.txt
├── render.yaml
├── Dockerfile
└── README.md
```

## Neutralidade e identificação

Este projeto apenas exibe resultados eleitorais oficiais e dados descritivos. Não faz recomendação de candidato, previsão eleitoral ou avaliação política.

O site deve deixar visível:

> Projeto independente. Dados eleitorais: Tribunal Superior Eleitoral (TSE).

## Limites

O TSE informa limite de 100 requisições por IP por segundo e alerta que múltiplos 404 podem causar bloqueio temporário. A aplicação evita varreduras automáticas de todos os BUs e consulta somente o município/seção solicitados, mantendo cache. citeturn0search0
