import json
import time

import requests
import streamlit as st
from dateutil.parser import isoparse
from newsdataapi import NewsDataApiClient
from openai import OpenAI
from datetime import datetime, timedelta

from constants import education_terms, companies

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
)

api = NewsDataApiClient(apikey=st.secrets["NEWS_API_KEY"])


def article_is_education_related(title, description):
    text = (title or "") + " " + (description or "")
    text_lower = text.lower()
    return any(term in text_lower for term in education_terms)


def get_bing_news(query):
    endpoint = "https://api.bing.microsoft.com/v7.0/news/search"
    params = {
        "q": query,
        "mkt": "en-US",
        "count": 50,
        "freshness": "Day",
        "sortBy": "Relevance"
    }
    headers = {
        "Ocp-Apim-Subscription-Key": st.secrets['BING_API_KEY']
    }
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        print(e)
        return []

    time.sleep(0.5)
    data = response.json()

    articles = data.get("value", [])
    filtered_articles = []
    for article in articles:
        pub_date_str = article.get("datePublished")
        title = article.get("name", "")
        description = article.get("description", "")
        url = article.get("url", "")
        pub_date = isoparse(pub_date_str)
        sources = article.get("provider", {})

        if article_is_education_related(title, description):
            filtered_articles.append({
                "title": title,
                "url": url,
                "description": description,
                "publishedAt": pub_date.isoformat(),
                "sources": [source['name'] for source in sources]})
    return filtered_articles


def get_newsapi_articles(outlets_popularity):
    if outlets_popularity == "Top 10%":
        priority = "top"
    else:
        priority = "medium"
    articles_data = api.latest_api(q="education", category=["education"],
                                   country="us", language="en", prioritydomain=priority,
                                   scroll=True, max_result=50)

    filtered_articles = []
    for article in articles_data["results"]:
        source_name = (article.get("source_name") or {}).lower()
        title = article.get("title", "")
        description = article.get("description", "")
        url = article.get("link", "")
        published_str = article.get("pubDate", "")

        try:
            pub_date = isoparse(published_str)
        except ValueError:
            continue

        now = datetime.now()
        if (now - timedelta(hours=24) <= pub_date <= now) and article_is_education_related(title, description):
            filtered_articles.append({
                "title": title,
                "url": url,
                "description": description,
                "publishedAt": pub_date.isoformat(),
                "sources": [source_name]
            })

    return filtered_articles


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def reduce_articles_batch(articles):
    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\nSources: {art['sources']}\n"

    prompt = f"""
        Role: You are an AI assistant that filters and prioritizes education-related news articles for an education-focused venture capital firm’s newsletter.
        Task:
        You are given a list of articles.
        Select exactly 10 articles that meet all of the following criteria:
        - Primarily cover education news.
        - Are important or broadly newsworthy, reflecting U.S. or global trends (avoid highly localized or niche events).
        - Exclude articles containing extremely negative or sensitive content (e.g., school shootings).
        - Exclude articles that do not indicate a significant development or trend in education.
        
        Output the chosen articles only in a JSON-like list of 10 objects with the keys:
        "title"
        "url"
        "description"
        "publishedAt"
        "sources"
        
        Do not include anything else in your final output—no explanations, no extra text.
        
        Articles:
        {articles_text}
        
        Output format:
        [{{"title":"...", "url":"...", "description":"...", "publishedAt":"...", "sources":"..."}}, ...]
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system",
                   "content": "You are an AI assistant that filters and prioritizes education-related news articles"},
                  {"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()
    reduced_articles = json.loads(content)
    return reduced_articles


def get_all_articles(outlets_popularity):
    bing_articles = []

    for company_name in companies:
        search_term = f'"{company_name}" education'
        bing_articles_batch = get_bing_news(search_term)
        bing_articles.extend(bing_articles_batch)

    newsapi_articles = get_newsapi_articles(outlets_popularity)
    all_articles = bing_articles + newsapi_articles

    chunk_size = 20
    reduced_all = []
    if len(all_articles) > chunk_size:
        for chunk in chunk_list(all_articles, chunk_size):
            reduced_chunk = reduce_articles_batch(chunk)
            reduced_all.extend(reduced_chunk)

    return reduced_all


def create_final_newsletter_prompt(articles):
    """
    Create the prompt for the final newsletter, including a user-facing structure
    for a multi-section education newsletter.
    """
    # Sort articles from newest to oldest
    articles.sort(key=lambda x: x['publishedAt'], reverse=True)

    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += (
            f"\nArticle {i}:\n"
            f"Title: {art['title']}\n"
            f"Summary: {art['description']}\n"
            f"URL: {art['url']}\n"
            f"PublishedAt: {art['publishedAt']}\n"
        )

    prompt = f"""
        Role: You are an AI newsletter writer for an education-focused venture fund, primarily covering U.S. education news (with limited global highlights if relevant).
        
        Instructions:
        
        Input:
        A list of priority companies whose news should be highlighted first.
        A batch of articles.
        
        Focus:
        Include only non-sensitive content (exclude events like school shootings or other highly negative items).
        Articles should primarily center on U.S. education (global news is acceptable but should not overshadow U.S. coverage).
        Deduplicate articles and prioritize those involving the priority companies or that show significant trends in education.
        
        Output Format: A visually appealing, professional newsletter with the following structure:
        Header
        Subject Line: Standard text with today’s date plus a relevant news teaser (e.g., “Antwalk raises $7.5M,” etc.).
        Preview Text (100–140 characters): Summarize the first three headlines in sentence form to encourage opens.
        Breaking News Section (1–2 articles, optional if no urgent developments)
        Top Stories Section (exactly 3 articles)
        More Stories Section, further divided into subcategories (1–5 articles each, 2–3 is ideal):
        AI
        Pre-K–12
        Workforce Learning & Skills
        Higher Ed & HireEd
        Within these categories, include any remaining important stories.
        
        Styling:
        Keep the text professional, concise, and visually clear.
        Ensure the newsletter reads as if it were polished and ready to send out.
        
        Constraints:
        Do not include explanatory text or commentary outside the newsletter.
        Do not exceed the requested number of articles in each section.
        End by presenting the final newsletter in the format described, and nothing else.
        
        Your Task:
        Read the provided list of priority companies and news articles in {articles_text}.
        Filter, categorize, and prioritize the stories as specified above.
        Present the final newsletter as your complete and only output.
        Input:
        Priority Companies:
        {companies}
        Articles: {articles_text}
        Final Output:
        (Newsletter in the exact structure required, no extra text.)
        Now produce the final newsletter.
    """
    return prompt


def generate_newsletter(all_articles):
    final_prompt = create_final_newsletter_prompt(all_articles)

    # 3. Send the prompt to GPT to create the newsletter
    response = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system", "content": "You are an AI newsletter writer for an education-focused venture fund."},
            {"role": "user", "content": final_prompt}
        ]
    )

    newsletter = response.choices[0].message.content
    return newsletter
