import click
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from magi_cli.spells import SANCTUM_PATH
from openai import OpenAI
from colorama import init, Fore, Style
from rich.console import Console
from rich.markdown import Markdown

init()  # Initialize colorama
console = Console()  # Initialize rich console

__requires__ = ['click', 'openai', 'colorama', 'rich']

def is_readable(file_path):
    """Check if a file is readable as text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.read(1024)  # Read only the first 1024 bytes for efficiency
            return True
    except (UnicodeDecodeError, IOError):
        return False

def read_directory(path, prefix="", md_file_name="directory_contents"):
    """Recursively read the contents of a directory and write them to a Markdown file in the .aether directory."""
    aether_dir = os.path.join(SANCTUM_PATH, '.aether')
    if not os.path.exists(aether_dir):
        os.makedirs(aether_dir)

    # Generate a timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_file_name_with_timestamp = f"{md_file_name}_{timestamp}.md"
    markdown_file_path = os.path.join(aether_dir, md_file_name_with_timestamp)

    contents = ""
    with open(markdown_file_path, 'a', encoding='utf-8', errors='replace') as md_file:
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                dir_line = f"{prefix}/{Fore.BLUE}{item}/{Style.RESET_ALL}\n"
                contents += dir_line
                md_file.write(f"## {dir_line}\n")
                contents += read_directory(full_path, prefix=prefix + "/" + item, md_file_name=md_file_name)
            else:
                file_line = f"{prefix}/{Fore.GREEN}{item}{Style.RESET_ALL}: "
                if is_readable(full_path):
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as file:
                        file_content = file.read()
                    file_line += f"\n```\n{file_content}\n```\n"
                else:
                    file_line += f"{Fore.YELLOW}[non-readable or binary content]{Style.RESET_ALL}\n"
                contents += file_line
                md_file.write(file_line)
    return contents

def get_enhanced_prompt():
    """Return enhanced system prompt with YAML spell creation knowledge."""
    return '''You are a technowizard trained in the arcane, specializing in spell creation through YAML configurations. 
You have deep knowledge of software development and computer science. You generate python scripts, bash scripts and spells in YAML. When creating spells, follow these guidelines:

1. Choose names for spells that reflect their purpose, for example:
   - echo (for a script that prints text)
   - mystic_portal (for a file transfer tool)
   - sacred_sentinel (for a monitoring script)
   - loci_logger (for a logging utility)
   - crystal_cipher (for an encryption tool)
   Always use underscores between words and keep names lowercase.

2. Generate complete YAML configurations following this structure:
   - name: Spell identifier (magical and evocative, lowercase with underscores)
   - description: Clear purpose description with a magical flavor
   - type: Usually 'bundled' or 'script'
   - shell_type: 'python' or 'bash'
   - requires: List of Python package dependencies
   - code: The main spell implementation (must include proper Click CLI setup)
   - artifacts: Any additional files needed

3. After providing the YAML configuration, always include this note, and format it with the generated spell name:
   "To create this spell, save the YAML to a file (e.g., <spell_name>.yaml) by entering `scribe` in the chat and then run:
   `cast sc <spell_name>.yaml` to create the spell in your .tome directory. You may then cast it at any time using `cast <spell_name>`."

Here is an example spell configuration:

```yaml
name: arcane_art
description: A spell to transmute plain text into mesmerizing ASCII art, using a selection of mystical fonts.
type: script
shell_type: python
requires:
  - art>=6.0
code: |
  #!/usr/bin/env python3
  from art import text2art
  import random
  import sys

  FONTS = ['block', 'banner', 'standard', 'avatar', 'basic', 'bigchief', 'cosmic', 'digital', 
          'dotmatrix', 'drpepper', 'epic', 'isometric1', 'letters', 'alligator', 'crazy', 'doom']

  def main():
      # Get text from args or use default
      text = sys.argv[1] if len(sys.argv) > 1 else "Magic!"
      
      # Try with a random font first
      font = random.choice(FONTS)
      try:
          art = text2art(text, font=font)
          print(f"\nUsing font: {font}\n")
          print(art)
      except Exception as e:
          print(f"Error with font {font}: {e}")
          print("\nTrying with standard font instead...")
          print(text2art(text))

  if __name__ == '__main__':
      main()
```

When generating python or bash scripts, use the following structure:

```bash
#!/usr/bin/env bash
# <description>
<content of script>
```

```python
# <description>
<content of script>
```

When providing a script, always include this note:
"To create this script, save the file to a text file (e.g., <script_name>.py or <script_name>.sh) by entering `scribe` in the chat. This will prompt you to save the file and you will select the file type.
It will then prompt for a name, and it will save the script in your current directory. You may then execute it."

Your responses for general queries should be informative and helpful, using your arcane knowledge
to assist with software development, system administration, and other technical tasks.'''

def send_message(message_log):
    """Send a message to the OpenAI API and return the response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OpenAI API key is not set. Unable to consult the aether for wisdom."
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=message_log,
            max_tokens=4096,
            temperature=0.7,
        )
        return response.choices[0].message.content if response.choices else "No response received from the aether."
    except Exception as e:
        return f"Error consulting the aether: {str(e)}"

