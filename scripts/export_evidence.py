"""Allowlisted synthetic evidence package; never traverse credential/runtime files."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
allowed = ['README.md', 'JUDGE_GUIDE.md', 'submission.json', 'IMPLEMENTATION_STATUS.md',
           'docs/ARCHITECTURE.md', 'docs/RELIABILITY_BRIEF.md', 'docs/EVALUATION.md',
           'docs/PROVENANCE.md', 'docs/REVIEW_FINDINGS.md',
           'evidence/offline-evaluation.json', 'evidence/offline-evaluation.md', 'evidence/local-demo.json']
output = root / '.runtime/export/returnpath-local-evidence.zip'
output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name in allowed:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing/unsafe allowlisted evidence path: ' + name)
        archive.write(path, name)
print('Exported allowlisted LOCAL evidence to .runtime/export/returnpath-local-evidence.zip')
