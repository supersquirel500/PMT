# ---------------------------------------
#  _____  __  __ _______        __   ___  
# |  __ \|  \/  |__   __|      /_ | / _ \ 
# | |__) | \  / |  | |    __   _| || | | |
# |  ___/| |\/| |  | |    \ \ / / || | | |
# | |    | |  | |  | |     \ V /| || |_| |
# |_|    |_|  |_|  |_|      \_/ |_(_)___/ 
# ----------------------------------------
#  Version 1.0
#  microPython Firmware esp32spiram-idf3-20191220-v1.12
#  Filename : reqst.py
#
#  uRequest extension
#  + Socket timeout
#  + HTTP Redirection
#  + Tag Parsing

import usocket
# garbage collector
import gc
from machine import reset,Timer
import ussl

# Returns Tuple of information from URL
def breakdown_url(url):
    try:
        proto, dummy, host, path = url.split("/", 3)
        path = "/{}".format(path) # Wireshark observation
    except ValueError:
        proto, dummy, host = url.split("/", 2)
        path = ""
    if proto == "http:":
        port = 80
    elif proto == "https:":
        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    return [proto, dummy, host, path, port]

def handlerTimer(timer):
    print("DNS_Lookup_Test: Timer Timeout")
    #Resets the device in a manner similar to pushing the external RESET button.
    reset()

# Initial check for open internet or splash page redirection
# Return Value: 5 value list: [addr, status, location, body, headers]
def request_dns_internet(method, url, data=None, json=None, headers={}, stream=None, timeout=3000):
    # Get stuff from URL
    _, dummy, host, _, _ = breakdown_url(url)
    # No need to check if Host is IP. It's first request we
    # do after connection
    # TODO: Uncomment if we decide it's needed
    # init harware timer
    # timer = Timer(0)
    # TODO: Uncomment this for solution
    #timer.init(period=3000, mode=Timer.ONE_SHOT,callback=handlerTimer)
    location = None

    ai = usocket.getaddrinfo(host, 80, 0, usocket.SOCK_STREAM)
    #TODO: Uncomment this for solution
    #timer.deinit()
    if ai != []:
        print(str(ai))
        print("DNS Lookup [OK]")
    else:
        print("DNS Lookup [Failed]")
        return [None,584,None,None,None]

    ai = ai[0]
    addr = ai[-1]
    recvd_headers = []
    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        s.connect(ai[-1])
        #if proto == "https:":
        #    s = ussl.wrap_socket(s, server_hostname=host)
        s.write(b"%s /api/ HTTP/1.0\r\n" % (method))
        if not "Host" in headers:
            s.write(b"Host: %s\r\n" % host)
        # Iterate over keys to avoid tuple alloc
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")
        if json is not None:
            assert data is None
            import ujson
            data = ujson.dumps(json)
            s.write(b"Content-Type: application/json\r\n")
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
        s.write(b"\r\n")
        if data:
            s.write(data)

        l = s.readline()
        print(l)
        l = l.split(None, 2)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            #print(l)
            colon = l.find(':')
            if colon != -1:
                key = l[0:colon]
                val = l[colon+1:]
                print("Header (key:val) {0}:{1}".format(key,val))
                recvd_headers[key]=val

            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    s.close()
                    del s
                    raise ValueError("Unsupported " + l)
            elif l.startswith(b"Location:"): # and not 200 <= status <= 299:
                location = str(l[10:])[2:-5]
                #print("Location [{}]".format(location))
                # close socket (should prevent ENOMEM error)
                # s.close()
                # del s
                # gc.collect()
                print("Redirection [{}]".format(location))
                # need to get the method from the redirection
    except (OSError, TypeError) as e:
        #TODO: remove print
        print("Warning: {0}".format(str(e)))

    print("Status_Code [{}]".format(status))
    body = s.read()
    s.close()
    del s
    gc.collect()
    print("Returning from request_dns_internet")
    return [addr, status, location, body.decode("utf-8"), headers]



