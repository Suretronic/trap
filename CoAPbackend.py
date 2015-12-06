#! /usr/bin/env python
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

try:
    import asyncio
except ImportError:
    # Trollius >= 0.3 was renamed
    import trollius as asyncio

from os import environ
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

import sys
import logging
import subprocess
import socket

import readline

import aiocoap
import aiocoap.proxy.client

import json, requests
import ast
import memcache

topic = u'armote.trap.reedsensor'

def configure_logging(verbosity):
    logging.basicConfig()

    if verbosity <= -2:
        logging.getLogger('coap').setLevel(logging.CRITICAL + 1)
    elif verbosity == -1:
        logging.getLogger('coap').setLevel(logging.ERROR)
    elif verbosity == 0:
        logging.getLogger('coap').setLevel(logging.WARNING)
    elif verbosity == 1:
        logging.getLogger('coap').setLevel(logging.INFO)
    elif verbosity >= 2:
        logging.getLogger('coap').setLevel(logging.DEBUG)

def incoming_observation(response, appSess, sessDetails):
    sys.stdout.buffer.write(b'---\n')
    if response.code.is_successful():
        sys.stdout.buffer.write(response.payload + b'\n' if not response.payload.endswith(b'\n') else b'')
        sys.stdout.buffer.flush()
        s = json.dumps(response.payload.decode('utf-8'))
        p = ast.literal_eval(json.loads(s))
        obj = {'macadrs': p['mc'], 'is_sprung': p['st'], 'datetime' : p['dttm'], 'volts': p['vt']}
        print('backend publishing armote.trap.reedsensor', obj)
        appSess.publish(topic, obj)
        # Cache incoming observation
        s = memcache.Client(["127.0.0.1:11211"])
        keytext = sessDetails.realm + '.' + topic
        s.set(keytext, obj, 600) # store address in cache with timeout
    else:
        print(response.code, file=sys.stderr)
        if response.payload:
            print(response.payload.decode('utf-8'), file=sys.stderr)

@asyncio.coroutine
def coap_request(appSess, sessDetails):
    print("coap_request...\n")
    #url = "coap://trap.armote.net/sensors/reedRelay"
    url = "coap://[2001:4428:29a::212:4b00:69c:f00d]/sensors/reedRelay"
    observe = True
 
    configure_logging(0)

    context = yield from aiocoap.Context.create_client_context()
    request = aiocoap.Message(code=getattr(aiocoap.numbers.codes.Code,'GET'))
    try:
        request.set_request_uri(url)
    except ValueError as e:
        raise parser.error(e)

    if not request.opt.uri_host:
        raise parser.error("Request URLs need to be absolute.")

    request.opt.accept = aiocoap.numbers.media_types_rev['application/json']

    if observe:
        request.opt.observe = 0
        observation_is_over = asyncio.Future()

    # request.opt.content_format = int(options.content_format)
    interface = context
    try:
        requester = interface.request(request)

        if observe:
            requester.observation.register_errback(observation_is_over.set_result)
            requester.observation.register_callback(lambda data: incoming_observation(data, appSess, sessDetails))
        try:
            response_data = yield from requester.response
        except socket.gaierror as  e:
            print("Name resolution error:", e, file=sys.stderr)

        if response_data.code.is_successful():
            sys.stdout.buffer.write(response_data.payload)
            sys.stdout.buffer.flush()
            incoming_observation(response_data, appSess, sessDetails)
            # if not response_data.payload.endswith(b'\n'):
            #     sys.stderr.write('\n(No newline at end of message)\n')
        else:
            print(response_data.code, file=sys.stderr)
            if response_data.payload:
                print(response_data.payload.decode('utf-8'), file=sys.stderr)
            sys.exit(1)

        if observe:
            print ("Observing...\n")
            exit_reason = yield from observation_is_over
            print("Observation is over: %r"%(exit_reason,), file=sys.stderr)
    finally:
        if not requester.response.done():
            requester.response.cancel()
        if observe and not requester.observation.cancelled:
            requester.observation.cancel()

class AppSession(ApplicationSession):
    """
    An application component that publishes CoAP notifications.
    """


    def onJoin(self, sessDetails):
        print("session attached")
        
        def lastEvent():
            s = memcache.Client(["127.0.0.1:11211"])
            keytext = sessDetails.realm + '.' + topic
            obj = s.get(keytext) # try get cached topic object
            if obj != None:
                print('backend re-publishing armote.trap.reedsensor', obj)
                #self.publish(topic, obj)
                return obj

        try:
            yield from asyncio.async(self.register(lastEvent, u'armote.trap.reedsensorLast'))
            print("procedure registered")
        except Exception as e:
            print("could not register procedure: {0}".format(e))
	   
        yield from asyncio.async(coap_request(self,sessDetails))

if __name__ == '__main__':
	
    wampAddress = u"ws://192.168.1.11:8080/ws"
    wampRealm = u"trapsensor"

    runner = ApplicationRunner(
        #environ.get("AUTOBAHN_TRAPSENSOR_ROUTER", u"ws://192.168.1.112:8080/ws"),
        wampAddress,
        realm = wampRealm,
        debug_wamp=False,  # optional; log many WAMP sessDetails
        debug=False,  # optional; log even more sessDetails
    )
    runner.run(AppSession)

