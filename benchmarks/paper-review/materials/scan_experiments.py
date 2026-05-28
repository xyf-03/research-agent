import re

with open(r'E:\autoreserach\tmp\research-agent\workspace-paper-review\benchmark\materials\fedaux_text.txt', 'r', encoding='utf-8') as f:
    content = f.read()

keywords = ['Experiment', 'experiment', 'Table', 'Result', 'accuracy', 'dataset', 'baseline', 'ablation', 'hyperparameter', 'Datasets', 'Results']

for m in re.finditer(r'=== PAGE \d+ ===', content):
    page_num = m.group()
    start = m.start()
    end_match = re.search(r'=== PAGE \d+ ===', content[start+1:])
    end = start + 1 + end_match.start() if end_match else len(content)
    page_text = content[start:end]
    found_kw = [kw for kw in keywords if kw in page_text]
    if found_kw:
        print(f'{page_num}: {found_kw}')
