# Logo Fetcher Quick Start Guide

This guide will help you get up and running with the Logo Fetcher app in under 5 minutes.

## For Team Testing

### Prerequisites
- Python 3.6 or higher
- pip (Python package manager)

### Step 1: Get the Code

**Option A: From ZIP file**
1. Extract the ZIP file to a folder on your computer
2. Open a terminal/command prompt
3. Navigate to the extracted folder: `cd path/to/logo-fetcher-app`

**Option B: From GitHub**
```bash
git clone https://github.com/yourusername/logo-fetcher-app
cd logo-fetcher-app
```

### Step 2: Install Dependencies

```bash
# For macOS/Linux
python3 -m pip install -r requirements.txt

# For Windows
python -m pip install -r requirements.txt
```

### Step 3: Test Run

**Web App Mode (Recommended for first-time users)**
```bash
# For macOS/Linux
streamlit run logo_fetcher.py

# For Windows
python -m streamlit run logo_fetcher.py
```
Your browser should open automatically to http://localhost:8501

**Command Line Mode**
```bash
# For macOS/Linux
python3 logo_fetcher.py apple.com "Apple Inc"

# For Windows
python logo_fetcher.py apple.com "Apple Inc"
```
Check the `logos` folder for your downloaded logo.

## Common Issues

1. **"Command not found: streamlit"**
   - Make sure your Python environment is in your PATH
   - Try running: `python -m streamlit run logo_fetcher.py`

2. **"No module named 'streamlit'"**
   - Install dependencies again: `pip install -r requirements.txt`
   - Try: `pip install streamlit`

3. **"Cannot connect to Streamlit"**
   - Try accessing http://localhost:8501 manually in your browser
   - Check if port 8501 is already in use: `netstat -ano | findstr 8501` (Windows) or `lsof -i:8501` (macOS/Linux)

4. **"No logo found"**
   - Try a different company domain
   - Check your internet connection

## Next Steps

- Try different company domains
- Customize the size by changing `TARGET_W` and `TARGET_H` constants
- Explore the code to understand how it works

Need help? Contact: [your-email@company.com]