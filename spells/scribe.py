import click
import os
import pathspec
import pyperclip
from datetime import datetime
from magi_cli.spells import SANCTUM_PATH

__requires__ = ['click', 'pyperclip', 'pathspec']

def is_readable(file_path):
    """Check if a file is readable as text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.read(1024)  # Read only the first 1024 bytes for efficiency
            return True
    except (UnicodeDecodeError, IOError):
        return False

def read_directory(path, prefix="", ignore_git=True, _gitignore_specs=None):
    """Recursively read the contents of a directory."""
    contents = ""
    
    # Initialize or update gitignore specs
    if _gitignore_specs is None:
        _gitignore_specs = []
    
    # Load gitignore patterns if needed
    if ignore_git:
        gitignore_path = os.path.join(path, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = [p.strip() for p in f.readlines() if p.strip() and not p.startswith('#')]
                # Create a new spec for this directory level
                current_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
                _gitignore_specs.append((path, current_spec))
                if patterns:  # Only show message if there are actual patterns
                    click.secho(f"Using .gitignore patterns from {gitignore_path}", fg='blue', dim=True)
    
    for item in os.listdir(path):
        # Skip .git directory if ignore_git is True
        if ignore_git and item == '.git':
            continue
            
        full_path = os.path.join(path, item)
        
        # Check against all gitignore specs, from most specific to most general
        should_ignore = False
        if ignore_git and _gitignore_specs:
            for spec_path, spec in reversed(_gitignore_specs):
                # Get the relative path from the gitignore file's location
                rel_to_spec = os.path.relpath(full_path, spec_path)
                # Normalize path separators for consistent matching
                rel_to_spec = rel_to_spec.replace(os.sep, '/')
                # For directories, ensure path ends with / for proper matching
                if os.path.isdir(full_path):
                    rel_to_spec += "/"
                if spec.match_file(rel_to_spec):
                    should_ignore = True
                    break
        
        if should_ignore:
            continue
        
        if os.path.isdir(full_path):
            dir_line = f"{prefix}/{item}/\n"
            contents += f"## {dir_line}\n"
            # Pass down the accumulated gitignore specs to subdirectories
            contents += read_directory(full_path, prefix=f"{prefix}/{item}", 
                                    ignore_git=ignore_git, 
                                    _gitignore_specs=_gitignore_specs[:])
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
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def scribe(args, include_git, verbose):
    """'scb' - Transcribe the contents of a file or directory into markdown. You may store the transcript in ~.sanctum/.aether."""
    if not args:
        click.secho("No path provided. The spell fizzles...", fg='red')
        return

    path = args[0]

    if not os.path.exists(path):
        click.secho(f"The path '{path}' does not exist. The spell fizzles...", fg='red')
        return

    click.secho(" Transcribing your chosen realm...", fg='blue')

    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            content = f"# {os.path.basename(path)}\n\n```\n{file.read()}\n```"
    elif os.path.isdir(path):
        content = f"# Directory: {os.path.basename(path)}\n\n{read_directory(path, ignore_git=not include_git)}"
    else:
        click.secho("The chosen path is neither a file nor a directory. The spell fizzles...", fg='red')
        return

    # Handle saving options
    save_to_aether = click.confirm(" Send transcription to the aether?", default=False)
    save_to_local = False
    
    if not save_to_aether:
        save_to_local = click.confirm(" Save to local directory?", default=False)
    
    # Save file if requested
    if save_to_aether or save_to_local:
        output_dir = os.path.join(SANCTUM_PATH, '.aether') if save_to_aether else os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the actual directory name instead of using the raw path argument
        if path == '.':
            base_name = os.path.basename(os.path.abspath(os.getcwd()))
        else:
            base_name = os.path.basename(os.path.abspath(path))
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"transcription_{base_name}_{timestamp}.md"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        if save_to_aether:
            click.secho(f" The transcription has been sent to the aether.", fg='green')
        else:
            click.secho(f" The transcription has been saved to {output_path}", fg='green')
    
    # Offer to copy to clipboard
    if click.confirm(" Copy transcription to clipboard?", default=False):
        pyperclip.copy(content)
        click.secho(" Transcription copied to clipboard!", fg='green')

    # Ask about clipboard regardless of save choice
    if not (save_to_aether or save_to_local):
        click.secho("No transcription was saved to file.")

alias = "scb"

def main():
    scribe()

if __name__ == '__main__':
    main()