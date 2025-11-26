# Environment Configuration Migration Guide

This document summarizes the migration from system environment variables to `.env` file configuration.

## What Changed

AgentMove now supports `.env` file for configuration management, making it easier to set up and maintain API keys and other settings.

## Quick Start

### For New Users

```bash
# 1. Copy the example configuration
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env  # or use any text editor

# 3. Start using AgentMove
python -m agent ...
```

### For Existing Users

Your existing environment variables (in `.bashrc` or shell) will continue to work. The `.env` file is optional but recommended.

## Migration Steps

If you want to migrate from `.bashrc` to `.env`:

1. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

2. **Copy your existing values**:
   Open your `.bashrc` or shell config and copy the values:
   ```bash
   # Old way (in .bashrc)
   export SiliconFlow_API_KEY="your_key"
   export nominatim_deploy_server_address="127.0.0.1:8080"
   ```

   Add them to `.env` (without `export`):
   ```bash
   # New way (in .env)
   SiliconFlow_API_KEY=your_key
   nominatim_deploy_server_address=127.0.0.1:8080
   ```

3. **(Optional) Remove from `.bashrc`**:
   You can remove the `export` lines from `.bashrc` if you prefer to use `.env` exclusively.

## File Structure

```
AgentMove/
├── .env                    # Your configuration (git-ignored)
├── .env.example            # Template with all available options
├── config.py               # Loads .env automatically
├── app/
│   └── backend/
│       └── config.py       # Also loads .env for demo settings
```

## Configuration Options

### LLM API Keys (Required - at least one)

```bash
SiliconFlow_API_KEY=your_key_here
DeepInfra_API_KEY=your_key_here
OpenAI_API_KEY=your_key_here
OpenRouter_API_KEY=your_key_here
vllm_KEY=EMPTY
```

### Address Resolution (Required for preprocessing)

```bash
nominatim_deploy_server_address=127.0.0.1:8080
```

### Optional Settings

```bash
# Proxy (leave empty if not needed)
PROXY=

# Demo server configuration
DEMO_HOST=0.0.0.0
DEMO_PORT=8000
DEMO_DEFAULT_CITY=Shanghai
DEMO_DEFAULT_MODEL=qwen2.5-7b
DEMO_DEFAULT_PLATFORM=SiliconFlow
```

## How It Works

1. **Automatic Loading**: When you import `config.py`, it automatically loads variables from `.env`
2. **Fallback**: If `.env` doesn't exist, it falls back to system environment variables
3. **No Breaking Changes**: Existing setups continue to work without modification

## Code Changes

### config.py

```python
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Now os.environ.get() works with both .env and system vars
PROXY = os.environ.get("PROXY", "")
NOMINATIM_DEPLOY_SERVER = os.environ.get("nominatim_deploy_server_address", "127.0.0.1:8080")
```

### app/backend/config.py

```python
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DEMO_CONFIG = {
    "host": os.environ.get("DEMO_HOST", "0.0.0.0"),
    "port": int(os.environ.get("DEMO_PORT", "8000")),
    # ...
}
```

## Troubleshooting

### Q: I get "python-dotenv not installed" warning

**A**: Install it:
```bash
pip install python-dotenv
# or
pip install -r requirements.txt
```

### Q: My .env file is not being loaded

**A**: Check:
1. The file is named exactly `.env` (not `env` or `.env.txt`)
2. The file is in the project root directory
3. `python-dotenv` is installed

### Q: Can I use both .env and system environment variables?

**A**: Yes! System environment variables take precedence over `.env` values.

### Q: Is .env file committed to git?

**A**: No, `.env` is in `.gitignore`. Only `.env.example` is tracked.

## Benefits of Using .env

1. **Easier Setup**: Copy and edit one file instead of modifying shell config
2. **Project-Specific**: Each project can have its own configuration
3. **No Shell Restart**: Changes take effect immediately, no need to reload shell
4. **Security**: File is git-ignored by default, reducing risk of accidentally committing keys
5. **Cross-Platform**: Works consistently across different operating systems

## Related Files

- [.env.example](.env.example) - Configuration template
- [config.py](config.py) - Main configuration loader
- [app/backend/config.py](app/backend/config.py) - Demo configuration
- [README.md](README.md) - User documentation
- [CLAUDE.md](CLAUDE.md) - Developer documentation

## Support

If you encounter any issues with the new configuration system, please:
1. Check this guide
2. Verify your `.env` file syntax
3. Try using system environment variables as a fallback
4. Open an issue on GitHub if problems persist
