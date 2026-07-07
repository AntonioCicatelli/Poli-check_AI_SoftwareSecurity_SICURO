![Logo](Dashboard/logo_non_trasparente.png)

**Poli-check AI** is an advanced microservices-based application designed to evaluate the reliability of political news through state-of-the-art fact-checking techniques, leveraging highly credible sources and a Graph-based Retrieval-Augmented Generation (GraphRAG) architecture.

Beginning with a claim provided by the user via an interactive dashboard, the system first verifies the domain relevance (ensuring the input is political) and then retrieves related web articles to assess the claim based on the reliability of the sources found. 

To ensure high accuracy in source selection and verification, the system performs a multi-tier search and dual filtering process:

1. **Dynamic Blacklist Filtering**: Instead of relying solely on a static ranking, sources are filtered using a dynamically loaded blacklist (e.g., OpenSources) to immediately exclude unreliable domains, known fake news sites, and pages lacking "reliable" or "political" classifications.
2. **Multi-Tier Search Strategy**: The system attempts a fast-track verification using the Google Fact Check API. If verified articles are not found, it falls back to a semantic web search powered by the Tavily API, navigating the web while actively ignoring blacklisted domains.
3. **Correlation Testing**: An additional correlation test is conducted using an LLM to verify the relevance and alignment between the scraped web source and the claim to be validated. This step minimizes the risk of selecting irrelevant or misleading articles.

Once validated, these articles undergo Named Entity Recognition (NER) to extract key political entities and are linked within a Neo4j GraphRAG framework. Finally, a Large Language Model (LLM) analyzes the graph context and generates a fluid, objective response in the user's original language.

**Objectives**:

- **Truthfulness Assessment**: Determine the truthfulness of the analyzed political news item—classifying it as True (🟢), False (🔴), or Unverifiable (🟡)—based exclusively on the identified web sources.
- **Transparent Explanations**: Provide clear and unbiased explanations of the verification process, explicitly citing the online articles and sources used in the final evaluation.
- **Knowledge Graphs**: Generate specific knowledge graphs mapping the relationships between the original claim, political entities (politicians, institutions, states, ...), and publishing sites to enhance interpretability.
- **Comprehensive Reporting**: Deliver a user-friendly, interactive chat interface accessible via a Streamlit dashboard, complete with visual graphs, source links, and conversational history.

### Tools and Technologies

- **Dashboard**: Built using **Streamlit** to provide an interactive and intuitive user interface for claim submission, conversational history, and visual graph exploration.
- **Backend & Microservices**: Powered by FastAPI to orchestrate the communication between the dashboard, the data processing pipeline, and local system processes.
- **Large Language Models (LLMs)**: Leverages **Groq Cloud** (e.g., Llama-3 models) for ultra-fast reasoning, summarization, correlation filtering, and Named Entity Recognition (NER), alongside **Ollama** for local text embeddings.
- **GraphRAG Framework**: Utilizes **Neo4j** as a vector and graph database to construct, store, and analyze complex relational knowledge graphs mapping political entities and web sources.
- **Search & Scraping**: Integrates the **Google Fact Check API** for fast-track verification, the **Tavily API** for advanced semantic web search, and **BeautifulSoup** for precise HTML content extraction.
- **Orchestration & Storage**: Uses **LangChain** to tie the Retrieval-Augmented Generation (RAG) pipeline together and **SQLite** for lightweight, persistent management of user queries and cached web sources.

![Poli-check_AI_Architecture](Dashboard/System.png)

---

## Prerequisites
To use this project, you need to configure the following tools:

1. **Docker Setup** *(Recommended)*
   - If using Docker, you can skip the manual installation steps below.
2. **Python Libraries** *(Manual Installation Only)*
3. **Neo4j** *(Manual Installation Only)*
4. **Ollama** *(Manual Installation Only)*
5. **API Keys** *(Google Fact Check, Tavily, and Groq Cloud)*

