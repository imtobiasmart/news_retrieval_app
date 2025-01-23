import json
from pydantic import BaseModel

import streamlit as st
from dateutil.parser import isoparse
from duckduckgo_search import DDGS
from openai import OpenAI

from constants import education_terms, companies, finance_keywords

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
)


class Article(BaseModel):
    title: str
    url: str
    description: str
    publishedAt: str
    source: str


class NewsArticles(BaseModel):
    articles: list[Article]


def article_is_education_related(title, description):
    text = f"{title} {description}".lower()
    return any(term in text for term in education_terms)

def article_is_related_to_financing(title, description):
    text = f"{title} {description}".lower()
    return any(keyword in text for keyword in finance_keywords)


def get_ddg_news(query, education_only):
    """
    Fetches news articles for the given query using DuckDuckGo's 'DDGS().news',
    then filters the articles to only include those that match your
    'article_is_education_related' criteria.
    """

    filtered_articles = []
    with DDGS() as ddgs:
        results = ddgs.news(
            keywords=query,
            region="us-en",  # Specify your region
            timelimit="d",  # 'd' = last 24 hours
            max_results=100  # Max number of results to fetch
        )

        for r in results:
            title = r.get("title", "")
            description = r.get("body", "")
            url = r.get("url", "")
            source = r.get("source", "")
            pub_date_str = r.get("date", "")

            try:
                pub_date = isoparse(pub_date_str)
            except (ValueError, TypeError):
                pub_date = None

            if not education_only or article_is_education_related(title, description) or article_is_related_to_financing(title, description):
                filtered_articles.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "publishedAt": pub_date.isoformat() if pub_date else "",
                    "source": source
                })

    return filtered_articles


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def reduce_articles_batch(articles):
    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\nSource: {art['source']}\n"
    prompt = f"""
        Role: You are an AI assistant that filters and prioritizes news articles for a newsletter.
        Task:
        You are given a list of articles.
        Select at 8-12 articles that meet all of the following criteria:
        - Are important or broadly newsworthy, reflecting U.S. or global trends (avoid highly localized or niche events).
        - Exclude articles containing extremely negative or sensitive content (e.g., school shootings).
        - Exclude duplicate articles, if there is more than one article with the same title, select the one with more credible source.
        - Remove any articles which source is related to country other than the United States.
        - Prioritize articles from the most reliable sources.
        
        Output the chosen articles only in a JSON-like list of objects with the keys:
        "title"
        "url"
        "description"
        "publishedAt"
        "source"
        
        Do not include anything else in your final output—no explanations, no extra text.
        
        Articles:
        {articles_text}
        
        Output format:
        [{{"title":"...", "url":"...", "description":"...", "publishedAt":"...", "source":"..."}}, ...]
    """
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format=NewsArticles
    )
    content = response.choices[0].message.content
    reduced_articles = json.loads(content)["articles"]
    return reduced_articles


def reduce_finance_articles_batch(articles):
    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\nSource: {art['source']}\n"

    prompt = f"""
        Role: You are an AI assistant that filters and prioritizes finance-related news articles for a venture capital firm’s newsletter.
        Task:
        You are given a list of articles.
        Select at 8-10 articles that meet all of the following criteria:
        - Primarily cover financial news.
        - Are important or broadly newsworthy, reflecting U.S. or global trends (avoid highly localized or niche events).
        - Exclude articles containing extremely negative or sensitive content (e.g., school shootings).
        - Exclude duplicate articles, if there is more than one article with the same title, select the one with more credible source.
        - Prioritize articles from the most reliable sources.
        - Remove any articles which source is related to country other than the United States.
        
        Output the chosen articles only in a JSON-like list of objects with the keys:
        "title"
        "url"
        "description"
        "publishedAt"
        "source"
        
        Do not include anything else in your final output—no explanations, no extra text.
        
        Articles:
        {articles_text}
        
        Output format:
        [{{"title":"...", "url":"...", "description":"...", "publishedAt":"...", "source":"..."}}, ...]
    """
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format=NewsArticles
    )
    content = response.choices[0].message.content
    reduced_articles = json.loads(content)["articles"]
    return reduced_articles


