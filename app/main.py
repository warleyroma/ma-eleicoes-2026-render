from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .cache import TTLCache
from .tse import TSEClient, TSEError

ROOT=Path(__file__).resolve().parent.parent
cache=TTLCache(settings.cache_ttl)
tse=TSEClient(settings.tse_uf,settings.tse_cargo,settings.tse_turno,cache)

app=FastAPI(title="MA Eleições 2026",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])


def resolve_candidate(numero: str | None = None, nome: str | None = None):
    numero = (numero or settings.candidato_numero or "").strip()
    nome = (nome or settings.candidato_nome or "").strip()

    # Primeiro tenta candidato em ambiente / busca direta.
    c = tse.candidate(numero, nome)
    if c:
        return c

    # Fallback: consulta a base oficial de candidatos do TSE.
    candidates = tse.candidate_directory()
    if not candidates:
        return None

    if numero:
        for cand in candidates:
            if str(cand.get("numero")) == numero:
                return cand
    if nome:
        n = " ".join(str(nome).upper().split())
        for cand in candidates:
            if " ".join(str(cand.get("nome", "")).upper().split()) == n:
                return cand
            if n in " ".join(str(cand.get("nome", "")).upper().split()):
                return cand
    return None


@app.get("/")
def home():
    return FileResponse(ROOT/"static/index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "uf": settings.tse_uf,
        "cargo": settings.tse_cargo,
        "eleicao": tse.eleicao or "auto",
        "source": "tse-dados-abertos",
    }


@app.get("/api/candidatos")
def candidatos():
    try:
        candidates = tse.candidate_directory()
        if not candidates:
            raise HTTPException(404, "Nenhum candidato encontrado na fonte oficial do TSE neste momento.")
        return sorted(candidates, key=lambda x: str(x.get("nome") or ""))
    except TSEError as e:
        raise HTTPException(502, str(e))


@app.get("/api/candidato")
def candidato(numero: str | None = Query(default=None), nome: str | None = Query(default=None)):
    try:
        c = resolve_candidate(numero, nome)
        if not c:
            raise HTTPException(404, "Candidato não encontrado. Defina CANDIDATO_NUMERO ou CANDIDATO_NOME ou selecione um candidato no frontend.")
        return {
            "numero": c.get("numero") or c.get("n"),
            "nome": c.get("nome") or c.get("nm") or c.get("nome_urna"),
            "nome_urna": c.get("nome_urna") or c.get("nome") or c.get("nm"),
            "partido_sigla": c.get("partido_sigla") or c.get("partido") or c.get("sigla_partido"),
            "partido_nome": c.get("partido_nome") or c.get("partido"),
            "cargo": c.get("cargo") or c.get("cargo_nome") or settings.tse_cargo,
            "votos": int(c.get("votos") or c.get("vap") or 0),
            "percentual": c.get("percentual") or c.get("pvap") or 0,
        }
    except TSEError as e:
        raise HTTPException(502, str(e))


@app.get("/api/municipios")
def municipios(numero: str | None = Query(default=None), nome: str | None = Query(default=None)):
    try:
        c = resolve_candidate(numero, nome)
        if not c:
            return []
        # O TSE só libera resultados por município/urna quando o pleito está em andamento/encerrado.
        # Enquanto isso, não há dados eleitorais consolidados para consumo por município.
        return []
    except TSEError as e:
        raise HTTPException(502, str(e))


@app.get("/api/municipios/{codigo}")
def municipio(codigo:str, numero: str | None = Query(default=None), nome: str | None = Query(default=None)):
    try:
        c = resolve_candidate(numero, nome)
        if not c:
            raise HTTPException(404, "Candidato não encontrado.")
        return {"codigo": str(codigo).zfill(5), "nome": "Dados de município indisponíveis no TSE ainda", "numero": str(c.get("numero") or ""), "votos": 0}
    except TSEError as e:
        raise HTTPException(502, str(e))


@app.get("/api/municipios/{codigo}/secoes")
def secoes(codigo:str):
    return []


@app.get("/api/secoes/{municipio}/{zona}/{secao}")
def secao(municipio:str, zona:str, secao:str, numero: str | None = Query(default=None), nome: str | None = Query(default=None)):
    return {
        "municipio": str(municipio).zfill(5),
        "zona": str(zona).zfill(4),
        "secao": str(secao).zfill(4),
        "situacao": "dados-ainda-nao-divulgados",
        "votos": 0,
        "arquivo_disponivel": False,
        "mensagem": "Os dados de urna e resultados por seção ainda não foram publicados oficialmente pelo TSE para este pleito."
    }


@app.get("/{path:path}")
def static(path:str):
    p=ROOT/"static"/path
    if p.exists() and p.is_file(): return FileResponse(p)
    return FileResponse(ROOT/"static/index.html")
