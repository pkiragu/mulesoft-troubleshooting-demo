#!/usr/bin/env python3
"""Prepare isolated Exchange projects and deliver this synthetic demo to CloudHub 2."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '.run/cloud-build'
ORG = '05464f06-6501-4ec9-932a-8193ad3f4559'
BASE = 'https://anypoint.mulesoft.com'
NS = 'http://maven.apache.org/POM/4.0.0'
ET.register_namespace('', NS)
N = {'m': NS}
APPS = ['mock-backend', 'inventory-system-api', 'order-system-api', 'order-process-api', 'shopping-experience-api']
PREFIX = 'showtell'

def child(parent, name, text=None):
    e = ET.SubElement(parent, '{'+NS+'}'+name)
    if text is not None: e.text = str(text)
    return e

def prepare(version):
    if not re.fullmatch(r'1\.0\.[0-9]+', version):
        raise ValueError('Version must be a unique 1.0.<number> release')
    STAGE.mkdir(parents=True, exist_ok=True)
    parent = ET.parse(ROOT/'pom.xml').getroot()
    for name in APPS:
        source = ROOT/('cloud' if name == 'mock-backend' else 'apps')/name
        dest = STAGE/name
        dest.mkdir(exist_ok=True)
        shutil.copytree(source/'src', dest/'src', dirs_exist_ok=True)
        shutil.copy2(source/'mule-artifact.json', dest/'mule-artifact.json')
        pom = ET.parse(source/'pom.xml').getroot()
        pom.remove(pom.find('m:parent', N))
        child(pom, 'groupId', ORG)
        child(pom, 'version', version)
        child(pom, 'name', name)
        props = pom.find('m:properties', N)
        if props is None: props = child(pom, 'properties')
        for e in parent.find('m:properties', N): props.append(copy.deepcopy(e))
        for tag in ['repositories', 'pluginRepositories']:
            pom.append(copy.deepcopy(parent.find('m:'+tag, N)))
        dist = child(pom, 'distributionManagement')
        repo = child(dist, 'repository')
        child(repo, 'id', 'anypoint-exchange')
        child(repo, 'url', f'https://maven.anypoint.mulesoft.com/api/v3/organizations/{ORG}/maven')
        # Exchange pre-deploy downloads its validation response as an artifact.
        # distributionManagement alone only configures uploads.
        pom.find('m:repositories', N).append(copy.deepcopy(repo))
        cfg = pom.find("m:build/m:plugins/m:plugin[m:artifactId='mule-maven-plugin']/m:configuration", N)
        child(cfg, 'classifier', 'mule-application')
        deploy = child(cfg, 'cloudhub2Deployment')
        for key, val in {'uri':BASE, 'provider':'MC', 'environment':'Sandbox', 'target':'Cloudhub-US-East-2',
            'muleVersion':'4.9.0', 'releaseChannel':'LTS', 'javaVersion':'17', 'businessGroupId':ORG,
            'applicationName':PREFIX+'-'+name, 'replicas':'1', 'vCores':'0.1', 'deploymentTimeout':'900000',
            'connectedAppClientId':'${env.ANYPOINT_CLIENT_ID}',
            'connectedAppClientSecret':'${env.ANYPOINT_CLIENT_SECRET}',
            'connectedAppGrantType':'client_credentials'}.items(): child(deploy,key,val)
        settings = child(deploy, 'deploymentSettings')
        child(settings, 'generateDefaultPublicUrl', 'true')
        # In-memory backend requires one replica and a clean restart between releases.
        child(settings, 'updateStrategy', 'recreate')
        properties = child(deploy, 'properties')
        child(properties, 'http.host', '0.0.0.0')
        child(properties, 'http.port', '8081')
        for service in ['backend','inventory','orders','process']:
            child(properties, service+'.host', '${env.DEMO_'+service.upper()+'_HOST}')
            child(properties, service+'.port', '443')
            child(properties, service+'.protocol', 'HTTPS')
        ET.indent(pom)
        ET.ElementTree(pom).write(dest/'pom.xml',encoding='unicode',xml_declaration=True)
    (STAGE/'settings.xml').write_text('''<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"><servers><server><id>anypoint-exchange</id><username>~~~Client~~~</username><password>${env.ANYPOINT_CLIENT_ID}~?~${env.ANYPOINT_CLIENT_SECRET}</password></server></servers></settings>''')
    (STAGE/'version.txt').write_text(version)
    print('Prepared five standalone Exchange projects:', version, flush=True)

def request(path, token=None, body=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=45) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        # Never log a token response or credential-bearing request.
        raise RuntimeError(f'Anypoint API returned HTTP {e.code} for {path}') from None

def discover_url(token, env_id, name):
    path=f'/amc/application-manager/api/v2/organizations/{ORG}/environments/{env_id}/deployments'
    deployments=request(path,token)
    matches=[x for x in deployments.get('items',[]) if x['name']==PREFIX+'-'+name]
    if len(matches)!=1: raise RuntimeError('Cannot uniquely identify deployment '+name)
    detail=request(path+'/'+matches[0]['id'],token)
    url=detail.get('target',{}).get('deploymentSettings',{}).get('http',{}).get('inbound',{}).get('publicUrl')
    if not url: raise RuntimeError('Deployment response has no publicUrl for '+name)
    if not url.startswith('https://'): url='https://'+url.removeprefix('http://')
    parsed=urllib.parse.urlparse(url)
    if not parsed.hostname or not parsed.hostname.endswith('.cloudhub.io'):
        raise RuntimeError('Unexpected deployment URL')
    return 'https://'+parsed.netloc

def health(url):
    for attempt in range(60):
        try:
            with urllib.request.urlopen(url+'/health',timeout=15) as r:
                if r.status==200 and json.load(r)['status']=='UP': return
        except (OSError,ValueError,KeyError): pass
        time.sleep(5)
    raise RuntimeError('Health check timed out: '+url)

def deploy():
    for key in ['ANYPOINT_CLIENT_ID','ANYPOINT_CLIENT_SECRET']:
        if not os.environ.get(key): raise RuntimeError('Missing '+key)
    token=request('/accounts/api/v2/oauth2/token',body={'grant_type':'client_credentials',
        'client_id':os.environ['ANYPOINT_CLIENT_ID'],'client_secret':os.environ['ANYPOINT_CLIENT_SECRET']})['access_token']
    if os.environ.get('GITHUB_ACTIONS'): print('::add-mask::'+token,flush=True)
    envs=request(f'/accounts/api/organizations/{ORG}/environments',token)['data']
    matching=[e for e in envs if e['name']=='Sandbox']
    if len(matching)!=1: raise RuntimeError('Sandbox environment not found uniquely')
    env_id=matching[0]['id']
    runenv=os.environ.copy()
    for service in ['BACKEND','INVENTORY','ORDERS','PROCESS']: runenv['DEMO_'+service+'_HOST']='localhost'
    urls={}
    outputs=ROOT/'delivery/cloud'
    outputs.mkdir(parents=True,exist_ok=True)
    for name in APPS:
        print('Packaging, publishing and deploying '+name,flush=True)
        mvn=['mvn','-B','-ntp','-e','-s',str(STAGE/'settings.xml'),'-f',str(STAGE/name/'pom.xml')]
        # Exchange publication is a separate lifecycle from CloudHub deployment.
        subprocess.run(mvn+['clean','deploy','-DskipMunitTests'],env=runenv,check=True)
        jar=list((STAGE/name/'target').glob('*-mule-application.jar'))
        if len(jar)!=1: raise RuntimeError('Expected one published application package')
        subprocess.run(mvn+['mule:deploy','-DmuleDeploy','-Dartifact='+str(jar[0])],env=runenv,check=True)
        url=discover_url(token,env_id,name)
        health(url)
        urls[name]=url
        service={'mock-backend':'BACKEND','inventory-system-api':'INVENTORY','order-system-api':'ORDERS','order-process-api':'PROCESS'}.get(name)
        if service: runenv['DEMO_'+service+'_HOST']=urllib.parse.urlparse(url).hostname
        jars=list((STAGE/name/'target').glob('*-mule-application.jar'))
        if len(jars)!=1: raise RuntimeError('Expected one deployed package for '+name)
        shutil.copy2(jars[0],outputs/jars[0].name)
        (outputs/'urls.json').write_text(json.dumps(urls,indent=2)+'\n')
        print(name+' healthy at '+url,flush=True)
    (outputs/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(outputs.glob('*.jar'))))
    for store in ['LONDON-01','BRISTOL-02']:
        expected=502 if store=='BRISTOL-02' and os.environ.get('DEMO_MODE','incident')=='incident' else 201
        body=json.dumps({'sku':'LAPTOP-01','storeId':store,'quantity':1}).encode()
        req=urllib.request.Request(urls['shopping-experience-api']+'/checkout',data=body,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=45) as r: status=r.status
        except urllib.error.HTTPError as e: status=e.code
        if status!=expected: raise RuntimeError(f'{store}: expected {expected}, received {status}')
        print(f'Cloud smoke: {store} returned expected HTTP {status}',flush=True)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write('## CloudHub demo deployed\n\n'+''.join(f'- [{n}]({u}/health)\n' for n,u in urls.items()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',metavar='VERSION');p.add_argument('--deploy',action='store_true');a=p.parse_args()
    if a.prepare: prepare(a.prepare)
    if a.deploy: deploy()
