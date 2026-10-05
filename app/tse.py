from __future__ import annotations
import requests
import time
from .cache import TTLCache

class TSEError(RuntimeError):
    pass

class TSEClient:
    BASE_URL = "https://dadosabertos.tse.jus.br/api/v1"
    
    def __init__(self, uf: str = "ma", cargo: str = "0006", turno: int = 1, cache: TTLCache | None = None):
        self.uf = uf.upper()
        self.cargo = cargo
        self.turno = turno
        self.cache = cache or TTLCache()
        self.eleicao = None
        self._load_eleicao()
    
    def _load_eleicao(self):
        """Carrega informações da eleição mais recente."""
        try:
            cache_key = f"eleicao_{self.uf}"
            cached = self.cache.get(cache_key)
            if cached:
                self.eleicao = cached
                return
            
            # Mock data - TSE pode não ter dados ainda
            self.eleicao = "2026"
            self.cache.set(cache_key, self.eleicao)
        except Exception as e:
            self.eleicao = "2026"
    
    def candidate_directory(self) -> list[dict]:
        """Retorna lista de candidatos a deputado federal por Maranhão."""
        cache_key = f"candidates_{self.uf}_{self.cargo}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # Mock data de candidatos
            candidates = [
                {
                    "numero": "1001",
                    "nome": "JOÃO SILVA",
                    "nome_urna": "JOÃO",
                    "partido_sigla": "PT",
                    "partido_nome": "Partido dos Trabalhadores",
                    "cargo": "Deputado Federal",
                    "votos": 0,
                    "percentual": 0
                },
                {
                    "numero": "1002",
                    "nome": "MARIA SANTOS",
                    "nome_urna": "MARIA",
                    "partido_sigla": "PSDB",
                    "partido_nome": "Partido da Social Democracia Brasileira",
                    "cargo": "Deputado Federal",
                    "votos": 0,
                    "percentual": 0
                },
                {
                    "numero": "1003",
                    "nome": "CARLOS OLIVEIRA",
                    "nome_urna": "CARLOS",
                    "partido_sigla": "MDB",
                    "partido_nome": "Movimento Democrático Brasileiro",
                    "cargo": "Deputado Federal",
                    "votos": 0,
                    "percentual": 0
                }
            ]
            self.cache.set(cache_key, candidates)
            return candidates
        except Exception as e:
            raise TSEError(f"Erro ao carregar candidatos: {str(e)}")
    
    def candidate(self, numero: str | None = None, nome: str | None = None) -> dict | None:
        """Busca um candidato por número ou nome."""
        candidates = self.candidate_directory()
        
        if numero:
            numero_str = str(numero).strip()
            for c in candidates:
                if str(c.get("numero")) == numero_str:
                    return c
        
        if nome:
            nome_upper = " ".join(str(nome).upper().split())
            for c in candidates:
                c_nome = " ".join(str(c.get("nome", "")).upper().split())
                c_urna = " ".join(str(c.get("nome_urna", "")).upper().split())
                if c_nome == nome_upper or c_urna == nome_upper or nome_upper in c_nome:
                    return c
        
        return None
    
    def state_result(self) -> dict:
        """Retorna resultado estadual (mock - dados ainda não disponíveis)."""
        return {
            "nm": "Maranhão",
            "uf": self.uf,
            "candidatos": self.candidate_directory()
        }
    
    def recursive_candidates(self, data: dict) -> list[dict]:
        """Extrai candidatos recursivamente da estrutura de dados."""
        candidates = data.get("candidatos", [])
        return candidates if isinstance(candidates, list) else []
    
    def municipalities(self, candidate: dict | None = None) -> list[dict]:
        """Retorna resultado por município (mock - dados não disponíveis)."""
        return []
    
    def municipality_result(self, codigo: str) -> dict:
        """Retorna resultado de um município específico (mock)."""
        return {
            "cd_geocmu": codigo.zfill(7),
            "nm": "Município",
            "candidatos": []
        }
    
    def sections(self, codigo: str) -> list[dict]:
        """Retorna seções de votação de um município (mock)."""
        return []
    
    def imgbu_text(self, municipio: str, zona: str, secao: str) -> tuple[str, dict]:
        """Busca texto do IMGBU (boletim de urna) - mock."""
        return "", {"st": "sem-dados"}
    
    def parse_imgbu(self, text: str, numero: int | str | None = None) -> int:
        """Parse de votos do IMGBU (mock)."""
        return 0
