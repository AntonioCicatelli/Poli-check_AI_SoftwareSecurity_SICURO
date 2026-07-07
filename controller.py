import os
import requests
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from log import Logger
from pydantic import BaseModel, Field

class InputText(BaseModel):
    """
    Data model for the input text used in POST requests.
    """
    text: str = Field(..., min_length=1, max_length=5000)

load_dotenv("key.env")

class Controller:
    def __init__(self):
        """
        Initializes the Controller instance.
        """
        self.logger = Logger(self.__class__.__name__).get_logger()

        self.ollama_server_url = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:8000")
        self.neo4j_server_url = os.getenv("NEO4J_API_URL", "http://127.0.0.1:8002")
        self.backend_server_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8001")

        self.app = FastAPI()

        self.app.add_api_route(
            path="/results",
            endpoint=self.post_results,
            methods=["POST"],
            response_model=dict,
            summary="Call backend run_pipeline API"
        )
        self.app.add_api_route(
            path="/clean_conversations",
            endpoint=self.clean_conversations,
            methods=["POST"],
            response_model=dict,
            summary="Clean conversations"
        )
        self.app.add_api_route(
            path="/conversations",
            endpoint=self.get_conversation,
            methods=["GET"],
            response_model=dict,
            summary="Get history of conversations"
        )
        
        if os.getenv("DOCKER") != "true":
            self._start_servers()

    def post_results(self, input_text: InputText):
        """
        Processes a text by calling the backend's /run_pipeline API.
        """
        data = {"text": input_text.text}
        try:
            response = requests.post(f"{self.backend_server_url}/run_pipeline", json=data)
            
            # Gestiamo in modo pacifico l'errore 400 del Gatekeeper
            if response.status_code == 400:
                error_data = response.json()
                detail = error_data.get("detail", "")
                
                # Se è un blocco del Gatekeeper, lo passiamo alla Dashboard in modo "pulito"
                if "DOMAIN_REJECTED" in detail or "SSRF_REJECTED" in detail:
                    clean_message = detail.replace("DOMAIN_REJECTED: ", "").replace("SSRF_REJECTED: ", "")
                    return {
                        "status_code": 200, # Diciamo alla Dashboard che la comunicazione è ok
                        "response": {
                            "gatekeeper_rejected": True,
                            "message": clean_message
                        }
                    }
                else:
                    raise HTTPException(status_code=400, detail=detail)

            elif response.status_code != 200:
                self.logger.error(f"Error from backend: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return {
                "status_code": response.status_code,
                "response": response.json()
            }
        except Exception as e:
            self.logger.error(f"Error calling run_pipeline: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def clean_conversations(self):
        try:
            response = requests.post(f"{self.backend_server_url}/delete_db")
            if response.status_code != 200:
                self.logger.error(f"Error from backend on delete_db: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return {}
        except Exception as e:
            self.logger.error(f"Error calling delete_db: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_conversation(self):
        try:
            response = requests.get(f"{self.backend_server_url}/get_history")
            if response.status_code != 200:
                self.logger.error(f"Error from backend on get_history: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            response = {
                "status_code": response.status_code,
                "response": response.json()
            }
            return response
        except Exception as e:
            self.logger.error(f"Error calling get_history: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _start_servers(self):
        try:
            url = f"{self.ollama_server_url}/start"
            requests.post(url)
            self.logger.info("Ollama server started successfully.")
        except Exception as e:
            self.logger.error(f"Error starting Ollama server: {e}")

        try:
            url = f"{self.neo4j_server_url}/start"
            requests.post(url)
            self.logger.info("Neo4j server started successfully.")
        except Exception as e:
            self.logger.error(f"Error starting Neo4j server: {e}")

    def stop_servers(self):
        try:
            url = f"{self.ollama_server_url}/stop"
            requests.post(url)
            self.logger.info("Ollama server stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping Ollama server: {e}")

        try:
            url = f"{self.neo4j_server_url}/stop"
            requests.post(url)
            self.logger.info("Neo4j server stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping Neo4j server: {e}")
            
controller = Controller()
app = controller.app