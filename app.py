import streamlit as st

from api import generate_newsletter, get_all_articles
from constants import companies_list

st.title("Education News Newsletter Generator")

outlets_popularity = st.radio(label="We can use top 10% of news outlets or top 30%, select one of the options.",
         options=["Top 10%", "Top 30%"], index=0)

st.write("Enter a list of companies (comma-separated) to fetch and summarize recent education-related news:")

companies_input = st.text_area("Companies:", companies_list)

if st.button("Generate Newsletter"):
    companies_list = [c.strip() for c in companies_input.split(",") if c.strip()]
    with st.spinner("Fetching and summarizing news..."):
        articles = get_all_articles(outlets_popularity, companies_list)
        newsletter = generate_newsletter(articles)

    st.markdown("## Articles")
    for article in articles:
        st.markdown(
            f"[{article['title']}]({article['url']}) - {article['publishedAt']}"
        )
    st.write("---")
    st.markdown("## Generated Newsletter")
    st.write(newsletter)