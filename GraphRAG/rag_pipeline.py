import dotenv
import time
import os
from GraphRAG.graph_manager import GraphManager
from GraphRAG.query_engine import QueryEngine
from log import Logger

class RAG_Pipeline:
    def __init__(self, env_file="key.env", config=None):
        """
        Initializes the RAG Pipeline, setting up environment variables, logging, graph manager, and query engine.

        Args:
            env_file (str): Path to the .env file containing configuration settings.
            config (dict, optional): Custom configuration to override default settings (load_data, generate_graphs, query_similarity).
        
        Raises:
            KeyError: If required environment variables are missing.
        """
        dotenv.load_dotenv(env_file, override=True)

        # Logger
        self.logger = Logger(self.__class__.__name__).get_logger()

        # Configures the GraphManager
        self.graph_manager = GraphManager(env_file)

        # Configures the QueryEngine
        self.query_engine = QueryEngine(env_file)

        # Customizable configuration
        self.config = {
            "load_data": True,             # Enables/disables data loading
            "generate_graphs": True,       # Enables/disables graph generation
            "query_similarity": True       # Enables/disables similarity queries
        }
        if config:
            self.config.update(config)
        
        #self.graph_manager.reset_data()

        self.graph_folder = os.getenv("ASSET_PATH")

        if not os.path.exists(self.graph_folder):
            os.makedirs(self.graph_folder)
            self.logger.info(f"Create '{self.graph_folder}' folder.")

    def load_data(self, data):
        """
        Loads the provided data into the graph via the GraphManager.

        Args:
            data (any): The data to be loaded into the graph.

        Raises:
            Exception: If there is an error during the data loading process.
        """
        if not self.config.get("load_data", True):
            self.logger.info("Data loading disabled by configuration.")
            return

        self.logger.info("Starting data loading...")
        try:
            self.graph_manager.load_data(data)
            self.query_engine.update_vector_index()
            self.logger.info("Data loaded and embedded successfully.")
        except Exception as e:
            self.logger.error(f"Error during data loading: {e}")
            raise

    def generate_and_save_graphs(self, current_data, output_folder):
        """
        Generates and saves graphs using the GraphManager.

        Args:
            output_folder (str): The folder path to save the generated graphs.

        Raises:
            Exception: If there is an error during graph generation.
        """
        if not self.config.get("generate_graphs", True):
            self.logger.info("Graph generation disabled by configuration.")
            return
        
        path_graph_topics=f"{output_folder}/graph_topics.jpg"
        path_graph_entities=f"{output_folder}/graph_entities.jpg"
        path_graph_sites=f"{output_folder}/graph_sites.jpg"

        self.logger.info("Starting graph generation...")
        try:
            titles = [item['title'] for item in current_data]
            self.graph_manager.extract_and_save_graph(titles, path_graph_topics, path_graph_entities, path_graph_sites)
        except Exception as e:
            self.logger.error(f"Error during graph generation: {e}")

    def query_similarity(self, query):
        """
        Executes a similarity query using the QueryEngine.

        Args:
            query (str): The query string to be executed for similarity-based retrieval.
        
        Raises:
            Exception: If there is an error during the similarity query execution.
        
        Returns:
            str: The result of the similarity query, or None if the query is disabled or an error occurs.
        """
        if not self.config.get("query_similarity", True):
            self.logger.info("Similarity query disabled by configuration.")
            return None

        self.logger.info("Starting similarity query...")
        try:
            result = self.query_engine.query_similarity(query)
            self.logger.info("Similarity query completed.")
            return result
        except Exception as e:
            self.logger.error(f"Error during similarity query execution: {e}")
            return None

    def run_pipeline(self, data, claim, claim_id):
        """
        Executes the entire pipeline: load data, generate graphs, and respond to the query.

        Args:
            data (any): The data to be loaded into the graph.
            claim (str): The claim to be verified.
            claim_id (str): The unique identifier for the claim (used for folders).
    
        Raises:
            Exception: If there is an error during any step of the pipeline.
        
        Returns:
            tuple: The result of the similarity query and the graph folder path, or (None, None) if an error occurs.
        """
        self.logger.info("Starting the entire pipeline...")
        start_time = time.time()  # Start time measurement
        try:
            # Step 1: Load the data
            self.load_data(data)

            claim_graphs_folder = f"{self.graph_folder}/{claim_id}"

            if not os.path.exists(claim_graphs_folder):
                os.makedirs(claim_graphs_folder)
                self.logger.info(f"Create '{claim_graphs_folder}' folder.")

            # Step 2: Generate and save graphs
            self.generate_and_save_graphs(data, claim_graphs_folder)
            
            # Step 3: Execute the similarity query
            # NOTA: Ora passiamo solo il "claim". Tutto il prompt complesso 
            # (regole, formattazione, ruolo) è gestito internamente dal QueryEngine!
            
            # Aggiungiamo un'istruzione ferrea direttamente in coda al claim per forzare la lingua
            claim_with_language_instruction = f"{claim}\n\n[SYSTEM INSTRUCTION: You MUST write your final response in the EXACT SAME LANGUAGE as the original claim above.]"
            
            result = self.query_similarity(claim_with_language_instruction)

            # Calculate total execution time
            total_time = time.time() - start_time
            self.logger.info(f"Pipeline completed successfully in {total_time:.2f} seconds.")

            return result, claim_graphs_folder
        except Exception as e:
            total_time = time.time() - start_time
            self.logger.error(f"Error during pipeline execution (total time: {total_time:.2f} seconds): {e}")
            return None, None