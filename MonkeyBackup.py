"""
Multithreaded modular backup script 
"""

import Queue
from threading import Thread
from optparse import OptionParser
import ConfigParser
import time
import os
import sys
import subprocess
import tempfile
import paramiko
import heapq

__title__ = "monkey-backup"
__version__ = "0.2.2"
__author__ = "Carles Amigo"
__email__= "fr3nd@fr3nd.net"
__url__= "http://www.fr3nd.net/projects/monkey-backup/"
__license__ = "GPL"
__description__ = __doc__

DEBUG    = 4
INFO     = 3
WARNING  = 2
CRITICAL = 1
NONE     = 0

LOG_ON_FILE = INFO
LOG_ON_SCREEN = WARNING


class PriorityQueue(Queue.Queue):
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = []
    def _qsize(self):
        """Return the number of items that are currently enqueued"""
        return len(self.queue)
    def _empty(self):
        """Check whether the queue is empty"""
        return not self.queue
    def _full(self):
        """Check whether the queue is full"""
        return self.maxsize > 0 and len(self.queue) >= self.maxsize
    def _put(self, item):
        """Put a new item in the queue"""
        heapq.heappush(self.queue, item)
    def _get(self):
        """Get an item from the queue"""
        return heapq.heappop(self.queue)
    def put(self, item, priority=0, block=True, timeout=None):
        """shadow and wrap Queue.Queue's own `put' to allow a 'priority' argument"""
        decorated_item = priority, time.time( ), item
        Queue.Queue.put(self, decorated_item, block, timeout)
    def get(self, block=True, timeout=None):
        """shadow and wrap Queue.Queue's own `get' to strip auxiliary aspects"""
        priority, time_posted, item = Queue.Queue.get(self, block, timeout)
        return item

class SshConnection(object):
    """Connects and logs into the specified hostname. 
    Arguments that are not given are guessed from the environment.
    Taken from http://commandline.org.uk/python/sftp-python-really-simple-ssh/""" 

    def __init__(self,
                 host,
                 username = None,
                 private_key = None,
                 password = None,
                 port = 22,
                 ):
        self._sftp_live = False
        self._sftp = None
        if not username:
            username = os.environ['LOGNAME']

        # Log to a temporary file.
        templog = tempfile.mkstemp('.txt', 'ssh-')[1]
        paramiko.util.log_to_file(templog)

        # Begin the SSH transport.
        self._transport = paramiko.Transport((host, port))
        self._tranport_live = True
        # Authenticate the transport.
        if password:
            # Using Password.
            self._transport.connect(username = username, password = password)
        else:
            # Use Private Key.
            if not private_key:
                # Try to use default key.
                if os.path.exists(os.path.expanduser('~/.ssh/id_rsa')):
                    private_key = '~/.ssh/id_rsa'
                elif os.path.exists(os.path.expanduser('~/.ssh/id_dsa')):
                    private_key = '~/.ssh/id_dsa'
                else:
                    raise TypeError, "You have not specified a password or key."

            private_key_file = os.path.expanduser(private_key)
            rsa_key = paramiko.RSAKey.from_private_key_file(private_key_file)
            self._transport.connect(username = username, pkey = rsa_key)
    
    def _sftp_connect(self):
        """Establish the SFTP connection."""
        if not self._sftp_live:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            self._sftp_live = True

    def get(self, remotepath, localpath = None):
        """Copies a file between the remote host and the local host."""
        if not localpath:
            localpath = os.path.split(remotepath)[1]
        self._sftp_connect()
        self._sftp.get(remotepath, localpath)

    def put(self, localpath, remotepath = None):
        """Copies a file between the local host and the remote host."""
        if not remotepath:
            remotepath = os.path.split(localpath)[1]
        self._sftp_connect()
        self._sftp.put(localpath, remotepath)

    def execute(self, command):
        """Execute the given commands on a remote machine."""
        channel = self._transport.open_session()
        channel.exec_command(command)
        output = channel.makefile('rb', -1).readlines()
        if output:
            return output
        else:
            return channel.makefile_stderr('rb', -1).readlines()

    def close(self):
        """Closes the connection and cleans up."""
        # Close SFTP Connection.
        if self._sftp_live:
            self._sftp.close()
            self._sftp_live = False
        # Close the SSH Transport.
        if self._tranport_live:
            self._transport.close()
            self._tranport_live = False

    def __del__(self):
        """Attempt to clean up if not explicitly closed."""
        self.close()

