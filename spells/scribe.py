import click
import os
import pyperclip
from datetime import datetime
from magi_cli.spells import SANCTUM_PATH

__requires__ = ['click', 'pyperclip']

def is_readable(file_path):
    """Check if a file is readable as text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.read(1024)  # Read only the first 1024 bytes for efficiency
            return True
    except (UnicodeDecodeError, IOError):
        return False

def read_directory(path, prefix="", ignore_git=True):
    """Recursively read the contents of a directory."""
    contents = ""
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if ignore_git and item == '.git':
            continue
        if os.path.isdir(full_path):
            dir_line = f"{prefix}/{item}/\n"
            contents += f"## {dir_line}\n"
            contents += read_directory(full_path, prefix=f"{prefix}/{item}", ignore_git=ignore_git)
        else:
            file_line = f"{prefix}/{item}: "
            if is_readable(full_path):
                with open(full_path, 'r', encoding='utf-8', errors='replace') as file:
                    file_content = file.read()
                file_line += f"\n```\n{file_content}\n```\n"
            else:
                file_line += "[non-readable or binary content]\n"
            contents += file_line
    return contents

@click.command()
@click.argument('args', nargs=-1)
@click.option('--include-git', is_flag=True, help='Include .git directory in transcription')
def scribe(args, include_git):
    """'scb' - Transcribe the contents of a file or directory into markdown. You may store the transcript in ~.sanctum/.aether."""
    click.echo("Channeling the arcane energies to transcribe your chosen realm...")

    if not args:
        click.echo("No path provided. The spell fizzles...")
        return

    path = args[0]

    if not os.path.exists(path):
        click.echo(f"The path '{path}' does not exist. The spell fizzles...")
        return

    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            content = f"# {os.path.basename(path)}\n\n```\n{file.read()}\n```"
    elif os.path.isdir(path):
        content = f"# Directory: {os.path.basename(path)}\n\n{read_directory(path, ignore_git=not include_git)}"
    else:
        click.echo("The chosen path is neither a file nor a directory. The spell fizzles...")
        return

    # Handle saving options
    save_to_aether = click.confirm("Do you wish to send this transcription to the aether?", default=False)
    save_to_local = False
    
    if not save_to_aether:
        save_to_local = click.confirm("Would you like to save it to your local directory?", default=False)
    
    # Save file if requested
    if save_to_aether or save_to_local:
        output_dir = os.path.join(SANCTUM_PATH, '.aether') if save_to_aether else os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{os.path.basename(path)}_transcription_{timestamp}.md"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        location = "the aether" if save_to_aether else "your local directory"
        click.echo(f"The transcription has been etched into {output_path} in {location}.")

    # Ask about clipboard regardless of save choice
    if click.confirm("Would you like to copy the transcription to your clipboard?", default=False):
        pyperclip.copy(content)
        click.echo("The transcription has been copied to your clipboard!")

    if not (save_to_aether or save_to_local):
        click.echo("No transcription was saved to file.")

alias = "scb"

def main():
    scribe()

if __name__ == '__main__':
    main()