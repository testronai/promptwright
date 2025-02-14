import os
import asyncio
import platform
import streamlit as st
from streamlit_ace import st_ace
from services.browser_task_runner import BrowserTaskRunner, BrowserTaskExecutionError
from utils.history_cleaner import HistoryCleaner
from services.code_generator import CodeGenerator
from services.config_manager import ConfigManager
from PIL import Image
import json
from datetime import datetime
import base64
from pathlib import Path
import logging
import sys
import pandas as pd

# Configure asyncio event loop for Windows
if platform.system() == 'Windows':
    try:
        # Try to use WindowsSelectorEventLoopPolicy
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Fallback to ProactorEventLoop if needed
        else:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
    except Exception as e:
        logger.warning(f"Failed to set Windows event loop policy: {str(e)}")

def get_csv_download_link(df):
    """Generate a link allowing the data in a given pandas dataframe to be downloaded"""
    csv = df.to_csv(index=True).encode('utf-8')
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="interacted-elements-{timestamp}.csv" class="download-button">📥 Download Elements CSV</a>'
    return href

# Configure logging with more detailed settings
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
PLAYWRIGHT_PYTHON = "playwright_py_code"
PLAYWRIGHT_TYPESCRIPT = "playwright_ts_code"
CYPRESS_TYPESCRIPT = "cypress_ts_code"
SELENIUM_JAVA = "selenium_java_code"
DEFAULT_PERSONA = PLAYWRIGHT_TYPESCRIPT

# Framework display names
FRAMEWORK_NAMES = {
    PLAYWRIGHT_PYTHON: "Playwright Python",
    PLAYWRIGHT_TYPESCRIPT: "Playwright TypeScript",
    CYPRESS_TYPESCRIPT: "Cypress TypeScript",
    SELENIUM_JAVA: "Selenium Java"
}

# Framework file extensions
FRAMEWORK_EXTENSIONS = {
    PLAYWRIGHT_PYTHON: ".py",
    PLAYWRIGHT_TYPESCRIPT: ".ts",
    CYPRESS_TYPESCRIPT: ".cy.ts",
    SELENIUM_JAVA: ".java"
}

# Framework prompt templates
FRAMEWORK_PROMPTS = {
    PLAYWRIGHT_PYTHON: "prompts/playwright_py_code_generation.txt",
    PLAYWRIGHT_TYPESCRIPT: "prompts/playwright_ts_code_generation.txt",
    CYPRESS_TYPESCRIPT: "prompts/cypress_ts_code_generation.txt",
    SELENIUM_JAVA: "prompts/selenium_java_code_generation.txt"
}

# Set page config - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Promptwright",
    page_icon=Image.open(os.path.join(os.path.dirname(__file__), "..", "assets", "promptwright-logo-small.png")),
    layout="wide"
)

# Add metadata tags for SEO and social sharing
st.markdown("""
    <div style="display:none">
        <!-- Primary Meta Tags -->
        <title>Promptwright - AI-Powered Browser Automation</title>
        <meta name="title" content="Promptwright - AI-Powered Browser Automation">
        <meta name="description" content="Transform natural-language prompts into automated browser workflows using AI. Generate reusable Playwright and Cypress scripts instantly.">
        
        <!-- Open Graph / Facebook -->
        <meta property="og:type" content="website">
        <meta property="og:url" content="https://promptwright.testronai.com/">
        <meta property="og:site_name" content="Promptwright">
        <meta property="og:title" content="Promptwright - AI-Powered Browser Automation">
        <meta property="og:description" content="Transform natural-language prompts into automated browser workflows using AI. Generate reusable Playwright and Cypress scripts instantly.">
        <meta property="og:image" content="https://promptwright.testronai.com/assets/promptwright-logo-big.png">

        <!-- Twitter -->
        <meta property="twitter:card" content="summary_large_image">
        <meta property="twitter:url" content="https://promptwright.testronai.com/">
        <meta property="twitter:title" content="Promptwright - AI-Powered Browser Automation">
        <meta property="twitter:description" content="Transform natural-language prompts into automated browser workflows using AI. Generate reusable Playwright and Cypress scripts instantly.">
        <meta property="twitter:image" content="https://promptwright.testronai.com/assets/promptwright-logo-big.png">
        
        <!-- Additional SEO tags -->
        <meta name="keywords" content="browser automation, AI testing, Playwright, Cypress, test automation, no-code automation, TestronAI, Promptwright">
        <meta name="author" content="TestronAI">
        <meta name="robots" content="index, follow">
        <link rel="canonical" href="https://promptwright.testronai.com/">
    </div>
""", unsafe_allow_html=True)

# Add Google Analytics tracking code
st.markdown("""
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-EMDBHRDSHT"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-EMDBHRDSHT');
    </script>
""", unsafe_allow_html=True)

# Initialize configuration manager
config_manager = ConfigManager()

