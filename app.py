import streamlit as st

from api import generate_newsletter, get_all_articles

st.title("Education News Newsletter Generator")

if st.button("Generate Newsletter"):
    with st.spinner("Fetching and summarizing news..."):
        articles = get_all_articles()
        newsletter = generate_newsletter(articles)

    st.markdown("## Articles")
    for article in articles:
        st.markdown(
            f"[{article['title']}]({article['url']}) - {article['publishedAt']}"
        )
    st.write("---")
    st.markdown("## Generated Newsletter")
    st.write(newsletter)