class Logger:
    """
    Class for logging. Had to create it because python logging module was not working with multithreading in 2.4
    It is safe to use it in a multithread environment.
    """
    class Worker(Thread):
        def __init__(self, parent, queue):
            self.parent = parent
            self.__queue = queue
            Thread.__init__(self)
            self.setName("logger")
        def run(self):
            while 1:
                item = self.__queue.get()
                if item is None:
                    self.parent.file.close()
                    break
                self.parent.file.write(self.parent.format(item[0] + "\n", item[1], self.parent.tag))
                self.parent.file.flush()
    
    def __init__(self, file, prefix="", tag=None, log_on_screen=LOG_ON_SCREEN, log_on_file=LOG_ON_FILE):
        """Initialize the logs"""
        self.file = open(os.path.dirname(file) + "/" + time.strftime(prefix) + os.path.basename(file),'a')
        self.log_on_screen = log_on_screen
        self.log_on_file = log_on_file
        self.tag = tag
        self.__queue = Queue.Queue()
        self.Worker(self, self.__queue).start()

    def log(self, message, level):
        """log a message in a specific level"""
        if level <= LOG_ON_SCREEN:
            print self.format(message, level, self.tag)
        if level <= LOG_ON_FILE:
            self.__queue.put((message, level))
    
    def format(self, message, level, tag):
        """Format the log message putting date and loglevel""" 
        if level == 1:
            strlevel = "CRITICAL"
        elif level == 2:
            strlevel = "WARNING"
        elif level == 3:
            strlevel = "INFO"
        elif level == 4:
            strlevel = "DEBUG"
        if tag:
            return time.strftime("%Y%m%d %H:%M:%S", time.localtime()) + " - " + strlevel + " - " + tag + " - " + message
        else:
            return time.strftime("%Y%m%d %H:%M:%S", time.localtime()) + " - " + strlevel + " - " + message
            
    
    def debug(self, message):
        """log a debug message"""
        self.log(message, DEBUG)
    
    def info(self, message):
        """log an info message"""
        self.log(message, INFO)
    
    def warning(self, message):
        """log a warning message"""
        self.log(message, WARNING)
    
    def critical(self, message):
        """log a critical message"""
        self.log(message, CRITICAL)

    def close(self):
        """Close the logfile"""
        self.__queue.put(None)

