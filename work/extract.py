import requests,json,concurrent.futures,pathlib,re,ast
base='https://mcp-developer.ifood.com.br'
nodes=json.load(open('work/371262153.json'))['data']['allMdx']['nodes']
paths=[n['fields']['pageId'].replace('/content/pages','/pt-BR') for n in nodes if n['fields']['filename']=='pt-BR' and '/docs/guides' in n['fields']['pageId']]
def fetch(p):
 j=requests.get(base+'/page-data'+p+'/page-data.json',timeout=45).json()
 ns=j['result']['data']['allMdx']['nodes']; n=next(n for n in ns if n['fields']['filename']=='pt-BR')
 return dict(url=base+p,title=n['frontmatter']['title'],body=n['body'])
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: pages=list(ex.map(fetch,paths))
json.dump(pages,open('work/pages.json','w'),ensure_ascii=False,indent=2)
print('Páginas recuperadas:',len(pages))
