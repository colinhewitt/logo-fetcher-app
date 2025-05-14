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

# We'll use a simpler approach for SVG handling
HAS_SVG_SUPPORT = False

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

def check_svg_url(url):
    """Check if a URL points to a valid SVG file and return the URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, headers=headers, timeout=5)
        
        # Check if the URL exists (status code 200)
        if response.status_code != 200:
            return None
            
        # Check if it's an SVG by content type or file extension
        content_type = response.headers.get('Content-Type', '').lower()
        if 'svg' in content_type or url.lower().endswith('.svg'):
            # Double-check with a GET request to make sure it's actually an SVG
            get_response = requests.get(url, headers=headers, timeout=5)
            content = get_response.text.lower()
            
            # Look for basic SVG markers in the content
            if '<svg' in content and '</svg>' in content:
                return url
    except Exception:
        pass
    
    return None

def scrape_website_for_logos(domain):
    """Scrape the website directly to find logo images."""
    logos = []
    svg_urls = []
    
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
                    svg_url = check_svg_url(absolute_url)
                    if svg_url:
                        svg_urls.append((f"SVG from website", svg_url))
                        st.info(f"Found SVG logo at {svg_url}")
                        
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
    
    # Return the top 3 largest unique logos and any SVG URLs found
    return [("Website: " + domain, img) for url, img in unique_logos[:3]], svg_urls

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
    svg_urls = []
    if include_website_scraping and len(results) < max_alternatives:
        website_logos, svg_urls = scrape_website_for_logos(domain)
        
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
    
    # More advanced SVG detection based on common patterns but with more robust validation
    if not svg_urls:
        with st.spinner("Checking for SVG logos in common locations..."):
            # Check common logo paths if no SVGs were found yet
            company_name = domain.split('.')[0]
            
            # Try to intelligently find SVG logos at common paths
            common_svg_paths = [
                # Standard logo paths
                f"https://{domain}/logo.svg",
                f"https://{domain}/assets/logo.svg",
                f"https://{domain}/images/logo.svg",
                f"https://{domain}/static/logo.svg",
                f"https://{domain}/img/logo.svg",
                f"https://{domain}/media/logo.svg",
                
                # Company specific paths
                f"https://{domain}/assets/{company_name}-logo.svg",
                f"https://{domain}/images/{company_name}-logo.svg",
                f"https://{domain}/static/{company_name}-logo.svg",
                f"https://{domain}/img/{company_name}-logo.svg",
                f"https://{domain}/{company_name}-logo.svg",
                
                # WordPress common paths
                f"https://{domain}/wp-content/uploads/logo.svg",
                f"https://{domain}/wp-content/themes/default/logo.svg"
            ]
            
            # Try each path to see if it exists (but don't display failures)
            found_svg = False
            for path in common_svg_paths:
                if '*' in path:  # Skip paths with wildcards as they can't be directly requested
                    continue
                    
                svg_url = check_svg_url(path)
                if svg_url:
                    svg_urls.append((f"SVG Logo", svg_url))
                    found_svg = True
                    break  # Found one, no need to keep trying
            
            # If we didn't find any SVG logos in common paths, don't show anything
            if not found_svg:
                pass  # No message to avoid confusion
    
    # Display any SVG URLs found with embedded preview
    if svg_urls:
        st.info("### SVG Logos Found (Vector Format)")
        for name, url in svg_urls:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"**{name}**")
                st.markdown(f"[Open in browser]({url})")
                st.markdown(f"Download: `curl -o logo.svg {url}`")
                
            with col2:
                # Try to display the SVG directly using HTML
                try:
                    # Fetch the SVG content
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200 and ('svg' in response.headers.get('Content-Type', '') or url.endswith('.svg')):
                        svg_content = response.text
                        
                        # Format SVG for display - add fixed dimensions if not present
                        if 'width=' not in svg_content.lower() and 'height=' not in svg_content.lower():
                            svg_content = svg_content.replace('<svg', '<svg width="200" height="100"', 1)
                        
                        # Embed the SVG directly using HTML
                        st.components.v1.html(
                            f"""
                            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                                {svg_content}
                                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                                    ↑ Vector SVG Preview (scales perfectly at any size)
                                </p>
                            </div>
                            """,
                            height=150
                        )
                    else:
                        st.warning("Could not preview SVG - check URL")
                except Exception as e:
                    st.warning(f"Could not preview SVG: {str(e)[:100]}")
    
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