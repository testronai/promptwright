# Promptwright

<img src="assets/promptwright-logo-small.png" alt="Promptwright Logo" width="250"/>

## Watch Demo 🎥
Click on the image below to watch the demo video:

[![Promptwright Demo](https://img.youtube.com/vi/93iif6_YZBs/0.jpg)](https://youtu.be/93iif6_YZBs)

Promptwright is an AI-powered tool that transforms natural-language user prompts into automated browser workflows while generating reusable test automation scripts. It bridges no-code simplicity with pro-code efficiency.


## Features

- **Natural Language Processing**: Convert plain English instructions into automated browser actions with the help of LLMs and generate reusable test automation scripts as byproducts.
- **Multi-Framework Support**: Generate code for:
  - Playwright (TypeScript & Python)
  - Cypress (TypeScript)
  - Selenium (Java)
- **Multiple AI Model Support**:
  - OpenAI (GPT-4, GPT-4o-mini, GPT-4o)
  - Anthropic (Claude 3.5 Haiku, Claude 3.5 Sonnet)
  - DeepSeek Chat
  - Groq (Mixtral-8x7b, LLaMA-3.3-70b)
  - Google (Gemini 2.0 Flash, Gemini 1.5 Pro)
- **Vision Capabilities**: Optional AI vision features for enhanced visual understanding
- **Flexible Browser Execution**:
  - Local browser execution
  - Remote browser execution via cloud providers:
    - Browserbase
    - Steel.dev
    - Browserless
    - Lightpanda
- **Interactive Web Interface**: User-friendly Streamlit interface with:
  - Real-time code generation
  - Task execution recording playback
  - Interactive elements table with CSV export
- **Professional-Grade Output**: Generate production-ready automation scripts
- **Element Locator Information**: Provides detailed element interaction data including:
  - CSS selectors
  - XPath locators
  - CSV export functionality for element data

## Setup

1. Make sure you have Python 3.11+ installed
2. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/promptwright.git
   cd promptwright
   ```
3. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment:
   - Copy `.env.example` to `.env`
   - Configure your model preferences:
     ```
     MODEL_PROVIDER=openai  # Options: 'openai', 'anthropic', 'deepseek', 'groq', 'google'
     MODEL_NAME=gpt-4      # Model options vary by provider:
                          # - OpenAI: 'gpt-4', 'gpt-4o-mini', 'gpt-4o'
                          # - Anthropic: 'claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022'
                          # - DeepSeek: 'deepseek-chat'
                          # - Groq: 'mixtral-8x7b-32768', 'llama-3.3-70b-versatile'
                          # - Google: 'gemini-2.0-flash', 'gemini-1.5-pro'
     ```
   - Add your API keys:
     ```
     OPENAI_API_KEY=your_openai_api_key_here
     ANTHROPIC_API_KEY=your_anthropic_api_key_here
     DEEPSEEK_API_KEY=your_deepseek_api_key_here
     GROQ_API_KEY=your_groq_api_key_here
     GOOGLE_API_KEY=your_google_api_key_here
     ```
   - For remote browser execution, configure cloud provider API keys:
     ```
     BROWSERBASE_API_KEY=your_browserbase_api_key_here
     STEELDEV_API_KEY=your_steeldev_api_key_here
     BROWSERLESS_API_KEY=your_browserless_api_key_here
     LIGHTPANDA_API_KEY=your_lightpanda_api_key_here
     ```
   - Make sure Chrome is installed on your system for local browser execution

## Installation Requirements

### Windows Users Important Note:
Do NOT use the Python installation from the Microsoft Store. Please follow these steps:

1. If you have Python installed from Microsoft Store, uninstall it first
2. Download Python from the official website: https://www.python.org/downloads/
3. During installation, make sure to check "Add Python to PATH"
4. Restart your computer after installation
5. Create a new virtual environment and install the requirements

This is necessary because the Microsoft Store version of Python has limitations that prevent Playwright from working correctly.

### Playwright Installation Steps:
After installing Python requirements, you need to install Playwright and its browser dependencies:

```bash
# Install Playwright
pip install playwright

# Install browser dependencies (Chromium, Firefox, Webkit)
playwright install chromium

# Install system dependencies (if needed)
playwright install-deps
```

Note: On Windows, make sure to run these commands in an administrator command prompt if you encounter any permission issues.

## Running the Application

Launch the Streamlit app with:
```bash
streamlit run src/app.py
```

The application will be available at `http://localhost:8501` by default.

## Using Promptwright

1. Configure your preferences in the sidebar:
   - Select AI model provider and model
   - Choose browser execution mode (local/remote)
   - Select target framework for code generation
2. Enter your automation task in natural language
3. Click "Go 🚀" to start the process
4. Watch as Promptwright:
   - Executes the task in a browser
   - Records the actions
   - Generates clean, reusable code in your chosen framework
   - Provides an interactive elements table
5. Download the generated code and elements data for future use

## Example Tasks

- Visit a website and fill out registration forms
- Perform search operations on websites
- Navigate through web applications
- Interact with UI elements (buttons, forms, etc.)
- Verify content and validate data
- Visit https://thinking-tester-contact-list.herokuapp.com/, login with 'testronai.com@gmail.com' as username and 'password' as password and submit. Then click 'Add a New Contact', fill in the contact form with random Indian-style data, and verify the contact details are correctly displayed in the table. Then logout from the application.
- Go to https://thinking-tester-contact-list.herokuapp.com/ and enter using any random funny username and password and do not submit the form.
- Go to google.com and search for 'testronai', and open the first link which has the word testronai in it.
- Go to testronai.com and click on watch demo button

## System Requirements

- Python 3.11+
- Chrome browser (for local execution)
- Internet connection
- API key(s) for chosen AI model provider
- API key for cloud browser provider (if using remote execution)

## Important Notes

1. Ensure Chrome is installed for local browser execution
2. Keep your API keys secure and never commit them to version control
3. Generated scripts require appropriate framework setup to run independently:
   - Node.js/Playwright for TypeScript scripts
   - Python/Playwright for Python scripts
   - Node.js/Cypress for Cypress scripts
   - Java/Selenium for Java scripts

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the [LICENSE](LICENSE) file for details.

### What this means:

- ✔️ You can view and use this code for personal and educational purposes
- ✔️ You can modify the code
- ✔️ You must preserve the copyright and license notices
- ✔️ You must disclose the source code when distributing the software
- ✔️ Changes must be released under the same license
- ❌ You cannot use this code for commercial purposes without explicit permission
- ❌ No warranty is provided

For more information about the AGPL-3.0 license, please visit: https://www.gnu.org/licenses/agpl-3.0.en.html

## Contributing

We welcome contributions to Promptwright! Here's how you can help:

### Getting Started

1. Fork the repository
2. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```
3. Make your changes
4. Write or update tests as needed
5. Run tests locally to ensure everything passes
6. Commit your changes:
   ```bash
   git commit -m "feat: add your feature description"
   # or
   git commit -m "fix: fix your bug description"
   ```
7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide for Python code
- Add comments and documentation for new features
- Update the README.md if you're adding or changing functionality

### Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update the requirements.txt if you've added new dependencies
3. Ensure your PR description clearly describes the problem and solution
4. Link any related issues in your PR description
5. Request review from maintainers

### Reporting Issues

- Use the GitHub issue tracker to report bugs
- Include detailed steps to reproduce the issue
- Include browser version and OS if relevant
- Include screenshots if applicable
- Use issue templates if available

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Be patient with questions
- Provide constructive feedback
- Focus on what is best for the community

### Areas for Contribution

- Bug fixes
- Documentation improvements
- New test automation framework support
- Performance optimizations
- New cloud browser provider integrations
- UI/UX improvements
- Test coverage improvements

### Questions or Need Help?

Feel free to:
- Open a [GitHub Discussion](https://github.com/browser-use/browser-use/discussions)
- Join our [Discord server](https://discord.gg/7MGWNqbY)
- Check existing issues and discussions before creating new ones

Thank you for contributing to Promptwright! 🚀

