"""Run the local Audiveris installation on the new source PDFs, retaining logs."""
from pathlib import Path
import argparse, json, os, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id')
    args = parser.parse_args()
    definitions = json.loads((ROOT/'tools/new-scores.json').read_text(encoding='utf-8'))
    java = ROOT/'tools/audiveris/Audiveris/runtime/bin/java.exe'
    for item in definitions:
        if args.id and item['id'] != args.id:
            continue
        source = ROOT/'data/sources'/item['source']
        incoming = ROOT/item['source']
        if incoming.exists() and not source.exists():
            incoming.rename(source)
        folder = ROOT/'data/omr/new'/item['id']
        folder.mkdir(parents=True, exist_ok=True)
        pdf = folder/(item['id']+'.pdf')
        if not pdf.exists():
            if item.get('skipPages'):
                sys.path.insert(0, str(ROOT/'tools/python-libs'))
                import fitz
                with fitz.open(source) as document:
                    document.select(list(range(item['skipPages'], len(document))))
                    document.save(pdf)
            else:
                shutil.copy2(source, pdf)
        with (folder/'transcribe.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([str(java), '-Xmx4g', '-Djava.awt.headless=true', '-cp',
                str(ROOT/'tools/audiveris/Audiveris/app/*'), 'Audiveris', '-batch', '-save',
                '-export', '-output', str(folder), '--', str(pdf)],
                env=dict(os.environ, APPDATA=str(ROOT/'tools/state')), stdout=log, stderr=subprocess.STDOUT)
        print(item['id'], 'exit', result.returncode, flush=True)

if __name__ == '__main__':
    main()
