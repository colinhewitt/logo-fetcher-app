import streamlit as st
import requests
import random
from PIL import Image
from io import BytesIO

# Logo sources with their templates
LOGO_SOURCES = {
    "Clearbit": "https://logo.clearbit.com/{domain}",
    "Logo.dev": "https://logo.dev/api?domain={domain}&format=png",
    "Favicon Grabber": "https://favicongrabber.com/api/grab/{domain}?pretty=true",
    "Brandfetch": "https://api.brandfetch.io/v2/brands/{domain}",
    "DuckDuckGo": "https://icons.duckduckgo.com/ip3/{domain}.ico"
}

def fetch_logo_from_source(source_name, domain):
    """Fetch a logo from a specific source."""
    url_template = LOGO_SOURCES[source_name]
    url = url_template.format(domain=domain)
    
    try:
        response = requests.get(url, timeout=10)
        
        # Special handling for Favicon Grabber which returns JSON
        if source_name == "Favicon Grabber" and response.status_code == 200:
            favicon_data = response.json()
            if "icons" in favicon_data and len(favicon_data["icons"]) > 0:
                # Get the first icon URL
                icon_url = favicon_data["icons"][0].get("src")
                if icon_url:
                    response = requests.get(icon_url, timeout=10)
        
        # Special handling for Brandfetch which returns JSON
        if source_name == "Brandfetch" and response.status_code == 200:
            brand_data = response.json()
            if "logos" in brand_data and len(brand_data["logos"]) > 0:
                # Get the first logo URL
                logo_url = brand_data["logos"][0].get("formats", [{}])[0].get("src")
                if logo_url:
                    response = requests.get(logo_url, timeout=10)
        
        if response.status_code == 200 and response.content:
            try:
                return Image.open(BytesIO(response.content))
            except Exception:
                return None
    except Exception:
        return None
    
    return None

def fetch_logos(domain, max_alternatives=5):
    """Fetch logos from multiple sources."""
    results = {}
    
    # Try each source
    for source_name in LOGO_SOURCES:
        img = fetch_logo_from_source(source_name, domain)
        if img:
            results[source_name] = img
            # Stop if we have reached the max number of alternatives
            if len(results) >= max_alternatives:
                break
    
    return results

def resize_image(img, max_size=(300, 150)):
    """Resize image while maintaining aspect ratio."""
    img.thumbnail(max_size, Image.LANCZOS)
    return img

st.set_page_config(
    page_title="Logo Fetcher",
    page_icon="🖼️",
    layout="centered"
)

st.title("Company Logo Fetcher 🖼️")

st.write("Enter a company domain name (e.g., 'apple.com') to fetch its logo and alternatives.")

# Create a form - this will enable Enter key submission
with st.form(key="logo_form"):
    domain = st.text_input("Domain name", placeholder="e.g., apple.com")
    max_alternatives = st.slider("Number of alternatives to show", min_value=1, max_value=5, value=3)
    submit_button = st.form_submit_button(label="Fetch Logos", type="primary")

# Process the form submission (happens on Enter key or button click)
if submit_button and domain:
    if not domain.startswith("http"):
        if not "." in domain:
            domain += ".com"
    
    # Extract just the domain part if a full URL was entered
    if domain.startswith("http"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc
    
    with st.spinner(f"Fetching logos for {domain}..."):
        logos = fetch_logos(domain, max_alternatives)
        
        if logos:
            st.success(f"Found {len(logos)} logo sources for {domain}")
            
            # Display each logo with its source
            for i, (source_name, logo) in enumerate(logos.items()):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**Source {i+1}:**")
                    st.write(source_name)
                with col2:
                    resized_logo = resize_image(logo)
                    st.image(resized_logo, caption=f"{domain} logo from {source_name}")
        else:
            st.error(f"Could not fetch any logos for {domain}")

st.write("---")
st.write("Powered by multiple logo API services")