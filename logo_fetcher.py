import streamlit as st
import requests
from PIL import Image
from io import BytesIO

def fetch_logo(domain):
    """Fetch a company logo from Clearbit's Logo API."""
    url = f"https://logo.clearbit.com/{domain}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            st.error(f"Could not fetch logo for {domain}. Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching logo: {e}")
        return None

st.set_page_config(
    page_title="Company Logo Fetcher",
    page_icon="🖼️",
    layout="centered"
)

st.title("Company Logo Fetcher 🖼️")

st.write("Enter a company domain name (e.g., 'apple.com') to fetch its logo.")
st.write("App running at http://localhost:8501")

# Create a form - this will enable Enter key submission
with st.form(key="logo_form"):
    domain = st.text_input("Domain name", placeholder="e.g., apple.com")
    submit_button = st.form_submit_button(label="Fetch Logo", type="primary")

# Process the form submission (happens on Enter key or button click)
if submit_button and domain:
    if not domain.startswith("http"):
        if not "." in domain:
            domain += ".com"
    
    # Extract just the domain part if a full URL was entered
    if domain.startswith("http"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc
    
    with st.spinner(f"Fetching logo for {domain}..."):
        logo = fetch_logo(domain)
        
        if logo:
            st.image(logo, caption=f"Logo for {domain}")
            st.success(f"Successfully fetched logo for {domain}")

st.write("Powered by Clearbit's Logo API")