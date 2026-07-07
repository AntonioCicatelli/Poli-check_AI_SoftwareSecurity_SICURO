import os
import sys
import requests

from PIL import Image
import dotenv
import glob
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import Logger

class DashboardPipeline:
    def __init__(self, env_file="key.env"):
        """
        Initializes the dashboard pipeline by loading environment variables 
        and setting up the logger and session state.
        """
        dotenv.load_dotenv(env_file, override=True)
        self.logger = Logger(self.__class__.__name__).get_logger()
        self.logo = os.getenv('AI_IMAGE_UI', 'Assets/Logo.jpg')
        self.controller_url = os.getenv('CONTROLLER_API_URL', 'http://127.0.0.1:8003')
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_assistant = os.path.join(base_dir, "news.png")
        self.icon_user = os.path.join(base_dir, "social-media.png")

        # Load image (used for header)
        try:
            self.image_header = Image.open(self.logo)
        except Exception as e:
            self.logger.error(f"Errore nel caricamento del logo: {e}")
            self.image_header = None

        # Initialize session state
        self._initialize_session_state()

    def _initialize_session_state(self):
        """
        Initializes session state variables for managing the chat messages 
        and view mode.
        """
        if "messages" not in st.session_state:
            st.session_state["messages"] = []
        if "view_mode" not in st.session_state:
            st.session_state.view_mode = "chat" 

    def _log_error(self, msg):
        self.logger.error(msg)
        st.error(msg)

    def delete_chat_history(self):
        try:
            response = requests.post(f"{self.controller_url}/clean_conversations")
            response.raise_for_status()
            st.sidebar.success("Chat history deleted successfully.")
        except requests.exceptions.RequestException as e:
            self._log_error(f"Error deleting chat history: {e}")

    def is_numeric_claim(self, claim_text):
        return claim_text.isdigit()

    def get_response(self, claim):
        """
        Requests a response from the controller server for the given claim.
        """
        with st.spinner("Processing news..."):
            try:
                response = requests.post(
                    f"{self.controller_url}/results",
                    json={"text": claim}
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("response", {})

                if result.get("gatekeeper_rejected"):
                    return {"rejected": True, "message": result.get("message")}

                claim_title = result.get("claim_title", "")
                claim_summary = result.get("claim_summary", "")
                query_result = result.get("query_result", "")
                sources = [{"title": src.get("title", ""), "url": src.get("url", "")} for src in result.get("sources", [])]

                images = self._load_images_from_folder(result.get("graphs_folder", ""))
                return {'rejected': False, 'title': claim_title, 'summary': claim_summary, 'response': query_result, 'sources': sources, 'images': images}
            
            except requests.exceptions.HTTPError as e:
                self._log_error(f"HTTP Error: {e}")
                return None
            except requests.exceptions.RequestException as e:
                self._log_error(f"Error in POST request: {e}")
                return None

    def _load_images_from_folder(self, folder):
        images = []
        if folder and os.path.isdir(folder):
            for file in glob.glob(os.path.join(folder, "*.jpg")):
                try:
                    img = Image.open(file)
                    images.append(img)
                except Exception as e:
                    self.logger.error(f"Error opening image {file}: {e}")
        return images

    def display_message(self, role, message, avatar=None):
        if role == "assistant":
            chat_msg = st.chat_message("assistant", avatar=self.icon_assistant) 
        else:
            chat_msg = st.chat_message("user", avatar=self.icon_user)
        chat_msg.write(message)

    def display_claim_response(self, response):
        assistant_message = st.chat_message("assistant", avatar=self.icon_assistant) 

        title_html = f"<h2 style='color: #FAFAFA; font-size: 1.5em; line-height: 1.4;'>{response['title']}</h2>"
        assistant_message.markdown(title_html, unsafe_allow_html=True)

        assistant_message.write(f"{response['response']}")

        with assistant_message.expander("📌 Sources"):
            for src in response.get('sources', []):
                st.markdown(f"- [{src['title']}]({src['url']})")

        images = response.get('images', [])
        if images:
            with assistant_message.container():
                cols = st.columns(len(images))
                for col, img in zip(cols, images):
                    col.image(img)

    def get_conversations(self):
        with st.spinner("Processing conversations..."):
            try:
                response = requests.get(f"{self.controller_url}/conversations")
                response.raise_for_status()
                data = response.json()
                return data.get("response", [])
            except requests.exceptions.RequestException as e:
                self._log_error(f"Error in GET request: {e}")
                return []

    def display_conversation(self, conversation):
        def display_message_markdown(role, content, avatar=None):
            if role == "assistant":
                message = st.chat_message("assistant", avatar=self.icon_assistant)
            else:
                message = st.chat_message("user", avatar=self.icon_user)
            message.markdown(content, unsafe_allow_html=True)

        content = f"""
        <h2 style='color: #FAFAFA; font-size: 1.5em; line-height: 1.4;'>{conversation['title']}</h2>
        """

        content += f"<p style='font-size: 1.1em; line-height: 1.6;'>{conversation['answer']}</p>"

        display_message_markdown("assistant", content)

        with st.expander("📌 Sources"):
            if conversation['sources']:
                sources_text = "\n\n".join([f"- [{src['title']}]({src['url']})" for src in conversation['sources']])
                st.markdown(sources_text)
            else:
                st.markdown("No sources available for this news.")

        if conversation.get('images'):
            cols = st.columns(len(conversation['images']))
            for col, img_path in zip(cols, conversation['images']):
                try:
                    # Apriamo l'immagine con PIL esattamente come facciamo per le nuove chat
                    img = Image.open(img_path) if isinstance(img_path, str) else img_path
                    col.image(img)
                except Exception as e:
                    self.logger.error(f"Impossibile caricare l'immagine dalla cronologia: {e}")

    def run(self):
        # 1. CSS Custom: manteniamo SOLO il blocco dell'a capo per i bottoni per non rompere il resize dinamico della sidebar
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] button p {
                    white-space: nowrap !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 2.5, 1]) 
        with col2:
            if self.image_header:
                st.image(self.image_header, use_container_width=True)

        st.markdown("---") 

        if st.session_state.view_mode == "chat":
            prompt = st.chat_input(max_chars=800, placeholder="Type your news or paste a URL here...")
            if prompt:
                if self.is_numeric_claim(prompt):
                    self.display_message("assistant", "This news is invalid because it consists only of numbers.")
                    st.session_state.messages = []
                else:
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    self.display_message("user", prompt)

                    if len(st.session_state.messages) > 0:
                        claim = st.session_state.messages[-1]['content']
                        response = self.get_response(claim)
                        
                        if response:
                            if response.get('rejected'):
                                self.display_message("assistant", response.get('message', "Input mismatch: not a political news"))
                            else:
                                self.display_claim_response(response)
                        else:
                            st.session_state.messages.pop()

        else:
            if 'selected_conversation' in st.session_state:
                selected_conversation = st.session_state.selected_conversation
                self.display_conversation(selected_conversation)
            else:
                self.display_message("assistant", "Waiting for your news...")

        with st.sidebar:
            col1, col2 = st.columns([0.8, 0.2])
            
            with col1: 
                if st.button(" New Chat", key="new_conv", use_container_width=True):
                    st.session_state.view_mode = "chat"
                    st.session_state.messages = [] 
                    st.session_state.selected_conversation = None
                    st.rerun()
            
            with col2: 
                if st.button("🗑️", key="del_chat", help="Delete Chat History", use_container_width=True):
                    self.delete_chat_history()
                    st.session_state.view_mode = "chat"
                    st.session_state.messages = [] 
                    st.session_state.selected_conversation = None
                    st.rerun()

            st.sidebar.title("Chat History")
            st.sidebar.text_input("Search previous chat...", key="search_query", placeholder="Type to search")

            conversations = self.get_conversations()
            filtered_conversations = [
                convo for convo in conversations if st.session_state.search_query.lower() in convo.get("title", "").lower()
            ] if "search_query" in st.session_state else conversations
            filtered_conversations = filtered_conversations[::-1] 

            if 'show_all_conversations' not in st.session_state:
                st.session_state.show_all_conversations = False

            max_display = 5
            if not st.session_state.show_all_conversations:
                display_conversations = filtered_conversations[:max_display]
            else:
                display_conversations = filtered_conversations

            for i, convo in enumerate(display_conversations):
                if st.sidebar.button(convo['title'][:50] + ("..." if len(convo['title']) > 50 else ""), key=f"convo_{i}"):
                    st.session_state.view_mode = "history"
                    st.session_state.selected_conversation = convo
                    st.rerun()

            if len(filtered_conversations) > max_display:
                if st.sidebar.button(
                    "Show Less Chats" if st.session_state.show_all_conversations else "Show More Chats"
                ):
                    st.session_state.show_all_conversations = not st.session_state.show_all_conversations
                    st.rerun()

if __name__ == "__main__":
    st.set_page_config(page_title="Poli-check AI", layout="wide", initial_sidebar_state="expanded")
    dashboard = DashboardPipeline()
    dashboard.run()