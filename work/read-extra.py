import json,re
exec(open('work/render.py').read().split("pages=json.load")[0])
ps=[]
for p in json.load(open('work/extra-pages.json')):
 n=p['nodes'][0];s=n['body'];root=s[s.rindex('return mdx(')+7:s.rfind('\n}')].rstrip(';\n ')
 ps.append(dict(url=p['url'],title=n['frontmatter']['title'],text=re.sub(r'\n{3,}','\n\n',render(root)).strip()))
json.dump(ps,open('work/extra-text.json','w'),ensure_ascii=False,indent=2)
for i,p in enumerate(ps):print(i,p['url'],len(p['text']))
