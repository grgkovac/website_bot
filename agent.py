import io
import httpx
from bs4 import BeautifulSoup
import pandas as pd
from typing import Literal

from pydantic_ai import Agent, DocumentUrl
# from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

agent = Agent(
    'google-gla:gemini-3-flash-preview',
    # 'openai-responses:gpt-5-mini',
    system_prompt=(
        "You are an assistant on a researchers website. "
        "Your task is to answer questions related to research done by Grgur Kovac (Flowers Team)."
    ),
    # tools=[duckduckgo_search_tool()]
)


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Get text and clean up whitespace
    text = soup.get_text(separator=' ')
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = '\n'.join(chunk for chunk in chunks if chunk)
    return clean_text


@agent.tool_plain
async def get_personal_website() -> str:
    """Fetches the content of Grgur Kovac's personal website."""
    return await fetch_website_content("https://grgkovac.github.io")


@agent.tool_plain
def get_cv_paper_pdf() -> DocumentUrl:
    return DocumentUrl(url='https://grgkovac.github.io/cv.pdf')


@agent.tool_plain
async def fetch_website_content(url: str) -> str:
    """
    Fetches the content of a website and cleans it.
    :param url: The URL of the website to fetch.
    :return: Cleaned text content of the website.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        try:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
        except Exception as e:
            return f"Error: {str(e)}"

        html = response.text
        if html.startswith("Error"):
            return html

        soup = BeautifulSoup(html, 'html.parser')
        clean_text = clean_soup(soup)
        return clean_text


@agent.tool_plain
async def get_google_scholar_profile() -> str:
    """
    Extracts publication data from a Google Scholar profile URL.
    """
    author_url = "https://scholar.google.com/citations?user=ZLA7iioAAAAJ&hl=en"
    return await fetch_website_content(author_url)


# papers
@agent.tool_plain
def get_GRIMGEP_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    GRIMGEP: Learning Progress for Robust Goal Sampling in Visual Deep Reinforcement Learning
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2008.04388')


@agent.tool_plain
def get_SocialAI_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    The SocialAI School: Insights from Developmental Psychology Towards Artificial Socio-Cultural Agents
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2307.07871')


@agent.tool_plain
def get_LLMs_as_superpositions_of_cultural_perspectives_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    Large Language Models as Superpositions of Cultural Perspectives
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2307.07870')


@agent.tool_plain
def get_stick_to_your_role_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    Stick to your Role! Stability of Personal Values Expressed in Large Language Models
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2402.14846')


@agent.tool_plain
async def get_stick_to_your_role_leaderboard_website_content(
        content: Literal["main_page", "motivation_and_methods_page"] = "main_page"
) -> str:
    """
    Fetches specific information from the 'Stick to your Role!' leaderboard space on Hugging Face.

    Args:
        content: The type of content to retrieve.
                 - 'main_page': The homepage showing current rankings and some basic information on the project.
                 - 'motivation_and_methods_page': Details on the motivation and methodology, in particular how the methodology differs from the paper.
    """
    # Use the .hf.space subdomain to access the Gradio/Streamlit app directly
    base_url = "https://flowers-team-sticktoyourroleleaderboard.hf.space"

    if content == "main_page":
        target_url = base_url
        return await fetch_website_content(target_url)
    elif content == "motivation_and_methods_page":
        target_url = f"{base_url}/about"
        return await fetch_website_content(target_url)

    else:
        return "Error: Invalid content type requested."


@agent.tool_plain
async def get_stick_to_your_role_leaderboard_data(
        sort_by: Literal[
            "Model", "Ordinal (Win rate)", "Cardinal (Score)", "RO Stability", "Stress", "CFI", "SRMR", "RMSEA"] = "Ordinal (Win rate)",
        columns_to_include: str = "all",
        top_n: int = 15
) -> str:
    """
    Retrieves and sorts the 'Stick to your Role!' leaderboard data as a Markdown table.

    Args:
        sort_by: Column to sort by. For Stress, SRMR, and RMSEA, lower is better (sorted ascending).
        columns_to_include: Comma-separated columns (e.g., 'Model, Stress, CFI') or 'all'.
        top_n: Number of rows to return.
    """

    async def fetch_csv_as_df(url: str) -> pd.DataFrame:
        """
        Fetches a CSV from a URL and returns a Pandas DataFrame.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            # Load the raw text into a buffer and then into Pandas
            return pd.read_csv(io.StringIO(response.text))

    url = "https://flowers-team-sticktoyourroleleaderboard.hf.space/static/leaderboard.csv"

    try:
        # 1. Fetch the data using our helper
        df = await fetch_csv_as_df(url)

        # 2. Logic for "Lower is Better" metrics
        # If the metric is an error or stress metric, sort ascending (0.1 is better than 0.9)
        is_ascending = sort_by in ["Stress", "SRMR", "RMSEA"]
        df = df.sort_values(by=sort_by, ascending=is_ascending)

        # 3. Handle Column Filtering
        if columns_to_include != "all":
            selected = [c.strip() for c in columns_to_include.split(",")]
            # Ensure 'Model' is always present for context
            if "Model" not in selected:
                selected.insert(0, "Model")

            # Filter only valid columns that exist in the CSV
            valid_cols = [c for c in selected if c in df.columns]
            df = df[valid_cols]

        # 4. Limit results and convert to Markdown
        table_str = df.head(top_n).to_markdown(index=False)
        return table_str

    except Exception as e:
        return f"Error processing leaderboard: {str(e)}"


@agent.tool_plain
def get_recursive_training_loops_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    Recursive Training Loops in LLMs: How training data properties modulate distribution shift in generated data?
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2504.03814')


@agent.tool_plain
def get_telephone_game_paper_pdf() -> DocumentUrl:
    """
    Fetches the pdf of the following paper
    When LLMs Play the Telephone Game: Cultural Attractors as Conceptual Tools to Evaluate LLMs in Multi-turn Settings
    :return:
    """
    return DocumentUrl(url='https://arxiv.org/pdf/2407.04503')
