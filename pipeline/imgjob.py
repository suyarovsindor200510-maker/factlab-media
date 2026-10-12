#!/usr/bin/env python3
"""usage: imgjob.py <ID> < urls.txt  -> jobs/<ID>-img.json (assets/<ID>/1.png ...)"""
import sys, json
ID = sys.argv[1]; urls = sys.stdin.read().split()
json.dump({'files': [{'url': u, 'path': f'assets/{ID}/{i+1}.png'} for i, u in enumerate(urls)]}, open(f'jobs/{ID}-img.json', 'w'))
print(len(urls), 'urls')
