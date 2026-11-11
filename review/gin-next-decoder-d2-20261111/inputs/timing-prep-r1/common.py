import json,os,pathlib
def save(path,value):
 path=pathlib.Path(path);temporary=path.with_name(path.name+".tmp");temporary.write_text(json.dumps(value,indent=2)+"\n")
 with temporary.open("rb")as f:os.fsync(f.fileno())
 temporary.replace(path)
