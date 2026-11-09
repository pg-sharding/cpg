import json,os,pathlib
def environment(prefix):
 e=os.environ.copy();e.update(LD_LIBRARY_PATH=str(pathlib.Path(prefix)/'lib'),LC_ALL='C');return e
def save(path,value):
 path.write_text(json.dumps(value,indent=2)+'\n')
