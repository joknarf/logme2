#!/usr/bin/python3
import subprocess, re
from ansi2html import Ansi2HTMLConverter

print("Content-type: text/html; charset=utf-8\n")

convansi = Ansi2HTMLConverter()

sql = 'select log_text from log where log_id=(select max(log_id) from log)'
log = subprocess.Popen("mysql --raw -Bs -D logme -e '"+ sql +"' |./typescript2txtcol 2>/dev/null", shell=True, stdout=subprocess.PIPE, encoding='utf8').stdout.read()
html = convansi.convert(log)
print(html)
exit(0)
