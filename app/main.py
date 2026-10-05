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

@app.get("/")
def home():
    return FileResponse(ROOT/"static/index.html")

@app.get("/api/health")
def health():
    return {"status":"ok","uf":settings.tse_uf,"cargo":settings.tse_cargo,"eleicao":tse.eleicao or "auto"}

@app.get("/api/candidatos")
def candidatos():
    try:
        data=tse.state_result()
        candidates=tse.recursive_candidates(data)
        return sorted([
            {"numero":c.get("n"),"nome":c.get("nm"),"partido":c.get("partido_sigla"),"cargo":c.get("cargo_nome")}
            for c in candidates
        ],key=lambda x:str(x["nome"] or ""))
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/api/candidato")
def candidato():
    try:
        c=tse.candidate(settings.candidato_numero,settings.candidato_nome)
        if not c:
            raise HTTPException(404,"Candidato não encontrado. Configure CANDIDATO_NUMERO ou CANDIDATO_NOME.")
        return {
            "numero":c.get("n"),"nome":c.get("nm"),"nome_urna":c.get("nmu"),
            "partido_sigla":c.get("partido_sigla"),"partido_nome":c.get("partido_nome"),
            "cargo":c.get("cargo_nome"),"votos":int(c.get("vap") or c.get("votos") or 0),
            "percentual":c.get("pvap") or c.get("percentual")
        }
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/api/municipios")
def municipios():
    try:
        c=tse.candidate(settings.candidato_numero,settings.candidato_nome)
        if not c: raise HTTPException(404,"Candidato não encontrado.")
        rows=tse.municipalities(c)
        # Se o EA20 estadual não trouxer a distribuição municipal, a interface
        # continuará funcional via endpoint individual.
        return rows
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/api/municipios/{codigo}")
def municipio(codigo:str):
    try:
        data=tse.municipality_result(codigo)
        c=tse.candidate(settings.candidato_numero,settings.candidato_nome)
        if not c: raise HTTPException(404,"Candidato não encontrado.")
        target=str(c.get("n"))
        rows=[]
        for cand in tse.recursive_candidates(data):
            if str(cand.get("n"))==target:
                return {
                    "codigo":str(codigo).zfill(5),
                    "nome":data.get("nm") or data.get("nome"),
                    "numero":target,
                    "votos":int(cand.get("vap") or 0),
                    "percentual":cand.get("pvap")
                }
        return {"codigo":str(codigo).zfill(5),"nome":data.get("nm") or data.get("nome"),"numero":target,"votos":0}
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/api/municipios/{codigo}/secoes")
def secoes(codigo:str):
    try:
        return tse.sections(codigo)
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/api/secoes/{municipio}/{zona}/{secao}")
def secao(municipio:str,zona:str,secao:str):
    try:
        c=tse.candidate(settings.candidato_numero,settings.candidato_nome)
        if not c: raise HTTPException(404,"Candidato não encontrado.")
        text,aux=tse.imgbu_text(municipio,zona,secao)
        votes=tse.parse_imgbu(text,c.get("n"))
        return {
            "municipio":str(municipio).zfill(5),
            "zona":str(zona).zfill(4),
            "secao":str(secao).zfill(4),
            "situacao":aux.get("st"),
            "votos":votes,
            "arquivo_disponivel":bool(text),
            "mensagem":None if text else "Arquivo IMGBU ainda não disponível para esta seção."
        }
    except TSEError as e:
        raise HTTPException(502,str(e))

@app.get("/{path:path}")
def static(path:str):
    p=ROOT/"static"/path
    if p.exists() and p.is_file(): return FileResponse(p)
    return FileResponse(ROOT/"static/index.html")
