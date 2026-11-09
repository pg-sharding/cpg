"""Prospective five-role Williams design; pure, deterministic and finite."""
import collections,itertools,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
ROLES=['B','T','N','H','C']
ORDERS=[[ROLES[(x+k)%5] for x in [0,1,4,2,3]] for k in range(5)]
ORDERS += [list(reversed(x)) for x in ORDERS[:5]]
CASES=json.loads((HERE/'inputs/cases.json').read_text())['cases']
def schedule(cohort):
 assert cohort in [0,1] and len(CASES)==19
 serial=0
 for case in CASES if cohort==0 else reversed(CASES):
  for round in range(12):
   order=ORDERS[round if round<2 else round-2]
   for position,role in enumerate(order):
    yield dict(serial=serial,cohort=cohort,case=case['name'],round=round,position=position,role=role,order=order,retained=round>=2)
    serial+=1
def check():
 pos=collections.Counter((role,i) for order in ORDERS for i,role in enumerate(order))
 adj=collections.Counter((order[i],order[i+1]) for order in ORDERS for i in range(4))
 assert len(ORDERS)==10 and len({tuple(x) for x in ORDERS})==10
 assert set(pos)==set(itertools.product(ROLES,range(5))) and set(pos.values())=={2}
 assert set(adj)=={(a,b) for a in ROLES for b in ROLES if a!=b} and set(adj.values())=={2}
 for cohort in [0,1]:
  rows=list(schedule(cohort));assert len(rows)==1140 and sum(x['retained'] for x in rows)==950
  assert not any(a['role']==b['role'] for a,b in zip(rows,rows[1:]))
 return dict(roles=ROLES,retained_orders=ORDERS,warm_orders=ORDERS[:2],positions_each=2,ordered_adjacencies_each=2,per_cohort=dict(raw=1140,retained=950,warm=190),both=dict(raw=2280,retained=1900,warm=380),immediate_same_role_commands=0)
if __name__=='__main__':print(json.dumps(check(),indent=2))
