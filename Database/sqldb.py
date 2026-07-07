import os
import sqlite3
import glob
import dotenv
import shutil
from log import Logger

class Database:
    def __init__(self, env_file="key.env"):
        """
        Initializes the Database class with the database file path.

        Args:
            env_file (str): The env file containing the API keys or database file paths. Default: "key.env".
        
        Raises:
            KeyError: If the environment variable for the database file path is not set.
        """
        self.logger = Logger(self.__class__.__name__).get_logger()
        try:
            dotenv.load_dotenv(env_file, override=True)
            self.db_file = os.environ["SQLDB_PATH"]
            self.assets_dir = os.environ["ASSET_PATH"]
        except KeyError as e:
            self.logger.error("Environment variable SQLDB_PATH not found.")
            raise e

        db_dir = os.path.dirname(self.db_file)  
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            self.logger.info("Created directory for the database file: %s", db_dir)

    def __enter__(self):
        """
        Establishes a connection to the SQLite database.

        Returns:
            sqlite3.Connection: A connection object to interact with the database.
        
        Raises:
            sqlite3.DatabaseError: If the connection to the database fails.
        """
        self.logger.info("Connecting to the SQLite database.")
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row
            self.logger.info("Successfully connected to the database.")
            return self.conn
        except sqlite3.DatabaseError as e:
            self.logger.error("Failed to connect to the database.")
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the SQLite database connection when the context manager is exited.
        """
        if self.conn:
            self.logger.info("Closing the database connection.")
            try:
                self.conn.close()
            except Exception as e:
                self.logger.error("Error while closing the database connection.")
                raise e

    def create_table(self, create_table_sql):
        """
        Creates a table in the SQLite database using the provided SQL statement.
        """
        self.logger.info("Creating table with SQL...")
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                conn.commit()
            self.logger.info("Table created successfully.")
        except sqlite3.DatabaseError as e:
            self.logger.error("Error creating table.")
            raise e

    def execute_query(self, query, params=()):
        """
        Executes a query on the SQLite database.
        """
        masked_params = [param if not isinstance(param, (bytes, bytearray)) else "BLOB" for param in params]
        self.logger.info("Executing query: %s", query)

        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
            self.logger.info("Query executed successfully.")
        except sqlite3.DatabaseError as e:
            self.logger.error("Error executing query.")
            raise e

    def fetch_all(self, query, params=()):
        """
        Fetches all records that match the provided SQL query.
        """
        self.logger.info("Fetching all records for query: %s with params: %s", query, params)
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
            self.logger.info("Fetched %d records.", len(result))
            return result
        except sqlite3.DatabaseError as e:
            self.logger.error("Error fetching records.")
            raise e
    
    def fetch_one(self, query, params=()):
        """
        Fetches the first record that matches the provided SQL query.
        """
        self.logger.info("Fetching one record for query: %s with params: %s", query, params)
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
            self.logger.info("Fetched one record.")
            return result
        except sqlite3.DatabaseError as e:
            self.logger.error("Error fetching record.")
            raise e

    def delete_all_conversations(self):
        """
        Deletes data from tables "claims", "answers", and "sources", and cleans up all images in subdirectories of the assets folder.
        """
        self.logger.info("Deleting all conversations and cleaning up subdirectories in assets.")
        try:
            # Deleting conversations from the database
            with self as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM claims;")
                cursor.execute("DELETE FROM answers;")
                cursor.execute("DELETE FROM sources;")
                conn.commit()
            self.logger.info("All conversations deleted successfully.")

            # Clean up subdirectories in the assets folder
            if os.path.isdir(self.assets_dir):
                for root, dirs, _ in os.walk(self.assets_dir, topdown=False):
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            shutil.rmtree(dir_path)
                            self.logger.info(f"Deleted directory and its contents: {dir_path}")
                        except OSError as e:
                            self.logger.error(f"Error deleting directory {dir_path}: {e}")
            else:
                self.logger.warning(f"Assets folder does not exist: {self.assets_dir}")
                
        except sqlite3.DatabaseError as e:
            self.logger.error("Error deleting conversations.")
            raise e
        except OSError as e:
            self.logger.error("Error cleaning up assets.")
            raise e
        
    def get_history(self):
        """
        Retrieves the conversations from the database, including their associated sources and any related images.
        """
        # Verifichiamo prima se la tabella esiste per evitare il crash a database vuoto
        check_table_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='claims';"
        
        try:
            table_exists = self.fetch_one(check_table_query)
            if not table_exists:
                self.logger.info("Database tables 'claims' not found. Returning empty history.")
                return [] # Ritorna una lista vuota in modo sicuro

            # Query to fetch claims and their associated answers
            query = """
            SELECT c.id, c.text, c.title, c.summary, a.answer, a.graphs_folder 
            FROM claims c
            INNER JOIN answers a ON c.id = a.claim_id
            """

            rows = self.fetch_all(query)

            if not rows:
                return []

            conversations = []

            for row in rows:
                claim_id = row[0]
                
                # Query to fetch sources associated with the claim
                sources_query = """
                SELECT title, url, body 
                FROM sources 
                WHERE claim_id = ?
                """
                sources_rows = self.fetch_all(sources_query, (claim_id,))

                # Format sources as a list of dictionaries
                sources = [{"title": s[0], "url": s[1], "body": s[2]} for s in sources_rows]

                images = []
                graphs_folder = row[5]
                jpg_files = []
                if graphs_folder and os.path.isdir(graphs_folder):
                    jpg_files = glob.glob(os.path.join(graphs_folder, "*.jpg"))
                else:
                    self.logger.warning("La cartella dei grafici non esiste o non è stata specificata.")

                # Append the conversation data to the list
                conversations.append({
                    "id": claim_id,
                    "claim": row[1],
                    "title": row[2],
                    "summary": row[3],
                    "answer": row[4],
                    "images": jpg_files,
                    "sources": sources 
                })

            return conversations
            
        except Exception as e:
            self.logger.error(f"Error while fetching history: {e}")
            return []