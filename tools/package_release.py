"""Package Persian Fairytale V2 without environments, private briefs or saves."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'release' / 'persian fairytale. V2.zip'
TOP = 'persian fairytale. V2'
TOP_FILES = ('README.md','VERSION.txt','START_GAME.bat','INSTALL_DEPENDENCIES.bat',
             'requirements.txt','launcher.py','server.py','runner.py','saves.py',
             'exercises.py','model_adapter.py','local_model_example.py')
DOCS = ('START_RU.md','CURRICULUM.md','SOURCES.md','ASSETS.md','TEST_REPORT.md',
        'DESKTOP_LEARNING_V2.md','UI_V2.md','MISSION_TEACHING_V2.md','DESKTOP_CURRICULUM_V2.md')

def main():
    DEST.parent.mkdir(exist_ok=True)
    route = json.loads((ROOT/'artifacts/browser-v2-route.json').read_text())
    assert route['passed'] and route['authoredTeachingMissions'] == 40
    for name, expected in route['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    assert json.loads((ROOT/'artifacts/browser-v2-ui/report.json').read_text())['passed']
    unit = json.loads((ROOT/'artifacts/unit-tests.json').read_text())
    assert unit['passed']
    for name, expected in unit['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    paths = [ROOT / p for p in TOP_FILES]
    for folder in ('static','data','notebooks','tests','tools'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.extend(ROOT/'docs'/p for p in DOCS if (ROOT/'docs'/p).exists())
    # These are current-edition evidence. Old build histories are not evidence.
    paths.extend(p for p in (ROOT/'artifacts').rglob('*') if p.is_file()
                 and p.suffix in ('.json','.png','.log') and 'initial' not in p.name)
    paths = sorted(set(paths))
    for p in paths:
        assert p.is_file(), p
        assert p.name not in ('BRIEF_RU.md','save.json','save.previous.json')
        assert p.suffix.lower() not in ('.jks','.keystore','.pem','.p12')
    manifest = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in paths:
            archive.write(p,TOP+'/'+p.relative_to(ROOT).as_posix())
        archive.writestr(TOP+'/MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(DEST) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(paths)+1
    report = {'archive':str(DEST),'files':len(paths)+1,'bytes':DEST.stat().st_size,
              'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest()}
    (DEST.parent/'release-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
