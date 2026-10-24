# facilitator helper (s3): builds injection/window-runs.txt (protocol 5.4) from the org's events, run logs and org-git. Read-only on the org.
import sys,json,glob,re,subprocess
from datetime import datetime,timedelta
S=sys.argv[1]; org=S+'/org'; out=sys.argv[2]
TID='20261024T041932216940-root-daff'; REV='20261024T041412342994-root-c209'
w0,w1='2026-10-24T04:19:32','2026-10-24T04:22:20'
ev=[]
for f in glob.glob(org+'/.runtime/events/*/*.jsonl'):
    for l in open(f):
        try: ev.append(json.loads(l))
        except Exception: pass
ev.sort(key=lambda e:(e['ts'],e.get('seq',0)))
starts=[e for e in ev if e['kind']=='run.start' and w0<=e['ts'][:19]<=w1]
o=open(out+'/window-runs.txt','w')
o.write(f"# window runs (protocol 5.4): runs that started in the injection window {w0}Z .. {w1}Z; injected task {TID}; revised (memo 1) task {REV}\n")
for s in starts:
    run=s['run']; agent=s['agent']; stem=run.split('@')[1]
    ee=[e for e in ev if e['kind']=='run.end' and e['run']==run]
    end=ee[0]['ts'] if ee else None
    log=open(f"{org}/{agent}/runs/{stem}.log").read()
    cmd=re.search(r'^# cmd: .*$',log,re.M).group(0)
    model=re.findall(r'--model (\S+)',cmd); eff=re.findall(r'--effort (\S+)',cmd)
    rp=[e for e in ev if e['kind']=='tool.call' and e.get('run')==run and 'revise_playbook' in json.dumps(e)]
    rl1=len(re.findall(r'^\[tool\] @hirearchy/revise_playbook(?= |$)',log,re.M))
    rl3=len(re.findall(r'^\[tool\] @hirearchy/\w+',log,re.M))
    o.write(f"\n## run {run} agent={agent} model={model} effort={eff} start={s['ts']} end={end} exit_code={ee[0].get('exit_code') if ee else None}\n")
    o.write(f"revise_playbook calls in this run (events): {len(rp)}; run-log RL1 lines: {rl1}; RL3 lines: {rl3}\n")
    for e in rp: o.write("  revise_playbook event: "+json.dumps(e)+"\n")
    lo=datetime.fromisoformat(s['ts'])-timedelta(seconds=1); hi=(datetime.fromisoformat(end) if end else datetime.fromisoformat(s['ts']))+timedelta(seconds=1)
    for f in sorted(glob.glob(f"{org}/{agent}/sent/*.md")):
        t=open(f).read(); h=t.split('---\n',2)[1]
        c=re.search(r"created: '?([^'\n]+)",h)
        if not c: continue
        ct=datetime.fromisoformat(c.group(1) if '+' in c.group(1) else c.group(1)+'+00:00')
        if lo<=ct<=hi:
            ty=re.search(r'type: (\S+)',h).group(1); to=re.search(r'to: (\S+)',h).group(1); src=re.search(r'source: (\S+)',h)
            st=re.search(r'status: (\S+)',h); mid=re.search(r'id: (\S+)',h).group(1)
            o.write(f"  {agent} message {mid} to={to} type={ty} status={st.group(1) if st else None} source={src.group(1) if src else None} created={c.group(1)}\n")
            if ty=='result':
                lm=re.search(r'## Lessons\n(.*?)(\n## |\Z)',t,re.S)
                o.write("  ## Lessons: "+(lm.group(1).strip() if lm else '(none)')+"\n")
    g=subprocess.run(['git','-C',org,'log','-1','--format=%h','--grep',stem,'-p'],capture_output=True,text=True).stdout
    mem="\n".join("    "+l for l in g.splitlines() if 'MEMORY.md' in l or l.startswith(('-','+')) )
    o.write(f"  org-git commit for this run (MEMORY.md lines of its diff):\n{mem}\n")
o.close(); print(len(starts),'window runs')
