import streamlit as st
import requests
import random
import re
import tempfile
import os
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Import CairoSVG for SVG conversion
try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False
    st.warning("CairoSVG is not installed. SVG logos will not be displayed. Install with: pip install cairosvg")

# Logo sources with their templates - order matters for priority
LOGO_SOURCES = {
    "Clearbit": "https://logo.clearbit.com/{domain}?size=500",  # Increased size
    "Logo.dev": "https://logo.dev/api?domain={domain}&format=png&size=large",
    "Brandfetch": "https://api.brandfetch.io/v2/brands/{domain}",
    "Favicon Grabber": "https://favicongrabber.com/api/grab/{domain}?pretty=true",
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

def convert_svg_to_png(svg_content, width=None, height=None):
    """Convert SVG content to PNG format using CairoSVG."""
    if not HAS_CAIROSVG:
        return None
        
    try:
        # Create a BytesIO object to store the PNG
        png_io = BytesIO()
        
        # Convert SVG to PNG
        if width and height:
            cairosvg.svg2png(bytestring=svg_content, write_to=png_io, output_width=width, output_height=height)
        else:
            cairosvg.svg2png(bytestring=svg_content, write_to=png_io)
            
        # Reset the position to the beginning of the BytesIO object
        png_io.seek(0)
        
        # Open the PNG with PIL
        return Image.open(png_io)
    except Exception as e:
        st.error(f"Error converting SVG to PNG: {e}")
        return None

def fetch_svg_logo(url):
    """Fetch an SVG logo from a URL and convert it to PNG."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'svg' in content_type or url.lower().endswith('.svg'):
                return convert_svg_to_png(response.content, width=500)
    except Exception as e:
        st.warning(f"Error fetching SVG: {e}")
    
    return None

def scrape_website_for_logos(domain):
    """Scrape the website directly to find logo images."""
    logos = []
    
    # Special case for Float - directly try the known URL
    if domain == "floatapp.com":
        try:
            url = "https://cdn.prod.website-files.com/678ca6953be404b47f5b05db/678cc3b918806dafa4e6c497_Float-logo-purple.svg"
            if HAS_CAIROSVG:
                svg_img = fetch_svg_logo(url)
                if svg_img:
                    logos.append((f"Float SVG", svg_img))
                    st.success(f"Successfully converted Float's SVG logo from {url}")
            else:
                st.info(f"Found Float's logo at {url}, but CairoSVG is not installed for conversion.")
        except Exception as e:
            st.warning(f"Error with Float logo: {e}")
    
    try:
        url = f"https://{domain}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # More specific logo patterns
            logo_patterns = [
                re.compile(r'(?:^|\W)logo(?:\W|$)', re.I),  # More specific logo match
                re.compile(r'(?:^|\W)brand(?:\W|$)', re.I),  # More specific brand match
                re.compile(r'company-logo', re.I),  # Common class name
                re.compile(r'site-logo', re.I),     # Common class name
                re.compile(r'main-logo', re.I),     # Common class name
            ]
            
            # Try to find company name in the domain to help identify the logo
            company_name = domain.split('.')[0]
            
            # Strategy 1: Look for images with 'logo' in the attributes
            for img in soup.find_all('img'):
                img_src = img.get('src', '')
                img_alt = img.get('alt', '')
                img_class = ' '.join(img.get('class', []))
                img_id = img.get('id', '')
                
                # Check if any of these attributes contain logo-related terms
                is_logo = any(
                    pattern.search(attr) 
                    for pattern in logo_patterns
                    for attr in [img_src, img_alt, img_class, img_id]
                )
                
                # Check if image contains company name
                contains_company_name = company_name.lower() in img_src.lower() or company_name.lower() in img_alt.lower()
                
                if (is_logo or contains_company_name) and img_src:
                    absolute_url = urljoin(url, img_src)
                    try:
                        img_response = requests.get(absolute_url, timeout=10)
                        if img_response.status_code == 200:
                            try:
                                img_data = Image.open(BytesIO(img_response.content))
                                
                                # More selective filtering for better logos
                                # Logos typically aren't extremely wide/narrow
                                aspect_ratio = img_data.width / img_data.height if img_data.height > 0 else 0
                                min_size = min(img_data.width, img_data.height)
                                
                                # Better logo criteria:
                                # - Not too small (min dimension of 50px)
                                # - Not extremely wide or tall (aspect ratio between 0.3 and 5)
                                # - Reasonable size (not over 1000px, which might be a banner)
                                if (min_size >= 50 and 
                                    0.3 <= aspect_ratio <= 5 and 
                                    img_data.width <= 1000):
                                    logos.append((absolute_url, img_data))
                            except Exception:
                                pass
                    except Exception:
                        pass
            
            # Strategy 2: Check for SVG logos in links
            for link in soup.find_all(['a', 'link']):
                href = link.get('href', '')
                if '.svg' in href.lower() and ('logo' in href.lower() or company_name.lower() in href.lower()):
                    absolute_url = urljoin(url, href)
                    
                    if HAS_CAIROSVG:
                        svg_img = fetch_svg_logo(absolute_url)
                        if svg_img:
                            logos.append((f"SVG from website", svg_img))
                    else:
                        st.info(f"Found SVG logo at {absolute_url}, but CairoSVG is not installed for conversion.")
                        
    except Exception as e:
        st.warning(f"Error scraping website: {e}")
        
    # Find unique logos (avoid duplicates that just have different URLs)
    unique_logos = []
    seen_signatures = set()
    
    for url, img in logos:
        # Create a simple signature based on image size and aspect ratio
        signature = (img.width, img.height, img.width/img.height if img.height > 0 else 0)
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_logos.append((url, img))
    
    # Sort by image size (larger first) for better quality options
    unique_logos.sort(key=lambda x: x[1].width * x[1].height, reverse=True)
    
    # Return the top 3 largest unique logos
    return [("Website: " + domain, img) for url, img in unique_logos[:3]]

def fetch_logos(domain, max_alternatives=5, include_website_scraping=True):
    """Fetch logos from multiple sources including direct website scraping."""
    results = {}
    
    # Always try Clearbit first - it's most reliable
    clearbit_img = fetch_logo_from_source("Clearbit", domain)
    if clearbit_img:
        results["Clearbit"] = clearbit_img
    
    # Then try other API sources
    for source_name in LOGO_SOURCES:
        if source_name == "Clearbit":  # Skip Clearbit as we already tried it
            continue
            
        if len(results) >= max_alternatives:
            break
            
        img = fetch_logo_from_source(source_name, domain)
        if img:
            # Check if this image is significantly different from ones we already have
            # We'll use dimensions as a simple heuristic
            is_unique = True
            for existing_img in results.values():
                # If dimensions are within 10% of each other, consider them similar
                width_ratio = img.width / existing_img.width if existing_img.width > 0 else 0
                height_ratio = img.height / existing_img.height if existing_img.height > 0 else 0
                
                if 0.9 <= width_ratio <= 1.1 and 0.9 <= height_ratio <= 1.1:
                    is_unique = False
                    break
                    
            if is_unique:
                results[source_name] = img
    
    # Finally try website scraping for higher quality logos if enabled and we still need more
    if include_website_scraping and len(results) < max_alternatives:
        website_logos = scrape_website_for_logos(domain)
        
        for i, (source, img) in enumerate(website_logos):
            # Check if this image is unique compared to existing ones
            is_unique = True
            for existing_img in results.values():
                width_ratio = img.width / existing_img.width if existing_img.width > 0 else 0
                height_ratio = img.height / existing_img.height if existing_img.height > 0 else 0
                
                if 0.9 <= width_ratio <= 1.1 and 0.9 <= height_ratio <= 1.1:
                    is_unique = False
                    break
                    
            if is_unique:
                results[f"Website Logo {i+1}"] = img
                if len(results) >= max_alternatives:
                    break
    
    # Special case for floatapp.com - try to fetch the SVG directly if not already added
    if domain == "floatapp.com" and not any("SVG" in key for key in results.keys()):
        float_svg_url = "https://cdn.prod.website-files.com/678ca6953be404b47f5b05db/678cc3b918806dafa4e6c497_Float-logo-purple.svg"
        if HAS_CAIROSVG:
            svg_img = fetch_svg_logo(float_svg_url)
            if svg_img:
                results["Float Official SVG"] = svg_img
    
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