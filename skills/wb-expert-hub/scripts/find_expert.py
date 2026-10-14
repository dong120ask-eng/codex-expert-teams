"""Search the local migrated expert catalog. No network or external actions."""
import argparse
import json
import pathlib
import sys

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--limit', type=int, default=12)
    parser.add_argument('--team', action='store_true')
    parser.add_argument('--category')
    args=parser.parse_args()
    root=pathlib.Path(__file__).resolve().parent.parent
    catalog=json.loads((root/'references/catalog.json').read_text(encoding='utf-8'))
    query=args.query.strip().casefold()
    result=[]
    for row in catalog:
        if args.team and row['type']!='team': continue
        if args.category and row['category']!=args.category: continue
        fields=[row['id'],row['name'],row['description'],row.get('plugin') or '',row['category']]
        matches=[i for i,text in enumerate(fields) if query in text.casefold()]
        if query and not matches: continue
        score=100 if query and query==row['id'].casefold() else 40 if query and query==row['name'].casefold() else 10-min(matches or [4])
        result.append((score,row))
    result.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    shown=[row for score,row in result[:max(1,min(args.limit,448))]]
    print(json.dumps({'query':args.query,'total':len(result),'results':shown},ensure_ascii=False,indent=2))
    return 0 if result else 1

if __name__=='__main__': raise SystemExit(main())
