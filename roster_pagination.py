"""Validate cached public Ankara register pages without discarding count drift."""
from bs4 import BeautifulSoup


def assemble(pages, alphabet, size=500):
    rows, variants, queries, errors = {}, {}, [], []
    for letter in alphabet:
        group=pages.get(letter,{})
        if 0 not in group:
            errors.append({'surname':letter,'issue':'first_page_missing'})
            continue
        counts=[];ids=[];page_errors=[]
        for start,page in sorted(group.items()):
            total=page.get('recordsFiltered');cells=page.get('data')
            if not isinstance(total,int) or total<0 or not isinstance(cells,list):
                raise ValueError('Unexpected official roster page schema')
            counts.append(total)
            if len(cells)!=min(size,max(0,total-start)):
                page_errors.append({'start':start,'issue':'unexpected_page_length'})
            for cell in cells:
                if len(cell)<5:raise ValueError('Missing official identity columns')
                text=lambda value:BeautifulSoup(value,'html.parser').get_text(' ',strip=True)
                reg=text(cell[2]);first=text(cell[3]);last=text(cell[4])
                if not reg.isdigit() or not first or not last:raise ValueError('Missing official roster identity')
                record={'regNumber':reg,'firstName':first,'lastName':last}
                if reg in rows and rows[reg]!=record:variants.setdefault(reg,[]).append(record)
                rows.setdefault(reg,record);ids.append(reg)
        expected=set(range(0,max(counts),size)) or {0}
        missing=sorted(expected-set(group))
        drift=len(set(counts))>1
        if missing:errors.append({'surname':letter,'issue':'pages_missing','starts':missing})
        if page_errors:errors.append({'surname':letter,'issue':'page_lengths','pages':page_errors})
        duplicates=len(ids)-len(set(ids))
        if duplicates:errors.append({'surname':letter,'issue':'duplicate_id_across_pages','count':duplicates})
        queries.append({'surname':letter,'reported_min':min(counts),'reported_max':max(counts),
                        'returned_rows':len(ids),'unique_ids':len(set(ids)),'count_changed':drift,
                        'all_planned_pages_fetched':not missing and not page_errors,
                        'stable_complete_pages':not missing and not page_errors and not duplicates and not drift and len(ids)==max(counts)})
    return {'rows':list(rows.values()),'unique_registrations':len(rows),'variants':variants,
            'queries':queries,'errors':errors,'all_planned_pages_fetched':len(queries)==len(alphabet) and all(q['all_planned_pages_fetched'] for q in queries),
            'all_letter_queries_complete':len(queries)==len(alphabet) and all(q['stable_complete_pages'] for q in queries) and not errors and not variants,
            'letters_with_count_drift':[q['surname'] for q in queries if q['count_changed']],
            'national_completeness_claim':False}
