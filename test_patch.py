import toml
import requests
from datetime import datetime

secrets = toml.load('.streamlit/secrets.toml')
firebase_api_key = secrets['FIREBASE_API_KEY']
base_url = "https://firestore.googleapis.com/v1/projects/site-departamento/databases/(default)/documents"

url = f'{base_url}/solicitacoes?key={firebase_api_key}'
try:
    all_docs = requests.get(url).json()
    first_doc_id = all_docs['documents'][0]['name'].split('/')[-1]
    
    novo_array = [
        {
            "legenda": "Testing legenda with \n new lines and stuff",
            "imagem_url": "https://fakeurl.com",
            "prompt_texto": "Prompt 1",
            "prompt_imagem": "Prompt 2",
            "tempo_segundos": 4.5,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
    ]
    
    map_values_list = []
    for tentativa in novo_array:
        fields = {}
        for k, v in tentativa.items():
            if isinstance(v, float) or isinstance(v, int):
                fields[k] = {"doubleValue": float(v)}
            else:
                fields[k] = {"stringValue": str(v) if v is not None else ""}
                
        map_values_list.append({"mapValue": {"fields": fields}})
        
    url_patch = f'{base_url}/solicitacoes/{first_doc_id}?updateMask.fieldPaths=tentativas_ia&key={firebase_api_key}'
    payload = {'fields': {'tentativas_ia': {'arrayValue': {'values': map_values_list}}}}
    
    res = requests.patch(url_patch, json=payload)
    print("STATUS", res.status_code)
    print("TEXT", res.text)
except Exception as e:
    print("ERROR", str(e))
