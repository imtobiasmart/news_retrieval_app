import requests
from dateutil.parser import isoparse
from openai import OpenAI
import streamlit as st
import json

from constants import education_terms

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
)


def article_is_education_related(title, description):
    text = (title or "") + " " + (description or "")
    text_lower = text.lower()
    return any(term in text_lower for term in education_terms)


def get_bing_news(query):
    endpoint = "https://api.bing.microsoft.com/v7.0/news/search"
    params = {
        "q": query,
        "mkt": "en-US",
        "count": 20,
        "freshness": "Day",
        "sortBy": "Relevance"
    }
    headers = {
        "Ocp-Apim-Subscription-Key": st.secrets["BING_API_KEY"]
    }
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        return []

    data = response.json()

    articles = data.get("value", [])
    filtered_articles = []
    for article in articles:
        pub_date_str = article.get("datePublished")
        title = article.get("name", "")
        description = article.get("description", "")
        url = article.get("url", "")
        pub_date = isoparse(pub_date_str)
        if article_is_education_related(title, description):
            filtered_articles.append({
                "title": title,
                "url": url,
                "description": description,
                "publishedAt": pub_date.isoformat()
            })
    return filtered_articles


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def reduce_articles_batch(articles):
    """
    Given a batch of articles, ask the AI model to pick out the most important 25 articles.
    You can also ask it to categorize them if you prefer.
    """
    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\n"

    prompt = f"""
You are an assistant that filters and prioritizes education-related news articles.
Return only the JSON array of objects, with no additional text, disclaimers, or code blocks. 
The output should be valid JSON containing up to 15 articles in the specified format. 
Do not include ellipses or placeholders. If there are fewer than 15 articles, just include those. 
No explanation should precede or follow the JSON.
You are given a list of articles.
Your task is to select up to 15 most important or newsworthy articles from the batch based on their descriptions. The relevance is determined as impact to the education field. 
Output them in a simple structured JSON-like format with keys: title, url, description, publishedAt.

Articles:
{articles_text}

Now select up to 15 top articles in terms of newsworthiness or importance, output as a list of objects that can be loaded to json. Only include news from the US or World in general, nothing super specific to other countries:
[{{"title":"...", "url":"...", "description":"...", "publishedAt":"..."}}, ...]
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a system that only outputs structured JSON. Do not include any commentary or explanation."},
                  {"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content.strip()

    return json.loads(content)


def create_final_newsletter_prompt(articles):
    articles.sort(key=lambda x: x['publishedAt'], reverse=True)

    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\n"

    prompt = f"""
You are an AI newsletter writer focused on education and breaking news. Your task is to create a professional, visually appealing newsletter targeted at an audience interested in the education landscape, from Pre-K to workforce skills, integrating structured news.

Use the following format:

Header:
- standard text with today's date and interesting and relevant news call out 
- 100-140 characters summarizing the first three headlines in sentence form to increase open rates
  Example: Antwalk raises $7.5 Million, upGrad reveals big hiring plans, HolonIQ says EdTech boosted in Q1 and stalled in Q2, and more.


Sections:
1. Breaking News Section (1-2 articles)
2. Top Stories Section (3 articles)
3. More Stories Section (Categorized into AI, Pre-K–12, Workforce Learning & Skills, Higher Ed & HireEd; 1-5 articles per category - more is better, but only relevant news.)

Categorize the articles yourself. Deduplicate and prioritize significant news. Do not include one article twice. Only use articles that are provided, do not include anything else.

Articles to work with:
{articles_text}

Produce the final newsletter now.
"""
    return prompt


def generate_newsletter(companies):
    all_articles = []
    for company_name in companies:
        search_term = f'"{company_name}" education'
        bing_articles = get_bing_news(search_term)
        all_articles.extend(bing_articles)

    if not all_articles:
        print("No articles found.")
    else:
        chunk_size = 30
        reduced_all = []
        if len(all_articles) > chunk_size:
            for chunk in chunk_list(all_articles, chunk_size):
                reduced_chunk = reduce_articles_batch(chunk)
                reduced_all.extend(reduced_chunk)
        else:
            reduced_all = all_articles

        # Now create final newsletter prompt
        final_prompt = create_final_newsletter_prompt(reduced_all)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": final_prompt}],
            temperature=0.7
        )

        newsletter = response.choices[0].message.content
        return reduced_all, newsletter
