import json,re,ast

def split(s):
 out=[];start=0;depth=0;i=0
 while i<len(s):
  c=s[i]
  if c in '\"\'':
   q=c;i+=1
   while i<len(s):
    if s[i]=='\\':i+=2;continue
    if s[i]==q:break
    i+=1
  elif c in '({[':depth+=1
  elif c in ')}]':depth-=1
  elif c==',' and depth==0:out.append(s[start:i].strip());start=i+1
  i+=1
 out.append(s[start:].strip());return out

def val(s):
 try:return ast.literal_eval(s)
 except:return s

def render(s):
 s=s.strip()
 if s.startswith(('"',"'")):
  v=val(s);return v if isinstance(v,str) else ''
 if not s.startswith('mdx('):return ''
 args=split(s[4:-1]);tag=val(args[0]);props=args[1] if len(args)>1 else '';children=''.join(render(x) for x in args[2:])
 if tag=='style':return ''
 if tag in ['h1','h2','h3','h4']:return '\n\n'+'#'*int(tag[1])+' '+children+'\n\n'
 if tag=='a':
  m=re.search(r'"?href"?:\s*("(?:\\.|[^"\\])*")',props)
  return '['+children+']('+val(m[1])+')' if m else children
 if tag=='li':return '\n- '+children
 if tag in ['p','ul','ol','table','blockquote']:return '\n'+children+'\n'
 if tag=='tr':return '\n'+children+'\n'
 if tag in ['td','th']:return children+' | '
 if tag=='pre':return '\n\n```\n'+children+'\n```\n\n'
 if tag=='strong':return '**'+children+'**'
 if tag=='inlineCode':return '`'+children+'`'
 if tag=='br':return '\n'
 if not args[0].startswith('"'):
  texts=[]
  pattern=r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
  for m in re.finditer(pattern,props):
   if props[m.end():].lstrip().startswith(':'):continue
   prefix=props[:m.start()]
   key=re.search(r'(\w+):\s*$',prefix)
   if key and key[1] in ['icon','mdxType','variant','className','id','href','src','image','imageUrl']:continue
   texts.append(val(m[0]))
  return '\n'+'\n'.join(texts)+'\n'+children
 return children
pages=json.load(open('work/pages.json'))
for name in ['glossary','changelog','terms-of-use']:
 n=json.load(open('work/'+name+'.json'));pages.append(dict(url='https://mcp-developer.ifood.com.br/pt-BR/docs/'+name,title=n['frontmatter']['title'],body=n['body']))
for p in pages:
 s=p['body'];start=s.rindex('return mdx(')+7 if 'return mdx(' in s else -1
 if start==-1:
  print('NO ROOT',p['url']);continue
 # root expression ends before function closure
 root=s[start:s.rfind('\n}')].rstrip(';\n ')
 p['text']=re.sub(r'\n{3,}','\n\n',render(root)).strip()
json.dump(pages,open('outputs/ifood-guias.json','w'),ensure_ascii=False,indent=2)
with open('outputs/ifood-guias.md','w') as f:
 f.write('# Documentação iFood MCP — extração dos guias\n\nData: 17/10/2026. Conteúdo obtido dos dados públicos das páginas do portal. Extração de texto e exemplos; imagens e diagramas não foram transcritos.\n\n')
 for p in pages:f.write(f"## {p['title']} — {p['url'].split('/guides')[-1] or 'Visão geral'}\n\nFonte: {p['url']}\n\n{p.get('text','')}\n\n---\n\n")
print([(p['url'].split('/guides')[-1],len(p.get('text',''))) for p in pages])
