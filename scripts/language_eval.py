"""Live-language smoke; synthetic input, no financial or messaging effects."""
import json
import tempfile
from pathlib import Path
from returnpath.config import Config
from returnpath import resolution as r

c = Config()
if c.get('RP_MODE') != 'connected-test':
    raise SystemExit('connected-test model configuration required')
c.values['RP_RESOLUTION_MODEL'] = 'live'
fixtures = [
    ('misspelled_package', ['packagea was broken', 'The item is scratched too. I would rather hang onto it for some money back.'], 'keep'),
    ('misspelled_damage', ['damanged item', 'I want to send it back and get my money back.'], 'return'),
    ('paraphrase_keep', ['One earcup is scratched, but it works. I would rather hang onto it if you can compensate me.'], 'keep'),
    ('paraphrase_return', ['It arrived in pieces. I would like to send it back and get my money back.'], 'return'),
]
rows=[]
with tempfile.TemporaryDirectory(prefix='returnpath-language-') as root:
    for name, messages, expected in fixtures:
        db=r.connect(Path(root)/(name+'.sqlite'))
        rid=r.start(db,'synthetic',r.catalog(c),'7201')
        try:
            first_state=None
            for message in messages:
                r.negotiate(db,c,rid,'synthetic',message)
                if first_state is None:
                    first_state=db.execute('SELECT state FROM resolutions').fetchone()[0]
            offer=db.execute('SELECT terms FROM offers ORDER BY rowid DESC LIMIT 1').fetchone()
            selected=json.loads(offer[0])['selected']['id'] if offer else None
            passed=selected==expected and (len(messages)==1 or first_state=='CLARIFY')
            rows.append({'scenario':name,'turns':len(messages),'first_state':first_state,'selected':selected,'passed':passed})
        except Exception as exc:
            rows.append({'scenario':name,'passed':False,'error_type':type(exc).__name__})
        finally:
            db.close()
report={'mode':'LIVE_MODEL','model':c.get('RP_MODEL'),'revision':r.REVISION,
        'scope':'Four synthetic language smoke scenarios; one trial each, not broad reliability evidence',
        'scenarios':len(rows),'passed':sum(row['passed'] for row in rows),'results':rows}
Path('evidence/language-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(int(report['passed']!=len(rows)))
