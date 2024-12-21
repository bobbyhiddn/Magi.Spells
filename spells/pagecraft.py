import sys
import os
import re
import requests
from bs4 import BeautifulSoup
import click
from openai import OpenAI
from magi_cli.spells import SANCTUM_PATH
from colorama import init, Fore, Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

init()  # Initialize colorama
console = Console()  # Initialize rich console

__requires__ = ['click', 'beautifulsoup4', 'openai', 'requests', 'colorama', 'rich']

# Load the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print(f"{Fore.RED}Please set the OPENAI_API_KEY environment variable.{Style.RESET_ALL}")
    sys.exit(1)
else:
    client = OpenAI(api_key=api_key)

# Function to send a message to the OpenAI chatbot model and return its response
def send_message(message_log):
    if client:
        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=message_log,
            max_tokens=12000,
            temperature=0.7,
        )
        return response.choices[0].message.content if response.choices else "No response received."
    else:
        return "OpenAI API key is not set. Unable to send message."

# Fetch the content from the given URL
def fetch_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
        sys.exit(1)

# Parse the fetched HTML content
def parse_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string if soup.title else "Untitled"
    # Extract all text content from the HTML, including scripts and styles
    body = soup.get_text(separator='\n')
    return title, body

# Clean the content
def clean_content(content):
    # Preserve the content as much as possible
    content = content.replace('â', "'").replace('ðŽ‰', '🎉')
    # Retain multiple newlines to preserve formatting
    content = re.sub(r'\r\n|\r', '\n', content).strip()
    return content

# Create the first draft of the Markdown content
def to_markdown(title, body):
    message_log = [
        {"role": "system", "content": (
            "You are an AI assistant that converts HTML content into a Markdown document. "
            "Please format the following content into Markdown, preserving all content exactly as it appears. "
            "Maintain the original structure, tone, and any repeated phrases or sections. "
            "Do not exclude any content. Thank you."
        )},
        {"role": "user", "content": f"# {title}\n\n{body}"}
    ]
    first_draft = send_message(message_log)
    return first_draft  # Return the first draft instead of saving it here

# Function to improve the Markdown content based on the review
def improve_markdown(first_draft, review_feedback, title, body):
    message_log = [
        {"role": "system", "content": (
            "You are an AI assistant that improves Markdown documents based on review feedback. "
            "Please revise the following Markdown content according to the feedback provided."
            "Only provide the markdown content; do not include any review feedback in the response."
            "Be as comprehensive as possible in addressing the feedback as well as improving the overall quality of the content."
            "Do not wrap the content in a markdown code block, just provide the content as markdown."
        )},
        {"role": "user", "content": (
            f"Markdown Content:\n{first_draft}\n\n"
            f"Review Feedback:\n{review_feedback}"
            f"Original Content:\n{title}\n{body}"
        )}
    ]
    improved_content = send_message(message_log)
    return improved_content

# Review the Markdown content using AI and get feedback
def review_content(original_content, markdown_content):
    review_message_log = [
        {"role": "system", "content": (
            "You are an AI assistant trained to review a transcribed Markdown document against the original content. "
            "Please provide detailed feedback on how well the content was transcribed, noting any discrepancies or issues. "
            "Do not provide a rating; instead, focus on actionable feedback that can help improve the transcription."
        )},
        {"role": "user", "content": (
            f"Original Content:\n{original_content}\n\n"
            f"Markdown Content:\n{markdown_content}"
        )}
    ]
    review_feedback = send_message(review_message_log)
    return review_feedback

# Perform a final review and return it
def final_review(original_content, improved_content):
    final_review_message_log = [
        {"role": "system", "content": (
            "You are an AI assistant trained to perform a final review of the improved Markdown document against the original content. "
            "Please provide a detailed review of how well the content was transcribed and improved, noting any remaining discrepancies or issues. "
            "Rate the transcription quality on a scale from 1 to 10, where 10 means the content is perfectly transcribed, and 1 means it is poorly transcribed. "
            "Include the rating at the end of your review."
        )},
        {"role": "user", "content": (
            f"Original Content:\n{original_content}\n\n"
            f"Improved Markdown Content:\n{improved_content}"
        )}
    ]
    return send_message(final_review_message_log)

