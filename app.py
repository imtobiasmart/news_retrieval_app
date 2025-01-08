import streamlit as st

from api import generate_newsletter, get_all_articles

st.title("Education News Newsletter Generator")

outlets_popularity = st.radio(label="We can use top 10% of news outlets or top 30%, select one of the options.",
         options=["Top 10%", "Top 30%"], default="Top 10%")

if st.button("Generate Newsletter"):
    with st.spinner("Fetching and summarizing news..."):
        articles = get_all_articles(outlets_popularity)
        newsletter = generate_newsletter(articles)

    st.markdown("## Articles")
    for article in articles:
        st.markdown(
            f"[{article['title']}]({article['url']}) - {article['publishedAt']}"
        )
    st.write("---")
    st.markdown("## Generated Newsletter")
    st.write(newsletter)