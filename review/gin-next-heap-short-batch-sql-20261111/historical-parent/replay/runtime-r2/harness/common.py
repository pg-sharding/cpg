import json,os,pathlib
def environment(prefix):
 e={k:v for k,v in os.environ.items()if not k.startswith('PG')and k not in('LD_PRELOAD','LD_LIBRARY_PATH')};e.update(LD_LIBRARY_PATH=str(pathlib.Path(prefix)/'lib'),LC_ALL='C');return e
def save(path,value):
 path.write_text(json.dumps(value,indent=2)+'\n')
