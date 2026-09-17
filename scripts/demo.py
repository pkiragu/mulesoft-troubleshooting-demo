#!/usr/bin/env python3
"""Local demo lifecycle. Never modifies the Anypoint Studio installation."""
import argparse,glob,json,os,shutil,socket,subprocess,sys,time,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parents[1];RUN=R/'.run';MULE=R/'.runtime/mule'
import hashlib
ALIAS=Path('/tmp')/('codex-mule-'+hashlib.sha256(str(R).encode()).hexdigest()[:12])
APPS=['inventory-system-api','order-system-api','order-process-api','shopping-experience-api']
def health(port):
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as r:return r.status==200
 except Exception:return False
def setup():
 if not (MULE/'bin/mule').exists():
  candidates=glob.glob('/Applications/AnypointStudio.app/Contents/Eclipse/plugins/org.mule.tooling.server.4.9.ee_*/mule')
  source=Path(os.environ.get('DEMO_MULE_SOURCE',candidates[0] if candidates else ''))
  if not (source/'bin/mule').exists():sys.exit('Set DEMO_MULE_SOURCE to a Mule 4.9 runtime directory.')
  shutil.copytree(source,MULE,ignore=shutil.ignore_patterns('apps','apps-staging','logs','policies','server-plugins','server-plugins-staging','*.pid','*.status'))
 for name in ['apps','logs']: (MULE/name).mkdir(exist_ok=True)
 java=shutil.which('java');conf=MULE/'conf/wrapper.conf'
 lines=conf.read_text().splitlines()
 conf.write_text('\n'.join('wrapper.java.command='+java if x.startswith('wrapper.java.command=') else x.replace('-XX:MaxMetaspaceSize=256m','-XX:MaxMetaspaceSize=512m') for x in lines)+'\n')
def build(app=None):
 cmd=['mvn','-B','-DskipMunitTests','package']
 if app:cmd+=['-pl','apps/'+app,'-am']
 subprocess.run(cmd,cwd=R,env={**os.environ,'JAVA_HOME':str(Path(shutil.which('java')).resolve().parents[1])},check=True)
def deploy(app=None):
 for a in ([app] if app else APPS):
  jar=R/'apps'/a/'target'/f'{a}-1.0.0-mule-application.jar'
  if not jar.exists():sys.exit('Missing package. Run python3 scripts/demo.py build first.')
  # Stage outside apps; rename atomically so Mule never sees a partial JAR.
  tmp=MULE/(a+'.jar.tmp');shutil.copy2(jar,tmp);tmp.replace(MULE/'apps'/(a+'.jar'))
def wait_ready(proc):
 for _ in range(120):
  if proc.poll() is not None:
   stop();sys.exit('Mule exited during startup. Inspect .run/mule-console.log.')
  if all(health(p) for p in [8095,8081,8082,8083,8084]):print('All four Mule APIs and mock backend are ready.');return
  time.sleep(1)
 stop();sys.exit('Startup timed out. Inspect .run/mule-console.log and .runtime/mule/logs/.')
def start():
 setup();RUN.mkdir(exist_ok=True)
 if ALIAS.is_symlink():
  if ALIAS.resolve()!=MULE.resolve():sys.exit('Runtime alias points elsewhere.')
 elif ALIAS.exists():sys.exit('Runtime alias path is occupied.')
 else:ALIAS.symlink_to(MULE,target_is_directory=True)
 for p in [8095,8081,8082,8083,8084]:
  with socket.socket() as s:
   if s.connect_ex(('127.0.0.1',p))==0:sys.exit(f'Port {p} is in use; stop the existing demo or choose different ports.')
 deploy()
 with (RUN/'backend.log').open('a') as f:
  proc=subprocess.Popen([sys.executable,str(R/'scripts/backend.py')],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 (RUN/'backend.pid').write_text(str(proc.pid))
 with (RUN/'mule-console.log').open('a') as f:
  opts=[shutil.which('java'),'-Xms256m','-Xmx1024m','-XX:MaxMetaspaceSize=512m',f'-Dmule.home={ALIAS}',f'-Dmule.base={ALIAS}','-Dmule.bootstrap.container.wrapper.class=org.mule.runtime.module.boot.internal.MuleContainerBasicWrapper','-Dmule.testingMode=true','-Djava.net.preferIPv4Stack=true','-Danypoint.platform.analytics_enabled=false','--module-path',str(ALIAS/'lib/boot'),'--add-modules=java.se,org.mule.runtime.jpms.utils,com.fasterxml.jackson.core,org.apache.commons.codec']
  for module,package in [('java.base','sun.nio.ch'),('java.management','sun.management'),('jdk.management','com.sun.management.internal'),('java.base','java.lang.reflect'),('java.base','java.lang'),('java.sql','java.sql'),('java.base','java.lang.invoke'),('java.base','jdk.internal.ref'),('java.base','java.nio')]:opts.append(f'--add-opens={module}/{package}=org.mule.runtime.jpms.utils')
  opts+=['--module','com.mulesoft.mule.boot/com.mulesoft.mule.runtime.MuleContainerBootstrap']
  proc=subprocess.Popen(opts,cwd=ALIAS,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 (RUN/'mule.pid').write_text(str(proc.pid));wait_ready(proc)
def stop():
 import signal
 for name in ['mule','backend']:
  p=RUN/(name+'.pid')
  if p.exists():
   pid=int(p.read_text())
   # Guard against a stale PID belonging to a different process.
   command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
   expected=f'-Dmule.home={ALIAS}' if name=='mule' else str(R/'scripts/backend.py')
   if expected in command:
    try:os.killpg(pid,signal.SIGTERM)
    except ProcessLookupError:pass
   p.unlink()
 for _ in range(40):
  if not any(health(p) for p in [8095,8081,8082,8083,8084]):break
  time.sleep(.25)
 print('Stopped demo-owned processes.')
p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','build','start','stop','status','deploy']);p.add_argument('--app',choices=APPS);args=p.parse_args()
if args.action=='setup':setup()
elif args.action=='build':build(args.app)
elif args.action=='start':start()
elif args.action=='stop':stop()
elif args.action=='deploy':deploy(args.app)
else:
 for port in [8095,8081,8082,8083,8084]:print(port,'UP' if health(port) else 'DOWN')