def reduce_education_articles_batch(articles):
    articles_text = ""
    for i, art in enumerate(articles, start=1):
        articles_text += f"\nArticle {i}:\nTitle: {art['title']}\nSummary: {art['description']}\nURL: {art['url']}\nPublishedAt: {art['publishedAt']}\nSource: {art['source']}\n"

    prompt = f"""
        Role: You are an AI assistant that filters and prioritizes education-related news articles for an education-focused venture capital firm’s newsletter.
        Task:
        You are given a list of articles.
        Select at 8-12 articles that meet all of the following criteria:
        - Primarily cover education news.
        - If there are news regarding companies financing like valuations, rounds of financing, etc., they must be included in the selection.
        - Are important or broadly newsworthy, reflecting U.S. or global trends (avoid highly localized or niche events).
        - Exclude articles containing extremely negative or sensitive content (e.g., school shootings).
        - Exclude articles that do not indicate a significant development or trend in education.
        - Exclude duplicate articles, if there is more than one article with the same title, select the one with more credible source.
        - If there are news from the best sources (Education Week, EdTech, eSchool News, EdSurge, Chalkbeat, 
        The Associated Press, Inside Higher Ed, EdSource, The Hechinger Report, Forbes, Brookings, Edutopia, 
        The Chronicle of Higher Education, The 74, Working Nation, KQED, TechCrunch, World Economic Forum), they must 
        be included in the selection.
        - Remove any articles which source is related to country other than the United States.
        
        Output the chosen articles only in a JSON-like list of objects with the keys:
        "title"
        "url"
        "description"
        "publishedAt"
        "source"
        
        Do not include anything else in your final output—no explanations, no extra text.
        
        Articles:
        {articles_text}
        
        Output format:
        [{{"title":"...", "url":"...", "description":"...", "publishedAt":"...", "source":"..."}}, ...]
    """
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[{"role": "user", "content": prompt}],
        response_format=NewsArticles
    )
    content = response.choices[0].message.content
    reduced_articles = json.loads(content)["articles"]
    return reduced_articles


def get_all_articles(keywords_list, news_topic="Education"):
    all_results = []
    education_only = news_topic == "Education"
    news_topic = "" if news_topic == "General" else news_topic

    for keyword in keywords_list:
        query = f'{news_topic} +\"{keyword}\"'
        results = get_ddg_news(query, education_only)
        all_results.extend(results)

    # Remove duplicates based on the title
    unique_articles = []
    seen_titles = set()

    for article in all_results:
        if article["title"] not in seen_titles:
            unique_articles.append(article)
            seen_titles.add(article["title"])

    chunk_size = 20
    reduced_all = []
    if news_topic == "Education":
        func = reduce_education_articles_batch
    elif news_topic == "Finance":
        func = reduce_finance_articles_batch
    else:
        func = reduce_articles_batch
    if len(unique_articles) > chunk_size:
        for chunk in chunk_list(unique_articles, chunk_size):
            reduced_chunk = func(chunk)
            reduced_all.extend(reduced_chunk)
    else:
        reduced_all = func(unique_articles)

    return reduced_all


def create_final_newsletter_prompt(articles, news_topic):
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
            f"Source: {art['source']}\n"
        )

    if news_topic == "Education":
        prompt = education_newsletter_prompt(articles_text)
    elif news_topic == "Finance":
        prompt = finance_newsletter_prompt(articles_text)
    else:
        prompt = newsletter_prompt(articles_text)

    return prompt


def generate_newsletter(all_articles, news_topic):
    final_prompt = create_final_newsletter_prompt(all_articles, news_topic)

    # 3. Send the prompt to GPT to create the newsletter
    response = client.chat.completions.create(
        model="o1-preview",
        messages=[
            {"role": "user", "content": final_prompt}
        ]
    )

    newsletter = response.choices[0].message.content
    return newsletter


def education_newsletter_prompt(articles_text):
    return f"""
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

def finance_newsletter_prompt(articles_text):
    return f"""
        Role: You are an AI newsletter writer for a venture fund, primarily covering U.S. news (with limited global highlights if relevant).
        
        Instructions:
        
        Input:
        A list of priority companies whose news should be highlighted first.
        A batch of articles.
        
        Focus:
        Include only non-sensitive content (exclude events like school shootings or other highly negative items).
        Articles should primarily center on U.S. education (global news is acceptable but should not overshadow U.S. coverage).
        Deduplicate articles and prioritize those involving the priority companies or that show significant trends in finance.
        
        Output Format: A visually appealing, professional newsletter with the following structure:
        Header
        Subject Line: Standard text with today’s date plus a relevant news teaser (e.g., “Antwalk raises $7.5M,” etc.).
        Preview Text (100–140 characters): Summarize the first three headlines in sentence form to encourage opens.
        Breaking News Section (1–2 articles, optional if no urgent developments)
        Top Stories Section (exactly 3 articles)
        More Stories Section, further divided into subcategories (1–5 articles each, 2–3 is ideal). 2-3 subcategories would be sufficient.
        
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

def newsletter_prompt(articles_text):
    return f"""
        Role: You are an AI newsletter writer, primarily covering U.S. news (with limited global highlights if relevant).
        
        Instructions:
        
        Input:
        A list of priority companies whose news should be highlighted first.
        A batch of articles.
        
        Focus:
        Include only non-sensitive content (exclude events like school shootings or other highly negative items).
        Articles should primarily center on U.S. (global news is acceptable but should not overshadow U.S. coverage).
        Deduplicate articles and prioritize those involving the priority companies.
        
        Output Format: A visually appealing, professional newsletter with the following structure:
        Header
        Subject Line: Standard text with today’s date plus a relevant news teaser (e.g., “Antwalk raises $7.5M,” etc.).
        Preview Text (100–140 characters): Summarize the first three headlines in sentence form to encourage opens.
        Breaking News Section (1–2 articles, optional if no urgent developments)
        Top Stories Section (exactly 3 articles)
        More Stories Section, further divided into subcategories (1–5 articles each, 2–3 is ideal). 2-3 subcategories would be sufficient.
        
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