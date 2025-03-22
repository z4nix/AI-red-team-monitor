import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import PaperDatabase
from config import APP_TITLE, APP_DESCRIPTION

# Page config
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🔍",
    layout="wide"
)

# Initialize database
db = PaperDatabase()

def main():
    # Header
    st.title(APP_TITLE)
    st.markdown(APP_DESCRIPTION)
    
    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Time period filter
    days_options = [7, 14, 30, 90, 180, 365]
    selected_days = st.sidebar.selectbox(
        "Time period", 
        options=days_options,
        format_func=lambda x: f"Last {x} days",
        index=0
    )
    
    # Category filter
    categories = ["All Categories"] + db.get_all_categories()
    selected_category = st.sidebar.selectbox("Attack category", categories)
    
    # Relevance score filter
    min_relevance = st.sidebar.slider(
        "Minimum relevance score", 
        min_value=1, 
        max_value=10, 
        value=1
    )
    
    # Get papers based on filters
    if selected_category == "All Categories":
        papers = db.get_recent_papers(days=selected_days, min_relevance=min_relevance)
    else:
        papers = db.get_papers_by_category(selected_category, days=selected_days)
        # Apply relevance filter manually since it's not part of category query
        papers = [p for p in papers if p.get('relevance_score', 0) >= min_relevance]
    
    # Database stats in sidebar
    st.sidebar.title("Database Stats")
    stats = db.get_stats()
    st.sidebar.metric("Total Papers", stats['total_papers'])
    st.sidebar.metric("Processed Papers", stats['processed_papers'])
    st.sidebar.metric("New Papers (Last 7 Days)", stats['recent_papers'])
    
    # Main content
    tabs = st.tabs(["Papers", "Analytics"])
    
    # Papers tab
    with tabs[0]:
        st.header("Research Papers")
        
        # No papers message
        if not papers:
            st.info(f"No papers found matching your criteria. Try adjusting the filters.")
            return
            
        # Papers count
        st.write(f"Found **{len(papers)}** papers matching your criteria.")
        
        # Sort options
        sort_options = {
            "Newest first": lambda x: x.get('published', ''),
            "Highest relevance first": lambda x: -x.get('relevance_score', 0),
            "Oldest first": lambda x: -x.get('published', '')
        }
        
        sort_by = st.selectbox(
            "Sort by", 
            options=list(sort_options.keys()),
            index=0
        )
        
        # Sort papers
        sorted_papers = sorted(papers, key=sort_options[sort_by], reverse=sort_by=="Newest first")
        
        # Display papers
        for i, paper in enumerate(sorted_papers):
            with st.expander(f"{paper['title']}"):
                # Paper metadata
                cols = st.columns([3, 1])
                
                with cols[0]:
                    st.write(f"**Authors:** {', '.join(paper['authors'])}")
                    st.write(f"**Published:** {paper['published']}")
                    
                    # Categories with styling
                    if paper.get('attack_categories'):
                        st.write("**Attack Categories:**")
                        cat_html = " ".join([f"<span style='background-color:#e6f3ff; padding:3px 7px; border-radius:10px; margin-right:5px;'>{cat}</span>" for cat in paper['attack_categories']])
                        st.markdown(cat_html, unsafe_allow_html=True)
                
                with cols[1]:
                    # Relevance score with color
                    score = paper.get('relevance_score', 0)
                    if score >= 8:
                        color = "#ff4b4b"  # Red for high relevance
                    elif score >= 5:
                        color = "#ffa64b"  # Orange for medium relevance
                    else:
                        color = "#4b8bff"  # Blue for low relevance
                        
                    st.markdown(f"""
                    <div style='background-color:{color}; padding:10px; border-radius:5px; text-align:center; color:white;'>
                        <div style='font-size:12px'>Relevance Score</div>
                        <div style='font-size:24px; font-weight:bold;'>{score}/10</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Paper summaries
                st.subheader("Brief Overview")
                st.write(paper.get('brief_overview', 'No overview available'))
                
                st.subheader("Technical Explanation")
                st.write(paper.get('technical_explanation', 'No technical explanation available'))
                
                # Links 
                st.write("**Links:**")
                col1, col2 = st.columns(2)
                col1.markdown(f"[View Abstract]({paper['abstract_url']})")
                col2.markdown(f"[Download PDF]({paper['pdf_url']})")
                
                # Add separator if not last item
                if i < len(sorted_papers) - 1:
                    st.markdown("---")
    
    # Analytics tab
    with tabs[1]:
        if papers:
            st.header("Paper Analytics")
            
            # Prepare data for charts
            df = pd.DataFrame(papers)
            
            # Add date column
            df['date'] = pd.to_datetime(df['published'])
            
            # Create two columns
            col1, col2 = st.columns(2)
            
            with col1:
                # Papers by category
                if 'attack_categories' in df.columns:
                    # Flatten categories
                    categories_flat = []
                    for cats in df['attack_categories']:
                        if isinstance(cats, list) and cats:
                            categories_flat.extend(cats)
                    
                    if categories_flat:
                        # Count occurrences of each category
                        category_counts = pd.Series(categories_flat).value_counts()
                        
                        # Create pie chart
                        fig1 = px.pie(
                            names=category_counts.index,
                            values=category_counts.values,
                            title='Distribution of Attack Categories',
                            hole=0.3
                        )
                        st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Papers by relevance score
                if 'relevance_score' in df.columns:
                    # Group by relevance score
                    relevance_counts = df['relevance_score'].value_counts().sort_index()
                    
                    # Create bar chart
                    fig2 = px.bar(
                        x=relevance_counts.index,
                        y=relevance_counts.values,
                        title='Papers by Relevance Score',
                        labels={'x': 'Relevance Score', 'y': 'Number of Papers'},
                        color=relevance_counts.index,
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Time series of papers
            if 'date' in df.columns:
                # Group by date
                papers_by_date = df.groupby(df['date'].dt.date).size()
                
                # Create time series chart
                fig3 = px.line(
                    x=papers_by_date.index,
                    y=papers_by_date.values,
                    title='Papers Published Over Time',
                    labels={'x': 'Date', 'y': 'Number of Papers'}
                )
                st.plotly_chart(fig3, use_container_width=True)

if __name__ == "__main__":
    main()
