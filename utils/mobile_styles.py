"""
Mobile-Responsive Styles for SwingFinder
Optimizes UI for phone and tablet viewing
"""

import streamlit as st


def apply_mobile_styles():
    """
    Apply mobile-responsive CSS to the Streamlit app.
    Makes the app work great on phones and tablets.
    """
    
    mobile_css = """
    <style>
    /* ========== MOBILE RESPONSIVE STYLES ========== */
    
    /* Make everything responsive */
    @media only screen and (max-width: 768px) {
        
        /* Reduce padding on mobile */
        .main .block-container {
            padding-top: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Make sidebar collapsible on mobile */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
        
        /* Larger touch targets for buttons */
        .stButton button {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px 24px !important;
        }
        
        /* Larger input fields */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox select {
            min-height: 44px !important;
            font-size: 16px !important;
        }
        
        /* Make sliders easier to use */
        .stSlider {
            padding: 10px 0 !important;
        }
        
        /* Stack columns on mobile */
        .row-widget.stHorizontal {
            flex-direction: column !important;
        }
        
        /* Make metrics stack vertically */
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
        
        /* Larger text for readability */
        .stMarkdown {
            font-size: 16px !important;
        }
        
        /* Make tables scrollable */
        .stDataFrame {
            overflow-x: auto !important;
        }
        
        /* Larger expander headers */
        .streamlit-expanderHeader {
            font-size: 18px !important;
            padding: 12px !important;
        }
        
        /* Make tabs easier to tap */
        .stTabs [data-baseweb="tab"] {
            min-height: 48px !important;
            font-size: 16px !important;
        }
    }
    
    /* ========== TABLET STYLES ========== */
    @media only screen and (min-width: 769px) and (max-width: 1024px) {
        
        .main .block-container {
            padding-top: 3rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Slightly larger touch targets */
        .stButton button {
            min-height: 44px !important;
        }
    }
    
    /* ========== GENERAL IMPROVEMENTS ========== */
    
    /* Better button styling */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* Better card styling */
    .element-container {
        border-radius: 8px !important;
    }
    
    /* Improve metric cards */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa !important;
        padding: 16px !important;
        border-radius: 8px !important;
        border: 1px solid #e9ecef !important;
    }
    
    /* Better expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        border: 1px solid #e9ecef !important;
    }
    
    /* Improve dataframe appearance */
    .stDataFrame {
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    /* Better alert boxes */
    .stAlert {
        border-radius: 8px !important;
        padding: 16px !important;
    }
    
    /* Improve progress bars */
    .stProgress > div > div {
        border-radius: 8px !important;
    }
    
    /* Better dividers */
    hr {
        margin: 2rem 0 !important;
        border: none !important;
        border-top: 2px solid #e9ecef !important;
    }
    
    /* ========== DARK MODE SUPPORT ========== */
    @media (prefers-color-scheme: dark) {
        
        div[data-testid="stMetric"] {
            background-color: #1e1e1e !important;
            border-color: #333 !important;
        }
        
        .streamlit-expanderHeader {
            background-color: #1e1e1e !important;
            border-color: #333 !important;
        }
        
        hr {
            border-top-color: #333 !important;
        }
    }
    
    /* ========== ACCESSIBILITY ========== */
    
    /* Focus indicators */
    button:focus,
    input:focus,
    select:focus {
        outline: 2px solid #0066cc !important;
        outline-offset: 2px !important;
    }
    
    /* Better contrast for links */
    a {
        color: #0066cc !important;
        text-decoration: underline !important;
    }
    
    a:hover {
        color: #0052a3 !important;
    }
    
    /* ========== CUSTOM COMPONENTS ========== */
    
    /* Stock cards */
    .stock-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
    }
    
    @media only screen and (max-width: 768px) {
        .stock-card {
            padding: 12px;
            margin: 6px 0;
        }
    }
    
    /* Alert badges */
    .alert-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 600;
        margin: 4px;
    }
    
    .alert-badge.bullish {
        background-color: #d4edda;
        color: #155724;
    }
    
    .alert-badge.bearish {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    .alert-badge.neutral {
        background-color: #fff3cd;
        color: #856404;
    }
    
    /* ========== LOADING STATES ========== */
    
    .stSpinner > div {
        border-color: #0066cc !important;
    }
    
    /* ========== SCROLLBAR STYLING ========== */
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    </style>
    """
    
    st.markdown(mobile_css, unsafe_allow_html=True)


def add_pwa_meta_tags():
    """
    Add Progressive Web App meta tags for mobile installation.
    """
    
    pwa_meta = """
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">
    <meta name="theme-color" content="#0066cc">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="SwingFinder">
    <link rel="apple-touch-icon" href="/favicon.ico">
    <link rel="manifest" href="/manifest.json">
    """
    
    st.markdown(pwa_meta, unsafe_allow_html=True)


def create_mobile_card(title: str, content: str, color: str = "blue"):
    """
    Create a mobile-friendly card component.
    """
    
    card_html = f"""
    <div class="stock-card">
        <h3 style="margin: 0 0 12px 0; color: {color};">{title}</h3>
        <div>{content}</div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


def create_alert_badge(text: str, badge_type: str = "neutral"):
    """
    Create a colored badge for alerts.
    badge_type: 'bullish', 'bearish', or 'neutral'
    """
    
    badge_html = f"""
    <span class="alert-badge {badge_type}">{text}</span>
    """
    
    return badge_html

