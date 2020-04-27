#!./python_wrapper
import sys, re
from subprocess import call, Popen, PIPE
from threading import Thread
from time import sleep
from datetime import datetime
import argparse
import requests
import json

class LogmeLogger(Thread):
    """In a thread continously read a log file to send to a log facility"""

    def __init__(self, logfile, quiet=False):
        Thread.__init__(self)
        self.finished = False
        self.logread = open(logfile, 'rb')
        self.quiet = quiet
        self.exit_code = None
    
    def format_str(self, string):
        string = re.sub(b'\x1b][^\x1b\x07]*\x07', b'', string, re.MULTILINE)
        string = string.replace(b'\n',b'\n' + datetime.now().strftime('%Y-%m-%d %H:%M:%S ').encode('utf8'))
        return string

    def run(self):
        log = b""
        last = False
        while True:
            new = self.logread.read(65000)
            self.echo(new)
            log += self.format_str(new)
            if log:
                if self.logwrite(log):
                   log = b""
            if last:
                self.logwrite(log)
                break
            if self.finished:
                last = True
            else:
                sleep(0.5)
        self.logread.close()
        self.logclose()

    def echo(self, logtext):
        if not self.quiet:
            #print(logtext.decode('utf8'), end='', flush=True)
            sys.stdout.write(logtext.decode('utf8'))
            sys.stdout.flush()

    def logwrite(self, logtext):
        pass    

    def logclose(self):
        pass

    def stop(self, exit_code):
        self.exit_code = exit_code
        self.finished = True

class LogmeHTTP(LogmeLogger):
    def __init__(self, logfile, quiet=False):
        LogmeLogger.__init__(self, logfile, quiet)
        self.url = 'http://localhost:8888/logme_api.py'
        self.payload = {
            "user": "root",
            "command": "test",
            "module": "test",
            "logtext": "",
        }

    def api_call(self):
        try:
            resp = requests.post( self.url, json=self.payload, timeout=10, headers={ 'Content-Type' : 'application/json' })
        except:
            sys.stderr.write('\nLOGme: API call failed\n')
            sys.stderr.flush()
            return False
        if resp and 'logid' in resp.json():
            self.payload['logid'] = resp.json()['logid']
        else:
            sys.stderr.write(' \nLOGme: Failed to retrieve log_id\n')
            sys.stderr.flush()
            return False
        return True

    def logwrite(self, logtext):
        self.payload['logtext'] = logtext.decode('utf8')
        if self.exit_code != None:
            self.payload['exit_code'] = self.exit_code
        return self.api_call()



class LogmeMysql(LogmeLogger):
    MYSQL=['/usr/bin/mysql', '-Bsu', 'joknarf', '-D', 'logme']

    def __init__(self, logfile, quiet):
        LogmeLogger.__init__(self, logfile, quiet)
        self.logid = ""
        self.mysql = None
        self.devnull = open(os.devnull, 'w')
        self.logconnect()

    def sql_str(self, string):
        string = string.replace('\\','\\\\').replace("'","\\'")
        return string

    def logconnect(self):
        if not self.logid:
            sql = "insert into log set log_text='',log_begin=now();select last_insert_id()"
            self.logid = Popen(LogmeMysql.MYSQL + ['-e', sql], stdout=PIPE, stderr=self.devnull).communicate()[0].decode('utf8').rstrip('\n')
        if self.logid:
            self.mysql = Popen(LogmeMysql.MYSQL, stdin=PIPE, stderr=self.devnull)
        else:
            sys.stderr.write('\nLOGme: Cannot connect to log DB\n')
            return False
        return True

    def logwrite(self, logtext):
        """write to log facility """
        # create new log
        if self.exit_code != None:
            sqlex = ",log_exitcode="+ str(self.exit_code)
        sql = "update log set log_text=concat(log_text,'"+ self.sql_str(logtext) +"')"+ sqlex +" where log_id="+ self.logid +";\n"
        try:
            self.mysql.stdin.write(sql)
            self.mysql.stdin.flush()
        except:
            sys.stderr.write("\nLOGme: Try Reconnect to log DB\n")
            self.logconnect()
            return False
        return True

    def logclose(self):
        """close log facility """
        self.mysql.stdin.close()
        self.mysql.wait()
        self.devnull.close()



class Logme():
    """
        A class to run command with script to get logged output
        Send the log to a log facility
    """
    def __init__(self, logfile='/var/tmp/logme.log', interactive=False, quiet=False):
        self.logfile = logfile
        open(logfile, 'w').close()
        self.interactive = interactive
        if interactive:
            self.quiet = True
        else:
            self.quiet = quiet
        self.exit_code = 0
        self.logthread = LogmeHTTP(logfile, self.quiet)
        self.logthread.start()

    def logwrite(self, line):
        logf = open(self.logfile, 'a')
        logf.write(line + "\n")
        logf.close()
        
    def run(self, command):
        self.logwrite('\nStarting command: '+ command)
        if self.interactive:
            cmd = ['/usr/bin/script', '--return', '--flush', '--quiet', '--append']
            if command:
                cmd += ['--command', command]
            cmd.append(self.logfile)
            self.exit_code = call(cmd)
        else:
            logf = open(self.logfile, 'a')
            self.exit_code = call(command, stdout=logf, stderr=logf, shell=True)
            logf.close()
        self.logwrite('End of command: '+ command +' : exit code: '+ str(self.exit_code) +"\n")
        self.logthread.stop(self.exit_code)
        self.logthread.join()

        return self.exit_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logfile', '-f', default='/var/tmp/logme.log')
    parser.add_argument('--command', '-c', default='')
    parser.add_argument('--interactive', '-i', action='store_true', default=False)
    parser.add_argument('--quiet', '-q', action='store_true', default=False)

    args = parser.parse_args()
    logjob = Logme(args.logfile, args.interactive, args.quiet)
    exit_code = logjob.run(args.command)
    print('==> logme done')
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
