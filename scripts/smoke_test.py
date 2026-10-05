import requests, sys

base=sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8000"
for path in ["/api/health","/api/candidatos","/api/candidato"]:
    r=requests.get(base+path,timeout=30)
    print(path,r.status_code,r.text[:300])
