import sys
import re
import subprocess

def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("Error: VERSION is required. Usage: make bump-version VERSION=x.y.z")
        sys.exit(1)

    version = sys.argv[1].strip()

    # Update pyproject.toml
    print(f"Updating pyproject.toml to version {version}...")
    with open('pyproject.toml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the top-level version
    content = re.sub(r'^version = ".*"', f'version = "{version}"', content, count=1, flags=re.MULTILINE)
    
    with open('pyproject.toml', 'w', encoding='utf-8', newline='') as f:
        f.write(content)

    # Update src/nlqe/__init__.py
    print(f"Updating src/nlqe/__init__.py to version {version}...")
    with open('src/nlqe/__init__.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = re.sub(r'^__version__ = ".*"', f'__version__ = "{version}"', content, count=1, flags=re.MULTILINE)
    
    with open('src/nlqe/__init__.py', 'w', encoding='utf-8', newline='') as f:
        f.write(content)

    # Git commands
    print("Committing changes and creating tag...")
    subprocess.run(['git', 'add', 'pyproject.toml', 'src/nlqe/__init__.py'], check=True)
    subprocess.run(['git', 'commit', '-m', f'chore: bump version to v{version}'], check=True)
    subprocess.run(['git', 'tag', '-a', f'v{version}', '-m', f'Release v{version}'], check=True)

    print(f"\nSuccess! Version bumped to {version} and tagged as v{version}.")
    print("Run 'git push origin main --tags' to publish.")

if __name__ == "__main__":
    main()
