from datetime import date
from io import StringIO
from pathlib import Path

import yaml
import pandas as pd
from mkdocs.structure.files import File



ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'bibliography.yml'
MD_TARGET_URI = 'bibliography.md'
BIB_TARGET_URI = 'bibliography.bib'


BOOKLET_FIELDS = {'author', 'title'}
BOOK_FIELDS1 = {'author', 'title', 'date', 'edition', 'publisher', 'isbn', 'doi', 'url'}
BOOK_FIELDS2 = {'editor', 'title', 'date', 'edition', 'publisher', 'isbn', 'doi', 'url'}

PRIO_COLUMNS = ('type', 'key', 'author', 'editor', 'title', 'subtitle', 'date', 'edition', 'publisher', 'isbn', 'doi', 'note', 'url')



def to_bibtex(entry):
    field_lines = []
    for k, v in entry.items():
        if k not in {'type', 'id'}:
            if isinstance(v, list):
                field_lines.append(f'{k} = {{{" and ".join(v)}}}')
            else:
                field_lines.append(f'{k} = {{{v}}}')
    return f'@{entry["type"]}{{{entry["key"]},\n  ' \
        + ',\n  '.join(field_lines) \
        + '\n}'


def on_files(files, config, **kwargs):
    with open(SOURCE, 'r', encoding='utf-8') as ifile:
        #read
        data = yaml.safe_load(ifile)
        
        
        #validate
        #check structure
        if not isinstance(data, list):
            raise TypeError('Bibliography not a list')
        for entry in data:
            if not isinstance(entry, dict):
                raise TypeError(f'Bibliography entry not a dict: {entry}')
            #check keys
            if not ('type' in entry and 'key' in entry):
                raise ValueError(f'Entry without type or key: {entry}')
            match entry['type']:
                case 'booklet':
                    if not entry.keys() >= BOOKLET_FIELDS:
                        raise ValueError(f'Booklet with missing fields: {entry['key']}')
                case 'book':
                    if not (entry.keys()>=BOOK_FIELDS1 or entry.keys()>=BOOK_FIELDS2):
                        raise ValueError(f'Book with missing fields: {entry['key']}')
                case _:
                    raise ValueError(f'Unrecognised entry type: {entry['type']}')
            #check values
            for k, v in entry.items():
                match k:
                    case 'author' | 'editor':
                        if not (isinstance(v, str) or isinstance(v, list) and all(isinstance(a, str) for a in v)):
                            raise TypeError(f'Wrong author/editor format: {entry['key']}')
                    case _:
                        if not isinstance(v, (str, int, date)):
                            raise TypeError(f'Wrong format: {entry['key']}')
        
        
        #tabulate
        df = pd.DataFrame.from_dict(data)
        
        
        #format
        #sort columns
        columns = [c for c in PRIO_COLUMNS if c in df.columns]
        columns += [c for c in df.columns if c not in PRIO_COLUMNS]
        df = df[columns]
        
        #edition from float to Int64 (allows NA)
        df = df.convert_dtypes()
        #keys anchors
        if 'key' in df.columns:
            df['key'] = df['key'].apply(
                lambda x: f'<a id={x}></a>{x}'
            )
        #authors/editors may be a list
        if 'author' in df.columns:
            df['author'] = df['author'].apply(
                lambda x: '<ul>'+''.join(f'<li>{e}</li>' for e in x)+'</ul>' if isinstance(x, list) else x
            )
        if 'editor' in df.columns:
            df['editor'] = df['editor'].apply(
                lambda x: '<ul>'+''.join(f'<li>{e}</li>' for e in x)+'</ul>' if isinstance(x, list) else x
            )
        #clickable dois
        if 'doi' in df.columns:
            df["doi"] = df['doi'].apply(
                lambda x: f'<a href="https://doi.org/{x}" target="_blank">{x}</a>' if pd.notna(x) else x
            )
        #clickable urls
        if 'url' in df.columns:
            df['url'] = df['url'].apply(
                lambda x: f'<a href="{x}" target="_blank">{x}</a>' if pd.notna(x) else x
            )
        #prepare NA cells as empty string
        df = df.astype('object').where(df.notna(), '')
        
        
        #write
        ofile = StringIO()
        ofile.write('---\n'
                    'hide:\n'
                    '  - toc\n'
                    'extra:\n'
                    '  layout: full\n'
                    '---\n'
                    '\n'
                    '# Bibliography\n'
                    '\n'
                    f'[Download `.bib`.]({BIB_TARGET_URI})\n'
                    '\n'
        )
        df.to_markdown(ofile, index=False)
        
        
        #emit bibtex
        bib = '\n\n'.join(to_bibtex(entry) for entry in data)
        
        
        #register
        files.append(File.generated(config, MD_TARGET_URI, content=ofile.getvalue()))
        files.append(File.generated(config, BIB_TARGET_URI, content=bib))
        
        return files
