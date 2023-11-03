import subprocess
import flask
import logging
from flask import Flask,jsonify
from os.path import exists
import iperf3
from multiprocessing import Process
import boto3
import os

# sample server

app = Flask(__name__)

def get_prompt_ip():
    '''
    Implements a very simple method to retrieve an idle prompt server ready to take traffic.
    TODO: a prod-ready example for idle ip retrieval, based on dynamoDB, will be provided in next iteration.
    '''
    table_name = os.environ['ROUTING_TABLE_NAME']
    ddb_entry_key = os.environ['ROUTING_ENTRY_KEY']
    dynamodb = boto3.client('dynamodb', region_name='us-west-2')
    ddb_response = dynamodb.get_item(TableName=table_name, Key={'EndpointName':{'S':ddb_entry_key}})
    for key in ddb_response['Item']:
        if key != 'EndpointName':
            print(key)
            return key

def get_prompt_ports():
    '''
    Ports to connect to the prompt server.
    '''
    return [5001, 5002, 5003, 5004, 5005]

def get_clients():
    '''
    Generates a list of iperf3 clients. Each client use 5 streams.
    '''
    clients = []
    for port in get_prompt_ports():
        client = iperf3.Client()
        client.server_hostname = get_prompt_ip()
        client.zerocopy = True
        client.verbose = True
        client.reverse = True
        client.port = port
        client.num_streams = 5
        client.duration = 10
        clients.append(client)
    return clients

def start_bandwidth_test(iperf3_client):
    '''
    Start a bandwidth test that lasts 10 seconds between the iperf3 client and iperf3 server.
    '''
    print('Starting iperf3 client run on port {0}'.format(iperf3_client.port))
    result = iperf3_client.run()
    print('Megabits per second  (Mbps)  {0} for client port {1}'.format(result.received_Mbps, iperf3_client.port))

@app.route('/invocations', methods=['POST'])
def serve():
    '''
    The standard API required for Sagemaker model container.
    This method is considered the backend of InvokeEndpoint() calls to a Sagemaker endpoint.
    '''
    procs = []

    # instantiating process with arguments
    for client in get_clients():
        print("Starting testing on port {}".format(client.port))
        proc = Process(target=start_bandwidth_test, args=[client])
        procs.append(proc)
        proc.start()

    # complete the processes
    for proc in procs:
        proc.join()

    # returns a dummy response. Actual performance testing results can be found in logs.
    return jsonify({"ExitCode": 0, "Body": "{}"})

@app.route('/ping', methods=['GET'])
def ping():
    '''
    The standard API required for Sagemaker model container.
    Just return "I am healthy!"
    '''
    return "success", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0')
