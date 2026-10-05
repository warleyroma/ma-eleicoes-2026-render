from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    tse_uf: str = "ma"
    tse_cargo: str = "0006"
    tse_turno: int = 1
    candidato_numero: str = ""
    candidato_nome: str = ""
    cache_ttl: int = 300
    geocode_enabled: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
