import subprocess
import time
import flask
import logging
from flask import Flask,jsonify
from os.path import exists
import iperf3
from multiprocessing import Process, Queue
import multiprocessing
import boto3
import os

# sample server

app = Flask(__name__)
Q = Queue()

def get_primary_prompt_ip():
    '''
    Implements a very simple method to retrieve an idle prompt server ready to take traffic.
    '''
    table_name = os.environ['ROUTING_TABLE_NAME']
    ddb_entry_key = os.environ['ROUTING_ENTRY_KEY']
    az = os.environ['AWS_AVAILABILITY_ZONE']
    network_nodes = os.environ['AWS_NETWORK_NODES']
    topology = network_nodes.split(', ')
    spine = topology[0]

    dynamodb = boto3.client('dynamodb', region_name='us-west-2')
    ddb_response = dynamodb.query(
        TableName=table_name,
        Select='ALL_ATTRIBUTES',
        Limit=100,
        ConsistentRead=True,
        KeyConditionExpression='#pk = :pkv',
        FilterExpression='(#r = :r OR #rt < :now) AND #ttl >= :now AND #azid = :az AND contains(#spine, :spine)',
        ExpressionAttributeNames={
            '#pk': 'ModelGroup-PrimaryNetworkTopo-shard',
            '#r': 'Reserved',
            '#ttl': 'TimeToLive',
            '#rt': 'ReservationTimeout',
            '#azid': 'AzId',
            '#spine': 'NetworkNodes'
        },
        ExpressionAttributeValues={
            ':pkv': { 'S': ddb_entry_key },
            ':r': { 'N': '0' },
            ':now': { 'N': str(int(time.time())) },
            ':az': { 'S': az },
            ':spine': { 'S': spine }
        }
    )
    return [{'key': item['EndpointName-Az-spine-partition']['S'], 'ipaddr': item['IpAddress']['S']} for item in ddb_response['Items']]

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
        client.server_hostname = get_primary_prompt_ip()
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
    print('Starting iperf3 client run on server {0} port {1}'.format(iperf3_client.server_hostname, iperf3_client.port))
    result = iperf3_client.run()
    print('Megabits per second  (Mbps)  {0} for client port {1}'.format(result.received_Mbps, iperf3_client.port))
    Q.put({"Speed": result.received_Mbps})

@app.route('/invocations', methods=['POST'])
def serve():
    '''
    The standard API required for Sagemaker model container.
    This method is considered the backend of InvokeEndpoint() calls to a Sagemaker endpoint.
    '''
    procs = []

    for client in get_clients():
        proc = Process(target=start_bandwidth_test, args=[client])
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()

    result = []
    total_speed = 0
    for i in range(len(get_prompt_ports())):
        port_res = Q.get()
        total_speed += port_res["Speed"]

    total_Gbps = total_speed / 1000 # Gbps to Mbps conversion ratio is 1000, not 1024
    return jsonify({"Total Bandwidth": "{} Gbps".format(total_Gbps)})

@app.route('/ping', methods=['GET'])
def ping():
    '''
    The standard API required for Sagemaker model container.
    Just return "I am healthy!"
    '''
    return "success", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0')
