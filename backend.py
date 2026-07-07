from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from WebScraper.scraper import Scraper
from Preprocessor.preprocessing_pipeline import Preprocessing_Pipeline
from Database.data_entities import Claim, Answer
from Database.sqldb import Database
from GraphRAG.rag_pipeline import RAG_Pipeline
from GraphRAG.graph_manager import GraphManager
import urllib.parse
import requests
from bs4 import BeautifulSoup

#LIBRERIE INSERITE PER SVENTARE ATTACCO SSRF
import socket
import ipaddress
from urllib3.util.connection import create_connection
from requests.adapters import HTTPAdapter
import threading

backend_app = FastAPI()

db = Database()

class InputText(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class PinnedIPAdapter(HTTPAdapter):
        """
        Forza le connessioni HTTP a usare un IP specifico già validato,
        invece di lasciare che venga risolto di nuovo (e potenzialmente diversamente) da requests.
        """
        _lock = threading.Lock()  # lock condiviso a livello di classe

        def __init__(self, pinned_ip, *args, **kwargs):
            self.pinned_ip = pinned_ip
            super().__init__(*args, **kwargs)

        def init_poolmanager(self, *args, **kwargs):
            kwargs['source_address'] = None
            super().init_poolmanager(*args, **kwargs)

        def send(self, request, **kwargs):
            # Sostituiamo temporaneamente la risoluzione DNS con l'IP già validato
            original_create_connection = create_connection

            def patched_create_connection(address, *args, **kwargs):
                host, port = address
                return original_create_connection((self.pinned_ip, port), *args, **kwargs)

            import urllib3.util.connection as urllib3_conn
            with PinnedIPAdapter._lock:  # <-- serializza l'accesso alla variabile globale
                urllib3_conn.create_connection = patched_create_connection
                try:
                    return super().send(request, **kwargs)
                finally:
                    urllib3_conn.create_connection = original_create_connection


def resolve_safe_ip(url: str):
    """
    Risolve l'hostname e restituisce un IP sicuro da usare per il pinning,
    oppure None se l'host non è sicuro o non risolvibile.
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            return None

        ip_addresses = socket.getaddrinfo(hostname, None)

        private_networks = [
            ipaddress.ip_network('0.0.0.0/8'),        # Esteso da /32 a /8 (RFC 1122 "this network")
            ipaddress.ip_network('127.0.0.0/8'),
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
            ipaddress.ip_network('169.254.0.0/16'),
            ipaddress.ip_network('::1/128'),
            ipaddress.ip_network('fe80::/10'),
            ipaddress.ip_network('fc00::/7'),
        ]

        safe_ip = None
        for item in ip_addresses:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            # FIX: normalizza gli indirizzi IPv4-mapped IPv6 (es. ::ffff:127.0.0.1)
            if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped

            for network in private_networks:
                if ip_obj.version == network.version and ip_obj in network:
                    return None  # Trovato anche un solo IP pericoloso -> blocca tutto

            if safe_ip is None:
                safe_ip = ip_str  # Teniamo il primo IP valido da "pinnare"

        return safe_ip

    except Exception:
        return None



@backend_app.post("/run_pipeline")
def process_text(input_text: InputText):
    text = input_text.text
    
    # --- LOGICA SICURA: Prevenzione SSRF (con IP pinning anti-rebinding) ---
    parsed_url = urllib.parse.urlparse(text)
    if parsed_url.scheme in ["http", "https"] and parsed_url.netloc:
        
        MAX_REDIRECTS = 5
        current_url = text
        final_body = None
        final_title = ""
        
        for _ in range(MAX_REDIRECTS):
            safe_ip = resolve_safe_ip(current_url)
            if safe_ip is None:
                raise HTTPException(
                    status_code=400,
                    detail="SSRF_REJECTED: Accesso negato: L'URL fornito punta a una risorsa interna o non autorizzata."
                )
            
            try:
                session = requests.Session()
                session.mount("http://", PinnedIPAdapter(safe_ip))
                session.mount("https://", PinnedIPAdapter(safe_ip))
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                # FIX: disabilitiamo i redirect automatici, li gestiamo manualmente
                response = session.get(current_url, headers=headers, timeout=10, allow_redirects=False)
                
                # Se è un redirect, ripetiamo il ciclo validando il NUOVO url
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        raise HTTPException(status_code=400, detail="Redirect non valido ricevuto dall'URL fornito.")
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue  # torna in cima al for: valida il nuovo URL da zero
                
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                final_title = soup.title.string if soup.title else ""
                final_body = soup.get_text(separator=' ', strip=True)
                break  # nessun redirect: abbiamo il contenuto, usciamo dal ciclo
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Impossibile estrarre il contenuto dall'URL fornito: {str(e)}")
        else:
            # Il for è terminato senza 'break' -> troppi redirect in catena
            raise HTTPException(status_code=400, detail="Troppi redirect: possibile tentativo di elusione dei controlli di sicurezza.")

        text = f"Verifica questa notizia estratta dal web: Titolo: {final_title}. Contenuto: {final_body}"[:3000]
    # --- FINE LOGICA SICURA ---

    preprocessor = Preprocessing_Pipeline()
    
    try:
        # FASE 1: Preprocessing e Gatekeeper (utilizzerà 'text' che ora contiene il testo dell'URL o il testo originale)
        claim_title, web_search_query, claim_summary = preprocessor.run_claim_pipe(text)
    # ... RESTO DEL CODICE INVARIATO (da except ValueError as e: in poi) ...
    
    except ValueError as e:
        # Se il Gatekeeper rifiuta la notizia (es. non è politica), restituiamo un errore 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Fallback per altri errori imprevisti nel preprocessing
        raise HTTPException(status_code=500, detail=f"Errore di preprocessing: {str(e)}")

    claim = Claim(text, claim_title, claim_summary)
    
    try:
        # FASE 2: Web Scraping
        scraper = Scraper()
        sources = scraper.search_and_extract(claim_title, web_search_query, num_results=10)
        if not sources:
            # Interrompiamo la pipeline qui e restituiamo il messaggio pulito per la dashboard
            return {
                "claim_title": claim_title, 
                "claim_summary": "No reliable sources were found to verify this query. The system exhausted all search attempts.", 
                "sources": [], 
                "query_result": "Unverifiable news, no source found 🟡", 
                "graphs_folder": ""
            }
        preprocessed_sources = preprocessor.run_sources_pipe(sources)
        claim.add_sources(preprocessed_sources)
        
        # FASE 3: Graph RAG
        rag = RAG_Pipeline()
        query_result, graphs_folder = rag.run_pipeline(preprocessed_sources, claim.text, claim.id)

        # --- NUOVO CONTROLLO DI SICUREZZA IN USCITA ---
        # Usiamo l'istanza di 'preprocessor' già creata nella FASE 1
        # Costruiamo un unico blob testuale con tutto ciò che uscirà verso il client
        sources_text = " ".join(
            f"{s.get('body', '')} {s.get('topic', '')}" for s in preprocessed_sources
        )
        full_output_to_check = f"{query_result}\n{sources_text}"

        output_safety = preprocessor.check_output_safety(full_output_to_check)

        if not output_safety["is_safe"]:
            raise HTTPException(
                status_code=403,
                detail=f"SECURITY_VIOLATION: {output_safety['reason']}"
            )
        # --- FINE CONTROLLO ---

        answer = Answer(claim.id, query_result, graphs_folder)
        
        return {
            "claim_title": claim_title, 
            "claim_summary": claim_summary, 
            "sources": preprocessed_sources, 
            "query_result": query_result, 
            "graphs_folder": graphs_folder
        }
    except Exception as e:
        # Evitiamo che errori di scraping o generazione crashino brutalmente il backend
        raise HTTPException(status_code=500, detail=f"Errore interno durante l'elaborazione: {str(e)}")


@backend_app.post("/delete_db")
def delete_database():
    # Cancella la cronologia SQLite e i file locali
    db.delete_all_conversations()
    
    # AGGIUNGI QUESTO: Resetta anche il grafo persistente su Neo4j
    try:
        gm = GraphManager()
        gm.reset_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel reset del grafo: {str(e)}")


@backend_app.get("/get_history")
def get_history():
    history = db.get_history()
    return history


    

  

