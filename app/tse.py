from __future__ import annotations
import re
import time
from typing import Any
import requests

BASE = "https://resultados.tse.jus.br/oficial"

class TSEError(RuntimeError):
    pass

class TSEClient:
    def __init__(self, uf="ma", cargo="0006", turno=1, cache=None):
        self.uf = uf.lower()
        self.cargo = str(cargo).zfill(4)
        self.turno = int(turno)
        self.cache = cache
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "MA-Eleicoes-2026-Portfolio/1.0"
        })
        self.eleicao = None
        self.pleito = None
        self.ciclo = None

    def get_json(self, url, cache_key=None):
        if cache_key and self.cache:
            v = self.cache.get(cache_key)
            if v is not None:
                return v
        r = self.s.get(url, timeout=30)
        if r.status_code != 200:
            raise TSEError(f"TSE HTTP {r.status_code}: {url}")
        try:
            data = r.json()
        except Exception as e:
            raise TSEError(f"Resposta não-JSON do TSE: {url}") from e
        if cache_key and self.cache:
            self.cache.set(cache_key, data)
        return data

    def bootstrap(self):
        if self.eleicao:
            return
        cfg = self.get_json(f"{BASE}/comum/config/ele-c.json", "ele-c")
        ciclo = None
        pleito = None
        eleicao = None

        def walk(x):
            if isinstance(x, dict):
                yield x
                for v in x.values():
                    yield from walk(v)
            elif isinstance(x, list):
                for v in x:
                    yield from walk(v)

        for obj in walk(cfg):
            if not isinstance(obj, dict):
                continue
            text = " ".join(str(v) for v in obj.values() if isinstance(v, (str,int)))
            low = text.lower()
            if "elei" in low and "2026" in low and ("estadual" in low or "geral" in low):
                if obj.get("cd"):
                    eleicao = str(obj["cd"])
                    break

        # Produção 2026: o TSE publicou os códigos 6257/6259/6261.
        # Deputado Federal está no pleito estadual 6259.
        eleicao = eleicao or "6259"
        pleito = "3220"
        ciclo = "ele2026"

        self.eleicao, self.pleito, self.ciclo = eleicao, pleito, ciclo

    def state_result(self):
        self.bootstrap()
        url = f"{BASE}/{self.ciclo}/{self.eleicao}/dados/{self.uf}/{self.uf}-c{self.cargo}-e{self.eleicao}-u.json"
        return self.get_json(url, f"state:{self.uf}:{self.cargo}:{self.eleicao}")

    def municipalities_config(self):
        self.bootstrap()
        url = f"{BASE}/{self.ciclo}/{self.eleicao}/config/mun-e{self.eleicao}-cm.json"
        return self.get_json(url, f"municipalities:{self.uf}:{self.eleicao}")

    @staticmethod
    def recursive_candidates(obj):
        found = []
        def walk(x, cargo_name=None):
            if isinstance(x, dict):
                current_cargo = x.get("nmn") or x.get("ds") or cargo_name
                if "cand" in x and isinstance(x["cand"], list):
                    for c in x["cand"]:
                        if isinstance(c, dict):
                            found.append({
                                **c,
                                "cargo_nome": current_cargo,
                                "partido_sigla": x.get("sg"),
                                "partido_nome": x.get("nm"),
                            })
                for v in x.values():
                    walk(v, current_cargo)
            elif isinstance(x, list):
                for v in x:
                    walk(v, cargo_name)
        walk(obj)
        # remove duplicates
        out, seen = [], set()
        for c in found:
            key=(str(c.get("n")),str(c.get("nm")))
            if key not in seen:
                seen.add(key); out.append(c)
        return out

    def candidate(self, numero="", nome=""):
        candidates = self.recursive_candidates(self.state_result())
        numero = str(numero).strip()
        nome = " ".join(str(nome).upper().split())
        for c in candidates:
            if numero and str(c.get("n")) == numero:
                return c
        if nome:
            for c in candidates:
                if " ".join(str(c.get("nm","")).upper().split()) == nome:
                    return c
            for c in candidates:
                if nome in " ".join(str(c.get("nm","")).upper().split()):
                    return c
        return None

    def municipalities(self, candidate):
        # O EA20 estadual pode trazer a distribuição municipal em diferentes
        # estruturas. Em vez de assumir um único layout, procuramos objetos
        # que possuam código/nome municipal e votação do candidato.
        state = self.state_result()
        target = str(candidate.get("n"))
        rows=[]

        def walk(x, parent=None):
            if isinstance(x, dict):
                keys={str(k).lower() for k in x}
                code=x.get("cd") or x.get("cod") or x.get("codigo")
                name=x.get("nm") or x.get("nome")
                if code and name and len(str(code)) in (4,5) and isinstance(x.get("cand"),list):
                    for c in x["cand"]:
                        if str(c.get("n"))==target:
                            rows.append({
                                "codigo":str(code).zfill(5),
                                "nome":name,
                                "votos":int(c.get("vap") or c.get("votos") or 0),
                                "percentual":c.get("pvap") or c.get("percentual") or 0
                            })
                for v in x.values():
                    walk(v,x)
            elif isinstance(x,list):
                for v in x:
                    walk(v,parent)
        walk(state)

        # Remove duplicates.
        out={}
        for r in rows:
            out[r["codigo"]]=r
        return list(out.values())

    def municipality_result(self, codigo):
        self.bootstrap()
        codigo=str(codigo).zfill(5)
        url=f"{BASE}/{self.ciclo}/{self.eleicao}/dados/{self.uf}/{self.uf}{codigo}-c{self.cargo}-e{self.eleicao}-u.json"
        return self.get_json(url, f"municipality:{self.uf}:{codigo}:{self.cargo}:{self.eleicao}")

    def sections_config(self):
        self.bootstrap()
        url=f"{BASE}/arquivo-urna/{self.pleito}/config/{self.uf}/{self.uf}-p{self.pleito}-cs.json"
        return self.get_json(url, f"sections:{self.uf}:{self.pleito}")

    def sections(self, municipio):
        data=self.sections_config()
        out=[]
        for abr in data.get("abr",[]):
            if str(abr.get("cd","")).lower()!=self.uf:
                continue
            for mu in abr.get("mu",[]):
                if str(mu.get("cd")).zfill(5)!=str(municipio).zfill(5):
                    continue
                for z in mu.get("zon",[]):
                    for sec in z.get("sec",[]):
                        out.append({
                            "municipio_codigo":str(mu.get("cd")).zfill(5),
                            "municipio_nome":mu.get("nm"),
                            "zona":str(z.get("cd")).zfill(4),
                            "secao":str(sec.get("ns")).zfill(4),
                            "principal":sec.get("nsp"),
                            "agregadas":sec.get("nsa"),
                        })
        return out

    def section_aux(self, municipio, zona, secao):
        self.bootstrap()
        municipio=str(municipio).zfill(5)
        zona=str(zona).zfill(4)
        secao=str(secao).zfill(4)
        filename=f"p{self.pleito}-{self.uf}-m{municipio}-z{zona}-s{secao}-aux.json"
        url=f"{BASE}/arquivo-urna/{self.pleito}/dados/{self.uf}/{municipio}/{zona}/{secao}/{filename}"
        return self.get_json(url, f"aux:{self.uf}:{municipio}:{zona}:{secao}:{self.pleito}")

    def imgbu_text(self, municipio, zona, secao):
        aux=self.section_aux(municipio,zona,secao)
        hashes=aux.get("hashes") or []
        if not hashes:
            return None, aux
        # Usa o hash mais recente que tenha arquivo IMGBU.
        chosen=None
        for h in reversed(hashes):
            files=h.get("arq") or h.get("nmarq") or []
            names=[]
            for f in files:
                names.append(f.get("nm") if isinstance(f,dict) else f)
            for nm in names:
                if str(nm).lower().endswith(".imgbu"):
                    chosen=(h,nm); break
            if chosen: break
        if not chosen:
            return None, aux
        h,nm=chosen
        url=f"{BASE}/arquivo-urna/{self.pleito}/dados/{self.uf}/{str(municipio).zfill(5)}/{str(zona).zfill(4)}/{str(secao).zfill(4)}/{h['hash']}/{nm}"
        r=self.s.get(url,timeout=30)
        if r.status_code!=200:
            return None, aux
        return r.content.decode("latin1","ignore"), aux

    @staticmethod
    def parse_imgbu(text, candidate_number):
        if not text:
            return None
        candidate_number=str(candidate_number)
        # Remove controles de impressão, mantendo separadores.
        clean=re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
        clean=re.sub(r"\s+"," ",clean)

        # Trabalha primeiro no trecho do cargo de Deputado Federal (0006/6).
        chunks=re.split(r"\bCARG\s*[:=]\s*", clean, flags=re.I)
        for chunk in chunks[1:]:
            header=chunk[:120]
            if re.search(r"\b6\b|0006",header):
                patterns=[
                    rf"(?<!\d){re.escape(candidate_number)}\s*[:=]\s*(\d+)",
                    rf"(?<!\d){re.escape(candidate_number)}\s+(\d+)(?!\d)",
                    rf"\b{re.escape(candidate_number)}\b[^\d]{{1,8}}(\d+)"
                ]
                for p in patterns:
                    m=re.search(p,chunk)
                    if m:
                        return int(m.group(1))
        # Fallback global.
        for p in [
            rf"(?<!\d){re.escape(candidate_number)}\s*[:=]\s*(\d+)",
            rf"(?<!\d){re.escape(candidate_number)}\s+(\d+)(?!\d)"
        ]:
            m=re.search(p,clean)
            if m:
                return int(m.group(1))
        return None
