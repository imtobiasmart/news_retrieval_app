import streamlit as st

from api import generate_newsletter, get_all_articles
from constants import companies_list

st.title("Education News Newsletter Generator")

st.write("Enter a list of companies (comma-separated) to fetch and summarize recent education-related news:")

companies_input = st.text_area("Companies:", companies_list)

if st.button("Generate Newsletter"):
    companies_list = [c.strip() for c in companies_input.split(",") if c.strip()]
    with st.spinner("Fetching and summarizing news..."):
        articles = get_all_articles(companies_list)
        newsletter = generate_newsletter(articles)

    st.markdown("## Articles")
    for article in articles:
        st.markdown(
            f"{article['title']} [{article['source']}]({article['url']}) - {article['publishedAt']}"
        )
    st.write("---")
    st.markdown("## Generated Newsletter")
    st.write(newsletter)