@click.command()
@click.argument('args', nargs=-1)  # Accept multiple arguments like other spells
def pagecraft(args):
    """ 'pgc' - Craft a Markdown page from a URL through the use of aether inquiry(AI). """

    if not args:
        print(f"{Fore.RED}Please provide a URL to craft a page from.{Style.RESET_ALL}")
        sys.exit(1)
    
    url = args[0]  # Take the first argument as the URL
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Stage 1: Fetch and parse content
        task = progress.add_task(f"{Fore.CYAN}Fetching content...{Style.RESET_ALL}", total=None)
        html = fetch_content(url)
        title, body = parse_content(html)
        body = clean_content(body)
        progress.update(task, completed=True)
        console.print(f"\n[cyan]Title:[/cyan] [green]{title}[/green]")
        
        # Stage 2: Generate the first draft
        task = progress.add_task(f"{Fore.CYAN}Generating the first draft...{Style.RESET_ALL}", total=None)
        first_draft = to_markdown(title, body)
        progress.update(task, completed=True)
        
        # Stage 3: Review the first draft
        task = progress.add_task(f"{Fore.CYAN}Reviewing the first draft...{Style.RESET_ALL}", total=None)
        review_feedback = review_content(body, first_draft)
        progress.update(task, completed=True)
        
        # Display review feedback
        console.print("\n[yellow]Review Feedback:[/yellow]")
        console.print(Panel(review_feedback, title="AI Review", border_style="yellow"))
        
        # Stage 4: Improve the Markdown content
        task = progress.add_task(f"{Fore.CYAN}Improving the Markdown content...{Style.RESET_ALL}", total=None)
        improved_content = improve_markdown(first_draft, review_feedback, title, body)
        progress.update(task, completed=True)
        
        # Stage 5: Generate filename
        task = progress.add_task(f"{Fore.CYAN}Generating a suitable filename...{Style.RESET_ALL}", total=None)
        filename_message_log = [
            {"role": "system", "content": "You are an AI trained to generate a suitable filename. Please generate a filename based on the following content."},
            {"role": "user", "content": improved_content}
        ]
        filename = send_message(filename_message_log)
        progress.update(task, completed=True)

    # Clean up filename
    filename = filename.replace(' ', '_').replace('/', '_').replace(':', '_').replace('"', '').replace('.txt', '').replace('`', '')
    if not filename.endswith(".md"):
        filename += ".md"
    
    # Handle archive path
    archive_path = os.getenv('SCRAPE_ARCHIVE_PATH')
    if archive_path:
        console.print(f"\n[cyan]The environment variable SCRAPE_ARCHIVE_PATH is set to:[/cyan] [green]{archive_path}[/green]")
        save_in_archive = click.prompt(f"{Fore.CYAN}Do you want to save the file in the scrape archive path? (Y/n){Style.RESET_ALL}", default='Y')
        if save_in_archive.lower() in ['y', 'yes', '']:
            save_dir = archive_path
        else:
            save_dir = os.getcwd()
    else:
        console.print("\n[yellow]You can set the SCRAPE_ARCHIVE_PATH environment variable if you want the document to be generated in a specific location.[/yellow]")
        save_dir = os.getcwd()

    # Ensure the directory exists
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    # Save the improved content
    full_path = os.path.join(save_dir, filename)
    with open(full_path, "w", encoding='utf-8') as f:
        f.write(improved_content)

    # Display final review
    console.print("\n[cyan]Final Review:[/cyan]")
    final_review_result = final_review(body, improved_content)
    console.print(Panel(final_review_result, title="Final AI Review", border_style="blue"))

    # Preview the markdown
    console.print("\n[cyan]Preview of the generated markdown:[/cyan]")
    md = Markdown(improved_content)
    console.print(Panel(md, title=filename, border_style="green"))

    console.print(f"\n[green]Content saved to:[/green] [blue]{full_path}[/blue]")

alias = "pgc"

def main():
    pagecraft()

# Entry point
if __name__ == "__main__":
    main()