@click.command()
@click.argument('args', nargs=-1)
def aether_inquiry(args):
    """'ai' - Call upon an aether intelligence (OpenAI) to answer questions, generate spells, or converse about files and folders."""
    
    # Initialize message log with enhanced system prompt
    message_log = [
        {"role": "system", "content": get_enhanced_prompt()}
    ]

    # Check for previous conversations
    aether_dir = os.path.join(SANCTUM_PATH, '.aether')
    os.makedirs(aether_dir, exist_ok=True)
    
    previous_inquiries = [f for f in os.listdir(aether_dir) 
                         if f.startswith('Inquiry-') and f.endswith('.md')]

    if previous_inquiries:
        if click.confirm(f"{Fore.CYAN}Would you like to continue a previous conversation?{Style.RESET_ALL}"):
            print(f"\n{Fore.CYAN}Select a previous conversation:{Style.RESET_ALL}")
            for idx, filename in enumerate(previous_inquiries, 1):
                print(f"{Fore.GREEN}{idx}. {filename}{Style.RESET_ALL}")
            
            selected = click.prompt(f"{Fore.CYAN}Enter conversation number (or press Enter to skip){Style.RESET_ALL}", 
                                  type=click.INT, default=0, show_default=False)
            
            if 1 <= selected <= len(previous_inquiries):
                with open(os.path.join(aether_dir, previous_inquiries[selected-1]), 'r') as f:
                    message_log.append({"role": "user", "content": f.read()})
                print(f"\n{Fore.GREEN}Previous conversation loaded. You may continue your inquiry.{Style.RESET_ALL}")

    # Handle file and directory inputs
    if args:
        for file_path in args:
            if os.path.isdir(file_path):
                if click.confirm(f"{Fore.CYAN}Transcribe contents of '{file_path}' directory?{Style.RESET_ALL}"):
                    directory_contents = read_directory(file_path)
                    message_log.append({"role": "user", "content": directory_contents})
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        message_log.append({"role": "user", "content": file.read()})
                except UnicodeDecodeError:
                    print(f"{Fore.RED}Unable to read '{file_path}' - file appears to be binary.{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}Provided files/folders have been analyzed. You may now inquire about them.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.CYAN}You may begin your inquiry with the aether.{Style.RESET_ALL}")

    last_response = ""
    while True:
        user_input = click.prompt(f"{Fore.CYAN}You{Style.RESET_ALL}", type=str)

        if user_input.lower() == "quit":
            if click.confirm(f"{Fore.CYAN}Save this conversation?{Style.RESET_ALL}"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                inquiry_filename = f"Inquiry-{timestamp}.md"
                
                with open(os.path.join(aether_dir, inquiry_filename), 'w') as f:
                    f.write(f"# Aether Inquiry Conversation - {timestamp}\n\n")
                    for message in message_log:
                        sender = 'User' if message['role'] == 'user' else 'mAGI'
                        f.write(f"{sender}: {message['content']}\n\n")
                print(f"{Fore.GREEN}Conversation saved as {inquiry_filename}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}May your future inquiries be fruitful. Farewell.{Style.RESET_ALL}")
            break

        elif user_input.lower() == "scribe":
            save_format = click.prompt(
                f"{Fore.CYAN}Save as{Style.RESET_ALL}",
                type=click.Choice(['yaml', 'python', 'bash', 'markdown', 'copy'], case_sensitive=False)
            )

            if save_format == "yaml":
                # Extract YAML content from code blocks
                yaml_blocks = re.findall(r'```yaml(.*?)```', last_response, re.DOTALL)
                if not yaml_blocks:
                    print(f"{Fore.YELLOW}No YAML configuration found in the response.{Style.RESET_ALL}")
                    continue
                    
                yaml_content = yaml_blocks[0].strip()
                yaml_file_name = click.prompt(f"{Fore.CYAN}Enter name for YAML file (without extension){Style.RESET_ALL}")
                
                with open(f"{yaml_file_name}.yaml", 'w') as f:
                    f.write(yaml_content)
                print(f"{Fore.GREEN}YAML configuration saved as {yaml_file_name}.yaml{Style.RESET_ALL}")
                print(f"\n{Fore.GREEN}To create the spell, run:{Style.RESET_ALL}")
                print(f"{Fore.GREEN}cast sc {yaml_file_name}.yaml{Style.RESET_ALL}")

            elif save_format == "python":
                # Extract Python code blocks
                code_blocks = re.findall(r'```python(.*?)```', last_response, re.DOTALL)
                if not code_blocks:
                    # Try alternative code block format
                    code_blocks = re.findall(r'```py(.*?)```', last_response, re.DOTALL)
                
                if not code_blocks:
                    print(f"{Fore.YELLOW}No Python code found in the response.{Style.RESET_ALL}")
                    continue
                
                # Combine all Python code blocks
                code = '\n\n'.join(block.strip() for block in code_blocks)
                python_file_name = click.prompt(f"{Fore.CYAN}Enter name for Python script (without extension){Style.RESET_ALL}")
                
                with open(f"{python_file_name}.py", 'w') as f:
                    f.write(code)
                # Make executable
                Path(f"{python_file_name}.py").chmod(0o755)
                print(f"{Fore.GREEN}Python script saved as {python_file_name}.py{Style.RESET_ALL}")

            elif save_format == "bash":
                # Extract bash code blocks
                code_blocks = re.findall(r'```bash(.*?)```', last_response, re.DOTALL)
                if not code_blocks:
                    # Try alternative code block format
                    code_blocks = re.findall(r'```sh(.*?)```', last_response, re.DOTALL)
                
                if not code_blocks:
                    print(f"{Fore.YELLOW}No bash code found in the response.{Style.RESET_ALL}")
                    continue
                
                # Combine all bash code blocks
                code = '\n\n'.join(block.strip() for block in code_blocks)
                bash_file_name = click.prompt(f"{Fore.CYAN}Enter name for bash script (without extension){Style.RESET_ALL}")
                
                with open(f"{bash_file_name}.sh", 'w') as f:
                    f.write('#!/bin/bash\n\n' + code)
                # Make executable
                Path(f"{bash_file_name}.sh").chmod(0o755)
                print(f"{Fore.GREEN}Bash script saved as {bash_file_name}.sh{Style.RESET_ALL}")

            elif save_format == "markdown":
                md_file_name = click.prompt(f"{Fore.CYAN}Enter name for Markdown file (without extension){Style.RESET_ALL}")
                with open(f"{md_file_name}.md", 'w') as md_file:
                    # Add some styling hints for the markdown
                    styled_response = f"# {md_file_name.title()}\n\n{last_response}"
                    md_file.write(styled_response)
                print(f"{Fore.GREEN}Markdown saved as {md_file_name}.md{Style.RESET_ALL}")
                
                # Preview the markdown
                print(f"\n{Fore.CYAN}Preview of the markdown:{Style.RESET_ALL}")
                md = Markdown(styled_response)
                console.print(md)

            elif save_format == "copy":
                file_name = click.prompt(f"{Fore.CYAN}Enter name for text file (without extension){Style.RESET_ALL}")
                with open(f"{file_name}.txt", 'w') as f:
                    f.write(last_response)
                print(f"{Fore.GREEN}Response saved as {file_name}.txt{Style.RESET_ALL}")

        else:
            message_log.append({"role": "user", "content": user_input})
            print(f"\n{Fore.CYAN}Consulting the aether...{Style.RESET_ALL}")
            response = send_message(message_log)
            message_log.append({"role": "assistant", "content": response})
            print(f"\n{Fore.MAGENTA}mAGI:{Style.RESET_ALL}")
            # Render the response as rich markdown
            md = Markdown(response)
            console.print(md)
            last_response = response

alias = "ai"

def main():
    aether_inquiry()

if __name__ == '__main__':
    main()