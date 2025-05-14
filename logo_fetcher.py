import streamlit as st
import requests
import random
import re
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

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

def scrape_website_for_logos(domain):
    """Scrape the website directly to find logo images."""
    logos = []
    try:
        url = f"https://{domain}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Strategy 1: Look for images with 'logo' in the filename, src, alt, or class
            logo_patterns = [
                re.compile(r'logo', re.I),  # Case-insensitive 'logo'
                re.compile(r'brand', re.I),  # Case-insensitive 'brand'
                re.compile(r'header', re.I),  # Header images sometimes contain logos
            ]
            
            for img in soup.find_all('img'):
                img_src = img.get('src', '')
                img_alt = img.get('alt', '')
                img_class = ' '.join(img.get('class', []))
                
                # Check if any of these attributes contain 'logo'
                is_logo = any(
                    pattern.search(attr) 
                    for pattern in logo_patterns
                    for attr in [img_src, img_alt, img_class]
                )
                
                if is_logo and img_src:
                    absolute_url = urljoin(url, img_src)
                    try:
                        img_response = requests.get(absolute_url, timeout=10)
                        if img_response.status_code == 200:
                            try:
                                img_data = Image.open(BytesIO(img_response.content))
                                
                                # Filter tiny images that are unlikely to be logos
                                if img_data.width >= 50 and img_data.height >= 50:
                                    logos.append((absolute_url, img_data))
                            except Exception:
                                pass
                    except Exception:
                        pass
            
            # Strategy 2: Look for SVG logos
            for svg in soup.find_all('svg'):
                svg_class = ' '.join(svg.get('class', []))
                if any(pattern.search(svg_class) for pattern in logo_patterns):
                    # We can't directly convert SVG to image here, but we can note it
                    st.write(f"Found SVG logo, but cannot convert it directly")
                    
            # Strategy 3: Look for favicon links
            for link in soup.find_all('link', rel=lambda r: r and ('icon' in r.lower())):
                href = link.get('href')
                if href:
                    absolute_url = urljoin(url, href)
                    try:
                        link_response = requests.get(absolute_url, timeout=10)
                        if link_response.status_code == 200:
                            try:
                                img_data = Image.open(BytesIO(link_response.content))
                                # Only add if decent size
                                if img_data.width >= 32 and img_data.height >= 32:
                                    logos.append((absolute_url, img_data))
                            except Exception:
                                pass
                    except Exception:
                        pass
                        
    except Exception as e:
        st.warning(f"Error scraping website: {e}")
        
    # Sort by image size (larger first) for better quality options
    logos.sort(key=lambda x: x[1].width * x[1].height, reverse=True)
    
    # Return the top 3 largest logos
    return [("Website: " + url, img) for url, img in logos[:3]]

def fetch_logos(domain, max_alternatives=5, include_website_scraping=True):
    """Fetch logos from multiple sources including direct website scraping."""
    results = {}
    
    # First try website scraping for higher quality logos if enabled
    if include_website_scraping:
        website_logos = scrape_website_for_logos(domain)
        for i, (source, img) in enumerate(website_logos):
            results[f"Website Logo {i+1}"] = img
            if len(results) >= max_alternatives:
                return results
    
    # Then try API sources
    for source_name in LOGO_SOURCES:
        if len(results) >= max_alternatives:
            break
            
        img = fetch_logo_from_source(source_name, domain)
        if img:
            results[source_name] = img
    
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
    include_website_scraping = st.checkbox("Include direct website scraping (higher quality logos)", value=True)
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
        logos = fetch_logos(domain, max_alternatives, include_website_scraping)
        
        if logos:
            st.success(f"Found {len(logos)} logo sources for {domain}")
            
            # Display each logo with its source and quality info
            for i, (source_name, logo) in enumerate(logos.items()):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**Source {i+1}:**")
                    st.write(source_name)
                    st.write(f"Size: {logo.width}×{logo.height}px")
                with col2:
                    resized_logo = resize_image(logo)
                    st.image(resized_logo, caption=f"{domain} logo from {source_name}")
                    
                # Add download button for each logo
                img_byte_arr = BytesIO()
                logo.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                st.download_button(
                    label=f"Download {source_name} Logo",
                    data=img_byte_arr,
                    file_name=f"{domain.replace('.', '_')}_{source_name.replace(' ', '_').replace(':', '')}_logo.png",
                    mime="image/png",
                )
                
                st.write("---")
        else:
            st.error(f"Could not fetch any logos for {domain}")

st.write("---")
st.write("Powered by multiple logo API services")