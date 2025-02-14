import os
import asyncio
import sys
import platform
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.agent.views import AgentHistoryList
import logging
from services.config_manager import ConfigManager
from datetime import datetime
from utils.logger_config import setup_logger
from utils.file_utils import FileUtils

# Get logger for this module
logger = logging.getLogger(__name__)

class BrowserTaskExecutionError(Exception):
    """Custom exception for browser task execution failures"""
    pass

class BrowserTaskRunner:
    def __init__(self):
        # Check if running Windows Store Python
        if sys.version.find("Microsoft Store") != -1:
            raise RuntimeError(
                "\nError: You are running Python from the Microsoft Store which has limited functionality."
                "\nPlease uninstall the Microsoft Store version and install Python from python.org instead:"
                "\n1. Uninstall Python from Microsoft Store"
                "\n2. Download and install Python from https://www.python.org/downloads/"
                "\n3. Make sure to check 'Add Python to PATH' during installation"
                "\n4. Restart your computer"
                "\n5. Create a new virtual environment and reinstall the requirements"
            )

        # Load .env file without clearing existing environment variables
        load_dotenv(find_dotenv(), override=True)
        
        # Get the project root directory (two levels up from this file)
        project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Set history directory to be in the project root
        history_dir = project_root / 'history'
        os.environ['HISTORY_DIR'] = str(history_dir)
        
        # Check history directory setup
        logger.info(f"\n=== History Directory Configuration ===")
        logger.info(f"HISTORY_DIR environment variable: {history_dir}")
        logger.info(f"HISTORY_DIR exists: {Path(history_dir).exists()}")
        if Path(history_dir).exists():
            logger.info(f"HISTORY_DIR permissions: {FileUtils.get_file_permissions(Path(history_dir))}")
            logger.info(f"HISTORY_DIR owner: {FileUtils.get_file_owner(Path(history_dir))}")
            logger.info(f"HISTORY_DIR group: {FileUtils.get_file_group(Path(history_dir))}")
        logger.info("=====================================\n")
        
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Configure event loop for Windows
        if platform.system() == 'Windows':
            # Use ProactorEventLoop on Windows
            if isinstance(asyncio.get_event_loop(), asyncio.SelectorEventLoop):
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
            # Ensure we're using ProactorEventLoop
            assert isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop)

        # Initialize browser configuration
        browser_config = self._get_browser_config()
        logger.debug(f"Final Browser Config: {browser_config}")
        self.browser = Browser(config=browser_config)
        
        # Debug logging
        logger.debug("BrowserTaskRunner initialized")

    def _get_browser_config(self) -> BrowserConfig:
        """
        Configure and return browser settings based on latest configuration
        """
        # Get latest settings from config manager
        self.browser_type = self.config_manager.get_config('BROWSER_TYPE', 'local').lower()
        self.cloud_provider = self.config_manager.get_config('BROWSER_CLOUD_PROVIDER', '').lower()
        
        logger.debug(f"Configuring browser with type: {self.browser_type}")
        
        config_params = {
            'headless': False,
            'disable_security': True,
            'highlight_elements': False
        }
        
        logger.info("\n=== Browser Configuration Details ===")
        logger.info(f"Browser Type: {self.browser_type}")
        logger.info(f"Cloud Provider: {self.cloud_provider}")
        logger.debug(f"Initial config_params: {config_params}")
        
        if self.browser_type == 'remote':
            logger.debug(f"Setting up remote browser with provider: {self.cloud_provider}")
            
            if not self.cloud_provider:
                error_msg = "BROWSER_CLOUD_PROVIDER is not set but BROWSER_TYPE is remote"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Remove local browser settings when using remote
            config_params.pop('headless', None)
            config_params.pop('disable_security', None)
            
            if self.cloud_provider == 'browserbase':
                api_key = self.config_manager.get_config('BROWSERBASE_API_KEY')
                if not api_key:
                    raise ValueError("BROWSERBASE_API_KEY not found in environment variables")
                config_params['cdp_url'] = f"wss://connect.browserbase.com?apiKey={api_key}"
                logger.info("Using Browserbase CDP URL")
            
            elif self.cloud_provider == 'steeldev':
                api_key = self.config_manager.get_config('STEELDEV_API_KEY')
                if not api_key:
                    raise ValueError("STEELDEV_API_KEY not found in environment variables")
                config_params['cdp_url'] = f"wss://connect.steel.dev?apiKey={api_key}"
                logger.info("Using Steel.dev CDP URL")
            
            elif self.cloud_provider == 'browserless':
                api_key = self.config_manager.get_config('BROWSERLESS_API_KEY')
                if not api_key:
                    raise ValueError("BROWSERLESS_API_KEY not found in environment variables")
                config_params['wss_url'] = f"wss://production-sfo.browserless.io/chromium/playwright?token={api_key}"
                logger.info("Using Browserless WSS URL")
            
            elif self.cloud_provider == 'lightpanda':
                api_key = self.config_manager.get_config('LIGHTPANDA_API_KEY')
                if not api_key:
                    raise ValueError("LIGHTPANDA_API_KEY not found in environment variables")
                config_params['cdp_url'] = f"wss://cloud.lightpanda.io/ws?token={api_key}"
                logger.info("Using Lightpanda CDP URL")
            
            else:
                logger.error(f"Unsupported cloud provider: {self.cloud_provider}")
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
            
            logger.debug("\nFinal Remote Config Parameters:")
            masked_params = config_params.copy()
            if 'cdp_url' in masked_params:
                masked_params['cdp_url'] = masked_params['cdp_url'].split('?')[0] + '?apiKey=***'
            if 'wss_url' in masked_params:
                masked_params['wss_url'] = masked_params['wss_url'].split('?token=')[0] + '?token=***'
            logger.debug(masked_params)
        else:
            logger.debug("\nUsing Local Browser Configuration:")
            logger.debug(config_params)
        
        return BrowserConfig(**config_params)

    def get_llm(self):
        """
        Configure and return the appropriate LLM based on latest settings
        """
        # Get latest settings from config manager
        self.model_provider = self.config_manager.get_config('MODEL_PROVIDER', 'openai').lower()
        self.model_name = self.config_manager.get_config('MODEL_NAME', 'gpt-4')
        
        logger.info("\n=== LLM Configuration ===")
        logger.info(f"Model Provider: {self.model_provider}")
        logger.info(f"Model Name: {self.model_name}")
        
        if self.model_provider == 'anthropic':
            logger.info("Using Anthropic configuration")
            return ChatAnthropic(
                model=self.model_name,
                anthropic_api_key=self.config_manager.get_config('ANTHROPIC_API_KEY'),
                temperature=0.7
            )
        elif self.model_provider == 'deepseek':
            logger.info("Using DeepSeek configuration")
            return ChatOpenAI(
                model=self.model_name,
                api_key=self.config_manager.get_config('DEEPSEEK_API_KEY'),
                openai_api_base="https://api.deepseek.com/v1",
                temperature=0.7
            )
        elif self.model_provider == 'groq':
            logger.info("Using Groq configuration")
            return ChatGroq(
                model=self.model_name,
                api_key=self.config_manager.get_config('GROQ_API_KEY'),
                temperature=0.7
            )
        elif self.model_provider == 'google':
            logger.info("Using Google configuration")
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.config_manager.get_config('GOOGLE_API_KEY'),
                temperature=0.7
            )
        else:
            logger.info("Using OpenAI configuration")
            return ChatOpenAI(
                model=self.model_name,
                api_key=self.config_manager.get_config('OPENAI_API_KEY'),
                temperature=0.7
            )

    async def execute_task(self, task: str) -> tuple[str, str]:
        """
        Execute a browser task and return the path to generated history file and timestamp
        
        Args:
            task: The task description to execute
            
        Returns:
            tuple[str, str]: Path to the generated history.json file and the timestamp used
            
        Raises:
            BrowserTaskExecutionError: If the task execution fails for any reason
        """
        # Get latest settings from config manager
        use_vision = self.config_manager.get_config('USE_VISION', 'false').lower() == 'true'
        conversation_path = self.config_manager.get_config('CONVERSATION_LOG_PATH', 'logs/conversation.json')
        
        logger.debug(f"use_vision is set to: {use_vision}")
        logger.debug(f"conversation_path is set to: {conversation_path}")
        
        # Create history folder if it doesn't exist
        history_folder = Path(os.getenv('HISTORY_DIR')).resolve()
        logger.info(f"History folder absolute path: {history_folder}")
        logger.info(f"History folder exists: {history_folder.exists()}")
        logger.info(f"History folder parent exists: {history_folder.parent.exists()}")
        
        try:
            history_folder.mkdir(exist_ok=True)
            logger.info(f"Successfully created history folder at {history_folder}")
            logger.info(f"History folder permissions: {FileUtils.get_file_permissions(history_folder)}")
            logger.info(f"History folder owner: {FileUtils.get_file_owner(history_folder)}")
        except Exception as e:
            logger.error(f"Failed to create history folder: {str(e)}")
            logger.error(f"Current process user ID: {os.getuid()}")
            logger.error(f"Current process group ID: {os.getgid()}")
            raise BrowserTaskExecutionError(f"Failed to create history folder: {str(e)}")
        
        # Generate timestamp for unique filename and folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        timestamp_folder = history_folder / timestamp
        try:
            timestamp_folder.mkdir(exist_ok=True)
            logger.info(f"Created timestamp folder: {timestamp_folder}")
            logger.info(f"Timestamp folder permissions: {FileUtils.get_file_permissions(timestamp_folder)}")
            logger.info(f"Timestamp folder owner: {FileUtils.get_file_owner(timestamp_folder)}")
            
            # Ensure timestamp folder has write permissions
            timestamp_folder.chmod(0o755)
            logger.info(f"Updated timestamp folder permissions to 755")
            
        except Exception as e:
            logger.error(f"Failed to create or set permissions on timestamp folder: {str(e)}")
            logger.error(f"Current process user ID: {os.getuid()}")
            logger.error(f"Current process group ID: {os.getgid()}")
            raise BrowserTaskExecutionError(f"Failed to setup timestamp folder: {str(e)}")
        
        # Create paths with timestamp folder
        history_path = timestamp_folder / f'history_{timestamp}.json'
        gif_path = timestamp_folder / f'recording_{timestamp}.gif'
        
        # Test if we can write to the gif path
        try:
            logger.info(f"Testing GIF path writability: {gif_path}")
            with open(gif_path, 'wb') as f:
                f.write(b'test')
            gif_path.unlink()  # Remove test file
            logger.info("Successfully verified GIF path is writable")
        except Exception as e:
            logger.warning(f"GIF path is not writable, will disable recording: {str(e)}")
            gif_path = None
        
        logger.info(f"Initializing agent with gif_path: {gif_path}")

        # Initialize agent with proper event loop handling
        if platform.system() == 'Windows':
            # Ensure we're using ProactorEventLoop for Windows
            loop = asyncio.get_event_loop()
            if not isinstance(loop, asyncio.ProactorEventLoop):
                loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)

        agent = Agent(
            task=task,
            llm=self.get_llm(),
            use_vision=use_vision,
            browser=self.browser,
            gif_filename=str(gif_path) if gif_path else None
        )
        logger.info("Agent initialized successfully")
        logger.info(f"Agent configuration: task={task}, use_vision={use_vision}, gif_path={gif_path}")

        # Log system resource info
        try:
            import psutil
            process = psutil.Process()
            logger.info(f"Current memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            logger.info(f"CPU usage: {process.cpu_percent()}%")
            logger.info(f"Open files: {len(process.open_files())}")
            logger.info(f"Current working directory: {process.cwd()}")
            logger.info(f"Process username: {process.username()}")
        except ImportError:
            logger.info("psutil not available for resource monitoring")
        except Exception as e:
            logger.error(f"Error getting resource info: {str(e)}")

        try:
            try:
                logger.info("Starting agent.run with max_steps=50")
                history: AgentHistoryList = await agent.run(max_steps=50)
                logger.info("Successfully completed agent.run")
                logger.info(f"History type: {type(history)}")
                logger.info(f"History content available: {history is not None}")
                if history:
                    logger.info(f"History steps recorded: {len(history.history) if hasattr(history, 'history') else 'unknown'}")
            except OSError as e:
                if str(e) == 'cannot open resource' and gif_path:
                    logger.warning("Resource error occurred with GIF recording, retrying without recording...")
                else:
                    logger.error(f"Agent task execution failed with OSError: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Agent task execution failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {e.args}")
                # Clean up the timestamp folder since task failed
                if timestamp_folder.exists():
                    logger.info(f"Cleaning up timestamp folder: {timestamp_folder}")
                    safe_cleanup_directory(timestamp_folder)
                raise BrowserTaskExecutionError(f"Task execution failed: {str(e)}")
            
            logger.info("Checking for recording file")
            # Extract actual timestamp from the gif_path that was created
            actual_timestamp = None
            recording_files = list(Path(history_folder).glob('*/recording_*.gif'))
            logger.info(f"Found {len(recording_files)} recording files")
            for file in recording_files:
                if file.exists():
                    actual_timestamp = file.parent.name
                    logger.info(f"Found recording file with timestamp: {actual_timestamp}")
                    break
            
            if actual_timestamp and actual_timestamp != timestamp:
                logger.info(f"Timestamps don't match. Original: {timestamp}, Actual: {actual_timestamp}")
                # If timestamps don't match, move files to correct folder
                new_folder = history_folder / actual_timestamp
                logger.info(f"Creating new folder: {new_folder}")
                if not new_folder.exists():
                    new_folder.mkdir(exist_ok=True)
                    logger.info(f"Created new folder with permissions: {FileUtils.get_file_permissions(new_folder)}")
                
                # Move history file if it exists
                if history_path.exists():
                    logger.info(f"Moving history file to new location")
                    new_history_path = new_folder / f'history_{actual_timestamp}.json'
                    history_path.rename(new_history_path)
                    history_path = new_history_path
                    logger.info(f"History file moved to: {new_history_path}")
                
                # Delete old folder if empty
                if timestamp_folder.exists() and not any(timestamp_folder.iterdir()):
                    logger.info("Removing empty timestamp folder")
                    timestamp_folder.rmdir()
                
                timestamp = actual_timestamp
                logger.info("File reorganization complete")
            
            # Save history to file using the correct timestamp
            try:
                logger.info(f"Attempting to save history to file: {history_path}")
                logger.info(f"History file parent folder exists: {Path(history_path).parent.exists()}")
                logger.info(f"History file parent folder permissions: {FileUtils.get_file_permissions(Path(history_path).parent)}")
                
                # Try to create an empty file first to test write permissions
                try:
                    Path(history_path).touch()
                    logger.info("Successfully created empty history file")
                except Exception as touch_error:
                    logger.error(f"Failed to create empty history file: {str(touch_error)}")
                    raise BrowserTaskExecutionError(f"Failed to create empty history file: {str(touch_error)}")

                # Try to write some test content
                try:
                    with open(history_path, 'w') as f:
                        f.write('{"test": "content"}')
                    logger.info("Successfully wrote test content to history file")
                except Exception as write_error:
                    logger.error(f"Failed to write test content: {str(write_error)}")
                    raise BrowserTaskExecutionError(f"Failed to write test content: {str(write_error)}")

                # Now try to save the actual history
                try:
                    agent.save_history(str(history_path))
                    logger.info("Successfully called agent.save_history")
                except Exception as save_error:
                    logger.error(f"Failed in agent.save_history: {str(save_error)}")
                    logger.error(f"Save error type: {type(save_error)}")
                    logger.error(f"Save error args: {save_error.args}")
                    raise BrowserTaskExecutionError(f"Failed in agent.save_history: {str(save_error)}")
                
                if Path(history_path).exists():
                    logger.info(f"Successfully saved history file at {history_path}")
                    logger.info(f"History file permissions: {FileUtils.get_file_permissions(Path(history_path))}")
                    logger.info(f"History file size: {Path(history_path).stat().st_size} bytes")
                    
                    # Try to read the file back to verify it's readable
                    try:
                        with open(history_path, 'r') as f:
                            content = f.read()
                            logger.info(f"Successfully read back history file, content length: {len(content)}")
                    except Exception as read_error:
                        logger.error(f"Failed to read back history file: {str(read_error)}")
                else:
                    logger.error(f"History file was not created at {history_path}")
                    raise BrowserTaskExecutionError("Failed to create history file")
                    
            except Exception as e:
                logger.error(f"Failed to save history file: {str(e)}")
                logger.error(f"Current working directory: {os.getcwd()}")
                logger.error(f"Process effective user ID: {os.geteuid()}")
                logger.error(f"Process effective group ID: {os.getegid()}")
                logger.error(f"Parent directory listing:")
                try:
                    for item in Path(history_path).parent.iterdir():
                        logger.error(f"  {item.name}: {FileUtils.get_file_permissions(item)}")
                except Exception as list_error:
                    logger.error(f"Failed to list parent directory: {str(list_error)}")
                raise BrowserTaskExecutionError(f"Failed to save history file: {str(e)}")
            
            return str(history_path), timestamp
            
        finally:
            await self.browser.close()

    async def close(self):
        """Close the browser instance"""
        await self.browser.close()

# Function to safely clean up a directory
def safe_cleanup_directory(dir_path: Path) -> None:
    try:
        # Ensure we're working with an absolute path
        dir_path = dir_path.resolve()
        logger.info(f"Cleaning up directory (absolute path): {dir_path}")
        
        if not dir_path.exists():
            logger.info(f"Directory does not exist, skipping cleanup: {dir_path}")
            return
        
        # Verify this is a subdirectory of the history folder
        if not str(dir_path).startswith(str(history_folder)):
            logger.error(f"Attempted to clean directory outside history folder: {dir_path}")
            return
        
        logger.info(f"Cleaning up directory: {dir_path}")
        for item in dir_path.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    logger.info(f"Removed file: {item}")
                elif item.is_dir():
                    safe_cleanup_directory(item)
            except Exception as e:
                logger.warning(f"Failed to remove {item}: {str(e)}")
        
        try:
            dir_path.rmdir()
            logger.info(f"Removed directory: {dir_path}")
        except Exception as e:
            logger.warning(f"Failed to remove directory {dir_path}: {str(e)}")
    except Exception as e:
        logger.warning(f"Error during cleanup of {dir_path}: {str(e)}") 