# Load the logo image
logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "promptwright-logo-small.png")
logo_img = Image.open(logo_path)

testron_logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "testron-logo.png")
testron_logo_img = Image.open(testron_logo_path)

# Add JavaScript for local storage operations
def init_local_storage():
    st.markdown("""
        <script>
            // Function to load settings from local storage
            const loadSettings = () => {
                const settings = localStorage.getItem('promptwright_settings');
                if (settings) {
                    window.parent.postMessage({
                        type: 'promptwright_settings_loaded',
                        settings: settings
                    }, '*');
                }
            };

            // Function to save settings to local storage
            const saveSettings = (settings) => {
                localStorage.setItem('promptwright_settings', settings);
            };

            // Load settings when page loads
            loadSettings();

            // Listen for settings updates from Streamlit
            window.addEventListener('message', (event) => {
                if (event.data.type === 'promptwright_save_settings') {
                    saveSettings(event.data.settings);
                }
            });
        </script>
    """, unsafe_allow_html=True)

# Initialize local storage
init_local_storage()

# Function to load saved settings
def initialize_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # If we have saved settings from a previous save operation
        if 'saved_settings' in st.session_state:
            saved = st.session_state.saved_settings
            # Initialize session state with saved values
            for key, value in saved.items():
                if key.endswith('_API_KEY'):
                    key_name = key.lower().replace('_api_key', '_key')
                    st.session_state[key_name] = value
                else:
                    st.session_state[key.lower()] = value
        else:
            # Initialize with defaults from config manager
            st.session_state.model_provider = config_manager.get_config('MODEL_PROVIDER', 'openai')
            st.session_state.model_name = config_manager.get_config('MODEL_NAME', 'gpt-4')
            st.session_state.api_key = config_manager.get_config(f"{st.session_state.model_provider.upper()}_API_KEY", '')
            st.session_state.use_vision = config_manager.get_config('USE_VISION', 'false').lower() == 'true'
            st.session_state.browser_type = config_manager.get_config('BROWSER_TYPE', 'local')
            st.session_state.cloud_provider = config_manager.get_config('BROWSER_CLOUD_PROVIDER', '')
            st.session_state.browserbase_key = config_manager.get_config('BROWSERBASE_API_KEY', '')
            st.session_state.steeldev_key = config_manager.get_config('STEELDEV_API_KEY', '')
            st.session_state.browserless_key = config_manager.get_config('BROWSERLESS_API_KEY', '')
            st.session_state.lightpanda_key = config_manager.get_config('LIGHT_PANDA_API_KEY', '')
            st.session_state.code_generation_persona = config_manager.get_config('CODE_GENERATION_PERSONA', DEFAULT_PERSONA)

# Initialize session state before creating any widgets
initialize_session_state()

# Initialize task input in session state if not present
if 'task_input' not in st.session_state:
    st.session_state.task_input = ""

# Initialize input enabled state
if 'input_enabled' not in st.session_state:
    st.session_state.input_enabled = True

# Callback to clear task input and enable input section
def clear_task_input():
    st.session_state.task_input = ""
    st.session_state.input_enabled = True
    if 'show_save_success' in st.session_state:
        del st.session_state.show_save_success

# Callback for form submission
def on_form_submit():
    st.session_state.input_enabled = False

# Update config manager with current session state values
# This ensures UI settings take precedence over .env
current_settings = {
    "MODEL_PROVIDER": st.session_state.model_provider,
    "MODEL_NAME": st.session_state.model_name,
    f"{st.session_state.model_provider.upper()}_API_KEY": st.session_state.api_key,
    "USE_VISION": str(st.session_state.use_vision).lower(),
    "BROWSER_TYPE": st.session_state.browser_type,
    "BROWSER_CLOUD_PROVIDER": st.session_state.cloud_provider if st.session_state.browser_type == "remote" else "",
    "CODE_GENERATION_PERSONA": st.session_state.code_generation_persona
}

# Add browser provider API keys if they are set
if st.session_state.browserbase_key:
    current_settings["BROWSERBASE_API_KEY"] = st.session_state.browserbase_key
if st.session_state.steeldev_key:
    current_settings["STEELDEV_API_KEY"] = st.session_state.steeldev_key
if st.session_state.browserless_key:
    current_settings["BROWSERLESS_API_KEY"] = st.session_state.browserless_key
if st.session_state.lightpanda_key:
    current_settings["LIGHTPANDA_API_KEY"] = st.session_state.lightpanda_key

# Update configurations in config manager with UI values
config_manager.update_from_ui(current_settings)

os.environ["ANONYMIZED_TELEMETRY"] = "false"

