import streamlit as st

from api import generate_newsletter
from constants import companies_list

st.title("Education News Newsletter Generator")

st.write("Enter a list of companies (comma-separated) to fetch and summarize recent education-related news:")

companies_input = st.text_area("Companies:", companies_list)

if st.button("Generate Newsletter"):
    companies_list = [c.strip() for c in companies_input.split(",") if c.strip()]
    if not companies_list:
        st.error("Please provide at least one company.")
    else:
        with st.spinner("Fetching and summarizing news..."):
            articles, newsletter = generate_newsletter(companies_list)

        st.markdown("## Articles")
        for article in articles:
            st.markdown(
                f"[{article['title']}]({article['url']}) - {article['publishedAt']}"
            )
        st.write("---")
        st.markdown("## Generated Newsletter")
        st.write(newsletter)