#!/usr/bin/python

# Used for the proxy selector script on Jormungandr Proxy Selector,
# another project by sdsdkkk
#
# Jormungandr Proxy Selector is a proxy selector written in C#
# with proxy testing functionality written in Python
#
# As proxy servers have caching capabilities, this script can only be used
# to test how fast the proxy server send the respond back to the client,
# regardless of whether the proxy server fetch the web page directly from
# the web server or just from the proxy server's cache.
#
# The implementation for forcing the proxy server to fetch the web page from
# the web server was written in C# side of the application, and has not been
# ported to the Python script yet.
#
# To do it in this version, get the proxy server to fetch Google's search
# result page, using randomly generated keyword embedded in the URL. Use that
# URL as the input argument to this script.

from datetime import datetime
from datetime import timedelta
import httplib
import sys
import optparse

#============================= PROXY SELECTOR CONFIGURATION =============================#
BUFFER_LENGTH = 60			# amount of record history saved
MA_PERIOD = 9				# moving average interval to make predictions
TIMEOUT = 10				# set timeout for connections
PROXY_LIST = 'proxylist.txt'		# list of proxy servers to be tested
RECORD_FILE = 'record.txt'		# testing history and prediction records
TESTING_URL = 'http://www.google.com'	# the URL to fetch web page from
SHOW_RECORDS = False			# show/don't show all data on record
#========================================================================================#


#================================== CLASS: ProxyServer ==================================#
# The ProxyServer class is used to store an individual proxy server's information, doing
# tests, and calculating predictions

class ProxyServer:
    def __init__(self, Proxy_Address, Proxy_Port, Trial_History, Prediction_History):
        self.ProxyAddress = Proxy_Address
        self.ProxyPort = Proxy_Port
        self.TrialHistory = Trial_History
        self.PredictionHistory = Prediction_History

    def CheckDelay(self):
        try:
            startTime = datetime.now()

            #Start a HTTP connection to the HTTP proxy
            c = httplib.HTTPConnection(self.ProxyAddress, self.ProxyPort)
            #Make a request to the web server
            c.request("GET", TESTING_URL)
            #set timeout
            c.sock.settimeout(TIMEOUT)
            r = c.getresponse()
            
            #Fetching the web page
            total_fetched_data = ''
            while 1:
                data = r.read(1024)
                total_fetched_data = total_fetched_data + data
                if len(data) < 1024:
                    break
            endTime = datetime.now()
            #Calculate delay, save to history
            delay = endTime - startTime
            current_speed = float(sys.getsizeof(total_fetched_data)) * 8/delay.seconds
            self.TrialHistory.insert(0, current_speed)
            prediction = 0
            if len(self.TrialHistory) >= MA_PERIOD:
                totalvalue = 0
                for i in range(1, MA_PERIOD + 1):
                    totalvalue = totalvalue + self.TrialHistory[i-1]
                prediction = float(totalvalue)/float(MA_PERIOD)
            self.PredictionHistory.insert(0, prediction)
        except:
            #If server didn't respond
            self.TrialHistory.insert(0, 0)
            prediction = 0
            if len(self.TrialHistory) >= MA_PERIOD:
                totalvalue = 0
                for i in range(1, MA_PERIOD + 1):
                    totalvalue = totalvalue + self.TrialHistory[i-1]
                prediction = float(totalvalue)/float(MA_PERIOD)
            self.PredictionHistory.insert(0, prediction)

        msg = self.ProxyAddress + ':' + str(self.ProxyPort)
        if len(self.TrialHistory) > BUFFER_LENGTH:
            self.TrialHistory.pop()
            self.PredictionHistory.pop()
        for i in range(0, len(self.TrialHistory)):
            msg = msg + ' ' + str(self.TrialHistory[i]) + ':' + str(self.PredictionHistory[i])
        return msg

#================================ CLASS: ProxyServerList ================================#
# The ProxyServerList class is used to manage a list of proxy servers, starting the tests,
# and writing the results into test record file

class ProxyServerList:
    def __init__(self):
        #Initialize empty list to contain server data
        self.ServerList = []
        proxystringlist = []

        #Get proxy list
        with open(PROXY_LIST) as f:
            fcontent = f.read()
            content = fcontent.split('\n')

        for index in range(len(content)):
            if len(content[index]) > 0 and content[index][0] != '#':
                prox_info = content[index]
                proxystringlist.insert(len(proxystringlist), prox_info)
                
        if len(proxystringlist) == 0:
            print 'Proxy list on proxylist.txt is empty.'
            sys.exit()

        #Match listed proxy with saved records
        with open(RECORD_FILE) as f:
            fcontent = f.read()
            content = fcontent.split('\n')
            
        for index in range(len(content)):
            if len(content[index]) > 0 and content[index][0] != '#':
                records = content[index].split(' ')
                if records[0] in proxystringlist:
                    proxystringlist.remove(records[0])
                    prox_info = records[0].split(':')
                    prox_address = prox_info[0]
                    prox_port = int(prox_info[1])
                    test_record = []
                    prediction_record = []
                    for i in range(1, len(records)):
                        time = records[i].split(':')
                        testrecorditem = float(time[0])
                        predictionrecorditem = float(time[1])
                        test_record.insert(len(test_record), testrecorditem)
                        prediction_record.insert(len(prediction_record), predictionrecorditem)
                    p = ProxyServer(prox_address, prox_port, test_record, prediction_record)
                    self.ServerList.insert(len(self.ServerList), p)
                    
        for index in range(len(proxystringlist)):
            prox_info = proxystringlist[index].split(':')
            prox_address = prox_info[0]
            prox_port = int(prox_info[1])
            p = ProxyServer(prox_address, prox_port, [], [])
            self.ServerList.insert(len(self.ServerList), p)

    def TestServers(self):
        f = open(RECORD_FILE, 'w')
        f.write("# This file is used to store the records of the proxies tested\n")
        f.write("# Modifying this file directly is not recommended, as for it can affect the program's performance\n\n")
        for server in self.ServerList:
            msg = server.CheckDelay()
            if SHOW_RECORDS:
                print msg
            else:
                buff = msg.split(' ')
                print buff[0] + ' ' + buff[1]
            f.write(msg + '\n')
        f.close()


#===================================== MAIN PROGRAM =====================================#

def main():
    global SHOW_RECORDS
    parser = optparse.OptionParser()
    parser.add_option("-t", "--target", action="store", type="string", dest="URL", help="change default testing URL", metavar="URL")
    parser.add_option("-r", "--record", action="store", type="string", dest="record", help="if true, show contents of record file", metavar="[T|F]")
    options, args = parser.parse_args()
    TESTING_URL = options.URL
    if options.record == 'T' or options.record == 't':
        SHOW_RECORDS = True
    proxylist = ProxyServerList()
    proxylist.TestServers()

if __name__ == "__main__":
    main()
