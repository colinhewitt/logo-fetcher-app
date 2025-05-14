# Logo Fetcher App

A dual-purpose tool to fetch, resize, and standardize company logos for reports and presentations. Works as both a command-line utility and a browser-based application.

## Features

- Fetches company logos from multiple sources (Clearbit, Logo.dev)
- Resizes logos to a uniform 160 × 80 px format with transparent padding
- Maintains aspect ratio during resizing
- Works both as a CLI tool and browser-based app
- Saves logos to a dedicated directory or offers download button

## Installation

```bash
# Clone this repository
git clone https://github.com/yourusername/logo-fetcher-app.git
cd logo-fetcher-app

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Command-line Mode

Simply provide a URL and company name:

```bash
python logo_fetcher.py https://openai.com "OpenAI"
```

This will:
1. Fetch the OpenAI logo
2. Resize it to 160 × 80 px
3. Save it to a `logos/` directory in PNG format

### Browser App Mode

Launch the Streamlit web interface:

```bash
streamlit run logo_fetcher.py
```

This will:
1. Open a browser window with the Logo Fetcher UI
2. Allow you to input company URL and name
3. Show a preview of the processed logo
4. Provide a download button for the PNG file

## How It Works

1. First tries Clearbit's Logo API (will sunset on Dec 1, 2025)
2. Falls back to Logo.dev if Clearbit fails
3. Uses the Pillow library for high-quality image processing
4. Maintains aspect ratio while fitting to target dimensions
5. Adds transparent padding to standardize dimensions

## Dependencies

- Python 3.6+
- requests: For HTTP requests
- pillow: For image processing
- streamlit: For the browser UI (only needed for web mode)

## Testing

You can quickly test if the tool is working with these examples:

```bash
# CLI examples
python logo_fetcher.py https://apple.com "Apple"
python logo_fetcher.py https://microsoft.com "Microsoft"

# Web UI
streamlit run logo_fetcher.py
```

## Troubleshooting

- If Streamlit doesn't open automatically, try accessing: http://localhost:8501
- If no logo is found, try using just the domain: `python logo_fetcher.py google.com "Google"`
- For deployment issues, ensure ports 8501 are not blocked by firewalls

## License

MIT