class Server:
    def __init__(self, dir, config):
        self.dir=dir
        self.servername=os.path.basename(self.dir)
        self.config = config
        self.logger = Logger(self.dir + "/log/" + self.servername + "-backup.log", prefix=self.config.get("lognameprefix") ,tag=self.servername)
        try:
            self.config.override_with(self.dir + "/config.ini")
        except IOError:
            # if there is no config file, we use the defaults
            pass
        self.backups=[]
        for backup in self.config.get("backups").replace(" ","").split(","):
            if backup == "mysql":
                self.backups.append(BackupMySQL(self))
            elif backup == "rdiff-backup":
                self.backups.append(BackupRdiffBackup(self))
            elif backup == "command":
                self.backups.append(BackupCommand(self))
    
    def run_backups(self):
        """Run all the backups defined in the config file"""
        for backup in self.backups:
            try:
                backup.run()
            except:
                self.logger.critical("Backup failed: " + str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
            try:
                backup.clean()
            except:
                self.logger.critical("Cleaning of old files failed: " + self.getName() + " failed: " + str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
        # everything has been done, so we close the log file
        self.logger.close()
            
    def __str__(self):
        return self.servername
    
class Backup:
    """Parent class for doing any backup. Should not be used. Just override it"""
    def __init__(self, server):
        self.server = server
    def run(self):
        """Method to run the backups."""
        pass
    
    def clean(self):
        """Method to clean old backups."""
        pass
    
class BackupMySQL(Backup):
    def __init__(self, server):
        Backup.__init__(self, server)
        
    def run(self):
        self.server.logger.info("Opening ssh connection to execute mysql-backup.sh ...")
        try:
            s = SshConnection(self.server.servername, self.server.config.get("sshuser","mysql"), private_key=self.server.config.get("sshkey","mysql"))
            output = s.execute("true") # run a dumb command to get the output. It has no effect because the command is set in the authorized_keys file
        except:
           self.server.logger.critical("Error running ssh: "+ str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
        if len(output)>0: 
            self.server.logger.warning("Output: " + str(output))
        else:
            self.server.logger.info("mysqldump finished...")
        
        self.server.logger.debug("Closing ssh connection...")
        s.close()

class BackupCommand(Backup):
    """Class to run any specified command when all the backups have been finished. This command will be executed on the backup server."""
    def run(self):
        command = self.server.config.get("command", "command")
        if command:
            self.server.logger.info("Running custom command...")
            self.server.logger.debug("Running command \"" + command + "\"...")
            args=command.split()
            try:
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = process.communicate()
            except:
                self.server.logger.critical("There was an error running the custom command: " + str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
            else:
                if process.returncode == 0:
                    self.server.logger.info("Custom command successfully executed (returncode=0)")
                    self.server.logger.debug("stdout: " + output[0] + ", stderr: " + output[1])
                else:
                    self.server.logger.critical("There was an error running the custom command. errorcode " + str(process.returncode))
                    self.server.logger.critical("stdout: " + output[0] + ", stderr: " + output[1])

class BackupRdiffBackup(Backup):
    """Class to backup using rdiff-backup"""
    def run(self):
        # check if destination directory exists and create it otherwise
        if not os.path.exists(self.server.dir + "/rdiff-backup"):
            os.makedirs(self.server.dir + "/rdiff-backup")
        
        args=[]
        args.append("/usr/bin/rdiff-backup")
        
        for file in self.server.config.get("global-include-file", "rdiff-backup").replace(" ","").split(",") + self.server.config.get("include-file", "rdiff-backup").replace(" ","").split(","):
            if file:
                if os.path.exists(file.replace("%server%",self.server.servername)):
                    args.append("--include-globbing-filelist=" + file.replace("%server%",self.server.servername))
        for file in self.server.config.get("global-exclude-file", "rdiff-backup").replace(" ","").split(",") + self.server.config.get("exclude-file", "rdiff-backup").replace(" ","").split(","):
            if file:
                if os.path.exists(file.replace("%server%",self.server.servername)):
                    args.append("--exclude-globbing-filelist=" + file.replace("%server%",self.server.servername))
        args.append("--no-hard-links")
        args.append("--no-eas")
        if self.server.config.get("extra-parameters", "rdiff-backup") != "":
            args.append(self.server.config.get("extra-parameters", "rdiff-backup"))
        args.append("root@" + self.server.servername + "::/")
        args.append(self.server.dir + "/rdiff-backup")
        self.server.logger.info("Running rdiff-backup...")
        self.server.logger.debug("Running " + " ".join(args))
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
        output = process.communicate()
        if process.returncode == 0:
            self.server.logger.info("rdiff-backup completed successfully")
            self.server.logger.debug("stdout: " + output[0] + ", stderr: " + output[1])
        else:
            self.server.logger.critical("There was an error running rdiff-backup: errorcode " + str(process.returncode))
            self.server.logger.critical("stdout: " + output[0] + ", stderr: " + output[1])
    
    def clean(self):
        # Delete old logs
        args=[]
        args.append("/usr/bin/rdiff-backup")
        args.append("--no-eas")
        args.append("--force")
        args.append("--remove-older-than=" + self.server.config.get("keep", "rdiff-backup"))
        args.append(self.server.dir + "/rdiff-backup")
        self.server.logger.info("Cleaning old rdiff-backup backups...")
        self.server.logger.debug("Running " + " ".join(args))
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
        output = process.communicate()
        if process.returncode == 0:
            self.server.logger.info("Old rdiff-backup backups successfully deleted")
            self.server.logger.debug("stdout: " + output[0] + ", stderr: " + output[1])
        else:
            self.server.logger.critical("There was an error deleting old backups: errorcode " + str(process.returncode))
            self.server.logger.critical("stdout: " + output[0] + ", stderr: " + output[1])

class BackupMonkey:
    class Worker(Thread):
        def __init__(self, queue, name, logger, dry):
            self.logger = logger
            self.dry = dry
            self.__queue = queue
            Thread.__init__(self)
            self.setName(name)
            
        def run(self):
            while 1:
                item = self.__queue.get()
                if item is None:
                    self.logger.info("monkey-" + self.getName() + " - thread finished")
                    break
                self.logger.info("monkey-" + self.getName() + " - started running " + item.servername + " backup...")
                if not self.dry:
                    item.run_backups()
                else:
                    item.logger.close()
                self.logger.info("monkey-" + self.getName() + " - finished running " + item.servername + " backup")
    
    def __init__(self, num_workers=4, logger=None, dry=False):
        self.__queue = PriorityQueue()
        self.__num_workers = num_workers
        self.dry = dry
        self.threads=[]
        self.logger = logger
    
    def start(self):
        """Start all the monkeys (threads)"""
        for i in range(self.__num_workers):
            self.logger.info("monkey-" + str(i) + " - thread started...")
            self.threads.append(self.Worker(self.__queue, str(i), self.logger, self.dry))
            self.threads[i].start()
    
    def get_num_monkeys(self):
        """Return the number of monkeys (threads)"""
        return self.__num_workers
    
    def enqueue(self, item, priority):
        """Enqueue server to be processed by any monkey (thread)"""
        self.__queue.put(item, priority)
    
    def wait(self):
        """Wait for all the monkeys (threads) to finish"""
        for thread in self.threads:
            thread.join()
            
class Config:
    """Wrapper to ConfigParser"""
    def __init__(self, file, verbose=False):
        self.verbose = verbose
        self.__read(file)
        
    def __read(self, file):
        self.config = ConfigParser.ConfigParser()
        f = open(file)
        self.config.readfp(f)
        f.close()
    
    def override_with(self, file):
        self.config2 = ConfigParser.ConfigParser()
        f = open(file)
        self.config2.readfp(f)
        f.close
    
    def get(self, option, section="default"):
        """Get the value for an option in a specific section"""
        try: 
            return self.config2.get(section, option)
        except:
            try:
                return self.config.get(section, option)
            except:
                return None

def main():
    global LOG_ON_FILE 
    global LOG_ON_SCREEN 

    usage="%prog [options] config_file.ini"
    parser = OptionParser(usage, version=__version__)
    parser.add_option("-v", "--verbose", action="count", dest="verbose", default=LOG_ON_SCREEN, help="Be more verbose on screen. Can be called multiple times.")
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="Enable debug mode. Will show debug messages on screen and on the logs")
    parser.add_option("-r", "--run", action="append", dest="server", default=[], help="Instead of running it for every server, just run the backup on the specified servers. It can be called multiple times")
    parser.add_option("-n", "--dry", action="store_true", dest="dry", default=False, help="Enable dry mode. Will not do anything, just show it on the terminal")

    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        parser.error("Config file should be specified")
    
    # Set the debug levels
    if options.dry:
        LOG_ON_FILE   = NONE
        LOG_ON_SCREEN = DEBUG
    elif options.debug:
        LOG_ON_FILE   = DEBUG
        LOG_ON_SCREEN = DEBUG
    elif options.verbose > LOG_ON_SCREEN:
        LOG_ON_SCREEN = options.verbose
    
    # Read the config file
    try:
        config = Config(file=args[0], verbose = options.verbose)
    except IOError:
        parser.error("Could not open config file.")
    except ConfigParser.NoOptionError:
        parser.error("Config file not complete.")
        
    mainlogger = Logger(config.get("logdir") + "/" + "monkey-backup.log", prefix=config.get("lognameprefix"))
    mainlogger.info("main - Backup started.")
    backup_monkey = BackupMonkey(num_workers=int(config.get("threads")), logger=mainlogger, dry=options.dry)
    
    if options.server:
        servers_to_backup=options.server
    else:
        servers_to_backup=os.listdir(config.get("backupdir"))

    for file in servers_to_backup:
        if os.path.isdir(config.get("backupdir") + "/" + file):
            try:
                server = Server(config.get("backupdir") + "/" + file, Config(file=args[0], verbose = options.verbose))
                priority = int(server.config.get("priority"))
            except:
                mainlogger.critical("main - Host " + config.get("backupdir") + " could not be added: " + str(sys.exc_info()[1]))
            else:
                backup_monkey.enqueue(server, priority )

    # after all the servers have been queued start processing them
    backup_monkey.start()
    for i in range(backup_monkey.get_num_monkeys()):
        backup_monkey.enqueue(None, 999999)
    
    # wait until all the backups have finished
    backup_monkey.wait()
    
    mainlogger.info("main - Backup finished.")
    mainlogger.close()
