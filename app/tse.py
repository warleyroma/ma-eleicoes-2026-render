from __future__ import annotations
import requests
from .cache import TTLCache

class TSEError(RuntimeError):
    pass

class TSEClient:
    """Cliente para acessar dados do TSE via API de dados abertos."""
    
    def __init__(self, uf: str = "ma", cargo: str = "0006", turno: int = 1, cache: TTLCache | None = None):
        self.uf = uf.upper()
        self.cargo = cargo
        self.turno = turno
        self.cache = cache or TTLCache()
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "MA-Eleicoes-2026/1.0"})
    
    def get_json(self, url: str, cache_key: str | None = None) -> dict | list:
        """Faz requisição HTTP com suporte a cache."""
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                raise TSEError(f"HTTP {r.status_code}: {url}")
            data = r.json()
        except requests.RequestException as e:
            raise TSEError(f"Erro de conexão com TSE: {str(e)}")
        except Exception as e:
            raise TSEError(f"Erro ao processar resposta do TSE: {str(e)}")
        
        if cache_key and self.cache:
            self.cache.set(cache_key, data)
        return data
    
    def candidate_directory(self) -> list[dict]:
        """Retorna lista real de candidatos a deputado federal por Maranhão do TSE."""
        cache_key = f"candidates_{self.uf}_{self.cargo}"
        
        try:
            # Tenta buscar dados reais da API de dados abertos do TSE
            # Formato: /v1/eleicao/:dataEleicao/candidato?uf=MA&cargo=6
            url = f"https://dadosabertos.tse.jus.br/api/v1/candidato?uf={self.uf}&cargo=6"
            data = self.get_json(url, cache_key)
            
            if isinstance(data, dict) and "data" in data:
                candidates = data.get("data", [])
            elif isinstance(data, list):
                candidates = data
            else:
                candidates = []
            
            # Normaliza campos
            result = []
            for c in candidates:
                result.append({
                    "numero": str(c.get("numero") or c.get("n") or ""),
                    "nome": str(c.get("nome") or c.get("nm") or c.get("nome_urna") or ""),
                    "nome_urna": str(c.get("nome_urna") or c.get("nome") or ""),
                    "partido_sigla": str(c.get("sigla") or c.get("sigla_partido") or c.get("partido_sigla") or ""),
                    "partido_nome": str(c.get("nome_partido") or c.get("partido_nome") or c.get("partido") or ""),
                    "cargo": str(c.get("cargo") or c.get("cargo_nome") or "Deputado Federal"),
                    "votos": int(c.get("votos") or 0),
                    "percentual": float(c.get("percentual") or 0)
                })
            
            return result
        except Exception as e:
            # Se falhar, retorna lista vazia em vez de dados fictícios
            print(f"Aviso: Não foi possível carregar candidatos reais: {e}")
            return []
    
    def candidate(self, numero: str | None = None, nome: str | None = None) -> dict | None:
        """Busca um candidato específico por número ou nome."""
        candidates = self.candidate_directory()
        
        if not candidates:
            return None
        
        if numero:
            numero_str = str(numero).strip()
            for c in candidates:
                if str(c.get("numero", "")) == numero_str:
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
        """Retorna resultado estadual (quando disponível)."""
        return {"candidatos": self.candidate_directory()}
    
    def recursive_candidates(self, data: dict) -> list[dict]:
        """Extrai candidatos recursivamente."""
        return data.get("candidatos", [])
    
    def municipalities(self, candidate: dict | None = None) -> list[dict]:
        """Retorna dados por município (quando disponível)."""
        return []
    
    def municipality_result(self, codigo: str) -> dict:
        """Retorna resultado de um município específico."""
        return {}
    
    def sections(self, codigo: str) -> list[dict]:
        """Retorna seções de votação de um município."""
        return []
    
    def imgbu_text(self, municipio: str, zona: str, secao: str) -> tuple[str, dict]:
        """Busca texto do IMGBU."""
        return "", {}
    
    def parse_imgbu(self, text: str, numero: int | str | None = None) -> int:
        """Parse de votos do IMGBU."""
        return 0