## Option 1: Run with Docker *(Recommended)*

To simplify the setup process, you can run the application using Docker. Ensure your **key.env** file is properly configured with **DOCKER=true** and your API keys before starting.
There are two options depending on your system:

### Standard Docker Setup
For systems that do not have a GPU compatible with CUDA, use the following command to start the application:
```bash
docker compose up --build
```

### GPU-Accelerated Setup (NVIDIA GPUs Required)
If your system has an NVIDIA GPU and supports CUDA, you can use the GPU-accelerated version for faster LLM local embeddings. Ensure that you have the **NVIDIA Container Toolkit** installed before running the following command:

- **Installation Guide:** [NVIDIA Container Toolkit Installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

- Note: if you are using **Docker Desktop on Windows**, the NVIDIA Container Toolkit is already included.

Once the toolkit is installed, run:
```bash
docker-compose -f docker-compose-gpu.yml build
docker-compose -f docker-compose-gpu.yml up
```

Note: Neo4j authentication is disabled by default in standard Docker configurations, so you may not need to provide a username and password depending on your **docker-compose** setup.

## Option 2: Manual Installation
If you prefer to install and run the application locally without Docker, follow these steps:

### Step 1: Set Up the Environment

#### 1. Create and activate a new virtual environment:
```bash
conda create --name myenv python=3.13.1
conda activate myenv
```

#### 2. Install the required Python libraries:
```bash
pip install -r requirements.txt
```

### Step 2: Neo4j Setup

#### Download Neo4j
Download the Community Edition of Neo4j Graph Database from the following link: [Neo4j Deployment Center](https://neo4j.com/deployment-center/).

Note: In the local version, you must configure the username and password for Neo4j. Update the **NEO4J_USERNAME** and **NEO4J_PASSWORD** variables in your **key.env** file accordingly.

#### Configure APOC
1. Copy the `apoc-5.26.1-core.jar` file from the `labs` folder and paste it into the `plugins` folder. Rename the copied file to `apoc.jar`.
2. Edit the `neo4j.conf` file in the `conf` folder and add the following lines at the end of the file:
   ```
   # Configure the plugin directory
   server.directories.plugins=plugins

   # Enable APOC procedures
   dbms.security.procedures.unrestricted=apoc.*, algo.*

   dbms.security.procedures.allowlist=apoc.meta.data,apoc.help
   ```

#### Set Up Environment Variables
1. Add the path to the `bin` folder of Neo4j to your system's environment variables:

   - **Windows:**
     1. Open the Start menu and search for "Environment Variables".
     2. Under "System Variables", find the **Path** variable, click "Edit", then "New", and add the path to your Neo4j **bin** folder (e.g., C:\neo4j\bin).
   
   - **Mac:**
     1. Open the terminal.
     2. Edit the `~/.zshrc` or `~/.bash_profile` file (depending on your shell) by adding:
        ```
        export PATH=$PATH:/path/to/neo4j/bin
        ```
     3. Save the file and reload the configuration by running:
        ```bash
        source ~/.zshrc
        ```

### Step 3: Ollama Setup

#### Download Ollama
1. Visit the official website: [Ollama](https://ollama.com/) and download the software for your platform.
Note: Ollama now offers a native Windows installer, so utilizing WSL (Windows Subsystem for Linux) is no longer strictly required, though it remains a valid alternative.

#### Download Models from Ollama
After installation, open your terminal or command prompt and download the default embedding model used by the GraphRAG pipeline:
```bash
ollama pull phi3.5
```

## Required Steps: API Configuration
Poli-check AI relies on external APIs for web search, fact-checking, and rapid language processing. You must configure these before running the application.

### Step 1: Search & Scraping APIs 
1. **Google Fact Check API**: Generate an API key from the [Google Cloud Console](https://console.cloud.google.com/) to enable the fast-track fact-check search.
2. **Tavily API**: Register at [Tavily](https://tavily.com/) to get an API key for the semantic web search fallback.  

### Step 2: Register on Groq Cloud
1. Register on [Groq Cloud](https://console.groq.com/).
2. Generate an API key. This will power the high-speed Llama models used for correlation filtering, NER, and response generation.

### Step 3: Create the `key.env` File

In case of launching with Docker, set `DOCKER=true` and uncomment all variables under the **Docker Version** section. Otherwise, set `DOCKER=false` and uncomment the variables under the **Local Version** section.

```env
DOCKER=true

# API URL Docker Version
OLLAMA_SERVER_URL=http://ollama:11434
NEO4J_SERVER_URL=http://neo4j:7474
OLLAMA_API_URL=http://ollama:11434
NEO4J_API_URL=http://neo4j:7474
BACKEND_API_URL=http://backend:8001
CONTROLLER_API_URL=http://controller:8003
NEO4J_URI=bolt://neo4j:7687

# API URL Local Version
# OLLAMA_SERVER_URL=http://localhost:11434
# NEO4J_SERVER_URL=http://localhost:7474
# OLLAMA_API_URL=http://localhost:8000
# NEO4J_API_URL=http://localhost:8002
# BACKEND_API_URL=http://localhost:8001
# CONTROLLER_API_URL=http://localhost:8003
# NEO4J_URI=bolt://localhost:7687

# DASHBOARD CONSTANTS
LOG_FILE=app.log
AI_IMAGE_UI=Dashboard/Logo.png

# GOOGLE FACT CHECK API KEY AND TAVILY API KEYS
GOOGLE_FACTCHECK_API_KEY=your_google_factcheck_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# DATABASE VARIABLES
SQLDB_PATH=data/fact_checker.db
ASSET_PATH=assets

# GRAPHRAG VARIABLES
MODEL_LLM_NEO4J=phi3.5:latest
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j

# GROQ VARIABLES
GROQ_MODEL_NAME=llama-3.3-70b-versatile
GROQ_LOW_MODEL_NAME=llama-3.1-8b-instant
GROQ_API_KEY=your_groq_api_key_here
```
---

## Project Overview  

The **Poli-check AI** system is designed to deliver robust political fact-checking capabilities by leveraging cutting-edge AI and modular architectural principles. Following an **object-oriented programming (OOP)** paradigm, each core component (e.g., Scraper, Summarizer, NER, QueryEngine) adheres to the **Single Responsibility Principle (SRP)**, ensuring high modularity and maintainability. The system employs a strict **pipeline architecture** to organize the workflow into discrete stages (Preprocessing, Multi-tier Web Scraping, and GraphRAG), improving scalability and error handling.  

The architecture follows a microservices model and consists of the following main components:  

- **Backend**: A FastAPI application that orchestrates the entire fact-checking pipeline, processes political claims, and interacts with the persistent SQLite database to store claims, validated sources, and conversational history.  
- **Dashboard**: A Streamlit-based interactive user interface that allows users to submit news, read the final verdicts, and explore visual knowledge graphs.  
- **Controller**: Functions as an **API Gateway**, managing communication between the frontend Dashboard and the Backend. In local deployments, it also coordinates the lifecycle (startup and shutdown) of background hardware-intensive servers.  

### Key Architectural Patterns  

- **API Gateway**: Implemented by the Controller, it centralizes access to the system's microservices, gracefully handles Gatekeeper rejections, and manages the local infrastructure via dedicated API calls.  
- **Pipeline Processing**: Implemented in the Backend, this design ensures modular and maintainable execution of distinct stages: domain validation, source retrieval (Google/Tavily), semantic filtering, NER extraction, and final LLM response generation.  

### Supporting Components  

To enhance functionality and ensure data privacy where necessary, the system integrates dedicated local and cloud servers:  

- **Ollama Server**: Executes local, lightweight Large Language Models specifically dedicated to computing vector embeddings for the text segments.  
- **Neo4j Console**: Handles the vector and graph database infrastructure, modeling complex semantic relationships between articles, political entities, and web sources.  

The system intelligently balances performance and hardware requirements by offloading heavy reasoning tasks (Named Entity Recognition, correlation filtering, and final text generation) to ultra-fast external APIs like **Groq Cloud** (using Llama 3 models), while keeping the embedding generation localized via Ollama. 

---

## Components  

### Preprocessing Components  

The Preprocessing phase acts as the data refinement engine, preparing both the user's initial query and the subsequently scraped articles for downstream evaluation. This step is essential for structuring the data and isolating the political entities required to build the **GraphRAG** network.

By leveraging **advanced LLMs**, the architecture balances speed and capability: **Groq Cloud APIs** execute complex semantic evaluations, while faster, localized models handle basic classification tasks to maintain system efficiency.   

1. **Summarizer**: Validates the political nature of the input, crafts highly optimized queries for different search engines, and generates neutral summaries.  
2. **NER (Named Entity Recognition)**: Isolates critical political actors, institutions, and geopolitical themes to establish the core nodes of the knowledge graph.  

#### Preprocessing Pipeline  

The **Preprocessing Pipeline** standardizes the flow of information, converting raw user inputs and unstructured web data into a cohesive format ready for deep fact-checking. It functions through two distinct phases:  

1. **Claim Preprocessing**  
    - Evaluates the domain using a lightweight model to instantly block non-political or off-topic queries.  
   - Utilizes the **llama-3.3** model via **Groq Cloud APIs** to generate a concise, 2-3 keyword string for exact-match searches, alongside a richer semantic query tailored for web crawlers.  
   - Produces a neutral, non-debunking summary of the claim in its original language to guide the final evaluation process.  

2. **Sources Preprocessing**  
    - Condenses the raw HTML body text of retrieved articles to accommodate the context window limits of the final RAG process.  
   - Deploys **NER** via Groq APIs to detect the primary topic and map extracted elements into specific geopolitical categories.  
   - Executes a global merging algorithm that standardizes entity aliases across all scraped documents (e.g., automatically linking "POTUS" and "Joe Biden" to a single, unified graph node).  

By structuring all inputs and scraped content, this pipeline establishes a pristine, reliable dataset for the verification engine workflows.

### Web Scraper Components  

The **Web Scraper** is tasked with intelligently navigating the internet to gather high-quality evidence while strictly filtering out misinformation. It operates through two primary modules:  

1. **Search Orchestrator & Dynamic Blacklist**  
   - Dynamically downloads the **OpenSources** dataset at runtime to maintain an up-to-date blacklist, immediately blocking domains flagged as fake news or conspiracies.  
   - Executes a fast-track query against the **Google Fact Check API** and falls back to the **Tavily API** for deep semantic searches, ensuring highly relevant and credible source retrieval while ignoring blocked sites.  

2. **Content Extractor & Correlation Filter**  
   - Employs web scraping techniques (**BeautifulSoup**) to extract the title and main body text from target URLs, carefully abiding by **robots.txt** rules and bypassing restricted access pages.  
   - Applies a final LLM-driven correlation test to read the extracted text and confirm it directly pertains to the user's claim, discarding irrelevant or clickbait articles before they reach the database.  

#### Web Scraping Pipeline 

The **Scraper** is implemented in the **Scraper class**, which orchestrates a multi-tiered search strategy utilizing the Google Fact Check API and the Tavily API, fortified by a dynamic reliability blacklist.

- **Main Method: `search_and_extract`**  
   It performs the web search and processes the results through three rigorous stages:

   1. **Search & Dynamic Filtering**
   Executes a fast-track query using the **Google Fact Check API**. If no results are found, it falls back to the **Tavily API** for a broader semantic search.  
      - Filters out unreliable results in real-time by actively excluding any domains present in the dynamically loaded **OpenSources blacklist**.  
      - Checks scraping permissions using the **can_scrape** method, which analyzes the target site's **robots.txt** file.

   2. **Content Extraction**  
      Uses the **extract_context** method to download and analyze web pages via **BeautifulSoup**. It safely extracts the title, body text, and domain, while intelligently bypassing or ignoring restricted pages (e.g., login prompts, paywalls, or captchas).

   3. **Correlation Filtering**  
      Applies the **correlation_filter**, which leverages a Groq Cloud LLM to verify the strict relevance of the extracted content to the user's specific claim. It ensures the source provides pertinent information before allowing it into the database.

This multi-stage process guarantees that only highly reliable, strictly relevant, and accessible sources are passed to the knowledge graph.

### GraphRAG Components 

The GraphRAG management components are responsible for ingesting, structuring, and analyzing the validated data to generate a highly contextualized fact-checking response. The process relies on two primary classes:

- **Graph Manager**
Handles the **data ingestion** phase. Validated articles, along with their extracted political entities, topics, and reference websites, are loaded into a **Neo4j** graph database. Instead of older frameworks, this module leverages the **langchain-neo4j** integration to execute precise Cypher queries. Additionally, it uses **networkx** and **matplotlib** to extract relationship networks and save them as visual graphs for the user dashboard. At the beginning of each execution cycle, it performs a complete cleanup (reset_data) of the GraphDB to ensure old information does not interfere with the new context.

- **Query Engine**
Manages the core steps of the RAG (Retrieval-Augmented Generation) process, interacting directly with the graph and vector space:
   - **Encoding & Indexing**: The validated text data is encoded into dense vector embeddings locally. This is performed using the lightweight **phi3.5:latest** model, hosted via the **Ollama** platform, and stored as a **Neo4jVector** index.
   - **Retrieving**: Using LangChain's **RetrievalQA**, the engine searches the vector index and graph relationships to retrieve the most relevant articles and entity connections matching the user's semantic query.
   - **Generating**: The retrieved graph context is injected into a specialized Chain-of-Thought (CoT) prompt. The powerful **llama-3.3-70b-versatile** model, accessed via the **Groq Cloud** platform, processes this context to generate an objective, bias-free analysis and a final visual verdict (True 🟢, False 🔴, or Unverifiable 🟡).

#### GraphRAG Pipeline

The **RAG_Pipeline** serves as the analytical core of Poli-check AI. It orchestrates the flow of validated information into a relational knowledge graph and extracts a definitive verdict. The pipeline executes in three synchronized phases:

1. **Data Ingestion & Graph Modeling**: 
   The pipeline feeds the preprocessed articles into a **Neo4j** database via the **GraphManager**. Using optimized Cypher queries, it maps out a complex knowledge web. It creates nodes for **Article**, **Site**, **Topic**, and the 8 distinct geopolitical entity categories (e.g., **Politici**, **Partiti_Movimenti**, **Stati_Nazioni**). These are interconnected using explicit relationships such as **PUBLISHED_ON**, **MENTIONS**, and **HAS_TOPIC**.

2. **Visual Graph Generation**:
   To ensure transparency and interpretability, the system automatically translates the internal Neo4j graph into user-friendly visual diagrams. Using **NetworkX** and **Matplotlib**, the pipeline generates three distinct, color-coded topological maps:
      - **graph_topics.jpg**: Maps articles to their overarching themes.
      - **graph_entities.jpg**: Maps articles to the specific political actors and institutions mentioned.
      - **graph_sites.jpg**: Maps articles to their publishing domains.

3. **Retrieval & CoT Generation**:
   The **QueryEngine** handles the final evaluation. First, it computes vector embeddings for the articles locally using **Ollama** (**phi3.5**) and retrieves the most semantically relevant nodes using LangChain's **Neo4jVector** index.
   Then, the context is passed to a powerful **Groq Cloud LLM** (llama-3.3-70b-versatile) instructed via a strict **Chain of Thought (CoT)** prompt. The model analyzes the evidence, explicitly cites the source articles, and outputs a highly structured final verdict (True 🟢, False 🔴, or Insufficient Information 🟡). A hardcoded system instruction ensures the entire response is automatically translated into the user's original language.

### Data Logic Components

The **Data Logic** layer guarantees that all interactions—from the user's initial prompt to the final web-scraped evidence—are persistently and securely stored. It leverages an Object-Oriented approach over a lightweight **SQLite** backend, ensuring the dashboard can instantly recall past conversations and visual assets.

1. **Entity Management**: 
   The system encapsulates business logic within dedicated data objects (**data_entities.py**), ensuring that every fact-check session is treated as an isolated, trackable transaction via uniquely generated UUIDs.

2. **Claim Class**: 
   The primary entry point. It stores the user's original text, the optimized search title, and the neutral summary. It also handles the complex serialization of scraped web sources, utilizing **json.dumps()** and **json.loads()** to safely pack and unpack the nested NER dictionaries into the SQL database.
3. **Answer Class**: 
   The culmination object. It securely links the generated LLM verdict and the file path of the corresponding graph images (**graphs_folder**) back to the original **Claim**.


#### SQLite Database Architecture

The **Database** class (**sqldb.py**) acts as the secure interface for local storage. It manages directory creation, automatic schema initialization, and safe SQL executions. The relational model is built on three primary tables:

- **sources**: The evidence table. Stores the scraped URLs, domain names, full body text, and the JSON-stringified political entities, linked to the claim via a Foreign Key (**claim_id**).
- **claims**: The anchor table. Stores the UUID, original text, search title, and summary of the user's query.
- **answers**: The results table. Stores the final LLM response and the directory path containing the generated NetworkX **.jpg** graphs, allowing the Dashboard to dynamically load the visual history of previous fact-checks.


#### Database Access

The **Database** class (**sqldb.py**) acts as the robust SQLite persistence layer for the application, handling both text data and asset paths through the following functions:
- **Initialization**: Dynamically loads paths from environment variables and safely creates necessary directories for the database file.
- **Connection Management**: Implements a strict context manager (**__enter__** and **__exit__**) to securely open, commit, and close SQLite connections, preventing database locks.
- **Query Execution**: Exposes specific methods like **fetch_all()**, **fetch_one()**, and **execute_query()** to handle safe SQL command execution and table creation.
- **Delete Conversations**: Completely wipes the **claims**, **answers**, and **sources** tables, and uses **shutil** to automatically physically delete the associated graph **.jpg** images from the local assets folder.
- **Get History**: Retrieves all saved sessions, mapping related sources and actively using **glob** to locate and bind the generated graph images to the correct conversation history.

### Backend Component

The **Backend Component** (**backend.py**) is a high-performance **FastAPI** application responsible for orchestrating the entire fact-checking pipeline. It serves as the core execution engine, seamlessly weaving together the preprocessing tools, web scraper, and GraphRAG modules, while securely handling all SQLite database transactions.

#### Workflow Overview
1. **Preprocessing (Phase 1)**: The backend receives the user's query and routes it through the **Preprocessing_Pipeline**. If the Gatekeeper model determines the input is not political, the backend immediately halts the pipeline and raises a controlled **400 Bad Request** HTTP exception.
2. **Web Scraping (Phase 2)**: It triggers the **Scraper** to find highly correlated articles. If the system exhausts all search attempts without finding reliable sources, the backend intelligently bypasses the LLM generation and returns an immediate "Unverifiable news" (🟡) clean response.
3. **GraphRAG Retrieval (Phase 3)**: Validated sources are fed into the **RAG_Pipeline**. The backend orchestrates the embedding, graph generation, and final Chain-of-Thought LLM response.
4. **Data Management**: Throughout the execution, the backend instantiates **Claim** and **Answer** entities, which automatically persist the step-by-step progress, source dictionaries, and graph folder paths into the SQLite database.

### Streamlit Dashboard

The **Streamlit Dashboard** (**dashboard.py**) provides an elegant, interactive, and dark-themed (**config.toml**) user interface. Instead of communicating directly with the backend, it securely routes all requests through the **Controller (API Gateway)**.
The dashboard offers two primary modes of operation, managed via session state:

1. **Chat Mode**: Allows users to input a claim via a chat interface (up to 800 characters). The dashboard displays a loading spinner during execution, elegantly renders the final LLM response, and presents the visual GraphRAG diagrams side-by-side.
2. **History Mode**: Automatically loaded when a user selects a past session. It renders the exact historical response, sources, and graphs exactly as they appeared during the original query.

#### Chat Input and Validation

In **Chat Mode**, the system performs immediate front-end validation. If a user inputs a numeric-only claim, the dashboard instantly flags it as invalid without making an API call. If the Controller returns a Gatekeeper rejection (e.g., "Input mismatch: not a political news"), the dashboard intercepts the error and displays it seamlessly in the chat flow as an AI response, avoiding ugly application crashes.

#### Sidebar Functionality

The dynamic sidebar enhances user navigation and session management:
- **New Chat**: Instantly clears the screen and resets the interface to Chat Mode.
- **Delete Chat History (🗑️)**: Triggers a secure API call to completely wipe the SQLite database and local image assets.
- **Chat History**: Displays past conversations chronologically. It includes a real-time text search bar to filter specific topics and a "Show More/Less Chats" toggle to manage UI clutter.

#### Retrieving Conversations

Upon startup or refresh, the dashboard retrieves the entire conversation history via a **GET request** to the Controller. It reconstructs the chat interface, mapping markdown text, interactive source links, and locally stored image paths.

#### Additional Features
- **Graphical Outputs**: Generated NetworkX graphs (Topics, Entities, Sites) are rendered inside the chat container using responsive Streamlit columns.
- **Collapsible Sources**: Extracted URLs and article titles are neatly hidden inside an interactive expander (📌 Sources), keeping the UI clean.
- **Custom Theming**: The UI is customized via a **config.toml** file, enforcing a dark background (**#0E1117**) with distinct blue highlights for interactive elements, ensuring a modern, professional look.

--- 

## Testing and Evaluation

Testing is a critical phase in Poli-check AI to ensure the system's reliability, accuracy, and robustness in political information verification. To rigorously assess the pipeline's real-world performance, the system underwent an empirical, end-to-end evaluation, simulating real user interactions and challenging the architecture with verified historical claims.

**Dataset-Driven System Testing**
Rather than relying solely on isolated component tests, the system's performance was evaluated using the FakeNewsNet dataset, specifically leveraging ground-truth verifications from the "PolitiFact" subset. This methodical approach ensures the system operates with high precision and handles edge cases transparently.

- Balanced Sampling: The system was tested against a balanced sample of 50 real-world political statements (25 strictly categorized as Fake and 25 as Real).
- End-to-End Pipeline Verification: Each claim was processed through the entire microservices architecture, validating the interaction between the Preprocessing Gatekeeper, the dynamic Web Scraper, and the GraphRAG Query Engine.
- Metric Evaluation: The system's final verdicts were measured against the dataset's ground truth using standard classification metrics (Accuracy, Precision, Recall, and F1-Score).
- Edge Case Handling: The testing phase specifically monitored the system's behavior under stressful conditions, assessing how the LLM manages ambiguous queries, partial truths, and constraints related to exact quotation matching, ensuring it safely defaults to "Insufficient Information" when sources are conflicting.

This rigorous empirical testing confirms that Poli-check AI operates with a high degree of reliability, particularly in detecting structural misinformation (achieving over 81% precision in Fake News detection).


--- 

## Authors

- [Antonio Cicatelli](https://github.com/AntonioCicatelli)
- [Carmine Gentile](https://github.com/GentileN46004870)

---


## License
This project is licensed under the [GNU General Public License v3.0](LICENSE). Refer to the LICENSE file for more information.