import os
import re

def find_bad_containers():
    pattern = re.compile(r'Container\s*\(.*?\)', re.DOTALL)
    bad_pattern = re.compile(r'color\s*=\s*')
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for match in pattern.finditer(content):
                            block = match.group(0)
                            if 'color=' in block:
                                # Check if color is an argument to Container, not a nested widget
                                # Simplistic check: if color= exists but not inside another widget call
                                print(f"Potential match in {path}:\n{block}\n")
                except:
                    pass

if __name__ == "__main__":
    find_bad_containers()
