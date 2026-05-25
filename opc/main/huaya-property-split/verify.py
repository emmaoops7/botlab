from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parent
ids=['home','login','payment','pay-now','my','property','repair','notice-detail']
class P(HTMLParser):
    def __init__(self): super().__init__(); self.ids=[]; self.scripts=[]; self.links=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if 'id' in d: self.ids.append(d['id'])
        if tag=='script' and 'src' in d: self.scripts.append(d['src'])
        if tag=='link' and 'href' in d: self.links.append(d['href'])
for rel in ['assets/common.css','assets/app.js','design/design.css','README.md']:
    assert (root/rel).exists(), rel
for folder in ['dev','design']:
    for pid in ids:
        f=root/folder/f'{pid}.html'; assert f.exists(), str(f)
        text=f.read_text(encoding='utf-8'); parser=P(); parser.feed(text)
        assert f'page-{pid}' in parser.ids, f'missing page id {folder}/{pid}'
        if folder=='dev': assert '../assets/app.js' in parser.scripts, f'missing app js {pid}'
        if folder=='design': assert '../assets/app.js' not in parser.scripts, f'design has app js {pid}'
assert (root/'design/index.html').exists()
print('OK: 8 dev pages, 8 design pages, shared assets, and static design index verified.')