# Add custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Hide the toolbar */
    div[data-testid="stToolbar"] {
        display: none;
    }
    
    /* Main app styling */
    .stApp {
        background-color: #1E1E1E !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Scale down main container elements */
    div[data-testid="stMainBlockContainer"] {
        transform: scale(0.9);
        transform-origin: top center;
        margin-top: -2rem !important;
    }

    /* Adjust logo size */
    div[data-testid="stHorizontalBlock"] div[data-testid="stImage"] {
        width: 160px !important;  /* Reduced from 200px */
    }

    /* App title styling */
    .app-title {
        font-size: 3rem !important;  /* Reduced from 3.5rem */
        font-weight: 700 !important;
        background: linear-gradient(135deg, #E86C52 0%, #FFB347 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        text-fill-color: transparent !important;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: -0.02em !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2) !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Description text styling */
    .description-text {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem !important;  /* Reduced from 1.2rem */
        line-height: 1.6 !important;
        color: #E0E0E0 !important;
        margin: 1.5rem 0 2rem 0 !important;
        padding: 0.8rem 1.2rem !important;  /* Reduced padding */
        border-left: 4px solid #E86C52 !important;
        background: rgba(232, 108, 82, 0.1) !important;
        border-radius: 0 8px 8px 0 !important;
    }

    /* Example Tasks styling */
    .example-tasks h3 {
        color: #E86C52 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;  /* Reduced from 1.1rem */
        font-weight: 600 !important;
        margin-bottom: 0.75rem !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }

    .example-tasks li {
        color: #E0E0E0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;  /* Reduced from 0.95rem */
        line-height: 1.5 !important;
        margin-bottom: 0.5rem !important;
        padding-left: 0.25rem !important;
        padding-right: 1rem !important;
    }

    .example-tasks li:last-child {
        margin-bottom: 0 !important;
    }

    /* Code section styling */
    .code-section h2 {
        color: #E86C52 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1.3rem !important;  /* Reduced from 1.5rem */
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    
    .stApp > header {
        background-color: transparent !important;
    }
    
    /* Container styling */
    .stApp > div:first-of-type {
        max-width: 100%;
        margin: 0 auto;
    }

    /* Remove extra margins from block container */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding-top: 0 !important;
    }

    div.block-container {
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
    }
    
    /* Form and input styling */
    .stTextArea textarea {
        background-color: #2D2D2D !important;
        border: 1px solid #E86C52 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #E86C52 !important;
        box-shadow: 0 0 0 1px #E86C52 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #E86C52 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
    }
    
    .stButton > button:hover {
        background-color: #FF7F5C !important;
    }
    
    /* Text colors */
    .stMarkdown {
        color: #CCCCCC !important;
    }
    
    h1 {
        color: white !important;
    }
    
    /* Header layout */
    div[data-testid="stHorizontalBlock"] {
        align-items: center;
        gap: 20px !important;
        margin-bottom: 2rem;
    }
    
    div[data-testid="stHorizontalBlock"] > div {
        flex: none !important;
    }
    
    /* Form container styling */
    [data-testid="stForm"] {
        background-color: #2D2D2D;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #E86C52;
        margin-top: 2rem;
    }
    
    /* Label styling */
    .stTextArea label {
        color: #E86C52 !important;
        font-weight: 600 !important;
    }
    
    /* Success message styling */
    .success-message {
        background-color: #2D2D2D;
        color: #28a745;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #28a745;
    }
    
    /* Code output styling */
    .output-container {
        background-color: #2D2D2D;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #E86C52;
    }

    .description-text strong {
        color: #E86C52 !important;
        font-weight: 600 !important;
    }

    /* Example Tasks styling */
    .example-tasks {
        background: #2D2D2D !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin: 1.5rem 0 !important;
        border: 1px solid #E86C52 !important;
        width: 100% !important;
    }

    .example-tasks h3::before {
        content: "🎯" !important;
        font-size: 1.2rem !important;
    }

    .example-tasks ol {
        margin: 0 !important;
        padding-left: 1.25rem !important;
        width: 100% !important;
    }

    /* Hide the default info icon and border */
    .stAlert {
        background-color: transparent !important;
        border: none !important;
    }
    .stAlert > div {
        border: none !important;
    }
    [data-testid="stAlertIcon"] {
        display: none !important;
    }

    /* Code section styling */
    .code-section {
        background: #2D2D2D !important;
        border-radius: 8px !important;
        padding: 1.5rem !important;
        margin: 1.5rem 0 !important;
        border: 1px solid #E86C52 !important;
    }

    /* Style the code block container */
    div[data-testid="stCodeBlock"] {
        margin-bottom: 1.5rem !important;
    }

    /* Style the download button */
    .download-button {
        display: inline-block;
        padding: 0.5rem 1rem;
        background-color: #2D2D2D;
        color: #E86C52 !important;
        text-decoration: none;
        border: 1px solid #E86C52;
        border-radius: 4px;
        transition: all 0.3s ease;
        text-align: center;
        width: 100%;
        margin: 0.5rem 0;
    }

    .download-button:hover {
        background-color: #E86C52;
        color: white !important;
        text-decoration: none;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #2D2D2D !important;
    }

    /* Minimize sidebar header height */
    [data-testid="stSidebarHeader"] {
        height: 20px !important;
        min-height: 20px !important;
        padding: 0 !important;
    }

    [data-testid="stLogoSpacer"] {
        height: 20px !important;
        min-height: 20px !important;
        padding: 0 !important;
    }

    /* Sidebar logo styling */
    .sidebar-logo-container {
        padding: 0.3rem 0.5rem 0.5rem 0.5rem !important;
        text-align: left !important;
    }
    
    .sidebar-logo-container img {
        width: 40px !important;
    }

    .sidebar-header {
        color: #E86C52 !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.3rem !important;
        padding-bottom: 0.3rem !important;
        border-bottom: 2px solid #E86C52 !important;
    }

    /* Style sidebar selectbox and text input */
    .stSelectbox [data-baseweb="select"] {
        background-color: #1E1E1E !important;
        border: 1px solid #E86C52 !important;
        border-radius: 8px !important;
    }

    .stTextInput input {
        background-color: #1E1E1E !important;
        border-color: #E86C52 !important;
        color: white !important;
    }

    /* Style the dropdown when expanded */
    div[data-baseweb="popover"] {
        background-color: #1E1E1E !important;
        border: 1px solid #E86C52 !important;
        border-radius: 8px !important;
    }

    /* Style the dropdown options */
    div[data-baseweb="select"] ul {
        background-color: #1E1E1E !important;
        border: 1px solid #E86C52 !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }

    /* Style the dropdown options on hover */
    div[data-baseweb="select"] ul li:hover {
        background-color: rgba(232, 108, 82, 0.1) !important;
        border-radius: 4px !important;
    }

    /* Style the selected option */
    div[data-baseweb="select"] [data-baseweb="selected-option"] {
        background-color: rgba(232, 108, 82, 0.1) !important;
    }

    /* Style the dropdown arrow */
    [data-baseweb="select"] svg {
        color: #E86C52 !important;
    }

    /* Style the dropdown when focused */
    .stSelectbox [data-baseweb="select"]:focus-within {
        border-color: #E86C52 !important;
        box-shadow: 0 0 0 1px #E86C52 !important;
    }

    /* Style the dropdown text */
    [data-baseweb="select"] [data-testid="stMarkdown"] p {
        color: #FFFFFF !important;
    }

    /* Style the dropdown placeholder */
    [data-baseweb="select"] [data-baseweb="placeholder"] {
        color: rgba(255, 255, 255, 0.6) !important;
    }

    /* Style sidebar sections */
    .sidebar-section {
        background-color: #1E1E1E !important;
        padding: 0.5rem !important;
        border-radius: 8px !important;
        margin-bottom: 0.5rem !important;
        border: 1px solid #E86C52 !important;
    }

    /* Reduce spacing between markdown elements in sidebar */
    .element-container {
        margin-bottom: 0.1rem !important;
    }

    /* Custom CSS for table column width */
    .dataframe th:nth-child(2), .dataframe td:nth-child(2) {
        min-width: 150px;  /* Set your desired minimum width */
    }
</style>
""", unsafe_allow_html=True)

# Title and description
header_cols = st.columns([1, 6])
with header_cols[0]:
    st.image(logo_img, width=200)
with header_cols[1]:
    st.markdown("<h1 class='app-title'>Promptwright</h1>", unsafe_allow_html=True)

st.markdown("""
<div class="description-text">
<strong>Promptwright</strong> transforms natural-language user prompts into automated browser workflows using AI, while instantly generating reusable <strong>Playwright</strong> and <strong>Cypress</strong> scripts. This empowers users to run tasks cost-effectively without recurring AI dependency, bridging <strong>no-code simplicity</strong> with <strong>pro-code efficiency</strong>.
</div>
""", unsafe_allow_html=True)

# Create a sidebar for configurations
with st.sidebar:
    # Add logo to sidebar
    st.markdown('<div class="sidebar-logo-container">', unsafe_allow_html=True)
    st.image(testron_logo_img, width=80)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h2 class='sidebar-header'>⚙️ Configuration</h2>", unsafe_allow_html=True)
    
    # Model Configuration Section
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<h3 class='sidebar-header'>🤖 Model Settings</h3>", unsafe_allow_html=True)
    
    # Dynamic model options based on provider
    model_options = {
        "openai": ["gpt-4", "gpt-4o-mini", "gpt-4o"],
        "anthropic": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
        "deepseek": ["deepseek-chat"],
        "groq": ["mixtral-8x7b-32768", "llama-3.3-70b-versatile"],
        "google": ["gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-pro"]
    }
    
    # Create a callback to update config when model provider changes
    def on_model_provider_change():
        current_settings = {
            "MODEL_PROVIDER": st.session_state.model_provider,
            "MODEL_NAME": model_options[st.session_state.model_provider][0],  # Default to first model
            f"{st.session_state.model_provider.upper()}_API_KEY": st.session_state.api_key,
            "USE_VISION": str(st.session_state.use_vision).lower(),
            "BROWSER_TYPE": st.session_state.browser_type,
            "BROWSER_CLOUD_PROVIDER": st.session_state.cloud_provider if st.session_state.browser_type == "remote" else "",
            "CODE_GENERATION_PERSONA": st.session_state.code_generation_persona
        }
        config_manager.update_from_ui(current_settings)
    
    # Create a callback to update config when model name changes
    def on_model_name_change():
        current_settings = {
            "MODEL_PROVIDER": st.session_state.model_provider,
            "MODEL_NAME": st.session_state.model_name,
            f"{st.session_state.model_provider.upper()}_API_KEY": st.session_state.api_key,
            "USE_VISION": str(st.session_state.use_vision).lower(),
            "BROWSER_TYPE": st.session_state.browser_type,
            "BROWSER_CLOUD_PROVIDER": st.session_state.cloud_provider if st.session_state.browser_type == "remote" else "",
            "CODE_GENERATION_PERSONA": st.session_state.code_generation_persona
        }
        config_manager.update_from_ui(current_settings)
    
    model_provider = st.selectbox(
        "Model Provider",
        ["openai", "anthropic", "deepseek", "groq", "google"],
        help="Select the AI model provider for task execution and code generation",
        key="model_provider",
        on_change=on_model_provider_change
    )
    
    model_name = st.selectbox(
        "Model Name",
        model_options.get(model_provider, []),
        help=f"Select the specific model from {model_provider.title()} to use",
        key="model_name",
        on_change=on_model_name_change
    )
    
    api_key = st.text_input(
        f"{model_provider.title()} API Key",
        type="password",
        help=f"Enter your {model_provider.title()} API key for authentication",
        key="api_key"
    )
    
    use_vision = st.toggle(
        "Enable Vision",
        help="Enable vision capabilities for tasks that require visual understanding",
        key="use_vision",
        value=False
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Browser Configuration Section
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<h3 class='sidebar-header'>🌐 Browser Settings</h3>", unsafe_allow_html=True)
    
    # Determine browser type options based on environment
    is_cloud = os.getenv("RUNNING_IN_CLOUD", "false").lower() == "true"
    browser_type_options = ["remote"] if is_cloud else ["local", "remote"]
    
    # Reset browser type if in cloud and currently set to local
    if is_cloud and st.session_state.get("browser_type") == "local":
        st.session_state.browser_type = "remote"
    
    browser_type = st.selectbox(
        "Browser Type",
        browser_type_options,
        help="Select 'local' for browser on your machine or 'remote' for cloud-based browser",
        key="browser_type"
    )
    
    # Only show cloud provider and API key settings if browser type is remote
    if browser_type == "remote":
        # Define available cloud providers
        cloud_providers = ["browserbase", "steeldev", "browserless", "lightpanda"]
        
        # Ensure cloud_provider has a valid value
        if "cloud_provider" not in st.session_state or st.session_state.cloud_provider not in cloud_providers:
            st.session_state.cloud_provider = cloud_providers[0]
            
        cloud_provider = st.selectbox(
            "Browser Cloud Provider",
            cloud_providers,
            help="Select a cloud provider for remote browser execution",
            key="cloud_provider"
        )

        # Only show API key input for the selected provider
        if cloud_provider:
            st.markdown("<h4 style='color: #E86C52; margin-top: 10px; font-size: 0.9rem; border-bottom: 1px solid #E86C52;'>🔑 API Key</h4>", unsafe_allow_html=True)
            
            if cloud_provider == "browserbase":
                browserbase_key = st.text_input(
                    "Browserbase API Key",
                    type="password",
                    help="API key for Browserbase cloud browser service",
                    key="browserbase_key"
                )
            elif cloud_provider == "steeldev":
                steeldev_key = st.text_input(
                    "Steel.dev API Key",
                    type="password",
                    help="API key for Steel.dev cloud browser service",
                    key="steeldev_key"
                )
            elif cloud_provider == "browserless":
                browserless_key = st.text_input(
                    "Browserless API Key",
                    type="password",
                    help="API key for Browserless cloud browser service",
                    key="browserless_key"
                )
            elif cloud_provider == "lightpanda":
                lightpanda_key = st.text_input(
                    "Lightpanda API Key",
                    type="password",
                    help="API key for Lightpanda cloud browser service",
                    key="lightpanda_key"
                )

            # Clear API keys for non-selected providers
            provider_keys = {
                "browserbase": "browserbase_key",
                "steeldev": "steeldev_key",
                "browserless": "browserless_key",
                "lightpanda": "lightpanda_key"
            }
            
            for provider, key in provider_keys.items():
                if provider != cloud_provider and key in st.session_state:
                    st.session_state[key] = ""
    else:
        # Set default empty values when browser type is local
        st.session_state.cloud_provider = ""
        st.session_state.browserbase_key = ""
        st.session_state.steeldev_key = ""
        st.session_state.browserless_key = ""
        st.session_state.lightpanda_key = ""
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # General Settings Section
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.markdown("<h3 class='sidebar-header'>🔧 General Settings</h3>", unsafe_allow_html=True)
    
    code_generation_persona = st.selectbox(
        "Code Generation Framework",
        [PLAYWRIGHT_PYTHON, PLAYWRIGHT_TYPESCRIPT, CYPRESS_TYPESCRIPT, SELENIUM_JAVA],
        format_func=lambda x: FRAMEWORK_NAMES[x],
        help="Select the test automation framework and language",
        key="code_generation_persona"
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Save Configuration Button
    if st.button("💾 Save Configuration", type="primary"):
        # Get current values from widgets directly
        current_settings = {
            "MODEL_PROVIDER": st.session_state.model_provider,
            "MODEL_NAME": st.session_state.model_name,
            f"{st.session_state.model_provider.upper()}_API_KEY": st.session_state.api_key,
            "USE_VISION": str(st.session_state.use_vision).lower(),
            "BROWSER_TYPE": st.session_state.browser_type,
            "BROWSER_CLOUD_PROVIDER": st.session_state.cloud_provider if st.session_state.browser_type == "remote" else "",
            "CODE_GENERATION_PERSONA": st.session_state.code_generation_persona
        }
        
        # Add browser provider API keys if they are set
        if st.session_state.browserbase_key:
            current_settings["BROWSERBASE_API_KEY"] = st.session_state.browserbase_key
        if st.session_state.steeldev_key:
            current_settings["STEELDEV_API_KEY"] = st.session_state.steeldev_key
        if st.session_state.browserless_key:
            current_settings["BROWSERLESS_API_KEY"] = st.session_state.browserless_key
        if st.session_state.lightpanda_key:
            current_settings["LIGHTPANDA_API_KEY"] = st.session_state.lightpanda_key
        
        # Update configurations in config manager
        config_manager.update_from_ui(current_settings)
        
        # Store settings for next session
        st.session_state.saved_settings = current_settings
        
        # Save settings to local storage
        st.markdown(
            f"""
            <script>
                window.parent.postMessage({{
                    type: 'promptwright_save_settings',
                    settings: '{json.dumps(current_settings)}'
                }}, '*');
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # Set a flag in session state to show the success message after rerun
        st.session_state.show_save_success = True
        st.session_state.last_saved_settings = current_settings
        
        # Re-enable the task input section
        st.session_state.input_enabled = True
        st.session_state.task_input = ""
        
        # Force a rerun to apply the new settings
        st.rerun()

# Show success message if flag is set (after rerun)
if 'show_save_success' in st.session_state and st.session_state.show_save_success:
    st.sidebar.success("✅ Configuration saved successfully!")
    with st.sidebar.expander("View Current Settings"):
        st.json(st.session_state.last_saved_settings)
    # Clear the flag
    del st.session_state.show_save_success

# Input section
with st.form(key="task_input_form"):
    task = st.text_area(
        "Enter your automation task and press Go 🚀",
        placeholder="Example: Go to google.com and search for 'testronai'",
        height=100,
        key="task_input",
        value=st.session_state.task_input,
        disabled=not st.session_state.input_enabled
    )
    
    submitted = st.form_submit_button("Go 🚀", 
                                    disabled=not st.session_state.input_enabled,
                                    on_click=on_form_submit)

def execute_browser_task(task: str, status_placeholder) -> tuple[str, str] | None:
    """Execute browser task and return history path and timestamp if successful"""
    try:
        # Create history folder if it doesn't exist and ensure we use absolute path
        history_folder = Path(os.path.join(os.path.dirname(__file__), "..", "history")).resolve()
        history_folder.mkdir(exist_ok=True, parents=True)
        
        try:
            # Execute the browser task first to get the timestamp
            with st.spinner("🚀 Executing browser task..."):
                runner = BrowserTaskRunner()
                history_path, timestamp = asyncio.run(runner.execute_task(task))
                return history_path, timestamp
        except BrowserTaskExecutionError as e:
            status_placeholder.error(f"❌ Browser Task Failed: {str(e)}")
            # Re-enable input for new task
            st.session_state.input_enabled = True
            st.session_state.task_failed = True
            return None
        except Exception as e:
            status_placeholder.error(f"❌ Unexpected error during browser task: {str(e)}")
            logger.error(f"Unexpected error during browser task: {type(e).__name__} - {str(e)}")
            # Re-enable input for new task
            st.session_state.input_enabled = True
            st.session_state.task_failed = True
            return None
    except Exception as e:
        status_placeholder.error(f"❌ Error during task execution: {str(e)}")
        st.session_state.input_enabled = True
        st.session_state.task_failed = True
        return None

if submitted and task:
    try:
        # Initialize task failure flag
        st.session_state.task_failed = False
        
        # Create placeholder for status messages
        status_placeholder = st.empty()
        progress_container = st.empty()
        
        # Create containers in the desired display order but don't populate them yet
        code_section = st.container()
        button_section = st.container()
        gif_section = st.container()
        
        # Function to show new task button
        def show_new_task_button():
            with button_section:
                col1, col2 = st.columns(2)
                with col2:
                    if st.button("🔄 Start New Task", key="new_task_button", use_container_width=True, type="primary", on_click=clear_task_input):
                        code_section.empty()
                        button_section.empty()
                        gif_section.empty()
                        st.rerun()
        
        try:
            # Execute browser task
            result = execute_browser_task(task, status_placeholder)
            
            # If task failed, show only the New Task button and stop
            if st.session_state.task_failed:
                show_new_task_button()
                st.stop()
            
            history_path, timestamp = result
            
            # Use absolute paths consistently
            history_folder = Path(os.path.join(os.path.dirname(__file__), "..", "history")).resolve()
            timestamp_folder = history_folder / timestamp
            cleaned_history_path = timestamp_folder / f'cleaned_history_{timestamp}.json'
            gif_path = timestamp_folder / f'recording_{timestamp}.gif'
            elements_file = timestamp_folder / f'elements_{timestamp}.json'
            
            with status_placeholder:
                with st.spinner("🧹 Cleaning history..."):
                    # Clean the history
                    cleaner = HistoryCleaner()
                    cleaner.clean_history(history_path, str(cleaned_history_path))
            
            with status_placeholder:
                # Show loading message before code generation
                st.info("🚀 Test code is brewing...☕⏳")
                
                try:
                    # Now initialize the code section after browser task is complete
                    with code_section:
                        # Determine language based on persona
                        if st.session_state.code_generation_persona == PLAYWRIGHT_PYTHON:
                            language = "python"
                        elif st.session_state.code_generation_persona == SELENIUM_JAVA:
                            language = "java"
                        else:
                            language = "typescript"
                        
                        framework_name = FRAMEWORK_NAMES[st.session_state.code_generation_persona]
                        st.markdown(f"### Generated {framework_name} Code", help="Code is being generated in real-time")
                        code_container = st.code("", language=language)
                    
                    # Stream the code generation
                    generator = CodeGenerator()
                    
                    # Select the appropriate prompt template based on persona
                    prompt_template_path = FRAMEWORK_PROMPTS[st.session_state.code_generation_persona]
                    
                    # Initialize variables for code generation
                    generated_code = ""
                    chunk_count = 0
                    
                    for code_chunk in generator.generate_typescript_code_stream(
                        cleaned_history_path=cleaned_history_path,
                        prompt_template_path=prompt_template_path
                    ):
                        chunk_count += 1
                        generated_code += code_chunk
                        
                        # Clean up the code for display - remove markdown code fences if present
                        display_code = generated_code
                        if "```python" in display_code:
                            display_code = "\n".join(line for line in display_code.split("\n") 
                                              if not line.strip().startswith("```python") and not line.strip() == "```")
                        elif "```typescript" in display_code:
                            display_code = "\n".join(line for line in display_code.split("\n") 
                                              if not line.strip().startswith("```typescript") and not line.strip() == "```")
                        elif "```java" in display_code:
                            display_code = "\n".join(line for line in display_code.split("\n") 
                                              if not line.strip().startswith("```java") and not line.strip() == "```")
                        
                        # Update the code display in real-time
                        code_container.code(display_code, language=language)
                    
                    # Show appropriate message based on generation result
                    if chunk_count > 0:
                        status_placeholder.success(f"✅ Code generated successfully!")
                        
                        # Add buttons in the button section
                        with button_section:
                            # Create two columns for the buttons
                            col1, col2 = st.columns(2)
                            
                            # Clean up the code for download
                            download_code = generated_code
                            if "```python" in download_code:
                                download_code = "\n".join(
                                    line for line in download_code.split("\n")
                                    if not line.strip().startswith("```python") and not line.strip() == "```"
                                ).strip()
                            elif "```typescript" in download_code:
                                download_code = "\n".join(
                                    line for line in download_code.split("\n")
                                    if not line.strip().startswith("```typescript") and not line.strip() == "```"
                                ).strip()
                            elif "```java" in download_code:
                                download_code = "\n".join(
                                    line for line in download_code.split("\n")
                                    if not line.strip().startswith("```java") and not line.strip() == "```"
                                ).strip()
                            
                            # Add download button in the first column
                            with col1:
                                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                                extension = FRAMEWORK_EXTENSIONS[st.session_state.code_generation_persona]
                                framework_name = FRAMEWORK_NAMES[st.session_state.code_generation_persona]
                                
                                # Convert code to base64
                                code_bytes = download_code.encode('utf-8')
                                code_b64 = base64.b64encode(code_bytes).decode()
                                
                                # Create custom download link
                                download_link = f'''
                                    <a href="data:text/plain;base64,{code_b64}" 
                                       download="promptwright-generated-code-{timestamp}{extension}" 
                                       class="download-button" 
                                       style="text-decoration:none; width:100%; display:inline-block; text-align:center;">
                                       📥 Download {framework_name} Code
                                    </a>
                                '''
                                st.markdown(download_link, unsafe_allow_html=True)
                            
                            # Add New Task button in the second column
                            with col2:
                                if st.button("🔄 Start New Task", key="new_task_button", use_container_width=True, type="primary", on_click=clear_task_input):
                                    code_section.empty()
                                    button_section.empty()
                                    gif_section.empty()
                                    st.rerun()
                    
                        # Display the recording after code generation
                        with gif_section:
                            st.markdown("### Task Execution Recording")
                            with open(gif_path, "rb") as f:
                                gif_contents = f.read()
                            gif_base64 = base64.b64encode(gif_contents).decode()
                            st.markdown(f"""
                                <div style='background-color: #2D2D2D; padding: 20px; border-radius: 10px; margin: 20px 0; border: 1px solid #E86C52; width: 100%;'>
                                    <img src='data:image/gif;base64,{gif_base64}' style='width: 100%; border-radius: 8px; display: block;'>
                                </div>
                            """, unsafe_allow_html=True)
                except Exception as e:
                    # Update status with error message
                    status_placeholder.error(f"❌ Error during code generation: {str(e)}")
                    logger.error(f"Error details: {type(e).__name__} - {str(e)}")
                    show_new_task_button()
                    st.stop()
                    
        except Exception as e:
            # Update status with error message
            status_placeholder.error(f"❌ Error during execution: {str(e)}")
            logger.error(f"Error details: {type(e).__name__} - {str(e)}")
            show_new_task_button()
            st.stop()
            
    except Exception as e:
        # Update status with error message
        status_placeholder.error(f"❌ Error during code generation: {str(e)}")
        logger.error(f"Error details: {type(e).__name__} - {str(e)}")
        show_new_task_button()
        st.stop()
        
    # Clear only the status placeholder after everything is done
    status_placeholder.empty()

# Display elements grid in a separate section outside the code generation block
if submitted and task:
    st.divider()
    st.subheader("🔍 Interacted Elements")
    
    try:
        # Get all elements files from all timestamp folders
        history_folder = Path(os.path.join(os.path.dirname(__file__), "..", "history"))
        elements_files = []
        for timestamp_dir in history_folder.glob('*'):
            if timestamp_dir.is_dir():
                elements_files.extend(timestamp_dir.glob('elements_*.json'))
        
        if not elements_files:
            st.info("No elements files found in history folder")
        else:
            # Get the most recent elements file
            latest_elements_file = max(elements_files, key=lambda x: x.stat().st_mtime)
            
            # Load the elements data
            with open(latest_elements_file, 'r') as f:
                elements_data = json.load(f)
            
            # Create simple list for display
            elements_list = []
            for element in elements_data.get('interacted_elements', []):
                if element and isinstance(element, dict):
                    elements_list.append({
                        'XPath': element.get('xpath', ''),
                        'CSS': element.get('css_selector', '')
                    })
            
            if elements_list:
                # Store elements list in session state
                st.session_state.current_elements_list = elements_list

                # Convert elements_list to a DataFrame and reset the index
                elements_df = pd.DataFrame(elements_list).reset_index(drop=True)

                # Add a column for the index starting from 1
                elements_df.index = elements_df.index + 1
                elements_df.index.name = 'No.'

                # Create columns for the download and table display
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    # Generate download link without causing refresh
                    if elements_list:
                        st.markdown(get_csv_download_link(elements_df), unsafe_allow_html=True)

                # Display the DataFrame with the index in the expander
                with st.expander("Interacted Elements Table"):
                    st.table(elements_df)
            else:
                st.warning("No elements found in the data")
            
            # Debug: Show raw data
            with st.expander("Debug: Raw Elements Data"):
                st.json(elements_data)
                
    except Exception as e:
        st.error(f"Error displaying elements: {str(e)}")
        st.write("Exception details:", str(e))

else:
    # Show some example tasks
    st.markdown("""
    <div class="example-tasks">
        <h3>Example Tasks</h3>
        <ol>
            <li>Visit https://thinking-tester-contact-list.herokuapp.com/, login with 'testronai.com@gmail.com' as username and 'password' as password and submit. Then click 'Add a New Contact', fill in the contact form with random Indian-style data, and verify the contact details are correctly displayed in the table. Then logout from the application.</li>
            <li>Go to https://thinking-tester-contact-list.herokuapp.com/ and enter using any random funny username  and password and do not submit the form.</li>
            <li>Go to google.com and search for 'testronai', and open the first link which has the word testronai in it.</li>
            <li>Go to testronai.com and click on watch demo button</li>
        </ol>
    </div>
    """, unsafe_allow_html=True) 
    