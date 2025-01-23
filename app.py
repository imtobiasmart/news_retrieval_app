import streamlit as st
from api import get_all_articles, generate_newsletter
from constants import companies_list

st.title("Newsletter Generator")

news_topic = st.radio("Select the type of newsletter you want to generate:", ["Education", "Finance", "General"])

st.write("Enter a list of keywords (comma-separated) to fetch and summarize recent news:")

keywords_input = st.text_area("Keywords:", companies_list)

is_newsletter_generated = st.radio("Do you want to generate the newsletter? If \"No\" is selected, you will only see the articles found.", ["Yes", "No"])

if st.button("Generate Newsletter"):
    keywords_list = [c.strip() for c in keywords_input.split(",") if c.strip()]
    with st.spinner("Fetching and summarizing news..."):
        articles = get_all_articles(keywords_list, news_topic)
        if is_newsletter_generated == "Yes":
            newsletter = generate_newsletter(articles, news_topic)

    st.markdown("## Articles")

    for article in articles:
        title = article['title'].replace('$', '\\$')
        source = article['source'].replace('$', '\\$')
        st.markdown(
            f"{title} [{source}]({article['url']}) - {article['publishedAt']}"
        )
    if is_newsletter_generated == "Yes":
        st.write("---")
        st.markdown("## Generated Newsletter")
        newsletter = newsletter.replace('$', '\\$')
        st.write(newsletter)
