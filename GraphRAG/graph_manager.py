import os
import time
import dotenv
import platform
import requests
import numpy as np
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from langchain_neo4j import Neo4jGraph
from log import Logger

class GraphManager:
    def __init__(self, env_file="key.env"):
        """
        Initializes the GraphManager by setting up the Neo4j connection.
        """
        dotenv.load_dotenv(env_file, override=True)
        self.logger = Logger(self.__class__.__name__).get_logger()
        self.platform = platform.system()

        if not self._is_neo4j_running():
            raise ConnectionError("Neo4j server is not running. Please start it.")
        
        # Neo4j connection parameters
        self.neo4j_url = os.environ["NEO4J_URI"].replace("http", "bolt")
        self.neo4j_username = os.environ["NEO4J_USERNAME"]
        self.neo4j_password = os.environ["NEO4J_PASSWORD"]

        # Initialize graph connection
        self.graph = Neo4jGraph(
            url=self.neo4j_url,
            username=self.neo4j_username,
            password=self.neo4j_password,
        )

        try:
            self.graph.query("RETURN 1")
            self.logger.info("Successfully connected to Neo4j.")
        except Exception as e:
            self.logger.error(f"Error during Neo4j connection: {e}")
            raise ConnectionError(f"Error during Neo4j connection: {e}")
    
    def reset_data(self):
        """
        Resets the database. 
        NOTE: Now this should ONLY be called when the user explicitly clears the chat history.
        """
        self.logger.info("Starting data reset process...")
        
        try:
            start_time = time.time()
            
            delete_queries = [
                "MATCH (a:Article) DETACH DELETE a",
                "MATCH (e:Politici) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Partiti_Movimenti) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Istituzioni) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Legislazione) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Eventi_Elettorali) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Stati_Nazioni) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Organizzazioni_Internazionali) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Conflitti_Eventi_Geopolitici) WHERE NOT (e)<-[:MENTIONS]-() DELETE e",
                "MATCH (e:Entity) WHERE NOT (e)<-[:MENTIONS]-() DELETE e", 
                "MATCH (s:Site) WHERE NOT (s)<-[:PUBLISHED_ON]-() DELETE s",
                "MATCH (t:Topic) WHERE NOT (t)<-[:HAS_TOPIC]-() DELETE t"
            ]
            
            for query in delete_queries:
                self.graph.query(query)

            elapsed_time = time.time() - start_time
            self.logger.info(f"Data reset completed in {elapsed_time:.2f} seconds.")
            
            self.graph.refresh_schema()
            self.logger.info("Schema refreshed successfully.")

        except Exception as e:
            self.logger.error(f"Error during data reset: {e}")

    def load_data(self, data):
        """
        Loads data into the Neo4j graph using specific political entity categories.
        Because we use MERGE, existing entities and sites will be linked rather than duplicated.
        """
        q_load_articles = """
        UNWIND $data AS article
        MERGE (a:Article {title: article.title})
        SET a.url = article.url,
            a.body = article.body

        MERGE (s:Site {name: article.site})
        MERGE (a)-[:PUBLISHED_ON]->(s)

        // Gestione del Topic
        WITH a, article
        MERGE (t:Topic {name: article.topic})
        MERGE (a)-[:HAS_TOPIC]->(t)

        // Gestione Entità: Politici
        WITH a, article
        UNWIND (CASE WHEN article.entities.Politici IS NOT NULL THEN article.entities.Politici ELSE [] END) AS pol
        MERGE (e:Politici {name: pol})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Partiti o Movimenti
        WITH a, article
        UNWIND (CASE WHEN article.entities.Partiti_Movimenti IS NOT NULL THEN article.entities.Partiti_Movimenti ELSE [] END) AS part
        MERGE (e:Partiti_Movimenti {name: part})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Istituzioni
        WITH a, article
        UNWIND (CASE WHEN article.entities.Istituzioni IS NOT NULL THEN article.entities.Istituzioni ELSE [] END) AS ist
        MERGE (e:Istituzioni {name: ist})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Legislazione
        WITH a, article
        UNWIND (CASE WHEN article.entities.Legislazione IS NOT NULL THEN article.entities.Legislazione ELSE [] END) AS leg
        MERGE (e:Legislazione {name: leg})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Eventi Elettorali
        WITH a, article
        UNWIND (CASE WHEN article.entities.Eventi_Elettorali IS NOT NULL THEN article.entities.Eventi_Elettorali ELSE [] END) AS ev
        MERGE (e:Eventi_Elettorali {name: ev})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Stati e Nazioni
        WITH a, article
        UNWIND (CASE WHEN article.entities.Stati_Nazioni IS NOT NULL THEN article.entities.Stati_Nazioni ELSE [] END) AS stat
        MERGE (e:Stati_Nazioni {name: stat})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Organizzazioni Internazionali
        WITH a, article
        UNWIND (CASE WHEN article.entities.Organizzazioni_Internazionali IS NOT NULL THEN article.entities.Organizzazioni_Internazionali ELSE [] END) AS org
        MERGE (e:Organizzazioni_Internazionali {name: org})
        MERGE (a)-[:MENTIONS]->(e)

        // Gestione Entità: Conflitti ed Eventi Geopolitici
        WITH a, article
        UNWIND (CASE WHEN article.entities.Conflitti_Eventi_Geopolitici IS NOT NULL THEN article.entities.Conflitti_Eventi_Geopolitici ELSE [] END) AS conf
        MERGE (e:Conflitti_Eventi_Geopolitici {name: conf})
        MERGE (a)-[:MENTIONS]->(e)
        """
        
        try:
            start_time = time.time()
            self.graph.query(q_load_articles, params={"data": data})
            elapsed_time = time.time() - start_time
            self.logger.info(f"Loading completed in {elapsed_time:.2f} seconds.")
        except Exception as e:
            self.logger.error(f"Error during data loading: {e}")
        
        self.graph.refresh_schema()

    def extract_and_save_graph(self, current_titles, output_file_topic, output_file_entity, output_file_site):
        """
        Executes a query on Neo4j for the CURRENT context, creates the graph, and saves it as a JPEG file.
        """
        try:
            blue_light = "#add8e6"  
        
            def create_and_save_graph(query, params, node_relation, node_label, edge_label, output_file):
                results = pd.DataFrame(self.graph.query(query, params=params))
                
                if results.empty:
                    self.logger.warning(f"No data found for graph {output_file}. Skipping generation.")
                    return

                G = nx.DiGraph()
                
                for _, row in results.iterrows():
                    G.add_edge(row[node_relation[0]], row[node_relation[1]], label=edge_label)

                colors = list(mcolors.TABLEAU_COLORS.values())
                color_map = {}
                unique_nodes = results[node_relation[1]].unique() 
                for i, node in enumerate(unique_nodes):
                    color_map[node] = colors[i % len(colors)] 

                node_colors = []
                for node in G.nodes():
                    if node in color_map:
                        node_colors.append(color_map[node])
                    else:  
                        node_colors.append(blue_light)

                edge_colors = []
                edge_labels = {}  
                for u, v, data in G.edges(data=True):
                    edge_colors.append(color_map[v])  
                    edge_labels[(u, v)] = data['label']  

                max_len = 15 
                labels = {}

                def split_label(label, max_len):
                    if len(label) <= max_len:
                        return label  
                    first_line = label[:max_len]
                    if len(first_line) == max_len:
                        first_line = first_line[:first_line.rfind(' ')] 
                        second_line = label[len(first_line):]
                    else:
                        second_line = label[len(first_line):]
                    
                    if len(second_line) > max_len:
                        second_line = second_line[:max_len] + "..."
                    
                    return f"{first_line}\n{second_line}"

                for node in G.nodes():
                    node_label = f"{node}" 
                    label_text = split_label(node_label, max_len)
                    labels[node] = label_text

                pos = nx.spring_layout(G, k=1.5, iterations=50)

                matplotlib.use('Agg')
                 
                plt.figure(figsize=(12, 9))
                nx.draw(
                    G,
                    labels=labels,
                    pos=pos,
                    with_labels=True,
                    node_color=node_colors,
                    edge_color=edge_colors,
                    node_size=3500,
                    font_size=6,
                    width=2
                )

                nx.draw_networkx_edge_labels(
                    G,
                    pos,
                    edge_labels=edge_labels,
                    font_size=6,
                    font_color="black"
                )

                plt.savefig(output_file, dpi=500)
                plt.close()

            # The queries now match current articles AND ANY historical article that shares the same target node
            
            # First graph: (Article)-[:HAS_TOPIC]->(Topic)
            query_topic = """
            MATCH (current:Article)
            WHERE current.title IN $titles
            MATCH (current)-[:HAS_TOPIC]->(t:Topic)
            MATCH (historical:Article)-[:HAS_TOPIC]->(t)
            RETURN DISTINCT historical.title AS Article, t.name AS Topic
            """
            create_and_save_graph(query_topic, {"titles": current_titles}, ("Article", "Topic"), "Topic", "HAS_TOPIC", output_file_topic)

            # Second graph: (Article)-[:MENTIONS]->(e)
            query_mentions = """
            MATCH (current:Article)
            WHERE current.title IN $titles
            MATCH (current)-[:MENTIONS]->(e)
            MATCH (historical:Article)-[:MENTIONS]->(e)
            RETURN DISTINCT historical.title AS Article, e.name AS Entity
            """
            create_and_save_graph(query_mentions, {"titles": current_titles}, ("Article", "Entity"), "Entity", "MENTIONS", output_file_entity)

            # Third graph: (Article)-[:PUBLISHED_ON]->(Site)
            query_site = """
            MATCH (current:Article)
            WHERE current.title IN $titles
            MATCH (current)-[:PUBLISHED_ON]->(s:Site)
            MATCH (historical:Article)-[:PUBLISHED_ON]->(s)
            RETURN DISTINCT historical.title AS Article, s.name AS Site
            """
            create_and_save_graph(query_site, {"titles": current_titles}, ("Article", "Site"), "Site", "PUBLISHED_ON", output_file_site)

            self.logger.info("Graphs generated and saved successfully.")
        except Exception as e:
            self.logger.error(f"Error during graph extraction and saving: {e}")

    def _is_neo4j_running(self):
        try:
            response = requests.get(os.getenv("NEO4J_SERVER_URL"), timeout=5)  
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False