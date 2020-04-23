#!./python_wrapper
import os, sys, json
from subprocess import call, Popen, PIPE


print("Content-type: application/json; charset=utf-8\n")


content_len = int(os.environ["CONTENT_LENGTH"])

body = sys.stdin.read(content_len)
sys.stderr.write(body + '\n')
payload = json.loads(body)

MYSQL=['/usr/bin/mysql', '-Bsu', 'joknarf', '-D', 'logme']

def sql_str(string):
	return string.replace('\\','\\\\').replace("'","\\'")

if not 'logid' in payload:
    sql = "insert into log set log_text='',log_begin=now();select last_insert_id()"
    logid = Popen(MYSQL + ['-e', sql], stdout=PIPE).communicate()[0].decode('utf8').rstrip('\n')
else:
	logid = payload['logid']

if 'exit_code' in payload:
	sql = "update log set log_exitcode="+ str(payload['exit_code']) +" where log_id="+ str(logid) +";\n"
	Popen(MYSQL + ['-e', sql], stdout=PIPE).communicate()[0].decode('utf8').rstrip('\n')
if payload['logtext']:
	sql = "update log set log_text=concat(log_text,'"+ sql_str(payload['logtext']) +"') where log_id="+ str(logid) +";\n"
	Popen(MYSQL + ['-e', sql], stdout=PIPE).communicate()[0].decode('utf8').rstrip('\n')


data = {
  "logid": logid,
}

print(json.dumps(data))