def request_splash_page(method, url, data=None, json=None, headers={}, stream=None, timeout=3000):
    # Get stuff from URL
    proto, dummy, host, path, port = breakdown_url(url)
    
    # DNS Host or IPv4
    is_ipv4 = False
    eight_bits = host.split(".")[0]
    # check 8 bits is enought
    try:
        if 0 < int(eight_bits) < 255:
            is_ipv4 = True
    except ValueError:
        # not an IP
        pass

    #DNS Resolving Test
    if not is_ipv4:
        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        if ai != []:
            print("DNS Lookup [OK]")
            ai = ai[0]
        else:
            print("DNS Lookup [Failed]")
            return [584,None]
    else:
        # Is IPv4
        print("DNS Lookup [Skipped]")
        # socket settings
        ai = [2,1,0,(host,port)]

    print(str(ai))
    addr = ai[-1]
    recvd_headers = []
    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        
        if proto == "https:":
            s = ussl.wrap_socket(s, server_hostname=host)
        s.connect(ai[-1])

        s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))
        if not "Host" in headers:
            s.write(b"Host: %s\r\n" % host)
        # Iterate over keys to avoid tuple alloc
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")
        if json is not None:
            assert data is None
            import ujson
            data = ujson.dumps(json)
            s.write(b"Content-Type: application/json\r\n")
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
        s.write(b"\r\n")
        if data:
            s.write(data)

        l = s.readline()
        print(l)
        l = l.split(None, 2)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            #print(l)
            colon = l.find(':')
            if colon != -1:
                key = l[0:colon]
                val = l[colon+1:]
                print("Header (key:val) {0}:{1}".format(key,val))
                recvd_headers[key]=val
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    s.close()
                    del s
                    raise ValueError("Unsupported " + l)
            elif l.startswith(b"Location:") and not 200 <= status <= 299:
                location = str(l[10:])[2:-5]
                
                print("L2 Location [{}]".format(location))
                # close socket (should prevent ENOMEM error)
                s.close()
                del s
                gc.collect()
                print("L2 Redirection")
                # need to get the method from the redirection
                res = test_dns_internet(location)[0:1]
                return [res[0], res[-1]] #CURRAN TODO: these values are now incorrect, get with David/Ben and find out what is needed
    except OSError as err:
        print(str(err))
        s.close()
        del s
        gc.collect()
        raise
    
    print("Status_Code [{}]".format(status))

    page = s.read()
    s.close()
    del s
    gc.collect()
    return [addr,status,page,headers]



def request(method, url, data=None, json=None, headers={}, stream=None, timeout=0.5):

    # DNS Host or IPv4
    is_ipv4 = False
    eight_bits = url.split(".")[0]
    # check 8 bits is enought
    try:
        if 0 < int(eight_bits) < 255:
            is_ipv4 = True
    except ValueError:
        # not an IP
        pass


    #DNS Resolving Test
    if not is_ipv4:

        # Get stuff from URL
        proto, dummy, host, path, port = breakdown_url(url)
        print("breakdown url returned: host: {0} port:{1} path:{2}".format(host,port,path))

        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        if ai != []:
            print("DNS Lookup [OK]")
            ai = ai[0]
        else:
            print("DNS Lookup [Failed]")
            return [584,None]
    else:
        # Is IPv4
        print("URL breakdown & DNS Lookup [Skipped]")
        # socket settings
        ai = [2,1,0,(host,port)]
    
    addr = ai[-1]
    recvd_headers = {}

    s = usocket.socket(ai[0], ai[1], ai[2])
    # set timeout
    s.settimeout(timeout)
    try:
        print("Connecting to {} ...".format(ai[-1]))
        s.connect(ai[-1])
        if proto == "https:":
            s = ussl.wrap_socket(s, server_hostname=host)
        s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))
        print("%s /%s HTTP/1.0\r\n" % (method, path))
        if not "Host" in headers:
            s.write(b"Host: %s\r\n" % host)
        # Iterate over keys to avoid tuple alloc
        print("Sending Headers...")
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")
            print("{0}: {1}".format(k,headers[k]))
        if json is not None:
            assert data is None
            import ujson
            data = ujson.dumps(json)
            s.write(b"Content-Type: application/json\r\n")
        print("Sending Headers...")
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
            print("Content-Length: %d\r\n" % len(data))
        s.write(b"\r\n")
        print("Headers Sent... \\r\\n")
        print("Sending body...")
        if data:
            s.write(data)
            print(data)
        
        l = s.readline()
        print(l)
        l = l.split(None, 2)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            l=l[0:-2] #remove newline chars
            colon = l.find(b':')
            if colon != -1:
                key = l[0:colon].decode('utf-8')
                val = l[colon+1:].decode('utf-8')
                print("Header (key:val) {0}:{1}".format(key,val))
                recvd_headers[key]=val
            #print(l)
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    raise ValueError("Unsupported " + l)
            elif l.startswith(b"Location:") and not 200 <= status <= 299:
                location = str(l[10:])[2:-5]
                print("Post Request Location [{}]".format(location))
                # close socket (should prevent ENOMEM error)
                s.close()
                del s
                gc.collect()
                print("Post Request Redirection")
                # need to get the method from the redirection
                return request_splash_page("GET",location)
    except OSError as err:
        s.close()
        del s
        gc.collect()
        raise

    print("Status_Code [{}]".format(status))
    
    # No need to read
    page = s.read()
    s.close()
    del s
    gc.collect()
    return [addr, status, page, recvd_headers]


def test_dns_internet(url, **kw):
    return request_dns_internet("GET", url, **kw)

def get_splash_page(url, **kw):
    return request_splash_page("GET", url, **kw)

def get(url, **kw):
    return request("GET", url, **kw)

def post(url, **kw):
    return request("POST", url, **kw)
